#!/usr/bin/env python3
"""把 Excel 母檔「C級題庫_母檔.xlsx」的資料寫進 vocab-c.html。

用法（在 gsat-english-site 資料夾內執行；只用 Python 內建模組，不需安裝套件）：
    python tools/sync-c-data.py "C:\\...\\2_題庫母檔\\C級題庫_母檔.xlsx"
加上 --check 只比對、不寫檔。

只會改寫 vocab-c.html 裡的兩行：
    const WEEKS_INFO = [...];   每週字數、優先度組成、複習週次
    const RAW_WORDS = [...];    單字資料
頁面其他部分（單字總數、級別選單、週數等）都是載入時由資料算出來的，不用跟著改。

RAW_WORDS 每筆欄位：
    [排名, 單字, 詞性, 級別(0=詞彙表外), 中文, 同字族, 日常頻率Zipf, 優先度(高/中/低),
     例句(**標紅**), 例句中譯(**標紅**), 週次]
"""
import html
import json
import re
import sys
import zipfile
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / 'vocab-c.html'
COLS = dict(A='rank', B='word', C='pos', D='level', E='zh', L='family',
            N='zipf', O='priority', P='example', Q='exampleZh')
PRI_ORDER = {'高': 0, '中': 1, '低': 2}
PER_WEEK_MAX = 40


def read_master(path):
    """讀母檔「題庫」工作表（第一個工作表）；公式欄（解析、出處、檢查）略過。"""
    s = zipfile.ZipFile(path).read('xl/worksheets/sheet1.xml').decode('utf-8')
    rows = []
    for _n, body in re.findall(r'<row r="(\d+)"[^>]*>(.*?)</row>', s, re.S)[1:]:
        d = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', body, re.S):
            col, inner = m.group(1), m.group(3) or ''
            if col not in COLS or '<f>' in inner:
                continue
            t = re.search(r'<t[^>]*>(.*?)</t>', inner, re.S)
            v = re.search(r'<v>(.*?)</v>', inner, re.S)
            d[COLS[col]] = html.unescape(t.group(1)) if t else (v.group(1) if v else '')
        if d.get('word', '').strip():
            rows.append(d)
    return rows


def plan_weeks(rows):
    """依「優先度 高→中→低，同優先度照排名」分週，每週約 38–39 字，共 ceil(N/40) 週。"""
    n = len(rows)
    weeks = -(-n // PER_WEEK_MAX)
    base, extra = divmod(n, weeks)
    order = sorted(range(n), key=lambda i: (PRI_ORDER.get(rows[i]['priority'], 9), int(rows[i]['rank'])))
    week_of, info, pos = {}, [], 0
    for w in range(1, weeks + 1):
        size = base + (1 if w <= extra else 0)
        members = order[pos:pos + size]
        pos += size
        for i in members:
            week_of[i] = w
        mix = {}
        for i in members:
            mix[rows[i]['priority']] = mix.get(rows[i]['priority'], 0) + 1
        mix_text = '／'.join(f'{k} {mix[k]}' for k in ('高', '中', '低') if k in mix)
        if w == 1:
            review = '—'
        else:
            prev = w - 1
            back = max(1, w - 4)
            review = f'第 {prev} 週' + (f'＋第 {back} 週' if back != prev else '')
        info.append({'week': w, 'title': f'第 {w} 週', 'wordCount': size,
                     'mix': '優先度 ' + mix_text, 'review': review})
    return week_of, info


def build(rows):
    week_of, info = plan_weeks(rows)
    raw = []
    for i, r in enumerate(rows):
        raw.append([
            int(r['rank']), r['word'].strip(), r['pos'].strip(),
            int(r['level']) if r.get('level', '').strip() else 0,
            r['zh'].strip(), r.get('family', '').strip(),
            float(r['zipf']) if r.get('zipf', '').strip() else 0,
            r['priority'].strip(), r['example'].strip(), r['exampleZh'].strip(), week_of[i]])
    return raw, info


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    raw, info = build(read_master(args[0]))
    text = PAGE.read_text(encoding='utf-8')
    new_weeks = 'const WEEKS_INFO = ' + json.dumps(info, ensure_ascii=False, separators=(',', ':')) + ';'
    new_raw = 'const RAW_WORDS = ' + json.dumps(raw, ensure_ascii=False, separators=(',', ':')) + ';'
    out, n1 = re.subn(r'^const WEEKS_INFO = .*;$', lambda m: new_weeks, text, flags=re.M)
    out, n2 = re.subn(r'^const RAW_WORDS = .*;$', lambda m: new_raw, out, flags=re.M)
    if (n1, n2) != (1, 1):
        sys.exit('vocab-c.html 找不到 WEEKS_INFO / RAW_WORDS 這兩行，沒有改動。')
    changed = out != text
    print(f'{len(raw)} 字，{len(info)} 週；' + ('資料有更新' if changed else '資料與頁面相同'))
    if changed and '--check' not in sys.argv:
        PAGE.write_text(out, encoding='utf-8', newline='')
        print('已寫入', PAGE.name)


if __name__ == '__main__':
    main()
