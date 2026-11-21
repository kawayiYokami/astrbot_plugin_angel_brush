"""Install the AstrBot stand-in once before any test module imports the plugin."""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _astrbot_stub():
    os.environ.setdefault(
        "ASTRBOT_TEST_DATA_PATH", tempfile.mkdtemp(prefix="astrbot-test-data-")
    )
    from astrbot_plugin_angel_brush.tests._bootstrap import install_fake_astrbot

    install_fake_astrbot()
    yield
