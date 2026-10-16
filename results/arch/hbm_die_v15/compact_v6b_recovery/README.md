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
| New/reshaped reserves | 21.6304 mm2 | XC32 500x1200, SMW4 216x1100, sucx4 600x600, cij_SW 200x200 |
| Reserves plus plan overlaps / outside | 0 / 0 | Lower-bound windows; mapped physical fit open |
| Default v5 reproduction | Exact; zero differing blocks | Current planner vs compact660_v5 |

The original four LK_N/scorer halo flags were a sub-nanometre rounding error
against the exact 20 um separation. The northern scorer stack now has 0.001 um
extra margin. No channel-capacity or timing gate changed.

`recovery.json` binds source ports and hashes for XC, SMW and cij to af261fbcb;
sucx/sfus bind the recovered uncommitted source hashes in the named suport tree.
The corrected-window overlay is `corrected.P.json` and `corrected_windows.png`.
It reshapes sucx to 600x600 and cij_SW to 200x200 in the empty COLL stack; the
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
crossing the full band. cij now has a 200x200 preliminary footprint; its 4429bits fit within the necessary5000bit perimeter budget. The SFU store
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
