# FABLE-CLOSURE-STRATEGY 2026-11-21 11:35 PST (lane FABLE-CLOSURE-1120): the planned S81 col DRC fix failed its proof twice on pin access, and the col GRT failures are one macro-corner or face strip per class at 13 % routing usage, not capacity

Supersedes the 09:25 round (FABLE-CLOSURE-0910, `git log -2 -- lanes/FABLE-CLOSURE-STRATEGY.md` on coord/state). Its levers 1 (place measurement, landed as 3ed87c352a) and 3a (obs_gcell_cap, landed as f56d99cf55 + 89ed3a69db) are done and drop out. Its stop list stands unless a line below changes it.

Reviewer: FABLE-CLOSURE-1120 (Fable). Read-only: nothing launched, cancelled, signalled or patched; no ot-run job. Scope: S81, HEAD, QC, KV physical design only.
Gate: DRC 0, TT setup >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. No die or outline growth. Nothing below is a new gate.
Marking: **V** = read by me this round from the named log, report or kit file. **R** = reported by the named lane or review. **I** = my inference. **P** = proposal.

## 0. Check of the COORD 11:2x context

| Item | Result |
|---|---|
| S81 col: M5 shorts at `u_cf` / `u_t0` pins are the blocker; fix = cfifo via-shadow view 1980f8126c | Blocker confirmed (R, FABLE-PD-S81-1100: 20 and 15 left). **The fix is not proven (V):** the col proof died DRT-1231 twice, the second time at 11:15 with the shadow already limited to M4 (a8f44f5106). See lever 1 |
| S81 lepe proof10: +1 relay stage gives CTS setup -64.5 | R only (FAM-S81-LEPE-3 handoff; epyc7 not read by me). Post-hook, not routed |
| QC strap: four `rs_n_c` chains merged by synthesis; btab -> `u_u_r3` at -124 | R, measured by FABLE-FIX-QC-STRAP on the a3 kit final `5_1_grt.odb`: -333.6 on 4 ends and -124.3 on 22 ends. The seat fix has a dry run only, no timing result |
| KV: hub_Eo ring cores, pv_v3 split, D27d red | hub ring: 5 masters re-frozen and SIGNED, G0 PASS on b5bd29148814, strict bind running (R). pv split 14 probe bind crashed three times on cut-lane packing; fix 502f9d7357 unpushed (R). D27d2 strict bind running, G0 PASS (R). **New (V):** 7 pv types fail at place on an illegal clock-landing band, 2 are over the cell cap (lever 6) |
| Lockup station helps S81 t39, hurts QC sle_ctl | R: t39 cross-tap 14,251 -> 9,161, hold cells 47,483 -> 36,145, TT -354.6 -> -291.4 (pre-GRT). QC general form TT -1.82 -> -133.98. A hold lever only |
| S81 serdes ench_j6a TT -59.95 on the CRC XOR chain | R (FAM-S81-SERDES-R5 handoff): 11 ends, worst `u_enc.rem_q[50]`, next -35.36; DRC 0, hold 0 |
| FLOW clock-first GRT A/B in flight | Base arm done 11:13 (R). Table in lever 4 |

## 1. Levers, ranked by types unblocked

### Lever 1. S81 col: the hard-core pin view needs an edge inset or a cell halo, and its proof must be a fresh kit (216 col types)

- Evidence:
  - R (FABLE-PD-S81-1100 section 1.3): every col kit that converges ends with macro-body shorts. pv11b73b67: 17 M5 + 3 M3 against `u_r0_u_cf`. pvd2159f4a: 31 M5 on `u_cf` and 8 at `u_t0` at iteration 15. ECO cannot remove them.
  - **V**: `epyc10 /srv/opentallas-scratch2/claude/opus-fix-qc-sle-r4-sc/col_eco/route.log` line 397: `[ERROR DRT-1231] Pin u_bound.u_u_r0_u_y_rt_7a_0.u.o[45]$_DFF_PN0_/RESETN does not have access point`, at 20 % of iteration 0 with 178 violations. `client4.log`: `COL_ECO master obs 16210 -> 25740 (added 9530)`, 18 nets ripped, exit 1 at 11:15. The earlier try (shadow to M2) died the same way (`route_try2_drt1231.log`).
  - The same exporter's EOL-stub half works: QC sle_sc_v1 cl115da35f signed 11:21 after a 22-pin ECO, DRC 0, TT -17.57 (R).
- Root cause (I): two things at the same edge. Routes travel under the M5 OBS on M2 to M4 and via up at the M5 pins inside the body. The shadow OBS that stops this reaches the macro boundary, and relay-station flops sit against that boundary with no halo, so a flop pin loses its last access point to the 0.072 um wide-shape spacing.
- Fix (P):
  1. Exporter: keep shadow OBS at least 0.30 um inside the macro boundary on M2 to M4, or shadow only the band that holds the shorts (4 to 14 um inside the pin edge, 2 um inside the opposite edge).
  2. Kit: one-row cell halo around `dsfd_cfifo_crs4` and the `u_t0` master for `OT_RELAY_MID` and face flops in col kits.
  3. Proof: one fresh routed col kit from the J7 tree, accepted on 0 violations against `u_cf` and `u_t0`. The ECO on the old placed DB cannot pass while a flop abuts the macro, so stop repeating it.
- Owner: FAM-S81-COL-H10-R3 (view, halo, proof), QC-SLE-R5 (exporter code inherited from OPUS-FIX-QC-SLE-R4-SC), S81-J6-ASSEMBLY-R4 (pick-up before the 04:15 apply; the view changes no row).

### Lever 2. S81 col: stations and wide buses crowd one macro corner or face strip per class; `OT_RELAY_MID_FIT` does not engage (col_h9_r0 about 60 types, col_h10_r0_p1 6, and every class J7 adds stations to)

- Evidence:
  - **V**, kit `epyc9 .../s81/224567138ab/items/col_h9_r0_p5__t1__pvc6e5797f/gen/...` (job 2432bcbc4bba, GRT-0116 at 09:33):
    - `5_1_grt.log` after 30 extra iterations: usage 13.06 %, total congestion 117,612, of which M4 20,065, M6 43,101, M8 52,796 (horizontal layers only). 7 clock nets lost their NDR (GRT-0273).
    - Final `congestion.rpt`: 791 gcells, 651 of them in one 50 um bin at x 1400 to 1450, y 600 to 650; 719 in the band y 600 to 650.
    - `macro_place.tcl` + LEF sizes: `u_r0_u_cf` covers x 1131.9 to 1412.7, y 604.8 to 673.9; core east edge 1438.56, so the slit east of it is 25.8 um. `u_r0_u_t0_payload` (86.4 x 25.92) sits at x 1339.3 to 1425.7, y 509.8 to 535.7.
    - Nets in the hot gcells: `u_y_xd_u_r0_u_t0_payload_i_0_0.d[*]` (payload536 bus) and `u_r0_u_y_rr_3_3.o[*]`. Place log: xd chain 1 station, path 409 um; rr chain 4 stations, path 883 um; `OT_RELAY_MID_FIT fitted 0 stations`.
  - R (FABLE-PD-S81-1100 1.2): class cl0045af7b stuck at 28,640 DRT violations, 26,999 of 27,106 in a 130 x 15 um strip under ROM pair `e2`; four xo stations plus the bus repeater row in three cell rows; FIT fitted 12 of 105, none of xo.
  - R (FAM-S81-COL-H10-R3 09:23): proof C placed 18,465 relay flops of 157 stations, `OT_RELAY_MID_FIT fitted 0`, hook `touched=0 expected=0`.
  - Log (V): GRT-0116 also on col_h9_r0_p3 pv625eef47, col_h10_r0_p1 pvb095fa2f, kv_leaf t1 and eng t1 between 09:40 and 10:52. Their logs went with the job dirs; not read.
- Root cause (I): `OT_RELAY_MID` puts each station as a compact cluster on its source-sink line. The line of a 276- to 536-bit bus passes a hard-core corner or a face strip where only the horizontal tracks above the OBS are left. FIT, the hook meant to spread them, counts no eligible group on three different kits.
- Fix (P):
  1. Find why the FIT group selector returns 0 on depth-row and xd / xo groups, and fix it before any station rule is added (one tool bug, three kits).
  2. Station generator: keep stations and their bus line 30 um off any hard-core corner; stagger parallel chains by one cluster length plus 20 um; seat the `t0_payload_i` station on the payload macro's pin face so the bus does not turn around `u_cf`.
  3. Before J7 col volume: the per-class placed read (probe2.py) plus one check: any gcell column between a hard core and the core edge narrower than 40 um that carries a bus of more than 200 bits.
- Owner: FAM-S81-COL-H10-R3 (FIT selector), FAM-S81-COL-H9R0-R3 (p5 and cl0045af7b station rows), FAM-S81-COL-R5 (per-class census, already started as COORD fix 4).

### Lever 3. Setup by pipeline stage where the logic depth is fixed (S81 col 216, serdes 16, lepe LP; QC st_a 11 and fw 4)

- Evidence:
  - Col (R): pv11b73b67 routed TT -205.74 without the ROM-input stage; pv1619ecc6 J5 TT -99.84 on 74 ends, all RDX / ROM-pval. Bench: the stage costs 1 cycle (go spacing 9 -> 10), token compile 0 loss. The stage is out of J7d until the go-guard gate; gate `chain_j7g` is running on candJ7cG.
  - Serdes (R): ench_j6a -59.95 on the `rem_q` CRC XOR chain. The only A/B in flight (enchp_j6b) tightens the route over-constraint 770 -> 740 ps and changes no logic.
  - Lepe LP (R): proof9 -292.1 (`g_rx` bank -> `f_host`), proof10 with the `unit_o0` relay -64.5 post-hook, lane 87 -> 88 cycles.
  - QC btab (R): `g_read -> u_u_r3/bt_q_p` -124.3 on 22 ends, 668 ps of wire over about 800 um. SRAM -> `g_read` has +58 to +225. A +345.6 um SRAM shift collides with the r1 / r2 corridor contents.
  - QC fw (log, V): slw_fw_v3 late ECO ended TT -84.28 -> -110.58, class REDESIGN. The `x_sc_i` +1 station rows wait in V3.
- Root cause: single-cycle paths whose depth does not shrink with placement: CRC XOR tree, unregistered ROM read plus wire into a core pin, one btab read fanned to four cores in the same cycle.
- Fix (P), all pre-approved as +cycles:
  1. Col: land the ROM-input stage in J7d if gate J7g is green by 19:00; else the first J8 row. Without it no col type reaches -42.
  2. Serdes: split the `rem_q` XOR tree into two registered stages in `ot_s81_kp4_enc_core` (+1 cycle, bench + LEC with H0_SEQ_ONLY=1). Do not wait for enchp_j6b: 30 ps of over-constraint does not buy 18 ps on an XOR depth.
  3. Lepe: proof10 to route; the `unit_o0` row is already with the assembly.
  4. QC btab: slack over the two cycles sums to -66 to +101 per bit, so re-siting alone cannot close every bit. Give `u_u_r3` its own `g_read` copy sited by slack balance toward r3, and take the rest with +1 cycle on the bt read for all four cores (BT_LAT is a core parameter: QC-PLAN decides between the per-core copy plus a 70 to 130 um SRAM move and the +1 cycle with a core re-harden).
- Owner: FABLE-FIX-S81-COLROM-R4, FAM-S81-SERDES-R6, FAM-S81-LEPE-3, QC-PLAN-R10 (successor QC-PLAN-R11) with FAM-QC-HCST-R2 and FAM-QC-FEFW-R2.

### Lever 4. Clock: route clock first, and balance taps to the slowest tap (all four dies)

- Evidence:
  - GRT A/B on KV hroot a5, 30 iterations (R, FLOW-CLKGRT-R2 11:13). Columns: overflow / t9 spread / max insertion / FF internal hold, violators.
    - base 424 / 244 / 483 / -170, 693
    - NDR off 385 / 266 / 655 / -177, 759
    - resistance-aware 423 / 138 / 371 / -79, 476
    - clock-first 336 / 170 / 410 / -87, 541
    - hook e338085d61 385 / 170 / 409 / -86, 542
  - Tap spread (R, FABLE-PD-S81-1100): lepe proof9 tap means 236 to 380 ps against a 250 target; three late taps stay late because balance only adds delay; 8,350 of 12,840 hold ends are cross-tap; 11,074 hold buffers moved setup -292 -> -423. 2,194 of 7,368 async pins sit on another tap than their `local_r`; `OT_TAP_RESET_AFFINITY` is unset.
  - Log (V): the post-CTS triage stopped S81 slice_station t36 and QC slw_st_a_v2 cl9f076a5c with the same reading on two dies: `pinreg mean 279.19 / 279.34, bound 250.00, dev 29.19 / 29.34, tol 20.0`. The lane had t36 at place PASS and routing as signable.
  - failure_breakdown (V): S81 123 taps over 1,650 sinks, insertion max 838, skew max 328. QC 68 over, max 493 / 137. HEAD 0 over, max 501 / 82.
  - HEAD shelf_we (R): hold -130.62 on 11,257 ends before repair (port_in 7,703, cross_tap 3,493); pass 1 closed it with 5,661 buffers; 363,650 non-tap cells = 90.9 % of the cap.
- Root cause (I): the balance target (250) is below what the slowest taps reach, so the spread is built in and both the hold repair and the triage bound pay for it. FastRoute also detours NDR clock nets.
- Fix (P):
  1. Make `OT_GRT_CLOCK_FIRST=1` default once hook r2 passes its incremental step; add resistance-aware layer assignment if the combined arm (running) keeps overflow <= base.
  2. Tap balance target = the slowest tap mean of the kit (or split the tap that sets it: lepe root `clk` at 1,000 sinks, `clk_t8`, `clk_t65`). Derive the post-CTS triage bound from the same measured number instead of the fixed 250; a constant 29 ps offset on two dies is the bound, not the design.
  3. `OT_TAP_RESET_AFFINITY=1` on the lepe proof10 overlay, then default for S81 types with `g_reset_balanced`.
  4. Lockups: S81 general form after t39's final-GRT TT; QC only the exact-ends form (2,918 ends against 87,819 latches in the failed run).
- Owner: FLOW-CLKGRT-R2 (1), TAP-GRID-R4 (2), FAM-S81-LEPE-3 (3), LOCKUP-STATION-R3 (4).

### Lever 5. S81 start-strobe paths at the clock landing: read one path before any row (slice_station t6, t18, t29, t45, serdes t16; QC slw_fw_v1)

- Evidence (V, autopilot/log.txt 08:15 to 10:03, PLACE-SETUP-STOP):
  - `u_cland_origin/s2 -> u_cland_reader_start_ft*_i_0/g_x[n].u_r/q`: t45 -577.12 (hop 143.4 um), t18 -856.83, serdes t16 -1,252.45 (hop 115.9 um).
  - `u_rrl_N/q -> u_cland_fstart_ft3_o/q`: t6 -432.47 (145.0 um), t29 -381.30 (175.2 um).
  - QC slw_fw_v1 cl592e3d37: `cland_rstart_in[0] -> u_cland_writer_start_x_st_a_o_0/q` -303.90 (138 um).
  - FLOW-PLACEMEAS-1121 listed the S81 group as "DATA, rstart class, left as is". I found no lane post that owns it. The path report was not on the gen host; I did not read it.
- Root cause (I, not measured): a hop of 116 to 175 um cannot cost 400 to 1,250 ps in wire. Either one origin flop drives every `g_x[k]` reader register unbuffered at place (fan-out), or the capture register is on a landed clock that the post-place scene still treats as ideal.
- Fix (P): one `report_checks -fields {fanout cap slew}` on a kept `3_place.odb` (t18 or serdes t16) decides. Fan-out: one `s2` copy per reader bank in `ot_dp_clk_landing` (keep attribute, 0 cycles). Clock: judge the class post-hook at CTS and take it out of the place stop. No station row before the read: the hop is already short.
- Owner: FAM-S81-SLICE-R4 (read and fix), FAM-S81-SERDES-R6 (t16), FLOW-OPS-1000 if it is the measurement. No lane owns the class today: NEW ownership needed.

### Lever 6. KV: stop D26 retries; pv needs landing-band rows and the split, in D27d2 / D28 (pv 15 types, hg / hgi 16, hub 4, sys_c; 6 of 56 signed)

- Evidence:
  - Log (V), 08:15 to 10:47: kv3_pv, pv_v2, v3, v4, v5, v6, v8 fail at place with `OT_CLAND no legal nonoverlapping row/site in reserved band for u_bound.u_cland_raw_fs_o_pvw__u_*_b_0/q (literal-local-reset)`. pv_v7 447,860 and pv_v12 499,054 cells at floorplan, over the 400k cap.
  - Log (V): kv3_hg -559.80 at place, start `..._owner_rst_n_r0.q$_DFF_PN0_`, a reset flop: the class 3ed87c352a removed from the stop, on a kit generated with D26 tools. kv3_sys_c -861.55, `u_bin_i_serdes_E_tx_up/q -> u_bout_o_dcal_dob/q[2]`, hop 159.7 um (not read).
  - R: D26 tools rt 4e46a7ec46c5 has no obs_gcell_cap (43 exposed types). pv split 14 bind crash = cut bits packed onto the lowest-id wide cut lane. hub_Eo 450k placed; ring rows final. io_cor_v1 variant A: 6 shorts at east-face `ft11_i[2..7]` (x 1278.6, y 518), then DPL-0033.
- Root cause (I): the D26 wave kits lack three fixes at once (obstruction-aware GRT, place measurement, landing remap), and the pv landing band has fewer legal sites than raw local-reset stages.
- Fix (P):
  1. No D26 relaunch of pv, hg, hgi, sys_c. KV-PLAN-R6 asked COORD for this call: yes.
  2. D27d2: add one pv type to its 9 gen proofs and run `kit_preflight.cland_band_sites` on it; if the band is still short, a band-size row per pv type (sites >= raw stages) goes into D28 with the split.
  3. pv: push 502f9d7357, then bind 8c -> R3 / R4 rows -> bind 10 with `LEAF_FIRST_HOP` 0 / 0 on both halves; v7 and v12 take the same split.
  4. hub: ring bind -> private kits, place census target about 320k.
  5. io_cor_v1: re-seat the `ft11_i[2..7]` face pins one pitch apart from the neighbouring strip; routing-only.
- Owner: KV-PLAN-R6 (1, 2), OPUS-FIX-KV-PV-R5 (3), FABLE-FIX-KV-HUB-R3 (4), FAM-KV-IOPC-R2 (5), OPUS-FIX-KV-HGI-R5 (hg / hgi relaunch on D27d2 only).

### Lever 7. QC: seat first-hop registers and landings at the pin face (st_a 11 types, sle_ctl, sle_stm 2, cb 17)

- Evidence (R):
  - st_a a3 kit, final `5_1_grt.odb`: 29 violating ends, WNS -333.62. `rs_n_c_p` 4 ends: one merged flop at y 1284 drives 4 cores, last hop 1,067 um. `rs_n_hi_p` -33.7, last fixed stage 439 um from the pin.
  - R8-CORE-SEAT dry run on the placed DB: 404 of 528 pins seated, chain hop max 250.6 um, 0 need a stage. The push ended rc 0 at 11:19 after one failed try; no bind, kit or timing result yet.
  - sle_ctl k_a2: GRT overflow 40k -> 0 (core-slit class fixed); setup flat at -75.6 on 558 ends, all `u_cland_cws2_i/d`: input delay 245 + 256.7 ps wire into a falling-edge capture at 416.5 = -123.2.
  - sle_stm_v2: `u_core.rst_n` on tap 0, leg 699 um; row `reset.inst_taps` tap 79 gives 190 um, 0 cycles. cbf_q00: re-picked taps 75 / 135 um against 525 / 506.
- Root cause: registers and landing bands seated where an older placement had their sinks, on a tap or band away from the core pin face. Yosys merges identical pad chains.
- Fix (P): `r8_keep` + `r_r8_core_seat` proof on slw_st_a_v2 cl9f076a5c now that V2 is applied (11:17). sle_ctl variant C (cws2 landing at y 1257.12, ft hop 314). stm and cb `inst_taps` rows in V3. The btab item is lever 3.
- Owner: FABLE-FIX-QC-STRAP-R2, QC-SLE-R5, FAM-QC-CB-R2, QC-PLAN-R10 (successor QC-PLAN-R11).

### Lever 8. Splits under the 400k cap on the one strip / body schema (S81 lepe_mu_C t1, c1x_C t1..t10, svc hi 7, serdes t4; KV hub_Eo / Wo, pv)

- Evidence (R): lepe_mu_C 499,795; c1x_C 477k to 503k; serdes t4 407,738; hub_Eo 450,499 placed. FLOW-STRIPBODY-1121: split OK (2 windows, 16 cut lanes), strict bind + LATCHECK running, branch not pushed. svc hi4 on J7: split rc 0, chainJ7 bind running; the `type_split` core-tap fix is waiting on the same branch. Three lanes carry private `type_split.py` / `split_bind_routes.py` edits (stripbody, KV-PV-R5 502f9d7357, SVC-R7 patch).
- Root cause: flat runs over the cap; one splitter with three unmerged private fixes.
- Fix (P): push order on one file set: split_bind_routes 502f9d7357 first (it has a test), then the strip_body branch with the core-tap fix; SVC-R8 drops its patch. Then lepe_mu_C and c1x_C as J8 rows.
- Owner: FLOW-STRIPBODY-1121 (merge owner), OPUS-FIX-KV-PV-R5, OPUS-FIX-S81-SVC-R8, FAM-S81-LEPE-3, FAM-S81-SLICE-R4.

HEAD has no lever of its own: 25 of 26 signed. hd_lep0N shelf_we is the path; the open number is hold-repair pass 2 against the cap (about 36k non-tap cells left). The START bench result is a bench model limit (ideal clock on a count-aligned die), not a design finding (HEAD-START-R17 09:26).

## 2. Stop list (new or changed; earlier lists stand)

| # | Dead end | Why | Owner to hold it |
|---|---|---|---|
| 1 | Another ECO run of the via shadow on the old pv11b73b67 DB in its present form | Died DRT-1231 twice (V); a flop abuts `u_cf` | FAM-S81-COL-H10-R3, QC-SLE-R5 |
| 2 | J7 col volume routing before one fresh col kit ends at 0 against `u_cf` / `u_t0` | Every converged kit ends at 15 to 20 | S81-J6-ASSEMBLY-R4 |
| 3 | GRT capacity, layer adjustment or obs_gcell_cap as a col fix | Usage 13.06 % (V) and 14.5 % (R); the overflow is one bin | FAM-S81-COL-H9R0-R3 |
| 4 | Relaunch of col_h9_r0_p5 pvc6e5797f or the cl0045af7b class with unchanged station sites | Same corner, same strip | FAM-S81-COL-H9R0-R3 |
| 5 | More station or depth rows on col while `OT_RELAY_MID_FIT` fits 0 | Each row adds a 276-bit cluster on the same line | FAM-S81-COL-R5, FAM-S81-COL-H10-R3 |
| 6 | Hold-buffer repair as the fix for a cross-tap class | lepe: 11,074 buffers, setup -292 -> -423 | FAM-S81-LEPE-3 |
| 7 | The general lockup form on QC; lockups as a setup lever anywhere | QC TT -1.82 -> -133.98; t39 TT still -291 | LOCKUP-STATION-R3 |
| 8 | NDR-off clock routing | Spread 266, insertion 655, hold -177: worst arm | FLOW-CLKGRT-R2 |
| 9 | Route over-constraint as the serdes encoder fix after enchp_j6b | XOR depth; 30 ps of constraint against an 18 ps miss on 11 ends | FAM-S81-SERDES-R6 |
| 10 | TT repair retries on ROM-pin endpoints; any col sign-off expectation without the ROM-input stage | -99.8 to -205.7 | FABLE-FIX-S81-COLROM-R4 |
| 11 | Plain +345.6 um btab SRAM shift; more strap repair passes | Collides in the r1 / r2 corridor; repair stalls at -230 | QC-PLAN-R10 / R11 |
| 12 | D26 relaunch of KV pv, hg, hgi, sys_c | Pre-fix kits; illegal landing band on 7 pv types; v7 / v12 over the cap | KV-PLAN-R6 |
| 13 | Plan rows from a PLACE-SETUP-STOP number of a kit generated before 3ed87c352a | kv3_hg -559.8 starts at a reset flop | KV-PLAN-R6, OPUS-FIX-KV-HGI-R5 |
| 14 | Station rows for the S81 start-strobe class before the path read | Hops are 116 to 175 um | FAM-S81-SLICE-R4 |
| 15 | HEAD core tap-pin move on the 405 um or the cell-budget argument | Measured legs 115 to 287 um; the class cost 5,661 buffers | FABLE-FIX-HEAD-LEP0N-R2 |
| 16 | HEAD START RTL, provider or relay change from the ideal-clock bench | 59 of 78 failures are the bench's crossing model | HEAD-START-R17 |
| 17 | ft0 pin-band or `frame_int` rank change for the y 1220 to 1260 band | Intermediate GRT report; gone at the end | FAM-S81-COL-H9R0-R3 |

## 3. Not checked

- Read by me this round: the p5 kit (GRT log, congestion report, macro placement, LEF sizes, place log), the col ECO route log and client log, autopilot/log.txt lines 08:15 to 11:07, failure_breakdown (11:10). Everything marked R is the lane's number.
- The S81 start-strobe path itself (lever 5): no report on the gen host; the cause is an inference.
- The other four GRT-0116 kits (p3 pv625eef47, h10_r0_p1 pvb095fa2f, kv_leaf t1, eng t1): logs were published out of the job dirs. Whether they are the corner / strip class is not known.
- Why `OT_RELAY_MID_FIT` selects 0 groups: three logs say it does; I did not read the hook.
- Whether an inset shadow still covers all 17 to 31 short spots, and where the abutting flop sits relative to the `u_cf` edge.
- lepe proof10 hold classes and routed timing; the hook_ra arm; D27d2 and hub ring binds; pv bind 8c; gate J7g; t39 final GRT.
- kv3_sys_c -861.55 and whether D27d2 cures the pv landing band.
- Slip of mine: one helper script was written to and removed from `/tmp` on epyc10 instead of a lane tmp dir. Nothing else was created on any host.

## 4. failure_breakdown (11:10, technical lines only)

- TAP-INSERTION qwen_compute: 2,987 taps in 31 types, 68 over 1,650 sinks; insertion max 493 (p50 268, p90 285), skew max 137.
- TAP-INSERTION s81: 2,714 taps in 46 types, 123 over 1,650; insertion max 838 (p50 461, p90 495), skew max 328.
- TAP-INSERTION s81_head: 154 taps in 8 types, 0 over; insertion max 501, skew max 82.
- Kit rows by technical class: KV "over 400k cells" 2, "CLAND ring band" 5; QC "hold after CTS" 1 (slw_st_a_v2 cl9f076a5c).
