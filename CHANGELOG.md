# Changelog

## 0.2.4 - 2026-11-21

### Fixed

- 生图后无法发送给用户：普通成员报 `Local file send is restricted`，沙箱模式报 `image path does not exist`。原因是原图保存在插件数据目录，而框架的 `send_message_to_user` 只放行会话工作区、AstrBot 临时目录与系统临时目录，插件数据目录不在其中。
- 现在每张图会额外复制一份到 `workspaces/<会话>/angel_brush/output/`，工具返回的 `absolute_path` 指向副本。原图仍完整保留在插件数据目录，`relative_path`、`remote_url`、`markdown` 均不受影响。
- 副本目录按 runtime 选择：`local` 用当前会话工作区（webchat 项目模式下是 `project_<id>`），`none` / `sandbox` 用 `workspaces/<umo>`。这与框架白名单取路径的方式一致，沙箱模式下白名单正是回落到 `workspaces/<umo>`。

### Changed

- 发送副本准备失败时返回 `ok: false, generated: true`，并提示处理发送问题而不是重新生图，避免把发送准备失败误认成生成失败。
- 副本源路径校验必须位于插件的 `generated-images` 目录内，越界直接拒绝。

### Tests

- 新增 `tests/_bootstrap.py`，用轻量替身替代 AstrBot 框架，使依赖框架的用例可以在不装框架的环境下运行。
- 新增 `tests/test_send_dir.py`：覆盖 local、webchat 项目、沙箱三种 runtime 的目录选择，副本改写与原件保留，越界拒绝，以及副本失败时的状态语义。
- 修正 `tests/test_brush.py` 中两条与当前实现相反的断言（工具描述早已改为「禁止在 markdown 内联」，用例仍在断言存在 markdown 图片行）。
