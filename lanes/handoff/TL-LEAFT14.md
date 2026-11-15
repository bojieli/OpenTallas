# TL-LEAFT14 (S81 ot_s81sl_leaf__t14) 11-14
- t14 attempt_4 FAIL GEN_LINT: ot_dp_clk_landing.sv:10 Cant find object for defparam LOCAL. Same error hits 52 wave rows (slice_station t49/t29, col_h9/h10, leaf t35 ...).
- Cause: s81 wave src (epyc9 .../s81-b3-clk/run/b/B3v/src, src_sha 7073a6b4) predates CLAND-RING-LOCALITY ef145cfb0d0; bind emits .LOCAL(1) but staged ot_dp_clk_landing.sv has no LOCAL parameter.
- Fix 11-14: replaced rtl/common/{ot_dp_clk_landing,ot_dp_clk_landing_ca,ot_dp_dly_cnt,ot_meso_fifo}.sv in B3v/src with origin/main versions (new inodes; backup epyc9 /srv/opentallas-scratch2/claude/tl-leaft14/bak). Defaults identical logic.
- Needs: KIT-OPS-3 retry of s81 rows failed with this GEN_LINT error (t14@4 first).
- 19:25 successor: live forms wave attempt_5 (epyc7 GRT pid 356408) + private r1 (epyc10 GRT pid 802561); both GRT extra iters; waiter on localhost scratchpad w14.sh. Do not relaunch.
- 01:10 successor: wave a5 gone (watchdog), r1 epyc10 still GRT; ASK Fable PD review posted; no relaunch.
- 01:35 r1 cancelled; r2 (u_vs +34.56, ft5 last stn (150,412)) place+GRT launched, log coord/lanes/tl-leaft14-logs/r2.log; next: post overflow after, hand delta to DIE-S81-92 if converges.
- 09:25 r2 result: overflow 139 (not 0), killed 143 externally; ASK posted.
