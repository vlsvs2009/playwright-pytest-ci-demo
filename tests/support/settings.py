"""Test-side configuration. The same values are passed to the app server we start."""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT_DIR / "reports"

# Fake demo credentials - not secrets. Override via env if needed.
DEMO_USERNAME = os.getenv("APP_DEMO_USERNAME", "demo@example.com")
DEMO_PASSWORD = os.getenv("APP_DEMO_PASSWORD", "demo-password")

SERVER_STARTUP_TIMEOUT_S = float(os.getenv("SERVER_STARTUP_TIMEOUT_S", "20"))
