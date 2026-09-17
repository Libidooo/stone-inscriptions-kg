#!/usr/bin/env python3
"""为 joinmap 生成批量导入JS"""
import json, os

with open(r'V:\图谱\dashboard\data\graph_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

inscriptions = [n for n in data['nodes'] if n['type'] == 'inscription']

# 收集唯一属性值
regions = sorted(set(n['region'] for n in inscriptions))
periods = sorted(set(n['period'] for n in inscriptions),
                 key=lambda p: {'隋':0,'初唐':1,'武周':2,'盛唐':3,'中唐':4,'晚唐':5,'五代':6,'北宋':7,'南宋':8,'不详':9}.get(p, 99))
classes = sorted(set(n['class'] for n in inscriptions))
sects = sorted(set(n['sect'] for n in inscriptions))
vows = sorted(set(n.get('vow', '信息不详') for n in inscriptions))

# 生成批处理：每批100条题记
BATCH_SIZE = 100

js_parts = []

# 添加地区节点
js_parts.append("// Regions")
for r in regions:
    js_parts.append(f'nodes.add({{id:"r_{r}",label:"{r}",group:"region",shape:"dot",size:20}});')

# 添加时间节点
js_parts.append("// Periods")
for p in periods:
    js_parts.append(f'nodes.add({{id:"p_{p}",label:"{p}",group:"period",shape:"dot",size:18}});')

# 添加阶层节点
js_parts.append("// Classes")
for c in classes:
    js_parts.append(f'nodes.add({{id:"c_{c}",label:"{c}",group:"class",shape:"dot",size:15}});')

# 添加宗派节点
js_parts.append("// Sects")
for s in sects:
    js_parts.append(f'nodes.add({{id:"s_{s}",label:"{s}",group:"sect",shape:"dot",size:17}});')

# 添加祈愿内容节点（一级编码）
js_parts.append("// Vows")
for v in vows:
    js_parts.append(f'nodes.add({{id:"w_{v}",label:"{v}",group:"vow",shape:"dot",size:16}});')

# 添加题记节点（分批次）
js_parts.append("// Inscriptions")
batch_num = 0
for i, ins in enumerate(inscriptions):
    nid = ins['id']
    name = ins['name'].replace('\\', '\\\\').replace("'", "\\'")
    region = ins['region']
    period = ins['period']
    cls = ins['class']
    sect = ins['sect']
    deity = ins.get('deity', '').replace('\\', '\\\\').replace("'", "\\'")
    patron = ins.get('patron', '').replace('\\', '\\\\').replace("'", "\\'")
    vow = ins.get('vow', '').replace('\\', '\\\\').replace("'", "\\'")

    js_parts.append(f'nodes.add({{id:"i_{nid}",label:"#{nid}",group:"inscription",title:"{name}",region:"{region}",period:"{period}",class:"{cls}",sect:"{sect}",vow:"{vow}",deity:"{deity}",patron:"{patron}",shape:"dot",size:5}});')

# 添加边
js_parts.append("// Edges")
for ins in inscriptions:
    nid = ins['id']
    region = ins['region']
    period = ins['period']
    cls = ins['class']
    sect = ins['sect']
    vow = ins.get('vow', '')
    js_parts.append(f'edges.add({{from:"i_{nid}",to:"r_{region}"}});')
    js_parts.append(f'edges.add({{from:"i_{nid}",to:"p_{period}"}});')
    js_parts.append(f'edges.add({{from:"i_{nid}",to:"c_{cls}"}});')
    js_parts.append(f'edges.add({{from:"i_{nid}",to:"s_{sect}"}});')
    if vow:
        js_parts.append(f'edges.add({{from:"i_{nid}",to:"w_{vow}"}});')

# 输出JS文件
output = '\n'.join(js_parts)
output_js = r'V:\图谱\data\export\import_joinmap.js'
with open(output_js, 'w', encoding='utf-8') as f:
    f.write(output)

size_kb = os.path.getsize(output_js) / 1024
print(f"Generated: {output_js} ({size_kb:.0f} KB)")
print(f"  Regions: {len(regions)}, Periods: {len(periods)}, Classes: {len(classes)}, Sects: {len(sects)}, Vows: {len(vows)}")
print(f"  Inscriptions: {len(inscriptions)}")
print(f"  Edges: {len(inscriptions) * 4 + sum(1 for i in inscriptions if i.get('vow'))}")
print(f"  Lines of JS: {len(js_parts)}")
