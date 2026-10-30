# DIE-HBM-22 (HBM die owner, 2026-10-29 16:35- PDT): die re-plan by locality for the 92 far pairs -- ESTIMATE (12.14b)

Input: plan of record d21h (die_plan 53b6d7beccd3, intel1 die-hbm-21/plan/d21h), its 312 lanes end-to-end (lanes.json,
extracted), and the 92 HBM-BIND-8 pairs left after h8b (rows103.json minus rows_h8b.json, 82,285 b).
Model (replan_est.py, plan arithmetic, UNCHECKED until built + G0/G0C/bind): the two SU/IDX/SFU rows per half are
permuted (row A y 4510.08 h 1555.2 under the hub row; row C y 10385.28 h 1572.48 above it; NE = MY mirror). A pair is
ADJ when the rectangles share >= 50 um of edge, else gap = edge-to-edge Manhattan, FAR > 1,200 um (lane_add --near-um).
Every plan lane AND every new pair is scored (moves must not make existing lanes far). opt.py = simulated annealing
over row orders (cost = sum bits x gap + far penalty + window over-subscription at 6 pins/um); variants.py = the table.

Facts that shape the re-plan:
- spu0 / spu1 are empty filler partitions (1,000 cells, 0 cores) -> free to resize/move.
- All b1xx / SU row types are PLAN-STRUCTURAL / NEEDS-KIT (HBM-018/-019): no kit is lost by a move or outline change.
- Rows A and C are 4,320 um apart (the hub row): no permutation makes a row-A SFU lane partition adjacent to b113 (ctl).
  => the SFU fix needs b110/b111 in row C (outline h 1555.2 -> 1572.48 = the b112/b113 template height; spu0 1684.8 ->
  466.56, spu1 1468.8 -> 2687.04 absorbs the freed row-A width).

| variant (per half, NE mirrored) | moves (both halves) | lanes re-routed | new far pairs / bits | all-lane far pairs / bits | bit-mm |
|---|---|---|---|---|---|
| d21h today | 0 | 0 | 92 incl. failed (far 54,498 b; non-adjacent 80,220 b) | 84 / 126,258 | 676,927 |
| VA_min: row A ... spu1 su30 **su31 b110 b100 b101**; row C **b113 b112** su00 su01 spu0 su10 su11 | 18 | 146 / 126,370 b | 54 / 42,509 | 82 / 117,415 | 604,498 |
| **VB2**: row A spu1(w) **b102 b100 b101 b103** su20 su21 **su31 su30**; row C spu0(n) su01 su00 **b110 b113 b111 b112** su11 su10 | 36 | 201 / 183,519 b | **36 / 16,377** | 68 / 107,585 | 420,775 |
| VB_opt (annealed, same sets) | 36 | 201 | 40 / 17,519 | 70 / 99,701 | 402,485 |

VB2 clears (ADJ after move): su30<->su31 4,755 b, b100<->b101 3,333, b100<->b102 2,777, b101<->b103 569, SFU
b113<->b110/b111/b112 7,658 + b113<->hub 2,970 + b111<->hub 570, hub<->su20 4,053 (su20 under the hub), b102->b101
1,181 NEAR (one hop through b100).
VB2 residual far (per half; NOT fixable by row order, need the item below):
- b113 ctl <-> sfu_N1/2/3 in su11/su20/su31: 3 x 1,112 b -> re-home the sfu_N cores into the SFU strip (core move, kits N/A).
- hub <-> spb0 (EP endpoint) 1,247 b -> ft slot on the shared type spb1 (type-shared rule, both halves identical).
- hub <-> hub over root 5,505 b (die) -> root feedthrough slot.
- b002/b103 -> root 297 b each, hub <-> sm0-3 37 b each, spt0->root 9, misc <= 4 b -> hop chain via root/ft slots.
So "0 far pairs" is NOT reachable by partition moves alone (estimate); it needs VB2 + sfu_N re-home + 2 ft slots.
Build note: no shared tool re-routes EXISTING lanes after partition moves (lane_add adds lanes only; hub_repack moves
cores inside a type). The build = a die-local event script: move origins/outlines -> drop the 201 lanes touching a
moved partition (ports, type buses, ft slots) -> rebuild them + the 92 pairs with lane_add's ADJ/NEAR builder (same
bits per pair; the binder matches crossings by partition pair) -> G0, G0C, strict bind.

## BUILD attempt (DIE-HBM-22-RP, 2026-10-29 17:29 PDT) -- time box reached, NOT G0-clean
replan_event.py (die-local; imports tools/die_plan lane_add/schema read-only) on d21h, runs intel1:/srv/opentallas-scratch2/claude/die-hbm-22/replan/{VB2,VA_min}.
| variant | die_plan sha | moved / dropped lanes | phase1 rebuilt / failed | mirror-name conflicts | 92 rows: built / FAR / failed | G0 (CHECKED) |
|---|---|---|---|---|---|---|
| VB2 | 4b5f1b0b3aa1 | 36 / 201 | 160 / 49 | 32 | 45 (50,682 b; adj 24, path 21) / 45 (16,377 b) / 12 | FAIL 4 schema (in_face == out_face U-turn ft slots); later checks masked |
| VA_min | 929c30fb74e7 | 18 / 146 | 126 / 20 | 30 | 17 (26,582 b) / 73 (42,509 b) / 6 | FAIL 5 schema (same U-turn class) |
FAR after VB2 = exactly the estimate residual (b113<->sfu_N su11/su20/su31, hub<->spb0, b002/b103->root, sm->hub 37 b, misc) -> estimate CONFIRMED by construction.
Rebuilt-lane cycles (plan arithmetic, UNCHECKED): VB2 94 lanes change, 27 up, max +34 / -31; VA_min 73 change, 14 up, max +7 / -26.
Open defects of the event (next step): (1) U-turn chains: reject a path whose crossed partition has in face == out face;
(2) 49/20 phase-1 failures "no macro-free station chain" on long chains via hub/sm/io/root (L48/L53/L106/L125 io<->root,
PHY<->hub, hub<->sm2/spb2, b112<->hub): keep the UNMOVED segments of a lane (re-route only the hops touching moved partitions)
instead of re-routing end-to-end; (3) mirror conflicts 30/32: NE mirror lanes on NW/NE-shared types (sm*, spt1/2, mcb, root)
allocate a different type-frame window than the NW lane -> build NE mirrors by mirroring the NW result, not re-allocating.
NOT UPDATED: clock sidecars, pg_bumps.json, internal_stations/die_ft_bands of moved types. Not bound (HBM-BIND-9 owns bind).
