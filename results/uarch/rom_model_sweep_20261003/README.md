# Which LLMs suit a ROM-weight design? Model sweep, 2026-10-03

**Status: MODEL ONLY, not adopted.** No RTL, no place and route, no inference. Every model is profiled from `config.json` plus safetensors headers. The profiler reads them with two HTTP range reads per shard and fetches no weights. The full tables are in [`tables.md`](tables.md), every number is in [`sweep.json`](sweep.json), and the replay steps are in [`REPLAY.md`](REPLAY.md).

## Question and comparison rule

The study asks which open models gain most from ROM weights, compared with a GPU-organised HBM design at the same total silicon. **HBM stacks count as silicon, at 1,150 mm² a stack**, following the user rule of ~1,000–1,300 mm². A second comparison holds total power equal instead. The figure of merit is per-user decode rate at batch 1, AR and with the best published drafter. Each side may decline speculation when it does not pay.

## Method

The method is a calibrated latency chain (`tools/rom_model_sweep.py`), in 1.2 GHz cycles.

**ROM layer** = 2,087 fixed body + active bytes / (k × 94.2 KB/cycle) + 2 × 991-cycle all-reduce + near-HBM attention (300 + KV / stack bandwidth). The terms come from:
- the Qwen RTL body split into fixed latency and weight stream;
- the measured TP-4 board all-reduce;
- `qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json`.

The ROM is laid out as follows:
- A die holds 3.14 GB of 8-bit weights. That is the 560 mm² array less 6,144 groups of logic, at 75 Mbit/mm² with no ECC.
- Dies are grouped into TP-k stages. Only the active stage works, so **total parameters buy dies, while active parameters and layer count buy time**.
- The ROM configuration is chosen per model from k ∈ {4, 8, 16}, s ∈ {1, 2, 4} stacks a die, and KV either local to its stage or striped over every die.

**HBM** uses right-sized 340.5 mm² dies, each with 4 stacks at 0.9 TB/s, and every matrix is TP-sharded over all dies. Its layer time is:

layer = max(W / BW, same fixed body) + attention + KV / BW + 2 all-reduces

The all-reduce is the measured one-shot: in-switch reduction, flat in die count.

**Speculation:**
- ROM lanes are m = 1 (the adopted V4.1 MTP policy), so a P-position verify re-streams weights P times.
- HBM SM columns take ≤16 positions on one fetch, but MoE verify reads the union of the experts the positions touch.

**Calibration identities** (asserted on every run):
- Qwen3-8B ROM with k = 4, s = 4 gives 229,090 cycles against the recorded 229,158 (5,238 tok/s).
- The Qwen HBM comparator with 2 dies gives 870 tok/s against the recorded 880.5.

## Result: ranked by iso-silicon AR ratio, 8K, batch 1

| model | act/total B | ROM dies | ROM AR 8K | HBM iso-Si | **AR ×, 8K** | AR ×, 32K | AR ×, iso-power | best-spec × | energy HBM/ROM |
|---|---|---|---|---|---|---|---|---|---|
| Mistral-Small-3.2-24B | 22.9/23.6 | 8 | 3,530 | 442 | **8.0** | 4.4 | 23 | no drafter | 15 |
| Qwen3-14B | 14.0/14.8 | 8 | 3,657 | 695 | **5.3** | 2.9 | 15 | 3.4 | 9.9 |
| Gemma-4-31B | 30.7/30.7 | 12 | 2,695 | 537 | **5.0** | 4.5 | 23 | 1.9 | 13 |
| Phi-4 (16K max) | 14.2/14.7 | 8 | 3,368 | 681 | **5.0** | n/a | 14 | no drafter | 8.8 |
| Qwen3-32B | 32.0/32.8 | 12 | 2,306 | 509 | **4.5** | 3.0 | 21 | 2.1 | 11 |
| Gemma-3-27B | 25.6/27.0 | 12 | 2,740 | 633 | **4.3** | 3.6 | 20 | no drafter | 12 |
| Qwen3.8-27B | 25.6/26.9 | 12 | 2,621 | 628 | **4.2** | 3.6 | 19 | 2.4 | 11 |
| Llama-3.3-70B | 69.5/70.5 | 24 | 1,919 | 464 | **4.1** | 3.2 | 13 | 1.8 | 12 |
| Qwen3-8B (anchor) | 7.6/8.2 | 4 | 3,157 | 870 | **3.6** | 2.4 | 7.2 | 2.3 | 7.7 |
| gpt-oss-20b | 3.6/20.9 | 8 | 8,313 | 2,527 | **3.3** | 2.6 | 8.7 | 5.0 | 8.2 |
| Gemma-4-26B-A4B | 3.8/25.2 | 12 | 6,681 | 3,506 | **1.9** | 1.8 | 7.5 | 2.8 | 5.1 |
| Llama-4-Scout | 16.1/107.8 | 36 | 3,607 | 2,220 | **1.6** | 1.6 | 4.7 | 1.9 | 4.0 |
| GLM-4.5-Air | 12.8/106.8 | 36 | 3,924 | 2,674 | **1.5** | 1.3 | 4.1 | 1.7 | 3.5 |
| Qwen3.6-35B-A3B | 3.0/34.7 | 12 | 5,061 | 3,800 | **1.3** | 1.3 | 4.6 | 1.6 | 3.1 |
| Qwen3-30B-A3B | 3.0/30.5 | 12 | 4,109 | 3,444 | **1.2** | 1.0 | 4.1 | 2.2 | 2.5 |
| Mistral-Small-4-119B | 6.1/119.0 | 40 | 5,690 | 5,273 | **1.1** | 1.1 | 2.4 | 1.4 | 2.5 |
| gpt-oss-120b | 5.1/116.8 | 40 | 5,868 | 5,903 | **0.99** | 0.97 | 2.2 | 1.4 | 2.2 |
| Qwen3-235B-A22B | 21.6/235.1 | 76 | 2,116 | 2,382 | **0.89** | 0.87 | 1.8 | 1.1 | 1.8 |
| MiniMax-M2.7 | 10.4/228.7 | 76 | 3,352 | 3,976 | **0.84** | 0.84 | 1.3 | 0.97 | 1.5 |
| DeepSeek-V4.1-Flash (anchor) | 16.1/748.5 | 240 | 4,843 | 5,988 | **0.81** | 0.81 | 0.99 | 1.00 | 1.1 |
| Kimi-K2-0905 | 31.7/1,026 | 336 | 2,980 | 3,771 | **0.79** | 0.76 | 0.80 | no drafter | 1.2 |

## Why: the first-principles drivers

1. **Density (active / total) sets the HBM side.** At equal silicon, HBM bandwidth scales with the silicon that the *total* parameters force on the ROM. The HBM token, however, streams only the *active* bytes.
   - For a dense model, the HBM design is bandwidth-bound at 80–90% of its token: Gemma-4-31B spends 1,627 of 1,861 µs on weights.
   - For a sparse MoE (≤0.1 active/total), the HBM design gets about 10× more bandwidth than its active bytes need. It falls onto the same latency floor as the ROM (fixed body plus 2 all-reduces a layer), and the ratio collapses to about 1. That is the DeepSeek and Kimi corner.
2. **Bytes per layer set the ROM side.** The ROM token is about L × (1.7 µs body + 1.65 µs all-reduces + attention). The weight stream is cheap: the active stage reads at about 450 TB/s per TP-4 group.
   - Wide, shallow dense models gain most: Mistral-Small-3.2 at 0.59 GB/layer over 40 layers gives 8×.
   - Deep ones gain less: Qwen3-32B at 0.51 GB/layer over 64 layers gives 4.5×.
   - Qwen3-8B at 0.23 GB/layer is too narrow. Its minimum 4-die group also hands the HBM side more silicon than the model needs (3.6×).
3. **KV size erodes the advantage with context.** At 32K, attention becomes a larger share of the ROM chain, and the ratio falls:
   - from 5.3× to 2.9× for full-GQA Qwen3-14B;
   - from 4.1× to 3.2× for Llama-3.3-70B.

   Models whose KV stops growing hold the ratio: sliding-window plus global attention (Gemma-4-31B, 4.5×) and hybrid linear attention (Qwen3.8-27B, 3.6×).
4. **Compute headroom for speculation favours HBM on dense models and ROM on MoE models.**
   - Dense: the HBM verify is nearly free, but ROM m = 1 lanes re-stream weights per position. Dense ratios therefore fall to about 1.8–3.4× with drafters.
   - MoE: the HBM verify must read the union of the experts its positions touch, so the ROM ratio *rises* with speculation (gpt-oss-20b 3.3× to 5.0×, Qwen3-30B-A3B 1.2× to 2.2×).
   - Short-P drafters (native MTP-1, EAGLE) suit ROM. DFlash (P = 16) suits HBM.
5. **Iso-power is far kinder to ROM.** An HBM die streaming at full rate burns about 400 W of DRAM traffic. A ROM die idles near 40 W plus its stacks. Energy per token is 9–15× better for mid-size dense models and about 1× at the MoE extreme.

## Where ROM's advantage peaks, and the third target

ROM's advantage peaks for **dense or low-sparsity models of 14–32B, which fit in 8–12 reticles (4–6 packages), at 8K–32K context**. There it is 4–8× AR at iso-silicon and 14–23× at iso-power. It stays above 4× to 70B dense. It falls to about 1× for MoE models with an active/total ratio of 0.05 or less (gpt-oss-120b, MiniMax, DeepSeek, Kimi).

**Recommended third target: Qwen3.8-27B** (Apache-2.0, released 2026-08). Reasons:
- It is the newest strong dense model in the sweep, needing 12 dies (6 packages).
- It reaches 4.2× AR at 8K and holds 3.6× at 32K, because 48 of its 64 layers are gated-delta linear attention.
- Its native MTP-1 matches ROM's m = 1 lanes (2.4× with speculation).
- It continues the Qwen golden and tooling lineage.

Runner-up: **Gemma-4-31B** (Apache-2.0). It has the best ratio that holds at 32K (4.5×) and published DFlash and EAGLE-3 drafters, but speculation does not pay on its ROM. **Mistral-Small-3.2-24B** has the highest raw ratio (8.0×) but no drafter, and its KV grows to 4.4× at 32K. The risk for Qwen3.8 is that its linear-attention state update is priced only as an ASSUMED 200-cycle chain, and no unit for it exists in this repository.

## Validation against the two existing targets, and caveats

**Qwen3-8B.** At the adopted k = 4, s = 4 design, ROM reaches 5,238 tok/s:
- against the repository's 2-die, 8-stack comparator (870 tok/s), that is 6.0×;
- with stacks counted as silicon, it is 3.3× (the comparator gets 4 dies, 1,570 tok/s).

The ~6.6× often quoted does not count HBM as silicon.

**DeepSeek-V4.1.** The generic chain gives 0.81× AR and 1.0× with speculation. The repository's detailed records give about 1.05–1.23× AR and about 0.65× with MTP. The generic model omits V4.1's mHC, Sinkhorn and indexer chains on both sides, and stores the experts at 8 bits rather than the product's FP4. Read the MoE-extreme rows to about ±30%.

**Graded assumptions:**
- The tau values are ASSUMED (MTP-1 1.8, MTP-3 2.6, EAGLE-3 3.0), except DFlash 3.656 and DSpark 3.649, which are repository measurements.
- The MoE select is 419 cycles. The KV is FP8.
- Vision towers are excluded. Llama and Gemma-3 were profiled from ungated unsloth mirrors.
- Changing the stack area to 1,000 or 1,300 mm² moves the ratios by ≤10% and does not change the ranking. The one exception is Qwen3-8B, where integer die rounding gives 3.6–4.9×.
