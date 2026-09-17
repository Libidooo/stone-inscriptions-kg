#!/usr/bin/env python3
"""Verify alignment between 5.7实体.xlsx and 题记原文.csv"""


import pandas as pd, sys
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录
sys.stdout.reconfigure(encoding='utf-8')

df_excel = pd.read_excel(str(ROOT / '5.7实体.xlsx'))
df_csv   = pd.read_csv(str(ROOT / '题记原文.csv'), encoding='utf-8-sig')

print('=== Excel 题记序号 ===')
print('min=%d, max=%d, count=%d, unique=%s' % (
    df_excel['题记序号'].min(), df_excel['题记序号'].max(),
    len(df_excel), df_excel['题记序号'].is_unique))

print()
print('=== CSV 序号 ===')
print('min=%d, max=%d, count=%d, unique=%s' % (
    df_csv['序号'].min(), df_csv['序号'].max(),
    len(df_csv), df_csv['序号'].is_unique))

excel_seqs = set(df_excel['题记序号'].tolist())
csv_seqs   = set(df_csv['序号'].tolist())

only_excel = excel_seqs - csv_seqs
only_csv   = csv_seqs - excel_seqs

print()
print('In Excel but not in CSV: %s' % (sorted(only_excel) if only_excel else 'None'))
print('In CSV but not in Excel: %s' % (sorted(only_csv) if only_csv else 'None'))

# Merge and check missing
df = df_excel.merge(df_csv, left_on='题记序号', right_on='序号', how='left')
missing = df[df['题记原文'].isna()]
print()
print('=== %d missing 题记原文 ===' % len(missing))

for _, row in missing.iterrows():
    csv_row = df_csv[df_csv['序号'] == row['题记序号']]
    if len(csv_row) == 0:
        print('  [%d] %s -> CSV 中无此序号' % (row['题记序号'], row['题记名称']))
    else:
        txt = csv_row['题记原文'].values[0]
        if pd.isna(txt) or txt.strip() == '':
            print('  [%d] %s -> CSV中原文为空' % (row['题记序号'], row['题记名称']))
        else:
            print('  [%d] %s -> CSV有原文(%d chars)但merge后为NaN(异常)' % (
                row['题记序号'], row['题记名称'], len(txt)))
