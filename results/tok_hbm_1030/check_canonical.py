"""Algebraic source-address epoch proof for the conservative whole programme.

Workspace values carry their canonical source address identity. Writes invalidate
old physical/source aliases. This checks address/version routing without replaying
hundreds of millions of tagged words or replacing any numerical arithmetic.
"""
import argparse,copy,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];p=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools');sys.path[:0]=[str(root/'tools/hbm_next'),str(p/'hbm_next'),str(p),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC,vm_value_phase as V,vm_expert_entry as E,vm_canonical_stream as C
ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,default=Path(__file__).parent/'canonical_all');args=ap.parse_args();base=args.base;packet=json.loads((base/'stream.json').read_text());raw=(base/'stream.hgi1r').read_bytes();source=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes());backing=packet['backing_range'][0];ALL=65535


def remove(maps,lo,hi,physical=False):
 out=[]
 for a,b,u in maps:
  start=u if physical else a;end=start+b-a
  for l,h in((start,min(end,lo)),(max(start,hi),end)):
   if h>l:
    delta=l-start;out.append((a+delta,a+delta+h-l,u+delta))
 return out


def require(maps,a,b,u):
 spans=[]
 for lo,hi,actual in maps:
  l,h=max(lo,a),min(hi,b)
  if l<h and actual+l-lo==u+l-a:spans.append((l,h))
 end=a
 for lo,hi in sorted(spans):
  if lo>end:break
  end=max(end,hi)
 assert end>=b,f'source epoch unavailable{a}:{b}->workspace{u}'


def check(mutation=None):
 seen={};checks=0;expert_count=0;stream_pairs=0
 for ph in packet['phases']:
  begin,end=ph['command_range'];maps=[];rfirst,rlast=ph['source_range'];expert=ph['kind']=='expert'
  if not expert and ph['kind']=='static' and rlast>rfirst:assert C.static_group_end(source,rfirst,rlast,IR)>=rlast,'reverse row-group dependency'
  if expert:
   expected,ep=E.lower(source,rfirst,rlast);epdec=IC.decode_all(expected);bi=0;expert_count+=1
  for pos in range(begin,end):
   meta=packet['records'][pos];r,x,_=IR.decode_one(raw,meta['offset'])
   if mutation and pos==mutation[0]:mutation[1](r,x)
   if meta['kind'] in('load','store'):
    a,b=meta['source_words'];u,v=meta['vm_words'];assert v-u==b-a and 0<=u<v<=262144
    hb=r.desc['A'if meta['kind']=='load'else'O'];vm=r.desc['O'if meta['kind']=='load'else'A']
    assert hb.base==backing+4*a and hb.n==b-a and vm.base==u and vm.n==b-a and r.wait==ALL,'native boundary descriptor differs'
    if meta['kind']=='load':maps=remove(maps,u,v,True)+[(a,b,u)]
    elif not expert:require(maps,a,b,u)
    continue
   if meta['kind']!='body':assert r.wait==ALL;continue
   index=meta['source_record'];seen.setdefault(index,[])
   if expert:
    q,y=epdec[bi][1:3];bi+=1;q=copy.deepcopy(q);q.wait|=ALL
    assert vars(r)==vars(q)and(x is None and y is None or x is not None and y is not None and vars(x)==vars(y)),'expert native source differs';checks+=1;seen[index]=None;continue
   originals=dict(IR.expand(source[index][1],source[index][2]));actual=IR.expand(r,x)
   assert [slot for slot,q in actual]==meta['source_slots']
   if r.unit=='ATT'and x and x.rsel:
    sx=source[index][2];require(maps,sx.rtab,sx.rtab+32*IR.PLAN_WORDS,x.rtab)
   for slot,q in actual:
    old=originals[slot];restored=copy.deepcopy(q);restored.wait=old.wait
    for k,d in restored.desc.items():
     if d.space=='VM':d.base=old.desc[k].base
    assert vars(restored)==vars(old),'static source arithmetic differs'
    seen[index].append(slot);wo=IR.written_operands(old)
    for k,d in old.desc.items():
     if d.space=='VM'and k not in wo:
      a,b=V.engine_span(old,k);u,v=V.engine_span(q,k);require(maps,a,b,u);checks+=1
    for k in wo:
     if k in old.desc and old.desc[k].space=='VM':
      a,b=V.engine_span(old,k);u,v=V.engine_span(q,k);maps=remove(remove(maps,a,b),u,v,True)+[(a,b,u)]
    if any(d.space=='STREAM'for k,d in q.desc.items()if k not in wo):
     assert ph['kind']=='stream_pair'and r.wait==source[index][1].wait,'streamed consumer source wait changed';stream_pairs+=1
  if expert:assert bi==len(epdec)
 # Every original record appears exactly once, or with all explicit row slots
 # in source order. Direct NOP/END controls outside workspace phases are exact.
 for index,(_,r,x,_)in enumerate(source):
  if r.unit=='CTL'and r.op in('NOP','END'):
   hits=[m for m in packet['records']if m['kind']=='body'and m['source_record']==index];assert len(hits)==1
   q,y,_=IR.decode_one(raw,hits[0]['offset']);assert q.wait==r.wait|ALL;q.wait=r.wait;assert vars(q)==vars(r)
  else:
   assert index in seen,'source record omitted'
   if seen[index] is not None:assert seen[index]==[slot for slot,q in IR.expand(r,x)],'source row lost/reordered/duplicated'
 return dict(address_checks=checks,expert_regions=expert_count,stream_rows=stream_pairs,source_records=len(source),native_commands=packet['native_commands'],transfer_bytes=packet['transfer_bytes'],max_vm_words=packet['max_vm_words'],numerical_arithmetic=False,backend_qualified=False,whole_programme_executable=False)

result=check();controls=[]
load=next(i for i,m in enumerate(packet['records'])if m['kind']=='load')
body=next(i for i,m in enumerate(packet['records'])if m['kind']=='body'and m['source_record']==3911)
for name,pos,mut in [('wrong_canonical_load',load,lambda r,x:setattr(r.desc['A'],'base',r.desc['A'].base+32)),('missing_load_drain',load,lambda r,x:setattr(r,'wait',0)),('stream_coupling_wait',body,lambda r,x:setattr(r,'wait',ALL))]:
 try:check((pos,mut))
 except(AssertionError,ValueError):controls.append(name)
 else:raise AssertionError(name+'escaped')
assert C.static_group_end(source,1540,1542,IR)<1542
controls.append('known_reverse_source_group_rejected')
result['controls']=controls;print(json.dumps(result))
