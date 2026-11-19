# FABLE-PD-QC-1230 2026-11-19 12:50 PST: QC coll_core wall, cbn_q11 stretch, st_a detours, N4.6f3 / N4.6e structure

Reviewer: FABLE-PD-QC-1230 (Fable). Read-only: no job launched, killed or patched. Technical PD only.
Marking: **V** = I opened the report, LEF, plan or render this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Sources (V): epyc9 `qc-coll-core-1118/c5,c20.rpt` (attempt_7), `qc-plan-r3-n41p/pkits/pk45_coll/gen/coll_core` (congestion-5.rpt,
tt_setup_repair.log, smells.json, density.png, macros/*.lef), `n46/plan_n46_g3.json` (carries f3), `n46g.py`, `n46f2.py`, `n46f3.py`.
Levers of FABLE-CLOSURE-STRATEGY 11:45, QC-PLAN-R3, SONNET-FIX-QC and QC-OWN-1119 are not repeated here.

## 0. Headline

1. **coll_core does not fail on bus bundles crossing a wall. It fails on macro pin faces that have no channel (V).** 75 % (attempt_7
   round 20) to 90 % (pk45_coll round 5) of the overflow sits inside the bodies of g_xf_1 / g_xf_2 and the two u_rring SRAMs, where the
   router has 5 H + 6 V tracks per gcell against 26 to 27 on open floor. Each fold slice has 512 `src` pins on its west face, and those
   faces look into slots of 4.3, 13.0 and 4.3 um. Fix = move cores (no re-shape), section 1.
2. **pk45_coll (the N4.5 form) repeats attempt_7, worse (V).** Round 5 sum 75,675 (attempt_7 round 5: 46,172); placement TT after repair
   -997.94 ps, tns -691,971. It will not give a usable GRT TT. Stop list item 1.
3. **cbn_q11: two 516-bit register groups share the same six column anchors (V).** The N4.4 row put `u_x_3_3.u_st.b_d` on the sites of
   `u_d6_u_fab_u_x_3_2_a_d.q`. Both cbn_q11 types carry it. Section 2.
4. **N4.6e moves the x_fw_ctl station into a channel that already holds two ft stations, and the bin site leaves two consumer legs over
   405 um (V from plan geometry).** Section 3 and 4.
5. **N4.6f3 has no proof kit on its own type, and cbf_q00 keeps four 625 to 637 um legs (V).** Section 4.

## 1. coll_core congestion

### Evidence
- V, overlay of every overflow row on the plan hard-core boxes (reports are capped at 10,000 H + 10,000 V rows, so sums are floors):

| report | sum | inside a core body | within 8 um of a core edge | open floor |
|---|---|---|---|---|
| attempt_7 round 20 (c20) | 33,087 | 24,795 (75 %) | 7,364 (22 %) | 811 (2.5 %) |
| pk45_coll round 5 | 75,675 | g_xf_1 + g_xf_2 alone 67,775 (90 %) | about 3,400 | under 1 % |

- V, c20 by core: g_xf_2 H 5,554 + V 2,274; g_xf_1 V 3,335 + H 2,065; u_rring g_b[0] H 4,864 + V 1,308; u_rring g_b[1] H 2,623 + V 1,361;
  u_pring 1,411. **g_sring has no row in the top 24**: the SRAM column at x 449 is not a hotspot (correction to the 12:04 post).
- V, capacity printed in the rows: inside a fold slice H 5 (4 to 6), V 6, and V 0 on 574 + 471 gcells (pk45); inside the 32x546 SRAM
  H 8, V 10; open floor 26 to 27. Gcell 0.57 um. The fold-slice LEF obstructs M1 to M5 over the full body, so only M6 / M7 pass.
- V, LEF pin faces: `ot_coll_fold_slice` 190.08 x 211.68: `src[512]` + `red_in` on the **W face, M4**, y 32 to 179; `sum[128]`, `e_out`,
  `v_out` on the E face, M4; clk / rst_n on S, M5. `ot_sram_1r1w_32x546`: 826 pins W (rd_out 546, wd_in 267), 825 pins E (w_mask 546,
  wd_in 279), all M4.
- V, plan geometry (plan_n46_g3 coll_core, 786.24 x 1589.76):

| pin face | pins | channel in front of it |
|---|---|---|
| g_xf_0 W (x 8.6) | 513 | 4.3 um of core to the die edge |
| g_xf_0 E / g_xf_1 W (x 198.7 to 203.0) | 130 + 513 | 4.3 um slot |
| g_xf_1 E / g_xf_2 W (x 393.1 to 406.1) | 130 + 513 | 13.0 um slot |
| u_rring g_b[0] E / g_b[1] W (x 221.0 to 241.9), same on u_pring | 825 + 826 | 20.9 um, and its north end meets g_xf_1 after 5.4 um |
| u_rring top (y 1100.5) to wall bottom (y 1105.9) | - | 5.4 um E-W |

- V, the overflow follows the faces, not the bundle paths: V overflow inside g_xf_2 is 2,012 of 2,274 in x 400 to 420 (its W face);
  inside g_xf_1 it is at x 200 to 240 and 360 to 400 (both edges); open-floor V overflow is 3,175 at x 220 to 240 (the SRAM gap) and 3,348
  at x 380 to 420. H overflow inside g_xf_1 / g_xf_2 is at y 1120 to 1220.
- V, pk45 placement density (smells.json): 0.87 to 0.88 in six bins at x 399, y 1109 to 1289, i.e. the 13 um slot is full of cells.
- V, named nets in the overflow rows of g_xf_1 / g_xf_2: `u_cland_io_collective__in_data/u_ring.dch[*].u_dsel` 14 to 21 %,
  `u_bout_rec_tx_s0` 4 to 16 %. in_data is 512 bits and `src` is 512 bits (I: the in_data read side is the `src` driver of the four
  x-fold slices, so every bit must reach four W faces).
- V, density.png: the east strip x 600 to 786 above y 900 and the band x 40 to 450, y 717 to 907 are empty. Room exists.
- V, pk45 `tt_setup_repair.log`: before -1100.83, after -997.94, tns -691,971, 926 cells added, 406,163 instances.

### Root cause
A 4.3 um slot holds about 7 gcells x 27 = 190 V tracks; a 13 um slot about 620. Each must serve 643 M4 pins. The nets therefore arrive
over the slice on M6 at 5 tracks per gcell and drop to M4 at the face, and the SRAM gap (1,651 pins in 20.9 um) has no north exit. The
N4.5 / N4.6 station rows ("wires cross cores on M6/M7") add demand on the same two layers. No GRT setting fixes a pin face without a channel.

### Fix, ranked (P; core moves only, r-core-shape respected; coordinates to be snapped by the plan tool)
1. **Wall respace (plan row, QC-PLAN-R3 composes, rows by QC-COLL-CORE-1118 or a new lane QC-COLL-WALL).** 48 um channel in front of
   every `src` face: g_xf_0 x 8.6 -> 51.8, g_xf_1 203.0 -> 289.9, g_xf_2 406.1 -> 528.0; g_pf_3 follows g_xf_0, g_xf_3 follows g_xf_2.
   3 x 190.1 + 3 x 48 = 714 um of 777 um core. The open channel above g_xf_1 keeps both N4.6 tx station sites clear.
   Expected: 48 um = 84 gcells x 27 = about 2,270 V tracks for 643 pins (28 % use, was over 100 %); removes the cause of 75 to 90 % of
   the overflow. Pass mark for the proof kit: round-5 sum under 5,000 and inside-core share under 30 %.
2. **SRAM field (same row).** u_pring / u_rring g_b[1] x 241.9 -> 300 (gap 79 um for 1,651 pins), g_sring column x 449.3 -> 530 (gap
   52 um, y unchanged: moving it south would hit g_pf_0). u_pring + u_rring rows 60 um south into the empty band (u_rring top
   1100.5 -> 1040.5): a 65 um E-W channel under the wall, about 2,960 H tracks where there are 5.4 um today.
   Expected: removes the u_rring / u_pring share (13.2k of 33.1k in c20).
3. **in_data bin site (plan row).** coll_core relay_sites cover rec_rx_s0 / s1 / s2 and fltv_s only (V); `u_bin_io_collective__in_data`,
   in_tag and cmd have none. With the channels of fix 1, site the in_data bin north of the wall (x 242 to 528, y 1330 to 1560) so one
   registered 512-bit bus enters the three channels. 0 cycles. Do this after fix 1, not instead of it.
4. **Timing is a separate item.** -998 ps at placement is not a congestion number. No path print exists in the kit logs (not checked:
   which ends). SONNET-FIX-QC or the coll owner prints the worst 20 ends from `4_cts.odb.tt` before any new coll_core timing row.
Owner: QC-PLAN-R3 (compose, bind, G0 KITFIT); rows QC-COLL-CORE-1118 if alive, else new lane. One private proof kit to GRT round 5 (r712).

## 2. cbn_q11__cl49ae4555 OT_XSTN_STRETCH (132 / 2712)

### Evidence
- V (plan_n46_g3 relay_sites, both `cbn_q11__cl49ae4555` and `cbn_q11__cl5cc92dfe`): `u_u_fab_u_x_3_3.u_st.b_d` (516 bits) and
  `u_d6_u_fab_u_x_3_2_a_d.q` (516 bits) have the **same 6 unique sites**: x 1159.92 to 1181.52, y 2309.04. `u_st.cnt` and `u_st.run` sit
  there too. That is 1,037 flops on six anchors (86 + 86 per anchor).
- V (type note): N4.4 moved the x_3_3 b_d / cnt / run sites to "the tap_d row +60.48 um (y 2309.04), x mirrored from x_3_2". The mirror
  landed on the last d6 stage of x_3_2.
- V: in the same 86 um east margin (x 1149 to 1235): x_3_3 tap_d 444 + cap 64 at y 2249, and the bc_o33 station 517 bits at
  (1192.3, 2272.3), 37 um from the b_d anchors.
- R (QC-OWN-1119): 64 / 2832 on N43R, 132 / 2712 on N45F and N46C. The count doubled after the N4.4 move.
- Not opened: the kit resize log (no kit directory for this type was found on epyc8 today), so which b_d instances fail is I.

### Root cause (I, on V geometry)
One of the two groups is displaced by the legaliser by one or two column heights (86 flops x 0.27 = 23 um each). b_d sinks are close,
so a 25 to 50 um displacement is over 3x the direct distance. The N43R 64 were the old north-face site (600 to 1001 um, per the note);
N4.4 fixed that and created the collision.

### Fix, ranked (P)
1. **Plan row (QC-PLAN-R3, next N4.6 compose):** x_3_3 `u_st.b_d` / `cnt` / `run` anchors to x 1194.48 to 1216.08 (+34.56, same y), or
   keep x and move +48.6 um in y; then check the bc_o33 station at (1192.3, 2272.3) is at least 25 um away. Both cbn_q11 types.
   Expected: 132 -> 0 at place; no cycle change (same registers).
2. **Tool (QC-PLAN-R3, `ft_site_dedupe`):** extend the dedupe from FT bit sites to relay_sites groups: two groups of different instances
   on one anchor is an error. PRECHECK-1119 gets the same check as an estimator.
3. `cbn_q11__cl5cc92dfe` is running on epyc9 (dpkit, 44 min at 12:40) with the same sites: expect the same stop; it is the free test.

## 3. sle_st_a_v2 b_tw_data_i / x_fw_ctl (-108 ps), A/B pk46_ctl2 vs pk46_e3

State (V 12:49): `pkits/` holds no pk46 directory; both G0s end "4 errors" (the known KITFIT 4, R). The A/B has not started, so the
points below can still be taken into the test form.

### Evidence (V, plan_n46_g3 `sle_st_a_v2__pv30dda31f__pvd2ec7769`, 622.08 x 1339.2)
- b_tw_data_i: 1080 bits, E face y 277.5 to 464.4, landing box cl_b_tw_data_i x 561.6 to 607.0. Consumer relay sites
  `u_pd1_b_tw_data_i_*` are on the E faces of the four cores: u_r0 (430, 157 to 165), u_r1 (404, 486 to 494), u_r2 (395, 831 to 839),
  u_r3 (395, 1168 to 1176).
- N4.6e bin: 1080 flops, 40 x 27, bbox x 479 to 521, y 533 to 547 (42 x 14 um), x pitch 1.08 = one flop width.
- Legs from the bin centre (500, 540): to u_r1 146 um, u_r2 400 um, **u_r0 449 um, u_r3 737 um**. Landing to bin 254 um. The u_r0 share
  goes north 170 um to the bin and comes back south 379 um; direct landing to u_r0 is 363 um.
- x_fw_ctl new stations (522.1, 1.0) (450, 120) (300, 257) (220, 512) (420, 640). Other ft stations in the plan: x_ctl_fw 631 bits at
  (330.2, 271.0), **33 um** from (300, 257); b_hw_ctl_hc0 1,573 bits at (385.4, 240.9), 86 um away; cws0 at (376.1, 669.6), 74 um from
  (420, 640). The u_r0-top channel (x 268 to 430, y 240 to 406) then holds three ft stations = 2,740 flops, and x_fw_ctl (S to E) crosses
  x_ctl_fw (E to S) there.
- V (`n46g.py`): the station check tests the station **centre point** against core boxes; the bin check tests bbox corners. Station
  centres are 10.9 to 15.6 um from a core (n46g3_report), less than half a 536-bit station footprint.
- R (SONNET-FIX-QC 08:02): the box x 450 to 615, y 320 to 645 is 64 % same-bus + bin demand after x_fw_ctl leaves.

### Root cause
The detours are the 1080-bit bus funnelling to one point beside its own landing, with two ft buses in the same box (R). N4.6e removes
23 % of the box demand (R) but (a) puts a 14 um tall funnel mouth for 1080 + 1080 nets in the box, (b) leaves two consumer legs over
405 um if the bin drives all four cores (I: fan-out per core not read from the netlist), and (c) relocates x_fw_ctl onto x_ctl_fw.

### Fix, ranked (P), owner QC-PLAN-R3 with SONNET-FIX-QC for the netlist read
1. Read the A/B on **two boxes**: B1 x 450 to 615, y 320 to 645 (the b_tw nets) and B2 x 268 to 430, y 240 to 406 (the new x_fw_ctl
   crossing). A pass on B1 with new overflow in B2 is a move, not a fix.
2. SONNET-FIX-QC: one netlist read, does `u_bin_b_tw_data_i/q` drive all four cores or 270 bits per core. If per core: four bin slices
   sited on the landing-to-core lines (u_r0 slice near (470, 250), u_r1 (470, 480), u_r2 (450, 700), u_r3 (450, 800) + its existing
   pd1), 0 cycles, no funnel. If broadcast: keep one bin but as a bit-ordered strip of the landing height (x 500, y 300 to 560), and the
   u_r3 leg needs a second stage.
3. x_fw_ctl station 3: at least 80 um from the x_ctl_fw station (330.2, 271.0), and `n46g.py` checks the station bbox, not the centre.
Expected: b_tw detour nets back to under 1.3x direct; value to be read at GRT TT in the kit frame (the -108 is stock RC, R).

## 4. Structural review of the in-flight events

### N4.6f3 (plan_n46_f3r.json; cbf_q00_s2 u_t01 / u_t10 swap, reset remap)
- V: tiles u_t00 (86.4, 77.8), u_t10 (691.2, 77.8), u_t01 (86.4, 1304.6) MY, u_t11 (691.2, 1304.6) MY: family arrangement, equal to
  cbf_q00__cl1b5a6458. Reset anchor: 39 relays, 10 local resets (family 29 / 5). `n46f3.py` copies s2's own START / local resets /
  anchor from N4.6d-b: structurally the right form (names stay in s2's own tree; the f2 rename needed a same-depth relay that s2 lacks).
- **Finding 1 (V): internal_stations `bus:bc_i00` legs 633.6 / 636.7 um and `bus:bc_i10` 625.0 / 628.1 um, 517 bits, 1 station each,
  in cbf_q00_s2 and in the family.** Both are over the r713 405 um rule and are not listed in the event notes. P: +2 stations each
  (4 legs of about 318 um, +2 cycles on the two lanes via sync_fixed_cycles), or state why the leg is covered (landing bin not read).
- **Finding 2 (V): the d6 chain `u_d6_u_fab_u_x_0_0_a_d.r[0..5]` is sited at 240 um steps** ((546, 931) (546, 1171) (372, 1238)
  (130, 1238) (84, 1434) (84, 1674)). The six stages end at y 1674; the 653 um leg QC-PLAN-R3 reports follows. P: re-space the same six
  stages evenly over the full route (the 354 um form of QC-PLAN-R3-x01-site.json); 0 cycles, removes the 653 um leg.
- **Finding 3: no proof kit on cbf_q00_s2.** Both N4.6 proofs are on sle_st_a_v2. r712 asks one private kit on the worst type of the
  event: cbf_q00_s2 to CTS TT on n46j before apply.
- Not checked: the offline resolve "39 kept, 0 remaps" (R) against a bound reset tree.

### N4.6e (plan_n46_g3.json)
Section 3 items. In addition (V): `sync` reports +2 cycles on sl_E1 / E3 / E5 x_fw_ctl (15 -> 17), bus_deltas empty, rule_broken empty:
latency side is consistent. The x_fw_ctl route is now 1,372 um in 5 hops for an S-to-E feed-through whose direct path is about 770 um.

## 5. Owners

| item | action | owner |
|---|---|---|
| coll_core wall respace + SRAM field + in_data bin | plan row, proof kit to GRT round 5 | rows QC-COLL-CORE-1118 or new QC-COLL-WALL; compose QC-PLAN-R3 |
| coll_core -998 ps ends | print worst 20 ends of 4_cts.odb.tt | SONNET-FIX-QC |
| cbn_q11 x_3_3 b_d anchors + group dedupe | plan row + ft_site_dedupe | QC-PLAN-R3; QC-OWN-1119 keeps the row and reads cl5cc92dfe |
| st_a bin fan-out read, two-box A/B read | netlist read, congestion read | SONNET-FIX-QC, QC-PLAN-R3 |
| cbf_q00 bc_i00 / bc_i10 legs, d6 re-space, s2 proof kit | plan row, kit | QC-PLAN-R3 |

## 6. Stop list
1. Do not wait on pk45_coll GRT and do not read it as a timing result: round 5 is 75,675 on the same slices, placement TT -998. Its
   owner (QC-PLAN-R3) decides the cancel; I am read-only.
2. No coll_core relaunch, GRT iteration change or allow-congestion variant before the wall respace.
3. No further station or relay row that routes a coll_core bus "over cores on M6/M7". The srr_cone region does not touch this cause.
4. Do not name the g_sring column as the hotspot.
5. No relaunch of either cbn_q11 type on a plan that keeps the shared anchors; a rerun repeats 132.
6. Do not apply N4.6e on the b_tw nets alone (box B2), and do not apply N4.6f3 without a cbf_q00_s2 kit at CTS TT.

## 7. Not checked
- Cell positions of the in_data ring, dsel muxes and bins in coll_core (no DB opened; the in_data-to-src link is from net names).
- The cbn_q11 resize log; the failing b_d instance names.
- b_tw_data_i fan-out per core; station footprint shape of ft stations.
- Whether a landing bin already splits the cbf_q00 bc_i00 / bc_i10 legs.
- Hold: nothing here changes the die intra hold -268 or the per-type hold window pilot.
