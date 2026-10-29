"""Prepare a standalone natural LP memory-landing child, never modify die plan."""
import importlib.util,json,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
b=Path(sys.argv[2]);b.mkdir(parents=True,exist_ok=True)
r=Path(__file__).resolve().parent
plan=json.load(open(sys.argv[1]))
plan['partition_types']['source_dsdv_mu_land']={'module':'dsdv_mu_land','outline_um':[475.2,216.0],'contents':[{'inst':'u_land','module':'dsdv_mu_land','status':'rework','note':'Standalone natural LP child only, no die adoption'}],'hard_cores':[dict(inst='u_land',module='dsdv_mu_land',origin_um=[0,0],outline_um=[475.2,216.0],orient='R0',track_offset_um=[.108,.012],pins_file=str(r/'pins.json'),lef=str((r/'dsdv_mu_land.lef').relative_to(repo)),obs_max='M5')]}
(b/'kit_plan.json').write_text(json.dumps(plan))
(b/'recipes.json').write_text(json.dumps({'dsdv_mu_land':{'ref_tile':'physical/ref_tile/dsdv_mu_land','io_hold':'sender_min'}},indent=2))
print('Prepared source-only standalone child; run modern legacy generator --trial, PLACE only before actual census/family plan.')
