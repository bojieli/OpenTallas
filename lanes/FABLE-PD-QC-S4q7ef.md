# FABLE-PD-QC-S4q7ef: r199 review-before-adopt of QC events S4q6d, S4q7e, S4q7f

2026-11-15 19:05 PST (03:05 UTC), FABLE-PD-QC-S4q7ef. Read-only. Nothing stopped, changed or launched except five small
python checks on epyc9 (plan JSON, derived R8 tables, bound RTL of the previous binds, qft3 harness).
Subjects: epyc9 die-qc-103/treeA plan_of_record zz_s29_qc103_{s4q6d,s4q7e,s4q7f}.json (+ sidecars), pinpad3.py,
bind_derive6.sh, w5_bcf_pads.json. Scripts and outputs: epyc9:/srv/opentallas-scratch2/claude/fable-pd-qc-s4q7ef/
(a1..a5.py/.out, b1.py/.out, s4q7f_extra_pads_48.json).
MEASURED = read or computed by me today. INFERENCE is marked.
State when written: the three first binds (S4Q6DBR / S4Q7EBR / S4Q7FBR) are still running; no derived table and no
rebind of these three exists. The pad replay therefore uses the derived tables of the same lane content: S4Q6BB (= S4q6d),
S4Q7CB (= S4q7e), S4Q7DB (= S4q7f). MEASURED: each event differs from its predecessor (6b / 7c / 7d) only in
reset.consumer_localization on the 9 sc types; lanes are identical.

## 0. Verdict per event

| event | verdict | reason |
|---|---|---|
| **S4q6d** | **ADOPT-OK** | Replay S4Q6BB + st_a ctl +3 / fe +1: 0 bad columns of 24, derive PASS (226,496 flops). sc/fe lanes at 3 / 3 / 4 (22 + 1), 0 lanes with fixed below source + destination, sc reset rows equal S4q3c on 9 of 9 types. |
| **S4q7e** | **ADOPT-OK** | Replay S4Q7CB + pins + the 72 pad rows: 0 bad columns, derive PASS (271,024 flops). Pads are the right form here (section 1, F1). Two non-blocking items become the next delta (F3, F5). |
| **S4q7f** | **BLOCKING** | Replay S4Q7DB + pins + the same 72 rows: **24 of 24 columns still fail** ("W5 S: no column pad up to 9 balances the tree"). The rebind will fail PARAM_REGEN as built. Fix measured (F2): 48 more pad sinks AND 24 tree-join pads, then 0 bad columns and derive PASS. |

## 1. Ranked findings

| # | finding | mark | owner |
|---|---|---|---|
| F1 | **S4q7e pads: right structure, small, and not in a ring band.** The 72 rows land as R8 pads at the far-cluster entry sink `u_fab.u_x_<c>_0.b_d`, i.e. inside the FAR cluster's type, after the landing ring and after the bus stations: cbf_q00 x2 `bc_i10` +2 (1,032 flops per instance, 23 instances), cbf_q00_s2 `bc_i00` +2 (1 instance), cbx_q10 x4 `bc_i20` and `bc_i30` +2 each (2,064 per instance; 4,128 on the one W5 S instance). Total 76,368 flops. Against the free `ot_dp_dly` flops these types already carry in the S4Q7DBQ bound RTL (cbx_q10 29,824; cbf_q00 37,545-38,059) that is +3 to +7 % (+14 % on the W5 S instance). They are a delay at the tile pin, not ring flops, so the band densities do not change. | MEASURED (location from member sink_part / lane dst bus; placement site INFERENCE: free cells between the last station and the tile pin, in the channel column) | none |
| F1b | One type gets a strap bank from the pads: cbx_q10__cl94a12200 (14 instances) has pad 2 on 13 instances and 4 on the W5 S one for `bc_i20` and `bc_i30`. By r8_strap_sites that is base 2 + an `ot_dp_dly_cnt` DMAX 2 bank on 2 x 516 bits in ALL 14 instances: about +2,064 bank flops per instance beyond the pad itself (max pad 4, far under the strap limit 15). The other 6 padded types have one pad value per bus (no bank). | MEASURED pads, bank size from the tool text | DIE-QC-103 (expect it in bind_r8pad_strap_audit; not a defect) |
| F2 | **S4q7f needs 72 more pad sinks than it has.** S4Q7CB -> S4Q7DB changes 48 members: lanes `c_<s>_bn_00__bc01` / `__bc11` and `c_<s>_tn_00__bc01` / `__bc11`, +3 each (the 3 FIRM stations on cbn_q01 `bc_i02` / `bc_i12`), sinks = NEAR cluster row-2 entries `u_x_0_2` / `u_x_1_2`. Near row-2 shifts become [2, 2, -1, -1] over columns 0-3 (were [-1, -1, -1, -1]). Two things break: (a) columns 2, 3 of the row-2 entry are 3 early, (b) rows 2-3 of the near cluster are 3 later than rows 0-1 at the top Morton join (`u_t_0_0` n_a / n_b), which no column pad can reach (a column pad shifts both row halves). Harness results on S4Q7DB + pins + 72 rows: +3 on near `u_x_2_2` / `u_x_3_2` `b_d` alone: 24 bad; +3 on near `u_t_0_0.n_a` alone: 24 bad; **both: 0 bad, derive PASS (271,024)**. Cost: 48 sinks x 3 x 516 = 74,304 flops in cbn_q11 x2 (`bc_i22` / `bc_i32`, 3,096 per instance) + 24 sinks x 3 x 514 = 37,008 flops at the near cluster root (`u_t_0_0.n_a`, sink part c_<s>_bn_00 / tn_00). Rows: epyc9 fable-pd-qc-s4q7ef/s4q7f_extra_pads_48.json; the n_a members are in the re-keyed cb16 table (tree_align), so the pin must take them from the EX table, +3. | MEASURED | DIE-QC-103 (pinpad), QC-CB-GEN-1115 (re-run w5exp on the next derived table) |
| F3 | **For S4q7f the cbn_q11 half of F2 should be real stations, not pads.** In the S4q7f sidecar, cbn_q11 x2 `bc_i22` (route 1,170 um, hops 176.6 / 332.6 / 328.3 / 332.6) and `bc_i32` (1,251 um, 141.2 / 371.5 / 367.2 / 371.5) each list `u_st` + one `u_st_more` site with plan_stations 0, lane fixed_cycles 0 and no `u_lpad` in the bound RTL (S4Q7DBQ). If `u_st_more` has no flop behind it the last leg is 661 / 739 um unregistered. The +3 these two buses need anyway (F2) pays for those sites: put the cycles on the route as plan station rows (FIRM), not as 3,096 free flops at the tile pin of the type whose SW corner is the known clump. Same pattern, lower urgency: cbx_q10 x4 `bc_i30` (1,262 um, 3 sidecar sites, 1 plan station, `u_lpad` D 1) gets +2 from the 72 rows; cbn_q11 `nb_i22` (3 sites, 2 plan stations, D 2, hops to 388.8). | sites, cycles and RTL depth MEASURED; "u_st_more has no flop" INFERENCE (kit consumer of `u_st_more` is not in treeA tools; only cland_bin_sites.py names it) | QC-CB-GEN-1115 confirms what backs each sidecar site; DIE-QC-103 rows |
| F4 | **cb band fill by event (ring flops from cb_ring_flops.json / rect area, 104 bands).** S4q6d: 80 bands above 0.6 (ring bands 0.99-1.19): legality only, as ruled; cbn_q11 clump unchanged. S4q7e: 59 above 0.6: cbn_q11 x2 / cbf_q11 are reshaped, but cbx_q10 x4 (`bc_i20` / `bc_i30` / `a22_i` 0.99-1.00), cbn_q01 x3 `bc_i02` 0.99, cbn_q11 `bc_i32` 0.99 and cbn_q00 stay at 1.0-1.18. S4q7f: ring bands at or under 0.58 (cbn_q11 `bc_i22` 0.583, cbf `bc_i00` / `bc_i10` 0.549, serdes_tx 0.55); left above: cbn_q00 cl622f65d2 / cldbcda913 (hard-core ring types, `rsf_i` 0.65: the rect is the macro, not a strip) and the `monitor_*` bands (603 flops in 411 um2, 1.47, 15 bands, unchanged by any event; the count is the scaled table value, not a place log). No band has a pin-to-band hop above 405 in any event. | MEASURED | QC-CB-GEN-1115 (monitor bands: one place-log count) |
| F5 | **S4q7e / S4q7f add head pads in the hc columns.** With the 72 rows the column head pads come out (2, 0, 2, 2) on 14 of 24 slice-sides and (0, 0, 0, 0) on 10 (S4q6d: 0 on all 24). Cause: the hc1 `cws1` / `cwn1` lanes +2 (14 lanes) move column 1; the derive pads heads 0, 2, 3 by 2 x 516 = 1,032 flops each (44,528 flops total, 271,024 against 226,496). Two consequences to read on the rebind: S_PAD / N_PAD now differ between instances of one head type (hard_core_param / type split), and +1,032 flops per head sit next to the hc landing strip that was sized for 8,902 flops at 0.53 (about +12 % if they place in the strip). | pads MEASURED in replay; placement effect INFERENCE | DIE-QC-103 (hcparam on S4Q7EBQ), QC-HC-STRIP-1115 |
| F6 | Station hops above 405 um with no sidecar row. S4q6d: cbf_q00_s2 `bc_i10` 1,025.5 and `bc_i00` 636.7, `nb_i12` 417.7 on 5 types, `y_o00` 413.0 on cbn_q00 x3 (all baseline, same in adopted S4q3c). S4q7e and S4q7f: only `y_o00` 413.0 x3. | MEASURED | QC-CB-GEN-1115 (`y_o00`) |
| F7 | Lane rule holds on all three: stationed lanes 1,372 / 1,372 / 1,420, 0 with fixed below source + destination; sc/fe 11 x (1, 2, 3), 11 x (2, 1, 3), 1 x (2, 2, 4). The pads are R8 pins, not lane fixed_cycles, so kit_istations' "bound module has N pad stages > planned" stop is not triggered by them (it would be if the rows were applied as fixed_cycles, as the pad post first proposed). | MEASURED rule; kit effect from tool text | DIE-QC-103 (keep pads in the R8 pin) |

## 2. What each event leaves open for the first hc / cb kit GRT (question 4)

- **DRT-0255 (hc, sc):** none of the three carries the M8 band phase key or a PG form; S4Q3C kits stopped again at 18:36
  (sle_hc2__clcc5e3e61, sle_sc_v1__cl7479a5ec). hc / sc kits on these events reach GRT (valid GRT evidence) and then
  stop in detailed route until DRT0255-PROOF's form is in the QC gen env. Not an adopt blocker. MEASURED log lines,
  INFERENCE outcome.
- **hc:** needs OT_CLAND_STRIP_DENS 0.45 in the item env ("target 0.45 -> rows 5" in the place log); hc2 has no pilot;
  on S4q7e / S4q7f add F5 (head pads beside the strip).
- **cb:** on S4q6d a cb kit GRT proves nothing new (bands at 1.0-1.19, clump unchanged). On S4q7e the proof types are
  cbn_q11 x2 and cbf_q11 only; cbx_q10 / cbn_q01 kits on S4q7e run at about 1.0 and should not be read as the fix.
  S4q7f (after F2) is the first plan where every strip band is at or under 0.58.
- **sc:** reset localization rows are out on all three, so the sc reset hop class (u_rrl_N to ot_dp_st, 690-1,041 um,
  QC-SC-ROWS) is open on all three until bind-reset-tree-1115 merges and the rows return (next delta).
- **fw / st_b setup:** identical in all three (S4q4c station rows, 18,500-19,700 flops per fw type). No event changes
  it; the first gate against -236 / -439 (fw) and -187 / -202 (st_b) is the read.

## 3. Ranked fixes

1. **DIE-QC-103, S4q7f (blocking, about 20 min + rebind):** extend the pin step with (a) +3 on the 48 near row-2 sinks
   (`c_<s>_bn_10__bc21` / `__bc31`, `c_<s>_tn_10__bc21` / `__bc31`; file s4q7f_extra_pads_48.json) and (b) +3 on
   `c16_<s>_{1,2}.u_t_0_0.n_a` (24 sinks, from the re-keyed cb16 table). Rebind as S4q7g. The running S4q7f rebind can
   finish for its report but cannot pass. MEASURED fix.
2. **DIE-QC-103 + QC-CB-GEN-1115, same S4q7g if QC-CB-GEN answers within the hour, else next delta:** carry item 1(a)
   as 3 plan station rows on cbn_q11 `bc_i22` / `bc_i32` (lane fixed +3 by the sum rule) instead of pads; the derive
   sees the same depth. Item 1(b) stays a pad (no route to station). INFERENCE on need (F3).
3. **DIE-QC-103, read on the S4q7e rebind (no hold):** hard_core_param and type count for the head types with
   S_PAD / N_PAD 2 (F5); r8pad strap audit for cbx_q10__cl94a12200 (F1b).
4. **KIT-OPS-5:** cb pilot on S4q7e = cbn_q11 only; cbx_q10 / cbn_q01 pilots wait for S4q7g. hc pilots as ruled.
5. **QC-CB-GEN-1115 (next delta):** one place-log flop count for a `monitor_*` band; `y_o00` 413-um hop on cbn_q00 x3;
   state per sidecar site whether a flop exists (`u_st`, `u_st_more`) so the site count and the lane cycles can be
   checked by one script.

## 4. Stop list

- Do not post READY+ADOPT for S4q7f as bound; do not relaunch it unchanged.
- Do not apply the pad rows as lane fixed_cycles (kit_istations stops on pad stages above planned stations).
- Do not equalise the four bcf lanes to their maximum (QC-CB-GEN measured 3 columns still bad) and do not pad near
  row-0 entries for the row-2 shift (the head pads already balance row 0; my test of that form left 24 bad).
- Do not drop the 3 stations on cbn_q01 `bc_i02` / `bc_i12` to avoid the pads: the routes are 1,244-1,262 um.
- Do not read a cbx_q10 / cbn_q01 kit GRT on S4q6d or S4q7e as the band verdict, nor an hc / sc DRT-0255 stop on any
  of the three as a plan failure.
- Do not hold S4q6d or S4q7e for F3-F6.

## 5. Not checked

- sdc_lint and tap sink caps of the release list: no kit exists for these plans and I did not run gen or check.py
  (time). PLAN-GATE-PRE-1115 must supply both before ADOPT, as r199 says.
- The actual rebinds (none finished): all pad results are harness replays on S4Q6BB / S4Q7CB / S4Q7DB.
- Band rect against core halo: my 4.32-um test flags 14-24 band / tile-core pairs per event, most also present on
  S4q6d; I did not compare with S4q3c or with QC-CB-GEN's checker. New in S4q7f by name: cbf_q00__cl870de686 `na_i00`
  / u_t01, `nb_i00` / u_t11 (cbf_q00 x3), cbf_q01_s2 `nb_i12` / u_t13. QC-CB-GEN: confirm these three.
- Where free pad cells place (no kit); whether the protocol tolerates the added cycles (latency table carries them).
