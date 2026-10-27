# FALLBACK-HEAD 2026-10-26 — s81_head bottom-up landed fallback (OWNER 16:5x, IF.FALLBACK)

Every number here is **UNCHECKED** until NUMBER-CHECK recomputes it. Plan d7b8d1eb (main 63f0898a3, sha256 of
physical/die_plan/s81_head/die_plan.json unchanged). No canonical plan, RTL or core changed.

## 1. Plan

**Regions = partitions (326).** Each partition closes its own CTS tree from ONE die clock entry (region root). The
existing hard cores (elemA/elemB cv views, 1,320 instances) are reused unchanged; inside hd_tile the tile tree feeds
their clock pins (CP2 lib insertion 415.6 / 378.8 TT). No die-level related pair crosses a partition boundary.

**Landing points: every plan port (428 crossings, 212,622 bits)**: `ot_dp_clk_landing` in the receiving partition at
the bus face. The source forwards its clock (`fclk_out_<bus>`), the ring writes on it and reads on the local clock.
There are no credits. The proved nominal contract is +3 fixed cycles per crossing (OFFSET 2 + RDREG 1).
`clock_landings.requirements`: 1,712 new scalar pins, 1,065,250 live ring FF, and **0 type splits (16 -> 16 types)**,
because every tile has the same i/o mask.

Area: ring 0.99 mm² on the 4.66 µm²/bit basis (0.32 % of the die), or 0.32 mm² FF-only. This is logical and UNMAPPED.

The row-pair alternative (50 regions, 152 crossings, +42 cycles/pass) is recorded only in `summary_rowpair.json`. It
keeps the tile-seam related pairs inside each region, and those pairs are what failed before (268/254), so it is not
proposed.

**Added cycles.** The critical lm_head pass is ctl -> spine down to row-pair 5 (6) -> W chain (25) -> spine up (6), so
37 landed crossings = +111 cycles. The TP4 rank all-gather legs add a worst 10 crossings each way (+60). The total is
**+171 cycles per head pass**.

**TOK-DS** (compose_tok_ds on 63f0898a3, same table of record):

| Mode | Baseline | Head passes on the critical path | Added | Fallback | Change |
|---|---|---|---|---|---|
| AR | 784.9 tok/s, T 1,528,917.6 | 1 (lm_head 8,450) | +171 cycles | 784.81 | −0.011 % |
| MTP | 2,749.3 tok/s, T_step 1,815,279.6 | 6 (5 draft.head + lm_head) | +1,026 cycles | 2,747.75 | −0.056 % |

## 2. Tooling (branch claude/fallback-head-1026)

- `tools/s81_head/fallback_land.py`
  - `plan`: region table in the exact `clock_landings` / `clock_landing_plan` format, plus a summary.
  - `compose`: runs the existing `requirements`, `clock_landing_plan.compose` and `landing_contract.check`.
  - `variant`: FB1, one entry per partition; hd_serdes entry moved out of the VDDPHY domain to the digital strip.
- `tools/s81_head/fallback_land_report.py`: landed-window report plus render. Per crossing it checks
  d = arr(dst entry) − arr(src entry), requiring |d| <= P/2 = 416.5 ps at TT AND FF, and reports the TT->FF drift.
- `tools/die_plan/die_trial.py --htree-full-depth` (opt-in; default byte-identical, tested): it bisects single-tap
  regions down to `--leaf-um`, so every leaf is at the same depth (equal-length by construction) and the leaf->entry
  leg is <= ~leaf_um. No pads, no trims, no post-measurement values.
- `tools/s81_head/test_fallback_land.py`: 4 tests PASS; `test_die_trial_core_obs` PASS.

## 3. Die GRT incl. clock + landed clock window

Recipe: combined die global_route = die_trial signal kit (M4-M7 adj 0.75) + die ctree (M8-M9 adj 0.4), ONE
global_route, **50 congestion iterations**, TT and FF. Native OpenSTA on GRT RC (mk_combo_dcm recipe). Run dir
epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026/fd300.

| Build | GRT overflow (every layer, TT+FF) | Entry slew max | Landed abs(d) max TT / FF | Verdict |
|---|---|---|---|---|
| leaf600 (default die_trial tree) | 0 | 786 ps (42 > 320) | 444.4 / 390.5 | FAIL, 4 crossings |
| **fd300** (`--htree-full-depth --leaf-um 300`) | **0** (0 GRT-0113/0114) | **96.7 ps** | **89.3 / 80.1** | **PASS** |
| fd600 (`--htree-full-depth`, leaf 600) | 0 | 289 ps | 98.0 / 88.6 | PASS |

leaf600 FAIL detail: the 4 crossings are corner serdes <-> station frames. Root cause: single-tap regions stop
bisecting early, so leaf legs are unrepeated and long and the depth is unequal (insertion spread 649 ps).

fd300 detail: insertion TT 5,816-5,995 (spread 179), FF 5,035-5,195 (spread 160); margin 327 ps; drift max 9.2 ps.
Render fd300/fb1_fd300.png (viewed: no red crossings, no slew rings, equal-depth tree).

## 3b. GEOM-REVIEW-7 FAIL on fd300 tree sites -> fs300 (COORD amend 17:21)

GEOM-REVIEW-7 found that 1,002 of the 1,663 fd300 buffers sat on hard cores. The report recount with this branch gives
1,360 cells on core, 56 in VDDPHY and 16 outside any partition, out of 2,333 buffers + repeaters. Rule 12.2a1 forbids
parent cells inside core outlines.

**Fix: `die_trial --tree-site-legal`** (opt-in, combined with `--htree-full-depth --leaf-um 300`).
- A SiteMap holds the 1,320 core outlines and the 12 VDDPHY rects (2.16 um halo) and requires every cell to sit inside
  a partition.
- A one-entry leaf buffer drives AT its entry, which is already in the tile channel.
- Every other buffer moves to the nearest legal channel point. A repeater slides along its leg first.
- `fallback_land_report.py` now runs an independent site check (no halo, own transform) and draws core outlines, PHY
  rects and every cell.

| Build | Cells | On core / in PHY / outside | GRT overflow TT+FF | Entry slew max | abs(d) max TT / FF | Insertion spread TT | Drift max |
|---|---|---|---|---|---|---|---|
| fd300 | 2,333 | 1,360 / 56 / 16 (FAIL) | 0 | 97 | 89.3 / 80.1 | 179 | 9.2 |
| **fs300** | 2,311 (648 reps) | **0 / 0 / 0** | **0** | **18.5** | **311.9 / 272.8** | 607 | 39.2 |

fs300 passes the landing window against 416.5, with a margin of only **105 ps TT** and 144 ps FF.
- The greedy nearest-site moves break equal length: 1,145 nodes moved and wire grew 4 %.
- The worst crossings are spine sp2<->sp3 (sp_x3, sp_b3, host_tx/rx_3), which sit on the two sides of an upper H-tree
  split.
- The 105 ps margin is below a ~5 % OCV allowance on a ~6 ns unshared tree (~300 ps, UNCHECKED estimate). It is
  therefore NOT robust.

**Next structural step (GEOM-7 item 1).** Snap the bisection itself to tile-relative channel crossings so that every
node of a level gets the same tile-local site and leg lengths stay equal. Also meet the sp2/sp3 seam at a common
spine-column node. Predict |d| before the build.

**Implication for the 16 ring rebuilds.** The tree buffers inside partitions are push-down cells in the partition
channels: 1,312+ of them in hd_tile at channel sites. Each type kit must reserve those sites (fs300/tree.json `sites`)
the way it reserves FT.

## 3c. COORD ruling 17:4x: equal-length site-legal tree (sl300) + uniform monitor (no type growth). UNCHECKED.

**Tree: `die_trial --htree-full-depth --leaf-um 300 --tree-site-slide`** (opt-in).
- Each buffer slides back along its OWN incoming leg (toward the parent's ideal point) to the first legal site. A node
  with one downstream path may also slide forward along that leg, whichever is nearer.
- Either move keeps every root->entry Manhattan length unchanged, so equal length holds by construction.
- 118 nodes had no legal point on either leg and fell back to the nearest site.
- **Prediction before build:** `tools/s81_head/tree_predict.py` is a least-squares stage model fitted on fd300+fs300.
  It has RMS 36 ps and under-predicted abs(d) by 45-70 ps on those two runs. It predicted max abs(d) 181 TT / 161 FF.

| Build | Cells | On core / PHY / outside | GRT TT+FF | Entry slew max | abs(d) max TT / FF | Margin TT | Spread TT | Drift |
|---|---|---|---|---|---|---|---|---|
| fs300 (nearest) | 2,311 | 0/0/0 | 0 | 18.5 | 311.9 / 272.8 | 105 | 607 | 39 |
| **sl300 (slide)** | 2,393 (730 reps) | **0/0/0** | **0** | 81 | **212.4 / 188.4** | **204** | 469 | 24 |

Measured 212.4 against the predicted 181, inside the predictor's known under-bias.
- Worst crossings: the chain turn tW3b10<->tW3b9 (212) and spine end sp5<->host (202).
- sp2<->sp3, the fs300 worst, is no longer in the top 5.
- A literal common spine node for sp2/sp3 was not needed: they share the root, and once equal length is restored their
  offset is small.

**Monitor: `fallback_land.py compose --monitor dataflow`** (opt-in mode added to clock_landing_plan.compose; the
default reset-wavefront mode is unchanged and all clock_landing tests still pass).
- The ready/fault status rides each landed DATA crossing as 2 spare bits of the receiving ring, on the same forwarded
  write clock.
- Its ctl pins are named by the data bus, so every instance of a type has identical declared ports. Every pin has
  exactly one driver and one receiver (landing_contract: no absent-child ties).
- Each type has ONE uniform tree bus toward ctl, chosen on a reverse-BFS potential (hd_tile = `o`). Other outputs carry
  local-only status, so the AND network is acyclic.
- **Types 16 -> 16** (was 33). landing_contract 0 errors (420 pins, 1,284 edges, max hop 18.3 um). Boot ready max 326
  cycles (was 692).

**Placement failures 10 -> 0.** Root cause: the hd_tile W/E faces are elemA columns from y 8.64, so no full-height face
strip exists. `_storage_band` now also tries equal-area channel-aspect banks, and only when both legacy aspects fail.
hd_tile `i` gets a 244.1 x 10.8 um bank in the 45-um horizontal core channel (y 362.9-373.7). Its max pin hop is
402.7 um against the 403 limit, which is tight. The tile kit must reserve this bank next to the tree sites.

## Not done (freeze gate 12.4a still open)

Die STA on real views needs four things first:

1. Landed partition views: every one of the 16 types rebuilt with its rings, fclk pins and monitor, then signed off.
2. Ring-window STA at the landing.
3. die_sta.py with `--spine-tree fd300`.
4. Clear the compose result. compose2 (after the buses fix): status OK, landing_contract 0 errors (487 pins, 1,403 infra
   edges, max hop 366 um), boot_ready max 692 cycles, network lane cycles 1,284 over 328 lanes. But **types 16 -> 33** (the
   monitor-cohort splits of hd_tile) and **10 placement failures**, one per hd_tile cohort type. Both have to be fixed in
   the ring rebuild plan, and the type growth has to be reduced. Full landed_plan.json:
   epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026/compose2/.

The hd_ctl observer ports (fault/ready) are not declared and are recorded as OPEN.
