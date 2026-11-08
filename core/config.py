"""Image generation config."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

PROVIDER_KINDS = {
    "comfyui",
    "openai",
    "xai",
    "seedream",
    "gemini",
    "sensenova",
}

# 模型前缀 -> 擅长画风描述（用户确认口径）
MODEL_STYLES: dict[str, str] = {
    "seedream": (
        "商业级写实与产品广告（光影/皮肤/金属/玻璃/水滴等物理材质还原、丁达尔光、环境反射，"
        "适合电商主图、产品广告、真实感人像写真）；杂志风信息图与结构化排版（图文混排、数据图表、"
        "科普图鉴、多语言文字渲染，适合公众号配图/课件/活动海报）；国风与传统艺术（古风、东方美学、"
        "汉服细节、古典建筑）；潮流动漫与手办风格（卡通、赛博朋克、手办模型质感、极简潮流插画）；"
        "影视与游戏概念原画（宏大世界观场景、角色立绘、分镜草图、多图多镜头人物一致性/锁脸强）"
    ),
    "gpt-image": (
        "版式化设计与信息卡片（手绘高亮信息卡片、产品视觉设定、多图层规范表等高信息密度排版）；"
        "经典动画与童话风格（吉卜力赛璐璐动画风、清新水彩、儿童绘本风）；现代创意与立体风格"
        "（3D Q版角色、Low Poly 低多边形、像素艺术、干净矢量插画）"
    ),
    "gemini": (
        "写实摄影与纪实风格（杂志封面、日常街景、高端商业人像，光影/PBR 材质/胶片颗粒感/构图把控到位）；"
        "3D 卡通与等距微缩模型 Isometric（色彩鲜艳的 3D 图标、建筑微缩景观，精准 45° 俯视等距视角）；"
        "信息图表与商业营销素材（清晰排版、图表、标语、现代极简设计，可在图中生成清晰易读的衬线/无衬线字体）"
    ),
    "sensenova": (
        "扁平、插画与手绘风（信息图 Infographics、条漫绘本；手绘水彩/水墨风带宣纸质感、复古中国风水墨；"
        "现代扁平插画小卡片/对话气泡/节点路径，色彩具设计感）；专业平面设计与商用海报风（复古高端海报："
        "摄影底图+低饱和暖色调+细长宋体排版；多层嵌套 UI/游戏 UI/电商素材/产品传单，结构严谨无乱码）；"
        "长卷与连环叙事风（24 节气国画长卷直出、多页绘本故事画风统一、人物不走调）；细腻真实的摄影与三次元写实"
        "（美学专家模块优化光影/材质/透视空间，画面干净少瑕疵）"
    ),
}

PROVIDER_TEMPLATES: dict[str, dict[str, Any]] = {
    "comfyui": {
        "name": "Local ComfyUI",
        "base_url": "http://127.0.0.1:8188",
        "model": {
            "name": "ComfyUI Workflow",
            "model": "",
            "default_size": "512x512",
            "default_aspect_ratio": "1:1",
        },
    },
    "openai": {
        "name": "OpenAI Images",
        "base_url": "https://api.openai.com/v1",
        "model": {
            "name": "GPT Image 1",
            "model": "gpt-image-1",
            "default_size": "1024x1024",
            "default_aspect_ratio": "1:1",
            "default_quality": "medium",
        },
    },
    "xai": {
        "name": "xAI Grok Imagine",
        "base_url": "https://api.x.ai/v1",
        "model": {
            "name": "Grok Imagine Image Quality",
            "model": "grok-imagine-image",
            "default_size": "1024x1024",
            "default_aspect_ratio": "1:1",
        },
    },
    "seedream": {
        "name": "Seedance / Seedream",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": {
            "name": "Seedream 4.0",
            "model": "doubao-seedream-4-0-250828",
            "default_size": "2048x2048",
            "default_aspect_ratio": "1:1",
            "default_quality": "standard",
        },
    },
    "gemini": {
        "name": "Gemini Nano Banana",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": {
            "name": "Nano Banana Pro",
            "model": "gemini-3-pro-image-preview",
            "default_size": "1K",
            "default_aspect_ratio": "1:1",
        },
    },
    "sensenova": {
        "name": "SenseNova",
        "base_url": "https://api.sensenova.cn/v1",
        "model": {
            "name": "SenseNova U1",
            "model": "sensenova-u1",
            "default_size": "1024x1024",
            "default_aspect_ratio": "1:1",
        },
    },
}


def _norm_text(v: Any) -> str | None:
    t = str(v).strip() if v is not None else ""
    return t if t else None


def _normalize_kind(v: Any) -> str:
    k = str(v or "").strip().lower()
    return k if k in PROVIDER_KINDS else "openai"


def _unique_strings(v: Any, lower: bool = False) -> list[str]:
    if not isinstance(v, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in v:
        t = str(item or "").strip()
        if not t:
            continue
        key = t.lower() if lower else t
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def endpoint_id(provider_id: str, model_id: str) -> str:
    return f"{provider_id.strip()}::{model_id.strip()}"


def parse_endpoint_id(value: str) -> tuple[str, str] | None:
    if "::" not in value:
        return None
    p, m = value.split("::", 1)
    p, m = p.strip(), m.strip()
    if not p or not m:
        return None
    return p, m


def create_provider(
    provider_type: str = "openai", seed: str | None = None
) -> dict[str, Any]:
    seed = seed or str(int(time.time() * 1000))
    kind = _normalize_kind(provider_type)
    tmpl = PROVIDER_TEMPLATES[kind]
    mid = tmpl["model"]["model"] or f"comfyui-workflow-{seed}"
    return {
        "id": f"image-provider-{kind}-{seed}",
        "name": tmpl["name"],
        "provider_type": kind,
        "enabled": True,
        "base_url": tmpl["base_url"],
        "api_keys": [],
        "timeout_seconds": 600,
        "watermark": False,
        "models": [
            {
                "id": mid,
                "name": tmpl["model"]["name"],
                "model": tmpl["model"]["model"],
                "enabled": True,
                "default_size": tmpl["model"].get("default_size"),
                "default_aspect_ratio": tmpl["model"].get("default_aspect_ratio"),
                "default_quality": tmpl["model"].get("default_quality"),
            }
        ],
        "comfyui_workflow_json": "",
        "comfyui_mapping": {},
    }


def _normalize_model(value: Any, kind: str, fallback_id: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        value = {}
    mid = str(value.get("id") or fallback_id).strip()
    if not mid or "::" in mid:
        return None
    model_val = str(value.get("model") or "").strip()
    fallback_name = model_val or mid
    return {
        "id": mid,
        "name": str(value.get("name") or "").strip() or fallback_name,
        "model": model_val or ("" if kind == "comfyui" else mid),
        "enabled": value.get("enabled", True) is not False,
    }


def normalize_provider(value: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        value = {}
    kind = _normalize_kind(value.get("provider_type"))
    tmpl = PROVIDER_TEMPLATES[kind]
    pid = str(value.get("id") or f"image-provider-{kind}-{index + 1}").strip()
    if not pid or "::" in pid:
        return None
    seen: set[str] = set()
    models = []
    for idx, m in enumerate(value.get("models") or []):
        nm = _normalize_model(m, kind, f"image-model-{idx + 1}")
        if not nm:
            continue
        key = nm["id"].lower()
        if key in seen:
            continue
        seen.add(key)
        models.append(nm)
    timeout = int(value.get("timeout_seconds") or 600)
    timeout = max(10, min(600, timeout)) if timeout > 0 else 600
    return {
        "id": pid,
        "name": str(value.get("name") or "").strip() or tmpl["name"],
        "provider_type": kind,
        "enabled": value.get("enabled", True) is not False,
        "base_url": str(value.get("base_url") or "").strip().rstrip("/")
        or tmpl["base_url"],
        "api_keys": _unique_strings(value.get("api_keys")),
        "timeout_seconds": timeout,
        "watermark": bool(value.get("watermark")),
        "models": models,
        "comfyui_workflow_json": str(value.get("comfyui_workflow_json") or "").strip(),
        "comfyui_mapping": value.get("comfyui_mapping") or {},
    }


def normalize_providers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for idx, p in enumerate(value):
        np = normalize_provider(p, idx)
        if not np:
            continue
        key = np["id"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(np)
    return out


def derive_model_options(providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    opts: list[dict[str, Any]] = []
    for p in providers:
        if not p.get("enabled"):
            continue
        for m in p.get("models") or []:
            if not m.get("enabled"):
                continue
            eid = endpoint_id(p["id"], m["id"])
            opts.append(
                {
                    "id": eid,
                    "provider_id": p["id"],
                    "provider_name": p["name"],
                    "provider_type": p["provider_type"],
                    "model_id": m["id"],
                    "model": m["model"],
                    "name": m["name"],
                    "label": f"{p['name']} / {m['name']}",
                }
            )
    return opts


def load_config(data_dir: Path) -> tuple[list[dict[str, Any]], str | None]:
    """Load providers.json from plugin data dir. Returns (providers, default_model_id)."""
    cfg_path = data_dir / "providers.json"
    if not cfg_path.exists():
        # create empty template
        try:
            cfg_path.write_text(
                json.dumps(
                    {"providers": [], "default_model_id": None},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
        return [], None
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        providers = normalize_providers(raw.get("providers"))
        default_id = str(raw.get("default_model_id") or "").strip() or None
        # validate default still exists
        if default_id and not any(
            o["id"] == default_id for o in derive_model_options(providers)
        ):
            default_id = None
        return providers, default_id
    except Exception:
        return [], None


def load_style_config(data_dir: Path) -> dict[str, Any]:
    """读取画风设置。返回 {style_recommend: bool, custom_style: str}。"""
    cfg_path = data_dir / "providers.json"
    if not cfg_path.exists():
        return {"style_recommend": False, "custom_style": ""}
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        return {
            "style_recommend": bool(raw.get("style_recommend")),
            "custom_style": str(raw.get("custom_style") or "").strip(),
        }
    except Exception:
        return {"style_recommend": False, "custom_style": ""}


def save_config(
    data_dir: Path,
    providers: list[dict[str, Any]],
    default_model_id: str | None,
    style_recommend: bool = False,
    custom_style: str = "",
    gif_frame_count: int | None = None,
    gif_frame_duration_ms: int | None = None,
    gif_auto_fit: bool | None = None,
) -> None:
    cfg_path = data_dir / "providers.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "providers": providers,
        "default_model_id": default_model_id,
        "style_recommend": bool(style_recommend),
        "custom_style": str(custom_style or "").strip(),
    }
    if gif_frame_count is not None:
        payload["gif_frame_count"] = max(2, min(16, int(gif_frame_count)))
    if gif_frame_duration_ms is not None:
        payload["gif_frame_duration_ms"] = max(20, min(2000, int(gif_frame_duration_ms)))
    if gif_auto_fit is not None:
        payload["gif_auto_fit"] = bool(gif_auto_fit)
    cfg_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def resolve_model(
    providers: list[dict[str, Any]], default_model_id: str | None, requested: str | None
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Resolve (provider, model, endpoint_id) or raise ValueError."""
    eid = (requested or "").strip() or (default_model_id or "").strip()
    if not eid:
        raise ValueError(
            "尚未选择默认生图模型，请先配置 providers.json 并设置 default_model_id。"
        )
    parsed = parse_endpoint_id(eid)
    if not parsed:
        raise ValueError(f"生图模型 ID 无效：{eid}")
    pid, mid = parsed
    prov = next((p for p in providers if p["id"] == pid), None)
    if not prov:
        raise ValueError(f"找不到生图供应商：{pid}")
    if not prov.get("enabled"):
        raise ValueError(f"生图供应商当前不可用：{prov['name']}")
    model = next((m for m in prov.get("models") or [] if m["id"] == mid), None)
    if not model:
        raise ValueError(f"找不到生图模型：{eid}")
    if not model.get("enabled"):
        raise ValueError(f"生图模型当前不可用：{model['name']}")
    if not (model.get("model") or "").strip() and prov["provider_type"] != "comfyui":
        raise ValueError(f"生图模型缺少供应商模型名：{model['name']}")
    return prov, model, endpoint_id(pid, mid)


def resolve_default_model(
    providers: list[dict[str, Any]], default_model_id: str | None
) -> dict[str, Any] | None:
    """根据默认模型 ID 解析出模型 dict；未配置/无效返回 None。"""
    if not default_model_id:
        return None
    parsed = parse_endpoint_id(default_model_id)
    if not parsed:
        return None
    pid, mid = parsed
    prov = next((p for p in providers if p["id"] == pid), None)
    if not prov:
        return None
    return next((m for m in prov.get("models") or [] if m["id"] == mid), None)


def model_style_hint(model: dict[str, Any] | None) -> str:
    """根据模型 dict 返回其擅长画风描述；未命中返回空串。

    用「包含」而非「前缀」匹配：真实模型名如 doubao-seedream-5.0-lite
    以 doubao 开头、sensenova-u1.5-lite 也常带厂商前缀，前缀匹配会漏。
    """
    if not model:
        return ""
    mname = str(model.get("model") or "").lower()
    for prefix, style in MODEL_STYLES.items():
        if prefix in mname:
            return style
    return ""


def build_style_hint(
    providers: list[dict[str, Any]],
    default_model_id: str | None,
    style_recommend: bool,
    custom_style: str,
) -> str:
    """拼接注入工具 description 的画风文案。
    - 模型推荐（勾选）命中当前默认模型时注入其擅长画风
    - 自定义画风非空时追加用户建议
    - 两者可叠加；都没有则返回空串（不注入）
    """
    parts: list[str] = []
    if style_recommend:
        model = resolve_default_model(providers, default_model_id)
        rec = model_style_hint(model)
        if rec:
            parts.append(f"当前模型擅长的画风：{rec}")
    cus = str(custom_style or "").strip()
    if cus:
        parts.append(f"用户希望使用的画风：{cus}")
    return "；".join(parts)


# 未配置时的动图默认值：16 帧 / 100ms（约 1.6s 循环，比官方默认 9帧/200ms 流畅得多）
DEFAULT_GIF_FRAME_COUNT = 16
DEFAULT_GIF_FRAME_DURATION_MS = 100


def load_gif_defaults(data_dir: Path) -> dict[str, Any]:
    """读取动图默认参数。未配置时返回内置默认（16 帧 / 100ms）。

    Returns:
        {"frame_count": int, "frame_duration_ms": int}，均已做范围钳制。
    """
    fc = DEFAULT_GIF_FRAME_COUNT
    fd = DEFAULT_GIF_FRAME_DURATION_MS
    cfg_path = data_dir / "providers.json"
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if raw.get("gif_frame_count") is not None:
                fc = max(2, min(16, int(raw["gif_frame_count"])))
            if raw.get("gif_frame_duration_ms") is not None:
                fd = max(20, min(2000, int(raw["gif_frame_duration_ms"])))
        except Exception:
            pass
    return {"frame_count": fc, "frame_duration_ms": fd}


def load_gif_auto_fit(data_dir: Path) -> bool:
    """读取「动图尺寸自动换算」开关，未配置时默认开启。"""
    cfg_path = data_dir / "providers.json"
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if "gif_auto_fit" in raw:
                return bool(raw["gif_auto_fit"])
        except Exception:
            pass
    return True


def model_supports_gif(model: dict[str, Any] | None) -> bool:
    """判断模型是否支持 gif 动图输出。

    当前仅 OpenAI gpt-image-2 系列（2.6 起官方支持 animated GIF）。
    其它供应商会忽略 output_format="gif"，因此需要提前拦截并提示用户。
    """
    if not model:
        return False
    mname = str(model.get("model") or "").strip().lower()
    return mname.startswith("gpt-image-2")
