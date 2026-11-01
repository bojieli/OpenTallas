import json,sys,collections,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S,check as C
import core_face_repin as F
root=Path(sys.argv[2]);raw=json.load(open(root/'die_plan.json'));col=json.load(open(root/'core_faces_full.json'))
hcs={(tn,hc['inst']):hc for tn,t in raw['partition_types'].items() for hc in t.get('hard_cores',[])}
groups=collections.defaultdict(list)
for key,hc in hcs.items():
 recs=[r for r in col if (r['type'],r['inst'])==key and r['mean']<C.FACE_AWAY_COS and not F.CLKRST.match(r['port'])]
 if not recs:continue
 ori=hc.get('orient','R0');assign={}
 for r in recs:
  f=min(F.FACES,key=lambda f:F.score_face([dict(r,orient=ori)],f)[0]);assign[r['port']]=f
 groups[(hc['pins_file'],ori,tuple(sorted(assign.items())))].append((key,recs))
rep={'note':'Only unsigned core views: incompatible partner directions demonstrated by per-table minimum FAIL counts; minimal shared table groups for equal face assignments. No cycles/outline/origins/clock/reset pins changed.','tables':[]}
for (pf,ori,assign),users in sorted(groups.items()):
 pins=json.load(open(root/pf)); original=json.loads(json.dumps(pins)); by=collections.defaultdict(list)
 for x in pins:by[F.base(x['name'])].append(x)
 hc=hcs[users[0][0]];cw,ch=hc['outline_um'];changes=[]
 for port,face in sorted(assign,key=lambda z:-len(by[z[0]])):
  recs=[dict(r,orient=ori) for _,rs in users for r in rs if r['port']==port]
  tang=[]
  for r in recs:
   for _,ux,uy in r['dirs']:
    x,y=F.core_dir(ori,ux,uy);tang.append(x if face in 'NS' else y)
  lay,step,nfree=F.place(pins,by[port],face,cw,ch,S.Plan(raw,None).layers,sum(tang)/len(tang),hc)
  changes.append(dict(port=port,face=face,pins=len(by[port]),layer=lay,trackstep=step,free=nfree))
 old_controls=[p for p in original if F.CLKRST.match(p['name'])];new_controls=[p for p in pins if F.CLKRST.match(p['name'])];assert old_controls==new_controls
 sh=hashlib.sha256(json.dumps(assign).encode()).hexdigest()[:10];dst=str(Path(pf).with_name(Path(pf).stem+'__cf1101_'+sh+'.json'));json.dump(pins,open(root/dst,'w'),indent=0)
 for key,_ in users:hcs[key]['pins_file']=dst
 rep['tables'].append(dict(source=pf,out=dst,users=[list(x[0]) for x in users],changes=changes,controls_byteidentical=True))
json.dump(raw,open(root/'specific_repin_plan.json','w'),indent=0);json.dump(rep,open(root/'specific_repin_report.json','w'),indent=2)
print('tables',len(rep['tables']),'cores',sum(len(t['users']) for t in rep['tables']),'ports',sum(len(t['changes']) for t in rep['tables']))
