# TL-COLH10R0P4 (S81 col_h10_r0_p4__t1) 11-14 04:51
- Real cause (same as P1/P5/LEAFT14): wave src B3v/src ot_dp_clk_landing.sv lacks LOCAL param while bind emits .LOCAL(1) -> GEN_LINT FAIL on all pv variants (pv5b623e07, pvcc166a6d, pvd11cc58b, pv07945c1e, pvc9270d09). Earlier 03:17 place_rc=99 was a harness copy-back issue.
- Fix already applied by TL-LEAFT14 on epyc7/9/10/intel1; I applied the same 4 rtl/common files (landing, landing_ca, dly_cnt, meso_fifo from origin/main) to epyc8 B3v/src (new inodes; backup epyc8 /srv/opentallas-scratch2/claude/tl-colh10r0p4/bak). All 5 gen hosts now fixed.
- Wave relaunched pvc9270d09 and pvd11cc58b at 04:47; follow them through gen/place/route. Pass -> AUTO-RESIGN row.
