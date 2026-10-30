from pathlib import Path
import sys,json
D=Path('/srv/opentallas-scratch2/claude/codex-qc-kits-2249');sys.path.insert(0,str(D/'src/tools/die_plan'))
import check as C,schema as S
out={}
for name in ['base_plan','macro_plan']:
 raw=json.load((D/(name+'.json')).open());r,summary=C.run(raw,plan_dir=D,completeness=True)
 out[name]={'errors':r.errors(),'summary':summary};(D/(name+'_g0c.json')).write_text(json.dumps(out[name],indent=2,default=list)+'\n');print(name,'errors',len(r.errors()),flush=True)
old={json.dumps(i,sort_keys=True) for i in out['base_plan']['errors']};new=[i for i in out['macro_plan']['errors'] if json.dumps(i,sort_keys=True) not in old]
(D/'macro_g0c_delta.json').write_text(json.dumps({'new_errors':new,'base_errors':len(out['base_plan']['errors']),'macro_errors':len(out['macro_plan']['errors'])},indent=2)+'\n');print('NEW',new,flush=True)
