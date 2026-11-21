"""LLM tools for Angel Brush - 2 tools with angel_ prefix."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.core.workspace import default_workspace_root

try:  # AstrBot 4.30 起 agent runtime 模块搬到了 astr_agent_runtime 下
    from astrbot.core.astr_agent_runtime.tools.computer_tools.util import (
        is_local_runtime,
        workspace_root_for_context,
    )
except ImportError:  # 4.29.x 及更早
    from astrbot.core.tools.computer_tools.util import (
        is_local_runtime,
        workspace_root_for_context,
    )

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


_SEND_SUBDIR = Path("angel_brush") / "output"


async def _send_output_dir(context: ContextWrapper[AstrAgentContext]) -> Path:
    """返回当前会话中「可被 send_message_to_user 读到」的图片目录。

    框架的发送工具只放行会话工作区、AstrBot 临时目录与系统临时目录下的
    文件；插件数据目录不在白名单内，直接把原图路径交给模型会发不出去
    （普通成员报权限错误，沙箱模式报路径不存在）。

    这里算目录的方式与框架白名单保持一致：local runtime 用
    workspace_root_for_context（webchat 项目模式下是 project_<id>），
    其余 runtime 下框架白名单回落到 legacy 的 workspaces/<umo>。
    """
    umo = context.context.event.unified_msg_origin
    if is_local_runtime(context):
        workspace = await workspace_root_for_context(context)
    else:
        workspace = default_workspace_root(umo)
    return workspace / _SEND_SUBDIR


async def _send_dir_or_none(context: ContextWrapper[AstrAgentContext]) -> Path | None:
    """解析可发送目录；失败时返回 None，退回原图路径而不是让生图失败。"""
    try:
        return await _send_output_dir(context)
    except Exception as exc:
        logger.warning(f"AngelBrush: 解析可发送目录失败，退回原图路径: {exc}")
        return None


def _copy_to_send_dir(
    images: list[dict[str, Any]], data_dir: Path, send_dir: Path
) -> list[dict[str, Any]]:
    """把原图复制到可发送目录，并把 absolute_path 指向副本。

    原图始终保留在插件数据目录：生成图片有实际成本，不能被任何自动清理
    带走；副本只服务于发送这一步，丢了还能从原图再复制。
    """
    source_root = (data_dir / "generated-images").resolve()
    send_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    for image in images:
        source = Path(image["absolute_path"]).resolve(strict=True)
        if not source.is_relative_to(source_root):
            raise ValueError(f"图片不在生成目录中: {source}")
        target = send_dir / source.name
        shutil.copyfile(source, target)
        copied.append({**image, "absolute_path": str(target)})
    return copied


def _tool_success_value(
    result: dict[str, Any],
    prefix: str,
    *,
    data_dir: Path | None = None,
    send_dir: Path | None = None,
) -> str:
    images = result.get("images") or []

    if send_dir is not None and data_dir is not None and images:
        try:
            images = _copy_to_send_dir(images, data_dir, send_dir)
        except (OSError, KeyError, ValueError) as exc:
            logger.warning(f"AngelBrush: 准备发送副本失败: {exc}")
            return json.dumps(
                {
                    "ok": False,
                    "generated": True,
                    "message": (
                        "图片已生成并保存到插件数据目录，但准备发送副本失败。"
                        "请处理发送问题，不要重新生图。"
                    ),
                    "error": str(exc),
                    "images": result.get("images") or [],
                },
                ensure_ascii=False,
            )

    image_lines = "\n".join(
        f"- {img.get('absolute_path') or img.get('relative_path')}" for img in images
    )

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
        result = await service.generate_images(
            self.data_dir,
            {"prompt": prompt, "size": resolution, "operation": "generate"},
        )
        return _tool_success_value(
            result,
            "图片已生成并保存到插件数据目录",
            data_dir=self.data_dir,
            send_dir=await _send_dir_or_none(context),
        )


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
        return _tool_success_value(
            result,
            "图片已编辑并保存到插件数据目录",
            data_dir=self.data_dir,
            send_dir=await _send_dir_or_none(context),
        )
