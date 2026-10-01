"""Starts the demo app in a uvicorn subprocess on a free port.

Each pytest-xdist worker starts its own instance, so workers never share state.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class AppServer:
    def __init__(self, app_dir: Path, log_file: Path, env: dict[str, str], startup_timeout: float = 20.0):
        self.app_dir = app_dir
        self.log_file = log_file
        self.env = env
        self.startup_timeout = startup_timeout
        self.instance_id = uuid.uuid4().hex
        self.url = ""
        self._process: subprocess.Popen | None = None

    def start(self, attempts: int = 3) -> AppServer:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(attempts):
            port = _free_port()
            url = f"http://127.0.0.1:{port}"
            command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
            log = self.log_file.open("w")
            process = subprocess.Popen(
                [*command, "--log-level", "warning"],
                cwd=self.app_dir,
                env={**os.environ, **self.env, "APP_INSTANCE_ID": self.instance_id, "PYTHONUNBUFFERED": "1"},
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            log.close()
            if self._wait_until_healthy(process, url):
                self._process, self.url = process, url
                return self
            # Most likely the port was grabbed between probing and binding: retry on a new one.
            self._kill(process)
        raise RuntimeError(f"App server did not become healthy. See {self.log_file}")

    def stop(self) -> None:
        if self._process is not None:
            self._kill(self._process)
            self._process = None

    def _wait_until_healthy(self, process: subprocess.Popen, url: str) -> bool:
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return False
            try:
                response = httpx.get(f"{url}/api/health", timeout=1)
                # The instance check guarantees we reached *our* process, not a neighbour's.
                if response.status_code == 200 and response.json().get("instance") == self.instance_id:
                    return True
            except httpx.TransportError:
                pass
            time.sleep(0.1)  # polling interval while the process boots (not a test wait)
        return False

    @staticmethod
    def _kill(process: subprocess.Popen) -> None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
