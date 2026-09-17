#!/usr/bin/env python3
"""检查数据质量：样本展示"""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'V:\图谱\dashboard\data\graph_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 展示各字段的样本
inscriptions = data['nodes']['inscriptions']
cfg = data['config']

print("=== 题记样本（前5条）===")
for s in inscriptions[:5]:
    print(f"  id={s['id']} | period={s['period']} | class={s['class']} | sect={s['sect']} | gender={s['gender']} | year={s['year_raw']} | year_start={s['year_start']}")

print("\n=== 各阶层的题记数量 ===")
classes = {}
for s in inscriptions:
    classes[s['class']] = classes.get(s['class'], 0) + 1
for c, n in sorted(classes.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")

print("\n=== 各宗派的题记数量 ===")
sects = {}
for s in inscriptions:
    sects[s['sect']] = sects.get(s['sect'], 0) + 1
for c, n in sorted(sects.items(), key=lambda x: -x[1]):
    color = cfg['sectColors'].get(c, '#888')
    print(f"  {c}: {n} (color={color})")

print("\n=== 年份范围 ===")
years = [s['year_start'] for s in inscriptions if s['year_start'] is not None]
print(f"  min={min(years)}, max={max(years)}")
print(f"  无年份: {sum(1 for s in inscriptions if s['year_start'] is None)}")

print("\n=== 性别分布 + 男左女右偏移 ===")
genders = {}
offsets = {}
for s in inscriptions:
    genders[s['gender']] = genders.get(s['gender'], 0) + 1
    o = s['genderOffset']
    offsets[s['gender']] = offsets.get(s['gender'], 0) + 1
print(f"  分布: {genders}")
print(f"  有偏移的: {offsets}")
