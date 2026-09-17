# 石刻造像题记知识图谱（Neo4j）

基于四川地区佛教石窟造像题记（992 条）构建的**知识图谱**：核心是 Neo4j 图数据库
（1521 节点 / 12549 关系，全中文标签），配 Python 数据管线、MySQL 镜像与 D3.js 辅助可视化。

## 数据库介绍

**数据来源**：四川地区（大足、安岳、广元、巴中、成都等 11 地）石窟造像题记 992 条，
时间跨度隋（581）至南宋（1279），每条含 25 个原始字段（题记名称、公元纪年、地点、窟位、
造像者身份/阶层/性别、出资者、所造佛像、宗派倾向、宗教类型、实践行为/祈愿内容/造像原因
三级编码、关联历史事件、经文、妆造类型等）。

**建模方式**：中心辐射（hub-and-spoke）+ 编码层级两类枢纽挂在 `题记` 实体上——

- 基础维度枢纽：每条题记经中文关系（`位于`、`所属朝代`、`阶层`、`所属宗派`、`造像题材`、
  `宗教类型`、`性别`、`妆造类型` 等）连到对应维度节点，支持任意维度组合的下钻查询
- 编码层级枢纽：祈愿内容 / 实践行为 / 造像原因各建一~三级树（`下级编码` 相连），
  最细层级连到题记（如 `祈愿内容一级(修行证悟) → 二级(普度众生) → 三级(上报四恩) → 题记#777`）

**题记节点属性**：除原始字段（`raw_*` 系列）外，含可直接检索的归一化属性 `period`、
`year_start`、`region`、`class_type`、`sect`、`subject`、`prayer_l1/l2`（祈愿编码）、
`makeup_normalized`（妆造归一化）等；`id`/`subject`/`prayer_l1` 建有索引。

**质量核验**：`scripts/08_verify_rules_neo4j.py` 对照《标注规范》词表全量核验——
一级维度 13/13、实践行为二级 30/30、造像原因二级 26/26 合规，无孤儿节点
（报告：`data/cleaned/neo4j_rules_audit.txt`）。

- 数据基准：`5.21实体.xlsx`（25 列原始数据）
- 编码规范：`标注规范/rules/`（祈愿内容 v3.0 含"四恩三有"、妆造类型 v1.1 等 8 份规则）

## 图结构总览

| 层 | 节点（标签） | 关系（类型） |
|----|-------------|-------------|
| 实体 | `题记` ×992 | — |
| 基础维度枢纽 | `地区`×11、`朝代分期`×10、`阶层标签`×48、`阶层类型`×7、`组织单位`×5、`宗派`×6、`造像题材`×11、`宗教类型`×5、`性别`×3、`妆造类型`×5 | `位于`、`所属朝代`、`阶层`、`阶层类型`、`组织单位`、`所属宗派`、`造像题材`、`宗教类型`、`性别`、`妆造类型` |
| 编码层级枢纽 | `祈愿内容一级/二级/三级`（5/17/304）、`实践行为一级/二级`（8/30）、`造像原因一级/二级/三级`（7/26/21） | 层级间 `下级编码`；最细层级经 `祈愿内容`/`实践行为`/`造像原因` 连到题记 |

二级编码括号内为三级细目（如"普度众生(上报四恩)"）；`题记` 节点上还有 `prayer_l1/l2`、
`vow_main/vow_detail`、`makeup_normalized` 等属性可直接查询。

## 快速开始：把图装进你的 Neo4j

### 第 0 步：安装 Neo4j（三选一，任一 5.x 均可）

**方式 A：Neo4j Desktop（Windows / macOS 推荐）**

1. 到 [neo4j.com/download](https://neo4j.com/download/) 下载 Neo4j Desktop 并安装（需注册免费账号）
2. 打开后新建本地 DBMS：`New → Local DBMS`，设一个密码（记住它），版本选 5.x → `Create`
3. 点击 `Start` 启动，浏览器打开 `http://localhost:7474`，首次登录用 `neo4j` + 你设的密码

**方式 B：Docker（任何平台）**

```bash
docker run -d --name neo4j-kg -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/你的密码 neo4j:5
# 浏览器打开 http://localhost:7474
```

**方式 C：Linux Server（tar 包）**

```bash
tar -xf neo4j-community-5.*-unix.tar.gz && cd neo4j-community-5.*
bin/neo4j-admin dbms set-initial-password 你的密码     # 首次设密码
bin/neo4j start                                        # 启动；Browser 同上
```

### 第 1 步：复原图

仓库已含全量重建脚本 `data/export/rebuild_full.cypher`（从当前库在线导出并逐项校验无损），
不依赖 Python：

```bash
cypher-shell -a bolt://127.0.0.1:7687 -u neo4j -p <你的密码> \
  -f data/export/rebuild_full.cypher
```

### 第 2 步：配置 Browser 样式

打开 Neo4j Browser（`http://localhost:7474`），把 `scripts/neo4j_browser_style.grass` 内容
粘贴到 `:style` 编辑器——三个编码维度分绿/橙/紫大胶囊、二三级逐级渐小，题记为小灰点。

### 第 3 步：查询

常用查询见 `scripts/query_aggregate.cypher`（Q1-Q14：三维交叉统计、祈愿/妆造分布、
编码层级浏览、四恩三有专项等）。随手试两条：

```cypher
MATCH (w:`祈愿内容一级`) RETURN w.name, size((w)-[:`下级编码`*1..2]->()) AS 子类数;
MATCH (i:`题记`) WHERE i.vow_detail CONTAINS '四恩' RETURN i.id, i.name, i.vow_detail;
```

不想装数据库？可直接读 `data/cleaned/inscriptions_clean.csv`（41 列 = 25 原始 + 16 归一化，
含全部编码）。D3 可视化见文末[辅助可视化](#辅助可视化d3可选)一节。

## 从源数据重建图（维护者）

改了 `5.21实体.xlsx` 数据或 `data/config/normalization_rules.json` 规则后：

```bash
pip install -r requirements.txt                    # Python ≥ 3.10

python scripts/01_extract_and_clean.py             # 清洗 → data/cleaned/inscriptions_clean.csv（41列）
python scripts/02_generate_graph_json.py           # D3 数据（顺带产物）

# Neo4j 同步（HTTP API 直连 127.0.0.1:7474；密码见下方"凭据"）
python scripts/05_update_vows_neo4j.py             # 祈愿层级枢纽
python scripts/06_sync_codes_neo4j.py              # 妆造 + 实践/造像原因编码枢纽
python scripts/08_verify_rules_neo4j.py            # 全量核验 → data/cleaned/neo4j_rules_audit.txt
python scripts/09_export_rebuild_cypher.py         # 重新导出 rebuild_full.cypher（提交入库）
```

以上 05/06/07/09 均支持 `--dry-run`。全新空库可改用 `scripts/import_to_neo4j.cypher`
（LOAD CSV 方式，需把清洗 CSV 放入 Neo4j `import` 目录）+ 05/06；
新库首次中文化运行 `python scripts/07_rename_chinese_neo4j.py`。

### 凭据

数据库密码不入库，二选一：

```bash
export NEO4J_PASSWORD='你的密码'                     # PowerShell: $env:NEO4J_PASSWORD='你的密码'
# 或
cp data/config/db_local.example.json data/config/db_local.json   # 填入 password（已 gitignore）
```

## MySQL 镜像（可选）

```bash
mysql -u root -p < scripts/schema.sql              # 11 张表 + 宽表视图 v_inscriptions_full
python scripts/export_to_mysql.py                  # 连接信息在脚本头部 DB_CONFIG 修改
```

## 辅助可视化：D3（可选，可自由扩展）

仓库自带一个基于 **D3.js** 的参考实现（3D 散点图：X=朝代、Y=阶层、Z=地理距离；
支持宗派筛选、年份滑条、祈愿组合搜索、详情面板）：

```bash
python scripts/02_generate_graph_json.py && cd dashboard && python -m http.server 8080
```

**更重要的是**：`dashboard/data/graph_data.json` 是一份与图数据库同构的通用数据源
（992 个题记节点 + 八类属性枢纽 + 关系边，含全部归一化字段），你完全可以**按自己的研究
需要构建多样的可视化视图**，例如：

- 力导向网络图（题记-枢纽全连通，观察编码星座结构）
- 时间轴/河流图（朝代 × 祈愿/妆造/宗派的演变）
- 桑基图（朝代 → 阶层 → 祈愿流向）
- 地理散点（`region` × `year_start` 的时空分布）
- 任意维度的自选下钻面板

`dashboard/js/main.js`（无构建、原生 D3）可作为改写起点；数据字段说明见
`scripts/02_generate_graph_json.py` 头注与 `data/config/normalization_rules.json`。

## 编码规范与归一化

| 维度 | 规则文件 | 版本 |
|------|---------|------|
| 祈愿内容 | `标注规范/rules/祈愿内容判定规则.md`（附录：旧词→v3.0 映射表） | v3.0（含四恩三有） |
| 妆造类型 | `标注规范/rules/妆造类型归一化规则.md`（仅"镌妆"归"新造兼妆修"） | v1.1 |
| 实践行为 / 造像原因 | 对应规则文件（附录A/B 为数据在用扩展词表） | — |

归一化配置集中在 `data/config/normalization_rules.json`（映射规则、扩展词表、颜色）。
辅助工具：`diff_521_vs_57.py`（新旧基准 diff）、`validate_outputs.py` / `check_data_quality.py`（自检）、
`extract_rule_vocab.py`（规则词表提取）。

## 约定

- 原始 Excel 只读不写；归一化一律以新列附加，原始列完整保留；缺失标记"不详/未知"
- 中文标签映射表：`data/config/neo4j_labels_zh.json`
- 凭据不入库：仅提交 `db_local.example.json` 模板
