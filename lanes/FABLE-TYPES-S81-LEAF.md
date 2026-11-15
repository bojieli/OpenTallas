# FABLE-TYPES-S81-LEAF 2026-11-14: root causes of the unclosed S81 leaf types

Scope: the 80 unclosed `ot_s81sl_leaf__*` (75) and `ot_s81sl_kv_leaf__*` (5) types. 67 have at least one physical-design problem on record since 11-12; 13 have none yet (kv_leaf t1/t2, t16, t26, t31, t33, t36, t44 clf6cf8492, t66, t67, t70, t75, t8). t34 / t9 / t73 / t75 / t39 are in FABLE-HARD-S81 and are not repeated.

Method: autopilot CLASSIFY lines 11-12..11-14 (138 verdicts), kit logs and reports of 254 leaf kit dirs on 7 hosts, the post-GRT TT gate log of 13 builds, the generator source, and one read-only STA on a copy of the leaf t69 global-routed database (ot-run, epyc8, 28 GB, 2 min). Nothing shared was changed, nothing killed.

Status of each statement: MEASURED = read from a log, report, source file or the STA run; INFERENCE = fits the numbers, not proven.

## 0. Verdict

No leaf build has ever finished detail route on the current plan, and none would sign off if it did. Three walls stand one behind the other, and today's lanes work on the first two only.

| wall | what stops | builds / types measured | fix in flight |
|---|---|---|---|
| 1 hold repair inside GRT | 3-h stall at -10 to -110 ps | 35 types | pre-GRT hold (on in kits since about 14:30): works |
| 2 detail route | DRT-0255 in iteration 1 | 14 builds, 8 types; 0 leaf builds got past it | PG-AWARE-1, not in any wave kit yet |
| 3 TT setup at sign-off | -164 to -267 ps on 197-1,600 endpoints (gate -42) | 13 of 13 builds, 8 of 8 types | none for the family |

Wall 3 and wall 1 have the same cause: the tap window in the kit SDC (section 1). It is the one finding of this review that no lane owns.

## 1. Cause A: the tap window charges every tap its worst pair (all leaf types)

### Evidence (MEASURED)

- Kit SDC (`constraint.sdc`, t69): every clock tap port has `set_clock_latency -source -early -<D_p>` with D_p 68-162 ps, late 0. t42: 118 on its ports. kv_leaf t5: 58-110.
- Generator, `gen_phys.py:2184-2200`: D_p is the maximum, over all regions of the type and over **every other tap q**, of the die clock proof's damage. A cross-tap setup path loses D of the capture tap; a cross-tap hold path loses D of the launch tap. Same-port pairs get it back as CRPR (t42 worst path: 118.00 credited).
- Post-GRT TT gate (`postcts_gate_TT.log`, global-route parasitics), every leaf build that has one:

| type / form | pre-GRT hold | TT setup WNS | endpoints < 0 | hold cells on the worst path |
|---|---|---|---|---|
| t69 wave a (intel2) | yes, 15,206 cells | -201.47 | 753 | 509 ps |
| t69 PG-AWARE proof | no | -200.54 | 501 | 0 |
| t25 cl431 t25A | yes, 7,332 | -250.91 | 656 | 397 ps |
| t25 cl431 t25B | no | -163.59 | 332 | 83 ps |
| t25 cl431 wave a4 | no | -248.86 | 202 | 150 ps |
| t25 cl431 t25af10 | yes, 8,730 | -221.12 | 270 | 0 |
| t40 clf8 t40f | yes, 11,328 | -261.68 | 965 | 407 ps |
| t21 t21f | yes, 17,393 | -195.53 | 711 | 151 ps |
| t42 fa / fb | no | -245.89 | 1,020 | 0 |
| t5 wave | yes, 14,293 | -219.42 | 498 | 0 |
| t6 p2 / pgcap proof | yes, 17,350 | -267.19 / -242.30 | 1,504 / 1,600 | 0 |
| kv_leaf t5 genB | no | -166.83 | 224 | 704 ps |

- STA on the t69 wave database (`5_1_grt.odb` copy, TT, same SDC, same RC; base reproduces the gate exactly):

| case | setup WNS | TNS | setup endpoints < 0 | TT hold endpoints < 0 |
|---|---|---|---|---|
| kit SDC | -201.47 | -47,770 | 753 | 174 |
| early source latency of every tap port set to 0 | -114.01 | -3,195 | 85 | 0 |

  The window is 668 of 753 violating endpoints and 93 % of the negative slack. 740 of the 753 are cross-tap paths; the median window on them is 119 ps.
- The same window drives the hold problem. Pre-GRT hold log of t69: FF hold -202.5 ps on 5,923 endpoints, 3,802 of them cross-tap (same-tap: 20). It takes 15,206 hold cells (7.1 % of the instances), and 364 of the 753 setup violators then carry hold cells (median 253 ps of them). Of the 448 endpoints below -42 ps, 150 pass with the hold cells removed.
- Where the 448 endpoints below -42 ps are (t69):

| start -> end | endpoints | what the path is made of (medians) |
|---|---|---|
| vp source registers (`g_hig/hog ... u_src`) -> lane ROM core pins `ln_*/r1[*]` | 239 | no logic; 15 wire repeaters, 516 ps; capture window 139-144 ps |
| vp driver -> vp driver registers (`dswp_q -> hw_d_q`) | 87 | 400 ps of hold cells, 248 ps of repeaters |
| reset relay `u_rrl` falling -> rising (half cycle) | 61 | half-cycle path, cross-tap (INFERENCE: the window is charged against 416 ps) |
| vp driver / source -> SRAM write pins `u_b0/u_b1` | 38 | 271 ps logic, 181 ps hold cells |
| other | 23 | |

### What is wrong

- The die clock delivers the taps of one leaf with 68-162 ps of unshared arrival after the common-path credit. That is real die skew inside a 1.44 x 1.23 mm partition and the kit must cover it.
- The kit covers it with the worst pair of each port against all other taps, including taps it exchanges no data with. INFERENCE: for the pairs that carry data the damage is smaller; the plan holds only the per-port maximum, so I could not measure by how much.
- Either way, 833 ps minus about 120 ps of window on setup and about 120 ps plus guard on hold leaves the leaf no room: the hold cells that fix one side break the other.

### Dead ends

- Any leaf route to sign-off on the present SDC. 50 leaf types were at route at 19:15; with pre-GRT hold and allow-congestion they now reach detail route, and each still ends at setup -160 to -270 ps.
- `ot_s81sl_vp` write-port RTL (TL-LEAF42SETUP) as the family setup fix. On t69 the SRAM write class is 38 of 448 endpoints. It stays useful for those, but its two overlay builds (KO4 t42, t6) have sat at geom PASS since 11:04 with no route, and the overlay bind was interrupted (signal 15) before it was admitted.
- Late ECO on a routed leaf: 448-1,600 endpoints is not a near miss.

### Fix (structural, in this order)

1. Die clock (DIE-S81-92, with the die clock tool): one landing per leaf partition and a balanced local tree to its 39 grid taps and core taps, so tap-to-tap damage inside a leaf is the local tree's skew, not the die spine's. Target D_p of 30 ps or less. This is the owner's regional-clock rule applied to the leaf; it removes the cause for setup and hold together.
2. Model, same event (gen owner, KIT-OPS-5): `die_sta_related --kit-window-out` takes the maximum only over taps q that have a data path with p in the bound netlist (the kit already lists them for `tap_pair_plan.tcl`). No physics is waived: a pair without a path cannot fail.
3. Plan (S81-LEAF-PLAN, B6): a link register at each lane-core group for the vp source buses (`--link-reg`, +1 cycle on that link class, pre-approved), so the 1-mm zero-logic runs end at a register beside the core. This is the 239-endpoint class and it remains at -59 ps with the window gone.
4. Reset relay `u_rrl`: make the falling-to-rising hop same-tap (61 endpoints; `tap_chain_affinity` already exists) or drop the half-cycle form.

### Proof

- Step 2 costs no build: rerun `die_sta_related` for one leaf type with the related-pair mask and my STA with the new D_p (script and database copy: epyc8 `/srv/opentallas-scratch2/claude/fable-types-s81-leaf/`, `sta_leaf.tcl`, 2 min). Pass mark: fewer than 150 endpoints below 0.
- One build after the event: t69 (kit and numbers above). Pass marks: pre-GRT FF hold before repair above -80 ps and under 5,000 hold cells; post-GRT TT setup WNS above -42 ps.

## 2. Cause B: hold repair pads setup-critical paths (all leaf types with pre-GRT hold)

- MEASURED: t69 worst path `vp_driver_dswp_q -> hw_d_q[99]`: 6 `HB4xp67` cells, 509 ps of 1,228 ps arrival; one of them drives 9 loads at 173 ps slew and costs 159 ps. Same form on t25A (397 ps), t40f (407 ps), kv_leaf t5 (704 ps).
- MEASURED: t25 with and without pre-GRT hold: 332 -> 656 violating endpoints; t69: 501 -> 753.
- Why: `pregrt_ff_hold.tcl` runs `repair_timing -hold` on placement RC with the TT scene as setup guard. The path looks 300 ps positive there; global route then adds 8-15 repeaters (max wire 100 um) and the slack is gone. The pads sit at the driver of a multi-fanout net, so one short branch pads every long branch.
- Fix (hold tool owner, TYPE-S81LEAF29): give the pre-GRT pass a setup margin equal to the measured GRT growth (`-setup_margin 150`), and pad at the violating endpoint, not at a driver with fanout above 1. Not a new gate: it only decides where the cells go. With cause A fixed the demand falls by the window anyway.
- Proof: rerun the pre-GRT pass on the t69 `4_cts.odb` (23 min), then GRT; count TT endpoints below 0 against 753 and 501.

## 3. Cause C: DRT-0255 (PG collisions): owned by PG-AWARE-1, nothing new

- MEASURED: 14 leaf builds on 8 types (t21, t25 cl431 x5, t40 clf8, t42 x3, t54 cl501, t69, t6, kv_leaf t5) ended in iteration 1 with DRT-0255; no leaf build passed it. Nets are `u_ft_ft*_o_*` repeaters and landing-ring nets near the W edge.
- MEASURED: wave kits generated today have `OT_PG_TRACK_TRUTH = 1` and no `OT_PG_CELL_KEEPOUT`; PG-AWARE-1 measured that the first alone does not clear it.
- Consequence: every leaf route now in flight ends here until the keep-out is in the S81 source. Its two leaf proofs (t69, t25) had not reached detail route when I looked.
- Nothing to add to PG-AWARE-1. Order of work: its flag into `die_gen_env` s81 before more leaf routes are spent.

## 4. Cause D: kv_leaf lane cores sit on grid taps (kv_leaf t1, t3, t4, t5)

- MEASURED (`4_1_cts.log`, today's kits): `OT_TAP_CORE 23 core clock pins, 19-20 outside target`. The 16 lane cores have 246 ps internal latency on a grid tap: effective 300-326 ps against 250; `u_vs` 356 ps. The leaf types got early core taps (4-8 outside today, 20-24 on 11-13); kv_leaf did not.
- Effect: kv_leaf t5 hold -242.9 ps on 5,189 endpoints, 3-h stall at -149.4; then DRT-0255; TT setup -166.8 with 704 ps of hold cells on the worst path.
- Fix (DIE-S81-92, leaf clock event): `core_tap_fix` / `pair.py --core-taps` for the four kv_leaf types, as done for leaf. Proof: kv_leaf t5 CTS log shows 5 or fewer pins outside target.
- kv_leaf t3 / t4 "GRT time cap" was repair_design at 12 nets/s on 349 k nets, not congestion (TYPE-S81-GRTCAP); the cap is now 0 in `die_gen_env`. Closed.

## 5. Cause E: GRT overflow (32 types on record): three different things

Binned from the kept congestion reports (net family, edge distance, gcell capacity).

| sub-class | types (measured) | evidence | fix / owner |
|---|---|---|---|
| E1 landing ring at the face | t54 cl706 (a10 today: 23,597; 89 % `u_cland_up` nets, 98 % in x 1300-1443, y 1100-1227), t53 clb6, t55, t2, t22, t47, t12, t59, t29, t32, t40 clf8 | hot spot named `u_cland_*` in the stop line | band events B4L4 / B5 (S81-LEAF-PLAN). t54 cl706: check it is in the 149-type list |
| E2 ft chains in the W strip | t24 cl81 (18,647; all within 60 um of W, y 400-700, 75 % `u_ft_*`), t12, t13, t71, t34, t52, t61, t62 | | B5 edge squeeze; FABLE-PLAN-EVENTS amends for B6 |
| E3 a few gcells over a core | t58 (62 gcells, 61 at capacity 8 or less, ft6 / ft7 at x 500, y 200), t23 (30, ft6, x 500 y 100), t68 (49, vp nets, x 800-900 y 300-400), t43 (62), t14 (28), t45, t50, t37 | the M8-only zone over a hard core | FABLE-HARD-S81 section 2 (no station or band over a core; M9 grant). With allow-congestion they pass GRT |
| inner block | t11 (22,095 at x 200-400, y 1000-1200; `u_ist_leafup` / `leafdn` 33 %; capacity 8 or less on 82 %), t56 (61,035 at x 1100, y 800) | station buses over cores | S81-LEAF-PLAN: re-site those stations (`--ft-resite`) |

- MEASURED: kits generated after about 18:30 carry `-allow_congestion`; earlier ones still stop on GRT-0116 with 30-62 gcells (t23 at 16:16, t54 at 19:06). E1 / E2 at 18-24 k are real and wait for the band events.
- Dead end: more wave attempts of E1 / E2 types on the pre-B4L4 bands.

## 6. Cause F: size after repeater insertion (t3, t1, t6, kv_leaf t5, t57)

- MEASURED, instances before -> after max-wire repair in GRT: t3 398,982 -> 505,664 (then GRT-0183, a ring net boxed in), t1 346,853 -> 444,116, kv_leaf t5 408,258 -> 430,590, t6 368,268 -> 419,271, t57 300,321 -> 380,910. Typical leaf: +25 %.
- Cause: slot fill 0.01-0.03 with cores at the W / E edges (visual class "oversized-slot / low-fill" on 39 types): every bus crosses about 1 mm at 100 um per repeater. The 239-endpoint class of section 1 is the same wires.
- Fix: the link registers of section 1 step 3 and the core moves of B5 / B6 shorten the runs; t3 and t1 go to OVERSIZE-1 if still above 400 k after that. No outline growth: it makes the runs longer.

## 7. Single types

- t72: `OT_CLAND no legal row/site` for `u_cland_ft0_i` in every wave attempt a3-a14 (last 18:29). MEASURED by TL-LEAFT72: ring needs 6,551 flops + 22,760 gates, band 5,163 um2; two extra rects in the same E column place it. The fix is not in the plan, so the wave keeps failing. Owner S81-LEAF-PLAN: add the two rects to t72 in B5 / B6. Proof: place passes in the first wave attempt after adoption.
- DRT-0073 on lane-core pin `c0[0]` (8 types, 11-13): fixed in the core view; later attempts pass. Closed.

## 8. Dead ends, in one list

- Leaf routes on the present tap-window SDC (section 1) and without the PG keep-out (section 3): 50 types at route at 19:15.
- In-GRT hold repair without the pre-GRT pass (variants-1 copies, 14 types stalled at 3 h), and lifting the hold time limit (t44B: 5,163 endpoints left after 7 chunks).
- Write-port RTL as the family setup fix; its idle overlay builds.
- Wave retries of t72; wave retries of E1 / E2 types before B4L4 / B5.

## 9. Not done

- Die pair-damage table per data-related tap pair (decides how much of the window step 2 removes).
- STA of a second type; the family statement rests on the gate numbers of 8 types and the decomposition of one.
- Whether B4L4 / B5 contain t54 cl706 and t11.
- PG-AWARE-1 leaf proof result.

Evidence: epyc8 `/srv/opentallas-scratch2/claude/fable-types-s81-leaf/` (STA script, database copy 616 MB, `out/paths_t69w.rpt`, `out/t69w.log`; can be deleted after the proof of section 1); a copy of the inputs on intel2 under the same path. Parsers ran read-only over ssh and left no files.
