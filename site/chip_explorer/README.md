# OpenTallas Chip Explorer

An interactive single-file companion site for the three designs (Qwen3-8B ROM at 8K, the DeepSeek-V4.1 ROM array at 1M, and the HBM accelerator). It has six sections:

1. **Die floorplans:** drawn to scale from real block geometry (first, the core of the design).
2. **Animated token:** one decode token on the floorplan.
3. **Timing and closure.**
4. **System array:** packages, dies, stages and links. Every array view lays itself out at its panel's width (a ResizeObserver redraws on resize), so the DeepSeek pipeline wraps as a serpentine and nothing scrolls sideways, at desktop or at 400 px. Links are drawn with a `--link` token stroke whose width scales with the link's bandwidth (`DATA.links`); hovering a link lights it and its endpoints, and flow dashes show traffic direction (static under `prefers-reduced-motion`).
2. **Rack:** ORv3 rack elevations drawn to scale (48 mm OpenU, 44 OU, 600 mm frame) with power shelves, trays, switch tier, busbar and liquid manifolds; the deployment's racks side by side with the token path (DS ROM) or switch uplinks (HBM); a to-scale tray plan; per-rack totals; link classes by distance. Hover a tray for its dies, click it for its plan, click a die to open it in the die section.
3. **Die floorplans:** drawn to scale from real block geometry.
4. **Animated token:** one decode token's data path, animated on the floorplan, with a speculation mode.
5. **Timing and closure:** a per-token latency breakdown, a block closure board, and the lever ladder.
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
- S81 die counts come from `results/uarch/dsrom_c_recheck_20261004/model.json`, and the 52 added draft dies from the DP1-EP5 draft record;
- per-die power comes from the S81 full-die floorplan and the HBM die floorplan, and system power from `results/arch/energy_silicon_measured/energy_silicon.json`;
- link rates come from `results/rtl/dsrom_1m_allmeasured_20261004/links.json` and `configs/hardware/technology.json`.

No committed S81 or HBM-accelerator rack design exists yet. The build packs trays into racks itself (`build_racks`), and those values are marked estimate. Replace them when a rack record lands.

Known stale inputs, to refresh when they land on main:
- Qwen ROM r17b. It is being rebuilt without the near-HBM row engines and with its clocks wired.
- The HBM DS die r14b. Its south SMs were mirrored, so its geometry and wire pricing will be redone.
- The S81 die. Its generator connectivity fix and the taller q-element slot are pending.
