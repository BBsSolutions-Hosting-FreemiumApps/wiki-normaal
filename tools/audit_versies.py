#!/usr/bin/env python3
"""Read-only check of all 66 RTF books against wiki blocks. No JS is modified."""
import sys,json,re,hashlib,subprocess,difflib,collections
from pathlib import Path

RTF=Path(sys.argv[1] if len(sys.argv)>1 else 'Ai-Elohim-YHWH-Studiebijbel-2026 (3).rtf')
OUT=Path(sys.argv[2] if len(sys.argv)>2 else 'tests/rtf-versievergelijking.json')
ROOT=Path(__file__).resolve().parent.parent
def got(path,prefix):
    raw=path.read_text(encoding='utf-8').strip()
    assert raw.startswith(prefix) and raw.endswith(');'), 'Onbekend JS-formaat '+str(path)
    return json.loads(raw[len(prefix):-2])
meta=got(ROOT/'data/meta.js','SBW.gotMeta(')
books=[b[0] for b in meta['books']]
assert len(books)==66
expr='|'.join(re.escape(b) for b in sorted(books,key=len,reverse=True))
header=re.compile(r'^\s*(?:\|\s*)?('+expr+r')\s+(\d{1,3}):(\d{1,3})(?=\b|\s|[-|])')
def key(m):return (books.index(m.group(1)),int(m.group(2)),int(m.group(3)))
def norm(s):
    s=s.replace('\x18','‘').replace('\x19','’').replace('\x1c','“').replace('\x1d','”')
    return re.sub(r'\s+',' ',s).strip()
data=RTF.read_bytes()
out=subprocess.check_output(['unrtf','--text',str(RTF)],timeout=300)
try: plain=out.decode('utf-8')
except UnicodeDecodeError:plain=out.decode('cp1252',errors='replace')
lines=plain.splitlines()
sources=[]
for i,line in enumerate(lines):
    m=header.match(line)
    if m:sources.append({'key':key(m),'line':i,'ref':line[:150]})
for i,item in enumerate(sources):
    end=sources[i+1]['line'] if i+1<len(sources) else len(lines)
    item['text']=norm(' '.join(lines[item['line']+1:end]))
old=[]
for i,(book,chapter,ref) in enumerate(meta['blk']):
    m=header.match(ref)
    if not m:raise ValueError('Ongeldige verseverwijzing: '+ref)
    old.append({'id':i,'key':key(m),'ref':ref})
books_data=[]
for b in range(66):
    p=ROOT/'data/b'/f'{b}.js'
    books_data.append(got(p,f'SBW.gotBook({b},'))
seq=difflib.SequenceMatcher(None,[x['key'] for x in old],[x['key'] for x in sources],autojunk=False)
matches={}
for op,ai,aj,bi,bj in seq.get_opcodes():
    if op=='equal':
        for oi,ni in zip(range(ai,aj),range(bi,bj)):matches[oi]=ni
counts=collections.Counter(); per_book=collections.defaultdict(collections.Counter)
miss=[]; diffs=[]
for i,o in enumerate(old):
    book=books[o['key'][0]]
    if i not in matches:
        counts['unmatched_headers']+=1;per_book[book]['unmatched_headers']+=1
        if len(miss)<75:miss.append(o['ref'])
        continue
    block=books_data[o['key'][0]]['bl'].get(str(o['id']))
    if not block:counts['missing_blocks']+=1;continue
    existing=norm(' '.join(''.join(str(s[0]) for s in row if isinstance(s,list) and s) for row in block['x'] if isinstance(row,list)))
    new=sources[matches[i]]['text']
    counts['aligned_headers']+=1;per_book[book]['aligned_headers']+=1
    if existing==new:
        counts['exact_text_matches']+=1;per_book[book]['exact_text_matches']+=1
    else:
        counts['text_mismatches']+=1;per_book[book]['text_mismatches']+=1
        if len(diffs)<100:
            diffs.append({'ref':o['ref'],'similarity':round(difflib.SequenceMatcher(None,existing,new).ratio(),3),
                         'existing':existing[:260],'rtf':new[:260]})
report={'status':'READ_ONLY_AUDIT','safe_to_publish':False,'source_name':RTF.name,
        'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),
        'bible_books':len(books),'existing_blocks':len(old),'source_headers':len(sources),
        'counts':dict(counts),'per_book':{k:dict(v) for k,v in per_book.items()},
        'unaligned_examples':miss,'text_mismatch_examples':diffs,
        'note':'Deze analyse vervangt nog geen tekst of kleuren. Bronheaders en wiki-records zijn verschillende gegevenslagen.'}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Bestaande blokken:',len(old),'bronheaders:',len(sources),'gekoppeld:',counts['aligned_headers'])
print('Exact:',counts['exact_text_matches'],'afwijkingen:',counts['text_mismatches'],'niet gekoppeld:',counts['unmatched_headers'])
print('Rapport:',OUT)
