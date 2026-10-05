# HBM comparator full-system RTL (reduced shape): replay

Branch `claude/hbm-system-rtl-20261003`. All RTL is new, under `rtl/gpu_sys/`, and default-off (`ENABLE = 0` drives every output to 0). No existing file is modified. Codex-owned bridge files are reused unmodified, or not used yet (see "Waiting on owners").

## What is built

| piece | file(s) | role |
|---|---|---|
| SIMT SM | `ot_gpu_simt_sm.sv`, `ot_gpu_simt_lane.sv`, `ot_gpu_simt_divlane.sv` | Runs the OTG-1 GPU ISA (`tools/gpu_sys/isa.py`). In-order issue with a scoreboard; 128 lanes; 256 vector and 16 uniform registers; the qualified FP32 add/mul pipes; integer/convert/shuffle ALU; 32 KiB shared memory; LSU with a sector coalescer. It wraps the existing exact tensor core `rtl/gpu/ot_gpu_sm.sv` and the TMA-style `rtl/gpu/ot_gpu_bulk_copy.sv`. Optional `div.rn`/`sqrt.rn` lanes (`HAS_DIV`). |
| command processor | `ot_gpu_cmdproc.sv` | Per-die front end. Walks the kernel-launch graph in stream order and posts the completion with the RESULT payload. |
| host bridge | `ot_gpu_host_bridge.sv` | Connects `rtl/host/ot_host_if.sv` (reused) to per-die doorbells and the completion join, plus the driver loader. All crossings use CDC FIFOs. |
| reset | `ot_gpu_reset_ctrl.sv` | Power-on reset: asynchronous assert, synchronised and ordered release per domain (mem/link, then SM, then host). |
| CDC | `ot_gpu_cdc_fifo.sv` (wraps `rtl/link/ot_link_afifo.sv`), `ot_gpu_mreq_cdc.sv` | Depths come from `tools/gpu_sys/cdc_sizing.py` and are measured. |
| memory | `ot_gpu_xbar.sv`, `ot_gpu_l2_slice.sv`, `ot_gpu_hbm_partition.sv`, `ot_gpu_memsys.sv` | Crossbar, 128 B-interleaved L2 slices, and HBM partitions around the timing-faithful `rtl/hdc/kv/ot_hdc_hbm_model.sv`. |
| collectives | `ot_gpu_coll_endpoint.sv`, `ot_gpu_coll_fabric.sv`, `ot_gpu_coll_mux.sv` | NVLS-style all-reduce and all-gather over die links into `rtl/link/ot_link_nvls_switch.sv` (reused). |
| system top | `ot_gpu_hbm_system.sv`, `ot_gpu_sys_glue.sv` | 2 dies × 2 SMs, 2 L2 slices plus 2 HBM partitions (2 pseudo-channels each) per die, 4 clock domains. |

Software stack (`tools/gpu_sys/`):
- `isa.py`: ISA reference semantics.
- `asm.py`: kernel builder and register allocation.
- `machine.py`: functional reference of the whole system.
- `qwen_hbm.py`: Qwen3 lowering, HBM images and emit.
- `v41_hbm.py`: DeepSeek-V4.1 lowering.
- `mem_image.py`: per-partition HBM images.

## Replay

```
# Python: functional machine vs golden (Qwen3 reduced, TP2, groups=256), all 16 prompt positions
python3 tools/gpu_sys/qwen_hbm.py --check --out results/rtl/hbm_system_rtl_20261003/qwen_functional.json

# unit gates
python3 tools/gpu_sys/run_simt_sm.py --cases 6 --out results/rtl/hbm_system_rtl_20261003/simt_sm.json
python3 tools/gpu_sys/run_cdc_fifo.py
python3 tools/gpu_sys/run_coll.py
python3 tools/gpu_sys/run_memsys.py
python3 tools/gpu_sys/run_unit_small.py --out results/rtl/hbm_system_rtl_20261003/unit_small.json

# end-to-end system RTL (Verilator 5.050), Qwen3 HBM comparator, reduced shape
python3 tools/gpu_sys/run_system.py --model qwen --out results/rtl/hbm_system_rtl_20261003/qwen_e2e.json
```

## Results

- Qwen3 HBM e2e: PASS. All 18 steps' next tokens match the golden, and the CQ tokens are 1073 382 93. It passes both without W2 (`qwen_e2e.json`, 1.76 M clk_sm cycles) and with W2 (`qwen_e2e_w2.json`, 2.29 M).
- Qwen functional machine: 16/16 positions bit-exact (`qwen_functional.json`).
- DS V4.1 functional machine: positions 0-3 bit-exact (`tools/gpu_sys/v41_hbm.py --check --npos 4`).
- DS V4.1 RTL e2e: running on ot-epyc1tb (see STATUS.md).
- Unit gates: `simt_sm.json` 12/12, `cdc_fifo.json`, `coll.json`, `memsys.json`, `host_bridge.json` and `unit_small.json` all PASS.
