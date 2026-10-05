# Qwen3-8B HBM accelerator at 8K: weight and KV stream at position 8,191 (2026-10-04)

**Result.** One decode token at P8191, with 8,192 positions of KV, is bit-exact against the GPU golden. The prompt token 24 gives 18 at both design points. Every stage's X matches on every die.

| | (a) TP2, same silicon | (b) TP4, iso silicon |
|---|---:|---:|
| Typical HBM layer | L2: 33,051 cycles | L20: 17,237 cycles |
| Stream words per layer per die (KV words) | 1,078 (86) | 555 (43) |
| Achieved stream rate per die | **3.848 TB/s = 96.2 %** | **3.798 TB/s = 95.0 %** |
| Controller stream rate per stack | 0.962 TB/s | 0.949 TB/s |
| Window-room block | 0 | 0 |
| Token | 1,161,915 cycles = 968.3 µs | 557,056 cycles = 464.2 µs |
| **Per-user rate at 8K** | **1,032.8 tok/s** | **2,154.2 tok/s** |
| At P1023 (HA8) | 1,113.3 tok/s | 2,317.6 tok/s |

The token rate is 1.2 GHz divided by the token cycles. Over the whole token, the stream averages 3.83 TB/s per die in (a) and 3.66 TB/s in (b). The SRAM-resident L0 and head pull that average down.

**Finding: the as-built 160-word window drops TP2 below 90 % at 8K.**
- At 8K, each layer's KV segment is 86 words (8.5 MB per die). It holds window room from its arrival until attention ends.
- The window is released only when the spine moves past it, so the stream can run only 34 words ahead into o_proj while attention and softmax run over 8,192 positions.
- With 160 words, L2 takes 35,353 cycles: 89.9 %, with 1,508 controller cycles blocked. The token runs at 967.1 tok/s.
- With `--winw 224` (21 MiB, an existing default-off flag), L2 takes 33,051 cycles and the stream is never blocked. 256 and 320 words give the identical layer time.
- Gain: **+6.8 %** per user for TP2 and +0.46 % for TP4.
- The window is paid for out of the SRAM budget: the runner subtracts it from the resident code words, and the measured L1/L5/L6 include that cost.

**First-access exposure.**
- At token start, L0 is SRAM-resident and its KV lands during the preroll (kv_wait 4 or 2 cycles).
- Within a layer, kv_wait is 2,217 cycles (TP2) or 897 cycles (TP4): the engine waits after qkv for the whole KV segment to land.
- The controller streams at full rate during that wait, so this is stream time, not lost bandwidth.

**Method.**
- This applies the owner rule: one RTL job per layer type, plus the head. Each job starts from the GPU golden exit of the previous layer.
- (a) runs L0 (SRAM), L1 (partly SRAM), L2 (×34) and head. (b) runs L0 (×5), L5, L6, L20 (×29) and head.
- The token is composed as 7 + Σ stages + 36 (`tools/qwen_hbmacc_p8191_compose.py`).
- The vehicle is the HA8 one (main e547a0986) with the r14 stream controller from main e2fb7f4ae. Source sha256 values are in each `token_result.json`.

**Not measured (unvalidated).**
- The embedding row fetch, about 60 cycles.
- The token's posted KV write-back.
- Window data: their arrival is timed, but the data come from the stage images.
- Preroll conventions: 5,000 controller cycles for L1/L5/L6, and 1,000 for L20 against a measured tail of 1,139, which is conservative.
- Area, routing and SS/FF timing of the vehicle and the 21 MiB window.

**Replay** (heavy jobs on EPYC under `/srv/opentallas-scratch/claude/qwen-hbmacc-8k/`; the golden runs on the local GPU):
```
QWEN_O4_TP=2 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 python3 tools/qwen_hbmacc_position_oracle_gpu.py --prep --stages W12/st6144_sw64/stages.txt \
  --pins oracle6144/oracle.json --layout-manifest "W12/img6144/L0-d{die}/layer0_rom.json" --head-manifest "W12/img6144/head-d{die}/head_rom.json" --out prep/tp2
... --run --prep-dir prep/tp2 --layers 36 --head --tokens prompt_tokens_8192.txt --positions 8191 --embedding-npz prompt_embedding.npz --out gold/tp2
python3 tools/qwen_hbmacc_rt_token_w12.py --build-only --workdir build_tp2_w224 --tp 2 --winw 224
python3 tools/qwen_hbmacc_layer_parallel.py --plan --plan-dir RUN --stages W12/st6144_sw64/stages.txt --oracle-dir gold/tp2/P8191 \
  --layout W12/img6144/L0-d0/layer0_rom.json --build-dir build_tp2_w224 --pos 8191 --token 24 --preroll 655 --preroll-stage L0=5000,L1=5000 \
  --driver-args "--winw 224" --only L0,L1,L2,head
python3 tools/qwen_hbmacc_layer_parallel.py --run --plan-dir RUN
python3 tools/qwen_hbmacc_p8191_compose.py --stage L0=1=RUN/L0/token_result.json --stage L1=1=... --stage L2=34=... --stage head=1=... --out compose.json
```
- (b) adds the HA8 TP4 flags (`b_p8191_w*/*/cmd.txt`) with `--preroll 1000 --preroll-stage L0=5000,L5=5000,L6=5000`.

**Files.**
- `measured_composition.json`: the summary.
- `compose_tp2_w{160,224}.json` and `b_p8191_w{160,224}/compose.json`: per-stage compositions.
- Stage jobs: `a_p8191/` (w160), `a_p8191_w{224,256,320}/`, `a_p8191_w224_head/` and `b_p8191_w{160,224}/`.
- `gold_tp2/` and `gold_tp4/`: oracle records.
