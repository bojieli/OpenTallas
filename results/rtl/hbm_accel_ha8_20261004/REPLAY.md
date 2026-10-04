# HA8: Qwen3-8B HBM accelerator, exact token at position 1023 (2026-10-04)

**Result.**
- (a) same silicon, 2 dies TP2, 8 stacks, 842 MiB SRAM: **1,077,832 cycles = 898.2 µs, 1,113 tok/s** per user.
- (b) iso total silicon, 4 dies TP4, 16 stacks, 1,686 MiB SRAM: **517,788 cycles = 431.5 µs, 2,318 tok/s**.
- Both tokens are exact: the prompt token 1796 at P1023 gives 12147 against the GPU oracle (logits 41f41df1 and 41f4268a).
- The numbers are in `measured_composition.json`.

**Vehicle.**
- The W12 exact datapath: static schedule, lane-local fusion, no kernel launch.
- Every HBM-resident INT8 code word and each layer's KV window is one prefetch stream, timed by the r14 streaming controller (52ce3e9c1, REFpb).
- The controller runs at CK/2 (1.024 ns) in its own clock domain, with 4 stacks per die. Gray counts cross through 2-flop synchronisers.
- The engine is gated exactly by ME_STALL / KV_HBM.
- SRAM holds the lm_head first, then the leading layers.

**Method.**
- Per the owner rule, one RTL job per layer type plus the head, each entered from the GPU golden exit of the previous layer. The token is composed as 7 + Σ stages + 36.
- (a) ran more layers than needed (27 HBM layers) before the rule arrived. All gave 30,748 cycles.
- A chained L1→L2 run matches the isolated L1 and comes within 49 cycles (0.16%) on L2, so the isolated composition is conservative.

**Typical (a) layer, die 0 cycles:**

| Category | Cycles | Share |
|---|---:|---:|
| HBM wait | 26,404 | 86% |
| matmul | 1,967 | |
| stream unit | 1,346 | |
| collective | 816 | |
| attention | 143 | |
| other | 69 | |
| KV wait | 4 | |

The layer equals its stream time: 1,003 words at 0.962 TB/s per stack.

**Rungs, measured on one layer.**
- R5a refresh-aware fetch (REFpb against REFab): −3,177 cycles per layer, **+10.3%** per user.
- HA1, HA2, HA3 and HA6 have no exposed time on HBM layers. Their upper bound is 0.63% of the token, so they are REJECTED for Qwen AR.
- R5b does not apply: the model is dense.
- Toggles in the vehicle: `--ref-mode`, `--coll-lat`, `--enable-ar256`, `--winw`, `--sram-mib`, `--stacks`.

**Replay** (heavy jobs run on EPYC or agidock; the golden runs on the local GPU):
```
QWEN_O4_TP=2 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 python3 tools/qwen_hbmacc_position_oracle_gpu.py --prep ...   # file decoding (pve1)
... --run --prep-dir PREP --head --tokens prompt_tokens.txt --positions 1023 --embedding-npz prompt_embedding.npz --out GOLD   # local GPU
python3 tools/qwen_hbmacc_rt_token_w12.py --build-only --workdir BUILD --tp 2
python3 tools/qwen_hbmacc_layer_parallel.py --plan --plan-dir RUN --stages st6144_sw64/stages.txt --oracle-dir GOLD/P1023 \
  --layout img6144/L0-d0/layer0_rom.json --build-dir BUILD --pos 1023 --token 1796 --preroll 655 --preroll-stage L0=5000,L1=5000 --only L0,L1,L2,head
python3 tools/qwen_hbmacc_layer_parallel.py --run --plan-dir RUN
```
- The measurements used ot_hbm_r14_stream_pc.sv at 52ce3e9c1 (source_sha256 in each token_result.json); main now carries the r8 SS-closing successor (3f14a175f), not re-measured here.
- Stream bandwidth bench: `rtl/test/hbm_accel_qwen/tb_hbmacc_wstream_bw.sv` (`stream_bench/`).

**Not claimed.**
- The embedding row fetch (about 60 cycles).
- Window data carried from HBM: arrival is timed, but the data come from the stage images.
- Area, routing and SS/FF timing of the vehicle.
- In TP4 the attention cycles are attributed under collective or stream unit.
