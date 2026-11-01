"""Clone the reviewed real fixture inputs for a fixture-only normal data hold repair.

The original failing route remains immutable. Reuse actual routed child views;
only the parent's ORFS hold repair margin changes, from15ps to40ps.
"""
from pathlib import Path
import argparse,shutil,json
p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
if a.out.exists():raise SystemExit('refusing existing output root')
a.out.mkdir(parents=True)
for n in ('hold_tx','hold_rx'):
 shutil.copytree(a.baseline/n,a.out/n)
p=a.out/'hold_parent';p.mkdir()
for f in (a.baseline/'hold_parent').iterdir():
 if f.is_file() and f.suffix in ('.tcl','.mk','.sdc','.v','.json'):shutil.copy2(f,p/f.name)
shutil.copytree(a.baseline/'hold_parent/macros',p/'macros')
for n in ('parent_plan.json','run_route.sh','planned_geometry.png','render.py'):shutil.copy2(a.baseline/n,a.out/n)
f=p/'config.mk';s=f.read_text();assert s.count('export HOLD_SLACK_MARGIN = 15')==1;s=s.replace('export HOLD_SLACK_MARGIN = 15','export HOLD_SLACK_MARGIN = 40');f.write_text(s)
(a.out/'hold_repair_variant.json').write_text(json.dumps(dict(baseline=str(a.baseline),scope='fixture-only normal ORFS data hold repair',measured_ff_miss_ps=-8.628736,hold_repair_margin_ps=40,preserved='allRTL/childactualviews/macro+pin geometry/sourceclock-35/-85early,0late/833ps/TT0/FF25; globalgates unchanged'),indent=2)+'\n')
