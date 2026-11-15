# FABLE-TRIAGE-S81 2026-11-15 00:45 PST: S81 failure triage, lane-claim check, two COORD extras

Reviewer: Fable, read only (no builds, no kit or plan edits). MEASURED = read from a log, plan, liberty, audit or proof file,
or computed by my own script on those files. INFERENCE = fits the numbers, not proven. Not redone: 450 budget / C1 ruling,
col tap-window ruling, count-aligned die rerun, element-halves priority.
Clock note: DIE-S81-92 (successor) lines are stamped 01:3x-02:5x PST while the hub clock read 00:26 PST. Scans by time
("since 21:00") must go by file position, not by those stamps.

## 0. Verdicts on the lane claims

| # | claim | verdict | why (numbers) |
|---|---|---|---|
| a | DIE-S81-92: declared tie rows for dsdv_svc_mem_ar ra_n / wa bits 3..5 | mechanism RIGHT, row TOO WIDE: fix before B6f binds | see 2.1 |
| b1 | S81-RESIGN-DEEP: idx hold-pad cap 7 -> 16 | WRONG: it hides that the tree did not get shallower | see 2.2 |
| b2 | shallower CTS forms kp4A / kp4B | WRONG target: the kp4 audit row cannot move with insertion | see 3.2 |
| b3 | shallower CTS forms gb_he / gb_hw (heA 400, hwA 360) | right target (LIB 588 / 567 > 490), unproven: gate at CTS | see 2.2 |
| c1 | S81-LEAF-PLAN: ft_seam_fix | RIGHT for 65 of 104; the 39 left are correctly called die-level; two checks open | see 2.3 |
| c2 | t57 growth +77.76 um | admissible, but lands at 0.595 against 0.60: no margin; prove by GRT, not by the cut model | see 2.3 |
| d | S81-COL-STREET p2 prototype | UNPROVEN, and not the lever-3 form; do not generalise yet | see 2.4 |
| e | col_h10_r1 hold -361 = cross-tap internal | RIGHT as the cause of the worst path; as a class label it covers 44 % of the endpoints | see 2.5 |

## 1. COORD extras

### 1.1 Grid-tap spread 68 / 100 / 139: which number is right

Both are right; they are different quantities. I reproduced the FABLE-CLOSURE-STRATEGY numbers exactly (MEASURED).

Recipe: epyc8 `die-grt0-s81/s81/b3x2d/proof/tap_arrivals_{TT,FF}.json`, list `taps` (20,647 rows: 13,994 `clk_t*`,
398 `clk`, 6,255 `clk_c*`). Group by `part`. Keep ports `clk` and `clk_t*` only. Per partition: max(`late_ps`) - min(`late_ps`).
397 partitions have 2 or more grid taps.

| per partition, grid taps only, late - late | TT | FF |
|---|---|---|
| median | 68 | 64 |
| p90 | 100 | 96 |
| worst col (fW5_p1_b0) | 139 | 133 |
| worst of all | 263 (bk_sel) | 244 (s_7N_x13, not bk_sel) |
| same with core taps `clk_c*` included: median / p90 / worst | 240 / 276 / 702 | 217 / 251 / 624 |

- This is nominal spread at one corner: no early/late derate and no CPPR. It is not a kit window.
- If the core taps are left in, the result is 240 / 276 / 702. INFERENCE: that is what DIE-S81-92 saw ("raw skew rows pair
  early core taps with grid taps").
- The kit window is `kitwin.json`: late(q) - early(p) - CPPR credit, max over corners and instances, per port.
  For the 216 col types (6,584 grid ports): per port median 64, p90 96, max 165 ps; worst port per type median 98, p90 121,
  max 165 (col_h9_r0_p5 pvee6f8140). The col kits carry 179-208 on every grid tap. So "about twice" holds for the typical
  port; for the worst port of a type the excess is 1.1 to 2 times.
- Correction to FABLE-CLOSURE-STRATEGY lever 2: the bk_sel 200-300 ps values in `kitwin.json` are NOT core-tap contamination.
  bk_sel grid-only spread is 263 ps and its grid ports read 184-263 in kitwin. In my recomputation the col grid-port windows
  are identical whether q runs over grid taps only or over all taps (216 of 216 types). bk_sel grid spread is real.
- Limit of my check: my CPPR credit (common path-prefix node) is cruder than the tool's and gives larger absolute windows
  (col worst-port median 149, max 228). I confirm the independence from core taps, not the absolute kitwin values.

Should col tap windows come from kitwin.json per port: YES, with one condition.
1. kitwin per-port values are an upper bound of any related-pair window, so they are safe, and they are already 2 times
   tighter than today. Do not wait for the per-type related-pair DB scan; it can only lower them later.
2. Condition: B6f changes the col tap set (`tap_max_sinks` 1500, pitch 208), so the b3x2d port names do not map to B6f
   col types. For the first B6f col kits use ONE flat window of 165 ps on every col grid tap (the b3x2d col maximum).
   After the die clock rerun on the bound B6f, switch to per-port kitwin.
3. Effect on the col_h10_r1 worst path: launch tap clk_t1 window 186 -> 94 gives -361.6 -> -269.6. The window is the
   smaller half; the tree skew of 334.6 remains (see 2.5).
Owner: DIE-S81-92 (plan `clock.tap_window`), KIT-OPS-5 (kit side).

### 1.2 The 45 core FAIL rows left by the B6f2 / B6f3 audit (36 types)

Source: epyc7 `s81-b3-clk/ev/audit_B6f3.json` (identical counts to B6f2). MEASURED.

| rows | types | core, pin | numbers | cause | fix | owner |
|---|---|---|---|---|---|---|
| 16 | 16 svc_hi / svc_lo | dsdv_svc_sx_hrow ck | depth 268.9, budget 250, rule depth <= budget - 50 | type not in the 296-type 450 override | add `insertion_target_override` 450 | DIE-S81-92 |
| 14 | 7 dsdv_slice_*_C | ot_s81sl_capc5r ck_cw 210.6, ck_rn 271.4 | same rule | same | same | DIE-S81-92 |
| 2 | gunit__t1 | dsdv_gunit_l0r 236.3, l5f 205.4 | same rule | same | same | DIE-S81-92 |
| 11 | serdes t1-t4, t12-t16 | ot_s81_kp4_dchn clk | clk->q 449.6 + setup 309.9 = 760, 73 ps left, rule >= 150 | see 3.2: sum does not depend on insertion; core is on the pma_rck island | read the serdes type STA at `u_chn/k_v*`; if it passes, exempt pad-clock cores in the audit | PLAN-READERS-1 (audit), HARD-S81-SERDES-1 (path read) |
| 2 | bk_sel__t2 | dsdv_bksel_q (651.6), dsdv_idx_tx_n32 (829.1) | clk->q 869 / 1014 against 833 | early tap equals depth, but the arc rule gives no credit for it; the taps are beyond T/2 = 416.5 | see 3.3 | S81-RESIGN-DEEP, S81-CORES-2 |

- 32 of the 45 rows (24 types) close with one plan line each and no re-sign: all depths are 205-271, far below 450 - 50.
- UNMEASURED rows that would fail on liberty depth: 437 = gb_hw 216 (567), gb_he 216 (588), mu72_lnland(_nst) 5 (297-299),
  station_t51_native_e 1 (347). The last 6 pass once their type is at 450. The summary's "6" excludes gb_he / gb_hw.

## 2. Evidence for the verdicts

### 2.1 (a) svc_mem tie rows

MEASURED (epyc7 `run/b/B6e/src/rtl/.../svc_rs/`, `fix_ties.py`):
- `u_wq_mem` is AW 3 (6 instances per rs partition), `u_qmem_mem` is AW 4, and inside the module both addresses go through
  `MAW'(...)`, a zero extension to the 5-bit macro address. Zero upper bits are the RTL's own function. The claim is right.
- But the row is `module dsdv_svc_mem_ar, port ra_n | wa, bits 3..5, value 0, types = 16 svc types`. It has no instance key.
  `dsdv_svc_rs.sv:368` instantiates the same module as `u_pbuf_mem` with AW 6, DEPTH 40: there bits 3..5 are live address
  bits (`pk_n[7:2]`, `pb_n`). On `u_qmem_mem` bit 3 is live on `ra_n` (`4'(rc - 1)`) and on `wa` for the non-P2 types.
- `bind.py:1476` `declared_ties.allows(type, module, port, bit, value)` only permits. A real lost connection on pbuf bits 3..5
  or qmem bit 3 in these 16 types would be reported, not failed.
- The rebind was still running at 00:40 (`out/bind_declared_ties.json` is from 11-13), so the counts are not checked yet.

Fix (DIE-S81-92; no LEC needed):
1. Key the rows by instance, or split the bit lists: `u_wq_mem` bits 3..5; `u_qmem_mem` bits 4..5 (plus `wa[3]` on P2 types
   only); nothing for `u_pbuf_mem`.
2. Acceptance on the rebind: per rs partition instance exactly 6 x 2 x 3 + 2 x 2 = 40 declared bits (41 on P2 types), and
   0 declared bits under any `u_pbuf_mem`. Any other count is a real TIED error.
The lane's stated counts (112 x 3 + 16 x 2, "x 14", 200) do not add up to each other; use the rule above.

### 2.2 (b) idx hold pad, CTS forms

MEASURED (epyc9 `s81-resign-deep/idx{A,B}`):
- idxA `5_1_grt.log:506`: `vo[261] -> g_face.vo_f[261]/D slack -321.0 ps needs 9 HB4 > 7`, FF, vclk FF 324.0.
- idxB `:502`: `vo[239]` slack -311.3, vclk FF 275.4.
- CTS skew: idxA setup 188.6 / hold 217.6; idxB 153.4 / 230.2. 11,549 register sinks on `ck_regs`, 10 macro sinks.
- Base: signed insertion 722.7 TT.

Reading: an input-port hold deficit is (flop clock arrival) - (vclk latency) to first order. idxA: 324 + 321 = about 645 ps
FF. idxB: 275 + 311 = about 587 ps FF, which is 722.7 x 0.81 = 585, the signed base depth. INFERENCE from the slack
arithmetic: neither form made the tree shallower. Only the virtual clock moved, and the pad demand is the difference.
With cap 16 the kit adds 9 HB4 (333 ps) on each face input bit and re-signs a core whose measured insertion is still about
720 TT under a 400 / 340 label. The die audit row (829 parent budget, clk->q 1014) does not change.

Fix (S81-RESIGN-DEEP):
1. Put the cap back to 7. The stop is the correct signal ("not contract demand; revise plan/boundary").
2. Gate every re-sign form at CTS, before GRT: pin-register mean on `4_cts.odb` within 40 ps of the vclk value.
   idxA and idxB fail this gate now. Apply the same gate to heA / heB / hwA / hwB.
3. Before a third idx form: one STA read on `idxB/4_cts.odb` giving stages, cell delay and wire delay from `ck` to the
   face registers and to the SRAM clock pins, and what `ck_regs` is (gate or buffer). The config history points at the
   cause: 11.5 k sinks behind one `ck_regs` net, legs to 202 um, 49-52 leaf repeaters added after the balance, balance
   against macro latency ("launch 978 vs macro 640"). `-no_insertion_delay` (idxB) moved 645 -> 587 only.
   If the read confirms it, the form is two taps (face registers / SRAM bank) in the core, not CTS arguments.
   Send the read to Fable before building.

### 2.3 (c) seam hops, t57

- MEASURED from the lane line: 104 seam hops on B6e0; 63 fixed by re-site or +1 station, 2 by re-spacing; 39 left because
  the seam gap is 730-850 um (slice_station t24/t25/t26/t36/t49/t50 to lk_ / iqf) or the slot is an svc type.
  A 730-850 um gap needs 2 stations in a place the slot does not own. "Needs die-level placement" is the right call.
- Open check 1: the B6e G0 named lane `xtier__seqhost__bk_sel` (hop 67, 494 um); the lane reports `xtier__seqhost__s_4N_C`
  (t31) as fixed. Confirm on the G0 of L6f + seam that the 4 named hop errors are gone by lane name, 0 new.
- Open check 2: every appended station is +1 cycle. LATCHECK covers the lane table, but the count-aligned chain now running
  (`b3x2d_ca`) reads the B3x2d latencies. Hand the list of lanes with +1 to DIE-S81-GRT0 so the count-align plan is redone
  on the B6f latencies, not reused.
- t57: +77.76 um takes s_6S_L0 from 0.63 to about 0.595 against 0.60. The margin is 0.005, and the neighbours shift into
  a 146.88 um gap (69 um left). The growth is pre-approved; the proof should be a plain GRT probe of t57 at the new width
  (M2-M7 overflow per layer), not the cut model. If 0.63 routes at 0 overflow in the same probe, skip the growth.
Owner: S81-LEAF-PLAN; die-level 39 hops to DIE-S81-92.

### 2.4 (d) street prototype

- MEASURED: no A/B result exists. First gens failed on a plan/bind mismatch (not the street delta); regens started 00:20;
  `~/cs/run_{base,street}.log` are empty.
- The only numbers are from `core_place route_supply` (cutV 0.89 -> 0.54, core_H 0.995 -> 0.66), run through a wrapper that
  works around two tool bugs (`__pv` types scored with model "none", abutted halves counted as overlaps).
- The prototype widens the N strip (86.4 -> 146.88) and shrinks the mid street (127 -> 114). The second 130-um street and the
  W 60.5 clearance of lever 3 are not in it.
- The col family's blocking failures tonight are clock and hold (2.5), GRT post-route repair time (col_h10_r2: 43,257 s
  in repair, not in routing) and place-stage setup (col_h10_r0_p1 cl911743eb: WNS -1,314.9, 9,418 endpoints). None of these
  is a street failure.
Decision rule (S81-COL-STREET): keep the single A/B. Generalise only if the plain GRT probe shows M6 and total overflow
down by half or more at equal cell count. Until the col clock fix (4.1) is in a kit, a street result cannot be read anyway.
Fix the two core_place bugs in the tool, with tests, before any seed is applied to 216 types.

### 2.5 (e) col_h10_r1 -361

From FABLE-PD-S81-2250 (MEASURED there) plus 1.1:
- Worst path `u_lpad_frame_int_i1.r[1][476] -> r[2][476]`: tree skew 334.6 (clk_t1 262.2 vs clk_t6 596.8 FF), window 186.0,
  margin 31.0, data 190.1. Cross-tap internal: right.
- Over 12,948 endpoints: 7,281 (56 %) are window only, 5,667 (44 %) remain with the window removed, 1,648 are port hold.
- New: the die delivers at most 94 ps on this type's grid ports (kitwin, clk_t1 94, clk 84, clk_t6 75) against 186 planned.
So the label is right for the worst path and incomplete as a class: more than half of the count is the plan window.

## 3. Failure mechanisms (S81, since 11-14 21:00)

| # | mechanism | evidence | root cause | fix | owner |
|---|---|---|---|---|---|
| 3.1 | col clock contract (hold, GRT repair time) | col_h10_r1 hold -361.6 / 12,948; col_h10_r2 GRT timecap 43,257 s in repair; 85 col rows held | tap trees 218-519 ps against 250, taps at the 3,000 cap; windows 179-208 against 165 delivered | B6f: 450, `tap_max_sinks` 1500, pitch 208, flat window 165 (1.1), lane-pad rank taps | DIE-S81-92, S81-COLGEN-1 |
| 3.2 | kp4_dchn boundary arcs (11 rows) | liberty: setup 310 on `k_v[3:0]` only (4 pins), `k_lo` up to 240, others negative; clk->q 450; depth 288.5 | clk->q grows and setup falls by the same amount when insertion moves, so the sum 760 is fixed by the core's input logic on k_v; the audit also pairs worst output with worst input | no kp4A / kp4B. Read the serdes kit STA at `u_chn/k_v*`. Fail: register k_v at the pin (RTL, +1 cycle on 4 bits). Pass: audit exemption | HARD-S81-SERDES-1, PLAN-READERS-1 |
| 3.3 | deep cores idx / bksel_q | depth 829 / 652, early taps beyond T/2 (416.5); idxA / idxB delivered about 645 / 587 FF | tree depth is structural (2.2); bksel_q has no signed record | 2.2 steps 1-3; bksel_q: S81-CORES-2 posts measured depth of the nsesc form at CTS | S81-RESIGN-DEEP, S81-CORES-2 |
| 3.4 | B6 bind | ELAB_RC 2 (3 mem files missing in manifest), then 200 TIED | macro define without files; widest-port binding | file fix is right; tie rows per 2.1 | DIE-S81-92 |
| 3.5 | seam hops over 405 um | G0: 454 / 494 / 540 / 532 um; 104 on B6e0 | last station of a slot too far from the out face; 39 with a 730-850 um die gap | 2.3 | S81-LEAF-PLAN, DIE-S81-92 |
| 3.6 | budget 250 on 24 non-col types | 32 audit rows, depth 205-271 | types outside the override list | 1.2 | DIE-S81-92 |
| 3.7 | leaf GRT no progress | leaf t62: 8.0 h without a non-iteration line at 5_1_grt | ft-slot congestion class (FABLE-LEAF-FTSLOT); not retried, correct | L6f slot rule (279 -> 1 on 17 types) then one t62 GRT probe | S81-LEAF-PLAN |
| 3.8 | flow: `ot_store` import | 113 place fails, all hosts | ot-job installed without ot_store.py / signed_store.py | fixed 00:26 (FLOW-OTSTORE). Left: land both files in the fleet install script | KIT-OPS-5 |
| 3.9 | flow: clients killed, exit 143, orphans | t38, t40, t50, t53, eng__t1 "client lost"; 3 kit_rtl exit 143 | operator stops of hub clients (KIT-OPS-6 r33) and SIGTERM, not kit faults | re-keyed already; no diagnosis needed | KIT-OPS-6 |
| 3.10 | flow: OOM (Error 247 / Killed) | leaf t37, t70, seqhost__t1, lepw_mu_LP__t2 | host memory, not design (INFERENCE: no log read) | measured-peak admission per FABLE-WAVE-REVIEW | KIT-OPS-6 |
| 3.11 | flow: stale or missing views | STALE-CORE-VIEW ot_s81sl_vsw (kv_leaf t4, leaf t26, +1); INFRA-VIEW-MISSING gunit l1f_ba0; WAIT-CHILD t51_native_w | views re-signed or not replicated after the plan moved | replicate the current vsw view; gunit l1f has no kit row (cores 62/64) | KIT-OPS-6, DIE-S81-90 |
| 3.12 | flow: failure text is an advisory | "FAIL INFRA @gen: TAP-RADIUS-TARGET ... radius 200.583/200.0 (advisory)" on 4 items | the classifier reports the last stderr line; an advisory cannot be the cause. The attempt log dirs I opened on intel1 are empty, so the real cause is not known | capture the exit line, not the last line; keep the gen log | KIT-OPS-6 |
| 3.13 | col place setup | col_h10_r0_p1 cl911743eb: WNS -1,314.9, TNS -2.2 us, 9,418 endpoints at place, attempt_30 | not diagnosed (no path read). 30 attempts on one design failure | stop relaunching; one path read after 3.1 is in the kit | DIE-S81-92 |

## 4. Stop list

1. Stop idxA / idxB at GRT; cap back to 7; no third form before the 2.2 read.
2. Stop kp4A / kp4B: the row they target cannot move (3.2).
3. No B6f bind with the module-wide tie rows (2.1).
4. No street generalisation to 216 types before one measured A/B (2.4).
5. No col wave rows released before B6f carries 450 + tap split + the 165 window; STOPLIST-2120 stays.
6. No relaunch of col_h10_r0_p1 cl911743eb (attempt 30) or leaf t62 without a changed plan.
7. Do not copy b3x2d kitwin per-port values onto B6f col types (ports differ); flat 165 until the die rerun.
8. Do not use the 240 / 276 / 702 (core taps included) figures as tap spread.
9. No t57 outline growth before the GRT probe at 0.63 (2.3).

## 5. Not verified

- kitwin absolute values (only their independence from core taps and their distribution).
- idx insertion (inferred from hold slack; no clock-arrival read of `4_cts.odb`).
- The rebind tie counts (bind still running).
- Mechanisms 3.10, 3.12, 3.13 (no log or path read).
- Whether the serdes kit STA passes at `k_v`.
- 2026-11-15 09:35 UTC [S81-RESIGN-DEEP -> FABLE-TRIAGE-S81] RESULT idx_tx_n32 pin-register CK insertion on stopped 4_cts.odb (kit postcts_gate.tcl, placement parasitics, n=853; ps): idxA tt n 853 mean 568.79 min 202.08 max 633.92 bound 400.0; idxA ff n 853 mean 475.44 min 99.63 max 531.54 bound 324.0; idxB tt n 853 mean 543.99 min 190.76 max 607.41 bound 340.0; idxB ff n 853 mean 455.36 min 93.28 max 509.92 bound 275.4;  signed base ref 722.7 TT / 592.8 FF mean (signoff core_latency: TT mean 677 max 817, FF mean 562 max 679). So shallower CTS cut mean only ~110-135 TT / ~90-105 FF vs signed; min 190-200 TT (a few early pin regs) makes spread ~400 TT; hold_est -299..-332 TT. Targets 400/340 not reached (mean 569/544). Evidence epyc9 s81-resign-deep/idx{A,B}/postcts_gate_{tt,ff}.json
