import odb,json,hashlib,re,sys
from pathlib import Path
sys.path.insert(0,'/work/own_audit/tools/ref_tile')
import native_census as NC
root=Path('/work/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_hroot_safe32_asap7_ref_gate/base');stage=sys.argv[1] if len(sys.argv)>1 else '4_1_cts';p=root/(stage+'.odb')
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

from collections import Counter,defaultdict
import gzip
rows=[];fixedpairs=[];instrows=[]
boundary_names=set()
for label in ['ot_out_flop_at_pins.txt','ot_inhold_firm.txt']:
 boundary_names.update(x.strip() for x in (root/label).read_text().splitlines() if x.strip())
def group(n):
 z=n.replace('\\','')
 for pattern,label in [('h0','head_capture'),('h1','head_middle'),('ctl_root','control_root'),('sid_root','strap_root'),('rst_root','reset_root')]:
  if ('u_esh.'+pattern) in z:return label
 if 'u_esh.cap[' in z:return 'head_capture' if '.q0$' in z else 'head_middle'
 if 'u_esh.region[' in z:
  if '.ctl' in z:return 'regional_control'
  if '.sid' in z:return 'regional_strap'
  if '.rn' in z:return 'regional_reset'
  if '.q' in z:return 'head_launch'
 if 'u_rly.' in z:return 'relay_'+z.split('u_rly.',1)[1].split('[')[0].split('$')[0]
 if 'ot_rst' in z or 'rst_land' in z:return 'flow_reset_landing'
 if 'hold' in z.lower() or 'pin' in z.lower():return 'flow_pin_helper'
 if n in boundary_names:return 'flow_boundary_identity'
 if 'ot_rst' in z.lower() or 'ot_pr_rst' in z.lower():return 'flow_reset_landing'
 return 'anonymous_mapped_cone'
for i in b.getInsts():
 role=roles.get(i.getMaster().getName(),{});mt=i.getMaster()
 instrows.append(dict(name=i.getName(),master=mt.getName(),status=i.getPlacementStatus(),fixed=i.isFixed(),boundary_identity=i.getName() in boundary_names,sequential=role.get('sequential'),transparent=i.getId() in trans,group=group(i.getName()),area_um2=mt.getWidth()*mt.getHeight()/u/u))
def fixed(t):return not hasattr(t,'getInst') or t.getInst().getName() in boundary_names
for driver,net,name in roots:
 if name=='port:ck' or nmap[net].getSigType()=='CLOCK':continue
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
 for t in ends.values():
  sp=point(t)
  if sp is None:continue
  if fixed(driver) and fixed(t):
   sink=t.getInst().getName()+'/'+t.getMTerm().getName() if hasattr(t,'getInst') else 'port:'+t.getName()
   fixedpairs.append(dict(driver=name,sink=sink,l1_um=round((abs(dp[0]-sp[0])+abs(dp[1]-sp[1]))/u,3)))
fixedpairs.sort(key=lambda r:-r['l1_um'])
groups=defaultdict(lambda:dict(count=0,fixed=0,sequential=0,area_um2=0,unfixed_area_um2=0))
for i in instrows:
 g=groups[i['group']];g['count']+=1;g['fixed']+=i['fixed'];g['sequential']+=bool(i['sequential']);g['area_um2']+=i['area_um2'];g['unfixed_area_um2']+=0 if i['fixed'] else i['area_um2']
result=dict(status='CLASSIFICATION_ONLY_NOT_SUCCESSOR',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),liberty=receipts,status_counts=dict(Counter(i['status'] for i in instrows)),groups=groups,fixed_to_fixed_pairs=len(fixedpairs),fixed_to_fixed_max_um=fixedpairs[0]['l1_um'] if fixedpairs else 0,fixed_to_fixed_over405=[x for x in fixedpairs if x['l1_um']>405],fixed_to_fixed_top30=fixedpairs[:30],total_area_um2=sum(i['area_um2'] for i in instrows),unfixed_area_um2=sum(i['area_um2'] for i in instrows if not i['fixed']),boundary_named_instances=sum(i['boundary_identity'] for i in instrows),nonboundary_functional_area_um2=sum(i['area_um2'] for i in instrows if i['sequential'] is not None and not i['boundary_identity']),unclassified_core_sequential=[i for i in instrows if i['sequential'] and not i['boundary_identity'] and i['group']=='anonymous_mapped_cone'],central_fence_area_um2=6400,role_errors=sorted(set(errors)),limitation='CTS stage includes clock/repair cells absent at preGPL. Exact successor preGPL classification must be repeated. Instance/BPin-centre coordinate proxy.')
Path('/out/central_classification_'+stage+'.json').write_text(json.dumps(result,indent=2)+'\n')
with gzip.open('/out/central_instances_'+stage+'.json.gz','wt') as f:json.dump(instrows,f)
print({k:v for k,v in result.items() if k not in ['groups','liberty','fixed_to_fixed_top30','fixed_to_fixed_over405','unclassified_core_sequential']})
print('boundary_pairs_over405',len(result['fixed_to_fixed_over405']),'unclassified_core_seq',len(result['unclassified_core_sequential']))
