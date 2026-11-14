# TL-COLH10R0P4 (S81 col_h10_r0_p4__t1) 11-14 04:51
- Real cause (same as P1/P5/LEAFT14): wave src B3v/src ot_dp_clk_landing.sv lacks LOCAL param while bind emits .LOCAL(1) -> GEN_LINT FAIL on all pv variants (pv5b623e07, pvcc166a6d, pvd11cc58b, pv07945c1e, pvc9270d09). Earlier 03:17 place_rc=99 was a harness copy-back issue.
- Fix already applied by TL-LEAFT14 on epyc7/9/10/intel1; I applied the same 4 rtl/common files (landing, landing_ca, dly_cnt, meso_fifo from origin/main) to epyc8 B3v/src (new inodes; backup epyc8 /srv/opentallas-scratch2/claude/tl-colh10r0p4/bak). All 5 gen hosts now fixed.
- Wave relaunched pvc9270d09 and pvd11cc58b at 04:47; follow them through gen/place/route. Pass -> AUTO-RESIGN row.
## 10:06 update
- LOCAL lint fixed; pv5b623e07 (a3) and pv07945c1e (a6, dedups pvcc166a6d/pvc9270d09/pvd11cc58b/pvd8c0565f) passed gen+place; geom PASS-COND (fill/empty advisory).
- Route jobs submitted: 2660187bad7f (pv5b623e07, 06:30) and ae2abae11aa1 (pv07945c1e, 07:39); ot-run clients alive on intel2 3.5 h, both queued on epyc9 admission (waiters 43, MemAvailable 160-64 headroom). Not dead, not started.
- Waiter armed on terminal lines (CLASSIFY/FINISH/FAIL) for both. On pass: AUTO-RESIGN row + RESULT.
