#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_update_vows_neo4j.py
以 5.21实体（祈愿内容编码 v3.0，含四恩三有）为基准，更新运行中的 Neo4j：


1. 重建祈愿层级枢纽 祈愿内容一级/二级/三级（2026-09 起标签中文化）
   - 二级编码 "普度众生 (上报四恩)" → 二级=普度众生, 三级=上报四恩
   - 层级连边 下级编码，最细层级 → 题记 连 祈愿内容
2. 同步 题记 属性：raw_祈愿1/2/3/4、vow_main、vow_detail
3. 同步本次基准中其余字段漂移（如 #6 的 sect_all / subject）

使用方法:
  python 05_update_vows_neo4j.py            # 密码经 NEO4J_PASSWORD 或 data/config/db_local.json 提供
  python 05_update_vows_neo4j.py --dry-run  # 只打印计划，不写库
"""
import re
import sys
from pathlib import Path
import json
import os
import csv
import argparse
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录

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
        cfg = ROOT / 'data' / 'config' / 'db_local.json'
        if cfg.exists():
            pw = json.loads(cfg.read_text(encoding='utf-8')).get('password', '')
    if not pw:
        sys.exit('未提供 Neo4j 密码：设置环境变量 NEO4J_PASSWORD，或创建 data/config/db_local.json')
    return ('neo4j', pw)

AUTH = _db_auth()
CSV_PATH = str(ROOT / 'data' / 'cleaned' / 'inscriptions_clean.csv')

MISSING = {'信息不详', '无记载与残损难辨', '缺失', '无法判定', '不详', '未知', '空白', ''}


def run(stmts, timeout=60):
    """stmts: 单条字符串 / 字符串列表 / {statement,parameters} 字典列表"""
    if isinstance(stmts, str):
        stmts = [stmts]
    normalized = []
    for s in stmts:
        normalized.append({'statement': s} if isinstance(s, str) else s)
    if not normalized:
        return None
    r = requests.post(URL, json={'statements': normalized},
                      headers={'Content-Type': 'application/json'}, auth=AUTH, timeout=timeout)
    result = r.json()
    if result.get('errors'):
        for err in result['errors']:
            print(f"  ERROR: {err['message']}")
        return None
    return result['results'][0] if result.get('results') else None


def split_top_level(val):
    """按 ;；、,， 拆分，但忽略括号（（）与半角）内部的分隔符"""
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


def split_vals(val, keep_missing=False):
    """拆分复合编码值（括号感知），默认剔除缺失标记"""
    out = []
    for p in split_top_level(val):
        if not keep_missing and p in MISSING:
            continue
        out.append(p)
    return out


def parse_l2(item):
    """取第一个顶层左括号：'普度众生 (上报四恩)' → ('普度众生', '上报四恩')"""
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
    """按位置配对两级列表（沿用 04 的 repeat-last 逻辑）"""
    if not a and not b:
        return []
    n = max(len(a), len(b))
    pairs = []
    for i in range(n):
        va = a[i] if i < len(a) else (a[-1] if a else '')
        vb = b[i] if i < len(b) else (b[-1] if b else '')
        pairs.append((va, vb))
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    # ─── 0. 连通性 ───
    res = run('RETURN 1 AS ok;')
    if not res or res['data'][0]['row'][0] != 1:
        sys.exit('无法连接 Neo4j，请确认服务已启动')
    print('[0] Neo4j 连接正常')

    # ─── 1. 读清洗数据 ───
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    print(f'[1] 读取清洗数据: {len(rows)} 条')

    # ─── 2. 解析祈愿层级 ───
    l1_nodes, l2_nodes, l3_nodes = set(), set(), set()
    e_l1l2, e_l2l3 = set(), set()   # (l1,l2), (l2,l3)
    e_wish = []                     # (level_label, name, insc_id)
    prop_updates = []               # per-inscription property updates

    for row in rows:
        iid = row['题记序号']
        l1s = split_vals(row.get('vow_main', ''), keep_missing=False) or (['信息不详'] if not row.get('vow_l2_norm') else [])
        l2_raw = split_vals(row.get('vow_l2_norm', ''))  # v3.0 归一化二级（01 脚本 vow_l2_norm）
        l2s = []
        for item in l2_raw:
            name, detail = parse_l2(item)
            l2s.append((name, detail))

        # 原始展示值（含括号），缺失时用"信息不详"
        disp_l1 = row.get('vow_main', '') or '信息不详'
        disp_l2 = row.get('vow_detail', '') or '信息不详'
        disp_l2n = row.get('vow_l2_norm', '') or '信息不详'
        details = [d for (_, d) in l2s if d]
        disp_l3 = '；'.join(details) if details else ''
        prop_updates.append((iid, disp_l1, disp_l2, disp_l3, disp_l2n))

        if not l1s and not l2s:
            continue

        # 位置配对 L1 ↔ L2
        paired = positional_pair(l1s, l2s)
        for l1, l2tuple in paired:
            l2name, l3name = l2tuple if l2tuple else (None, None)
            if l1:
                l1_nodes.add(l1)
            if l2name:
                l2_nodes.add(l2name)
            if l3name:
                l3_nodes.add(l3name)
            if l1 and l2name:
                e_l1l2.add((l1, l2name))
            if l2name and l3name:
                e_l2l3.add((l2name, l3name))
            # 最细层级连题记
            if l3name:
                e_wish.append(('祈愿内容三级', l3name, iid))
            elif l2name:
                e_wish.append(('祈愿内容二级', l2name, iid))
            elif l1:
                e_wish.append(('祈愿内容一级', l1, iid))

    print(f'[2] 祈愿层级解析: WishL1={len(l1_nodes)} WishL2={len(l2_nodes)} WishL3={len(l3_nodes)} '
          f'| L1→L2={len(e_l1l2)} L2→L3={len(e_l2l3)} HAS_WISH={len(e_wish)}')

    if args.dry_run:
        print('[dry-run] 仅打印计划，未写库')
        print('  WishL1:', sorted(l1_nodes))
        print('  WishL2 示例:', sorted(l2_nodes)[:10])
        return

    # ─── 3. 清空并重建 Wish 枢纽 ───
    print('[3] 重建 WishL1/L2/L3 枢纽...')
    for label in ('祈愿内容一级', '祈愿内容二级', '祈愿内容三级'):
        run(f'MATCH (n:`{label}`) DETACH DELETE n')

    stmts = []
    for n in l1_nodes:
        stmts.append(f"MERGE (:`祈愿内容一级` {{name: '{n}'}})")
    for n in l2_nodes:
        stmts.append(f"MERGE (:`祈愿内容二级` {{name: '{n}'}})")
    for n in l3_nodes:
        stmts.append(f"MERGE (:`祈愿内容三级` {{name: '{n}'}})")
    for i in range(0, len(stmts), 50):
        run(stmts[i:i + 50])

    stmts = []
    for (a, b) in e_l1l2:
        stmts.append(f"MATCH (a:`祈愿内容一级` {{name: '{a}'}}), (b:`祈愿内容二级` {{name: '{b}'}}) MERGE (a)-[:`下级编码`]->(b)")
    for (a, b) in e_l2l3:
        stmts.append(f"MATCH (a:`祈愿内容二级` {{name: '{a}'}}), (b:`祈愿内容三级` {{name: '{b}'}}) MERGE (a)-[:`下级编码`]->(b)")
    for i in range(0, len(stmts), 50):
        run(stmts[i:i + 50])

    stmts = []
    for (label, name, iid) in e_wish:
        stmts.append(f"MATCH (n:`{label}` {{name: '{name}'}}), (i:`题记` {{id: '{iid}'}}) "
                     f"MERGE (n)-[:`祈愿内容`]->(i)")
    for i in range(0, len(stmts), 50):
        run(stmts[i:i + 50])

    # ─── 4. 同步 Inscription 属性 ───
    print('[4] 同步 Inscription 祈愿属性...')
    stmts = []
    for (iid, w1, w2, w3, w2n) in prop_updates:
        safe1 = w1.replace("'", "\\'")
        safe2 = w2.replace("'", "\\'")
        safe3 = w3.replace("'", "\\'")
        stmts.append({
            'statement': (
                "MATCH (i:`题记` {id: $id}) "
                "SET i.raw_祈愿1 = $w1, i.raw_祈愿2 = $w2, i.raw_祈愿3 = $w3, "
                "    i.raw_祈愿4 = '', i.vow_main = $w1, i.vow_detail = $w2, "
                "    i.vow_l2_norm = $w2n"
            ),
            'parameters': {'id': iid, 'w1': w1, 'w2': w2, 'w3': w3, 'w2n': w2n}
        })
    for i in range(0, len(stmts), 100):
        run(stmts[i:i + 100])

    # ─── 5. 同步其他字段漂移（sect_all / subject 等） ───
    print('[5] 同步 sect_all / subject 属性...')
    drift = []
    for row in rows:
        drift.append({
            'statement': ("MATCH (i:`题记` {id: $id}) "
                          "SET i.sect_all = $sa, i.subject = $sub, i.religion_type = $rt, "
                          "    i.prayer_l1 = $w1, i.prayer_l2 = $w2"),
            'parameters': {
                'id': row['题记序号'],
                'sa': row.get('sect_all', '') or '',
                'sub': row.get('subject', '') or '',
                'rt': row.get('religion_type', '') or '',
                'w1': row.get('vow_main', '') or '',
                'w2': row.get('vow_detail', '') or '',
            }
        })
    for i in range(0, len(drift), 100):
        run(drift[i:i + 100])

    # subject 漂移修复边（#6: 无法判定→观音 时补 DEPICTS）
    res = run("MATCH (i:`题记`) MATCH (s:`造像题材` {name: i.subject}) "
              "WHERE NOT (i)-[:`造像题材`]->(s) RETURN i.id AS id, s.name AS sub LIMIT 50")
    if res and res['data']:
        fix = []
        for r_ in res['data']:
            fix.append(f"MATCH (i:`题记` {{id: '{r_['row'][0]}'}}), (s:`造像题材` {{name: '{r_['row'][1]}'}}) "
                       f"MERGE (i)-[:`造像题材`]->(s)")
        run(fix)
        print(f"      补建 DEPICTS 边: {len(fix)} 条")

    # ─── 6. 验证 ───
    print('[6] 验证:')
    for q, label in [
        ("MATCH (n:`祈愿内容一级`) RETURN count(n) AS c", '祈愿内容一级 节点'),
        ("MATCH (n:`祈愿内容二级`) RETURN count(n) AS c", '祈愿内容二级 节点'),
        ("MATCH (n:`祈愿内容三级`) RETURN count(n) AS c", '祈愿内容三级 节点'),
        ("MATCH ()-[r:`祈愿内容`]->() RETURN count(r) AS c", '祈愿内容 边'),
        ("MATCH (i:`题记` {id:'777'}) RETURN i.vow_main AS a, i.vow_detail AS b", '#777 祈愿'),
    ]:
        res = run(q)
        if res and res['data']:
            print(f"  {label}: {res['data'][0]['row']}")
    res = run("MATCH (w:`祈愿内容三级` {name:'上报四恩'})-[r:`祈愿内容`]->(i) "
              "RETURN w.name AS l3, count(i) AS c")
    if res and res['data']:
        print(f"  四恩三有相关(上报四恩→题记): {res['data'][0]['row']}")
    print('完成！')


if __name__ == '__main__':
    main()
