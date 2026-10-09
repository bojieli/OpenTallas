# DFlash for Qwen3-8B on the generic HBM die (HGI-1), 2026-10-09

This record covers the drafter `z-lab/Qwen3-8B-DFlash-b16`, used unchanged: BF16 weights, 5 layers, target layers [1, 9, 17, 25, 33], mask token 151,669, non-causal block attention. It runs on 4 r25 dies at TP4 with an 8K context.

The record contains:

- `dflash_proof.json` comes from `python3 -m hgi_sim.dflash_proof --blocks 4,8,16`. It holds the functional runs on a tiny target and drafter (random BF16 weights, 6 target layers, 2 drafter layers).
- `dflash_timing.json` comes from `python3 -m hgi_sim.dflash_timing`. It times one full-size step at position 8,192 − B under the CP-modelled S2 schedule, with 0 races. The cycle counts are pathfinding figures: the unit costs come from `calibration.json`.
- Compiler: `tools/hgi_sim/dflash.py`. The step programming rules are in spec §7.4 (`docs/HBM_GENERIC_INTERFACE.md`).

## Can the current interface run DFlash?

Yes. One step is a single doorbell, with no new hardware. Two items are still open, and the spec's open items list them.

| Owner question | Answer |
|---|---|
| (1) Verify at 8 vs 16 positions | `SM.MATVEC` `[4:2]` lets ≤ 8 slots share one weight read. Block 8 is 1 weight pass; block 16 is 2 passes of every target and drafter matrix. |
| (2) Per-slot causal counts | The 3-bit `slot` field cannot reach slot 15, so DYN `POS_SLOT1` is not used. Each step, one `DMA.LOAD` of a U32 table T[q] = q at POS + 1 + s (`ibcast`) writes one I table per slot. Records then use `n_sel` = 63 (N_FROM_VM). |
| (3) Drafter attention (context + whole block, bidirectional) | No new DYN or mask code is needed. ATT B = the drafter context rows (`n_sel` = POS) and ATT C = the block's own rows (static n = B). Every lane uses count pos + B. |
| (4) Target hidden-state capture and `fc` / KV injection | The verify layer loop is split at layers 1, 9, 17, 25 and 33. At each split a `DMA.STORE` writes every slot's residual (BF16) to CTXF. The drafter context K/V for the B most recent committed positions are rebuilt every step: `fc` (SM fmt 0, one record per captured layer) → SU pairwise → `COLL.ALL_GATHER` → `hidden_norm` → K/V projection, `k_norm`, RoPE → `DMA.STORE`. |
| (5) Mask embedding | The mask embedding is a static descriptor base. |
| (5) Entry | One doorbell at `entry_verify` runs draft, verify and accept. |
| (5) Accept with 18-bit ids | The ids are stored as U32 and reloaded as INT8 bytes. The SU computes Σ(byte diff)², then min(·, 1). `ARGMAX.LOCAL` with `imm_a` = 0 gives k = accepted + 1. |
| (5) KV rollback | Nothing is needed: every count derives from POS, and the next step overwrites the rejected rows. |

| Gap | Kind | Resolution |
|---|---|---|
| G18: the SM RTL (`ot_hbm_accel_smh`) has no slot count | Hardware fidelity (hbm-forks) | The spec says one weight read serves 8 slots, and the simulator implements that bit-exact. The RTL issue is not benched. If every slot re-issues the line, the step is 3.9× slower (table below). |
| G19: ATT lanes field cannot encode 16 | Spec clarification | 0 encodes 16. This is backward compatible, and is in the simulator and the spec. |
| Q-MTP-1: the completion carries one token, but a step commits k | Hardware (cmdproc) | Proposed `CTL.TOKX`: A[0] = k, A[1..k] = tokens, and the CP emits k completion beats. It is simulated. |

## Functional proof (`dflash_proof.json`)

The proof compares the simulator against the golden bit for bit, on every die and every step. It checks:

- the draft ids;
- the committed tokens;
- the target KV rows [pos, pos + B) for all layers;
- the drafter KV rows [pos − B, pos);
- the captured features [pos, pos + B).

Runs:

- **Blocks 4, 8, 16.** Each runs 3 steps. Step 1 uses oracle drafts and reaches full acceptance (k = B). Every committed stream equals plain AR greedy decoding from the same state.
- **Mutants.**
  - The verify mask tail is not zeroed: the run fails, because the committed tokens no longer equal AR.
  - The drafter attends causally: the draft ids change, so the run fails. Output stays lossless, as verification guarantees.

## Timing at 8K (`dflash_timing.json`, 1.2 GHz)

AR uses the same cost model: 1,261,770 cycles, **951.0 tok/s**. One-beat INT8 would give 922,645 cycles, 1,300.6 tok/s, but it is rejected (NO_FIT).

The τ values:

- **Block 16.** The published τ is 8.01, from DFlash arXiv:2602.06036v2 Table 3 (B200, SGLang, c = 1, MATH-500). It is the largest published Qwen3-8B τ. Our 264-turn measurement is 3.656 cycle-weighted and 4.662 averaged over workloads.
- **Block 8.** No τ is published. Anchored to the paper: 8.01 × (our MATH-500 non-thinking ratio of block 8 to block 16, 5.8265 / 8.3572) = 5.584. Measured directly at block 8: 3.2956 cycle-weighted, 3.748 averaged over workloads.

| Block | SM slots | INT8 issue | Step cycles | tok/s at published τ | tok/s at measured τ (cycle-wt / workload-mean) |
|---:|---|---|---:|---:|---:|
| 16 | shared (spec) | two-beat | 5,359,384 | **1,793.5** (8.01) | 818.6 / 1,043.8 |
| 16 | shared (spec) | one-beat (NO_FIT) | 4,519,583 | 2,126.8 | 970.7 / 1,237.8 |
| 8 | shared (spec) | two-beat | 2,679,956 | **2,500.4** (5.584, anchored) | 1,475.7 / 1,678.2 |
| 8 | shared (spec) | one-beat (NO_FIT) | 2,260,055 | 2,964.9 | 1,749.9 / 1,990.0 |
| 16 | re-issue per slot (RTL as is) | two-beat | 20,767,685 | 462.8 | — |
| 8 | re-issue per slot (RTL as is) | two-beat | 10,346,122 | 647.6 | — |

The block-16 step costs 4.25 AR tokens; the block-8 step costs 2.12. The weight stream is shared across slots, so these extra costs are the ones that grow with B (unit busy, block 16):

- the SU softmax over B × 8,192 scores per head: 0.80 M;
- the two LM-head passes, each in 4-slot pieces because VM holds 4 × 37,984 logits: 0.61 M;
- per-slot RMSNorm records: 0.20 M;
- B-wide all-reduces: 0.45 M.

Software levers that would cut these costs, none of them applied:

- binding `FUSED.SOFTMAX` once CF-SFX passes;
- argmax on the LM-head STREAM with the row scale applied in place;
- ROW_NORM over m rows.

GPU like for like (DFlash Table 3, one B200, c = 1): AR 230 tok/s; DFlash 1,175 tok/s at τ 8.01. On the generic die at the same published τ:

- AR is 951.0 tok/s, 4.13× the GPU's AR.
- DFlash block 16 is 1,793.5 tok/s, 1.53× the GPU's DFlash.
- Block 8 is 2,500.4 tok/s (2.13×), at the anchored τ.
