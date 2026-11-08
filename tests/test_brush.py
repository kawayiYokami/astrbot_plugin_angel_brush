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

def test_openai_payload_gif_animated():
    """gpt-image 2.6 动图：output_format=gif + 帧参数，越界钳制/非法回落。"""
    from astrbot_plugin_angel_brush.core import providers as prov

    model = {"model": "gpt-image-2.6", "default_size": None}

    # 默认 png，且不带动图参数
    p = prov.openai_generation_payload({"prompt": "a cat"}, model)
    assert p["output_format"] == "png"
    assert "frame_count" not in p
    assert "frame_duration_ms" not in p

    # gif 动图显式参数
    p2 = prov.openai_generation_payload(
        {
            "prompt": "a bouncing ball",
            "output_format": "gif",
            "frame_count": 12,
            "frame_duration_ms": 250,
        },
        model,
    )
    assert p2["output_format"] == "gif"
    assert p2["frame_count"] == 12
    assert p2["frame_duration_ms"] == 250

    # 越界钳制：frame_count 2-16，frame_duration_ms 20-2000
    p3 = prov.openai_generation_payload(
        {"prompt": "x", "output_format": "gif", "frame_count": 99, "frame_duration_ms": 1},
        model,
    )
    assert p3["frame_count"] == 16
    assert p3["frame_duration_ms"] == 20

    # 非法 output_format 回落 png，且不泄漏帧参数
    p4 = prov.openai_generation_payload({"prompt": "x", "output_format": "bogus"}, model)
    assert p4["output_format"] == "png"
    assert "frame_count" not in p4

    # 老模型 gpt-image-1 行为不变
    p5 = prov.openai_generation_payload(
        {"prompt": "x", "size": "1024x1024"},
        {"model": "gpt-image-1", "default_size": "512x512"},
    )
    assert p5["output_format"] == "png"
    assert p5["size"] == "1024x1024"



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
    assert "Markdown 图片行" in gen.description
    assert "prompt" in gen.parameters["properties"]
    assert "resolution" in gen.parameters["properties"]
    assert gen.parameters["required"] == ["prompt"]
    assert gen.parameters["additionalProperties"] is False

    assert edit.name == "angel_image_edit"
    assert "Markdown 图片行" in edit.description
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
        assert "![生成图片]" in payload["message"]


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


def test_model_supports_gif():
    """只有 gpt-image-2 系列支持 gif 动图。"""
    from astrbot_plugin_angel_brush.core import config as cfg

    assert cfg.model_supports_gif({"model": "gpt-image-2.6"}) is True
    assert cfg.model_supports_gif({"model": "gpt-image-2"}) is True
    assert cfg.model_supports_gif({"model": "gpt-image-1"}) is False
    assert cfg.model_supports_gif({"model": "doubao-seedream-4-0"}) is False
    assert cfg.model_supports_gif({"model": "gemini-3-pro-image-preview"}) is False
    assert cfg.model_supports_gif(None) is False
    assert cfg.model_supports_gif({}) is False
