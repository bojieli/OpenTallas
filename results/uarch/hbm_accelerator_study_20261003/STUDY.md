# HBM inference accelerator: model-first study (2026-10-03)

Status: **MODEL ONLY**.

- Record: `ladder.json`, produced by `ladder_model.py` (see REPLAY.md).
- Ablation: the GPU-organised comparator, which is the W19 composed TP-96 token, 442.14 µs = 2,261.7 tok/s.
- Method: each rung is an additive µs delta on that token. The delta is applied at each verify width P = 1..6, using DSpark's measured-union compositions.
- Executor of record: Codex. The full plan is in [HANDOFF_TO_CODEX.md](HANDOFF_TO_CODEX.md).

## DeepSeek-V4.1-Flash, 1M context (200K is within 0.2%)

| Rung | What | AR µs saved | Verify(6) µs saved | AR tok/s after | Class | GPU-standard or ours |
|---|---|---:|---:|---:|---|---|
| R0 | GPU-faithful: grid sync (1.43 µs) per dependent op | – | – | 1,098.6 | – | GPU |
| R1 | Persistent static program + 62-cycle hardware barrier (this is the ablation) | 468.1 | – | 2,261.7 | measured barrier | partly GPU; the die-wide barrier is ours |
| R0c | Honest ablation: refresh-live routed fetch + ACK/fence/owner service | −14.9 | −14.9 | 2,188.2 | model | correction |
| R1b | tx-count arrival, release broadcast removed | 8.9 | 8.9 | 2,231.5 | model | GPU-derived |
| R2 | Direct 2-level die-to-die topology (measured C1 hop 210/221 ns + in-package 83 ns) | 70.1 | 70.1 | 2,645.1 | measured hop, ESTIMATED topology | ours |
| R3a | Cut-through collectives (transferred from the measured Qwen async collective) | 17.9 | 17.9 | 2,776.2 | ESTIMATE (transfer) | ours |
| R3b | TMEM-style epilogue fusion | 6.1 | 11.8 | 2,824.0 | model (FA on W19) | GPU |
| R4b | Per-stack index scorers + top-k chase | 3.4 | 3.4 | 2,851.5 | model; below the 1% gate on its own | ours |
| R5a | Refresh-aware streaming controller on the routed fetch | 13.5 | 13.5 | 2,965.3 | measured bench basis | ours |
| R5b | Shared expert issued first, so the routed fetch overlaps it | 5.6 | 10.6 | **3,015.2** | ESTIMATE (hide window) | ours (compiler) |
| R6a | One select unit per verify position | 0 | 14.0 | 3,015.2 | measured select | ours |
| R7a | Serial chain at 1.091 GHz (CONDITIONAL: the ratio FIFO fails SS by −75.6 ps) | 13.6 | 26.2 | 3,144.0 | ESTIMATE | ours |

**Composed accelerator**, firm rungs at 1M:
- AR: 331.7 µs = **3,015 tok/s** (+33% over the ablation; +38% over the honest ablation).
- DSpark γ=5 at τ 3.649: step 608.0 µs (draft 42.3) = **6,001 tok/s**. At τ 4: 6,579. At the agentic τ 4.555: 7,493.

**Sensitivities:**
- With the conditional R7a: AR 3,144, MTP 6,293.
- An optimistic switched topology (light-FEC links + in-switch reduce, ASSUMED) gives AR 3,334.

**Price-first items** (not yet priced; these are handoff tasks):
- Collective-count reduction in the TP-96 program (6 per layer).
- Router-predicted expert prefetch (its recall needs a GPU trace study).
- Die count, and 2 stacks per die, at iso-power.
- The R8b MTP penalty (union stream at half the bandwidth; ESTIMATED at about −4%).

**Rejected:**
- SRAM-resident hot weights for DS: bandwidth does not bind at batch 1, because the 37 µs sweep runs under a 330 µs chain.

## Qwen3-8B (8K) is bandwidth-bound: per-user rate = stack bandwidth / bytes per token

| Rung | AR tok/s | DFlash b16 tok/s (τ 3.656) |
|---|---:|---:|
| Q0 GPU-faithful (fixed launch/sync of 1.464 ms) | 384.7 | – |
| Q1 ablation (2 dies, 8 stacks at 0.9 TB/s) | 880.8 | 2,671 |
| Q2 measured streaming controller (0.958 TB/s per stack) | 937.6 | 2,843 |
| Q3 one-stream/async collectives | 0, hidden under the stream: REJECTED | |
| Q4 near-HBM attention | 0, KV is still read from DRAM: REJECTED | |
| Q5 842 MiB SRAM on the same 2×815 mm² footprint (lm_head first) | 1,051 | 3,356 (5,966 at τ 6.5) |
| Iso total silicon with ROM option C (4 dies + 16 stacks + 1,686 MiB SRAM) | 2,391 | 7,493 |

**Energy per token:**

| Design | J/token |
|---|---:|
| ROM, calibrated (2,793 tok/s) | 0.148 |
| ROM, near-HBM (5,237 tok/s) | 0.115 |
| HBM accelerator, AR, same silicon as the ablation | 0.853 |
| HBM accelerator, DFlash, same silicon as the ablation | 0.267 |

**Finding on positioning.** ROM wins Qwen per-user rate under AR, and wins energy and iso-power in every mode. The exception is speculation:
- With DFlash and iso total silicon, the HBM accelerator (7.5k tok/s, model) exceeds the ROM's AR-only target (5,237, model).
- "ROM wins dense small" therefore needs ROM speculation (m ≥ 2 lanes) or must be stated as per-joule.

**Qwen3.8-27B (ASSUMED config):**
- HBM accelerator with 16 stacks: AR 583 / DFlash 2,047.
- ROM, scaled by 64/36 layers: about 2,945 AR, using roughly 3.6× the ROM silicon.
- B200 FP8, tier 2: 126.
- ROM's advantage grows with dense size: the HBM bytes per token grow 3.6×, while the ROM chain grows 1.8×.

## Against real GPUs

**Qwen3-8B:**
- B200 SGLang, measured: BF16 AR 230; DFlash 955 (code) and 1,175 (math). B200 FP8, tier 2: 331.
- H200 NIM FP8: 235. H100 FP8 (modelled): 193.
- HBM accelerator on the same silicon as one B200 (2 dies, 8 stacks): AR 1,051 (3.2× B200 FP8) and DFlash 3,356 (2.9–3.5× B200 measured DFlash at the paper's τ).

**DS V4.1:**
- 8×B200, tier 2: 282 AR / 548 MTP. Published R1 min-latency: 368 with MTP.
- Accelerator: 3,015 AR / 6,001 MTP, about 11× at a similar system power (about 9.8 kW against 8×B200 at 5.5–9.6 kW).
- Accelerator silicon is 5.4× the B200 system's total silicon (DRAM included). GPUs cannot buy per-user latency with more silicon.

**DS, ROM vs HBM accelerator:**
- The HBM accelerator wins per-user rate: 3,015 / 6,001 against ROM 2,787 / 4,589.
- It also wins on silicon: 32.7k mm² of logic against 169.5k, and 0.42M total mm² against 0.63M (DRAM at an ASSUMED 1,000 mm² per stack).
- ROM wins energy per token at batch 1: 0.68 J against 3.24 J.
