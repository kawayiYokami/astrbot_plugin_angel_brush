"""Minimal AstrBot stand-in so tests can import the plugin without the framework.

The stub mirrors the real semantics of the helpers the plugin calls:

- ``get_astrbot_data_path`` points at a temp dir supplied by the test
- ``default_workspace_root(umo)`` is ``<data>/workspaces/<normalized umo>``
- ``is_local_runtime`` reads ``provider_settings.computer_use_runtime``
- ``workspace_root_for_context`` returns the workspace pinned on the fake context
"""

from __future__ import annotations

import os
import re
import sys
import types


class _FakeLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None


def _normalize_umo_for_workspace(umo: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", umo.strip()) or "unknown"


def install_fake_astrbot() -> None:
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    api_star_module = types.ModuleType("astrbot.api.star")
    api_web_module = types.ModuleType("astrbot.api.web")
    core_module = types.ModuleType("astrbot.core")
    agent_module = types.ModuleType("astrbot.core.agent")
    run_context_module = types.ModuleType("astrbot.core.agent.run_context")
    tool_module = types.ModuleType("astrbot.core.agent.tool")
    agent_ctx_module = types.ModuleType("astrbot.core.astr_agent_context")
    runtime_module = types.ModuleType("astrbot.core.astr_agent_runtime")
    runtime_tools_module = types.ModuleType("astrbot.core.astr_agent_runtime.tools")
    computer_tools_module = types.ModuleType(
        "astrbot.core.astr_agent_runtime.tools.computer_tools"
    )
    computer_util_module = types.ModuleType(
        "astrbot.core.astr_agent_runtime.tools.computer_tools.util"
    )
    utils_module = types.ModuleType("astrbot.core.utils")
    path_module = types.ModuleType("astrbot.core.utils.astrbot_path")
    star_module = types.ModuleType("astrbot.core.star")
    star_tools_module = types.ModuleType("astrbot.core.star.star_tools")
    workspace_module = types.ModuleType("astrbot.core.workspace")

    logger = _FakeLogger()
    api_module.logger = logger

    class FunctionTool:
        """Fake FunctionTool base class for testing."""

        def __class_getitem__(cls, item):
            return cls

        async def call(self, context, **kwargs):  # pragma: no cover - overridden
            raise NotImplementedError

    class ToolExecResult:
        pass

    class ContextWrapper:
        pass

    class AstrAgentContext:
        pass

    class Star:
        def __init__(self, context=None):
            self.context = context

    def register(*args, **kwargs):
        def decorator(cls):
            return cls

        return decorator

    class Context:
        pass

    class StarTools:
        @staticmethod
        def get_data_dir(plugin_name: str | None = None):
            from pathlib import Path

            return (
                Path(get_astrbot_data_path()) / "plugin_data" / (plugin_name or "test")
            )

    tool_module.FunctionTool = FunctionTool
    tool_module.ToolExecResult = ToolExecResult
    tool_module.ToolSet = object
    run_context_module.ContextWrapper = ContextWrapper
    agent_ctx_module.AstrAgentContext = AstrAgentContext
    api_star_module.Context = Context
    api_star_module.Star = Star
    api_star_module.register = register
    star_tools_module.StarTools = StarTools

    def error_response(*args, **kwargs):
        return None

    def json_response(*args, **kwargs):
        return None

    class _Request:
        pass

    api_web_module.error_response = error_response
    api_web_module.json_response = json_response
    api_web_module.request = _Request()

    def get_astrbot_data_path() -> str:
        return os.environ["ASTRBOT_TEST_DATA_PATH"]

    def get_astrbot_plugin_data_path() -> str:
        return os.path.join(get_astrbot_data_path(), "plugin_data")

    def get_astrbot_temp_path() -> str:
        return os.path.join(get_astrbot_data_path(), "temp")

    def get_astrbot_workspaces_path() -> str:
        return os.path.join(get_astrbot_data_path(), "workspaces")

    def get_astrbot_root() -> str:
        return os.path.dirname(get_astrbot_data_path())

    path_module.get_astrbot_data_path = get_astrbot_data_path
    path_module.get_astrbot_plugin_data_path = get_astrbot_plugin_data_path
    path_module.get_astrbot_temp_path = get_astrbot_temp_path
    path_module.get_astrbot_workspaces_path = get_astrbot_workspaces_path
    path_module.get_astrbot_root = get_astrbot_root

    from pathlib import Path

    def default_workspace_root(umo: str) -> Path:
        return (
            Path(get_astrbot_workspaces_path()) / _normalize_umo_for_workspace(umo)
        ).resolve(strict=False)

    def workspace_root(umo: str) -> Path:
        return default_workspace_root(umo)

    def is_local_runtime(context) -> bool:
        cfg = context.context.context.get_config(
            umo=context.context.event.unified_msg_origin
        )
        runtime = str(
            cfg.get("provider_settings", {}).get("computer_use_runtime", "none")
        )
        return runtime == "local"

    async def workspace_root_for_context(context) -> Path:
        pinned = getattr(context, "workspace_root", None)
        if pinned is not None:
            return Path(pinned)
        return default_workspace_root(context.context.event.unified_msg_origin)

    computer_util_module.workspace_root = workspace_root
    computer_util_module.is_local_runtime = is_local_runtime
    computer_util_module.workspace_root_for_context = workspace_root_for_context

    workspace_module.normalize_umo_for_workspace = _normalize_umo_for_workspace
    workspace_module.default_workspace_root = default_workspace_root
    workspace_module.workspace_root = workspace_root

    modules = {
        "astrbot": astrbot_module,
        "astrbot.api": api_module,
        "astrbot.api.star": api_star_module,
        "astrbot.api.web": api_web_module,
        "astrbot.core": core_module,
        "astrbot.core.agent": agent_module,
        "astrbot.core.agent.run_context": run_context_module,
        "astrbot.core.agent.tool": tool_module,
        "astrbot.core.astr_agent_context": agent_ctx_module,
        "astrbot.core.astr_agent_runtime": runtime_module,
        "astrbot.core.astr_agent_runtime.tools": runtime_tools_module,
        "astrbot.core.astr_agent_runtime.tools.computer_tools": computer_tools_module,
        "astrbot.core.astr_agent_runtime.tools.computer_tools.util": computer_util_module,
        "astrbot.core.utils": utils_module,
        "astrbot.core.utils.astrbot_path": path_module,
        "astrbot.core.star": star_module,
        "astrbot.core.star.star_tools": star_tools_module,
        "astrbot.core.workspace": workspace_module,
    }
    sys.modules.update(modules)


class FakeToolContext:
    """Stand-in for ContextWrapper[AstrAgentContext] used by tool tests."""

    def __init__(
        self,
        umo: str = "default:GroupMessage:10001",
        runtime: str = "none",
        workspace_root: str | None = None,
    ):
        self.workspace_root = workspace_root
        self.context = types.SimpleNamespace(
            event=types.SimpleNamespace(unified_msg_origin=umo),
            context=types.SimpleNamespace(
                get_config=lambda umo=None: {
                    "provider_settings": {"computer_use_runtime": runtime}
                }
            ),
        )
