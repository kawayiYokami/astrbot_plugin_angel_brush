# AngelBrush - 让机器人会画画、会改图

[![AstrBot Plugin](https://img.shields.io/badge/AstrBot-Plugin-blue)](https://github.com/Soulter/AstrBot)

AngelBrush 是一个专为 [AstrBot](https://github.com/Soulter/AstrBot) 平台设计的生图插件。聊天时说一句话就能出图，发一张图就能改图，图片保存在本地，随用随取。

## ✨ 核心特性

### 🎨 说话就出图

不用记任何指令，像平时聊天一样说"画一只坐在云朵上的橘猫"，机器人画好直接发给你。

### ✏️ 发图就能改

把图发给机器人，再告诉它想怎么改——换背景、去掉路人、换个风格、几张图合成一张，都可以。

### 🏪 七家画图服务随便换

OpenAI、xAI、豆包 Seedream、Gemini、SenseNova、ModelScope 魔搭、本地 ComfyUI 都支持。想用哪家就用哪家，也可以同时配好几家，随时切换。

### 🖥️ 配置全在网页上

打开 AstrBot 管理页面的 **插件页面 → brush-config**，填个密钥、选个模型，点点就能用，不用碰任何配置文件。

### 📁 画过的图都在

每张图按日期自动存好，不会丢。WebUI 里随时能翻最近画过的图。

## 🎯 主要功能

- **文字生成图片**：一句话描述，出一张图
- **图片编辑**：发图 + 说需求，改出新图；最多 16 张一起参考，支持蒙版
- **多服务管理**：多家画图服务共存，模型独立启用停用
- **网页配置**：供应商、模型、默认选择、试用测试，全在 WebUI 完成
- **工具测试**：不用进聊天，网页上直接试画，立刻看效果

## 🌟 天使五件套

同一只粉毛天使的五个能力化身，合在一起就是一个完整的灵魂：

| 插件 | 能力 |
|------|------|
| [天使之心](https://github.com/kawayiYokami/astrbot_plugin_angel_heart) | 智能群聊/私聊交互，懂分寸、知进退 |
| [天使之眼](https://github.com/kawayiYokami/astrbot_plugin_angel_eye) | 聊天记录查询，随时翻旧账 |
| [天使之笑](https://github.com/kawayiYokami/astrbot_plugin_angel_smile) | 表情包管理，看见好看的就想收进库存 |
| [天使之魂](https://github.com/kawayiYokami/astrbot_plugin_angel_memory) | AI 记忆与认知，越用越懂你 |
| [天使的画笔](https://github.com/kawayiYokami/astrbot_plugin_angel_brush) | 说话出图、发图改图 |

---

## 🚀 快速开始

### 前置要求

- [AstrBot](https://github.com/Soulter/AstrBot) 平台已安装并运行
- 至少一家画图服务的密钥（Key）

### 安装步骤

1. **非市场安装**：将插件下载到 AstrBot 的 plugins 目录
2. **市场安装**：在 AstrBot 的 插件-插件市场中搜索「天使的画笔」安装

### 开始使用

1. 打开 AstrBot 管理页面，进入 **插件页面 → brush-config**
2. 在 **供应商设置** 里添加画图服务：选类型、填网址和密钥，再填模型名
3. 在 **功能设置** 里选好默认模型，点右下角"保存"
4. 去聊天框跟机器人说"画一张 xxx"，就这些

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 🙏 致谢

- 感谢 [AstrBot](https://github.com/Soulter/AstrBot) 提供的优秀平台
- 感谢所有贡献者和用户的支持

---

**AngelBrush** - 你说一句，它画一张 💖
