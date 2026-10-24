// 把 vocab-quiz 儲存庫的 A、B 級題庫（詞性、例句）同步到 vocab-a.html、vocab-b.html。
// 用法（在 gsat-english-site 資料夾內執行）：
//   node tools/sync-ab-from-quiz.js check <vocab-quiz 資料夾>   只比對，列出會改幾處
//   node tools/sync-ab-from-quiz.js apply <vocab-quiz 資料夾>   寫入兩個頁面
// 只改 RAW_WORDS 裡每個字的詞性（第 3 欄）與例句（第 15 欄）；排名、考頻、週次等欄位不動。
// 單字清單必須與 data/A.json、data/B.json 一致，否則會中止。
const fs = require('fs');
const mode = process.argv[2];
const QUIZ = process.argv[3];
if (!['check', 'apply'].includes(mode) || !QUIZ) { console.log(process.argv[1], '← 請看檔案開頭的用法'); process.exit(1); }
const path = require('path');
const SITE = path.resolve(__dirname, '..');
const strip = s => (s || '').replace(/\*\*/g, '');
const MARK = 'const RAW_WORDS = ';
let total = { pos: 0, ex: 0, cleared: 0 };

for (const L of ['A', 'B']) {
  const f = path.join(SITE, `vocab-${L.toLowerCase()}.html`);
  const h = fs.readFileSync(f, 'utf8');
  const i = h.indexOf(MARK) + MARK.length;
  const j = h.indexOf('];', i) + 1;
  const slice = h.slice(i, j);
  const old = JSON.parse(slice);
  console.log(`${L}: 無損往返 ${JSON.stringify(old) === slice}`);

  const nw = JSON.parse(fs.readFileSync(path.join(QUIZ, 'data', `${L}.json`), 'utf8'));
  const nm = new Map(nw.map(x => [strip(x.word).toLowerCase(), x]));
  let pos = 0, ex = 0, cleared = 0;
  for (const r of old) {
    const n = nm.get(r[1].toLowerCase());
    if (!n) { console.log(`${L}: 題庫裡找不到 ${r[1]}，已中止`); process.exit(1); }
    if (r[2] !== n.pos) { r[2] = n.pos; pos++; }
    const want = strip(n.example);
    if ((r[14] || '') !== want) { if (!want) cleared++; r[14] = want; ex++; }
  }
  console.log(`${L}: 詞性 ${pos}、例句 ${ex}（其中清空 ${cleared}）`);
  total.pos += pos; total.ex += ex; total.cleared += cleared;
  if (mode === 'apply') fs.writeFileSync(f, h.slice(0, i) + JSON.stringify(old) + h.slice(j));
}
console.log(mode, JSON.stringify(total));
