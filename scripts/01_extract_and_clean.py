#!/usr/bin/env python3
"""
石刻造像题记知识图谱 - 数据清洗与归一化
输入: 5.21实体.xlsx（仓库根，保留所有原始列；祈愿内容编码 v3.0 含四恩三有）
输出: data/cleaned/inscriptions_clean.csv


使用方法:
  python 01_extract_and_clean.py              # 输出 CSV + JSON
  python 01_extract_and_clean.py --mysql      # 输出 CSV + JSON + MySQL
"""

import re
import json
import sys
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录

# ─── 配置 ───────────────────────────────────────────────────────────
EXCEL_PATH = ROOT / '5.21实体.xlsx'
CONFIG_PATH = ROOT / 'data' / 'config' / 'normalization_rules.json'
OUTPUT_CSV = ROOT / "data" / "cleaned" / "inscriptions_clean.csv"
OUTPUT_JSON = ROOT / "data" / "cleaned" / "inscriptions_clean.json"

MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "stone_inscriptions",
}

# ─── 加载配置 ───────────────────────────────────────────────────────
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


# ===================================================================
# 归一化函数
# ===================================================================

def normalize_region(location_str: str) -> str:
    """从地点字符串提取短地名"""
    if pd.isna(location_str) or not location_str:
        return "其他"
    for rule in CONFIG["region_rules"]["patterns"]:
        if rule["pattern"] in str(location_str):
            return rule["short"]
    return CONFIG["region_rules"]["default"]


def extract_year_start(year_str) -> int:
    """从公元纪年提取首年整数"""
    if pd.isna(year_str):
        return None
    s = str(year_str).strip()
    # 范围格式 "650-655" → 650
    m = re.match(r"(\d{3,4})\s*[-–—]", s)
    if m:
        return int(m.group(1))
    # 单年 "895" → 895
    m = re.match(r"^(\d{3,4})$", s)
    if m:
        return int(m.group(1))
    # 年份在文本中
    m = re.search(r"(\d{3,4})", s)
    if m:
        return int(m.group(1))
    return None


def normalize_period(year_start) -> str:
    """根据首年映射到朝代分期"""
    if year_start is None:
        return CONFIG["period_rules"]["unknown_label"]
    for period in CONFIG["period_rules"]["periods"]:
        if period["start"] <= year_start < period["end"]:
            return period["name"]
    return CONFIG["period_rules"]["unknown_label"]


def parse_class_unit(cls_raw):
    """解析组织单位：个人/家庭/社邑/群体/未知"""
    if pd.isna(cls_raw) or not cls_raw:
        return "未知"
    s = str(cls_raw).strip()
    if "混合" in s:
        return "群体"
    if "家庭合署" in s:
        return "家庭"
    if "社邑" in s or "临时联合" in s or "行业结社" in s or "集体捐造" in s:
        return "社邑"
    if s in ["[不详]", "信息空白"] or not s:
        return "未知"
    return "个人"


def parse_class_type(cls_raw):
    """从原始阶层字段提取主阶层类型。
    分类：官员/士人/僧侣/工匠/富众信士/平民/未知"""
    if pd.isna(cls_raw) or not cls_raw:
        return "未知"
    s = str(cls_raw).strip()
    if s in ["[不详]", "信息空白(个体)", "信息空白"]:
        return "未知"
    direct_map = [
        ("皇室宗亲", "官员"), ("宗族官僚", "官员"), ("在职官员", "官员"),
        ("封爵贵族", "官员"), ("官员士人", "官员"), ("豪强地主", "官员"),
        ("军人武士", "官员"),
        ("名门士族", "士人"), ("乡绅士人", "士人"),
        ("僧团僧伽", "僧侣"), ("僧尼个体", "僧侣"),
        ("商贾匠人", "工匠"),
        ("虔诚弟子", "富众信士"),
        ("平民合众", "平民"), ("普通百姓", "平民"), ("基层百姓", "平民"),
        ("未明群体", "平民"),
        ("道士", "僧侣"),
    ]
    for pat, label in direct_map:
        if pat in s:
            return label
    return "未知"


def parse_mixed_classes(cls_raw):
    """从混合群体(职官A、职官B)提取所有参与阶层"""
    if pd.isna(cls_raw) or "混合" not in str(cls_raw):
        return ""
    m = __import__('re').search(r'\(([^)]+)\)', str(cls_raw))
    if not m:
        return ""
    parts = __import__('re').split(r'[、；]', m.group(1))
    labels = []
    # 去掉括号内的补充信息（如家庭合署）
    clean_parts = [__import__('re').sub(r'[（(][^）)]*[）)]', '', p).strip() for p in parts]
    for p in clean_parts:
        for pat, label in [
            ("皇室宗亲", "官员"), ("宗族官僚", "官员"), ("在职官员", "官员"),
            ("封爵贵族", "官员"), ("豪强地主", "官员"), ("军人武士", "官员"),
            ("名门士族", "士人"), ("乡绅士人", "士人"),
            ("僧团僧伽", "僧侣"), ("僧尼个体", "僧侣"), ("僧", "僧侣"),
            ("商贾匠人", "工匠"), ("匠人", "工匠"),
            ("虔诚弟子", "富众信士"), ("弟子", "富众信士"),
            ("平民合众", "平民"), ("普通百姓", "平民"), ("基层百姓", "平民"),
            ("信徒", "平民"),
            ("道士", "僧侣"), ("道人", "僧侣"),
        ]:
            if pat in p and label not in labels:
                labels.append(label)
                break
    return ";".join(labels) if labels else ""


def normalize_class_new(cls_raw, identity_str):
    """新的阶层归一化：同时生成 class_label, class_unit, class_types_detail"""
    if pd.isna(identity_str):
        identity_str = ""
    if pd.isna(cls_raw):
        cls_raw = ""
    s = str(cls_raw).strip()

    # 未知处理
    if s in ["[不详]", "信息空白(个体)", "信息空白", ""] or s == "nan":
        return "未知", "未知", ""

    unit = parse_class_unit(s)
    primary = parse_class_type(s)

    if unit == "群体":
        mixed = parse_mixed_classes(s)
        if not mixed:
            mixed = fallback_keyword_match(identity_str)
        # class_type取最高成分（第一个）
        primary = mixed.split(";")[0] if mixed else primary
        return primary, "群体", mixed or primary

    # 个人/家庭/社邑
    if unit == "未知":
        return primary, "未知", ""
    return primary, unit, ""


def fallback_keyword_match(text: str) -> str:
    """仅在身份表述中使用关键词匹配"""
    for mapping in CONFIG["class_rules"]["mappings"]:
        for kw in mapping["keywords"]:
            if kw in text:
                return mapping["label"]
    return "未知"


def normalize_sect(sect_str) -> str:
    """从宗派倾向字段提取主宗派（仅正式教派，排除观音/地藏/弥勒/药师等主体标签）

    支持多分隔符：优先按；拆分，再按，拆分，取第一个成分
    例如："密教,观音体系" → 取"密教" → 匹配密教
          "禅宗；律宗" → 取"禅宗" → 匹配禅宗
          "观音体系；地藏体系" → 不匹配任何教派 → 无法判定
    """
    if pd.isna(sect_str) or not sect_str:
        return CONFIG["sect_rules"]["unknown_label"]
    s = str(sect_str).strip()

    # 先按；拆分，再按，拆分，取第一个非空成分
    import re
    parts = re.split(r'[；;，,]', s)
    primary = parts[0].strip() if parts else s

    for mapping in CONFIG["sect_rules"]["mappings"]:
        if mapping["pattern"] in primary:
            return mapping["label"]
    return CONFIG["sect_rules"]["unknown_label"]


def normalize_religion_type(religion_str) -> str:
    """从宗教类型字段归一化"""
    if pd.isna(religion_str) or not religion_str:
        return CONFIG["religion_type_rules"]["unknown_label"]
    s = str(religion_str).strip()
    for mapping in CONFIG["religion_type_rules"]["mappings"]:
        if mapping["pattern"] in s:
            return mapping["label"]
    return CONFIG["religion_type_rules"]["unknown_label"]


def normalize_sect_all(sect_str) -> str:
    """提取所有宗派，保留完整信息，用分号分隔
    例如："密教,观音体系" → "密教;观音"
          "观音体系；地藏体系" → "观音;地藏"
    """
    if pd.isna(sect_str) or not sect_str:
        return CONFIG["sect_rules"]["unknown_label"]
    s = str(sect_str).strip()
    import re
    parts = re.split(r'[；;，,]', s)
    seen = set()
    result = []
    for p in parts:
        p = p.strip()
        for mapping in CONFIG["sect_rules"]["mappings"]:
            if mapping["pattern"] in p and mapping["label"] not in seen:
                result.append(mapping["label"])
                seen.add(mapping["label"])
                break
    return ";".join(result) if result else CONFIG["sect_rules"]["unknown_label"]


def normalize_subject(sect_str, deity_str) -> str:
    """从[宗派倾向]的体系标签提取主体（五大体系），
    其次从[所造佛像名称]补充提取"""
    # 第一步：从宗派倾向字段提取体系标签（优先）
    if not pd.isna(sect_str) and sect_str:
        s = str(sect_str)
        for mapping in CONFIG["subject_rules"]["mappings"]:
            if mapping["pattern"] in s:
                return mapping["label"]
    # 第二步：从所造佛像名称补充提取（fallback）
    if pd.isna(deity_str) or not deity_str:
        return CONFIG["subject_rules"]["unknown_label"]
    d = str(deity_str)
    for mapping in CONFIG["subject_rules"].get("fallback_patterns", []):
        if mapping["pattern"] in d:
            return mapping["label"]
    return CONFIG["subject_rules"]["unknown_label"]


def normalize_gender(gender_str) -> str:
    """性别归一化"""
    if pd.isna(gender_str) or not gender_str:
        return "未知"
    s = str(gender_str).strip()
    if "男" in s:
        return "男"
    if "女" in s or "雌" in s:
        return "女"
    return "未知"


def clean_vow(v) -> str:
    """清理祈愿内容编码值：去除全部空白"""
    return re.sub(r"\s+", "", str(v)) if not pd.isna(v) else ""


def normalize_vow_main(vow_l1) -> str:
    """祈愿内容一级编码归一化：去空白、复合值取主成分、跨维度误标修正。
    对应《祈愿内容判定规则》v3.0（含四恩三有）的 A-H 八类词表；
    "修证悟道"是造像原因规则的大类，出现在祈愿列属误标，统一修正为"修行证悟"。"""
    s = clean_vow(vow_l1)
    if not s or s == "nan":
        return "信息不详"
    first = re.split(r"[、;；,，]", s)[0]
    first = first or "信息不详"
    return CONFIG["vow_rules"]["l1_fixes"].get(first, first)


def normalize_vow_l2(vow_l2) -> str:
    """祈愿内容二级编码归一化到 v3.0 二级词表（vow_rules.l2_mapping）。
    括号细目保留原样，仅映射括号前的类目名；已合规的值原样通过。
    分割为括号感知（细目括号内的"、"不作为分隔符）。"""
    s = clean_vow(vow_l2)
    if not s or s == "nan":
        return "信息不详"
    mapping = CONFIG["vow_rules"]["l2_mapping"]

    # 括号感知的顶层分割
    parts, buf, depth = [], [], 0
    for ch in s:
        if ch in "（(":
            depth += 1
            buf.append(ch)
        elif ch in "）)":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif depth == 0 and ch in ";；、,，":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))

    def map_item(item: str) -> str:
        m = re.match(r"^(.+?)[（(](.+)[)）]$", item.strip())
        if m:
            name, detail = m.group(1), m.group(2)
            return f"{mapping.get(name, name)}({detail})"
        return mapping.get(item.strip(), item.strip())

    out = [map_item(p) for p in parts if p.strip()]
    return "；".join(out) or "信息不详"


def normalize_makeup(makeup_str) -> str:
    """妆造类型归一化（对应《妆造类型归一化规则》v1.1）：
    新造 / 新造兼妆修 / 重妆 / 重修 / 不详。
    关键点：仅含"镌妆"亦归入"新造兼妆修"（镌造+妆銮，含新建属性，
    如 #48 何仪兴造像记）；缺失值统一为"不详"。"""
    if pd.isna(makeup_str):
        return "不详"
    s = re.sub(r"\s+", "", str(makeup_str))
    if not s or s in ("无", "[不详]", "nan"):
        return "不详"
    has_new = "新造" in s
    has_decor = ("重修" in s) or ("重妆" in s) or ("镌妆" in s)
    if has_new and has_decor:
        return "新造兼妆修"
    if has_new:
        return "新造"
    if "镌妆" in s:
        # 仅"镌妆"=雕刻+妆銮，含新建属性 → 新造兼妆修（规则 v1.1，如 #48 何仪兴造像记）
        return "新造兼妆修"
    if "重妆" in s:
        return "重妆"
    if "重修" in s:
        return "重修"
    return "不详"


# 实践行为二级编码的动作类别词表（用于妆造-实践一致性校验）
PRACTICE_MAKEUP_WORDS = ("妆銮彩绘", "复新重修", "金装宝饰", "妆修")
PRACTICE_CREATE_WORDS = ("发心造像", "镌刻雕造", "绘塑造像", "开窟凿洞", "建寺创殿", "造塔建幢")


def check_makeup_practice_contradiction(makeup_norm: str, practice_l2: str) -> str:
    """校验妆造类型与实践行为编码是否矛盾（2026-09 妆造分类建议新增的系统性校验步骤）。
    返回矛盾说明字符串，无矛盾返回空串。"""
    if pd.isna(practice_l2):
        return ""
    s = str(practice_l2)
    has_makeup_act = any(w in s for w in PRACTICE_MAKEUP_WORDS)
    has_create_act = any(w in s for w in PRACTICE_CREATE_WORDS)
    if makeup_norm == "新造" and has_makeup_act:
        return "妆造=纯新造 但实践行为含妆修动作（妆銮彩绘/复新重修等）"
    if makeup_norm == "重妆" and has_create_act and not has_makeup_act:
        return "妆造=重妆 但实践行为仅含新造动作（发心造像/镌刻雕造等）"
    return ""


# ===================================================================
# 主流程
# ===================================================================

def main():
    print(f"[1/3] 读取 Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name=0, dtype=str)

    # 去除完全空行
    df = df.dropna(how="all").reset_index(drop=True)
    total = len(df)
    print(f"      共读取 {total} 条题记")

    print("[2/3] 执行归一化...")

    # --- 地区归一化 ---
    df["region_short"] = df["地点"].apply(normalize_region)

    # --- 时间归一化 ---
    df["year_start"] = df["公元纪年"].apply(extract_year_start)
    df["period"] = df["year_start"].apply(normalize_period)

    # --- 阶层归一化 ---
    # normalize_class_new returns (class_type, class_unit, mixed_detail)
    classes = df.apply(
        lambda row: normalize_class_new(row.get("阶层"), row.get("造像者身份表述")),
        axis=1, result_type="expand"
    )
    df["class_type"] = classes[0]
    df["class_unit"] = classes[1]
    df["class_types"] = classes[2]
    # 生成可读的 class_label
    df["class_label"] = df.apply(
        lambda row: "群体(" + row["class_types"].replace(";", "/") + ")" if row["class_unit"] == "群体"
                    else (row["class_type"] + "(" + row["class_unit"] + ")" if row["class_unit"] not in ["未知", "个人"]
                          else row["class_type"]),
        axis=1
    )

    # --- 宗派提取（主宗派） ---
    col_sect = "宗派倾向(主宗派倾向；副宗派倾向）"
    df["sect_main"] = df[col_sect].apply(normalize_sect)

    # --- 宗派提取（全部，保留多宗派信息） ---
    df["sect_all"] = df[col_sect].apply(normalize_sect_all)

    # --- 宗教类型归一化（比宗派更上层：佛教/道教/混合/儒教） ---
    df["religion_type"] = df["宗教类型"].apply(normalize_religion_type)

    # --- 主体提取（从宗派倾向+造像名称提取主尊） ---
    col_sect = "宗派倾向(主宗派倾向；副宗派倾向）"
    df["subject"] = df.apply(
        lambda row: normalize_subject(row.get(col_sect), row.get("所造佛像名称")),
        axis=1
    )

    # --- 性别归一化 ---
    df["gender_normalized"] = df["性别"].apply(normalize_gender)

    # --- 祈愿内容编码归一化（v3.0 词表，含四恩三有） ---
    df["vow_main"] = df["祈愿内容（一级编码）"].apply(normalize_vow_main)
    df["vow_detail"] = df["祈愿内容（二级编码）"].apply(clean_vow)
    df["vow_l2_norm"] = df["祈愿内容（二级编码）"].apply(normalize_vow_l2)

    # --- 妆造类型归一化（妆造类型归一化规则 v1.1） ---
    df["makeup_normalized"] = df["妆造类型"].apply(normalize_makeup)

    # --- 校验：妆造类型 vs 实践行为一致性（2026-09 建议新增） ---
    contradictions = []
    for _, r in df.iterrows():
        msg = check_makeup_practice_contradiction(
            r["makeup_normalized"], r.get("实践行为（二级编码）", ""))
        if msg:
            contradictions.append(f"#{r['题记序号']} {r['题记名称']}: {msg}")
    print(f"      妆造分布: {df['makeup_normalized'].value_counts().to_dict()}")
    print(f"      妆造-实践矛盾校验: {len(contradictions)} 条需人工复核")
    if contradictions:
        with open(OUTPUT_CSV.parent / "makeup_practice_contradictions.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(contradictions))

    # 统计信息
    print(f"      地区分布: {df['region_short'].value_counts().to_dict()}")
    print(f"      时间分期: {df['period'].value_counts().to_dict()}")
    print(f"      class_unit: {df['class_unit'].value_counts().to_dict()}")
    print(f"      class_type: {df['class_type'].value_counts().to_dict()}")
    print(f"      阶层分布: {df['class_label'].value_counts().to_dict()}")
    print(f"      宗派分布(主): {df['sect_main'].value_counts().to_dict()}")
    print(f"      宗派分布(全): {df['sect_all'].value_counts().to_dict()}")
    print(f"      主体分布: {df['subject'].value_counts().to_dict()}")
    print(f"      宗教类型: {df['religion_type'].value_counts().to_dict()}")
    print(f"      性别分布: {df['gender_normalized'].value_counts().to_dict()}")
    print(f"      祈愿内容(L1归一): {df['vow_main'].value_counts().to_dict()}")
    l2_check = df['vow_l2_norm'].apply(lambda s: any(p.split('(')[0] not in CONFIG['vow_rules']['l2_vocab']
                                                     for p in s.split('；')))
    bad = df.loc[l2_check, 'vow_l2_norm'].value_counts()
    print(f"      祈愿L2归一后不在v3.0词表的取值: {bad.to_dict() if len(bad) else '无 ✓'}")

    # 排序（按题记序号）
    if "题记序号" in df.columns:
        df["_sort"] = pd.to_numeric(df["题记序号"], errors="coerce")
        df = df.sort_values("_sort").drop(columns=["_sort"])

    # --- 输出 CSV（保留所有原始列 + 新增归一化列） ---
    print(f"[3/3] 写入 CSV → {OUTPUT_CSV}")
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # 同时输出一份 JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"      写入 JSON → {OUTPUT_JSON}")
    print("      CSV/JSON 完成！")

    # --- 可选：MySQL 输出 ---
    if "--mysql" in sys.argv:
        print("\n[可选] 写入 MySQL...")
        try:
            from sqlalchemy import create_engine, text
            url = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset=utf8mb4"
            engine = create_engine(url)

            col_sect = "宗派倾向(主宗派倾向；副宗派倾向）"
            df.to_sql("_temp_import", engine, if_exists="replace", index=False, chunksize=200)
            print("      临时表写入完成，可通过 export_to_mysql.py 导入正式表结构")
        except Exception as e:
            print(f"      MySQL 写入失败: {e}")
            print("      提示: 请确认已安装 pymysql (pip install pymysql sqlalchemy) 且 MySQL 已启动")

    print("      全部完成！")


if __name__ == "__main__":
    main()
