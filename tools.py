"""LLM tools for Angel Brush - 2 tools with angel_ prefix."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext

_GEN_BASE_DESC = "根据提示词生成一张图片，自动保存到插件数据目录；返回为 file 绝对路径，禁止在 markdown 内联。"
_EDIT_BASE_DESC = "基于一张或多张输入图片按提示词编辑出新图（局部修改、消除、换背景、扩图、多图融合、风格参考），自动保存到插件数据目录；返回为 file 绝对路径，禁止在 markdown 内联。"


def _style_suffix(data_dir: Path) -> str:
    """读取画风配置并拼出 description 后缀；无画风时返回空串。"""
    from .core import config as cfg

    try:
        providers, default_id = cfg.load_config(data_dir)
        style = cfg.load_style_config(data_dir)
        hint = cfg.build_style_hint(
            providers,
            default_id,
            style.get("style_recommend", False),
            style.get("custom_style", ""),
        )
        return f"\n\n画风要求：{hint}" if hint else ""
    except Exception:
        return ""


def _update_description(tool: "AngelImageGenerateTool | AngelImageEditTool", base: str, data_dir: Path) -> None:
    tool.description = base + _style_suffix(data_dir)


def update_tool_descriptions(
    gen_tool: "AngelImageGenerateTool | None", edit_tool: "AngelImageEditTool | None"
) -> None:
    """按当前画风配置刷新两个工具的 description（运行时调用，无需重启）。"""
    if gen_tool is not None:
        _update_description(gen_tool, _GEN_BASE_DESC, gen_tool.data_dir)
    if edit_tool is not None:
        _update_description(edit_tool, _EDIT_BASE_DESC, edit_tool.data_dir)


async def collect_event_image_refs(event: Any) -> list[str]:
    """从当前消息（含引用/回复的图）中提取图片，返回 service 可解析的引用。

    LLM 无法得知用户"引用图片"的真实本地路径，若沿用模型自填的 images，
    就会出现"改出来的图跟原图无关"。因此编辑类工具必须以消息里的真实图片为准：
    优先本地绝对路径，否则统一转成 base64 data URL。

    注意：QQ/OneBot 的"引用消息"在 AstrBot 里是 Reply 组件，被引用消息的内容
    （含图片）挂在 Reply.chain 上，必须递归进去取；只看顶层 Image 是拿不到的。
    """
    if event is None:
        return []
    try:
        comps = event.get_messages() or []
    except Exception:
        return []
    try:
        from astrbot.core.message.components import Image, Reply  # type: ignore
    except Exception:
        return []

    # 引用消息里的图片优先（用户明确要改的就是那张），其次是本条消息自带的图
    imgs: list[Any] = []
    for c in comps:
        if isinstance(c, Reply):
            for rc in getattr(c, "chain", None) or []:
                if isinstance(rc, Image):
                    imgs.append(rc)
    for c in comps:
        if isinstance(c, Image):
            imgs.append(c)

    refs: list[str] = []
    for c in imgs:
        p = str(getattr(c, "path", "") or "").strip()
        # 本地路径可能已被平台清理，失效时改走 base64，避免拿到死路径
        if p and Path(p).exists():
            refs.append(p)
            continue
        try:
            b64 = await c.convert_to_base64()
        except Exception:
            b64 = ""
        if b64:
            refs.append(f"data:image/png;base64,{b64}")
    return refs


def _tool_success_value(result: dict[str, Any], prefix: str) -> str:
    images = result.get("images") or []
    image_lines = "\n".join(
        f"- {img.get('absolute_path') or img.get('relative_path')}" for img in images
    )
    import json

    payload = {
        "ok": True,
        "message": (
            f"{prefix}。已落盘到插件数据目录，返回为 file 绝对路径。必须使用 send_message_to_user 发送给用户，禁止在 markdown 内联。\n"
            f"调用示例：{{\"messages\": [{{\"type\": \"image\", \"path\": \"<file 绝对路径>\"}}]}}\n"
            f"待发送的图片 file 路径如下：\n{image_lines}\n"
            f"收到本工具结果后，立即调用 send_message_to_user 发送以上 file 路径的图片，不要只回复文字。"
        ),
        "provider": result.get("provider_name"),
        "providerType": result.get("provider_type"),
        "modelId": result.get("model_id"),
        "model": result.get("model"),
        "images": images,
        "providerText": result.get("provider_text"),
    }
    return json.dumps(payload, ensure_ascii=False)


@dataclass
class AngelImageGenerateTool(FunctionTool[AstrAgentContext]):
    name: str = "angel_image_generate"
    description: str = _GEN_BASE_DESC
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "生成图片时，把提示词写成一段连续的中文描述，包含主体、场景、光线、风格、构图，以及画面的情绪、氛围和故事感。描述要细致，用词要华丽，文笔要丰富，尽可能丰富，像在给画家描述一幅你想画的画，写成一篇小作文。不只是描述画面里有什么，还要描述这幅画给人的感觉、藏着的情感和故事。",
                },
                "resolution": {
                    "type": "string",
                    "description": "分辨率，例如 1024x1024，默认 1920x1920。",
                },
                "output_format": {
                    "type": "string",
                    "description": "输出格式：png（默认）、jpeg、webp、gif（动图，需 gpt-image-2 系列模型）。用户要求动图/会动的图时传 gif。",
                },
            },
            "required": ["prompt"],
            "additionalProperties": False,
        }
    )
    data_dir: Path = field(default=None)  # type: ignore[assignment]

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        from .core import service

        # 每次调用前刷新 description，保证画风变更即时进入下一轮 schema
        try:
            _update_description(self, _GEN_BASE_DESC, self.data_dir)
        except Exception:
            pass
        prompt = str(kwargs.get("prompt") or "").strip()
        resolution = str(kwargs.get("resolution") or "").strip() or None
        output_format = str(kwargs.get("output_format") or "").strip() or None
        # 用户在消息里引用/发送了图片时，本质是改图请求；模型常会错调 generate，
        # 这里自动切到 edit，保证引用的图片一定参与生成。
        try:
            event_refs = await collect_event_image_refs(
                getattr(getattr(context, "context", None), "event", None)
            )
        except Exception:
            event_refs = []
        if event_refs:
            result = await service.generate_images(
                self.data_dir,
                {
                    "prompt": prompt,
                    "operation": "edit",
                    "images": event_refs,
                    "output_format": output_format,
                },
            )
            return _tool_success_value(result, "已按引用的图片完成编辑并保存到插件数据目录")
        result = await service.generate_images(
            self.data_dir,
            {
                "prompt": prompt,
                "size": resolution,
                "operation": "generate",
                "output_format": output_format,
            },
        )
        return _tool_success_value(result, "图片已生成并保存到插件数据目录")


@dataclass
class AngelImageEditTool(FunctionTool[AstrAgentContext]):
    name: str = "angel_image_edit"
    description: str = _EDIT_BASE_DESC
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "编辑意图描述，说明要修改什么、保留什么。",
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "输入图片引用列表，支持插件数据目录相对路径、本地绝对路径或 data URL；多张时用于多图融合/参考。",
                },
                "mask": {
                    "type": "string",
                    "description": "可选 mask 图片引用，白色/不透明区域表示允许修改；仅部分供应商支持，不支持时会返回错误。",
                },
                "resolution": {
                    "type": "string",
                    "description": "最短边长度，例如 1024，不填按原图最短边；不要与 aspect_ratio 拼成 AxB，避免冲突。",
                },
                "aspect_ratio": {
                    "type": "string",
                    "description": "宽高比，例如 16:9、9:16、1:1、3:4，不填按原图比例。",
                },
            },
            "required": ["prompt", "images"],
            "additionalProperties": False,
        }
    )
    data_dir: Path = field(default=None)  # type: ignore[assignment]

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        from .core import service

        # 每次调用前刷新 description，保证画风变更即时进入下一轮 schema
        try:
            _update_description(self, _EDIT_BASE_DESC, self.data_dir)
        except Exception:
            pass
        prompt = str(kwargs.get("prompt") or "").strip()
        images = kwargs.get("images") or []
        mask = str(kwargs.get("mask") or "").strip() or None
        if isinstance(images, str):
            images = [images]
        images = [str(x).strip() for x in images if str(x).strip()]
        # 用户在当前消息里引用/发送的图片才是真正的编辑对象，覆盖模型自填的 images
        try:
            event_refs = await collect_event_image_refs(
                getattr(getattr(context, "context", None), "event", None)
            )
            if event_refs:
                images = event_refs
        except Exception:
            pass
        resolution = str(kwargs.get("resolution") or "").strip() or None
        aspect_ratio = str(kwargs.get("aspect_ratio") or "").strip() or None
        result = await service.generate_images(
            self.data_dir,
            {
                "prompt": prompt,
                "images": images,
                "mask": mask,
                "operation": "edit",
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
            },
        )
        return _tool_success_value(result, "图片已编辑并保存到插件数据目录")
