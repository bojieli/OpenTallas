from pathlib import Path
import json
P=Path(__file__).parent/'packet';meta=json.loads((P/'packets.json').read_text());HRMASK=(1<<453)-1
for sid,delay in [(0,576),(11,2)]:
 key=f'o_s{sid}';m=meta[key];old=[int(x,16) for x in (P/(key+'.hex')).read_text().split()]
 ib=(old[m['go']]>>73)&((1<<379)-1);descriptor=(old[m['arm']]>>1)&((1<<72)-1)
 g0=m['go'];bshift=g0+60-m['arm'];g1=g0+delay+320;N=g1+delay+400
 raw={};gold={}
 for c,v in enumerate(old):
  if v and c!=m['go']:
   raw[c]=v
   b=c+bshift;v2=v
   if v&(1<<453):v2=(v&((1<<478)-1))|sum(0x4080<<(478+16*k) for k in range(64))
   raw[b]=raw.get(b,0)|v2
 raw[g0]=raw.get(g0,0)|(1<<452)|(ib<<73)|1
 # Different ROM base proves completeIB lifetime while read descriptor is identical.
 ib2=ib^(1<<300)
 raw[g1]=raw.get(g1,0)|(1<<452)|(ib2<<73)|1
 for c in range(N):
  # Retain an invalid stale XPF+unrelatedIB at idle to exercise outervalid gating.
  if c not in raw:raw[c]=(descriptor<<1)|(((0x1234567+c*7)&((1<<379)-1))<<73)
  v=raw[c];h=v&HRMASK
  if h&(1<<452):h&=~(1<<452)
  gold[c]=(v&~HRMASK)|h
 for g,ibx in [(g0,ib),(g1,ib2)]:
  e=g+delay;h=gold[e]&HRMASK
  if not h&1:h&=~(1<<1)
  h=(h&~(((1<<379)-1)<<73))|(ibx<<73)|(1<<452)|1
  gold[e]=(gold[e]&~HRMASK)|h
 for n,d in [('raw',raw),('gold',gold)]:
  (P/f'epoch_{sid}_{n}.hex').write_text('\n'.join(f'{d[c]:0376x}' for c in range(N))+'\n')
 (P/f'epoch_{sid}.json').write_text(json.dumps(dict(sid=sid,delay=delay,g0=g0,g1=g1,emit0=g0+delay,emit1=g1+delay,ncy=N,first_vector_bf16='4000',second_vector_bf16='4080',IB=[f'{ib:095x}',f'{ib2:095x}']),indent=2)+'\n')
