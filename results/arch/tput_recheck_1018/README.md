# TPUT-RECHECK 2026-10-18: multi-request throughput of the current designs against the A100 80GB

Owner question (10-18): the 09-23 iso-area / iso-power studies looked promising for total throughput under many
concurrent requests. Does that still hold after all the iterations?

Producer: `compute.py` (writes `summary.json`). This is an analysis lane: no RTL and no fleet jobs.

Comparator: the **A100 80GB SXM only**. It is TSMC N7, the same 7 nm class as ASAP7, and the same baseline the 09-23
studies used (owner correction 10-18). Its constants are 826 mm², 5 HBM2e stacks, 2.039 TB/s, 80 GB, 400 W, BF16 312 /
INT8 624 TOPS, from `configs/hardware/technology.json` `reference_parts.a100_sxm_80gb`.

## Short answer

**No. The 09-23 multi-request advantage does not hold for the current designs.**

- **What does hold:**
  - Every design is faster per user than the A100 at batch 1.
  - The Qwen ROM is 27.6x per device and 2.6x per mm² at batch 1.
  - The ROM designs would lead per W and per HBM stack at saturation, but the power figures behind the per-W ratios
    are stale.
- **What does not hold:**
  - **Today every current design runs one request at a time.** No RTL or compiler supports a second request in
    flight, so aggregate = single-stream.
  - At saturation, measured per mm² against an A100 (modelled at its own capacity limit), the designs are 0.03x-0.21x
    today.
  - Even after the missing multi-request support is built, the bounds model gives 0.27x-0.94x per mm².

## Table (AR, target contexts: DeepSeek 1M, Qwen 8K)

Ratios are ours divided by the A100's. Above 1 means we are better.

| design | silicon (logic) | stacks | power (W) | b1 tok/s | A100 b1 | b1 /device | b1 /mm² | b1 /W | agg today | agg today /mm² | agg after multi-request support | its bound | /mm² | /W | /stack |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DS ROM array S81 p4l (440 dies) | 351,648 mm² | ~440 | ~38,200 (stale) | **1,243** (composed) | 406 (8xA100) | 3.06 | 0.058 | 0.26 | 1,243 (1 in flight) | 0.007 | **53,316** at ~43 in flight (modelled) | layer-20 index scan, HBM BW per user | 0.32 | 1.41 | 1.53 |
| Qwen ROM TP8 (8 x 841 + 8 x 272.6) | 8,909 mm² | 32 | ~7,000 (stale) | **4,769** (composed) | 173 (1xA100) | 27.6 | 2.56 | 1.57 | 4,769 (1 in flight) | 0.210 | **21,436** at ~4.5 in flight (modelled) | KV-die attention service, one request at a time | 0.94 | 0.58 | 1.59 |
| HBM d4g, DeepSeek (TP-192) | 123,231 mm² | 384 | 12,544 (stale) | **1,994** (composed) | 406 (8xA100) | 4.91 | 0.26 | 1.25 | 1,994 (time-share) | 0.034 | **15,951** with P=8 lanes (modelled, unbuilt) | token latency (step unchanged) | 0.27 | 1.29 | 0.53 |
| HBM d4g, Qwen (TP-8) | 5,135 mm² | 16 | ~2,600 (rough) | **931** (composed) | 173 (1xA100) | 5.38 | 0.87 | 0.82 | 931 (time-share) | 0.071 | **7,448** with P=8 lanes (modelled, unbuilt) | token latency; KV bandwidth from P=16 | 0.57 | 0.54 | 1.10 |

**A100 baselines.** These are modelled rooflines with the repo's assumed efficiencies (weight 0.75, KV 0.70, compute
0.45, capacity 0.90), so they are an **upper bound for the A100**.

- **Qwen3-8B, 8K, W8 weights, 8-bit KV.** The A100 serves 173 tok/s at batch 1. It holds at most 105 users at 8K, where
  it reaches **2,109 tok/s**, bound by the KV read. With BF16 KV it holds 52 users and reaches 1,053 tok/s.
- **DeepSeek-V4.1-Flash, 1M.** It takes 8 x A100 (one HGX) to store the 510 GB checkpoint at official precision
  with weight-only dequantisation.
  - That leaves 70 users of KV at 1M, where the 8 GPUs reach **3,164 tok/s**, bound by the expert-weight read.
  - Batch 1 is 406 tok/s on the roofline. Real A100 software is far below that at batch 1.
- **Measured anchor.** The repo has no measured A100 decode trace (`results/DECISION.md:96`, Open). The only public
  anchor found is short-context only: TensorRT-LLM Llama-3-8B at about 4,500 output tok/s on one A100 40GB
  ([Modal example](https://modal.com/docs/examples/trtllm_llama)).

**Iso-area restatement.** This is the aggregate the same silicon buys as A100s (each at its saturation point):

| design | ours (after multi-request support) | A100s of equal area |
|---|---|---|
| S81 | 53k tok/s | 168k tok/s |
| Qwen ROM | 21.4k tok/s | 22.7k tok/s |
| HBM-DS | 16k tok/s (P=8) | 59k tok/s |
| HBM-Qwen | 7.4k tok/s (P=8) | 13.1k tok/s |

## Grades

| grade | applies to |
|---|---|
| composed | Batch-1 rates from `results/arch/token_path_1018/<design>.json`. They mix measured and priced terms. The share measured on current RTL is 10.3% for DS ROM, 0.7% for Qwen ROM, 9.6% for HBM-DS and 6.9% for HBM-Qwen (banner in each file). |
| modelled | Every aggregate after multi-request support, and every A100 number. Formulas are in `summary.json` `agg_bounds` / `p_lane_potential`. |
| stale | All power. No current die has a power figure. Sources: S81 84.1 W/die (10-04); Qwen 09-28 envelope 435-619 W per 841 mm² die; HBM-DS 12,544 W (10-07, older geometry). HBM-Qwen uses a rough 0.5 W/mm². **Treat every per-W ratio as ±50%.** |
| derived | S81 die count. It is 97 stages x 4 rank dies + 52 non-layer dies carried over from rm5; no record states the p4l total. |

## (b) Concurrency each design supports today, and what is missing

- **S81 p4l: 1 in flight today.** It has the most groundwork.
  - **Already in the RTL:**
    - `{user 10, tok 21, pos 21}` on start frames and commands (`dsdv_seq_host.sv`).
    - Per-user window-ring addressing, `WB + 68·u` (`dsdv_svc_att.sv`).
    - **Two job contexts a die** (`ot_dsdv_fixed_issue.sv`). The calendar is fixed, and a same-cycle engine collision
      between the two contexts is a fault, not a stall.
  - **Missing:**
    - A multi-user compiled calendar. `dv_layer_compile.py` compiles one token, and no S81 die-run schedule exists.
    - User-tagged or buffered activation hand-off.
    - A per-user index-key base in `svc_sx`.
    - HBM sizing for N users on p4l.
  - **Bounds after the fix:**
    - Stage occupancy gives about 115k tok/s: 1.2 GHz over the busiest stage's ~10.4k cycles.
    - The layer-20 index scan gives 53k tok/s: 71 MB of index keys a user a token on 4 one-stack dies. This is the
      binding one.
    - KV capacity is about 241 users per busiest stack, which does not bind.
    - With 4 stacks on the scan dies (the 10-06 rule), the bound moves to stage occupancy, about 115k tok/s, which is
      0.68x the A100 per mm².
  - Two contexts a die would be enough: in-flight ≈ 43 users against 97 stages x 2 contexts.
- **Qwen ROM TP8: 1 in flight, by construction.**
  - `qkd_host_if_pins.sv:104` stops elaboration with `$fatal` unless NSLOT==1 && ENG_CTX==1.
  - The KV attention service has a static buffer of capacity 1 (`tools/qwen_static_schedule/attention.py`).
  - `kv_calendar` has no user dimension.
  - The user-tagged `ot_qwen_activation_handoff` exists but is used in its testbench only.
  - **Bounds after the fix:**
    - The KV-die service gives 21.4k tok/s: 1,555 cycles x 36 layers.
    - Matvec windows give 22.6k tok/s: weights are re-streamed per user at 1 MAC/lane/cycle, so batching does not
      amortise the ROM read.
    - KV HBM gives 53k tok/s.
    - So the design saturates at **~4.5 users**. That is consistent with the TP4 10-09 pricing: 25.4k at 4.6 users.
- **HBM d4g: 1 job at a time.**
  - `ot_hbm_token_loop.sv` takes `{job, tok, pos}` with no user field and no KV base, and the ISA records are
    single-row.
  - Concurrent requests can only time-share, so aggregate = 1,994 tok/s (DS) and 931 tok/s (Qwen).
  - **P position lanes (lane HBM-MTP) are the only lever, and they are unbuilt.** They need:
    - P x the MACs on each weight word;
    - a row-count ISA;
    - multi-query attention;
    - an expert-union compiler.
  - **Modelled at P=8, holding today's token latency per step:**
    - DS: 16k tok/s. Its bandwidth ceiling is 152k at P=128.
    - Qwen: 7.4k tok/s. Its KV-bandwidth ceiling is 20.8k, reached from P=16.
  - DeepSeek expert sharing across independent users is small. Union(8) is 39.7 distinct experts a layer against
    6 x 8 = 48 (`hbm_mtp_next_1018/stats/moe_union.json`, uncommitted).

## (c) Which bound sets the aggregate, and how it compares

The ROM designs keep weights on-die. Batching therefore cannot amortise a weight read, which is the A100's whole
large-batch gain, and the aggregate is set by per-user state:

- **DeepSeek:** the 1M-context index scan in HBM (S81), which is not shared across users.
- **Qwen:** the KV-die attention service, then 604 MB of KV a user a token.

Each design's area is dominated by ROM and compute sized for one user's latency:

- S81: 440 reticle dies.
- Qwen ROM: 16 dies.
- HBM-DS: 192 dies for one TP-192 user.

The A100, by contrast, is weight-bandwidth-bound at batch 1 but amortises weights across ~70-105 users. That is why
per mm² at saturation we are at 0.27x-0.94x, while per HBM stack the ROM designs are 1.5-1.6x: they spend their HBM
bandwidth only on KV. Per W the ROM designs show 0.6x-1.4x, but on stale power.

## (d) What changed against the 09-23 numbers, and why

1. **The 09-23 A100 frame had no KV term.**
   - In `rom_iso_area_inside_a100_die.json` the A100 by_batch goes compute-bound at 20,612 tok/s from batch 64. It has
     no KV read and no capacity limit, so "batch 256" is not servable at 8K.
   - With 8K FP8/INT8 KV the A100 tops out at 105 users and 2.1k tok/s.
   - This makes the A100 *weaker* at large batch than 09-23 assumed: 2.1k now, against 20.6k then.
2. **Our designs grew by 5-11x in silicon for the same models.** These are the owner rules since 09-23:
   - KV in HBM;
   - official checkpoint precision (DeepSeek 510 GB of weights in ROM);
   - 8-bit Qwen instead of q4p25;
   - 1.2 GHz static schedule with no backpressure;
   - landed crossings and relay costs;
   - HBM priced at physical bandwidth;
   - single-user latency first.

   What that did to each design:
   - **Qwen:** one 826 mm² die at q4p25 with 596 mm² of ROM (09-23) became 8,909 mm² (8 compute + 8 KV dies). The
     batch-1 rate fell from 6,734 to 4,769 tok/s.
   - **DeepSeek:** the 09-23 arrays were DSV4-Flash (not V4.1) at 50-68k mm². S81 p4l is ~352k mm².
3. **The 09-23 DeepSeek 13-16x was not against an A100.**
   - It was against a B200 cluster that the record itself says was link-latency-bound in tensor parallel.
   - It was roofline on both sides, and its worst operating points were already 0.9-1.75x.
   - Against an A100 HGX at saturation, S81 today is 0.007x per mm². After multi-request support it is 0.32x (0.68x
     with 4-stack scan dies).
4. **Multi-request execution was assumed, not built.** The 09-23 and 09-26 aggregates (array b4096 113k-1.35M tok/s)
   assumed pipeline fill. None of the current RTL or compilers keep more than one request in flight (section b).

## What would change the answer

These are ranked by gain per effort, using the bounds above.

1. **S81:**
   - Build the multi-user calendar. Two contexts a die already exist, so the compiler must prove two contexts
     collision-free.
   - Tag the activation hand-off with the user.
   - Give 4 stacks to the scan dies.

   Together these give about 115k tok/s (0.68x A100 per mm², ~2-3x per W on the stale power).
2. **Qwen ROM:**
   - Make the KV-die attention service multi-slot (2-4 buffers) and give the host leaf NSLOT>1.
   - Beyond ~22k tok/s the next limit is the matvec windows. To pass it, the MAC lanes would need to apply one ROM
     word to several users (P accumulators). That costs area and must not slow batch 1 (AGENTS utilisation rule).
3. **HBM d4g:** P-lane batching is the only design here that can scale like a GPU. A ceiling of 152k tok/s for DS
   would be 2.6x the A100 per mm². It is unbuilt and unpriced in area, and owner priority keeps HBM MTP parked.

## Files

- `compute.py`: the model (all constants and sources inline).
- `summary.json`: every number with grade, formula and source.
