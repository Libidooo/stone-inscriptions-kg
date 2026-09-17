#!/usr/bin/env python3
"""详细检查年份异常值的归属阶段"""
import json
with open(r'V:\图谱\dashboard\data\graph_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== 年份<581 的题记 ===")
for s in data['nodes']['inscriptions']:
    y = s['year_start']
    if y is not None and y < 581:
        print(f"  id={s['id']} | year={y} | period='{s['period']}' | name={s['name']}")

print("\n=== 年份>1279 的题记 ===")
for s in data['nodes']['inscriptions']:
    y = s['year_start']
    if y is not None and y > 1279:
        print(f"  id={s['id']} | year={y} | period='{s['period']}' | name={s['name']}")

print("\n=== 无年份的题记(前10) ===")
for s in data['nodes']['inscriptions']:
    if s['year_start'] is None:
        print(f"  id={s['id']} | period='{s['period']}' | year_raw={s['year_raw']} | name={s['name']}")
