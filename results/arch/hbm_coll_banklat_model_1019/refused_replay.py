import sys,json,hashlib
from pathlib import Path
import strict_contract as S
r=Path(sys.argv[1]);raw=json.loads((r/'raw.json').read_text());top=next(iter(raw['modules']));m=raw['modules'][top]
counts={'cells':len(m['cells']),'ports':len(m['ports']),'masters':len(raw['native_master_pins'])}
for n,c in list(m['cells'].items()):
 pins=raw['native_master_pins'][c['type']]
 S.require(set(c['connections'])==set(pins),f'pin inventory {n}')
 for p in list(c['connections']):
  S.require(c['pin_signal_types'][p]==pins[p]['signal_type'],f'role {n}/{p}')
  if pins[p]['signal_type'] in ('POWER','GROUND'):
   del c['connections'][p];del c['port_directions'][p]
 if not c['connections']:del m['cells'][n]
for n,p in list(m['ports'].items()):
 if p['signal_type'] in ('POWER','GROUND'):del m['ports'][n]
libs=sorted(r.glob('*.lib*'))
try:
 native=S.native_cells(libs,used_masters={c['type'] for c in m['cells'].values()});result=S.census(raw,top,native)
except Exception as e:
 result={'status':'REFUSED','reason':type(e).__name__+': '+str(e),'no_safe_claim':True}
result['source_odb_sha256']=raw['source_odb_sha256'];result['raw_counts']=counts
result['inputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [r/'raw.json']+libs}
Path('strict_refusal.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
