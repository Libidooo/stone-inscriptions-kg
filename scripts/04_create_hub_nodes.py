from pathlib import Path
import json
import os
# -*- coding: utf-8 -*-
"""
04_create_hub_nodes.py
为实践行为、祈愿内容、造像原因创建 一级/二级/三级 中心节点
并按层级连接（一级→二级→三级→Inscription）
"""
import os, sys, json
import requests


# ============================================================
# 1. 连接 Neo4j
# ============================================================
url = 'http://localhost:7474/db/neo4j/tx/commit'
headers = {'Content-Type': 'application/json'}
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

auth = _db_auth()

def run_cypher(stmt, timeout=30):
    r = requests.post(url, json={'statements': [{'statement': stmt}]},
                      headers=headers, auth=auth, timeout=timeout)
    result = r.json()
    if 'errors' in result and result['errors']:
        for err in result['errors']:
            print(f"  ERROR: {err['message']}")
        return None
    return result['results'][0] if result.get('results') else None

def run_batch(stmts, timeout=60):
    """Run multiple statements in one transaction"""
    if not stmts:
        return
    batch = []
    for s in stmts:
        batch.append({'statement': s})
    r = requests.post(url, json={'statements': batch},
                      headers=headers, auth=auth, timeout=timeout)
    result = r.json()
    if 'errors' in result and result['errors']:
        for err in result['errors']:
            print(f"  BATCH ERROR: {err['message']}")
    return result

# ============================================================
# 2. 从 CSV 读取数据，构建层级关系
# ============================================================
import csv
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录

csv_path = str(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv')

# 读取所有行
rows = []
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"Read {len(rows)} rows from CSV")

# 三个字段的类型定义
FIELD_DEFS = [
    {
        'name': '实践行为',
        'label_l1': 'PracticeL1', 'label_l2': 'PracticeL2', 'label_l3': 'PracticeL3',
        'rel_l1_l2': 'HAS_SUBTYPE', 'rel_l2_l3': 'HAS_SUBTYPE', 'rel_to_insc': 'HAS_PRACTICE',
        'col_l1': '实践行为（一级编码）', 'col_l2': '实践行为（二级编码）', 'col_l3': '实践行为（三级编码）',
    },
    {
        'name': '祈愿内容',
        'label_l1': 'WishL1', 'label_l2': 'WishL2', 'label_l3': 'WishL3',
        'rel_l1_l2': 'HAS_SUBTYPE', 'rel_l2_l3': 'HAS_SUBTYPE', 'rel_to_insc': 'HAS_WISH',
        'col_l1': '祈愿内容（一级编码）', 'col_l2': '祈愿内容（二级编码）', 'col_l3': '祈愿内容（三级编码）',
    },
    {
        'name': '造像原因',
        'label_l1': 'CauseL1', 'label_l2': 'CauseL2', 'label_l3': 'CauseL3',
        'rel_l1_l2': 'HAS_SUBTYPE', 'rel_l2_l3': 'HAS_SUBTYPE', 'rel_to_insc': 'HAS_CAUSE',
        'col_l1': '造像原因（一级编码）', 'col_l2': '造像原因（二级编码）', 'col_l3': '造像原因（三级编码）',
    },
]

def split_vals(val):
    """Split compound values by 全角分号, exclude missing-value patterns"""
    if not val:
        return []
    parts = val.split('；')
    result = []
    missing_patterns = ['信息不详', '无记载与残损难辨', '缺失', '无法判定', '不详', '未知', '空白']
    for p in parts:
        p = p.strip()
        if p and p not in missing_patterns:
            result.append(p)
    return result

def positional_pair(l1s, l2s, l3s):
    """
    Pair up L1/L2/L3 values by position.
    For compound values like L1=[A,B], L2=[C,D], L3=[E,F]
    produces pairs: (A,C,E), (B,D,F)
    Handles length mismatches by repeating the last value.
    """
    max_len = max(len(l1s), len(l2s), len(l3s))
    pairs = []
    for i in range(max_len):
        l1 = l1s[i] if i < len(l1s) else l1s[-1] if l1s else ''
        l2 = l2s[i] if i < len(l2s) else l2s[-1] if l2s else ''
        l3 = l3s[i] if i < len(l3s) else l3s[-1] if l3s else ''
        if l1 or l2 or l3:
            pairs.append((l1, l2, l3))
    return pairs

# 对每个字段，收集所有唯一的节点值和边
all_nodes = {}  # label -> set of names
all_edges_l1_l2 = {}  # (label_l1, label_l2) -> set of (name_l1, name_l2)
all_edges_l2_l3 = {}  # (label_l2, label_l3) -> set of (name_l2, name_l3)
all_edges_l3_insc = {}  # label_l3 -> set of (name_l3, insc_id)

for fd in FIELD_DEFS:
    label_l1 = fd['label_l1']
    label_l2 = fd['label_l2']
    label_l3 = fd['label_l3']
    
    # Initialize collections
    for lbl in [label_l1, label_l2, label_l3]:
        if lbl not in all_nodes:
            all_nodes[lbl] = set()
    
    key_l1_l2 = (label_l1, label_l2)
    key_l2_l3 = (label_l2, label_l3)
    if key_l1_l2 not in all_edges_l1_l2:
        all_edges_l1_l2[key_l1_l2] = set()
    if key_l2_l3 not in all_edges_l2_l3:
        all_edges_l2_l3[key_l2_l3] = set()
    if label_l3 not in all_edges_l3_insc:
        all_edges_l3_insc[label_l3] = set()
    
    for row in rows:
        l1_vals = split_vals(row.get(fd['col_l1'], ''))
        l2_vals = split_vals(row.get(fd['col_l2'], ''))
        l3_vals = split_vals(row.get(fd['col_l3'], ''))
        insc_id = row['题记序号']
        
        if not l1_vals and not l2_vals and not l3_vals:
            continue
        
        # Add nodes
        for v in l1_vals:
            all_nodes[label_l1].add(v)
        for v in l2_vals:
            all_nodes[label_l2].add(v)
        for v in l3_vals:
            all_nodes[label_l3].add(v)
        
        # Pair up by position
        pairs = positional_pair(l1_vals, l2_vals, l3_vals)
        
        for l1, l2, l3 in pairs:
            if l1 and l2:
                all_edges_l1_l2[key_l1_l2].add((l1, l2))
            if l2 and l3:
                all_edges_l2_l3[key_l2_l3].add((l2, l3))
            if l3:
                all_edges_l3_insc[label_l3].add((l3, insc_id))

# Print stats
for fd in FIELD_DEFS:
    print(f"\n=== {fd['name']} ===")
    for level, label in [(1, fd['label_l1']), (2, fd['label_l2']), (3, fd['label_l3'])]:
        print(f"  Level {level}: {len(all_nodes[label])} nodes")
    
    key_l1_l2 = (fd['label_l1'], fd['label_l2'])
    key_l2_l3 = (fd['label_l2'], fd['label_l3'])
    print(f"  L1→L2 edges: {len(all_edges_l1_l2[key_l1_l2])}")
    print(f"  L2→L3 edges: {len(all_edges_l2_l3[key_l2_l3])}")
    print(f"  L3→Inscription edges: {len(all_edges_l3_insc[fd['label_l3']])}")

# ============================================================
# 3. 生成并执行 CYPHER
# ============================================================

print("\n=== Creating nodes and relationships ===")

# 先清除已有节点和关系（如果之前运行过）
for fd in FIELD_DEFS:
    for label in [fd['label_l1'], fd['label_l2'], fd['label_l3']]:
        run_cypher(f"MATCH (n:{label}) DETACH DELETE n", timeout=30)
    print(f"  Cleared old {fd['name']} nodes")

# 创建所有节点
node_stmts = []
for label, names in all_nodes.items():
    for name in names:
        node_stmts.append(f"MERGE (:{label} {{name: '{name}'}})")

# Batch create nodes
print(f"  Creating {len(node_stmts)} nodes...")
batch_size = 50
for i in range(0, len(node_stmts), batch_size):
    run_batch(node_stmts[i:i+batch_size], timeout=60)

# 创建一级→二级关系
edge_stmts_l1_l2 = []
for (label_l1, label_l2), pairs in all_edges_l1_l2.items():
    for name_l1, name_l2 in pairs:
        edge_stmts_l1_l2.append(
            f"MATCH (a:{label_l1} {{name: '{name_l1}'}}), "
            f"(b:{label_l2} {{name: '{name_l2}'}}) "
            f"MERGE (a)-[:HAS_SUBTYPE]->(b)"
        )

print(f"  Creating {len(edge_stmts_l1_l2)} L1→L2 edges...")
for i in range(0, len(edge_stmts_l1_l2), batch_size):
    run_batch(edge_stmts_l1_l2[i:i+batch_size], timeout=60)

# 创建二级→三级关系
edge_stmts_l2_l3 = []
for (label_l2, label_l3), pairs in all_edges_l2_l3.items():
    for name_l2, name_l3 in pairs:
        edge_stmts_l2_l3.append(
            f"MATCH (a:{label_l2} {{name: '{name_l2}'}}), "
            f"(b:{label_l3} {{name: '{name_l3}'}}) "
            f"MERGE (a)-[:HAS_SUBTYPE]->(b)"
        )

print(f"  Creating {len(edge_stmts_l2_l3)} L2→L3 edges...")
for i in range(0, len(edge_stmts_l2_l3), batch_size):
    run_batch(edge_stmts_l2_l3[i:i+batch_size], timeout=60)

# 创建三级→Inscription关系
edge_stmts_l3_insc = []
for label_l3, pairs in all_edges_l3_insc.items():
    rel_name = [f['rel_to_insc'] for f in FIELD_DEFS if f['label_l3'] == label_l3][0]
    for name_l3, insc_id in pairs:
        edge_stmts_l3_insc.append(
            f"MATCH (n:{label_l3} {{name: '{name_l3}'}}), "
            f"(i:Inscription {{id: '{insc_id}'}}) "
            f"MERGE (n)-[:{rel_name}]->(i)"
        )

print(f"  Creating {len(edge_stmts_l3_insc)} L3→Inscription edges...")
for i in range(0, len(edge_stmts_l3_insc), batch_size):
    run_batch(edge_stmts_l3_insc[i:i+batch_size], timeout=60)

# ============================================================
# 4. 验证
# ============================================================
print("\n=== Verification ===")
for fd in FIELD_DEFS:
    for level, label in [(1, fd['label_l1']), (2, fd['label_l2']), (3, fd['label_l3'])]:
        res = run_cypher(f"MATCH (n:{label}) RETURN count(n) AS c", timeout=15)
        if res:
            cnt = res['data'][0]['row'][0]
            print(f"  {label}: {cnt} nodes")
    
    # Check relationships
    res = run_cypher(
        f"MATCH (a:{fd['label_l1']})-[:HAS_SUBTYPE]->(b:{fd['label_l2']}) "
        f"RETURN count(*) AS c", timeout=15)
    if res:
        print(f"  {fd['label_l1']}→{fd['label_l2']}: {res['data'][0]['row'][0]} edges")
    
    res = run_cypher(
        f"MATCH (a:{fd['label_l2']})-[:HAS_SUBTYPE]->(b:{fd['label_l3']}) "
        f"RETURN count(*) AS c", timeout=15)
    if res:
        print(f"  {fd['label_l2']}→{fd['label_l3']}: {res['data'][0]['row'][0]} edges")
    
    res = run_cypher(
        f"MATCH (n:{fd['label_l3']})-[:{fd['rel_to_insc']}]->(i:Inscription) "
        f"RETURN count(*) AS c", timeout=15)
    if res:
        print(f"  {fd['label_l3']}→Inscription: {res['data'][0]['row'][0]} edges")

print("\nDone! Hub nodes created successfully.")
