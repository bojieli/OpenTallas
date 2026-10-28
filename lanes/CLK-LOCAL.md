# CLK-LOCAL lane (CLK-LOCAL-EST-1: local clock form estimate on all 5 dies, estimate-only, no builds)

Owner question: "can variation be reduced by locality of the clock tree? 5-7 ns of unshared clock is almost certainly caused by a
non-local clock tree." Release form per 12.16e (coord 6f4412474): LOCAL. This file feeds each die owner's plan event.

## Method (shared by all dies)
- CURRENT = each die's CA-OCV-1 gate inputs: same proof/plan/bind and the same die_sta_related model (claude/ca-ocv-1-1028@07833e2f9:
  spice x1.0485/x1.0552, region key, cppr-lca, clock_variation table g021 0.21 %/mm, shared droop, core lat 250/202.5).
  Script cur.py reproduces the CA-OCV-1 numbers exactly on KV and QC (CHECKED). From it I take, per crossing: the last common tree node,
  the launch and capture unshared branch, OCV lo/hi, and gate margins. topo.py rebuilds the region clock tree from the taps'
  tree_path (region root = LCP of its taps; parent = region with the longest proper-prefix root).
- START-TREE AMBIGUITY (COORD 08:xx input from DIE-QC-9), emulated as count_align_plan does it (amb.py):
  - A start-tree edge is CLEAN iff [d_lo - T/8, d_hi + T/8] holds no rise or fall sampling boundary. d is the TT u FF STA interval of
    that region pair, incl. OCV. A width <= T/2 - 2ap = 208 ps is clean whatever d is; up to 625 ps it is clean only if d lands well.
  - Each unclean edge adds 1 cycle to every crossing whose start-tree path uses it, and these add up along the path.
  - Crossing width = own d width + 2 x wander + ambiguity x T.
  - Depth needed uses a conservative K quantisation: D8 iff width <= 5.75 T, D16 iff width <= 13.75 T. UNCHECKED vs count_align_plan
    itself; QC cross-check is below.
- LOCAL = tools/die_plan/locality.py (main 59a3b1974f, LOCALITY-SCORE-3 code) run on the die's CURRENT region map (bind parts ->
  region), not on a new map, with feed 'fish':
  - the spine through the region centres is laid along the max-weight crossing spanning tree;
  - each region has a fishbone tree;
  - every on-feed crossing is a tree edge, with its last common point at the feed tap;
  - margins come from the shared clk_aocv g021 table + one-sided droop + class-B core latency + 5 % wander, through
    count_align_plan UNCHANGED (K, DEPTH 4/8, start tree, path ambiguity).
  - v_TT = measured clock speed x spice 1.0485: KV 321 -> 336.6 ps/mm; QC 199 x 1.548 (QC measured/model leg ratio) -> 323 ps/mm.
    FF = TT x 0.855 (table mu ratio; QC measured 1.293/1.548 = 0.835). Unless marked otherwise, all LOCAL numbers are ESTIMATE /
    UNCHECKED.
  - Crossing classes: tree-edge (on feed); short-loop (off feed, unshared <= 2.5 ns); long-loop (off feed, > 2.5 ns).
- START EDGES in the local form (startedge.py): one dedicated start port per feed edge at the clock fork.
  - The launch flop sits at the feed tap on the parent spine (0 unshared below the fork). The child's sync flop sits at its region
    root entry.
  - unshared = forwarded spine tap -> child centre, bounded by (w + h)/2 of the child region.
  - The width uses the same table, x spice, with droop between regions and 2 x 10 ps pin-cap range, at the worst of TT/FF.
  - This is what makes the count/start relation come from the edge's own tree node, not from the region-pair union of all its taps.
- Data: intel1:/srv/opentallas-scratch2/claude/clk-local-est-1/kv/ and epyc2:/srv/opentallas-scratch2/claude/clk-local-est-1/qc/
  (cur.json, cur_topo.json, loc_v1/loc_{fish,spine,fwd}.json, local_fish_feed.tsv = the forwarding graph, local_fish_crossings.tsv =
  tree node / unshared / depth per crossing). Scripts: localhost /home/ubuntu/.claude/jobs/b7f906df/tmp/clkloc/.

## CORRECTION to the brief's belief (CHECKED on KV and QC)
- KV and QC do NOT hang their region clocks off a die-wide tree. Both are ALREADY neighbour-forwarded region trees:
  - KV: one root (hgi_WN_5), 128 regions, region-tree depth up to 18 hops, region root arrival 0.03..9.92 ns, in-region insertion
    median 0.54 / max 0.85 ns.
  - QC: one root (sl_E0_stm), 313 regions, depth up to 21 hops, root arrival 0.03..10.6 ns, in-region insertion 0.70 / 0.88 ns.
- locality.py 'fish' on the same map rebuilds the SAME forwarding tree: KV 127/127 edges identical, QC 311/316.
- So the 5-16 ns of unshared clock does not come from a die-wide tree. It comes from two things:
  - (a) LOOP-CLOSING crossings (KV 1235/3595, QC 613/2537): data links between regions that are neighbours on the die but up to
    20-25 hops apart in the forwarding tree. Their unshared clock is the forwarded-chain difference: KV up to 16.0 ns, QC up to
    8.1 ns. Every L2197-type worst case is one of these.
  - (b) Tree edges whose start/CA interval is the UNION over all tap pairs of the region pair. With OCV this is 420 (KV) / 546 (QC) ps
    median wide, far above the 208 ps clean bound. So most start edges turn ambiguous, and ambiguity accumulates along the start-tree
    paths of the loop crossings.
- Re-feeding alone (fish vs the current fwd) only shortens tree edges: KV tree-edge unshared 2.0-2.2 -> 0.86-1.43 ns. It cannot make
  a loop crossing short: in any spanning tree of a 2-D region array, some physical neighbours are far apart in the tree.

## KV (DIE-KV)  [first, negative margins]
| | CURRENT (gate inputs, CHECKED) | LOCAL fish, same 128-region map (ESTIMATE) |
|---|---|---|
| forwarding | already neighbour-forwarded tree from hgi_WN_5, depth 18 | fish spine along the same MST, same root, 18 hops |
| worst unshared | 15.98 ns (hroot_EN<->phy_EN_7, LCA = die root h, 4.78/11.20 ns, 72/165 stages) | tree-edge 1.43 ns; long-loop 13.70 ns (same pair) |
| unshared tree-edge / loop med (max) | 2.00 (2.19) / 3.69 (15.98) ns | 0.86 (1.43) / 2.38 (13.70) ns |
| worst OCV | 706 ps (TT, loop); tree-edge max 130 | tree-edge 103 ps; long-loop 691 ps |
| clean start edges | no OCV 121/127; with OCV 47/127 (width med 420 ps) | 127/127 (dedicated fork start port: width med 76 / max 91 ps; even with the sync at the far leaf 146 ps <= 208) |
| path ambiguity | with OCV: 0 cyc 647, 1 cyc 1944, >=4 cyc 424, up to 12 cyc | 0 on every crossing |
| min CA margin | gate -66.7 FF / -62.2 TT (38 TT / 54 FF < 100) | 109.4 ps, 0 < 100 |
| depth needed | with OCV + ambiguity: D4 643, D8 2644, D16 224, >D16 84 | D4 3525, D8 70 (all long-loop), D16 0, FAIL 0 |
- Verdict:
  - Locality + fork start ports bring every crossing to >= 100 ps: 0 below 100 at D8 (min 109.4), and no crossing needs D16
    (ESTIMATE).
  - Without the fork start ports, the current topology needs D16 on 224 crossings and cannot fit 84 even at D16, because of start
    ambiguity.
  - The OCV term alone is not the problem. Replanning K on the bind's old (no-OCV) ambiguity leaves only 4 crossings < 100 at D8.
- Remaining risk: the 539 long-loop crossings (70k bits, D4 469 / D8 70) are direct crossings between distant tree branches, with up
  to 13.7 ns unshared and 691 ps OCV. They PASS with the computed bound, but they break the letter of 12.16b(i) ("never one crossing
  between distant tree branches").
  - Hop chains along the tree: 25 hops max, +694k extra bit-hops (latency, impractical).
  - Re-tree so the heavy loop pairs become tree edges (die owner's plan event).
- Cost of the local form:
  - Forwarded chain root -> farthest region (phy_ES_0): 18 hops, 9.74 ns TT insertion. That latency is absorbed by the count.
  - Jitter: a forwarded chain adds no PLL jitter (the source is shared). Buffer random jitter adds sqrt(N): ~165 stages x ~0.2 ps
    is ~2.6 ps rms, which is negligible (UNCHECKED: no jitter model exists).
  - Duty cycle along ~100+ buffer stages is the real chain risk: an uncorrected 0.5 ps/stage rise/fall mismatch gives ~50 ps of DCD
    at the far end. The CA ring and the start sync use RISE edges (EDGE_FALL only on some start edges), so DCD matters only for
    falling-edge start syncs and the guard path (T/8). Remedy: regenerate the duty cycle every ~5 hops, or use inverter pairs
    alternating polarity (UNCHECKED, needs one spice run).
  - Extra buffers: ~= current (same tree); tracks: worst face ratio 0.718, 0 boundaries over 1.

## QC (DIE-QC)  [first, negative margins]
| | CURRENT (gate inputs K2/G_tp, CHECKED) | LOCAL fish, same map (317 regions, ESTIMATE) |
|---|---|---|
| forwarding | already neighbour-forwarded tree from sl_E0_stm, depth 21 | fish spine on the same tree (311/316 edges), 21 hops |
| worst unshared | 8.07 ns (coll_s<->c_W5_bf_00, 4.01/4.06); sl_*_st_b->c_*_tn_10 7.97 ns (0.96/7.01) | tree-edge 1.26 ns; long-loop 8.40 ns (sl_*_st_b->c_*_tn_10, LCA sl_*_ctl, 10 hops) |
| unshared tree-edge / loop med (max) | 1.41 (3.06) / 2.20 (8.07) ns | 0.80 (1.26) / 1.66 (8.40) ns |
| worst OCV | 391 ps (loop); tree-edge max 165 | tree-edge 99 ps; long-loop 469 ps |
| clean start edges | no OCV 172/312; with OCV 99/312 (width med 546 ps). DIE-QC-9 t6 planner: 231 -> 171/312, CONSISTENT in kind; my region-union interval is wider | 316/316 (fork start port: width 88-89 ps; far-leaf sync 144 ps) |
| path ambiguity | with OCV: 0 cyc 1434, 1 cyc 847, 2-8 cyc 256 | 0 |
| min CA margin | gate -48.7 FF / -14.1 TT (37 TT / 4 FF < 100) | 105.9 ps, 0 < 100 |
| depth needed | with OCV + ambiguity: D4 1663, D8 784, D16 90 (DIE-QC-9 t6: 94 FAIL, 11 fit D8, 83 need D16) | D4 2396, D8 162 (tree-edge 46, long-loop 116), D16 0, FAIL 0 |
- Verdict:
  - Locality + fork start ports bring every crossing to >= 100 ps at D8: min 105.9, 0 need D16 (ESTIMATE).
  - The fork start port (each edge's count from its own tree node) is what removes the ~5 ns median ambiguity found by DIE-QC-9.
    The feed shape alone does not remove it.
- Remaining risks:
  - The 137 long-loop crossings (69k bits) sit between distant branches, up to 8.4 ns. The 12 sl_*_st_b -> c_*_tn_10 pairs (7.45 ns
    on the c_ side, 10 hops) are the place to re-tree: feed c_*_tn_10 from sl_*_st_b, or close the loop at sl_*_ctl with a short spur.
  - Margins are thin: worst lo 105.9 / hi 160.0 ps. The 'fwd' feed instead of fish gives 20 FAIL at D8, so fish (spine from the
    centre, not from the parent leaf) is required.
  - The region-union spread is not in the locality model, and QC in-region spread is 92/122 ps. Hence the dedicated start port is
    mandatory, not optional.
- Cost:
  - Chain to the farthest region (c_E5_tn_10): 21 hops, 12.6 ns TT, absorbed by the count. Jitter and DCD as for KV (~120+ stages,
    DCD regeneration needed, UNCHECKED).
  - Tracks: worst face ratio 0.935, 0 over 1.

## S81 (DIE-S81)  [inputs: codex-s81-owner-0359 proof_body, plan_s5, die-s81-8 gate_sspice bind; v 335 x1.0485 = 351.2 ps/mm]
- CURRENT (CHECKED): the brief's belief HOLDS for S81. All 398 regions hang straight off one deep die tree, with no region forwarded
  from another:
  - region root paths are up to 126 tree levels; root arrival 0.06..12.23 ns; in-region insertion median 0.40 / max 0.93 ns;
  - every crossing's last common node lies above both region roots: LCA h for 70 crossings, the rest on shared trunk nodes.
| | CURRENT (CHECKED) | LOCAL fish, same 398-region map (ESTIMATE) |
|---|---|---|
| worst unshared | 18.85 ns; median 1.37, p90 3.38 | tree-edge 0.86 median / 1.88 max; long-loop 21.3 ns (s_4S_L3<->s_4S_x06 and s_5S_L4<->s_5N_L2, 43 hops, LCA = root s_0S_L0) |
| worst OCV | 803 ps (TT) | tree-edge 128 ps; long-loop 1059 ps |
| clean start edges | no OCV 389/397; with OCV 312/397 (width median 347 ps) | fork start port 397/397 (width median 75 / max 184 ps); 396/397 if the sync sits at the far leaf |
| path ambiguity | with OCV: 0 cycles 1921, 1 cycle 292, 2-6 cycles 93 | 0 |
| min CA margin | gate 50.1 TT / 59.0 FF (10 / 13 below 100) | 114.6 ps, 0 below 100 |
| depth | with OCV + ambiguity: D4 1939, D8 314, D16 53 | D4 2253, D8 53 (all long-loop), D16 0 |
- Verdict:
  - Locality plus a start tree that follows the clock tree (fork start ports; this is START-TREE-1's job) puts every crossing at
    >= 100 ps with DEPTH 8 (ESTIMATE). That removes DIE-S81-11 group B (the 24 start-only crossings) and the 44 that needed more
    than D8.
  - Group A matches this: 5 pairs at 9-12 ns across the root split. In the local form, the cross-tier s_xN <-> s_xS / bk_sel pairs
    become long-loop crossings that are still direct at D8, with 1059 ps OCV.
  - DIE-S81-11's later trunk split (2.0-3.2 ns) is the better fix for group A: unshared drops 4-6x, while hop chains (19-35 hops) were
    rejected.
- Costs:
  - The feed is 32 hops / 15.3 ns from root to the farthest region (fE4_p6_b2), so this is the die with the most duty-cycle exposure.
  - 4 region faces exceed the track supply (worst 1.078). That needs a check in the plan event.
  - Max region insertion is 1.74 ns because the region spans 8.66 mm (single big partitions), which is above the 12.13a 1-1.5 ns
    guidance.

## HEAD (s81_head, DIE-HEAD)  [inputs: die-head-5 sta_ival proof, die_plan_root_sp5, die-head-7 bind_idreg; v 349 x1.0485 = 365.9]
- CURRENT (CHECKED): HEAD is already the local form, a spine with fishbones.
  - 12 spine and service roots (sp0..sp5, ctl, host, lep0N, lk_HOST0/1, sst5) feed 298 child regions one level down.
  - Region root arrival 2.35..5.83 ns.
  - Unshared: median 0.74 / p90 1.03 / max 4.89 ns. OCV: median 65 / max 213 ps.
  - Start edges with OCV: 324/325 clean (width median 172 ps). 7 crossings carry 1 cycle of ambiguity.
  - The gate's 4 TT crossings below 100 ps (78.6, sp3->sp2) are a K-plan without OCV. Replanned with OCV they need D4 420 / D8 7, and
    none need D16.
- LOCAL fish on the same map is NOT better for HEAD.
  - The MST rebuilds a different feed: only 26 of 325 edges match the current one.
  - It makes the 12 chE/chW turn links (tE*b0<->sp*, sp*->t*o0) into long loops: 7.03 ns, 24 hops, against 4.89 ns today.
  - Its margins are 108.0 / 152.2 ps, D4 413 / D8 14.
- Verdict: KEEP the current HEAD spine. Plan K/DEPTH with the OCV-inclusive bound (count_align_plan --sta-clock-ocv, CA-OCV-1) and
  move the one ambiguous start edge to a fork start port. Then every crossing is >= 100 ps at D8 (ESTIMATE from the emulation). No
  re-tree is needed.

## HBM (DIE-HBM)  [no built clock/CA bind (CA-OCV-1: none); plan hbm-streets2-1027/c18 + LOCALITY-SCORE-3 map tree_s3.5c5 (63 regions); v 349 ASSUMED x1.0485 = 365.9]
- CURRENT: no proof to check.
  - DIE-HBM-7 (UNCHECKED here): with a scatter + die-root LCA, 36 crossings / 2.8k bits exceed the 833 ps window (923 ps OCV). With
    a tree node at each crossing the worst is 607 ps and 0 fail.
- LOCAL fish (ESTIMATE):
  - feed root T029, chain 11 hops / 10.8 ns;
  - tree-edge unshared: median 0.83 / max 3.78 ns. Max region insertion is 2.29 ns because the regions span 8.8 mm (single
    partitions);
  - long-loop: 84 crossings, median 5.70 / max 18.55 ns (T059<->T060), OCV up to 849 ps;
  - count_align_plan on the modelled tree edges: 152 crossings with 1 cycle of ambiguity, 6 with 5. Result: D4 445, D8 67, FAIL 7.
    The 7 are 3 x T059<->T060 (amb 5) and 4 'unreached' (T001-T007, T005-T009: a start-tree component that the clean edges do not
    reach).
  - Fork start ports at the child root: 61/62 edges clean (width median 113 / max 231 ps). The one unclean edge is the 8.8 mm child.
    With the sync at the far leaf only 42/62 are clean.
- Verdict: locality alone does NOT close HBM. What does:
  - (1) Fork start ports, with the sync flop ON the forwarded spine at the tap, not at the child centre. Its unshared is then ~0 and
    the child-internal skew is checked as a related pair inside the region. All 62 edges become clean and the 4 'unreached' are
    connected.
  - (2) T059<->T060 at 18.5 ns: amb 0 then gives a width of about 2 x 849 + 2 x 928 wander, about 3.6 ns, which fits D8 (5.75 T).
    Even so, re-tree so that T059/T060 are tree neighbours; 12.16b(i) does not allow a direct crossing between distant branches.
  - (3) Measure HBM's real clock speed (349 is assumed).
  - Big-partition regions (8.8 mm, 2.3 ns insertion) exceed the 12.13a guidance. Whether the in-region related pairs close is a
    die-STA question that is not scored here.

## SUMMARY (current = gate inputs with the CA-OCV-1 model, CHECKED; local = fish on the current map + start tree following the clock tree with fork start ports, ESTIMATE/UNCHECKED)
| die | current form | worst unshared ns cur -> local tree-edge / long-loop | worst OCV ps cur -> local | min CA margin ps cur (gate) -> local | <100 ps cur -> local | depth need cur (OCV+amb) -> local |
|---|---|---|---|---|---|---|
| KV | forwarded tree, 18 hops | 15.98 -> 1.43 / 13.70 | 706 -> 103 / 691 | -66.7 -> 109.4 | 92 -> 0 | D16 224, >D16 84 -> D8 70, D16 0 |
| QC | forwarded tree, 21 hops | 8.07 -> 1.26 / 8.40 | 391 -> 99 / 469 | -48.7 -> 105.9 | 41 -> 0 | D16 90 (QC-9 t6: 83) -> D8 162, D16 0 |
| S81 | regions off one deep die tree | 18.85 -> 1.88 / 21.31 | 803 -> 128 / 1059 | 50.1 -> 114.6 | 23 -> 0 | D16 53 -> D8 53, D16 0 |
| HEAD | spine + fishbone (already local) | 4.89 (keep) ; fish 1.43 / 7.03 | 213 -> keep | 78.6 -> >=100 with OCV K | 4 -> 0 | D8 7 -> keep |
| HBM | not built | (scatter: >9) -> 3.78 / 18.55 | 923 -> 223 / 849 | n/a -> 104.3 + 7 FAIL | n/a -> 7 FAIL | -> D8 67 + 7 FAIL; 0 with spine-tap sync |
- ANSWER TO THE OWNER:
  - Yes, locality cuts the variation, but only on crossings that are tree edges: unshared drops to <= 1.4-1.9 ns and OCV to
    <= 100-130 ps on every die.
  - The multi-ns unshared that remains comes from two things:
    - (a) LOOP-CLOSING neighbour links that the forwarding tree places far apart: 8-21 ns, up to 43 hops. A single spanning tree
      cannot avoid them on a 2-D region array.
    - (b) START-TREE AMBIGUITY: region-pair-union start intervals of 350-550 ps against the 208 ps clean bound, which then adds up
      along the start-tree path. This is the dominant cause of the D16 need on KV/QC/S81 (DIE-QC-9 confirms it).
  - What fixes them, and is required together with locality:
    - (i) a start tree equal to the clock tree, with a dedicated start port at each fork (START-TREE-1). This takes path ambiguity to
      0 on every die except one HBM edge, which needs the sync on the spine tap.
    - (ii) K/DEPTH from the OCV-inclusive plan-time bound (CA-OCV-1 count_align_plan --sta-clock-ocv).
  - With (i) + (ii), every crossing on KV/QC/S81/HEAD reaches >= 100 ps at DEPTH 8, and no crossing needs DEPTH 16.
- Still at odds with 12.16b(i) (direct crossings between distant branches that pass on their computed bound, at D8):
  - KV 539, QC 137, S81 270, HBM 84 long-loop crossings.
  - Hop chains cost 13-43 hops (impractical).
  - The structural fix is re-treeing the heavy loop pairs, i.e. S81 trunk split; QC sl_*_st_b -> c_*_tn_10; HBM T059/T060.
- Long forwarded chains (9-15 ns, 11-32 hops) do not matter for jitter (common source, about 3 ps rms random, UNCHECKED). Duty-cycle
  drift of about 0.5 ps per stage (UNCHECKED, needs one spice run) matters for falling-edge start syncs and the T/8 guard. Plan a
  DCD-restoring stage every ~5 hops, or count-align on rising edges only.
