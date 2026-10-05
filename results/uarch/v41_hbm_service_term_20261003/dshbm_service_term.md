# DeepSeek-V4.1 HBM: priced per-boundary service term

This is a model-only review. It was run against `origin/main` `7b4d51a08` in a scratch worktree, which has since been removed. Nothing in the repo was edited.

Machine-readable record: `dshbm_service_term.json`. Computation: `compute.py` and `compute_out.json`. Proposed change: `uarch_model_service_term.patch`, which is not applied.

## Bottom line
- **The boundary service term itself is small.**
  - It costs 4 cycles (central) × 329 = 1.27 µs, which takes the rate from 2,801.8 to **2,791.8 tok/s (−0.36%)**.
  - The bounds are 2 cycles (−0.18%) and 6 cycles (−0.53%).
  - All three are below the 1% adoption gate.
- **The material omission is an uncounted HBM fetch, not one of the 329 boundaries.**
  - The 40 routed-expert weight fetches on the path depend on the router's choice, so their addresses exist only after top-6. The prefetching bulk copy cannot hide them.
  - `v41_hbm_chain` charges them **0**. The matvecs are re-priced by `sm_op_cycles`, which is compute plus drain only, and `arch_graph` is priced with `hbm=None`.
  - The W19 RTL bench measures this exposure at 133–526 ns per layer.
- **Corrected DS HBM AR (both terms):**

  | Case | tok/s | Change |
  |---|---|---|
  | Low | 2,754.1 | −1.7% |
  | **Central** | **2,650.9** | **−5.4%** |
  | High | 2,625.3 | −6.3% |

- **MTP:** 5,539.4 becomes 5,484.1, **5,361.7** or 5,330.7 tok/s (−1.0%, −3.2%, −3.8%). These are optimistic, because the MTP expert union streams longer (W19 composes 39 µs of fetch).
- **Qwen HBM:** negligible. 4 cycles gives −0.001%, and even 62 cycles gives −0.006%. The model is stream-bound and has no data-dependent weight fetch.

## 1. Boundary classification (329 = `v41_boundaries`)
| Class | Count | Nodes | GPU mechanism | Already priced |
|---|---|---|---|---|
| B1: on-die producer→consumer (root/L2 x broadcast) | 120 | wq_b, wo_a, experts_gu (40 each) | st.async / bulk copy plus mbarrier complete_tx (Hopper), or membar.gl plus grid barrier | Barrier 62 cycles (measured) + x tail 16 = 78 cycles; x_broadcast_fill |
| B2: matvec→cross-die collective | 161 | a_proj, wo_b, router, down (40 each), lm_head (1) | NVLS multimem, or put-with-signal plus flag wait | 78 cycles + 0.668 µs × ~188 collectives (125.9 µs); fabric CDC assumed inside 0.668 µs |
| B3: attention unit scores→pv | 40 | L*.attn.scores | Head-local kernel stage (mbarrier) | 78 cycles |
| B4: index select→KV gather from HBM | 8 | L{2,8,…,36}.idx.topk_final | Index-driven TMA gather | 78 cycles + 254.8 ns gather (250 ns *budget*) |
| *B5: routed-expert HBM fetch (not counted)* | *40* | *top6_order→experts_gu* | *TMA loads after routing, then tx-count wait* | ***0*** |
| Prefetched dense-weight arrival | 281 | all matvecs | TMA plus mbarrier tx-count | Hidden: the 37.4 µs sweep runs under the 357 µs chain |

## 2. Components and sources
**Per boundary, consumer-side and serial (cycles; low / central / high):**
- **Mirrored RF write ACK: 2 / 2 / 2.**
  - `rtl/gpu/ot_gpu_rf_service.sv:46` registers `ack_valid` the edge after `write_go`, and `:18` blocks the service until the ACK drains.
  - `tools/h4_v1_physical_join.py:170` (`SerializedOwner.ack`) charges `time+=2+stalls`.
  - This is the source of the prior audit's 2-cycle figure. Its `installed_RF_shared` write offset of 1 is the local lower bound.
- **Visibility fence: 0 / 1 / 1.** In `ot_gpu_rf_visibility_fence.sv:36-38,51`, `writes_visible` asserts in the same cycle as the ACK, and `fence_valid` asserts one edge after the retire.
- **Owner tag/generation compare: 0 / 1 / 1.** The W5 owner gate is not built yet. A same-cycle compare costs 0 cycles; a registered compare costs 1.
- **RF arbitration stall: 0 / 0 / 2.**
  - The `prefer_write` alternation (`ot_gpu_rf_service.sv:18-20,43`) makes a write wait for `read_pending` + `rsp_valid`.
  - At a boundary the SM has finished its op, so the central case expects no competing read.
- **Reverse retirement: 0, off the path.** The x store and operand registers are double-buffered, and there is a 128 KB/SM staging ring, so a slot is reused only two ops later.
- **CDC: 0.**
  - The model uses one SM clock (1.0339 GHz TT). A GPU runs the SU work on SIMT lanes in that same domain.
  - Not included: if the W18 two-domain plan were applied, each crossing would cost 4 slow / 5 fast cycles (`CDC_W18`, `uarch_model.py:3802`).

**Per routed fetch (ns; low / central / high):**
- **First access after top-6: 133.2 / 469.5 / 526.4.**
  - Source: `results/rtl/w19_expert_fetch.json` `audit_comparison.exposed_ns`. The low bound has refresh postponed; the central value is the mean of the six refresh-live AR cases.
  - The bench's controller and PHY latencies are 10 ns each way, which is ASSUMED.
- **CDC, HBM service↔SM, two crossings: 5.4 / 6.4 / 7.4.**
  - Measured in `results/rtl/v41_link_cdc_campaign.json`: a 2-flop Gray FIFO takes 3.0–4.1 RX cycles. The same structure is in `ot_hbm_r14_fifo2.sv` and `ot_async_fifo.sv`.
  - The W19 bench runs on a single clock, so this cost is not already in its figure.
- **Stall: 0 / 0.1 / 18.3.**
  - Central is M/D/1 at ρ = 37.4/356.9 = 0.105 with S = 2.05 ns per 64 B pseudo-channel access.
  - High is the measured W19 case with 80% background traffic (+18.3 ns).
  - The repo has no finite wait bound: `installed_services_r2` has `physical_wait_upper=None`.

**Sensitivities (not part of the term):**
- If the barrier were not GPU-faithful, the real-GPU options would be:
  - A pre-Hopper membar round trip: +62 cycles per boundary, giving 2,655 tok/s.
  - A Hopper cluster barrier at 181–213 cycles (H800 DSMEM): 2,533 to 2,469 tok/s.
  - The model's 62-cycle die-wide barrier network has no counterpart in a shipped GPU.
- If the CSA gather is charged at the model's own `HBM_LOADED_LAT_NS` of 500 ns: +1.96 µs, giving 2,786.5 tok/s.
- The headline loses 0.089% of rate per cycle per boundary, which confirms the earlier sensitivity figure.

## 3. Results
| | T (µs) | AR tok/s | Δ | MTP tok/s | Δ |
|---|---|---|---|---|---|
| Record | 356.9 | 2,801.8 | – | 5,539.4 | – |
| Boundary term only, central | 358.2 | 2,791.8 | −0.36% | 5,527.9 | −0.21% |
| Fetch only, central | 376.0 | 2,659.9 | −5.06% | 5,372.5 | −3.01% |
| **Both, low** | 363.1 | 2,754.1 | −1.70% | 5,484.1 | −1.00% |
| **Both, central** | 377.2 | **2,650.9** | −5.39% | **5,361.7** | −3.21% |
| **Both, high** | 380.9 | 2,625.3 | −6.30% | 5,330.7 | −3.77% |

There is a larger, separate gap. `results/uarch/w19_hbm_token_ar.json` composes the token from RTL ops with W15 product-port collectives and gets **2,019.2 tok/s**: its collectives take 283.7 µs against the headline's 125.9 µs.

## 4. Stale 2,920 in docs/MICROARCH_MODEL.md
- **Where it appears:** lines 245, 271, 288, 343, 378, 380, 404, 459, 651 and 1061. The same lines carry MTP 5,673 against the record's 5,539.4.
- **Where it came from:** `19d7ff597` (2026-09-29) produced 2,919.8, with drain 70 cycles and boundary 38 + 16 = 54 cycles.
- **How it fell:**
  - `89b439b1d`: 2,914.4 (barrier 40).
  - `264d52811`: 2,856.2. The barrier rose to 62 at the 504 µm/stage SS wire reach.
  - `28618da40`: 2,801.8. The LAT-7 add/mul raised the V4.1 drain from 70 to 95 cycles.
- **Why the doc is stale:** it was last touched for this figure at `84aa38cea`, and was never re-synced after either re-measurement. Both are cycle increases charged at the unchanged 1.0339 GHz clock.

## 5. Register-file area omission: confirmed
- **Confirmed.** `sm_area` counts SRAM only for x_store, staging and scratch. `ot_gpu_rf_service.sv` holds 512 × 128 FP32 in two 1R1W copies, which is 128 macros of `ot_sram_1r1w_128x256` (512 KB) per SM.
- **Area:** 0.6525 mm² per SM, or **20.88 mm² per die**.
- **Die fit:**
  - V4.1: 187.9 → 208.8 mm² of 688.4 mm².
  - Qwen: 152.0 → 172.9 mm².
  - Both still fit.
- **Right-sized die (affects cost):**
  - V4.1: 340.5 → 367.6 mm².
  - Qwen: 265.8 → 292.9 mm².
- **Static power:** about +0.10 W leakage and +0.28 W clock per die.
- **Rate:** unaffected.

## 6. Proposed change (`uarch_model_service_term.patch`)
- The patch adds `V41_HBM_SERVICE` (off / low / central / high, with sources in comments) and a `service="off"` parameter to `v41_hbm_chain`.
- When the term is enabled, it adds `boundary_service` = nb × cycles / clock, and `routed_fetch` = 40 × ns.
- With the default `off`, the patch adds no keys. I checked that it reproduces `hbm_gpu.json` rows 7–14 exactly.
- The MTP path and `V41_DRAFT_FRACTION` pick up the term through `v41_hbm_chain` automatically.
- It does not add headline rows. Per AGENTS.md, adoption would need a labelled row and a re-statement decision.
