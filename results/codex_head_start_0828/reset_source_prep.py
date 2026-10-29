"""Derive START reset sources from the final composed geometry and verify raw-Q fixed point."""
import json,sys
from pathlib import Path
repo,compose,stages,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
sys.path[:0]=[str(repo/'tools/die_plan'),str(repo/'tools/s81_head')]
import schema as S,reset_tree as RT
from head_start_reset_exports import plan_exports
from head_start_reset_aliases import reuse_existing,declare
src=compose/'landed_plan.json';raw=json.load(open(src));p=S.Plan(raw,src);st=json.load(open(stages/'start_stages.json'))
offsets=RT.wf_plan(p)
(out/'reset_offsets.json').write_text(json.dumps(offsets,indent=1)+'\n')
exports=reuse_existing(plan_exports(p,offsets,st),offsets)
(out/'exports.json').write_text(json.dumps(exports,indent=1)+'\n')
declared=declare(raw,exports);p2=S.Plan(declared,src)
bad=[];checked=0
for tn,rows in exports['types'].items():
    tree=RT.for_type(p2,tn)
    relays=RT.start_relays(tree) if tree.get('start') else tree['relays']
    byname={r['name']:r for r in relays}
    for row in rows:
        actual=byname.get(row['instance']);checked+=1
        if actual is None or actual['q']!=row['net'] or max(abs(a-b) for a,b in zip(actual['xy'],row['xy_um']))>.001:
            bad.append(dict(type=tn,expected=row,actual=actual))
report=dict(verdict='FAIL' if bad or exports['summary']['over_hop'] else 'PASS',selected_type_raw_sources=checked,
            raw_Q_or_coordinate_mismatches=len(bad),examples=bad[:8],reset_sources=exports['summary'],
            authority='actual current COMPOSE -> RT.for_type -> exports -> declare -> RT.for_type raw-Q/coordinate fixed point; physical phase NOT RUN')
(out/'fixedpoint.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps(report))
if report['verdict']!='PASS':raise SystemExit(1)
settle=max(74,exports['summary']['max_relative_raw_release']+4)
(out/'settle.txt').write_text(str(settle)+'\n')
