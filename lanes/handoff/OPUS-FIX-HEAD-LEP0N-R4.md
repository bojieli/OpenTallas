# OPUS-FIX-HEAD-LEP0N-R4 (11-21 04:2x PST): hd_lep0N owner + HEAD plan-event rows (successor of R3)

Predecessor: lanes/handoff/OPUS-FIX-HEAD-LEP0N-R3.md (measured congestion cause, cancelled refs, column design).
Lane dirs: epyc10 /srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r2 (L, Codex shelf1121/split1121/late_meta1121),
epyc10 /srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r3/{cancelled_ref,col1121}; hub logs intel2 ~/opus-fix-head-lep0n-r4/.

## In flight (waiters armed, OT_LANE=OPUS-FIX-HEAD-LEP0N-R4)
1. MAIN: ten-bank shelf place, unit oth-ubuntu-1632910-1795258813 (epyc10, kit L/shelf1121/reset_remapped_v2/gen/hd_lep0N,
   run_place.log). 04:2x: pre-GPL ring placement done (3_2_place_iop at 11:20 UTC). Next: when 3_3/3_place lands, compare
   east band (x 800-1600, y 550-700) RUDY/GRT congestion vs r11b (col1121/../cancelled_ref/r11b/reports).
   stage_odb_cap.log "Permission denied" lines = root-owned container results it cannot trim; harmless.
2. COLUMN A/B v2 (private plan delta, COORD ruling): col1121/run_col2.sh = lep_col.py column macros + tapmove.py (78 covered
   explicit taps -> nearest legal street site, same legality as taps.explicit_tap_sites; names/order kept; max move 103 um,
   mean 34) + reprice.py (78 tap_offset rows += fitted leg 0.188/0.175 ps/um TT/FF on tree_e5c13a routed RC; shift mean
   5.1 ps, max 19.3, 9 > 10 ps; ESTIMATE - the routed re-issue comes from the die clock after apply; the r13 clock input plan
   and die_trial_r13.py were cleaned up, so the tree cannot be regenerated bit-for-bit). Plan col1121/tapmv/plan.json sha
   336b359e59e7. Pipeline remap -> gen (HEAD env, no S81 GPL exit) -> preflight -> strict bind + LATCHECK; ot-run unit
   oth-ubuntu-3293119-1795262563 (epyc10), hub log ~/opus-fix-head-lep0n-r4/col2_pipe.otrun.log. Then G0 + kit.
3. Split TX extraction LEC oth-ubuntu-1710854-1795258959: backup proof only.

## Late-meta RX fix (-679 ps, L/late_meta1121, elab + depth-28 lemma PASS)
Not in the column build: gen uses --rtl-root = the sealed r16 snapshot, and the candidate adds a file (meta_rowpair.sv);
mixing it would confound the congestion A/B. It goes as an RTL row into the next HEAD event (manifest tree), then the
placed/timed build on whichever macro form wins.

## HEAD plan-event rows held here (next batched HEAD event ~11-22 01:xx, 24 h after r16 apply)
- R4-1 hd_lep0N macro form: shelf (42fd64227556) or column (336b359e59e7) - whichever clears the east band.
- R4-2 hd_lep0N 78 tap moves + re-priced rows (col1121/tapmv/tap_moves.json, tap_rows_est.json) if column wins.
- R4-3 hd_lep0N late-meta RTL (L/late_meta1121/candidate) once placed/timed.
- SERDES-R4 rows (posted 03:50): hd_st_k5 reader_start rx_i:4 <- rr_t54 1676 um (~4 registered START relays),
  hd_st_m rx_i:1 <- rr_t8 1261 um (~3); note R-REACH-5 also lists 110 hd_st_k5 and 17 hd_ctl_n raw reset hops over 405
  (epyc10 .../opus-fix-head-serdes-r4/reach/draft.tsv). +cycles pre-approved; post START LATENCY delta.
- SERDES-R4 once sdr2d proves: hd_serdes tap_group u_enc -> clk_t20, verilog_defines += OT_S81_KP4_SYN_SCOPY,
  OT_KEEP_WIRES += ot_s81_kp4_dsyn:S_u.
Event = strict bind + LATCHECK + G0, then apply.

## Reported
- 04:2x BUG to FLEET-WATCH-R4: ot-run --cancel reached only stale clients (r8b/r11b/lep_p3 units), containers kept running.

## UPDATE 11-21 ~06:xx PST
- Shelf kit 1632910 FAILED 3_3 exit 2 = plan geometry stop (OT_CLAND band FAIL: txwd_l1b0/b1 rects under moved g_tx[2] bank4,
  0 free). Not GPL / placement-setup / tool. Env diff vs r11b: intended r16 changes only.
- Fix LEP-BANDFIX-1 (epyc10 .../opus-fix-head-lep0n-r3/bandfix.py PLAN OUT REP [radius_steps] [target]): rects < 50 % free slide
  same-size to nearest site >= target free (shelf 0.8: 3 rects, max 15.7 um; column 0.6 r420: 52 rects, median 49, max 148 um).
- Pipelines (run_bf.sh NAME: gen -> preflight -> strict bind/LATCHECK -> G0) memory-queued on epyc10:
  hub ~/opus-fix-head-lep0n-r4/{shelf_bf,col_bf}_pipe.otrun.log. NEXT: on BF_PIPE_PASS launch
  ot-run --mem 48 --threads 12 --hosts epyc10 --dir D/NAME/gen -- bash D/NAME/gen/run_kit.sh D/NAME/gen/hd_lep0N route 48 12
  (ot-run needs --stage for scripts outside --dir; first launch was REFUSED by ISOLATION step 3).
- Column v1 kit (gen3) never started (client stopped while memory-queued); superseded by col_bf.
- START rows: reach_rules fix --rules 1 = raw re-points only (k5 32, m 5), rr_t54/rr_t8 hops gone; landing_local_resets left
  (k5 87 over 405, m 1 at 410). Re-pointing local resets to rst_n leaf taps gives 'missing' raws (they need rst_rl relays):
  open row for the reset owner. Files startfix/{fix_plan.json,fix_report.json,after.tsv}; fix2_plan.json is INVALID, do not use.
- Split TX LEC FAILED (19 unproven equiv, lane1/2 RX valid/credit) - backup only, not chased.
