// ================================================================
// 石刻造像题记知识图谱 - Neo4j 全量导入脚本 v5.0（中文标签版）
// 节点标签与关系类型均为中文，与 05/06 同步脚本、neo4j_labels_zh.json 一致
// 数据基准: 5.21实体（祈愿 v3.0 含四恩三有；妆造 v1.1）
// ================================================================

// ─── 1. 地区 ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.region_short AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`地区` {name: name});

// ─── 2. 朝代分期 ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.period AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`朝代分期` {name: name});

MATCH (p:`朝代分期` {name:'隋'}) SET p.start_year=581,p.end_year=618;
MATCH (p:`朝代分期` {name:'初唐'}) SET p.start_year=618,p.end_year=690;
MATCH (p:`朝代分期` {name:'武周'}) SET p.start_year=690,p.end_year=705;
MATCH (p:`朝代分期` {name:'盛唐'}) SET p.start_year=705,p.end_year=755;
MATCH (p:`朝代分期` {name:'中唐'}) SET p.start_year=755,p.end_year=845;
MATCH (p:`朝代分期` {name:'晚唐'}) SET p.start_year=845,p.end_year=907;
MATCH (p:`朝代分期` {name:'五代'}) SET p.start_year=907,p.end_year=965;
MATCH (p:`朝代分期` {name:'北宋'}) SET p.start_year=965,p.end_year=1127;
MATCH (p:`朝代分期` {name:'南宋'}) SET p.start_year=1127,p.end_year=1279;

// ─── 3. 阶层（类型/单位/复合标签） ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.class_type AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`阶层类型` {name: name});

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.class_unit AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`组织单位` {name: name});

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.class_label AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`阶层标签` {name: name});

// ─── 4. 宗派 ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.sect_main AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`宗派` {name: name});

// ─── 5. 造像题材 ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.subject AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`造像题材` {name: name});

// ─── 6. 宗教类型 ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.religion_type AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`宗教类型` {name: name});

// ─── 6b. 祈愿内容一级（v3.0 词表） ───
// 注：二/三级祈愿枢纽由 05_update_vows_neo4j.py 细化生成
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.vow_main AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`祈愿内容一级` {name: name});

// ─── 6c. 妆造类型（v1.1） ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
WITH DISTINCT row.makeup_normalized AS name WHERE name IS NOT NULL AND name <> ''
MERGE (:`妆造类型` {name: name});

// ─── 7. 题记（含祈愿/妆造编码字段） ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
CREATE (i:`题记` {
  id: row.题记序号,
  name: row.题记名称,
  year_raw: row.公元纪年,
  year_start: toInteger(row.year_start),
  period: row.period,
  region: row.region_short,
  class_label: row.class_label,
  class_type: row.class_type,
  class_unit: row.class_unit,
  sect: row.sect_main,
  sect_all: row.sect_all,
  subject: row.subject,
  religion_type: row.religion_type,
  deity: row.所造佛像名称,
  patron: row.出资者,
  gender: row.gender_normalized,
  location: row.地点,
  identity: row.造像者身份表述,
  prayer_l1: row.vow_main,
  prayer_l2: row.vow_detail,
  makeup_normalized: row.makeup_normalized
});

// ─── 8. 关系 ───
LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (r:`地区` {name: row.region_short})
CREATE (i)-[:`位于`]->(r);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (p:`朝代分期` {name: row.period})
CREATE (i)-[:`所属朝代`]->(p);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (c:`阶层标签` {name: row.class_label})
CREATE (i)-[:`阶层`]->(c);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (ct:`阶层类型` {name: row.class_type})
CREATE (i)-[:`阶层类型`]->(ct);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (cu:`组织单位` {name: row.class_unit})
CREATE (i)-[:`组织单位`]->(cu);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (s:`宗派` {name: row.sect_main})
CREATE (i)-[:`所属宗派`]->(s);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (s:`造像题材` {name: row.subject})
CREATE (i)-[:`造像题材`]->(s);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (r:`宗教类型` {name: row.religion_type})
CREATE (i)-[:`宗教类型`]->(r);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (v:`祈愿内容一级` {name: row.vow_main})
CREATE (v)-[:`祈愿内容`]->(i);

LOAD CSV WITH HEADERS FROM 'file:///inscriptions_clean.csv' AS row
MATCH (i:`题记` {id: row.题记序号}) MATCH (m:`妆造类型` {name: row.makeup_normalized})
CREATE (i)-[:`妆造类型`]->(m);

// ─── 9. 索引 ───
CREATE INDEX insc_id IF NOT EXISTS FOR (i:`题记`) ON (i.id);
CREATE INDEX insc_subject IF NOT EXISTS FOR (i:`题记`) ON (i.subject);
CREATE INDEX insc_vow IF NOT EXISTS FOR (i:`题记`) ON (i.prayer_l1);

// ─── 10. 统计 ───
MATCH (n) RETURN labels(n) AS 标签, count(n) AS 数量 ORDER BY 数量 DESC;
