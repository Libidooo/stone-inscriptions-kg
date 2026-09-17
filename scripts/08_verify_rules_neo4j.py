#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
08_verify_rules_neo4j.py
全量核验：Neo4j 各维度节点是否严格遵照《标注规范/rules》词表。


核验维度与基准：
- 妆造类型           ← 妆造类型归一化规则 v1.1（5类）
- 祈愿内容一级       ← 祈愿内容判定规则 v3.0（A-H 八类）
- 祈愿内容二级       ← 祈愿内容判定规则 v3.0 二级编码列（24类）
- 实践行为一级       ← 实践行为判定规则（A造像制作/B供养施舍/C庄严修饰）
- 实践行为二级       ← 实践行为判定规则编码表（73名，extract_rule_vocab.py 提取）
- 造像原因一级       ← 造像原因判定规则（A-H+Z 九类）
- 造像原因二级/三级  ← 造像原因判定规则编码表（89名）
- 宗派/宗教类型/题材/朝代/地区/性别/组织单位/阶层类型 ← config + 对应规则

输出：data/cleaned/neo4j_rules_audit.txt
"""
import sys
import os
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录

sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    sys.exit("需要 requests")

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

# ─── 规范词表（来源见文件头） ───
VOCAB = {
    '妆造类型': ['新造', '新造兼妆修', '重妆', '重修', '不详'],
    '祈愿内容一级': ['超度往生', '现世福报', '国邦安宁', '佛法弘传', '修行证悟', '游观纪胜', '杂缘祈愿', '信息不详'],
    '祈愿内容二级': ['往生净土', '离苦解脱', '弥勒信仰', '延寿增福', '功名富贵', '家庭和睦', '禳灾解冤',
               '子嗣后裔', '财富资业', '国运太平', '农业天候', '佛法兴隆', '永久纪念', '开悟证果',
               '断障出离', '普度众生', '纪游雅集', '礼佛访古', '感应灵异', '祝寿庆诞', '纪功留名',
               '农事祈愿', '其他私愿', '信息不详'],
    '实践行为一级': ['造像制作', '供养施舍', '庄严修饰'],  # + 附录A 扩展（见 PRACTICE_EXT_L1）
    '造像原因一级': ['超度荐亡', '祈福禳灾', '报恩酬德', '修证悟道', '护国兴邦', '弘法传教', '修复缮完', '杂缘因由', '信息不详'],
    '宗派': ['净土', '密教', '禅宗', '华严', '天台', '律宗', '无法判定'],
    '宗教类型': ['佛教', '道教', '儒教', '混合', '无法判定'],
    '造像题材': ['观音', '地藏', '弥勒', '药师', '阿弥陀', '释迦', '佛', '天尊', '老君', '三清', '无法判定'],
    '朝代分期': ['隋', '初唐', '武周', '盛唐', '中唐', '晚唐', '五代', '北宋', '南宋', '不详'],
    '地区': ['大足', '巴中', '广元', '安岳', '成都', '绵阳', '资中', '内江', '眉山', '蒲江', '其他'],
    '性别': ['男', '女', '未知'],
    '组织单位': ['个人', '家庭', '社邑', '群体', '未知'],
    '阶层类型': ['官员', '士人', '僧侣', '工匠', '富众信士', '平民', '未知'],  # 项目定义的归并类（源自阶层划分规则 A/B 编码体系）
}

# 从规则文件提取的完整编码名（供 L2/L3 参考）
_extracted = json.loads((ROOT / 'data' / 'config' / 'rule_vocab_extracted.json').read_text(encoding='utf-8'))
_cfg = json.loads((ROOT / 'data' / 'config' / 'normalization_rules.json').read_text(encoding='utf-8'))
PRACTICE_ALL = set(_extracted['实践行为判定规则.md']) | set(_cfg['practice_ext_vocab']['l2'])
CAUSE_ALL = set(_extracted['造像原因判定规则.md']) | set(_cfg['cause_ext_vocab']['l2'])
PRACTICE_EXT_L1 = set(_cfg['practice_ext_vocab']['l1'])  # 实践行为判定规则 附录A 扩展一级

# 造像原因二级层级名（规则 3.1 示例及结构；亡亲超荐等）
CAUSE_L2_EXTRA = {'亡亲超荐', '直系亲属超荐', '泛称亡亲超荐'}

# 祈愿内容三级/造像原因三级 = 数据括号细目（信息性维度，无严格词表）
INFORMATIONAL = ['祈愿内容三级', '造像原因三级', '阶层标签']

# 各维度连到题记的关系名
REL_OF = {
    '妆造类型': '妆造类型', '祈愿内容一级': '祈愿内容', '祈愿内容二级': '祈愿内容', '祈愿内容三级': '祈愿内容',
    '实践行为一级': '实践行为', '实践行为二级': '实践行为', '实践行为三级': '实践行为',
    '造像原因一级': '造像原因', '造像原因二级': '造像原因', '造像原因三级': '造像原因',
    '宗派': '所属宗派', '宗教类型': '宗教类型', '造像题材': '造像题材', '朝代分期': '所属朝代',
    '地区': '位于', '性别': '性别', '组织单位': '组织单位', '阶层类型': '阶层类型', '阶层标签': '阶层',
}


def run(stmt):
    r = requests.post(URL, json={'statements': [{'statement': stmt}]},
                      headers={'Content-Type': 'application/json'}, auth=AUTH, timeout=60)
    j = r.json()
    if j.get('errors'):
        print('ERROR:', j['errors'][0]['message'])
        return []
    return [d['row'] for d in j['results'][0]['data']] if j.get('results') else []


def fetch_nodes(label, rel):
    """返回 [(name, 关联题记数), ...]。
    层级枢纽标签（祈愿/实践/原因 × 一二三级）经 下级编码*0..2 间接计数，其余按直接边计数。"""
    if label.startswith(('祈愿内容', '实践行为', '造像原因')):
        rows = run(f"MATCH (n:`{label}`) "
                   f"OPTIONAL MATCH (n)-[:`下级编码`*0..2]-()-[:`{rel}`]->(i:`题记`) "
                   f"RETURN n.name AS name, count(DISTINCT i) AS c ORDER BY c DESC")
    else:
        rows = run(f"MATCH (n:`{label}`) OPTIONAL MATCH (n)-[:`{rel}`]->(i:`题记`) "
                   f"RETURN n.name AS name, count(i) AS c ORDER BY c DESC")
    return rows


def main():
    report = []
    total_dims = 0

    def emit(line=''):
        print(line)
        report.append(line)

    emit('=' * 72)
    emit('Neo4j 节点 vs 标注规范 全量核验报告')
    emit('=' * 72)

    # 图完整性概览
    labels = run("MATCH (n) RETURN labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")
    emit('\n【图概览】' + ', '.join(f"{l}×{c}" for l, c in labels))
    total_nodes = sum(c for _, c in labels)
    emit(f'节点总数: {total_nodes}')

    # ─── 严格核验 ───
    emit('\n' + '─' * 72)
    emit('一、封闭词表维度（严格核验）')
    emit('─' * 72)
    for dim, vocab in VOCAB.items():
        rel = REL_OF[dim]
        nodes = fetch_nodes(dim, rel)
        if not nodes:
            emit(f'\n◆ {dim}: 库中无此标签！')
            continue
        total_dims += 1
        vocab_set = set(vocab)
        if dim == '实践行为一级':
            vocab_set |= PRACTICE_EXT_L1
        names = {n for n, _ in nodes}
        in_vocab = [(n, c) for n, c in nodes if n in vocab_set]
        out_vocab = [(n, c) for n, c in nodes if n not in vocab_set]
        rule_unused = vocab_set - names
        status = '✓ 合规' if not out_vocab else f'✗ 有偏差（{len(out_vocab)} 项）'
        emit(f'\n◆ {dim} — {status}')
        emit(f'   节点 {len(nodes)} 个，其中词表内 {len(in_vocab)} 个')
        if out_vocab:
            for n, c in out_vocab:
                emit(f'   ✗ 不在规范词表: 「{n}」（关联题记 {c} 条）')
        if rule_unused:
            emit(f'   · 规范定义但库中未出现: {sorted(rule_unused)}')

    # ─── 参考核验（L2 对完整编码表） ───
    emit('\n' + '─' * 72)
    emit('二、层级编码维度（对照规则完整编码表，参考核验）')
    emit('─' * 72)
    for dim, ref_set, note in [
        ('实践行为二级', PRACTICE_ALL, '实践行为判定规则 73 项编码名 + 附录A 扩展'),
        ('造像原因二级', CAUSE_ALL | CAUSE_L2_EXTRA, '造像原因判定规则 89 项编码名 + 附录B 在用词表'),
    ]:
        rel = REL_OF[dim]
        nodes = fetch_nodes(dim, rel)
        if not nodes:
            emit(f'\n◆ {dim}: 库中无此标签！')
            continue
        total_dims += 1
        in_v = [(n, c) for n, c in nodes if n in ref_set]
        out_v = [(n, c) for n, c in nodes if n not in ref_set]
        in_cnt = sum(c for _, c in in_v)
        out_cnt = sum(c for _, c in out_v)
        emit(f'\n◆ {dim}（基准: {note}）')
        emit(f'   节点 {len(nodes)} 个: 词表内 {len(in_v)} 个（题记关联 {in_cnt}）｜'
             f'表外 {len(out_v)} 个（题记关联 {out_cnt}）')
        if out_v:
            for n, c in out_v[:15]:
                emit(f'   · 表外: 「{n}」（{c} 条）')
            if len(out_v) > 15:
                emit(f'   · …其余 {len(out_v) - 15} 项见完整报告')

    # ─── 信息性维度 ───
    emit('\n' + '─' * 72)
    emit('三、信息性维度（无封闭词表，仅登记）')
    emit('─' * 72)
    for dim in INFORMATIONAL:
        rel = REL_OF[dim]
        nodes = fetch_nodes(dim, rel)
        if nodes:
            emit(f'◆ {dim}: {len(nodes)} 个节点（来源：数据原始层级值/复合标签）')

    # ─── 孤儿节点检测（任何路径都无法连到题记的枢纽） ───
    emit('\n' + '─' * 72)
    emit('四、孤儿节点检测（经任何路径均不与题记相连）')
    emit('─' * 72)
    orphans = run("MATCH (n) WHERE NOT n:`题记` AND NOT EXISTS {(n)-[*1..3]-(:`题记`)} "
                  "RETURN labels(n)[0] AS label, n.name AS name")
    if orphans:
        for label, name in orphans:
            emit(f'✗ 孤儿: [{label}] 「{name}」 — 建议删除（历史导入残留）')
    else:
        emit('✓ 无孤儿节点')

    out_path = ROOT / 'data' / 'cleaned' / 'neo4j_rules_audit.txt'
    out_path.write_text('\n'.join(report), encoding='utf-8')
    print(f'\n完整报告: {out_path}')


if __name__ == '__main__':
    main()
