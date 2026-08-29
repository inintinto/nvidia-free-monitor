# 项目路线图 (Project Roadmap)

本文档阐明 `nvidia-free-monitor` 的核心战略定位、核心工程原则、已完成能力、当前工作重点及长期技术演进方向。

---

## 🧭 项目战略定位 (Project Direction)

本项目坚持 **NVIDIA First** 核心战略：

1. **立足 NVIDIA 深度深耕**：当前项目的核心定位是 **NVIDIA 免费 AI API 端点监控、官方元数据聚合与不可变证据链引擎 (NVIDIA Free Endpoint / Model Availability Monitor)**。我们将优先把针对 NVIDIA 端点的巡检可靠性、官方技术规格覆盖度、SHA-256 证据账本及 Serverless 查询前端做到扎实、严谨与稳定。
2. **长期探索可复用抽象**：在现有单平台架构完全成熟、数据链路经过充分生产验证后，审慎探索将通用的监控、快照归档、证据链状态机与数据分发模式推广至其他公开、免费的 AI 端点或模型可用性（Model Availability）数据源。
3. **质量重于平台数量**：我们绝不为了盲目追求平台数量而牺牲数据权威性、测试覆盖率与工程可靠性。

---

## 🎯 范围与工程原则 (Scope Principles)

- **NVIDIA First（单点做深）**：聚焦于 NVIDIA NIM 与 Build 端点生态，确保元数据精确无误。
- **Evidence over Speculation（真实证据高于主观猜测）**：坚持 Ground Truth 优先；缺失参数严格留空，严禁基于模型名称主观脑补。
- **Lightweight Infrastructure（极简轻量架构）**：坚守 GitHub Actions + GitOps + Cloudflare Workers 的 Zero-VPS Serverless 架构，不引入沉重的常驻服务器或私有数据库集群。
- **Quality before Platform Count（质量重于数量）**：宁缺毋滥，每条入库的元数据均须具备不可变的快照与哈希背书。
- **No Hard Deadlines（不设硬性时间节点）**：遵循质量驱动与测试驱动节奏，不制定脱离实际工程验证的阶段截止时间。
- **No Unsupported Promises（不作未经验证的承诺）**：清晰区分“已完成”、“进行中”与“长期探索”，杜绝功能虚标。

---

## 🟢 已完成能力 (Completed)

以下能力已在当前代码库完整实现，并通过了全量 329 项离线自动化测试验证：

- [x] **NVIDIA API 实时端点监控**：GitHub Actions 每 30 分钟自动化巡检，精准检测模型新增（`added`）与下线（`removed`）。
- [x] **双重安全熔断守卫**：实现 `MIN_VALID_MODEL_COUNT=50` 与 `MAX_DROP_RATIO=0.5` 异常防跌保护。
- [x] **官方一手元数据提取**：每日自动提取 `build.nvidia.com` Next.js React Server Components (RSC) 数据流与 HTML 结构化元数据。
- [x] **版本化原始快照归档**：在 `data/sources/nvidia_build/snapshots/` 实现一手证据文件的 Git 自动化归档。
- [x] **SHA-256 追加式证据账本**：实现轻量区块链式哈希校验账本（`evidence_ledger.py`），支持全量离线确定性状态重放与跨进程排他锁保护。
- [x] **Reddit 社区生态证据加固 (v3.1.0)**：实现基于纯内存 SHA-256 密码学存证的 Zero Raw Storage 机制，彻底杜绝原始帖子与用户内容落盘，严格维持 NVIDIA 官方 Ground Truth 绝对压制（`NVIDIA_BUILD > COMMUNITY_FORUM`），网络故障 100% 隔离（注：生产 CI 默认未配置密钥，保持可选 Sidecar 状态）。
- [x] **Telegram 差量变动告警**：在模型发生变动时自动向 Telegram 会话/群组/频道推送格式化 HTML 报告。
- [x] **Cloudflare Worker Serverless Bot 前端**：基于边缘计算与 GitHub Raw CDN 缓存，提供 0 服务器成本的交互式查询。
- [x] **4 级交互式目录导航与 5 级模糊搜索**：支持按厂商与能力下钻浏览，以及精准/别名/分词/模糊加权搜索 (`/model <query>`)。
- [x] **真实公共 Demo Bot 接入**：公开接入全天候可用实机 Bot [`@nvidiamonitor_bot`](https://t.me/nvidiamonitor_bot)。
- [x] **100% 离线自动化测试套件**：包含 282 项 Python 单测与 47 项 Worker 单测（共 329 项测试）。
- [x] **开源安全与治理体系**：MIT License、SECURITY.md（私网漏洞提报）、CODE_OF_CONDUCT.md、日志正则脱敏与独立代理语义。

---

## 🟡 当前重点方向 (Current Focus)

当前阶段的核心精力聚焦于代码质量加固、元数据覆盖度扩充与开源协作规范建设：

- [ ] **NVIDIA 抓取鲁棒性加固**：进一步提升针对官方网页频繁改版、RSC 数据格式演进的自愈解析与异常诊断能力。
- [ ] **模型富元数据深度覆盖扩充**：持续解析并扩充更多端点活跃模型的官方规格（架构、总参数量、激活参数量、官方文档链接等），逐步提升 [`data/model_catalog.json`](data/model_catalog.json) 覆盖深度。
- [ ] **证据质量与确定性重放维护**：持续校验并维护证据账本的历史一致性，确保重放算法对边界数据具备强健鲁棒性。
- [ ] **Telegram Bot 交互体验打磨**：微调键盘长文本排版与多语言交互提示，扩充中文与常用模型别名匹配映射表。
- [ ] **开源开发者基础设施建设**：
  - 完善部署手册 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) 与贡献规范 [`CONTRIBUTING.md`](CONTRIBUTING.md)；
  - 建立自动化 PR CI 测试流水线（`.github/workflows/ci.yml`），自动运行全量测试套件；
  - 建立 Issue / PR 结构化规范模板。

---

## 🔮 长期探索方向 (Future Direction)

以下方向属于中长期演进探索，不代表当前已支持或承诺具体交付周期：

### 1. 平台适配器抽象探索 (Platform Adapter Exploration)
- **目标**：在 NVIDIA 监控体系完全成熟后，探索将当前的数据获取、差量比对、快照归档与元数据合并层抽象为通用的适配器接口。
- **现状说明**：当前代码库已具备良好的三层身份解耦（Platform $\rightarrow$ Provider $\rightarrow$ Model）与通用的证据账本数据结构，但**独立的通用平台 Adapter 接口目前尚未实现**。未来将在保持单平台稳定性的前提下，审慎探索接入其他公开免费 AI 端点可用性数据源的可行性。

### 2. 开发者数据消费接口 (Developer Data Feeds)
- **目标**：探索导出标准化、结构稳定的静态 JSON / Catalog Feeds。
- **现状说明**：方便第三方开源 AI 客户端、模型聚合平台或监控面板直接订阅或消费由证据链背书的模型状态与规格数据。
