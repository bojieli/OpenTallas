# FABLE-CLOSURE-STRATEGY 2026-11-15 09:3x PST: eight levers, RESETN seam class, stop list

Read-only review by FABLE-CLOSURE-0910. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 07:3x strategy (kept below), FABLE-PD-S81-0850, PD-PLACE-0830, PD-S81C-0730 sections 7-8, PD-HEAD-0700, PD-KV-0800,
PD-QC-SUC-0800, PD-QC-0700, FABLE-S81-TYPEMERGE, `failure_breakdown.py` (09:11), `KIT-WAVE FAIL` 07:10-09:04, the handoffs,
the queue to line 13995, and the seam RTL (`rtl/common/landed_parent/ot_pl_seam.sv`, main).
MEASURED = read by me today. REPORTED = from a lane or review file. INFERENCE is marked. I ran no STA and no what-if.

`failure_breakdown.py` 09:11, technical rows only: S81 types 36/394 (69 running, 3 route held, 3 held for the event, 1 RTL
lint); HEAD 19/26 (7 running); QC 3/127 (50 held for the event, 31 running, 11 route held, 5 place error); KV 5/56
(28 running, 14 held, 2 global place, 1 place). No congestion, DRC or post-route timing class is listed on any of the four dies.
Wave failures 07:10-09:04, design classes only: ring band blocked 4 (KV hgi_v6, hub_Wo), `cland_col_cursor` 6 (KV), LEC 1
(QC slw_hc3), GEN_LINT `defparam LOCAL` in `ot_dp_clk_landing.sv` 9 S81 slice_station types + lepe_nh_mus_LP. The rest
(STALE-CORE-VIEW 58, bootstrap gen 22, place RC 0 on another host 16 + 18 quoted as "plan geometry") are tool classes.

## 0. What changed since 07:3x

1. Three dies are about to rebuild nearly all their types (S81 B6gE about 13:00, QC S4q3, KV 7u). None of those kits
   reserves the sites of the die clock cells. If the types sign first, the HEAD result (lever 1) repeats on each die
   and every type re-keys once more. The reservation belongs in these three events, not after them.
2. The col RESETN at -183 ps is a family item: every col family carries the seam writer that makes it (lever 3).
3. KV 7j is adopted (08:47). HEAD NF6 is adopted. The p6 M8 grant reaches 0 overflow at GRT (was 106 %).
4. Two one-line or one-step fixes named at 08:30 and 07:30 have not moved (section 2).

## 1. Levers, ranked by types or dies unblocked

| # | dies | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | HEAD, KV now; S81, QC before their events sign | Die clock cells under partitions: reserve the sites in the type, cut the abstract, drop the GRT-only obstructions | the die DRC gate of all four dies; avoids a second re-key of about 500 types | DIE-ROUTE-ABS-1 (tool), HEAD-100, KV-102, DIE-S81-92, DIE-QC-103 |
| 2 | S81 | One stacked event B6gE with one compose last; sign-off key = layout hash | 350 held types; 395 builds down to about 212, then 198 | DIE-S81-92, S81-TAPROWS, S81-PHYT1, S81-CA-BAND, S81-TYPEMERGE-IMPL, S81-LEAF-PLAN |
| 3 | S81 | Seam writer async clear (RESETN): site the reset leaf at the station; registered per-chunk clear if needed | all 216 col types (12 families) | TL-COLH9R0P6 (STA + pilot), new lane S81-SEAM-RST (generator), DIE-S81-92 (event) |
| 4 | QC, KV | Buses that cross a type in one cycle: station rows per matched group, and a placed-dump scan on every type | QC su_c 3, fw / st_b about 45; KV pv 11, hg / hgi 19 | QC-FWST, DIE-QC-103, KV-102, KV-PVGEN, KV-ECTLK-RL; scan = new lane |
| 5 | KV, S81 | Clock landing ring bands: two-column floor, band order, tap sites as obstacles | KV 19 hg / hgi + hub_Wo + io types; S81 11 band-less types (7 svc, leaf t8 / t72, t51) | KV-102 (7t), S81-CA-BAND, S81-PHYT1, TYPES-KV-FAIL (cursor line) |
| 6 | QC, KV | Latency literals and pad tables tied to a lane depth: regenerate in the bind chain, straps in hard cores | QC S4q3 / S4v2 / S4fw adoption, 4 sta_region parents; KV krsp +5 | DIE-QC-103, HCPARAM-ALL, KV-ECTLK-RL, KV-102 |
| 7 | S81 | col p5 / p6 frame channel: M8 E-W grant as a die key | 24 col types (12 p6, 12 p5) | TL-COLH9R0P6, DIE-S81-92 |
| 8 | S81, KV | Core clock reference: one tap row per core at the signed value; macro clock pins ahead of their registers | bksel_q then bk_sel__t2; 216 col types; kv3_hub_C | CORE-BKSEL-1115, S81-TAPROWS, KV-102 (7q) |

### Lever 1. Die clock cells under the partitions (cross-die)

Evidence:
- REPORTED (FABLE-PD-HEAD-0700, epyc2 `die-head-route-1/head/p20nc_gate/unitruns/probe_u201_b/drc_TT.rpt`): 2,800 markers,
  2,788 within 0.5 um of a die clock inverter, on 250 sites; 600 of 606 clock cells of the unit lie inside a tile. What-if on
  u201: as built 3,276 / 2,786 / 2,800 / 2,679; windows at the cells 621 / 96 / 96 / 74; windows plus no GRT-only obstructions
  340 / 44 / 44 / 21 (19 of the 21 are M8 min step on the clock wire itself). 0 was not reached in 4 steps.
- MEASURED (epyc2 `die-route-abs-1/r_cut2`, the lane's own cut database): iteration 0 at 80 % shows 481 violations, against
  3,276 as built. It agrees with the what-if.
- REPORTED (DIE-ROUTE-ABS-1 handoff): cells under a partition: HEAD 44,519 of 44,547; KV 32,280 of 32,280; QC 127,101 of
  127,106; S81 no kit tree found (the B6gsh clock kit has 91,460 die clock cells, 0335 H). Tool `abstract_cutout.py` and the
  kit flag `--cut-abstracts-under-clock` are on a branch. "Per-type site reservation not started. M8 step unassigned."
- REPORTED: HEAD declares 63 islands per tile in one row; 3 of 600 cells are in one. KV: 437 of 32,856 in a declared island.

Root cause: `die_trial.SiteMap` allows a die clock cell anywhere in a partition outside hard cores. The type under it never
kept that site free, so on a signed type the conflict is real metal, and the abstract cut alone hides it. The M8 / M9
residue is `grt/obs.tcl` (clock track reservations and PG copies) left in the route database.

Fix, in this order:
1. DIE-ROUTE-ABS-1: finish r_cut2, then one u201 run of 12 steps with the cut and with the `obs.tcl` obstructions removed
   in `unit_prep.py`. That is the one-unit-at-0 proof. Assign the `obs.tcl` removal to this lane now; it has no owner.
2. HEAD-100: one clock site template per type (mirror the R0 tree for MY / MX / R180), written as `clock.die_islands_um`,
   kit built with `--island-sites`, windows cut on M1-M7. hd_tile is one type for about 300 instances: rebuild it once with
   the islands as placement and M1-M7 routing blockages. Check first whether the signed hd_tile is empty at the sites.
3. DIE-S81-92, DIE-QC-103, KV-102: run the `abstract_cutout.py` dry run on the current die clock kit, take the per-type
   window list, and put it into B6gE, S4q3 and 7u as type blockages. Cost per type is small (HEAD: 5,511 um2 of 6.6 mm2).
   If the die tree is not final, reserve the windows of the current tree and make the tree snap to reserved sites later.
   S81 start-stage flops (2,430) take the same rule.
4. Measure memory on the real fix before unit volume: the what-ifs peaked at 83 and 99 GB against 9.4 GB as built.
Unblocks: HEAD die DRC (about 12-14 h of unit passes after item 1), KV die DRC, and one avoided rebuild on S81 and QC.

### Lever 2. S81 stacked event B6gE

Evidence (REPORTED, FABLE-PD-S81-0850; DIE-S81-92 handoff 09:03):
- B6gslswrp compose: 0 band failures of 1,255 (was 17); lane sums equal B6gslsw. B6gslcf / B6gshcf failed and are closed.
- Risks measured: 22 bands with a pin hop of 401 um or more against the 402.84 limit, 4 bands with a 2.16 um side; strap
  window margin 105.5 / 106.0 ps against 100; E2 as built sat on a composed plan (withdrawn 09:02, now rows).
- Type merge: 395 types hold 187 physical problems. Layout hash without the child instance name: col 216 -> 33 builds.
- svc: with `tap_clear_um` 4.32 no sink is farther than 26.3 um from a tap site (was up to 624 um).

Fix: as ordered in 0850 section 3: adopt the first candidate that binds; then one event on `B6gsl_or13_rp` with rows only
(tr4 + idx, PHYT1 with svc `tap_clear_um` and reserved tap sites, TYM keep_outs + R2, R4 re-run, E2 by rows_merge), one
compose last, then G0, bind, LATCHECK, bind_reset diff. Add to the same event, because the col and svc types regenerate there:
- the clock site windows of lever 1;
- the seam reset siting of lever 3;
- `die.layer_budget.type_m8_grant` for the 24 p5 / p6 types (lever 7): confirm the key is in the B6gE base, it is in B6c4;
- R1 with `collector_children[].part` out of the hash (TYPEMERGE 5.1). It is no design change and is worth 183 builds.
Pilot before the svc wave: GPL + CTS on svc_hi t6 and t3 (S81-CA-BAND). Re-plan the strap table after any die clock re-route.

### Lever 3. S81 seam writer async clear (the RESETN class)

Evidence:
- REPORTED (TL-COLH9R0P6, queue line 13981, form fd GRT repair): worst RESETN -603 ps at iteration 0, -183 ps at iteration
  250. Sink: 24 `DFFASRHQNx1` of `u_u_lpl_6_w.u_y_w` on net `clr_n[0]`, driven by one NOR2x1. Netlist read only, no path report.
- MEASURED (`ot_pl_seam.sv` 201-244): `ot_pl_seam_w_plr` drives `ot_pl_seam_cq` with `clr_n = rsi & {CHUNKS{e}}`. `rsi` is an
  input port (one reset leaf per 24-bit chunk); `e` is a local flop `rq` (async clear by `rse`, D = `rse`). The gate is
  combinational and sits on an async pin, so the recovery path is: last stage of the reset delay chain -> wire -> NOR -> 24 pins.
- MEASURED: `ot_pl_seam_r_plq` also uses `ot_pl_seam_cq`, but its clear is the local registered `wq`: a short path. Not this class.

Answers to COORD:
1. Count. The module is referenced only from the S81 col frame generators (`rtl/dsrom_sys/s81_dv/frame_lp`, `tools/s81_dv`).
   Frame RTL: 20 writers in col_h9, 22 in col_h10. Bound kit RTL on epyc7 (wave runs 7073a6b4a59 / 3fa87b84b18): every col
   family read has it: h9_r0_p1..p6 about 4-5 each, h9_r1 about 6-7, h9_r2 about 2-3, h10_r0_p4 about 2-3, h10_r2 about 4-5
   (grep hits; h10_r0_p1 and h10_r1 had no kit RTL on that host). So 12 families = all 216 col types, 14-33 builds after the
   merge. Other dies: 0 instances in `rtl/` and `tools/` on main; HEAD, QC and KV do not use the seam station.
   The neighbouring class on other dies is reset relay reach (KV pv: relay to RESETN 650-1,070 um, -411 ps), a different cause.
2. Fix. The registered per-chunk clear is the right structure, but take the cheaper step first, in this order:
   a. TL-COLH9R0P6: `report_checks` to one RESETN pin on fd `4_cts.odb` (10 minutes). It splits the -603 into launch clock,
      wire from the `d14` last stage, the NOR, and the fan-out. INFERENCE: -603 at iteration 0 is about 1.1 mm of wire at
      1.24 ps/um, so the last stage of the 14-stage `ot_dp_dly` is not at the station.
   b. Siting, no RTL change: put the last `d14` stage of `rsi` and `rse`, the `rq` flop and the NOR into the station's
      `relay_mid` group, and spread the other 13 stages along the route (the `dly_spread` hook QC already uses on
      `ot_dp_dly` pipes). The recovery path is then local. No LEC, no latency change.
   c. If (b) leaves it negative (one NOR2x1 on 24 clears spread along the seam): registered clear per chunk, cycle-neutral:
      tap the chain one stage early (D = 13), `rq2 <= rse13`, `c[k] <= rsi13[k] & rq2`, and `clr_n[k] = c[k]` straight from
      the flop. Release is the same cycle as today. Assertion can differ by one cycle while `rse` falls, so run the
      `tb_ot_pl_seam` miter and bind_reset before use. It also removes the gate from the async pin.
   Do not make the station flops synchronous-clear: that puts a gate back on the D pin of a relay-placed station.
   Timing repair cannot close it (350 ps gained in 250 iterations, still -183).
3. Owner. TL-COLH9R0P6 keeps (a) and the pilot on fd. The generator change (b) in `frame_seam_pipe.py` / `relay_mid.tcl`
   is a new Sonnet lane, S81-SEAM-RST, reporting to DIE-S81-92, landed with B6gE. (c) needs the RTL owner and the miter.
   Gate: recovery and removal >= 0 at CTS on one h9 and one h10 type before the col wave.

### Lever 4. Buses that cross a type in one cycle (QC and KV)

Evidence (REPORTED):
- QC su_c (PD-QC-SUC-0800): slw_su_c has 7,037 zero-logic bits over 405 um, 3,453 over 580 um; one source register feeds
  both side faces 1,207 um apart. sle_su_c with 4 stations still has CTS WNS -487 ps. 3 types, 12 instances.
- QC fw (PD-QC-0700): sle_fw_v2 `x_fe_p1_i` 818 pairs over 405 um, -467.6 ps placed; S4x mirrored 117 rows onto the wrong face.
- KV pv_v1n (PD-KV-0800): 389,907 cells at 2.9 % utilisation; setup -1,573 ps on 17,239 endpoints, 310 k repair buffers,
  register-to-register up to 3,009 um, clock skew 439-493 ps. The split fixes none of it.
- KV hg: krsp fan-out to four ectl cores spans 915 um; ruling krsp +5 on all frames, round trip 26, QK 37.
- G0 does not see glue sources: S4q2 G0 reports 2 hops on slw_su_c where the placed dump has 636 groups.

Fix:
1. QC-FWST: su_c rows of PD-QC-SUC section 3 (8 lanes, about 15 banks per type, `u_twb` at x about 570) on the S4fw4b line,
   with the `qc_fabric_transport` replay before the bind. DIE-QC-103 adopts.
2. KV-102 / KV-PVGEN: pv stations per matched group on all 11 pv types (7r), from the family listing on the attempt_7
   `4_cts.odb`; clock sinks off the macros. KV-ECTLK-RL: the four cores at 37 / 26 in the same event as krsp +5.
3. New lane: the placed-dump scan (`zl.py`, 580 um, non-strap groups, 20 s) as a post-place check on every type of the four
   dies. It would have stopped su_c, pv_v1n and hg at placement. Run it now on the held placed hg_v1 / v1p3 / v1p4 databases.

### Lever 5. Clock landing ring bands

Evidence: KV hgi_v8 ring ft20_i is 8.64 x 84.24 um, needs 222.5 of 727.8 um2, and finds no legal site (PD-PLACE-0830 C).
KV-BAND-C widened 259 of 360 hg / hgi bands to 17.28 um (7t, in gates). MEASURED in the wave log: kv3_hub_Wo fails the same
way at 08:36 on a `literal-local-reset` band, which is outside the 19 types 7t covers. S81: 22 form J bands at 401-402.8 um.
Root cause: one-column bands, filled after firm cells that already sit in them.
Fix: KV-102 extends the two-column floor to every KV type with a ring or local-reset band (hub_Wo, io_cor, io_ft) in 7u.
S81-CA-BAND keeps reserved tap sites as band obstacles and runs the svc pilot. TYPES-KV-FAIL installs the one-line
`set cland_col_cursor {}` (section 2).

### Lever 6. Depth literals and pad tables

Evidence (REPORTED): QC `cb16_pads_hbm_codex.json` keyed to the old bound depth drops 48 members = 24,672 bits (replay
predicted the exact count); S4x needs +2 on both st_a return lanes; 4 sta_region parents differ in 32 parameters from the
bound RTL; 3 sta_region masters (n6_s7, n6_s8) have no kit row at 09:11. KV: qkd_ectlk_q0..q3 hold RESPONSE_LAT / QK as
literals. QC slw_hc3: LEC fails on 51 of 112,450 points, async-reset registers 367 against 365, after 9.8 h.
Fix: DIE-QC-103 regenerates the pad table in `bind_chain.sh` for every variant, and reads the 2 lost async-reset registers
of slw_hc3 from the bound against the gate netlist (xl3 l3 path) before any rebuild. HCPARAM-ALL makes SKEW_N / SKEW_S and
the ectl depths strap inputs, so the next station event rebuilds no hard core. No second depth change on KV after 37 / 26.

### Lever 7. col p5 / p6 M8 grant

Evidence (REPORTED, TL-COLH9R0P6 09:10): form fd with the M8 E-W grant: GRT 0 overflow on M2-M8 in 15 extra iterations,
M8 use 3.12 %. Before: 832-850 overflow units (fa), 106 % and 36,026 gcells over 90 % (keeper).
Fix: the grant is a die key; DIE-S81-92 carries it in B6gE for the 12 p6 and 12 p5 types. Then lever 3 is what is left on p6.

### Lever 8. Core clock reference

Evidence (REPORTED, PD-S81C sections 7-8): bksel b1c pin-register mean 790.1 TT / 635.0 FF, real spread 83 ps; FF hold
3,501 of 3,888 endpoints are macro pins (pk2 clk lands 48 ps after its registers, lib hold 125). The stage SDC still had
975 until patched. col types carry two tap rows per half (437 / 533 and 476 / 553) against the signed 465.39. KV hub_C
`kvs_ctl.ck` is 603.2 against a signed 283.5.
Fix: CORE-BKSEL-1115 finishes b1o / b1g with every ETM clock pin at least 100 ps TT ahead of its registers, none negative.
S81-TAPROWS: one row per core at the signed value in B6gE (the tr4 step). KV-102: 7q with kvs_ctl and both views attached.
QC cb tile taps over T/2: answered by DIE-QC-103 08:45 (fixed in main `tap_offset_table`); closed.

## 2. Items from earlier reviews that are not moving

| item | since | state at 09:3x | action |
|---|---|---|---|
| `set cland_col_cursor {}` in `landing_placement.tcl` | 08:30 | KV io_ft_v1 failed again at 09:03; 6 failures since 07:10 | TYPES-KV-FAIL, this hour |
| Remove `grt/obs.tcl` obstructions before DRT | 08:1x | handoff says "unassigned" | DIE-ROUTE-ABS-1 |
| Per-type clock site reservation | 07:3x | "not started"; three dies regenerate today | lever 1 item 3 |
| Placed-dump zero-logic scan as a gate | 07:4x | no owner | new lane |
| Hold ECO: non-port scope, 5 ps target | 07:3x | no real-kit run found in my reads (not verified further) | FLOW-LATEECO first run on t47 |
| sta_region n6_s7 / n6_s8 masters | 07:3x | "no kit-wave row" for 3 cores | HCPARAM-ALL |
| Family listing on held placed hg_v1 / v1p3 / v1p4 | 07:55 | no post found | TYPES-KV-FAIL |
| 45 S81 lanes over 405 um after LT2; 48 long start hops | 05:1x | ruling given for the start stage 08:55; lanes have no owner | DIE-S81-92 after B6gE |
| GEN_LINT `defparam LOCAL` in `ot_dp_clk_landing.sv` | 08:53 | 10 S81 types fail at gen; cause not read by me | DIE-S81-92 names an owner |

Place results lost when the job ran on another host (14 of 18 "place failures", PD-PLACE-0830) are a tool class, owner
WAVE-COPYBACK-1115. They matter here only because they hide the real place classes above.

## 3. Stop list (technical dead ends)

1. No more DRT iterations, unit volume or KV units on the current abstracts; no full-die single-process detail route.
2. No abstract cut used as a result on a signed type that is not empty at the sites.
3. No regenerating abstracts with "pin shape on the plan layer only": no abstract pin is in any marker.
4. No timing repair or relaunch for the col RESETN; no synchronous-clear seam station.
5. No builds on B6gslcf / B6gshcf / B6gshcfrp / TYM1-3 / TYM3J; no row patch on a composed plan; one compose, last.
6. No release of the 11 band-less S81 types from B6gslsw; no svc wave before the t6 / t3 pilot.
7. No kv3_pv_v1n split, no 7g, no L2359 work; no adoption of 7m or of 7n as built.
8. No routing of the held kvgeom5 hg builds; no unchanged relaunch of hg / hgi, su_c, fw or pv types: they are -450 to
   -1,570 ps at placement by plan.
9. No second ECTL depth change; no tap row from the unsigned ahub eco1 record.
10. No S4r4 / S4r5 sign tests, no S4x as built, no station on one leg of a matched join.
11. No bksel kit at vclk 975, no B2, no 700 ps gate; no `b1g_class.tcl` counts (no parasitics).
12. No tuning of kvgeom6 ring bands; judge on 7t / 7u kits.
13. No slw_hc3 rebuild before the 2 async-reset registers are explained.
14. No allow-congestion form on col p6 (fc); the grant form replaces it.
15. Still in force: 07:3x items 5, 6, 8, 10-13 and the 05:1x items 5-9.

## 4. Not verified

- Lever 1: 0 violations on a unit; whether signed hd_tile is empty at the sites; the S81 and QC window lists.
- Lever 3: no STA path report exists. The wire-length reading of -603 is inference. The instance counts are grep hits in
  bound kit RTL of one type per family. The one-cycle assertion difference of form (c) is not simulated.
- Lever 5: the occupant of the hub_Wo band. Lever 6: the slw_hc3 register names.
- Bind and LATCHECK of B6gslsw / B6gslswrp, S4q3, S4fw4b, 7q-7t were running; every adoption above is conditional on them.
- I did not check that `type_m8_grant` is in the B6gE base plan.

---

# PREVIOUS VERSION (07:24 file, sections dated 05:1x and 07:3x), kept unchanged

# FABLE-CLOSURE-STRATEGY 2026-11-15 05:1x PST: technical closure levers for S81, HEAD, QC, KV

Read-only review. Technical physical design only. HBM is parked. No job, plan or kit was touched.
Previous version (03:2x, with the 01:3x review below it): the commit of this file before this one in the `~/coord` history.

Sources: FABLE-PD-S81-0335 (A-C), FABLE-TRIAGE-HEADKV 15-21, FABLE-KVOVF 8-13, FABLE-PD-QC-0300, the queue to 05:14,
`failure_breakdown.py` (05:10), `autopilot/kit_wave_stages.tsv` (05:07), and my own reads of the run directories below.
MEASURED = read by me at 05:1x from a log, table or process list. REPORTED = from a lane post. INFERENCE is marked.

`failure_breakdown.py` technical classes at 05:10: timing after route 3 (S81 slice_station__t47; KV kv3_phy_v1, kv3_sys_SD),
place error 2 (S81 slice_station t17 +1). Everything else is running, held or a flow class.

## 0. Four things the lanes have not seen

1. The HEAD region route units do not converge, and the residue is not a routing problem. Three units of 141 clock
   nets each stand at 2,750-2,850 violations after iteration 2, with the same count on five layers (lever 2).
2. QC and KV types go into detail route with setup already 130 to 1,550 ps negative. The route then runs for hours
   on a design that cannot pass the -42 ps gate (lever 3).
3. The S81 count-aligned plan passes on the adopted clock kit, but its compose step fails on the hard PHY wrappers
   and reports 5.6 million added flops. The 350 types wait on that (lever 1).
4. QC has no row on the adopted S4k event yet, and 13 KV types fail generation on one tool error (lever 4).

## 1. Levers, ranked by types or dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | Count-aligned compose: one landing per hard PHY wrapper; explain the 5.6 M flops | 350 held types | DIE-S81-92, KIT-OPS-6 |
| 2 | HEAD, KV (then S81, QC) | Die route units: remove the fixed-shape violations before volume | the DRC gate of every die | DIE-HEAD-ROUTE-1, DIE-KV-ROUTE-1 |
| 3 | QC, KV | Read setup after CTS; start the structural fix then, not after the route | about 20 running types now, the family behind them | DIE-QC-103, KV-102 |
| 4 | QC, KV | Generation: S4k rows, pruned bind sources, `tap_offset_table` | QC 36 types, KV 13 types | KIT-OPS-5, GENBUG-IMPL, KIT-OPS-6 |
| 5 | S81 | Leaf kits fail before placement on B6gsh itself (3 defects) | 79 leaf types, the LT2 proof | S81-LEAF-PLAN, GENBUG-IMPL |
| 6 | KV | kv3_hg / hgi: kvgeom7 with a two-level reset tree and a start-broadcast stage | 19 hg / hgi types | KV-102, FABLE-KVOVF |
| 7 | HEAD | NF adoption: relay pin lists differ between copies of hd_spn and hd_spn_wshim_rx | 26 types | HEAD-99, HEAD-CLKFEED-1 |
| 8 | QC | cb family: S4p/q/r, and the ring-to-load site form that has no owner | 17 cb types | DIE-QC-103, CLAND-BIN |

### Lever 1. S81: the count-aligned compose

Evidence:
- REPORTED (DIE-S81-92 05:13, epyc7 `die-clk-s81-b6/s81/B6gsh/ca_g3f`): on the adopted B6gsh clock kit with measured
  fall arrivals: 2,330 crossings, 0 without K, depth 4/8/16 = 1,377/953/0, worst lo 104.5 ps, start tree 555/555
  clean (15 unclean with rise only). Plain and strap-form binds pass with 0 violations. Same form on B3x2d:
  1,683/647/0, 556/556 clean.
- REPORTED (DIE-S81-92 05:09, `ca_compose/compose_report.json`): compose of B6gsh with that table fails:
  `hard partition phy_hbm: exactly one landing per hard wrapper supported, got dfi_i0..dfi_i7`. Requirements line:
  9,320 new scalar pins, 5,612,245 added live storage flops, 395 types. Today's sidecar has 993 crossings.
- The hop-limited form fails (66 start edges), so the plan has no reach check on its 555 start hops.

Root cause: the identity part map gives every hard PHY wrapper several regions, so one wrapper gets several
landings. The table also moves 1,337 crossings from the fixed +3 form to rings. INFERENCE: the 5.6 M flops are
ring storage counted at full bus width times depth for all 2,330 crossings, about 2,400 flops per crossing.

Fix (DIE-S81-92; KIT-OPS-6 for the tool):
1. Hard wrappers keep one landing: merge each hard partition's regions into its wrapper region in the region table
   (the `merge_hard` form), then re-plan. Check that the 8 `dfi` buses still get one K each; if their windows do
   not overlap, they stay on the fixed +3 form, which the PHY has today.
2. Before the bind, split the 5.6 M by type and by depth. Depth 8 on 953 crossings is the cost. Give the per-type
   added area against the free area of the 350 types; a type over its outline is a plan change, and it must be
   known before 350 kits regenerate.
3. Start-hop reach: list the start hops over 405 um from the plan (66 edges fail the limit). Each needs a retime
   site or is declared and measured; do not leave it unread.
4. Then bind + LATCHECK, release the 350 once.

### Lever 2. Die route by region units: fixed-shape violations

Evidence (MEASURED, epyc2 `/srv/opentallas-scratch3/claude/die-head-route-1/head/p20nc_gate`):
- `units/units.log`: 326 units, 44,549 nets all assigned, 1 merge, 11 passes (sizes 40/42/48/42/40/40/32/21/14/5/2).
- Three units, 141 own nets each, started 03:56-04:03. Form (a) full die: iteration 0 ends at 3,833 / 3,276 / 4,151
  violations; 11.6-12.0 GB; still in iteration 1 after 75 min. Form (b) crop (6.7 mm2): the same iteration-0 counts
  within 1 (3,887 / 3,276 / 4,152), then 2,856 -> 2,852 (u198), 2,786 -> 2,800 (u201), 2,758 -> 2,769 (u261);
  3-7.6 GB; in iteration 3 after 70 min.
- u198_b after iteration 2, by layer: Short M1 691, M2 252, M3 252, M4 252, M5 252, M6 252, M7 298, M8 183;
  Metal Spacing M1 50, M8 274; Min Step M8 79. The own nets have 5 / 20 / 3 / 3 / 26 um of wire on M3-M7 and
  6.4 / 4.6 mm on M8 / M9. The database has 9 fixed shapes on M2 and 9 on M3 in the region.
- No marker file is written, so the violating shapes are not named.
- The full-die run (`p16g/drt7_small96_TT`) started iteration 0 at 03:38 and has printed nothing since (95 min).

Root cause: the residue is the same on every unit and does not fall between iterations, so no number of
iterations reaches 0. INFERENCE: 252 shorts on each of M2-M6 with almost no wire there is one via stack per
terminal, dropped from M8 to a pin shape on M1 through the partition abstract (about 250 terminals per unit).
The M8 part (spacing 274, min step 79, short 183) is the landing at the M8 pin against the region PG grid.
The crop form agrees with the full-die form at iteration 0, so the split itself is sound.

Fix (DIE-HEAD-ROUTE-1; DIE-KV-ROUTE-1 uses the result):
1. Rerun one unit in form (b) with `-output_drc` and 3 iterations. Group the markers by layer and by the two
   shape owners (own net, PG, abstract pin, abstract obstruction). This takes about 30 minutes and decides the rest.
2. If the M1-M7 shorts are stacks to lower pin shapes: the die abstracts must carry one pin shape per die pin, on
   the plan pin layer (M8, or M7 for the 133-168 clock pins the wave reports "on M7, not M8"), and no lower shape.
   Regenerate the abstracts; no type is rebuilt.
3. If the M8 part is pin against PG: cut the region grid over the pin window (the `clock_entry_pg_cut` form the
   kits already use inside a type).
4. Do not start the 326-unit volume, and do not start KV, before one unit ends at 0. A pass costs about 440
   thread-hours.
5. Use form (b) for volume (same counts, a third of the memory, faster). Stop the full-die run and the three
   form (a) units once item 1 is posted.
6. Timing of (b): at 0 violations a unit should take about 3 iterations. From today's 20-25 min per iteration,
   11 passes are about 12-14 h of wall time if each pass has its threads. That closes HEAD on 11-16, not today,
   and only after items 1-3.

### Lever 3. QC and KV types: setup is lost before the route starts

Evidence (MEASURED, `run_route.log` / `pregrt_ff_hold.log` of the running kits, line `OT_PREGRT_FF_HOLD ... setup_wns`):

| die | type | setup before route, ps | cells | note |
|---|---|---|---|---|
| QC | cbn_q11 cl49ae4555 | -861 | 365 k | 10,948 hold cells |
| QC | sle_fw_v2 cl69f5e854 | -453 | 403 k | hold still -92 ps on 515 endpoints |
| QC | slw_fw_v3 | -380 | 405 k | |
| QC | sle_st_b_v2 clfde1249e | -302 | 469 k | |
| QC | slw_fw_v2 cl8537f156 | -133 | 398 k | |
| QC | slw_su_l1 clcc9d0155 | -84 | 122 k | |
| QC | coll_ftc / coll_n / sle_su_l0 | -41 / +22 / +28 | | can pass |
| KV | kv3_pv_v1n | -1,546 | 824 k | 60,255 hold endpoints |
| KV | kv3_hgi_v3 | -1,160 | 434 k | |
| KV | kv3_hgi_v2 cle0015330 | -641 | 310 k | |
| KV | kv3_io_cor | +54 | 278 k | can pass |

- Wave table, last 48 h: QC has 5 failures at place or route (4 of them host events) and KV has 4. Neither die has a
  congestion or DRC class. The types do not fail early; they run 2-15 h and end as "timing after route".
- The gate is -42 ps. Of 13 running types read, 4 can pass.
- Limit: these are placement-parasitic numbers from the kit's hold-repair step, both corners. On the cb types part
  of the -861 may be the early-tap credit (tile clk-to-q 923 ps). Not split by path family by me.

Root cause: the long zero-logic hops and unstationed buses already measured on kv3_hg / hgi (FABLE-KVOVF 11-14)
and on the cb family (FABLE-PD-QC-0300) exist in the other families too (fw, st_b, su, pv), and nobody reads them
until the route ends.

Fix (DIE-QC-103 for QC, KV-102 for KV; one Sonnet lane per family):
1. Now: for every type with a `4_cts.odb`, run the endpoint listing FABLE-KVOVF used (`fable-kvovf/sta_t_hgi2`,
   10 minutes each): families, endpoints, worst slack, straight distance. Post one table per die.
2. Start with QC fw (6 slw + 4 sle types, -133 to -453 ps), st_b, and KV pv (11 types; pv_v1n is 824 k cells).
3. Each family gets the kv3_hgi form: station the bus at 380 um steps in the plan, or site the existing register
   at the equal-hop point. The S4r-style nested delta is the vehicle on QC, kvgeom7 on KV.
4. A type worse than -150 ps after CTS does not need its route to be judged; the lane starts the fix at CTS.
   The route may finish for DRC data.
5. kv3_pv_v1n at 824 k cells: split it (the approved over-400 k rule) in the same delta.

### Lever 4. Generation on the adopted plans

Evidence (MEASURED, `kit_wave_stages.tsv` 05:07):
- QC: 0 rows on event S4K; the newest rows are S4C. 36 types fail at `kit_rtl` between 01:14 and 04:43 with
  "bind of record names HDL sources that are gone" (`die-qc-103/treeA/...`). 28 of the 127 types end there now.
- KV: 13 types fail at `gen` between 04:25 and 05:06 with `module 'gen_phys' has no attribute 'tap_offset_table'`:
  kv3_hgi, hgi_v1, v4, v7, v8, hroot, io_cor_v1, pc x4, pv_v3n, pv_v5. REPORTED (KV-102 04:01): `check.py` in the
  same tree calls `port_pg_free`, which the installed `schema.py` lacks.
- QC also: sle_hc2 has 345,951 cells on 0.44 mm2 (0.79 cells/um2 against 0.42); the wave asks for x1.87 area or a split.

Root cause: the KV tree has a `gen_phys.py` / `schema.py` older than its callers after the 03:43 copy install
(INFERENCE; the QC die STA failed on the same function from an old tree). The QC bind of record lost its sources.

Fix: GENBUG-IMPL + KIT-OPS-6 put main's `tap_offset_table` and `port_pg_free` into the KV tree and test one gen and
one G0. KIT-OPS-5 points QC `kit_rtl` at the S4KR bind and confirms the first S4K row. DIE-QC-103 puts the sle_hc2
split into S4p/q/r.

### Lever 5. S81 leaf kits

Evidence (REPORTED, S81-LEAF-PLAN 05:12, epyc7 `s81-leaf-plan/cp27`): all six leaf kits fail before placement on
B6gsh and on LT2 alike. (1) t14, t54: `sdc_lint`, the core-tap latency has early = late (-96.8 ps) where the plan
window is -355.8 early. (2) t17, t72: the sidecar's reset collectors differ from the bound RTL. (3) t62: a lane
macro R180 -> MX cannot sit on the tracks. B6gsl (LT2) is in gates.
MEASURED (epyc2 process list): S81 col_h9_r0_p1 x2, col_h9_r0_p2, col_h10_r1 and leaf t11 have been in `5_1_grt`
for 6-15 h at one core each. Their logs were not read.

Root cause: base-plan and generator defects, not the throat delta. (1) is the plan W window missing from the SDC
writer; it would under-constrain every core-tap type, not only these.

Fix: GENBUG-IMPL fixes (1) in the SDC writer (write early and late from the plan window) and checks how many
released S81 types carry the equal pair. S81-LEAF-PLAN regenerates the sidecar from the B6gsh bind for (2) and
runs `orient_realize.py` for (3), then the place + global-route proof. DIE-S81-92 reads one of the 15-h `5_1_grt`
logs before the 350 types are released into the same step.

### Lever 6. KV hg / hgi

Evidence (REPORTED, FABLE-KVOVF 05:14, v_hgi2 at CTS): TNS -4.47k (merged -558k), 30 endpoints left, WNS -414 ps.
kp bus 0 (was 430), core reset pins 0, chain 0. Left: 7 reset-relay D pins (-227 ps), 12 start / reset broadcast
flops from `u_cland_rst_ft0_i` (-252 to -414), 6 `u_bin_i_ectl` (-80), 2 others. kvgeom7 a/b/c are in gates;
their G0 fails on the tool error of lever 4.

Fix (KV-102): kvgeom7b plus a two-level reset relay tree and one relay stage on the start / reset broadcast, on
all 19 hg / hgi types. The kp +2 cycles and reset +1 cycle need the RTL owner's functional check. Then the same
family listing on kv3_hg (lever 3 method), whose WNS stays near -600 without bus stations.

### Lever 7. HEAD NF

Evidence (REPORTED): NC gates pass on the old-form sidecar (bind, cohort 26/26, LATCHECK 329/329). lep0N spread
246 -> 63 ps. Start reset regenerated: 1,368 reset ports, settle 88. Open (HEAD-99 04:50): the both-edge re-bind
does not prepare, because relay pin lists differ between copies of hd_spn (sp0/3/4 against sp1/2) and
hd_spn_wshim_rx. K per copy is a strap and is not the cause. The route gate (lever 2) must use the adopted kit.

Fix (HEAD-99): use the partition-origin form with 0 relays, as section 17 of FABLE-TRIAGE-HEADKV set, through the
approved `landing_remap` branch. If two copies still need different relay stage counts, give all copies the larger
count (one type, +1 cycle on the short copies) and do not split the type. sp5 seam trim of 20 ps goes with it.

### Lever 8. QC cb family

Evidence (REPORTED): S4k adopted (bind 0, LATCHECK 1,921/1,921). S4p/q/r binds launched; no result posted. The die
STA chain on S4k runs from a main-based tree. Hops after S4k on nb_i12 are 411-418 um (accepted).
DIE-QC-103's question on a plan site for `u_st` has no answer; CLAND-BIN has posted nothing since the G2 result.

Fix: CLAND-BIN builds the equal-hop form (FABLE-PD-QC-0300 section 3) and the cbf_q01 place-only proof. Adopt the
largest of S4p/q/r that passes. The first QC die STA result then ranks the tile-boundary pairs.

## 2. Answers to the three questions

(a) QC and KV sign slowly for two reasons. The types that run are not failing early: they carry -130 to -1,550 ps of
setup into a multi-hour route (9 of 13 read). The types that do not run are stopped at generation (QC 36 on
missing bind sources and no S4K row; KV 13 on `tap_offset_table`). Congestion and DRC are not classes on either die.
(b) Not today. The split is right and form (b) matches form (a), but a unit of 141 nets holds about 2,800
violations that iterations do not remove. One marker dump decides the fix. After it, HEAD needs about 12-14 h for
11 passes. KV has no unit run that I found, and DIE-KV-ROUTE-1 has no post since 03:2x.
(c) No owner or no progress: the `u_st` / equal-hop site form (CLAND-BIN silent); KV start tree and unit route on
kvgeom6 (DIE-KV-ROUTE-1 silent); the 45 S81 lanes over 405 um after LT2 (set aside, no owner); the read of leaf
t54's route box; the HEAD relay pin-list rule (HEAD-99 asked for an owner).

## 3. Stop list

1. No unit-route volume and no KV unit run before one unit reaches 0.
2. No more iterations on a unit whose count is flat; 60 iterations will not clear fixed shapes.
3. No full-die single-process detailed route (95 min in iteration 0 without a line), and no form (a) for volume.
4. No release of the 350 S81 types before the compose passes and the added flops are priced per type.
5. No hop-limited start form on S81 (66 fail), and no rise-only start edges.
6. No relaunch of a QC or KV type that entered route under -150 ps of setup without a design change.
7. No type split of hd_spn for a relay count difference.
8. No counting of v_hgi2 or any kit-RTL edit form.
9. Still in force from 03:2x and FABLE-PD-QC-0300: no cycles on a subset of the four cb columns, no G2 beside the
   ring as default, no legacy half-period S81 clock numbers, no size-7 cut-out runs.

# FABLE-CLOSURE-STRATEGY 2026-11-15 07:3x PST: cross-die levers, S81 delta order, stop list

Read-mostly review, technical physical design only, HBM parked. Nothing launched, stopped or changed.
New since 05:1x: FABLE-PD-S81-0335 D-H, PD-S81T-0710, PD-S81C-0730, PD-QC-0700, PD-QCC-0740, PD-PHY-0710, KVOVF 14-16,
the queue to 07:20, `failure_breakdown.py` 07:11. No FABLE-PD-HEAD-0700 file exists.
MEASURED = read by me today from a plan, log or report. REPORTED = from a lane or review post. INFERENCE is marked.
My scripts (read-only plan scans): epyc7 / epyc9 / epyc2 `/tmp/fcs_scan.py`, `fcs_det.py`, `fcs_l2.py`, `fcs_drc.py`.
Plans scanned: S81 `B6gslcf.json` (epyc7 s81-b3-clk/ev), QC `zz_s29_qc103_s4q2.json` (epyc9 die-qc-103/treeA), KV kvgeom6
`plan_c.json` (epyc7 kw45/src_kv_kvgeom6_pgL), HEAD `gate/plan_nc/prep/source_plan.json` (epyc2 die-head-route-1; NC, not NF4).

`failure_breakdown.py` 07:11, technical classes: none new. S81 134 held + 68 running, QC 64 running + 36 held + 5 waiting on
the sta_region cores, KV 42 running + 6 placed, HEAD 6 held. Every open technical item is behind a plan event or a die gate.

## 0. Five things the per-die reviews did not see

1. The HEAD route-unit residue is named. It is die clock cells under partition abstracts, not pins and not PG (lever 1).
   This is the same for all four dies.
2. B6gslcf did not pass at 07:06 (it is not "in bind"). Two causes, both small and both in the compose (lever 2).
3. Every one of the 216 S81 col types has two tap rows per element half with two different insertions, and neither is the
   signed reference (lever 3).
4. Station registers with plan sites inside hard cores: S81 36 types (not 5), QC 7 types. They sit in the G0 baseline (lever 4).
5. Two items PD-S81T lists as missing from the CA plan are in it: the col tap window (165 ps on 216 of 216 col types, in the
   die table `clock.tap_window.per_type_ps`) and `reset_replicate` on col_h10_r1 (12 of 12). Only the type-level key is absent.

## 1. Levers, ranked

| # | dies | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | HEAD now; KV, S81, QC next | Die clock cells under partition abstracts: cut the abstract, reserve the sites | the DRC gate of every die | DIE-HEAD-ROUTE-1 (proof), KIT-OPS-6 (abstract + site map) |
| 2 | S81 | CA delta: 7 lanes at -1 and one wrong source clock port; take `--strap-window` in the same bind | 335 landed types | DIE-S81-92, KIT-OPS-6 |
| 3 | S81, QC, KV | Core tap rows: one row per core, at the signed reference | S81 216 col types + bk_sel__t2 + eng__t1; QC 18 cb types and KV hub_C to check | DIE-S81-92; DIE-QC-103, KV-102 |
| 4 | S81, QC | Station sites inside cores and strips over their track count: one geometry delta | S81 about 60 leaf types; QC 7 su types | S81-LEAF-PLAN + S81-LEAF-STRIP (one row owner per type), DIE-QC-103 |
| 5 | QC, KV | Stations on one leg of a latency-matched join; frozen pad tables | QC S4v2 / S4fw adoption (about 45 types), KV 7j/7k (19 hg / hgi) | DIE-QC-103, KV-102, KIT-OPS-6 |
| 6 | all | Hold ECO: non-port scope, 5 ps target, setup guard | t47, gunit, 6 sta_region masters, the S81 routed-not-signed rows | FLOW-LATEECO, KIT-OPS-5 |
| 7 | QC | Skew depth of the sta_region masters as straps | 4 parents now, 3 re-hardenings per later station event | DIE-QC-103, CORE-ROWS-1115 |
| 8 | S81 | col and phy clock: build, do not plan further | 12 col_h10_r1 (then the col family), phy__t1 | DIE-S81-92 |

### Lever 1. Die route: clock cells under the partition abstracts (cross-die)

Evidence (MEASURED, epyc2 `die-head-route-1/head/p20nc_gate/unitruns/probe_u201_b/drc_TT.rpt`, written 06:03, not yet
posted by the lane; unit u201, 141 clock nets, crop form, 3 steps: 3,276 -> 2,786 -> 2,800):
- 2,800 markers. 1,904 are an own clock net against a partition instance (`tW1b8` 1,894, `tW1b9` 10):
  Short M1 400, M2 252, M3 252, M4 252, M5 252, M6 252, M7 244.
- The M2-M6 markers are the same 252 points on every layer (184 distinct 1-um points over x 1654-2415, y 10869-11878),
  so each is one via stack from M8 down to M1. At the first point the net `ck_rn1089_1` also touches the die clock
  cell `ck_r1089_2` on M1. The stacks end on die clock cells that sit inside the partition.
- The partition abstract (`kit/abstracts/ot_s81hd_lep0N.lef`, source "plan abstract") has OBS on M1, M2, M3 over the
  full outline and block rectangles from M4 up.
- Rest: M1 clock net against VDD 178 and net against net 97 (at the cells); M7 against PG 77; M8 against abstract
  obstruction 120 short / 177 spacing, M8 against PG 67 + 7, M8 min step 83.
- The other five running units are flat as well (u201_b at 2,611 in iteration 9).
- Kit: 10,660 repeaters and 13,093 leaves in the HEAD tree. S81 has 91,460 die clock cells and 2,430 start stages
  (REPORTED, 0335 H), and its types carry no reserved sites (MEASURED: no `reserved_sites_um` key on any of 395 types;
  none on QC 130, KV 56 or HEAD 26 either).

Root cause: `die_trial.SiteMap` puts die clock cells on any site inside a partition and outside hard cores. The
abstract of that partition blocks every layer there, and the type under it never reserved the site. This corrects my
05:1x inference (stacks to lower pin shapes of the abstract): there is no lower pin shape; the target is a die cell.
No iteration count removes it. For a signed type the conflict is real metal, not only an abstract shape.

Fix:
1. Proof, 30-40 minutes (DIE-HEAD-ROUTE-1): cut the lep0N abstract OBS on M1-M7 over the 252 cell positions of u201
   (cell box plus one via column), rerun the same 3 steps. Expected: the 1,904 instance markers go to 0. The M8 part
   (about 400) stays and is then the only thing left to name.
2. Site map from the layout, not from the outline (KIT-OPS-6): for a type with a closed view, a site is legal only
   where the view has free rows and a free M1-M7 column; for a type without one, the plan reserves a small set of
   rectangles (`clock.reserved_sites_um`, kind die_clock_tree) on the tree pitch (HEAD kit: repeaters 150 um, leaves
   200 um) and the tree snaps to them. The abstract generator cuts OBS over the cells actually placed.
3. Count before choosing per type: sites used by the die tree against free sites in each signed view. A signed type
   keeps its record when every cell fits in free area; only the others re-key.
4. Same change for the start-stage flops (S81 2,430 x 4.32 um, already an open note in 0335 H).
5. M8: after step 1, split the M8 markers into pin landing against abstract obstruction (cut a window around each
   M8 pin) and against the region PG (the `clock_entry_pg_cut` form). DIE-KV-ROUTE-1's M8 / M9 pin-against-PG scan
   answers the PG half for KV.
Unblocks: HEAD die DRC today's blocker; the same defect waits on KV (127 units listed, none run), S81 and QC.
Owner: DIE-HEAD-ROUTE-1; KIT-OPS-6 for the generator and SiteMap; each die owner for the reserved rows.

### Lever 2. S81 CA delta: why B6gslcf failed, and the form to rebind

Evidence (MEASURED, epyc7 `s81-b3-clk/run/b/B6gslcf`, `g0/g0_report.json`, `bind.log`; compose rc 0):
- G0: 7 errors, all schema: `latency.lanes.<lane>.clock_landing: -1 < 0` on attn / attnh / hbm between svc_5 -> svc_4,
  svc_11 -> svc_10, svc_13 -> svc_12. This is the check 0335 section B asked for at 03:35 (2 crossings at -1 then).
- Bind: 80 errors in the summary; the log shows 1 EMIT and 29 LF_CS_DEPTH. EMIT: `bk_sel__t2: fclk_out_tl_o0 contract
  source_clock_port clk_t2 is not an input port of the type`. bk_sel__t2 has 7 core taps and no grid tap in the plan.
  The 29 LF_CS_DEPTH lines (24 leaf, 5 kv_leaf) say "no bound module file": INFERENCE, they follow from the failed emit.
- B6gshcf fails the same way.

Root cause: the compose writes a negative landing when K lands before the lane's own stations, and it names a grid tap
as the write-clock source on a type that has only core taps.
Fix (DIE-S81-92, KIT-OPS-6 for the compose):
1. The 7 lanes: +1 station cycle on the three svc pairs (cycles are pre-approved) and re-plan K for those ports; do
   not relax the schema.
2. Source clock port: take it from the ports the type has (`clk` for a type without grid taps).
3. Rebind on the uncapped F table with `--strap-window` (REPORTED DIE-S81-92 06:38: 977 / 16, strap bind rc 0,
   0 violations, lo 105.5 / hi 112.4, 144 of 160 depth-8 crossings back to depth 4, 243 k fewer flops). Depth is type
   content; taking it now means the 335 types are built once. Guard 417 gives the same types 160 depth-8 buses that the
   next delta would shrink again.
4. Compose variant C as ruled. Its 17 -> 1 result was measured on the guard-417 table; read the band report again on
   the strap-window table before the bind.
Unblocks: 335 landed types. The 52 types of `types_depth_open.json` stay at risk of one depth change until the 48 long
start hops are measured (0335 G), as already ruled.

### Lever 3. Core tap rows (cross-die)

Evidence (MEASURED, plan scans):
- S81 B6gslcf, all 216 col types: each element half has two tap rows. `u_w.ck` 437.413 / 348.735 and `u_w.clk`
  532.993 / no FF value; `u_e.ck` 476.052 / 382.22 and `u_e.clk` 553.179 / no FF value. 3,456 rows. The signed
  reference is 465.39 / 361.26 (PD-S81C). The `.ck` rows are 28 ps late and 11 ps early of it, the `.clk` rows 67.6 and
  87.8 ps early. The kit wrote the `.clk` value against a 250 cap (PD-S81T section 5).
- S81 rows whose owner text is the liberty maximum: bk_sel__t2 `u_tx.ck` 829.1 (early 579.1) and eng__t1 `u_e.ck`
  848.98 (early 599.0; "no measured mean in the view"), both over T/2 = 416.5; `eng_rr_h0` 270.23. eng__t1 is new.
- QC S4q2: 72 core taps on 18 cb types are over T/2 early: tiles `u_tNN.ck` 733.25 and 774.38 against budget 250
  (early 483 and 524). KV kvgeom6: kv3_hub_C `ahub.ck[0..2]` 1,003.4 (early 753). HEAD NC: none.

Root cause: tap rows are written by several events from different sources (liberty maximum, placed view, routed view)
and nothing compares a row with the frame the core was signed in. A stale pin name leaves a second row behind.
Fix:
1. DIE-S81-92, rows only, in the CA rebind: one row per half, 465.39 / 361.26, on the pin name of the signed LEF;
   delete the twin. bk_sel__t2 at 450 with the idx row 722.7 / 592.8 (PD-S81C 2.3). eng__t1 `u_e`: read the signed
   record's `io_reference_ps`; if the core has none, measure the pin-register mean on its routed view first.
2. PLAN-READERS-1: the audit fails a core tap whose value differs from the signed `io_reference_ps`, fails two rows
   on one core clock, and fails a row without an FF value.
3. DIE-QC-103 and KV-102: state how the kit times a core tap more than T/2 early (cb tiles, ahub). If it is clamped,
   as on S81 col, part of the -861 ps on cbn_q11 is this and not a data path. Not checked by me.
Unblocks: timing truth on 216 col types before they are rebuilt on the CA plan; bk_sel__t2; eng__t1.

### Lever 4. Station sites inside cores, strips over their track count

Evidence (MEASURED, plan scans; my count for t14 by feed-through bit sites is 1,483, equal to PD-S81T):
- S81 B6gslcf, `internal_stations` register sites inside a hard-core box: 36 types, 1,306 sites, 75,617 bits; only
  71 sites are within 2.2 um of a core edge. Largest: leaf t22 29,674 bits (the vn -> lane bundle entry sits inside
  5 lane cores), t41 23,623, t8 4,415, t37 2,354, t56 1,574, t65 1,574, t28 1,569, t72 1,558, t75 1,308, t61 1,291.
  Also 6 col_h10_r0_p1 types with 1 site each.
- S81 feed-through bit sites inside cores: t65 3,140, t32 1,584, t14 1,483, t38 1,016, t16 21, and
  slice_station__t51 13,574 inside its two native children (plus 73 grid taps). t51 may be by design (child-side
  form); it is also the last CA band failure.
- QC S4q2: 7 su types, 208 sites, 19,918 bits (sle_su_l1 x2 3,713 each, sle_su_l0 x2 2,652, slw_su_l0 x3 2,396): the
  `flt_su_c_i` pin chain passes through lanes 5 and 6. KV: kv3_pv_v5 / v5n, 6 sites each. HEAD: 0.
- PD-S81T: 13 leaf types with a strip over 1.0 x its tracks, 5 with a slot under 20 um holding over 200 sites. G0
  reports the in-core sites only when new; the old ones are in the accepted baseline.
- Limit: I did not open a placed database. The legaliser displacement (126 um on t14) is the check for each type.

Root cause: cores were moved by several events (LT2, quad staging, orient) and station sites were not re-derived.
Fix: one leaf geometry delta (section 2), with the station re-site as a generated step after every core move; G0
"station site inside a core" is never baselined (GENBUG-IMPL). QC: DIE-QC-103 re-sites the su pin chain in the S4fw
event. A type on this list is not released before its row is re-sited.

### Lever 5. Stations on one leg of a matched join (QC and KV, same class)

Evidence (REPORTED): QC S4x does not bind because +2 on st_b moves regions 4-7 past region 0 (PD-QC-0700 2.1); the
cb16 pad table was keyed to the old bound depth, three rounds lost (1.3). KV 7a-7f at 07:09: PARAM_REGEN "ECTL: K
round trips differ per frame [18, 24]", because the hg stations sit on the request / response buses of one frame
only; KV also had to pin 91 pad members. QC-FWST has S4fw on S4q2 with levers 3-6 in gates.
Root cause: a station event changes one leg of a latency-matched pair; tables derived once are not re-derived.
Fix:
1. KV-102: the equal-depth form (the same +N on krq / krs of every frame) is the structural one. 7j / 7k drop the
   stations and leave the hg krsp hop at -568 ps; adopt one of them only as a step.
2. KIT-OPS-6: the derive replay as a pre-bind step on both dies (the QC replay predicted 24,672 stale bits exactly,
   in minutes), and every pad table regenerated in the bind chain.
3. Stations enter a plan per matched group, not per bus.

### Lever 6. Hold ECO scope

Evidence (REPORTED): kv3_phy_v1 late ECO TT -34 -> -248 while fixing port hold; t47 -0.54 ps on one output port,
alternating between two bits at target 0; gunit_l1f_bf 15 reg-to-reg at -4.82; sta_region masters -3 to -7 on at most
19 endpoints, sibling closed in one pass. FLOW-LATEECO READY @d63e3dc5a1d (core-only default), no real-kit run yet.
Fix: merge it; add a 5 ps target and a stop when TT setup falls under -42; first real run = t47 from its i2 database
(3 h). Then the S81 routed-not-signed rows (25 since 11-06, 19 slice_station, not opened by anyone) in one batch.

### Lever 7. QC sta_region skew depth as straps

Evidence (REPORTED, PD-QCC-0740; GENBUG-IMPL 07:11): 4 types, 32 parameters differ between plan and bound RTL on S4p
and again on S4q2; KV, S81 and HEAD have 0 `param_wrap` rows (QC S4q2 has 188). 12 kits for both parameter sets run.
Fix: as PD-QCC R1: SKEW_N / SKEW_S as strap inputs of one master in the next QC event; the bind check merges now.
S4v2 and S4fw move the cb column again, so without straps the masters are rebuilt a third time.

### Lever 8. S81 col and phy clock

Evidence (MEASURED on B6gslcf): col types have `tap_max_sinks` 1500, budget 450, per-type window 165 on 216 of 216,
`reset_replicate` on 144 of 216 including all 12 col_h10_r1. phy__t1 has 0 taps and no `tap_max_sinks`.
Fix: no more col plan work before one col_h10_r1 build to CTS on the CA plan with the lever-3 rows (pass: PD-S81-2250
gate). phy__t1: grid taps along the strip in the same rows-only change (PD-S81T section 6).

## 2. S81 queued row deltas on B6gslcf: conflicts and order

Type overlap of the queued sets (MEASURED from the lists in 0335 D, PD-S81T, the 07:10 posts and my scan):

| type | collector (D2) | orient (D3) | strip | slot / in-core ft | in-core istation | CA band failure |
|---|---|---|---|---|---|---|
| leaf t8 | x | | x | | 4,415 | 2 |
| leaf t72 | x | | x | | 1,558 | 2 |
| leaf t33 | x | x | x | | | |
| leaf t52 | x | | x | | 273 | |
| leaf t58 | | x | | slot 1,342 sites | | |
| leaf t68 | x | | | slot 403 sites | | |
| leaf t65 | | | | slot 263 sites, in-core 3,140 | 1,574 | |
| leaf t28, t75, t13, t43, t10, t71, t74 | | | x | | 262-1,569 | |
| leaf t37 | | x | | | 2,354 | |
| kv_leaf t3 | x | x | | | | |

Conflicts:
1. Two lanes own rows of the same type: S81-LEAF-STRIP (13 strip types) and S81-LEAF-PLAN (orient 13, t14, slots).
   t33 is in both. One owner per type row; S81-LEAF-STRIP takes every type in the table above.
2. Order inside a type matters: a core move changes station sites, collector taps and landing bands. A collector
   reattach or a band placed before the move is wrong after it.
3. The CA compose rebases 21,010 pins and places bands against the cores. Any leaf row change after it invalidates
   the bands of that type. The compose must be the last step of every S81 event from now on.
4. `--strap-window` and the capped start tree change depth (160 -> 16 depth-8, or 205 + 13 depth-16 with the 48 long
   hops open). Variant C was proven on the guard-417 table only.
5. FABLE-S81-TYPEMERGE R2 (strap width = group maximum) edits what the compose writes; as a row patch it is
   overwritten by the next compose. R3a (monitor entry union) moves col landing pins and must come before a compose.
6. The clock rows (lever 3, col reset copies, phy__t1 taps) touch col, bk_sel, eng and phy only: no overlap with the
   leaf sets.

Merge order:
- E1, now: B6gsl + rows-only clock changes (lever 3 S81 rows, phy__t1 taps) + compose (F table, `--strap-window`,
  variant C, the two compose fixes) -> bind + LATCHECK. Release: col, slice, svc, serdes and the leaf types not in E2.
- E2, leaf geometry, one delta: orient -> core moves (strip re-path, slot, t14) -> station re-site (ft and
  internal) -> collector reattach -> compose again. About 60 leaf types; proof = place + GRT 0 overflow on t75, t14,
  t22 and t8 before the bind. These types are held out of E1's release.
- E3, die level: capped start tree with the measured long hops, TYPEMERGE R2 inside the compose and R3a before it.
  Re-keys only the types whose depth or strap width changes.
- R1 of TYPEMERGE (sign-off key = layout hash) is no plan change and can apply at E1's release: it cuts the col
  builds from 216 to about 14-20 and is the largest single saving on S81.

## 3. Stop list (technical dead ends)

1. No more iterations, unit volume or KV unit runs on the current abstracts: 1,904 of 2,800 markers are fixed
   geometry. No full-die run either.
2. No reading of the unit residue as pin-against-PG until the abstract cut is proven; the PG part is under 330.
3. No rebind of the CA delta with the schema relaxed for negative landings.
4. No guard-417 CA release if the strap-window table binds: it builds 144 depth-8 buses that the next delta removes.
5. No further shallow-tree forms of gb_he / gb_hw, no idxD, no kit vclk below the typed reference (PD-S81C).
6. No col_h10_r1 form on the B3t block and no new col plan fields before one CTS build on the CA plan.
7. No leaf row change after a compose without a compose rerun; no second owner on a leaf type row.
8. No release of a type whose station sites lie inside a core, and no baseline for that G0 class.
9. No KV or QC station event on one leg of a matched join; no S4r4 / S4r5 sign tests; no S4x as built.
10. No n6_s7 / n6_s8 sta_region views registered as S4p or S4q2 children.
11. No port-scope hold ECO on a type; no zero-target ECO pass.
12. No wave attempts on the three QC PHY types; no plan-window move to the PHY macro pins.
13. No phy__t1 split and no relaunch before it has taps; no t75 retry as INFRA; no t14 launch on its current row.
14. Still in force: the 05:1x list items 5-9.

## 4. Not verified

- Lever 1: no rerun with a cut abstract; the M1-M7 claim rests on the marker geometry and the lep0N LEF. I did not
  confirm the master of `tW1b8`; the marker field (760 x 1,010 um) fits inside lep0N (1,892 x 1,227).
- Lever 2: the 29 LF_CS_DEPTH lines as a follow-on of the emit error; the band fit on the strap-window table.
- Lever 3: which of `.ck` / `.clk` is the pin of the signed LEF; how QC and KV kits handle a tap over T/2 early.
- Lever 4: plan reads only, boxes as origin + outline; no placed database opened; whether t51 and the QC su lanes are
  true hard cores for placement (they are `hard_cores` rows in the plan).
- HEAD was scanned on the NC source plan, not NF4 / NF5. The route gate must be rerun on the adopted kit.
- No what-if was run in this review.
