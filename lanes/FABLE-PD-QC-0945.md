# FABLE-PD-QC-0945 2026-11-20 09:45 PST: QC event R4 A4 (s29q103S4Q9N46R4A4) structural review; fixes ranked for V1

Reviewer: FABLE-PD-QC-0945 (Fable). Read-only: no job launched, cancelled or patched; no plan edited; no STA run.
Marking: **V** = I opened the plan, report, log or image this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Gate: DRC 0, routed TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. Hop cap 300 um. Nothing below is a new gate or hold.

Sources (V):
- Plan `zz_s29_qc103_s4q9n46r4_final_preview.json` (sha 2c1e1ca66262) in the live tree `kw45/snap_qwen_compute/qwen_compute_n46r4_a4`; my scripts ran on epyc2.
- PRECHECK on A4, epyc9 `/srv/opentallas-scratch2/claude/precheck-runs/qwen_compute_s29q103S4Q9N46R4A4_11201735/` (133 types, 278 s), and the V0E run `..._N46V0E_11201232/` for comparison.
- G0 A4, epyc10 `qc-plan-r3-n41p/n46/v1_cbc/r4_direct/g0_a4/g0.log`: PASS, 0 errors, 571 warnings.
- Congestion reports of the two kept sle_ctl kits: intel1 `ot-jobs/sle_ctl__cl372cea1c-route-key-cardinal-779827-1795122315` and epyc10 `ot-jobs/sle_ctl__cla4f6f12f-route-civil-redfish-276253-1795122318`, `congestion-10.rpt` of each.
- E3 st_a evidence, epyc7 `.../r4_direct/gen_representative_a3_retry/sust_e3_s1_reseat_evidence/{s1_reseat_405.json,review.md,e3_s1_reseat.png}` and `sust_e3_private_halo_overlay/e3_halo_plan.png`. Both images viewed.
- `lanes/GRT-TRIAGE-1120.tsv`, `lanes/QC-HOLD-0030.md`, `lanes/QC-HOLD-0030-INDELAY.md`, `lanes/posts/QC-PLAN-R4.md`, `lanes/FABLE-CLOSURE-STRATEGY.md` (09:05).

## 0. Headline

1. **A4 is a reset-reach and bind-coherence event. Its data geometry is the V0E geometry (V).** The PRECHECK score table of A4 equals the V0E table in every column except R4 (reset reach 405 -> 300). Hops, taps and cross-tap hold structure did not change. Kits on A4 will generate again, and will then meet the same placement, GRT and hold results as V0E kits.
2. **The E3 rs_s0 / rs_s1 FIRM conflict is in all 11 st_a types, not only E3 (V).** 51 to 77 colliding sites per type. The proven reseat covers one type and uses 391 / 405 um legs.
3. **sle_ctl congestion has one cause (V).** 72 % and 79 % of the overflow of the two kept kits lies in x 300 to 600. 43 % of the nets in those markers belong to the four `b_hw_hc*_o` station chains, which all leave the `u_tap` core from one corner, 8 um from `u_ctl`.
4. **No lockup latch row exists in the plan (V).** 2,941 of 3,141 zero-logic station hops have launch and capture on different nearest taps.

| check | A4 result (V) | verdict |
|---|---|---|
| reset collector trees | 129 of 129 at reach 300; worst hop 298.6 um (coll_s); depth up to 15 (cbn_q00) | sound |
| landing START stage chains | 13,500 stage hops, 0 over 300 um | sound |
| data station hops | 1,030 of 4,692 nominal hops over 300 um, 102 over 405; 99 types, 311 instances | unchanged from V0E |
| die-level reach fields | `die.reach_um` 405, `reset.hop_um` 405, `budgets.ft_station_max_um` 405 | local 300 only |
| first rank | 178,437 of 1,212,611 port bits on 102 types have no planned register within 50 um | unchanged |
| exact-bank site conflicts | 11 st_a types, rs_s0 against rs_s1 | open |
| clock taps | 125 types have a tap over 1,000 sinks; 25 types have stale sink bins; 0 tap sites in or within 4.32 um of an SRAM / ROM | bins stale |
| hold structure | 113 types flagged; 0 latch rows | open |
| congestion | sle_ctl one zone; coll_core 45.6 % hard-core area with 4 to 13 um channels | open |

## 1. Hops over 300 um

**Evidence (V, my scan of `internal_stations`, chain `from_um -> regs_um -> to_um`, Manhattan; PRECHECK R1 agrees: 100 types FLAG, worst 678.2 um).**
- 1,295 rows: 1,091 `per_bit`, 168 bank, 36 exact. 412 rows on 99 types carry a hop over 300 um; 334,401 bit-hops.
- Position of the 1,030 long hops: 399 are the first hop of the chain, 353 middle, 278 last.

| family | bus | form | worst chain (um) | bits | types |
|---|---|---|---|---|---|
| cbf_q00, cbf_q00_s2, cbx_q10, cbn_q00 | bc_i00 / bc_i10 / bc_i30 | bank | 634 + 637; 614 + 611 | 517 | 10 |
| slw_fe_v2, sle_fe_v1 | arv, arm | per_bit | 549 + 275; 511 + 256 | 1 | 3 |
| slw_stm_v1 / v2 / v3 | flt_o | bank | 544 + 536 + 548 | 1 | 6 |
| fe (4 families) | ard, x_stm_p1_i | per_bit | 463 + 3 x 232 | 512 to 544 | 8 |
| fw (5 families) | cmd | per_bit | 456 + 2 x 228 | 116 | 10 |
| slw_su_c, sle_su_c | x_su_l0_i | per_bit | 451 + 3 x 225 | 452 | 3 |
| cbf_q01, cbn_q01 | nb_i12 | bank | 418, 415, 415, 411 | 515 | 5 |
| sle_ctl | b_hw_hc2_o and 12 others | per_bit | up to 369 | 16,589 total | 7 |

**Root cause.** Two classes. (a) The first register after the port or core pin is not at the port: the first hop carries the distance the later equal hops do not (fe, fw, su_c). (b) The chain has too few stations for its length (cb `bc_i` two hops of about 630 um; stm `flt_o`).

**Limit of this scan.** It is the nominal centroid chain. On `per_bit` rows the per-bit leg differs. On the st_a exact rows the nominal chain reads 268 / 255 um while the measured per-bit legs are up to 428.5 um (section 6).

## 2. First-rank seating

**Evidence.**
- V, PRECHECK BOUNDARY-REG: 102 types; worst slw_sc_v1 6,317 of 18,840 port bits on 18 ports, sle_sc_v2 6,123, sle_stm_v1 3,725, coll_ftc 2,796.
- V, `QC-HOLD-0030-INDELAY.md`: 106 of 131 variants have an input delay over 416.5 ps; the fw / fe / stm families sit at 84 to 88 % of the period. The first rank has 100 to 130 ps for its wire.
- R, QC-PLAN-R3 08:41: slw_fe_v1 with its 10 existing scalar registers seated: 744.6 -> 189.8, 707.5 -> 179.1, 731.3 -> 147.6 um, 0 cycles added. This is a private V0E attempt. It is not in A4: the A4 fe rows are the V0E rows.

**Root cause.** The plan gives the first rank a centroid, not a site at the port window. The placer then pulls it toward its fanout.

## 3. Density and congestion zones

### 3.1 sle_ctl (7 types, 12 instances)
**Evidence (V, `congestion-10.rpt` of the two kept kits; first 20,000 markers of each).**

| kit | overflow | H / V | share in x 300 to 600 | top zones (x, y: overflow) | zero-capacity markers |
|---|---|---|---|---|---|
| cl372cea1c, intel1 | 43,104 | 22,652 / 20,452 | 79 % | 400,300: 15,293; 400,400: 13,139; 600,300: 8,786 | 5.8 % |
| cla4f6f12f, epyc10 | 40,250 | 21,923 / 18,327 | 72 % | 400,300: 13,924; 600,300: 11,237; 400,400: 9,694 | 5.8 % |

Net owners in the x 300 to 600 markers, both kits: `u_ist_b_hw_hc*_o` 43 %, flat core nets 31 to 32 %, `u_ist_b_tw_data_st_a_o` 16 %, `u_ft_cws*_o` 7 %, `u_ist_x_fw_o` 2 %.

Plan geometry of sle_ctl__cl372cea1c (V), outline 1226.88 x 1339.2:
- `u_tap` box x 164 to 467, y 328 to 458. `u_ctl` box x 475 to 821, y 337 to 596. The channel between them is 8 um.
- The four `b_hw_hc*_o` chains (1,574 bits each) start at (219, 328), (440, 400), (307, 328) and (216, 328): 6,296 bits leave `u_tap` from its south-west edge and its east corner.
- `b_tw_data_i` (2,103 bits) ends at (475, 337), the south-west corner of `u_ctl`. `b_tw_data_st_a_o` (1,081 bits) runs from (660, 200) west to the W face at y 371, under `u_tap`.
- FT `cws1` (516 bits, N -> S) leaves in window x 367 to 457, the `u_tap` column. FT `cws2` leaves in x 618 to 707, the `u_ctl` column.
- My demand estimate from the station rows alone puts the peak in the 100 um bins (400, 200), (300, 200), (200, 300), (300, 300). It matches the measured zones.

**Root cause.** Two hub cores side by side with 8 um between them, and about 10,100 bus bits that start, end or pass at their shared corner. The zero-capacity markers are in the same bins. Iterations cannot remove this.

### 3.2 coll_core
**Evidence.**
- V, plan: 29 hard cores cover 45.6 % of the outline. Channels: `g_xf_0` to `g_xf_1` 4 um, `g_xf_1` to `g_xf_2` 13 um, `rring` SRAM top (y 1101) to `g_xf` bottom (y 1106) 5 um.
- V, plan: stations `rec_tx_s0` (548 bits) and `io_collective__out_data` (512 bits) run north at x 262 to 275 from y 1041 / 1169 to y 1351 / 1473, across the `g_xf_1` box (x 203 to 393, y 1106 to 1318).
- R, GRT-TRIAGE: zones 300,1100 / 400,1100 / 300,1200 / 200,1000; overflow 30,528 and 33,196 at iteration 20; both jobs ended at TT -701.6 and -575.8.
- R, OPUS-FIX-QC-COLLCORE 09:10: pkw4 (read register) still has -479 on 392 ends `rdq -> out_data`.

**Root cause.** Timing first (single-cycle SRAM read and its 140 to 493 um legs), then a wall of abutted cores under two wide north-bound buses. I did not open a coll_core congestion report: both containers are gone.

## 4. Clock taps

**Evidence (V).**
- PRECHECK R3: 125 types have a tap over the 1,000-sink cap on bins + planned row registers. Worst: sle_ctl__cla4f6f12f 5,130 on one tap (28 taps over), slw_su_l1 4,061 and 4,001, sle_ctl__cl67434795 3,709, slw_fw_v1__cl51d45468 3,650.
- STALE-BINS, 25 types: kits saw more clock sinks than the plan bins hold. slw_su_l1 3.12x, slw_fe_v2 1.75x, slw_stm_v1 1.72x, sle_ctl 1.69x (106,822 against 63,131), sle_su_l0 1.63x.
- TAP-CAP after the 200 um rebalance: cbn_q11__cl5cc92dfe 1 tap, coll_ft__cla4a25d77 6 of 9 taps.
- My scan: 14,554 clock / reset tap sites, 0 inside an SRAM or ROM box, 0 within 4.32 um. (The N46T draft had 14.)
- R, QC-PLAN-R3 07:46: V1A "coherent native-plus-row bins and retap" draft, 127 types, 0 errors. Not in A4.

**Root cause.** Density taps are computed from bins measured before the station rows and landing rings were added. The sle_ctl family is the worst case and is also the congested one.

## 5. Hold structure at 833 ps

**Evidence.**
- V, PRECHECK R2: 113 types FLAG. 2,941 of 3,141 zero-logic station hops have launch and capture on different nearest taps and no latch. Worst: sle_su_l1 101 of 116 per type, sle_su_l0 88 and 82 of 96, slw_su_l1 85 and 80 of 113, slw_su_l0 82 and 80 of 92.
- V, plan: no `internal_stations` row carries a latch or lockup key. `clock.tap_window.per_type_ps` runs 20 to 190 ps, median 70.
- V, `QC-HOLD-0030.md`: 27 kits failed sign-off on internal FF hold of -1.4 to -41 ps on 1 to 308 ends. Class C names the ends: zero-logic `u_lpad_*.r[] -> r[]`, `u_ist` pad chains and `xl` write-data chains.
- R2 is an upper bound: hops inside 5 unshared clock stages also pass, and that needs the built tree.

**Root cause.** Station hops are 225 to 300 um and the tap radius is 200 um, so consecutive banks are on different taps by construction. With no logic between them the hold margin is the tap-to-tap skew. Buffers repair it after GRT and the routed RC moves it back.

## 6. E3 rs_s1 FIRM conflict

**Evidence (V).**
- My scan of exact `bit_sites_um` (cell 1.404 x 0.27 um) on every type: rs_s0 stage 0 against rs_s1 stage 0 collide on all 11 st_a types. sle / slw st_a_v2 (5 types, 6 instances): 51 each. sle_st_a_v1: 65, 65, 63. slw_st_a_v1: 77, 77, 77. The other exact rows (su_c, x_ctl_o) have 0. No exact site lies in a hard-core box or halo.
- The nominal `regs_um` of both rows lie inside the `u_r1` box on all 11 types (22 rows).
- `s1_reseat_405.json` for E3: 51 sites moved by at most 29.4 um, overlap 51 -> 0. Legs of the moved bits after the reseat: input median 270.9, max 391.1 um; output median 311.0, max 405.0 um. 24 of the 51 go to `u_r3`, 24 to `u_r2`, 3 to `u_r1`. The script is named `reseat_405.py`; its review says the two-leg form "fits the original 405 um data price".
- Plan: landing rings at y 69; `u_r0` to `u_r3` stacked to y 1240. Ring to core box: `u_r1` 337 to 404 um, `u_r2` 683 to 741 um, `u_r3` 1,020 to 1,069 um, with one station stage. The lane measured 777.6 to 794.2 um from bin sites to the `u_r3` pins.
- R, QC-SUST-MACRO 09:09: the E3 place stopped rc 2 at GPL on the collision. The halo PDN passed (8,044 pin and 10,563 rail checks).

**Root cause.** One packed bank per bus serves four consumers at 15 to 1,069 um. Each bit sits at the midpoint of its own leg, so the two banks crowd the same rows beside `u_r1` and `u_r2`. One stage cannot carry 794 um under 300 um legs: it needs three legs.

**I.** The other 10 st_a types will stop at GPL the same way when they reach place on A4.

## 7. Fixes for V1, ranked (P). Owner of the event: QC-PLAN-R4

| # | fix | evidence | owner | check |
|---|---|---|---|---|
| 1 | st_a rs_s0 / rs_s1 on all 11 types: two station stages (+1 cycle, pre-approved), every leg at or under 300 um, banks generated disjoint. Stage 1 beside `u_r1`, stage 2 beside `u_r2`; `u_r0` / `u_r1` take the pad cycle. Run the cross-bank overlap test on every exact row in compose. | section 6 | QC-SUST-MACRO-1119 (rows), QC-PLAN-R4 (compose, latency) | overlap 0 on 11 types; max per-bit leg <= 300; one st_a_v1 and one st_a_v2 place-only |
| 2 | sle_ctl hub, all 7 types: move `u_ctl` east to open a channel of at least 60 um beside `u_tap` (move only, no re-shape, no outline change); put the stage-0 banks of the four `b_hw_hc*_o` chains on four different sides of `u_tap`; take `b_tw_data_st_a_o` south of y 328; move the `cws1` FT window off the `u_tap` column. | section 3.1 | QC-PLAN-R4; FABLE lead if a hub split is wanted | my station-demand estimate before build; then one kit: overflow under 1,000 by iteration 10 |
| 3 | Sink bins from the newest placed kit for the 25 STALE-BINS types, then retap; take the V1A retap draft. sle_ctl first, with fix 2. | section 4 | QC-PLAN-R4, PRECHECK-1119 | R3: no tap over 1,000 on bins + rows; STALE-BINS 0 |
| 4 | First rank seated FIRM at the port window on the fe, fw, su_c, sc and stm families (the slw_fe_v1 form), then re-scan; stage rows only for legs still over 300 um. | sections 1, 2 | QC-PLAN-R4, LONG-LEG-0040 | BOUNDARY-REG bits fall; first-hop count of 399 falls |
| 5 | cb `bc_i00 / bc_i10 / bc_i30` (10 types, 517 bits): two more stations per chain (+2 cycles), or move the ring to the core side. stm `flt_o` (1 bit): one more station. | section 1 | QC-PLAN-R4 | R1 worst under 300 on cb |
| 6 | Lockup latch at the launch side of zero-logic station chains, su_l0 / su_l1 first (80 to 101 hops per type), then lpad / ist pad chains named in QC-HOLD-0030 class C. Where two banks fit one tap radius, share the tap instead. | section 5 | QC-PLAN-R4 (rows), QC-HOLD-0030 (ends list) | R2 unlatched count; first su kit CTS FF hold on those ends >= 0 without buffers |
| 7 | Global 300: `die.reach_um`, `reset.hop_um`, `ft_station_max_um` to 300 with the priced BOOT 1492. | section 0 table; R QC-PLAN-R3 08:41 | QC-PLAN-R4 | G0 0; LATCHECK 1921 |
| 8 | coll_core: no row in V1 unless the R4-bound successor of pkw4 / pkw5 reads the `rdq -> out_data` class at or above -42 at GRT TT. Then open the `g_xf_0 / 1 / 2` channels for the two north buses. | section 3.2 | OPUS-FIX-QC-COLLCORE | class read, not WNS |

Order of proof (owner: reps first): one st_a_v2, one sle_ctl, one su_l1 and one fe kit on the V1 draft to GRT TT before the cut.

## 8. Stop list

- No reading of A4 as a 300 um event. Only the reset trees are at 300.
- No relaunch of an st_a kit that stopped at GPL on the rs_s0 / rs_s1 collision with unchanged rows.
- No hand reseat of the other 10 st_a types in the 405 form (legs 391 / 405 um) as the V1 form.
- No new sle_ctl kit on the A4 geometry run to 30 GRT iterations. Read overflow at iteration 10; the zone is known. The two kept jobs stay as admitted.
- No coll_core wave kit before the read-register class passes on an R4 bind.
- No retap from the current bins on the 25 STALE-BINS types.
- No station row before the first rank is seated and re-scanned (09:05 list).
- No hold-buffer ECO on a zero-logic cross-tap chain (09:05 list).
- No E3 result read as family proof: it is one type of 11, and the halo and the reseat are separate changes.

## 9. Not checked

- Die-level lane hops between partitions (ports, FT stations): G0 passes at the 405 die reach; I did not re-scan them at 300.
- Per-bit legs of the 1,091 `per_bit` rows; only nominal chains and the 51 E3 bits.
- No placed A4 kit exists yet (E0 ctl place is running, R). Nothing here is a placed or routed A4 measurement; the congestion reports are V0E-geometry kits.
- Hold is static structure only; no STA. R2 is an upper bound.
- Routing blockage layers of `u_tap`, `u_ctl` and `ot_coll_fold_slice` (plan `obs_max` is empty); the 60 um channel in fix 2 is a first estimate, not a track count.
- Whether the four st_a_v2 types held by exact key launch on A4.
- Marker lists are capped at 20,000 per report, so zone shares are of the listed markers.
- Token, ROM content, LEC and procedural items are out of scope.
