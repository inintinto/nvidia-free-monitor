# NVIDIA Free Endpoint Monitor v3 架构设计与边界规范

本文档为 `nvidia-free-monitor` v3 版本的正式架构设计、部署边界规范与实施路线图。

---

## 1. 系统定位与核心身份体系

### 1.1 系统定位
本项目定位为 **“NVIDIA Free Endpoint 全球免费模型监控与交互式目录系统”**：
- **监控端**：自动化追踪 NVIDIA 官方 API 目录变动，提供毫秒级生命周期审计与实时告警。
- **查询端**：为全球开发者提供即时、结构化、多维度的 Telegram 免费模型目录检索前端。

### 1.2 三层模型身份体系 (Identity Hierarchy)
系统严格区分并固化三层身份体系，绝不混淆平台方与模型原厂：

```
Level 1: Platform (模型托管与服务平台)
         └── 恒为 "NVIDIA NIM"

Level 2: Provider (模型原厂/研发机构)
         ├── NVIDIA (研发 Nemotron, NV-Embed, Parakeet, Edify 等)
         ├── DeepSeek AI (研发 DeepSeek V4 Flash, DeepSeek R1 等)
         ├── Meta (研发 Llama 3.1, Llama 3.3 等)
         ├── Google (研发 Gemma, CodeGemma 等)
         ├── Zhipu AI / Moonshot AI / Mistral AI / 01-ai / BAAI / IBM 等

Level 3: Model (具体模型实例)
         ├── Display Name: DeepSeek V4 Flash 0731
         ├── Model ID: deepseek-ai/deepseek-v4-flash-0731
         └── Model Family: DeepSeek-V4
```

> **重要准则**：NVIDIA 既是 NIM 平台提供方，也是 Nemotron 系列模型的研发方，二者在 `Platform` 与 `Provider` 层级分别记录，概念清晰解耦。

---

## 2. 部署架构与职责边界 (Deployment Architecture)

本项目采用 **Serverless + GitOps 现代化轻量架构**，无需采购或维护常驻 VPS。

```
                    ┌──────────────────────────────────────────────┐
                    │            NVIDIA Free API Endpoint          │
                    │   https://integrate.api.nvidia.com/v1/models │
                    └──────────────────────┬───────────────────────┘
                                           │
                        [GitHub Actions 每 30 分钟采集]
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │             GitHub Actions Runner            │
                    │               (src/monitor.py)               │
                    └───────┬──────────────────────────────┬───────┘
                            │                              │
                    [检测到变更时发送告警]              [自动 Commit & Push]
                            ▼                              ▼
                    ┌───────────────┐              ┌───────────────────────────┐
                    │ Telegram Bot  │              │       Git Repository      │
                    │  变更广播推送  │              │ (data/model_catalog.json) │
                    └───────────────┘              │ (data/lifecycle.json)     │
                                                   └─────────────┬─────────────┘
                                                                 │
                                                    [HTTPS 异步拉取最新数据]
                                                                 ▼
┌───────────────────────┐                  ┌───────────────────────────────────┐
│     Telegram User     │ <==============> │     Cloudflare Workers 前端       │
│  /start /models /model│ (Webhook 实时交互)│          (TypeScript/JS)          │
│  Inline Keyboard 菜单 │                  │  • setMyCommands 原生菜单注入      │
│  Model Detail 详情卡片│                  │  • Unified Model Resolver 检索    │
└───────────────────────┘                  └───────────────────────────────────┘
```

### 2.1 各组件职责分工

| 组件 | 运行载体 | 核心职责 |
| :--- | :--- | :--- |
| **数据采集与审计** | **GitHub Actions** | • 每 30 分钟定时抓取 NVIDIA `/v1/models`<br>• 模型 Added / Removed 变动检测与 baseline 管理<br>• `lifecycle.json` 与 `model_catalog.json` 自动维护<br>• 变更发生时通过 Telegram Bot 发送广播告警<br>• 自动化测试 / CI 门禁与数据版本控制 |
| **查询交互前端** | **Cloudflare Workers** | • 接收 Telegram Webhook 实时请求<br>• 自动初始化/更新 Telegram 原生 Bot Command 菜单 (`setMyCommands`)<br>• 处理 `/start`, `/models`, `/model <query>`, `/help`<br>• 处理 Inline Keyboard 按钮回调 (Provider $\rightarrow$ Capability $\rightarrow$ Model $\rightarrow$ Detail)<br>• 调用与核心契约一致的 Model Resolver 检索引擎<br>• 从 GitHub 仓库读取最新 catalog/lifecycle 数据并缓存<br>• 渲染并返回高可读性 Telegram HTML 详情卡片 |
| **用户交互端** | **Telegram** | • 用户操作 UI<br>• 原生 Bot Command 菜单与输入建议<br>• 四级 Inline Keyboard 交互<br>• Model Detail 富文本渲染 |
| **GCP / VPS** | **明确不使用** | • **V3 架构严禁要求常驻 VPS**<br>• 不引入 Docker、PostgreSQL、Redis 等外部重型依赖<br>• 不修改用户现有的其他 VPS 服务 |

---

## 3. Telegram Bot 原生菜单注入规范 (Menu Injection)

**Telegram Bot Command Menu 是 V3 Stage 2 的强制验收特性。**

### 3.1 菜单命令清单

```
/start  - NVIDIA 免费模型监控
/models - 浏览免费模型目录
/model  - 查询指定模型
/help   - 查看使用帮助
```

### 3.2 技术实现与生命周期准则
1. **自动化注入 API**：通过 Telegram Bot API 的 `setMyCommands` HTTP 端点进行注册。
2. **幂等性与零手动配置**：Worker 部署或冷启动时自动校验并更新菜单，不依赖 BotFather 手动维护。
3. **多语言与 Scope 支持**：
   - 默认全局 scope 与私聊 scope (`BotCommandScopeDefault`, `BotCommandScopeAllPrivateChats`) 均自动下发。
   - 优先支持中文（`zh`）与英文（`en`）描述。
4. **Token 安全**：`TELEGRAM_BOT_TOKEN` 仅通过 Cloudflare Worker Secret 注入，严禁写入源码。

---

## 4. 四级 Inline Keyboard 交互状态机

用户通过 `/models` 进入四级树状导航：

```
Level 1: Provider Selection
Level 2: Capability Filter (多标签)
Level 3: Model Listing (友好名称)
Level 4: Model Detail View
```

### 4.1 视图与状态流转

```
[用户输入 /models]
         │
         ▼
┌────────────────────────────────────────┐
│ Level 1: Provider Menu                 │
│ 请选择模型提供商:                      │
│ [ 🟢 NVIDIA ]     [ 🔵 DeepSeek AI ]   │
│ [ 🟣 Meta ]       [ 🟠 Zhipu AI ]      │
│ [ 🟡 Moonshot AI ][ ⚪ Other Providers ]│
│ [ 🌐 All Models ]                      │
└──────────────────┬─────────────────────┘
                   │ (选中 Provider, 如 DeepSeek AI)
                   ▼
┌────────────────────────────────────────┐
│ Level 2: Capability Menu (多标签支持)  │
│ DeepSeek AI - 请选择能力分类:          │
│ [ 💬 Chat ]       [ 🧠 Reasoning ]     │
│ [ 💻 Coding ]     [ 👁 Vision ]        │
│ [ 🎵 Audio ]      [ 🖼 Image ]         │
│ [ 📋 All Models ] [ 🔙 Back ]          │
└──────────────────┬─────────────────────┘
                   │ (选中 Capability, 如 Coding)
                   ▼
┌────────────────────────────────────────┐
│ Level 3: Model Listing Menu            │
│ DeepSeek AI > Coding 模型列表:         │
│ [ 🔹 DeepSeek V4 Flash 0731 ]          │
│ [ 🔹 DeepSeek Coder 6.7B ]             │
│ [ 🔙 Back ]                            │
└──────────────────┬─────────────────────┘
                   │ (点击具体模型)
                   ▼
┌────────────────────────────────────────┐
│ Level 4: Model Detail View             │
│ 渲染完整 Model Detail HTML 卡片        │
│ 附带: [ 🔙 返回列表 ] [ 🌐 官方门户 ]  │
└────────────────────────────────────────┘
```

### 4.2 Callback Data 64 字节超限防御
- **协议格式**：`c:<view>:<arg1>:<arg2>`
- **短 ID / 索引映射**：在内存中建立模型序号映射（`0 <-> deepseek-ai/deepseek-v4-flash-0731`），按钮回调参数仅传递 `c:d:0`（$\le 10$ 字节），彻底杜绝 Telegram 64 字节截断问题。

---

## 5. 统一检索解析引擎 (Unified Model Resolver)

`/models` 导航与 `/model <query>` 命令检索**共用同一个 Model Resolver 检索契约**，禁止为 Telegram 单独开发另一套逻辑。

### 5.1 检索优先级打分标准

| 优先级 | 分值 | 规则 | 示例输入 $\rightarrow$ 目标 |
| :--- | :--- | :--- | :--- |
| **Rank 1** | **100** | 精确 Model ID 匹配 | `deepseek-ai/deepseek-v4-flash-0731` $\rightarrow$ DeepSeek V4 Flash |
| **Rank 2** | **90** | 精确 Display Name / Alias 匹配 | `DS V4 Flash 0731`、`nemotron` $\rightarrow$ 精确命中 |
| **Rank 3** | **75** | Slug / Suffix 匹配 | `deepseek-v4-flash-0731` $\rightarrow$ 精确命中 |
| **Rank 4** | **60** | Token All-Match 全词匹配 | `deepseek v4 flash` $\rightarrow$ 命中候选 |
| **Rank 5** | **40** | Partial / Substring 模糊匹配 | `llama` $\rightarrow$ 匹配全部 Llama 系列 |

### 5.2 检索响应决策
- **`EXACT` (唯一命中)**：直接渲染完整 Model Detail HTML 卡片。
- **`MULTIPLE` (多项候选命中)**：返回 Inline Keyboard 按钮列表（如匹配到 4 个 Llama 模型供用户二次选择）。
- **`EMPTY` (无结果)**：返回友好提示：
  ```text
  ❌ No models found matching "<query>".
  💡 Try /models to browse by Provider or use a more specific name.
  ```

---

## 6. Model Detail 标准卡片与 HTML 格式规范

```html
🤖 <b>DeepSeek V4 Flash 0731</b>
<i>DeepSeek-V4 Series</i>

🏷 <b>Model ID:</b> <code>deepseek-ai/deepseek-v4-flash-0731</code>
🏢 <b>Provider:</b> <code>DeepSeek AI</code>
🌐 <b>Platform:</b> <code>NVIDIA NIM</code>
✨ <b>Status:</b> 🟢 Active Free Endpoint

📋 <b>Specifications:</b>
• <b>Architecture:</b> <code>MoE</code>
• <b>Parameters:</b> <code>Unknown</code>
• <b>Context Length:</b> <code>128k</code>
• <b>Capabilities:</b> <code>Chat</code>, <code>Reasoning</code>, <code>Coding</code>

⏱ <b>Lifecycle:</b>
• <b>First Seen:</b> <code>2026-07-31</code>
• <b>Free Since:</b> <code>2026-07-31</code>
• <b>Last Active:</b> <code>2026-08-23 10:00 UTC</code>
• <b>Official Lifecycle:</b> <code>Active (No Deprecation Announced)</code>

📊 <b>Global NVIDIA API Calls:</b>
• <b>Last 30 Days:</b> <code>3.2M calls</code>
• <i>Source: NVIDIA API Catalog Public Aggregate (Global)</i>

🔗 <a href="https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731">NVIDIA NIM Portal</a> | <a href="https://www.deepseek.com">Official Site</a>
```

### 全球公开调用量 (`UsageStats`) 严格规范
1. **纯全球公开汇总**：所有 `api_calls_*` 必须指代 **NVIDIA 官方公开的全球模型调用统计**。
2. **严禁混淆个人数据**：绝对不包含用户自己的调用量、Telegram Bot 调用量或本项目请求量。
3. **严禁非法推算**：严禁使用 `30d / 30` 估算日调用量。
4. **缺省保护**：官方无数据时显示 `Data not published by NVIDIA` 或 `null`，严禁伪造。

---

## 7. 三层数据存储架构 (Data Schema)

```
data/
├── nvidia_api_models.json    # [Layer 1] 原始 API Baseline (保持纯净，供 v2 监控 diff)
├── model_catalog.json        # [Layer 2] 富元数据模型目录 (支持多 Capability、架构、别名与全球调用量)
└── lifecycle.json            # [Layer 3] 模型生命周期历史 (区分观测下线与官方废弃宣告)
```

---

## 8. Secrets 安全规范

| 凭据名称 | 所属环境 | 访问权限 | 用途 |
| :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Cloudflare Worker Secret | Worker 专用 | 处理 Webhook、响应查询、注入 Bot 菜单 |
| `TELEGRAM_BOT_TOKEN` | GitHub Actions Secret | Workflow 专用 | 检测到模型变动时发送告警广播 |
| `TELEGRAM_CHAT_ID` | GitHub Actions Secret | Workflow 专用 | 告警广播目标频道/群组 |
| `TELEGRAM_WEBHOOK_SECRET_TOKEN` | Cloudflare Worker Secret | Worker 专用 | (可选) 校验 Telegram Webhook 来源合法性 |

> **红线原则**：所有 Token / Secret 严禁进入 Git 仓库、代码文件、日志输出与测试用例。

---

## 9. 实施阶段与 Stage 2 强制验收清单

### 9.1 四阶段规划
- **Stage 1 (已完成)**：数据模型与 Model Resolver 纯 Python 核心引擎 + 15 项测试套件。
- **Stage 2 (下一步)**：Cloudflare Worker Telegram 前端 + Bot Menu 注入 + 完整 UI 交互。
- **Stage 3**：GitHub Actions 监控流水线与 `lifecycle.json` / `model_catalog.json` 自动同步挂钩。
- **Stage 4**：端到端云端联合部署与全链路自动化验证。

### 9.2 Stage 2 强制验收检查清单 (Checklist)

进入 Stage 2 实施后，必须逐项达成以下验收标准方可交付：

- [ ] **Cloudflare Worker 正常运行**：能够正确解析请求并响应。
- [ ] **Telegram Webhook 通信畅通**：与 Telegram Bot API 双向握手正常。
- [ ] **`/start` 命令响应正常**：展示系统欢迎与操作指引。
- [ ] **`/models` 目录导航正常**：完整呈现 Provider 列表。
- [ ] **`/model <query>` 精确与模糊检索正常**：支持别名、Model ID 与模糊词。
- [ ] **`/help` 帮助指南正常**：呈现清晰的操作说明。
- [ ] **Telegram Bot Command Menu 注入成功**：通过 `setMyCommands` 正确下发官方菜单。
- [ ] **输入 `"/"` 命令自动补全正常**：Telegram 客户端弹出 `/models`、`/model` 等建议列表。
- [ ] **四级导航状态机流转正常**：Provider $\rightarrow$ Capability $\rightarrow$ Model $\rightarrow$ Detail 无卡顿。
- [ ] **Inline Keyboard `[ 🔙 Back ]` 返回正常**：层级返回准确无误。
- [ ] **Model Detail 视觉层次与 HTML 转义正常**：特殊字符（`<tag>`, `&`, `_`）无解析错误。
- [ ] **Global API Calls 语义安全呈现**：严格展示全球公开统计，无数据时安全显示。
- [ ] **Resolver 共享一致性**：按钮点击与命令行搜索共用同一检索内核。
- [ ] **零 VPS 依赖达成**：全链路运行于 Cloudflare Workers 与 GitHub，不依赖 GCP VPS。
