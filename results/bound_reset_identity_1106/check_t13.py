import sys,json,copy
from pathlib import Path
from types import SimpleNamespace
w=Path('/srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106');sys.path.insert(0,str(w/'tools/die_plan'))
import bound_reset_contract as B,gen_phys as G,reset_tree as R
p=Path(__file__).parent/'t13';tn='ot_s81sl_leaf__t13';files=[p/'t13_wrapper.sv',p/'t13.sv',p/'bind_cells.sv']
r=B.source(p/'t13.sv',tn,p,w);r['bound_module']='s81p_ot_s81sl_leaf__t13_bound'
t=json.loads((p/'current_type.json').read_text());P=SimpleNamespace(types={tn:t})
try:G.install_bound_native_reset(P,tn,files,source_contract=r)
except Exception as e:print('CURRENT308_REJECTED',e)
else:raise AssertionError('308 accepted')
t['clock']['landing_contract']['collector_tree']=copy.deepcopy(r['tree'])
c=G.install_bound_native_reset(P,tn,files,source_contract=r)
(p/'out').mkdir(exist_ok=True);B.stage(p/'out',r,c)
node=next(x for x in c['physical_nodes'] if x['name']=='u_rrl_176');assert node['d']=='rst_root_n' and node['depth']==1 and abs(node['xy'][0]-1388.88)<1e-6 and abs(node['xy'][1]-922.32)<1e-6
assert len(c['tree']['relays'])==306 and len(c['physical_nodes'])==307
text=(p/'out/reset_tree.tcl').read_text();assert '1388.880 922.320' in text and 'disconnect' not in text and 'u_bound[./]u_rrl_176[./]*' in text
print('ACTUAL306_VERIFIED',len(c['native_paths']),c['verified_cell_classes'],c['planned_native_max_hop_um'])
print('TREE_SHA',r['tree_sha256'])
(p/'out/actual_result.json').write_text(json.dumps(dict(relays=306,physical_nodes=307,node176=node,max_hop_um=c['planned_native_max_hop_um'],tree_sha256=r['tree_sha256']),indent=1))

import shutil
for src in files:shutil.copyfile(src,p/'out'/src.name)
copied=[p/'out'/src.name for src in files]
c2=G.install_bound_native_reset(P,tn,copied)
assert c2['native_paths']==c['native_paths']
assert c2['physical_nodes']==c['physical_nodes']
bad=copy.deepcopy(c['physical_nodes'])
next(x for x in bad if x['name']=='u_rrl_176')['xy']=[86.4,17.28]
try:B.placement(P,tn,c['tree'],bad,c['native_paths'])
except ValueError as e:assert 'beyond captured reach' in str(e);print('ACTUAL_WRONG176_MUTANT_REJECTED',e)
else:raise AssertionError('wrong long-edge physical placement accepted')
print('STAGED_KIT_REIMPORT_PASS')
