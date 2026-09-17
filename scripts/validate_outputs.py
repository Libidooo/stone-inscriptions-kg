#!/usr/bin/env python3
"""验证所有输出文件（适配 graph_data.json v4.0 list 结构）"""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. 验证 graph_data.json
print("=== Graph Data Validation ===")
with open(r'V:\图谱\dashboard\data\graph_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f"Version: {data['version']}")
nodes = data['nodes']
inscriptions = [n for n in nodes if n['type'] == 'inscription']
hubs = [n for n in nodes if n['type'] == 'hub']
print(f"Inscriptions: {len(inscriptions)}")
print(f"Hub nodes: {len(hubs)} (by category: ", end='')
by_cat = {}
for h in hubs:
    by_cat[h['category']] = by_cat.get(h['category'], 0) + 1
print(by_cat, ")")
print(f"Edges: {len(data['edges'])}")
s = inscriptions[0]
print(f"Sample: id={s['id']} name={s['name']} period={s['period']} class={s['classType']} "
      f"sect={s['sect']} gender={s['gender']} vow={s.get('vow')}/{s.get('vowDetail')}")
cfg = data['config']
print(f"Sect colors: {len(cfg['sectColors'])} entries")
print(f"Periods: {cfg['periodOrder']}")
print(f"Classes: {cfg['classOrder']}")
print(f"Regions geo: {cfg['regionGeoOrder']}")
print(f"Vow order: {cfg.get('vowOrder')}")
print(f"Stats.vows: {data['stats'].get('vows')}")

# 2. 文件大小
for path, label in [
    (r'V:\图谱\data\cleaned\inscriptions_clean.csv', 'CSV'),
    (r'V:\图谱\dashboard\data\graph_data.json', 'JSON'),
    (r'V:\图谱\scripts\01_extract_and_clean.py', 'Script 1'),
    (r'V:\图谱\scripts\02_generate_graph_json.py', 'Script 2'),
    (r'V:\图谱\scripts\05_update_vows_neo4j.py', 'Script 5'),
    (r'V:\图谱\scripts\import_to_neo4j.cypher', 'Cypher Import'),
    (r'V:\图谱\scripts\query_aggregate.cypher', 'Cypher Query'),
    (r'V:\图谱\dashboard\index.html', 'HTML'),
    (r'V:\图谱\dashboard\js\main.js', 'JS'),
    (r'V:\图谱\dashboard\css\style.css', 'CSS'),
]:
    size = os.path.getsize(path)
    print(f"  {label}: {path.split(os.sep)[-1]} ({size/1024:.1f} KB)")

# 3. 验证 CSV
import pandas as pd
df = pd.read_csv(r'V:\图谱\data\cleaned\inscriptions_clean.csv', encoding='utf-8-sig')
print(f"\nCSV rows: {len(df)}, columns: {len(df.columns)}")
expected_cols = ['题记序号', '题记名称', '时间', '公元纪年', '地点', '窟位',
    '造像者人数', '性别', '所造佛像名称', '出资者', '造像者身份表述',
    '阶层', '社邑组织', '实践行为（一级编码）', '实践行为（二级编码）',
    '祈愿内容（一级编码）', '祈愿内容（二级编码）',
    '造像原因（一级编码）', '造像原因（二级编码）',
    '关联历史事件', '经文', '妆造类型', '宗教类型',
    '宗派倾向(主宗派倾向；副宗派倾向）', '备注',
    'region_short', 'year_start', 'period', 'class_label', 'sect_main',
    'religion_type', 'gender_normalized', 'vow_main', 'vow_detail', 'vow_l2_norm',
    'makeup_normalized']
for col in expected_cols:
    assert col in df.columns, f"Missing column: {col}"
print(f"All {len(expected_cols)} columns present OK")
print(f"Regions: {df['region_short'].value_counts().to_dict()}")
print(f"Periods: {df['period'].value_counts().to_dict()}")
print(f"Classes: {df['class_label'].value_counts().to_dict()}")
print(f"Sects: {df['sect_main'].value_counts().to_dict()}")
print(f"Genders: {df['gender_normalized'].value_counts().to_dict()}")
print(f"Vows(L1): {df['vow_main'].value_counts().to_dict()}")

print("\n=== All validations passed ===")
