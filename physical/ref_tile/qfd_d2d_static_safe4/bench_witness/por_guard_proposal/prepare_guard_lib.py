from pathlib import Path
import re,gzip,hashlib,json
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
files=sorted(p.glob('*RVT_TT*'));files=[f for f in files if 'FAKE' not in f.name]
texts={f.name:(gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()) for f in files}
def blocks(s,typ):
 for m in re.finditer(r'\b'+typ+r'\s*\(([^)]*)\)\s*\{',s):
  depth=1;i=m.end()
  while depth:
   depth+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m.group(1),s[m.start():i]
seq=next(s for n,s in texts.items() if '_SEQ_' in n);header=seq[:re.search(r'\bcell\s*\(',seq).start()];header=re.sub(r'library\s*\([^)]*\)','library (guard_actual_TT)',header,count=1)
for typ in ['lu_table_template','power_lut_template']:
 known={n for n,_ in blocks(header,typ)}
 for s in texts.values():
  for n,b in blocks(s,typ):
   if n not in known:header+='\n'+b+'\n';known.add(n)
cells={}
for s in texts.values():
 for n,b in blocks(s,'cell'):
  if n in cells:assert cells[n]==b
  cells[n]=b
Path('/data/guard_actual_TT.lib').write_text(header+'\n'+'\n'.join(cells.values())+'\n}\n')
Path('/data/guard_actual_liberty_sha256.json').write_text(json.dumps({str(p/n):hashlib.sha256((p/n).read_bytes()).hexdigest() for n in texts},indent=2)+'\n')
print('GUARD_LIBRARY actual_nonfake_cells',len(cells))
