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

- [x] W6.1 Qwen-HBM: short prompt → prefill → decode → real tokens — **token-identical to the reference oracle**, and **decode reaches a real EOS**. `TA-QW-AGENT-1` ran 112 prompt tokens to the natural stop at token 151645 after 23 tokens (`results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json`), `TA-QW-CHAT-1` ran 24 tokens (`..._ta-qw-chat-1_...`); both agree with the oracle at every position, with no legitimacy problems and all 27 admission checks passing
- [~] W6.2 Qwen-ROM: identical token sequence from the ROM deployment — **reported, being re-verified with persisted evidence** (the reporting run left no artifact in `results/`, so the claim below is not yet checkable in this repository) — 75 instructions, 239 descriptors, admitted; **24 tokens token-for-token identical to the external oracle and to the HBM target**. All 27 distinct prefill kernels diffed kernel-by-kernel against HBM through the `on_issue` hook: bit-identical, output hash for output hash, including the KV window and the final logits. Storage-class equivalence re-proved after every change: 18 descriptors differ, all `MEMORY_OBJECT`, all ROM→HBM, none beyond storage class
- [ ] W6.3 DeepSeek-HBM (32 node): short prompt → real tokens — **no tokens yet, and two of the three remaining blockers are decisions, not bugs.** The deployment admits (996 instructions, 2,307 descriptors, work bound proved exactly) and `HYPER_CONNECT_PRE` now executes against the frozen `VECTOR.MHC` operand row. It stops at the branch reduction the ABI leaves to `REDUCTION.EXPERT_SUM`, which provably cannot carry per-token weights over a token block (**OI-28**). Behind that: the functional simulator binds no `NODE_ID`, so the mandated 32-node capability cannot execute at all (**OI-27**), and the `attention_kv_view` row space needs an extent no view can present (**OI-26**). Landed on the way: the mHC pre/post split, the axis-1 index concatenations (**OI-20**), and two contract-naming defects (**OI-29**)
- [ ] W6.4 DeepSeek-ROM (wafer): identical token sequence
- [x] W6.5 Independent reference oracle per model (from official modeling code) — external oracle: `tools/run_qwen3_reference_oracle.py`— token-level match
- [~] W6.6 Checkpoint/restart exactness on all four — **Qwen-HBM proven; the other three wait on W6.2-W6.4**. `tools/run_abi3_restart_exactness.py` runs one workload three times in three separate OS processes: uninterrupted; interrupted after N tokens with the device state serialised by `runtime/sim/checkpoint.py`; and finished in a fresh process that loads only that checkpoint. `TA-QW-CHAT-1` on `torch_cpu`, 93 prompt tokens, 6 new tokens split 3+3: both runs give `[1654, 525, 2661, 1447, 12, 3070]`, with identical retired work in every transaction and identical values for all 42 architectural counters (`results/abi3/restart_exactness.json`). Fifteen guards stand between the run and the word *pass* — three distinct PIDs, one deployment digest, one implementation identity, one runtime source digest, and explicit non-emptiness and length checks, because two empty lists are not a match. Two controls make the pass mean something: erasing the KV STATE images from the checkpoint diverges at the first resumed token, and erasing everything **except** the STATE images still reproduces the sequence, so what carries the generation is the STATE resources and the cursor, not activation scratch. The source-digest guard earned itself on its first run, refusing a token-identical result because a concurrent commit changed `runtime/` between two phases
- [x] W6.7 Fail-closed campaigns — `tools/run_abi3_failclosed_campaign.py`, 8/8 refused against the **real** Qwen deployment: six corruption classes refused at admission, a mid-transaction fault leaving cursor and generation unchanged, and no prepared state left open. Found and fixed a real defect on its first run

## W7 — Cycle model and capability

- [x] W7.1 One event-driven cycle simulator over the same ABI 3.0 artifacts — `runtime/cycle/model.py`, trace derived by running the frozen device itself
- [x] W7.2 Capability records for SKY130 view and ASAP7 view (separately versioned) — five cost tables with per-parameter provenance
- [x] W7.3 32-node fabric model (latency, serialization, contention, credits, retry) — `runtime/cycle/fabric.py` ClusterFabric
- [x] W7.4 Wafer fabric model (reticle/tile routing, congestion, barriers) — `runtime/cycle/fabric.py` WaferFabric
- [x] W7.5 Counter reconciliation: functional == cycle == RTL for the same program — functional vs cycle agreement over 31 architectural counters

## W8 — RTL 3.0

- [x] W8.1 Microsequencer RTL (fetch/decode/loop/predicate/event/trap/complete) — `rtl/abi3/ot_a3_microsequencer.sv`; operand tensor-view resolution (A4 dynamic terms, A13 partial final extent) — `rtl/abi3/ot_a3_view_resolver.sv`
- [x] W8.2 Queue/event/state controller RTL — `rtl/abi3/ot_a3_event_scoreboard.sv`, `ot_a3_state_controller.sv`
- [~] W8.3 Representative engine datapaths (DMA, tensor MAC array, vector, selection)
- [~] W8.4 Inter-chip endpoint RTL (packets, credits, retry, collectives)
- [~] W8.5 ROM service RTL (Qwen chip, DeepSeek wafer tile)
- [x] W8.6 Verilator co-simulation vs functional simulator on generated programs — 41 cases, 135 issue events, 354 resolved tensor views (amendments A4 and A13), 11 traps matched on two simulators, 2,903 checks each
- [x] W8.7 Fault/stall/backpressure/reset campaigns — 17 negative cases incl. CRC, illegal opcode, loop overrun, mid-transaction trap

## W9 — Physical (SKY130 implementation view, ASAP7 predictive view)

- [x] W9.1 Inventory available PDKs/tools; record what can actually run offline — `docs/ABI3_PHYSICAL_VIEWS.md`
- [x] W9.2 SKY130 synthesis + place/route of RTL 3.0 blocks; area/timing/power — SKY130 HD full place-and-route, 0 DRC, 0 antenna
- [x] W9.3 ASAP7 synthesis (predictive) of the same blocks — ASAP7 full place-and-route; archived case reproduced bit-for-bit
- [ ] W9.4 SRAM/ROM macro methodology per view
- [ ] W9.5 Feed characterized capability back into cycle model; recompile; rerun

## W10 — Mandatory workload campaigns

- [ ] W10.1 Qwen exactly 8,000 natural prompt tokens → decode to first EOS (HBM + ROM) — **blocked on OI-21**, not on anything architectural: the deployment admits and the oracle for this workload exists, but prefill attention as implemented needs ~26 h for an 8,000-token prompt. Started, measured, stopped at 43 min
- [ ] W10.2 Qwen repeated-special-token stress run — same 8,000-token prompt, so **blocked on OI-21** for the same reason
- [x] W10.3 Qwen chat workload (pinned template) — `TA-QW-CHAT-1`, 93 prompt tokens, 24 decoded tokens, token-identical to the oracle; the model is mid-derivation at the token cap (`We are given:\n\n- **Ship 1** (from Port A) leaves at **06:00**`), so this record proves token fidelity, not answer correctness, and W10.1 carries the run to EOS
- [x] W10.4 Qwen agentic workload — `TA-QW-AGENT-1` decoded a **complete, well-formed tool call and stopped at a real EOS** entirely on the accelerator: ```bash / awk -F',' '{sum += $2} END {print sum}' inventory.txt / ```. Token-identical to the oracle. Feeding the result back through the sandbox loop is `tools/run_qwen3_agent_episode.py`
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
- **OI-7 — DeepSeek 32-node HBM capacity: closed for the deployment profile.**
  Two profiles are now built: `kernel_ir.v3.json` declares an 8,192-token
  context, which is what actually executes and what fits the 32-node cluster,
  and `kernel_ir.v3.capacity200k.json` declares 200,064 for capacity study.
  Original diagnosis follows. The
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
- **OI-16 — closed. RTL implements amendment A13.** `rtl/abi3/ot_a3_view_resolver.sv`
  resolves a tensor view's A4 dynamic index terms and its A13 partial final
  extent, and `ot_a3_microsequencer.sv` runs it over every operand view of an
  OPERATOR-family instruction before that instruction issues, publishing the
  resolved extent and element offset on a view port. The descriptor image now
  carries 192 bytes per record rather than 128, because a TENSOR_VIEW's dynamic
  terms start at payload offset 72 and a 128-byte prefix stopped one block
  short. The correlation campaign compares 354 resolved views against
  `runtime.sim.memory.ViewResolver.resolve` — the functional device's own
  resolver, evaluated against the loop bindings the device recorded at each
  issue — over eleven new vectors covering N divisible by T, N with a partial
  final iteration, N < T, N = 0, a constant-bounded loop, nested block loops
  folded by `min()`, and the A4 maximum of four dynamic terms. Three deliberate
  mutations of the RTL rule — removing the clamp, using the prose formula of
  section 12.4 verbatim, and narrowing the term counter so a four-term view
  wraps — are each rejected by both simulators, so the vectors are not
  vacuous.
- **OI-16a — wire format section 12.4's prose formula is narrower than the
  reference resolver, and the resolver is normative.** Section 12.4 states
  `dim0 = remaining if 0 < remaining < dim0 else dim0`.
  `ViewResolver._remaining_rows` additionally requires `remaining <
  bound_divisor` before a loop bounds anything, and folds several
  symbol-bounded loops over one view with `min()`. The two disagree only when a
  view's leading extent exceeds the block size: with `bound_divisor = 4`,
  `dim0 = 6` and `SPAN_TOKENS = 5`, the resolver leaves `dim0 = 6` and the
  prose formula gives 5. The RTL follows the resolver, and vector
  `a13_extent_above_block` pins the disagreement so it cannot drift silently.
  Nothing in `runtime/abi3/` was changed; if the intent is the prose reading,
  the resolver is the place to decide it.
- **OI-16b — the RTL lagged commit 46b6fb5 on abort accounting.** That commit
  made an abort discard the whole *declared* prepared state set
  (`counters.add("state.discards", len(session.states))`), which the RTL's
  state controller did not do: it counted only STATE.DISCARD instructions. The
  divergence was invisible because the checked-in vectors predated the commit
  and nobody had regenerated them. `ot_a3_state_controller.sv` now takes a
  `session_state_count` and adds it on `discard_all`, and the case record
  carries the deployment's STATE-descriptor count.
- **OI-16c — the vector generator could not regenerate its own vectors.** Since
  the verifier gained its schedule-completeness proof, `Workspace` in
  `tools/build_abi3_rtl_vectors.py` was rejected for reusing one TENSOR
  SCHEDULE descriptor across every engine family. It now creates one schedule
  per family. Separately, `case_work_bound_deficit` documented a work-bound
  deficit that `DeploymentBuilder._proved_work` has since repaired, so the case
  no longer traps; the work-bound trap is still covered by
  `case_work_bound`.
- **OI-17 — the ABI 2.5 retained deployment cannot load in a fresh checkout.**
  Four `tests/runtime` tests fail with "deployment file set differs from the
  final manifest": the manifest names 31 files and 13 are present, the missing
  18 being the multi-gigabyte `memory/hbm/hbm.*.bin` images that were never
  tracked. This is pre-existing and unrelated to ABI 3.0 - the failing lane
  imports neither `runtime.sim` nor `runtime.abi3` - but it means those four
  tests fail on any clone, so either the loader should distinguish "artifact not
  built" from "artifact corrupted", or the tests should skip when the images are
  absent.


- **OI-18 — a campaign run writes its deployment into the checkpoint
  directory.** `tools/run_abi3_campaign.py` uses `--deployment-root` both to
  resolve the checkpoint's relative weight paths *and* as the place to publish
  `program.bin`, `descriptors.bin` and `deployment.json`. Running a Qwen
  campaign therefore drops 104 KB into the user's Hugging Face cache. It is
  small and it is not a weight image — zero-copy holds — but a read-only
  checkpoint, a read-only mount, or a cache the user cleans between runs would
  each break it for a reason that has nothing to do with the deployment. The
  publish target should be a separate argument defaulting to `build/abi3/<id>/`,
  with the checkpoint root used only for reading.

- **OI-25 — fourteen test files still validate the retired ABI 2.5 lane, and
  one of them fails.** `tests/compiler/test_tensor_accelerator_qwen_rtl_rope.py`
  fails `test_rope_builder_reproduces_retained_artifact` — and it fails on a
  clean checkout of HEAD, so it predates tonight's work. It rebuilds a vector
  artifact from `results/tensor_accelerator/qwen3_full_model_physical/ir/tensor_kernel_ir.json`
  (the ABI 2.5 IR, not `build/ir-v3/qwen3-8b/kernel_ir.v3.json`) and from a
  second repository at `/home/ubuntu/OpenTallas-ta-integration/`. Thirteen more
  files in `tests/compiler/test_tensor_accelerator_qwen_*.py` have the same two
  dependencies.

  Whether they pass tells us nothing about ABI 3.0: they exercise a pipeline
  this program has replaced, from inputs that are not the shared IR. **The lane
  should be quarantined** — moved to a clearly named directory with a note that
  it is superseded — so that no reader takes a green tick there as evidence for
  the new ABI, and so a red one is not mistaken for an ABI 3.0 regression.

  I have deliberately *not* silenced the failing test. Skipping the one that
  happens to be red, while leaving thirteen green ones making claims about a
  retired lane, would make the suite look better and the repository less honest.
  The quarantine is a single coherent change and belongs in one commit, once the
  concurrent backend work has settled. Related to [OI-17], which is the same
  lane failing for a different reason.

- **OI-29 — the measured DeepSeek prefill ladder, and two defects closed off
  it.** Because OI-28 stops the real graph at the third kernel, the rest of the
  prefill was walked with a *diagnostic* graph in which the branch reduction is
  replaced by a `SELECT` of stream 0 — structurally identical, numerically
  wrong, never published — on the single-chip capability (OI-27 rules out the
  cluster). It admits (911 instructions, 2,114 descriptors) and fails in this
  order:

  1. `numeric profile 418 names no RMSNorm contract this engine implements` —
     **closed.** Amendment A8 gives the vector engine two RMSNorm contracts and
     it dispatches on the one the NUMERIC descriptor names. The DeepSeek
     exporter names its own qualified source identity,
     `normalization_rms_norm_bf16_v1`; the arithmetic it denotes is
     `deepseek_rmsnorm_binary32_v1`, qualified in
     `results/abi3/numeric_contract_qualification.json`. Naming the execution
     contract is what `EXECUTION_CONTRACT` in the HBM lowering exists for.
     Qwen names `qwen3_rmsnorm_fp32_bf16_v1` and is untouched.
  2. `numeric profile 456 declares epsilon 0x358637bd; the unweighted head
     RMSNorm contract requires the BF16 encoding 0x3586` — **closed.** The
     released *unweighted* head norm is qualified against
     `head_rms_norm_bf16`, which takes a BF16 epsilon code because the kernel
     adds it to a BF16 mean. The NUMERIC field is otherwise a binary32 pattern,
     so the backend now narrows it for that one operand shape. Qwen's head norm
     passes a gain vector, takes the weighted path, and keeps binary32.
  3. `RoPE coefficient view 461 has last axis 1; expected cosine then sine over
     512` — **open.** This is IR3-GAP-4, which amendment A9 resolved in the
     schema and the DeepSeek exporter has not yet taken up: `Tensor.generator`
     now lets a derived constant be declared, so the rotary coefficient rows can
     fill `VECTOR.ROPE`'s `in1` instead of the position offset the exporter
     still passes there. Qwen already declares the table this way.

  The ladder was not walked past that point. Its value is the ordering: every
  step so far has been a *naming* or *encoding* mismatch between the exporter
  and an engine that refuses to guess, not a missing capability.

- **OI-28 — `REDUCTION.EXPERT_SUM` cannot express the mHC branch reduction, and
  that is what now blocks the DeepSeek HBM prefill.** *(Found by landing the
  ABI's own `HYPER_CONNECT_PRE` decomposition.)* The frozen `VECTOR.MHC` row
  gives `HYPER_CONNECT_PRE` two output views and spends them on the packed
  `[tokens, 2, streams]` pre/post coefficient block and the
  `[tokens, streams, streams]` combination matrix, leaving the branch input
  `y[t,h] = sum_m pre[t,m] * x[t,m,h]` to a separate `REDUCTION.EXPERT_SUM`.
  The exporter now says exactly that. The operator then fails, and it fails for
  a reason no exporter can fix:

  > `reduction output view 413 holds 425984 elements, expected 16384`

  `EXPERT_SUM` reduces the **leading** axis of `input_view_0` and takes exactly
  one weight per leading index (`weight_view.element_count == values_view.dims[0]`).
  The branch weights vary per token *and* per stream. A descriptor covering a
  512-token block would need `512 x 4` weights against 4 leading contributions,
  and there is no view that supplies them. Four framings were checked and all
  four fail:

  | framing | why it fails |
  |---|---|
  | contributions `[tokens, streams, width]` | leading axis is tokens, so out must be `[streams, width]`, not `[tokens, width]` — the measured error |
  | contributions presented stream-major `[streams, tokens, width]` | shapes agree, but `weight_view.element_count` must then be 4 and the request has `4 x tokens` weights |
  | one descriptor per token (`bound_divisor = 1`) | A13's admission rule forbids `dim0 > bound_divisor`, so a rank-3 contributions view of `dim0 = 4` is **refused at admission**; a rank-3 view of `dim0 = 1` reduces one stream |
  | `bound_divisor = streams` | the loop trip count becomes `ceil(span / 4)`, which is not the token count |

  So this is a product decision, not a lowering bug. Two resolutions are
  available and both cost something:

  - **Apply the weight before the reduction (amendment A10).** A10 already
    blesses this: an `EXPERT_SUM` that omits `input_view_1` declares the weight
    was applied earlier, which is exactly what the DeepSeek MoE does. One
    `VECTOR.SCALE` sub-case 1 with the coefficient read through a trailing
    zero-stride axis, writing binary32, then `EXPERT_SUM` over a stream-major
    view. It is bit-exact — the frozen reference is "four binary32 branch
    products reduced by a balanced tree and converted once to BF16", which is
    a binary32 product then a `PAIRWISE_TREE` sum, not a fused product-add. It
    costs a materialised `[span, 4, 4096]` binary32 intermediate (17 GB at the
    declared 262,144-token context, 537 MB at 8,192) and it needs a stream-major
    contributions view, whose leading axis is then *not* the token axis, which
    silently defeats A13 whenever `span mod block` is 1, 2 or 3.
  - **Amend the operand row** so a weighted reduction can name its axis and take
    one weight per reduced *element* rather than per reduced *index*. That is an
    ABI change and therefore not ours to make.

  Until one is chosen the DeepSeek HBM prefill stops at
  `main.layer00.hc_attn_pre.branch_reduce`. Everything before it now runs:
  `HYPER_CONNECT_PRE` executes and writes both frozen output views.

- **OI-27 — no multi-node deployment can execute functionally: `NODE_ID` is
  never bound.** The 32-node capability makes every large contraction
  column-sharded (`shard_columns = cols // 32`), and the resulting views carry a
  `RUNTIME_SYMBOL` term on `NODE_ID`. `runtime/driver.py` binds `SPAN_TOKENS`,
  `POSITION_START`, `POSITION_END` and `CONTEXT_LENGTH`; `runtime/sim/device.py`
  adds `PHASE` and `GENERATION_INDEX`. Nothing binds `NODE_ID` or `NODE_COUNT` —
  only the verifier and the cycle model do — so the first sharded matmul traps
  with `view 431: symbol NODE_ID is unbound`. The mandated W6.3 capability is
  `hbm_sram_cluster_32.json`, so **W6.3 cannot produce a token until the
  functional simulator has a node dimension**, independently of every operand
  issue above. Binding `NODE_ID = 0` would not fix it: one device would then
  compute 1/32 of every contraction's columns and the LINK all-gather has no
  peer to gather from. The single-chip capability lowers the same graph
  unsharded and does execute, which is how the ladder below was measured.

- **OI-26 — the `attention_kv_view` row space needs an extent no ABI 3.0 view
  can present, and the neutral IR states the wrong one.** *(Investigation only;
  no change landed.)* The 43 axis-0 `CONCAT` kernels resolve to inputs
  `(span_tokens, 512)`, `(128, 512)` and `(context_groups_ratio_R, 512)` against
  an output declared as `(attention_rows_ratio_R, 512)` — a derived symbol with
  no entry in the ABI's frozen registry, so no view can carry it and the backend
  falls back to a `SPAN_TOKENS` row loop that A13 clamps to 104 rows.

  **What the operand actually needs.** `docs/DEEPSEEK_V4_ATTENTION_KV_VIEW_EVIDENCE.md`
  is explicit, and it is not one extent but two, one per phase:

  ```text
  prefill: current_kv[0:S]                   || compressed_valid_prefix[0:floor(S / R)]
  decode:  physical_window_capacity[0:128]   || compressed_valid_prefix[0:floor((start_pos + 1) / R)]
  ```

  Prefill has **no** window segment and decode has **no** current segment. The
  IR's single three-input `CONCAT` with one `attention_rows_*` extent is the
  union of both layouts, which is a shape neither phase has. That is a defect in
  the neutral IR independent of the symbol question, and it has to be fixed
  first: the kernel should be two phase-predicated compositions, which ABI 3.0
  already supports through instruction predicates and the `PHASE` symbol.

  **What today's symbols can and cannot express**, taking the composition as
  per-segment movements into row windows (the same idiom as OI-20's column
  concatenation):

  | quantity | expressible today? |
  |---|---|
  | segment offsets `S x 512` and `S x 512 + 128 x 512` | **yes** — one `RUNTIME_SYMBOL` term on `SPAN_TOKENS` plus a static element offset |
  | the current segment's `S` rows | **yes** — a block loop on `SPAN_TOKENS`, clamped exactly by A13 |
  | the window segment's 128 rows | **yes** — static |
  | the compressed prefix's `floor(X / R)` rows | **no** |

  The last one is the whole gap, and it is narrower than "a symbol for
  `attention_rows_*`". A view's leading extent is a *static* field; the only
  runtime narrowing in ABI 3.0 is A13, which clamps to `symbol - i x bound_divisor`
  in the loop's own units. A loop bound comes closer — `bound_symbol = CONTEXT_LENGTH`,
  `bound_divisor = R`, `step = 1` gives `trip = ceil(context_length / R)` by
  `runtime.sim.device.loop_trip_count` — but the reference says `floor`, and
  `ceil` copies one uncommitted group whenever `R` does not divide the context
  (at `R = 128` and a 104-token prompt, `ceil` is 1 and `floor` is 0). No
  `lower_bound` makes `ceil` into `floor` at every input.

  **If a symbol is added, this is what it would have to mean.** Not
  `attention_rows_*`: that is a sum of three things, two of which are already
  expressible, and it differs per phase and per layer. What is missing is *the
  number of committed rows of the compressed-KV stream this operand reads*.
  Three shapes it could take, in increasing generality:

  1. Two request-scoped symbols, `COMPRESSED_ROWS_RATIO_4` and
     `COMPRESSED_ROWS_RATIO_128`, bound by the host as `floor(context_length / R)`.
     Exact, trivial to bind — and it puts one model's two compression ratios in
     a model-neutral registry, which is the objection.
  2. One symbol `COMMITTED_STATE_ROWS`, meaning the committed row count of the
     state resource the operand reads. This is the honest quantity: the count is
     a property of the compressed-KV resource's cursor, which the STATE
     descriptor already carries. But ABI symbols are request-scoped scalars with
     no operand context, so this needs a resolution rule ("resolved against the
     resource this view's object belongs to") that no other symbol has.
  3. Generalise the extent rule instead of the registry: let a tensor view name
     a symbol and a divisor for its leading extent, resolving as
     `dim0 = min(dim0, floor(symbol / divisor) - i x block)`. A13 becomes the
     special case with `divisor = 1`. Model-neutral, subsumes the case above,
     and is a wire-format change to `TENSOR_VIEW` rather than a registry
     addition — so it is the largest of the three and the only one that is not
     purely additive.

  Recommendation: fix the phase split in the neutral IR first, since it is
  needed under every option and may narrow the requirement; then choose between
  (1) and (3). This is TA-ABI3-WIRE-1 amendment territory and is left for
  decision.

- **OI-24 — a zero-source memory object committed its whole declared arena on
  activation, and the DeepSeek cluster plan declares 160.4 GiB of it.**
  `MemoryObject` built zero-sourced objects with `np.full`, which writes every
  byte and so commits the entire arena up front. The kernel killed the process:
  `Out of memory: Killed process 706797 (python3) ... anon-rss:153687324kB`.
  `np.zeros` is calloc-backed and faults lazily, giving identical bytes at a
  ~33 GB peak. The arena is sized by `span_tokens` at its 8,192 maximum, so this
  scales with the declared context and not with the workload — a short prompt
  paid the full price.

- **OI-23 — the committed state image holds one layer's KV window out of
  thirty-six, so the ABI's durability record is not a durability record.**
  *(Found by the restart-exactness work.)* `Device._apply_commit` reads
  `prepared[0 : rows × row_bytes]` and appends it to the committed image at the
  cursor. That is a coherent contract for one logical stream. But
  `_state_view` in the HBM backend merges 36 layer KV resources into a single
  physical resource whose prepared image holds 36 populated windows of 393,216
  bytes, one per layer. A commit publishes the window at offset 0 and nothing
  else, and the committed image is never read back. A restart from the ABI's own
  durability record would lose 35 of 36 layers of KV cache.

  **The ABI is right and the backend is wrong.** A resource is one durable
  stream; the backend declared thirty-six of them as one, in a layout the commit
  contract cannot publish. The fix belongs in the layout, not in
  `_apply_commit`: make the resource's row the concatenation of all layers' rows
  for one position, so `capacity_rows` counts positions and one commit of
  `span_tokens` rows publishes every layer. Per-layer views then take a column
  offset inside the row — the same state-plane idiom the ROM lane already uses
  for the key and value halves.

  Execution today is unaffected, because reads name the prepared image; it is
  the durability claim that is hollow. W6.6's proof stands on its own terms —
  it checkpoints the prepared image, and says so — but it cannot be restated as
  "restart from the committed state" until this is fixed.

- **OI-22 — the HBM lane's block loop ran once at any prompt length, so every
  token past the first 512 was silently dropped.** *(Found by the ROM lane; fixed.)*
  `Device._loop_trip` computes `trip = ceil(ceil(span / bound_divisor) / step)`
  — it has already divided the symbol by the divisor before the step applies.
  The HBM lowering emitted `step = bound_divisor`, which divides a second time
  and yields `trip = 1` at *every* span. Verified on a clean checkout of HEAD, by
  summing the rows a token-indexed view presents across all iterations:

  | span | trip | rows presented |
  |---:|---:|---:|
  | 93 | 1 | 93 |
  | 512 | 1 | 512 |
  | 600 | 1 | **512 of 600** |
  | 8,000 | 1 | **512 of 8,000** |

  Every gate this program has passed used a prompt of 93 or 112 tokens, which
  fits in one block, so the encoding was correct on every workload anyone had
  run. The mandatory 8,000-token workload would have returned an answer computed
  from one sixteenth of its prompt. It would not have looked wrong: it would
  have produced fluent tokens, and under the campaign runner as it stood this
  morning it would have been recorded as `status: pass`, because nothing
  compared them to anything (OI-18's sibling defect, fixed earlier today). The
  two findings are the same lesson from opposite ends.

  The fix is `step = 1` with `upper_bound = trip`: the induction variable counts
  blocks, not rows. Confirmed end to end as well as at the resolver: a
  600-token prompt (one block plus 88) now runs to completion with
  `tensor.embedding_rows = 600`, which is `prompt + generated - 1` because the
  last generated token is never fed back. Before the fix that number would have
  been 512. Coverage is then exact at 93, 512, 600, 1,024, 8,000 and
  8,192, and the deployment still admits with the same 75 instructions, 218
  descriptors and work bound 22,715. **It was found only because the ROM lane
  lowered the same graph independently and encoded the loop differently** —
  neither lane's tests could have caught it alone.

- **OI-21 — prefill attention is a per-(token, head) Python loop, and it is
  what blocks the mandatory 8,000-token workload.**
  `runtime/sim/engines/attention.py::_execute_dense_gqa` iterates every (token,
  head) pair, and inside the token loop it copies the whole K cache
  (`np.ascontiguousarray(keys[:context, kv_head, :])`) though the copy depends
  only on the head and the context. Measured on this machine, one (token, head)
  score costs ~1.26 µs per context row, near-perfectly linear in context, so for
  Qwen3-8B's 32 query heads over 36 layers a prefill of T tokens costs
  `32 × 36 × 1.26 µs × T²/2` in score matmuls alone:

  | T | score matmuls | with the value matmul |
  |---:|---:|---:|
  | 93 | 6.3 s | ~13 s |
  | 1,000 | 726 s | ~24 min |
  | 8,000 | 12.9 h | **~26 h** |

  *Two corrections to that table, both from doing the work.* The `T²/2` is
  optimistic: prefill runs as a **single** span-8000 transaction with
  `context = 8000`, so every token contracts the full context and the cost is
  `T²`. The real 8K prefill was about 21.5 h of attention. **Fixed:** the engine
  now contracts a block of query rows per call rather than one (token, head)
  pair, with key and value blocks hoisted per KV head, and the BF16 kernel picks
  a K-major schedule for large tiles. Measured 8.5–10.3× on prefill and 2.0–2.2×
  on decode, which is memory-bound and has little to batch. The 8K prefill is now
  ~2.55 h.

  The arithmetic did not move, and that was checked rather than argued: 168
  engine comparisons against the pristine pre-change modules, bit-identical on
  raw `uint16` codes with every counter equal, plus 916 kernel comparisons, an
  adversarial operand pool of signed zeros and subnormals, and mutation testing
  that catches a reversed reduction, a `np.tile`-for-`np.repeat` mask swap and a
  transposed write-back. Both differentials refuse to report a pass at zero
  comparisons.

  `TA-QW-8K-1` ran for 43 minutes and was still in prefill softmax. It and
  `TA-QW-STRESS-1`, which has the same 8,000-token prompt, were stopped rather
  than left to run for a day and a half each. **This is an implementation
  problem, not an architectural one** — the ABI, the numeric contract and the
  descriptors are all fine, and the arithmetic to be performed is unchanged. The
  reduction runs over `head_dim`, which batching does not touch, so batched
  query rows should be bit-identical; that is the property any fix has to prove
  rather than assume, because a faster attention that changes one token is worse
  than no change at all.

- **OI-20 — the IR uses `CONCAT` for a broadcast along a new axis.** The
  DeepSeek mHC hyper-connection expansion is a `CONCAT` kernel whose four inputs
  are all the same tensor (`main.token_embed.output`, `[span_tokens, 4096]`) and
  whose output is `main.hc_expand.output`, `[span_tokens, 4, 4096]`. The ABI's
  `REDUCTION.GROUPED_CONCAT` concatenates along axis 0, giving `[416, 4096]` for
  a 104-token span, so the engine refuses — correctly — and the DeepSeek HBM
  deployment cannot prefill. Two things are worth recording beyond the fix.
  First, the engine's `np.concatenate(...).reshape(out_dims)` would have
  produced numerically wrong data had the shape check not stopped it, placing
  four consecutive *tokens* where four *streams* belong; the fail-closed check
  is the only thing between that and a plausible wrong answer. Second, since all
  four inputs are the same tensor, this is a broadcast, and ABI 3.0 views carry
  per-axis strides — a zero-stride axis expresses it with no operator and no
  data movement at all.

  **Corrected census, and half of it now closed.** The other 84 `CONCAT`
  kernels are not all axis-0. Forty-one of them
  (`main.layerNN.index_topk.concat`, `main.layerNN.compressed_dense_indices.concat`)
  join along **axis 1** — 128 window indices beside 512 selected indices, or
  beside a symbolic compressed-group width — which `REDUCTION.GROUPED_CONCAT`
  cannot express at all, since axis 0 would join two operands of different
  widths. These now lower as one `DMA.TRANSFER` per input into its own column
  range of the destination row: the same `key_then_value` idiom
  `_emit_state_append` already uses for a fused KV append, with an arena object
  in place of a state resource, and stated in offsets rather than performed by
  an operator. The remaining 43 are the `attention_kv_view` row-space
  compositions, which are a different problem entirely — see OI-26.

- **OI-19 — the storage-class equivalence proof is narrower than the claim
  resting on it.** `tools/prove_storage_class_equivalence.py` builds the same
  graph twice *through one backend*, varying only the weight storage class, and
  shows nothing else differs. That is a real result and it holds for both
  models. But the ROM-versus-HBM comparison needs the stronger property that
  `rom_qwen3` and `hbm_sram` lower the same graph to the *same program*, and
  that does not hold today: 31 instructions / 210 descriptors from the ROM
  lowering against 75 / 218 from the HBM lowering. Until they agree, a measured
  ROM-versus-HBM difference is partly a difference between two compilers. The
  README and `ABI3_PROGRAM_REPORT.md` §2.2 previously stated the narrow proof in
  words that implied the broad one; both are corrected. Two things are needed:
  re-run the proof once the ROM lane lands (the recorded result predates the A13
  loop-compression change to the HBM lowering), and add a cross-backend program
  comparison that either shows the two agree or reports exactly where they do
  not.
