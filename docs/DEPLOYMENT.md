# NVIDIA Free Endpoint Monitor 部署与配置指南 (Deployment Guide)

本指南面向希望搭建、运行或私有化部署 `nvidia-free-monitor` 的开发者与运维人员。

本项目采用 **Serverless + GitOps 架构**，无需采购或维护常驻 VPS。根据你的实际需求，可自由选择以下三种独立且渐进的部署场景：

- [🎯 场景 A：仅启用 GitHub Actions 自动监控与告警](#-场景-a仅启用-github-actions-自动监控与告警)（极简部署）
- [🌐 场景 B：部署完整 Telegram Bot + Cloudflare Worker 查询前端](#-场景-b部署完整-telegram-bot--cloudflare-worker-查询前端)（全栈私有化）
- [💻 场景 C：本地 Python 运行与离线测试开发](#-场景-c本地-python-运行与离线测试开发)（本地分析与调试）

---

## 🎯 场景 A：仅启用 GitHub Actions 自动监控与告警

适用于只需在 GitHub 云端自动巡检 NVIDIA API 模型变动，并在检测到模型新增/下线时向指定的 Telegram 会话、群组或频道接收差量通知的用户。

### 1.1 Fork 仓库并启用 Actions
1. 点击本仓库右上角的 **Fork** 按钮，将仓库复制到你的个人 GitHub 账号下。
2. 进入你 Fork 后的仓库页面，点击 **Actions** 标签页。
3. 若页面提示 *"Workflows aren't being run on this forked repository"*，点击 **"I understand my workflows, go ahead and enable them"** 启用自动化工作流。

---

### 1.2 获取 Telegram Bot Token 与 Chat ID

#### Step 1: 创建 Bot 并获取 Bot Token
1. 在 Telegram 中搜索并打开官方机器人 [@BotFather](https://t.me/BotFather)。
2. 发送 `/newbot` 指令，按照提示为你的 Bot 设置显示名称（Name）和用户名（Username，必须以 `bot` 结尾）。
3. 完成后，@BotFather 将提供一段 API Token（格式形如 `123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567`），记为 `<YOUR_TELEGRAM_BOT_TOKEN>`。

#### Step 2: 获取目标会话的 Chat ID (推荐使用官方 API)
> ⚠️ **关于 `getUpdates` 与 Webhook 的关系说明**：
> 当 Bot 已设置 Webhook 时，Telegram 不允许同时通过 `getUpdates` 接收更新。因此推荐在配置 Webhook 之前先执行本步骤；若后续需要重新使用 `getUpdates` 获取信息，可先调用官方 `deleteWebhook`（`curl "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/deleteWebhook"`）临时删除当前 Webhook。

1. **私聊通知（个人接收告警）**：
   - 在 Telegram 中向你的新 Bot 发送一条 `/start` 消息。
   - 在终端或浏览器中请求官方接口：
     ```bash
     curl "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/getUpdates"
     ```
   - 在返回的 JSON 中查找 `result[0].message.chat.id`（正整数，例如 `123456789`）。

2. **群组 / 超级群通知（团队接收告警）**：
   - 将你的 Bot 邀请加入目标群组，并在群内发送一条消息（如 `/start` 或 `test`）。
   - 请求 `getUpdates` 接口，在返回的 JSON 中查找 `result[0].message.chat.id`（负整数，例如 `-1001234567890`）。

3. **频道通知（广播接收告警）**：
   - 将你的 Bot 添加为目标频道的**管理员（Administrator）**，并确保赋予 **Post Messages（发布消息）** 权限。
   - **公开频道**：可以直接使用 `@频道用户名` 作为 `TELEGRAM_CHAT_ID`。
   - **私有频道**：在频道发布一条测试消息后调用 `getUpdates`，提取 `channel_post.chat.id` 获取数字 ID（负整数，例如 `-1009876543210`）。

---

### 1.3 配置 GitHub Actions Secrets
进入 Fork 后的仓库页面：
1. 依次点击 **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**。
2. 点击 **New repository secret**，分别添加以下两个环境变量：

| Secret 名称 | 必需度 | 说明 | 示例值 |
| :--- | :---: | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | 告警必需 | @BotFather 颁发的 Bot Token | `<YOUR_TELEGRAM_BOT_TOKEN>` |
| `TELEGRAM_CHAT_ID` | 告警必需 | 接收告警的会话/群组/频道 ID | `<YOUR_TELEGRAM_CHAT_ID>` |

> **💡 缺省与容错说明**：
> 若未配置上述 Secrets，GitHub Actions 的定时巡检与数据基线更新仍会 100% 正常执行。只有当实际检测到模型变动且缺少凭据时，控制台才会输出 `[INFO] Telegram credentials not configured, skipping notification.` 并安全跳过发送，流水线绝不会因此报错中断。

---

### 1.4 验证场景 A 运行
1. 进入 **Actions $\rightarrow$ NVIDIA Free Endpoint Monitor**。
2. 点击右侧 **Run workflow** 手动触发一次执行。
3. 执行成功后，查看 Run 日志确认基线对比结果；若存在模型变动且配置了有效凭据，你的 Telegram 将立即收到格式化 HTML 告警通知。

---

## 🌐 场景 B：部署完整 Telegram Bot + Cloudflare Worker 查询前端

适用于希望搭建自己的 Telegram 交互式查询机器人（支持 `/models` 4 级目录浏览与 `/model` 5 级模糊搜索）的用户。

> 💡 **项目体验**：维护者已部署公共演示 Bot [@nvidiamonitor_bot](https://t.me/nvidiamonitor_bot) 供直接体验。若需私有化部署，请遵循以下流程。

### 2.1 准备工作
- 已完成 [场景 A](#-场景-a仅启用-github-actions-自动监控与告警) 的 Fork 与 Bot Token 获取。
- 本地安装 **Node.js 20+** 与 **npm**。
- 拥有一个免费的 [Cloudflare](https://dash.cloudflare.com/) 账号。

---

### 2.2 修改 `wrangler.toml` 数据源绑定
进入 `worker/` 目录，打开 [`worker/wrangler.toml`](../worker/wrangler.toml)：

```toml
name = "nvidia-free-monitor-bot"
main = "src/index.ts"
compatibility_date = "2024-12-01"

[vars]
# ⚠️ 关键步骤：请将下方修改为你 Fork 后的 GitHub 仓库名
GITHUB_REPO = "<YOUR_GITHUB_USERNAME>/nvidia-free-monitor"
GITHUB_BRANCH = "main"
```

> **为什么必须修改 `GITHUB_REPO`？**
> Worker 启动后会自动从 GitHub Raw CDN 定时拉取并缓存模型元数据。修改为你的仓库名可确保 Worker 实时读取你自己仓库同步生成的最新 `model_catalog.json` 与 `nvidia_api_models.json`。

---

### 2.3 安装依赖与登录 Cloudflare

```bash
# 1. 进入 worker 目录
cd worker

# 2. 安装项目依赖
npm install

# 3. 本地调试（可选）
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars 填入 TELEGRAM_BOT_TOKEN 后启动本地开发服务器
# npm run dev

# 4. 登录 Cloudflare 账号
npx wrangler login
```

---

### 2.4 配置 Cloudflare Worker Secrets
在 `worker/` 目录下通过 Wrangler CLI 配置生产凭据。通过 `wrangler secret put` 写入的 Secret 会被加密直接保存至 Cloudflare 边缘运行时并即时生效（无需依赖重新构建）：

```bash
# 确保当前处于 worker/ 目录 (若不在请执行 cd worker)

# 1. 必填：配置 Bot Token
npx wrangler secret put TELEGRAM_BOT_TOKEN
# 提示输入时粘贴你的 <YOUR_TELEGRAM_BOT_TOKEN>

# 2. 可选（强烈推荐）：配置 Webhook 签名密钥，防止伪造请求
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET_TOKEN
# 提示输入时设置一个自定义高强度随机字符串（如字母数字组合）

# 3. 可选（强烈推荐）：配置管理接口保护密钥
npx wrangler secret put INIT_COMMAND_SECRET
# 提示输入时设置一个自定义高强度管理密钥
```

---

### 2.5 发布部署并获取 Worker 域名

```bash
# 在 worker/ 目录下执行部署
npm run deploy
```

部署成功后，控制台将输出你的 Worker 线上生产域名，例如：
`https://nvidia-free-monitor-bot.<YOUR_SUBDOMAIN>.workers.dev`

记下该域名，记为 `https://<YOUR_WORKER_SUBDOMAIN>.workers.dev`。

---

### 2.6 注册 Telegram Webhook 与初始化菜单

#### Step 1: 注册 Webhook (`setWebhook`)
调用 Telegram 官方 API 将流量导向你的 Cloudflare Worker。根据是否配置了 `TELEGRAM_WEBHOOK_SECRET_TOKEN`，选择对应的调用方式：

- **情况 ①：已配置 `TELEGRAM_WEBHOOK_SECRET_TOKEN`（推荐）**：
  ```bash
  curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook" \
    -H "Content-Type: application/json" \
    -d '{
      "url": "https://<YOUR_WORKER_SUBDOMAIN>.workers.dev/telegram/webhook",
      "secret_token": "<YOUR_WEBHOOK_SECRET_TOKEN>"
    }'
  ```

- **情况 ②：未配置 Webhook Secret（极简部署）**：
  ```bash
  curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook" \
    -H "Content-Type: application/json" \
    -d '{
      "url": "https://<YOUR_WORKER_SUBDOMAIN>.workers.dev/telegram/webhook"
    }'
  ```

预期返回：`{"ok":true,"result":true,"description":"Webhook was set"}`。

#### Step 2: 验证 Webhook 状态 (`getWebhookInfo`)
```bash
curl "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```
确认返回的 JSON 中 `"url"` 与你的 Worker 地址一致且 `"pending_update_count": 0`。

#### Step 3: 初始化 Bot 多语言快捷菜单 (`init-commands`)
调用 Worker 提供的初始化端点向 Telegram 注册中英文指令列表。根据是否配置了 `INIT_COMMAND_SECRET`，选择对应的调用方式：

- **情况 ①：已配置 `INIT_COMMAND_SECRET`（推荐）**：
  ```bash
  curl -X POST "https://<YOUR_WORKER_SUBDOMAIN>.workers.dev/telegram/init-commands" \
    -H "X-Init-Command-Secret: <YOUR_INIT_COMMAND_SECRET>"
  ```

- **情况 ②：未配置 Init Secret（极简部署）**：
  ```bash
  curl -X POST "https://<YOUR_WORKER_SUBDOMAIN>.workers.dev/telegram/init-commands"
  ```

预期返回：
```json
{
  "success": true,
  "registeredScopes": [
    "default (zh-default)",
    "default (zh)",
    "default (en)",
    "all_private_chats (zh-default)",
    "all_private_chats (zh)",
    "all_private_chats (en)"
  ],
  "errors": []
}
```

---

### 2.7 场景 B 交互全功能验证
在 Telegram 中向你的 Bot 发送以下指令进行端到端验证：

1. **健康检查验证**：
   在浏览器中访问 `https://<YOUR_WORKER_SUBDOMAIN>.workers.dev/health`（或 `/`），将返回标准 JSON：
   ```json
   {
     "status": "ok",
     "service": "nvidia-free-monitor-worker",
     "version": "3.0.0-stage2b"
   }
   ```
2. **欢迎指令 (`/start`)**：收到图文欢迎卡片及快捷导航按钮。
3. **目录浏览 (`/models`)**：展示当前 Catalog 中的模型厂商，并支持按厂商与能力继续下钻浏览。
4. **精确搜索 (`/model <精确名称>`)**：
   - 发送 `/model DeepSeek V4 Pro 0813`（*以当前 Catalog 为准，若模型更迭可替换为当前存在的其他模型*）$\rightarrow$ 立即返回排版完整的模型规格卡片（包含架构、参数量、上下文及官方链接）。
5. **模糊与多匹配搜索 (`/model <关键词>`)**：
   - 发送 `/model deepseek` 或 `/model llama` $\rightarrow$ 自动触发多结果解析器，返回候选列表按钮（例如 `🔍 找到 N 个与「deepseek」相关的模型`），点击即可展开对应详情。
6. **空搜索容错**：
   - 发送 `/model non_existent_model` $\rightarrow$ 收到未找到提示，并引导使用 `/models` 浏览全量目录。

---

## 💻 场景 C：本地 Python 运行与离线测试开发

适用于需要在本地单次执行监控、抓取官方元数据、调试证据链状态机或运行自动化测试的开发者。

### 3.1 准备环境
- 安装 **Python 3.12+**。
- **0 外部 pip 依赖**：核心代码全部依赖 Python 标准库，无需执行 `pip install -r requirements.txt`。

---

### 3.2 环境变量注入与本地执行
> ⚠️ **关于 `.env` 文件的说明**：
> 本项目 Python 核心代码遵循零第三方依赖原则，**不会**自动从磁盘加载 `.env` 文件。根目录的 [`.env.example`](../.env.example) 仅作为配置项名称与格式的参考模板。在本地执行时，请通过当前终端的 Shell 显式注入环境变量。

#### ① Linux / macOS (Bash / Zsh)
```bash
# 1. 注入环境变量 (可选，若需测试真实告警推送)
export TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>"
export TELEGRAM_CHAT_ID="<YOUR_TELEGRAM_CHAT_ID>"

# 可选代理配置 (若本地网络需要访问外部接口)
# export HTTP_PROXY="http://127.0.0.1:7890"
# export HTTPS_PROXY="http://127.0.0.1:7890"

# 2. 运行端点监控与差量比对
python src/monitor.py

# 3. 运行官方元数据抓取与合并
python -m src.catalog.orchestrator

# 4. 运行多源统一证据链编排 (dry-run 模式不写入磁盘)
python -m src.catalog.unified_orchestrator --dry-run
```

#### ② Windows (PowerShell)
```powershell
# 1. 注入环境变量 (可选)
$env:TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>"
$env:TELEGRAM_CHAT_ID="<YOUR_TELEGRAM_CHAT_ID>"

# 2. 运行监控脚本
python src/monitor.py

# 3. 运行官方元数据抓取
python -m src.catalog.orchestrator
```

#### ③ Windows (Command Prompt)
```cmd
:: 1. 注入环境变量 (可选)
set TELEGRAM_BOT_TOKEN=<YOUR_TELEGRAM_BOT_TOKEN>
set TELEGRAM_CHAT_ID=<YOUR_TELEGRAM_CHAT_ID>

:: 2. 运行监控脚本
python src/monitor.py
```

---

### 3.3 运行全量 100% 离线测试套件
本项目包含覆盖完整监控、解析器、状态机、多源编排与前端 Worker 的测试套件，**当前测试基准均基于本地静态快照与离线模拟数据运行，无需外部网络连接即可完整执行**：

```bash
# 1. 运行 Python 全量测试 (当前基准: 278 项测试，约 7~9 秒)
python -m unittest discover -s tests -v

# 2. 运行 Cloudflare Worker 全量测试 (当前基准: 47 项测试，约 1 秒)
npm --prefix worker test

# 当前代码库测试总基准: 325 / 325 PASS (100% Passing Rate)
```

---

## 🛡️ 常见排错与运维安全规范 (Troubleshooting & Security)

### 4.1 常见排错

1. **问题：发送消息后 Telegram Bot 没有反应**
   - 检查 Webhook 状态：调用 `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"`。
   - 若 `last_error_message` 提示 `Wrong response from webhook`，请检查 Worker 是否已成功部署且 `/telegram/webhook` 路径正确。
   - 若配置了 `TELEGRAM_WEBHOOK_SECRET_TOKEN`，确认 `setWebhook` 传递的 `secret_token` 与 Worker Secret 100% 一致。
2. **问题：`/telegram/init-commands` 报 `401 Unauthorized`**
   - 确认请求头中传递的 `X-Init-Command-Secret` 与 Worker 中设置的 `INIT_COMMAND_SECRET` 完全一致。
3. **问题：GitHub Actions 定时任务未按计划运行**
   - 进入仓库 **Actions** 页面，确认未处于禁用状态。
   - GitHub 平台在 Fork 仓库长期无活动（超过 60 天）时可能会自动暂停定时任务，进入 Actions 页面点击任意工作流即可重新激活。

---

### 4.2 生产安全规范
- **凭据绝不入库**：切勿将包含真实 Token 的 `.env` 或 `.dev.vars` 提交至 Git 仓库。
- **敏感日志脱敏**：`src/monitor.py` 内置了正则脱敏拦截器，即使网络报错也不会在 CI 日志中打印包含真实 Bot Token 的完整 API URL。
- **代理独立配置**：`src/catalog/build_parser.py` 严格遵循 `HTTP_PROXY` 与 `HTTPS_PROXY` 独立协议语义，未显式设置时默认为纯净直连。
- **漏洞披露**：如在部署或运行过程中发现安全问题，请参阅 [SECURITY.md](../SECURITY.md) 通过 GitHub Private Vulnerability Reporting 私网渠道向维护者提交。
