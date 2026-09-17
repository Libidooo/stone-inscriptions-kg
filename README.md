# 石刻造像题记知识图谱可视化系统

## 概述

基于四川地区佛教石窟铭文 Excel 数据，构建 Neo4j 图数据库 + D3.js 前端可视化系统。

## 数据源

- `V:/图谱/5.21实体.xlsx`（同目录 `.csv` 为原始导出）— 当前数据基准（992 条题记，25 列）
  - 2026-09 起以 5.21实体 为基准：祈愿内容编码升级为 v3.0 词表（对应《标注规范/rules/祈愿内容判定规则.md》，
    E-03-01-01 普度众生关键词新增"四恩三有"；护国兴邦→国邦安宁、超度荐亡→超度往生、弘法传教→佛法弘传等重标）
- `V:/图谱/5.7实体.xlsx` — 旧基准（存档，只读）
- 包含：实体序号、题记名称、时间、公元纪年、地点、窟位、造像者人数、性别、所造佛像名称、出资者、造像者身份表述、阶层、社邑组织、实践行为编码、祈愿内容编码、造像原因编码、关联历史事件、经文、妆造类型、宗教类型、宗派倾向、备注

## 项目结构

```
V:/图谱/
├── data/
│   ├── cleaned/inscriptions_clean.csv  # 清洗后数据（41列：25原始 + 16归一化，含 vow_main/vow_detail/vow_l2_norm/makeup_normalized）
│   └── config/normalization_rules.json  # 可配置的归一化规则
├── scripts/
│   ├── 01_extract_and_clean.py          # 数据清洗与归一化（读 5.21实体.xlsx，含妆造-实践矛盾校验）
│   ├── 02_generate_graph_json.py        # 生成前端可视化 JSON（含祈愿/妆造枢纽）
│   ├── 05_update_vows_neo4j.py          # 直连 Neo4j 重建祈愿层级（祈愿内容一/二/三级）
│   ├── 06_sync_codes_neo4j.py           # 直连 Neo4j 同步妆造(v1.1)+实践/原因编码枢纽
│   ├── 07_rename_chinese_neo4j.py       # Neo4j 标签/关系中文化（映射表见 data/config/neo4j_labels_zh.json）
│   ├── 08_verify_rules_neo4j.py         # 全量核验：节点 vs 标注规范词表（报告在 data/cleaned/neo4j_rules_audit.txt）
│   ├── import_to_neo4j.cypher           # Neo4j 全量导入脚本 v5.0（中文标签版）
│   └── query_aggregate.cypher           # Cypher 聚合查询 Q1-Q14（中文标签版）
├── dashboard/
│   ├── index.html                       # 可视化主页面
│   ├── js/main.js                       # D3.js 布局与交互（含祈愿筛选/详情）
│   ├── css/style.css                    # 样式
│   └── data/graph_data.json             # 预处理可视化数据（v4.0）
├── README.md
└── requirements.txt
```

## 可视化布局

| 维度 | 映射 |
|------|------|
| **大节点** = 地区 | 半径大小表示该地区题记总数 |
| **X 轴** = 时间 | 隋 → 初唐 → 武周 → 盛唐 → 中唐 → 晚唐 → 五代 → 北宋 → 南宋 |
| **Y 轴** = 社会阶层 | 工匠 → 信众 → 僧侣 → 士人 → 官员 |
| **节点颜色（内圆）** = 宗派 | 观音/净土/弥勒/药师/地藏/密教/禅宗/华严/天台/无法判定 |
| **节点描边（外圈）** = 宗教类型 | 佛教/道教/混合/儒教/无法判定（比宗派更上层的分类） |
| **男左女右** | 同一坐标点，男性向左偏移，女性向右偏移 |

### 交互功能

- **Hover**：显示题记详情（名称、出资者、年代、宗派、阶层、祈愿内容）
- **Click**：右侧详情面板（展示所有字段，含祈愿内容一级/二级编码）
- **宗派筛选**：下拉多选框，只显示选中宗派
- **祈愿筛选**：搜索面板下拉框，按祈愿一级编码（超度往生/现世福报/国邦安宁等）过滤
- **时间滑条**：双值范围滑条，过滤公元纪年
- **图例**：颜色→宗派 + 性别标识

## 运行步骤

> Python：本机 `V:` 盘受 Windows 应用控制策略限制无法运行 venv 内的原生 DLL，
> 请直接使用系统 Python（依赖见 `requirements.txt`）。

### 1. 数据清洗

```bash
python scripts/01_extract_and_clean.py
```
输出: `data/cleaned/inscriptions_clean.csv`（含 `vow_main`/`vow_detail` 祈愿归一化列）

### 2. 生成前端数据

```bash
python scripts/02_generate_graph_json.py
```
输出: `dashboard/data/graph_data.json`（题记节点含 vow/vowDetail，另含祈愿枢纽节点与 HAS_VOW 边）

### 3. Neo4j

方式 A（增量更新已运行的库，推荐）：

```bash
python scripts/05_update_vows_neo4j.py           # 祈愿层级（密码经 NEO4J_PASSWORD 或 data/config/db_local.json 提供）
python scripts/06_sync_codes_neo4j.py            # 妆造(v1.1) + 实践/原因编码枢纽
# 两个脚本均支持 --dry-run 先查看计划
```

方式 B（全量重导）：

1. 将 `data/cleaned/inscriptions_clean.csv` 复制到 Neo4j 的 `import` 目录
   （本机 DBMS: `C:\ndb\Data\dbmss\dbms-03dc6b1b-ac18-4bb5-a870-722846996af6\import\`）
2. 在 Neo4j Browser 中执行 `scripts/import_to_neo4j.cypher`
3. 执行 `scripts/05_update_vows_neo4j.py` 补全祈愿二/三级层级（WishL2/WishL3）
4. 执行 `scripts/query_aggregate.cypher` 进行查询（Q9-Q12 为祈愿内容分析）

### 4. 启动可视化

直接在浏览器打开 `dashboard/index.html`（通过本地 HTTP 服务器，如 `python -m http.server 8080`）

## 归一化规则

所有规则在 `data/config/normalization_rules.json` 中配置：

| 规则 | 说明 |
|------|------|
| region_rules | 从地点提取短地名（大足、巴中、广元等） |
| period_rules | 从公元纪年首年映射到朝代分期 |
| class_rules | 从阶层+身份表述归一化到六大类 |
| sect_rules | 从宗派倾向字段提取主宗派 |
| vow_main / vow_detail / vow_l2_norm | 祈愿编码归一化：一级修正+主成分（vow_main）、二级原始（vow_detail）、二级映射到 v3.0 词表（vow_l2_norm，映射表见规则附录） |
| makeup_normalized | 妆造类型归一化（01 脚本内置，规则 v1.1：新造/新造兼妆修/重妆/重修/不详；仅"镌妆"归新造兼妆修） |
| 一致性校验 | 妆造-实践行为矛盾排查（01 脚本内置，输出 makeup_practice_contradictions.txt） |
| sect_colors | 宗派→颜色映射 |
| gender_colors | 性别→颜色映射 |

## MySQL 数据库

项目提供完整的 MySQL 支持，将 CSV 数据导入结构化关系型数据库：

### 表结构

`scripts/schema.sql` 定义了 11 张表：

| 表 | 说明 |
|----|------|
| `inscriptions` | 题记主表（992条），含所有原始字段 + 归一化字段的外键引用 |
| `regions` | 地区参考表 |
| `periods` | 朝代分期参考表 |
| `sects` | 宗派参考表 |
| `religion_types` | 宗教类型参考表 |
| `subjects` | 造像主体/题材参考表 |
| `class_types` | 阶层类型（质的分类）参考表 |
| `class_units` | 组织单位（量的分类）参考表 |
| `class_labels` | 阶层复合标签参考表 |
| `inscription_sects` | 题记↔宗派多对多关系表 |
| `donors` | 出资者明细表（按分隔符拆分多人） |

### 快速使用

```bash
# 1. 在 MySQL 中执行建表
mysql -u root -p < scripts/schema.sql

# 2. 导入数据
python scripts/export_to_mysql.py

# 3. 或一步到位（清洗+导入）
python scripts/01_extract_and_clean.py --mysql
```

> 注：本机未安装/未启动 MySQL 服务（3306 无响应），以上命令需在 MySQL 可用后执行；
> `schema.sql` 的 `prayer_code_l1/l2` 已更新为祈愿 v3.0 词表注释，导出脚本会
> 自动写入 5.21实体 的新编码，无需改动。

### 常用分析查询

```sql
-- 各朝代各宗派题记数量
SELECT p.name AS 朝代, s.name AS 宗派, COUNT(*) AS 数量
FROM inscriptions i
JOIN periods p ON i.period_id = p.id
JOIN sects s ON i.sect_main_id = s.id
GROUP BY p.name, s.name
ORDER BY p.sort_order, 数量 DESC;

-- 各地区观音造像分布
SELECT r.short_name AS 地区, COUNT(*) AS 数量
FROM inscriptions i
JOIN regions r ON i.region_id = r.id
JOIN subjects s ON i.subject_id = s.id
WHERE s.name = '观音'
GROUP BY r.short_name ORDER BY 数量 DESC;

-- 官员出资的造像
SELECT i.name AS 题记, i.deity AS 所造佛像, s.name AS 宗派
FROM inscriptions i
JOIN class_types ct ON i.class_type_id = ct.id
JOIN sects s ON i.sect_main_id = s.id
WHERE ct.name = '官员' ORDER BY i.year_start;

-- 各祈愿一级编码分布（v3.0 词表）
SELECT prayer_code_l1 AS 祈愿一级, COUNT(*) AS 数量
FROM inscriptions
GROUP BY prayer_code_l1 ORDER BY 数量 DESC;

-- 四恩三有相关：祈愿二级编码含"四恩"的题记
SELECT orig_id, name AS 题记, prayer_code_l1, prayer_code_l2
FROM inscriptions
WHERE prayer_code_l2 LIKE '%四恩%';
```

视图 `v_inscriptions_full` 提供了与清洗 CSV 完全一致的宽表输出，方便兼容现有前端和脚本。

## 约束条件

- 原始 Excel 数据只读不写
- 所有归一化列以新列附加，原始列完整保留
- 缺失信息标记为"不详"或"未知"

## Neo4j 中文标签与关系

2026-09 起 Neo4j 图全部使用中文标签/关系（由 `07_rename_chinese_neo4j.py` 执行，
映射表：`data/config/neo4j_labels_zh.json`）：

| 英文（旧） | 中文（现） | 英文（旧） | 中文（现） |
|-----------|----------|-----------|----------|
| Inscription | 题记 | LOCATED_IN | 位于 |
| Region | 地区 | FROM_PERIOD | 所属朝代 |
| Period | 朝代分期 | HAS_CLASS | 阶层 |
| Class / ClassType / ClassUnit | 阶层标签 / 阶层类型 / 组织单位 | HAS_TYPE / HAS_UNIT | 阶层类型 / 组织单位 |
| Sect | 宗派 | BELONGS_TO | 所属宗派 |
| Subject | 造像题材 | DEPICTS | 造像题材 |
| ReligionType | 宗教类型 | HAS_RELIGION | 宗教类型 |
| Gender | 性别 | HAS_GENDER | 性别 |
| MakeupType | 妆造类型 | HAS_MAKEUP | 妆造类型 |
| WishL1/L2/L3 | 祈愿内容一级/二级/三级 | HAS_WISH | 祈愿内容 |
| PracticeL1/L2/L3 | 实践行为一级/二级/三级 | HAS_PRACTICE | 实践行为 |
| CauseL1/L2/L3 | 造像原因一级/二级/三级 | HAS_CAUSE | 造像原因 |
| — | — | HAS_SUBTYPE | 下级编码 |

核验：`python scripts/08_verify_rules_neo4j.py` 输出各维度节点与
《标注规范》词表的合规/偏差报告（`data/cleaned/neo4j_rules_audit.txt`）。
当前状态：**全维度合规**（一级 13/13、实践二级 30/30、原因二级 26/26、无孤儿节点）。

Browser 可视化样式：将 `scripts/neo4j_browser_style.grass` 内容粘贴到
Neo4j Browser 的 `:style` 编辑器（一级枢纽=三色大胶囊，题记=小灰点，二/三级=渐小胶囊）。
