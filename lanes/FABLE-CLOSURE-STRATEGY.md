# FABLE-CLOSURE-STRATEGY 2026-11-17 09:20 PST (0920): delta on 07:15

Reviewer: FABLE-CLOSURE-STRATEGY-0920 (Fable). Read-only, no jobs launched. Technical PD only. HBM parked.
Blocking gates: DRC 0, routed TT setup >= -42 ps, internal FF hold >= 0, die bind + LATCHECK.

Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal, not measured.

## 0. What changed since 07:15

1. **KV HG6 bind is FAIL, not running (V).** D18 gate on epyc8: PRE PASS, G0 0 errors, LATCHECK 2404 / 2404 PASS, but strict bind has **31 errors**: 30 `R8_STALE` (29 on `hsl_EN_12.ai <- hsl_EN_11.ao`, "as-built 0 bound 7, table bound 5"). The D19 R8 check prints `R8 FAIL`: 64 of 3,001 groups unequal, 2 inversions, 6 types conflicting. This is finding S4 of FABLE-PLAN-KV-HG6: LATCHECK passes per lane while the group pads are wrong (lever 3).
2. **S81 SerDes H16 is clean at GRT in PG region mode, and stopped on a harness error (V).** Span 75.0 PASS, GRT congestion 0 / 0 / 0, setup TNS 0, hold +0.12. Exit 6 at 09:10 is `cannot open '/work/postcts_gate.tcl'`, not design. H15 is one step behind and will stop the same way (lever 6).
3. **DRT-0255 has a proven cause on serdes (R, FABLE-FIX-S81-SERDES2):** one-gcell-high M6 guides in the gcell row under an M6 PG pair. Position test: 17 of 28 logged kits (QC 9, HEAD 4, S81 4), 43 of 77 points against 18 % by chance. The worker-edge idea is withdrawn (lever 4).
4. **S81 strip is a family problem (R, S81-DIE-R3):** `ft_channel_tracks` flags 25 channels in 20 types; the moves-only D6 seed fails (t34 timing_over 5 -> 23, t13 4 -> 50, t71 stays 0.90). My 07:15 lever 6 item 1 (three VE moves, 0 cycles) is **withdrawn** (lever 5).
5. **HEAD corridor: there is no capacity limit (R, FABLE-FIX-HEAD-CORRIDOR 09:09).** `edges_g1.py` mapped model stages to plan rects by prefix after the chains were renumbered. With the map by tag: reach-bad 3,309 -> 0, worst cut 1.195 -> 0.838, krx3_r0 is legal. The B2 numbers of FABLE-PLAN-HEAD-NF15F and the "13,200 nets on 11,046 tracks" in the brief used the scrambled edge set and are withdrawn. Open: 3,531 unassigned, vertical access over limit at 23 of 27 anchors (lever 7).
6. **HEAD credit depth (R):** K-link round trip 24 on RX lanes 1 and 2; depth 16 fails, 24 passes with zero slack; uniform 28 recommended. rs5 gates all PASS.
7. **QC:** cb closes with `latch_except ["tap[0]"]` + 3 HB4 (TT setup >= +90.6, FF hold >= +93.9 over 2,032 tap pins, R). Face-row pilot signed off through a 2-cell post-route ECO (R). D4 fixed the kit_rtl path class (R).
8. **HEAD sd9f is not signed off yet (V):** the verification DRT of run_eco3 started with 230 violations and was in iteration 1 at 09:08.

## 1. Evidence I opened

| item | host, path | result |
|---|---|---|
| H16 CTS / hold | epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-serdes2/H16/serdes__t13/gen/serdes__t13/run_route.log` | `OT_STB_SPAN` 25,112 sinks, min 2025.1, max 2100.1, span 75.0 PASS. Pre-GRT FF hold +4.9, 13,472 hold cells, cross-tap +45.0. The same line prints setup_wns -77.35; I did not resolve its corner |
| H16 GRT | same kit, `run/logs/asap7/dp_serdes__t13/base/5_1_grt.log`, `5_1_grt.json` | `OT_PG_TRACK_TRUTH region 2713 GRT capacity cuts, 100 % per gcell, M5=1051/4204 M6=696/4176 M7=966/5131`. Usage 3.07 % total (M6 0.99 %), congestion 0 / 0 / 0. Hold -24.27 / 80 ends -> +0.12 with 80 buffers. Setup TNS 0, hold TNS 0. Non-tap cells 407,007 |
| H16 stop | same kit, `postcts_gate_TT.log`, `FAIL_POSTCTS`, `H16_run_route.out` | `[ERROR STA-0340] cannot open '/work/postcts_gate.tcl'` (the file is in the kit, 17,120 bytes) -> `OT_LEGACY_GATE grt FAIL: missing postcts gate` -> exit 6. No `grt_policy.json`, so no TT read by class. No DRT |
| H15 | epyc9 same lane, `H15/.../5_1_grt.tmp.log` | In GRT antenna repair at 09:11; congestion 0 / 0 / 0; hold -16.98 / 113 ends -> +0.04 with 120 buffers |
| KV D18 gate | epyc8 `/srv/opentallas-scratch2/claude/kv-r3/d18gate/{pre,g0,bind,latcheck}.log` | PRE PASS 0 findings; G0 0 errors / 2,396 warnings; LATCHECK 2404 / 2404; bind `errors: 31`, 30 `R8_STALE` |
| KV D19 R8 | epyc8 `kv-r3/r8check_d19.log` | `R8 FAIL`: groups_unequal 64, inversions 2, types_conflicting 6. Types: kv3_pc_v1 cl7f648944 (9 sites), cl4ea58a5c (4), kv3_pc_v3 (2), kv3_pc cl5a95b461, kv3_hg_v1p3. Example pads [-22, -24] on `slg_*_4.x__tok <- kvs_emb.px_tok` |
| HEAD sd9f | intel2 `~/head-types-r4-logs/sd9f_eco3.log` | Verification DRT: 0th iteration 230 violations, 1st iteration running |
| Failure classes | intel2 `tools/failure_breakdown.py` 09:10 | S81 types 41 / 394: kit_rtl 28, other flow 7, kit input missing 7 (bk_sel), congestion 1 (phy__t1), place error 1 (serdes__t3), hold after CTS 1 (serdes__t4). QC 9 / 127: kit_rtl 28 (pre-D4 rows), running 36, route held 2 (cbn_q01). KV 6 / 56: 9 wait on child. HEAD 23 / 26 |

Not opened: the col branch `claude/s81-col-prd-obs-1117`, the strip channel census, the corridor g3a files, the HEAD credit benches, the QC N plan, the DRT-0255 scan file.

## 2. Levers, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: merge the obstruction fix, hold margins and sstn M5 block before the released members route | 203 col types | S81-TYPES-R3 |
| 2 | QC | event N on M5 (cb `tap[0]` row + N START + SC reset + R-REACH-4), clock of record | 18 cb types + about 112 re-sign + die bind | QC-PLAN-R3, QC-TYPES-R3 |
| 3 | KV | HG6: equalise station depth per R8 group, regenerate the R8 table | 50 unsigned types | KV-R3 |
| 4 | all | PG region mode as the GRT default | 17 of 28 logged DRT-0255 kits on 3 dies | FABLE-FIX-S81-SERDES2 (branch), then all type lanes |
| 5 | S81 | strip family: re-slot ft across channels, then widen with +1 register on bus links | 20 flagged types (25 channels) | FABLE-FIX-S81-STRIP, S81-DIE-R3 |
| 6 | S81 | SerDes: resume H16 / H15 from the GRT DB to DRT | 11 serdes types | FABLE-FIX-S81-SERDES2 |
| 7 | HEAD | NF15f: tag-mapped edges, bit-slice relay columns, credit 28 | hd_lep0N, hd_mesh, hd_serdes + die gate | FABLE-FIX-HEAD-CORRIDOR, HEAD-PLAN-R4, HEAD-TYPES-R4 |
| 8 | all | post-route internal HB4 ECO as an automatic fallback | near-miss hold on any type | QC-TYPES-R3 (tool), all type lanes |

### Lever 1. S81 col (203 types)

Evidence (R, FABLE-PD-S81-0720 and the brief): pg3 routed TT -39.25 passes; 57 internal FF hold ends at -7.61 (50 are hard core `u_s13` output -> first flop); the repair run crashed in DRT-1231 on 3,967 PG-track obstructions left in the GRT DB. The fix is on `claude/s81-col-prd-obs-1117` (not opened by me).
Root cause: unchanged from 07:15. Obstruction removal existed on the first-route path only; hold closed to +5 / 0 before a route that takes 8 to 12.5 ps; GRT sees M5 gaps in the sstn abstract.
Fix (S81-TYPES-R3).
1. Merge the branch, then check on one member that the per-layer obstruction count before detail route equals the seed.
2. `OT_HOLD_FF_MARGIN`: same-tap 5 -> 15 ps pre-GRT, GRT repair 0 -> 10 ps. H16 shows the cost is small: 80 buffers closed 24 ps at GRT on 407k cells.
3. M5 block over every `ot_s81_sstn_*` interior at floorplan.
4. Region mode (lever 4) replaces the obstruction form on new col kits, so item 1 becomes a check, not a dependency.
5. Members already routed: lever 8 tool.

### Lever 2. QC event N on M5 (about 130 types)

Evidence (R, QC-TYPES-R3 07:37): after the join fix all five former ends are +324..+426; the only negative ends are the four `tap[0]` latch pins (-27..-127). With the pin on latch D and 3 HB4: TT setup +90.6..+181.3, TT hold +120.3..+205.1, FF hold +93.9..+151.1; census over 2,032 tap pins has 0 negative at both corners. M5 gates: LATCHECK 1921 / 1921, G0 0 errors (R, QC-PLAN-R3). The pad numbers are placement estimates.
Root cause: unchanged. `tap[0]` has its own core arc (window 261 to 624 ps); rows drift with every tree re-cut.
Fix.
1. QC-PLAN-R3: N = M5 + `latch_except ["tap[0]"]` + `latch_except_hb4 {"tap[0]": 3}` on `qfd_tile_nk_a0c` + N START + SC reset + R-REACH-4, one bind. Never `["tap"]`.
2. QC-TYPES-R3: cbn_q01 pilot acceptance after route, not after CTS: the four `tap[0]` pins TT setup >= +60 and FF hold >= +50 on the routed DB. The margin at CTS is +90 / +94; route will move it by 10 to 20 ps.
3. Clock of record by tree sha (07:15 lever 2 item 3) is still not built. Without it N will re-open the 112-type drift.
4. Region mode on the N kits: QC has 9 of the 17 position-matched DRT-0255 kits.

### Lever 3. KV HG6 (50 types)

Evidence (V, section 1): bind 31 errors, R8 FAIL with 64 unequal groups and 6 conflicting types. Example pads [-22, -24], [-3, -4], [-1, 0], [2, 4], [3, 4].
Root cause. HG6 adds +1..+4 cycles per bus (960 lane-cycles). An R8 group holds buses with different k (`af__fault` +4, `px_tok` +4, `o_ctl` +0), so the group target moves and the strap pads (DMAX 1-2) cannot follow. Two separate effects: the R8 table was not regenerated after the stations (`R8_STALE`, bound 7 against table 5), and replicas of one type now need different pads at 16 sites.
Fix (KV-R3), P.
1. In `compose_hg6.py`, per R8 group: k_group = max k over the member buses. Buses with a smaller k take the difference as receiver `lpad` (or extra stations on the same path). Every member of a group then moves by the same k and the pads stay in range. Cost: flops only, 0 new cycles on the group beyond its slowest bus.
2. Regenerate the R8 table from the new bind before the R8 check. A negative pad of -22 is a stale table, not a real requirement: check that first.
3. If a replica set still differs after 1 and 2, equalise on the source side (`bound_ist` on the source lane, per instance). Do not split the type.
4. Gate: bind 0, `R8 PASS` with groups_unequal 0, LATCHECK 2404 / 2404, then the PC dry GEN of `kv3_pc_v1__cl23f6a148`.
5. kv3_hub_C (773,818 cells, R): split is a separate event (KV-HUBC-SPLIT). It does not block HG6.

### Lever 4. PG region mode as fleet default. Verdict: yes, as a default, after one DRT proof

Evidence. V: H16 in region mode: 2,713 capacity cuts, GRT congestion 0, usage 3.07 %, no new overflow. R: all four failing serdes nets carry a one-gcell-high M6 guide under an M6 VSS / VDD pair; the default obstruction form still let GRT lay guides there (5,038 obstructions); 17 of 28 logged kits match by position. Not measured: a DRT pass in region mode (H16 stopped before DRT), and the setting of 21 of the 28 old kits.
Root cause: GRT counts tracks under a PG stripe pair as usable; detail route cannot use them, so maze route dies on a guide it cannot realise. Region mode removes that capacity in GRT, so the failure becomes a GRT detour or an honest overflow instead of DRT-0255 hours later.
Judgement.
1. Default `OT_PG_TRACK_TRUTH_MODE=region` in gen_phys for all four dies, in the one branch FABLE-FIX-S81-SERDES2 already prepared, as soon as H16 or H15 passes DRT iteration 1 (hours, not a new experiment). Do not wait for more pilots: the capacity it removes is not usable in detail route either.
2. Cost to price: the cut is 100 % of a gcell in the stripe rows (M5 1051 / 4204, M6 696 / 4176, M7 966 / 5131 as printed). Sparse types do not notice. Dense channels do: S81 strip seams, the HEAD corridor (cut 0.838) and QC cb. The plan-time models must use the same capacity: `ft_channel_tracks` (45.6 tracks / um) and `alloc_r4` / `vert_access` (25 % PG share) need a check against the region-mode cut, else the plan passes and GRT overflows.
3. Not covered by region mode: the HEAD reserved-site / M8-grant class (5 HEAD kits) and DRT-0073 pin access on QC hard cores. Those keep their own fixes.
4. Apply to new kits and kits before GRT only (config by copy + mv). Never patch a kit past GRT.

### Lever 5. S81 strip family (20 types, 25 channels)

Evidence (R, S81-DIE-R3 08:43 / 08:53): VE_m|VE_s inner gap 34.56 um carries 3,190-3,427 bits on t22 / t2 (2.0-2.2), t9 1.50, t73 1.07; VE_s|vq t17 / t23 / t67 1.26-1.31; west seam t71 / t13 / t34; vsw|VE_m t57 / t46; slice c1x t8 / t9 and iq t1 0.87-1.04. Moves-only seed: bus links reach 594 um against 585, 5 stations need +1 register. No flagged type has a GRT result; the 0.70 limit is calibrated on t34 alone (1.12 -> M6 2,199 + M8 1,254 overflow).
Root cause: N / S ft slots are assigned to one channel per type without a capacity test. 3,400 bits need about 107 um at 0.70 x 45.6 tracks / um; the gap is 34.56. Width cannot come from moves alone because the bus links already sit at the reach limit.
Fix (FABLE-FIX-S81-STRIP plans; S81-DIE-R3 binds), P.
1. Re-slot first, 0 cycles: distribute the ft slots of a type over all its vertical channels in proportion to width (the census has `widen_by` per channel). A type whose total channel width covers total bits / (0.70 x 45.6) needs no core move.
2. Only where the total is short: widen by VE move with `--link-reg`, +1 register on the bus-link class (pre-approved, r567). Price it in LATCHECK in the same event.
3. Second calibration point before 20 types are re-planned: GRT one flagged type on the current floor (t22 or t2 at 2.1-2.2, the kit exists at place) with no early stop. If it routes, 0.70 is too strict and the list shrinks. t62 (0.25) is the low point.
4. D6 keeps the check as warn and carries bksel only (r567). The strip re-plan is one event after it, all 20 types, check blocking.
5. Use region-mode capacity in the calibration (lever 4 item 2).

### Lever 6. S81 SerDes (11 types)

Evidence (V, section 1). 16 rounds work: span 75.0 (H16), 70.4 (H15, R). At GRT in region mode H16 has setup TNS 0, hold +0.12, congestion 0. The stop is the post-CTS gate container not finding `/work/postcts_gate.tcl`.
Fix (FABLE-FIX-S81-SERDES2).
1. Do not rerun CTS or GRT. Fix the gate mount, rerun the gate, resume route from `5_1_grt.odb` (sha 9e362b03 on H16). H15 gets the same before it reaches the gate.
2. Acceptance stays the routed TT by class and DRT iteration 1 without DRT-0255. The AM class (`rxf_q` fall -> `face_am3.parts`) decides the centre trunk; no trunk row before that read.
3. Then one gen_phys branch: region mode + `OT_STB_ROUNDS=16` for serdes, and the other 10 types.
4. serdes__t3 / __t4 / t12 / G / J stay floorplan items (R), not this clock.

### Lever 7. HEAD NF15f

Evidence (R): corridor g3a it1 on plan 94de298f: reach-bad 0, cut 0.838 at x 980 (9,113 / 10,871), mandatory 0.553, over 405 um only ktx2_r0; still 3,531 unassigned and 23 of 27 anchors over the vertical limit. Credit: RTT 24 on RX lanes 1, 2. rs5: bind PASS, cohort 26 / 26, LATCHECK 329 / 329, G0 0 errors. Reset entry-phase model 0 fails on 357 parts, min margin 118.8 ps, old clock only.
Root cause: compact relay anchors (16.7-54 um wide) force every bit to leave its trunk track, run vertically to a flop and return; that is the vertical demand and the unassigned count. The corridor itself has room.
Fix.
1. FABLE-FIX-HEAD-CORRIDOR: relay ranks as bit-slice columns on the trunk tracks in the y 665-846 channel. Acceptance on the exact plan sha: unassigned 0, reach-bad 0, every hop <= 405, vertical ratio <= 0.9, rect overlap with hard cores / reserved sites / pin windows 0. No growth, no M8-all, no fourth KRX stage.
2. HEAD-PLAN-R4: retire `edges_g1.py`; `KCRED` uniform 28 with `LOCAL_POP` on `CORE_CRED >= 12`; measure RTT in the bench; strap x 10.016.
3. HEAD-TYPES-R4: rebuild and re-sign `ot_s81hd_lep_pair` at the same outline after item 2. sd9f: wait for the verification DRT result; make the reserved-site carve a generator rule before the hd_lep0N and hd_mesh kits.
4. Reset labels only after the NF15f clock GEN.

### Lever 8. Post-route internal HB4 ECO. Verdict: fleet default as a fallback, with limits

Evidence (R, QC-TYPES-R3): coll_ucie first sign-off FF hold -1.55 on 2 reset-removal ends; 2 HB4, 3 nets re-routed, DRT 0, signed off; replayed end to end by `hold_eco_internal_run.py`. S81 col pg3: 57 ends at -7.61 (78 HB4) is the same shape. H16: 80 ends at -24 after GRT.
Judgement.
1. Yes: run it automatically when the first sign-off fails only on internal FF hold. It turns a full re-route into a 3-net incremental route.
2. Limits, so it does not hide structure: worst end >= -15 ps, at most about 100 ends, each end has TT setup slack above the pad delay + 20 ps, no clock net and no port path touched, PG-track obstructions absent from the DB (the col crash), `design_is_routed` checked before the result is written (the sd9f abort).
3. Outside the limits it is a skew or margin problem: fix the pre-route margin (lever 1 item 2) or the tap, not the ECO.
4. It is not a replacement for the explicit pad row on QC `tap[0]`.

## 3. Stop list (changes; the 07:15 list otherwise stands)

1. S81 strip: the three VE moves as a moves-only D6 row; re-planning 20 types on the single t34 calibration point; holding D6 / bksel for the strip re-plan.
2. S81 SerDes: worker-offset DRT experiments; H12 / H13 / H14 as route forms (obstruction mode, expected DRT-0255); a new CTS for H16 / H15; `OT_STB_ROUNDS` 8.
3. PG: the obstruction form of `OT_PG_TRACK_TRUTH` on any new kit; more position scans of old kits.
4. HEAD: any decision from `edges_g1.py`, the a2 / g2 runs or "13,200 on 11,046"; growth +60 / +120 or M8-all as corridor fixes; a fourth KRX stage; per-class credit depth; widening compact anchors in x.
5. KV: binding HG6 again without group-equal k; reading LATCHECK 2404 / 2404 as proof of the token schedule; a type split for the 6 conflicting types; a tap re-cut inside HG6.
6. QC: `["tap"]`; accepting the cb pilot on CTS numbers; a separate event for the cb row.
7. Hold: post-route ECO beyond the limits of lever 8; hold repair on a DB that still carries PG-track obstructions.

## 4. Not checked

- No DRT result exists in region mode. The default verdict rests on the H16 GRT read and the lane's guide geometry.
- H16 GRT TT by class: `grt_policy.json` was not written. Setup TNS 0 is from the stage metrics; the -77.35 in the pre-GRT hold line is unexplained.
- Why `/work/postcts_gate.tcl` was not visible to the gate container.
- The KV fix is a proposal: I read the error lines, not the group table or `compose_hg6.py`.
- The strip census, the corridor g3a result, the credit benches, the col branch and the QC pad numbers are lane reports.
- The meaning of the `M6=696/4176` denominator (stripes or tracks).
