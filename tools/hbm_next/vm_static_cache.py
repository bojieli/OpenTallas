#!/usr/bin/env python3
"""Compile-time resident-value tracking; eliminate only proven redundant DMA.

No runtime cache/allocator/RTL is added. Values have unique opaque identities;
actual copies propagate identities. Native arithmetic remains unchanged. Writes
conservatively assign fresh identities; unknown external HBM writes invalidate
all backing identities. Decisions depend only on the fixed command stream.
"""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
from vm_value_phase import engine_span
from vm_expert_entry import lower as expert_lower,translate
from vm_phase_region import merge_intervals


class Values:
 def __init__(self,backing):
  self.backing=backing;self.disjoint_external_writes=0;self.external_invalidations=0
  self.vm=np.zeros(262144,np.uint64);self.back=np.arange(1,524289,dtype=np.uint64);self.serial=524289
 def fresh(self,array,lo,hi):
  array[lo:hi]=np.arange(self.serial,self.serial+hi-lo,dtype=np.uint64);self.serial+=hi-lo
 def body(self,r,x,meta,expert_writes,IR):
  if expert_writes is not None:
   for lo,hi in expert_writes:self.fresh(self.vm,lo,hi)
   return
  if meta.get('expert_body'):return
  for slot,q in IR.expand(r,x):
   for name in IR.written_operands(q):
    if name not in q.desc:continue
    if q.desc[name].space=='VM':
     lo,hi=engine_span(q,name);self.fresh(self.vm,lo,hi)
    elif q.desc[name].space=='HBM':
     d=q.desc[name];sizes={'FP32':4,'U32':4,'BF16':2,'FP8E4M3':1,'INT8':1,'UE8M0':1}
     known=d.fmt in sizes and d.n>0 and d.m>0 and d.stride>=0 and d.istride>=0 and d.base>=0 and d.base>>37==0 and not any(getattr(d,k,0)for k in('indexed','dyn_sel','n_sel','lstride','l1stride'))
     end=d.base+(max(1,d.m)-1)*d.stride+(max(1,d.n)-1)*(d.istride or 1)*sizes.get(d.fmt,1)+sizes.get(d.fmt,1)
     if known and not(max(d.base,self.backing)<min(end,self.backing+524288*4)):self.disjoint_external_writes+=1
     else:self.fresh(self.back,0,len(self.back));self.external_invalidations+=1


def opaque_expert_writes(source,first,last,IR):
 raw,p=expert_lower(source,first,last);segs=p['segments'];ranges=[]
 for index in range(first,last+1):
  r,x=source[index][1:3]
  rows=[(0,r)]if x and x.rsel else IR.expand(r,x)
  for slot,q in rows:
   for name in IR.written_operands(q):
    if name not in q.desc or q.desc[name].space!='VM':continue
    lo,hi=engine_span(q,name)
    if x and x.rsel:hi+=((5*7+5)if x.emask>>IR.OPND.index(name)&1 else 5)*x.rs.get(name,0)
    ranges.append([translate(lo,segs),translate(hi-1,segs)+1])
 return merge_intervals(ranges)


def optimize(packet,raw,source,IR,mutant=None):
 ref=Values(packet['backing_range'][0]);actual=Values(packet['backing_range'][0]);records=[];blob=bytearray();mapping={};expert_at={};expert_indices=set();copy_checks=0;removed=0;removed_bytes=0;baseline_bytes=packet['transfer_bytes'];base=packet['backing_range'][0];fault_injected=False
 for ph in packet['phases']:
  if ph['kind']!='expert':continue
  begin,end=ph['command_range'];first_body=next(i for i in range(begin,end)if packet['records'][i]['kind']=='body')
  expert_at[first_body]=opaque_expert_writes(source,*ph['source_range'],IR)
  expert_indices.update(i for i in range(begin,end)if packet['records'][i]['kind']=='body')
 def emit(r,x,meta):
  enc=IR.encode(r,x);m=copy.deepcopy(meta);m.update(offset=len(blob),bytes=len(enc));records.append(m);blob.extend(enc)
 def execute_copy(values,r,kind):
  hb=r.desc['A'if kind=='load'else'O'];vm=r.desc['O'if kind=='load'else'A'];a=(hb.base-base)//4;n=hb.n;u=vm.base
  assert hb.base>=base and (hb.base-base)%4==0 and 0<=a<a+n<=524288 and 0<=u<u+n<=262144
  if kind=='load':values.vm[u:u+n]=values.back[a:a+n]
  else:values.back[a:a+n]=values.vm[u:u+n]
 for index,meta in enumerate(packet['records']):
  mapping[index]=len(records);r,x,_=IR.decode_one(raw,meta['offset']);kind=meta['kind']
  if kind in('load','store'):
   a,b=meta['source_words'];u,v=meta['vm_words'];assert a%8==b%8==u%8==v%8==0
   # Verify native packet metadata before using its static identity mapping.
   hb=r.desc['A'if kind=='load'else'O'];vd=r.desc['O'if kind=='load'else'A'];assert hb.base==base+a*4 and hb.n==b-a and vd.base==u and vd.n==b-a
   equal=np.all(actual.vm[u:v].reshape(-1,8)==actual.back[a:b].reshape(-1,8),axis=1);needed=np.flatnonzero(~equal);groups=np.split(needed,np.flatnonzero(np.diff(needed)!=1)+1)
   execute_copy(ref,r,kind)
   emitted=0
   for group in groups:
    if len(group)==0:continue
    lo=int(group[0])*8;hi=(int(group[-1])+1)*8;q=copy.deepcopy(r)
    q.desc['A'if kind=='load'else'O'].base+=lo*4;q.desc['A'if kind=='load'else'O'].n=hi-lo
    q.desc['O'if kind=='load'else'A'].base+=lo;q.desc['O'if kind=='load'else'A'].n=hi-lo
    m=copy.deepcopy(meta);m.update(source_words=[a+lo,a+hi],vm_words=[u+lo,u+hi],hbm_range=[base+4*(a+lo),base+4*(a+hi)],original_command=index)
    if mutant=='skip_first_required_load'and kind=='load'and not fault_injected:
     fault_injected=True;continue
    if mutant=='wrong_first_store'and kind=='store'and emitted==0:q.desc['O'].base+=32
    execute_copy(actual,q,kind);emit(q,None,m);emitted+=hi-lo
   # Full affected range equality establishes the copy-elision step even when
   # a partial sector was unmodified or contained NaN/metadata payloads.
   dstref=ref.vm[u:v]if kind=='load'else ref.back[a:b];dstactual=actual.vm[u:v]if kind=='load'else actual.back[a:b]
   assert np.array_equal(dstref,dstactual),f'copy-elision changed {kind} at original command{index}'
   copy_checks+=1;removed_bytes+=(b-a-emitted)*4
   if emitted==0:removed+=1
  else:
   m=copy.deepcopy(meta)
   if index in expert_indices:m['expert_body']=True
   if kind=='body':
    assert IR.encode(r,x)==raw[meta['offset']:meta['offset']+meta['bytes']],'body encoding changed'
    writes=expert_at.get(index);ref.body(r,x,m,writes,IR);actual.body(r,x,m,writes,IR)
   emit(r,x,m)
 mapping[len(packet['records'])]=len(records)
 assert np.array_equal(ref.vm,actual.vm)and np.array_equal(ref.back,actual.back),'final opaque value identity differs'
 out=copy.deepcopy(packet);out['records']=records
 for ph in out['phases']:
  begin,end=ph['command_range'];ph['command_range']=[mapping[begin],mapping[end]];ph['commands']=mapping[end]-mapping[begin]
 out.update(native_commands=len(records),transfer_bytes=baseline_bytes-removed_bytes,static_resident_value_cache=True,baseline_native_commands=packet['native_commands'],baseline_transfer_bytes=baseline_bytes,elision=dict(complete_dma_commands_removed=removed,bytes_removed=removed_bytes,copy_induction_checks=copy_checks,final_workspace_and_backing_equal=True,all_body_bytes_preserved=True,external_HBM_write_policy='prove exact static linear disjointness; invalidate all backing identities for unknown/overlapping writes',disjoint_external_write_rows=ref.disjoint_external_writes,external_invalidations=ref.external_invalidations,expert_write_policy='fresh opaque identities over conservative actual native output bounds'))
 return bytes(blob),out


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in('stream','source-image','compiler-tools','out-dir'):ap.add_argument('--'+name,required=True)
 a=ap.parse_args();p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
 import isa_rows as IR,image_check as IC
 path=Path(a.stream);packet=json.loads(path.read_text());raw=path.with_name('stream.hgi1r').read_bytes();source=IC.decode_all(Path(a.source_image).read_bytes());data,result=optimize(packet,raw,source,IR)
 controls=[]
 for mut in('skip_first_required_load','wrong_first_store'):
  try:optimize(packet,raw,source,IR,mut)
  except AssertionError:controls.append(mut)
  else:raise AssertionError('cache mutant escaped:'+mut)
 result['elision']['controls']=controls;out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);(out/'stream.hgi1r').write_bytes(data);(out/'stream.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:result[k]for k in('native_commands','transfer_bytes','baseline_native_commands','baseline_transfer_bytes','elision')}))

if __name__=='__main__':main()
