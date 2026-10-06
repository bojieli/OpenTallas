# OpenTallas Chip Explorer

An interactive single-file companion site for the three designs (Qwen3-8B ROM at 8K, the DeepSeek-V4.1 ROM array at 1M, and the HBM accelerator). It has six sections:

1. **Die floorplans:** drawn to scale from real block geometry. This comes first because the die is the core of each design.
2. **Animated token:** one decode token's data path, animated on the floorplan, with a speculation mode.
3. **Timing and closure:** a per-token latency breakdown, a block closure board, and the lever ladder.
4. **System array:** packages, dies, stages and links. Every array view lays itself out at its panel's width (a ResizeObserver redraws on resize), so the DeepSeek pipeline wraps as a serpentine and nothing scrolls sideways, at desktop or at 400 px. Links are drawn with a `--link` token stroke whose width scales with the link's bandwidth (`DATA.links`); hovering a link lights it and its endpoints, and flow dashes show traffic direction (static under `prefers-reduced-motion`).
5. **Rack:** ORv3 rack elevations drawn to scale (48 mm OpenU, 44 OU, 600 mm frame) with power shelves, trays, switch tier, busbar and liquid manifolds; the deployment's racks side by side with the token path (DS ROM) or switch uplinks (HBM); a to-scale tray plan; per-rack totals; link classes by distance. Hover a tray for its dies, click it for its plan, click a die to open it in the die section.
6. **Machine comparison.**

Published view: https://claude.ai/artifact/5nPT6Gbv82bWNaFrpigSTc (private; share from the page's Share menu).

## Build

    python3 tools/chip_explorer_build.py

This writes `site/chip_explorer/build/data.json` (git-ignored; the data is embedded in the page) and `site/chip_explorer/index.html`, which is the page to publish.

## Layout

- `src/head.html`, `src/body.html`, `src/app.js`: the page and its rendering code.
- `inputs/`: snapshots of data that were not yet on main when the site was built:
  - `geo.json`: Qwen ROM r17b and S81 block geometry, extracted by `tools/chip_explorer_extract_geo.py`.
  - `qwen_r17b/`: r17b IR, path STA and GRT summaries from branch `claude/qwen-die-rebuild-20261005`.
  - `qhbm_*.json`: the HBM Qwen die. It is now on main under `results/rtl/hbm_accel_qwen_die_floorplan_20261005/`.
  - `hbm_ds_ir.json`.
- Everything else is read from committed records under `results/`. The list is at the top of `tools/chip_explorer_build.py`.

## Replacing values with measured ones

Every value in `DATA` is `{v, unit, status, src}`, where `status` is one of measured / analytical / estimate / placeholder. The page's Data provenance drawer lists them all. To update the page:

1. Replace a snapshot in `inputs/`, or update the record under `results/`, or change the value's entry in the build script.
2. Rebuild.
3. Republish.

The rendering code does not need to change.

Rack data (`DATA.racks`, `DATA.links`) is assembled in `tools/chip_explorer_build.py`:
- frame, cable, power-shelf and cooling constants come from `results/arch/v41_rack.json`, the legacy 28-stage rack study;
- the DS ROM S81 racks, die counts, HBM stacks and hop classes come from `results/arch/dsrom_s81_rack_20261006/rack.json` (`tools/dsrom_s81_rack.py`);
- per-die power comes from the S81 full-die floorplan and the HBM die floorplan, and system power from `results/arch/energy_silicon_measured/energy_silicon.json`;
- link rates come from `results/rtl/dsrom_1m_allmeasured_20261004/links.json` and `configs/hardware/technology.json`; link latencies from `results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json`.

The S81 rack record resolves three conflicts the rack view exposed (CLAUDE DS-RACK, 2026-10-06):
- **Links.** Owner decision 2026-10-06: every link that leaves a package runs full RS(544,514) FEC (board, in-rack cable, rack to rack), for the DS ROM array and the HBM accelerator. Light FEC is not used anywhere; in-package UCIe keeps its own spec. The DS ROM stage hop, token return and TP4 collectives are re-measured in RTL on the full-FEC channel; each hop class adds only its cable flight beyond the 0.3 m inside the 209 ns channel. The packing puts two stages in a tray and runs the chain down R1 and up R2. That gives 40 board hops, 39 tray-to-tray hops and 1 rack crossing, the minimum for 81 stages at two a tray.
- **HBM stacks.** KV stacks are sized to need (scenario C). The 32 scan dies and the 12 head dies have 4 stacks each, the other 292 layer dies have 1, and the Engram table and draft dies have none: 468 stacks. The S81 die floorplan is the scan die. The power model's 452 is the same rule at 8 head dies.
- **Head and table dies.** The split is 12 head dies plus 36 Engram table dies, making 372 dies, plus 52 draft dies for 424 in total. Two older figures are stale: 8 + 36 from the C1 ledger, and 12 + 32 that this page showed earlier.

The HBM accelerator fits one rack; its packing is still built here (`build_racks`) and marked estimate.

Known stale inputs, to refresh when they land on main:
- Qwen ROM r17b. It is being rebuilt without the near-HBM row engines and with its clocks wired.
- The HBM DS die r14b. Its south SMs were mirrored, so its geometry and wire pricing will be redone.
- The S81 die. Its generator connectivity fix and the taller q-element slot are pending.
