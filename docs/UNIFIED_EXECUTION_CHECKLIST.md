# Unified ABI 3.0 execution checklist

**Checklist ID:** TA-CHK-3.0
**Owner:** single unified implementation agent (no parallel top-level owners)
**Baseline commit:** c83e543
**Issue date:** 2026-08-29
**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done and evidenced · `[!]` blocked/deferred with reason

> This checklist is the single source of truth for program progress. It supersedes
> the per-lane status tables in the four planning documents where they disagree.
> Every `[x]` must name the artifact or test that proves it.

---

## W0 — Architecture freeze and plan repair

- [ ] W0.1 Record TA-A3-ARCH-0 disposition (accept ADR-003 + wire format TA-ABI3-WIRE-1)
- [ ] W0.2 Revise plans: replace 4-parallel-owner model with unified-owner model
- [ ] W0.3 Freeze the *feasibility-corrected* workload contract (what actually runs, on what hardware, at what boundary)
- [ ] W0.4 Freeze the "engine arithmetic substrate" decision (numpy/torch as engine datapath, not as model)
- [ ] W0.5 Freeze repository ownership paths and module contracts

## W1 — ABI 3.0 core (blocking dependency for everything)

- [ ] W1.1 `spec/abi3/` normative record definitions (from TA-ABI3-WIRE-1)
- [ ] W1.2 `runtime/abi3/` encoder/decoder: program header, 32B instruction, descriptor header + 14 typed payloads
- [ ] W1.3 Host submission/completion record codec
- [ ] W1.4 Capability record + feature-bit registry + counter registry
- [ ] W1.5 Independent verifier (loop bounds, work bound, branch targets, event/state proofs, permissions, CRC/digests)
- [ ] W1.6 Deployment manifest + digest binding + signature metadata
- [ ] W1.7 Tiny deterministic fixture lowered through HBM and ROM storage classes; byte-identical rebuild; corruption rejection
- [ ] W1.8 Unit tests for every record type and every fail-closed path

## W2 — Neutral IR v3

- [ ] W2.1 Model Graph v3 schema (source semantics, phases, state effects, numeric-contract IDs)
- [ ] W2.2 Tensor Kernel IR v3 schema (target numerics, iteration domains, tensor views, deps, counter classes)
- [ ] W2.3 Neutrality checker (no ROM/HBM/SRAM/stage/queue/address terms in either IR)
- [ ] W2.4 Qwen3-8B exporter → Model Graph v3 → Kernel IR v3
- [ ] W2.5 DeepSeek-V4-Flash exporter → Model Graph v3 → Kernel IR v3
- [ ] W2.6 Cross-model operator union report; both exporters pass one schema + verifier

## W3 — Functional simulator (ABI 3.0 device)

- [ ] W3.1 Device memory model (HBM/SRAM/ROM/host windows, permissions, mmap-backed weight regions)
- [ ] W3.2 Microsequencer: fetch/decode/retire, loops, predicates, events, waits, fences, traps, completion
- [ ] W3.3 Transactional state engine (prepare/commit/discard, generations, session store)
- [ ] W3.4 DMA engine (transfer/fill/gather/scatter)
- [ ] W3.5 Tensor engine (BF16/FP8-E4M3FN/MXFP4-E2M1+E8M0; matmul/grouped/routed/embed)
- [ ] W3.6 Vector engine (rmsnorm, head-rmsnorm, rope, add, silu-mul, convert, scale, softmax, compress, mhc, hadamard, index-score, sqrt-softplus)
- [ ] W3.7 Attention engine (dense/GQA/sparse)
- [ ] W3.8 Route engine (topk, biased topk, weight-normalize, expert dispatch, index topk, hash route, window index)
- [ ] W3.9 Reduction engine (ordered sum, expert sum, vocab gather, grouped concat, partition sum)
- [ ] W3.10 Selection engine (argmax, token append, EOS) — on-device, no host argmax
- [ ] W3.11 Link engine (send/recv/remote-dma/multicast/gather/scatter/collective/barrier) for 32-node + wafer
- [ ] W3.12 Observation/recovery engines + full counter set
- [ ] W3.13 Host queue driver (capability, load/activate, session, generate, checkpoint/restore)

## W4 — HBM/SRAM backend (shared chip; 1 node Qwen, 32 nodes DeepSeek)

- [ ] W4.1 Physical Plan IR (allocation, tiling, banks, schedules, topology)
- [ ] W4.2 Weight/state allocator + HBM address map (mmap-backed, no 16/156 GB copy)
- [ ] W4.3 Tiling + loop-nest schedule synthesis (loop-compressed programs)
- [ ] W4.4 Descriptor + program emission (ABI 3.0)
- [ ] W4.5 Independent legality checker (reconstructs the plan without reusing the generator)
- [ ] W4.6 Qwen single-node deployment
- [ ] W4.7 DeepSeek 32-node sharded deployment (experts, sparse gather, collectives, coordinated commit)

## W5 — ROM backends

- [ ] W5.1 Common ROM contracts (immutable regions, repair map, inverse reconstruction)
- [ ] W5.2 Qwen conventional single-chip ROM partition + images + schedules + deployment
- [ ] W5.3 DeepSeek wafer-scale reticle/tile ROM placement + on-wafer fabric + distributed HBM state + deployment
- [ ] W5.4 Inverse proof: ROM image → original weights bit-exact
- [ ] W5.5 Independent schedule checker

## W6 — Real end-to-end execution (the correctness spine)

- [ ] W6.1 Qwen-HBM: short prompt → prefill → decode → first EOS, real tokenizer tokens, validated text
- [ ] W6.2 Qwen-ROM: identical token sequence from the ROM deployment
- [ ] W6.3 DeepSeek-HBM (32 node): short prompt → real tokens
- [ ] W6.4 DeepSeek-ROM (wafer): identical token sequence
- [ ] W6.5 Independent reference oracle per model (from official modeling code) — token-level match
- [ ] W6.6 Checkpoint/restart exactness on all four
- [ ] W6.7 Fail-closed campaigns (corrupted program/descriptor/CRC/permission/trap → no partial commit)

## W7 — Cycle model and capability

- [ ] W7.1 One event-driven cycle simulator over the same ABI 3.0 artifacts
- [ ] W7.2 Capability records for SKY130 view and ASAP7 view (separately versioned)
- [ ] W7.3 32-node fabric model (latency, serialization, contention, credits, retry)
- [ ] W7.4 Wafer fabric model (reticle/tile routing, congestion, barriers)
- [ ] W7.5 Counter reconciliation: functional == cycle == RTL for the same program

## W8 — RTL 3.0

- [ ] W8.1 Microsequencer RTL (fetch/decode/loop/predicate/event/trap/complete)
- [ ] W8.2 Queue/event/state controller RTL
- [ ] W8.3 Representative engine datapaths (DMA, tensor MAC array, vector, selection)
- [ ] W8.4 Inter-chip endpoint RTL (packets, credits, retry, collectives)
- [ ] W8.5 ROM service RTL (Qwen chip, DeepSeek wafer tile)
- [ ] W8.6 Verilator co-simulation vs functional simulator on generated programs
- [ ] W8.7 Fault/stall/backpressure/reset campaigns

## W9 — Physical (SKY130 implementation view, ASAP7 predictive view)

- [ ] W9.1 Inventory available PDKs/tools; record what can actually run offline
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
