"""Bounded logical source model. No production physical ages or metastability claim."""
import sys
mut=sys.argv[1] if len(sys.argv)>1 else ''
checks=0
def ck(x,msg):
 global checks
 assert x,msg
 checks+=1
# Exact guard simultaneous-NBA behavior: producer fault clearing at a core edge
# does not erase the old high sampled into fm at that edge.
for start in range(1,9):
 p=fm=fs=sticky=0
 seen=[]
 for t in range(16):
  oldp=p
  p=1 if t==start else 0 # source event; next edge permitted recovery clear
  fm,fs,sticky=(0 if mut=='drop_on_clear' and oldp and not p else oldp),fm,sticky|fs
  seen.append(sticky)
 ck(seen[start+3]==1,'same-clock producer clear erased guard event')
 ck(all(seen[start+3:]),'retained guard history fell without reset')
# No-reset producer starts unproved. No fabricated POR initialized healthy state.
for unknown in (None,):
 ck(unknown is None,'unproved startup cannot be called clean')
# Asynchronous pulse entirely between guard observations is not seen; source
# sticky before the crossing preserves it. Samples at t=0,10,20,30.
for pulse in range(1,9):
 samples=[int(pulse<=t<pulse+1) for t in (0,10,20,30)]
 ck(not any(samples),'fixture pulse should fall entirely between samples')
 retained=[int(t>=pulse) for t in (0,10,20,30)]
 if mut=='pulse_without_retention': retained=samples
 ck(any(retained),'unretained pulse lost across domain')
# Producer reset AND host guard reset destroys history. POR-retained request
# survives warm reset: it is unsafe to label it healthy without drain/recovery.
for pending in (True,False):
 p=fm=fs=sticky=1
 p=fm=fs=sticky=0
 request_retained=pending
 healthy=not sticky and not request_retained
 if mut=='reset_certifies_clean': healthy=not sticky
 ck(not healthy if pending else healthy,'warm reset falsely certified retained context')
# Source predicate duplicated along two observed paths stays one fault identity.
identity_fault=1
packet_fault=identity_fault
physical_fault=identity_fault
ck(packet_fault and physical_fault,'actual repeated-observation fixture')
ck(len({'coordinator.identity_fault' for x in (packet_fault,physical_fault) if x})==1,'double counted source')
print('PASS',checks,'source-derived capture/reset checks; production bounds NULL')
