# INFRA-FIRST-QC-R33 (2026-10-27 17:20-18:35 PDT)

Base: claude/qc-infra-r32-1027@91bf875e89. Export inputs = R32 model (args.json) + --a0-band-window 3 --a0-band-window-tol 30
(ACCEPTED basis, COORD ruling R32 (a); cost ledgered in coord lanes/CLOCK-RESIDUAL.md). Event plan = R31 dry15c plan.json,
builder = this branch tools/ (die_clock_mesh/die_clock_128 unchanged vs R32), trunk_escape 100.
Data: intel2:/srv/opentallas-scratch2/claude/qc-infra-r33/.

## 1. Feed-column de-confluence (COORD ruling R32 (b)): opt-in, default output unchanged (45 tests PASS)
tools/die_plan/qc_clk_mesh3.py adds two options.
- --a0-band-col-side N: the band y-tree column = feed column + N island x-pitches (4.86 um) on the column-tree lane side.
  The sign comes from the core geometry (legalize lane_sign), so W/E mirror types get mirrored offsets. A die-edge column
  flips to the other side.
- --col-tap-side N: the merged top-leaf / column-tap cell snaps from a plan point N pitches toward (+) or away from (-)
  the column-tree lane.

All exports: geometry PASS, reach 448.524, band resid max 144.1 unchanged.

| export (all with window 3 / tol 30) | band resid TT med (ps) | dry17 no_clock_track |
|---|---|---|
| R32 dry16_w3t30 (no column moves) | 35.2 | **682** |
| band -2, tap +1 | 33.4 | 885 |
| band +3 | 34.0 | 793 |
| band +3, tap -1 | 34.0 | 782 |
| band +3, tap +1 | 34.0 | 852 |
| band +4, tap +1 | 33.7 | 769 |
| band -3, tap -1 | 32.2 | 976 |

Result: disjoint island columns at the feed column do NOT reduce the census; every variant is worse. Not adopted (own
runs, UNCHECKED). Exports with a column move also carry +224..238 instances (band anchor/width re-choice; equal stage
counts kept).

## 2. Why (classify_trunks.py; dry16_w3t30_classes.txt vs dry17_b4t1_classes.txt)
Column-on-column convergence does not dominate the 682 failures. They come from HORIZONTAL M8 16w top-tree trunks that
fill the pin windows of the cells they pass.
- 96 col_node M9 driver jogs sit under the 16w top LEAF leg (top_node -> col_tap). The leg crosses the column-tree lane
  on its way to the tap. No column move changes this count.
- 108 band row x-tree node escape jogs (period offset ~337 um) share a row window with a passing 16w top trunk (top_rep at
  offset ~318). The A0 band rows sit on the same VSS slot rows as the top local-tree lanes.
- 85+ top x-tree nodes (offset ~627) fail on escape M9 drops, and 104 top_rep fail on escape jogs (offset ~318), with no
  other cell nearby. Each 16w trunk's own escape out of its window lands on a neighbour lane that already holds a 16w
  trunk (lane pitch 8.64, escape offsets +-7.3 / +-16.0).

Next structural fix:
- (i) vertical landing of the top leaf leg: the horizontal run on the parent lane ends at the tap column, then an M9 drop
  to the tap, so the leg never crosses the column-tree lane;
- (ii) band row trees on slot rows disjoint from the top local-row lanes (row allotment per type, mirrored);
- (iii) escape targets that skip lanes holding a 16w top trunk.

## 3. FT per-bit source pins (COORD ruling R32 (c)): ft/ (sub-agent run, reviewed)
ft/ft_pin_hops_src.py keeps the R32 model and adds the real per-bit source pins for non-slot sources. The pins come from
the kit pin generator (gen_phys.type_pins -> schema.Plan.port_pins), with the same face, window, layer and bit order the
kits use. All 250 instances matched.

The R32 over-limit list holds 37 instances in its JSON. Its README said 41; 41 is not reproduced.

Real worst in-hop is 402.9 um (coll_f4 out_err_re_wi <- coll_f3); worst out-hop is 401.2. **0 instances are over 405, so
no register move, no station and 0 cycles.**

- CHECKED: coll_n rec_rx_s0 plan pins == QC-KITS-R1 pre-kit pins.json (548/548, dx 0).
- CHECKED: the 45 neighbour-matched instances agree with R32 within 0.64 um.
- UNCHECKED: the other per-instance hops (plan geometry; no cut kit yet for those source types).
