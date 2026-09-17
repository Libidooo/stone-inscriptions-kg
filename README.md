# 石刻造像题记知识图谱（Neo4j）

基于四川地区佛教石窟造像题记（992 条）构建的**知识图谱**：核心是 Neo4j 图数据库
（1521 节点 / 12549 关系，全中文标签），配 Python 数据管线、MySQL 镜像与 D3.js 辅助可视化。

- 数据基准：`5.21实体.xlsx`（25 列原始数据）
- 编码规范：`标注规范/rules/`（祈愿内容 v3.0 含"四恩三有"、妆造类型 v1.1 等 8 份规则）
- 图已通过全量核验：一级维度 13/13、实践二级 30/30、造像原因二级 26/26 合规，无孤儿节点

## 图结构总览

| 层 | 节点（标签） | 关系（类型） |
|----|-------------|-------------|
| 实体 | `题记` ×992 | — |
| 基础维度枢纽 | `地区`×11、`朝代分期`×10、`阶层标签`×48、`阶层类型`×7、`组织单位`×5、`宗派`×6、`造像题材`×11、`宗教类型`×5、`性别`×3、`妆造类型`×5 | `位于`、`所属朝代`、`阶层`、`阶层类型`、`组织单位`、`所属宗派`、`造像题材`、`宗教类型`、`性别`、`妆造类型` |
| 编码层级枢纽 | `祈愿内容一级/二级/三级`（5/17/304）、`实践行为一级/二级`（8/30）、`造像原因一级/二级/三级`（7/26/21） | 层级间 `下级编码`；最细层级经 `祈愿内容`/`实践行为`/`造像原因` 连到题记 |

二级编码括号内为三级细目（如"普度众生(上报四恩)"）；`题记` 节点上还有 `prayer_l1/l2`、
`vow_main/vow_detail`、`makeup_normalized` 等属性可直接查询。

## 快速开始：把图装进你的 Neo4j

仓库已含全量重建脚本 `data/export/rebuild_full.cypher`（从当前库在线导出并逐项校验无损），
不依赖 Python，适用于任意 Neo4j 5.x：

```bash
# 1. 安装 Neo4j 5.x（Desktop 或 Server 均可），启动后执行：
cypher-shell -a bolt://127.0.0.1:7687 -u neo4j -p <你的密码> \
  -f data/export/rebuild_full.cypher

# 2. 打开 Neo4j Browser (http://localhost:7474)，粘贴 scripts/neo4j_browser_style.grass
#    到 :style 编辑器 —— 三个编码维度分绿/橙/紫胶囊，题记为小灰点

# 3. 跑查询：scripts/query_aggregate.cypher（Q1-Q14：三维统计、祈愿/妆造分布、
#    层级浏览、四恩三有专项等）
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

## 辅助可视化：D3（可选）

```bash
python scripts/02_generate_graph_json.py && cd dashboard && python -m http.server 8080
```

3D 散点图：X=朝代、Y=阶层、Z=地理距离；支持宗派筛选、年份滑条、祈愿组合搜索、详情面板。

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
