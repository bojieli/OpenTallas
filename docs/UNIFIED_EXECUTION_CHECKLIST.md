# Unified ABI 3.0 execution checklist

**Checklist ID:** TA-CHK-3.0
**Owner:** single unified implementation agent (no parallel top-level owners)
**Baseline commit:** c83e543
**Issue date:** 2026-08-29
**Last updated:** 2026-08-29, ten parallel workers active
**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done and evidenced · `[!]` blocked/deferred with reason

> This checklist is the single source of truth for program progress. It supersedes
> the per-lane status tables in the four planning documents where they disagree.
> Every `[x]` must name the artifact or test that proves it.

---

## W0 — Architecture freeze and plan repair

- [x] W0.1 Record TA-A3-ARCH-0 disposition (accept ADR-003 + wire format TA-ABI3-WIRE-1) — `docs/TA_A3_ARCH_0_REVIEW_AND_PLAN_REVISION.md`
- [x] W0.2 Revise plans: replace 4-parallel-owner model with unified-owner model — same document, section 4
- [x] W0.3 Freeze the *feasibility-corrected* workload contract (what actually runs, on what hardware, at what boundary) — same document, section 5
- [x] W0.4 Freeze the "engine arithmetic substrate" decision (numpy/torch as engine datapath, not as model) — same document, section 7
- [x] W0.5 Freeze repository ownership paths and module contracts — `runtime/abi3/`, `runtime/sim/`, `compiler/ir/v3/`, `compiler/backends/`

## W1 — ABI 3.0 core (blocking dependency for everything)

- [~] W1.1 `spec/abi3/` normative record definitions (from TA-ABI3-WIRE-1)
- [x] W1.2 `runtime/abi3/` encoder/decoder: program header, 32B instruction, descriptor header + 14 typed payloads — `runtime/abi3/records.py`, `descriptors.py`
- [x] W1.3 Host submission/completion record codec — `runtime/abi3/records.py` Submission/Completion
- [x] W1.4 Capability record + feature-bit registry + counter registry — `runtime/abi3/capability.py`, `runtime/sim/counters.py` (94 counters)
- [x] W1.5 Independent verifier (loop bounds, work bound, branch targets, event/state proofs, permissions, CRC/digests) — `runtime/abi3/verifier.py` (11 proofs)
- [x] W1.6 Deployment manifest + digest binding + signature metadata — `runtime/abi3/deployment.py`
- [x] W1.7 Tiny deterministic fixture lowered through HBM and ROM storage classes; byte-identical rebuild; corruption rejection — `runtime/abi3/fixture.py` — HBM and ROM builds, byte-identical rebuild, 4 corruption classes rejected
- [~] W1.8 Unit tests for every record type and every fail-closed path

## W2 — Neutral IR v3

- [x] W2.1 Model Graph v3 schema (source semantics, phases, state effects, numeric-contract IDs) — `compiler/ir/v3/kernel_ir.py`
- [x] W2.2 Tensor Kernel IR v3 schema (target numerics, iteration domains, tensor views, deps, counter classes) — `compiler/ir/v3/kernel_ir.py` + `lowering.py` (53 kinds mapped)
- [x] W2.3 Neutrality checker (no ROM/HBM/SRAM/stage/queue/address terms in either IR) — `compiler/ir/v3/kernel_ir.py::check_neutral`
- [x] W2.4 Qwen3-8B exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/qwen3.py`; 691 kernels, 1127 tensors, 36 states, all 399 weight bindings verified against 16,381,470,720 real checkpoint bytes; graph_id `65eb209f`
- [~] W2.5 DeepSeek-V4-Flash exporter → Model Graph v3 → Kernel IR v3
- [ ] W2.6 Cross-model operator union report; both exporters pass one schema + verifier

## W3 — Functional simulator (ABI 3.0 device)

- [x] W3.1 Device memory model (HBM/SRAM/ROM/host windows, permissions, mmap-backed weight regions) — `runtime/sim/memory.py` (mmap-backed, strided zero-copy views)
- [x] W3.2 Microsequencer: fetch/decode/retire, loops, predicates, events, waits, fences, traps, completion — `runtime/sim/device.py`
- [x] W3.3 Transactional state engine (prepare/commit/discard, generations, session store) — `runtime/sim/device.py` staged commit
- [x] W3.4 DMA engine (transfer/fill/gather/scatter) — `runtime/sim/engines/dma.py`
- [x] W3.5 Tensor engine — `runtime/sim/engines/tensor.py` + `runtime/sim/formats.py`
- [~] W3.6 Vector engine (rmsnorm, head-rmsnorm, rope, add, silu-mul, convert, scale, softmax, compress, mhc, hadamard, index-score, sqrt-softplus)
- [x] W3.7 Attention engine (dense/GQA/sparse) — `runtime/sim/engines/attention.py`
- [x] W3.8 Route engine — `runtime/sim/engines/route.py`
- [x] W3.9 Reduction engine — `runtime/sim/engines/reduction.py`
- [x] W3.10 Selection engine (argmax, token append, EOS) — `runtime/sim/engines/selection.py`, on-device
- [~] W3.11 Link engine (send/recv/remote-dma/multicast/gather/scatter/collective/barrier) for 32-node + wafer
- [ ] W3.12 Observation/recovery engines + full counter set
- [x] W3.13 Host queue driver — `runtime/driver.py`, real 128-byte submission/completion records per token

## W4 — HBM/SRAM backend (shared chip; 1 node Qwen, 32 nodes DeepSeek)

- [~] W4.1 Physical Plan IR (allocation, tiling, banks, schedules, topology)
- [~] W4.2 Weight/state allocator + HBM address map (mmap-backed, no 16/156 GB copy)
- [~] W4.3 Tiling + loop-nest schedule synthesis (loop-compressed programs)
- [~] W4.4 Descriptor + program emission (ABI 3.0)
- [~] W4.5 Independent legality checker (reconstructs the plan without reusing the generator)
- [ ] W4.6 Qwen single-node deployment
- [ ] W4.7 DeepSeek 32-node sharded deployment (experts, sparse gather, collectives, coordinated commit)

## W5 — ROM backends

- [~] W5.1 Common ROM contracts (immutable regions, repair map, inverse reconstruction)
- [~] W5.2 Qwen conventional single-chip ROM partition + images + schedules + deployment
- [~] W5.3 DeepSeek wafer-scale reticle/tile ROM placement + on-wafer fabric + distributed HBM state + deployment
- [~] W5.4 Inverse proof: ROM image → original weights bit-exact
- [~] W5.5 Independent schedule checker

## W6 — Real end-to-end execution (the correctness spine)

- [ ] W6.1 Qwen-HBM: short prompt → prefill → decode → first EOS, real tokenizer tokens, validated text
- [ ] W6.2 Qwen-ROM: identical token sequence from the ROM deployment
- [ ] W6.3 DeepSeek-HBM (32 node): short prompt → real tokens
- [ ] W6.4 DeepSeek-ROM (wafer): identical token sequence
- [ ] W6.5 Independent reference oracle per model (from official modeling code) — token-level match
- [ ] W6.6 Checkpoint/restart exactness on all four
- [ ] W6.7 Fail-closed campaigns (corrupted program/descriptor/CRC/permission/trap → no partial commit)

## W7 — Cycle model and capability

- [~] W7.1 One event-driven cycle simulator over the same ABI 3.0 artifacts
- [~] W7.2 Capability records for SKY130 view and ASAP7 view (separately versioned)
- [~] W7.3 32-node fabric model (latency, serialization, contention, credits, retry)
- [~] W7.4 Wafer fabric model (reticle/tile routing, congestion, barriers)
- [ ] W7.5 Counter reconciliation: functional == cycle == RTL for the same program

## W8 — RTL 3.0

- [~] W8.1 Microsequencer RTL (fetch/decode/loop/predicate/event/trap/complete)
- [~] W8.2 Queue/event/state controller RTL
- [ ] W8.3 Representative engine datapaths (DMA, tensor MAC array, vector, selection)
- [ ] W8.4 Inter-chip endpoint RTL (packets, credits, retry, collectives)
- [ ] W8.5 ROM service RTL (Qwen chip, DeepSeek wafer tile)
- [~] W8.6 Verilator co-simulation vs functional simulator on generated programs
- [ ] W8.7 Fault/stall/backpressure/reset campaigns

## W9 — Physical (SKY130 implementation view, ASAP7 predictive view)

- [~] W9.1 Inventory available PDKs/tools; record what can actually run offline
- [ ] W9.2 SKY130 synthesis + place/route of RTL 3.0 blocks; area/timing/power
- [ ] W9.3 ASAP7 synthesis (predictive) of the same blocks
- [ ] W9.4 SRAM/ROM macro methodology per view
- [ ] W9.5 Feed characterized capability back into cycle model; recompile; rerun

## W10 — Mandatory workload campaigns

- [ ] W10.1 Qwen exactly 8,000 natural prompt tokens → decode to first EOS (HBM + ROM)
- [ ] W10.2 Qwen repeated-special-token stress run
- [ ] W10.3 Qwen chat workload (pinned template) with question-specific checks
- [ ] W10.4 Qwen agentic workload (model-generated tool calls, sandboxed, fed back)
- [ ] W10.5 DeepSeek long-context campaign (target 200,000; record achieved boundary honestly)
- [ ] W10.6 DeepSeek agentic scenario

## W11 — Governed comparison and release

- [ ] W11.1 TA-CMP-7-SKY130: Qwen ROM vs HBM, DeepSeek ROM-wafer vs HBM-32-node
- [ ] W11.2 TA-CMP-7-ASAP7: same, predictive view, no cross-view mixing
- [ ] W11.3 Evidence ledger: every number traced to executed counters or labeled external
- [ ] W11.4 Final status report and README update

---

## Open issues raised by workers (tracked, not deferred silently)

- **OI-1 — on-device selection numerics are unqualified.** The Qwen exporter
  names `greedy_lowest_token_id_argmax_v1` and `exact_token_append_eos_v1`, but
  no qualification evidence exists for either. ABI 2.5 kept argmax on the host,
  so this is genuinely new numeric surface. Evidence is required before an
  acceptance claim; a differential against the reference oracle's token IDs is
  the natural form.
- **OI-2 — `CheckpointBinding` carries no per-binding checkpoint identity.**
  Model Graph v2's binding carried a `checkpoint_lock_id`; v3 records the lock
  id once in `source`. Acceptable for one-checkpoint graphs, insufficient if a
  graph ever mixes checkpoints. Revisit before any multi-source deployment.
- **OI-3 — `Tensor` has no layout field.** Head-shaped views rely on row-major
  equivalence between `(tokens, heads, head_dim)` and `(tokens, heads*head_dim)`.
  True today; would break for any non-row-major source tensor.
