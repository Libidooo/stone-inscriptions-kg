#!/usr/bin/env python3
"""分批导入数据到 joinmap"""
import json, subprocess, time
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录


# 读取数据和 JS 注入脚本
with open(str(ROOT / 'dashboard' / 'data' / 'graph_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

inscriptions = [n for n in data['nodes'] if n['type'] == 'inscription']

TARGET = "E67702CFF57FEE468CADC94B4C9EBA09"
BASE = "http://localhost:3456"

def eval_js(code):
    """Inject JS via CDP"""
    result = subprocess.run(
        ["curl.exe", "-s", "-X", "POST", f"{BASE}/eval?target={TARGET}",
         "-d", code],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout

# 1. 先清空
print("Clearing existing nodes...")
eval_js("_network.body.data.nodes.clear(); _network.body.data.edges.clear();")

# 2. 属性节点
print("Adding attribute nodes...")
attrs = []
for r in sorted(set(n['region'] for n in inscriptions)):
    attrs.append(f'{{id:"r_{r}",label:"{r}",group:"region",shape:"dot",size:25}}')
for p in ['隋','初唐','武周','盛唐','中唐','晚唐','五代','北宋','南宋','不详']:
    if any(n['period'] == p for n in inscriptions):
        sz = sum(1 for n in inscriptions if n['period'] == p)
        attrs.append(f'{{id:"p_{p}",label:"{p} ({sz})",group:"period",shape:"dot",size:max(15,min(30,{sz}*0.3))}}')
# classes
classes_ordered = ['工匠','信众','僧侣','士人','官员','未知']
for c in classes_ordered:
    if any(n['class'] == c for n in inscriptions):
        sz = sum(1 for n in inscriptions if n['class'] == c)
        attrs.append(f'{{id:"c_{c}",label:"{c} ({sz})",group:"class",shape:"dot",size:max(12,min(25,{sz}*0.3))}}')
# sects
sects_ordered = ['观音','净土','弥勒','药师','地藏','密教','禅宗','华严','天台','无法判定']
for s in sects_ordered:
    if any(n['sect'] == s for n in inscriptions):
        sz = sum(1 for n in inscriptions if n['sect'] == s)
        attrs.append(f'{{id:"s_{s}",label:"{s} ({sz})",group:"sect",shape:"dot",size:max(14,min(28,{sz}*0.3))}}')

# 分批添加属性节点 (50个一批)
batch_size = 50
for i in range(0, len(attrs), batch_size):
    batch = attrs[i:i+batch_size]
    js = f"_network.body.data.nodes.add([{','.join(batch)}]);"
    r = eval_js(js)
    print(f"  Attrs batch {i//batch_size + 1}/{(len(attrs)-1)//batch_size + 1}: {r[:50]}")
    time.sleep(0.1)

# 3. 题记节点 - 分批（每个inscription包含大量文本）
print("Adding inscription nodes...")
BATCH = 50
for i in range(0, len(inscriptions), BATCH):
    batch_ins = inscriptions[i:i+BATCH]
    node_defs = []
    for ins in batch_ins:
        nid = ins['id']
        name = ins['name'].replace('\\','\\\\').replace("'","\\'").replace('"','\\"')
        node_defs.append(
            f'{{id:"i_{nid}",label:"#{nid}",group:"inscription",'
            f'title:"{name}",'
            f'region:"{ins["region"]}",period:"{ins["period"]}",'
            f'class:"{ins["class"]}",sect:"{ins["sect"]}",'
            f'shape:"dot",size:4}}'
        )
    
    js = f"_network.body.data.nodes.add([{','.join(node_defs)}]);"
    r = eval_js(js)
    cnt = len(batch_ins)
    print(f"  Ins batch {i//BATCH + 1}/{(len(inscriptions)-1)//BATCH + 1}: +{cnt} nodes")
    time.sleep(0.1)

# 4. 添加边（每批次添加题记-属性边）
print("Adding edges...")
EDGE_BATCH = 50
all_edges = []
for ins in inscriptions:
    nid = ins['id']
    for attr_type, attr_val in [('r', ins['region']), ('p', ins['period']), 
                                  ('c', ins['class']), ('s', ins['sect'])]:
        all_edges.append(f'{{from:"i_{nid}",to:"{attr_type}_{attr_val}"}}')

for i in range(0, len(all_edges), EDGE_BATCH):
    batch_edges = all_edges[i:i+EDGE_BATCH]
    js = f"_network.body.data.edges.add([{','.join(batch_edges)}]);"
    r = eval_js(js)
    if (i // EDGE_BATCH) % 20 == 0:
        print(f"  Edges batch {i//EDGE_BATCH + 1}/{(len(all_edges)-1)//EDGE_BATCH + 1}")
    time.sleep(0.05)

print("=== DONE ===")
print(f"Total: {len(attrs)} attr nodes + {len(inscriptions)} inscription nodes + {len(all_edges)} edges")
