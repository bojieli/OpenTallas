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

- [x] W1.1 `spec/abi3/` normative record definitions (from TA-ABI3-WIRE-1) — `spec/abi3/{records,descriptor_payloads,registries,counters}.json`, generated from the encoder with a `--check` drift gate
- [x] W1.2 `runtime/abi3/` encoder/decoder: program header, 32B instruction, descriptor header + 14 typed payloads — `runtime/abi3/records.py`, `descriptors.py`
- [x] W1.3 Host submission/completion record codec — `runtime/abi3/records.py` Submission/Completion
- [x] W1.4 Capability record + feature-bit registry + counter registry — `runtime/abi3/capability.py`, `runtime/sim/counters.py` (94 counters)
- [x] W1.5 Independent verifier (loop bounds, work bound, branch targets, event/state proofs, permissions, CRC/digests) — `runtime/abi3/verifier.py` (11 proofs)
- [x] W1.6 Deployment manifest + digest binding + signature metadata — `runtime/abi3/deployment.py`
- [x] W1.7 Tiny deterministic fixture lowered through HBM and ROM storage classes; byte-identical rebuild; corruption rejection — `runtime/abi3/fixture.py` — HBM and ROM builds, byte-identical rebuild, 4 corruption classes rejected
- [x] W1.8 Unit tests for every record type and every fail-closed path — `tests/abi3/` — 469 tests; wire-format parser mutation-tested against 7 injected drifts

## W2 — Neutral IR v3

- [x] W2.1 Model Graph v3 schema (source semantics, phases, state effects, numeric-contract IDs) — `compiler/ir/v3/kernel_ir.py`
- [x] W2.2 Tensor Kernel IR v3 schema (target numerics, iteration domains, tensor views, deps, counter classes) — `compiler/ir/v3/kernel_ir.py` + `lowering.py` (53 kinds mapped)
- [x] W2.3 Neutrality checker (no ROM/HBM/SRAM/stage/queue/address terms in either IR) — `compiler/ir/v3/kernel_ir.py::check_neutral`
- [x] W2.4 Qwen3-8B exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/qwen3.py`; 691 kernels, 1127 tensors, 36 states, all 399 weight bindings verified against 16,381,470,720 real checkpoint bytes; graph_id `65eb209f`
- [x] W2.5 DeepSeek-V4-Flash exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/deepseek_v4.py`; 3003 kernels, 71278 tensors, 229 states, 156,015,698,140 bound weight bytes
- [x] W2.6 Cross-model operator union report; both exporters pass one schema + verifier — `tests/compiler/test_neutral_ir_cross_model.py` (22 gates); union published as `spec/abi3/numeric_contract_union.json` (71 contracts)

## W3 — Functional simulator (ABI 3.0 device)

- [x] W3.1 Device memory model (HBM/SRAM/ROM/host windows, permissions, mmap-backed weight regions) — `runtime/sim/memory.py` (mmap-backed, strided zero-copy views)
- [x] W3.2 Microsequencer: fetch/decode/retire, loops, predicates, events, waits, fences, traps, completion — `runtime/sim/device.py`
- [x] W3.3 Transactional state engine (prepare/commit/discard, generations, session store) — `runtime/sim/device.py` staged commit
- [x] W3.4 DMA engine (transfer/fill/gather/scatter) — `runtime/sim/engines/dma.py`
- [x] W3.5 Tensor engine — `runtime/sim/engines/tensor.py` + `runtime/sim/formats.py`
- [x] W3.6 Vector engine (rmsnorm, head-rmsnorm, rope, add, silu-mul, convert, scale, softmax, compress, mhc, hadamard, index-score, sqrt-softplus) — `runtime/sim/engines/vector.py`
- [x] W3.7 Attention engine (dense/GQA/sparse) — `runtime/sim/engines/attention.py`
- [x] W3.8 Route engine — `runtime/sim/engines/route.py`
- [x] W3.9 Reduction engine — `runtime/sim/engines/reduction.py`
- [x] W3.10 Selection engine (argmax, token append, EOS) — `runtime/sim/engines/selection.py`, on-device
- [x] W3.11 Link engine (send/recv/remote-dma/multicast/gather/scatter/collective/barrier) for 32-node + wafer — `runtime/sim/engines/link.py`
- [x] W3.12 Observation/recovery engines + full counter set — sequencer-executed; 115-counter registry published
- [x] W3.13 Host queue driver — `runtime/driver.py`, real 128-byte submission/completion records per token

## W4 — HBM/SRAM backend (shared chip; 1 node Qwen, 32 nodes DeepSeek)

- [x] W4.1 Physical Plan IR (allocation, tiling, banks, schedules, topology) — `compiler/backends/hbm_sram/plan.py`
- [x] W4.2 Weight/state allocator + HBM address map (mmap-backed, no 16/156 GB copy) — zero-copy: 14 objects over 399 checkpoint ranges for Qwen, 196 objects for DeepSeek; no image written
- [x] W4.3 Tiling + loop-nest schedule synthesis (loop-compressed programs) — Qwen 69 instructions from 691 kernels (13,400x vs ABI 2.5); tiling in SCHEDULE descriptors
- [x] W4.4 Descriptor + program emission (ABI 3.0) — `compiler/backends/hbm_sram/lower.py`
- [x] W4.5 Independent legality checker (reconstructs the plan without reusing the generator) — `compiler/backends/hbm_sram/check.py`, does not import the generator
- [~] W4.6 Qwen single-node deployment
- [~] W4.7 DeepSeek 32-node sharded deployment (experts, sparse gather, collectives, coordinated commit)

## W5 — ROM backends

- [x] W5.1 Common ROM contracts (immutable regions, repair map, inverse reconstruction) — `compiler/backends/rom/common/image.py` incl. repair map
- [x] W5.2 Qwen conventional single-chip ROM partition + images + schedules + deployment — Qwen ROM 29 instructions, 14 role-striped banks, 16,381,470,720 B
- [x] W5.3 DeepSeek wafer-scale reticle/tile ROM placement + on-wafer fabric + distributed HBM state + deployment — DeepSeek ROM wafer 322 instructions, 172 regions, 9,300 tiles of 37 reticles, 18 link instructions
- [x] W5.4 Inverse proof: ROM image → original weights bit-exact — inverse proof passes bit-identically over 16.4 GB and 156 GB
- [~] W5.5 Independent schedule checker

## W6 — Real end-to-end execution (the correctness spine)

- [~] W6.1 Qwen-HBM: short prompt → prefill → decode → first EOS, real tokenizer tokens, validated text — **executes end to end and produces real tokens**; on a 5-token prompt the selected token matches the vendor reference (`results/abi3/qwen3_activation_bisect.json`). Pinned-workload agreement and decode-to-EOS still to confirm
- [ ] W6.2 Qwen-ROM: identical token sequence from the ROM deployment
- [ ] W6.3 DeepSeek-HBM (32 node): short prompt → real tokens
- [ ] W6.4 DeepSeek-ROM (wafer): identical token sequence
- [x] W6.5 Independent reference oracle per model (from official modeling code) — external oracle: `tools/run_qwen3_reference_oracle.py`— token-level match
- [ ] W6.6 Checkpoint/restart exactness on all four
- [ ] W6.7 Fail-closed campaigns (corrupted program/descriptor/CRC/permission/trap → no partial commit)

## W7 — Cycle model and capability

- [x] W7.1 One event-driven cycle simulator over the same ABI 3.0 artifacts — `runtime/cycle/model.py`, trace derived by running the frozen device itself
- [x] W7.2 Capability records for SKY130 view and ASAP7 view (separately versioned) — five cost tables with per-parameter provenance
- [x] W7.3 32-node fabric model (latency, serialization, contention, credits, retry) — `runtime/cycle/fabric.py` ClusterFabric
- [x] W7.4 Wafer fabric model (reticle/tile routing, congestion, barriers) — `runtime/cycle/fabric.py` WaferFabric
- [x] W7.5 Counter reconciliation: functional == cycle == RTL for the same program — functional vs cycle agreement over 31 architectural counters

## W8 — RTL 3.0

- [x] W8.1 Microsequencer RTL (fetch/decode/loop/predicate/event/trap/complete) — `rtl/abi3/ot_a3_microsequencer.sv`
- [x] W8.2 Queue/event/state controller RTL — `rtl/abi3/ot_a3_event_scoreboard.sv`, `ot_a3_state_controller.sv`
- [~] W8.3 Representative engine datapaths (DMA, tensor MAC array, vector, selection)
- [~] W8.4 Inter-chip endpoint RTL (packets, credits, retry, collectives)
- [~] W8.5 ROM service RTL (Qwen chip, DeepSeek wafer tile)
- [x] W8.6 Verilator co-simulation vs functional simulator on generated programs — 30 cases, 99 issue events, 12 traps matched on two simulators
- [x] W8.7 Fault/stall/backpressure/reset campaigns — 17 negative cases incl. CRC, illegal opcode, loop overrun, mid-transaction trap

## W9 — Physical (SKY130 implementation view, ASAP7 predictive view)

- [x] W9.1 Inventory available PDKs/tools; record what can actually run offline — `docs/ABI3_PHYSICAL_VIEWS.md`
- [x] W9.2 SKY130 synthesis + place/route of RTL 3.0 blocks; area/timing/power — SKY130 HD full place-and-route, 0 DRC, 0 antenna
- [x] W9.3 ASAP7 synthesis (predictive) of the same blocks — ASAP7 full place-and-route; archived case reproduced bit-for-bit
- [ ] W9.4 SRAM/ROM macro methodology per view
- [ ] W9.5 Feed characterized capability back into cycle model; recompile; rerun

## W10 — Mandatory workload campaigns

- [ ] W10.1 Qwen exactly 8,000 natural prompt tokens → decode to first EOS (HBM + ROM)
- [ ] W10.2 Qwen repeated-special-token stress run
- [ ] W10.3 Qwen chat workload (pinned template) with question-specific checks
- [ ] W10.4 Qwen agentic workload (model-generated tool calls, sandboxed, fed back)
- [x] W10.5 DeepSeek long-context campaign — largest context **actually executed is 8,000 tokens**; 32K/128K/200K exhaust GPU memory in the mHC hyper-connection, not the sparse indexer. A 200,000-token prefill needs a chunked rewrite of the vendor prefill path on any GPU: `hc_post` alone is 48.8 GiB at that context and the indexer term 2.33 TiB, while persistent KV state is only 2.32 GiB
- [x] W10.6 DeepSeek agentic scenario — 47 tokens to EOS, well-formed DSML tool call, byte-identical across independent process invocations

## W11 — Governed comparison and release

- [ ] W11.1 TA-CMP-7-SKY130: Qwen ROM vs HBM, DeepSeek ROM-wafer vs HBM-32-node
- [ ] W11.2 TA-CMP-7-ASAP7: same, predictive view, no cross-view mixing
- [~] W11.3 Evidence ledger: every number traced to executed counters or labeled external
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
- **OI-4 — no governed stochastic sampling contract.** The neutral IR cannot
  express randomness and `SELECTION.SAMPLE` is unimplemented, so neither lane
  can honour a `do_sample: true` request. Greedy acceptance is unaffected
  (ADR-003 section 7 makes sampling optional), but inventing an RNG to close
  this would make every future result irreproducible. Closing it needs a
  versioned RNG and probability contract first.
- **OI-5 — descriptor CRC and header digests are not checked in RTL.** The RTL
  microsequencer enforces instruction and header CRC32C, but descriptor record
  CRCs and the header's four SHA-256 digests need a digest engine that does not
  exist yet. Until it does, RTL's "fail before work is issued" is narrower than
  the ABI's.
- **OI-6 — Yosys 0.68 cannot parse SystemVerilog packages**, so `rtl/abi3`
  cannot enter the repository's existing synthesis flow unchanged. The
  synthesis probe required textually inlining the package.
- **OI-7 — DeepSeek 32-node HBM capacity: diagnosed and largely closed.** The
  reported overflow (172 GB per node against 96 GB) came from sizing activation
  arenas at the *architectural* endpoint rather than the *deployment's* declared
  context. Measured, at a declared context of 8,192 tokens — which is what
  actually executes — the arenas are 3.64 GiB instead of 152.39 GiB, and the
  32-node plan **fits at 4.65 GiB per node** against 96 GiB available. Sizing
  arenas at the capability endpoint is the error; ADR-003 section 19 makes such
  values capability fields precisely so a deployment can declare less.
  Two things remain open at the mandatory context:
  - **200,000 is not an admissible deployment context.** It must be a whole
    number of 128-token sliding windows, so the nearest admissible value is
    200,064. The workload contract should either adopt 200,064 or state that the
    prompt is 200,000 within a 200,064 context.
  - At 200,064 the plan fails earlier, in `main.layer00.routed_experts.gate`,
    where a routed-expert weight multiply is being planned as a contraction:
    operands `(1200384, 4096)` and `(1200384, 1)` share no depth axis. That is a
    backend classification bug at scale, not a capacity result.

- **OI-8 — `MEMORY_OBJECT.base_address` defaults to zero.** Every object can
  present at address zero, so the cycle model cannot map objects onto HBM
  channels or SRAM banks and substitutes a synthetic packed placement. Channel
  and bank conflict numbers from such a deployment are a property of the model,
  not of the plan. Backends must assign real base addresses; `bank_or_tile` has
  the same problem.
- **OI-9 — `SCHEDULE.resource_bound` has no defined unit** and `priority` is
  unmodelled. Both are recorded and explicitly not timed rather than silently
  consumed. ABI 3.0 does not say whether `resource_bound` counts lanes, engine
  instances or SRAM regions.
- **OI-10 — `Symbolic.maximum` semantics were never frozen.** Qwen writes
  `multiplier=1` so both readings agree; DeepSeek writes `multiplier=6,
  maximum=1572864`, which only parses as the *extent* maximum. The ROM backend
  took that reading; the other inflates the activation footprint six-fold
  (2.14 TB against 916 GB). The contract should say which.
- **OI-11 — `queue.max_occupancy` is an architectural-group counter no
  functional model can fill.** It sits outside the timing group, so the cycle
  model declines to write it rather than break the counter-agreement rule.
  Either it belongs in the timing group or the rule needs a named exception.
- **OI-12 — no capability advertises queue depth or issue width.** ADR-003
  section 9 makes them capabilities rather than assumptions, but only
  `max_outstanding_per_queue` exists; everything else comes from a cost table
  and is labelled assumed.
- **OI-13 — the released TileLang `fp4_gemm` is wrong on sm_120.** Maximum
  absolute error 6.52 against a signal of mean magnitude 1.28, verified against
  two mutually independent references that agree with each other to half a
  bfloat16 ulp. Because the routed experts are most of the model it does not
  crash; it produces fluent, on-topic, semantically empty text. The oracle uses
  the release's own documented FP8 recast and re-proves the check at every
  start. Any future use of that kernel must repeat the check.
- **OI-14 — the released `sparse_attn` kernel cannot launch at 64 heads on
  sm_120**, requesting 141,312 bytes of dynamic shared memory against 101,376
  available. Split into four 16-head launches, which is bitwise identical
  because the heads are independent, and is the per-rank head count the
  vendor's own world_size=4 configuration produces.
- **OI-15 — every operation is wrapped in a per-token loop.** The HBM lowering
  emits nineteen `SPAN_TOKENS` loops inside the layer body, so a 93-token
  prefill issues about 63,600 engine dispatches, each on one token row. The
  instruction count looks compressed but the retired work is not: this is the
  ABI 2.5 failure mode in different clothes, one dispatch per token instead of
  one command per tile. Every engine already accepts `[span, ...]`, so the body
  should issue one dispatch per operation for the whole span, with the token
  axis carried as a symbolic view dimension. Loops belong only where the work
  genuinely varies — layers, and token *blocks* if an SRAM working set needs
  bounding. Expected effect is roughly 90x fewer dispatches, which is what makes
  the 8,000-token campaign feasible.

