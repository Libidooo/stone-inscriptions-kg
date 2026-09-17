#!/usr/bin/env python3
"""精确检查宗派字段的原始值"""
import pandas as pd

df = pd.read_csv(r'V:\图谱\data\cleaned\inscriptions_clean.csv', encoding='utf-8-sig')
col = '宗派倾向(主宗派倾向；副宗派倾向）'

# 写样本身份到文件
with open(r'V:\图谱\data\cleaned\sect_samples.txt', 'w', encoding='utf-8') as f:
    f.write("=== 所有唯一宗派倾向值 ===\n")
    for v, c in df[col].value_counts().items():
        f.write(f"  [{v}] = {c}\n")
    
    f.write("\n=== 宗教类型所有唯一值 ===\n")
    for v, c in df['宗教类型'].value_counts().items():
        f.write(f"  [{v}] = {c}\n")
    
    f.write("\n=== 宗教类型=道教的样本 ===\n")
    dao = df[df['宗教类型'] == '道教']
    for i, row in dao.head(10).iterrows():
        f.write(f"  #{row['题记序号']} | 宗派倾向=[{row[col]}] | 造像=[{row['所造佛像名称']}]\n")
    
    f.write("\n=== 包含'禅宗'的样本 ===\n")
    chan = df[df[col].str.contains('禅宗', na=False)]
    for i, row in chan.iterrows():
        f.write(f"  #{row['题记序号']} | 宗派倾向=[{row[col]}]\n")
    
    f.write("\n=== 包含'华严'的样本 ===\n")
    hy = df[df[col].str.contains('华严', na=False)]
    for i, row in hy.iterrows():
        f.write(f"  #{row['题记序号']} | 宗派倾向=[{row[col]}]\n")
    
    f.write("\n=== 包含'三教'的样本 ===\n")
    sj = df[df['宗教类型'].str.contains('三教|二教', na=False)]
    for i, row in sj.iterrows():
        f.write(f"  #{row['题记序号']} | 宗教类型=[{row['宗教类型']}] | 宗派倾向=[{row[col]}]\n")

print("Written to sect_samples.txt")
