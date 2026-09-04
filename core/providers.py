"""Provider payload builders."""

from __future__ import annotations

import base64
from typing import Any

# ---------- helpers ----------


def _trim_opt(v: Any) -> str | None:
    t = str(v).strip() if v is not None else ""
    return t if t else None


def effective_size(req: dict[str, Any], model: dict[str, Any]) -> str | None:
    return _trim_opt(req.get("size")) or _trim_opt(model.get("default_size"))


def effective_aspect(req: dict[str, Any], model: dict[str, Any]) -> str | None:
    return _trim_opt(req.get("aspect_ratio")) or _trim_opt(
        model.get("default_aspect_ratio")
    )


def effective_quality(req: dict[str, Any], model: dict[str, Any]) -> str | None:
    return _trim_opt(req.get("quality")) or _trim_opt(model.get("default_quality"))


def effective_prompt(req: dict[str, Any]) -> str:
    p = str(req.get("prompt") or "").strip()
    neg = _trim_opt(req.get("negative_prompt"))
    if neg:
        return f"{p}\n\n请避免出现以下内容：{neg}"
    return p


def parse_pixel_size(value: str) -> tuple[int, int] | None:
    s = value.strip().lower().replace("×", "x")
    if "x" not in s:
        return None
    w, h = s.split("x", 1)
    try:
        wi, hi = int(w.strip()), int(h.strip())
    except ValueError:
        return None
    if wi == 0 or hi == 0:
        return None
    return wi, hi


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return max(1, a)


def aspect_from_dimensions(w: int, h: int) -> str:
    g = _gcd(w, h)
    return f"{w // g}:{h // g}"


def parse_aspect_ratio(value: str) -> tuple[int, int] | None:
    if ":" not in value:
        return None
    w, h = value.strip().split(":", 1)
    try:
        wi, hi = int(w.strip()), int(h.strip())
    except ValueError:
        return None
    if wi == 0 or hi == 0:
        return None
    return wi, hi


def openai_size_from_aspect(value: str, arbitrary: bool) -> str | None:
    parsed = parse_aspect_ratio(value)
    if not parsed:
        return None
    w, h = parsed
    ratio = w / h
    if arbitrary:
        if not (1 / 3 <= ratio <= 3):
            return None
        if 0.87 <= ratio <= 1.15:
            return "1024x1024"

        def _rnd(v: float) -> int:
            return max(1, round(v / 16)) * 16

        if ratio > 1:
            return f"1536x{max(512, min(1536, _rnd(1536 / ratio)))}"
        else:
            return f"{max(512, min(1536, _rnd(1536 * ratio)))}x1536"
    if ratio > 1.15:
        return "1536x1024"
    if ratio < 0.87:
        return "1024x1536"
    return "1024x1024"


def append_endpoint(base_url: str, suffix: str) -> str:
    base = base_url.strip().rstrip("/")
    suffix = suffix.strip()
    if not suffix.startswith("/"):
        suffix = "/" + suffix
    if base.lower().endswith(suffix.lower()):
        return base
    return base + suffix


# ---------- payload builders ----------


def openai_generation_payload(
    req: dict[str, Any], model: dict[str, Any]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model["model"],
        "prompt": effective_prompt(req),
        "n": 1,
    }
    is_gpt = str(model.get("model") or "").strip().lower().startswith("gpt-image")
    arbitrary = str(model.get("model") or "").strip().lower().startswith("gpt-image-2")
    if is_gpt:
        payload["output_format"] = "png"
    else:
        payload["response_format"] = "b64_json"

    size = (
        _trim_opt(req.get("size"))
        or (
            _trim_opt(req.get("aspect_ratio"))
            and openai_size_from_aspect(str(req.get("aspect_ratio")), arbitrary)
        )
        or _trim_opt(model.get("default_size"))
        or (
            _trim_opt(model.get("default_aspect_ratio"))
            and openai_size_from_aspect(
                str(model.get("default_aspect_ratio")), arbitrary
            )
        )
    )
    if size:
        payload["size"] = size
    q = effective_quality(req, model)
    if q:
        payload["quality"] = q
    return payload


def _xai_resolution(req: dict[str, Any], model: dict[str, Any]) -> str | None:
    for cand in [effective_size(req, model), effective_quality(req, model)]:
        if not cand:
            continue
        norm = cand.strip().lower()
        if norm in ("1k", "2k"):
            return norm
        parsed = parse_pixel_size(norm)
        if parsed:
            w, h = parsed
            return "2k" if max(w, h) > 1536 else "1k"
    return None


def xai_generation_payload(
    req: dict[str, Any], model: dict[str, Any]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model["model"],
        "prompt": effective_prompt(req),
        "n": 1,
        "response_format": "b64_json",
    }
    aspect = effective_aspect(req, model)
    if not aspect:
        sz = effective_size(req, model)
        if sz:
            parsed = parse_pixel_size(sz)
            if parsed:
                aspect = aspect_from_dimensions(*parsed)
    if aspect:
        payload["aspect_ratio"] = aspect
    res = _xai_resolution(req, model)
    if res:
        payload["resolution"] = res
    return payload


def _is_seedream_v5(model_name: str) -> bool:
    low = (model_name or "").lower()
    return "seedream" in low and ("5.0" in low or "5-0" in low)


def _seedream_min_pixels(model_name: str) -> int:
    """豆包 seedream 5.0 系列 image 生成最小像素要求（官方报错口径）。"""
    return 3686400  # 1920x1920


def enlarge_seedream_size(raw: str | None, model_name: str) -> str | None:
    """豆包专用尺寸放大函数：seedream 5.0 若像素不足 3686400，
    把短边钉到 1920、长边按原比例等比放大取整；合法原样返回。
    解析不出像素时落 1920x1920。仅对 seedream 5.0 生效。"""
    if not raw or not _is_seedream_v5(model_name):
        return _trim_opt(raw)
    s = raw.strip()
    low = s.lower()
    # 档位词 / 无法解析成像素：兜底 1:1 最小合法
    if low in ("1k", "2k", "4k") or "x" not in s:
        return "1920x1920"
    parsed = parse_pixel_size(s)
    if not parsed:
        return "1920x1920"
    w, h = parsed
    if w * h >= _seedream_min_pixels(model_name):
        return f"{w}x{h}"
    short, long_ = (w, h) if w <= h else (h, w)
    k = 1920 / short
    long_scaled = int(round(long_ * k))
    if w <= h:
        return f"1920x{long_scaled}"
    return f"{long_scaled}x1920"


def seedream_generation_payload(
    req: dict[str, Any], provider: dict[str, Any], model: dict[str, Any]
) -> dict[str, Any]:
    model_name = str(model.get("model") or "")
    raw = _trim_opt(req.get("size")) or _trim_opt(model.get("default_size"))
    if not raw:
        raw = "1920x1920" if _is_seedream_v5(model_name) else "2048x2048"
    size = enlarge_seedream_size(raw, model_name)
    payload: dict[str, Any] = {
        "model": model["model"],
        "prompt": effective_prompt(req),
        "response_format": "b64_json",
        "watermark": bool(provider.get("watermark")),
    }
    if _is_seedream_v5(model_name):
        payload["output_format"] = "png"
    if size:
        payload["size"] = size
    # quality mapping for seedream: standard/fast etc via model default
    q = effective_quality(req, model)
    if q:
        payload["quality"] = q
    return payload


def gemini_generation_payload(
    req: dict[str, Any], model: dict[str, Any]
) -> dict[str, Any]:
    rf: dict[str, Any] = {"type": "image", "mime_type": "image/png"}
    size = effective_size(req, model)
    aspect = effective_aspect(req, model)
    if not aspect and size:
        parsed = parse_pixel_size(size)
        if parsed:
            aspect = aspect_from_dimensions(*parsed)
    if aspect:
        rf["aspect_ratio"] = aspect
    if size:
        norm = size.strip().upper()
        if norm in ("512", "1K", "2K", "4K"):
            rf["image_size"] = norm
    return {
        "model": model["model"],
        "input": [{"type": "text", "text": effective_prompt(req)}],
        "response_format": rf,
    }


def comfyui_generation_payload(
    req: dict[str, Any], model: dict[str, Any]
) -> dict[str, Any]:
    # ComfyUI uses workflow JSON injection; for mock we return generic
    return {"prompt": effective_prompt(req), "model": model.get("model") or ""}


# ---------- edit helpers (resolution=最短边, aspect_ratio=比例, 不填按原图, 不拼 AxB) ----------


def _parse_short_resolution(value: Any) -> int | None:
    s = str(value).strip() if value is not None else ""
    if not s:
        return None
    low = s.lower().strip()
    bucket = {"512": 512, "1k": 1024, "2k": 2048, "4k": 4096}
    if low in bucket:
        return bucket[low]
    # 纯数字最短边
    try:
        iv = int(float(s))
        if iv > 0:
            return iv
    except Exception:
        pass
    parsed = parse_pixel_size(s)
    if parsed:
        return min(parsed)
    return None


def _compute_wh_from_short_and_aspect(short: int, aspect: str) -> tuple[int, int] | None:
    parsed = parse_aspect_ratio(aspect)
    if not parsed or short <= 0:
        return None
    w_r, h_r = parsed
    if w_r <= 0 or h_r <= 0:
        return None
    ratio = w_r / h_r
    if ratio >= 1:
        h = short
        w = int(round(short * ratio))
    else:
        w = short
        h = int(round(short / ratio))
    # 保持最短边精确，不强制对齐到 16，避免按原图时失真；长边已按比例计算为整数
    return w, h


def _edit_explicit_aspect(req: dict[str, Any]) -> str | None:
    t = _trim_opt(req.get("aspect_ratio"))
    if t:
        return t
    sz = _trim_opt(req.get("size"))
    if sz:
        parsed = parse_pixel_size(sz)
        if parsed:
            return aspect_from_dimensions(*parsed)
    return None


def openai_edit_scalar_fields(
    req: dict[str, Any], model: dict[str, Any]
) -> list[tuple[str, str]]:
    fields = [("model", model["model"]), ("prompt", effective_prompt(req)), ("n", "1")]
    mn = str(model.get("model") or "").lower()
    is_gpt = mn.startswith("gpt-image")
    if is_gpt:
        fields.append(("output_format", "png"))
    else:
        fields.append(("response_format", "b64_json"))
    # 编辑：resolution=最短边 + aspect_ratio=比例，二者独立不拼 AxB 冲突；由 service 已按原图回退
    # 兼容直调：同时接受 resolution 与旧 size(AxB) 别名
    res_raw = _trim_opt(req.get("resolution")) or _trim_opt(req.get("size"))
    short = _parse_short_resolution(res_raw)
    aspect = _trim_opt(req.get("aspect_ratio"))
    # 若 aspect 缺但 res_raw 本身是 AxB，推导比例（兼容旧用法的 size=1024x1024）
    if not aspect and res_raw:
        parsed_sz = parse_pixel_size(res_raw)
        if parsed_sz:
            aspect = aspect_from_dimensions(*parsed_sz)
    size: str | None = None
    if short is not None and aspect:
        wh = _compute_wh_from_short_and_aspect(short, aspect)
        if wh:
            size = f"{wh[0]}x{wh[1]}"
    elif short is not None:
        # 只有最短边：若模型有默认比例则结合，否则不发让 service 的 aspect 回退已生效
        size = None
        # 兜底：若模型有 default_aspect_ratio，可与 short 组合
        model_aspect = _trim_opt(model.get("default_aspect_ratio"))
        if model_aspect:
            wh = _compute_wh_from_short_and_aspect(short, model_aspect)
            if wh:
                size = f"{wh[0]}x{wh[1]}"
        else:
            # 纯 AxB 旧入参直接透传，避免测试与旧链路断裂
            if res_raw and parse_pixel_size(res_raw):
                size = res_raw
    elif aspect:
        # 只有比例：short 已由 service 按原图回退，此分支理论上不会命中，保留兜底
        model_size = _trim_opt(model.get("default_size"))
        fallback_short = _parse_short_resolution(model_size) if model_size else None
        if fallback_short is not None:
            wh = _compute_wh_from_short_and_aspect(fallback_short, aspect)
            if wh:
                size = f"{wh[0]}x{wh[1]}"
        else:
            # 直接走 aspect->size 的旧映射（避免不发导致 1:1），仅兜底
            arbitrary = mn.startswith("gpt-image-2")
            size = openai_size_from_aspect(aspect, arbitrary)
    if size:
        fields.append(("size", size))
    q = effective_quality(req, model)
    if q:
        fields.append(("quality", q))
    return fields


def xai_edit_payload(
    req: dict[str, Any], model: dict[str, Any], data_urls: list[str]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model["model"],
        "prompt": effective_prompt(req),
        "n": 1,
        "response_format": "b64_json",
    }
    if len(data_urls) == 1:
        payload["image"] = {"url": data_urls[0]}
    else:
        payload["images"] = [{"url": u} for u in data_urls]
    # 编辑：resolution=最短边映射为 1k/2k，aspect_ratio 独立透传，不填按原图已由 service 回退；兼容 size 别名
    aspect = _trim_opt(req.get("aspect_ratio")) or _edit_explicit_aspect(req)
    if aspect:
        # 去掉旧 auto 兜底的自动推断：若 service 已回退这里必有值；否则保留兼容
        if aspect != "auto" or "aspect_ratio" not in payload:
            payload["aspect_ratio"] = aspect
    # 兼容 size 别名
    res_raw = _trim_opt(req.get("resolution")) or _trim_opt(req.get("size"))
    short = _parse_short_resolution(res_raw)
    if short is not None:
        payload["resolution"] = "2k" if short > 1536 else "1k"
    # 兼容：若两者都缺（理论上 service 已回退），不发则供应商保持原图
    if "aspect_ratio" not in payload and len(data_urls) > 1:
        payload["aspect_ratio"] = _edit_explicit_aspect(req) or "auto"
    return payload


def seedream_edit_payload(
    req: dict[str, Any],
    provider: dict[str, Any],
    model: dict[str, Any],
    data_urls: list[str],
) -> dict[str, Any]:
    prompt = effective_prompt(req)
    model_name = str(model.get("model") or "")
    res_raw = _trim_opt(req.get("resolution")) or _trim_opt(req.get("size"))
    short = _parse_short_resolution(res_raw)
    aspect = _trim_opt(req.get("aspect_ratio"))
    # 若 aspect 缺但 res_raw 是 AxB，推导比例
    if not aspect and res_raw:
        parsed_sz = parse_pixel_size(res_raw)
        if parsed_sz:
            aspect = aspect_from_dimensions(*parsed_sz)
    size: str | None = None
    if short is not None and aspect:
        wh = _compute_wh_from_short_and_aspect(short, aspect)
        if wh:
            size = f"{wh[0]}x{wh[1]}"
    elif short is not None and not aspect:
        # 只有短边：若 res_raw 本身是 AxB 则直接用，避免丢失
        if res_raw and parse_pixel_size(res_raw):
            size = res_raw
    elif aspect and short is None:
        # 只有比例：保留旧行为把比例写入 prompt 提示词（seedream 兼容），同时尝试算 size
        prompt += f"\n\n画面宽高比：{aspect}"
    if size:
        size = enlarge_seedream_size(size, model_name)
    payload: dict[str, Any] = {
        "model": model["model"],
        "prompt": prompt,
        "response_format": "b64_json",
        "watermark": bool(provider.get("watermark")),
    }
    if _is_seedream_v5(model_name):
        payload["output_format"] = "png"
    payload["image"] = data_urls[0] if len(data_urls) == 1 else data_urls
    if size:
        payload["size"] = size
    return payload


def gemini_edit_payload(
    req: dict[str, Any], model: dict[str, Any], images: list[dict[str, Any]]
) -> dict[str, Any]:
    rf: dict[str, Any] = {"type": "image", "mime_type": "image/png"}
    aspect = _trim_opt(req.get("aspect_ratio"))
    if aspect:
        rf["aspect_ratio"] = aspect
    res_val = _trim_opt(req.get("resolution")) or _trim_opt(req.get("size"))
    if res_val:
        norm = res_val.strip().upper()
        if norm in ("512", "1K", "2K", "4K"):
            rf["image_size"] = norm
        else:
            short = _parse_short_resolution(res_val)
            if short is not None:
                if short <= 512:
                    rf["image_size"] = "512"
                elif short <= 1024:
                    rf["image_size"] = "1K"
                elif short <= 2048:
                    rf["image_size"] = "2K"
                else:
                    rf["image_size"] = "4K"
    items: list[dict[str, Any]] = [{"type": "text", "text": effective_prompt(req)}]
    for im in images:
        items.append(
            {
                "type": "image",
                "mime_type": im["mime"],
                "data": base64.b64encode(im["bytes"]).decode(),
            }
        )
    return {"model": model["model"], "input": items, "response_format": rf}
