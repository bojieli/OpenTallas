"""Create an isolated actual-native A0 reset source from the pinned REGROOT5 ODB.
Run in OpenROAD's Python interpreter. No placement/timing qualification is implied.
The original face FF is retained as stage two. Only reset-cone endpoint inputs
and its D input change; every old cell/master and all other equations survive.
"""
import collections,hashlib,json,os,re
import odb
path=os.environ['A0_ODB']; out=os.environ['A0_OUT']; os.makedirs(out,exist_ok=True)
db=odb.dbDatabase.create(); odb.read_db(db,path); block=db.getChip().getBlock()
seq=re.compile(r'DFF|LATCH|DHL'); trans=re.compile(r'^(BUF|INV|HB).*ASAP7')
def key(p):return p.getInst().getName()+'/'+p.getMTerm().getName()
def ins(i):return [p for p in i.getITerms() if str(p.getIoType())=='INPUT' and p.getNet() and str(p.getSigType()) not in ('POWER','GROUND')]
def outs(i):return [p for p in i.getITerms() if str(p.getIoType())=='OUTPUT' and p.getNet()]
def clocks(i):return sorted({p.getNet().getName() for p in ins(i) if p.getMTerm().getName() in ('CK','CLK','CP','clk') or str(p.getMTerm().getSigType())=='CLOCK'})
def snapshot():return {key(p):(p.getNet().getName() if p.getNet() else None) for i in block.getInsts() for p in i.getITerms()}
old=snapshot(); oldmasters={i.getName():i.getMaster().getName() for i in block.getInsts()}
root=block.findInst('u_g.reset_q$_DFF_P_'); assert root and root.getMaster().getName()=='DFFHQNx1_ASAP7_75t_R'
rootq=root.findITerm('QN').getNet(); raw=root.findITerm('D').getNet(); assert raw.getName()=='rst_n'
# Original QN is inverted, hence every path parity is explicit, including
# the native buffer/inverter forest rather than guessed RTL wire names.
def leaves(net,parity=0,seen=None):
 seen=set() if seen is None else set(seen)
 assert net.getId() not in seen;seen.add(net.getId());found=[]
 for p in net.getITerms():
  if str(p.getIoType())!='INPUT':continue
  i=p.getInst();m=i.getMaster().getName()
  if trans.match(m):
   oo=outs(i);assert len(oo)==1
   found+=leaves(oo[0].getNet(),parity^(m.startswith('INV')),seen)
  else:found.append((p,parity))
 return found
endpoints=leaves(rootq); assert len({key(p) for p,_ in endpoints})==len(endpoints)
def owners_net(net,seen=None):
 seen=set() if seen is None else set(seen)
 if net.getId() in seen:return set()
 seen.add(net.getId());result=set()
 for p in net.getITerms():
  if str(p.getIoType())!='INPUT':continue
  i=p.getInst()
  if seq.search(i.getMaster().getName()) or str(i.getMaster().getType())=='BLOCK':result.update(clocks(i))
  else:
   for oo in outs(i):result.update(owners_net(oo.getNet(),seen))
 return result
cohorts=collections.defaultdict(list)
for p,parity in endpoints:
 i=p.getInst()
 own=set(clocks(i)) if seq.search(i.getMaster().getName()) or str(i.getMaster().getType())=='BLOCK' else set().union(*(owners_net(oo.getNet()) for oo in outs(i)))
 assert len(own)==1,(key(p),own)
 cohorts[next(iter(own))].append((p,parity))
# Two face stages + one face-clock branch + local-clock leaf, equal depth.
# QN has inverted polarity. Every inserted FF has a dedicated inverter to
# expose positive reset. Both polarity outputs are available without ties.
added=[]; nodes=[]
def ff(name,clock,d):
 i=odb.dbInst.create(block,db.findMaster('DFFHQNx1_ASAP7_75t_R'),name)
 inv=odb.dbInst.create(block,db.findMaster('INVx1_ASAP7_75t_R'),name+'_positive')
 qn=odb.dbNet.create(block,name+'_qn');q=odb.dbNet.create(block,name+'_q')
 i.findITerm('D').connect(d);i.findITerm('CLK').connect(block.findNet(clock));i.findITerm('QN').connect(qn)
 inv.findITerm('A').connect(qn);inv.findITerm('Y').connect(q)
 added.extend([name,name+'_positive']);nodes.append(dict(name=name,clock=clock,d=d.getName(),q=q.getName(),qn=qn.getName()))
 return q,qn
face1,_=ff('a0_reset_face1','ck_fa4',raw);root.findITerm('D').disconnect();root.findITerm('D').connect(face1)
# Reuse existing original root inversion via a new independent inverter.
inv=odb.dbInst.create(block,db.findMaster('INVx1_ASAP7_75t_R'),'a0_reset_face2_positive');positive=odb.dbNet.create(block,'a0_reset_face2_q')
inv.findITerm('A').connect(rootq);inv.findITerm('Y').connect(positive);added.append(inv.getName())
groups=[]
for clock,ep in sorted(cohorts.items()):
 for first in range(0,len(ep),24):groups.append((clock,ep[first:first+24]))
assert len(groups)<=32
branch,_=ff('a0_reset_branch','ck_fa4',positive)
rows=[]
for n,(clock,group) in enumerate(groups):
 q,qn=ff('a0_reset_leaf_%02d'%n,clock,branch)
 for p,parity in group:
  previous=p.getNet().getName();p.disconnect();p.connect(q if parity else qn)
  rows.append(dict(endpoint=key(p),clock=clock,leaf=n,original_net=previous,root_qn_parity=parity,new_net=p.getNet().getName()))
new=snapshot();changed={k:[v,new[k]] for k,v in old.items() if new[k]!=v}
expected={r['endpoint'] for r in rows}|{key(root.findITerm('D'))};assert set(changed)==expected
assert all(block.findInst(n).getMaster().getName()==m for n,m in oldmasters.items())
# No ghost leaves: every one has original source consumers; raw pin one D.
assert all(any(r['leaf']==n for r in rows) for n in range(len(groups)))
manifest=dict(schema='opentallas.a0.native_reset.v1',input_sha256=hashlib.sha256(open(path,'rb').read()).hexdigest(),original_cells=len(oldmasters),added_cells=added,changed_original_inputs=changed,leaf_endpoints=rows,inserted_ff=nodes,face_stage2=root.getName(),face_clock='ck_fa4',raw_input_loads=1,face_stages=2,branch_stages=2,max_leaf_native_inputs=max(len(g) for _,g in groups),cohort_clocks={k:len(v) for k,v in sorted(cohorts.items())},stage4_local_release='four rising sample edges including face1, face2, branch and clock-owned leaf; phase/order explicit, not qualified',adoption=False,physical_phase_bound=False)
json.dump(manifest,open(out+'/manifest.json','w'),indent=2)
odb.write_db(db,out+'/candidate.odb')
# Emit exact native-source connectivity, named specialized top, all original
# BTerms preserved. Every master pin, including hard macro bit pins, explicit.
def esc(s):return '\\'+s+' '
with open(out+'/candidate.v','w') as f:
 f.write('// Generated from pinned actual REGROOT5 ODB; isolated source, no physical qualification.\nmodule qfd_tile_nk_regroot5_reset_native (\n'+',\n'.join(esc(p.getName()) for p in block.getBTerms())+'\n);\n')
 for p in block.getBTerms():f.write(str(p.getIoType()).lower()+' '+esc(p.getName())+';\n')
 portnames={p.getName() for p in block.getBTerms()}
 for net in block.getNets():
  if net.getName() not in portnames and str(net.getSigType()) not in ('POWER','GROUND'):f.write('wire '+esc(net.getName())+';\n')
 for p in block.getBTerms():
  if p.getNet().getName()!=p.getName():
   a,b=(p.getNet().getName(),p.getName()) if str(p.getIoType())=='INPUT' else (p.getName(),p.getNet().getName())
   f.write('assign '+esc(a)+' = '+esc(b)+';\n')
 for i in block.getInsts():
  pins=[p for p in i.getITerms() if p.getNet() and str(p.getSigType()) not in ('POWER','GROUND')]
  bundles=collections.defaultdict(dict); scalar=[]
  for p in pins:
   m=re.fullmatch(r'(.*)\[(\d+)\]',p.getMTerm().getName())
   if m:bundles[m[1]][int(m[2])]=p.getNet().getName()
   else:scalar.append('.'+esc(p.getMTerm().getName())+'('+esc(p.getNet().getName())+')')
  for name,bits in sorted(bundles.items()):
   assert set(bits)==set(range(max(bits)+1)),(name,bits)
   scalar.append('.'+esc(name)+'({'+','.join(esc(bits[n]) for n in reversed(range(max(bits)+1)))+'})')
  f.write(esc(i.getMaster().getName())+' '+esc(i.getName())+' (\n'+',\n'.join(scalar)+'\n);\n')
 f.write('endmodule\n')
print('A0_RESET_NATIVE_CREATED',len(rows),'consumers',len(groups),'clock-owned leaves',len(added),'added cells')
