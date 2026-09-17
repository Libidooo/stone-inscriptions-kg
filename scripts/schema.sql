-- ================================================================
-- 石刻造像题记知识图谱 - MySQL 数据库建表脚本
-- 四川地区佛教石窟铭文 (992条题记)
-- ================================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS stone_inscriptions
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE stone_inscriptions;

-- ─── 1. 参考表 ───────────────────────────────────────────────────

-- 1a. 地区
CREATE TABLE regions (
  id         TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  short_name VARCHAR(20) NOT NULL COMMENT '地区简称（如大足、巴中）',
  full_name  VARCHAR(50) DEFAULT NULL COMMENT '完整地名',
  UNIQUE KEY uk_region (short_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='石刻出土地点/地区';

-- 1b. 朝代分期
CREATE TABLE periods (
  id         TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(10) NOT NULL COMMENT '分期名称（隋、初唐……）',
  start_year SMALLINT UNSIGNED DEFAULT NULL COMMENT '起始公元年',
  end_year   SMALLINT UNSIGNED DEFAULT NULL COMMENT '终止公元年',
  sort_order TINYINT UNSIGNED DEFAULT 0 COMMENT '显示顺序',
  UNIQUE KEY uk_period (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='朝代分期参照表';

-- 1c. 宗派
CREATE TABLE sects (
  id     TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name   VARCHAR(20) NOT NULL COMMENT '宗派名称（净土/密教/禅宗……）',
  color  VARCHAR(7) DEFAULT NULL COMMENT '前端展示色号 #RRGGBB',
  UNIQUE KEY uk_sect (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='佛教宗派参照表';

-- 1d. 宗教类型（佛教/道教/混合/儒教）
CREATE TABLE religion_types (
  id     TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name   VARCHAR(10) NOT NULL COMMENT '宗教类型',
  color  VARCHAR(7) DEFAULT NULL,
  UNIQUE KEY uk_religion (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宗教类型参照表';

-- 1e. 造像主体/题材（观音、弥勒、阿弥陀……）
CREATE TABLE subjects (
  id     TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name   VARCHAR(20) NOT NULL COMMENT '主体名称',
  color  VARCHAR(7) DEFAULT NULL,
  UNIQUE KEY uk_subject (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='造像主体/题材参照表';

-- 1f. 阶层类型（质的分类）
CREATE TABLE class_types (
  id   TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(10) NOT NULL COMMENT '阶层类型（官员/士人/僧侣/工匠/信众/平民/未知）',
  UNIQUE KEY uk_class_type (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='造像者阶层-质的分类';

-- 1g. 组织单位（量的分类）
CREATE TABLE class_units (
  id   TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(10) NOT NULL COMMENT '组织单位（个人/家庭/社邑/群体/未知）',
  UNIQUE KEY uk_class_unit (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='造像者组织单位';

-- 1h. 完整阶层标签（组合标签）
CREATE TABLE class_labels (
  id   SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL COMMENT '阶层复合标签',
  UNIQUE KEY uk_class_label (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='阶层复合标签';

-- ─── 2. 主表 ─────────────────────────────────────────────────────

CREATE TABLE inscriptions (
  id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  -- 原始字段
  orig_id             VARCHAR(10) NOT NULL COMMENT '原始题记序号（如 1, 2, …）',
  name                VARCHAR(200) DEFAULT NULL COMMENT '题记名称',
  time_raw            VARCHAR(100) DEFAULT NULL COMMENT '时间（原始）',
  year_raw            VARCHAR(50) DEFAULT NULL COMMENT '公元纪年（原始）',
  year_start          SMALLINT UNSIGNED DEFAULT NULL COMMENT '公元纪年首年（提取）',
  location            VARCHAR(200) DEFAULT NULL COMMENT '地点（原始）',
  cave_position       VARCHAR(100) DEFAULT NULL COMMENT '窟位',
  maker_count         VARCHAR(20) DEFAULT NULL COMMENT '造像者人数',
  gender_raw          VARCHAR(10) DEFAULT NULL COMMENT '性别（原始）',
  gender_normalized   VARCHAR(4) DEFAULT NULL COMMENT '性别（归一化：男/女/未知）',
  deity               VARCHAR(200) DEFAULT NULL COMMENT '所造佛像名称',
  patron              TEXT DEFAULT NULL COMMENT '出资者',
  identity_desc       TEXT DEFAULT NULL COMMENT '造像者身份表述',
  class_raw           VARCHAR(100) DEFAULT NULL COMMENT '阶层（原始）',
  community_org       VARCHAR(200) DEFAULT NULL COMMENT '社邑组织',
  practice_code_l1    VARCHAR(200) DEFAULT NULL COMMENT '实践行为（一级编码）',
  practice_code_l2    VARCHAR(200) DEFAULT NULL COMMENT '实践行为（二级编码）',
  prayer_code_l1      VARCHAR(200) DEFAULT NULL COMMENT '祈愿内容（一级编码，v3.0词表：超度往生/现世福报/国邦安宁/佛法弘传/修行证悟/游观纪胜/杂缘祈愿/信息不详）',
  prayer_code_l2      VARCHAR(200) DEFAULT NULL COMMENT '祈愿内容（二级编码，括号内为三级细目，如：普度众生 (上报四恩)）',
  reason_code_l1      VARCHAR(200) DEFAULT NULL COMMENT '造像原因（一级编码）',
  reason_code_l2      VARCHAR(200) DEFAULT NULL COMMENT '造像原因（二级编码）',
  related_events      VARCHAR(500) DEFAULT NULL COMMENT '关联历史事件',
  sutra               VARCHAR(200) DEFAULT NULL COMMENT '经文',
  decoration_type     VARCHAR(100) DEFAULT NULL COMMENT '妆造类型',
  makeup_normalized   VARCHAR(20) DEFAULT NULL COMMENT '妆造类型（归一化 v1.1：新造/新造兼妆修/重妆/重修/不详；仅镌妆亦归新造兼妆修）',
  religion_raw        VARCHAR(50) DEFAULT NULL COMMENT '宗教类型（原始）',
  sect_raw            VARCHAR(200) DEFAULT NULL COMMENT '宗派倾向（原始）',
  notes               TEXT DEFAULT NULL COMMENT '备注',

  -- 归一化字段
  region_id           TINYINT UNSIGNED DEFAULT NULL COMMENT '地区ID → regions.id',
  period_id           TINYINT UNSIGNED DEFAULT NULL COMMENT '朝代分期ID → periods.id',
  class_type_id       TINYINT UNSIGNED DEFAULT NULL COMMENT '阶层类型ID → class_types.id',
  class_unit_id       TINYINT UNSIGNED DEFAULT NULL COMMENT '组织单位ID → class_units.id',
  class_label_id      SMALLINT UNSIGNED DEFAULT NULL COMMENT '阶层标签ID → class_labels.id',
  class_types_detail  VARCHAR(100) DEFAULT NULL COMMENT '群体详细阶层成分（分号分隔）',
  sect_main_id        TINYINT UNSIGNED DEFAULT NULL COMMENT '主宗派ID → sects.id',
  sect_all            VARCHAR(100) DEFAULT NULL COMMENT '全宗派（分号分隔）',
  religion_type_id    TINYINT UNSIGNED DEFAULT NULL COMMENT '宗教类型ID → religion_types.id',
  subject_id          TINYINT UNSIGNED DEFAULT NULL COMMENT '造像主体ID → subjects.id',

  -- 元信息
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

  UNIQUE KEY uk_orig_id (orig_id),
  INDEX idx_year_start (year_start),
  INDEX idx_region (region_id),
  INDEX idx_period (period_id),
  INDEX idx_sect_main (sect_main_id),
  INDEX idx_subject (subject_id),
  INDEX idx_religion (religion_type_id),
  INDEX idx_class_type (class_type_id),
  INDEX idx_class_unit (class_unit_id),
  INDEX idx_gender (gender_normalized),

  CONSTRAINT fk_ins_region FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_period FOREIGN KEY (period_id) REFERENCES periods(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_class_type FOREIGN KEY (class_type_id) REFERENCES class_types(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_class_unit FOREIGN KEY (class_unit_id) REFERENCES class_units(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_class_label FOREIGN KEY (class_label_id) REFERENCES class_labels(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_sect_main FOREIGN KEY (sect_main_id) REFERENCES sects(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_religion FOREIGN KEY (religion_type_id) REFERENCES religion_types(id) ON DELETE SET NULL,
  CONSTRAINT fk_ins_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='石刻造像题记主表（992条）';

-- ─── 3. 多对多关系表 ─────────────────────────────────────────────

-- 题记 ↔ 宗派（支持一条题记有多个宗派倾向）
CREATE TABLE inscription_sects (
  inscription_id INT UNSIGNED NOT NULL COMMENT '题记ID',
  sect_id        TINYINT UNSIGNED NOT NULL COMMENT '宗派ID',
  is_main        TINYINT(1) DEFAULT 0 COMMENT '是否为主宗派',
  PRIMARY KEY (inscription_id, sect_id),
  CONSTRAINT fk_is_inscription FOREIGN KEY (inscription_id) REFERENCES inscriptions(id) ON DELETE CASCADE,
  CONSTRAINT fk_is_sect FOREIGN KEY (sect_id) REFERENCES sects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题记-宗派多对多关系';

-- 题记 ↔ 出资者（多人出资拆分为独立行）
CREATE TABLE donors (
  id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  inscription_id  INT UNSIGNED NOT NULL COMMENT '题记ID',
  donor_name      VARCHAR(100) NOT NULL COMMENT '出资者名称',
  sort_order      TINYINT UNSIGNED DEFAULT 0 COMMENT '在题记中的顺序',
  CONSTRAINT fk_donor_inscription FOREIGN KEY (inscription_id) REFERENCES inscriptions(id) ON DELETE CASCADE,
  INDEX idx_donor_name (donor_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='出资者明细表';

-- ─── 4. 视图 ─────────────────────────────────────────────────────

-- 题记宽表视图（方便直接替代旧的 CSV 查询）
CREATE OR REPLACE VIEW v_inscriptions_full AS
SELECT
  i.orig_id                        AS `题记序号`,
  i.name                           AS `题记名称`,
  i.time_raw                       AS `时间`,
  i.year_raw                       AS `公元纪年`,
  i.year_start                     AS `year_start`,
  r.short_name                     AS `region_short`,
  i.location                       AS `地点`,
  i.cave_position                  AS `窟位`,
  i.maker_count                    AS `造像者人数`,
  i.gender_normalized              AS `gender_normalized`,
  i.deity                          AS `所造佛像名称`,
  i.patron                         AS `出资者`,
  i.identity_desc                  AS `造像者身份表述`,
  i.class_raw                      AS `阶层`,
  ct.name                          AS `class_type`,
  cu.name                          AS `class_unit`,
  cl.name                          AS `class_label`,
  i.class_types_detail             AS `class_types`,
  i.community_org                  AS `社邑组织`,
  i.practice_code_l1               AS `实践行为（一级编码）`,
  i.practice_code_l2               AS `实践行为（二级编码）`,
  i.prayer_code_l1                 AS `祈愿内容（一级编码）`,
  i.prayer_code_l2                 AS `祈愿内容（二级编码）`,
  i.reason_code_l1                 AS `造像原因（一级编码）`,
  i.reason_code_l2                 AS `造像原因（二级编码）`,
  i.related_events                 AS `关联历史事件`,
  i.sutra                          AS `经文`,
  i.decoration_type                AS `妆造类型`,
  i.makeup_normalized              AS `妆造类型（归一化）`,
  rt.name                          AS `religion_type`,
  sm.name                          AS `sect_main`,
  i.sect_all                       AS `sect_all`,
  sb.name                          AS `subject`,
  p.name                           AS `period`,
  i.religion_raw                   AS `宗教类型`,
  i.sect_raw                       AS `宗派倾向(主宗派倾向；副宗派倾向）`,
  i.notes                          AS `备注`
FROM inscriptions i
LEFT JOIN regions r        ON i.region_id = r.id
LEFT JOIN periods p        ON i.period_id = p.id
LEFT JOIN class_types ct   ON i.class_type_id = ct.id
LEFT JOIN class_units cu   ON i.class_unit_id = cu.id
LEFT JOIN class_labels cl  ON i.class_label_id = cl.id
LEFT JOIN sects sm         ON i.sect_main_id = sm.id
LEFT JOIN religion_types rt ON i.religion_type_id = rt.id
LEFT JOIN subjects sb      ON i.subject_id = sb.id;

-- ─── 5. 常用分析查询示例 ─────────────────────────────────────────

-- 各朝代各宗派题记数量
-- SELECT p.name AS 朝代, s.name AS 宗派, COUNT(*) AS 数量
-- FROM inscriptions i
-- JOIN periods p ON i.period_id = p.id
-- JOIN sects s ON i.sect_main_id = s.id
-- GROUP BY p.name, s.name
-- ORDER BY p.sort_order, 数量 DESC;

-- 各地区观音造像分布
-- SELECT r.short_name AS 地区, COUNT(*) AS 数量
-- FROM inscriptions i
-- JOIN regions r ON i.region_id = r.id
-- JOIN subjects s ON i.subject_id = s.id
-- WHERE s.name = '观音'
-- GROUP BY r.short_name
-- ORDER BY 数量 DESC;

-- 官员出资的造像统计
-- SELECT i.name AS 题记, i.deity AS 所造佛像, s.name AS 宗派
-- FROM inscriptions i
-- JOIN class_types ct ON i.class_type_id = ct.id
-- JOIN sects s ON i.sect_main_id = s.id
-- WHERE ct.name = '官员'
-- ORDER BY i.year_start;
