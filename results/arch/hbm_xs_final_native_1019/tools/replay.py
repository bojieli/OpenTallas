import json,gzip,hashlib,sys,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).parent/'tools/closure_loop'))
import safe_source_contract as S
root=Path(__file__).parent/'out'; rawpath=root/'raw.json';raw=json.loads(rawpath.read_text())
top=next(iter(raw['modules']));mod=raw['modules'][top];omitted=Counter();physical=[]
for name,p in list(mod['ports'].items()):
 if p['signal_type'] in ('POWER','GROUND'):omitted['top_pg']+=len(p['bits']);del mod['ports'][name]
for name,c in list(mod['cells'].items()):
 pins=raw['native_master_pins'][c['type']]
 S.require(set(c['connections'])==set(pins),f'inventory {name}')
 for pin in list(c['connections']):
  S.require(c['pin_signal_types'][pin]==pins[pin]['signal_type'] and c['port_directions'][pin]==pins[pin]['direction'],f'role {name}/{pin}')
  if pins[pin]['signal_type'] in ('POWER','GROUND'):
   omitted['instance_pg']+=len(c['connections'][pin]);del c['connections'][pin];del c['port_directions'][pin]
 if not c['connections']:physical.append(dict(instance=name,master=c['type'],pins=pins));del mod['cells'][name]
libs=sorted(p for p in root.glob('*.lib*') if 'FAKE' not in p.name)
provenance=dict(raw_sha256=S.sha(rawpath),odb_sha256=raw['source_odb_sha256'],collector_sha256=S.sha(S.__file__),libs=[dict(path=p.name,sha256=S.sha(p)) for p in libs],pg_omissions=dict(omitted),pg_only_cells=physical)
try:
 native=S.native_cells(libs,used_masters={c['type'] for c in mod['cells'].values()});r=S.census(raw,top,native)
 r['provenance']=provenance
 with gzip.open(root/'census.json.gz','wt') as f:json.dump(r,f,sort_keys=True)
 summary={k:v for k,v in r.items() if k not in ('drivers','input_registration','output_ownership','provenance')}
 summary['canonical_violators']=[{k:v for k,v in d.items() if k not in ('endpoints','clock_endpoints')} for d in r['drivers'] if d['driver'] in r['violations'] and not d['transparent']]
 summary['provenance']={k:v for k,v in provenance.items() if k!='pg_only_cells'}
 summary['pg_only_cells']=len(physical)
except Exception as e:
 summary=dict(verdict='REFUSED',error=str(e),provenance={k:v for k,v in provenance.items() if k!='pg_only_cells'})
(root/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('provenance','canonical_violators')}))
