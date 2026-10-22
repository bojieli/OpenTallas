import json,re,collections,hashlib
from pathlib import Path
source=json.loads(Path('mapped.json').read_text());m=source['modules']['ot_s81sl_ve'];ledger=json.loads(Path('ve_native32_limit32.v.ledger.json').read_text())
area={};libsha={}
for name in ['AO','INVBUF','OA','SEQ','SIMPLE']:
 p=Path(name+'.lib');text=p.read_text();libsha[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 headers=list(re.finditer(r'cell\s*\(\s*([^\s)]+)\s*\)\s*{',text))
 for i,h in enumerate(headers):
  body=text[h.end():headers[i+1].start() if i+1<len(headers) else len(text)]
  a=re.search(r'\barea\s*:\s*([0-9.eE+-]+)(?:\s*;|\s*\n)',body)
  if a:area[h.group(1).strip('"')]=float(a.group(1))
old=collections.Counter(c['type'] for c in m['cells'].values() if c['type']!='$scopeinfo')
new=collections.Counter(m['cells'][original]['type'] for original in ledger['origins'].values())
unknown=sorted((set(old)|set(new))-set(area));assert not unknown,unknown
report=dict(kind='technology library area MODEL ONLY; emitted source not adopted',source_json_sha256=ledger['source_sha256'],candidate_sha256=ledger['output_sha256'],lib_sha256=libsha,limit=32,clones=ledger['clones'],old_cells=sum(old.values()),new_cells=sum(new.values()),old_library_area_um2=sum(area[t]*n for t,n in old.items()),new_library_area_um2=sum(area[t]*n for t,n in new.items()),old_ff=sum(n for t,n in old.items() if t.startswith(('DFF','SDFF'))),new_ff=sum(n for t,n in new.items() if t.startswith(('DFF','SDFF'))),extra_inv_note='emit may add INV edges after transparent canonicalization; retention area/native census still required')
Path('ve_resource_model.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
