# S81-COL-J9 handoff (Opus, started 11-23 05:5x PST; LIVE MEMORY)
Replaces FAM-S81-COL-H10-R4, FAM-S81-COL-H9R0-R4, OPUS-FIX-S81-COL-RANKSEAT-R2, VIS-S81-COL, UCF-VIEW-FIX, FIX-S81-UCF-VIEW (their handoffs = history).
Lane dirs: epyc10 + intel2 /srv/opentallas-scratch2/claude/s81-col-j9 (nehg/, tmp/, lagprobe.*). Deliver rows to S81-J9-ASSEMBLY-R6 (wave A 10:30, wave B 12:30 / second compose <17:00).

## State at start (05:5x)
- col_h10 rows (SEAMBLK 5dbaeeb50fbd, TAPSPLIT 0c8530ca4c1c, TAPGRT ef09171c92b8, REACH v2 5f8b2104a625, GROW 02b182e95344, ECORR) PRE-gated in epyc10 fam-s81-col-h10-r4/j9/r2m/plan_final.json 708e94880349 (= R2 95ddb + H10 delta, ECORR form). ASSEMBLY adopted. Swap alt yg8 ae2b9ab9abc7 (not rebased on R2).
- cl95b37463__pv1a6ec9c2@2 cancelled 03:58 by H10-R4 (no keep). Relaunch on J9 bound tree after the cut.
- item_env: col_h* OT_KEEP_WIRES=ot_dp_dly:r; col_h9_r0_* = "ot_dp_dly:r ot_s81_rly:rq" (merge: globs by length, exact last; exact col entries set no KEEP_WIRES -> keep applies). All col entries still set OT_RELAY_MID_RE old regex (env beats plan relay_mid_re_types) -> J8/J9 apply must unset (ASSEMBLY j8_apply.sh).

## NE-NODES + HOPGAP gap (found 06:0x)
- H9R0 composed NE (243907ae3dc1) + HOPGAP (680e3fa669c4) only on v3+strip (b01c97949450); RANKSEAT graft _ss/R2 and r2m do NOT carry them; manifest has no row. Fixed by 3-way merge base ac3a (plan_v3_strip) / mine b01c / theirs r2m 708e9 -> epyc10 s81-col-j9/nehg/plan_m.json (R2+H10 30924/30924 kept, NE/HG 355/355 kept).
- BUG found: HOPGAP moves p2 cl0045af7b u_r0.u_s4 W 8.64 (406.08->397.44) but leaves clk_t36 at 393.12,907.2 (illegal; bind would refuse; PRE LANDREMAP reset tree build fails die-wide). fix_t36.py shifts clk_t36 -> 384.48,907.2 on the 5 types. Rerun nehg/run_nehg2.sh -> plan_final2.json + pre2.json.

## COL-ROMIN-LAG probe (RANKSEAT item; decision 10:30, default NO-LAG 6251a023d393)
- planR2L bind b_808b37ec0b73 epyc7 DONE 05:15. Probe launched 06:1x: intel2 s81-col-j9/lagprobe.sh (ot_build_hub --goal finish, rt 73fdcdf7365e, --ab OT_PROBE_THROUGH=1 --ab OT_RELAY_MID_RE=), log lagprobe.log, pid lagprobe.pid. Read 4_cts_post_hook latch u_lk_xd_* -> ROM setup (was -94.9) and ROM-out side.

## Probes adopted
- VIS h10p1 (ECORR vs swap): intel2 vis-s81-col/bld/h10p1.log pid 840057, epyc8 treeJ7V3 bind running. Winner by 09:30 (default swap per manifest; r2m is ECORR form -> if swap, rebase yg8 like runm.sh).
- VIS cl774 SSTRIP probe: intel2 vis-s81-col/bld/cl774.log pid 2152802 (run-item since 05:48, intel1 treeJ7V2).
- u_cf DRT probe: intel2 unit oth-ubuntu-2670192-1795435218, ucf-view-fix/probe_p3/out/route.log (opt iter 1 at 05:5x). Evidence only; row 3i stays. VIA34/M4 shorts at u_cf -> M3-shadow variant.
- FABLE-FIX-S81-COL-RANKSEAT h9r1 planR2 rep in GRT on intel2 (latch hold read).

## Census (HOTSPOT-GAPS v2.4 col rows: 179; 105 covering_row NONE)
- scratch col_gaps.tsv. NONE classes: RESET-ASYNC 38, HOLD-SKEW 19, IO-BOUNDARY 19 (CLASS-FIX-RHI), CLOCK-NDR-DROP 12 (FLOW-OPS REASON), REPAIR-CAP 7, CLOCK-SKEW 7, GLOBAL-DEMAND 2, REACH 1.
