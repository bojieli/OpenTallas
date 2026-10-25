#!/usr/bin/env python3
"""Head counterpart of KV's measured m5 extracted-SPEF ECO; frozen RTL/SDC/clock tree."""
import json,pathlib,shutil,sys
src=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]);here=pathlib.Path(__file__).resolve().parent
if out.exists():raise SystemExit(f'refuse existing {out}')
out.mkdir(parents=True)
for p in src.iterdir():
 if p.name in ('run','views','__pycache__') or p.name.startswith(('signoff','.ot-run','run_','sta_','image.')):continue
 if p.is_dir():shutil.copytree(p,out/p.name)
 elif p.is_file():shutil.copy2(p,out/p.name)
base=next((src/'run/results/asap7').glob('*/base'));nick=base.parent.name
b=out/'run/results/asap7'/nick/'base';b.mkdir(parents=True)
shutil.copy2(base/'5_2_route.odb',b/'4_cts.odb')
for n in ('6_final.spef','1_2_yosys.v','1_synth.v','clock_period.txt','mem.json','ot_face_flops.txt','ot_unreg_pins.txt'):
 if (base/n).is_file():shutil.copy2(base/n,b/n)
ob=src/'run/objects/asap7'/nick/'base'
if ob.exists():shutil.copytree(ob,out/'run/objects/asap7'/nick/'base')
for kind in ('logs','reports'):(out/f'run/{kind}/asap7'/nick/'base').mkdir(parents=True)
(b/'4_cts.sdc').write_text((out/'constraint.sdc').read_text()+'\nset_propagated_clock [all_clocks]\n')
with (out/'config.mk').open('a') as f:f.write('\n# Extracted SPEF repair, KV m5/DRV_LAST+RETIME_LAST recipe; 833ps unchanged\nexport POST_GLOBAL_ROUTE_TCL = /work/eco_route.tcl\noverride export PWR_NETS_VOLTAGES =\noverride export GND_NETS_VOLTAGES =\n')
for n in ('eco_route.tcl','run_eco.sh','run_inside.sh','pair_skew.tcl','signoff.py'):
 shutil.copy2(here/n if (here/n).is_file() else here.parents[1]/"die_plan"/n,out/n)
(out/'ECO.json').write_text(json.dumps({'source_kit':str(src),'source_route':str(base/'5_2_route.odb'),'source_parasitics':str(base/'6_final.spef'),'recipe':'KV measured m5, maxfanout24/slew20/setup10/hold5,DRV_LAST=1,RETIME_LAST=1','RTL_SDC_clock':'unchanged','corners':['tt','ff']},indent=2)+'\n')
print(out)
