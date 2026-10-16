# Wider SU band with side-upper SFU store: unadopted physical study

This 813.0 mm² alternative adds 500 µm to each SU band, preserving the actual
7200 × 1800 SM frames and 330.48-square qcore reserve. Outline is
32990 × 24643.831 µm, within the existing reticle dimensions. Area rises
33.0 mm² (4.23%) from the 780 mm² diagnostic. This is a geometry comparison,
not an adopted die contract or a measured token-cost acceptance.

The known hard-frame cut through SU group1 improves from 0.731897 to 0.250386:
2,676 actual source-derived data bits now have 760 µm total channel at the
established 14.0625 tracks/µm supply. This excludes other traffic, clock roots,
reset glue, actual programme 474-macro candidate homes, SKV and collective homes.
Those exclusions remain mandatory blockers to whole-SU capacity qualification.
The older aggregate graph score (V0.493/H0.566, weighted stages8.871) is historical
and cannot substitute for a complete source-bound cut.

The SFU store moves into the free side-upper bay, SW x6599.4/y7258.21, with exact
mirrored homes in other quarters. It remains adjacent to the core corner at a
43.2 µm rectangle gap, while exposing the north core boundary for the wide LG
links. The old store directly overhead obstructed this escape. Actual core/store
peer pins, macro fit, registered boundary timing and clock delivery remain open.
No inherited SFU view is overlaid on this new geometry.

The complete plan has zero rectangle overlaps/outside/fixed-return violations.
The sixteen RF geometric routes need at most34 stages at480 µm; retain the actual
production36. All576 standard48 footprints fit without hard-block intersections,
max centre hop467 µm. Actual qcore endpoint views and64 internal RF commit paths,
per-bit native arcs/route lengths and clocks remain mandatory. The qcore source
must retain all76,220 actual native flops, including all six RF replicas.

The R23 SFU comparison needs736 stations, each thirteen actual48-bit leaves
(9,568 total), plus15 new reset flops per station (11,040 total). No reset-glue
physical master or complete station placement has been qualified. The long SFU
result-to-SUCX return requires explicit new fixed stages and compiler availability;
those stages do not exist in stable source. No current source snapshot was changed.

Personally inspected figures: sfu_barrier_cuts.png shows the widened green
channels and side-upper store; rf_centre_allocation.png shows RF paths in the
band and central gaps. Both are geometric witnesses only. Programme partition
remains coordinator-owned and is not silently charged to this free corridor.

Reproduce:

```sh
python3 tools/hbm_die_v15/compact_plan.py --area 813 --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --sfu-store-side --band 3391.92 --su-w 1797.12 --su-h 2671.92 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --carry --out results/arch/hbm_die_v15/core4_sfu2_wide
python3 tools/hbm_die_v15/v6_eval.py results/arch/hbm_die_v15/core4_sfu2_wide --slack 1200
python3 tools/hbm_die_v15/rf_centre_routes.py results/arch/hbm_die_v15/core4_sfu2_wide
python3 tools/hbm_die_v15/rf_centre_allocate.py results/arch/hbm_die_v15/core4_sfu2_wide
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan results/arch/hbm_die_v15/core4_sfu2_wide --out results/arch/hbm_die_v15/core4_sfu2_wide/sfu_barrier_cuts.json
```
