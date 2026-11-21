# FABLE-PD-KV-0730 (2026-11-21 05:37-06:05 PST): KV D27d structural review (plan 07a462a13e91) + the hroot and hgi private deltas

Reviewer: FABLE-PD-KV-0730 (Fable). Read-only: nothing launched, cancelled, signalled or patched. Plan JSON and report files were read in
place with short python (seconds, epyc8 / epyc2). Marking: **V** read this round, **R** reported by the owning lane, **I** inferred, **P** proposal.
Clock numbers are post-hook only (`OT_TAP_BALANCE done`, `OT_TAP_INSERTION`, `OT_CTS_POST_TIMING`); no `4_cts_final.rpt` number is used.
Earlier reviews stand (FABLE-PD-KV-2230, -1840, -1500; FABLE-CLOSURE-STRATEGY 05:25 levers 5 and 8).

Inputs (epyc8 /srv/opentallas-scratch2/claude): D27d plan `kv-plan-r3/d27c/tree/.../plan_of_record/plan_c.json` (= `fam-kv-hub-r2/ana/plan_d27d_base.json`,
byte-equal as JSON, V); G0 `kv-plan-r3/d27c/g0gate_d27d/g0/g0_report.json`; census `kv-plan-r4/d27d/out/census/ABS-CENSUS.tsv`; latency
`kv-plan-r4/d27d/out/d27d_latency/qwen_kvsys_latency.json`; hroot plan `fam-kv-hub-r2/launch_a5603p/.../plan_c.json` (3f4e0024a8d1) + its G0
`fam-kv-hub-r2/g0gate_a2`; hgi plan `opus-fix-kv-hgi-r3/launch_r3/.../plan_c.json` (152d6c878972). hroot kit: epyc2
`/srv/opentallas-scratch3/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D25d/items/kv3_hroot/attempt_5/gen/kv3_hroot`.

State at 06:00: D26 APPLIED 05:42 (R). D27d G0 PASS (0 errors, 2,483 warnings); D27d re-bind `bindgate_d27d_r5` at RC_ELAB (V). hroot G0 PASS, bind
running; hgi G0 and bind running, no `g0_report.json` yet (V).

## 0. Verdict

D27d is a correct step (0 census regressions, no pv rows, io_cor_v1 reset rows in), but it is **not** close-by-construction on four counts, and
its census line "HOP 662 rows / 22 types, worst 482" under-reads it:

1. **Hops over 405 um exist in D27d and the census does not see most of them (V).** (a) `kv3_hgi_v1` (both clones): `i_ectl_Q_N_tN` hop 4,
   1,560 bits, 482 um; G0 marks it `complete:internal_station` on both types. Neither delta touches it. (b) `kv3_hroot`: the relay chains
   dsel -> bin are 738 / 653 / 556 / 437 um (kvpc / slg / kvs fan / esh; `ana/h1_report.json` `before_max`). They are `relay_sites` chains,
   which `plan_geom_census` does not count: hroot has **no** row in ABS-CENSUS. (c) G0 `routed_reach`: 56 hops route over 405 um round blocking
   cores (hg 4 a type, hgi 2-3 a type; e.g. the head e0 kt row, Manhattan 223, routed 439).
2. **10,268 relay sites and 155 station registers sit inside hard cores (V, my scan of every type).** All 19 hg / hgi types: 476-544 kst
   relay sites and 7-8 kt station registers inside `head*_e2` / `e4`. Also `kv3_pv_v5` / `v5n`: the `o_kvs_ctl_dcfg__age_vport` row (the R8_STALE
   bus) has a station at (24.6, 1151.2) inside `pvg0_p0` (x 14.7-394.9, y 1097-1287) and hops of 382-386 um. ft slots: no bit site is inside a
   core on any type (the `regs_um` centroids of 162 ft stations fall inside cores on 7 hgi and 12 pv types, but their `bit_sites_um` are outside).
3. **Clock: 119 taps over the sink cap in 18 types (V, G0 `tapcap-count`).** pv_v6n `clk_t13` 4,306 sinks (cap 1,000); pv_v7 `clk_t9` 1,859;
   hgi_v8 `clk_t36` 1,651 (cap 1,200). 22 `xtap_latency` rows on pv (ft hops between different tap ports, window 192.5 ps, no lockup).
4. **Size: 6 pv types over 400k and 3 near it by the plan estimate (V, G0 `cell_budget`)**; the 11 unsplit pv kits measure 381-639k (R
   strategy section 4). D27d carries no split by design.

The two private deltas do not conflict with each other (section 4). Each has one structural gap (sections 2 and 3).

## 1. D27d against close-by-construction

| Check | Result | Evidence |
|---|---|---|
| Every placed hop <= 405 um | **Fail** on hgi_v1 x2 (482) and hroot (738); 56 routed-over rows | ABS-CENSUS: 662 HOP rows = 344 at 360-405, 188 at 330-360, 128 at 300-330, 2 over 405. Internal-station hops over 300 um: 2,492 (my count). ft slots: 906 of 1,017 have a hop over 300, 0 over 405 (pv 506 of 535, hgi 166 of 173). |
| Depth-aligned bundles | Not yet readable | First bind: R8 `groups_unequal 32` of 3,001, `replica_unequal 0`, `inversions 0`; 30 R8_STALE on `kvs_ctl.dcfg__age_vport_*` (bound 32 / 47 against table 31). `types_conflicting 7` are the owner strap sites (R). LATCHECK did not run (no `*_bound_top.sv`). |
| No station or relay site in a core | **Fail**, 19 hg / hgi types + pv_v5 / v5n | item 2 above |
| Reset legs within caps | Plan side passes; kit side unproven | EVENT-CENSUS `RESET_UM 300.0` OK on the 19 types that carry `relay_um`; io_cor_v1 has 41 `bank_taps` / 137 sinks, including the six `u_ft_ft16_o_*` banks of the 2,001 um failure (V). 53 R-REACH-6 ring-reset fans span 1,409-1,436 um and rely on the RING-RSTFAN-1 generator. pv reset (`u_rrl_928` 1,811 um, R) is not in D27d. |
| Tap / clock structure | **Fail** on pv (and hgi_v8 t36); hroot see section 2 | item 3; G0 `timing_audit` 21 rows (ring core `fclk` depth 208-638 ps, "no early tap") on hgi x11, pv x8, hub_C. |
| Feed-through capacity, hgi faces | Unchanged from D25e3 | Lever-8 rows are not in D27d. G0 worst partition segment 0.52 (`horizontal@17250:hgi_EN_5`), worst cut 0.16. `street_die_leg`: 256 die-lane station points fall on hgi head cores (lanes L341-L346, sys_c -> hub_C, 1-59 bits); the type ft bit sites are outside the cores, so this is a die-leg coordinate reading, not a placement (I). |
| Cells <= 400k | **Fail** on pv | pv_v2 / v2n 420k, v4 424k, v4n 437k, v5n 420k, v6 416k, v6n 423k OVER; v1 339k, v5 395k, hub_Ei 388k NEAR (+-25 %). hroot measured 126,451 non-tap at GRT (V). |
| Lane latency | Consistent, not gated yet | 2,404 lanes, 30,124 lane-cycles, max 107 (L2045 sys_SE -> hub_Wi, 522 b), 3 padded lanes (52 cycles, hub_Wi -> hub_Wo). Against D27c: 292 lanes changed, sum -439, no lane longer. |

G0 also repeats two "next plan event" items no row addresses: R-REACH-3 on hub_C (72 face buses, 7,760 bits over 200 um from their consumer,
worst `o_kvs_ctl_o_hroot_WS` 1,118 b x 1,129 um) and sys_c (30 buses, worst 552 b x 1,620 um).

## 2. hroot: is the -532 ps at tap t9 structural?

**It is real and it is created at global route; it is not a CTS-tree fault and not a pre-hook reading (V).** I agree with
FABLE-FIX-KV-HUB 05:41; the numbers below are my own read.

- Post-hook CTS (`4_1_cts.log`): `OT_TAP_BALANCE done: 236 delay cells; tap mean insertion 238..268 ps (spread 30, target 250)`;
  `OT_TAP_INSERTION tap=clk_t9 sinks=1478 ins_ps=280.2 skew_ps=47.7`; `OT_CTS_POST_TIMING setup_ws -39.71 hold_ws -303.02`. Clean tree.
- The same log already warns: `OT_TAP_SPAN limit 300 um: 10 of 41 taps over, max 454` (t9 447, t10 454, t17 423, t25 390); t9 holds 1,478 sinks against a cap of 1,500.
- `5_global_route.rpt` line 74: source latency 248.75, target latency 781.06 on `u_rly.fan_c[179]`, setup skew -532.31. This report is the
  **FF corner** (`OT_GRT_REPORT_CORNER FF`), so -532 is an FF number and must not be quoted as TT. The clock path to `fan_c[143]` (line 510-556)
  has seven `clkleafrepg_*` repeaters in series in front of `clkbuf_leaf_52_clk_t9`, then a 17-load leaf net with 102.9 ps of wire and
  325 ps slew at the CLK pin: arrival 615 ps against 215 ps at the launch flop (`clk_t20`). `OT_CLK_LEAF_REPEAT grt done: 21 nets repeated, 39 repeaters`, no re-balance after it.
- Scope: 14 `fan_c` CLK pins and 18 other CLK pins are over the slew limit; GRT max 114 %, 24,832 gcells over 90 %.
- TT at GRT is -753.66 (TNS -28.3k, 464 endpoints); the FF report worst max path is -474.94. The clock branch and the 336 ps wire on kc `rd_bin -> ko` are separate causes.

So: structural cause = tap span and tap load in the E strip (t9 447 um, 1,478 sinks) in a congested region; mechanism = the GRT leaf-repeat pass.

**Variant A (plan 3f4e0024a8d1) does not remove the cause (V).** Its diff against D27d is `kv3_hroot.internal_stations`, `kv3_hroot.relay_sites`
(3,895 changed, 784 added) and `clock.ring_hold.sender_ps_types.kv3_hroot = -50`; the hroot `clock` block is unchanged (36 added taps).
Assigning its relay sites to the nearest tap: `clk_t25` 1,057 sites, sink box 487 um, 89 sites beyond the 200 um radius; `clk_t40` 920 sites,
388 um, 83 beyond; `fan` now spans x 1509-1892, y 152-758. The t9 problem moves to t25 / t40. Hops: kvpc 390 max with 197 of 299 bits over 300; slg 321 with all 144 over 300.
Variant B (R: plan 9ec33fa3c347, kvpc +2 and slg +1 stations, 41 -> 52 taps, 0 sink boxes over 300 um, +12 lane-cycles on 8 lanes) is the right form; I did not read its plan.

## 3. hgi / hg kst re-site (plan 152d6c878972)

What it does (V): diff = `internal_stations` + `relay_sites` on 19 hg / hgi types, nothing else. Sites inside cores go 10,268 -> 0 relay
sites and 151 -> 0 kt registers. Station count kept, so 0 cycles. Max hop 355.3 (hg) / 330.5 (hgi).

Gaps (V geometry, I consequence):

1. **Every moved hop still crosses a whole head core.** hgi_v8 e4 row: (194.4, 682.56) -> (194.4, 563.76) -> (194.4, 327.24) -> (194.4, 233.28):
   the middle hop (236.5) runs across `head2_e2` (y 337-553). e6 row: (194.4, 1002.24) -> (194.4, 671.76) crosses `head2_e4`, and
   (194.4, 563.76) -> (194.4, 233.28) crosses `head2_e2`: 330.5 each. The stations sit on the core centre column (core x 86.4-302.4), so a route
   round the core adds 216 um: 453 and 547 um routed. G0 models the head cores as blocking (M1-M5; its e0 row reads 439 routed for 223 Manhattan),
   so `g0gate_r3` should report these under `routed_reach` / `station_core`. They close only as M6 / M7 over-core routes that rise at the core face.
2. **Clusters are single points 9.7-10.8 um from a core face.** Each kst group (34 bits) has one coordinate; e4 station 0 and e6 station 1 share
   the same point (x, 563.76): 272 flops there, 272 at (x, 671.76), and in the y 233-337 street 816 kst flops on one x (680 before). This is the
   face-gcell loading lever 8 set out to remove.
3. **The uniform kt-depth form became uneven hops**: 149.8 / 149.8 / 149.8 -> 118.8 / 236.5 / 94.0 (e4) and 256.3 x3 -> 330.5 / 108.0 / 330.5 (e6);
   hg head1_e4 has two stations 1.08 um apart ((764.64, 327.24), (764.64, 326.16)) behind a 355.3 um hop. That is the bunched-stage pattern measured on hroot.
4. The good form is already in the same plan: the e5 / e7 rows run in the x street (x 345.6; e7 has 5 stations), and hg head1_e6 was jogged to x 646.9 with three 334.8 um in-street hops.

Streets after the re-site, hgi_v8 (V): y 553-683 also holds ft4 station 2 (1,044 b, x 413-579), ft17 station 1 (552 b, x 380-467), ft26 station 0
(1,056 b, x 305-330, y 574-748), ft25 (256 b); y 233-337 holds ft25 station 0 (x 233-253, y 314-330), ft17 station 0, ring cores `cl_ft25_i`
(x 199-245, y 259-309) and `cl_ft17_i`. No moved site lands on an existing relay site (0 of 544). The measured hot zone (R: x street 302-389 at y 1000-1060, hst3_g + ft4 + ft26) is not touched.

## 4. Do the hroot and hgi deltas conflict?

**No (V).** hroot touches only type `kv3_hroot` and `clock.ring_hold.sender_ps_types`; hgi touches only the 19 `kv3_hg*` types. No key is
shared. The streets y 553-683 and 233-337 are in the hg / hgi type frames; hroot's coordinates ((1590, 710), x 1600-1900) are in the hroot frame
(outline 1900.8 x 838.08). Both were generated on 07a462a13e91, so they merge as three disjoint row sets; re-run both generators on the D28 base.
One caution: FAM-KV-HUB-R2 handoff step 3 proposes the same kst move that OPUS-FIX-KV-HGI-R3 built. Carry it once, from the hgi lane.
hub G0 `gone r_reach 1` + 61 new `station_core` rows are a newer-tool check on unchanged hg types, not a hub effect.

## 5. Ranked fixes

| # | Fix (P) | Evidence | Owner |
|---|---|---|---|
| 1 | pv split in D28 with its clock rows: every half <= 400k, taps <= cap with sink box <= 300 um, ring in the same half as its bus window, R8 table re-derived on the split. No unsplit pv kit. | 6 OVER + 3 NEAR (G0); 381-639k measured; 119 taps over cap, pv_v6n t13 4,306; split-10 bind 76 errors (R) | OPUS-FIX-KV-PV-R4 (successor R5) |
| 2 | hroot: carry variant B, not A. Gate the rows on one kit read at GRT: post-hook tap spread, no tap sink box over 300 um, and the FF `report_clock_skew` line on clk under 100 ps. | section 2; A moves 1,057 sites onto t25 at 487 um | FABLE-FIX-KV-HUB |
| 3 | hgi / hg kst rows: re-emit e4 / e6 in the x-street form (as e5 / e7 and hg head1_e6): leave the core S face, turn into the x street, stations at <= 300 um, per-bit sites spread along the street instead of one point. e6 needs +1 station; pad all 16 kt inputs to one depth (+1 cycle on the kt path, intra-partition). | section 3 items 1-3 | OPUS-FIX-KV-HGI-R4 |
| 4 | hgi_v1 x2: +1 station on `i_ectl_Q_N_tN` hop 4 at the turn ((320, 640) -> (320, ~900) -> (133, 935): 260 + 222 um), +1 cycle on that bus, R8 kept equal across the two clones. | 482 um, 1,560 bits, G0 `complete:internal_station` | OPUS-FIX-KV-HGI-R4; row to KV-PLAN-R5 |
| 5 | pv_v5 / v5n `dcfg__age_vport` row: move the station out of `pvg0_p0` and add 1 station (hops 382-386 -> under 300) in the same pass that refreshes the 30 R8 rows, so the table is refreshed once. | section 0 item 2; R8_STALE bound 32 / 47 vs 31 | KV-PLAN-R5 (refresh now); OPUS-FIX-KV-PV-R4 (row, D28) |
| 6 | Make `plan_geom_census` count `relay_sites` chains and ft slots, so the event line stops under-reading (hroot 738 um is invisible today). Estimator only. | section 0 item 1b | KV-PLAN-R5 -> PRECHECK-1119 |
| 7 | hgi_v8 `clk_t36` 1,651 sinks: one added tap; pv xtap hops: same-tap re-assignment or the proven lockup form only. | G0 `tap_sink_cap`, `xtap_latency` 22 | OPUS-FIX-KV-HGI-R4; OPUS-FIX-KV-PV-R4 |
| 8 | io_cor_v1: read the first D27d kit post-hook for `u_rrl_67 -> ft16`; confirm the 41 `bank_taps` tap ids (1-50) against the reset tree of the D27d bind before volume. | rows present (V); tap-id check not possible from the plan (section 7) | FAM-KV-IOPC |
| 9 | hub_C / sys_c window moves (R-REACH-3) as D28 rows or an explicit deferral. | 7,760 bits, worst 1,129 um; sys_c 1,620 um | FABLE-FIX-KV-HUB |

Flow item, already posted by FABLE-FIX-KV-HUB to FLOW-NOADV-R3 (I confirm the evidence): `clk_leaf_repeat.tcl` GRT pass repeats one branch and does not re-balance.

## 6. What D28 must carry

1. pv split + pv clock / tap rows + pv reset rows (two-pass on the split bind) + pv relay_depth legs + pvx_regen column law (fix 1).
2. pv_v5 / v5n age_vport station row (fix 5).
3. hroot variant B rows + taps + `sender_ps_types.kv3_hroot`, after its GRT read (fix 2).
4. hg / hgi kst rows in the x-street form, generated on the D28 base (fix 3); hgi_v1 ectl station (fix 4); hgi_v8 t36 tap (fix 7).
5. hub_Eo / hub_Wo / sys_c reset pass 2 on the D27 plan, hub_C split if FABLE-FIX-KV-HUB posts one (R, KV-PLAN-R4 section 3).
6. hub_C / sys_c window rows or a written deferral (fix 9).
7. Lane latency re-emitted once, after rows 1-6 (+12 lane-cycles hroot B on 8 lanes; +1 ectl; kt path intra-partition).

## 7. Stop list

- Do not quote D27d as "worst hop 482, 662 rows": hroot relay chains (738 um) and ft slots are outside that census.
- No hroot variant A kit and no variant A rows in D28.
- Do not carry the kst rows of 152d6c878972 into D28 unchanged; the hgi_v1 proof kit to GRT iteration 10 may run as the measurement.
- Do not carry the kst move twice (hub handoff step 3 and the hgi lane are the same row set).
- No unsplit pv kit on any plan; the 11 running ones cannot sign (R). The cancel is COORD's call.
- Do not read `5_global_route.rpt` slack or skew as TT (FF corner); do not read `4_cts_final.rpt` at all.
- No `bank_taps` volume before the tap ids are checked against the tree of the plan they are in (standing item from -2230).
- No second R8 refresh for the age_vport rows: one refresh, with fix 5 decided first.

## 8. Not checked

- `g0gate_r3` (hgi) had no report at 06:00: section 3 item 1 is my geometry, not yet the tool's `routed_reach`.
- Variant B plan 9ec33fa3c347 and its G0 / bind: reported only.
- gcell size against the 9.72 um margin; over-core M6 / M7 capacity on the head cores.
- io_cor_v1 `bank_taps` tap id -> xy (ids index the reset tree, not `local_taps_um`); why FAM-KV-IOPC proof_B died at 05:03.
- TT worst path of hroot at GRT (only the FF report lists paths). hub_Wi and hgi_v8 D26 pilots. pv split plan 086a50a08e27.
- The nearest-tap assignment in section 2 is a plan-site estimate (flow assigns with the cap); FABLE-FIX-KV-HUB's replay gives t25 497 um / 1,214 sinks.
