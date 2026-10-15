#!/usr/bin/env python3
"""Enumerate the actual MIX4/VM slot join and a proposed bank-striped storage ABI.

This is a geometry/calendar witness, not native RTL or mapped-SRAM qualification.
The current producer has HLAYOUT=1, H base256/K2048/W4096/V6144 (the full-shape
component fixture). The current VM chooses slot={lane group,row[1:0]} and has
one read per bank. Proposed bank stripes preserve every HC H row and change only
K/W/V storage; no production source consumes this proposed ABI yet.
"""
import collections, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv',
 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_rsched.sv',
 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static512_suhc.sv',
 'rtl/dsrom_sys/engram/mix/tb_s81_engram_mix4_c.sv']
def bank(row):return (row&31)^(((row>>5)&7)<<2)
def slot(i,row):return ((i>>2) if i<16 else 5)*4+(row&3)
def phys(addr,b):return (addr<<5)|(b^((addr&7)<<2))
def rows(beat,phase,striped):
 out=[];hhi=(bank(256+4*beat)>>2)
 for q in range(4):
  i=5*q;out.append((i,256+4*beat+q,'H'))
  if phase=='REDUCE':
   for k in range(1,5):
    lane=i+k
    row=phys(64+beat,(((hhi+1+(lane>>2))&7)<<2)|(lane&3)) if striped else (2048 if k<3 else 4096)+320*q+2*beat+((k-1)&1)
    out.append((lane,row,'K' if k<3 else 'W'))
  elif q==0:
   for k in (1,2):out.append((k,phys(256+beat,(((hhi+1)&7)<<2)|k) if striped else 6144+2*beat+k-1,'V'))
 return out
def inspect(striped):
 failures=[];maxslot=maxbank=0;storage={};aliases=[]
 for phase in ['REDUCE','ADD']:
  for t in range(160):
   rr=rows(t,phase,striped);ss=collections.defaultdict(list);bb=collections.defaultdict(list)
   for i,r,kind in rr:
    ss[slot(i,r)].append(i);bb[bank(r)].append(i)
    identity=(kind,t,i) if kind!='H' else ('H',t,i//5)
    if r in storage and storage[r]!=identity:aliases.append((r,storage[r],identity))
    storage[r]=identity
   sc={k:v for k,v in ss.items() if len(v)>1};bc={k:v for k,v in bb.items() if len(v)>1}
   maxslot=max(maxslot,max(map(len,ss.values())));maxbank=max(maxbank,max(map(len,bb.values())))
   if sc or bc:failures.append(dict(phase=phase,beat=t,slot_collisions=sc,bank_collisions=bc))
 return dict(native_join_compatible=not failures,max_simultaneous_requests_per_slot=maxslot,max_simultaneous_requests_per_bank=maxbank,
  failing_phase_beats=len(failures),first_failures=failures[:4],stored_rows=len(storage),storage_aliases=len(aliases),first_aliases=aliases[:4])
def main():
 current=inspect(False);candidate=inspect(True)
 assert not current['native_join_compatible']
 assert candidate['native_join_compatible'] and candidate['storage_aliases']==0
 return dict(schema='opentallas.s81.engram.vm-layout-witness.v1',source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
  shape=dict(copies=4,words_per_copy=5120,reduction_beats=160,add_beats=160),current=current,candidate=candidate,
  scope='Static full-shape address/slot/bank witness only; candidate storage ABI is not implemented or adopted. Existing ideal-VM arithmetic component benches do not qualify native MIX4+128SRAM integration.',
  remaining=['Versioned descriptor and producer/compiler staging map','RTL row address generation','Full128SRAM exact numerical and commit/return-slot proof plus actual DUT mutants','Current parent geometry and source-bound physical closure'])
if __name__=='__main__':print(json.dumps(main(),indent=1))
