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

## Not done (freeze gate 12.4a still open)

Die STA on real views needs four things first:

1. Landed partition views: every one of the 16 types rebuilt with its rings, fclk pins and monitor, then signed off.
2. Ring-window STA at the landing.
3. die_sta.py with `--spine-tree fd300`.
4. The compose step finished. Run 1 of `clock_landing_plan.compose` FAILED after ~14 min with KeyError buses
   (HEAD frame types hd_turn_a/b and hd_st_* declare only ft_slots). This branch makes it generic with
   setdefault("buses"); clock_landing tests still PASS (17). The rerun is live:
   epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026/compose2/compose_report.json (log compose2.log).

The hd_ctl observer ports (fault/ready) are not declared and are recorded as OPEN.
