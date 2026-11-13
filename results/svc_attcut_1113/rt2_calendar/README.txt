SVC native H8 RT2 replay-overrun diagnosis, Codex 2026-11-13.

CONFIRMED witness in run_core_0.log (frozen baseline):
EXP 78 lv1 mode1 pending0 badgrp0 fault0
EXP 79 lv1 mode1 pending1 badgrp0 fault0
EXP 80 lv1 mode1 pending0 badgrp0 fault1
The cycle79 incoming P load overlaps the expander replay. The expander cannot accept it, but the parent has already consumed it. Sticky af becomes1 at80.

The parent allows LA=3 lookahead P blocks and p_go every cycle. The expander contract requires P loads at most every2 cycles and no other load in the replay slot after a live second word. Fresh delayed band feedback changes the burst spacing and therefore which words are lost. In the frozen model, the first56 merge-input events match; the next24 (job3, blocks0..2) have differing payloads with matching fin/block tags; laterjob3 blocks match. This locates corruption upstream of reduction, not in the merge arithmetic.

Existing bench summary faults=nflt counts expected golden fault bits, not observed expander af. Dummy sc.hex/pv.hex files make faults0 uninformative for protocol af. Both old reference and band DUT need the replay-slot guard before their native comparison is meaningful. Preserve old FAIL.

EXACT TRACE RECIPE (no RTL compilation, frozen ls_pair model archives):
1. trace_core.cpp includes Vtb.h and Vtb__Syms.h and inspects preserved state. It traces only through cycle450. CORE_IN is real head0 r_iv/r_ibank/r_ib. CORE_WR is real enabled stationary write mask/data and bank. EXP is real u_expand pending/bad_group/fault plus the actual load source. Wrapper input ports may be optimized aliases left at0, so do not use them as evidence.
2. run_core.sh compiles only this diagnostic harness and links each unchanged ls_pair/obj_s81_srx0_m0_hc and obj_s81_srx1_m0_band2m1t1_hc/Vtb__ALL.a with their existing verilated.o/verilated_threads.o. No archive, frozen source or verdict is modified.
3. job_core.sh runs the relink/simulation in the same verilator/verilator:v5.032 container used for those archives. A prior host5.050 header attempt failed before simulation; build_0.log is retained. Do not mix runtime header versions.
4. Admission command on intel2:
~/.local/bin/ot-run --hosts epyc2 --mem 16 --threads 2 --dir /srv/opentallas-scratch2/claude/hard-s81-svc-1/tile3/pvtrace -- bash /srv/opentallas-scratch2/claude/hard-s81-svc-1/tile3/pvtrace/job_core.sh
5. Actual running frontend: intel2 PID323280; log ~/tmp/hard_s81_svc_pvtrace_core_codex.log; E2 unit oth-ubuntu-1487115-1794608807. Outputs run_core_0.log/run_core_1.log.

Diagnosis accepted by SVC parent; it is implementing a source guard under OT_SVC_H8_REUSE_RT2 and launching fresh guarded reference/DUT proofs. No source edits by this diagnostic lane. No new probes are needed until fresh archives are available; the helper can then confirm actual af stays0.
