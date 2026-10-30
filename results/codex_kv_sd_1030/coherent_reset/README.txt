SD reset/collector coherent candidate — no plan-of-record adoption.
Existing try6 reused old bound reset names under a new physical reset tree.
Concrete mismatch: RTL u_rrl_25 -> rst_n_t4 (E1892,160), but physical hook
u_rrl_25 -> rst_rl_25 at S1650,30.24. This explains the 18/20 missing names
and long raw-reset/START paths; it is not justified by optimized dead nodes.

This patch refreshes only SD/_v1 reset/collector tree metadata and native RTL
against the actual candidate tree. All other54types compare exact. New/old
reset depth5/5, relay count59/56 and56/52. Fresh strictbind actual160parts/
56types/errors0/unbound0/tied0/undriven0/multiply0. Native module u_rrl_25 now
loads rst_rl_24 -> rst_rl_25 at the planned S1650,30.24 site.

Smallest native reset+START lockstep: both18tap+START graphs,12000random
cycles,0mismatch; skipped-stage mutant caught13694comparisons. First harness
failed because a JSON roundtrip changed tap_roles integer keys into strings,
making the harness emit mission logic for a bootstrap graph. The corrected
harness regenerates fresh RT objects exactly like bind.py; the failure is kept.

Boot data cycles0; raw depth/local monitor unchanged; inherited conservative
ready budget392 is retained (computed topology bound335 is not a speed claim).
The strictbind used the otherwise-identical pre-conservative-budget sidecar
335; changing that informational bound to392 changes no emitted RTL.
This is a candidate functional proof, not physical signoff or adoption.

Important physical delta vs canonical plan_c: primary taps5south ->6rim plus
secondary clk_clk_phy declaration. Thus the old SDPG/try6 kits have frozen
outline but prior-trial clock pins, not identical canonical clock pins.
A coherent die clock/provider rerun is needed before adoption/counting.
Macro references and sink census in this patch are the existing staged trial
inputs; normalize to the portable macro/pin package when generating final kits.

Live/held: inherited try6 kept collect-only; own SDPG diamond DPL passed and
full placed GEOM/GRT50 running. No CTS/detailed route launched.
