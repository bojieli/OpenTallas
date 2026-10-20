import odb,json,hashlib,re,sys
from pathlib import Path
sys.path.insert(0,'/work/own_audit/tools/ref_tile')
import native_census as NC
root=Path('/work/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_hroot_safe32_asap7_ref_gate/base');p=root/'4_1_cts.odb'
log=Path('/work/cts.log').read_text();libs=sorted(set(re.findall(r'^read_liberty (\S+)',log,re.M)))
roles,receipts=NC.liberty_roles(libs)
d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron();roots=[];loads={};trans={};errors=[];nmap={n.getId():n for n in b.getNets()}
def point(t):
 if hasattr(t,'getInst'):
  z=t.getInst().getBBox();return ((z.xMin()+z.xMax())/2,(z.yMin()+z.yMax())/2)
 bs=[z for pin in t.getBPins() for z in pin.getBoxes()]
 if not bs:return None
 z=bs[0];return((z.xMin()+z.xMax())/2,(z.yMin()+z.yMax())/2)
for inst in b.getInsts():
 its=[t for t in inst.getITerms() if t.getNet() and t.getIoType() in ('INPUT','OUTPUT') and t.getSigType() not in ('POWER','GROUND')]
 if not its:continue
 role=roles.get(inst.getMaster().getName())
 if not role:errors.append('missingcell:'+inst.getMaster().getName());continue
 ins=[];outs=[]
 for t in its:
  pr=role['pins'].get(t.getMTerm().getName())
  if not pr:errors.append('missingpin:'+inst.getMaster().getName()+'/'+t.getMTerm().getName());continue
  if pr['direction']=='input':
   if not pr['clock']:ins.append(t);loads.setdefault(t.getNet().getId(),[]).append(t)
  elif pr['direction']=='output':outs.append((t,pr['function']))
 istrans=False
 if not role['sequential'] and len(ins)==1 and len(outs)==1:
  t,f=outs[0];pn=ins[0].getMTerm().getName();f=re.sub(r'[\s()]','',f or '')
  if f in (pn,'!'+pn,'~'+pn,pn+"'"):
   trans[inst.getId()]=t.getNet().getId();istrans=True
 for t,f in outs:
  const=not role['sequential'] and re.sub(r'[\s()]','',f or '') in ('0','1',"1'b0","1'b1")
  if not istrans and not const:roots.append((t,t.getNet().getId(),inst.getName()+'/'+t.getMTerm().getName()))
for t in b.getBTerms():
 n=t.getNet()
 if not n or n.getSigType() in ('POWER','GROUND'):continue
 if t.getIoType()=='INPUT':roots.append((t,n.getId(),'port:'+t.getName()))
 elif t.getIoType()=='OUTPUT':loads.setdefault(n.getId(),[]).append(t)
rows=[]
for driver,net,name in roots:
 if name=="port:ck" or nmap[net].getSigType()=="CLOCK":continue
 dp=point(driver)
 if dp is None:continue
 stack=[net];seen=set();ends={}
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  for t in loads.get(n,[]):
   if hasattr(t,'getInst') and t.getInst().getId() in trans:stack.append(trans[t.getInst().getId()])
   else:ends[(hasattr(t,'getInst'),t.getId())]=t
 vals=[(abs(dp[0]-sp[0])+abs(dp[1]-sp[1]))/u for t in ends.values() if (sp:=point(t)) is not None]
 if vals:rows.append(dict(driver=name,net=nmap[net].getName(),terminal_count=len(ends),max_endpoint_manhattan_um=round(max(vals),3)))
rows.sort(key=lambda r:-r['max_endpoint_manhattan_um']);result=dict(clock_exclusion='Declared spec clock port ck plus ODB CLOCK nets; Liberty clock pins excluded at terminals.',method='Truth-functional unary BUF/INV traversal using ten actual loaded TT/FF Liberty files; source driver to distinct nontransparent/nonclock endpoint Manhattan distance. Instance-centre/BPin-centre coordinate proxy.',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),liberty=receipts,role_errors=sorted(set(errors)),transparent_instances=len(trans),roots_with_endpoints=len(rows),max_endpoint_manhattan_um=rows[0]['max_endpoint_manhattan_um'],over405=[x for x in rows if x['max_endpoint_manhattan_um']>405],top30=rows[:30]);Path('/out/placed_reach_union.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['top30','liberty','over405']});print('over405',len(result['over405']))
if errors:raise SystemExit(2)
