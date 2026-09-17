#!/usr/bin/env python3
"""检查宗教类型和宗派倾向字段的完整分布"""
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录


df = pd.read_csv(str(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv'), encoding='utf-8-sig')

print("=== 宗教类型 完整分布 ===")
rel = df['宗教类型'].value_counts()
for v, c in rel.items():
    print(f"  [{v}] = {c}")

print("\n=== 宗派倾向 完整分布 ===")
col = '宗派倾向(主宗派倾向；副宗派倾向）'
sect_raw = df[col].value_counts()
for v, c in sect_raw.items():
    print(f"  [{v}] = {c}")

print("\n=== 宗教类型 × 宗派倾向 交叉表 ===")
ct = pd.crosstab(df['宗教类型'], df[col])
print(ct.to_string())

print("\n=== 当前 sect_main 分布 ===")
print(df['sect_main'].value_counts().to_string())

print("\n=== 原始宗派倾向中未被 sect_main 覆盖的值 ===")
current_sects = set(df['sect_main'].unique())
for v in df[col].unique():
    if v not in current_sects and str(v) != 'nan':
        print(f"  未覆盖: [{v}]")
