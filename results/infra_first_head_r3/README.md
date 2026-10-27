# INFRA-FIRST-HEAD-3 R3: s81_head channel-row global tree, one continuous mesh, edge-pin stubs, PG (D-INFRA-FIRST-HEAD)

Branch claude/infra-head2-1027 (R2 worktree reused, on 8ccc0bb5a3). Plan physical/die_plan/s81_head/die_plan.json
sha256 674a8ac9 is NOT edited in R3. Run dir intel2:/srv/opentallas-scratch2/claude/infra-head3-1027 (m2 = tree + mesh,
mp3 = master-plan --mesh, pg = PG lane). All numbers are plan-model, own-tool and UNCHECKED unless marked CHECKED.

## 1. Tree sites off the hard cores (task 1) -- `tools/s81_head/head_mesh_r3.py`
- Root cause of R2's 552/1224 on-core sites: the row x-trees ran on the eB island row (tile y 876.96), so every leg between
  eB islands (708.48 apart) put repeaters on eB / tile glue.
- R3 structure: the row x-trees run on the hd_tile **horizontal channel** between the eA rows (tile-frame y 354.24; eA bottom
  ends 328.32 on the rebuilt outline, eA top starts 380.16, both +1.08 clear; MY-invariant; the line crosses no hard core
  across a whole half, CHECKED arithmetic). Mesh drivers sit at the tile **channel cross** (354.24, 354.24) = the 12.2a
  "partition channel cross" island. The y-trunk is on the spine column (hd_spn soft). The two station rows (type-frame y 613.44,
  die y 1944 / 15612.48, 18 drivers each) are their own x-trees, spliced onto the trunk at the delay-matched point
  (y 4182.09 / 13996.80) with +1 plan-computed arm stage (12.8 d1; not a post-measurement pad).
- Gate (head tree_on_islands, plan-model classification of every node + leg repeater + driver): **PASS, 1387 sites:
  1128 tile channel row, 103 spine slots, 156 station slots; 0 on hard core / PHY / reserve frame / tile glue**; max stage
  segment 444.3 um <= 450.
- Tree: 300 drivers, 36/37 stages, 787 repeaters, 525.1 mm wire (16W, 2x BUFx24), plan arrival TT 3093.3-3095.9 / FF
  2485.9-2492.3 ps, **nominal driver skew TT 2.58 / FF 6.41 ps**; legs straight except the two station arms (1.75-um jog at
  the trunk x 8762.82 vs station root x 8761.07).

## 2. Edge clock pins (task 2; COORD RULING INFRA-FIRST-HEAD-2 ASK2)
Stub = plan-computed tile pushdown route from the nearest mesh strap to the R12 kit edge pin (rebuilt outline, plan origin
and core orient), identical on every instance of each core slot:
- elemA N-face pin (293.58, 317.576) -> **43.38 um** to the M9 column on the tile axis (x 354.24) in the eA channel
  (1056 instances, min = max; CHECKED arithmetic 354.24 - (17.28 + 293.58)).
- elemB W-face pin (0.042, 257.58) -> **38.92 um** to the M9 column x 177.12 through tile glue (264 instances; CHECKED
  arithmetic 216.042 - 177.12).
- Recorded in lanes/CLOCK-RESIDUAL.md as a stub (no residual tool used). **Insertion: PENDING.** HEAD-KITS R12b has not
  finished (02:5x: elemB route epyc2 unit oth-ubuntu-1807202-1793090484, ETA ~03:30; elemA intel1 waiter pid 1160184, ETA
  ~05:00). Reference only: elemB R10 GRT edge-pin max-rise 252.55 TT / 196.95 FF (CHECKED in HEAD-CORE-R10), inside the
  12.3 band. COLLECT: R12b routed 6_final RCX clock pin -> sinks max/min at TT and FF for each core; accept if inside
  250+-20 TT / 202.5+-20 FF, else flag for the next-core-round centre re-pin.

## 3. Continuous mesh (task 3) -- plan model
- Straps: 52 M8 rows (4 per tile row: eA 168.48 / channel 354.24 / eA 540.00 / eB 876.96, extended over the turns and the
  spine; + 2 station rows + 2 serdes strip rows) and 66 M9 columns (tile x 177.12 / 354.24 / 531.36; full height to the
  serdes strip rows over the station band, stopped at the tile array next to the corner reserve frames). 894.6 mm M8 +
  961.8 mm M9 (8W assumed).
- Own gates: continuity **PASS (1 component)**; drivers on strap **PASS 300/300**; tap stubs **PASS (<= 200 um)**: core
  centre entries 0, edge pins 43.38 / 38.92, partition taps max 159.84 (hd_spn tap at the tile-row boundary), density
  sinks 30.16. The 16W trunks + 8W straps use about 0.7 % of M9 / 0.4 % of M8 tracks (PG lane estimate).
- Master-plan --mesh (mp3, export `tools/s81_head/head_mesh_export.py`, straps exported as a full lattice = pessimistic):
  FAIL. The FAILs are plan-declaration items for the PLAN-DELTA, not tree geometry:
  - clock_sites / island_lattice: the channel-row slots and the channel-cross island are not yet declared islands in the
    plan (the hd_tile partition island is still at (354.24, 518.4)); 504 nodes + 264 drivers read as "tile_glue".
  - clock_shield: 118/118 straps overlap the plan 0.48@8.64 PG grid; they need the VSS-phase lanes of the new PG grid (sec. 4).
  - footless_stubs / island_ft_inputs: the export carries no strap binding / the 5280 unused in-core island ft inputs are not
    yet tied to their local strap.
  - tree_balance (length-family) FAILs by design for a delay-balanced tree; tree_on_islands (the master-plan's own
    island_tree, a different tree) FAILs with spread 4794 um; clock_entry / core_insertion_model / core_reach FAIL as in R2
    (edge pins, out-of-calibration centre model). Data: data/mp3_gates.json.
- Renders viewed: render/r3_mesh_tree.png, r3_zoom_tile.png (rows in the eA channel, no site on a grey core),
  r3_zoom_spine.png (trunk + M8 rows across the spine), r3_zoom_corner.png (station row, serdes strip row, reserve frame
  left clear). GEOM REQ posted.

## 4. PG (task 4) -- see pg/README.md
- Head power from the hold2 GRT netlists (OpenSTA, activity 0.5): elemA 0.1487 W, elemB 0.1370 W; hd_tile 1.493 W/mm2
  upper bound (glue at core density), 289.6 W for 264 tiles = 4.6x the R1 borrowed basis (UNCHECKED).
- **No M8/M9 grid meets 35 mV with the plan's 150-um power bumps** (best 69.4 mV, both layers ~100 % metal).
- PDNSim window: M8 0.48@4.32 + M9 6.48@34.56 with **75-um core power bumps: 24.5 mV PASS**, M8 29.4 % / M9 48.3 % tracks;
  the 10.8-um VSS-adjacent gaps take 16W / 2x16W trunks with <= 4.32-um jog (UNCHECKED). The bump pitch is a package
  decision -> ASK.

## 5. Not done (task 5)
- Die GRT >= 50 iterations incl. the clock: NOT launched. It needs the built clock (die_clock_mesh combo DEF of this
  mesh + tree, with the plan-delta islands and the VSS-phase PG), which needs the PLAN-DELTA items above first.
- Mesh MC (qc_clk_mesh3 solve form, one variation model per segment) and related-pair die STA (main die_sta_related.py,
  0.21 %/mm AOCV outside the mesh, droop per mesh): NOT RUN.

| item | value | status |
|---|---|---|
| tree sites off cores | 1387 sites, 0 on core/PHY/reserve/glue | UNCHECKED (tool) |
| channel row clear of cores | 328.32+1.08 < 354.24 < 380.16-1.08 | CHECKED (arithmetic) |
| max stage segment | 444.3 um <= 450 | UNCHECKED |
| tree nominal skew TT / FF | 2.58 / 6.41 ps | UNCHECKED |
| tree arrival TT / FF | 3093-3096 / 2486-2492 ps | UNCHECKED |
| tree size | 300 drv, 36/37 stages, 787 reps, 525.1 mm | UNCHECKED |
| elemA / elemB edge-pin stub | 43.38 / 38.92 um, identical per inst | CHECKED (arithmetic) |
| core insertion from R12b | PENDING | -- |
| mesh continuity / drivers on strap | 1 component / 300 of 300 | UNCHECKED |
| mesh wire M8 / M9 | 894.6 / 961.8 mm | UNCHECKED |
| master-plan --mesh | FAIL (declaration + shield + stubs) | UNCHECKED |
| head power elemA / elemB @0.5 | 0.1487 / 0.1370 W | UNCHECKED |
| PG at 150-um bumps | best 69.4 mV FAIL | UNCHECKED |
| PG M8 0.48@4.32 + M9 6.48@34.56, 75-um bumps | 24.5 mV PDNSim, M8 29.4 % / M9 48.3 % | UNCHECKED |
| die GRT / mesh MC / die STA | NOT RUN | -- |
