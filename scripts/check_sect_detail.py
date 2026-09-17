#!/usr/bin/env python3
"""精确检查宗派倾向字段的解析问题"""
import pandas as pd, json
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录


df = pd.read_csv(str(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv'), encoding='utf-8-sig')
col_sect = '宗派倾向(主宗派倾向；副宗派倾向）'

# Check what normalize_sect outputs vs raw
raw_sects = df[col_sect].value_counts()
print("=== 原始宗派倾向字段 (TOP 30) ===")
for v, c in raw_sects.head(30).items():
    mapped = "?"
    print(f"  [{v}] → ? (count={c})")

# Check 宗教类型 values more precisely
print("\n=== 宗教类型 (所有唯一值) ===")
for v in sorted(df['宗教类型'].unique()):
    c = (df['宗教类型'] == v).sum()
    print(f"  [{v}] = {c}")

# How many have 道教 in 宗派倾向?
has_daojiao = df[col_sect].str.contains('道教', na=False)
print(f"\n=== 宗派倾向包含'道教'的条目: {has_daojiao.sum()} ===")

# Check sect_main for entries where 宗教类型=道教
dao_rel = df[df['宗教类型'] == '道教']
print(f"\n=== 宗教类型=道教 的 sect_main 分布 ===")
print(dao_rel['sect_main'].value_counts().to_string())

# What about 禅宗?
has_chan = df[col_sect].str.contains('禅宗', na=False)
print(f"\n=== 宗派倾向包含'禅宗': {has_chan.sum()} ===")

# 华严?
has_huayan = df[col_sect].str.contains('华严', na=False)
print(f"=== 宗派倾向包含'华严': {has_huayan.sum()} ===")

# 三教?
has_sanjiao = df[col_sect].str.contains('三教', na=False)
print(f"=== 宗派倾向包含'三教': {has_sanjiao.sum()} ===")
