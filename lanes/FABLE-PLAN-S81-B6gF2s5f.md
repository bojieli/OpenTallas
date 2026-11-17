# FABLE-PLAN-S81-B6gF2s5f: structural review of S81 plan event B6gF2s5f, 2026-11-16 20:5x PST

Read-only review, in parallel with the bind (owner S81-DIE-R2). MEASURED = my own diff / geometry run on epyc10 (python3 -I).
Event plan: epyc10 `/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s5f.json` sha c20ec9e4c3c4 (= E/cand/plan_C3.json),
sidecar `ev/B6gF2s5f_sidecar.json` 98aa35e5a944. Base: adopted 819037bbe371 (`run/b/B6gF2s4tapfix1/src/physical/die_plan/s81/plan_h2_2249.json`)
and its `sidecar_new.json`. There is no compose receipt: s5f is a row delta on the composed 819 plan, not a recompose.

## Verdict

**GO for the bind. No blocking finding (none has a failing measured number).**
B6gF2s5f carries 5 of the 9 listed items. The clock / CA items are not in it and must not be reported as landed.

## 1. Does every intended row land? (plan diff: 2,826 leaf differences, all in 4 types + 2 lanes + the lockup list)

| Item | In s5f | Measured |
|---|---|---|
| gunit bf signed shape | YES | 4 bf cores 432x172.8 -> 432x216, LEF + pins = `dsdv_gunit_l1f_bf_signed_1116`; 4 ba1 (u_ahi) origin y +43.2; 4 bf clock landings y +21.6, 4 ahi landings +43.2. 22 cores, 0 overlaps, 0 outside (top ahi edge 1222.56 of 1226.88) |
| t34 VQ +43.2 | YES | u_lf.u_vq origin y 527.04 -> 570.24, tap +43.2, 21 of 330 station rows rebuilt; 27 cores, 0 overlaps |
| t43 two-station rows | YES | 9 rows withdrawn, 15 added (318 -> 324), every new row 2 stations; lanes dn/up_s_4N_L1 fixed 6->7 / 3->4 |
| t8 tap move | YES | 3 edge_clocks + 23 landing pins x 1440.736 -> 1596.256; 2 collector_local_sources 1442.88 -> 1598.4; 3 bands now single rects |
| SerDes out of relay_lockup | YES | reset.relay_lockup.types 345 -> 334, 0 serdes entries |
| svc_2 -20 ps clock row | NO | 0 differences under `clock` outside gunit / t34 / t8. Not buildable (R2); the svc_0 +20..32 form is not built |
| 9 latency-0 crossings | n/a | the new table is not in; sidecar crossings unchanged |
| CA table 38 -> 24, hbmrd_i0 growth | NO | sidecar = adopted + 38 leaf differences, all `collector.types.ot_s81sl_leaf__t8`; 993 crossings, 447,111 bits, 440 lanes unchanged |
| e5 ELAB_RC2 OOM fix | YES, holding | ELAB_MEM=160; asbuilt.json was 1.78 GB at 20:40 PST and still growing (e5 died at 1.37 GB; 819 wrote 3.35 GB) |
| Form B (+1 write-bus, t34 / t62) | NO | comes in the fresh C4 bind on top of C3 (COORD r431, branch d1645b7afcd) |

## 2. Reach (every hop <= 405 um)

- Changed rows: t34 max hop 394.8 um (21 rows), t43 max 377.5 um (15 rows, hops 377.5 / 344.8 / 260.6). 0 over 405.
- Whole plan: 24,785 station rows, 13 rows over 405 on 13 types, max 422.6 um (12 x col_h10_r1 cl95b37463 `bus:frame_int_i0`, 1 x dsdv_slice_iq_C__t1).
  Identical in the base (13 rows, 422.6): inherited, not caused by this event. Owner S81-TYPES-R2 (col), next event.
- t8 pin-to-band hops improve: ft0_i 402.0 -> 282.2, ft1_i 402.8 -> 284.2, monitor_1 192.2 -> 68.0 um.
- R-REACH-4 (forwarded-clock source): no G0 finding so far; G0 was still running at 20:43 (1,527 lines, TAP-LIMIT-INFO / TAP-RADIUS-TARGET advisories only, 0 error lines).

## 3. Col relay depth (lever 2)

DEFERRED. 0 col types differ from the base. S81-COLRELAY result (20:07): 8 of the 18 NOFIT groups of col_h10_r0_p1 are row-fixable
(one `bus:xo_o0` row, 3 stations, max hop 390, +3 cycles on xo_E1_in_a, 7 types) and go into C4. The other 10 need relay depth in the col RTL
generator (S81-TYPES-R2).

## 4. Tap insertion / window

- gunit bf tap: insertion 360.0 -> 412.99 ps TT, 293.4 -> 339.27 FF (signed view, n 4,911). Type budget 450: 37.0 ps left. PASS.
- The die clock (ECOv3 tree cda34b3a) was measured with bf at 360. The bf sinks now sit +53.0 TT / +45.9 FF later and this event has no clock re-run.
  TT setup margins of record (+340.6 intra, +270.1 seam) cover it; FF hold is UNMEASURED on this die. Advisory.
  Owner S81-DIE-R2: use the signed bf insertion in the post-bind die STA that already checks the relay hops.
- t34 VQ and t8: positions only, no insertion change. G0 radius advisories on t34 (288.2 / 200) and t8 (242.8 / 200) are not new classes.

## 5. Latency for LATCHECK

- latency.lanes: 873 lanes, sum 14,715 -> 14,717; only dn_s_4N_L1 8->9 and up_s_4N_L1 5->6. CA sidecar cycles unchanged. No form B cycle is in s5f, so nothing is half-applied.
- Watch 1 (S81-TYPES-R-STRIP): the withdrawn t43 rows carried 192 dn / 100 up bits, the new ones 101 / 410. u_vs.s_d (156 b), s_v and fault (1 b up) have no row.
  The lane is +1 for all bits, so these bits need a second stage from the kit default; R2 measured their merged site (772.4, 184.5) inside u_lf.u_vn.u_b
  (~529 dn bits). No catch-all row has been delivered. t43 stays HOLD at the kit until it is; site-only, no rebind.
- Watch 2 (S81-DIE-R2): the gunit rows change no lane (0 gunit lane differences) although the bind adds OT_GUNIT_BF_FWPIPE with RT_LAT 66/64. LATCHECK decides.

## 6. Core reshape

One shape change in 21,010 cores: the 4 gunit bf, 432x172.8 -> 432x216. This restores the signed 1116 view (FABLE-FIX-S81-GUNIT, COORD ruling), so the
unsigned nrev_1113 shape is withdrawn rather than a signed core reshaped. No type outline, module or orientation changes anywhere else.

## 7. Event name vs hold terms

- No live S81 hold names B6gF2s5f (or any F2s5 name). Every S81 event term is `event_adopt:3fa87b84b18` (mig-024-k1 220 keys, mig-003 13, mig-002 13, mig-006 1, mig-009..022 14).
  So nothing releases on this event's name; mig-007-k7-k8 releases on the exact post `result:S81-DIE-R2:lepe-mu-view PASS`.
- INFERENCE (evaluator not run by me): under r419 a historical event never releases. If the adoption changes the config event key, those 261 keys go back to held.
  Adopt as r414 did: keep `event` 3fa87b84b18 and change only `plan_event`. Owner S81-DIE-R2, check by HOLDGEN-1115 / FIX-S81-COL-STALE before the atomic apply.
- The bind runs on source `_f2s4_cohort_d3`; the adopted tree has been `_d4` since 20:15 (tree_switch_s81.json). My d3/d4 compare showed only the two manifest files
  differing before it was cut at 120 s, so it is not a complete proof. The adoption tuple must name d4 with an equality proof, or the bind is rerun on d4. Owner S81-DIE-R2.

## Not checked

Bind and LATCHECK verdicts (running), G0 final count, the t43 leaf station netlist (die_b178_lfcs.v), FF hold of any pair.
