"""Web API for Angel Brush - providers CRUD and test generation."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from astrbot.api import logger

try:
    from astrbot.api.web import error_response, json_response, request

    HAS_WEB = True
except ImportError:
    try:
        from quart import request  # type: ignore

        HAS_WEB = False
    except ImportError:
        HAS_WEB = False

        def _fallback(*_a, **_k):
            raise RuntimeError("Web API not available")

        json_response = error_response = _fallback  # type: ignore


def _ok(data: Any = None, message: str = "") -> Any:
    if HAS_WEB:
        return json_response({"status": "ok", "message": message, "data": data})
    from quart import jsonify as _jsonify  # type: ignore

    return _jsonify({"status": "ok", "message": message, "data": data})


def _err(message: str, status_code: int = 400) -> Any:
    if HAS_WEB:
        return error_response(message, status_code=status_code)
    from quart import jsonify as _jsonify  # type: ignore

    resp = _jsonify({"status": "error", "message": message, "data": {}})
    resp.status_code = status_code
    return resp


async def _get_json() -> dict[str, Any]:
    if HAS_WEB:
        data = await request.json(default=None)  # type: ignore
    else:
        try:
            data = await request.json  # type: ignore
        except Exception:
            data = None
    return data if isinstance(data, dict) else {}


class BrushAPI:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.gen_tool: Any = None
        self.edit_tool: Any = None

    async def list_config(self):
        from .core import config as cfg

        providers, default_id = cfg.load_config(self.data_dir)
        options = cfg.derive_model_options(providers)
        style = cfg.load_style_config(self.data_dir)
        return _ok(
            {
                "providers": providers,
                "default_model_id": default_id,
                "options": options,
                "templates": cfg.PROVIDER_TEMPLATES,
                "style_recommend": style.get("style_recommend", False),
                "custom_style": style.get("custom_style", ""),
            }
        )

    async def save_config(self):
        from .core import config as cfg

        payload = await _get_json()
        raw_providers = payload.get("providers")
        default_id = payload.get("default_model_id")
        if raw_providers is not None and not isinstance(raw_providers, list):
            return _err("providers 必须是数组")
        providers = cfg.normalize_providers(raw_providers or [])
        # 直接覆盖保存，不校验 default_model_id 是否在 options 中（草稿为准）
        if default_id:
            default_id = str(default_id).strip() or None
        else:
            default_id = None
        style_recommend = bool(payload.get("style_recommend"))
        custom_style = str(payload.get("custom_style") or "").strip()
        try:
            cfg.save_config(
                self.data_dir,
                providers,
                default_id,
                style_recommend=style_recommend,
                custom_style=custom_style,
            )
        except Exception as e:
            logger.error(f"AngelBrush save failed: {e}", exc_info=True)
            return _err(f"保存失败: {e}")
        # 保存后同步刷新已注册 LLM 工具的 description，画风即时进入下一轮 schema
        try:
            from . import tools as brush_tools

            brush_tools.update_tool_descriptions(self.gen_tool, self.edit_tool)
        except Exception as e:
            logger.warning(f"AngelBrush update tool descriptions failed: {e}")
        options = cfg.derive_model_options(providers)
        return _ok(
            {
                "providers": providers,
                "default_model_id": default_id,
                "options": options,
                "style_recommend": style_recommend,
                "custom_style": custom_style,
            },
            "已保存",
        )

    async def test_generate(self):
        payload = await _get_json()
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            return _err("prompt 不能为空")
        use_mock = bool(payload.get("mock"))
        # 完整透传两工具全部参数（前端两 tab 共用此接口）
        # 生成：size=AxB；编辑：resolution=最短边、aspect_ratio=比例，互不拼 AxB
        size_val = (
            str(payload.get("size") or payload.get("resolution") or "").strip()
            or None
        )
        resolution_val = (
            str(payload.get("resolution") or "").strip() or None
        )
        # 若前端编辑仍用 size 传最短边（如 1024），后端 service 会把 size 别名为 resolution
        aspect_ratio = str(payload.get("aspect_ratio") or "").strip() or None
        quality = str(payload.get("quality") or "").strip() or None
        negative_prompt = (
            str(payload.get("negative_prompt") or "").strip() or None
        )
        model_id = str(payload.get("model_id") or "").strip() or None
        operation = str(payload.get("operation") or "").strip() or None
        # n / seed 需容错
        n_val = payload.get("n")
        try:
            n_val = int(n_val) if n_val is not None and str(n_val).strip() != "" else 1
        except Exception:
            n_val = 1
        seed_val = payload.get("seed")
        try:
            seed_val = int(seed_val) if seed_val is not None and str(seed_val).strip() != "" else None
        except Exception:
            seed_val = str(seed_val).strip() if seed_val is not None else None
        images = payload.get("images")
        if not isinstance(images, list):
            images = []
        images = [str(x).strip() for x in images if str(x).strip()]
        mask = str(payload.get("mask") or "").strip() or None
        # operation 兜底：有图即编辑
        if images and not operation:
            operation = "edit"
        if not operation:
            operation = "generate"
        if use_mock:
            buf = io.BytesIO()
            # 编辑 mock 用不同底色以示区分
            color = (80, 140, 220) if operation == "edit" else (200, 80, 80)
            Image.new("RGB", (256, 256), color=color).save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return _ok(
                {"mock": True, "b64": b64, "mime": "image/png", "prompt": prompt},
                "mock 生成成功",
            )
        from .core import service

        req: dict[str, Any] = {
            "prompt": prompt,
            "size": size_val,
            "resolution": resolution_val or (size_val if operation == "edit" else None),
            "aspect_ratio": aspect_ratio,
            "quality": quality,
            "negative_prompt": negative_prompt,
            "n": n_val,
            "seed": seed_val,
            "model_id": model_id,
            "operation": operation,
            "images": images,
            "mask": mask,
        }
        try:
            result = await service.generate_images(self.data_dir, req)
        except Exception as e:
            logger.warning(f"AngelBrush test_generate failed: {e}")
            return _err(str(e))
        preview = []
        for img in result.get("images") or []:
            try:
                b = Path(img.get("absolute_path", "")).read_bytes()
                b64 = base64.b64encode(b).decode()
                preview.append(
                    {
                        "b64": b64,
                        "mime": img.get("mime", "image/png"),
                        "relative_path": img.get("relative_path"),
                        "markdown": img.get("markdown"),
                    }
                )
            except Exception:
                preview.append(
                    {
                        "relative_path": img.get("relative_path"),
                        "markdown": img.get("markdown"),
                    }
                )
        return _ok(
            {
                "images": preview,
                "provider": result.get("provider_name"),
                "model": result.get("model"),
            },
            "生成成功",
        )

    async def list_generated(self):
        gen_root = self.data_dir / "generated-images"
        items: list[dict[str, Any]] = []
        if gen_root.exists():
            for date_dir in sorted(gen_root.iterdir(), reverse=True)[:5]:
                if not date_dir.is_dir():
                    continue
                for f in sorted(date_dir.iterdir(), reverse=True)[:20]:
                    if f.is_file() and f.suffix.lower() in {
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                        ".gif",
                        ".bmp",
                    }:
                        rel = f.relative_to(self.data_dir).as_posix()
                        items.append(
                            {
                                "relative_path": rel,
                                "name": f.name,
                                "date": date_dir.name,
                            }
                        )
                        if len(items) >= 40:
                            break
        return _ok(items)

    async def image_b64(self):
        try:
            rel = (request.query.get("path") or "").strip()
        except Exception:
            try:
                rel = (request.args.get("path") or "").strip()  # type: ignore[attr-defined]
            except Exception:
                rel = ""
        if not rel:
            return _err("缺少 path 参数")
        target = (self.data_dir / rel).resolve()
        try:
            target.relative_to(self.data_dir.resolve())
        except ValueError:
            return _err("非法路径", 403)
        if not target.is_file():
            return _err("文件不存在", 404)
        data = target.read_bytes()
        suffix = target.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        mime = mime_map.get(suffix, "image/png")
        b64 = base64.b64encode(data).decode()
        return _ok({"b64": b64, "mime": mime, "path": rel})


def register_routes(
    context,
    data_dir: Path,
    gen_tool: Any = None,
    edit_tool: Any = None,
) -> None:
    api = BrushAPI(data_dir)
    if gen_tool is not None:
        api.gen_tool = gen_tool
    if edit_tool is not None:
        api.edit_tool = edit_tool
    routes = [
        ("/astrbot_plugin_angel_brush/config", api.list_config, ["GET"], "生图配置"),
        (
            "/astrbot_plugin_angel_brush/config/save",
            api.save_config,
            ["POST"],
            "保存生图配置",
        ),
        (
            "/astrbot_plugin_angel_brush/test_generate",
            api.test_generate,
            ["POST"],
            "测试生图",
        ),
        (
            "/astrbot_plugin_angel_brush/generated",
            api.list_generated,
            ["GET"],
            "已生成图片列表",
        ),
        (
            "/astrbot_plugin_angel_brush/image_b64",
            api.image_b64,
            ["GET"],
            "图片 base64",
        ),
    ]
    for path, handler, methods, desc in routes:
        try:
            context.register_web_api(path, handler, methods, desc)
        except Exception as e:
            logger.warning(f"AngelBrush register {path} failed: {e}")
    logger.info("AngelBrush: web api registered (5 routes)")
