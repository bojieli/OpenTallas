#!/usr/bin/env python3
from pathlib import Path
import json,re,hashlib,sys,shutil
HERE=Path(__file__).resolve().parent
k=Path(sys.argv[1]);ledger=json.load(open(HERE/'actual_macro_aliases.json'));mapping=ledger['mapping']
meta=k/'run/results/asap7/dp_col_h10_r0_p4__t1/base/1_2_yosys_native_metadata.json'
cells=json.load(open(meta))['modules']['s81p_col_h10_r0_p4__t1']['cells']
assert len(mapping)==87 and len(set(mapping.values()))==87
assert all(n in cells for n in mapping.values())
prior=k/'prior_physical_aliases';prior.mkdir(exist_ok=True)
files=[*k.glob('*.tcl'),*k.glob('*.sdc'),*[k/x for x in ['budget.json','core_latency.json','landing_contract.json']]]
changed={}
for p in files:
 s=p.read_text();new=s
 for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):
  new=re.sub(r'(?<![\w.])'+re.escape(a)+r'(?![\w.])',lambda m:b,new)
 if new==s:continue
 if (prior/p.name).exists():raise RuntimeError('aliastransform already applied or concurrent modification: '+p.name)
 shutil.copy2(p,prior/p.name);p.write_text(new)
 changed[p.name]=dict(before=hashlib.sha256(s.encode()).hexdigest(),after=hashlib.sha256(new.encode()).hexdigest())
assert 'macro_place.tcl'in changed
placements=re.findall(r'place_macro -macro_name \{([^}]+)\}',(k/'macro_place.tcl').read_text())
assert len(placements)==87 and set(placements)==set(mapping.values())
(k/'actual_macro_aliases.json').write_text(json.dumps(dict(ledger,metadata_sha256=hashlib.sha256(meta.read_bytes()).hexdigest(),changed=changed,geometry='names only; exact original locations/orientations/pins/clock origins retained'),indent=2))
print('Applied exact87actual physical aliases to',list(changed),'No plan/RTL/geometry changes.')

