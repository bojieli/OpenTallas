# Wider SU band with side-upper SFU store: unadopted physical study

This 813.0 mm² alternative adds 500 µm to each SU band, preserving the actual
7200 × 1800 SM frames and 330.48-square qcore reserve. Outline is
32990 × 24643.831 µm, within the existing reticle dimensions. Area rises
33.0 mm² (4.23%) from the 780 mm² diagnostic. This is a geometry comparison,
not an adopted die contract or a measured token-cost acceptance.

The known hard-frame cut through SU group1 improves from 0.731897 to 0.250386:
2,676 actual source-derived data bits now have 760 µm total channel at the
established 14.0625 tracks/µm supply. This excludes other traffic, clock roots,
reset glue, actual programme 476-macro candidate homes, SKV and collective homes.
The actual RF36 programme candidate is 302 global macros becoming 476 local
macros (quarter counts98/141/101/136), +174 SRAMs/+0.67753 mm² macro area. The
frozen-S 301→474 count is historical and does not size this native alternative.
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

Source-pinned R23 station placement attempt:
`python3 tools/hbm_die_v15/sfu_lg_face_windows_1016.py` assigns all4,448 core
LG bits to four distinct partial N-face windows (utilization0.559233), matching
the actual local_rq/local_wq/local_rr/local_w_done ABI and peer ports. It keeps
all port base vectors on one face. Whole-core other ports, native endpoint
views/clock roots and PG legality remain open; these are proposals.
`python3 tools/hbm_die_v15/sfu_split48_footprints_1016.py` places the actual
13×21.6-square leaf shapes in each of736 stations, source419e476e9/physical
scalar14-clock ABId78d342fe. Three-column/five-row banks use distinct actual ABI escape centres, not a
shared core-centre proxy. Group3 return uses five-column/three-row banks and
moves turn stages19/20 together by86.4µm along the route. Independently staggered
turns and2.16µm-snapped footprints now place all9,568 leaf shapes with zero
rectangle conflicts, including against576 RF footprints and enlarged720-square
SUCX windows. The former139/70-conflict attempts are superseded by this concrete
escape and station-shape repair. All interior EW envelopes pass with43.2µm
pin allowance plus4.32µm snap allowance and explicit lateral-stub cost. Worst envelope is
414.55425µm against415.662µm native EW reach, only1.10775µm (~0.842ps)
planning margin. This thin estimate is not routed timing closure. Actual
per-bit obstacle-aware routes, clocks and endpoint views remain mandatory.
The736 station reset leaves (15FF each) are still unplaced/unqualified.
This proves only leaf footprint feasibility, not complete station qualification.

A separate balanced successor preserves the diagnostic above: run
`python3 tools/hbm_die_v15/balance_sfu_split48_1016.py`. Six explicit station
moves redistribute neighboring spacing without adding stages. Independent
final collision scan remains zero; worst EW envelope falls to397.27425µm,
18.38775µm (about13.975ps) below the measured415.662µm reach.
The before/after actual footprint image sfu_split48_balanced.png was personally
inspected; sfu_split48_balanced.json records every move and binds its input.
This improves geometric planning margin only. Actual endpoint views, routed
wire RC/cuts, source/leaf clock delivery, reset-leaf view/placement and actual
compiler cost still prevent native adoption. It does not resolve programme476,
SKV/collective homes, the connected eight-by-two SM roof/OBS/PG obligations or
new fixed-stage SFU result transport.
