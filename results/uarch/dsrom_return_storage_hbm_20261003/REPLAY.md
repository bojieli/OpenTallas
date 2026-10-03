# Replay: dsrom_return_storage_hbm_20261003

Model only. It needs no GPU and runs no model inference.

```bash
git -C /home/ubuntu/OpenTallas worktree add --detach /tmp/pin-e634 e634046fe   # model the isopower study pinned
DSROM_MODEL_ROOT=/tmp/pin-e634 python3 tools/dsrom_return_storage_hbm.py run      # ~2 min: raw.json
python3 tools/dsrom_return_storage_hbm.py compose                                 # seconds: model.json
```

## What `run` does

It runs `cons_v41_rom(58, 8, 36, …)` with the isopower history study's settings, once for each index-reader bandwidth of 4, 3, 2 and 1 stacks (750 B per cycle a stack) at 1M and at 200K.

## Checks

- **Baseline:** 4 stacks must reproduce 2,563.7 tok/s at 1M and 2,680.6 at 200K.
- **Asserted in `compose`:**
  - the 138,469,120-bit formula, against the return audit;
  - the NP 4096 figure, against the r4 budget;
  - the shard bits;
  - the 924.29 mm² composition.
- **Pinned records:** the git sha and sha256 of each are in `model.json` under `pins`.
