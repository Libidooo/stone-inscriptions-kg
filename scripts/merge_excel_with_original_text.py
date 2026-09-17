#!/usr/bin/env python3
"""
Merge 5.7 entities Excel with original inscription text from CSV.
Output: $EXTERNAL_OUT_DIR/5.7实体含原文.{csv,xlsx}
"""

import pandas as pd, os, sys
sys.stdout.reconfigure(encoding='utf-8')

excel_path = r'V:\图谱\5.7实体.xlsx'
csv_path   = r'V:\图谱\题记原文.csv'
out_dir = os.environ.get('EXTERNAL_OUT_DIR', '')

df_excel = pd.read_excel(excel_path)
df_csv   = pd.read_csv(csv_path, encoding='utf-8-sig')

print(f'Excel: {df_excel.shape}')
print(f'CSV:   {df_csv.shape}')

# Merge on 题记序号 = 序号
df = df_excel.merge(df_csv, left_on='题记序号', right_on='序号', how='left')
print(f'Merged: {df.shape}')
print(f'Missing 题记原文: {df["题记原文"].isna().sum()}')

# Drop redundant 序号 column
df = df.drop(columns=['序号'])

# Write output
out_csv  = os.path.join(out_dir, '5.7实体含原文.csv')
out_xlsx = os.path.join(out_dir, '5.7实体含原文.xlsx')
df.to_csv(out_csv, index=False, encoding='utf-8-sig')
df.to_excel(out_xlsx, index=False)

print(f'CSV:  {out_csv}')
print(f'XLSX: {out_xlsx}')
print(f'Columns ({len(df.columns)}): {list(df.columns)}')
