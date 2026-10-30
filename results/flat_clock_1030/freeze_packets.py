import sys,gzip,json
from pathlib import Path
sys.path.insert(0,'snapshot_v5')
import flat_clock_forest as F
T=json.loads(Path('types.json').read_text())
for tag,kind in [('a','slice_station__t7__cl362204c4'),('b','slice_station__t7__cl945bc067')]:
 target=Path(f't7{tag}_flat_clock_forest_v5.json')
 if target.exists():raise FileExistsError(target)
 with gzip.open(f't7{tag}_corrected_native80_sites_v4.json.gz','rt') as f:c=json.load(f)
 places=json.loads(Path(f't7{tag}_sites_v4_placements.json').read_text())
 review=f'/srv/opentallas-scratch/claude/flat-clock-model/t7{tag}_flat_clock_sites_v4.png; LOOK 2026-10-30; native sites/occupancy; separate16 primary and native forwarded roots; endpoint-corrected FFs unchanged; planned connections not routed wires; physical recovery/root review still required'
 p=F.freeze_candidate(c,T[kind]['module'],places,'lib',review,type_spec=T[kind]);p['physical_authority']=False
 target.write_text(json.dumps(p))
 print(tag,json.dumps(dict(module=p['module'],roots=len(p['roots']),drivers=len(p['cells']),sinks=sum(len(n['sinks']) for n in p['cells']),periods=p['clock_periods'],max_leaf_reach_um=max(sum(abs(a-b) for a,b in zip(n['placement']['centre_um'],s['xy_um'])) for n in p['cells'] for s in n['sinks']),qualification='MODEL_PACKET_ONLY_NATIVE_RECOVERY_HELD')))
