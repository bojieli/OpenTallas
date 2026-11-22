# FABLE-CLOSURE 2026-11-22 02:35 PST: col is 214 of the 439 unsigned types and its first zero-overflow GRT landed at 02:20; leaf, KV hg/hgi and KV pv are each stuck on one structural item their owner lane is not fixing

Reviewer: Fable (FABLE-CLOSURE review for COORD). Read-only: nothing launched, cancelled, patched or deleted. Follows `FABLE-CLOSURE-STRATEGY.md` (23:25); its levers and stop list stand unless a line here changes them.
Count 01:57: 548 any / 438 current. S81 46/394, HEAD 25/26, QC 61/127, KV 6/56. HBM parked.
Gate: DRC 0, TT >= -42 ps, internal FF hold >= 0, bind + latency, LEC. No die or outline growth.
Marking: **V** = I read it this round from the named file. **R** = reported by a lane post (23:10 to 02:27). **I** = my inference. **P** = proposal.
Sources: OWNERS-SWEEP 02:26, RELEASE_TREE failure breakdown 02:21, CLASS-SWEEP-1122, FIX-SYNC-{S81,QC,KV,HEAD}, NEARMISS, 81 lanes' posts.

## 1. Families ranked by types unlocked per hour to sign-off

Hours are my estimate (I) to the first counted sign-offs of the family, on the route the owner lane is on now.

| # | Die | Family | Unsigned | Owner lane(s) | Route to sign-off | Hours | Types/h |
|---|---|---|---|---|---|---|---|
| 1 | S81 | col (h9_r0 60, h9_r1 60, h9_r2 58, h10 36) | 214 | OPUS-FIX-S81-COLROM-R6, FAM-S81-COL-H9R0-R4, FAM-S81-COL-H10-R4 | J8 cut 16:00, then wave | ~30 | ~7 |
| 2 | S81 | leaf + kv_leaf | 80 | OPUS-FIX-S81-LEAF-R10 | J8, then wave | ~30 | ~2.7 |
| 3 | QC | cb (cbn 8, cbf 6, cbx 3) | 17 | FAM-QC-CB-R4 | V3 06:00, kits | ~18 | ~0.9 |
| 4 | KV | hg / hgi | 19 | OPUS-FIX-KV-HGI-R6 | D28 12:00, kits held on lockup | ~24+ | <=0.8 |
| 5 | S81 | svc (hi 8, lo 8) | 16 | OPUS-FIX-S81-SVC-R9 | J8, then wave | ~30 | ~0.5 |
| 6 | KV | pv | 16 | OPUS-FIX-KV-PV-R7 | v3 in D28, 15 types D29 | ~40 | ~0.4 |
| 7 | S81 | dsdv C / LP slices | ~17 | FAM-S81-LEPE-4, FAM-S81-DSDV-R1, FAM-S81-SLICE-R6 | XMID form, J8 / J9 | ~36 | ~0.5 |
| 8 | QC | st_a / st_b | 14 | QC-PLAN-R13, FAM-QC-HCST-R3 | V3 / V4 | ~24 | ~0.6 |
| 9 | S81 | serdes | 11 | FAM-S81-SERDES-R7 / R8 | private sign-off + J8 | ~12-30 | ~0.5 |
| 10 | KV | pc | 6 | KV-WAITBIND-R1, FAM-KV-IOPC-R4 | pc_v1 D28; pc_v3 pcreg D29 | ~24-40 | ~0.2 |

Not families, but the nearest counts: about 30 QC types are already running on the V2 wave; four QC near-miss types (sle_fw_v2 x2, sle_su_l1, slw_fw_v1) sit at TT -47 to -78 with ECO exhausted and need one stage row each in V4 (NEARMISS); HEAD's last type hd_lep0N is in place on r18e (V 02:30).

## 2. Top 6: blocker, owner lever, missing lever

### 2.1 S81 col (214)
- Blocker (V, final `5_1_grt.log` of six representative kits): every one ends GRT-0116, at only 6.6 to 14.9 % total usage, so the overflow is local, not a density limit.

| Kit (host) | Overflow | Hotspot (100 um bin) | Nets in the hotspot |
|---|---|---|---|
| col_h10_r1 base / D / E (epyc9) | 2370 / 1725 / 2039 | (500-600, 0) | `u_lpad_frame_int_i1.r[1..3]`, `frame_int_i1_q`, `u_ist_frame_int_o1_1` |
| col_h9_r0_p2 keep / STAGGER (epyc8) | 944 / 829 | (1100, 900) | `u_lpl_9_w.q`, `rt_7b_0.o`, `u_ist_frame_int_o0_0` |
| col_h9_r0_p3 (epyc8) | 1784 | (1300-1400, 600) | `xo_i0_b`, `u_bin_xo_i0`, `u_lpad_xo_i0.q`, `cland_xo_i0` |
| col_h9_r0_p6 (epyc8) | 394 | (800, 1100) | `u_ist_frame_int_o0_2` |
| col_h10_r0_p4 (epyc7) | 2475 | (1200, 300) and (1300, 800) | `xb_1_0.i`, `rt_2b_1.o`, `payload_i_0`; `frame_int_o0_is0_q` |
| col_h10_r2 pv1619ecc6 (epyc7) | 154 | (800, 1000) | unnamed buffer nets |

- It is one class (I, from the table plus R COLROM-R6 01:21): wide boundary registers (lpad pad ranks, ist stations, bin / cland rings of 1,000 to 1,264 bits) whose plan seat keys cover only sample bits, so the rank piles up at one point. COLROM-R6 measured it on col_h10_r1: 5 keys per 1,264-bit rank, 6,300 flops at y < 100.
- New this round (V, epyc9 `OPUS-FIX-S81-COLROM-R6/col_h10_r1__t1__cld01bb4ae_1121231740`, `5_1_grt.tmp.log` line 238): **kit H reached overflow 0 / 0 / 0 at extra iteration 16 of 50**, usage 11.82 %, and is in post-GRT repair. It is the first col kit with zero overflow. No GRT timing yet; CTS post-hook setup was +19.20 (R, pre-repair). Kit F (per-flop planD seats + south seats) still has 42 boxes at iteration 38 (V).
- Owner lever: right for col_h10_r1 (south seats + kit E `OT_RELAY_MID_RE` + 50 iterations). Not yet right for the family: kit C and kit G carry keep + STAGGER + the env row but no rank seats for `xo_i0`, `frame_int_o0` or `lpl_9_w`, and the earlier keep and STAGGER kits left 829 to 944 on exactly those nets.
- Fastest missing lever (P):
  1. A rank-level seat key in the tools (seat every bit of a keyed rank along its rank line, spread over y), in place of per-bit plan rows per type. One tool change covers all 11 col sub-forms; per-type hand kits cost 3 h each to a GRT read.
  2. `OT_GRT_CONG_ITERS=50` as the col item_env default: H cleared at iteration 16; the 10-iteration kits all stopped at GRT-0116.
  3. Do not wait for the J8 wave to count. Under the COORD 01:16 ruling, launch the 11 col_h10_r1 siblings on kit H's private form as soon as H's `5_1_grt.odb` reads TT >= -42 and FF hold >= 0.

### 2.2 S81 leaf + kv_leaf (80)
- Blocker (V, epyc7 `private/FABLE-FIX-S81-LEAF-R8/ot_s81sl_leaf__t39_1121220439`, `5_1_grt.tmp.log`):
  - GRT attempt 1 ended with overflow 983 after 10 iterations (usage 7.95 %); the residual retry then let the flow continue.
  - GRT hold repair found **4,033 hold endpoints**, start ws -55.98, TNS -96,282 at margin 30. The endpoints are `u_bound.u_bin_leafdn_i0/q[*]/D`, the boundary input register of the leafdn bus, with input ports excluded (`OT_GRT_NONPORT`). After 90 iterations it has added 177 buffers and ws is -67.4. At that rate it will hit the 3 h hold cap, not close.
  - Setup at CTS post-hook was -153.84 on recovery paths from `u_lpad_leafdn_i0.q[594]` to reset relay flops, launch clock 453.6 ps against capture 388 to 393 ps. That slack is pre-repair; I use it only to name the path: a reset bit riding the pad chain on a tap about 60 ps later than its sinks.
- Root cause (I): the leafdn pad chain and its bin register sit on different clock taps, so a zero-logic register hand-off of about 600 bits x several ranks fails hold. This is the tap-skew class, which the owner rule fixes by structure, not padding.
- Owner lever: LEAF-R10's J8 rows (re-grid plan d, raw-reset plan e, respace) fix G0, reach and reset hops. They are needed, but none of them puts lpad and bin on one tap or moves the reset bit, so the 75 leaf kits would launch on J8 into the same 4,033-endpoint hold stall (I).
- Fastest missing lever (P): a clock row per leaf type that puts each lpad last rank and its `u_bin_*` register on the same tap (or a launch-side lockup on the lpad last rank), plus 50 GRT iterations, added to plan e before the 14:00 row deadline. Read the launch/capture taps from t39's `5_1_grt.odb` first.

### 2.3 QC cb (17)
- Blocker (R FAM-QC-CB-R4 00:10 / 00:31, CLASS-SWEEP class A): setup into the NK core `tap[0]` pin. V2 routes were flat at -160 / -200 ps in pre-GRT repair and were cancelled. With row A the latch endpoints leave the worst list; what remains is 3 x HB4 (212 ps) ahead of a pin whose window is [16, 440] ps, giving -105, and a lockup latch on a late tap, -90. Internal FF hold closes after pre-GRT repair (+45).
- V 02:30: the ctsfam2 kit (row A + `tap[0]` = 1) is in `3_4_place_resized` on epyc10; `OT_NK_CHAIN` moved the chain hops from max 727 um to 396 um. No CTS or GRT read yet.
- Owner lever: right (row A, rev5 `tap[0]` 3 -> 1, row D tap balance).
- Missing (P): only delivery. rev5 must ride the V3 candidate that ships at 06:00 (d5r), or 17 types wait for V4. If d5r is not clean at 05:40, CB-R4 should sign the cb kits from its private ctsfam plan (COORD 01:16 ruling) and not wait for V4.

### 2.4 KV hg / hgi (19)
- Blocker (R OPUS-FIX-KV-HGI-R6 02:23): the fresh empty-dir strict bind R6h is clean (G0 PASS, bind errors 0, LATCHECK 0), but `lockup_regions` is **inert in real binds**: every hg / hgi type still has a 40-load "rest" region and no NK lockup latch is mapped to its core, while the lane's debug-harness bind produced 18 regions. That is a flow defect in the bind / emit path, not a row defect. Kits stay held.
- Second blocker (R): GRT-0273 in the centre channel; the re-site rows (ectl landing, krsp bank) are in the D28 package.
- Owner lever: the rows are right and handed off for D28. The lane is now debugging the tool alone, with 19 types held behind it and no placed proof that the re-site rows clear GRT-0273.
- Missing (P): split the work. One lane fixes the inert `lockup_regions` path (diff the debug-harness call against the real bind call: which stage drops the key). In parallel, launch one hg and one hgi private kit to GRT on R6h to prove the re-site rows; hold margin is then read with the lockup fix, not guessed.

### 2.5 S81 svc (16)
- Blocker (R OPUS-FIX-S81-SVC-R9 02:21): bind only. The J8 split pieces had 203 bind errors and are down to 1, which belongs to LEPE (the `u_bout_unit_o0.d` relay_depth row; LEPE-4 answered 02:25 that it drops from J8). The final private gate is still in bind. No physical blocker is on record: three split layouts passed full stock split runs (R, R8).
- Owner lever: right.
- Missing (P): SVC-R9 holds all 16 rows for the J8 wave. When its private gate is green, launch the six split pieces as signable private kits from that bind. That saves the J8 apply plus wave queue, roughly 8 to 12 h.

### 2.6 KV pv (16)
- Blocker (R OPUS-FIX-KV-PV-R7 00:32 / 01:21 / 01:29): clock tap load. After the split, taps carry 4,670 to 5,800 sinks against a cap of 1,000, and moving the cut (x 993.6, 1028.16, 1123.2) or insetting the cut-face bank by 25.92 um does not help. The residual is a register cluster at the cut corner (x 1042-1107, y 30-150; 11,277 sinks in 111 bins) with no legal tap site. Only v3 closes (+3 taps) and goes to D28; 15 types stay unsplit.
- Owner lever: partly right. Cut-line tuning is measured dead. The next step it names (a `place_regions` row at util ~0.5 on the soft group owning the cluster) attacks the right object, but the 11-05 placed DB is gone, so it is attributing the cluster from RTL.
- Missing (P): spread the sinks, not the taps. Either seat the cluster's registers on a rank grid (same form as the col rank seats, 2.1) so no 10.8 um bin holds more than about 100 sinks, or add tap sites inside the cluster by opening the keep-out with a core move (cores move, never re-shape). One fresh v6n place is needed for the census; nothing else in the fleet has it.

## 3. Fable fix lanes (P)

| Lane | Family | Pairs with | Types |
|---|---|---|---|
| FABLE-FIX-S81-COL-RANKSEAT | S81 col | COLROM-R6, COL-H9R0-R4, COL-H10-R4 | 214 |
| FABLE-FIX-S81-LEAF-TAPHOLD | S81 leaf | LEAF-R10 | 80 |
| FABLE-FIX-KV-LOCKUP-INERT | KV hg / hgi | KV-HGI-R6, KV-PLAN-R6 | 19 |
| FABLE-FIX-KV-PV-SINKSPREAD | KV pv | KV-PV-R7 | 15 |

**FABLE-FIX-S81-COL-RANKSEAT.** Goal: one tools change that seats whole wide-register ranks, so every col sub-form reaches GRT overflow 0 without per-type hand seats. Start from the six failed `congestion.rpt` files in section 2.1 and the owners' existing `4_cts.odb` files; census which keyed ranks (lpad, ist, bin, cland, lpl) have fewer seat keys than bits, on all 11 sub-forms. Implement a rank-level key match (all bits of a keyed rank seated on the rank line, spread in y, FIRM) with a test, push to main, and write the J8 col rows that use it. Pairs with OPUS-FIX-S81-COLROM-R6, which keeps kits H / P / P2 / G on col_h10_r1 and files nothing separately, with FAM-S81-COL-H9R0-R4 (kit C, files the combined J8 col set by 14:00) and FAM-S81-COL-H10-R4 (E15E-CHAN row, proof A2). Build only for sub-forms that have no proof with seats in flight: col_h9_r0_p3 (`xo_i0`), col_h9_r0_p6 and col_h10_r0_p4 (`frame_int_o0`). Do not rebuild col_h10_r1 or col_h9_r0_p2.

**FABLE-FIX-S81-LEAF-TAPHOLD.** Goal: remove the 4,033-endpoint `u_bin_leafdn_i0` hold class and the late reset bit on the leafdn pad chain by structure, for 75 leaf types. Read launch and capture taps from the t39 `5_1_grt.odb` (epyc7, kit of FABLE-FIX-S81-LEAF-R8, now watched by LEAF-R10); confirm whether the launch is the lpad last rank or the cland ring. Write a per-type clock row (shared tap for the lpad last rank and its bin register, or launch-side lockup) and move the reset bit's relay to a tap matching its sinks; gate it with plan_gate_pre on plan e. Pairs with OPUS-FIX-S81-LEAF-R10, which keeps plan d / e, the respace and the t39 kit, and merges the tap row into the J8 leaf delta. One new proof kit only: t39 on plan e + the tap row, 50 GRT iterations. The two 21 h and 27 h t39 GRT jobs of the LOCKUP-STATION lanes (section 4) are not this proof.

**FABLE-FIX-KV-LOCKUP-INERT.** Goal: make `lockup_regions` take effect in a real strict bind, so 19 hg / hgi kits can be released. Diff the HGI-R6 debug-harness bind (18 regions) against fresh27h (11 + rest, 40 loads) stage by stage: plan key read, region-to-core mapping, emit. Fix on main with a test that fails on the inert case, then re-bind R6h once and show the regions in bound text. Pairs with OPUS-FIX-KV-HGI-R6, which keeps the rows, the D28 package and the two proof kits of section 2.4, and with KV-PLAN-R6 for the D28 / D29 slot. Fable runs no kit; its only job is one bind.

**FABLE-FIX-KV-PV-SINKSPREAD.** Goal: a pv form in which no tap exceeds the cap on the 15 unsplit types, for D29. Get one fresh v6n place (the only build), census the cut-corner cluster by owner module, then write either rank seats for it (reusing the RANKSEAT key) or a core move that opens legal tap sites, and run the tap load report plus plan_gate_pre. Pairs with OPUS-FIX-KV-PV-R7, which keeps row 1 (v3 split) and the D28 hand-off and stops its own D29 cut-line and bank-offset trials (measured dead). Start this lane last: it unlocks the fewest types per hour.

No Fable lane for QC cb or S81 svc: the owner levers are right and what is missing is delivery (sections 2.3, 2.5).

## 4. For COORD, outside the ranking

- Two old leaf t39 GRT jobs on epyc7 have run 27.4 h and 21.3 h at about 20 GB each and are at extra iteration 15 of 30 (V 02:29): `lockup-station-1130-meas/proof2` (pid 278006) and `lockup-station-r2/proof6_t39` (pid 338136). I did not touch them. They are for LOCKUP-STATION-R3 to justify or cancel under the >3 h rule.
- KV hroot variant A (V, epyc10): GRT hold guard ended with 0 violators (ws +37.89), TT post-hook -39.04; detailed route is at 84,228 violations at 20 % of iteration 0. Judge on DRT convergence (strip density class KV-C14).
- J8 respace: do not apply the J7 ledger to the 75 leaf types (R LEAF-R10 02:18); respace after composing.

## 5. Not checked

- Kit H timing after GRT repair, and kit C / G / P / P2 at any routed stage.
- Which flops launch the leaf `u_bin_leafdn_i0` hold paths: no STA was run; the tap-skew cause is inferred from the endpoint names and the CTS path clocks.
- KV hg / hgi, pv and S81 svc blockers are from lane posts only; I opened no DB for them.
- QC cb at CTS or GRT on row A + rev5 (kit still in place).
- Hours in section 1 are estimates, not measured queue times.
