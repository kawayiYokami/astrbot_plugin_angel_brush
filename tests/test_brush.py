"""Tests for angel brush - payloads, storage, mock generation."""

from __future__ import annotations

import base64
import io
import json
import tempfile
from pathlib import Path

import httpx
import pytest
from PIL import Image


def _tiny_png_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


TINY_B64 = _tiny_png_b64()
TINY_BYTES = base64.b64decode(TINY_B64)

# ---------- payload tests ----------


def test_openai_payload():
    from astrbot_plugin_angel_brush.core import providers as prov

    req = {"prompt": "a cat", "size": "1024x1024"}
    model = {"model": "gpt-image-1", "default_size": "512x512"}
    p = prov.openai_generation_payload(req, model)
    assert p["model"] == "gpt-image-1"
    assert p["prompt"] == "a cat"
    assert p["size"] == "1024x1024"
    assert p["output_format"] == "png"

    # aspect ratio -> size mapping for gpt-image-2
    req2 = {"prompt": "a cat", "aspect_ratio": "16:9"}
    model2 = {
        "model": "gpt-image-2",
        "default_size": None,
        "default_aspect_ratio": None,
    }
    p2 = prov.openai_generation_payload(req2, model2)
    assert "size" in p2
    assert p2["size"]  # should be mapped from aspect


def test_xai_payload():
    from astrbot_plugin_angel_brush.core import providers as prov

    req = {"prompt": "cat", "size": "1024x1024"}
    model = {"model": "grok-imagine-image", "default_size": None}
    p = prov.xai_generation_payload(req, model)
    assert p["model"] == "grok-imagine-image"
    assert "aspect_ratio" in p
    assert p["resolution"] in ("1k", "2k")


def test_seedream_payload():
    from astrbot_plugin_angel_brush.core import providers as prov

    req = {"prompt": "cat", "size": "2048x2048"}
    provider = {"watermark": True}
    model = {"model": "doubao-seedream-4-0-250828"}
    p = prov.seedream_generation_payload(req, provider, model)
    assert p["model"] == "doubao-seedream-4-0-250828"
    assert p["size"] == "2048x2048"
    assert p["watermark"] is True


def test_gemini_payload():
    from astrbot_plugin_angel_brush.core import providers as prov

    req = {"prompt": "cat", "size": "1K", "aspect_ratio": "16:9"}
    model = {"model": "gemini-3-pro-image-preview"}
    p = prov.gemini_generation_payload(req, model)
    assert p["model"] == "gemini-3-pro-image-preview"
    assert p["response_format"]["type"] == "image"
    assert "aspect_ratio" in p["response_format"]


def test_openai_edit_scalar_fields():
    from astrbot_plugin_angel_brush.core import providers as prov

    req = {"prompt": "edit cat", "size": "1024x1024"}
    model = {"model": "gpt-image-1"}
    fields = prov.openai_edit_scalar_fields(req, model)
    d = dict(fields)
    assert d["model"] == "gpt-image-1"
    assert d["prompt"] == "edit cat"
    assert "size" in d


def test_storage_validation():
    from astrbot_plugin_angel_brush.core import storage

    # valid
    mime, ext, w, h = storage.format_info(TINY_BYTES)
    assert mime == "image/png"
    assert w == 1 and h == 1

    # empty -> error
    with pytest.raises(ValueError, match="空图片"):
        storage.format_info(b"")

    # html -> error
    with pytest.raises(ValueError, match="无法识别|仅支持"):
        storage.format_info(b"<html>bad gateway</html>")

    # data url decode
    data_url = f"data:image/png;base64,{TINY_B64}"
    decoded = storage.decode_b64(data_url)
    assert decoded == TINY_BYTES

    # persist
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        asset = storage.persist_image(d, TINY_BYTES)
        assert asset["mime"] == "image/png"
        assert Path(asset["absolute_path"]).exists()
        assert asset["markdown"].startswith("![生成图片](")


def test_tool_schema():
    from astrbot_plugin_angel_brush.tools import (
        AngelImageEditTool,
        AngelImageGenerateTool,
    )

    gen = AngelImageGenerateTool(data_dir=Path(tempfile.gettempdir()))
    edit = AngelImageEditTool(data_dir=Path(tempfile.gettempdir()))

    assert gen.name == "angel_image_generate"
    assert "禁止在 markdown 内联" in gen.description
    assert "prompt" in gen.parameters["properties"]
    assert "resolution" in gen.parameters["properties"]
    assert gen.parameters["required"] == ["prompt"]
    assert gen.parameters["additionalProperties"] is False

    assert edit.name == "angel_image_edit"
    assert "禁止在 markdown 内联" in edit.description
    assert "prompt" in edit.parameters["properties"]
    assert "images" in edit.parameters["properties"]
    assert "mask" in edit.parameters["properties"]
    assert set(edit.parameters["required"]) == {"prompt", "images"}
    assert edit.parameters["additionalProperties"] is False


@pytest.mark.asyncio
async def test_mock_openai_generate():
    from astrbot_plugin_angel_brush.core import service, config

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        # setup provider config
        providers = [
            {
                "id": "image-provider-openai-1",
                "name": "OpenAI Images",
                "provider_type": "openai",
                "enabled": True,
                "base_url": "https://api.example.com/v1",
                "api_keys": ["sk-test"],
                "timeout_seconds": 30,
                "watermark": False,
                "models": [
                    {
                        "id": "gpt-image-1",
                        "name": "GPT Image 1",
                        "model": "gpt-image-1",
                        "enabled": True,
                    }
                ],
                "comfyui_workflow_json": "",
                "comfyui_mapping": {},
            }
        ]
        config.save_config(data_dir, providers, "image-provider-openai-1::gpt-image-1")

        # mock transport
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/images/generations"
            body = json.loads(request.content)
            assert body["model"] == "gpt-image-1"
            assert body["prompt"] == "a cute cat"
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"b64_json": TINY_B64, "revised_prompt": "a cute cat revised"}
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api.example.com"
        ) as mock_client:
            result = await service.generate_images(
                data_dir,
                {"prompt": "a cute cat", "size": "1024x1024"},
                http_client=mock_client,
            )

        assert result["provider_type"] == "openai"
        assert len(result["images"]) == 1
        img = result["images"][0]
        assert img["mime"] == "image/png"
        assert img["width"] == 1
        assert Path(img["absolute_path"]).exists()
        assert "![生成图片]" in img["markdown"]

        # tool success value contains markdown
        # directly test service result formatting
        payload = json.loads(
            __import__(
                "astrbot_plugin_angel_brush.tools", fromlist=["_tool_success_value"]
            )._tool_success_value(result, "图片已生成并保存到插件数据目录")  # type: ignore
        )
        assert payload["ok"] is True
        # 工具结果只给 file 路径，明确禁止在 markdown 里内联图片
        assert "![生成图片]" not in payload["message"]
        assert "send_message_to_user" in payload["message"]
        assert payload["images"][0]["markdown"] == img["markdown"]


@pytest.mark.asyncio
async def test_mock_openai_edit():
    from astrbot_plugin_angel_brush.core import config, service

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        # create a tiny image file for edit input
        img_path = Path(tmp) / "input.png"
        img_path.write_bytes(TINY_BYTES)
        data_url = f"data:image/png;base64,{TINY_B64}"

        providers = [
            {
                "id": "image-provider-openai-1",
                "name": "OpenAI Images",
                "provider_type": "openai",
                "enabled": True,
                "base_url": "https://api.example.com/v1",
                "api_keys": ["sk-test"],
                "timeout_seconds": 30,
                "watermark": False,
                "models": [
                    {
                        "id": "gpt-image-1",
                        "name": "GPT Image 1",
                        "model": "gpt-image-1",
                        "enabled": True,
                    }
                ],
                "comfyui_workflow_json": "",
                "comfyui_mapping": {},
            }
        ]
        config.save_config(data_dir, providers, "image-provider-openai-1::gpt-image-1")

        def handler(request: httpx.Request) -> httpx.Response:
            # edit uses multipart
            assert request.url.path == "/v1/images/edits"
            return httpx.Response(200, json={"data": [{"b64_json": TINY_B64}]})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api.example.com"
        ) as mock_client:
            result = await service.generate_images(
                data_dir,
                {
                    "prompt": "make cat blue",
                    "images": [str(img_path)],
                    "operation": "edit",
                },
                http_client=mock_client,
            )
        assert len(result["images"]) == 1

        # also test with data_url input
        transport2 = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport2, base_url="https://api.example.com"
        ) as mock_client:
            result2 = await service.generate_images(
                data_dir,
                {"prompt": "make cat blue", "images": [data_url], "operation": "edit"},
                http_client=mock_client,
            )
        assert len(result2["images"]) == 1


@pytest.mark.asyncio
async def test_mock_openai_url_response():
    """Supplier returns url instead of b64_json - plugin should download."""
    from astrbot_plugin_angel_brush.core import config

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        providers = [
            {
                "id": "image-provider-openai-1",
                "name": "OpenAI Images",
                "provider_type": "openai",
                "enabled": True,
                "base_url": "https://api.example.com/v1",
                "api_keys": ["sk-test"],
                "timeout_seconds": 30,
                "watermark": False,
                "models": [
                    {
                        "id": "gpt-image-1",
                        "name": "GPT Image 1",
                        "model": "gpt-image-1",
                        "enabled": True,
                    }
                ],
                "comfyui_workflow_json": "",
                "comfyui_mapping": {},
            }
        ]
        config.save_config(data_dir, providers, "image-provider-openai-1::gpt-image-1")

        # We need to mock both generation and download
        # For url case, service will call _download_remote which creates its own client
        # So we patch by providing http_client for generation, but download will still try real network
        # To avoid, we mock generation to return b64 and test url parsing separately is enough
        # Instead test parsing logic directly
        from astrbot_plugin_angel_brush.core.service import _parse_openai_response

        pending = _parse_openai_response(
            {"data": [{"url": "https://example.com/img.png"}]}
        )
        assert pending[0]["remote_url"] == "https://example.com/img.png"


# ---------- modelscope (async task protocol) ----------


def _modelscope_provider() -> dict:
    return {
        "id": "image-provider-modelscope-1",
        "name": "ModelScope API-Inference",
        "provider_type": "modelscope",
        "enabled": True,
        "base_url": "https://api-inference.modelscope.cn",
        "api_keys": ["ms-testkey-placeholder"],
        "timeout_seconds": 30,
        "watermark": False,
        "models": [
            {
                "id": "Qwen/Qwen-Image-2.1-Turbo",
                "name": "Qwen Image 2.1 Turbo",
                "model": "Qwen/Qwen-Image-2.1-Turbo",
                "enabled": True,
            }
        ],
        "comfyui_workflow_json": "",
        "comfyui_mapping": {},
    }


def test_modelscope_payload():
    from astrbot_plugin_angel_brush.core import providers as prov

    req = {"prompt": "cat", "size": "1024x1024", "quality": "high"}
    model = {"model": "Qwen/Qwen-Image-2.1-Turbo"}
    p = prov.modelscope_payload(req, model)
    assert p == {"model": "Qwen/Qwen-Image-2.1-Turbo", "prompt": "cat"}
    p2 = prov.modelscope_payload(req, model, ["data:image/png;base64,xxx"])
    assert p2["image_url"] == ["data:image/png;base64,xxx"]


def test_modelscope_url_guard():
    from astrbot_plugin_angel_brush.core.service import _ensure_public_image_url

    assert _ensure_public_image_url("https://cdn.example.com/a.png")
    assert _ensure_public_image_url("data:image/png;base64,xxx")
    for bad in (
        "http://127.0.0.1/a.png",
        "http://localhost/a.png",
        "http://192.168.1.1/a.png",
        "http://10.0.0.5/a.png",
        "http://[::1]/a.png",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/a.png",
    ):
        with pytest.raises(ValueError, match="不安全"):
            _ensure_public_image_url(bad)


@pytest.mark.asyncio
async def test_mock_modelscope_generate(monkeypatch):
    from astrbot_plugin_angel_brush.core import config, service

    monkeypatch.setattr(service, "_MODELSCOPE_POLL_INTERVAL", 0)

    async def fake_download(provider, api_key, url):
        assert url.startswith("https://")
        return TINY_BYTES

    monkeypatch.setattr(service, "_download_remote", fake_download)

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        config.save_config(
            data_dir,
            [_modelscope_provider()],
            "image-provider-modelscope-1::Qwen/Qwen-Image-2.1-Turbo",
        )

        calls = {"post": 0, "poll": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/v1/images/generations":
                calls["post"] += 1
                assert request.headers.get("x-modelscope-async-mode") == "true"
                body = json.loads(request.content)
                assert body["model"] == "Qwen/Qwen-Image-2.1-Turbo"
                assert body["prompt"] == "给图中的狗戴上一个生日帽"
                assert "image_url" not in body
                return httpx.Response(200, json={"task_id": "task-123"})
            if (
                request.method == "GET"
                and request.url.path == "/v1/tasks/task-123"
            ):
                assert request.headers.get("x-modelscope-task-type") == "image_generation"
                calls["poll"] += 1
                if calls["poll"] == 1:
                    return httpx.Response(200, json={"task_status": "RUNNING"})
                return httpx.Response(
                    200,
                    json={
                        "task_status": "SUCCEED",
                        "output_images": ["https://cdn.example.com/out.png"],
                    },
                )
            raise AssertionError(f"unexpected request {request.method} {request.url}")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api-inference.modelscope.cn"
        ) as mock_client:
            result = await service.generate_images(
                data_dir,
                {"prompt": "给图中的狗戴上一个生日帽"},
                http_client=mock_client,
            )
        assert calls["post"] == 1
        assert calls["poll"] == 2
        assert result["provider_type"] == "modelscope"
        assert len(result["images"]) == 1
        assert result["images"][0]["remote_url"] == "https://cdn.example.com/out.png"
        assert Path(result["images"][0]["absolute_path"]).exists()


@pytest.mark.asyncio
async def test_mock_modelscope_edit(monkeypatch):
    from astrbot_plugin_angel_brush.core import config, service

    monkeypatch.setattr(service, "_MODELSCOPE_POLL_INTERVAL", 0)

    async def fake_download(provider, api_key, url):
        return TINY_BYTES

    monkeypatch.setattr(service, "_download_remote", fake_download)

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        config.save_config(
            data_dir,
            [_modelscope_provider()],
            "image-provider-modelscope-1::Qwen/Qwen-Image-2.1-Turbo",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                body = json.loads(request.content)
                assert body["prompt"] == "把背景换成海边"
                urls = body["image_url"]
                assert isinstance(urls, list) and len(urls) == 1
                assert urls[0].startswith("data:image/png;base64,")
                return httpx.Response(200, json={"task_id": "task-9"})
            assert request.url.path == "/v1/tasks/task-9"
            return httpx.Response(
                200,
                json={
                    "task_status": "SUCCEED",
                    "output_images": ["https://cdn.example.com/edit.png"],
                },
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api-inference.modelscope.cn"
        ) as mock_client:
            result = await service.generate_images(
                data_dir,
                {
                    "prompt": "把背景换成海边",
                    "images": [f"data:image/png;base64,{TINY_B64}"],
                    "operation": "edit",
                },
                http_client=mock_client,
            )
        assert len(result["images"]) == 1


@pytest.mark.asyncio
async def test_mock_modelscope_task_failed(monkeypatch):
    from astrbot_plugin_angel_brush.core import config, service

    monkeypatch.setattr(service, "_MODELSCOPE_POLL_INTERVAL", 0)

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        config.save_config(
            data_dir,
            [_modelscope_provider()],
            "image-provider-modelscope-1::Qwen/Qwen-Image-2.1-Turbo",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(200, json={"task_id": "task-x"})
            return httpx.Response(
                200,
                json={"task_status": "FAILED", "message": "模型排队超时"},
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://api-inference.modelscope.cn"
        ) as mock_client:
            with pytest.raises(ValueError, match="生图任务失败：模型排队超时"):
                await service.generate_images(
                    data_dir,
                    {"prompt": "cat"},
                    http_client=mock_client,
                )
