# DIE-HEAD-21 HK2: plan_hk2 (HEAD kit plan with real SRAM macros)

COORD ruling 2026-10-28: plan_hk1 lists behavioural SRAM models as sources for serdes/mesh/ctl/host, and Yosys runs out of
memory on them. Put the SRAM macros in their place, and add the lep_pair hard cores to hd_lep0N.
Tool: `tools/s81_head/head_kit_macros_delta.py` (test: `test_head_kit_macros_delta.py`, 5 PASS). Rebuild: `gen_kits_hk2.sh OUT`.

Input plan_hk1 = results/head_kits_1_1028/plan_hk1.json.gz (sha256 of the unzipped file a9773915...).
SRAM census = `sram_census.json`: Yosys run (orfs:asap7lock, docker 48 GB cap, intel2) over the HK1 kit filelists, with
every SRAM model swapped for its `_bb.v`, then `hierarchy; proc; flatten; select -list t:<macro>`. The paths are the
flattened instance names that `macro_place.tcl` uses.

## Estimate (CHECKED: census from Yosys, sizes from LEF, placement checked against plan keepouts)

| type | SRAM | macro area um2 | + channels | outline um2 | placed | where |
|---|---|---|---|---|---|---|
| hd_serdes | 1 x 64x546 2c (178.6x81) + 1 x 32x546 (177.8x81) | 28,868 | 32,844 | 3.54 M (only the logic strip y<150 is free; the PHY domain is above) | Y | x1486-1881, y34.6-124.2, next to the S coll_o0 window |
| hd_mesh | 72 x 256x64 + 38 x 32x64 (2 lanes x 55) | 124,005 | 199,951 | 1.77 M | Y | lane u_la: under the N coll window; lane u_lb: next to the W coll window (x43-) |
| hd_ctl | 4 x 64x512 r2c2 (171.3x77.8) | 53,294 | 60,942 | 1.77 M | Y | SW quadrant, x95-456 y112-380 |
| hd_host | 72 x 256x64 + 38 x 32x64 (2 lanes x 55) | 124,005 | 199,951 | 1.77 M | Y | lane0: next to the W coll window; lane1: above the S coll windows |
| hd_lep0N | 45 parent SRAM (LEP-C0, from main) + 4 lep_pair cores | - | - | 1.77 M | Y (SRAM) | main LEP-C0 floorplan |

Each mesh/host lane has 36 big + 19 small SRAM, the same set as the LEP pair child. It is laid out in that child's column
pattern on the 8.64-um lattice (column pitch 51.84, big row pitch 51.84, small row pitch 25.92). The block slides along
its window face and stays as close to the window as the keepouts allow. The keepouts are: landing bands, reserved
die-clock sites and islands (+8.64); strap and landing-pin points (+4.32); a 34.56-um boundary strip in front of every
bus window; and PHY PG domains. Reset local taps that a macro blocked moved to the nearest free 4.32 site: mesh 4,
host 4, lep0N 6 (see `report.json`).

## Plan form

- Nested SRAM go in `hard_cores[]` in the S81 form: lef, lib, origin on the 8.64 lattice, track_offset [0.108, 0.012],
  obs_max M4, pins_file `core_pins/<m>.json` built from the LEF. They are not `contents[]`, because gen_rtl instantiates
  every contents entry in the wrapper ("unbound ports"). The same problem affects the LEP-C0 hd_lep0N on main: its 45
  SRAM `contents` cannot be kit-generated, so they were converted too (42 snapped to the lattice, 0 clashes).
- The behavioural `<m>.v` sources are replaced by `<m>_bb.v`. This includes the ctl 32x64/256x64 models, which ctl lists
  but never instantiates. `core_pg_connect: true` is set on all 5 types.
- hd_lep0N: outline, module and sources are identical in hk1 and main. The tool copies u_core PAIR=1, the 4 lep_pair
  hard_cores (pins_file re-pointed), core_pg_connect and main reset taps. Reconciled with the one-entry plan_hk1:
  - g_pp[1] and g_pp[2] (at x8.64) sat on the new W landing bands coll_i1/coll_i2, so they moved +34.56 to x43.2.
  - g_pp[3] (at x1028.16, mirrored) overlaps the E bands coll_i3/lepk_i0. No lattice shift is legal: the clock island at
    x1007-1016 is on the west and the bands are on the east, which leaves 367 um, less than the 388.8-um child.
    **UNRESOLVED**: the core is left in place and reported. It has no view, so kits do not place it yet.
  - 2 u_land SRAM (g_t[3], g_t[4]) moved off the reserved die-clock site, to y665 and y717.
- hd_tile pins_file (`../../wt/codex-head-die-1028-0405/...`, which does not resolve) re-pointed to the repo copy
  (same sha).

## Validation (CHECKED)

- G0C (`check.py --completeness`, core_conns): FAIL, 16 ERRORs, all `insertion_target` (one-entry 450 vs 250), the same
  as plan_hk1. plan_hk1 had 26 ERRORs; the 10 hd_tile pins_file errors are now fixed. There are 0 hard_cores or track
  errors for the 271 new hard cores. There is a new WARN only: core_faces (connectivity unknown) x6.
- `gen.py phys --clock-landing --trial` for the 5 types, then kit_preflight:
  - PASS: serdes, mesh, ctl, host.
  - **FAIL: lep0N** (module_closure: `ot_s81hd_lep_pair` has no view or `_bb`; it needs the PAIR child kit, and
    plan_hk1 failed the same way).
  - The kits have 2 / 110 / 4 / 110 / 45 `place_macro` lines and no behavioural SRAM sources left.
- All renders `png/<type>.png` were viewed. No place/route was launched.
