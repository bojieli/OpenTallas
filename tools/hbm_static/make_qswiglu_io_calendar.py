#!/usr/bin/env python3
"""Actual fixed native-memory schedule for the canonical 3072-word GLU join.

The explicit diagnostic VM allocation remains separate from native die-layout
qualification. Payloads are actual data addresses/slots, no fixture result data.
"""
from pathlib import Path
import sys,json
F=[('prefetch_v',8),('prefetch_scalar',8),('prefetch_sector',128),('prefetch_group',16),
   ('prefetch_local_addr',120),('prefetch_word',24),('scalar_addr',96),('scalar_enable',4),
   ('drain_v',2),('drain_addr',30),('drain_vm_sector',32),('drain_round_bf16',2),('arith_start',1)]
assert sum(w for _,w in F)==471
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rows=[]
for t in range(800):
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
 if t==192:d.update(prefetch_v=16,prefetch_scalar=16,prefetch_sector=2052<<64,prefetch_group=1<<8)
 if t==210:d['arith_start']=1
 if 587<=t<779:
  beat=t-587
  d.update(drain_v=3,drain_addr=(beat*16)|((beat*16+8)<<15),drain_vm_sector=(4096+beat*2)|((4096+beat*2+1)<<16))
 word=0;offset=0
 for name,w in F:
  value=d.get(name,0)
  if not 0<=value<1<<w:raise ValueError((t,name,value))
  word|=value<<offset;offset+=w
 rows.append(word)
(out/'io.hex').write_text(''.join(f'{word:0118x}\n' for word in rows))
(out/'io_manifest.json').write_text(json.dumps(dict(width=471,rows=800,prefetch_edges=192,scalar_prefetch_edge=192,
 arith_start_edge=210,drain_edges=[587,779],real_programme_SRAMs=6,VM_map='diagnostic SID0 G0/U1026/route2052/O4096',
 full_4x7168_IO_schedule=False,native_die_qualified=False),indent=2)+'\n')
