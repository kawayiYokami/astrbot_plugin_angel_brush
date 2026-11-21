"""Tests for copying generated images into a framework-allowed directory.

The framework's ``send_message_to_user`` only accepts files under the session
workspace, the AstrBot temp dir, or the system temp dir. Plugin data is not on
that list, so the tool has to hand the model a path inside the workspace.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from astrbot_plugin_angel_brush.tests._bootstrap import (
    FakeToolContext,
    install_fake_astrbot,
)


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    root = tmp_path / "data"
    monkeypatch.setenv("ASTRBOT_TEST_DATA_PATH", str(root))
    install_fake_astrbot()
    return root


def _write_source(data_dir: Path, name: str = "a.png") -> Path:
    src = data_dir / "generated-images" / "20261121" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"png-bytes")
    return src


# ---------- output directory resolution ----------


@pytest.mark.asyncio
async def test_local_runtime_uses_session_workspace(data_root):
    from astrbot_plugin_angel_brush.tools import _send_output_dir

    ctx = FakeToolContext(umo="default:GroupMessage:10001", runtime="local")
    out = await _send_output_dir(ctx)

    expected = (
        data_root
        / "workspaces"
        / "default_GroupMessage_10001"
        / "angel_brush"
        / "output"
    )
    assert out == expected.resolve(strict=False)


@pytest.mark.asyncio
async def test_local_runtime_webchat_project_uses_project_workspace(
    data_root, tmp_path
):
    from astrbot_plugin_angel_brush.tools import _send_output_dir

    pinned = tmp_path / "data" / "workspaces" / "project_abc"
    ctx = FakeToolContext(runtime="local", workspace_root=str(pinned))
    out = await _send_output_dir(ctx)

    assert out == pinned / "angel_brush" / "output"


@pytest.mark.asyncio
async def test_sandbox_runtime_uses_legacy_workspace(data_root, tmp_path):
    from astrbot_plugin_angel_brush.tools import _send_output_dir

    # 沙箱模式下框架白名单回落到 legacy 的 workspaces/<umo>，
    # 项目工作区不参与，这里确认插件没有误用它。
    ctx = FakeToolContext(
        umo="default:GroupMessage:10001",
        runtime="sandbox",
        workspace_root=str(tmp_path / "project_workspace"),
    )
    out = await _send_output_dir(ctx)

    assert "project_workspace" not in str(out)
    assert out.parent.parent.name == "default_GroupMessage_10001"


@pytest.mark.asyncio
async def test_resolution_failure_returns_none(data_root):
    from astrbot_plugin_angel_brush.tools import _send_dir_or_none

    class _Broken:
        @property
        def context(self):
            raise RuntimeError("boom")

    assert await _send_dir_or_none(_Broken()) is None


# ---------- copying ----------


def test_copy_rewrites_absolute_path_and_keeps_original(data_root, tmp_path):
    from astrbot_plugin_angel_brush.tools import _tool_success_value

    data_dir = tmp_path / "plugin_data"
    src = _write_source(data_dir)
    send_dir = tmp_path / "out"

    result = {
        "images": [
            {
                "absolute_path": str(src),
                "relative_path": "generated-images/20261121/a.png",
            }
        ]
    }
    payload = json.loads(
        _tool_success_value(result, "图片已生成", data_dir=data_dir, send_dir=send_dir)
    )

    assert payload["ok"] is True
    copied = Path(payload["images"][0]["absolute_path"])
    assert copied.parent == send_dir
    assert copied.read_bytes() == b"png-bytes"
    assert src.exists(), "原图必须保留在插件数据目录"
    assert payload["images"][0]["relative_path"] == "generated-images/20261121/a.png"


def test_without_send_dir_keeps_original_path(data_root, tmp_path):
    from astrbot_plugin_angel_brush.tools import _tool_success_value

    data_dir = tmp_path / "plugin_data"
    src = _write_source(data_dir)

    payload = json.loads(
        _tool_success_value(
            {"images": [{"absolute_path": str(src)}]}, "图片已生成", data_dir=data_dir
        )
    )

    assert payload["ok"] is True
    assert payload["images"][0]["absolute_path"] == str(src)


def test_rejects_image_outside_generated_dir(data_root, tmp_path):
    from astrbot_plugin_angel_brush.tools import _tool_success_value

    data_dir = tmp_path / "plugin_data"
    data_dir.mkdir(parents=True)
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"secret")

    payload = json.loads(
        _tool_success_value(
            {"images": [{"absolute_path": str(outside)}]},
            "图片已生成",
            data_dir=data_dir,
            send_dir=tmp_path / "out",
        )
    )

    assert payload["ok"] is False
    assert payload["generated"] is True
    assert payload["images"][0]["absolute_path"] == str(outside)


def test_copy_failure_reports_generated_not_failed(data_root, tmp_path):
    from astrbot_plugin_angel_brush.tools import _tool_success_value

    data_dir = tmp_path / "plugin_data"
    src = _write_source(data_dir)

    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory")

    payload = json.loads(
        _tool_success_value(
            {"images": [{"absolute_path": str(src)}]},
            "图片已生成",
            data_dir=data_dir,
            send_dir=blocked,
        )
    )

    assert payload["ok"] is False
    assert payload["generated"] is True, "生成已成功，不能报成生成失败"
    assert "不要重新生图" in payload["message"]
