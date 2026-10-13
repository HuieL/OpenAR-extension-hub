# OpenAR Extension Hub — Agent Y 工作台（TODO 与里程碑）

本文件只在本仓库的 `todo` 分支维护，**永不合入 `main`**（`main` 是对外发布内容，必须干净）。
派工与验收由 OpenRA Review 负责；OpenRA 主仓库的 `TODO.md` 只记录 Y 的一行状态与交接 SHA。

规格（以 OpenRA 主仓为准，勿复制）：`docs/skill-extension-hub-design.md`（§3 能力与界面两维、§5 Registry、§6 最小契约）、`docs/skill-extension-hub-todo.md`（HUB-00…10）、`docs/hub-00-reuse-map.md`、`docs/extension-foundation-v2.md`（ExtensionDefinition 契约，G 维护）。

## 0. 角色与边界

- **Y 负责本仓库的全部内容**：目录、扩展条目、schema、生成的 `extensions.json`、校验脚本、CI、贡献说明、播种与发布。
- **不负责**：OpenRA 侧 ExtensionDefinition/binding/Hub UI（G+D）、registry 客户端/安装/回滚（C）、执行隔离/权限（A）、Skill（X 的 `OpenAR-skill-hub`）。
- **协作**：
  - 条目里的扩展 manifest 必须符合 G 维护的 ExtensionDefinition 契约，**不另造格式**；契约有缺口时向 G 提，不在本仓自行扩字段。
  - 与 X 共用「条目公共核心字段」（id/kind/name/summary/source/version/license/review/compat），字段名与语义两仓一致。
  - 各功能 owner（H Craft、I Discover/Survey、K Notes、G Calendar/Deadlines 等）提供自己扩展的事实与包，在本仓推 `agent-<x>/<topic>`，Y 审内容，Review 合入 `main`。
- **分支与合入**：只推 `agent-y/<topic>`；**不直接推 `main`**；Review 审查后合入。
- **main 只放发布内容**；TODO、回执、证据只在 OpenRA 主仓。
- **安全**：不提交凭据；manifest 只引用 connection/credential 的 id，不含 token；CI 只读、无 secrets、不执行 PR 中脚本；不收第三方整库源码。

## 1. 当前事实（2026-10-12）

- `main` 已建立（f78bcf7：README+MIT LICENSE，2026-10-12 推送）；GitHub 默认分支已由用户设为 `main`（2026-10-12 确认）。
- **用户裁定 2026-10-12：内置 extension 不上 hub**（与 skill-hub 同步）。随 App 编译的扩展留在 OpenRA（其目录从 `builtin:*` 显示），本仓不列 bundled 条目；`delivery` 枚举删 `bundled`（`agent-y/drop-bundled`）。原计划的 7 个 bundled 条目（calendar、deadlines、scratchpad、craft-suite、daily-picks、survey、paper-reviewer）全部取消。
- HUB-M1 的 MCP 测试对象：`hub.mcp-echo`（OpenRA 验收用 stdio echo 本地 MCP server 的公开版本；原草案名 `openra.mcp-echo` 不可用——`openra.*` 保留给内置且被运行时 user-definition 解析拒绝）。
- X 的 registry 客户端（HUB-01，`hub-refresh`）已 ACCEPT→train-15；它按 commit SHA 读取本仓 `extensions.json` 并逐条校验 sha256。

## 2. 里程碑

| 里程碑 | 内容 | 通过条件 |
| --- | --- | --- |
| **SY-M0 骨架** | 目录、schema、索引生成与校验、CI、README/LICENSE、贡献说明 | Review 合入成为 `main`；校验本地与 CI 都过 |
| **SY-M1 首批条目（HUB-M1 的 extension 半）** | 一个本地 MCP 集成（stdio echo）可安装 | C 的客户端固定 SHA 读到并校验；OpenRA 安装该 MCP、在项目中调用、结果可 @、升级、回滚（C/A/G 验收） |
| **SY-M2 可适配可贡献（HUB-M2）** | 一个 L2 三栏条目完整元数据（由首个第三方适配承担）；Craft Suite 组件分列；社区/私有来源说明 | 外部贡献样例从 PR 到合入走通；hub 托管与上游固定条目的差异在条目与 Hub 中清楚 |
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
- 回执（2026-10-12，`agent-y/skeleton@550264e`，基 `main@f78bcf7`）：6 个新文件——`schemas/extension-entry.schema.json`（draft-07，镜像 OpenRA 公共条目契约（docs/public-contract.md））、`scripts/build_index.py`（生成 extensions.json，`--check` 供 CI）、`scripts/validate.py`（与 Rust 校验同规则：字节长度上限、命名空间 id 段规则、40/64 位小写 hex、路径安全、delivery⇔assets/mcp 一致性、索引新鲜度）、`.github/workflows/validate.yml`（只读、checkout 固定 SHA、无 secrets）、`CONTRIBUTING.md`、空 `extensions.json`。本地验证：`build_index.py`/`validate.py`/`--check` 全过；负例演练（http repo + `..` 路径 + 分支 revision + package 缺 assets）被正确拒绝；正例演练（合法 bundled 条目）通过后已移除。未改 schema 之外任何契约；勾选由 Review 依据本回执执行。

### SY-01 首批条目（NOW）
- [ ] `hub.mcp-echo`（`delivery: mcp-local`，`integration: L0`）：OpenRA 验收用 echo fixture 的公开版本（只放 manifest 与公开资产，不复制 OpenRA 源码）；HUB-M1 的端到端测试对象。
- ~~7 个 bundled 条目~~：用户裁定 2026-10-12 取消（内置 extension 不上 hub）；`agent-k/notes-bundled-facts` 证据分支不再需要。
- 交付：`agent-y/seed-mcp-echo`、`agent-y/drop-bundled`。
- 回执（2026-10-12）：①`agent-y/drop-bundled@a0d4421`（基 `main@6ed1ba7`，4 文件）：schema/validator/CONTRIBUTING 删 `bundled` delivery，selftest 该例改为拒绝检查，`openra.*` 不再作 id 示例；validate/build-index --check/26 负例全过。②`agent-y/seed-mcp-echo@e1bf81d`（2 commits：包 `3fe5d5d` + 条目 `e1bf81d`）：`entries/extensions/hub.mcp-echo/package/`（extension.json manifest、server/echo.py 带 shebang+exec bit、MIT LICENSE、zip 资产 2652 B sha256 5be23d8a…）+ entry.json；资产 URL 为固定 revision 的 raw.githubusercontent 直链（运行时下载器拒绝重定向，GitHub release 302 不可用），已实测 200 直达、哈希相符；echo server 本地握手实测（initialize/tools list/echo/boom/unknown tool）；schema digest 与验收 fixture 一致（54669b5e…/d95b00b2…）；id 由 `openra.mcp-echo` 改名 `hub.mcp-echo`。validate/build-index --check/26 负例全过；勾选由 Review 依据本回执执行。

### SY-02 原生适配与贡献（LATER）
- [ ] ~~calendar 作为 HUB-M2 的三栏样例~~（用户裁定取消：内置不上 hub）；三栏样例由首个 L2 第三方适配条目承担（与 G/D 核对）。
- [ ] Craft Suite：一个 Suite 条目引用各组件（Photo/Vector/Deck/Print…），组件独立版本/平台；安装 Suite 不安装全部组件（与 H 核对）。
- [ ] CONTRIBUTING：开发者自托管源码/发行包，向本仓提交元数据 PR；外部 MCP 可从官方 MCP Registry 只读导入元数据（须固定 revision 并实测能力）。
  - 回执（2026-10-13，`agent-y/context7-remote@354514c`，基 `main@b556e7e`，2 文件）：CONTRIBUTING 新增 "Remote MCP services" 节（observed=实活探测非承诺；元数据可只读导入官方 MCP Registry/上游仓，观测必须来自本 hub 自己的探测；source 仍固定 40-hex revision；观测漂移→更新或弃用，绝不静默改写）+ 首个真实第三方 `mcp-remote` 条目 `upstash.context7`（MIT、上游仓可钉、无鉴权；2026-10-13 实测握手：server 4.3.0、tools [resolve-library-id, query-docs]、resources []、含一次真实 tools/call）。validate/build-index --check/38 负例全过；勾选由 Review 依据本回执执行。
- [ ] 弃用/高风险/下架流程同 X。

## 4. 验收与回报
- 每个分支：validate 输出、条目数、是否改 schema（改则写 schemaVersion 与对 C/X/G 的影响）。
- 回报写在 OpenRA 主仓 TODO 的 Y 行（分支@SHA + 一句结论）；本仓 main 不写回执。
- 规模：每分支新增手写文件 ≤5、修改 ≤10，每分支 ≤4 个新条目。

## 5. OpenRA 主仓上的底座工作（用户 10-12：X/Y 在 OpenRA 分支写入底座以无缝集成）

- 在 OpenRA 只推 `agent-y/<topic>` 分支；Review 审查，Rust 改动进 Mac 门禁 train 后合入。派工以 OpenRA `TODO.md` 的 Y 行为准。
- **HUB-05 条目 → ExtensionDefinition 安装/binding（Y 负责）**：
  - [ ] 使用 X 的 HUB-01 registry 客户端读条目（不另写客户端）；把 `package`/`mcp-local`/`cli` 条目映射为 G 的 ExtensionDefinition + 已登记 binding，经 C 的 OpenRA 安装内核 + ChangeSet 安装（改 OpenRA 安装内核需 C 共审）。
  - [ ] `mcp-remote` 只登记连接，不伪装已安装（bundled 已随用户裁定移除）。
  - [ ] MCP/CLI 使用已有 adapter 实测 transport 与 tools，纯浏览不启动不可信服务；通用工具表单复用 G 已合的 MCP generic tools 宿主表单。
  - [ ] 测试：`hub.mcp-echo` 从目录→批准→固定安装→项目内调用→结果可 @→升级→回滚；目录离线时已装能力可用。
- 不碰：契约定义与 Hub UI（G+D）、registry 客户端（X）、安装内核（C）。

## 6. HUB-11 Community, Credits & Discovery（后续里程碑 SY-M4；规格 OpenRA `docs/hub-community-discovery.md`）

**SY-00 起就预留署名字段**：entry.json 公共核心与 X 仓同名同义——`authors[]`{name,github}、`maintainers[]`、`contributors[]`、`adapters[]`、`registrySubmitter`、`categories[]`。社区数据（creators/featured/collections/discovery）**只在 X 仓 `community/`**，本仓不复制。
- **SY-M4（HUB-M1 通过后）— OpenRA 侧展示（`agent-y/hub-community-ui`）**
  - [ ] 在 **G 的 Hub 页容器**内实现：条目详情的作者/维护者/贡献者/适配者区（可跳 GitHub）、按作者查看其公开条目、首页 Featured / New / Recently Updated / Trending（Trending 标注数据来源与窗口）、Collections 浏览。G 审契约，D 审布局。
  - [ ] 反馈与贡献按钮：View Source / Report Issue / Suggest Improvement / Contribute——打开对应 GitHub Issue/Discussion/PR 模板，由用户确认后提交，agent 不代发；OpenRA 不存评论。
  - [ ] Community 收录、Featured、Verified 分开显示；精选 ≠ 安全审计；合集变更不自动安装或启用。
  - [ ] 离线用缓存目录；趋势数据缺失/失败不影响安装与使用。


## 7. Public Release Gate（用户 10-12，硬规则）

- 本仓库**只放 OpenRA Public Contract 之上的可下载/适配资产**（条目元数据、schema、第三方或社区 skill/扩展的公开内容与发行包索引、校验脚本、CI）。**不得包含 OpenRA 核心逻辑**：不复制 OpenRA 源码、内部模块路径、内部 HTTP 路由、宿主 token 名、未公开的数据结构。
- 条目与 schema 只能引用 OpenRA `docs/public-contract.md` 中列出的稳定字段与接口（由 G+A 维护，尽量小）；需要新接口时向 OpenRA 提最小公共契约变更，不在本仓自定义宿主行为。
- 每个合入 main 的分支都要过 Review 的 Public Release Gate：路径白名单、与 OpenRA 源文件逐字节比对、内部标识/密钥扫描、无符号链接/大文件、CI 只读且 action 固定 SHA、无 `pull_request_target`。不通过不合入。
- 本 `todo` 分支同样公开可见：不要写 OpenRA 内部文件路径或实现细节，只引用公共文档名。
