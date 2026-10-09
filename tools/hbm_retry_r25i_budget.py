import sys,json,hashlib,pathlib
sys.path.insert(0,'tools')
import hbm_accel_die_fp as H
import hbm_die_clock_inputs as C
m=C.apply(H.build(H.R25I,network_probe=True))
p={k:v for k,v in H.manhattan_paths(m).items() if k.startswith('link') or 'su_coll' in k}
b=[dict(name=n,kind=c,bits=w,endpoints=e) for n,c,w,e in m['buses'] if 'link' in n or 'lkS' in n or 'lkN' in n]
r=dict(variant='CURRENT_R25I',scope='GEOMETRIC_PATHFINDING_NO_FF_CAPTURE_OR_FEC_MEASUREMENT',clock_contract=m['external_clock_inputs'],paths=p,buses=b,physical_RTT_qualified=False,RTT_cycles=None,source_sha256={f:hashlib.sha256(pathlib.Path('tools',f).read_bytes()).hexdigest() for f in ['hbm_accel_die_fp.py','hbm_die_clock_inputs.py']})
pathlib.Path('budget.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(p,indent=2))
