"""Runtime settings, read from environment variables.

The demo credentials below are intentionally fake and exist only so the
test suite has something to log in with.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    demo_username: str
    demo_password: str
    enable_test_api: bool
    instance_id: str


def get_settings() -> Settings:
    return Settings(
        demo_username=os.getenv("APP_DEMO_USERNAME", "demo@example.com"),
        demo_password=os.getenv("APP_DEMO_PASSWORD", "demo-password"),
        # The reset endpoint is only mounted when explicitly enabled (tests do this).
        enable_test_api=os.getenv("APP_ENABLE_TEST_API", "0") == "1",
        # Lets a test runner confirm it is talking to the server it started.
        instance_id=os.getenv("APP_INSTANCE_ID", "local"),
    )
