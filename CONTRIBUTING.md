# 贡献指南 (Contributing to NVIDIA Free Endpoint Monitor)

感谢你关注并有意愿为 `nvidia-free-monitor` 做出贡献！

本项目致力于构建自动化、高可靠的 NVIDIA 免费 AI API 端点监控、官方元数据聚合与不可变证据链引擎，并提供 Serverless Telegram 查询前端。我们欢迎社区开发者提交 Issue、报告缺陷、补充模型技术元数据或改进代码。

在提交 Pull Request 或 Issue 之前，请阅读以下简明指南，以确保协作高效且代码库保持高质量。

---

## 🛠️ 开发环境要求

参与项目开发与测试需要以下本地基础环境：

| 组件 | 版本要求 | 依赖说明 |
| :--- | :---: | :--- |
| **Python** | **Python 3.12+** | **核心代码 0 pip 依赖**：完全基于 Python 标准库开发，无需安装第三方 pip 包。 |
| **Node.js** | **Node.js 20+** | 仅用于 `worker/` 前端开发与测试，包管理器使用 **npm**。 |

---

## 🧪 运行测试套件

本项目推崇测试驱动开发（TDD）规范，所有单元测试均使用本地静态快照，**100% 离线运行且无任何网络 IO 依赖**。

在提交修改前，请确保在本地完整运行并全部通过测试套件：

```bash
# 1. 运行 Python 全量测试 (当前基准: 278 项测试)
python -m unittest discover -s tests -v

# 2. 运行 Cloudflare Worker 全量测试 (当前基准: 47 项测试)
npm --prefix worker test

# 当前代码库测试总通过率要求: 100% (325 / 325 PASS)
```

---

## 📐 核心工程约束与开发规范

为保持项目的纯净性与可长期维护性，请务必遵守以下核心原则：

### 1. Python 核心零外部依赖 (Zero Pip Dependencies)
- `src/` 下的核心监控与元数据解析逻辑必须**严格仅依赖 Python 标准库**（如 `urllib`, `json`, `hashlib`, `re`, `pathlib`, `unittest` 等）。
- 请勿随意引入 `requests`, `python-dotenv`, `pydantic` 等第三方包，以保持轻量跨平台特性与极简运行环境。

### 2. 真实证据优先与零臆测原则 (Ground Truth First, No Guessing)
- **官方数据优先**：元数据采集以 `build.nvidia.com` 官方 RSC Payload 与 HTML（Tier 1）为最高权威。
- **严禁主观推测参数**：若官方网页或接口未明确披露模型的参数量、激活参数或上下文长度，对应字段必须保留为空（`null` 或未定义），**严禁仅凭模型名称字面（如 `405B`）主观臆断填写**。
- **快照与证据账本**：每次新增官方数据解析规则，需在 `data/sources/nvidia_build/snapshots/` 归档原始快照，并确保 `src/catalog/evidence_ledger.py` 具备可重复的确定性重放能力。

### 3. 严格的安全与凭据隔离 (Zero Secrets)
- **切勿将任何敏感信息提交至 Git**：禁止提交 `.env`、`.dev.vars`、真实 Telegram Bot Token、Chat ID 或 API 密钥。
- 项目在 `.gitignore` 中默认排除了各类环境变量文件，本地调试请参考 [`.env.example`](.env.example) 与 [`worker/.dev.vars.example`](worker/.dev.vars.example)。
- 如果修改了日志输出逻辑，请确保异常日志经过 `sanitize_log_message()` 脱敏处理，防止凭据泄露。

---

## 🔄 提交 Issue 与 Pull Request 流程

### 提交 Issue
- **Bug 报告**：请附带复现步骤、报错日志（已脱敏）及 Python/Node 环境版本。
- **模型元数据补全 / 修正**：欢迎提供官方 `build.nvidia.com` 页面链接或权威一手文档，协助扩充 [`data/model_catalog.json`](data/model_catalog.json)。
- **功能建议**：欢迎提出关于端点监控、解析算法或 Bot 查询交互的改进构想。

### 提交 Pull Request (PR)
1. **Fork 本仓库** 并基于 `main` 分支创建特性分支（例如 `git checkout -b feat/add-model-resolver-rule`）。
2. **最小范围修改**：保持修改高度聚焦，避免无关的文件格式化或大规模无关重构。
3. **编写与补充测试**：若新增了功能或修复了缺陷，请在 `tests/` 或 `worker/tests/` 中增加对应的单元测试用例。
4. **验证全量测试**：确保本地运行 `python -m unittest discover -s tests` 与 `npm --prefix worker test` 全部通过。
5. **规范提交信息**：建议采用清晰的语义化提交前缀（如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`）。
6. **提交 PR 描述**：
   - 清楚说明该 PR 解决了什么问题或增加了什么能力；
   - 附带本地测试执行通过的简要说明。

---

## 🛡️ 安全漏洞报告 (Security)

请**切勿**通过公开 GitHub Issue 报告潜在的安全漏洞或凭据泄露问题。

如发现安全风险，请遵循我们的 [SECURITY.md](SECURITY.md)，通过 GitHub 官方提供的 **Private Vulnerability Reporting（私网漏洞提报）** 渠道与维护者联系，我们将优先评估并及时修复。

---

## 📜 行为准则与开源许可证

- 本项目遵循 [Contributor Covenant 2.1](CODE_OF_CONDUCT.md) 社区行为规范，期待所有参与者保持友善、尊重与专业的沟通氛围。
- 参与本项目的代码贡献均在宽松的 [MIT License](LICENSE) 授权下发布。
