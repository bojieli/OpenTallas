# Qwen3-8B ROM full-die composition (near-HBM r2 frame): replay

Tool: `tools/qwen_rom_fulldie.py`. Inputs:

- `results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r2.json`, merged from `claude/qwen-rom-floorplan-nearhbm-20261003` @ ced04cd96.
- The v2 E/W HBM PHY abstract `physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy`.
- The snap library `physical/common/ot_macro_track_snap.tcl`, merged from `claude/macro-alignment-fix-20261003` @ 53487e07b.

All input digests are recorded in `floorplan.json` under `sources_sha256`.

## Floorplan (deliverable 1)

```
python3 tools/qwen_rom_fulldie.py plan     # floorplan.json/.svg/.def, domains.sdc, pdn.tcl
python3 tools/qwen_rom_fulldie.py clock    # clock_trunk.json (case d)
```

| File | Content |
|---|---|
| `floorplan.json` | Die and region rectangles, per-region PG coverage and power density, spine packing, instance counts, bus classes, clock domains, crossings |
| `floorplan.def` | All 3,218 instances FIXED; clock-domain REGIONS/GROUPS; partial placement blockages over the link channels |
| `domains.sdc` | Three clocks (0.833 / 1.111 / 1.024 ns) at 60/25 ps uncertainty; asynchronous groups; crossing list |
| `pdn.tcl` | pdngen M8/M9 straps per region at the r2 per-net coverages, as 0.48 µm stripes: tile field 4.41 %, strip/controller 16.7 %, hub/IO 2.5 % |
| `abstracts/elements_real.lef.gz` | Every generated element abstract with real ASAP7 pins on its facing edges |
| `abstracts/elements_k16.lef.gz` | The same abstracts in the bundled k = 16 view used by case (b) |

## Feasibility cases (deliverable 2)

Each case is written locally and run on ot-epyc1tb in `openroad/orfs:asap7lock`. The runner is `tools/qwen_rom_fulldie_run_case.sh` (copied to the case root as `run_case.sh`) (it writes `<log>.exit/.start/.end`). The remote root is `/srv/opentallas-scratch/claude/qwen-fulldie/cases`.

```
python3 tools/qwen_rom_fulldie.py real --work W/a_real                       # (a) legality, track assert, pin_access
python3 tools/qwen_rom_fulldie.py grt  --work W/b_k16 --k 16                 # (b) bundled GRT, central tree top
python3 tools/qwen_rom_fulldie.py grt  --work W/b_k32 --k 32 --tag k32
python3 tools/qwen_rom_fulldie.py grt  --work W/b_k16_banded --k 16 --tree banded --tag banded
python3 tools/qwen_rom_fulldie.py ir   --work W/c_<win> --window tile_field|shoreline_w|spine_hub   # (c) PSM
run_case.sh <case> run.tcl run.log <cpus> <mem_gb>
```

Results are recorded in `feasibility.json` and summarised in `README.md` as they land.
