#!/usr/bin/env python3
"""
XiaoLing (小玲) - Local Model Backend Service
Supports:
- Web UI serving (index.html)
- Health check endpoint (/health, /api/health)
- OpenAI-compatible chat completions (/v1/chat/completions)
- Sandbox knowledge base learning endpoint (/api/learn, /v1/sandbox/learn)
- --daemon quiet background mode
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# In-memory sandbox knowledge base
SANDBOX_KNOWLEDGE_BASE = []

class XiaoLingHandler(BaseHTTPRequestHandler):
      def _send_cors_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

      def do_OPTIONS(self):
                self.send_response(200)
                self._send_cors_headers()
                self.end_headers()

      def do_GET(self):
                parsed_path = urllib.parse.urlparse(self.path).path

        # 1. Health check endpoint
                if parsed_path in ['/health', '/api/health', '/v1/health']:
                              self.send_response(200)
                              self.send_header('Content-Type', 'application/json')
                              self._send_cors_headers()
                              self.end_headers()
                              response = {
                                  "status": "ok",
                                  "service": "xiaoling-backend",
                                  "version": "1.0.0",
                                  "knowledge_items": len(SANDBOX_KNOWLEDGE_BASE)
                              }
                              self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                              return

                # 2. Web interface serving (index.html)
                if parsed_path in ['/', '/index.html']:
                              file_path = os.path.join(os.path.dirname(__file__), 'index.html')
                              if os.path.exists(file_path):
                                                self.send_response(200)
                                                self.send_header('Content-Type', 'text/html; charset=utf-8')
                                                self._send_cors_headers()
                                                self.end_headers()
                                                with open(file_path, 'rb') as f:
                                                                      self.wfile.write(f.read())
                              else:
                                                self.send_response(404)
                                                self.end_headers()
                                                self.wfile.write(b"index.html not found")
                                            return

        # Fallback 404
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b"Not Found")

      def do_POST(self):
                parsed_path = urllib.parse.urlparse(self.path).path
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'

        try:
                      body = json.loads(post_data.decode('utf-8')) if post_data else {}
except Exception:
            body = {}

        # 3. OpenAI-compatible local chat completions endpoint
        if parsed_path in ['/v1/chat/completions', '/api/chat']:
                      messages = body.get('messages', [])
                      model = body.get('model', 'xiaoling-local')

            user_prompt = ""
            for msg in reversed(messages):
                              if msg.get('role') == 'user':
                                                    user_prompt = msg.get('content', '')
                                                    break

                          reply_content = f"【小玲本地回复】收到的消息: '{user_prompt}'。"
            if SANDBOX_KNOWLEDGE_BASE:
                              reply_content += f"\n(当前沙箱知识库已学习 {len(SANDBOX_KNOWLEDGE_BASE)} 条数据)"

            response_payload = {
                              "id": f"chatcmpl-xiaoling-{int(time.time())}",
                              "object": "chat.completion",
                              "created": int(time.time()),
                              "model": model,
                              "choices": [{
                                                    "index": 0,
                                                    "message": {
                                                                              "role": "assistant",
                                                                              "content": reply_content
                                                    },
                                                    "finish_reason": "stop"
                              }],
                              "usage": {
                                                    "prompt_tokens": len(user_prompt),
                                                    "completion_tokens": len(reply_content),
                                                    "total_tokens": len(user_prompt) + len(reply_content)
                              }
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode('utf-8'))
            return

        # 4. Sandbox knowledge base learning endpoint
        if parsed_path in ['/api/learn', '/v1/sandbox/learn', '/api/knowledge/learn']:
                      content = body.get('content') or body.get('text') or body.get('data') or "Empty content"
                      source = body.get('source', 'user-sandbox')

            item = {
                              "id": len(SANDBOX_KNOWLEDGE_BASE) + 1,
                              "content": content,
                              "source": source,
                              "timestamp": time.time()
            }
            SANDBOX_KNOWLEDGE_BASE.append(item)

            response_payload = {
                              "status": "success",
                              "message": "沙箱知识库已成功学新条目",
                              "item": item,
                              "total_items": len(SANDBOX_KNOWLEDGE_BASE)
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode('utf-8'))
            return

        # Fallback 404
        self.send_response(404)
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(b"Not Found")


def run_server(host='0.0.0.0', port=8000):
      server_address = (host, port)
    httpd = HTTPServer(server_address, XiaoLingHandler)
    print(f"[*] 小玲 (XiaoLing) 本地后端服务已启动: http://{host}:{port}")
    try:
              httpd.serve_forever()
except KeyboardInterrupt:
        print("\n[*] 服务已停止。")


def daemonize():
      """Run server in silent background daemon mode"""
    if os.name != 'posix':
              print("[!] --daemon mode relies on POSIX fork. Running standard background mode...")
              run_server()
              return

    try:
              pid = os.fork()
              if pid > 0:
                            print(f"[*] 小玲服务已切换至后台静默运行 (PID: {pid})")
                            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"Fork failed: {e}\n")
        sys.exit(1)

    os.setsid()
    os.umask(0)

    try:
              pid = os.fork()
              if pid > 0:
                            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"Fork #2 failed: {e}\n")
        sys.exit(1)

    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null', 'r') as f:
              os.dup2(f.fileno(), sys.stdin.fileno())
          with open('xiaoling_daemon.log', 'a+') as f:
                    os.dup2(f.fileno(), sys.stdout.fileno())
                    os.dup2(f.fileno(), sys.stderr.fileno())

    run_server()


if __name__ == '__main__':
      parser = argparse.ArgumentParser(description="小玲 (XiaoLing) 本地模型后端服务")
    parser.add_argument('--host', default='0.0.0.0', help='监听地址 (默认 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='监听端口 (默认 8000)')
    parser.add_argument('--daemon', action='store_true', help='静默后台运行模式')

    args = parser.parse_args()

    if args.daemon:
              daemonize()
else:
        run_server(host=args.host, port=args.port)
