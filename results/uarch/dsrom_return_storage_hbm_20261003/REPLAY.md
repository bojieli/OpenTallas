# Replay: dsrom_return_storage_hbm_20261003

Model only. It needs no GPU and runs no model inference.

```bash
python3 tools/dsrom_return_storage_hbm.py run       # ~2 min: raw.json on this checkout's unified model (merged origin/main, 32d865831+)
python3 tools/dsrom_return_storage_hbm.py compose   # seconds: model.json incl. scenario_c
# the first record (ad04a76d3) ran DSROM_MODEL_ROOT=<worktree at e634046fe>; that baseline was 2,563.7 / 2,680.6
```

## What `run` does

It runs `cons_v41_rom(58, 8, 36, …)` with the isopower history study's settings, once for each index-reader bandwidth of 4, 3, 2 and 1 stacks (750 B per cycle a stack) at 1M and at 200K.

## Checks

- **Baseline (2026-10-03 re-run, HEAD model):** 4 stacks give 2,535.5 tok/s at 1M and 2,649.7 at 200K. The 28.2 tok/s (4.34 µs) drop from e634046fe is the 32d865831 hub-edge wire: 57 stage hops × 75 ns = 4.27 µs (`model.json` `baseline_at_model.hop_check`). Scenario C then gives 2,489.9 at 1M.
- **Asserted in `compose`:**
  - the 138,469,120-bit formula, against the return audit;
  - the NP 4096 figure, against the r4 budget;
  - the shard bits;
  - the 924.29 mm² composition.
- **Pinned records:** the git sha and sha256 of each are in `model.json` under `pins`.
