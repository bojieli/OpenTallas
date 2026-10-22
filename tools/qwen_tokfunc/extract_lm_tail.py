#!/usr/bin/env python3
"""Extract the preserved real KC8/J3 tail, exact scales and independent FP32 golden.

Pure fixture arithmetic/extraction; no RTL simulation or full-token qualification.
The event dates retain the old monolith calendar; safe-station CFG legality must
be separately bound and priced by its owner.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--events',type=Path,required=True)
p.add_argument('--golden-source',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
spec=importlib.util.spec_from_file_location('tail_golden',a.golden_source)
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
ev={}
for line in gzip.open(a.events,'rt'):
 e,port,h=line.split();key=(int(e),int(port));ev[key]=ev.get(key,0)|int(h,16)
cmd=[]
for (e,port),v in sorted(ev.items()):
 if port==0 and v&1 and (v>>1)&7==2 and (v>>7)&255==3:
  cmd.append(dict(edge=e,slice=(v>>112)&15,mode=(v>>4)&3,nwords=3,
                  kc=((v>>59)&255)+1,sbase=(v>>15)&511,dbase=(v>>26)&((1<<24)-1),word=f'{v:029x}'))
assert [(x['slice'],x['mode'],x['kc']) for x in cmd]==[(9,3,8),(8,2,8)]
streams={};selected={};cluster=[None]*8
for s in (8,9):
 for pn in (0,1):
  port=2+2*s+pn
  for half in (0,1):
   rows=[(e,(v>>(514*half))&((1<<514)-1)) for (e,pt),v in sorted(ev.items())
         if pt==port and (v>>(512+514*half))&1][-24:]
   assert len(rows)==24 and all(rows[3*k+j][0]==rows[0][0]+8*k+j for k in range(8) for j in range(3))
   streams[f's{s}_rs{"s" if pn==0 else "n"}_{"hi" if half else "lo"}']=[e for e,v in rows]
   for e,v in rows:selected[(e,port)]=selected.get((e,port),0)|(v<<(514*half))
   ci=(0 if s==8 else 4)+({(0,1):0,(0,0):1,(1,0):2,(1,1):3}[(pn,half)])
   cluster[ci]=np.array([(v>>(32*l))&0xffffffff for e,v in rows[-3:] for l in range(16)],dtype=np.uint32)
tables={};packets=[]
for (e,port),v in sorted(ev.items()):
 if port==41 and (v>>1087)&1 and (v>>1084)&7==2 and (v>>1080)&15==8:
  addr=(v>>1052)&((1<<24)-1);pay=v&((1<<1024)-1)
  packets.append(dict(edge=e,address=addr,payload=f'{pay:0256x}',stream_word=f'{v:0272x}'))
  for j in range(4):tables[addr+j]=(pay>>(256*j))&((1<<256)-1)
scales=np.array([((tables[264+j]>>(16*l))&65535)<<16 for j in range(3) for l in range(16)],dtype=np.uint32)
cv=[G.from_bits(x) for x in cluster]
recv=G.add(G.add(cv[0],cv[1]),G.add(cv[3],cv[2]))
send=G.add(G.add(cv[4],cv[5]),G.add(cv[7],cv[6]))
from_trace=G.mul(G.add(recv,send),G.from_bits(scales))
# Recreate the exact benchmark RNG stream without retaining the full 311MB W.
rng=np.random.default_rng(1)
for first in range(0,18944,128):rng.integers(-127,128,size=(min(128,18944-first),4096))
w=rng.integers(-127,128,size=(48,4096)).astype(np.float32)
x=(rng.standard_normal(4096)*2.0).astype(np.float32)
sc=G.to_bf16((rng.random(18992)*.02+.001).astype(np.float32))[18944:]
assert np.array_equal(G.bits(sc),scales), 'recreated scale RNG stream differs from real BTAB'
independent=G.mul(G.matvec(w,x,512),sc)
assert np.array_equal(G.bits(independent),G.bits(from_trace)), 'real final-prefix tree differs from independent seed1 golden'
def words(v):
 bits=G.bits(v)
 return [f'{sum(int(bits[16*j+l])<<(32*l) for l in range(16)):0128x}' for j in range(3)]
result=dict(schema='opentallas.qwen.lm_tail_cut.v1',scope='one real two-station KC8/J3 tail; no upstream MAC or global26check/full-token claim',
 extractor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 events_sha256=hashlib.sha256(a.events.read_bytes()).hexdigest(),golden_source_sha256=hashlib.sha256(a.golden_source.read_bytes()).hexdigest(),
 seed=1,rows=[18944,18992],commands=cmd,stream_edges=streams,
 pair_pin_events=[dict(edge=e,port=pt,word=f'{v:0257x}') for (e,pt),v in sorted(selected.items())],
 receiver_btab_stream_packets=packets,receiver_scale_words=[f'{tables[264+j]:064x}' for j in range(3)],
 expected_sender_nb_data=words(send),expected_receiver_scaled_data=words(independent),
 expected_receiver_idx=[0,1,2],expected_receiver_last=[0,0,1],independent_seed_golden_matches_trace_tree=True,
 timing_limit='Original cfg entries3280/3282 arrive after firstnear3290; protected safe station needs explicit quiet earlier CFG. Input values/old dates preserved; source owner must record/legalize CFG timing without claiming original/full programme ages.')
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps(dict(rows=result['rows'],receiver_words=result['expected_receiver_scaled_data'],golden_match=True)))
