#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
09_export_rebuild_cypher.py
从运行中的 Neo4j 在线导出全量重建脚本 data/export/rebuild_full.cypher。

生成的脚本可在任意 Neo4j 5.x 上一次性复原当前完整图（中文标签/关系、
全部枢纽与题记、关系边、索引），用法：
  cypher-shell -a bolt://127.0.0.1:7687 -u neo4j -p <密码> -f rebuild_full.cypher
或分段粘贴到 Neo4j Browser。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import requests

URL = 'http://127.0.0.1:7474/db/neo4j/tx/commit'
AUTH = None  # 由下方凭据加载


def _db_auth():
    import os
    pw = os.environ.get('NEO4J_PASSWORD', '')
    if not pw:
        cfg = ROOT / 'data' / 'config' / 'db_local.json'
        if cfg.exists():
            pw = json.loads(cfg.read_text(encoding='utf-8')).get('password', '')
    if not pw:
        sys.exit('未提供 Neo4j 密码：设置环境变量 NEO4J_PASSWORD，或创建 data/config/db_local.json')
    return ('neo4j', pw)


AUTH = _db_auth()


def run(stmt):
    r = requests.post(URL, json={'statements': [{'statement': stmt}]},
                      headers={'Content-Type': 'application/json'}, auth=AUTH, timeout=120)
    j = r.json()
    if j.get('errors'):
        print('ERROR:', j['errors'][0]['message'])
        return []
    return [d['row'] for d in j['results'][0]['data']] if j.get('results') else []


def esc(v):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace('\\', '\\\\').replace("'", "\\'") + "'"


def props(p):
    return '{' + ', '.join(f"{k}: {esc(v)}" for k, v in p.items()) + '}'


def main():
    nodes = run("MATCH (n) RETURN labels(n) AS ls, properties(n) AS p ORDER BY labels(n)[0], n.name, n.id")
    rels = run("MATCH (a)-[r]->(b) RETURN labels(a)[0] AS la, coalesce(a.id, a.name) AS ka, "
               "labels(b)[0] AS lb, coalesce(b.id, b.name) AS kb, type(r) AS t")
    print(f"节点 {len(nodes)}，关系 {len(rels)}")

    out = ["// 石刻造像题记知识图谱 - 全量重建脚本（由 09_export_rebuild_cypher.py 自动生成）",
           "// 用法: cypher-shell -u neo4j -p <密码> -f rebuild_full.cypher",
           "// 幂等提示: 会先清空 题记 与全部枢纽标签后重建",
           "MATCH (n) WHERE ANY(l IN labels(n) WHERE l IN "
           "['题记','地区','朝代分期','阶层标签','阶层类型','组织单位','宗派','造像题材',"
           "'宗教类型','性别','妆造类型','祈愿内容一级','祈愿内容二级','祈愿内容三级',"
           "'实践行为一级','实践行为二级','实践行为三级','造像原因一级','造像原因二级','造像原因三级']) "
           "DETACH DELETE n;",
           ""]

    for ls, p in nodes:
        label = ls[0]
        out.append(f"CREATE (:{label} {props(p)});")
    out.append("")

    for la, ka, lb, kb, t in rels:
        ka_esc, kb_esc = esc(str(ka)), esc(str(kb))
        if la == '题记':
            m1 = f"(a:`题记` {{id: {ka_esc}}})"
        else:
            m1 = f"(a:`{la}` {{name: {ka_esc}}})"
        if lb == '题记':
            m2 = f"(b:`题记` {{id: {kb_esc}}})"
        else:
            m2 = f"(b:`{lb}` {{name: {kb_esc}}})"
        out.append(f"MATCH {m1}, {m2} CREATE (a)-[:`{t}`]->(b);")

    out += ["",
            "CREATE INDEX insc_id IF NOT EXISTS FOR (i:`题记`) ON (i.id);",
            "CREATE INDEX insc_subject IF NOT EXISTS FOR (i:`题记`) ON (i.subject);",
            "CREATE INDEX insc_vow IF NOT EXISTS FOR (i:`题记`) ON (i.prayer_l1);",
            "MATCH (n) RETURN labels(n)[0] AS 标签, count(n) AS 数量 ORDER BY 数量 DESC;"]

    dst = ROOT / 'data' / 'export' / 'rebuild_full.cypher'
    dst.write_text('\n'.join(out), encoding='utf-8')
    print(f"写入 {dst} ({dst.stat().st_size/1024:.0f} KB)")


if __name__ == '__main__':
    main()
