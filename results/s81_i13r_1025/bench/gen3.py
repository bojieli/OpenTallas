# S81-I13 restructured TX helper bench vectors (single job): the R3 five cases + skip/two-source positives
# + wrong-qslot / candidate-order / id-order / mutant-target negatives.  usage: gen3.py <repo> <outdir>
from pathlib import Path
import random,sys,json
sys.path.insert(0,sys.argv[1]+'/tools/s81_dv/layer_prog')
import lower_bk as B
O=Path(sys.argv[2]);O.mkdir(parents=True,exist_ok=True)
N=2300
r=random.Random(1025)
ids=sorted(r.sample(range(2048),512));keys={p:0x3f80+p%64 for p in ids}
# skip: 1024 candidates (256 per rank), 512 of them selected -> the merge walk retires unselected rows
cand=sorted(r.sample(range(2048),1024));ck={p:0x2a00+(p*7)%251 for p in cand}
sel=sorted(r.sample(cand,512))
def rank_lists(pos,kk,tag,qmap=lambda q:q):
 out=[]
 for rank in range(4):
  pp=[p for p in pos if p>>9==rank]
  out.append(B.lane_words_indexed13([kk[p] for p in pp],pp,0,512,qmap(rank),tag))
 return out
def interleave(a,b):
 out=[];i=j=0
 while i<len(a) or j<len(b):
  if i<len(a):out.append(a[i]);i+=1
  if j<len(b):out.append(b[j]);j+=1
 return out
cases={}
for case in ['dense','cam','miss','duplicate','wrongtag','skip','twosrc','wrongq','order','idorder']:
 vi=[0]*N;vo=[0]*N
 P,K=(cand,ck) if case=='skip' else (ids,keys)
 S=sel if case=='skip' else ids
 if case=='dense':
  beats=[b for w in B.lane_words_sparse([keys[p] for p in ids],ids,0,512,0,0x33) for b in B.bk_beats(2,w)]
 elif case=='twosrc':
  L=rank_lists(P,K,0x33)
  b2=[b for w in L[0]+L[1] for b in B.bk_beats(2,w)];b3=[b for w in L[2]+L[3] for b in B.bk_beats(3,w)]
  beats=interleave(b2,b3)   # two sources, beat-interleaved: per-lane staging + per-lane HDR qslot
 else:
  use=ids[:-1] if case=='miss' else P
  L=rank_lists(use,K,0x34 if case=='wrongtag' else 0x33,(lambda q:2 if q==1 else q) if case=='wrongq' else (lambda q:q))
  if case=='order':L[0][1],L[0][2]=L[0][2],L[0][1]   # rank0 type8 words 0 and 1 swapped: descending inside qslot0
  ws=[w for l in L for w in l]
  if case=='duplicate':ws+=B.lane_words_indexed13([keys[ids[0]]],[ids[0]],0,512,0,0x33)
  beats=[b for w in ws for b in B.bk_beats(2,w)]
 t=50
 for b in beats:vi[t]=b;t+=1
 assert t<780,t
 vo[800]=B.ctl_beat(B.tx_payload(2,0x44,512,0,0x33,0,1,640,dst=1,loop=True,indexed13=True,qshift=9,candidate_lookup=case!='dense'))
 tt=824
 idw=[]
 for rank in range(4):
  pp=[p for p in S if p>>9==rank]
  for off in range(0,len(pp),16):
   part=pp[off:off+16];idw.append(B.idx_word(part+[0]*(16-len(part)),(1<<len(part))-1,0,rank,off+16>=len(pp),0x33))
 if case=='idorder':idw[3],idw[4]=idw[4],idw[3]
 for w in idw:
  for b in B.egress_beats(w):vo[tt]=b;tt+=1
 for b in B.egress_beats(B.done_word(512,0x33)):vo[tt]=b;tt+=1
 expected=[]
 for rank in range(4):
  pp=[p for p in S if p>>9==rank]
  expected+=B.lane_words_indexed13([K[p] for p in pp],pp,0,512,rank,0x44)
 eb=[b for w in expected for b in B.bk_beats(2,w)]
 (O/(case+'_vi.hex')).write_text('\n'.join(f'{x:069x}' for x in vi)+'\n')
 (O/(case+'_vo.hex')).write_text('\n'.join(f'{x:069x}' for x in vo)+'\n')
 cases[case]=dict(expected_beats=[f'{x:x}' for x in eb],input_done=tt,input_last=t,k=512,candidates=len(P),
                  expected_fault=case not in ['dense','cam','skip','twosrc'])
(O/'cases.json').write_text(json.dumps(cases,indent=1)+'\n')
print({k:(len(v['expected_beats']),v['expected_fault']) for k,v in cases.items()})
