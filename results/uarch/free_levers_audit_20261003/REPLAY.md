# Replay: free-levers audit (2026-10-03)

Source: branch `claude/free-levers-audit-20261003`, based on main `298ba9d79`. The bench ran on `ot-agidock128` (Verilator 5.050, `~/.local/opentallas-tools/verilator-5.050`) from an rsync copy of `tools/ rtl/ configs/ physical/asap7_memory_macros/ot_rom_8192x274_m8/` at that commit.

## 1. Mini checkpoint (local; the host does not hold the 476 GB snapshot)

```
python3 results/uarch/free_levers_audit_20261003/bench/make_mini_snapshot.py \
    --snapshot ~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277 \
    --out $SCRATCH/mini
```

The tensor bytes are copied verbatim. Their sha256 pins are in `measured/mini_snapshot_tensor_pins.json`.

## 2. Phase-merge A/B on the flat W17-runtime field RTL

```
python3 results/uarch/free_levers_audit_20261003/bench/phase_merge_flat.py --snapshot $SCRATCH/mini \
    --workdir $W/work_rt --result measured/phase_merge_flat_bst2.json            # BST 2 (the gate's)
python3 results/uarch/free_levers_audit_20261003/bench/phase_merge_flat.py --snapshot $SCRATCH/mini \
    --workdir $W/work_rt17 --bst 17 --result measured/phase_merge_flat_bst17.json  # BST 17 (the routed die)
```

- Each run takes about 25 minutes, most of it the `build_flat` compile. The simulation takes seconds.
- Model: `rtl/w17_runtime/v41die/ot_v41_fieldtop`, with NP 16, R 4, NBF 8, PHW 4 and VAW 16.
- The phases, images and golden are those of `tools/w17_runtime_v41_field_rt_gate.py` and `tools/w17_runtime_v41_die_images.py`.
- The harness `bench/flat_bench.cpp` drives the same ops protocol as the gate's host.

## 3. Pricing

```
python3 results/uarch/free_levers_audit_20261003/bench/price.py   # -> free_levers_audit.json
```

The basis is `results/uarch/v41_rom.json` design `proposal` at 1M (262.55 µs at 1.0339 GHz, 271,449 cycles). The 1% gate is 2,714 cycles.

## Not used, and why
- `tools/v41_field_rt_gate.py` (legacy `rtl/v41die`) fails at HEAD:
  1. `MODMISSING ot_hdc_cg`.
  2. With that module added, its unchanged phase list fails the composition-vs-flat check at tick 252 (`port=o_data`).
  3. The legacy flat RTL writes wrong addresses and values.
- Its record pins match commit `e9bd212f9`, which predates `541ef17eb`/`01855c929`, the commits that restored the pinned originals.
- The runtime variant was used instead.
