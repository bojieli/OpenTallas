# DIEVIEW-S81-1113: S81 die-level visual layout review (read-only)

Stamp: 2026-11-13 06:08 PST. Lane DIEVIEW-S81 (Fable), for COORD. No plan, kit or queue row was changed.
Plan reviewed: plan of record of the S81 wave, `kit_wave.json dies.s81` event 7073a6b4a59, epyc7/epyc9 `/srv/opentallas-scratch2/claude/kw45/src_s81_main_7073a6b4a5/physical/die_plan/s81/plan_h2_2249.json`, sha256 18c864518844 (ready12b-A). 398 partitions, 395 plan types, 205 kit items, die 31.95 x 25.44 mm = 812.7 mm2.

## 0. What I viewed

No current S81 die-level render existed (DIE-PROTO-2 rendered only KV and HEAD; the only S81 die drawing was HFP-S81-1 of 11-12, now withdrawn). I rendered the plan myself (ot-run on epyc7, matplotlib from the plan JSON, script `epyc7:/srv/opentallas-scratch2/claude/dieview-s81/code/render_die.py`). Copies are committed in `lanes/dieview-s81-1113/`:

| image | content |
|---|---|
| `s81_die_floorplan.png` (+ `_SHORE_S`) | partitions by family, every hard core, IO windows, channels, clock root |
| `s81_die_dataflow_ports.png` | all 2,330 ports as arrows across their face windows |
| `s81_die_lanes_e2e.png` | all 873 lanes, first source to last sink |
| `s81_die_thru_fill.png` | relayed (feed-through) bits and hard-core fill per partition |
| `s81_die_clock_tree.png`, `s81_die_clock_reset.png` | die clock H-tree i30padtb (intel1 `s88/dc_i30padtb/tree.json`, built on ready11r positions, the adopted tree), die taps per partition, forwarded-clock edges, reset parent tree and depth |
| `s81_die_status.png` | sign-off state and latest physical failure class per partition |

Also viewed: `lanes/hfp-s81-1112/hfp_s81_1v2.png`. Type renders viewed (all event 7073a6b4a59 unless noted; copies of the auto_geom images in `lanes/dieview-s81-1113/types/`):
- leaf t40__clf8bbdae1: epyc8 `kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/ot_s81sl_leaf__t40__clf8bbdae1/geom/auto_geom.png` and `.../gen/.../run/layout_review/grt/congestion.png`
- leaf t53__clb66fa5cb (epyc8), t41 a3, t28 a3 (epyc9), same tree, `geom/auto_geom.png`
- dsdv_slice_c1x_C__t3 a1 (epyc8) `geom/auto_geom.png`; dsdv_slice_iq_C__t1 a25 (epyc8) `layout_review/place/density.png`
- serdes__t2 a27 (epyc9, event e9eda32d41c) `geom/auto_geom.png`; serdes__t13 a27 (epyc9) `layout_review/place/density.png`
- frame col_h10_r2__t1__cl1f5d6c2a: epyc9 `vislayout2-s81/b/h10/.../run/layout_review/grt/congestion.png` (11-12 form b/h10)

NOT viewed (renders pruned by cleanup; I used the GEOM-VIS-1 verdict text of 11-12 instead): bk_sel__t2, iqf__t1, the other col_h items, slice_station__t52. No render exists for the svc types (they stop at gen_lint), gunit__t1 (stops at gen) and dsdv_slice_kv512_C__t1 a35.

No S81 die GRT exists on this plan (die-recheck runs the ESTIMATE on ready11r; DIE-PROTO-2 step 4 never ran). So die-level congestion below is judged from port and relay loads, not from a route.

## 1. The die in one paragraph

Three regions on one rigid 1442.88 x 1226.88 lattice: two frame wings (216 tiles, 382 mm2, 47% of the die), a centre of leaves and slices (75 leaf + 5 kv_leaf + 16 slice C + 4 LP), and the svc block (16 tall tiles, 65 mm2) on the HBM PHY at the south shore. Two station columns (x 8.8-10.2 and 21.7-23.2 mm) plus inner station tiles separate them (46 tiles, 81 mm2, 2% core fill). 14 SerDes double tiles sit on the N and S edges. The data flow is sound and matches the owner's hand-floorplan intent in its main lines: frame chains run vertically inside a wing column, every leaf column feeds a slice row, the svc ring sits on the PHY. The sign-off problem is not at die level. It is inside four tile templates that are each copied 16 to 216 times, and one of them (frames) has no owner today.

Sign-off state on the picture (`s81_die_status.png`): 20 of 398 partitions are signed off, all slice stations. 0 of 216 frame tiles, 0 of 80 leaves, 0 of 20 slices, 0 of 16 svc, 0 of 14 SerDes.

## 2. Findings, ranked by sign-off impact

### F1. Frame family col_h9/col_h10: 216 partitions, 26 kit items, 0 signed off, no owner (HIGHEST)
- Seen: every frame tile is red (latest physical class GRT overflow) on the status map. In the b/h10 congestion render the four ROM-pair bands fill the west 80% of the tile; rows of 8 to 17 small cores sit INSIDE the 70-um streets between the bands, leaving 5-20 um slivers; the hot knot is the W-centre crossing (x 270-530, y 430-640) where the S D-pin group lands under a band; the east 20% of the tile holds 8 small blocks and nothing else. GEOM-VIS-1/2 described the same form on five more col_h items (BAD / ISSUES).
- State: 337 FAIL events on 26 items, 26 GRT-overflow records 11-08..11-11, none since. The family is still on event e9eda32d41c, is route-held for the porous-view DRT-0073 class since 11-10, and no lane posted on col_h on 11-13.
- Fix (one template, 26 items): move the small-core rows out of the band streets into the empty east strip as one column block with its pins facing a >= 43.2 um street; that turns each band street into a clear ~70-200 um channel. Land the S D-pin group at the street centre. Split the taps that carry 3,000-4,400 sinks.
- Rulebook: R-STREET-1, R-STREET-2, R-STREET-4 (small cores are in a station alley); R-REACH tap cap; porous views to LEAF-DRT73-1 (same view set: dsfd_qbank_S/N).
- Owned: NO. VISLAYOUT2-S81 is gone and S81-FORMS-1's scope is leaf + dsdv. Recommend COORD opens FRAME-FORMS-1 now (or widens S81-FORMS-1) and puts the frame views into LEAF-DRT73-1's scope. This is 54% of the die's partitions.

### F2. Leaf family: 80 partitions, 80 kit items; one template defect set, four symptoms
- Seen on t40cl, t53cl, t41, t28: (a) the 27 hard cores are packed into the W/SW two thirds; the east 30-35% of every tile is empty (fill 0.9-4%, 94-95% empty). (b) The 16 lane ROMs (ot_dsrom_su_hcpost_lane_pr) stand as a double column 30-40 um from the W face with 8.64 um gaps, directly behind the W pin bar. (c) All std logic sits in a ~150-um pocket east of that column (x 280-450), where single taps carry 3,228 / 3,331 / 6,618 / 12,565 sinks while most of the ~40 grid taps carry under 100. (d) t28: big cores 30 um above the S pin bar (9,574 M5/M7 pins on its N and S faces). (e) The red clock line on every auto_geom: farthest sink 2.05-2.30 mm from its own clock driver, which is the core tap that does not sit at its core.
- Symptoms by structural.tsv record since 11-08: GRT overflow 74 (hot spots are the pocket and the SW pin corner, viewed on t40cl), DRT-0073 18 (ot_s81sl_vs u[235] on 11-10, lane ROM c0/c2 pins on 11-13), post-CTS hold stop at -334..-432 ps 11, routed-not-signed with setup -417..-494 ps 2.
- Die-level cause that the type lanes do not see (`s81_die_thru_fill.png`): leaves relay 230k bits and terminate 95k. The leaf next to each slice row (L1) relays 5-8k bits for the leaves stacked behind it (up to 4 deep), through a tile whose west third is a macro wall. s_3N_L0 (kv_leaf t2, a 3-tile slot with 16% core fill) relays 8.9k bits, the highest on the die.
- Fix: ONE leaf template, applied to all 80 items in one event: lane ROM column moved in from the W face with a >= 43.2 um pin street and a >= 43.2 um channel between its two columns (or abutted pin-to-pin, R-STREET-3); the big cores spread east into the empty third so the N-S transit lanes get a straight street (R-STREET-5, sized by the relayed bits: L1 tiles need the 8k-bit width, L4 tiles do not); core taps re-bound to their cores; grid taps re-seeded on the logic pockets after the re-pack, <= 800 sinks.
- Rulebook: R-STREET-2/3/5, R-CLOCK-5, R-REACH (tap cap). New sub-rule proposed, R-STREET-7 "transit streets are sized per slot position, from the die relay table" (the same type family has 1.3k to 8k relayed bits depending on its row).
- Owned: yes, in three lanes that must land as one event. S81-FORMS-1 (street + core-tap rebind), LEAF-DRT73-1 (lane ROM pin access), HOLD-TAP-1 (R-CLOCK-5 check). Gap: the tap re-seed (c) and the per-row transit width are in nobody's list; give both to S81-FORMS-1. Relaunching leaves before that event cannot pass (HOLD-TAP-1 said the same).

### F3. svc block: 16 partitions, 16 items, 242 FAIL events, never reached placement; the next wall
- Seen (`_SHORE_S`): each svc tile is 1443 x 2748/2851 um and 68-71% hard core: a wall-to-wall SRAM array with ~8 um gaps, one pin row in the middle and one 300-400 um logic strip at the top. All 16 items stop at gen_lint (a behavioural memory of 160 x 265 = 42,400 bits over the 16,384-bit synthesis limit, plus the tie-clock export form), on a kit_wave hold "SVC-RS FLAT 4M cells, REDESIGN split" from 11-08. The plan-route table already predicts route supply p99 5.4-7.8 against a limit of 1.5 on the ring streets.
- Fix: (1) the 42,400-bit staging memory becomes a generated macro (owner rule: memories are generated macros); (2) the svc tile is split per R-CAP-3 into array core(s) + a logic partition, the array hardened once and reused 16 times; (3) ring streets to R-STREET-1 width before the first place.
- Rulebook: R-CAP-3, R-STREET-1, R-RTL-3 (macro ports). 
- Owned: NO current owner (S81-SVCRS-1/2 and VL3-S81-SVCSTN are gone; DIE-S81-88 lists svc builds as stale). Recommend HARD-S81-SVC-1. The svc tiles also stretch the wing rows (F6).

### F4. dsdv slice C: 16 partitions, 16 items, 230 FAIL events
- Seen on c1x t3 and iq t1: five xf cores form an unbroken wall across x 465-1000 at mid height and cut the tile into a north and a south half; the cap core stands 35 um from the W face; pins on all four faces (14.5k); 1,224 unregistered ft0_i pins; 20,055 register-to-register captures over 405 um (max 1.79 mm); taps with 12,614 / 5,695 / 5,549 sinks. 650k std cells after repair against 330k at synthesis: the excess is repeaters on over-long paths.
- Fix: S81-FORMS-1's plan stands (harden u_xg.u_s xs4 as one core, hand re-layout of the 16 C rows). Add three things to that re-layout: break the xf wall (2 + 3 with a >= 43.2 um N-S street, or move it to a face it abuts), register ft0_i at the pin, and re-seed the taps. Without them the cell count stays inflated by reach repair even after the xs4 core is out.
- Rulebook: R-CAP-3, R-STREET-1/2, R-REACH. Owned: HARD-S81-DSDV-1 + S81-FORMS-1.

### F5. SerDes: 14 partitions, 11 items, 153 FAIL events
- Seen on t2 and t13: a 2886 x 1227 double tile, 94% empty. The PMA pair lies along the shore edge, the KP4 core and SRAMs sit 700-800 um away mid-tile, the lane port bar is on the far E/W face 1.5-2.5 mm away; logic is smeared along the diagonals of that triangle. One recovered-clock tap (io_pma_rck) drives 22,310 sinks, the farthest 3.5 mm from the driver; r2r max 2.5 mm. Die level: the 14 PHY windows have 5 different shapes (2246x323 to 2886x1227), which is why 14 instances need 11 types.
- Fix: HARD-S81-SERDES-1's repipeline (R-RTL) is necessary but not sufficient. Collapse the triangle: KP4 core + SRAMs directly under the PMA at the port-face end, port bar at that same end, rck domain confined to a region box next to the PMA with its own regional tap set. Then one layout template in W/E mirror for all 14 (one PHY window shape).
- Rulebook: R-RTL-1/3, R-REACH, R-CAP-2 (outline). Owned: HARD-S81-SERDES-1 (geometry part is not in its handoff; add it).

### F6. Die level: dead bands, station columns, far-placed control blocks (no sign-off blocker; next plan event)
- The two svc rows are 2851 and 2748 um tall against 2 x 1227 tile rows, so both wings carry white bands of 397 and 294 um (`s81_die_floorplan.png`, y 3.8 and 6.9 mm): about 14 mm2 unused, and 28 planned channel crossings (frame chains of up to 1,264 bits) run over them. The reset depth also jumps across the lower band (depth 0-3 below, 6-11 above, `s81_die_clock_reset.png`): check that the frame_int pairs across the band are in the reset-safe list.
- Station columns: 46 tiles, 81 mm2, 2% core fill, 161k relayed bits. COORD ruled they stay (11-12). I agree for this release: they are the only signed-off family and they carry the frame-to-slice fan-in (6 frame groups per wing converge on 2 slice rows; column tops carry 7.5k bits).
- Control blocks sit at the periphery, far from their partners: seqhost (centre-south) to bk_sel (N edge) 20 mm / 17 hops; svc_14 to bk_sel 24.8 mm / 17 hops; eng (S edge) to s_6N_C 19 mm; iqf (SW) to s_0N_LP 16.6 mm. Low width (276-604 bits), so no congestion, but 13-17 station hops each and they pass through the hottest relay tiles. Move bk_sel/gunit/eng/iqf/seqhost into the free and station cells next to the slice rows at the centre re-pack.
- HBM shore: the PHY (8.66 mm) sits under 6 of the 8 svc_lo columns; svc_0 and svc_14 reach it through neighbours (2 hops). Acceptable. SerDes are on the N/S edges only, PHY supply domains separate. No finding.
- Rulebook: new die-level section proposed, R-DIE-1 "regions own their row pitch; no tall family may stretch a neighbour region's rows" (HFP-S81-1 D1 kept, D3/D4 dropped). Owned: DIE-S81-88 centre re-pack (later event). Not before the 11-15 freeze ends.

### F7. Die clock and reset (advisory under the nominal gate)
- Clock (`s81_die_clock_tree.png`): the adopted H-tree is load-weighted and not mirror-symmetric on a mirror-symmetric die. Level-1 nodes sit at x 11.6 mm (W wing AND centre) and x 27.5 mm (E wing alone). The E-wing-to-centre seam therefore crosses the root cut (20,956 bits, 12 of the 15 residual pairs of the 06:07 run were there), the W-wing-to-centre seam crosses a level-3 cut. Insertion is 11.9-12.5 ns TT with 250k clock cells and 13.9 m of wire; pairs across the root cut share almost none of it. The gate is nominal by owner rule (METHODOLOGY 6.1), and the nominal score is 0/946 over, so this is not a blocker. It is the first place a real-view die STA will hurt.
- Fix at the next die clock run (it must be re-run anyway: the tree is on ready11r positions, the plan is ready12b-A): root at the centre, three level-1 branches W wing | centre | E wing, so both seams have the same common depth and the centre (leaf-slice, svc) stays under one branch. Then confirm on the die STA that DIE-PROTO-2 step 4 still owes.
- Taps: 20,555 die taps, 40-119 per tile, on a uniform grid; the kits show sinks concentrated on a few of them (F1, F2, F4). The grid is seeded before the cores are packed. Re-seed after each template re-pack.
- Reset: wavefront from the centre, depth up to 12, clean concentric picture; only the band jump of F6 to check.
- Rulebook: R-CLOCK (new R-CLOCK-6 "die spine branches follow the plan regions; taps are seeded after core packing"). Owned: DIE-S81-88 (clock run), DIE-PROTO-2 (STA). The re-seed has no owner.

## 3. The hardest types (>= 5 failed attempts, not signed off)

Source: `autopilot/log.txt` KIT-WAVE FAIL events per item, `autopilot/OWNERS.tsv` state, `autopilot/structural.tsv` since 11-08. 158 kit items qualify. Most of their FAIL events are staging (kit not self-contained, gen KeyError, stale topology, pruned sources, host/disk), which KIT-STAGE/KIT-OPS own; the layout causes are the rest.

| group (layout cause) | items | partitions | what I saw | fix | rulebook | owner |
|---|---|---|---|---|---|---|
| A. macro wall at a pin face + logic trapped in pockets + lane ROM pin access + core tap off its core | leaf 73, kv_leaf 5 | 80 | F2 | one leaf template event | R-STREET-2/3/5, R-CLOCK-5, R-REACH | S81-FORMS-1, LEAF-DRT73-1, HOLD-TAP-1; tap re-seed unowned |
| B. small cores inside band streets, empty east strip | col_h 26 | 216 | F1 | one frame template event | R-STREET-1/2/4, R-REACH | NONE |
| C. flat macro array, memory as flops, never placed | svc 16 | 16 | F3 | macro + split + streets | R-CAP-3, R-STREET-1 | NONE |
| D. over cell cap from reach repair, core wall across the tile | dsdv C 16 | 16 | F4 | xs4 core + C-row re-layout + break xf wall | R-CAP-3, R-STREET, R-REACH | HARD-S81-DSDV-1, S81-FORMS-1 |
| E. three anchors 1.5-2.5 mm apart in a 94%-empty double tile, one 22k-sink clock | serdes 11, seqhost 1 | 15 | F5 | repipeline + collapse the triangle + one template | R-RTL, R-REACH, R-CAP-2 | HARD-S81-SERDES-1 (geometry not yet in scope) |
| F. over-sized slot, pins under a macro wall or across the slot diagonal (verdict text only, not viewed) | bk_sel, iqf, gunit | 3 | GEOM-VIS-1 11-12 | shrink slot, pins to the logic side, move next to partners (F6) | R-CAP-2, R-STREET-2 | DIE-S81-88; no dedicated lane |
| G. station hold on port contract, GRT time cap | slice_station 3, dsdv LP 4 | 7 | not viewed; R-CLOCK proof t41 covers the form | hold build (R-CLOCK-1) at next kit | R-CLOCK-1/4 | HOLD-TAP-1 |

Full list by family (FAIL events per item):
- **leaf** (73 items, 750 FAIL events): leaf__t21 19, leaf__t27 18, leaf__t50 16, leaf__t40__clf8bbdae1 16, leaf__t72 15, leaf__t56 15, leaf__t4 15, leaf__t74 14, leaf__t40__cl86ea32b3 14, leaf__t3 14, leaf__t24__cl2456157b 14, leaf__t53__cl958451dd 13, leaf__t32 13, leaf__t29 13, leaf__t26 13, leaf__t17 13, leaf__t10 13, leaf__t61 12, leaf__t31 12, leaf__t23 12, leaf__t67 11, leaf__t42 11, leaf__t33 11, leaf__t25__cl55642d17 11, leaf__t25__cl431c660f 11, leaf__t15 11, leaf__t8 10, leaf__t73 10, leaf__t66 10, leaf__t60 10, leaf__t58 10, leaf__t54__cl706d9749 10, leaf__t53__clb66fa5cb 10, leaf__t43 10, leaf__t39 10, leaf__t37 10, leaf__t28 10, leaf__t22 10, leaf__t16 10, leaf__t14 10, leaf__t70 9, leaf__t68 9, leaf__t57 9, leaf__t54__cl501e5681 9, leaf__t52 9, leaf__t44__clf6cf8492 9, leaf__t24__cl81374cd8 9, leaf__t13 9, leaf__t12 9, leaf__t11 9, leaf__t1 9, leaf__t69 8, leaf__t65 8, leaf__t5 8, leaf__t47 8, leaf__t46 8, leaf__t45 8, leaf__t44__clf4ea6d4b 8, leaf__t41 8, leaf__t38 8, leaf__t36 8, leaf__t35 8, leaf__t2 8, leaf__t9 7, leaf__t75 7, leaf__t71 7, leaf__t6 7, leaf__t51 7, leaf__t34 7, leaf__t30 7, leaf__t62 6, leaf__t7 5, leaf__t40__cl86ea32b3__sid5S 5
- **frame col_h9/h10** (26 items, 337 FAIL events): col_h9_r0_p1__t1 20, col_h9_r0_p4__t1__clcb2fbfe8 18, col_h9_r0_p3__t1__cl0cd90c0e 18, col_h10_r0_p4__t1 18, col_h9_r0_p2__t1__cl0045af7b 16, col_h10_r0_p1__t1__cl574cc59d 16, col_h9_r1__t1__clf32cde8d 15, col_h9_r0_p6__t1 15, col_h10_r2__t1__cl99efd374 15, col_h10_r0_p1__t1__cl911743eb 15, col_h9_r0_p5__t1 14, col_h9_r0_p4__t1__cl8ef405e8 14, col_h10_r2__t1__cl8b686b3e 13, col_h9_r0_p3__t1__cl31d0dc4b 12, col_h9_r0_p2__t1__cl9f71e63d 12, col_h10_r2__t1__clac068e56 12, col_h10_r2__t1__cl1f5d6c2a 12, col_h10_r1__t1__cld01bb4ae 12, col_h9_r2__t1__clce45cab5 11, col_h9_r1__t1__cl49d7a23e 11, col_h9_r0_p3__t1__cl8ce97bcb 10, col_h10_r1__t1__cl95b37463 10, col_h9_r2__t1__clc9ad8f7e 8, col_h9_r2__t1__clb8d86cd5 7, col_h9_r2__t1__cl774acf45 7, col_h9_r2__t1__cl87f3ff59 6
- **svc** (16 items, 242 FAIL events): hi_pvso_entry__t1 21, hi_rs__t3 19, hi_pvso_entry__t2 18, hi_rs__t2 17, hi_rs__t1 17, lo_rs_w__t1 16, lo_rs__t3 16, lo_rs__t2 16, lo_rs__t5 15, lo_rs__t4 15, lo_rs__t1 15, hi_rs__t6 15, hi_rs__t4 14, hi_rs__t5 12, lo_rs__t6 11, lo_rs__t7 5
- **dsdv slice C** (16 items, 230 FAIL events): kv512_C__t1 34, iq_C__t1 24, c1x_C__t6 17, c1x_C__t8 16, lepw_mus_C__t1 15, lepe_mu_C__t1 14, c3x_C__t1 14, c1x_C__t7 14, lepw_mu_C__t1 12, lepe_nh_mus_C__t1 11, c1x_C__t1 11, c1x_C__t5 10, c1x_C__t3 10, c1x_C__t10 10, c1x_C__t9 9, c1x_C__t4 9
- **serdes** (11 items, 153 FAIL events): serdes__t15__cla2127225 17, serdes__t13 17, serdes__t4 16, serdes__t3 16, serdes__t16 16, serdes__t2 15, serdes__t12 15, serdes__t15__cla3d02796 13, serdes__t14 13, serdes__t1__clfe1f0815 8, serdes__t1__clb45db5be 7
- **kv_leaf** (5 items, 55 FAIL events): kv_leaf__t2 15, kv_leaf__t3 11, kv_leaf__t1 11, kv_leaf__t5 10, kv_leaf__t4 8
- **misc (bk_sel, gunit, iqf, seqhost)** (4 items, 49 FAIL events): gunit__t1 20, bk_sel__t2 17, iqf__t1 7, seqhost__t1 5
- **dsdv slice LP** (4 items, 22 FAIL events): lepw_mus_LP__t2 6, lepe_mu_LP__t2 6, lepw_mu_LP__t2 5, lepe_nh_mus_LP__t1 5
- **slice_station** (3 items, 21 FAIL events): slice_station__t52 9, slice_station__t51 6, slice_station__t24__cl64811a5d 6

## 4. What I would do first (COORD)

1. Name an owner for the frame template (F1) today. 216 tiles wait on one drawing, and the fix is the same move S81-FORMS-1 is making on leaves.
2. Name an owner for svc (F3). It has cost 242 failed launches without reaching placement.
3. Hold leaf relaunches until the single leaf event (street + lane ROM views + core-tap rebind + tap re-seed) is bound; the three lanes should post one joint READY.
4. Add the geometry items to HARD-S81-SERDES-1 and HARD-S81-DSDV-1 (F5, F4).
5. After the freeze (11-15 04:00): re-run the die clock on the current plan with region-following branches, and run the S81 die GRT/STA prototype that has never run on this plan.

## 5. Limits

- No die GRT or die STA exists for plan 18c864518844; congestion at die level is inferred from port density (max 8.0 bits/um on the svc attn faces) and relay load.
- The clock tree drawn is the adopted i30padtb tree on ready11r positions. I did not check that ready12b-A moved no tap.
- Per-item sign-off state is from OWNERS.tsv at 05:45; clone items (`__cl…`) not listed there were mapped to their base type.
- "Not owned" means: no lane in the brief's owner list covers it and no lane posted on it on 11-13 00:00-06:00.
- Sink counts per tap are from the kits' auto_geom labels on the viewed attempts only.
- Renders for frames other than col_h10_r2 b/h10, bk_sel, iqf and station t52 were already pruned; those rows rest on GEOM-VIS verdict text.
