# DSpark drafter ingest + Markov epilogue in RTL at P8191 (replaces the priced 7,875 cycles)

Vehicle: the VPRM REAL_MEM die, i.e. the same build (`bld_dbg`) and the same one-stack KV path as every other ctx8k component (`tools/qwen_rom_rt_vprm_w12.py`). Inputs, stage images and ISA goldens come from `tools/qwen_dspark_ingest_markov_rtl.py`. Every job matches its ISA golden bit for bit: the golden runs the same program with the GPU matvec, and the driver checks are in `res/k_*.json`. No job faults.

| job | what | cycles | checks |
|---|---|---|---|
| k_ING | FC 20,480->4,096 x 3 committed rows (die row slices), the all-gather as one 768-word all-reduce of zero-padded slices, hidden_norm x 3 | 3,327 | 12/12 exact |
| k_CTX0..2 | drafter layer-0 context K/V of rows 8185, 8186, 8187 (`context_kv_program`: QKV .. K/V write) | 4,447 each | X + K/V exact |
| k_MKV | one Markov slot: w2 (37,984 x 256 a die) . w1[prev] + the base logits | 920 | 80/80 exact |

The operands are real: the target's hidden states after layers 1/9/17/25/33 at P8185..8187, its logits at P8191, and prev, the token at 8191. They came from HF on the local GPU and are used as operands only. The ING ISA output also equals the plain W8 FC + `G.rmsnorm` semantics (`golden.json`).

## Composition per draft step (S = 3, n_ctx = 3)

| term | measured | priced |
|---|---|---|
| ingest = ING + 5 layers x (CTX0 + CTX1 + CTX2) | 3,327 + 5 x 13,341 = **70,032** | 3,024 |
| Markov = 3 x MKV (+ 3 x 736 argmax/gather, priced: no RTL) | 2,760 (+ 2,208) = **4,968** | 4,851 |
| total | **75,000** (97.1% measured) | 7,875 |

Why ingest is far above the price:
- Each context row costs 4,447 cycles, of which 3,713 are the KV write-back drain/retire fence. On this one-stack REAL_MEM path, that fence waits behind the layer-window fill the service streams at the same time (68,896 sectors).
- Only 734 cycles a row remain once that wait is removed. This figure is derived from the counters; it is not a separate run.
- The pricing counted only the K/V projection words. The reused program also keeps the Q projection, the norms and RoPE.

On the STREAM4 path, the drain contention should largely disappear (counter-derived ingest 3,327 + 15 x 734 = 14,337). That is unvalidated until it is run on STREAM4.

Still not RTL:
- the biased argmax over 37,984 logits plus the cross-die gather. The stream unit has SUM/MAX reducers but no argmax, and the ME argmax cannot see the added bias.
- the w1 row lookup (the IO-edge ROM; preloaded by the host here).

Effect on the ctx8k step (`../step_composed_ctx8k.json`, 1,057,503 cycles with 7,875 priced): with the measured 75,000 the step becomes 1,124,628 cycles. That cuts the DSpark per-user rate by 6.0% on this vehicle, to about 3,240 tok/s at the same tau.

Replay:
```
python3 tools/qwen_dspark_ingest_markov_rtl.py prep --snapshot-target <Qwen3-8B snapshot> --tokens prompt_tokens_8192.txt --out operands.npz
QWEN_O4_TP=4 HDC_SU_WIDTH=64 python3 tools/qwen_dspark_ingest_markov_rtl.py build --images <dspark images @3fdf7430c> --out stages
HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 python3 tools/qwen_dspark_ingest_markov_rtl.py golden --stages stages --operands operands.npz --out . --remote-root /srv/opentallas-scratch/claude/qwen-dspark-ingest
# on ot-epyc1tb: run.sh k_ING | k_CTX0..2 | k_MKV  (qwen_rom_rt_vprm_w12.py --plan k_*/plan --expect k_*/expect.json --kv-dir kv0 (zero window))
python3 tools/qwen_dspark_ingest_markov_rtl.py collect --res res --out record.json
```
