"""
石刻造像题记知识图谱 - CSV → MySQL 导入脚本
从清洗后的 CSV (inscriptions_clean.csv) 写入 MySQL


使用方法:
  1. 先执行 schema.sql 创建数据库和表
  2. 修改下方 DB_CONFIG 连接信息
  3. python export_to_mysql.py

依赖: pip install pymysql pandas sqlalchemy
"""

import json
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录

# ─── 配置 ───────────────────────────────────────────────────────────
CSV_PATH = ROOT / "data" / "cleaned" / "inscriptions_clean.csv"
CONFIG_PATH = ROOT / 'data' / 'config' / 'normalization_rules.json'

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",       # ← 修改为你的 MySQL 密码
    "database": "stone_inscriptions",
}
# ───────────────────────────────────────────────────────────────────

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def get_engine():
    url = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4"
    return create_engine(url)


def load_reference_ids(engine):
    """加载所有参考表的 name→id 映射"""
    refs = {}
    for table in ["regions", "periods", "sects", "religion_types",
                   "subjects", "class_types", "class_units", "class_labels"]:
        rows = engine.execute(text(f"SELECT id, name FROM {table}")).fetchall()
        refs[table] = {row[1]: row[0] for row in rows}
    return refs


def main():
    print(f"读取清洗数据: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"共 {len(df)} 条记录")

    engine = get_engine()

    # ─── 1. 填充参考表 ───
    print("\n[1/4] 填充参考表...")
    col_sect = "宗派倾向(主宗派倾向；副宗派倾向）"

    # 地区
    regions = df["region_short"].dropna().unique()
    for r in regions:
        engine.execute(text("INSERT IGNORE INTO regions (short_name) VALUES (:n)"), {"n": r})

    # 朝代分期 + sort_order
    period_order = ["隋", "初唐", "武周", "盛唐", "中唐", "晚唐", "五代", "北宋", "南宋", "不详"]
    for i, p in enumerate(period_order):
        engine.execute(text("INSERT IGNORE INTO periods (name, sort_order) VALUES (:n, :o)"),
                       {"n": p, "o": i})

    # 更新 period start/end
    for p in CONFIG["period_rules"]["periods"]:
        engine.execute(
            text("UPDATE periods SET start_year=:s, end_year=:e WHERE name=:n"),
            {"s": p["start"], "e": p["end"], "n": p["name"]}
        )

    # 宗派
    for m in CONFIG["sect_rules"]["mappings"]:
        label = m["label"]
        color = CONFIG["sect_colors"].get(label)
        engine.execute(text("INSERT IGNORE INTO sects (name, color) VALUES (:n, :c)"),
                       {"n": label, "c": color})

    # 宗教类型
    for m in CONFIG["religion_type_rules"]["mappings"]:
        label = m["label"]
        color = CONFIG.get("religion_type_colors", {}).get(label)
        engine.execute(text("INSERT IGNORE INTO religion_types (name, color) VALUES (:n, :c)"),
                       {"n": label, "c": color})

    # 主体
    all_subjects = set()
    for m in CONFIG["subject_rules"]["mappings"]:
        all_subjects.add(m["label"])
    for m in CONFIG["subject_rules"].get("fallback_patterns", []):
        all_subjects.add(m["label"])
    for s in all_subjects:
        color = CONFIG.get("subject_colors", {}).get(s)
        engine.execute(text("INSERT IGNORE INTO subjects (name, color) VALUES (:n, :c)"),
                       {"n": s, "c": color})

    # 阶层类型
    for t in df["class_type"].dropna().unique():
        engine.execute(text("INSERT IGNORE INTO class_types (name) VALUES (:n)"), {"n": t})

    # 组织单位
    for u in df["class_unit"].dropna().unique():
        engine.execute(text("INSERT IGNORE INTO class_units (name) VALUES (:n)"), {"n": u})

    # 阶层标签
    for l in df["class_label"].dropna().unique():
        engine.execute(text("INSERT IGNORE INTO class_labels (name) VALUES (:n)"), {"n": l})

    refs = load_reference_ids(engine)
    print("  参考表填充完成")

    # ─── 2. 写入题记主表 ───
    print("\n[2/4] 写入 inscriptions 主表...")
    inserted = 0
    for _, row in df.iterrows():
        sect_raw = row.get(col_sect)
        engine.execute(text("""
            INSERT INTO inscriptions (
                orig_id, name, time_raw, year_raw, year_start,
                location, cave_position, maker_count,
                gender_raw, gender_normalized, deity, patron,
                identity_desc, class_raw, community_org,
                practice_code_l1, practice_code_l2,
                prayer_code_l1, prayer_code_l2,
                reason_code_l1, reason_code_l2,
                related_events, sutra, decoration_type, makeup_normalized,
                religion_raw, sect_raw, notes,
                region_id, period_id, class_type_id, class_unit_id,
                class_label_id, class_types_detail,
                sect_main_id, sect_all, religion_type_id, subject_id
            ) VALUES (
                :o, :n, :t, :y, :ys,
                :l, :c, :m,
                :g, :gn, :d, :p,
                :id, :cr, :co,
                :pcl1, :pcl2, :prl1, :prl2,
                :rl1, :rl2,
                :re, :s, :dt, :mk,
                :rr, :sr, :nt,
                :rid, :pid, :ctid, :cuid,
                :clid, :ctd,
                :smid, :sa, :rtid, :sbid
            )
        """), {
            "o": str(row.get("题记序号", "")),
            "n": str(row.get("题记名称", "")),
            "t": str(row.get("时间", "")),
            "y": str(row.get("公元纪年", "")),
            "ys": None if pd.isna(row.get("year_start")) else int(row["year_start"]),
            "l": str(row.get("地点", "")),
            "c": str(row.get("窟位", "")),
            "m": str(row.get("造像者人数", "")),
            "g": str(row.get("性别", "")),
            "gn": str(row.get("gender_normalized", "未知")),
            "d": str(row.get("所造佛像名称", "")),
            "p": str(row.get("出资者", "")),
            "id": str(row.get("造像者身份表述", "")),
            "cr": str(row.get("阶层", "")),
            "co": str(row.get("社邑组织", "")),
            "pcl1": str(row.get("实践行为（一级编码）", "")),
            "pcl2": str(row.get("实践行为（二级编码）", "")),
            "prl1": str(row.get("祈愿内容（一级编码）", "")),
            "prl2": str(row.get("祈愿内容（二级编码）", "")),
            "rl1": str(row.get("造像原因（一级编码）", "")),
            "rl2": str(row.get("造像原因（二级编码）", "")),
            "re": str(row.get("关联历史事件", "")),
            "s": str(row.get("经文", "")),
            "dt": str(row.get("妆造类型", "")),
            "mk": str(row.get("makeup_normalized", "不详")),
            "rr": str(row.get("宗教类型", "")),
            "sr": str(sect_raw if pd.notna(sect_raw) else ""),
            "nt": str(row.get("备注", "")),
            "rid": refs["regions"].get(str(row.get("region_short", ""))),
            "pid": refs["periods"].get(str(row.get("period", ""))),
            "ctid": refs["class_types"].get(str(row.get("class_type", ""))),
            "cuid": refs["class_units"].get(str(row.get("class_unit", ""))),
            "clid": refs["class_labels"].get(str(row.get("class_label", ""))),
            "ctd": str(row.get("class_types", "")),
            "smid": refs["sects"].get(str(row.get("sect_main", ""))),
            "sa": str(row.get("sect_all", "")),
            "rtid": refs["religion_types"].get(str(row.get("religion_type", ""))),
            "sbid": refs["subjects"].get(str(row.get("subject", ""))),
        })
        inserted += 1
        if inserted % 200 == 0:
            print(f"  已写入 {inserted} 条...")
    print(f"  inscriptions 写入完成: {inserted} 条")

    # ─── 3. 写入多对多 inscription_sects ───
    print("\n[3/4] 写入 inscription_sects 多对多关系...")
    ins_map = {}
    rows = engine.execute(text("SELECT id, orig_id FROM inscriptions")).fetchall()
    for r in rows:
        ins_map[r[1]] = r[0]

    rel_count = 0
    for _, row in df.iterrows():
        ins_id = ins_map.get(str(row.get("题记序号", "")))
        if ins_id is None:
            continue
        # 主宗派
        sect_main = str(row.get("sect_main", ""))
        if sect_main in refs["sects"]:
            engine.execute(text("""
                INSERT IGNORE INTO inscription_sects (inscription_id, sect_id, is_main)
                VALUES (:iid, :sid, 1)
            """), {"iid": ins_id, "sid": refs["sects"][sect_main]})
            rel_count += 1

        # 副宗派（从 sect_all 拆分）
        sect_all_raw = str(row.get("sect_all", ""))
        if sect_all_raw and sect_all_raw != "无法判定":
            for s_name in sect_all_raw.split(";"):
                s_name = s_name.strip()
                if s_name and s_name in refs["sects"] and s_name != sect_main:
                    engine.execute(text("""
                        INSERT IGNORE INTO inscription_sects (inscription_id, sect_id, is_main)
                        VALUES (:iid, :sid, 0)
                    """), {"iid": ins_id, "sid": refs["sects"][s_name]})
                    rel_count += 1
    print(f"  inscription_sects 写入完成: {rel_count} 条关系")

    # ─── 4. 写入出资者 ───
    print("\n[4/4] 写入 donors 出资者表...")
    donor_count = 0
    for _, row in df.iterrows():
        ins_id = ins_map.get(str(row.get("题记序号", "")))
        if ins_id is None:
            continue
        patron_raw = row.get("出资者", "")
        if pd.isna(patron_raw) or not str(patron_raw).strip():
            continue
        # 按常见分隔符拆分出资者姓名
        import re
        names = re.split(r'[、，,;；/／\s]+', str(patron_raw).strip())
        for i, name in enumerate(names):
            name = name.strip()
            if name:
                engine.execute(text("""
                    INSERT INTO donors (inscription_id, donor_name, sort_order)
                    VALUES (:iid, :dn, :so)
                """), {"iid": ins_id, "dn": name, "so": i})
                donor_count += 1
    print(f"  donors 写入完成: {donor_count} 条")

    print("\n全部完成！")


if __name__ == "__main__":
    main()
