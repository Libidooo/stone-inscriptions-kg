#!/usr/bin/env python3
"""审核数据库中的异常条目"""
import pandas as pd

df = pd.read_csv(r'V:\图谱\data\cleaned\inscriptions_clean.csv', encoding='utf-8-sig')

print("=== 儒教条目 ===")
rujia = df[df['宗教类型'].str.contains('儒教', na=False)]
for i, row in rujia.iterrows():
    print(f"  #{row['题记序号']} | 宗教=[{row['宗教类型']}] | 题材=[{str(row['所造佛像名称'])[:40]}] | 地点=[{str(row['地点'])[:30]}]")

print("\n=== 道教条目(前10) ===")
dao = df[df['宗教类型'] == '道教'].head(10)
for i, row in dao.iterrows():
    print(f"  #{row['题记序号']} | 题材=[{str(row['所造佛像名称'])[:40]}] | 地点=[{str(row['地点'])[:30]}]")

print("\n=== 宗教类型分布 ===")
print(df['宗教类型'].value_counts().to_string())

print("\n=== 宗派分布 ===")
sect_col = '宗派倾向(主宗派倾向；副宗派倾向）'
print(df[sect_col].value_counts().head(20).to_string())

print("\n=== 无法判定宗派且非佛教的条目(前5) ===")
col = '宗派倾向(主宗派倾向；副宗派倾向）'
unk = df[(df[col] == '无法判定') & (~df['宗教类型'].str.contains('佛教', na=False))]
print(f"  共 {len(unk)} 条")
for i, row in unk.head(5).iterrows():
    print(f"  #{row['题记序号']} | 宗教=[{row['宗教类型']}] | 题材=[{str(row['所造佛像名称'])[:40]}]")

print("\n=== 空白名称/出资者的条目 ===")
empty = df[df['题记名称'].isna() | (df['题记名称'] == '') | df['题记名称'].str.strip().eq('')]
print(f"  空名称: {len(empty)}")

no_patron = df[df['出资者'].isna() | (df['出资者'] == '') | df['出资者'].str.contains('不详|无', na=False)]
print(f"  无出资者: {len(no_patron)}")

print("\n=== 6-10世纪的佛教条目数量 ===")
buddhist = df[df['宗教类型'] == '佛教']
print(f"  佛教: {len(buddhist)}")
taoist = df[df['宗教类型'] == '道教']
print(f"  道教: {len(taoist)}")
mixed = df[df['宗教类型'].str.contains('混合', na=False)]
print(f"  混合: {len(mixed)}")
