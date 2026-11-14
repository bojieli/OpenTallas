# TL-COLH10R0P4 (S81 col_h10_r0_p4__t1) 11-14 04:51
- Real cause (same as P1/P5/LEAFT14): wave src B3v/src ot_dp_clk_landing.sv lacks LOCAL param while bind emits .LOCAL(1) -> GEN_LINT FAIL on all pv variants (pv5b623e07, pvcc166a6d, pvd11cc58b, pv07945c1e, pvc9270d09). Earlier 03:17 place_rc=99 was a harness copy-back issue.
- Fix already applied by TL-LEAFT14 on epyc7/9/10/intel1; I applied the same 4 rtl/common files (landing, landing_ca, dly_cnt, meso_fifo from origin/main) to epyc8 B3v/src (new inodes; backup epyc8 /srv/opentallas-scratch2/claude/tl-colh10r0p4/bak). All 5 gen hosts now fixed.
- Wave relaunched pvc9270d09 and pvd11cc58b at 04:47; follow them through gen/place/route. Pass -> AUTO-RESIGN row.
## 10:06 update
- LOCAL lint fixed; pv5b623e07 (a3) and pv07945c1e (a6, dedups pvcc166a6d/pvc9270d09/pvd11cc58b/pvd8c0565f) passed gen+place; geom PASS-COND (fill/empty advisory).
- Route jobs submitted: 2660187bad7f (pv5b623e07, 06:30) and ae2abae11aa1 (pv07945c1e, 07:39); ot-run clients alive on intel2 3.5 h, both queued on epyc9 admission (waiters 43, MemAvailable 160-64 headroom). Not dead, not started.
- Waiter armed on terminal lines (CLASSIFY/FINISH/FAIL) for both. On pass: AUTO-RESIGN row + RESULT.
## 10:14 correction
- 2660187bad7f (pv5b623e07) is NOT blocked on LEC: container dpkit-...-225259 (epyc9) is in 5_1_grt, openroad 108% CPU, log at extra iteration 30/30 (congestion not converging, GRT-0116 likely next). A second container dpkit-...-3888328 (epyc7, 5.7 h, 93% CPU) also runs GRT for the same item, at extra iteration 10/30; the LEC reuse-proof owner id 2563149 is not a live container (stale reference, harmless).
- ae2abae11aa1 (pv07945c1e): a1.log last 09:47, still waiting on memory admission (epyc9 load 115/96, waiters 43). Not yet admitted; ADMIT-TUNE-1 did not free it.
- If epyc9 GRT fails: read overflow map, apply COLH9R1 forms (UTIL 0.3-0.4, MAX_LAYER M8/M9), share with TL-COLH10R0P1.
## 10:19 B3x2 forms
- No B3x2 attempt exists for col_h10_r0_p4 pvs (wave launches only under old plan 4b7f1e087434; B3x2b plan f272fe26b84d contains the same pv names). So ae2abae11aa1 NOT cancelled (COORD condition unmet).
- epyc7 -3888328: sealed ot-job col_h10_r0_p4__t1__pv5b623e07-route-loved-redfish-3822634 (started 06:33, kit copy_back intel1->epyc8, run_kit.sh route 48 8), a second route of the same old-plan kit; its ot-run client is not on intel2/intel1/epyc*.
- Private B3x2b forms launched on intel2 (kit_wave.py run-item, specs ~/type-s81-colh10r0p4/{fa,fb,fc}, work epyc10 /srv/opentallas-scratch2/claude/tl-colh10r0p4/<k>): fa UTIL0.4 M8, fb UTIL0.3 M9, fc UTIL0.5 M9, all OT_GRT_ALLOW_CONGESTION=1.
## 10:27
- Cancelled ae2abae11aa1 (old-plan pv07945c1e, never admitted) by exact PIDs 3901872/3582093/3581956 per COORD.
- 2660187bad7f (pv5b623e07, old plan) CLASSIFIED STRUCTURAL grt-overflow GRT-0116 at 10:27 (extra iterations 30/30 not converged), as predicted. Epyc7 duplicate (-3888328) still in GRT, kept.
- Main path: B3x2b forms fa/fb/fc (UTIL 0.4 M8 / 0.3 M9 / 0.5 M9, ALLOW_CONGESTION), waiter armed on run-item exit.
## 10:28
- Cancelled epyc7 duplicate per COORD: verified container dpkit-col_h10_r0_p4__t1__pv5b623e07-3888328 label ot-job.dir ...pv5b623e07-route-loved-redfish-3822634 and its run_kit.sh route cmdline, then docker stop + kill ot-job pid 3822634 (wrapper chain 3820217/3819383 exited). No pv5b623e07 process or container remains on epyc7.
## 13:33
- Form fa (U0.4 M8 ALLOW_CONG) run-item ended at geom (auto_geom FAIL = fill/empty advisory, same as wave PASS-COND). I launched its route myself: ot-run client pid 2704909 on intel2, kit epyc10 /srv/opentallas-scratch2/claude/tl-colh10r0p4/fa/gen/col_h10_r0_p4__t1__pv5b623e07, log ~/type-s81-colh10r0p4/fa/route.log; queued on epyc10 memory admission. fb/fc still in geom; launch their routes the same way when they stop.
