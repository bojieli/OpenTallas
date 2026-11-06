import sys,json,copy
from pathlib import Path
from types import SimpleNamespace
w=Path('/srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106');sys.path.insert(0,str(w/'tools/die_plan'))
import bound_reset_contract as B,gen_phys as G
p=Path(__file__).parent;tn='ot_s81sl_leaf__t25__cl431c660f'
f=p/'t25_bound.sv';files=[p/'t25_wrapper.sv',f,p/'t13/bind_cells.sv']
r=B.source(f,tn,p,w);tree=r['tree'];assert len(tree['relays'])==237
outline=[max([tree['root'][k]]+[v['xy'][k] for v in tree['relays']])+10 for k in range(2)]
typ=dict(outline_um=outline,clock=dict(landing_contract=dict(collector_tree=copy.deepcopy(tree))))
P=SimpleNamespace(types={tn:typ})
c=G.install_bound_native_reset(P,tn,files,source_contract=r)
result=dict(type=tn,logical_relays=237,physical_nodes=len(c['physical_nodes']),tree_sha256=r['tree_sha256'],max_hop_um=c['planned_native_max_hop_um'],verified_cell_classes=c['verified_cell_classes'])
(p/'t25_result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
