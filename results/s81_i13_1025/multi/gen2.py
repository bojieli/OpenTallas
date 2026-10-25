# S81-PORTS: I13 two-job tag-bank overlap bench (job B input arrives while job A transmits)
from pathlib import Path
import random,sys,json
sys.path.insert(0,sys.argv[1]+'/tools/s81_dv/layer_prog')
import lower_bk as B
O=Path(__file__).parent; N=3400
def job_words(ids,keys,tag):
 ws=[]
 for rank in range(4):
  pp=[p for p in ids if p>>9==rank]
  ws+=B.lane_words_indexed13([keys[p] for p in pp],pp,0,512,rank,tag)
 return ws
def egress(ids,tag):
 out=[]
 for rank in range(4):
  pp=[p for p in ids if p>>9==rank]
  for off in range(0,len(pp),16):
   part=pp[off:off+16];out+=B.egress_beats(B.idx_word(part+[0]*(16-len(part)),(1<<len(part))-1,0,rank,off+16>=len(pp),tag))
 return out+B.egress_beats(B.done_word(512,tag))
def expect(ids,keys,otag):
 e=[]
 for rank in range(4):
  pp=[p for p in ids if p>>9==rank]
  e+=B.lane_words_indexed13([keys[p] for p in pp],pp,0,512,rank,otag)
 return [b for w in e for b in B.bk_beats(2,w)]
r=random.Random(2510)
A=sorted(r.sample(range(2048),512));KA={p:0x3f80+p%64 for p in A}
Bi=sorted(r.sample(range(2048),512));KB={p:0x2a00+(p*7)%251 for p in Bi}
cases={}
for case,tb_ in (("multi",0x34),("samebank",0x35)):
 vi=[0]*N;vo=[0]*N
 t=50
 for w in job_words(A,KA,0x33):
  for b in B.bk_beats(2,w):vi[t]=b;t+=1
 assert t<780,t
 vo[800]=B.ctl_beat(B.tx_payload(2,0x44,512,0,0x33,0,1,640,dst=1,loop=True,indexed13=True,qshift=9,candidate_lookup=True))
 tt=824
 for b in egress(A,0x33):vo[tt]=b;tt+=1
 t=900   # job B exchange lands while job A is transmitting (A output 856..1422 in r3)
 for w in job_words(Bi,KB,tb_):
  for b in B.bk_beats(2,w):vi[t]=b;t+=1
 assert t<1600,t
 c2=1700
 vo[c2]=B.ctl_beat(B.tx_payload(2,0x45,512,0,tb_,0,1,640,dst=1,loop=True,indexed13=True,qshift=9,candidate_lookup=True))
 tt=c2+24
 for b in egress(Bi,tb_):vo[tt]=b;tt+=1
 assert tt<N-700,tt
 eb=expect(A,KA,0x44)+expect(Bi,KB,0x45)
 (O/(case+'_vi.hex')).write_text('\n'.join(f'{x:069x}' for x in vi)+'\n')
 (O/(case+'_vo.hex')).write_text('\n'.join(f'{x:069x}' for x in vo)+'\n')
 cases[case]=dict(expected_beats=[f'{x:x}' for x in eb],expected_fault=(case=="samebank"),jobs=2)
(O/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
print({k:len(v["expected_beats"]) for k,v in cases.items()})
