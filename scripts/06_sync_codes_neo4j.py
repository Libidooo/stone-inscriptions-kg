#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_sync_codes_neo4j.py
以 5.21实体 为基准，同步运行中 Neo4j 的编码层（2026-09 妆造分类建议 + 系统性排查）：

1. 妆造（妆造类型归一化规则 v1.1）
   - 同步 i.makeup_normalized / i.raw_妆造（修复 #48/#218/#222 镌妆误标"缺失"，
     全库"缺失"统一改为"不详"）
   - 重建 HAS_MAKEUP 边（Inscription → MakeupType）
2. 实践行为 / 造像原因
   - 同步 i.raw_实践1..4 / i.raw_原因1..4（库内为早期粗映射旧值，926/913 条与 5.21 不一致）
   - 重建 PracticeL1/2/3、CauseL1/2/3 枢纽及 HAS_SUBTYPE、HAS_PRACTICE、HAS_CAUSE 边
   （祈愿 WishL1/2/3 已由 05_update_vows_neo4j.py 同步，本脚本不重复处理）

使用方法:
  python 06_sync_codes_neo4j.py            # 密码经 NEO4J_PASSWORD 或 data/config/db_local.json 提供
  python 06_sync_codes_neo4j.py --dry-run
"""
import re
import sys
from pathlib import Path
import json
import os
import csv
import argparse

sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    sys.exit("需要 requests: pip install requests")

URL = 'http://127.0.0.1:7474/db/neo4j/tx/commit'
def _db_auth():
    """凭据加载：环境变量 NEO4J_PASSWORD → data/config/db_local.json（已 gitignore）"""
    pw = os.environ.get('NEO4J_PASSWORD', '')
    if not pw:
        cfg = Path(r'V:\图谱\data\config\db_local.json')
        if cfg.exists():
            pw = json.loads(cfg.read_text(encoding='utf-8')).get('password', '')
    if not pw:
        sys.exit('未提供 Neo4j 密码：设置环境变量 NEO4J_PASSWORD，或创建 data/config/db_local.json')
    return ('neo4j', pw)

AUTH = _db_auth()
CSV_PATH = r'V:\图谱\data\cleaned\inscriptions_clean.csv'

MISSING = {'信息不详', '无记载与残损难辨', '缺失', '无法判定', '不详', '未知', '空白', ''}

# 造像原因一级词表（判定规则 A-H+Z）：二级列中出现这些词属"一级回填/混杂值"，过滤之
CAUSE_L1_VOCAB = {'超度荐亡', '祈福禳灾', '报恩酬德', '修证悟道', '护国兴邦', '弘法传教', '修复缮完', '杂缘因由', '信息不详'}

# 数据错字修正（图层级，原始数据不改）
CAUSE_TYPO_FIX = {'修复圣象': '修复圣像', '忘亲超荐': '亡亲超荐'}

_CAUSE_NAME_DETAIL = __import__('re').compile(r'^(\S+?)\s*[（(](.+)[)）]$')


def clean_cause_l2(val):
    """造像原因二级清洗（核验偏差1的图层层处理，原始数据不改）：
    1. 顶层分割（括号感知）：;；、,，/ 及 '->' 箭头混杂值
    2. "类目 (细目)" 形式保持完整；含内部空格的混杂串再按空格拆词
    3. 剔除一级词表成分（525 行二级被一级词回填，无增量信息）
    4. 错字修正（修复圣象→修复圣像、忘亲超荐→亡亲超荐）
    返回净化后的成分列表"""
    s = str(val or '').replace('->', '；')
    parts, buf, depth = [], [], 0
    for ch in s:
        if ch in '（(':
            depth += 1
            buf.append(ch)
        elif ch in '）)':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif depth == 0 and ch in ';；、,，/':
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf))

    def keep(token: str) -> bool:
        if not token or token in MISSING:
            return False
        if token[0] in '（(':
            return False  # 混杂值破碎后的孤儿括号片段（如 "(重装)"）
        m = _CAUSE_NAME_DETAIL.match(token)
        name = m.group(1) if m else token
        return name not in CAUSE_L1_VOCAB

    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = _CAUSE_NAME_DETAIL.match(p)
        if m:
            if keep(p):
                name = CAUSE_TYPO_FIX.get(m.group(1), m.group(1))
                out.append(f"{name}({m.group(2)})")
            continue
        if ' ' in p or '\u3000' in p:
            for t in re.split(r'\s+', p):
                t = t.strip()
                if keep(t):
                    out.append(CAUSE_TYPO_FIX.get(t, t))
        elif keep(p):
            out.append(CAUSE_TYPO_FIX.get(p, p))
    return out


def run(stmts, timeout=60):
    if isinstance(stmts, str):
        stmts = [stmts]
    normalized = [{'statement': s} if isinstance(s, str) else s for s in stmts]
    if not normalized:
        return None
    import requests as rq
    r = rq.post(URL, json={'statements': normalized},
                headers={'Content-Type': 'application/json'}, auth=AUTH, timeout=timeout)
    j = r.json()
    if j.get('errors'):
        for err in j['errors']:
            print(f"  ERROR: {err['message']}")
        return None
    return j['results'][0] if j.get('results') else None


def split_top_level(val):
    """按 ;；、,， 拆分，但忽略括号内部分隔符"""
    parts, buf, depth = [], [], 0
    for ch in str(val or ''):
        if ch in '（(':
            depth += 1
            buf.append(ch)
        elif ch in '）)':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif depth == 0 and ch in ';；、,，':
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf))
    return [p.strip() for p in parts if p.strip()]


def parse_detail(item):
    """'普度众生 (上报四恩)' → ('普度众生', '上报四恩')"""
    s = item.strip()
    depth = 0
    for idx, ch in enumerate(s):
        if ch in '（(':
            if depth == 0:
                name = s[:idx].strip()
                detail = s[idx + 1:].rstrip('）)').strip()
                return (name or s, detail or None)
            depth += 1
        elif ch in '）)':
            depth = max(0, depth - 1)
    return s, None


def positional_pair(a, b):
    if not a and not b:
        return []
    n = max(len(a), len(b))
    out = []
    for i in range(n):
        va = a[i] if i < len(a) else (a[-1] if a else '')
        vb = b[i] if i < len(b) else (b[-1] if b else '')
        out.append((va, vb))
    return out


# 层级编码字段定义（实践行为 / 造像原因）
FIELD_DEFS = [
    {
        'name': '实践行为',
        'col_l1': '实践行为（一级编码）', 'col_l2': '实践行为（二级编码）',
        'labels': ('实践行为一级', '实践行为二级', '实践行为三级'),
        'rel_to_insc': '实践行为',
        'prop_prefix': 'raw_实践',
    },
    {
        'name': '造像原因',
        'col_l1': '造像原因（一级编码）', 'col_l2': '造像原因（二级编码）',
        'labels': ('造像原因一级', '造像原因二级', '造像原因三级'),
        'rel_to_insc': '造像原因',
        'prop_prefix': 'raw_原因',
    },
]


def build_hierarchy(rows, fd):
    """从 CSV 行解析某编码字段的层级节点与边"""
    l1s_, l2s_, l3s_ = set(), set(), set()
    e12, e23 = set(), set()
    e_insc = []  # (label, name, insc_id)
    props = []   # (iid, l1_disp, l2_disp, l3_disp)

    for row in rows:
        iid = row['题记序号']
        l1_list = [x for x in split_top_level(row.get(fd['col_l1'], '')) if x not in MISSING]
        # 造像原因二级经 clean_cause_l2 清洗（一级词回填过滤 + 混杂值拆分）
        if fd['name'] == '造像原因':
            l2_items = clean_cause_l2(row.get(fd['col_l2'], ''))
        else:
            l2_items = [x for x in split_top_level(row.get(fd['col_l2'], '')) if x not in MISSING]
        l2_parsed = [parse_detail(item) for item in l2_items]

        disp_l1 = '；'.join(l1_list) if l1_list else '信息不详'
        disp_l2 = '；'.join(row.get(fd['col_l2'], '').strip().split('；')) or '信息不详'
        disp_l3 = '；'.join(d for (_, d) in l2_parsed if d)
        props.append((iid, disp_l1, disp_l2, disp_l3))

        if not l1_list and not l2_parsed:
            continue
        for l1, l2t in positional_pair(l1_list, l2_parsed):
            l2name, l3name = l2t if l2t else (None, None)
            if l1:
                l1s_.add(l1)
            if l2name:
                l2s_.add(l2name)
            if l3name:
                l3s_.add(l3name)
            if l1 and l2name:
                e12.add((l1, l2name))
            if l2name and l3name:
                e23.add((l2name, l3name))
            if l3name:
                e_insc.append((fd['labels'][2], l3name, iid))
            elif l2name:
                e_insc.append((fd['labels'][1], l2name, iid))
            elif l1:
                e_insc.append((fd['labels'][0], l1, iid))
    return l1s_, l2s_, l3s_, e12, e23, e_insc, props


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    res = run('RETURN 1 AS ok;')
    if not res or res['data'][0]['row'][0] != 1:
        sys.exit('无法连接 Neo4j')
    print('[0] Neo4j 连接正常')

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    print(f'[1] 读取清洗数据: {len(rows)} 条')

    # ─── 2. 妆造同步 ───
    mk_dist = {}
    for row in rows:
        v = row.get('makeup_normalized', '不详') or '不详'
        mk_dist[v] = mk_dist.get(v, 0) + 1
    print(f"[2] 妆造归一化(v1.1)分布: {mk_dist}")

    hierarchies = {}
    for fd in FIELD_DEFS:
        h = build_hierarchy(rows, fd)
        hierarchies[fd['name']] = (fd, h)
        l1s_, l2s_, l3s_, e12, e23, e_insc, _ = h
        print(f"[3] {fd['name']}层级: L1={len(l1s_)} L2={len(l2s_)} L3={len(l3s_)} "
              f"| L1→L2={len(e12)} L2→L3={len(e23)} {fd['rel_to_insc']}={len(e_insc)}")

    if args.dry_run:
        print('[dry-run] 未写库')
        return

    # ─── 4. 妆造：属性 + 边 ───
    print('[4] 同步妆造属性与 HAS_MAKEUP 边...')
    stmts = [{
        'statement': ("MATCH (i:`题记` {id: $id}) "
                      "SET i.makeup_normalized = $mk, i.raw_妆造 = $raw"),
        'parameters': {'id': r['题记序号'],
                       'mk': r.get('makeup_normalized', '不详') or '不详',
                       'raw': r.get('妆造类型', '') or ''}
    } for r in rows]
    for i in range(0, len(stmts), 100):
        run(stmts[i:i + 100])

    run("MATCH ()-[r:`妆造类型`]->() DELETE r")
    for name in mk_dist:
        run(f"MERGE (:`妆造类型` {{name: '{name}'}})")
    stmts = []
    for r in rows:
        mk = (r.get('makeup_normalized', '不详') or '不详').replace("'", "\\'")
        stmts.append(f"MATCH (i:`题记` {{id: '{r['题记序号']}'}}), "
                     f"(m:`妆造类型` {{name: '{mk}'}}) CREATE (i)-[:`妆造类型`]->(m)")
    for i in range(0, len(stmts), 100):
        run(stmts[i:i + 100])

    # ─── 5. 实践/原因：属性 + 枢纽重建 ───
    for fd in FIELD_DEFS:
        print(f"[5] 重建 {fd['name']} ({fd['labels'][0]}..{fd['labels'][2]})...")
        _, (l1s_, l2s_, l3s_, e12, e23, e_insc, props) = hierarchies[fd['name']]

        for label in fd['labels']:
            run(f"MATCH (n:`{label}`) DETACH DELETE n")

        stmts = []
        for n in l1s_:
            stmts.append(f"MERGE (:`{fd['labels'][0]}` {{name: '{n}'}})")
        for n in l2s_:
            stmts.append(f"MERGE (:`{fd['labels'][1]}` {{name: '{n}'}})")
        for n in l3s_:
            stmts.append(f"MERGE (:`{fd['labels'][2]}` {{name: '{n}'}})")
        for i in range(0, len(stmts), 50):
            run(stmts[i:i + 50])

        stmts = []
        for (a, b) in e12:
            stmts.append(f"MATCH (a:`{fd['labels'][0]}` {{name: '{a}'}}), (b:`{fd['labels'][1]}` {{name: '{b}'}}) "
                         f"MERGE (a)-[:`下级编码`]->(b)")
        for (a, b) in e23:
            stmts.append(f"MATCH (a:`{fd['labels'][1]}` {{name: '{a}'}}), (b:`{fd['labels'][2]}` {{name: '{b}'}}) "
                         f"MERGE (a)-[:`下级编码`]->(b)")
        for i in range(0, len(stmts), 50):
            run(stmts[i:i + 50])

        stmts = []
        for (label, name, iid) in e_insc:
            stmts.append(f"MATCH (n:`{label}` {{name: '{name}'}}), (i:`题记` {{id: '{iid}'}}) "
                         f"MERGE (n)-[:`{fd['rel_to_insc']}`]->(i)")
        for i in range(0, len(stmts), 50):
            run(stmts[i:i + 50])

        prefix = fd['prop_prefix']
        stmts = [{
            'statement': (f"MATCH (i:`题记` {{id: $id}}) "
                          f"SET i.{prefix}1 = $a, i.{prefix}2 = $b, i.{prefix}3 = $c, i.{prefix}4 = ''"),
            'parameters': {'id': p[0], 'a': p[1], 'b': p[2], 'c': p[3]}
        } for p in props]
        for i in range(0, len(stmts), 100):
            run(stmts[i:i + 100])

    # ─── 6. 验证 ───
    print('[6] 验证:')
    for q, label in [
        ("MATCH (i:`题记` {id:'48'}) RETURN i.makeup_normalized AS mk, i.raw_妆造 AS raw", '#48 妆造'),
        ("MATCH (m:`妆造类型`) RETURN m.name AS name, count{(i)-[:`妆造类型`]->(m)} AS c ORDER BY c DESC", 'MakeupType 分布'),
        ("MATCH (i:`题记` {id:'3'}) RETURN i.raw_实践1 AS p1, i.raw_实践2 AS p2", '#3 实践行为'),
        ("MATCH ()-[r:`实践行为`]->() RETURN count(r) AS c", '实践行为 边'),
        ("MATCH ()-[r:`造像原因`]->() RETURN count(r) AS c", '造像原因 边'),
        ("MATCH (n) RETURN count(n) AS c", '总节点数'),
    ]:
        res = run(q)
        if res and res['data']:
            rows_out = [d['row'] for d in res['data']]
            print(f"  {label}: {rows_out if len(rows_out) > 1 else rows_out[0]}")
    print('完成！')


if __name__ == '__main__':
    main()
