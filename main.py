"""AstrBot plugin: 天使的画笔 - image generation."""

from __future__ import annotations

import os
import re

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.star.star_tools import StarTools

from .tools import AngelImageEditTool, AngelImageGenerateTool

# 关键词触发：「画一张动图 <描述>」直接生成 GIF 动图
_DRAW_GIF_RE = re.compile(r"^\s*画一张\s*动图\s*(.*)$", re.S)


def _plugin_version() -> str:
    try:
        meta_path = os.path.join(os.path.dirname(__file__), "metadata.yaml")
        with open(meta_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip()
    except (OSError, ValueError):
        pass
    return "0.0.0"


@register(
    "astrbot_plugin_angel_brush",
    "kawayiYokami",
    "天使的画笔：自调度生图插件",
    _plugin_version(),
    "https://github.com/kawayiYokami/AstrBot",
)
class AngelBrushPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.context = context
        self.config = config if isinstance(config, dict) else {}

        data_dir = StarTools.get_data_dir("astrbot_plugin_angel_brush")
        self.data_dir = data_dir
        logger.info(f"AngelBrush: data_dir={data_dir}")

        # Register LLM tools - angel_ prefix required
        self.gen_tool = AngelImageGenerateTool(data_dir=data_dir)
        self.edit_tool = AngelImageEditTool(data_dir=data_dir)
        self.context.add_llm_tools(self.gen_tool, self.edit_tool)
        logger.info("AngelBrush: registered angel_image_generate / angel_image_edit")

        # Optional: register web api for providers.json editing
        try:
            from .web_api import register_routes

            register_routes(self.context, data_dir, self.gen_tool, self.edit_tool)
            logger.info("AngelBrush: web api registered")
        except Exception as e:  # pragma: no cover
            logger.debug(f"AngelBrush: web api not registered: {e}")

    @filter.regex(r"^\s*画一张\s*动图\s*(.*)$")
    async def angel_draw_gif(self, event: AstrMessageEvent) -> None:
        """关键词触发：画一张动图 <描述> → 直接生成 GIF 动图并回复。

        走的是一条独立于 LLM 工具的确定性链路：正则命中即出图，不依赖大模型
        判断是否调用工具。回复后禁止默认 LLM 请求，避免重复作答。
        """
        from .core import config as cfg
        from .core import service

        text = event.get_message_str().strip()
        m = _DRAW_GIF_RE.match(text)
        prompt = (m.group(1).strip() if m else "").strip()
        if not prompt:
            event.set_result(
                MessageEventResult().message(
                    "想画什么动图呢？发送「画一张动图 描述」，"
                    "例如：画一张动图 一只在霓虹街头跳舞的橘猫"
                )
            )
            event.should_call_llm(True)
            return

        # 非 gpt-image-2 系列供应商会忽略 output_format=gif，提前拦截并提示
        try:
            providers, default_id = cfg.load_config(self.data_dir)
            model = cfg.resolve_default_model(providers, default_id)
        except Exception:
            model = None
        if not cfg.model_supports_gif(model):
            event.set_result(
                MessageEventResult().message(
                    "画动图需要 gpt-image-2 系列模型（如 gpt-image-2.6）。"
                    "请先在 WebUI → 功能设置里把默认模型切换过去。"
                )
            )
            event.should_call_llm(True)
            return

        # 用户引用/发送了图片 → 走图生图，把静图改造成动图；否则纯文生图
        try:
            from .tools import collect_event_image_refs

            refs = await collect_event_image_refs(event)
        except Exception:
            refs = []
        payload: dict = {"prompt": prompt, "output_format": "gif"}
        if refs:
            payload["operation"] = "edit"
            payload["images"] = refs
        else:
            payload["operation"] = "generate"

        try:
            result = await service.generate_images(self.data_dir, payload)
        except Exception as e:
            logger.warning(f"AngelBrush 关键词动图生成失败: {e}")
            event.set_result(MessageEventResult().message(f"动图生成失败：{e}"))
            event.should_call_llm(True)
            return

        images = result.get("images") or []
        if not images:
            event.set_result(
                MessageEventResult().message("动图生成失败：供应商没有返回图片")
            )
            event.should_call_llm(True)
            return

        mer = MessageEventResult().message(
            f"动图好了（{result.get('provider_name', '')} / {result.get('model', '')}）"
        )
        for img in images:
            path = img.get("absolute_path")
            if path:
                mer.file_image(path)
        event.set_result(mer)
        event.should_call_llm(True)

    async def terminate(self):
        logger.info("AngelBrush: terminated")
