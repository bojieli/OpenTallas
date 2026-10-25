from pathlib import Path
import random,sys,json
sys.path.insert(0,sys.argv[1]+'/tools/s81_dv/layer_prog')
import lower_bk as B
O=Path(__file__).parent
r=random.Random(1025)
ids=sorted(r.sample(range(2048),512));keys={p:0x3f80+p%64 for p in ids}
N=2300
cases={}
for case in ['dense','cam','miss','duplicate','wrongtag']:
 vi=[0]*N;vo=[0]*N
 if case=='dense':
  ws=B.lane_words_sparse([keys[p] for p in ids],ids,0,512,0,0x33)
 else:
  use=ids[:-1] if case=='miss' else ids
  ws=[]
  for rank in range(4):
   pp=[p for p in use if p>>9==rank]
   ww=B.lane_words_indexed13([keys[p] for p in pp],pp,0,512,rank,0x34 if case=='wrongtag' else 0x33)
   ws+=ww
  if case=='duplicate':ws+=B.lane_words_indexed13([keys[ids[0]]],[ids[0]],0,512,0,0x33)
 t=50
 for w in ws:
  for b in B.bk_beats(2,w):vi[t]=b;t+=1
 assert t<780,t
 vo[800]=B.ctl_beat(B.tx_payload(2,0x44,512,0,0x33,0,1,640,dst=1,loop=True,indexed13=True,qshift=9,candidate_lookup=case!='dense'))
 tt=824
 for rank in range(4):
  pp=[p for p in ids if p>>9==rank]
  for off in range(0,len(pp),16):
   part=pp[off:off+16];ww=B.idx_word(part+[0]*(16-len(part)),(1<<len(part))-1,0,rank,off+16>=len(pp),0x33)
   for b in B.egress_beats(ww):vo[tt]=b;tt+=1
 for b in B.egress_beats(B.done_word(512,0x33)):vo[tt]=b;tt+=1
 expected=[]
 for rank in range(4):
  pp=[p for p in ids if p>>9==rank]
  expected+=B.lane_words_indexed13([keys[p] for p in pp],pp,0,512,rank,0x44)
 eb=[b for w in expected for b in B.bk_beats(2,w)]
 (O/(case+'_vi.hex')).write_text('\n'.join(f'{x:069x}' for x in vi)+'\n')
 (O/(case+'_vo.hex')).write_text('\n'.join(f'{x:069x}' for x in vo)+'\n')
 cases[case]=dict(expected_beats=[f'{x:x}' for x in eb],input_done=tt,input_last=t,k=512,packet_words=len(ws),expected_fault=case not in ['dense','cam'])
(O/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
