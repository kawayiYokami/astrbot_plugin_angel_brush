# Changelog

## 0.2.6 - 2026-11-24

### Fixed

- ModelScope 报「HTTP 404，404 page not found」：base_url 按其它供应商惯例带 `/v1`（如 `https://api-inference.modelscope.cn/v1`）时，路径会被拼成 `/v1/v1/images/generations`，被供应商网关拒绝。新增 `modelscope_endpoint` 拼接，根地址、带 `/v1`、带完整 endpoint 三种写法均归一到正确路径；任务轮询 URL 同样处理。
- WebUI 切换供应商类型时，若 Base URL 仍为空或为某模板默认值，会自动跟随新类型同步（自定义地址不覆盖），避免从其它类型切到 modelscope 后残留旧网关地址；Base URL 提示文案按类型区分。
- ModelScope 提交任务时记录实际请求 URL（`modelscope POST <endpoint> model=… async=true`，不含密钥），排障时可直接核对路径。

## 0.2.5 - 2026-11-24

### Added

- 新增 ModelScope（魔搭）API-Inference 供应商：走官方异步任务协议，提交 `X-ModelScope-Async-Mode` 生图任务后轮询 `v1/tasks/<task_id>` 直到 SUCCEED/FAILED，等待时长受供应商 `timeout_seconds` 约束。
- 文生图与图像编辑均已支持：编辑时把输入图转成 base64 data URL 放入 `image_url` 列表，最多 10 张；mask 暂不支持，会给出明确提示。
- 默认模板模型 `Qwen/Qwen-Image-2.1-Turbo`；API Key 可在 WebUI 填写，也可通过环境变量 `MODELSCOPE_API_TOKEN` / `MODELSCOPE_API_KEY` 提供（配置留空时生效，源码与测试不含任何密钥）。
- 任务结果图片地址做安全校验：仅允许 http/https，拒绝 localhost、环回、私有与保留地址，防止响应字段被利用发起内网请求。
- 画风推荐文案补充 Qwen-Image 擅长方向：复杂指令遵循与多图编辑、图内中英文文字渲染、写实人像与设计感插画。
- WebUI 供应商类型下拉新增 modelscope，配套文案与画风预览同步更新。

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
