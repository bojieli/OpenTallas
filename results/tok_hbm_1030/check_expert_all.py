"""Qualify bounded dynamic expert relocation on all40 actual source blocks."""
import copy,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];p=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools');sys.path[:0]=[str(root/'tools/hbm_next'),str(p/'hbm_next'),str(p),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC,vm_expert_entry as E
from hgi_sim import machine as M
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes());packets=[];checks=0
profiles=[[[0,1,2,3,4,383]]*6,[list(range(i*6,(i+1)*6))for i in range(6)],[[0,7,11,19,i+30,383]for i in range(6)]]
for first,(_,union,x,_)in enumerate(rr):
 if(union.unit,union.op)!=('IDX','UNION'):continue
 blob,packet=E.lower(rr,first);last=packet['source_range'][1];low=IC.decode_all(blob);segments=packet['segments'];T=lambda n:E.translate(n,segments)
 for rows in profiles:
  old=((np.arange(1<<19,dtype=np.uint64)*2654435761)^0x9e3779b9).astype(np.uint32);a=union.desc['A']
  for rho,ids in enumerate(rows):old[a.base+rho*a.stride:a.base+rho*a.stride+6]=ids
  ids,tables=IR.idx_union(rows,384,7);old[union.desc['D'].base]=len(ids);old[union.desc['O'].base:union.desc['O'].base+len(ids)]=ids
  for L,(n,entries)in enumerate(tables):
   addr=union.desc['R'].base+L*32;old[addr:addr+32]=0;old[addr]=n;old[addr+1:addr+1+n]=[IR.entry_word(*e)for e in entries]
  new=np.zeros(262144,np.uint32)
  for s in segments:
   a,b=s['source_words'];c,d=s['vm_words'];new[c:d]=old[a:b]
  od=M.Die(0,M.Hbm());nd=M.Die(0,M.Hbm());od.vm=old;nd.vm=new;om=M.Machine([od]);nm=M.Machine([nd])
  for index in range(first,last+1):
   r,x=rr[index][1:3];q,y=low[index-first][1:3]
   for L in range(len(ids))if x and x.rsel else(0,):
    original=IR.expand(r,x,old,L);relocated=IR.expand(q,y,new,L);assert len(original)==len(relocated)
    for(slot,o),(nslot,n)in zip(original,relocated):
     assert slot==nslot;expected=copy.deepcopy(o)
     for k,d in expected.desc.items():
      if d.space=='VM':d.base=T(d.base)
     if(expected.unit,expected.op)==('CTL','LOOP'):expected.imm_a=T(expected.imm_a)
     assert vars(expected)==vars(n),'native arithmetic/shape/slot changed';checks+=1
     om.cur=o;nm.cur=n
     for k,d in o.desc.items():
      if d.indexed:
       oldid=int(old[o.desc['I'].base+L]);newid=int(new[n.desc['I'].base+L]);assert oldid==newid
       if d.space=='VM':
        oa=om.eff(d,od,L)[0];na=nm.eff(n.desc[k],nd,L)[0];assert old[oa]==new[na],'indexed VM payload differs';checks+=1
       else:assert d.base+oldid*d.dyn_mul==n.desc[k].base+newid*n.desc[k].dyn_mul
  assert int(old[union.desc['D'].base])==int(new[T(union.desc['D'].base)])
 packets.append(dict(source_range=packet['source_range'],native_commands=len(low),high_water_words=packet['high_water_words']))
controls=[]
for label,mutate in [('union_shape',lambda rs:setattr(rs[1559][1].desc['A'],'m',7)),('unknown_rtab',lambda rs:setattr(rs[1562][2],'rtab',rs[1562][2].rtab+32)),('unknown_index_extent',lambda rs:setattr(rs[1560][1].desc['A'],'dyn_mul',2))]:
 bad=copy.deepcopy(rr);mutate(bad)
 try:E.lower(bad)
 except ValueError:controls.append(label)
 else:raise AssertionError('unknown dynamic source escaped: '+label)
assert len(packets)==40
print(json.dumps(dict(components=packets,profiles_per_component=len(profiles),checks=checks,controls=controls,max_vm_words=max(p['high_water_words']for p in packets),all_fit_old_vm=True,numerical_arithmetic=False,whole_programme_executable=False),indent=1))
