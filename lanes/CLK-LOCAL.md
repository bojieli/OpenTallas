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
