#!/usr/bin/env python3
"""Opt-in physical view split for measured conflicts in shared HBM bank pin tables.
Keep identical failing directional signatures shared; only the original table's
conflicting instances gain separate physical tables. Outlines/source/cycles stay fixed.
The ordinary core_face_repin tool performs the subsequent actual repin.
"""
import sys,json,copy,hashlib,os,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import check as C, schema as S
src,out=map(Path,sys.argv[1:3]); out.mkdir(parents=True,exist_ok=True)
r=json.load(open(src/'die_plan.json'));p=S.Plan(copy.deepcopy(r),src/'die_plan.json'); rec=[]
C.check_core_faces(p,C.Report(True),str(src),None,collect=rec)
hcs={(tn,h['inst']):h for tn,t in r['partition_types'].items() for h in t.get('hard_cores',[])}
bad={}
for x in rec:
 if x['mean']>=C.FACE_AWAY_COS:continue
 h=hcs[x['type'],x['inst']]
 if 'vms_bank' not in h['module']:continue
 face=C.best_face(x['dirs']); ori=h.get('orient','R0')
 if ori in ('MX','R180') and face in 'NS':face={'N':'S','S':'N'}[face]
 if ori in ('MY','R180') and face in 'EW':face={'E':'W','W':'E'}[face]
 bad.setdefault((x['type'],x['inst']),[]).append((x['port'],face))
for f in src.iterdir():
 if f.name=='die_plan.json':continue
 d=out/f.name
 if f.is_dir():shutil.copytree(f,d,dirs_exist_ok=True)
 elif not d.exists():os.link(f,d)
changes=[]
for key,signature in sorted(bad.items()):
 h=hcs[key]; old=h['pins_file']; sig=hashlib.sha256(json.dumps(sorted(signature)).encode()).hexdigest()[:8]
 new=old[:-5]+'__conflict_'+sig+'.json'
 if not (out/new).exists():shutil.copy2(src/old,out/new)
 h['pins_file']=new
 changes.append(dict(type=key[0],inst=key[1],old=old,new=new,signature=sorted(signature)))
(out/'die_plan.json').write_text(json.dumps(r,indent=1))
(out/'pin_conflicts_report.json').write_text(json.dumps(dict(schema='hbm.pin_conflicts.v1',changes=changes,new_tables=len(set(c['new'] for c in changes)),source_or_cycle_changes=0),indent=1))
print(len(changes),'instances',len(set(c['new'] for c in changes)),'new physical tables')
