import sys, json
sys.path.insert(0, '/home/ubuntu/wt-hbmphys-budget/tools')
import hbm_accel_die_fp as F
v = F.variant_arg(sys.argv[1])
m = F.build(v, network_probe=bool(v.get('sm_physical_grid')))
out = dict(geo={k: (x if isinstance(x,(int,float,str,list,dict)) else str(x)) for k,x in m['geo'].items()},
           insts=[i.d() for i in m['insts']],
           buses=[dict(bid=b[0], cls=b[1], bits=b[2], eps=[str(e) for e in b[3]]) for b in m['buses']],
           regions={k: str(x) for k,x in (m.get('regions') or {}).items()} if isinstance(m.get('regions'),dict) else str(m.get('regions'))[:2000])
json.dump(out, open(sys.argv[2],'w'))
print(len(out['insts']), len(out['buses']))
