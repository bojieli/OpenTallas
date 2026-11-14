# FABLE-REVIEW-COL (Fable) 2026-11-14 05:4x PST - S81 ROM column family (col_h9 / col_h10, r0 r1 r2)

Scope: 216 partition types in plan B3w (col_h9_r0_p1..p6 60, col_h9_r1 60, col_h9_r2 60, col_h10_r0_p1/p4 12, col_h10_r1 12, col_h10_r2 12).
Work dir: epyc7 /srv/opentallas-scratch2/claude/fable-review-col (scripts, dumps, proof runs p_*). Renders: same dir png/ and intel2 ~/fable-review-col/png/.
Evidence DBs (wave 7073a6b4a59, B3v plan): col_h9_r1 pv47efee8f 4_cts, col_h9_r2 4_cts (TYPE-COLH9R2 copy), col_h9_r0_p2 pvd86cb19a 4_cts, col_h10_r2 pv7a8a5452 3_place, col_h10_r0_p1 3_place.

## 0. Answer in five lines
1. The col_h9_r1 GRT failure is NOT the ROM/s orientation. It is 126 relay nets (y_rt_20a_5 / y_rt_20b_sk -> node n20.a/.b) that cross the bf wall (col3_c, zero M6 capacity) plus 304 buffers placed in the 8.6-um dead-end slot between the two bf16_half macros. Proof: B3w flips alone leave overflow 27,162; flips + slot blockage + those 304 buffers moved to the top strip give overflow 0.
2. The relay bunching behind it is family-wide and has one cause: OT_RELAY_MID_RE does not match the bound-wrapper names of the region relays, so about 12,500 of 18,000 relay flops per type are never station-placed.
3. B3w: adopt as-is (harmless, proven routable), but it fixes neither r1 nor anything that was failing GRT. The 168 mixed groups need no plan change.
4. Outline: keep. Standard cells are 0.8-1.3 percent of the outline, so fill 0.011 is intrinsic; r2r 1180 is the relay bunching of point 2.
5. The 216 types are not pin variants. Pins are identical inside every partition; "pv" is the per-instance ROM image parameter. 216 builds collapse to 95 with no plan change and to about 16 with one clock-landing unification.

## 1. Geometry (what the renders show)
- Dataflow per element N: 7 ROMs c{N}_0..6 (38.04 x 62.95) -> s{N} (cfg7_seq 17.28 x 51.84) -> bs{N} (qbank_S) -> element halves e{N}.u_w + u_e (2 x 268.4 x 221.4, abutted) -> bn{N} (qbank_N) -> relay regs -> node tree (dsfd_node_* 43.2 x 77.8, east side). The bf element is a wall: bf16_half x2 | col3_c | gap | front_roots | gap | col3_c | bf16_half x2, 1124 x 199 um.
- ROM pins are on BOTH faces: local-W = addr 12 + ce + clk + 29 rd_out, local-E = 43 rd_out. cfg7_seq uses 48 rd bits (29 W + 19 E), cfg7_seq_bfp all 72. No orientation puts all ROM pins toward s: 19 (or 43) bits per ROM always leave the far face. s has 356 of 373 pins (q0..q6, a, ce) on local-W.
- r0 template: ROM rows in the bands between element rows, s in the row. r1/r2 template: element pairs pushed apart, ROM stacks 2 wide x 4 high in a 310-um central corridor (channels 25 / 22.4 / 65 um), s at the stack corner. B3v had s pin faces pointing away from the east stacks (630 of 2303 ROM-s pin pairs with neither face toward the partner in r1/r2; r0 423).
- Frame buses enter only at x 6..330 on N/S (1167 + 321 bits, M7/M5). r0 also carries the 1104-bit xo crossing E->W at y 740..980.
- Density: col_h9_r1 movable std-cell area 13,229 um2 = 0.76 percent of the core; macros 47 percent (43-55 across the family); only 13-30 percent of 8-um bins hold any cell.
- Every type has dead-end slots between hard cores: the 8.6 x 242 um ha|hb gap, twice per bf wall (4 in col_h10_r1), plus 8.1 x 221 e|w gaps in col_h10_r0 and one 8.6 x 78 ha|n16 gap in col_h10_r1.

Renders (PNG):
- col_h9_r1_B3v.png: r1 as built, ROM-s pin pairs coloured by facing, 81 nets across col3_c, slot with 304 cells.
- col_h9_r0_p2_B3v.png: r0 as built (ROM rows, s mid-row).
- col_h10_r2_B3v.png: col_h10 r2 as built (same geometry as col_h9_r2).
- col_h10_r1_B3w_plan.png: B3w plan, pin faces after the flips, the lone east ROMs (red boxes), slots to block.
- col_h9_r1_B3w_plan_rules.png: B3w plan with the slot blockages and the relay polyline of rule R-COL-4.
- col_h9_r1_grt_proof.png: congested gcells of the flips-only GRT run.

## 2. Structural causes
C1 (r1 blocker, 95 percent of the overflow). Node n20 (LLfu, 1270..1313 x 985..1063, a/b pins on its E face) is fed by relay chains y_rt_20a_0..5 and y_rt_20b_*. All stages sit bunched at x 640..690, y 1070..1160 (the channel between front_roots and the east col3_c). The last hop is 772 / 735 um median and its straight line crosses the east bf wall. col3_c blocks M2-M5 and leaves zero-capacity M6 gcells; the placer/repair put 304 buffers of these nets into the ha|hb slot, reachable only across col3_c. 126 nets x 209 um of zero-capacity gcells = the 25.6k M6 overflow.
C2 (family-wide, the reason for C1 and for r2r 1180). kit config OT_RELAY_MID_RE = ^(.*[.]u_y_[A-Za-z0-9_]+)[.] needs ".u_y_". Region relays are named u_bound.u_u_y_rt_10a_0.u.o[..] (r1/r2) or u_bound.u_u_r0_u_y_xo0_0.o[..] (r0): "_u_y_", no match. In col_h9_r1 18,053 relay flops exist, 5,558 match (lpl children only); log line "OT_RELAY_MID placed 1293 relay flops of 8 stations (19 relay groups)". With the group regex corrected the placed DBs show, per type, relay hops with median > 405 um: r1 49 bundles / 7,986 connections, r0 51 / 8,385 (xo chain hops 1,170-1,330 um), col_h10_r2 19 / 3,650. The stages exist (cycles are already paid); they are just not sited.
C3 (hygiene, not a GRT blocker). r1/r2 reused r0 orientations after the ROMs moved east of s. B3w corrects it. On col_h10_r2 (= col_h9_r2 geometry) GRT at placement gives overflow 0 with B3v orientations and 0 with B3w flips (wirelength 7.387 -> 7.359 M um). The r2 GRT-0183 on net122658 did not reproduce in either run; it appears only after GRT repair_design put a buffer against the ROM edge, and B3w moves that pin to the other face.
C4 (not a defect). Mixed groups: one ROM behind the s pin face (bf row c8_6 / c13_6 / c15_6 in every r1/r2 type; c7_6, c9_6 in col_h10_r1). The nets wrap a 17-um macro in open band space. r0 has 20 ROMs behind s per type (s sits mid-row) and nobody routes worse for it.
C5 (outline). Whitespace is 52 percent, of which 42 points are the three bands between element rows (150-184 um x full width) that hold only s / bs / bn / stations. Band contents are 95-121 um tall, so trimming bands gains about 100 um of 1227 (8 percent); a real cut (ROM stacks into bands, corridor removed, width 1443 -> about 1160, -20 percent) is a re-floor of all 216 types and of the S81 frame pitch. Neither changes closure.

## 3. Rule set (R-COL)
R-COL-1 ORIENT (= B3w, adopt as-is). Per ROM group u_c{N}_* vs u_s{N}: ROM east of s -> R0, west -> MY; s -> MY (R180 if MX) only when all its ROMs are east. Keep every ROM face on a channel >= 20 um (present: 22.4 / 25 / 65). No extra move for mixed groups.
R-COL-2 SLOT (plan, all 216 types, with the next bind). Hard placement blockage over every gap < 12 um between two hard cores with > 50 um overlap, full gap rectangle. Routing stays open (bf16_half ha.clk enters from the slot at its mid-length, 121 um from the mouth; its tap leg routes in, no cell inside). Rectangles (um, x0 y0 x1 y1):
 - col_h9_r1, col_h9_r2, col_h10_r2: [17.39 1054.09 259.31 1062.73], [899.56 1054.09 1141.48 1062.73]
 - col_h10_r1: ha|hb gaps at y 1140 and y 147, x 17..259 and 899..1141 (4), plus ha|n16 8.6 x 78 at x 1140 y 52
 - col_h9_r0_p1..p6: ha|hb at x 86 and x 968, y 1089 (2)
 - col_h10_r0_p1/p4: ha|hb at x 86 and x 968, y 657 (2); e|w 8.1 x 221 at x 579 (y 216 and y 950/1002)
 Generator: fable-review-col/planstat.py prints them from the plan for every family.
R-COL-3 RELAY SITING (kit / FLOW, one line + one switch). OT_RELAY_MID_RE = ^(.*[._]u_y_[A-Za-z0-9_]+)[.] (group = u_bound.u_u_y_rt_10a_0; lpl children unchanged) and OT_RELAY_MID_FIT=1 for the col family. Acceptance: OT_RELAY_MID log reports all relay groups (about 18k flops in r1), and no relay hop median > 405 um at 3_place (fable-review-col/relay2.py <dump> 405 20).
R-COL-4 WALL (plan internal_stations, r1 first). The bf wall rows and any hard core > 100 um wide are no-cross obstacles for relay lines. Chains whose straight source-sink line crosses one get plan internal_stations with regs_um on a channel polyline, hops <= 405 um. col_h9_r1: chains y_rt_20a_* and y_rt_20b_* -> u_n20.a/.b: polyline (663,1120) -> (663,1190) -> (1335,1190) -> (1335,1024), stages spread evenly (top strip y 1158..1227, then the 43-um gap between n20 and n18). Same pattern for the lpl_2_r / lpl_3_r -> n22 and n19.o -> lpl_5_w bundles (525-708 um today). relay_mid FIT may already satisfy this once R-COL-3 lands; the plan entry is the fallback if FIT picks the straight line.
R-COL-5 OUTLINE / DENSITY (whole family, r0 included). Keep the outlines. For macro columns judge density by (a) no cell in a slot (R-COL-2), (b) relay hops <= 405 um (R-COL-3), (c) macro area / outline >= 0.43; fill / empty of std cells stay advisory (fill cannot exceed about 0.02 here). Do not open a compaction event for closure; if area matters later, do it once for all families with the next die re-floor (width 1443 -> about 1160 by moving ROM stacks into the bands).
R-COL-6 VARIANTS. Build per kit identity, not per pv (section 5).

## 4. Proof (GRT only, ot-run on epyc7, plain global_route on the wave DBs, same routing layers M2-M7; flips done in place, no re-placement)
| run | DB | change | extra iterations | overflow total (M6) |
| wave baseline (TYPE-COLH9R1) | col_h9_r1 pv47efee8f 4_cts | none | 30 | 26,909 (25,574) |
| p_r1_flip | same | B3w flips: 29 ROM + 2 s | 8 | 27,162 (25,729) |
| p_r1_fix | same | flips + 2 slot blockages + 304 slot buffers moved to y 1165+ and legalised | 26 | 0 |
| p_h10r2_base | col_h10_r2 pv7a8a5452 3_place | none | 12 | 0 |
| p_h10r2_flip | same | B3w flips: 29 ROM + 2 s | 17 | 0 |
Limits of the proof: GRT congestion only, no repair_design, no timing, no detail route; p_r1_fix moved only the slot buffers (the y_rt flops stayed bunched), so the full R-COL-3 effect is not yet measured; col_h10_r1 has no placed DB yet, so its lone east ROMs (c7_6, c9_6) are judged from geometry. No col type has reached GRT pass in the wave on epyc7 yet (r0 kits are at CTS), so "r0 passes" is unproven too.

## 5. Why 216 types, and the collapse (for the owner)
- Pins: the plan `buses` field has exactly 1 distinct value inside each of the 12 partitions. There are no pin variants.
- "pv" is a parameter variant: 35-42 strings per type, P_u_c5_0_INSTANCE="u_f_0R13.u_r1.u_c5_0" etc., that select the ROM image of that die instance (DIE-QC-97 param class). Every die instance has a different image, so the split made one type per instance (60 instances -> 60 types).
- The ROM is a hard macro with one LEF and one lib for all images. Measured: pv47efee8f and pv637e5d47 of col_h9_r1 have byte-identical 1_2_yosys.v, io.tcl, macro_place.tcl, constraint.sdc and pins.json (module name normalised). Of 58 col kits built on epyc7, 25 are distinct (col_h9_r1 21 -> 4, col_h9_r2 19 -> 7).
- Plan fields: ignoring param_set, 216 -> 95 classes; the only remaining difference is clock (landing_contract pins on the clock-landing instances and 2 of 13 added_taps). Ignoring clock as well, 216 -> 16 geometries. col_h9_r1 is 54 identical + 6 clock-landing instances; col_h9_r2 60 -> 18; col_h10_r1 12 -> 2; col_h9_r0_p6 12 -> 1; col_h9_r0_p1..p5 stay 1 per instance because every r0 instance has its own landing contract.
- Step A, now, no plan change: key the wave build on kit identity (hash of normalised netlist + io.tcl + macro_place.tcl + SDC + clock taps); one build per identity, its R-MINIMAL record credited to every member; param_set recorded as the ROM-image binding (image goes in at ROM generation / GDS merge; LEC and token proof stay per image). 216 -> about 95 builds. Latency 0, area 0.
- Step B, with the next S81 plan event: one clock landing per partition (same 13-15 added_taps in every instance, landing-contract pins present everywhere and tied off where unused). 95 -> about 16 builds. Cost: at most 2 extra clock taps and about 4 unused M7 pins per instance, no data latency. Needs DIE-S81-92 and the CLAND owner to confirm the tied-off pins are legal for bind.
- Speed: a col build is GRT 0.3-1.8 h plus GRT repair_design 5.7-6 h (TYPE-COLH9R2) before detail route, about 40 GB. Every structural fix (this review has three) is re-run on every build. 216 builds per round against 95 or 16: the collapse is faster by 2.3x after step A and about 13x after step B, and step A is a wave bookkeeping change of hours.
- Not analysed: merging r0_p1..p6 into fewer partitions (they differ in outline height 1279 / 1236 and core lists). Not needed once A and B land.

## 6. What DIE-S81-92 should do now
1. Finish and adopt B3w as-is. Do not expect col_h9_r1 to pass on it; tell TYPE-COLH9R1 the M8/M9 forms fa-fd treat a symptom.
2. B3x, one event for all 216 types: R-COL-2 slot blockages + R-COL-4 internal_stations for the wall-crossing chains (r1 n20 / n22 first).
3. Ask KIT-OPS-3 / FLOW for R-COL-3 (regex + FIT) and canary it on col_h9_r1 pv47efee8f and one r0 (xo chain); gate = relay2.py shows no hop > 405 um.
4. Ask KIT-OPS-3 / wave for step A dedup before relaunching the column wave; raise step B with the CLAND owner.
5. Leave outlines and mixed groups alone.
