import sys,json
from pathlib import Path
W=Path(__file__).resolve().parents[3];sys.path.insert(0,str(Path(__file__).parent))
import delta_cconn_1025 as C
raw=json.load(open(W/'physical/die_plan/s81/die_plan.json')); rep={}
types=[tn for tn,t in raw['partition_types'].items() if any(h['module']==C.XF[0] for h in t.get('hard_cores',[]))]
for size in C.xfin_sizes():
    misses=[tn for tn in types if not C.xfin_grow(raw['partition_types'][tn],rep,size,dry=True)]
    print('TRY',size,misses,flush=True)
    if not misses: break
else: raise SystemExit('No common xfin outline fits every parent')
for tn in types: rep[tn]=C.xfin_grow(raw['partition_types'][tn],rep,size)
C.xfin_pins(W/'physical/die_plan/s81/inputs/core_pins/ot_s81dv_xfin.json',size)
# Preserve the plan's compact per-bit encoding.
import compact_plan as pdump
(W/'physical/die_plan/s81/die_plan.json').write_text(pdump.dumps(raw))
Path(sys.argv[1]).write_text(json.dumps(dict(size=size,types=rep,cell_area_um2=75438.654,fill=75438.654/(size[0]*size[1])),indent=1))
