# HBM SM frame re-pack (H-SM-REPACK, 2026-10-15)

**Question.** TILE-FILL (354b5bb2e) found the 32 `hfd_sm` frames take 362 mm2 of the 660 mm2 die at 19.5 % fill.
What is the smallest SM frame that can close, built from the SM's closed children?

**Answer.**

* The v5 slot (6,609.6 x 1,712.08) assumes an SM tile of 693.44 x 609.92 (codex/sm-dense-pack-1015 62f2a4a7b). That
  tile is unbuilt. It needs 6 new transport masters, and it carries the 3,705-bit E-W bus on M8 over the leaves.
  A cluster's signals stop at M7 unless H-DIE grants M8 (`cluster_layer_grant`). With that grant, die M8/M9 are PG-only
  over every tile.
* Under the M7 cap, the bus must run in a horizontal channel that holds no macros. The smallest closable tile built
  from closed children only is **rp1: 397.44 x 1,192.32 = 0.474 mm2**. For comparison, cpt is 0.627 and r16 is 0.790.
  * The 10 closed leaf views are re-stacked N-S: xs, then bdc and tct, then tcl x2. Leaf 1 is the mirror image.
  * The W transit and E beat stages use the CLOSED `ot_smh_tr_group_beat_e` master, x2.
  * The 265.68-um channel is sized from the crossing bits: 3,705 face pins on M4 + M6 take 203 um; H cut 0.56.
  * The smallest gap between children is 23.76 um. The RTL registers every port at its pin.
  * Estimated parent sinks: ~14.6k (the cpt FAIL had 22,862 sinks on one root).
* **rp2** is the A/B twin. It also hardens the N/S landings (closed `ot_smh_tr_group_land` x2), so parent sinks drop to
  ~10.4k. Cost: 397.44 x 1,330.56 = 0.529 mm2.

| frame | outline um | mm2 / SM | 32 SM mm2 | vs v5 | child coverage | content fill | min gap |
|---|---|---|---|---|---|---|---|
| v5 (slot, unqualified tile) | 6,609.6 x 1,712.08 | 11.32 | 362.1 | - | 69.8 % | 19.5 % | 10.8 um (front) |
| rp1 | 3,697.92 x 2,505.6 | 9.27 | 296.5 | -65.6 | 89.2 % | 23.9 % | 21.6 um |
| rp2 | 3,697.92 x 2,782.08 | 10.29 | 329.2 | -32.9 | 88.9 % | 21.5 % | 21.6 um |

The rp frames use 8 columns. Each column is 2 tiles plus a BE; the W columns are the same master placed MY. The
static front (`ot_smh_static_front`: fc_xl, fc_t x2, fc_xr x2, fc_b x2, plus about 50k um2 of cells) sits in a
345.6-um middle column. Tiles are 21.6 um apart.

## Why content fill stays near 24 %, not 60 %

The closed leaves are already about 50 % full inside, and that space is mostly routing they need. In rp1 the leaf
outlines alone are 0.197 mm2 of the 0.474 mm2 tile. Another 0.106 mm2 is the transport channel, whose height is set by
the 3,705 bits that cross every tile.

Two levers would go further:

* **An H-DIE M8 grant for the tile.** The bus moves over the leaves, which needs the 6 new masters of the v5 tile and
  about 0.42 mm2. Die feedthrough over SM frames then has to use reserved lanes.
* **An RTL change by H-SM.** Today the tile chain re-registers the 2,069-bit x-write beat in every tile. A narrower
  beat, or a per-column x-write, would shrink the channel.

## Pictures (looked at, owner rule 20:45)

| image | what it shows |
|---|---|
| `v5_frame.png` | The front column (front_n / front_s) stands about 370 um taller than the tile stack, leaving empty bands over and under 8 tile columns. There are 10.8 / 12.96 um slivers inside the front. The front holds the legacy front_n / front_s / fc_bc / fc_is, which `ot_smh_static_front` no longer instantiates. |
| `v5_tile.png` | The bus would need M8 over the leaves. The rowE strips are 20-30 um thin. |
| `rp1_tile.png` | One child column. The transport channel holds only the two beat_e masters plus cells. It is a large, low-fill band, but it is cut-bound. |
| `rp1_frame.png` / `rp2_frame.png` | No nested wrapper whitespace at the frame level (89 % child coverage). The front column is the only sparse part, about 0.43 mm2 of space per SM. |

## Jobs

| job | candidate | host |
|---|---|---|
| `smh_tile_rp1-rp1-COMMIT-619450852` | rp1 | EPYC4 |
| `smh_tile_rp2-rp2-COMMIT-39fd03eab` | rp2 | from the queue |

Both jobs run the full lockstep bench plus the late32 / hold0 / strap mutants. The frame route waits for a closed
tile view: no SM-level route is possible before that.

## Files

| file | purpose |
|---|---|
| `tools/hbm_sm_repack_1015/geom.py` | the geometry, single source |
| `tools/hbm_sm_repack_1015/repack.py` | the analysis and renders |
| `physical/ref_tile_specs/smh/mk_smh_tile_rp.py` | the kit generator (`SMH_RP=rp1` or `rp2`) |
