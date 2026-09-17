# 石刻造像题记知识图谱

基于四川地区佛教石窟造像题记（992 条）构建的知识图谱系统：**Python 数据管线 + Neo4j 图数据库 + MySQL + D3.js 3D 可视化**。

- 数据基准：`5.21实体.xlsx`（25 列：题记名称、时间、地点、造像者身份/阶层/性别、宗派倾向、宗教类型、实践行为/祈愿内容/造像原因编码等）
- 编码规范：见 `标注规范/rules/`（祈愿内容 v3.0 含"四恩三有"、妆造类型 v1.1、阶层划分、宗派判定等 8 份规则）
- 所有脚本路径均为仓库相对路径，克隆到任意目录即可运行

## 仓库结构

```
├── 5.21实体.xlsx / .csv      # 当前数据基准（旧基准 5.7实体.xlsx 仅存档）
├── data/
│   ├── cleaned/              # 清洗产物：inscriptions_clean.csv(41列)、核验报告、diff 记录
│   ├── config/               # normalization_rules.json(归一化规则)、db_local.example.json(凭据模板)
│   └── export/               # neo4j.dump、JoinMap 导出 JS
├── scripts/                  # 全部管线脚本（见下文）
├── dashboard/                # D3.js 3D 可视化（纯静态，无需构建）
├── 标注规范/                  # 数据标注规则文档
└── requirements.txt
```

## 快速开始

### 0. 环境准备

- Python ≥ 3.10，安装依赖：`pip install -r requirements.txt`
- 可选：Neo4j 5.x（Desktop 或 Server）、MySQL 8.x

### 1. 数据清洗（必跑）

```bash
python scripts/01_extract_and_clean.py
```

读取根目录 `5.21实体.xlsx` → 输出 `data/cleaned/inscriptions_clean.csv`（25 原始列 + 16 归一化列）。
归一化列包括：`region_short`、`period`、`class_*`、`sect_main/sect_all`、`subject`、`religion_type`、
`vow_main/vow_detail/vow_l2_norm`（祈愿编码 v3.0，含四恩三有）、`makeup_normalized`（妆造 v1.1）。
内置"妆造-实践矛盾校验"，疑似矛盾清单输出到 `data/cleaned/makeup_practice_contradictions.txt` 供人工复核。

### 2. 生成可视化数据

```bash
python scripts/02_generate_graph_json.py
```

输出 `dashboard/data/graph_data.json`（题记节点 + 地区/朝代/阶层/宗派/宗教/题材/祈愿/妆造八类枢纽 + 关系边）。

### 3. 打开可视化

```bash
cd dashboard && python -m http.server 8080
# 浏览器访问 http://localhost:8080
```

3D 立体散点图：X 轴=朝代分期（隋→南宋）、Y 轴=社会阶层、Z 轴=地理辐射距离（以成都为原点）；
节点内色=宗派、大小=组织单位（个人/家庭/社邑/群体）。支持：宗派多选筛选、年份双滑条、
时期/地区/阶层/祈愿组合搜索定位、点击详情面板（含祈愿编码、妆造归一化）、交叉统计。

## Neo4j 同步（可选）

脚本通过 HTTP API 直连本机 Neo4j（`127.0.0.1:7474`）。密码两种提供方式任选：

```bash
# 方式一：环境变量
export NEO4J_PASSWORD='你的密码'        # Windows PowerShell: $env:NEO4J_PASSWORD='你的密码'
# 方式二：本地配置文件（不会提交到 git）
cp data/config/db_local.example.json data/config/db_local.json
# 编辑 db_local.json 填入 password
```

同步脚本（均支持 `--dry-run` 预览）：

```bash
python scripts/05_update_vows_neo4j.py    # 祈愿层级枢纽（祈愿内容一/二/三级）
python scripts/06_sync_codes_neo4j.py     # 妆造(v1.1) + 实践行为/造像原因编码枢纽
python scripts/08_verify_rules_neo4j.py   # 全量核验：节点 vs 标注规范词表
```

图采用中文标签/关系（`题记`、`祈愿内容一级`、`位于`、`下级编码` 等，映射表
`data/config/neo4j_labels_zh.json`；新库首次中文化运行 `python scripts/07_rename_chinese_neo4j.py`）。
可视化样式：把 `scripts/neo4j_browser_style.grass` 内容粘贴到 Neo4j Browser 的 `:style` 编辑器。

**全新数据库**：将 `data/cleaned/inscriptions_clean.csv` 复制到 Neo4j 实例的 `import` 目录
（Neo4j Desktop：DBMS → Open Folder → Import），在 Browser 依次执行
`scripts/import_to_neo4j.cypher` → 上述 05/06 脚本；常用查询见 `scripts/query_aggregate.cypher`（Q1-Q14）。

当前核验状态：一级维度 13/13、实践二级 30/30、造像原因二级 26/26 全部合规，无孤儿节点
（报告：`data/cleaned/neo4j_rules_audit.txt`）。

## MySQL 导入（可选）

```bash
mysql -u root -p < scripts/schema.sql        # 建库建表（11 张表 + 宽表视图）
python scripts/export_to_mysql.py            # 从清洗 CSV 导入（连接信息在脚本头部 DB_CONFIG 修改）
```

`inscriptions` 主表含 `prayer_code_l1/l2`（祈愿编码）、`makeup_normalized`（妆造归一化）等字段；
视图 `v_inscriptions_full` 输出与 CSV 一致的宽表。

## 编码规范与归一化规则

| 维度 | 规则文件 | 版本 |
|------|---------|------|
| 祈愿内容 | `标注规范/rules/祈愿内容判定规则.md`（附录含旧词→v3.0 映射表） | v3.0（含四恩三有） |
| 妆造类型 | `标注规范/rules/妆造类型归一化规则.md`（仅"镌妆"归"新造兼妆修"） | v1.1 |
| 实践行为 / 造像原因 | 对应规则文件（附录A/B 为数据在用扩展词表） | — |
| 阶层 / 宗派 / 社邑 / 题记名称 | 对应规则文件 | — |

归一化配置集中在 `data/config/normalization_rules.json`（地区/朝代/宗派/题材映射、祈愿 L2 映射表、
扩展词表），改配置后重跑 01/02 即可生效。

## 数据变更流程

修改 `5.21实体.xlsx`（或换成新基准文件，同步改 `scripts/01_extract_and_clean.py` 的 `EXCEL_PATH`）后：

```bash
python scripts/01_extract_and_clean.py      # 清洗
python scripts/02_generate_graph_json.py    # D3 数据
python scripts/05_update_vows_neo4j.py      # Neo4j 祈愿层
python scripts/06_sync_codes_neo4j.py       # Neo4j 其余编码层 + 妆造
python scripts/08_verify_rules_neo4j.py     # 核验
```

辅助工具：`scripts/diff_521_vs_57.py`（新旧基准逐列 diff）、`scripts/validate_outputs.py` /
`check_data_quality.py`（产物自检）、`scripts/extract_rule_vocab.py`（从规则文档提取词表，供 08 使用）。

## 约定

- 原始 Excel 数据只读不写；所有归一化列以新列附加，原始列完整保留
- 缺失信息标记为"不详"或"未知"
- 数据库凭据不入库：`data/config/db_local.json` 已被 `.gitignore` 忽略，只提交 example 模板
