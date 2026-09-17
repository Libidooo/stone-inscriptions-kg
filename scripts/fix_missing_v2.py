import os
#!/usr/bin/env python3
"""Precise fix for 12 not-in-txt entries using docx contextual matching."""

import pandas as pd, sys, docx, os
sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = os.environ.get('EXTERNAL_OUT_DIR', '')  # 外部输出目录，经环境变量提供
merged_csv = os.path.join(OUT_DIR, '5.7实体含原文.csv')
df = pd.read_csv(merged_csv, encoding='utf-8-sig')

doc = docx.Document(os.path.join(os.path.expanduser('~'), 'Desktop', '5.2题记汇总.docx'))
texts = [p.text.strip() for p in doc.paragraphs]
entries = []
current = []
for t in texts:
    if t: current.append(t)
    else:
        if current: entries.append(current); current = []
if current: entries.append(current)
entries = entries[1:]

def extract_clean_text(entry_lines):
    """Extract only 题记文字 content, strip metadata."""
    texts = []
    for line in entry_lines:
        s = line.strip()
        if not s: continue
        if any(s.startswith(p) for p in ('题记时间', '造像时间', '妆饰时间', '重装时间',
            '地点', '造像题材', '妆饰题材', '重装题材', '来源', '备注',
            '题记名称', '题记作者', '作者', '《', '至第')): continue
        if s.startswith('//'): continue
        # Clean field prefix
        for prefix in ['题记文字：', '题记文字……', '题记文字1：', '题记文字2：',
                       '题记文字3：', '题记文字4：', '题记文字5：', '题记文字6：',
                       '题记内容：']:
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        texts.append(s)
    return '\n'.join(texts) if texts else ''

# ─── Manual exact mapping based on content analysis ────────────────

fixes = {}

# ── 横梁子 entries (422-424) ──
# docx 427: ...任永乐敬造... → 横梁子4号龛, 二菩萨 → seq 423
# docx 429: combined entry, 任永安 张剑 记 part → seq 424
# seq 422 横梁子造像记, 景云二年711年, 地点横梁子造像 → docx 429 (景云二年)

fixes[422] = '景云二年二月二日于此'
fixes[423] = '……任永乐敬造…….'
fixes[424] = '任永安 张剑 记'

# ── 圆觉洞一窟多人 entries (445-453) ──
# All are 十六罗汉像 in 圆觉洞南面山崖 area
# docx entries 444-450 are in 圆觉洞 area, with 十六罗汉 content
# docx 450 is explicitly "至第四百五十三条" = txt 453
# Mapping by cave location + content:
# docx 444 (圆觉洞22号龛, 救苦白衣观音) → seq 445
# docx 446 (圆觉洞22号龛, 三世佛) → seq 446
# docx 447 (圆觉洞33号龛, 佛顶尊胜陀罗尼) → seq 447
# docx 448 (圆觉洞37号龛, 大悲观音菩萨) → seq 448
# docx 449 (圆觉洞40号龛, 装彩记) → seq 449
# docx 450 (圆觉洞40号龛, 十六罗汉题刻) → seq 450
# docx 451 (圆觉洞40号龛, 势至) → seq 451
# docx 452 (圆觉洞40号龛, 观音) → seq 452
# docx 453 (圆觉洞56号龛, 十王像) → seq 453

docx_map_445_453 = {
    445: 444,  # 敬鎸造救苦白衣觀音记
    446: 446,  # 敬镌桩三世
    447: 447,  # 佛顶尊胜陀罗尼
    448: 448,  # 大悲观音菩萨
    449: 449,  # 男..... (装彩记)
    450: 450,  # 至第四百五十三条 (十六罗汉题刻)
    451: 451,  # 势至……任……
    452: 452,  # 观音……女弟子杨……
    453: 453,  # /□□僧…… (十王像/重修)
}

for seq, idx in docx_map_445_453.items():
    if idx < len(entries):
        text = extract_clean_text(entries[idx])
        if text:
            fixes[seq] = text

# ── Apply fixes ──
for seq, text in fixes.items():
    df.loc[df['题记序号'] == seq, '题记原文'] = text
    print('seq %d: fixed (%d chars)' % (seq, len(text)))

# ── Also check 8 txt entries - just verify they're clean ──
for seq in [92, 269, 310, 429, 439, 911, 919, 947]:
    row = df[df['题记序号'] == seq]
    if len(row):
        txt = str(row.iloc[0]['题记原文'])
        print('seq %d: %d chars - %s...' % (seq, len(txt), txt[:60].replace('\n',' | ')))

# ── Write ──
df.to_csv(merged_csv, index=False, encoding='utf-8-sig')
df.to_excel(os.path.join(OUT_DIR, '5.7实体含原文.xlsx'), index=False)
print('\nDone!')
