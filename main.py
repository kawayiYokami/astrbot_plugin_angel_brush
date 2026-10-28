"""AstrBot plugin: 天使的画笔 - image generation."""

from __future__ import annotations

import os

from astrbot.api.star import Context, Star, register
from astrbot.core.star.star_tools import StarTools

from astrbot.api import logger

from .tools import AngelImageEditTool, AngelImageGenerateTool


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

    async def terminate(self):
        logger.info("AngelBrush: terminated")
