# NVIDIA Free Endpoint Monitor (v3)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js: 20+](https://img.shields.io/badge/Node.js-20%2B-green?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Tests: 325 Passing](https://img.shields.io/badge/Tests-325%20Passing%20(Baseline)-success?logo=github-actions&logoColor=white)](#-测试套件-testing)
[![Architecture: Zero--VPS](https://img.shields.io/badge/Architecture-Serverless%20%2F%20Zero--VPS-orange?logo=cloudflare&logoColor=white)](#-部署与架构-architecture)

> **NVIDIA Free API 模型自动监控、官方元数据聚合与证据链引擎，并提供 Serverless Telegram 交互式查询前端。**
>
> Automated monitoring, official metadata aggregation, and SHA-256 evidence ledger for NVIDIA Free API endpoints, powered by a Zero-VPS Serverless Telegram query bot.

---

## 📑 目录 (Table of Contents)

1. [💡 核心特性 (Key Features)](#-核心特性-key-features)
2. [🏛️ 系统架构 (Architecture)](#️-系统架构-architecture)
   - [三层身份体系 (Identity Hierarchy)](#三层身份体系-identity-hierarchy)
   - [数据流全景图 (Data Flow Diagram)](#数据流全景图-data-flow-diagram)
   - [SHA-256 证据链与状态机 (Evidence Engine)](#sha-256-证据链与状态机-evidence-engine)
3. [🤖 Telegram Bot 前端 (Telegram Bot Frontend)](#-telegram-bot-前端-telegram-bot-frontend)
   - [支持命令 (Commands)](#支持命令-commands)
   - [4 级交互式目录导航 (4-Level Catalog Navigation)](#4-级交互式目录导航-4-level-catalog-navigation)
   - [5 级模糊搜索与别名解析 (Model Resolver)](#5-级模糊搜索与别名解析-model-resolver)
   - [模型详情卡片 (Model Detail Card)](#模型详情卡片-model-detail-card)
   - [公共 Demo Bot 与频道 (Demo Bot & Channel)](#公共-demo-bot-与频道-demo-bot--channel)
4. [📊 数据资产与基线 (Data Assets Baseline)](#-数据资产与基线-data-assets-baseline)
5. [🚀 快速上手 (Quick Start)](#-快速上手-quick-start)
   - [Python 监控与元数据同步](#1-python-监控与元数据同步)
   - [Cloudflare Worker 本地调试与部署](#2-cloudflare-worker-本地调试与部署)
   - [GitHub Actions 自动化流水线配置](#3-github-actions-自动化流水线配置)
6. [🧪 测试套件 (Testing)](#-测试套件-testing)
7. [🛡️ 安全与隐私实践 (Security & Privacy)](#️-安全与隐私实践-security--privacy)
8. [📄 开源治理与社区 (Governance & Community)](#-开源治理与社区-governance--community)

---

## 💡 核心特性 (Key Features)

- **🔄 自动化双轮监控驱动**：
  - **实时差量巡检**：GitHub Actions 每 30 分钟轮询 NVIDIA 官方 API，精准检测模型新增（`added`）与下线（`removed`），仅在基线变动时触发 Git 提交并推送 Telegram HTML 告警。
  - **官方元数据同步**：每日定时提取 `build.nvidia.com` Next.js React Server Components (RSC) 数据流与 HTML 语义，结构化归档官方一手技术规格。
- **📜 SHA-256 不可变证据链引擎**：
  - 采用追加式（Append-only）JSONL 证据账本，每条元数据均携带时间戳、字段级哈希与 SHA-256 区块链式签名，支持确定性状态重放。
  - 严格遵循 **Ground Truth 优先**与 **零盲目猜测（No Guessing）** 原则，缺失的参数量或上下文严格标记为空，绝不从模型名称胡乱推测。
- **⚡ 零 VPS（Zero-VPS）现代 Serverless 架构**：
  - 核心监控基于 GitHub Actions + GitOps。
  - 查询前端基于 Cloudflare Workers (Edge V8) + GitHub Raw CDN 缓存，**运行服务器成本为 0**。
- **🔍 智能多维模型检索前端**：
  - 完整的 Telegram 交互式菜单：涵盖 30 家模型研发机构 Persona、4 级交互键盘以及 5 级评分的模糊别名搜索引擎。
- **🪶 纯净工程设计**：
  - Python 核心管道 **0 个外部 pip 依赖**，完全依赖 Python 3.12+ 标准库。
  - 全量 325 项自动化测试套件 **100% 离线运行**，无任何外部网络 IO 依赖。

---

## 🏛️ 系统架构 (Architecture)

### 三层身份体系 (Identity Hierarchy)

系统严格区分模型托管平台、研发原厂与具体模型实例，彻底解耦概念定义：

```text
Level 1: Platform (模型托管与服务平台)
         └── "NVIDIA NIM" (integrate.api.nvidia.com)

Level 2: Provider (模型原厂 / 研发机构)
         ├── NVIDIA (研发 Nemotron, NV-Embed, Parakeet 等)
         ├── DeepSeek AI (研发 DeepSeek V4, DeepSeek R1 等)
         ├── Meta (研发 Llama 3.1, Llama 3.3 等)
         ├── Google (研发 Gemma 2, CodeGemma 等)
         └── 智谱 AI / 零一万物 / 百川智能 / 阿里通义 / 微软 / Mistral 等 30 家原厂

Level 3: Model (具体模型实例)
         ├── Model ID: deepseek-ai/deepseek-v4-pro-0813
         ├── Display Name: DeepSeek V4 Pro 0813
         └── Model Family: DeepSeek-V4
```

> **概念准则**：NVIDIA 既是 NIM 平台运营方，也是 Nemotron 系列模型的研发原厂，系统在 `Platform` 与 `Provider` 字段严格解耦记录。

---

### 数据流全景图 (Data Flow Diagram)

```text
               ┌──────────────────────────────────────────────────────────┐
               │                NVIDIA Official Endpoints                 │
               │  1. API: https://integrate.api.nvidia.com/v1/models      │
               │  2. Web: https://build.nvidia.com/<model_id>             │
               └───────────────┬──────────────────────────┬───────────────┘
                               │                          │
               [每 30 分钟轮询] │                          │ [每日 06:00 UTC 同步]
                               ▼                          ▼
   ┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
   │      src/monitor.py (Engine 1)      │  │        src/catalog/ (Engine 2)      │
   │  - 安全守卫 (MIN_COUNT, MAX_DROP)   │  │  - build_parser.py (RSC 流/HTML解析)│
   │  - 差量对比 (Added / Removed)       │  │  - snapshot.py (版本化快照归档)     │
   │  - Telegram 告警推送 (Token 脱敏)   │  │  - evidence_ledger.py (SHA-256账本) │
   └───────────────────┬─────────────────┘  │  - merge.py (Ground Truth 裁决合并) │
                       │                    └───────────────────┬─────────────────┘
                       │                                        │
                       ▼                                        ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │                           Git Data Layer (GitOps)                            │
   │  ├── data/nvidia_api_models.json    (实时端点基线快照: 83 模型)               │
   │  ├── data/model_catalog.json        (结构化元数据: 参数量/上下文/模态/链接)  │
   │  ├── data/lifecycle.json            (双时间戳生命周期追踪)                   │
   │  ├── data/provider_catalog.json     (30 家原厂品牌与分类字典)                │
   │  └── data/sources/nvidia_build/     (20 个官方原始证据快照)                  │
   └──────────────────────────────────────┬───────────────────────────────────────┘
                                          │
                        [GitHub Raw CDN 自动拉取与 5 分钟缓存]
                                          │
                                          ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │                  Cloudflare Worker Telegram Bot (Frontend)                   │
   │  - worker/src/index.ts       (Webhook 接收与 Secret Token 验签)              │
   │  - worker/src/catalog.ts     (CatalogStore 内存加载与自动刷新)               │
   │  - worker/src/handlers.ts    (4 级交互式键盘导航: 厂商 -> 能力 -> 模型)      │
   │  - worker/src/resolver.ts    (5 级评分模糊与别名搜索引擎)                    │
   │  - worker/src/branding.ts    (厂商 Persona 徽章与 HTML 安全转义)             │
   └──────────────────────────────────────────────────────────────────────────────┘
```

---

### SHA-256 证据链与状态机 (Evidence Engine)

系统通过证据分层与不可变状态机保证所有技术元数据的权威性：

1. **4 级证据来源分层（Ground Truth 优先）**：
   - **Tier 1 (`OFFICIAL_BUILD`)**：`build.nvidia.com` 官方 RSC Payload 与 HTML（最高优先级，绝对权威）。
   - **Tier 2 (`OFFICIAL_DOCS`)**：`docs.api.nvidia.com` 官方接口文档。
   - **Tier 3 (`COMMUNITY_EVAL`)**：开源基准与社区评测（仅作辅助补充）。
   - **Tier 4 (`LOCAL_HEURISTIC`)**：本地规则推断（仅用于模型分类与显示排序标签，严禁填充参数量等核心字段）。
2. **防篡改与确定性重放**：
   - 每次数据提取均生成唯一 `EvidenceItem`，包含字段值、置信度、时间戳及来源快照路径。
   - `EvidenceLedger` 维护追加式账本，每个记录点均计算前向 SHA-256 签名，支持完全离线重放重建 Catalog 状态。

---

## 🤖 Telegram Bot 前端 (Telegram Bot Frontend)

本项目提供了一个基于 Cloudflare Workers 的极速 Serverless Telegram Bot 前端。

### 支持命令 (Commands)

| 命令 | 描述 | 说明 |
| :--- | :--- | :--- |
| `/start` | 启动与系统概览 | 欢迎消息、功能简介与快速入口 |
| `/models` | 浏览免费模型目录 | 触发 4 级交互式 Inline Keyboard 导航 |
| `/model <query>` | 精准/模糊查询模型 | 查询指定模型详情，如 `/model deepseek` 或 `/model llama-405b` |
| `/help` | 查看使用帮助 | 完整的命令说明与搜索技巧 |

---

### 4 级交互式目录导航 (4-Level Catalog Navigation)

Bot 采用短回调 ID 协议（`c:<view>:<idx>`），有效规避 Telegram 64 字节 Inline Callback 长度限制：

```text
Level 1: 厂商选择 (Provider Menu)
         ├── 🏢 DeepSeek AI (2 models)
         ├── 🏢 Meta (2 models)
         ├── 🏢 Google (1 models)
         └── 🏢 NVIDIA (1 models) ...
                 │
                 ▼
Level 2: 能力分类 (Capability Menu)
         ├── 💬 Chat / General
         ├── 💻 Coding
         ├── 🧠 Reasoning
         └── 👁️ Vision ...
                 │
                 ▼
Level 3: 模型列表 (Model List Menu)
         ├── ⚡ 🟢 DeepSeek V4 Flash 0731
         └── 👑 🟢 DeepSeek V4 Pro 0813
                 │
                 ▼
Level 4: 模型详情卡片 (Model Detail Card 2.0)
```

---

### 5 级模糊搜索与别名解析 (Model Resolver)

用户执行 `/model <query>` 时，解析器按以下 5 级加权机制匹配最佳结果：

1. **Exact Model ID Match (Score 100)**：完全匹配标准 ID（如 `deepseek-ai/deepseek-v4-pro-0813`）。
2. **Display Name Match (Score 90)**：精确匹配官方显示名称（如 `DeepSeek V4 Pro 0813`）。
3. **Normalized Slug Match (Score 75)**：忽略分隔符与大小写匹配（如 `deepseekv4pro`）。
4. **Token All-Match (Score 60)**：输入的所有分词均被模型名称包含（如 `llama 405b` $\rightarrow$ `meta/llama-3.1-405b-instruct`）。
5. **Fuzzy Substring Match (Score 40)**：部分子字符串容错匹配。

---

### 模型详情卡片 (Model Detail Card)

检索输出包含结构化排版的 HTML 详情卡片：

```text
🤖 DeepSeek AI 👑 DeepSeek V4 Pro 0813

📐 模型规格
• 架构类型: MoE (混合专家)
• 总参数量: 1.65T (官方认证)
• 激活参数: 49B (官方认证)
• 上下文长度: 1M tokens (官方认证)
• 输入模态: Text | 输出模态: Text

🎯 能力标签
• 💬 Chat  • 💻 Coding  • 🧠 Reasoning

📅 生命周期
• 状态: 🟢 活跃 (Active)
• 首次观测上线: 2026-08-27 UTC

🔗 官方资源
• [NVIDIA Build 页面](https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813)
• [API 接入文档](https://docs.api.nvidia.com/nim/deepseek-ai/deepseek-v4-pro-0813)
```

---

### 公共 Demo Bot 与频道 (Demo Bot & Channel)

- **💬 公共 Demo Bot**：
  > 维护者可在此配置公共演示 Bot 链接；用户亦可依照下文指南使用 Cloudflare Workers 免费一键部署专属私有 Bot。
- **📢 官方动态频道**：
  > 预留用于模型变动实时广播的 Telegram Channel 入口（可在 GitHub Secrets 中配置 `TELEGRAM_CHAT_ID` 绑定至你的私有或公开频道）。

---

## 📊 数据资产与基线 (Data Assets Baseline)

以下为当前代码库基准快照数据（非固定上限，随自动化流水线持续增量演进）：

| 文件路径 | 类型 | 当前基准规模 | 核心职责 |
| :--- | :---: | :---: | :--- |
| [`data/nvidia_api_models.json`](data/nvidia_api_models.json) | JSON | **83 个活跃模型** | 官方 API 端点实时基准快照，用于差量监控与告警 |
| [`data/model_catalog.json`](data/model_catalog.json) | JSON | **9 个深度模型** | 聚合官方富元数据（参数量、上下文、模态、官方链接等） |
| [`data/provider_catalog.json`](data/provider_catalog.json) | JSON | **30 家研发机构** | 模型研发厂商 Persona、官方品牌名称与分类定义 |
| [`data/lifecycle.json`](data/lifecycle.json) | JSON | **生命周期记录** | 记录模型上线观测时间与官方弃用（Deprecation）时间戳 |
| [`data/sources/nvidia_build/snapshots/`](data/sources/nvidia_build/snapshots/) | HTML/JSON | **20 个原始快照** | Git 版本化存储的官方原始网页与 RSC Payload 证据快照 |

---

## 🚀 快速上手 (Quick Start)

### 1. Python 监控与元数据同步

Python 核心组件基于标准库开发，无需安装任何外部 pip 包。

```bash
# 1. 克隆仓库
git clone https://github.com/inintinto/nvidia-free-monitor.git
cd nvidia-free-monitor

# 2. 配置环境变量 (可选，若需发送 Telegram 告警)
cp .env.example .env
# 编辑 .env 填入 TELEGRAM_BOT_TOKEN 与 TELEGRAM_CHAT_ID

# 3. 运行端点差量监控
python src/monitor.py

# 4. 运行官方元数据抓取与同步
python -m src.catalog.orchestrator

# 5. 运行多源统一证据链编排 (支持 dry-run 预览)
python -m src.catalog.unified_orchestrator --dry-run
```

---

### 2. Cloudflare Worker 本地调试与部署

```bash
# 1. 进入 worker 目录并安装开发依赖
cd worker
npm install

# 2. 配置本地环境变量 (用于本地测试)
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars 填入 TELEGRAM_BOT_TOKEN

# 3. 本地启动开发服务器
npm run dev

# 4. 部署至 Cloudflare Workers
npm run deploy

# 5. 在 Cloudflare 中配置生产 Secrets
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET_TOKEN # 可选：Webhook 签名校验
npx wrangler secret put INIT_COMMAND_SECRET           # 可选：保护 /telegram/init-commands 接口

# 6. 初始化 Telegram Bot 菜单命令
curl -X POST https://<your-worker-subdomain>.workers.dev/telegram/init-commands \
  -H "X-Init-Command-Secret: <your_secret_if_configured>"
```

---

### 3. GitHub Actions 自动化流水线配置

Fork 本仓库后，在 GitHub 仓库 **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions** 中配置以下 Secrets 即可实现全自动无人值守监控：

| Secret 名称 | 是否必填 | 用途说明 |
| :--- | :---: | :--- |
| `TELEGRAM_BOT_TOKEN` | 必填 (用于告警) | 由 [@BotFather](https://t.me/BotFather) 颁发的 Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 必填 (用于告警) | 接收模型变动通知的目标频道 ID、群组 ID 或个人 Chat ID |

---

## 🧪 测试套件 (Testing)

本项目坚持严格的测试驱动开发（TDD）规范，所有测试 100% 离线运行，零网络 IO 依赖。

```bash
# 运行 Python 全量测试套件 (当前基线: 278 项测试)
python -m unittest discover -s tests -v

# 运行 Cloudflare Worker 全量测试套件 (当前基线: 47 项测试)
npm --prefix worker test

# 当前代码库测试总基准: 325 / 325 PASS (100% Passing Rate)
```

---

## 🛡️ 安全与隐私实践 (Security & Privacy)

- **零凭据仓库原则**：代码库与历史记录中严禁包含任何真实 API Key、Bot Token 或密码；所有凭据均通过环境变量或 KMS 注入。
- **日志防御性脱敏**：`src/monitor.py` 在捕获网络异常时，自动通过正则表达式将包含在 Telegram API URL 中的 Bot Token 替换为 `bot***REDACTED***`，防止 CI 日志泄密。
- **环境代理独立解析**：严格遵循 `HTTP_PROXY` 与 `HTTPS_PROXY` 独立协议语义，未配置代理时强制返回纯净直连实例，彻底消除本地硬编码代理端口。
- **CI 流水线严格白名单熔断**：`.github/workflows/official-metadata.yml` 在提交变更前强制校验 Git Diff，除 `data/model_catalog.json` 与 `snapshots/` 外，任何非授权文件变动将直接阻断并报错。
- **漏洞披露途径**：如发现安全缺陷，请参阅 [SECURITY.md](SECURITY.md)，通过 GitHub Private Vulnerability Reporting 私网安全通道提交。

---

## 📄 开源治理与社区 (Governance & Community)

- **开源许可证**：本项目采用标准宽松的 [MIT License](LICENSE) 授权，Copyright (c) 2026 inintinto。
- **行为准则**：本项目遵循 [Contributor Covenant 2.1](CODE_OF_CONDUCT.md) 社区行为规范。
- **安全政策**：详见 [SECURITY.md](SECURITY.md)。
- **贡献指南**：*CONTRIBUTING.md 规范即将在后续阶段正式发布*。欢迎通过 [GitHub Issues](https://github.com/inintinto/nvidia-free-monitor/issues) 与 [Pull Requests](https://github.com/inintinto/nvidia-free-monitor/pulls) 参与社区共建！
