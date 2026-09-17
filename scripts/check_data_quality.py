from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录
#!/usr/bin/env python3
"""检查数据质量：样本展示（适配 graph_data.json v4.0 list 结构）"""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')


with open(ROOT / 'dashboard' / 'data' / 'graph_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

inscriptions = [n for n in data['nodes'] if n['type'] == 'inscription']
cfg = data['config']

print("=== 题记样本（前5条）===")
for s in inscriptions[:5]:
    print(f"  id={s['id']} | period={s['period']} | class={s['classType']} | sect={s['sect']} "
          f"| gender={s['gender']} | year={s['year_raw']} | year_start={s['year_start']} "
          f"| vow={s.get('vow')}/{s.get('vowDetail')}")

print("\n=== 各阶层类型的题记数量 ===")
classes = {}
for s in inscriptions:
    classes[s['classType']] = classes.get(s['classType'], 0) + 1
for c, n in sorted(classes.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")

print("\n=== 各宗派的题记数量 ===")
sects = {}
for s in inscriptions:
    sects[s['sect']] = sects.get(s['sect'], 0) + 1
for c, n in sorted(sects.items(), key=lambda x: -x[1]):
    color = cfg['sectColors'].get(c, '#888')
    print(f"  {c}: {n} (color={color})")

print("\n=== 各祈愿一级编码的题记数量 ===")
vows = {}
for s in inscriptions:
    v = s.get('vow', '信息不详')
    vows[v] = vows.get(v, 0) + 1
order = cfg.get('vowOrder', [])
for c, n in sorted(vows.items(), key=lambda x: (-x[1], order.index(x[0]) if x[0] in order else 99)):
    print(f"  {c}: {n}")

print("\n=== 年份范围 ===")
years = [s['year_start'] for s in inscriptions if s['year_start'] is not None]
print(f"  min={min(years)}, max={max(years)}")
print(f"  无年份: {sum(1 for s in inscriptions if s['year_start'] is None)}")

print("\n=== 性别分布 ===")
genders = {}
for s in inscriptions:
    genders[s['gender']] = genders.get(s['gender'], 0) + 1
print(f"  分布: {genders}")
