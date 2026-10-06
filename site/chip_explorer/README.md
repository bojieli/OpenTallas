# OpenTallas Chip Explorer

An interactive single-file companion site for the three designs (Qwen3-8B ROM at 8K, the DeepSeek-V4.1 ROM array at 1M, and the HBM accelerator). It has five sections:

1. **System array:** packages, dies, stages and links.
2. **Die floorplans:** drawn to scale from real block geometry.
3. **Animated token:** one decode token's data path, animated on the floorplan, with a speculation mode.
4. **Timing and closure:** a per-token latency breakdown, a block closure board, and the lever ladder.
5. **Machine comparison.**

Published view: https://claude.ai/artifact/5nPT6Gbv82bWNaFrpigSTc (private; share from the page's Share menu).

## Build

    python3 tools/chip_explorer_build.py

This writes `site/chip_explorer/build/data.json` and `site/chip_explorer/index.html`, which is the page to publish.

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

Known stale inputs, to refresh when they land on main:
- Qwen ROM r17b. It is being rebuilt without the near-HBM row engines and with its clocks wired.
- The HBM DS die r14b. Its south SMs were mirrored, so its geometry and wire pricing will be redone.
- The S81 die. Its generator connectivity fix and the taller q-element slot are pending.
