// ================================================================
// 石刻造像题记知识图谱 - 聚合查询（中文标签版，对应 import v5.0）
// ================================================================

// ─── Q1: 地区×时间×阶层 三维计数 ───
MATCH (i:`题记`)-[:`位于`]->(r:`地区`),
      (i)-[:`所属朝代`]->(p:`朝代分期`),
      (i)-[:`阶层`]->(c:`阶层标签`)
WHERE p.name <> '不详' AND c.name <> '未知'
RETURN r.name AS 地区,
       p.name AS 朝代,
       c.name AS 阶层,
       count(i) AS 数量
ORDER BY 地区, p.start_year, 阶层;

// ─── Q2: 地区×宗派 交叉统计 ───
MATCH (i:`题记`)-[:`位于`]->(r:`地区`),
      (i)-[:`所属宗派`]->(s:`宗派`)
WHERE s.name <> '无法判定'
RETURN r.name AS 地区,
       s.name AS 宗派,
       count(i) AS 数量
ORDER BY 地区, 数量 DESC;

// ─── Q3: 地区题记总数（用于节点大小） ───
MATCH (i:`题记`)-[:`位于`]->(r:`地区`)
RETURN r.name AS 地区, count(i) AS 总数 ORDER BY 总数 DESC;

// ─── Q4: 各阶层题记统计 ───
MATCH (i:`题记`)-[:`阶层`]->(c:`阶层标签`)
RETURN c.name AS 阶层, count(i) AS 总数 ORDER BY 总数 DESC;

// ─── Q5: 各宗派题记统计 ───
MATCH (i:`题记`)-[:`所属宗派`]->(s:`宗派`)
RETURN s.name AS 宗派, count(i) AS 总数 ORDER BY 总数 DESC;

// ─── Q6: 各朝代题记数量 ───
MATCH (i:`题记`)-[:`所属朝代`]->(p:`朝代分期`)
RETURN p.name AS 朝代, p.start_year AS 起始年, count(i) AS 总数 ORDER BY 起始年;

// ─── Q7: 特定地区题记明细（示例：大足） ───
MATCH (i:`题记`)-[:`位于`]->(r:`地区` {name: '大足'}),
      (i)-[:`所属朝代`]->(p:`朝代分期`),
      (i)-[:`阶层`]->(c:`阶层标签`)
OPTIONAL MATCH (i)-[:`所属宗派`]->(s:`宗派`)
RETURN i.id AS 序号, i.name AS 名称, p.name AS 朝代, c.name AS 阶层,
       s.name AS 宗派, i.deity AS 佛像, i.patron AS 出资者, i.gender AS 性别
ORDER BY i.id;

// ─── Q8: 前端可视化完整导出（含祈愿/妆造） ───
MATCH (i:`题记`)
OPTIONAL MATCH (i)-[:`位于`]->(r:`地区`)
OPTIONAL MATCH (i)-[:`所属朝代`]->(p:`朝代分期`)
OPTIONAL MATCH (i)-[:`阶层`]->(c:`阶层标签`)
OPTIONAL MATCH (i)-[:`所属宗派`]->(s:`宗派`)
RETURN i.id AS 序号, i.name AS 名称, i.year_start AS 公元起年, i.year_raw AS 公元纪年,
       r.name AS 地区, p.name AS 朝代, c.name AS 阶层标签, s.name AS 宗派,
       i.deity AS 佛像, i.patron AS 出资者, i.gender AS 性别, i.identity AS 身份,
       i.location AS 地点, i.vow_main AS 祈愿一级, i.vow_detail AS 祈愿二级,
       i.makeup_normalized AS 妆造归一
ORDER BY i.id;

// ─── Q9: 祈愿一级编码分布（v3.0 词表，含四恩三有） ───
MATCH (i:`题记`)
RETURN i.vow_main AS 祈愿一级, count(i) AS 总数 ORDER BY 总数 DESC;

// ─── Q10: 朝代 × 祈愿一级 交叉统计 ───
MATCH (i:`题记`)-[:`所属朝代`]->(p:`朝代分期`)
WHERE p.name <> '不详'
RETURN p.name AS 朝代, i.vow_main AS 祈愿一级, count(i) AS 数量
ORDER BY p.start_year, 数量 DESC;

// ─── Q11: 祈愿层级浏览（祈愿内容一级→二级→三级→题记数） ───
MATCH (l1:`祈愿内容一级`)-[:`下级编码`*1..2]->(leaf)
WHERE (leaf:`祈愿内容二级` OR leaf:`祈愿内容三级`)
OPTIONAL MATCH (leaf)-[:`祈愿内容`]->(i:`题记`)
RETURN l1.name AS 一级,
       [x IN labels(leaf) WHERE x STARTS WITH '祈愿'][0] AS 层级,
       leaf.name AS 类目,
       count(DISTINCT i) AS 题记数
ORDER BY 一级, 层级 DESC, 题记数 DESC;

// ─── Q12: 四恩三有相关题记 ───
MATCH (w:`祈愿内容三级`)-[:`祈愿内容`]->(i:`题记`)
WHERE w.name CONTAINS '四恩' OR w.name CONTAINS '三有'
OPTIONAL MATCH (i)-[:`所属朝代`]->(p:`朝代分期`)
OPTIONAL MATCH (i)-[:`位于`]->(r:`地区`)
RETURN i.id AS 序号, i.name AS 名称, w.name AS 祈愿细目,
       p.name AS 朝代, r.name AS 地区
ORDER BY i.id;

// ─── Q13: 妆造类型分布与朝代交叉（v1.1） ───
MATCH (i:`题记`)-[:`妆造类型`]->(m:`妆造类型`)
OPTIONAL MATCH (i)-[:`所属朝代`]->(p:`朝代分期`)
RETURN m.name AS 妆造类型, p.name AS 朝代, count(i) AS 数量
ORDER BY 妆造类型, 数量 DESC;

// ─── Q14: 实践行为/造像原因 层级概览 ───
MATCH (l1)-[:`下级编码`*1..2]->(leaf)-[r]->(i:`题记`)
WHERE labels(l1)[0] IN ['祈愿内容一级','实践行为一级','造像原因一级']
  AND type(r) IN ['祈愿内容','实践行为','造像原因']
RETURN labels(l1)[0] AS 维度, l1.name AS 一级, leaf.name AS 类目, count(DISTINCT i) AS 题记数
ORDER BY 维度, 一级, 题记数 DESC;
