"""Fresh master-plan then mesh2 lattice; preserve independent failure verdicts."""
import subprocess,json,sys
from pathlib import Path
repo=Path(sys.argv[1]);out=Path(sys.argv[2]);plan=out/'canonical68_ft.json';tools=repo/'tools/die_plan';records=[]
commands=[['python3',str(tools/'die_infra.py'),'master-plan',str(plan),'--out',str(out/'master_plan'),'--tree-lattice','c4x4','--region-dist','--declared-slots','--core-obs-top','M7','--no-render'],['python3',str(tools/'qc_clk_mesh2.py'),'plan',str(plan),'--tree-plan',str(out/'master_plan/die_tree_plan.json'),'--rows','gaps','--gap-m','4','--gap-dy','144','--ky','1','--tap-at-driver','--out',str(out/'mesh2')]]
for tag,cmd in zip(['master_plan','mesh2'],commands):
 if tag=='mesh2' and not (out/'master_plan/die_tree_plan.json').is_file():records.append(dict(step=tag,status='BLOCKED: no freshly generated tree-plan'));break
 with (out/(tag+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
 records.append(dict(step=tag,returncode=r.returncode,command=cmd))
(out/'recipe_result.json').write_text(json.dumps(records,indent=1)+'\n');print(json.dumps(records,indent=1))
