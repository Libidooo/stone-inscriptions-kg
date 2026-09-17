#!/usr/bin/env python3
"""检查年份异常值"""
import json
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录
with open(str(ROOT / 'dashboard' / 'data' / 'graph_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)


print("=== 年份异常值 ===")
for s in data['nodes']['inscriptions']:
    y = s['year_start']
    if y is not None and (y < 500 or y > 1300):
        print(f"  id={s['id']} | year_raw={s['year_raw']} | year_start={y} | period={s['period']} | name={s['name'][:30]}")

print("\n=== 无年份的题记 ===")
count = 0
for s in data['nodes']['inscriptions']:
    if s['year_start'] is None:
        count += 1
        if count <= 5:
            print(f"  id={s['id']} | period={s['period']} | year_raw={s['year_raw']} | name={s['name'][:40]}")
print(f"  共{count}条无年份")
