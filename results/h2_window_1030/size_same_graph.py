"""Root-authorized ordinary R9 sizing on the reviewed fixed H2 graph.

Uses canonical coordinate-descent objective/loads and 80ps IN/OUT guard.
No geometry/stage/fit change. Final qualification is deliberately deferred
until new footprints/converter/PG/collision/render review passes.
"""
from pathlib import Path
import json,math,sys
R=Path(sys.argv[1]);S=R/'src';O=R/'sizing'
if O.exists():raise SystemExit('sizing output already exists')
O.mkdir()
sys.path[:0]=[str(S/'results/core_lat_r8_1026'),str(S/'results/core_lat_r9_1026')]
import l0r_r8_uf3 as A
rec=json.loads((R/'candidate_v2/plan_geometry.json').read_text())[0]
sl=json.loads((R/'candidate_v2/slice_geometry_native.json').read_text())
root=next(n['xy_um'] for n in sl['core_tree']['nodes']if n['name']=='mp_ck_root')
length=sum(abs(a-b)for a,b in zip(root,rec['native_input']['xy_um']))
L=A.U.load_libs(R/'inputs/lib');master=rec['frozen_masters']['root']
arrival={c:A.U.R45*length*(A.U.C45*length/2+L[c][master]['cin'])for c in ('TT','FF')}
stock=A.V3.predict3
def native_input(P,libs,c,*args,**kw):
 kw['s_root']=math.hypot(kw.get('s_root',0),2.2*arrival[c])
 return stock(P,libs,c,*args,**kw)
A.V3.predict3=native_input
source=(S/'results/core_lat_r9_1026/l0r_r9_d1.py').read_text()
needle='rec["d1_uf3"]["prediction"] = A.calibrated_summary(P, L, pmax, pmin)'
assert source.count(needle)==1
source=source.replace(needle,'rec["d1_uf3"]["final_qualification"] = "DEFERRED pending actual converted footprints/PG/collision/render LOOK"')
# Canonical root is fixed throughout descent, so native entry arrival/slew are
# invariant. Full downstream loads and upstream timing are recomputed per trial.
sys.argv=[str(S/'results/core_lat_r9_1026/l0r_r9_d1.py'),str(R/'candidate_v2/plan_geometry.json'),str(R/'baseline/geo.txt'),str(R/'inputs/lib'),str(R/'inputs/uf_phys3_v1.json'),str(O/'plan_sized.json'),'--slew','80']
globals()['__file__']=sys.argv[0]
exec(compile(source,sys.argv[0],'exec'),globals())
(O/'scope.json').write_text(json.dumps(dict(topology='fixed reviewed e72',root='fixed actual native ck[0]',native_input_wire_um=length,native_input_arrival_ps=arrival,stages='unchanged',fit='unchanged uf_phys3_v1',qualification='not yet run'),indent=2)+'\n')
