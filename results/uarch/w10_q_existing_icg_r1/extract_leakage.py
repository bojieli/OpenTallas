import gzip,hashlib,json,re
from decimal import Decimal as D
from pathlib import Path
base=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');items=[];by_cell={}
for corner in ('SS','TT','FF'):
 for group,date in [('SIMPLE','211120'),('AO','211120'),('OA','211120'),('INVBUF','220122'),('SEQ','220123')]:
  p=base/f'asap7sc7p5t_{group}_RVT_{corner}_nldm_{date}.lib';p=p if p.exists() else Path(str(p)+'.gz');r=p.read_bytes();s=gzip.decompress(r).decode() if p.suffix=='.gz' else r.decode();largest=D(0);winner=''
  for m in re.finditer(r'cell\s*\(([^)]*)\)\s*\{',s):
   i=m.end();depth=1
   while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
   c=s[m.start():i];values=[abs(D(v)) for v in re.findall(r'leakage_power\s*\([^)]*\)\s*\{[^}]*?value\s*:\s*([-+\d.eE]+)',c,re.S)];scalar=re.search(r'cell_leakage_power\s*:\s*([-+\d.eE]+)',c)
   bound=max(sum(values,D(0)),D(scalar[1]) if scalar else D(0))
   by_cell[m[1]]=max(by_cell.get(m[1],D(0)),bound*D('1e-12'))
   if bound>largest:largest=bound;winner=m[1]
  items.append({'path':str(p),'source_sha256':hashlib.sha256(r).hexdigest(),'max_cell':winner,'all_state_leakage_upper_pW':str(largest)})
Path('/out/leakage_palette.json').write_text(json.dumps({'sources':items,'per_cell_all_state_leakage_upper_W':{k:str(v) for k,v in sorted(by_cell.items())},'global_all_state_cell_leakage_upper_W':str(max(D(x['all_state_leakage_upper_pW']) for x in items)*D('1e-12'))},indent=2)+'\n')
