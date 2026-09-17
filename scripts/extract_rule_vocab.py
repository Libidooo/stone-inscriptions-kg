#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从标注规范规则文件提取编码词表（供核验脚本 08 使用）"""
import re
import sys
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]  # 仓库根目录


sys.stdout.reconfigure(encoding='utf-8')
RULES = ROOT / '标注规范' / 'rules'


def extract_names(fname):
    txt = (RULES / fname).read_text(encoding='utf-8')
    # 表格行：|A\-01\-02<br>|发心建造|...  → 取第二列统一中文名称
    names = re.findall(r'^\|[A-Z][\d\\\-]+(?:<br>)?\|([^|]+)\|', txt, re.M)
    return [n.replace('<br>', '').replace('\\', '').replace('**', '').strip() for n in names if n.strip()]


vocab = {}
for fname in ['实践行为判定规则.md', '造像原因判定规则.md']:
    vocab[fname] = extract_names(fname)
    print(f"{fname}: {len(vocab[fname])} 个编码名")
    print(' ', vocab[fname])
    print()

out = ROOT / 'data' / 'config' / 'rule_vocab_extracted.json'
out.write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding='utf-8')
print('写入', out)
