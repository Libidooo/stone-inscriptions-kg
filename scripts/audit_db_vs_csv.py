from pathlib import Path
import json
import os
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 Neo4j 库内编码属性与 5.21 清洗 CSV 的差异（实践行为/造像原因/妆造）"""
import sys, csv, requests
sys.stdout.reconfigure(encoding='utf-8')


URL = 'http://127.0.0.1:7474/db/neo4j/tx/commit'
def _db_auth():
    """凭据加载：环境变量 NEO4J_PASSWORD → data/config/db_local.json（已 gitignore）"""
    pw = os.environ.get('NEO4J_PASSWORD', '')
    if not pw:
        cfg = ROOT / 'data' / 'config' / 'db_local.json'
        if cfg.exists():
            pw = json.loads(cfg.read_text(encoding='utf-8')).get('password', '')
    if not pw:
        sys.exit('未提供 Neo4j 密码：设置环境变量 NEO4J_PASSWORD，或创建 data/config/db_local.json')
    return ('neo4j', pw)

AUTH = _db_auth()


def run(stmt, params=None):
    r = requests.post(URL, json={'statements': [{'statement': stmt, 'parameters': params or {}}]},
                      headers={'Content-Type': 'application/json'}, auth=AUTH, timeout=60)
    j = r.json()
    if j.get('errors'):
        print('ERROR:', j['errors'][0]['message'])
        return []
    return [d['row'] for d in j['results'][0]['data']] if j.get('results') else []


# 拉库内属性
db = {r[0]: {'p1': r[1] or '', 'p2': r[2] or '', 'c1': r[3] or '', 'c2': r[4] or '',
             'mk': r[5] or '', 'mkraw': r[6] or ''}
      for r in run("MATCH (i:Inscription) RETURN i.id, i.raw_实践1, i.raw_实践2, "
                   "i.raw_原因1, i.raw_原因2, i.makeup_normalized, i.raw_妆造")}

with open(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

diff_p, diff_c, diff_mk, diff_mraw = [], [], [], []
for row in rows:
    iid = row['题记序号']
    d = db.get(iid)
    if not d:
        continue
    p1 = (row.get('实践行为（一级编码）') or '').strip().rstrip('、;；,，').replace('、', '；')
    p2 = (row.get('实践行为（二级编码）') or '').strip().rstrip('、;；,，').replace('、', '；')
    if p1 != d['p1'].replace('、', '；') or p2 != d['p2'].replace('、', '；'):
        diff_p.append((iid, d['p1'], d['p2'], p1, p2))
    c1 = (row.get('造像原因（一级编码）') or '').strip()
    c2 = (row.get('造像原因（二级编码）') or '').strip()
    if c1 != d['c1'] or c2 != d['c2']:
        diff_c.append((iid, d['c1'], d['c2'], c1, c2))
    mkraw = (row.get('妆造类型') or '').strip()
    if mkraw != d['mkraw'].strip():
        diff_mraw.append((iid, d['mkraw'], mkraw))

print(f"实践行为 属性不一致: {len(diff_p)} 条")
for x in diff_p[:10]:
    print(f"  #{x[0]}: DB[{x[1]} | {x[2]}] CSV[{x[3]} | {x[4]}]")
if len(diff_p) > 10:
    print(f"  ... 其余 {len(diff_p)-10} 条")

print(f"\n造像原因 属性不一致: {len(diff_c)} 条")
for x in diff_c[:5]:
    print(f"  #{x[0]}: DB[{x[1]} | {x[2]}] CSV[{x[3]} | {x[4]}]")
if len(diff_c) > 5:
    print(f"  ... 其余 {len(diff_c)-5} 条")

print(f"\n妆造类型原始值不一致: {len(diff_mraw)} 条")
mk_dist = {}
for row in rows:
    raw = (row.get('妆造类型') or '').strip()
    has_new = '新造' in raw
    has_re = ('重修' in raw) or ('重妆' in raw) or ('镌妆' in raw)
    if not raw or raw in ('无', '[不详]'):
        v = '不详'
    elif has_new and has_re:
        v = '新造兼妆修'
    elif has_new:
        v = '新造'
    elif '重妆' in raw:
        v = '重妆'
    elif '重修' in raw:
        v = '重修'
    else:
        v = '不详'
    mk_dist[v] = mk_dist.get(v, 0) + 1
print("按规则 v1.0 计算的期望分布:", mk_dist)
db_mk = {}
for d in db.values():
    db_mk[d['mk']] = db_mk.get(d['mk'], 0) + 1
print("库内当前分布:", db_mk)
