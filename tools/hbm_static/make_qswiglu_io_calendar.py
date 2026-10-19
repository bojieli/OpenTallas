#!/usr/bin/env python3
"""Actual fixed native-memory schedule for the canonical 3072-word GLU join.

The explicit diagnostic VM allocation remains separate from native die-layout
qualification. Payloads are actual data addresses/slots, no fixture result data.
"""
from pathlib import Path
import sys,json
from os import environ
F=[('prefetch_v',8),('prefetch_scalar',8),('prefetch_sector',128),('prefetch_group',16),
   ('prefetch_local_addr',120),('prefetch_word',24),('scalar_addr',96),('scalar_enable',4),
   ('drain_v',2),('drain_addr',30),('drain_vm_sector',32),('drain_round_bf16',2),('arith_start',1)]
assert sum(w for _,w in F)==471
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
overlap=environ.get("SFU_IO_OVERLAP", "0")=="1"
length,scalar_edge,arith_edge,drain_edge=(432,0,20,210) if overlap else (800,192,210,587)
# Split SFU (core + bank-pair LG leaves, H-SU 10-15): every VM read returns 2*LG_PATH edges later at the core
# (LG_PATH = 1 leaf edge + R die relays), so arithmetic start, drain and the programme length move by that constant.
lg_path=int(environ.get("SFU_LG_PATH","0"))
shift=2*lg_path
length,arith_edge,drain_edge=length+shift,arith_edge+shift,drain_edge+shift
rows=[]
for t in range(length):
 d=dict(scalar_addr=12672<<24,scalar_enable=2)
 if t<192:
  d.update(prefetch_v=0,prefetch_sector=0,prefetch_group=0,prefetch_local_addr=0)
  for part in range(2):
   for base,group in ((0,0),(1026,2)):
    sector=base+t*2+part;b=sector%8
    d['prefetch_v']|=1<<b
    d['prefetch_sector']|=sector<<(16*b)
    d['prefetch_group']|=group<<(2*b)
    d['prefetch_local_addr']|=(t*16+part*8)<<(15*b)
 if t==scalar_edge:
  d['prefetch_v']=d.get('prefetch_v',0)|16
  d['prefetch_scalar']=16
  d['prefetch_sector']=d.get('prefetch_sector',0)|(2052<<64)
  d['prefetch_group']=d.get('prefetch_group',0)|(1<<8)
 if t==arith_edge:d['arith_start']=1
 if drain_edge<=t<drain_edge+192:
  beat=t-drain_edge
  d.update(drain_v=3,drain_addr=(beat*16)|((beat*16+8)<<15),drain_vm_sector=(4096+beat*2)|((4096+beat*2+1)<<16))
 word=0;offset=0
 for name,w in F:
  value=d.get(name,0)
  if not 0<=value<1<<w:raise ValueError((t,name,value))
  word|=value<<offset;offset+=w
 rows.append(word)
(out/'io.hex').write_text(''.join(f'{word:0118x}\n' for word in rows))
# SFU programme store r10, decision B (SFU-PS-3 10-17, coordinator sign-off for the compiler owner): the r10 head
# REGISTERS the programme start (io_word[470] -> +1 edge -> programme calendar), so the compile schedule places
# arith_start ARITH_START_ADVANCE_R10=1 IO row EARLIER for that store; compiler_control then reaches the core on the
# same edge as with r7c. Every other IO field is unchanged (the core ignores bit 470). io.hex stays the reference image.
# SFU-PS-4 relays (10-17): + one per-row launch relay in front of the programme leaves -> the programme start is 2 edges
# after IO2 bit 26, so the advance is 2 (io_word and status each +1 by the output relay / status pre-combine: D=5, status 3).
ARITH_START_ADVANCE_R10=2
assert arith_edge-ARITH_START_ADVANCE_R10>=0
bit=470
rows_r10=[(w&~(1<<bit)) for w in rows]
rows_r10[arith_edge-ARITH_START_ADVANCE_R10]|=1<<bit
(out/'io_store_r10.hex').write_text(''.join(f'{word:0118x}\n' for word in rows_r10))
(out/'io_manifest.json').write_text(json.dumps(dict(width=471,rows=length,prefetch_edges=192,scalar_prefetch_edge=scalar_edge,
 arith_start_edge=arith_edge,drain_edges=[drain_edge,drain_edge+192],overlap=overlap,real_programme_SRAMs=6,VM_map='diagnostic SID0 G0/U1026/route2052/O4096',
 arith_start_edge_store_r10=arith_edge-ARITH_START_ADVANCE_R10,arith_start_advance_store_r10=ARITH_START_ADVANCE_R10,
 full_4x7168_IO_schedule=False,lg_path=lg_path,latency_shift_edges=shift,native_die_qualified=False),indent=2)+'\n')
