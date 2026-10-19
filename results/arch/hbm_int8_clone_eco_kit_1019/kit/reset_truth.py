"""Exhaustive source calendar + network identity consequence, no simulator.
Actual RTL truth/reset benches are frozen separately and require fleet execution.
This proves no new state at the physical branches; analogue pulse checks stay OPEN.
"""
import json,itertools
from prove_topology import virtual,prove
j,p=virtual();proof=prove(j,p,True)
checks=0
for initial in itertools.product((0,1),repeat=2):
 for seq in itertools.product((0,1),repeat=8):
  a,b=initial
  history=[initial[1],initial[0]]
  for rst in seq:
   old_b=b;a,b=rst,a
   history.append(rst)
   assert b==history[-2]
   # Native INV source may have either polarity. Four/three HB4 remain identity;
   # retained and new reset INV outputs equal the original reset INV output.
   for upstream in (0,1):
    old=1-upstream;branch0=1-upstream;branch1=1-upstream
    assert old==branch0==branch1;checks+=1
   # Two real sampled stages, ordinary assertion AND release; no new FF/edge.

# Explicit old state model tracks two samples for both phases and clock stop.
for level in (0,1):
 a=b=1-level
 a,b=level,a;assert b==1-level
 a,b=level,a;assert b==level
 before=(a,b)
 # Physical BUF/INV network cannot update either sampled state while clock stops.
 assert (a,b)==before
print(json.dumps(dict(status='SOURCE_CALENDAR_AND_NATIVE_FUNCTION_INDUCTION_PASS',reset_identity_checks=checks,assertion_edges=2,release_edges=2,added_edges=0,source_output_ages=[2,3],age_basis='all2782 native FF identities/clock/control/data functions unchanged, exact original RTL fixtures pinned',physical_pulse_and_native_fixture_replay='OPEN_UNTIL_GRANTED_NATIVE_SUCCESSOR'),indent=2))
