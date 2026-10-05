# Replay: ROM vs HBM model sweep (2026-10-03)

There is no inference and no weight download. Step 1 needs network access to huggingface.co, for config.json, the safetensors index and the shard headers by HTTP range read. Step 2 is offline.

```bash
# 1. Header-only profiles (pinned revisions in tools/rom_model_sweep_profile.py MODELS).
#    --v41-anchor writes the DeepSeek-V4.1 anchor offline from configs/models/candidates/deepseek-v4.1-flash.json
#    and data/inventory/deepseek-v4.1-flash.json.
PYTHONPATH=src python3 tools/rom_model_sweep_profile.py --cache-dir <scratch>/hfcache --v41-anchor
git diff --exit-code configs/models/candidates/rom_sweep/      # profiles reproduce byte for byte

# 2. The sweep: writes sweep.json and tables.md here; asserts the Qwen calibration identities
python3 tools/rom_model_sweep.py
git diff --exit-code results/uarch/rom_model_sweep_20261003/    # deterministic output

# 3. Stack-area sensitivity (README caveat): write to scratch, not into the tree
python3 tools/rom_model_sweep.py --stack-mm2 1000 --out <scratch>/s1000/sweep.json
python3 tools/rom_model_sweep.py --stack-mm2 1300 --out <scratch>/s1300/sweep.json
```

## Inputs

The source hashes are in `sweep.json` under `sources`. The inputs are:

- `results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json`: the body cycles, attention terms and non-layer cycles. Its headline token is 229,158 cycles.
- `results/rtl/w15_collectives.json`: the UCIe TP-2 all-reduce (71 cycles), the board collective fit and the hop latency.
- `configs/hardware/technology.json`: the energy and idle-power constants.
- Constants restated from `tools/uarch_model.py`, each with its line comment:
  - `QWEN_AREA.array_mm2`;
  - `qwen_rom_area_per_group_mm2`;
  - the 75 Mbit/mm² density rule;
  - `HBM_STACK_B` and `HBM_CAP_EFF`;
  - the 0.9 TB/s stack rate;
  - the right-sized 340.5 mm² HBM die;
  - the Qwen ROM and HBM static ledgers in `results/uarch/economics.json`.

## HF repositories (license; profiled revision)

The pinned revision for each model is in `tools/rom_model_sweep_profile.py` and in each profile. The gated originals were profiled from ungated mirrors:

- `meta-llama/Llama-3.3-70B-Instruct` via `unsloth/Llama-3.3-70B-Instruct`;
- `meta-llama/Llama-4-Scout-17B-16E-Instruct` via `unsloth/Llama-4-Scout-17B-16E-Instruct`;
- `google/gemma-3-27b-it` via `unsloth/gemma-3-27b-it`.

The drafter repositories in the profiles were found through the HF model search API on 2026-10-03. None was downloaded or run.
