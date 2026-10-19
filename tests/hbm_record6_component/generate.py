#!/usr/bin/env python3
"""Opt-in R6 component images; never changes production R-mode admission."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/hbm_static'),str(ROOT/'tools/hgi_sim')]
from su_arith_generate import FIELDS
from su_arith_compile import pack,physical_word
from hbm_layer_vehicle import layer_images as LI

def decode(w):
 d={}
 for n,b in reversed(FIELDS): d[n]=w&((1<<b)-1);w>>=b
 assert w==0
 return d

def canonical(x):
 # Explicit binary32 rounding after every operation, exactly 160 sequential
 # eight-word sums then a +0-padded 256-leaf pairwise tree.
 x=np.asarray(x,np.uint32).view(np.float32)
 y=np.multiply(x,x,dtype=np.float32)
 chunks=[]
 for i in range(0,1280,8):
  v=np.float32(0)
  for z in y[i:i+8]:v=np.add(v,z,dtype=np.float32)
  chunks.append(v)
 chunks+= [np.float32(0)]*96
 while len(chunks)>1: chunks=[np.add(chunks[i],chunks[i+1],dtype=np.float32) for i in range(0,len(chunks),2)]
 return int(np.float32(chunks[0]).view(np.uint32))


def addition_trace(out, ledger, original, second):
 ops=ledger['source_schedule']+[dict(o,source_start=o['start']+3,source_done=o['done']+3,station=40)for o in ledger['global_schedule']]
 assert len(ops)==1281
 ops.sort(key=lambda o:(o['station'],o['source_start']))
 digest=lambda x:hashlib.sha256(repr(x).encode()).hexdigest()
 producers={o['result']for o in ops}
 rows=[]
 for ep,data in enumerate((original,second)):
  sq=np.multiply(data.view(np.float32),data.view(np.float32),dtype=np.float32).view(np.uint32)
  values={digest(('square',i)):int(v)for i,v in enumerate(sq)}
  values.update({digest(('canonical_zero',('square',i))):int(sq[i])for i in range(0,1280,8)})
  zero=set(d for o in ops for d in o['operands'] if d not in values and d not in producers)
  assert len(zero)==2,zero
  values.update({d:0 for d in zero})
  pending=list(ops);actual={}
  while pending:
   ready=[o for o in pending if all(d in values for d in o['operands'])]
   assert ready,'cyclic/missing expression ownership'
   for o in ready:
    aa,bb=[values[d]for d in o['operands']]
    yy=int(np.add(np.uint32(aa).view(np.float32),np.uint32(bb).view(np.float32),dtype=np.float32).view(np.uint32))
    values[o['result']]=yy;actual[o['result']]=(aa<<64)|(bb<<32)|yy;pending.remove(o)
  rows.extend(actual[o['result']]for o in ops)
  assert values[ledger['global_schedule'][-1]['result']]==canonical(data)
 (out/'adds.mem').write_text(''.join(f'{r:024x}\n'for r in rows))
 (out/'adds.json').write_text(json.dumps(ops,indent=2)+'\n')

def generate(a):
 out=a.output;out.mkdir(parents=True,exist_ok=False)
 inv=json.loads(a.inventory.read_text());front=json.loads(a.front_words.read_text())
 z=np.load(a.operands);original=np.asarray(z['r0.k6.A'],np.uint32).reshape(-1)
 assert len(original)==1280
 assert hashlib.sha256(original.tobytes()).hexdigest()==inv['exact_fixture_entry']['inputs']['A']['sha256']
 assert canonical(original)==0x40a2a1ed
 second=(original.view(np.float32)*np.float32(.5)).astype(np.float32).view(np.uint32)
 assert np.all(second!=original)
 gold=[canonical(v)for v in (original,second)]
 assert gold[1]!=gold[0]
 ledger=[];payload=[]
 for q in range(4):
  ql=LI.QLine(); d0=decode(front[0][q]); backend=dict(cp_m1=2,cm_m1=2,cm_m2=0,cm_qm=0,ca_ad=0,ci_sfu=0,cs_sfu=0,cs_e1=0,ce_e2=0,co_rnd=0,co_dst=0,dst=0)
  # Backend controls remain installed for every edge through last OUT.
  for e in range(672):ql.f['control'][e]=pack(backend)
  for g in range(4):
   d=decode(front[g][q]);d.update(backend)
   # All absent B/C/D identities alias live A, including affine lane terms.
   aterms=d['ld_c']&((1<<240)-1)
   d['ld_c']=sum(aterms<<(240*s)for s in range(4))
   d['vb']=sum(physical_word(q,g)<<(24*s)for s in range(4))
   d['emit']=1;d['ld']=0
   ql.f['control'][32+112*g]=pack(d)
   if g==0:
    setup=dict(d);setup.update(ld=1,emit=0)
    ql.f['control'][16]=pack(setup)
   active=128 if q in(0,2)else 32
   logical=46336+g*320+(0,128,160,288)[q]
   for k in range(active//8):
    port=k%8;sec=(q<<13)|((g*2+k//8)<<3)|port
    ql.vmr(g*2+k//8,port,sec,k,g)
    words=[logical+k*8+j for j in range(8)]
    ledger.append(dict(q=q,g=g,k=k,port=port,sector=sec,logical=words,fill=g*2+k//8))
    payload.append((q,port,sec,words))
  if q==0:
   # Root predicted591, qcoreLOAD592,EXPORT602,scalar613,
   # RF pin646/commit647,class5 648,DRAIN650,native670.
   def red(op,tag=0):return (1<<73)|(op<<70)|(tag<<8)
   ql.f['red'][592]=red(0)
   ql.f['red'][602]=red(4,0x100)
   ql.f['rf'][648]=(1<<8)<<(5*9)
   ql.vmw(650,0,1,0,0,4096,1)
  lines=ql.lines(); assert len(lines)==672
  LI.column_image(lines,out/f'q{q}')
  manifest=json.loads((out/f'q{q}/cols/manifest.json').read_text()) if (out/f'q{q}/cols/manifest.json').exists() else {}
  # The real packed rows are checked independently, including bank identities.
  rows={}
  for w in (out/f'q{q}/cols/config.mem').read_text().split():
   bank=int(w[:4],16);row=int(w[4:6],16)
   assert row<128,(bank,row)
   assert row not in rows.setdefault(bank,[]),(bank,row)
   rows[bank].append(row)
  (out/f'q{q}/occupancy.json').write_text(json.dumps({str(k):len(v)for k,v in rows.items()},indent=2)+'\n')
 for ep,data in enumerate((original,second)):
  (out/f'square{ep}.mem').write_text(''.join(f'{int(v):08x}\n'for v in np.multiply(data.view(np.float32),data.view(np.float32),dtype=np.float32).view(np.uint32)))
  (out/f'input{ep}.mem').write_text(''.join(f'{int(v):08x}\n'for v in data))
  packs=[]
  for q,p,sec,words in payload:
   value=sum(int(data[w-46336])<<(32*j)for j,w in enumerate(words))
   packs.append(dict(q=q,bank=p,sector=sec,value=f'{value:064x}'))
  (out/f'preload{ep}.json').write_text(json.dumps(packs,indent=2)+'\n')
 (out/'gold.mem').write_text(''.join(f'{v:08x}\n'for v in gold))
 assert len(ledger)==160 and len(set((r['q'],r['port'])for r in ledger))==24
 assert sorted(w for r in ledger for w in r['logical'])==list(range(46336,47616))
 receipt=dict(scope='SOURCE ONLY until real fleet RTL receipts',source_pgslice_sha256='32e68bbd89af6e890132e022800d3ac096371a040caa94b1253602d51200d567',episodes=2,gold=[f'{v:08x}'for v in gold],fills=ledger,native_banks=24,command_edges=672,root_prediction=591,native_done_prediction=670,producer='fixture-owned original1280words; second exactpower2 scaled input',physical_hold=['RFcoherentstorage','native timing','reach','reset/fanout','parent H'])
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 # The bench generator only consumes these actual source-derived images.
 (out/'station_ledger.json').write_text(a.station_ledger.read_text())
 addition_trace(out,json.loads(a.station_ledger.read_text()),original,second)
 from tb_generate import emit
 emit(out,receipt,json.loads(a.source_binding.read_text()))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--station-ledger',type=Path,required=True);p.add_argument('--source-binding',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--front-words',type=Path,required=True);p.add_argument('--operands',type=Path,required=True);p.add_argument('output',type=Path);generate(p.parse_args())
