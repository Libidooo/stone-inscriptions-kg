#!/usr/bin/env python3
"""验证清洗输出"""
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录


df = pd.read_csv(str(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv'), encoding='utf-8-sig')

print("=== 原始阶层分布 ===")
print(df['阶层'].value_counts().to_string())

print("\n=== 官员样本 (前20) ===")
officials = df[df['class_label'] == '官员']
for i, row in officials.head(20).iterrows():
    print(f"  #{row['题记序号']} | 阶层=[{row['阶层']}] | 身份=[{row['造像者身份表述']}]")

print("\n=== 未知样本 (前10) ===")
unknown = df[df['class_label'] == '未知']
for i, row in unknown.head(10).iterrows():
    print(f"  #{row['题记序号']} | 阶层=[{row['阶层']}] | 身份=[{row['造像者身份表述']}]")

print("\n=== 工匠样本 ===")
artisans = df[df['class_label'] == '工匠']
for i, row in artisans.head(10).iterrows():
    print(f"  #{row['题记序号']} | 阶层=[{row['阶层']}] | 身份=[{row['造像者身份表述']}]")
