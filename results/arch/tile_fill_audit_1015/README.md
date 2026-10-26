# Tile fill audit, 2026-10-15 (TILE-FILL)

**Question (owner).** `qfd_tile_nk` is only about 27 % filled: 83 macros sit in a tight cluster with channels under
20 um, and the rest of a 449 x 1,443 um slot is empty. Do S81, HBM and the other Qwen die have the same problem,
with tiles that take far more area than their content needs because of bad internal geometry?

**Answer.** Yes, on three of the four dies, and each time in the dominant replicated tile:

| die | worst tile (instances) | outline, mm2/die | fill | whitespace, mm2/die | recoverable by re-pack, mm2/die | class |
|---|---|---|---|---|---|---|
| Qwen compute (840.7 mm2) | `qfd_tile_nk` + `qfd_tile_nl` (720 + 48) | 497.9 | 27.2 % | 361.8 | **211** keeping children (model) / 276 flattened; Q-TILE-REPACK a1 = **223.6** | c |
| HBM (660 mm2) | `hfd_sm` frame (32) | 362.1 | 19.5 % | 291 | **~150** (100-180) | c + b |
| S81 (858 mm2) | ROM field frames (128) | 538.6 | 46.1 % | 290.5 | **~52** without re-closing ROM masters; 90-95 with a 60 %-util re-harden | c + a |
| Qwen KV/system | none large (lane8 at 62 %) | 60.7 closed | 48 % | 31 | ~7 | a / b |

Classes: **a** = routing or channel space that is needed; **b** = the outline is pin-limited (bound by its perimeter,
not its area); **c** = bad internal arrangement or empty wrapper space around the children.

* JSON: `tile_fill_audit.json`. It has a `summary` per design, plus `per_die.<die>.rows`, one row per master. Each
  row gives the outline, real content, instance count, fill, the whitespace inside that master's own level,
  `channels.min_channel_um`, the pin bound, the re-pack targets and the class.
* Tools: `tools/tile_fill_audit_1015/scan_archive.py`, then `driver.py <index.json> <out.json>`; the core
  calculations are in `audit.py`.

## Method

* **Content** is raw ROM/SRAM macro area plus std-cell area, excluding fill and decap cells. It is summed over the
  whole hard-child subtree.
  * The std-cell area comes from the latest CLOSED view of each master in `/home/ubuntu/closed_archive`, 1,187
    elements. The source is the ORFS `finish__design__instance__area__stdcell` metric. Where a view has no metadata,
    the area is computed from the DEF components and the ASAP7 LEF cell sizes.
  * Hard children are read from `6_final.def` COMPONENTS.
* **Outline** is the die slot where a contract defines one:
  * S81: v21 GEN18 hier slots.
  * Qwen compute: CONTRACT.md sections 1 to 3.
  * KV: the v1.4.1 contract slots.
  * HBM: compact660_v5.

  Otherwise it is the LEF SIZE of the closed view.
* **Instance counts** come from the die port-binds:
  * S81: bind5, 78,109 instances.
  * Qwen compute: c13, 720 nk tiles plus 48 nl tiles.
  * KV: v1.4.1.
  * HBM: compact660_v5 and glue26d.

  Nested instances are counted by expanding each parent's DEF children.
* **Pin bound** uses the S-NET face rule: 0.12 um per pin on the N/S faces, 0.16 um per pin on the W/E faces, plus
  8.64 um.
* **Re-pack target** is a model, not a route. The rules:
  * Hard children: outline x 1.10.
  * Raw macros: area x 1.15 (abutted rows, a 20-um channel every second row).
  * Std cells: area / 0.50 utilisation.
  * The result is then raised to at least the pin-bound outline.
* Masters with no closed content are listed as unknown, not counted as waste.
  * S81 hub clusters: `sp_su_s`, `sp_hc_s/t`, `sp_vm`. Most of their children are unclosed.
  * Qwen spine slots: `su64_sfu`, VM, port tiles, `xcol`. 43.3 mm2.
  * KV strips and relays: 28.8 mm2.

## Qwen compute

* **`qfd_tile_nk` / `qfd_tile_nl`, 768 x 449.28 x 1,442.88 = 497.9 mm2 (59 % of the die), class c.**
  * Content: 177.6k um2 per nk tile, 167.9k per nl tile.
  * Each tile holds 14 hard children: 5 `ot_qwen_tile_rpair` (311.04 x 129.6), 8 `ot_qwen_tile_lsl_fp1`
    (99.79 x 140.4) and the node (47.52 x 432). Together they cover only 51.5 % of the slot. The channels between
    children are 21.6 um.
  * **239 mm2 per die of whitespace sits at the tile-parent level**, outside every child.
  * Recoverable: about 211 mm2 per die re-placing the closed children (model), or 276 mm2 flattened.
  * The Q-TILE-REPACK a1 plan is 457.92 x 779.76: RPH=1, the 10 ROM macros at tile level, a 3x3 lane grid. It is
    -45 %, or **223.6 mm2 per die**, at +1.9 % column width. The gate is pending (el1013-qwen-elements-r4.log
    19:45).
* **`ot_qwen_tile_rpair`, 3,840 nested, 45.4 % fill, 84.5 mm2 of whitespace inside the children, class c.**
  * It holds 2 ROM 4096x266 macros (15.3k um2) and 2.97k um2 of std cells in 311.04 x 129.6.
  * The N face carries 1,024 pins, which need only 131.5 um, so the 311-um width is not forced by pins. The macro
    channel is 21.6 um.
  * Recoverable: about 64 mm2 by re-packing, or all of it by flattening as in RPH=1.
* `ot_qwen_tile_lsl_fp1`: 65 % fill, class a. `ot_qwen_tile_node`: 46.5 % fill.
* Spine:
  * The `tt_ctlm` slot is 777.6 x 1,814.4, but the closed view is 475.2 x 475.2, so fill is 4 %. Slot slack is
    1.3 mm2.
  * The `sp_band_lanes` slot is 881 x 1,132; the closed q4 view is 388.8 x 583.2, so fill is 8 %. Slot slack is
    2.7 mm2.
  * `xcst_n/s`: 768 instances at 19 % fill, class b. 509 W pins fix the height at 90 um.

## HBM

The die plan, compact660_v5, gives slots of 535.17 mm2 inside the 660 mm2 die. The remaining 125 mm2 is die-level
channels, which are needed (a). The worst pin cut is 0.598.

* **`hfd_sm` frame, 32 x 6,609.6 x 1,712.08 = 362.1 mm2 (55 % of the die). Fill 19.5 % (2.21 mm2 of content per
  SM), 291 mm2 of whitespace.**
  * **Frame arrangement (c), 109 mm2.** The children's outlines cover only 7.90 of 11.32 mm2. The frame is an 8x2
    tile array with the front block shifted +292 um and 20-um clearances.
  * **Tile internal, 70 mm2.** The tiles are 693.44 x 609.92, and the group outlines fill 67.7 % of them.
    * The height is bound by the cut (b): 3,705 E-W bits on M8 at 0.16 um.
    * The width is not (c): about 370 of 693 um is enough. Narrowing the tiles is worth about 100 mm2 per die.
  * **Leaf internal, 83 mm2 (a/b).** xs is 55.8 % full, bdc 51.6 %, tct 51 %, tcl 54.4 %. The transport leaves
    `beat_w` and `row_w` are only 17.6 % and 22.8 % full.
  * **Front children, 29 mm2, pin-limited (b).** Fills: `front_n` 10.6 %, `front_s` 5.6 %, `fc_xl` 5.8 %,
    `pt_w` 7.7 %. Their faces need 462 to 593 um at 0.16 um per pin. Only moving pins to two layers or to other
    faces recovers this area.
  * Minimum macro channel: 21.4 um in xs, 20 um in the tile.
  * **Recoverable: about 150 mm2 per die** (100-180).
  * Source: git 62f2a4a7b on branch `codex/sm-dense-pack-1015` (not on main): `complete35.json`,
    `complete16.json`, `COMPLETE.txt`.
* **IDX scorers, 4 x 11.55 mm2, 45 % fill.**
  * Each holds 512 hslices at 57 % fill.
  * The hslice is near pin-bound (b): 2,304 N/S pins need 139 of 172.8 um.
  * Recoverable: about 6 mm2.
* **VM bank slots, 32 slots, 9.36 mm2, 24.5 % fill.**
  * The bank (356.4 x 365.04) holds one column of 3 SRAMs, each 174.7 x 70.5, with 20.25-um channels. About 91 um
    on each side is empty.
  * It is not pin-limited (it needs 133 x 133), so this is c.
  * Recoverable: about 4 mm2.
* HC shells and PC rows have unclosed contents. Their estimated slack is about 4 mm2 and 8-10 mm2.
* The SU slices total 35.6 mm2, with unknown fill.
* **HBM total recoverable: about 165-180 mm2 per die**, roughly a quarter of the 660 mm2 die.

## S81 (DeepSeek ROM)

* **ROM field frames, 128 frames, 538.6 mm2. Content 248.2 mm2, fill 46.1 %, 290.5 mm2 of whitespace.**
  * **Inside closed masters: 166.1 mm2.**
    * `ot_v41_rom_elem_q_qxpq_w10`: 1,898 instances, 510.84 x 221.4, 62.8 % fill, 79.8 mm2. Its 4 ROM 4096x274
      macros are abutted at 0.54 um, and the std cells sit at about 48.5 % utilisation (a).
    * `bf_col`: 1,038 instances, 57.5 % fill, 39.4 mm2 (a).
    * `dsfd_node_*`: 4,706 instances, 86.4 x 77.76, 22.5 % fill, 24.5 mm2 (c).
    * Others: `sstn` 7.1, `bf_front` 5.4, `cfg7_seq` 4.5, `cfifo` 3.7.
  * **At frame level, between masters: 124.4 mm2.**
    * Empty q lanes: 19.1 mm2. 106 frames with 19 pairs leave the R lane of their last q slot empty.
    * cfg bands: about 56 mm2. The q-slot bands are 53 % full and the BF-slot bands about 30 %.
    * The right x-relay lane takes 23.6 mm2 and is needed (a).
  * Minimum macro channel: 8.6 um (ROM72 to ROM72 in the cfg band) and 9.3 um (elem to elem).
  * **Recoverable: about 52 mm2 per die without re-closing ROM masters.**
    * 20-pair frames, which also gain 92 pairs: 19.1 mm2.
    * The node strip narrowed from 86.4 to 43.2 um: 19.7 mm2. The node is sized by an area decision of 6,703 um2,
      but its content is 1,515 um2.
    * The BF cfg band re-slotted: 12.9 mm2.
    * Re-hardening qxpq and `bf_col` at 60 % utilisation adds a further 37-44 mm2, for a total of about 90-95 mm2.
  * Caveat: relay counts per slot are scaled from plan r8c, so the cfg-band figure is ±10 mm2.
* **Stations.**
  * `dsfd_stnv_566x1`, 814 instances at 77.76 x 36.72 (2.32 mm2), about 10 % fill.
    * The width is pin-bound at 76.6 um.
    * The 36.72-um depth only needs about 13 um (b+c). Recoverable: about 1.5 mm2.
  * `sstn_e0e1c0c1si` / `e0c0si`, 1,265 instances at 172.8 x 30.24, 11 % fill.
    * The pins span only 77.5 um of the 172.8-um width (c). Recoverable: about 5.2 mm2.
  * `cfg7_seq`, 2,417 instances at 10 % fill.
    * The height is pin-bound by 355 W pins.
    * About 16 um of width would be enough (b+c). Recoverable: about 2.8 mm2.
  * Relays `dsfd_rly_*`, 15.12 x 15.12, about 20k instances at 33 % fill.
    * Pin-bound (b). Recoverable: under 0.6 mm2.
* **Hub.** Content cannot be measured yet because most cluster children are unclosed. Child-outline coverage:

  | cluster | coverage |
  |---|---|
  | `su_s` | 65 % |
  | `hc_s` | 92.5 % |
  | `hc_t` | 88.7 % |
  | `vm` | 94 % |
  | `collective` | 50 % |

  * The closed `hc_cth` stripes (`ctrn`/`ctfx`/`ctfn`/`ctfs`) are 13 to 33 % full and carry 2-3k pins per face.
    They are thin (13-26 um), so the absolute waste is small.
  * The hub's 82.6 mm2 of roads is die-level routing, not tile fill.

## Qwen KV/system

There is no large offender here.

* `ot_qkh_lane8`, 2,048 instances: 62 % fill (a).
* `qkd_ctrl_pc`: 24 % fill. The height is pin-bound by 1,169 W pins (b+c). Recoverable: 2.8 mm2.
* `qkd_kvwq_leaf_s_w129_m`: 5 % fill (c). Recoverable: 2.7 mm2.
* The head leaves (b) offer 2.2 mm2.
* Total recoverable: about 7 mm2.

## Recommended order

1. **Qwen compute:** run the `qfd_tile_nk` RPH=1 re-pack (a1/a2/b1 gates are in flight, Q-TILE-REPACK). It is worth
   about 224 mm2 per die. The same cure applies to `rpair`: flatten it, do not re-close it.
2. **HBM:** re-pack the `hfd_sm` frame: narrow the tiles toward about 370 um and place the front block abutted. It
   is worth about 150 mm2. The front children need two-layer or other-face pin plans, because they are b.
3. **S81:**
   * Use 20-pair frames and the 43.2-um node strip in the next canonical field. This is worth about 39 mm2 and
     needs no ROM re-close.
   * Re-slot the BF cfg band: 12.9 mm2.
   * Re-hardening qxpq/`bf_col` (+37-44 mm2) is optional.

Analysis only: no route jobs were launched.
