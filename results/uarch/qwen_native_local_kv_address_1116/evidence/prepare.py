from pathlib import Path
import json,sys
P=Path(__file__).resolve().parent;sys.path.insert(0,'/tmp/qc-fp8-inverse');from fp8_inverse import fp8_to_fp32_bits
G=json.load(open('/tmp/qc-fp8-inverse/golden256.json'));bytes_=G['bytes_seat_order'];cases=[]
for pos in [15,16,8191]:cases.append(dict(name=f'local_pos{pos}',mode=1,pos=pos,expect='PASS'))
cases += [dict(name='legacy_local_pos15',mode=0,pos=15,expect='FAULT'),dict(name='epoch8192',mode=1,pos=8192,expect='FAULT'),dict(name='dim128',mode=1,pos=16,expect='FAULT',mut='dim'),dict(name='codecNaN',mode=1,pos=16,expect='FAULT',mut='codec'),dict(name='wrongkind',mode=1,pos=16,expect='FAULT',mut='kind'),dict(name='wrongdata',mode=1,pos=16,expect='TYPED_DATA_FAIL',mut='data'),dict(name='held_epoch_pos',mode=1,pos=16,expect='PASS',mut='livepos'),dict(name='overlap_epoch',mode=1,pos=16,expect='FAULT',mut='overlap')]
for case in cases:
 d=P/case['name'];d.mkdir(exist_ok=True);rows=[]
 # direct formatter face: {word_index2,word_slot1,nin18,issue_kind2,issue_v1,epoch_begin1,epoch_pos18,wa1536,wd2048,we64}
 for c in range(110):
  we=wa=wd=0
  for h in range(8):
   for dim in range(h,128,8):
    # Actualcollectorpartialmask geometry: earlyheads precedelateheads2cycles. K0/1 andVproducerwindowsindependent.
    stage=0 if dim<64 else 1;cycle=20+(dim//8)+(2 if h>=4 else 0)
    if c==cycle:
     k=dim
     if case.get('mut')=='dim' and dim==0:k=128
     if case.get('mut')=='kind' and dim==0:k|=1<<20
     val=fp8_to_fp32_bits(bytes_[dim]);
     if case.get('mut')=='codec' and dim==0:val=0x7fc00000
     if case.get('mut')=='data' and dim==0:val=fp8_to_fp32_bits(1)
     we|=1<<h;wa|=k<<(24*h);wd|=val<<(32*h)
    if c==60+(dim//8)+(2 if h>=4 else 0):
     k=(1<<20)|dim;val=fp8_to_fp32_bits(bytes_[128+dim]);we|=1<<h;wa|=k<<(24*h);wd|=val<<(32*h)
  eb=int(c==0 or case.get('mut')=='overlap' and c==15);ep=case['pos'] if not(case.get('mut')=='livepos' and c>=10) else 8191
  iv=int(c in [3,4,5]);ik={3:0,4:1,5:2}.get(c,0);nin=128 if ik==0 else 64;slot=int(c in [45,50,90,95]);ix={45:0,50:1,90:2,95:3}.get(c,0)
  vals=[(we,64),(wd,2048),(wa,1536),(ep,18),(eb,1),(iv,1),(ik,2),(nin,18),(slot,1),(ix,2)];v=off=0
  for val,w in vals:assert 0<=val<1<<w;v|=val<<off;off+=w
  assert off==3691;rows.append(f'{v:0923x}')
 (d/'stim.hex').write_text('\n'.join(rows)+'\n')
(P/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');(P/'golden256.json').write_text(json.dumps(G,indent=2)+'\n')
