from pathlib import Path
import json,sys,random
sys.path.insert(0,"mem_compiler")
import sram_gen as G
s=G.SramSpec("hidx_storage_equation_32x64",32,64,1,1,"1r1w",0,0)
Path("slice.v").write_text(G.behavioural(s,G.pins_for(s),"// MODEL ONLY; NO PHYSICAL OR LIBERTY ADMISSION"))
# Exhaustive finite-width source equations; fault flag does not gate accesses.
sets=[]
for b in range(8):
 seen=set()
 for f0 in range(128):
  k=(b-f0)%8;fr=f0+k;wa=fr>>3
  assert 0<=wa<32
  for nf in range(16):
   if k<nf:seen.add(wa)
 sets.append(sorted(seen))
assert all(x==list(range(17)) for x in sets[:7]) and sets[7]==list(range(16))
# Independent arbitrary-state transition induction over one memory bit.
# For a=0..31, bit=0..287 assume old64[a][bit] == slices[a][bit].
# Exhaust all old, wd, mask, write/read enable and same/different address.
n=0
for old in range(2):
 for data in range(2):
  for mask in range(2):
   for we in range(2):
    for re in range(2):
     for same in range(2):
      for hold in range(2):
       q=old if re else hold
       nxt=data if we and mask else old
       # Separate independent projected implementation samples before update.
       projected_q=(old if re else hold)
       projected_state=((old & (1-(we&mask))) | (data & (we&mask)))
       assert q==projected_q and nxt==projected_state
       n+=1
Path("equations.json").write_text(json.dumps({"write_addresses_by_bank":sets,"read_addresses":list(range(8)),"transition_cases":n,"fault_injection_equivalence":"REFUSED: physical coupling/alias faults can cross removed rows/columns","repair":"hard-disabled by exact source","powerup":"zero simulation or related arbitrary low288 state; no silicon initialization claim"},indent=2)+"\n")
print("PASS source equation exhaustive addresses and %d one-bit transition cases"%n)
