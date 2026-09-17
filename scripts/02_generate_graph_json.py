#!/usr/bin/env python3
"""
石刻造像题记知识图谱 - 生成前端网络图 JSON
输入: 清洗后的 CSV (inscriptions_clean.csv)
输出: dashboard/data/graph_data.json (力导向网络图格式)

使用方法: python 02_generate_graph_json.py
"""

import json
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict

CSV_PATH = Path(r"V:\图谱\data\cleaned\inscriptions_clean.csv")
OUTPUT_JSON = Path(r"V:\图谱\dashboard\data\graph_data.json")
CONFIG_PATH = Path(r"V:\图谱\data\config\normalization_rules.json")

PERIOD_ORDER = ["隋", "初唐", "武周", "盛唐", "中唐", "晚唐", "五代", "北宋", "南宋", "不详"]
CLASS_ORDER = ["工匠", "信众", "僧侣", "士人", "官员", "未知"]

REGION_GEO_ORDER = [
    "广元", "绵阳", "巴中", "成都", "安岳",
    "资中", "内江", "眉山", "蒲江", "大足", "其他"
]

# 祈愿内容一级编码展示顺序（对应祈愿内容判定规则 v3.0：A-H 类）
VOW_ORDER = ["超度往生", "现世福报", "国邦安宁", "佛法弘传", "修行证悟", "游观纪胜", "杂缘祈愿",
             "修证悟道", "信息不详"]

# 妆造类型归一化展示顺序（妆造类型归一化规则 v1.1）
MAKEUP_ORDER = ["新造", "新造兼妆修", "重妆", "重修", "不详"]

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def make_hub_id(cat, val):
    """生成属性枢纽节点的唯一ID"""
    return f"hub_{cat}_{val}"


def main():
    print(f"读取清洗数据: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # ─── 1. 题记节点 ───
    inscription_nodes = []
    for _, row in df.iterrows():
        inscription_nodes.append({
            "id": str(row.get("题记序号", "")),
            "name": str(row.get("题记名称", "")),
            "type": "inscription",
            "group": "inscription",
            "region": str(row.get("region_short", "")),
            "period": str(row.get("period", "不详")),
            "class": str(row.get("class_label", "未知")),
            "classUnit": str(row.get("class_unit", "未知")),
            "classType": str(row.get("class_type", "未知")),
            "classTypes": str(row.get("class_types", "")),
            "sect": str(row.get("sect_main", "无法判定")),
            "sectAll": str(row.get("sect_all", "无法判定")),
            "subject": str(row.get("subject", "无法判定")),
            "religionType": str(row.get("religion_type", "无法判定")),
            "gender": str(row.get("gender_normalized", "未知")),
            "vow": str(row.get("vow_main", "信息不详")) or "信息不详",
            "vowDetail": str(row.get("vow_detail", "信息不详")) or "信息不详",
            "makeup": str(row.get("makeup_normalized", "不详")) or "不详",
            "makeupRaw": str(row.get("妆造类型", "")).strip(),
            "deity": str(row.get("所造佛像名称", "")),
            "patron": str(row.get("出资者", "")),
            "year_raw": str(row.get("公元纪年", "")),
            "year_start": None if pd.isna(row.get("year_start")) else int(row["year_start"]),
            "identity": str(row.get("造像者身份表述", "")),
            "location": str(row.get("地点", "")),
            "religion": str(row.get("宗教类型", "")),
        })

    id_set = {n["id"] for n in inscription_nodes}

    # ─── 2. 属性枢纽节点 ───
    # 收集所有唯一属性值
    hub_data = {}  # hub_id -> {name, category, count}
    edge_list = []  # {source: inscription_id, target: hub_id, weight: 1}

    # 地区
    for val in df["region_short"].unique():
        hid = make_hub_id("region", val)
        cnt = int((df["region_short"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "region", "count": cnt}

    # 时间分期
    for val in df["period"].unique():
        hid = make_hub_id("period", val)
        cnt = int((df["period"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "period", "count": cnt}

    # 阶层
    for val in df["class_label"].unique():
        hid = make_hub_id("class", val)
        cnt = int((df["class_label"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "class", "count": cnt}

    # 宗派
    for val in df["sect_main"].unique():
        hid = make_hub_id("sect", val)
        cnt = int((df["sect_main"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "sect", "count": cnt}

    # 宗教类型
    for val in df["religion_type"].unique():
        hid = make_hub_id("religion", val)
        cnt = int((df["religion_type"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "religion", "count": cnt}

    # 主体（造像题材）
    for val in df["subject"].unique():
        hid = make_hub_id("subject", val)
        cnt = int((df["subject"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "subject", "count": cnt}

    # 祈愿内容（一级编码归一化列 vow_main，由 01 脚本生成）
    for val in df["vow_main"].unique():
        hid = make_hub_id("vow", val)
        cnt = int((df["vow_main"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "vow", "count": cnt}

    # 妆造类型（归一化列 makeup_normalized，规则 v1.1）
    for val in df["makeup_normalized"].unique():
        hid = make_hub_id("makeup", val)
        cnt = int((df["makeup_normalized"] == val).sum())
        hub_data[hid] = {"id": hid, "name": val, "category": "makeup", "count": cnt}

    # ─── 3. 连线：每条题记 → 其属性枢纽节点 ───
    for _, row in df.iterrows():
        ins_id = str(row.get("题记序号", ""))
        # 地区
        v = str(row.get("region_short", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("region", v), "type": "LOCATED_IN"})
        # 时间
        v = str(row.get("period", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("period", v), "type": "FROM_PERIOD"})
        # 阶层
        v = str(row.get("class_label", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("class", v), "type": "HAS_CLASS"})
        # 宗派
        v = str(row.get("sect_main", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("sect", v), "type": "BELONGS_TO"})
        # 宗教类型
        v = str(row.get("religion_type", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("religion", v), "type": "HAS_RELIGION"})
        # 主体
        v = str(row.get("subject", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("subject", v), "type": "DEPICTS"})
        # 祈愿内容
        v = str(row.get("vow_main", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("vow", v), "type": "HAS_VOW"})
        # 妆造类型
        v = str(row.get("makeup_normalized", ""))
        if v:
            edge_list.append({"source": ins_id, "target": make_hub_id("makeup", v), "type": "HAS_MAKEUP"})

    # 去重
    seen_edges = set()
    unique_edges = []
    for e in edge_list:
        key = (e["source"], e["target"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    # ─── 4. 组装全部节点 ───
    all_nodes = []
    all_nodes.extend(inscription_nodes)
    for hid, hdata in hub_data.items():
        all_nodes.append({
            "id": hid,
            "name": hdata["name"],
            "type": "hub",
            "group": hdata["category"],
            "category": hdata["category"],
            "count": hdata["count"],
        })

    # ─── 5. 统计 ───
    stats = {
        "total": len(inscription_nodes),
        "hubNodes": len(hub_data),
        "edges": len(unique_edges),
        "sects": [s for s in df["sect_main"].value_counts().index.tolist()],
        "religionTypes": [s for s in df["religion_type"].value_counts().index.tolist()],
        "regions": [s for s in df["region_short"].value_counts().index.tolist()],
        "subjects": [s for s in df["subject"].value_counts().index.tolist()],
        "vows": sorted(df["vow_main"].unique().tolist(),
                       key=lambda v: VOW_ORDER.index(v) if v in VOW_ORDER else 99),
        "makeups": sorted(df["makeup_normalized"].unique().tolist(),
                          key=lambda v: MAKEUP_ORDER.index(v) if v in MAKEUP_ORDER else 99),
    }

    # ─── 6. 最终输出 ───
    graph_data = {
        "version": "4.1",
        "description": "四川地区佛教石窟铭文知识图谱 - v4.1 with vow(祈愿v3.0含四恩三有) + makeup(妆造v1.1)",
        "config": {
            "sectColors": CONFIG["sect_colors"],
            "subjectColors": CONFIG["subject_colors"],
            "religionTypeColors": CONFIG["religion_type_colors"],
            "genderColors": CONFIG["gender_colors"],
            "periodOrder": PERIOD_ORDER,
            "classOrder": CLASS_ORDER,
            "regionGeoOrder": REGION_GEO_ORDER,
            "vowOrder": VOW_ORDER,
            "makeupOrder": MAKEUP_ORDER,
        },
        "stats": stats,
        "nodes": all_nodes,
        "edges": unique_edges,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)

    print(f"写入前端 JSON → {OUTPUT_JSON}")
    print(f"  题记节点: {len(inscription_nodes)}")
    print(f"  属性枢纽节点: {len(hub_data)}")
    print(f"  连线: {len(unique_edges)}")
    print(f"  文件大小: {OUTPUT_JSON.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
