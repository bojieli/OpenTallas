import odb,json,hashlib,re,sys
from pathlib import Path
sys.path.insert(0,'/audit_tools')
import native_census as NC
p=next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/4_1_cts.odb'))
log=Path('/gate/cts.log').read_text();libs=sorted(set(re.findall(r'^read_liberty (\S+)',log,re.M)))
roles,receipts=NC.liberty_roles(libs)
d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron();roots=[];loads={};trans={};errors=[];nmap={n.getId():n for n in b.getNets()}
def point(t):
 if hasattr(t,'getInst'):
  
  if t.getInst().getMaster().isBlock():
   ok,x,y=t.getAvgXY()
   if not ok:raise RuntimeError('no macro pin geometry:'+t.getInst().getName()+'/'+t.getMTerm().getName())
   return(x,y)
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
  pn=t.getMTerm().getName();pr=role['pins'].get(pn)
  if pr is None:
   bm=re.fullmatch(r'(.*)\[(-?\d+)\]',pn)
   if bm and int(bm[2]) in role['bus_order'].get(bm[1],[]):pr=role['pins'].get(bm[1])
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
macro_names={i.getName() for i in b.getInsts() if 'grp_rsp' in i.getMaster().getName()}
macro_nets={t.getNet().getId() for i in b.getInsts() if i.getName() in macro_names for t in i.getITerms() if t.getNet()}
print("DEBUG",len(macro_names),len(roots),len(loads),len(trans),len(errors),errors[:5],[(n,roles[n].get("sequential"),list(roles[n].get("pins",{}).items())[:2]) for n in roles if "grp_rsp" in n])
rows=[]
for driver,net,name in roots:
 if name in ('port:ck','port:hck'):continue
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
 if vals and ((hasattr(driver,'getInst') and driver.getInst().getName() in macro_names) or any(hasattr(t,'getInst') and t.getInst().getName() in macro_names for t in ends.values())):rows.append(dict(driver=name,net=nmap[net].getName(),terminal_count=len(ends),max_endpoint_manhattan_um=round(max(vals),3)))
rows.sort(key=lambda r:-r['max_endpoint_manhattan_um']);result=dict(clock_exclusion='Declared spec clock ports ck/hck excluded as roots; actual Liberty clock pins excluded at terminals; no ODB-label-based data exemption.',method='Truth-functional unary BUF/INV traversal using actual loaded TT/FF Liberty files; source driver to distinct nontransparent/nonclock endpoint Manhattan distance. Macro-pin actual getAvgXY; standard-cell instance-centre/BPin-centre coordinate proxy. Only roots with tiny-ring macro driver or endpoint retained; these are transparent-root-to-terminal reaches, not complete sequential combinational-cone path lengths.',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),liberty=receipts,role_errors=sorted(set(errors)),transparent_instances=len(trans),roots_with_endpoints=len(rows),max_endpoint_manhattan_um=rows[0]['max_endpoint_manhattan_um'] if rows else None,over405=[x for x in rows if x['max_endpoint_manhattan_um']>405],top30=rows[:30]);Path('/out/placed_reach_union.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['top30','liberty','over405']});print('over405',len(result['over405']))
if errors or not rows:raise SystemExit(2)
