import re, csv, sys

txt_path = 'V:/图谱/5.2题记汇总.txt'
csv_path = 'V:/图谱/题记原文.csv'

lines = open(txt_path, 'r', encoding='utf-8').read().split('\n')

# Entry boundary: line starts with 第(Chinese number)条
# Numbers include: 零〇一二三四五六七八九十百千万
entry_pat = re.compile(r'^第[零〇一二三四五六七八九十百千万]+条')

field_markers = [
    '题记文字：', '题记内容：', '题记名称：', '题记时间：', '造像时间：',
    '妆饰时间：', '题记地点：', '地点：', '造像题材：', '妆饰题材：',
    '题记题材：', '题材：', '来源：', '备注：'
]

def is_field_start(t):
    for f in field_markers:
        if t.startswith(f):
            return True
    return False

def extract_text(lines_block):
    full = ''
    active = False
    for line in lines_block:
        t = line.strip()
        if not t:
            if active:
                full += '\n'
            continue

        if t.startswith('题记文字：'):
            if not active:
                full = t[5:]
                active = True
        elif t.startswith('题记内容：') and not active:
            full = t[5:]
            active = True
        elif is_field_start(t):
            active = False
        elif active:
            full += '\n' + t

    return full.strip()

# Find all entry boundaries
entries = []
for i, line in enumerate(lines):
    if entry_pat.match(line.strip()):
        entries.append(i)

# Process
results = []
for idx, si in enumerate(entries):
    ei = entries[idx + 1] if idx + 1 < len(entries) else len(lines)
    text = extract_text(lines[si + 1:ei])
    # Read the actual entry number from the header line
    hdr = lines[si].strip()
    m = entry_pat.match(hdr)
    num_str = m.group(0)
    cn_num = num_str[1:-1]  # strip 第 and 条
    
    # Map Chinese number to Arabic
    cn_map = {'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,
              '十':10,'百':100,'千':1000}
    def cn2n(s):
        total = 0
        tmp = 0
        for ch in s:
            n = cn_map.get(ch, 0)
            if n >= 10:
                if tmp == 0:
                    tmp = 1
                total += tmp * n
                tmp = 0
            else:
                tmp += n
        return total + tmp
    
    entry_num = cn2n(cn_num)
    results.append((entry_num, text))

# Sort by entry number
results.sort(key=lambda x: x[0])

# Fill gaps: ensure entries 1..max are present
max_num = max(r[0] for r in results)
num_map = dict(results)
all_entries = []
for n in range(1, max_num + 1):
    all_entries.append((n, num_map.get(n, '')))

# Write CSV
with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['序号', '题记原文'])
    for i, text in all_entries:
        w.writerow([i, text])

print(f'Total: {len(all_entries)} entries')
print(f'With text: {sum(1 for _, t in all_entries if t)}')
print(f'Without text: {sum(1 for _, t in all_entries if not t)}')
print(f'Max number: {max_num}')
print(f'CSV saved to: {csv_path}')
