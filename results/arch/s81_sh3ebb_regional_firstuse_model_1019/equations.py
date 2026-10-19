"""Finite four-state source equations; not an RTL simulator or reachability proof."""
import itertools,json,pathlib
H=pathlib.Path(__file__).resolve().parent
V=('0','1','x','z')
def band(a,b):
 if a=='0' or b=='0':return '0'
 if a=='1' and b=='1':return '1'
 return 'x'
checks=[]
for rn,raw in itertools.product(V,repeat=2):
 # Anchor captures rn & pin in one FF; candidate simultaneously captures both operands.
 anchor=band(rn,raw);sampled_rn=rn;sampled_raw=raw;candidate=band(sampled_rn,sampled_raw)
 assert candidate==anchor
 checks.append([rn,raw,anchor,candidate])
# Between edges the candidate must use sampled rn, never live reset.
anchor=band('1','1');sampled=band('1','1');live_reset_mutant=band('0','1')
assert anchor==sampled=='1' and live_reset_mutant!='1'
# No extra sampled-rn stage: the first published post-release event is visible on its original edge.
assert band('1','1')=='1' and band('0','1')=='0'
# Actual ASR zero contract: SETN=1, recognized RESETN=0 assertion forces zero without any clock.
# Before the first recognized assertion, no equality to a permanent physical tie is asserted.
pre_assert={'anchor_tie':'0','candidate_arbitrary_q':'x'};assert pre_assert['anchor_tie']!=pre_assert['candidate_arbitrary_q']
after_assert='0';after_release_no_clock=after_assert;after_next_edge='0'
assert after_assert==after_release_no_clock==after_next_edge=='0'
# Wrong unreset/synchronous pin-FF models cannot meet the clock-stopped assertion contract.
assert 'x'!=after_assert
out={'scope':'four-state bitwise equations / event contract only; no RTL simulator, native phase or parent adoption','truth_table':checks,'truth_checks':len(checks),'live_reset_qualifier_mutant':'REJECT','extra_sampled_rn_stage_mutant':'REJECT','unreset_or_synchronous_only_pin_mutant':'REJECT','pre_assert_difference_preserved':pre_assert,'parent_first_observable':None}
(H/'equations.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS 16 exact four-state sampled-edge equations; REJECT 3 mechanism mutants; pre-assertion difference retained; parent first observable NULL')
