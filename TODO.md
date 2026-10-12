# OpenAR Extension Hub — Agent Y 工作台（TODO 与里程碑）

本文件只在本仓库的 `todo` 分支维护，**永不合入 `main`**（`main` 是对外发布内容，必须干净）。
派工与验收由 OpenRA Review 负责；OpenRA 主仓库的 `TODO.md` 只记录 Y 的一行状态与交接 SHA。

规格（以 OpenRA 主仓为准，勿复制）：`docs/skill-extension-hub-design.md`（§3 能力与界面两维、§5 Registry、§6 最小契约）、`docs/skill-extension-hub-todo.md`（HUB-00…10）、`docs/hub-00-reuse-map.md`、`docs/extension-foundation-v2.md`（ExtensionDefinition 契约，G 维护）。

## 0. 角色与边界

- **Y 负责本仓库的全部内容**：目录、扩展条目、schema、生成的 `extensions.json`、校验脚本、CI、贡献说明、播种与发布。
- **不负责**：OpenRA 侧 ExtensionDefinition/binding/Hub UI（G+D）、registry 客户端/安装/回滚（C）、执行隔离/权限（A）、Skill（X 的 `OpenAR-skill-hub`）。
- **协作**：
  - 条目里的扩展 manifest 必须符合 G 维护的 ExtensionDefinition 契约（`src/local/extension_manifest.rs`），**不另造格式**；契约有缺口时向 G 提，不在本仓自行扩字段。
  - 与 X 共用「条目公共核心字段」（id/kind/name/summary/source/version/license/review/compat），字段名与语义两仓一致。
  - 各功能 owner（H Craft、I Discover/Survey、K Notes、G Calendar/Deadlines 等）提供自己扩展的事实与包，在本仓推 `agent-<x>/<topic>`，Y 审内容，Review 合入 `main`。
- **分支与合入**：只推 `agent-y/<topic>`；**不直接推 `main`**；Review 审查后合入。
- **main 只放发布内容**；TODO、回执、证据只在 OpenRA 主仓。
- **安全**：不提交凭据；manifest 只引用 connection/credential 的 id，不含 token；CI 只读、无 secrets、不执行 PR 中脚本；不收第三方整库源码。

## 1. 当前事实（2026-10-12）

- 本仓库目前只有一个分支 `agent-k/notes-bundled-facts`（K 的证据交接，**HOLD**：证据不进 hub）。因仓库曾为空，GitHub 暂把它当默认分支；`main` 建立后由用户把默认分支设为 `main`，该分支由 Review 归档删除。
- OpenRA 已适配并随 App 编译的扩展（`delivery: bundled`，代码随 App 更新，不可单独安装）：`openra.calendar`、`openra.deadlines`、`openra.scratchpad`（Notes）、`openra.craft-suite`、`openra.daily-picks`、`openra.survey`、`openra.paper-reviewer`。`openra.skill-hub` 是宿主内置管理入口，**不作为条目**。`openra.tool` 是 E18 用户自带工具样例（可作为"独立包"示例的来源）。
- HUB-M1 的 MCP 测试对象：OpenRA `scripts/acceptance-mcp.sh` 的 stdio echo 本地 server（无自定义 UI 的工具集成）。
- C 的 registry 客户端（HUB-01）尚未实现；它将按 commit SHA 读取本仓 `extensions.json` 并逐条校验 sha256。

## 2. 里程碑

| 里程碑 | 内容 | 通过条件 |
| --- | --- | --- |
| **SY-M0 骨架** | 目录、schema、索引生成与校验、CI、README/LICENSE、贡献说明 | Review 合入成为 `main`；校验本地与 CI 都过 |
| **SY-M1 首批条目（HUB-M1 的 extension 半）** | 一个本地 MCP 集成（stdio echo）可安装；7 个 bundled 扩展只读登记 | C 的客户端固定 SHA 读到并校验；OpenRA 安装该 MCP、在项目中调用、结果可 @、升级、回滚（C/A/G 验收）；bundled 条目在 Hub 显示"随 App 更新" |
| **SY-M2 可适配可贡献（HUB-M2）** | 一个已适配原生扩展的三栏条目（calendar）完整元数据；Craft Suite 组件分列；社区/私有来源说明 | 外部贡献样例从 PR 到合入走通；bundled 与独立包差异在条目与 Hub 中清楚 |
| **SY-M3 第三方富 UI（HUB-M3，后置）** | MCP Apps / 沙箱 UI 条目格式 | 先等 OpenRA 侧隔离与消息桥评审通过，再开放条目 |

## 3. 任务

### SY-00 骨架（NOW）
- [ ] 目录：
  ```
  README.md
  LICENSE                          # 仓库元数据与脚本：MIT；条目各按上游许可
  extensions.json                  # 由 scripts 生成，禁止手改
  entries/extensions/<id>/entry.json
  schemas/extension-entry.schema.json
  scripts/build-index.(py|mjs) scripts/validate.(py|mjs)
  .github/workflows/validate.yml
  CONTRIBUTING.md
  ```
- [ ] `entry.json`：公共核心（与 X 相同字段名/语义：`schemaVersion`=1、`id` 命名空间、`kind`="extension"、`name` 一个简短英文名、`summary`+5 语言 i18n、`source`{repo,path,revision=40 位 SHA}、`version`、`license`、`review`、`compat`{minHost,hostApi,platforms}）+ extension 专属：
  - `delivery`: `bundled` | `package`（已支持格式的固定发行包）| `mcp-local` | `mcp-remote` | `cli`
  - `integration`: `L0`（agent 可调用，无页面）| `L1`（宿主通用表单/列表/详情）| `L2`（OpenRA UI 契约：中间页+右栏）| `L3`（MCP Apps 沙箱 UI，后置）——**宿主按实际声明+已登记 binding 判定，条目不能自称更高层级**
  - `capabilities` 与 `uiContributions` 分开列；`bindings[]`（builtin/skill/cli/mcp，只声明）；`auth`{需要的 connection 类型，不含任何凭据}；`artifacts`（产出类型）；`dependencies`（显式、有界，不做通用求解）
  - `package`/`mcp-local`/`cli`：`assets[]`{platform,url,sha256,bytes}；`mcp-remote`：endpoint、认证需求、**观测到的**能力及观测时间（不声称远端不可变）
- [ ] `extensions.json` 投影 + validate（与 X 相同规则：一致性、唯一 id、无未知字段、哈希、路径安全、大小上限）。
- [ ] CI 同 X：只读、无 secrets、不执行 PR 代码，action 固定到 SHA。
- 交付：分支 `agent-y/skeleton` → Review 合入成为 `main`。

### SY-01 首批条目（NEXT）
- [ ] `openra.mcp-echo`（`delivery: mcp-local`，`integration: L0`）：来源为 OpenRA `scripts/acceptance-mcp.sh` 的 echo fixture，固定 OpenRA revision；这是 HUB-M1 的端到端测试对象。
- [ ] 7 个 bundled 条目：calendar、deadlines、scratchpad(Notes)、craft-suite、daily-picks、survey、paper-reviewer——`delivery: bundled`，`integration` 按 OpenRA 实际实现填写（向各 owner 核实，不猜），`compat.minHost` = 首个包含它的 OpenRA 版本；不提供安装资产。
- [ ] K 的 `agent-k/notes-bundled-facts` 只作为 scratchpad 条目的事实参考，证据本身不进本仓。
- 交付：`agent-y/seed-mcp-echo`、`agent-y/seed-bundled`（每分支 ≤4 条）。

### SY-02 原生适配与贡献（LATER）
- [ ] calendar 作为 HUB-M2 的三栏样例补全 `uiContributions`（与 G/D 核对）。
- [ ] Craft Suite：一个 Suite 条目引用各组件（Photo/Vector/Deck/Print…），组件独立版本/平台；安装 Suite 不安装全部组件（与 H 核对）。
- [ ] CONTRIBUTING：开发者自托管源码/发行包，向本仓提交元数据 PR；外部 MCP 可从官方 MCP Registry 只读导入元数据（须固定 revision 并实测能力）。
- [ ] 弃用/高风险/下架流程同 X。

## 4. 验收与回报
- 每个分支：validate 输出、条目数、是否改 schema（改则写 schemaVersion 与对 C/X/G 的影响）。
- 回报写在 OpenRA 主仓 TODO 的 Y 行（分支@SHA + 一句结论）；本仓 main 不写回执。
- 规模：每分支新增手写文件 ≤5、修改 ≤10，每分支 ≤4 个新条目。

## 5. OpenRA 主仓上的底座工作（用户 10-12：X/Y 在 OpenRA 分支写入底座以无缝集成）

- 在 OpenRA 只推 `agent-y/<topic>` 分支；Review 审查，Rust 改动进 Mac 门禁 train 后合入。派工以 OpenRA `TODO.md` 的 Y 行为准。
- **HUB-05 条目 → ExtensionDefinition 安装/binding（Y 负责）**：
  - [ ] 使用 X 的 HUB-01 registry 客户端读条目（不另写客户端）；把 `package`/`mcp-local`/`cli` 条目映射为 G 的 ExtensionDefinition + 已登记 binding，经 C 的 `acquire::extension`/`market` + ChangeSet 安装（改 `acquire/*`、`changesets.rs` 需 C 共审）。
  - [ ] `bundled` 条目只做启用/配置映射，不下载；`mcp-remote` 只登记连接，不伪装已安装。
  - [ ] MCP/CLI 使用已有 adapter 实测 transport 与 tools，纯浏览不启动不可信服务；通用工具表单复用 G 已合的 MCP generic tools 宿主表单。
  - [ ] 测试：`openra.mcp-echo` 从目录→批准→固定安装→项目内调用→结果可 @→升级→回滚；目录离线时已装能力可用。
- 不碰：契约定义与 Hub UI（G+D）、registry 客户端（X）、安装内核（C）。

## 6. HUB-11 Community, Credits & Discovery（后续里程碑 SY-M4；规格 OpenRA `docs/hub-community-discovery.md`）

**SY-00 起就预留署名字段**：entry.json 公共核心与 X 仓同名同义——`authors[]`{name,github}、`maintainers[]`、`contributors[]`、`adapters[]`、`registrySubmitter`、`categories[]`。社区数据（creators/featured/collections/discovery）**只在 X 仓 `community/`**，本仓不复制。
- **SY-M4（HUB-M1 通过后）— OpenRA 侧展示（`agent-y/hub-community-ui`）**
  - [ ] 在 **G 的 Hub 页容器**内实现：条目详情的作者/维护者/贡献者/适配者区（可跳 GitHub）、按作者查看其公开条目、首页 Featured / New / Recently Updated / Trending（Trending 标注数据来源与窗口）、Collections 浏览。G 审契约，D 审布局。
  - [ ] 反馈与贡献按钮：View Source / Report Issue / Suggest Improvement / Contribute——打开对应 GitHub Issue/Discussion/PR 模板，由用户确认后提交，agent 不代发；OpenRA 不存评论。
  - [ ] Community 收录、Featured、Verified 分开显示；精选 ≠ 安全审计；合集变更不自动安装或启用。
  - [ ] 离线用缓存目录；趋势数据缺失/失败不影响安装与使用。
