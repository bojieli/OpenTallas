import json,subprocess,pathlib,sys
r=pathlib.Path.cwd();out=r/'results/arch/qw_landw_1019/native_1020';jobs=json.loads((out/'jobs.json').read_text());rows=[]
for j in jobs:
 cmd=[sys.executable,'tools/hier_contract/native_pin_audit.py','--root',str(r),'--view',j['view'],'--cell',j['cell'],'--case','k0,k1,k2,k3','--case-evidence','QW-LAND8/QW-LANDW GEN contract: each own K strap constant from tie cells; GEN must set_case_analysis all four, actual per-instance K proof separately owed']
 p=subprocess.run(cmd,text=True,capture_output=True);(out/(j['job']+'.json')).write_text(p.stdout);(out/(j['job']+'.stderr')).write_text(p.stderr);rows.append(dict(job=j['job'],rc=p.returncode))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
