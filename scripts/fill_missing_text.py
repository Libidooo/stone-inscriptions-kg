import os
#!/usr/bin/env python3
"""
Fill missing 题记原文 entries from 5.2题记汇总.docx
Source: 5.2题记汇总.txt (980 entries with explicit numbering) + 5.2题记汇总.docx (fuller content)
"""

import re, pandas as pd, sys, docx, os
sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = os.environ.get('EXTERNAL_OUT_DIR', '')  # 外部输出目录，经环境变量提供

# ─── 1. Parse txt with explicit numbering ──────────────────────────
txt_lines = open(r'V:\图谱\5.2题记汇总.txt', 'r', encoding='utf-8').read().split('\n')

cn_map = {'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000}
def cn2n(s):
    total=0; tmp=0
    for ch in s:
        n=cn_map.get(ch,0)
        if n>=10:
            if tmp==0: tmp=1
            total+=tmp*n; tmp=0
        else: tmp+=n
    return total+tmp

entry_pat = re.compile(r'^第([零〇一二三四五六七八九十百千万]+)条')

# Find all entry positions
txt_entries = {}
i = 0
while i < len(txt_lines):
    m = entry_pat.match(txt_lines[i].strip())
    if m:
        seq = cn2n(m.group(1))
        start = i + 1
        end = start
        while end < len(txt_lines):
            if entry_pat.match(txt_lines[end].strip()):
                break
            end += 1
        txt_entries[seq] = (start, end)
        i = end
    else:
        i += 1

print('Txt entries parsed: %d' % len(txt_entries))

# ─── 2. Parse docx into entries ─────────────────────────────────────
doc = docx.Document(os.path.join(os.path.expanduser('~'), 'Desktop', '5.2题记汇总.docx'))
docx_paras = [p.text.strip() for p in doc.paragraphs]

docx_entries = []
current = []
for t in docx_paras:
    if t:
        current.append(t)
    else:
        if current:
            docx_entries.append(current)
            current = []
if current:
    docx_entries.append(current)
# Skip first entry (document title)
if docx_entries and docx_entries[0][0].startswith('《'):
    docx_entries = docx_entries[1:]

print('Docx entries parsed: %d' % len(docx_entries))

# ─── 3. For each missing seq, extract text ──────────────────────────

failed_extraction = [92, 269, 310, 429, 439, 911, 919, 947]  # in txt but extraction failed
not_in_txt        = [422, 423, 424, 445, 446, 447, 448, 449, 450, 451, 452, 453]  # not in txt

def extract_from_txt(seq):
    """Extract raw text from txt entry by combining all lines."""
    if seq not in txt_entries:
        return None
    start, end = txt_entries[seq]
    lines = txt_lines[start:end]
    # Filter out pure metadata lines (题记时间/造像时间/地点/造像题材/来源/备注/作者/妆饰时间/重装等)
    # Keep lines that are actual inscription content
    meta_prefixes = ('题记时间', '造像时间', '妆饰时间', '重装时间', '地点', '造像题材',
                     '妆饰题材', '重装题材', '来源', '备注', '作者', '题材',
                     '《', '（', '(', '另', '共')
    text_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_meta = any(stripped.startswith(p) for p in meta_prefixes)
        if is_meta:
            continue
        # Skip lines that are purely source info
        if '造像记' in stripped and len(stripped) < 15:
            continue
        text_lines.append(stripped)
    return '\n'.join(text_lines) if text_lines else None

def find_docx_entry(seq_num, name, deity, loc_short):
    """Find the matching docx entry for a given seq number.
    Uses multiple strategies:
    1. Check docx entries that contain '至第四百X条' markers
    2. Match by location + deity keywords
    """
    # Strategy: search all docx entries for matching content
    best_matches = []
    for ei, entry in enumerate(docx_entries):
        combined = '\n'.join(entry)
        score = 0
        if loc_short and loc_short in combined:
            score += 2
        if deity and '十六罗汉' in combined and '十六罗汉' in str(deity):
            score += 3
        elif deity and deity != '[不详]' and isinstance(deity, str) and len(deity) > 2:
            if deity in combined:
                score += 2
        if name and any(kw in combined for kw in name.replace('（', '(').replace('）', ')').split('记')[0].split('造像')):
            score += 1
        if score > 0:
            best_matches.append((score, ei, entry))
    if best_matches:
        best_matches.sort(key=lambda x: -x[0])
        return best_matches[0][2]
    return None

def extract_from_docx(entry):
    """Extract 题记文字 from a docx entry."""
    for line in entry:
        if line.startswith('题记文字'):
            # Extract text after the prefix
            if '：' in line:
                text = line.split('：', 1)[1]
                if text.strip():
                    return text.strip()
            elif ' ' in line:
                text = line.split(' ', 1)[1] if len(line.split(' ', 1)) > 1 else ''
                if text.strip():
                    return text.strip()
    # If no 题记文字 found, combine all lines that aren't metadata
    meta_prefixes = ('题记时间', '造像时间', '妆饰时间', '重装时间', '地点', '造像题材',
                     '妆饰题材', '重装题材', '来源', '备注', '作者', '题记名称')
    texts = []
    for line in entry:
        stripped = line.strip()
        if not stripped:
            continue
        is_meta = any(stripped.startswith(p) for p in meta_prefixes)
        if is_meta:
            continue
        texts.append(stripped)
    return '\n'.join(texts) if texts else None

# Read Excel for name/deity/location reference
df_excel = pd.read_excel(r'V:\图谱\5.7实体.xlsx')

# Process all 20 missing entries
results = {}
all_missing = failed_extraction + not_in_txt

for seq in all_missing:
    row = df_excel[df_excel['题记序号'] == seq]
    if len(row) == 0:
        results[seq] = None
        continue
    name = str(row.iloc[0]['题记名称'])
    deity = str(row.iloc[0].get('所造佛像名称', ''))
    loc = str(row.iloc[0].get('地点', ''))
    loc_short = loc[:10] if loc else ''

    # Try extracting from txt first
    text = extract_from_txt(seq)
    if text:
        print('seq %d: from txt (%d chars)' % (seq, len(text)))
        results[seq] = text
        continue

    # Try extracting from docx
    docx_entry = find_docx_entry(seq, name, deity, loc_short)
    if docx_entry:
        text = extract_from_docx(docx_entry)
        if text:
            print('seq %d: from docx (%d chars) via scoring' % (seq, len(text)))
            results[seq] = text
            continue

    # Manual lookups for specific cases
    if seq == 422:
        # 横梁子造像记 → likely has very minimal text
        for ei, entry in enumerate(docx_entries):
            if any('大唐贞观廿一年' in l for l in entry):
                results[seq] = '大唐贞观廿一年岁次丁未九月一日甲申/口弟子王佛愿敬造释嘉口一龛六/(道?)众生普同供养。'
                print('seq %d: manual match - 横梁子王佛愿' % seq)
                break
    elif seq == 423:
        for ei, entry in enumerate(docx_entries):
            if any('任永乐敬造' in l for l in entry):
                text = extract_from_docx(entry)
                results[seq] = text
                print('seq %d: manual match - 横梁子任永乐' % seq)
                break
    elif seq == 424:
        # 横梁子任永安 → look for combined entry with 王宝定 + 任永乐 + 任永安
        for ei, entry in enumerate(docx_entries):
            if any('任永安' in l for l in entry) and any('王宝定' in l for l in entry):
                text = extract_from_docx(entry)
                results[seq] = text
                print('seq %d: manual match - 横梁子任永安' % seq)
                break
    elif seq in (445, 446, 447, 448, 449, 450, 451, 452, 453):
        # 圆觉洞造像记（一窟多人） → map to sequential docx entries
        # docx entries ~444-458 correspond to 圆觉洞 area
        # Excel 445-453 = docx 444-452 offset
        offset_map = {445: 444, 446: 445, 447: 446, 448: 447, 449: 448,
                      450: 449, 451: 450, 452: 451, 453: 452}
        if seq in offset_map:
            idx = offset_map[seq]
            if idx < len(docx_entries):
                text = extract_from_docx(docx_entries[idx])
                if text:
                    results[seq] = text
                    print('seq %d: from docx entry %d' % (seq, idx))
                    continue
        print('seq %d: NOT FOUND' % seq)
    else:
        print('seq %d: NOT FOUND' % seq)

# ─── 4. Merge into the combined file ────────────────────────────────
print()
print('=== Summary ===')
merged_csv = os.path.join(OUT_DIR, '5.7实体含原文.csv')
df_merged = pd.read_csv(merged_csv, encoding='utf-8-sig')
filled = 0
still_missing = 0
for seq, text in results.items():
    if text:
        df_merged.loc[df_merged['题记序号'] == seq, '题记原文'] = text
        filled += 1
    else:
        still_missing += 1
        print('STILL MISSING: seq %d' % seq)

# Write updated file
out_csv = os.path.join(OUT_DIR, '5.7实体含原文.csv')
out_xlsx = os.path.join(OUT_DIR, '5.7实体含原文.xlsx')
df_merged.to_csv(out_csv, index=False, encoding='utf-8-sig')
df_merged.to_excel(out_xlsx, index=False)

print('Filled: %d / 20' % filled)
print('Still missing: %d' % still_missing)
print('Updated: %s' % out_csv)
