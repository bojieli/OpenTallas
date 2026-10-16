> **UNIT CORRECTION (2026-10-16):** The 0.52 mm2 SRAM figure is TOTAL across all32XC, not perXC. EachXC has one1024x256 macro174.744x70.488 and one128x256 macro94.824x41.064:0.016206mm2 macro area. With20umouter/intermacro channels, stacked lowerbound214.744x171.552um. The historical500x1200(.60mm2) reserves below are conservative unused-space experiments, NOT measured area requirements and NOT justification for die growth. Actual216x216XC native kit/fit is now owned by xc_physical with explicit local SM home x3788.64,y1343.52; it remains unqualified until actual synthesis/gate/native proof.

# Interrupted v6b adoption recovery

Status: **FAIL CLOSED; active v15 grants unchanged.**

The committed `v6_plan_1016/v6b` study is 770.4 mm2, SM 7050 x 1780,
SU 1790 x 2681.6. The interrupted worker subsequently used SM 7200 x 1800,
SU 1797.12 x 2671.92, a mid-band quarter core, mirrored eastern slices,
and an SFU core/store beside the hub. That is a different 780.0 mm2 candidate,
32990 x 23643.528 um. These two candidates must not be conflated.

Recovered measurements:

| Evidence | Result | Scope |
|---|---:|---|
| Plan overlaps / outside | 0 / 0 | Existing graph plus sucx/sfus/cij draft windows |
| Fixed LG/QUANT return violations | 0 | NW QUANT moved beside its bank pair |
| Lane cuts V / H | 0.410 / 0.550 | Existing graph only; no new join edges |
| Bit-weighted relay stages | 8.537 | Existing pin/lane model, reach 480 um; v5 7.47 |
| RF route model maximum | 66 stages | Previously adopted production RF_RELAY is 36 |
| New/reshaped reserves | 22.296 mm2 | XC32 500x1200, SMW4 216x1100, sucx4 720x720, cij_SW 200x360 |
| Reserves plus plan overlaps / outside | 0 / 0 | Lower-bound windows; mapped physical fit open |
| Default v5 reproduction | Exact; zero differing blocks | Current planner vs compact660_v5 |

The original four LK_N/scorer halo flags were a sub-nanometre rounding error
against the exact 20 um separation. The northern scorer stack now has 0.001 um
extra margin. No channel-capacity or timing gate changed.

`recovery.json` binds source ports and hashes for XC, SMW and cij to af261fbcb;
sucx/sfus bind the recovered uncommitted source hashes in the named suport tree.
The corrected-window overlay is `corrected.P.json` and `corrected_windows.png`.
It reshapes sucx to 720x720 and cij_SW to 200x360 in the empty COLL stack; the
SMW window moves beside sucx. The corrected overlay has zero overlaps/outside
and passes the necessary total-perimeter capacity test for all45 source-bound
new masters. Exact face assignment and full incident graphs remain OPEN.

Those source prerequisites remain pending native proof and commit. Every new
window explicitly has no physical view. Existing cut and stage figures omit all
45 new masters' incident connections, listed explicitly in the report.

Two inherited windows were mathematically impossible at the existing 0.096 um
pitch and 0.60 face utilization, even before assigning ports to incident faces:

| Window | Actual port bits | All-face perimeter capacity |
|---|---:|---:|
| sucx 216 x 194.4 | 13225 | 5129 |
| cij_SW 43.2 x 138.24 | 4429 | 2267 |

The four sucx instances now have larger preliminary windows; a distributed structure remains preferable if incident-face budgets fail. The suport source
owner agrees a 600 x 600 lower-bound reserve still needs actual face proof, and
four local slice-facing capture/store leaves may avoid the two 4096-bit buses
crossing the full band. cij now has a 200x360 preliminary footprint; its IDX interface uses the longer east face. The SFU store
has 1859 port bits against a 16105-bit perimeter capacity; this passes only the
necessary perimeter test, not mapped fit or timing.

The source-independent rectangle gap from sucx to its four slices is
approximately 3.15, 0.292, 0.834, 3.69 mm (NW up to 3.79 mm). These are lower
bounds, not actual source-pin reach. The draft RQ/RQC/SD zero and INJ_RET 11 must
not be assumed legal. COLL/cx and SFU-store/core gaps are 21.6 um before pin
placement. Actual fixed-calendar relay depths, buffer capacity and total token
cost remain unmeasured.

The old translation-based grant rehome also fails: host_N outside; five overlaps
(hc_eng/hub plus four calendars/hubs); twelve old RF paths with homes in hard
footprints. `grant_audit.json` records these exact failures. The rehome tool now
refuses active writes when its geometry audit fails and permits an explicit
diagnostic `--out`. This proposal is not evidence of a real-view die trial.

Reproduce from the worker branch:

```sh
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 2 --sfu-at-hub --mirror-east --band 2891.92 --su-w 1797.12 --su-h 2671.92 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --out results/arch/hbm_die_v15/compact_v6b_recovery
python3 tools/hbm_die_v15/v6_eval.py results/arch/hbm_die_v15/compact_v6b_recovery --slack 600
python3 tools/hbm_die_v15/su_rf_route_pins.py --plan results/arch/hbm_die_v15/compact_v6b_recovery
python3 tools/hbm_die_v15/recovery_v6b.py --plan results/arch/hbm_die_v15/compact_v6b_recovery
python3 tools/hbm_die_v15/rehome_v6.py --plan results/arch/hbm_die_v15/compact_v6b_recovery --dry-run
```

Next: partition/reshape sucx and cij from actual ports; add their complete graph
edges; repair explicit calendar/HC/host homes and route every RF path around all
hard blocks; recompile actual relay deadlines and measure total token cost;
then adopt grants and build a new real-view die case. No EPYC1 job was submitted.

Visual inspection performed with the image tool on `layout/die_floorplan.png`
and `corrected_windows.png`: the16unused HC/SFU group regions support32XC
reserves and the COLL stack has room for the enlarged sucx/cij plus narrow SMW.
The die still has long quarter-core/RF paths and sparse centre-channel access;
these images establish placement geometry only.


Source-bound per-face successor (`join_faces.json`): sucx now assigns4136bits
on each side to its two incident slices,4050bits on the COLL-facing face, and
903bits on the remaining face. Utilizations are0.55147,0.54000,0.12040, below0.60.
The smaller600x600 suggestion fails actual side-face incidence and was enlarged.
cij uses E2184/360um=0.5824, S1218/200um=0.58464, N1024/200um=0.49152;
its clock/reset/fault use W. Every source port bit is assigned once and all
centres lie on0.012+0.048k tracks. PG stripe clearance and peer pin agreement
remain open; these are not qualified production pins.

`join_edges.json` recovers824incident edges (600from af261fbcb,224from the
source-hashed recovered SU spec). All45new masters have incidence. Missing
physical homes remain explicit for su_prog (16edges) and subr4 reset sources.
Other non-leaf peer mappings state their scope; a parent rectangle is not an
exact source pin. These824edges must replace the old aggregate graph edges
appropriately before the full pin-cut claim can be updated.

XC identity is now assigned by an exact minimax matching to actual SM consumers
across each quarter's eight free windows, minimizing worst gap then total gap.
This lowers worst XC-to-own-SM gap from9630.08to3430.08um (relay lower bound
20to7 at480um), without moving a rectangle. Corresponding SW row-pair gaps are
3430.08/1610.08/121.84/1941.84um; lower-bound stages7/3/0/4.
The preferred structural alternative is an explicit XC child inside its own
SM hierarchical frame near command capture, with the long low-rate programme
load connection. This needs H-SM's actual parent placement/view grant; a child
cannot silently occupy the current SM hard abstract. The band plan is a
geometrically legal fallback, not the selected production implementation.

Reproduce the source-bound additions after recovery_v6b.py:

```sh
python3 tools/hbm_die_v15/join_face_assignment.py results/arch/hbm_die_v15/compact_v6b_recovery
python3 tools/hbm_die_v15/join_edge_audit.py results/arch/hbm_die_v15/compact_v6b_recovery
```

The updated corrected_windows.png was inspected with the image tool after
reshaping sucx/cij and reassigning XC identities; zero overlaps/outside remain.
