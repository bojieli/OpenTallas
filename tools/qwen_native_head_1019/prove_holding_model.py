"""Mathematical storage recurrence only; no production RTL qualification."""
import itertools,json
checks=0
for phase0 in (0,1):
 for hist in itertools.product(range(2),repeat=3):
  for seq in itertools.product(range(2),repeat=7):
   line=list(hist);phase=phase0;bank=[None,None];bank[phase]=line[1];bank[1-phase]=line[0];result=line[2]
   for value in seq:
    old=bank[phase];bank[phase]=value;result=old;phase^=1
    line=[value]+line[:2]
    assert result==line[-1];checks+=1
# Continuous clocks carry invalid payload history too. Valid-only advances fail.
line=[0,0,0];bank=[0,0];phase=0;conditional_witness=None
for edge,(value,valid)in enumerate([(1,1),(0,0),(0,0),(0,1)]):
 line=[value]+line[:2]
 if valid:result=bank[phase];bank[phase]=value;phase^=1
 if result!=line[-1]:conditional_witness=edge;break
assert conditional_witness is not None
# Resetting only the new pointer is not equivalent to unreset source data.
line=[1,0,1];phase=1;bank=[line[0],line[1]]
correct_old=bank[phase];rewound_old=bank[0]
assert correct_old!=rewound_old
# A write-first bank destroys the required OLD collision result.
collision_bank=[0,0];collision_phase=0;old=collision_bank[collision_phase]
collision_bank[collision_phase]=1;write_first=collision_bank[collision_phase]
assert old!=write_first
print(json.dumps({'kind':'ABSTRACT_RECURRENCE_NOT_RTL','checks':checks,'all_initial_histories_bijective':'PASS','continuous_update_required':True,'valid_gating_mutant_fail_edge':conditional_witness,'pointer_rewind_mutant':'FAIL exact retained-history mismatch','write_first_mutant':'FAIL input1 vs OLD0','reset_convergence_only':'After3 uninterrupted edges any legal phase converges; qualification of earlier payload consumers remains OPEN','native_or_production_claim':False},indent=2))
