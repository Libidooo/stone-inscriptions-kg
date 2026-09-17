from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录
#!/usr/bin/env python3
"""对比 5.21实体（新基准）与 5.7实体.xlsx（旧基准）的差异"""
import sys, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')


NEW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser('~'), 'Downloads', '5.21实体 - Sheet1.csv')
OLD = str(ROOT / '5.7实体.xlsx')

df_new = pd.read_csv(NEW, dtype=str, encoding='utf-8-sig').fillna('')
df_old = pd.read_excel(OLD, sheet_name=0, dtype=str).fillna('')

print(f"新(5.21): {len(df_new)} 行 x {len(df_new.columns)} 列")
print(f"旧(5.7):  {len(df_old)} 行 x {len(df_old.columns)} 列")

# 列对比
cols_new, cols_old = list(df_new.columns), list(df_old.columns)
print(f"\n列完全一致: {cols_new == cols_old}")
if cols_new != cols_old:
    print("仅新有:", [c for c in cols_new if c not in cols_old])
    print("仅旧有:", [c for c in cols_old if c not in cols_new])

# 按题记序号对齐
new_ids = set(df_new['题记序号'])
old_ids = set(df_old['题记序号'])
print(f"\n序号新增({len(new_ids - old_ids)}): {sorted(new_ids - old_ids, key=lambda x: int(x) if x.isdigit() else 99999)}")
print(f"序号删除({len(old_ids - new_ids)}): {sorted(old_ids - new_ids, key=lambda x: int(x) if x.isdigit() else 99999)}")

merged = df_old.merge(df_new, on='题记序号', how='inner', suffixes=('_old', '_new'))
print(f"可对齐行数: {len(merged)}")

# 逐列统计差异
print("\n=== 各列差异统计 ===")
diff_rows_by_col = {}
for c in cols_new:
    if c == '题记序号' or c not in cols_old:
        continue
    co, cn = c + '_old', c + '_new'
    if co not in merged.columns or cn not in merged.columns:
        continue
    mask = merged[co].str.strip() != merged[cn].str.strip()
    n = int(mask.sum())
    if n > 0:
        diff_rows_by_col[c] = n
        print(f"{c}: {n} 行有差异")

# 明细：按列输出前若干条差异
print("\n=== 差异明细 ===")
for c, n in sorted(diff_rows_by_col.items(), key=lambda x: -x[1]):
    co, cn = c + '_old', c + '_new'
    mask = merged[co].str.strip() != merged[cn].str.strip()
    sub = merged.loc[mask, ['题记序号', co, cn]]
    print(f"\n--- {c}（{n} 行）---")
    for _, r in sub.head(60).iterrows():
        print(f"  #{r['题记序号']}: [{str(r[co])[:60]}] -> [{str(r[cn])[:60]}]")
    if n > 60:
        print(f"  ...（其余 {n-60} 行略，见完整输出文件）")

# 完整明细写文件
with open(str(ROOT / 'data' / 'cleaned' / 'diff_521_vs_57.txt'), 'w', encoding='utf-8') as f:
    for c, n in diff_rows_by_col.items():
        co, cn = c + '_old', c + '_new'
        mask = merged[co].str.strip() != merged[cn].str.strip()
        f.write(f"\n===== {c} ({n} rows) =====\n")
        for _, r in merged.loc[mask, ['题记序号', co, cn]].iterrows():
            f.write(f"#{r['题记序号']}: [{r[co]}] -> [{r[cn]}]\n")
print("\n完整明细: data/cleaned/diff_521_vs_57.txt")
