# Qwen methodology re-plan: both-cluster xt1 PASS

Collected 2026-10-25 from the existing epyc3 run, without rebuilding or changing the RTL. Bind = `epyc1:/srv/opentallas-scratch2/claude/qc/bind_meth_cb16` on `claude/qc-meth-1024@a281ceb5ce` (405-um methodology re-plan plus R8/CB16).

Nominal lead24/gap4: **near64/64 and far64/64 exact** across QKV/O/GU/down. The +1 hr-lane mutant also remains numerically64/64, and the strict static-consumer schedule gate catches it on all16 signal groups (cw_go and result edges for4 operations on2 clusters). `results/schedule_gate.json` verdict PASS. This is the same numeric-plus-fixed-consumer-edge rule as the accepted capacity pass.

The regenerated constants are kept alongside the actual timing records. The link pass is `../link_meth` on parent commit f3edf0870: tp8 3/3 +9 mutants, xdie9/9 +13, ovl4u2/2 +8, all PASS. tp8 LS is407; +1296 collective cycles/token vs LS389.

This carve does not establish a whole generated-die token pass or physical sign-off. The generated bound top still distributes rst_n directly; wavefront reset/start-broadcast integration remains open (see link_meth README). Existing bound-s8 stage failures are tracked independently in TOK-QW.

The paused collector `finish_xt1.py` contained an invalid unquoted rsync command. Collection here uses the existing `bind_smoke.fixed_schedule_gate` on untouched simulation logs; the failed collector did not require another simulation.
