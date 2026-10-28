"""Image generation service - self-scheduling."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote
import os

import httpx
from PIL import Image

from . import config as cfg
from . import providers as prov
from . import storage

from astrbot.api import logger


def _image_dimensions(data: bytes) -> tuple[int, int] | None:
    try:
        with Image.open(io.BytesIO(data)) as im:
            return int(im.width), int(im.height)
    except Exception:
        return None


def _normalize_request(raw: dict[str, Any]) -> dict[str, Any]:
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("生图提示词不能为空")
    if len(prompt) > 100_000:
        raise ValueError("生图提示词过长，最多 100000 个字符")
    # images / mask
    images = [str(x).strip() for x in (raw.get("images") or []) if str(x).strip()]
    mask = str(raw.get("mask") or "").strip() or None
    op = str(raw.get("operation") or "generate").strip().lower()
    if images:
        op = "edit"
    elif op == "edit" and not images:
        raise ValueError("图像编辑至少需要一张输入图片（images）")
    if mask and op != "edit":
        raise ValueError("mask 只能在图像编辑时使用，请同时提供 images")
    n = int(raw.get("n") or 1)
    n = max(1, min(4, n))
    if op == "edit":
        n = 1
    # resolution 语义分流：generate 为 AxB，edit 为最短边单值
    if op == "edit":
        resolution = (str(raw.get("resolution") or raw.get("size") or "").strip() or None)
        size = None
        # 兼容误传 AxB 的情况：若 resolution 含 x/× 则保留，后续回退时会取最短边
    else:
        size = (str(raw.get("size") or raw.get("resolution") or "").strip() or None)
        resolution = None
    return {
        "prompt": prompt,
        "operation": op,
        "size": size,
        "resolution": resolution,
        "aspect_ratio": (str(raw.get("aspect_ratio") or "").strip() or None),
        "quality": (str(raw.get("quality") or "").strip() or None),
        "negative_prompt": (str(raw.get("negative_prompt") or "").strip() or None),
        "n": n,
        "seed": raw.get("seed"),
        "images": images,
        "mask": mask,
        "model_id": (str(raw.get("model_id") or "").strip() or None),
    }


def _resolve_edit_defaults(req: dict[str, Any], edit_inputs: dict[str, Any]) -> None:
    if req.get("operation") != "edit":
        return
    if not edit_inputs.get("images"):
        return
    dims = _image_dimensions(edit_inputs["images"][0]["bytes"])
    if not dims:
        return
    w, h = dims
    orig_short = min(w, h)
    orig_aspect = prov.aspect_from_dimensions(w, h)
    # resolution：最短边，不填按原图
    if not req.get("resolution"):
        req["resolution"] = str(orig_short)
    else:
        r = str(req["resolution"]).strip()
        low = r.lower()
        # 若误传 AxB，取最短边，避免 AxB 冲突
        if "x" in low or "×" in r:
            parsed = prov.parse_pixel_size(r)
            if parsed:
                req["resolution"] = str(min(parsed))
    # aspect_ratio：比例，不填按原图
    if not req.get("aspect_ratio"):
        req["aspect_ratio"] = orig_aspect


async def _load_image_bytes(ref: str) -> tuple[bytes, str]:
    ref = ref.strip()
    if not ref:
        raise ValueError("图片引用为空")
    if ref.startswith("data:"):
        # data:image/png;base64,xxx
        b = storage.decode_b64(ref)
        # guess mime from prefix
        mime = "image/png"
        if ref.startswith("data:"):
            try:
                mime = ref.split(";")[0].split(":")[1]
            except Exception:
                pass
        return b, mime
    # try local file path
    # Support file://
    if ref.startswith("file://"):
        parsed = urlparse(ref)
        p = unquote(parsed.path or "")
        if os.name == "nt" and len(p) > 2 and p[0] == "/" and p[2] == ":":
            p = p[1:]
        data = Path(p).read_bytes()
        mime = _guess_mime(data)
        return data, mime
    # http
    if ref.startswith("http://") or ref.startswith("https://"):
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(ref)
            if r.status_code != 200:
                raise ValueError(f"下载图片失败 HTTP {r.status_code}: {ref}")
            return r.content, r.headers.get("content-type", "image/png").split(";")[
                0
            ].strip()
    # plain local path
    p = Path(ref)
    if p.exists():
        data = p.read_bytes()
        return data, _guess_mime(data)
    raise ValueError(f"无法解析图片引用：{ref[:80]}")


def _guess_mime(data: bytes) -> str:
    try:
        fmt = Image.open(io.BytesIO(data)).format or "PNG"
        mapping = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "GIF": "image/gif",
            "WEBP": "image/webp",
            "BMP": "image/bmp",
        }
        return mapping.get(fmt.upper(), "image/png")
    except Exception:
        return "image/png"


def _image_to_data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


async def _load_edit_inputs(req: dict[str, Any]) -> dict[str, Any]:
    if req["operation"] != "edit":
        return {"images": [], "mask": None}
    if not req["images"]:
        raise ValueError("图像编辑至少需要一张输入图片")
    if len(req["images"]) > 16:
        raise ValueError(
            f"图像编辑最多支持 16 张输入图片，当前 {len(req['images'])} 张"
        )
    images = []
    for idx, ref in enumerate(req["images"]):
        b, mime = await _load_image_bytes(ref)
        # validate format
        storage.format_info(b)
        images.append({"bytes": b, "mime": mime, "ref": ref})
    mask = None
    if req["mask"]:
        b, mime = await _load_image_bytes(req["mask"])
        storage.format_info(b)
        mask = {"bytes": b, "mime": mime}
    return {"images": images, "mask": mask}


def _select_api_key(provider: dict[str, Any]) -> str:
    keys = [str(k).strip() for k in (provider.get("api_keys") or []) if str(k).strip()]
    if not keys:
        return ""
    # simple round-robin by cursor file? use first for now
    return keys[0]


def _parse_openai_response(value: dict[str, Any]) -> list[dict[str, Any]]:
    data = value.get("data")
    if not isinstance(data, list):
        raise ValueError("供应商响应缺少 data 图片数组")
    out: list[dict[str, Any]] = []
    errs: list[str] = []
    for item in data:
        if isinstance(item, dict) and item.get("error"):
            errs.append(
                str(
                    item["error"].get("message")
                    or item["error"].get("code")
                    or "图片生成失败"
                )
            )
            continue
        revised = None
        if isinstance(item, dict):
            revised = item.get("revised_prompt") or item.get("revisedPrompt")
        b64 = None
        url = None
        if isinstance(item, dict):
            b64 = item.get("b64_json") or item.get("b64Json")
            url = item.get("url")
        if b64:
            raw = storage.decode_b64(str(b64))
            out.append({"bytes": raw, "remote_url": None, "revised_prompt": revised})
        elif url and str(url).strip():
            out.append({"remote_url": str(url).strip(), "revised_prompt": revised})
    if not out:
        if errs:
            raise ValueError(f"供应商未返回可用图片：{'；'.join(errs)}")
        raise ValueError("供应商响应中没有可用图片")
    return out


def _parse_gemini_response(
    value: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    images: list[dict[str, Any]] = []
    texts: list[str] = []
    # steps style
    steps = value.get("steps")
    if isinstance(steps, list):
        for step in steps:
            contents = step.get("content") if isinstance(step, dict) else None
            if not isinstance(contents, list):
                continue
            for c in contents:
                if not isinstance(c, dict):
                    continue
                t = c.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
                if c.get("type") != "image":
                    continue
                enc = c.get("data")
                if not enc:
                    continue
                raw = storage.decode_b64(str(enc))
                images.append(
                    {"bytes": raw, "remote_url": None, "revised_prompt": None}
                )
        if images:
            return images, ("\n".join(texts) if texts else None)
    # candidates style
    cands = value.get("candidates")
    if isinstance(cands, list):
        for cand in cands:
            parts = None
            if isinstance(cand, dict):
                parts = (
                    cand.get("content", {}).get("parts")
                    if isinstance(cand.get("content"), dict)
                    else None
                )
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not isinstance(part, dict):
                    continue
                t = part.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
                inline = part.get("inlineData") or part.get("inline_data")
                if not isinstance(inline, dict):
                    continue
                enc = inline.get("data")
                if not enc:
                    continue
                raw = storage.decode_b64(str(enc))
                images.append(
                    {"bytes": raw, "remote_url": None, "revised_prompt": None}
                )
    if not images:
        txt = "\n".join(texts)
        raise ValueError(
            f"Gemini 未返回图片数据：{txt}" if txt else "Gemini 未返回图片数据"
        )
    return images, ("\n".join(texts) if texts else None)


async def _download_remote(provider: dict[str, Any], api_key: str, url: str) -> bytes:
    if url.startswith("data:image/"):
        return storage.decode_b64(url)
    async with httpx.AsyncClient(
        timeout=int(provider.get("timeout_seconds") or 600)
    ) as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise ValueError(f"下载生成图片失败：HTTP {r.status_code}")
        data = r.content
        if len(data) > storage.MAX_IMAGE_BYTES:
            raise ValueError("图片超过 64 MiB 大小限制")
        return data


async def _request_with_provider(
    provider: dict[str, Any],
    model: dict[str, Any],
    req: dict[str, Any],
    edit_inputs: dict[str, Any],
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    kind = provider["provider_type"]
    api_key = _select_api_key(provider)
    if kind != "comfyui" and not api_key:
        raise ValueError(f"生图供应商“{provider['name']}”尚未配置 API Key")

    # inject client for testability
    client = http_client or httpx.AsyncClient(
        timeout=int(provider.get("timeout_seconds") or 600)
    )
    close_client = http_client is None

    try:
        if kind == "openai":
            if req["operation"] == "edit":
                # multipart /images/edits
                fields = prov.openai_edit_scalar_fields(req, model)
                # limits
                if len(edit_inputs["images"]) > 16:
                    raise ValueError(
                        f"{provider['name']} 图像编辑最多支持 16 张输入图片，当前 {len(edit_inputs['images'])} 张"
                    )
                if (
                    edit_inputs["mask"] and kind == "openai" and False
                ):  # openai supports mask
                    pass
                endpoint = prov.append_endpoint(provider["base_url"], "/images/edits")
                # build multipart via httpx
                files = []
                data = {k: v for k, v in fields}
                for idx, im in enumerate(edit_inputs["images"]):
                    ext = {
                        "image/png": "png",
                        "image/jpeg": "jpg",
                        "image/gif": "gif",
                        "image/webp": "webp",
                        "image/bmp": "bmp",
                    }.get(im["mime"], "png")
                    files.append(
                        ("image[]", (f"image-{idx}.{ext}", im["bytes"], im["mime"]))
                    )
                if edit_inputs["mask"]:
                    m = edit_inputs["mask"]
                    ext = {"image/png": "png", "image/jpeg": "jpg"}.get(
                        m["mime"], "png"
                    )
                    files.append(("mask", (f"mask.{ext}", m["bytes"], m["mime"])))
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(
                    endpoint, data=data, files=files, headers=headers
                )
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                value = resp.json()
                pending = _parse_openai_response(value)
                return pending, None
            else:
                endpoint = prov.append_endpoint(
                    provider["base_url"], "/images/generations"
                )
                payload = prov.openai_generation_payload(req, model)
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                value = resp.json()
                pending = _parse_openai_response(value)
                return pending, None

        elif kind == "xai":
            if req["operation"] == "edit":
                if len(edit_inputs["images"]) > 3:
                    raise ValueError(
                        f"{provider['name']} 图像编辑最多支持 3 张输入图片，当前 {len(edit_inputs['images'])} 张"
                    )
                if edit_inputs["mask"]:
                    raise ValueError(
                        f"{provider['name']} 图像编辑暂不支持 mask，请改用文字描述需要修改的区域"
                    )
                urls = [
                    _image_to_data_url(im["bytes"], im["mime"])
                    for im in edit_inputs["images"]
                ]
                payload = prov.xai_edit_payload(req, model, urls)
                endpoint = prov.append_endpoint(provider["base_url"], "/images/edits")
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending = _parse_openai_response(resp.json())
                return pending, None
            else:
                endpoint = prov.append_endpoint(
                    provider["base_url"], "/images/generations"
                )
                payload = prov.xai_generation_payload(req, model)
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending = _parse_openai_response(resp.json())
                return pending, None

        elif kind == "seedream":
            if req["operation"] == "edit":
                if len(edit_inputs["images"]) > 10:
                    raise ValueError(
                        f"{provider['name']} 图像编辑最多支持 10 张输入图片，当前 {len(edit_inputs['images'])} 张"
                    )
                urls = [
                    _image_to_data_url(im["bytes"], im["mime"])
                    for im in edit_inputs["images"]
                ]
                payload = prov.seedream_edit_payload(req, provider, model, urls)
                endpoint = prov.append_endpoint(
                    provider["base_url"], "/images/generations"
                )
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending = _parse_openai_response(resp.json())
                return pending, None
            else:
                endpoint = prov.append_endpoint(
                    provider["base_url"], "/images/generations"
                )
                payload = prov.seedream_generation_payload(req, provider, model)
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending = _parse_openai_response(resp.json())
                return pending, None

        elif kind == "gemini":
            if req["operation"] == "edit":
                if len(edit_inputs["images"]) > 14:
                    raise ValueError(
                        f"{provider['name']} 图像编辑最多支持 14 张输入图片，当前 {len(edit_inputs['images'])} 张"
                    )
                payload = prov.gemini_edit_payload(req, model, edit_inputs["images"])
                endpoint = prov.append_endpoint(provider["base_url"], "/interactions")
                headers = {"x-goog-api-key": api_key, "Api-Revision": "2026-05-20"}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending, text = _parse_gemini_response(resp.json())
                return pending, text
            else:
                payload = prov.gemini_generation_payload(req, model)
                endpoint = prov.append_endpoint(provider["base_url"], "/interactions")
                headers = {"x-goog-api-key": api_key, "Api-Revision": "2026-05-20"}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending, text = _parse_gemini_response(resp.json())
                return pending, text

        elif kind == "sensenova":
            # compatible with openai
            if req["operation"] == "edit":
                endpoint = prov.append_endpoint(provider["base_url"], "/images/edits")
                fields = prov.openai_edit_scalar_fields(req, model)
                data = {k: v for k, v in fields}
                files = []
                for idx, im in enumerate(edit_inputs["images"]):
                    ext = {"image/png": "png", "image/jpeg": "jpg"}.get(
                        im["mime"], "png"
                    )
                    files.append(
                        ("image[]", (f"image-{idx}.{ext}", im["bytes"], im["mime"]))
                    )
                if edit_inputs["mask"]:
                    m = edit_inputs["mask"]
                    ext = {"image/png": "png"}.get(m["mime"], "png")
                    files.append(("mask", (f"mask.{ext}", m["bytes"], m["mime"])))
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(
                    endpoint, data=data, files=files, headers=headers
                )
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending = _parse_openai_response(resp.json())
                return pending, None
            else:
                endpoint = prov.append_endpoint(
                    provider["base_url"], "/images/generations"
                )
                payload = prov.openai_generation_payload(req, model)
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise ValueError(
                        f"{provider['name']} 请求失败：HTTP {resp.status_code}，{resp.text[:2000]}"
                    )
                pending = _parse_openai_response(resp.json())
                return pending, None

        elif kind == "comfyui":
            raise ValueError("ComfyUI 暂未实现，请使用 openai 兼容供应商")
        else:
            raise ValueError(f"未知供应商类型：{kind}")
    finally:
        if close_client:
            await client.aclose()


async def generate_images(
    data_dir: Path,
    raw_request: dict[str, Any],
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    req = _normalize_request(raw_request)
    providers, default_id = cfg.load_config(data_dir)
    provider, model, eid = cfg.resolve_model(providers, default_id, req.get("model_id"))
    logger.info(
        f"[天使的画笔] 开始 operation={req['operation']} provider={provider['name']} model={model['model']} prompt={req['prompt'][:80]}"
    )
    edit_inputs = await _load_edit_inputs(req)
    _resolve_edit_defaults(req, edit_inputs)
    pending_list, provider_text = await _request_with_provider(
        provider, model, req, edit_inputs, http_client=http_client
    )
    assets: list[dict[str, Any]] = []
    for pending in pending_list:
        if "bytes" in pending:
            raw_bytes = pending["bytes"]
        elif pending.get("remote_url"):
            raw_bytes = await _download_remote(
                provider, _select_api_key(provider), pending["remote_url"]
            )
        else:
            continue
        asset = storage.persist_image(
            data_dir,
            raw_bytes,
            remote_url=pending.get("remote_url"),
            revised_prompt=pending.get("revised_prompt"),
        )
        assets.append(asset)
        if len(assets) >= req["n"]:
            break
    if not assets:
        raise ValueError("供应商未返回可保存的图片")
    logger.info(f"[天使的画笔] 完成 provider={provider['name']} images={len(assets)}")
    return {
        "provider_id": provider["id"],
        "provider_name": provider["name"],
        "provider_type": provider["provider_type"],
        "model_id": eid,
        "model": model["model"] or model["id"],
        "images": assets,
        "provider_text": provider_text,
    }
