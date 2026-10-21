# S81 head die H1: floorplan and unrouted plan (HD-FP, 10-21)

Die **15876 x 22636.8 um = 359.4 mm²**, inside the 26 x 33 mm reticle (858 mm²). This is larger than the spec's ~13 x 20.5 mm estimate because the outline was grown, not squeezed. The picture is `results/arch/s81_head_1021/h1/floorplan_h1.png` (+ `.svg`): routed wires and relay stations; tile labels give the bundle index, with `>` = flows E (R0) and `<` = flows W (MY).

## Regenerate

```
python3 tools/s81_dv/head72/hd_floorplan.py results/arch/s81_head_1021/h1/placement_h1.json [--tile 648 --chx 108 --chy 108 ...]
python3 tools/s81_dv/head72/hd_plan.py build results/arch/s81_head_1021/h1/placement_h1.json results/arch/s81_head_1021/h1/plan_unrouted_h1.json
python3 tools/s81_dv/dv_route72.py results/arch/s81_head_1021/h1/plan_unrouted_h1.json plan_routed_h1_raw.json
python3 tools/s81_dv/head72/hd_plan.py check plan_routed_h1_raw.json
python3 tools/s81_dv/head72/hd_plan.py cut   plan_routed_h1_raw.json cut_h1.json
python3 tools/s81_dv/head72/hd_plan.py draw  placement_h1.json plan_routed_h1_raw.json floorplan_h1.png
```

The tile outline is a parameter (`--tile`, `--tile-h`). An HD-TILE fallback outline only needs these commands re-run.

## Content

311 blocks:
- 253 `ot_s81hd_tile` (648 x 648) placed in 260 slots;
- 13 `ot_s81hd_spo` and 13 `ot_s81hd_spr` (216 x 648);
- `ot_s81hd_ctl` (1512 x 2592);
- `ot_s81hd_lep` (1296 x 2592);
- 13 `ot_s81hd_lane` (518.4 x 1123.2);
- 17 `ot_pdie_serdes` (518.4 x 3844.8).

There are 48 geometry-only `blockages`: the row channels inside the tile arrays (see below).

371 links, by class:width:

| Class | Width (b) | Links |
|---|---|---|
| chain | 565 | 224 |
| chain | 682 | 55 |
| spine | 682 | 28 |
| coll | 512 | 17 |
| coll | 562 | 17 |
| unit | 512 | 15 |
| unit | 562 | 15 |

## Spec reconciliation (lead decision needed)

Spec v1 s2 says "13 levels per half (N, S)". It also says 52 chains of <= 5 tiles a row (253 of 260 slots) and a die of ~13 x 20.5 mm. These cannot all hold:
- 13 levels per half with 10-tile row-pair chains is 520 slots and ~40 mm of height, over the reticle;
- 5-tile chains would need 52 rows, also ~40 mm.

H1 therefore builds **13 levels in total: N 7 + S 6**:
- 26 chains x 10 slots, so 13 spo + 13 spr nodes (not 26 + 26);
- the 7 empty slots are the return-row column-0 slot of the 7 outermost chains (N04W, N05W/E, N06W/E, S05W/E).

The tree is shallower than the spec model (spine <= 7 levels each way). HD-TILE's masters are unchanged.

## Geometry

- **Tile arrays:**
  - 5 columns x 26 rows per side, pitch 756 (108 channels).
  - W tiles on the out row are MY (flow W) and return-row tiles are R0; E is the mirror image.
  - U-turn in a 648 outer channel.
- **Spine:**
  - The spo lane (W) and the spr lane (E) are 216 wide, with 108 between them and 216 to each array.
  - spo_k sits on the out row of level k and spr_k on the return row, so spo.oe / spr.iw cross the other lane where it has no node.
  - S-half nodes are MX.
- **ctl:** in the band between the halves, centred on the spine. It is 2592 tall so each face has <= ~4 pins/um (E face 9 lanes x 1074 b).
- **SerDes:** column A has 5 slots on each edge (row street 799.2). Column B leaves row 2 (the ctl band height) open, and every core link crosses there.
  - W column A: HOST0, WN2, WN3, WN0, WN1. W column B: HOST1, DW0 | DW1.
  - E column A: M0..M4. E column B: DE0, M5 | DE1, DE2.
- **Lanes and lep:**
  - Each lane sits beside its SerDes, at the slot end nearest the band.
  - The lep is in the W A' column at band height, between pair B (WN2/WN3, below) and pair A (WN0/WN1, above).
- **Array guards:** geometry-only reserves over every row channel inside the two tile arrays, so die wires cannot use the arrays as a through-route.
  - dv_route72 sees them as obstacles; rvcase as a placement blockage plus an M1-M6 obstruction.
  - Chain links (W/E faces), U-turns and spine lanes are unaffected.
  - Without the guards, the router sent 1074-b core links down the 108-um array channels (first PNG review). With them, those links run in the outer channel and the band.

## Route (dv_route72, local, 0.2 s)

**0 routing failures.** 930 relay stations, **212,005 bit-mm**. The longest station-to-station hop is **396.5 um** (<= 405 everywhere); no over-reach.

| Class | Links | Stations | bit-mm |
|---|---|---|---|
| chain | 279 | 92 | 43,636 |
| spine | 28 | 54 | 16,175 |
| coll | 34 | 63 | 13,646 |
| unit (ctl <-> lane/lep) | 30 | 721 | 138,548 |

- Station widths: 682 x 146, 512 x 391, 562 x 393.
- The longest links are the ctl <-> lane core links: c_ln_mesh4_t/r at 12.9 mm with 36 stations, and host0 at 12.1 mm.
- All 224 exact-565 chain links (tile -> tile, spo.ow -> W head, E tail -> spr.ie) carry 0 stations and stay inside one region.
- Detail: `route_check_h1.json`. Routed copy: `plan_routed_h1_raw.json`. The chain run script re-routes from the unrouted plan.

## Cut analysis on the routed plan (`cut_h1.json`; 6.9 tracks/um/layer, vertical cuts 3 H layers, horizontal cuts 2 V layers)

| Cut | Bits | Tracks | Ratio |
|---|---|---|---|
| Vertical, full 22.6 mm (worst x = 12398) | 27,398 | 468,582 | 0.058 |
| Vertical, densest 648-um window (E outer channel, y 12031..) | 4,978 | 13,414 | **0.371** |
| Horizontal, full 15.9 mm (worst y = 8597) | 10,638 | 219,089 | 0.049 |
| Horizontal, densest 648-um window (x 8381.., y 11880) | 2,930 | 8,942 | 0.328 |

PASS: everything is <= 0.55.

## Open items for binding (HD-CHAIN)

1. **Placeholder widths.** The ctl <-> lane (512 / 562) and ctl <-> lep (2 x 512 + 2 x 562) core widths are placeholders: HD-CTL's ports.json was not on origin at build time. They are all in the table at the top of `hd_plan.py`; edit it and regenerate. The port names are plan names:
   - ctl: `<lane>_t/_r`, `lep_t<k>/lep_r<k>`, `sn_o/sn_i/ss_o/ss_i`;
   - lane: `core_i/core_o/tx/rx`;
   - lep: `core_i<k>/core_o<k>/tx0..3/rx0..3` (lep lane k <-> lk_WN<k>);
   - tile: `i/o`;
   - spo: `i/o/ow/oe`;
   - spr: `i/iw/ie/o`.
2. **Bus B lane width.** Bus B (565 b) rides 682-b lanes wherever a station or a region crossing exists (117 spare top bits, the dv_bind lane-quantisation rule). This is because dsfd_dvrlyh/dsfd_dvland exist only for 70/276/512/562/682 b. The alternative is new 565-b relay/land views.
   - 682 has no SN relay view (dv_station_dirs72 substitutes, as in G7).
   - 512 has EW/WE only.
3. **Orientations.** `facts.instance_orientations` (W/E tile MY, S spine MX) goes into the bind table's `instance_orientations`.
4. **Straps.** `facts.tile_straps.per_instance` gives `row0_by_rank` and `ten_by_rank` (rank bases 0 / 32384 / 64768 / 97024; bundle 252 has ten = 0 on ranks 2/3). The die-level strap mechanism (per-rank ROM code / die variant) is HD-CHAIN's choice.
5. **Regions.** group = clock region (`cl<H><L>W` = spo + W chain, `cl<H><L>E` = spr + E chain, clctl, cllep, cl_<lane>, SerDes edge). Land-plan rows are needed for every cross-region link:
   - the spine levels;
   - ctl <-> spine roots;
   - spo.oe -> E head, and W tail -> spr.iw;
   - the top spine U-turns;
   - all `unit` links.
6. **Spec.** The 13-level total (N 7 + S 6) needs to be confirmed in the spec (see above).
