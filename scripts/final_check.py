#!/usr/bin/env python3
"""最终验证：各字段分布"""
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录


df = pd.read_csv(str(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv'), encoding='utf-8-sig')

print("=== 宗派分布 (sect_main) ===")
for v, c in df['sect_main'].value_counts().items():
    print(f"  {v}: {c}")

print("\n=== 宗教类型分布 (religion_type) ===")
for v, c in df['religion_type'].value_counts().items():
    print(f"  {v}: {c}")

print("\n=== 宗教类型 × 宗派 交叉 ===")
ct = pd.crosstab(df['religion_type'], df['sect_main'])
for r in ct.index:
    for c in ct.columns:
        if ct.loc[r, c] > 0:
            print(f"  {r} × {c}: {ct.loc[r, c]}")
