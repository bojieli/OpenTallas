# Replay: dsrom_isopower_history_20261003

This study is model only. It needs no GPU and runs no model inference.

```bash
git checkout claude/dsrom-isopower-history-20261003
python3 tools/dsrom_isopower_history.py run       # ~5.5 min: writes raw.json
python3 tools/dsrom_isopower_history.py compose   # seconds: writes model.json
```

## What `run` does

- It executes `tools/uarch_model.py` (sha256 2da5b6d9…, unmodified) as follows:
  - `cons_v41_rom(58, 8, 36, …)` with the S58 selection's settings, copied from `tools/dsrom_4096_partition_token_options.py`. It must reproduce AR 2,563.7 tok/s at 1M and 2,680.6 at 200K.
  - For m = 1..6, it monkeypatches `_cons_adjust` so that, for P > 1 only, each field node's issue is multiplied by ⌈P/m⌉/P and the graph is re-solved.
  - It captures `_cons_cooling` and `v41_die_static_parts` for the static ledger.
- It then runs `economics()`, `economics_levers()` and `v41_hbm_n(96, 4, …, clock_hz=1.2e9)` at 1M and 200K.

## What `compose` uses

`compose` is plain arithmetic. Its constants are in the tool, each with its source:

| Constant | Source |
|---|---|
| C1 rates | abd77c4e1 `results/uarch/dsrom_parallelism_20261003/model.json` |
| HBM DSpark | d2aff19ef `results/speculative/v41_hbm_speculation_methods_20261003/v41_hbm_speculation_methods.json` |
| Qwen rows | `results/uarch/consolidation.json` |
| HBM pJ/bit and idle W | `configs/hardware/power_scenarios.json` memory |
| DRAM die area | public secondary source (121 mm²) |
| Base die area | ASSUMED |

## Checks

- `raw.json` rom 1048576/m1 `ar_tokens_s` == 2563.7 and 200000/m1 == 2680.6.
- `raw.json` hbm 1048576 `ar.saturated.aggregate_tokens_s` == 25292.7, which equals consolidation's equal-power row.
