import json
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs


MAX_WORKERS = 10


class ThreadPoolHTTPServer(ThreadingMixIn, HTTPServer):
    """
    使用固定线程池处理请求，而不是每个请求创建一个新线程。

    这样更接近真实服务端：
    - 线程数量有限；
    - 超过线程池容量的请求需要排队；
    - 可以观察阻塞式 I/O 在线程资源受限时的性能变化。
    """

    daemon_threads = True

    def __init__(self, server_address, request_handler_class, max_workers=50):
        super().__init__(server_address, request_handler_class)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def process_request(self, request, client_address):
        self.executor.submit(self.process_request_thread, request, client_address)

    def server_close(self):
        super().server_close()
        self.executor.shutdown(wait=True)


class ThreadPoolHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_json({"status": "ok"})
            return

        if parsed.path == "/io":
            query = parse_qs(parsed.query)
            delay = float(query.get("delay", ["0.5"])[0])

            # 阻塞式等待，会占用线程池中的一个工作线程
            time.sleep(delay)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ok')
            return

        self.send_response(404)
        self.end_headers()

    def send_json(self, data: dict):
        body = json.dumps(data).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # 关闭访问日志，避免日志 I/O 影响压测结果
        return


def main():
    host = "127.0.0.1"
    port = 8001

    server = ThreadPoolHTTPServer(
        (host, port),
        ThreadPoolHTTPHandler,
        max_workers=MAX_WORKERS,
    )

    print(
        f"Thread pool HTTP server running at http://{host}:{port}, "
        f"max_workers={MAX_WORKERS}"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
