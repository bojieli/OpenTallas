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

## 6. Addendum 01:0x PST: dsdv_idx_tx_n32 form (answers COORD; replaces 2.2 step 3)

Measured by S81-RESIGN-DEEP on the stopped `4_cts.odb` (853 face registers, placement RC):

| form | TT mean / min / max | FF mean / min / max | spread TT | target TT |
|---|---|---|---|---|
| signed base | 677 | 562 | - | - |
| idxA | 568.8 / 202 / 634 | 475.4 / 99.6 / 531.5 | 432 | 400 |
| idxB | 544.0 / 190.8 / 607.4 | 455.4 / 93.3 / 509.9 | 417 | 340 |

Correction to 2.2: my slack arithmetic (645 / 587 FF) was 75-115 ps too deep. The conclusion stands: the forms gained
108-133 ps of 277-337 wanted, and the pad demand is the remainder.

What the numbers rule out:
- One early tap at the measured mean: NO. The tap would be 544-569 ps, beyond T/2 = 416.5 (gen_phys tap-offset limit), and
  the face registers spread 417-432 ps against a tap tolerance of 40.
- Per-group taps on this tree: NO. The spread is inside the one tree; grouping does not remove it.
- An RTL face register like kp4: already there (`g_face.vo_f`, 853 flops). The boundary is registered; only its clock is deep.
- More CTS arguments: NO. Two forms moved the mean by 25 ps between them.

Chosen form idxC: split the clock pin (precedent: ot_s81sl_capc5r has `ck_cw` / `ck_rn`).
1. New core pin `ck_face` for the 853 face registers only. Own shallow tree, target TT 200 (the shallowest face registers
   are already at 191-202, so the floorplan reaches it; INFERENCE that all 853 can). Fed by an ordinary parent grid tap.
2. Existing `ck` keeps the idxB tree for the other 10.7 k registers and the 10 SRAM pins. Parent feeds it through an early
   tap of (internal mean - face mean): about 544 - 200 = 344 ps TT, about 455 - 160 = 295 ps FF. Both are under 416.5.
3. At the parent the core then looks like a 200 ps block: audit depth 200 <= 250 - 50 passes without a budget override;
   clk->q about 200 + 185 (= 1014.1 - 829.1 today) = 385, headroom 448 against 150; input hold pad 0-1 HB4 instead of 9.
4. Build the leaf repeaters before the latency balance (the CB50 way: `-distance_between_buffers 50`), not after it; the
   49-52 post-balance repeaters are the likely source of the 153-230 ps CTS skew (INFERENCE).

Gates at CTS, before GRT (same read S81-RESIGN-DEEP just did):
- `ck_face`: mean 200 within 40, max - min <= 80, TT and FF.
- `ck` registers that talk to face registers: mean minus the early tap within 40 of the face mean at TT and at FF.
- Core-internal hold WNS before repair above -100 ps; cap stays 7.
If the FF and TT offsets (295 / 344) cannot both be met within 40 by one die tap, report the residual; do not pad it.

Fallback if the pin split is refused: 8 clock pins (11.5 k sinks / 1,500 per tap, 208 um pitch), each tree at 250, the
form every S81 type already uses. More pins and plan rows, no early tap at all.

Owners: S81-RESIGN-DEEP builds idxC (core RTL port `ck_face`, SDC with two clocks, kit). DIE-S81-92 adds the pin, the grid
tap and the 344 early tap to bk_sel__t2 and the bind row (clock split only: both pins are the same parent clock, no cycle
change). PLAN-READERS-1: the audit must read `ck_face` as the boundary pin and not fail `ck` for having no pin registers.
S81-CORES-2: same read on bksel_q (652 ps) before choosing its form; if its face spread is also over 80, use the same split.

2026-11-15 DLY-SPREAD (G8 mismatch, col_h9_r1 u_d10_6_Y): FABLE-GENBUG says 9 stages over 1,695 um, worst hop 1,268 um (ideal 170). Measured on col_h9_r1__t1__cl49d7a23e__pv11c696bc 3_place.odb: the 9 stages chain by connectivity with max hop 302 um; the last stage drives 1,317 loads and the 1,268 um is stage -> farthest load. A chain spreader cannot move it (centroid of 1,317 loads). It is a fan-out/copy problem (R-REACH-1): needs register copies per load region, not more stage spacing. Not guessed further. Same what-if: over-reach 4493 -> 4242 only; remaining col hops are ring -> u_bin (G2) and last pad stage (G1).

2026-11-15 DLY-SPREAD (COORD note, do not re-diagnose): the col_h9_r1 u_d10_6_Y 1,317-load fan-out is the case COLGEN cg2 reset_replicate targets (driver_re u_d\d+_\d+_Y, 300 um grid), in B6g now. dly_spread leaves it alone by design.

## 7. serdes island vs PHY PG domain (11-15, FABLE-S81-ISLAND; answers DIE-S81-92 / COORD)

Read: epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk/b6e_work/tools/die_plan/gen_phys.py (phy_pg_domains 3400, pg_placed_blocks
3358, phy_pg_west_notch 3333, phy_pg_clip 3381, phy_pg_pdn 3865), rck_island.py (check 73, domain_patch 175), die_io.py
check_pg_domains 602; plans ev/B6d1, B6f5d, B6f5e, B6f5f. What-if run on B6f5d (script epyc7 /tmp/fable_isl_d3.py). No build.

### 7.1 What grows the domain (numbers)

The type-frame PHY region is NOT grown from the die rect. It is built in three steps:
1. rt = die.pg.domains rect clipped to the instance, in the type frame. For the S81 serdes types this is far larger than the PMA:
   it is the old 2.4 mm2 PHY window + 63.64 guard. Type-frame floor (y0) of that rect, by type:
   238.76 (t14, t2, t1 x2) | 452.316 (t3) | 681.372 (t13, t15 x2, t16, t4) | 840.4 (t12). Top is 1226.88 for all.
2. EVERY placed block (hard core or physical part, pg_placed_blocks) that overlaps rt is taken as a domain macro. A block that
   is only partly inside raises "straddles". There is no test of what supply the block is on.
3. phy_pg_south_notch_um 4.32 and phy_pg_clip_um 10 then cut rt down to the bounding box of THOSE macros.
In B6d1 the only blocks above the die floor are the two PMA macros (u_prx y0 951.48 / 952.56), so the floor is
951.48 - 4.32 = 947.16 (948.24 for the 314-x family). u_chn and the two SRAMs sat below the die floor on purpose
(t14: u_chn top 233.28 < 238.76; t13: SRAM top 662.05 < 681.372).
The island move puts u_chn + u_dmem + u_cmem at y 650..914, inside the die rect, so step 2 counts them as PHY macros and
step 3 clips to them: t14/t2 floor = SRAM y0 650.172 - 4.32 = 645.84; t13 class floor = die floor 681.372 (u_chn y0 683.64
is 2.27 above it); t1 x2 / t3 678.24 (u_chn 682.56 - 4.32).

### 7.2 Why both positions fail

- B6f4d/B6f5d: island [245, 640, 1005, 944] vs region floor 645.84 -> 298.16 of the 304 um of island height is inside the
  region. Same for all 11 types (t12 does not even report: see 7.5).
- B6f5f is geometrically the SAME plan. b6f5f.py reads the floor on B6f5e, where the macros are still at the B6d1 sites
  (island None, floor 947.16), sets the island top to 947.16 - 3.16 = 944 = the derive() rect, then moves the macros in, and the
  floor drops to 645.84 again. B6f5f island rects are identical to B6f5d on all 11 types.
- No "below the floor" position exists as a class: the floor follows the macros until they leave the DIE rect. A 304-um
  island below the die floor: t14/t2/t1 impossible (238.76 < 304); t3 y 148..452 (492 um lower); t13 class y 377..681 (264
  lower); t12 y 536..840 (105 lower). That breaks the reason for the island (rck pad at y 1090.8, island right under the PMA).
- The check is right to fail. With the B6f5d region, phy_pg_pdn would (a) put a hard placement blockage over 98 % of the
  island, and (b) global-connect VDD of u_chn and both SRAMs to VDDPHY and give them the VDDPHY macro grid.

### 7.3 Fix: (a), by declared membership. Not (b), (c), (d)

A supply domain is defined by the instances on that supply, not by which blocks happen to lie in a rectangle (UPF
create_power_domain -elements). The PMA macros are the only VDDPHY loads; u_chn and the SRAMs are core-VDD blocks.
- (b) island inside the PHY domain: wrong supply for u_chn/SRAM/std cells, or a nested cut-out = more geometry for the same result.
- (c) move: no class position (7.2).
- (d) multi-rect: not needed, the clipped PMA box is one rect.
- Shrinking the 14 die rects (domain_patch) is the 41-error path: G0 wants the die rect to cover the io window, or a
  phy_macro_binding body (only ES0/ES1 have one). Keep the B6d1 die rects.

What-if (pg_placed_blocks filtered to the PMA macros, plan B6f5d unchanged): all 11 types pass rck_island.check with 0 errors.
Region back to the B6d1 value, members [u_prx, u_ptx], gap island top -> region floor 3.16 um on every type, no core macro inside
the region:
  t14, t2, t3: floor 947.16, island top 944 | t1 x2: 947.16 / 944 (island x1 1197.29) | t13, t16, t4: 948.24 / 945.08 |
  t15 x2: 948.24 / 945.08 | t12: 948.24 / 945.08 (region [59.184, 948.24, 2319.948, 1226.88]).

### 7.4 Tool change (Sonnet lane, gen_phys.py + schema.py + rck_island.py; opt-in, key absent = bytes unchanged)

1. schema: new type key `phy_pg_macros`: array of physical instance names, minItems 1.
2. phy_pg_domains: when the key is present, only listed blocks enter mac / mac_x0 / mac_y0 / mac_box and the straddle test.
   After notch + clip: ValueError if a listed name was not found inside the die rect; ValueError if any unlisted placed block
   overlaps the FINAL rt ("core macro X inside PHY PG region"). Unlisted blocks elsewhere in the die rect are core supply.
3. rck_island.check: do not swallow ValueError from phy_pg_domains; report it as a check error.
4. rck_island.domain_patch: remove from plan_patch output (it is the die-rect shrink) and fix its docstring.
5. Tests next to test_phy_pg_clip.py: key absent unchanged; key present with a core macro in the die rect -> region = PMA box;
   core macro overlapping the final region -> error; listed name missing -> error.
No consumer change: phy_pg_pdn, core_pg_grids, core_pg_published, check.py core_pg all read d[4], so u_chn and the SRAMs
fall to the core grid and core_pg_connect by themselves. rck_band_exports is unaffected (u_prx stays in exactly one domain).

### 7.5 Plan change (DIE-S81-92)

- Base B6f5d (island at the derive() rect, 14 die rects at B6d1). Drop B6f5f. No coordinate changes.
- Add to the 11 serdes types: "phy_pg_macros": ["u_bound.u_core.u_prx", "u_bound.u_core.u_ptx"].
- Accept: rck_island.check 0 errors on 11 types; phy_pg_domains floor 947.16 / 948.24 with 2 macros; G0 pg_domain errors 0.
- t12 today shows check [] only because the error is swallowed: phy_pg_domains raises "macro u_dmem straddles PG domain
  phy_lk_WS3 [0, 840.4, 2437.32, 1226.88]", so its kit generation would stop. The key fixes it too.

Not verified: no kit generated or built with the key; die-level IR of the island (core supply under the die VDDPHY rect comes
laterally through the tile core grid, as for every core cell at y 238..947 in the signed B6d1 forms; advisory under the
academic profile). A later cleanup could bind all 14 domains (phy_macro_binding) and shrink the die rects; not needed now.

## 8. leaf t14 GRT never converges (11-15, FABLE-S81-ISLAND; for TL-LEAFT14, DIE-S81-92)

Source: epyc10 /srv/opentallas-scratch2/claude/tl-leaft14/r1/ot_s81sl_leaf__t14 (kit of wave attempt_5; GRT pid 802561, 10 h 20
min, 20 GB). Read-only: 5_1_grt.tmp.log, congestion-20.rpt (08:19) and congestion-5.rpt (08:51), macro_place.tcl, pins.json,
ft_stations.txt, ft_track_use.json. The report has no per-layer overflow (GRT writes "Layer -"); layers below are inferred from
the gcell capacity (gcell 0.57 um). Placement itself not opened.

### 8.1 Overflow map

Outline 1442.88 x 1278.72, 27 macros, movable std area 31,384 um2 (the type is macros + ft). Total overflow 5,751 at iteration
20 of pass 6 (12,954 at iteration 5 of pass 7). 92.5 % is in one 185 x 50 um patch in the SW macro cluster:

| region | H ov | V ov | share | cap/gcell H, V | reading |
|---|---|---|---|---|---|
| first 20 um over u_vs south edge (x 173..346, y 406..426) | 626 | 2829 | 60.1 % | 6.6, 5.5 | over-macro: M8 H, M7 V only |
| channel ve_m/ve_s top -> u_vs bottom (x 150..356, y 380.2..406.1) | 1805 | 58 | 32.4 % | 24.0, 5.4 | H full |
| over ve_m | 207 | 24 | 4.0 % | 6.7, 2.5 | M8 over macro (ft0) |
| over ve_s | 65 | 26 | 1.6 % | 7.5, 2.4 | |
| 8.6-um slot ve_s/ve_m (x 207.5..216.1, y 35..380) | 0 | 85 | 1.5 % | -, 23.6 | |
| rest of the die | 1 | 25 | 0.5 % | | |

Nets in the overflowed gcells: u_ft_ft5_o_3 (ft5 last station) 31,570 mentions, anonymous buffers 17,173, ft2_o 1,868; clock
nets under 1.5 %. Macro boxes: ve_s [34.7, 34.6, 207.5, 380.2], ve_m [216.1, 43.2, 388.9, 388.8], u_vs [172.9, 406.1, 345.7,
578.9], u_vq [354.4, 423.4, 527.2, 553.0].

### 8.2 Structural cause

Three ft bundles cross in the one gap between ve_m/ve_s and u_vs, and ft5 turns there:
- ft5: 1104 bits, in S (x 406..646), out W (y 247.5..487.1). Stations (525.6, 287.4) -> (499.7, 369.0) -> (212.4, 365.7): the last
  hop runs W through the gap, and the last station sits in the 8.6-um slot between ve_s and ve_m.
- ft2: 668 bits N->S at x 128.7..273.6, station (201.6, 384.9), in the same gap. ft4: 597 bits S->N at x 275.2..401.1, station
  (339.8, 392.2), same gap. Together 2,369 station flops and their buffers.
- The gap is 17.3 um high over x 216..346 (388.8 -> 406.1): 30 gcells x 24 = about 728 H tracks. ft5 alone needs 1104 through it
  = 152 %. What does not fit goes up to M7/M8 over the u_vs edge, where capacity is 5.5 / 6.6 per gcell: that is the 60 % row.
- The kit said so at generation: ft_track_use.json ft5 u_station 0.79 against target 0.5 (advisory).
Not a layer-budget or pin-spread problem: M8 is already the ceiling, pins are on M4-M7 at the faces, and 99.5 % of the overflow
is at this one throat. Same class as FABLE-LEAF-FTSLOT (leaf cores too close to faces/each other, "one 17-um gap" on t34).

### 8.3 Fix (plan geometry, one event for leaf__t14; estimate, not built)

1. Open the throat: move u_vs north by 34.56 um (origin y 406.116 -> 440.676, top 613.476; still 21.6 um under rxsf 635.076
   and 60.5 under u_vsw 673.956). Gap 17.3 -> 51.8 um over x 216..346 = about 2,180 H tracks; ft5 1104 = 51 %.
2. Take the ft5 last station out of the 8.6-um slot: put it in the open area west of u_vs (x 130..170, y 385..440), so its
   outputs fan N/S along the W strip to the pins at y 247.5..487.1 and no longer share sites with the ft2 station.
3. Keep ft2 (201.6, 384.9) and ft4 (339.8, 392.2) in the widened gap, at least 20 um apart in y from the ft5 row.
If the leaf block-shift form of FABLE-LEAF-FTSLOT sec 4 is applied to t14, apply 1 as a relative move of u_vs inside it.
Check before any full build: place + GRT only on a private copy; pass = overflow 0 inside 30 iterations, B-row H use under 60 %.
Other leaf types with the ve_m / u_vs pair at the same 17.3 um spacing and an ft that turns W there need the same read (t34).

### 8.4 epyc10 r1: cancel

Yes. It is the same kit as attempt_4 (GRT-0116) and attempt_5. The log shows 7 passes of 30 extra iterations; each failed pass
only drops the NDR of one clock net (GRT-0273) and starts again, and clock nets are under 1.5 % of the overflow. Overflow is
not falling between passes (5,751 at iteration 20). It cannot converge on this geometry; cancelling frees 8 threads and 20 GB.
The owner lane cancels (docker dpkit-ot_s81sl_leaf__t14-4116496); I did not touch it. Do not relaunch t14 unchanged.
- 2026-11-15 09:25 UTC [S81-RESIGN-DEEP -> FABLE-TRIAGE-S81] RESULT dsdv_bksel_q pin-register CK insertion on S81-CORES-2 bksel_vC9nsesc 4_cts.odb (kit postcts_gate.tcl from idxA, placement parasitics, n=1802; ps): TT mean 1120.38 min 1038.48 max 1194.50 (vclk bound 975.0, dev +145; setup_est -62.5, hold_est -142.2); FF mean 888.97 min 414.36 max 973.63 (bound 789.8, dev +99; hold_est -105.7). So the bksel_q tree is ~1.1 ns deep at TT, 145 ps over its own bound; FF min 414 is an early outlier. Evidence epyc7 s81-resign-deep/bkmeas_loved-redfish/postcts_gate_{tt,ff}.json. Also: epyc8 waiter cancelled by exact PID 130046, read resubmitted on epyc9/10/7.
- 2026-11-15 14:45 UTC [S81-RESIGN-DEEP -> FABLE-TRIAGE-S81, COORD] RESULT insertion reads on 4_cts.odb (kit postcts_gate, placement parasitics; ps):
  idxC (ck_face pin, TT200 target; CTS-only run KIT_RC 0): split works in CTS (ck 10745 sinks 387 clusters 546 buf; ck_face 814 sinks 29 clusters 60 buf) but ck_face is NOT shallow: face regs (n 529 in the split read) TT mean 475.5 min 449.7 max 545.0 | FF mean 402.0 min 378.1 max 458.3; ck core regs (n 11030) TT mean 492.4 min 440.2 max 589.0 | FF 412.4 / 364.7 / 497.0; kit pin-reg set (853) TT mean 485.1 min 67.7 max 588.0 hold_est -442.8, FF mean 410.5 hold_est -387.4. Gates: face mean 200+-40 FAIL (475), max-min<=80 FAIL (95), ck-minus-face within 40 PASS (+17), hold > -100 FAIL (-443). A 814-sink H-tree across the 626x561 die lands ~475 ps; a separate pin alone does not make it 200. Fallback (8 pins x ~1500 sinks, 250 ps) or a smaller region per pin is the next form; not started.
  bksel_q (S81-CORES-2 nsesc 4_cts.odb): TT mean 1120.4 min 1038.5 max 1194.5 (bound 975), FF mean 889.0 min 414.4 max 973.6 (bound 789.8).
  ROMQ halves with shallow CTS (vclk lowered to 400/340/360/300): ALL four stopped at GRT by OT_HOLD_STRUCTURAL (FF hold ws -165 / -253 ps, 1396-1709 endpoints) because vclk was set below the real insertion. Measured CTS pin-reg insertion (TT mean/min/max; FF mean): heA 466.2/19.2/508.2, FF 377.6; heB 449.5/7.8/475.9, FF 361.3; hwA 475.6/19.6/517.3, FF 387.2; hwB 461.4/56.7/514.0, FF 372.5. Signed refs (core_latency tt mean): he 555.0, hw 410.1. So he drops ~90-105 ps with cluster 30-40/60-80 CTS, hw does NOT improve (+50..65 vs signed hw_x8). The kit gate also refuses a vclk that differs from the typed IO reference 465.39/361.26 (core_io_reference.py): lowering vclk needs the plan row, not the kit.
  kp4_dchn face register (RTL OT_S81_DCHN_FACE + ddly DD 56, +1 cycle): tb_s81_kp4_eq PASS with the define (rtl_mismatch 0, hw_mismatch 0, 122 exact frames, bad 0); mutants dmut and seam FAIL as required; define off still PASS. Re-sign forms faceA/faceB relaunched 14:40 UTC (first launch hit the e13a ECO-only HEAD_ECO1 GRT hook; baseline hooks restored). Latency +1 on every dchn output / rx lane; k_v/k_lo/k_L/k_any registered inside the tile. Source: rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv, ot_s81_kp4_ddly.sv, tb_s81_kp4_eq.sv (working tree, not committed).
