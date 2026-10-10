# R25GQ: HBM die re-floorplan, owner Option A (2026-10-10, hbm-phys-1010 [fp])

This is the successor to R25GP. It keeps the same outline, 31,734.288 x 25,282.8 um (802.33 mm2).

- **Generator:** `tools/hbm_accel_die_fp.py` preset `r25gq` (`build_r25gq`). It is opt-in, and the r25gp, r25gph and default plan outputs stay byte-identical.
- **Record:** `tools/hbm_r25gq_plan.py --out <this dir>` writes `summary.json`.
- **Grades:**
  - Geometry is a generator plan built from measured block outlines. Legality: 208 instances, 0 overlaps, 0 outside (`check_r25gq.txt`).
  - Channels are an ESTIMATE. There is no die GRT yet, and the nets are R25GPH logical nets carried over plus the Option A nets.
  - Power is a PROJECTION.
- **Not checked yet:** pin clashes, the margin lint and the die top lint need die nets, and a placement plan has none. They run on the network build after the dependent blocks are re-routed.

## Contents
- **SM:** 32 in a 3 x 3 grid.
- **Attention:** 32 tiles, as PS halves in a 4 x 2 grid per quadrant. R25GP row r maps to row r // 2.
- **SU:** 512 lanes. The slot is 2,016.144 x 2,808 um, sized by `hbm_hub_quarter_gen --tiled --lanes 128 --groups 4 --wct 456` at dc737578e. That gives 128 hfd_su_tile_xl in 8 columns and 16 chains, with 116.64 um channels.
- **SFU:** half width, on the SU column.
- **HC:** 4 quarters, placed over a 2 x 3 index_q stack.
- **Index score grids:** 36/64 of R25GP.
- **VM:** VM8 vertical halves.
- **Spine:** reordered, with quant, HGI VM and CP abutting so the shared lane group B stays short.
- **Option A nets:**
  - Wide VM lane groups of 17,792 b each: group A chains VM -> SU -> SFU -> HC (SW), group B covers quant | VM | CP.
  - ATT record broadcast: 1,250 b to each quadrant root tile.
  - CP <-> MTP ports: 120 b.
  - f_mtp 517 / t_mtp 197 reserved.
  - Loader host port h widened by +150 out / +125 in, to the host interface.
- **Channels:**
  - svc -> SM gap: 129.6 -> 345.6 um.
  - SM row channels: 520 -> 1,209.6 um and 259 -> 561.6 um.
  - SM -> hub edge channel: 551 -> 648 um.
  - Inner SM column channels: 259 -> 432 um.
  - Spine side channels: 1,244 -> 1,546.6 um.
  - SM group east strip: 264 -> 605 um.

Files: the `r25gq_*` / `r25gph_*` `floorplan.{png,svg}`, the `congestion.png` heat maps, `floorplan.json` / `.def`, `power_*.json` and `summary.json`.
