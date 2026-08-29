## 📋 PR 概述 (Pull Request Overview)

- **变更类型 (Type of Change)**:
  - [ ] 🐛 缺陷修复 (Bug Fix)
  - [ ] 📋 模型元数据补全/修正 (Model Metadata Update)
  - [ ] ✨ 新特性/功能增强 (Feature / Enhancement)
  - [ ] 📚 文档完善 (Documentation)
  - [ ] 🧪 测试用例补充 (Testing)
  - [ ] 🧹 代码重构与整理 (Refactoring / Chore)

- **解决的问题 / 变更目的 (Motivation & Context)**:
  <!-- 简要说明本 PR 解决了什么问题，或实现了什么具体功能 -->

---

## 🛠️ 修改范围与影响 (Scope & Impact)

- **涉及的主要模块**:
  <!-- 例如：src/catalog/build_parser.py, worker/src/resolver.ts, data/model_catalog.json 等 -->
- **向后兼容性 (Backward Compatibility)**:
  - [ ] 完全向后兼容 (No Breaking Changes)
  - [ ] 存在不兼容变更（请在下方详细说明）

---

## 🧪 测试与验证结果 (Testing & Verification)

- **本地测试执行状态**:
  ```bash
  # Python 全量测试 (当前基准: 278 项)
  python -m unittest discover -s tests -v

  # Worker 全量测试 (当前基准: 47 项)
  npm --prefix worker test
  ```
- **测试结果简述**:
  <!-- 例如：本地 325 项单测 100% 通过，并针对新增逻辑补充了对应单元测试用例 -->

---

## 🛡️ 贡献规范核验清单 (Contributor Checklist)

在提交 PR 之前，请核对并勾选以下事项（遵循 [CONTRIBUTING.md](https://github.com/inintinto/nvidia-free-monitor/blob/main/CONTRIBUTING.md)）：

- [ ] **全量测试通过**：本地运行 Python (278) 与 Worker (47) 测试均 100% 通过。
- [ ] **Python 零外部依赖**：`src/` 核心代码严格仅依赖 Python 标准库，未引入任何第三方 pip 包。
- [ ] **Ground Truth 准则**：若修改了 `data/model_catalog.json`，所有技术参数均有官方一手 Build 页面或文档背书，无任何主观猜测数值。
- [ ] **零凭据准则 (Zero Secrets)**：确认未将任何真实 Bot Token、API Key、密码或私有配置提交至 Git，日志无明文凭据泄漏。
- [ ] **变更聚焦**：无无关代码格式化或大规模无关重构，保持最小范围修改。
