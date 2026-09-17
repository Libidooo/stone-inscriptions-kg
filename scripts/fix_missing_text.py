import os
#!/usr/bin/env python3
"""Fix the 12 not-in-txt entries with exact docx mapping."""

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

def get_text(entry):
    """Extract clean 题记文字 from entry."""
    texts = []
    for line in entry:
        s = line.strip()
        if not s: continue
        # Skip pure metadata
        if any(s.startswith(p) for p in ('题记时间', '造像时间', '妆饰时间', '重装时间', '地点',
            '造像题材', '妆饰题材', '重装题材', '来源', '备注', '题记名称', '题记作者', '作者')): continue
        # Skip section headers
        if s.startswith('《') and s.endswith('》'): continue
        if s.startswith('//'): continue
        if s.startswith('至第'): continue
        texts.append(s)
    return '\n'.join(texts) if texts else ''

# ─── Map docx entries to exact excel seq ───────────────────────────

# From the txt: gaps are at 422, 423, 424, 445, 446, 447, 448, 449, 450, 451, 452, 453
# docx entries that fill these gaps:

gap_map = {
    # 横梁子 area
    422: 426,   # 横梁子造像记 → "大唐贞观廿一年...王佛愿敬造释嘉口一龛"
    423: 427,   # 横梁子任永乐杨穆造像记 → "...任永乐敬造....."
    424: 429,   # 横梁子任永安造像记 → combined entry with 任永安 张剑 记

    # 圆觉洞 area - all 一窟多人 entries (十六罗汉像)
    # docx entries 444-456 are 圆觉洞 area
    # entry 450 is "至第四百五十三条" (the 十六罗汉 labels entry)
    # offset: gap starts at txt 445, docx entry ~444
    445: 444,   # 圆觉洞（一窟多人）-2 → 敬鎸造救苦白衣觀音记
    446: 446,   # -3 → 敬镌桩三世
    447: 447,   # -4 → 佛顶尊胜陀罗尼
    448: 448,   # -5 → 大悲观音菩萨
    449: 449,   # -6 → / 男..... (装彩记)
    450: 450,   # -7 → 至第四百五十三条 (十六罗汉题刻)
    451: 451,   # -8 → 势至……任……
    452: 452,   # -9 → 观音……女弟子杨……
    453: 453,   # -10 → /□□僧…… (十王像/重修)
}

for seq, docx_idx in gap_map.items():
    if docx_idx < len(entries):
        text = get_text(entries[docx_idx])
        if text:
            df.loc[df['题记序号'] == seq, '题记原文'] = text
            print('seq %d (docx %d): OK (%d chars)' % (seq, docx_idx, len(text)))
        else:
            print('seq %d (docx %d): EMPTY text' % (seq, docx_idx))
    else:
        print('seq %d: docx idx %d out of range' % (seq, docx_idx))

# ─── Also check 8 txt entries for prefix noise ────────────────────
# Clean up entries that have field prefix noise
for seq in [92, 269, 310, 429, 439, 911, 919, 947]:
    row = df[df['题记序号'] == seq]
    if len(row):
        txt = str(row.iloc[0]['题记原文'])
        if '题记1文字：' in txt or '题记2文字：' in txt or '题记文字……' in txt or '题记文字1：' in txt:
            # Clean by extracting just the meaningful text
            lines = txt.split('\n')
            cleaned = []
            for line in lines:
                s = line.strip()
                if not s: continue
                # Remove field prefix
                for prefix in ['题记1文字：', '题记2文字：', '题记文字1：', '题记文字2：',
                               '题记文字3：', '题记文字4：', '题记文字5：', '题记文字6：',
                               '题记文字……', '题记文字：', '题记名称：', '题记作者：', '作者：',
                               '外龛右壁：', '题记文字']:
                    if s.startswith(prefix):
                        s = s[len(prefix):]
                        break
                cleaned.append(s)
            clean_text = '\n'.join(cleaned)
            df.loc[df['题记序号'] == seq, '题记原文'] = clean_text
            print('seq %d: cleaned prefix noise (%d chars)' % (seq, len(clean_text)))

# ─── Write ─────────────────────────────────────────────────────────
df.to_csv(merged_csv, index=False, encoding='utf-8-sig')
df.to_excel(out_xlsx if (out_xlsx := os.path.join(OUT_DIR, '5.7实体含原文.xlsx')) else '', index=False)

print('\nDone! Updated files in %s' % OUT_DIR)

# Verify
missing_ids = [92, 269, 310, 422, 423, 424, 429, 439, 445, 446, 447, 448, 449, 450, 451, 452, 453, 911, 919, 947]
print('\n=== Final verification ===')
for s in missing_ids:
    row = df[df['题记序号'] == s]
    if len(row):
        txt = str(row.iloc[0]['题记原文'])
        print('%3d: %s' % (s, txt[:80].replace('\n', ' | ')))
