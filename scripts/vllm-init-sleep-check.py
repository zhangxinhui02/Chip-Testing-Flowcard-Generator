#!/usr/bin/env python3
"""
vLLM post-start gatekeeper

行为：
1. 后台轮询 vLLM 的 /health，直到 ready
2. 调用一次 POST /sleep?level=1
3. 对外暴露新的 /health
   - 在 sleep 成功前返回 503
   - 在 sleep 成功后返回 200
"""

from __future__ import annotations

import json
import logging
import signal
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

VLLM_HOST = "127.0.0.1"
VLLM_PORT = 8000
GATE_HOST = "0.0.0.0"
GATE_PORT = 18080

READY_TIMEOUT_SECONDS = 1800
POLL_INTERVAL_SECONDS = 3
HTTP_TIMEOUT_SECONDS = 10
SLEEP_LEVEL = 1

LOG_LEVEL = "INFO"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("vllm-init-sleep-check")


class State:
    """共享状态"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.ready_for_compose = False
        self.vllm_ready = False
        self.sleep_called = False
        self.error: str | None = None
        self.start_ts = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "ready_for_compose": self.ready_for_compose,
                "vllm_ready": self.vllm_ready,
                "sleep_called": self.sleep_called,
                "error": self.error,
                "uptime_seconds": round(time.time() - self.start_ts, 3),
            }

    def set_vllm_ready(self, value: bool) -> None:
        with self._lock:
            self.vllm_ready = value

    def set_sleep_called(self, value: bool) -> None:
        with self._lock:
            self.sleep_called = value

    def set_ready_for_compose(self, value: bool) -> None:
        with self._lock:
            self.ready_for_compose = value

    def set_error(self, value: str | None) -> None:
        with self._lock:
            self.error = value


STATE = State()
STOP_EVENT = threading.Event()


def build_url(path: str) -> str:
    return f"http://{VLLM_HOST}:{VLLM_PORT}{path}"


def http_request(url: str, method: str = "GET", body: bytes | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url=url, method=method, data=body)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        return resp.status, resp.read()


def wait_until_vllm_ready() -> None:
    deadline = time.time() + READY_TIMEOUT_SECONDS
    health_url = build_url("/health")

    logger.info("Waiting for vLLM to become ready: %s", health_url)

    while not STOP_EVENT.is_set():
        if time.time() > deadline:
            raise TimeoutError(
                f"Timed out waiting for vLLM readiness after {READY_TIMEOUT_SECONDS} seconds"
            )

        try:
            status, _ = http_request(health_url, method="GET")
            if status == HTTPStatus.OK:
                STATE.set_vllm_ready(True)
                logger.info("vLLM is ready.")
                return
        except urllib.error.HTTPError as e:
            logger.warning("vLLM /health returned HTTP %s; retrying.", e.code)
        except urllib.error.URLError as e:
            # logger.info("vLLM /health not ready yet: %s", e.reason)
            pass
        except Exception as e:
            logger.warning("Unexpected error when probing vLLM /health: %s", e)

        time.sleep(POLL_INTERVAL_SECONDS)


def call_sleep_once() -> None:
    sleep_url = build_url(f"/sleep?level={SLEEP_LEVEL}")
    logger.info("Calling vLLM sleep endpoint once: %s", sleep_url)

    status, body = http_request(sleep_url, method="POST")
    if status != HTTPStatus.OK:
        raise RuntimeError(f"/sleep returned unexpected status {status}: {body!r}")

    STATE.set_sleep_called(True)
    logger.info("vLLM sleep succeeded.")


def orchestrate() -> None:
    try:
        wait_until_vllm_ready()
        call_sleep_once()
        STATE.set_ready_for_compose(True)
        logger.info("Gate is now healthy for Docker Compose.")
    except Exception as e:
        logger.exception("Gate orchestration failed: %s", e)
        STATE.set_error(str(e))
        # 失败时保持 /health = 503，便于 healthcheck 继续失败
        STATE.set_ready_for_compose(False)


class HealthHandler(BaseHTTPRequestHandler):
    server_version = "vllm-init-sleep-check/1.0"

    def _write_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        snap = STATE.snapshot()

        if self.path == "/health":
            if snap["ready_for_compose"]:
                self._write_json(HTTPStatus.OK, {"status": "ok", **snap})
            else:
                self._write_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "starting", **snap})
            return

        if self.path == "/status":
            self._write_json(HTTPStatus.OK, snap)
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found", "path": self.path})

    def log_message(self, fmt: str, *args) -> None:
        logger.info('%s - "%s"', self.address_string(), fmt % args)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def install_signal_handlers(server: ThreadingHTTPServer) -> None:
    def _handle_signal(signum, _frame) -> None:
        logger.info("Received signal %s, shutting down.", signum)
        STOP_EVENT.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


def main() -> int:
    worker = threading.Thread(target=orchestrate, daemon=True)
    worker.start()

    with ThreadingHTTPServer((GATE_HOST, GATE_PORT), HealthHandler) as server:
        install_signal_handlers(server)
        logger.info("Gate health server listening on %s:%s", GATE_HOST, GATE_PORT)
        try:
            server.serve_forever()
        finally:
            STOP_EVENT.set()

    return 0


if __name__ == "__main__":
    sys.exit(main())
