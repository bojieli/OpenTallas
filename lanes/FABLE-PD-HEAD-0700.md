# FABLE-PD-HEAD-0700: HEAD serdes / host family physical-design review (2026-11-21 06:35-07:05 PST)

Read-and-analyse only. No build, no kit, DB or job touched. HEAD is 25/26 signed off (only hd_lep0N is not); hd_serdes
and hd_host_e here are deferred re-signs.

Evidence (read-only copies and my STA outputs):
- epyc9 `/srv/opentallas-scratch2/claude/fable-pd-head-0700/sdr2d_evidence/`: final GRT DB of the first GRT
  (`5_1_grt.final_1353.odb`, 05:53 PST), `route.guide.1352`, stage reports, GRT/CTS/gate logs.
- epyc10 `/srv/opentallas-scratch2/claude/fable-pd-head-0700/{db,kit,q}`: same DB + `4_cts.odb`, kit small files,
  `q/grt.hold.rpt` (483 paths), `q/cts.hold.rpt` (262 paths), scripts `hold.tcl`, `pads.tcl`, `nets.tcl`, `bar.tcl`.
- STA basis of my numbers: FF libraries of the kit gate receipt, kit SDC, `setRC_rcx.tcl`, propagated clocks,
  `estimate_parasitics -global_routing` (GRT DB) / `-placement` (CTS DB). The kit gate also swaps in the signal-C table
  (OT_RC_SIGNAL x1.13), so its slacks are deeper than mine on the same paths (gate -188.58, mine -116.5 on the same
  worst path). Classes and causes are the same; where I quote the gate I say so.

## 0. Live finding (posted 06:44, not acted on)

The sdr2d "route" job (epyc9 `oth-ubuntu-3513796-1795271147`, `run_kit.sh ... route 96 16`) is not in detailed route.
The route goal re-ran the CTS-stage TT setup repair (29.38 -> 43.38, 0 cells added), kept it and rewrote `4_cts.odb` at
06:32 PST. That made it newer than `5_1_grt.odb` (05:53), so make restarted `global_route.tcl` at 06:38
(`5_1_grt.tmp.log`). About 3 h of GRT is being repeated; the first final GRT DB, guide and reports will be overwritten
(copies above). The DRT-0255 / ring read of sdr2d is therefore about 3 h later than the 06:30 post implies.

## 1. Event 2: sdr2d. Setup collapse dropped; FF hold root cause

Setup: dropped per COORD. `5_global_route.rpt` (-189.74 / TNS -8293) was written 05:24, before the GRT-stage TT repair
(`tt_setup_keep.log`: -424.03 -> +2.60 in the kit session, 2,271 cells; R4 reads +45.45 on the final DB). No setup
path is below 0 on the final GRT DB.

FF hold, final GRT DB. Gate (`postcts_gate_FF.log`, vclk bound to the measured 467.19): 2,937 violating endpoints =
1,954 ring-input ports (worst -68.30, `coll_i0[507]`), 420 output ports (worst -47.03, `rst_start_raw_3`), 563
internal reg-to-reg, worst -188.58. Only the 563 internal ones are against the owner gate (internal FF hold >= 0).

Internal class (my session: 483 clk-group endpoints, worst -116.5; pma_rck group has no internal violator, only
`pma_rx` port inputs):

| launch tap -> capture tap | endpoints | worst (ps) | launch insertion | capture insertion | SDC tap window |
|---|---|---|---|---|---|
| clk_t14 -> clk_t4 | 178 | -106.2 | 351 | 464 | 94 |
| clk_t14 -> clk_t5 | 108 | -116.5 | 350 | 476 | 94 |
| clk_t20 -> clk_t4 | 63 | -92.9 | 455 | 466 | 50 |
| clk_t7 / t8 / t13 / t11 / t15 -> clk_t20 | 83 | -61.8 | 345-365 | 455-459 | 50-92 |
| clk_t20 -> clk_t5 | 22 | -108.6 | 455 | 507 | 50 |
| clk_t22 -> clk_t4 | 12 | -62.4 | 354 | 457 | 94 |
| t4/t5 same or mixed, t20 same | 17 | -93.9 | 451-457 | 547-567 | 50-64 |

Every violator is captured on clk_t4 (258), clk_t5 (139) or clk_t20 (86). All are `u_ptx` (l[0..2] -> q, pma_tx
output pipeline) or `u_enc` <-> neighbours. Worst: `u_ptx.l[2][135]` (clk_t14) -> `u_ptx.q[135]` (clk_t5).

Wire RC versus clock latency, same 262 start/end pairs on post-CTS `4_cts.odb` (placement RC) and the final GRT DB:

    slack +63.8 -> -35.2 (change -99.0) = data +4.4, launch insertion +17.5, capture insertion +118.8

It is a clock-latency change on three capture taps, not data wire RC. Per tap (FF, CTS -> GRT):

| tap | CTS | GRT | change | where the change sits (mean per path) |
|---|---|---|---|---|
| clk_t4 (1,000 sinks) | 344 | 467 (to 578) | +123 | tap-balance pad chain +112.3, leaf buffer +8.9, sink wire +5.6 |
| clk_t5 (541 sinks) | 348 | 481 (to 608) | +133 to +255 | pad chain +90.9, GRT leaf repeaters +46.1 (max +94.6), sink wire +11.4 (max +109) |
| clk_t20 (11,321 sinks, u_enc) | 406 | 456 | +50 | GRT leaf repeaters +38.3, trunk +10.1 |
| clk_t14, t22, t7, t8, t13, t11 | 341-360 | 345-367 | +1 to +9 | none |

Root cause 1 (new, measured): the pad chain crosses a reserved clock-site wall. The tap pins clk_t4 (1240.336,
16.928) and clk_t5 (1284.24, 16.928) are M7 pins inside one reserved clock-site obstruction, M1-M7,
(1214.19, 16.2)-(1330.88, 18.36): 116.7 um long, 2.16 um tall, with a placement blockage. OT_CLK_OBS_HALO / legalisation
put the BUFx4 pad chain (`clk_t4_tb0_d0..d13`, `clk_t5_tb0_d0..d14`) on both sides of it, rows y 15.4/15.7 and y 18.6.
A chain net that crosses has pins 3.2-4.0 um apart and must route around the end of the wall:

| net | pin HPWL (um) | GRT guide length (um) | guide bbox x |
|---|---|---|---|
| clk_t4_tb0_n0, n1, n2, n4, n5 | 3.2-3.6 | 79.8, 87.8, 89.5, 88.9, 82.1 | 1207-1245 (wall end 1214.19) |
| clk_t5_tb0_n1, n2 | 3.7-4.0 | 142.5, 140.2 | 1285-1351 (wall end 1330.88) |
| same-row chain nets (t4 n6-n12, t5 n3-n13, all of t14) | 0.5 | 0.0-1.1 | local |

Placement RC priced every chain stage at 16.6-16.9 ps; GRT RC prices the crossing stages at 22-61 ps
(`clk_t5_tb0_d2` 61.1, `d3` 52.8; `clk_t4_tb0_d1..d6` 22-40). clk_t14 sits at a 5.2 x 1.9 um site, its chain stays on
one side, and it does not move. CTS tap balance (602 delay cells, tap means 429..509 TT) was therefore balanced on a
delay the route cannot deliver.

Root cause 2 (FLOW-LEAFREP-1121 class, second die): OT_CLK_LEAF_REPEAT in the GRT step added repeaters on clk_t5
(`clkleafrepg_149454` + `_849461`: +19.9 +74.7 ps on that branch) and clk_t20 (`_749460` + `_949462`: +38 ps), on
single branches, with no re-balance. Same mechanism FLOW-LEAFREP-1121 confirmed on KV hroot at 06:56.

Contributing, settings: `OT_TAP_GRT_PRE` (GRT-RC tap re-balance, `tapbal_grt.tcl`, in the kit) is not set in the sdr2d
config.mk nor in the r16 wave hd_serdes attempt_2 config.mk. The sd9d a4 lineage set it by hand. I did not check the
signed sd9he kit.

Contributing, repair budget: the GRT hold guard got one 200-buffer chunk (2,224 s): ws -197.09 -> -138.16, then
RSZ-0060 and the setup guard stop. A 100+ ps cross-tap skew on 563 endpoints is not a buffer-repair problem; the
pre-GRT hold pass had already spent 17,718 hold cells for a +5 ps start.

Not established: whether the routed DB would show the same pad-chain detours (DRT follows the guides, so I expect
yes); the hd_ptx placement itself (q regs y 4.3-8.6, l regs y 5.7-112) was not reviewed.

## 2. Event 1: DRT-0255 (sdr2c, hd_host_e) and the FLOW-OBS-GCELL-1121 fix

What is proven: two instances, both a horizontal-layer guide (M4 sdr2c, M6 host_e) in a gcell row that a reserved
clock-site obstruction covers across its tracks, with 1 (sdr2c) and 2 (host_e) tracks left. Why DRT cannot use
tracks that are spacing-legal by the fix's own test (346.464 - 0.048 > 346.41) is not explained; "fewer than 3 tracks"
is a threshold that covers both observed cases, not a derived rule. A gcell left with exactly 3 tracks is untested.

The fix (`obs_gcell_cap.tcl`, commit e44fcd0731 in the lane clone, not pushed; read in full): logic is sound for the
class as stated; the planner handles both edges, thin obstructions, partial along-track cover (conservative), M2-M7
(reserved sites are M1-M7 only, so M8 needs nothing). Probe on hd_host_e: 668 of 2,125 partly covered gcells cut,
GRT ends at 0 overflow. The proof run (host_e GRT + route, epyc8 `oth-ubuntu-2792729-1795271476`) had not reported.

It is NOT complete. Gaps, in order of risk:

1. Fresh-session incremental GRT does not get the cap. Region adjustments live in GlobalRouter, not in the ODB.
   `grt_pg_replay.tcl` (used by `tt_setup_repair.tcl` at the GRT stage) restores only OT_PG_CELL_KEEPOUT,
   OT_PG_TRACK_TRUTH and OT_PGCAP. On sdr2d that session added 2,271 cells and re-routed 1,524+ nets with no cap, so
   those nets can land in the same sliver gcells and DRT-0255 returns after a "fixed" GRT. Add the cap to the replay
   list; then check the other scripts that open a routed DB and route (`final_ff_hold.tcl`, `core_final_repair.tcl`,
   `core_drv_repair.tcl`, `grt_final_full.tcl`, `grt_stall_resume.tcl`) for the same omission. I did not audit those.
2. It runs before PG-track-truth and counts only dbObstruction shapes. A gcell with 3+ tracks clear of the
   obstruction but fewer than 3 once the PG-illegal tracks are removed (M5/M6/M7: 2,484 / 963 / 1,856 PG-truth
   obstructions on sdr2d) is still a sliver. Count free tracks against obstruction + PG-truth shapes together.
3. Pin exemption is per whole strip: one BTerm shape anywhere along the strip exempts every gcell of it (102 of 2,125
   on host_e). On vertical layers a strip is the full obstruction height (up to 40 gcells on the sdr2c column).
   Exempt only the gcells the pin shape touches.
4. Macro OBS and fixed-instance blockages (hd_serdes 3 macros, hd_lep0N 4 cores) are not dbObstructions and are not
   examined. No failure seen from them; same geometry class.
5. The A/B that would settle the mechanism (sdr2e, lattice snap) is on its 3rd launch and has no result.

Exposure of other HEAD types: not measured per type (my host sweep for kit `reserved_sites.tcl` returned nothing in
time). What is measured: hd_serdes has 177 reserved sites / 1,263 obstruction rects, all off the 0.57-um gcell grid,
20,611 guide boxes of 5,368 nets partly overlapping (R4, sdr2c); hd_host_e has 2,125 partly covered gcells. Reserved
die-clock sites are generated for every HEAD type that hosts die clock cells, so every re-sign and hd_lep0N is exposed
until the fix and gap 1 are on the runtime. The 25 signed types passed DRT without it, so the per-build hit rate is
below one, not zero.

The same reserved obstructions also cause section 1 (pad chains straddling a long strip). Types whose tap pins sit in
long strips are exposed to that; in hd_serdes the strips over 20 um are 116.7, 108.4, 31.4 and 30.2 um long.

## 3. Event 3: hd_serdes / hd_host classes with two or more failures

| class | instances | state |
|---|---|---|
| DRT-0255 at a reserved-site sliver gcell | sdr2c, hd_host_e | fix in test, incomplete (section 2) |
| stage report quoted before the stage's own repair / wrong frame | sdr2d GRT -189.74; sd9c / sd9d gate on the unrepaired fallback DB (-166.87 / -169.19); the 11-20 CTS pre-hook case | rule exists (final stage DB only); the reports are still written before the repair |
| resume or route goal redoes or kills upstream work | sdr2d route re-running GRT now; sdr2e try1 RESYNTH-GUARD (exit 12); sdr2d false PLACE-SETUP-STOP (fixed eda19506a55); 11-18 SWITCH-SUPERSEDE kills | open for the route goal (section 0) |
| GRT-stage TT repair crash (RSZ-0074 / GRT-0228) | sd9c, sd9d a3, a4, private ttfix | fixed on main (504fcadebf); did not recur on sdr2c / sdr2d |
| clock insertion moves between CTS and GRT, cross-tap hold or setup follows | sdr2d t4/t5/t20 (this note); sd9d u_rm.mem (tree 1,148 ps); hd_lep0N tap window classes; KV hroot | section 1 fixes |
| encoder wire-dominated setup (rem_q / ch_q / pw / pi2) | sd9c, sd9d, sdr2c, sdr2d (-424 before GRT repair) | closed on sdr2d by one tap + repair (+79 or better); costs 2,271 cells |
| private kit env differs from the wave env | sdr2c (-allow_congestion, GPL exit), lep0N shelf_bf / col_bf, OT_TAP_GRT_PRE here | check per kit |

hd_host_e: GRT TT -64.98 (gate -42 at route) then DRT-0255. One build, no second class yet. hd_host_w / host_n: no
failure of a repeated class found in the 11-19..11-21 posts.

## 4. Ranked fix list

1. FLOW-OBS-GCELL-1121: add the obstruction cap to `grt_pg_replay.tcl` (gap 1) before pushing. Without it the cap is
   lost in the GRT-stage TT repair session of exactly the kits that need it. Then gaps 2 and 3. Proof = host_e route
   with a GRT-stage repair session in the chain, DRT past iteration 0.
2. FLOW-OBS-GCELL-1121 (obstruction placement side; hand to FLOW-LEAFREP-1121 if COORD prefers the clock lane): keep a
   tap's whole pad chain and its first tree buffer on one side of the reserved obstruction that holds the tap pin (the
   sink-centroid side, contiguous rows), in `clk_obs_halo.tcl` / `tap_balance.tcl`. Add an estimator line at GRT: any
   `*_tb*` chain net whose guide length exceeds 10x its pin HPWL. This removes +91 to +112 ps on clk_t4 / clk_t5.
3. FLOW-LEAFREP-1121: the GRT leaf-repeat pass must re-balance the tap it changes (OT_CLK_LEAF_GRT_BAL in test). Add
   sdr2d clk_t5 / clk_t20 to its A/B set (DB copy above). Removes +38 to +95 ps.
4. OPUS-FIX-HEAD-SERDES-R4: for the next hd_serdes kit only (no new build now): set `OT_TAP_GRT_PRE = 1` so taps are
   re-balanced on GRT RC, and diff config.mk against the signed sd9he kit before launch. Row for the HEAD plan owner:
   clk_t4 (1,000 sinks, at cap) and clk_t5 carry the `u_ptx` output pipeline while its launch side is on clk_t14 with a
   94 ps window; put `u_ptx.l[*]` and `u_ptx.q` on one tap (tap_group, as done for u_enc) so the 298 t14/t22 -> t4/t5
   pairs become same-tap.
5. FLOW-OBS-GCELL-1121 (flow, small): the route goal must not rewrite `4_cts.odb` when `5_1_grt.odb` exists
   (section 0); and write `5_global_route.rpt` after the GRT-stage repair, or stamp it PRE-REPAIR in its first line.
6. FABLE-FIX-HEAD-LEP0N: before col_we / shelf_we reach GRT, read the reserved strips against the tap pins and the pad
   chains of the 4-core type (same check as fix 2, estimator only), and take the cap with gap 1 fixed for its DRT.
   hd_lep0N is the only unsigned HEAD type, so it should not find these two classes at route.

## 5. Stop list

- Stop quoting kit stage `.rpt` slacks (`5_global_route.rpt`, `4_cts_final.rpt`); read the final stage DB.
- Stop pushing e44fcd0731 as the complete DRT-0255 fix; it needs the replay hook first.
- Stop treating the sdr2d FF hold as a repair-budget question (more hold chunks, more HB4 pads, ECO passes). The
  563 endpoints are one skew of 100+ ps on three taps.
- Stop expecting the OT_RESERVED_SNAP lattice snap (42fa174c180) to cure DRT-0255; R4 computed that it keeps both
  tracks open. Let sdr2e finish as the A/B, no relaunch if it dies again.
- Stop chaining "route" onto a finished GRT kit through `run_kit.sh route` until fix 5 lands; it repeats GRT.
- No new hd_serdes / hd_host_e builds (deferred re-signs); no cancel of sdr2d, host_e proof, sdr2e or the r16 wave
  hd_serdes attempt_2: none is measured below the -300 line.

---

(Earlier review under the same lane name, 2026-11-15, kept below unchanged.)

# FABLE-PD-HEAD-0700: HEAD die route by region-net units, why the count is flat (2026-11-15 08:1x PST)

Scope: physical design only. Evidence: epyc2 `/srv/opentallas-scratch3/claude/die-head-route-1/head/p20nc_gate/unitruns/probe_u201_b`
(`drc_TT.rpt`, 2,800 markers after iteration 2, crop form), the unit database `unit.odb`, the kit under `tree/kit`.
My runs: epyc2 `/srv/opentallas-scratch3/claude/fable-pd-head-0700` (wi1, wi2), epyc10 `/srv/opentallas-scratch2/claude/fable-pd-head-0700`.
MEASURED unless marked INFERENCE.

## 1. What the 2,800 markers are (u201, crop form, after iteration 2)

| layer | markers | object pair |
|---|---|---|
| M1 | 721 | Short 400 clock net vs tile abstract (obstruction), 178 clock net vs VDD/VSS, 97 clock vs clock; spacing 46 |
| M2, M3, M4, M5, M6 | 252 each (+13 EOL/spacing on M4/M5) | Short, clock net vs the tile abstract `ot_s81hd_tile_p` (its obstruction), all of them |
| M7 | 323 | Short 244 clock net vs tile abstract, 77 clock net vs VDD/VSS (the tile's M7 PG pins), 2 clock vs clock |
| M8 | 475 | 297 clock net vs die obstruction, 74 clock net vs PG stripe, 104 clock vs clock (min step 83 included) |
| M9, V8 | 8 | clock vs obstruction / PG |

- 2,788 of 2,800 markers lie within 0.5 um of a die clock inverter body; 2,796 within 2 um. They sit on 250 sites.
- No marker is at the unit box or crop edge. No marker involves a fixed net of an earlier pass (this is pass 1; the
  685 other clock nets are special with no shapes). No abstract signal pin is involved.
- So the answer to the classes asked: PG stripe 329 (M1 178, M7 77, M8 74), abstract obstruction about 1,900
  (M1-M7), die obstruction on M8/M9 301, via stack = all of M2-M6, fixed net 0, unit boundary 0, macro pin 0.

## 2. Root cause

**The die clock inverters are placed on top of the partitions, and the abstracts are solid there.**
- The unit has 606 `CKINVDCx16` cells; 600 lie inside a tile's bounding box (6 outside). Their pins are on M1.
- The unit's 141 own nets have 282 M1 cell pins and 43 M9 tap terminals; the wire is on M8/M9 (6.7 / 4.7 mm). Every
  cell pin therefore needs one via stack M1 -> M8. The log counts 254 up-vias on each of M1..M6: one stack per pin
  that DRT managed to build.
- The tile abstract (closed view, `write_abstract_lef -bloat_occupied_layers`) has ONE obstruction rectangle on
  each of M1..M7 covering 99.2 % of the tile, plus 164 full-height M7 PG pins. Each stack crosses that slab once per
  layer: one short per layer per stack. That is the "252 on each of M2-M6". It is the stack count, not a layer effect.
  M1 and M7 are higher because the cell's own M1 pins and rails and the tile's M7 PG pins add shorts.
- It cannot converge: both objects are fixed (cell position, abstract). DRT can only move the stack inside the
  slab. Iterations 3-9 go 2,679 -> 2,604; the pilots are flat for the same reason.
- The plan does reserve islands for die clock cells (`clock.die_islands_um`, 63 per tile, 8.64 x 8.64 um, one row at
  y 349.92-358.56), but they belong to an older clock. Of the 600 cells over tiles, 3 have their centre in a declared
  island. The adopted regional tree (link_htree + DME, feed hk6) puts its cells elsewhere, and the kit was built
  without island windows (`--island-sites` is not in its arguments).

**Second cause, M8/M9 (about 480 markers): GRT-only obstructions are still in the route database.**
- The unit database carries 51,091 M8 and 45,971 M9 die obstructions from `grt/obs.tcl`. The kit writes them for
  global route: PG stripes as obstructions, and `reserve_rects`, the tracks reserved FOR the clock legs (0.4 um wide).
- In detail route the clock wire is put on its own reserved track and shorts against the reservation: 297 of the
  475 M8 markers name an obstruction; the 0.4 um reservation class is the largest.

Not the cause: unit split, crop, reach, pass colouring, small worker. Form (a) and form (b) agree to 1 marker at
iteration 0 and u201 a/b are identical through iteration 3 (3,276 / 2,786 / 2,800 / 2,679).

## 3. Fix, ranked, with the what-if

**What-if wi1 (u201, same database, same guides, same steps):** the tile abstract's M1-M7 obstruction and M7 PG
pins cut by a window at every clock cell body (+1.08 um each side; 600 windows, under 5,511 um2 of 6.6 mm2 of tiles).

| | iteration 0 | iteration 1 | by layer at iteration 1 |
|---|---|---|---|
| as built | 3,276 | 2,786 | M1 668, M2-M6 255-258 each, M7 335, M8 782, M9 108 (iteration 0 table) |
| wi1 windows | 621 | 96 | M1-M7: 0. M8 91 (short 55, spacing 26, min step 10), M9 4, V8 1 |

So the windows remove every M1-M7 marker in two iterations. The 96 left are all M8/M9.
wi2 (windows + the GRT-only obstructions removed from the route database): 340, 44, 44, 21; see section 6.

Ranked changes:
1. **Remove the GRT-only obstructions before detail route** (owner DIE-HEAD-ROUTE-1, `unit_prep.py`; KV the same):
   delete every die obstruction on M8/M9 that comes from `grt/obs.tcl` (clock reservations and PG duplicates).
   The real PG stripes are in the database as special wires and stay.
2. **Clock cell sites must be holes in the types** (owner HEAD-99 for the plan, KIT-OPS-5 for the clock kit):
   - Take the cell list of the ADOPTED kit clock, map each cell into its partition type frame, union over all
     instances of the type (`apply_clkmesh_sites.py` does exactly this) and write `clock.die_islands_um`.
     Measured on this crop: R0 tiles share the template (97 of 98 and 70 of 93 sites equal to tW1b8's 141);
     the MY tiles have 0 exact matches after mirroring. Force one site template per type (mirror the R0 tree for
     MY/MX/R180) before the union, otherwise the tile carries two or four sets.
   - Build the kit with `--island-sites`, and extend the window cut from M1-M3 to M1-M7 for closed views
     (`island_windows` / `abstract_lef`, `ISLAND_PG_CUT` already cuts M7 PG).
   - A signed type whose layout is not empty at a site must be rebuilt with the island as a placement and M1-M7
     routing blockage. For hd_tile this is one type for about 300 instances. NOT verified by me: whether the signed
     hd_tile is empty at the new sites (its `6_final.odb` on epyc2 did not load: read_db iostream error; check the
     copy). Expect it is not empty, since the sites are not the declared ones.
   - Cheaper alternative to test first (KIT-OPS-5): snap the region tree cells to the islands the type already has.
     With 63 islands in one row against 141 cells spread over the tile height I do not expect it to hold the
     405 um leg bound; a one-kit run answers it.
3. **Tap ends** (owner KIT-OPS-5, low): the 43 taps of a unit are die terminals on M9 (`t_<part>__clk_tN`,
   DRT-0422 "no track through the centre" on all 43); the tile's real `clk_tN` pins are on M7 and are not on the
   net. Connect the net to the abstract pin so the last drop is routed and checked. Not a cause of the flat count.

Gate for "one unit at 0": u201 with 1 + the windows. Then the three pilot units, then volume.

## 4. Stop list

- Stop iterating the six pilot runs (u198/u201/u261, forms a and b): they are at 2,604-2,621 and cannot fall.
- Stop the full-die run `p16g/drt7_small96_TT`: same database, same two causes, no iteration line yet.
- Do not start pass 2..11 or any KV unit until one unit is at 0.
- Do not tune DRT (iterations, costs, worker size, pin access) for this; do not move via stacks by hand.
- Do not regenerate abstracts with "pin shape on the plan layer only" (the earlier inference in
  FABLE-CLOSURE-STRATEGY lever 2): no abstract pin is in any marker.
- Do not keep the windows what-if as a result: it only shows the mechanism. A window over a type that is not empty
  there hides a real short.

## 5. KV

Same cause, three layers instead of seven. On the kvgeom6 route kit (epyc10 `die-kv-route-1/runs6/p6/die_grt.odb`):
- 32,856 `CKINVDCx16` die clock cells, all 32,856 with their centre inside a partition and under that partition's
  M1, M2 and M3 obstruction (plan abstracts; M4-M7 are not solid there).
- 437 of 32,856 are inside a plan-declared die island (the plan has 4,977 island rectangles in 44 of 56 types);
  the kit was built without `--island-sites`.
- 65,712 M1 cell pins on 32,858 nets: expect about 3 shorts per pin on M1-M3 plus the M8/M9 class, since the same
  `obs.tcl` reservations are in the database.
- DIE-KV-ROUTE-1's check "M8/M9 abstract pins against PG: 0 shorts" is correct and is not this class.
Keep KV units stopped; apply fixes 1 and 2 with KV's region map.

## 6. Later results

u201, crop form, same guides and step table, violations after iterations 0 / 1 / 2 / 3 / 4:

| run | 0 | 1 | 2 | 3 | 4 | what is left |
|---|---|---|---|---|---|---|
| as built (pilot u201_b) | 3,276 | 2,786 | 2,800 | 2,679 | 2,619 | section 1 (2,604 at iteration 9) |
| wi1: windows at the clock cells | 621 | 96 | 96 | 74 | 73 | M8/M9 only: 61 clock vs die obstruction, 9 min step, 3 clock vs PG |
| wi2: windows + no GRT-only obstructions | 340 | 44 | 44 | 21 | (stopped, 4 steps asked) | 19 min step on M8 (clock net alone, 7-24 nm steps), 1 short M8 and 1 short M9 clock vs PG |

- **0 was NOT reached** in the 4 steps I ran. wi2 was still falling (44 -> 21 on the first DRC-driven step); the
  stock table has 21 more steps. The M1-M7 classes are gone in both what-ifs from iteration 1 on.
- The 19 M8 min-step markers are own-net geometry (a via landing or jog on the M8 clock wire), not a fixed-object
  conflict. INFERENCE: they clear in the DRC-driven steps; if a residue stays, it is the M7-to-M8 via landing against
  the clock wire width, to be read from the marker list of a 10-step run.
- Cost seen: wi1 83 GB and wi2 99 GB peak against 9.4 GB as built. I did not find which of my two changes causes
  it (the abstract obstruction cut into 548 rectangles per layer, or loading through LEF + DEF instead of the
  database). Measure on the real fix before volume; it sets units per host.
- Files: epyc2 `/srv/opentallas-scratch3/claude/fable-pd-head-0700/wi1` and `wi2` (`drt.log`, `drc_TT.rpt`,
  `lef/ot_s81hd_tile_p.lef` = the windowed abstract, `mklef.py` one level up).

Next step for DIE-HEAD-ROUTE-1: rerun wi2's form for 12 steps on u201 with `-output_drc`; that is the "one unit at
0" proof of the mechanism. In parallel HEAD-99 + KIT-OPS-5 make the sites real (fix 2), because the windows are not
valid on the signed tile until the type is empty there.
