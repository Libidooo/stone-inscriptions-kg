#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07_rename_chinese_neo4j.py
将 Neo4j 节点标签改为"中文+层级编码"、关系类型改为中文，提升 Browser 可视化可读性。

- 节点标签：WishL1 → 祈愿内容一级、PracticeL2 → 实践行为二级、Inscription → 题记 …
- 关系类型：HAS_WISH → 祈愿内容、LOCATED_IN → 位于、HAS_SUBTYPE → 下级编码 …
- 同步重建索引（题记.id / 题记.subject / 题记.prayer_l1）
- 映射表落盘 data/config/neo4j_labels_zh.json，供 05/06/08 脚本与文档引用

使用方法:
  python 07_rename_chinese_neo4j.py --dry-run   # 查看计划
  python 07_rename_chinese_neo4j.py             # 执行改名
"""
import sys
import os
import json
import argparse
from pathlib import Path

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
MAPPING_PATH = Path(r'V:\图谱\data\config\neo4j_labels_zh.json')

LABEL_MAP = {
    'Inscription':  '题记',
    'Region':       '地区',
    'Period':       '朝代分期',
    'Class':        '阶层标签',
    'ClassType':    '阶层类型',
    'ClassUnit':    '组织单位',
    'Sect':         '宗派',
    'Subject':      '造像题材',
    'ReligionType': '宗教类型',
    'Gender':       '性别',
    'MakeupType':   '妆造类型',
    'PracticeL1':   '实践行为一级',
    'PracticeL2':   '实践行为二级',
    'PracticeL3':   '实践行为三级',
    'WishL1':       '祈愿内容一级',
    'WishL2':       '祈愿内容二级',
    'WishL3':       '祈愿内容三级',
    'CauseL1':      '造像原因一级',
    'CauseL2':      '造像原因二级',
    'CauseL3':      '造像原因三级',
}

REL_MAP = {
    'LOCATED_IN':  '位于',
    'FROM_PERIOD': '所属朝代',
    'HAS_CLASS':   '阶层',
    'HAS_TYPE':    '阶层类型',
    'HAS_UNIT':    '组织单位',
    'BELONGS_TO':  '所属宗派',
    'DEPICTS':     '造像题材',
    'HAS_RELIGION': '宗教类型',
    'HAS_GENDER':  '性别',
    'HAS_MAKEUP':  '妆造类型',
    'HAS_SUBTYPE': '下级编码',
    'HAS_PRACTICE': '实践行为',
    'HAS_WISH':    '祈愿内容',
    'HAS_CAUSE':   '造像原因',
}


def run(stmts, timeout=120):
    if isinstance(stmts, str):
        stmts = [stmts]
    normalized = [{'statement': s} if isinstance(s, str) else s for s in stmts]
    if not normalized:
        return None
    r = requests.post(URL, json={'statements': normalized},
                      headers={'Content-Type': 'application/json'}, auth=AUTH, timeout=timeout)
    j = r.json()
    if j.get('errors'):
        for err in j['errors']:
            print(f"  ERROR: {err['message']}")
        return None
    return j['results'][0] if j.get('results') else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    res = run('RETURN 1 AS ok;')
    if not res or res['data'][0]['row'][0] != 1:
        sys.exit('无法连接 Neo4j')
    print('[0] Neo4j 连接正常')

    # 盘点现状
    label_counts = {d['row'][0]: d['row'][1]
                    for d in run("MATCH (n) RETURN labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")['data']}
    rel_counts = {d['row'][0]: d['row'][1]
                  for d in run("MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY c DESC")['data']}
    print(f"[1] 现状: {len(label_counts)} 种标签 / {len(rel_counts)} 种关系")

    todo_labels = {old: new for old, new in LABEL_MAP.items() if old in label_counts}
    done_labels = [new for new in LABEL_MAP.values() if new in label_counts]
    todo_rels = {old: new for old, new in REL_MAP.items() if old in rel_counts}
    done_rels = [new for new in REL_MAP.values() if new in rel_counts]

    print(f"[2] 待改标签: {todo_labels}")
    print(f"[3] 待改关系: {todo_rels}")
    if done_labels or done_rels:
        print(f"    已是中文(跳过): 标签{done_labels} 关系{done_rels}")
    if args.dry_run:
        print('[dry-run] 未写库')
        return

    # ─── 4. 改节点标签 ───
    print('[4] 改节点标签...')
    for old, new in todo_labels.items():
        r = run(f"MATCH (n:`{old}`) SET n:`{new}` REMOVE n:`{old}` RETURN count(n) AS c")
        cnt = r['data'][0]['row'][0] if r and r['data'] else '?'
        print(f"    {old} → {new} ({cnt})")

    # ─── 5. 改关系类型（Neo4j 不支持原地改类型：建新删旧） ───
    print('[5] 改关系类型...')
    for old, new in todo_rels.items():
        r = run(f"MATCH (a)-[r:`{old}`]->(b) CREATE (a)-[:`{new}`]->(b) DELETE r RETURN count(r) AS c")
        cnt = r['data'][0]['row'][0] if r and r['data'] else '?'
        print(f"    {old} → {new} ({cnt})")

    # ─── 6. 索引重建（指向中文标签） ───
    print('[6] 重建索引...')
    idx_stmts = [
        "DROP INDEX inscription_id IF EXISTS",
        "DROP INDEX inscription_subject IF EXISTS",
        "DROP INDEX inscription_vow IF EXISTS",
        "CREATE INDEX insc_id IF NOT EXISTS FOR (i:`题记`) ON (i.id)",
        "CREATE INDEX insc_subject IF NOT EXISTS FOR (i:`题记`) ON (i.subject)",
        "CREATE INDEX insc_vow IF NOT EXISTS FOR (i:`题记`) ON (i.prayer_l1)",
    ]
    for s in idx_stmts:
        run(s)

    # ─── 7. 落盘映射表 ───
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPPING_PATH, 'w', encoding='utf-8') as f:
        json.dump({'labels': LABEL_MAP, 'relationships': REL_MAP}, f, ensure_ascii=False, indent=2)
    print(f"[7] 映射表写入 {MAPPING_PATH}")

    # ─── 8. 验证 ───
    print('[8] 验证:')
    lc = {d['row'][0]: d['row'][1]
          for d in run("MATCH (n) RETURN labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")['data']}
    rc = {d['row'][0]: d['row'][1]
          for d in run("MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY c DESC")['data']}
    for k, v in lc.items():
        print(f"    [{k}] ×{v}")
    for k, v in rc.items():
        print(f"    -{k}- ×{v}")
    residual_en = [l for l in lc if l in LABEL_MAP] + [t for t in rc if t in REL_MAP]
    print(f"    残留英文标签/关系: {residual_en if residual_en else '无 ✓'}")
    print('完成！')


if __name__ == '__main__':
    main()
