# Unified ABI 3.0 execution checklist

**Checklist ID:** TA-CHK-3.0
**Owner:** single unified implementation agent (no parallel top-level owners)
**Baseline commit:** c83e543
**Issue date:** 2026-08-29
**Last updated:** 2026-08-30 — every load-bearing figure below re-verified
against the artifact that produces it (`make check-prose-figures`)
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
- [x] W1.4 Capability record + feature-bit registry + counter registry — `runtime/abi3/capability.py`, `runtime/sim/counters.py` (121 counters — `runtime.sim.counters.COUNTERS`; the
  registry publishes the names in `spec/abi3/counters.json` but no scalar count, so
  this one figure has no producer a checker can read)
- [x] W1.5 Independent verifier (loop bounds, work bound, branch targets, event/state proofs, permissions, CRC/digests) — `runtime/abi3/verifier.py` (11 proofs)
- [x] W1.6 Deployment manifest + digest binding + signature metadata — `runtime/abi3/deployment.py`
- [x] W1.7 Tiny deterministic fixture lowered through HBM and ROM storage classes; byte-identical rebuild; corruption rejection — `runtime/abi3/fixture.py` — HBM and ROM builds, byte-identical rebuild, 4 corruption classes rejected
- [x] W1.8 Unit tests for every record type and every fail-closed path — `tests/abi3/` — 469 tests; wire-format parser mutation-tested against 7 injected drifts

## W2 — Neutral IR v3

- [x] W2.1 Model Graph v3 schema (source semantics, phases, state effects, numeric-contract IDs) — `compiler/ir/v3/kernel_ir.py`
- [x] W2.2 Tensor Kernel IR v3 schema (target numerics, iteration domains, tensor views, deps, counter classes) — `compiler/ir/v3/kernel_ir.py` + `lowering.py` (53 kinds mapped)
- [x] W2.3 Neutrality checker (no ROM/HBM/SRAM/stage/queue/address terms in either IR) — `compiler/ir/v3/kernel_ir.py::check_neutral`
- [x] W2.4 Qwen3-8B exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/qwen3.py`; 728 kernels, 1165 tensors, 36 states, all 399 weight bindings verified against 16,381,470,720 real checkpoint bytes; graph_id `88496d70b772…` <!-- figure: 728 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.kernels" name="Qwen kernels" --> <!-- figure: 1165 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.tensors" name="Qwen tensors" --> <!-- figure: 36 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.states" name="Qwen states" --> <!-- figure: 16,381,470,720 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.bound_weight_bytes" name="Qwen bound weight bytes" --> <!-- figure: "88496d70b772…" src="results/abi3/program_status.json#neutral_ir.qwen3-8b.graph_id" name="Qwen graph id" -->
- [x] W2.5 DeepSeek-V4-Flash exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/deepseek_v4.py`; 3976 kernels, 7066 tensors, 229 states, 156,015,698,140 bound weight bytes <!-- figure: 3976 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.kernels" name="DeepSeek kernels" --> <!-- figure: 7066 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.tensors" name="DeepSeek tensors" --> <!-- figure: 229 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.states" name="DeepSeek states" --> <!-- figure: 156,015,698,140 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.bound_weight_bytes" name="DeepSeek bound weight bytes" -->
- [x] W2.6 Cross-model operator union report; both exporters pass one schema + verifier — `tests/compiler/test_neutral_ir_cross_model.py` (33 gates); union published as `spec/abi3/numeric_contract_union.json` (67 contracts) <!-- figure: 67 src="spec/abi3/numeric_contract_union.json#contract_count" name="numeric contract union size" -->

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
- [x] W3.12 Observation/recovery engines + full counter set — sequencer-executed; 121-counter registry published
- [x] W3.13 Host queue driver — `runtime/driver.py`, real 128-byte submission/completion records per token

## W4 — HBM/SRAM backend (shared chip; 1 node Qwen, 32 nodes DeepSeek)

- [x] W4.1 Physical Plan IR (allocation, tiling, banks, schedules, topology) — `compiler/backends/hbm_sram/plan.py`
- [x] W4.2 Weight/state allocator + HBM address map (mmap-backed, no 16/156 GB copy) — zero-copy: 14 objects over 399 checkpoint ranges for Qwen, 196 objects for DeepSeek; no image written
- [x] W4.3 Tiling + loop-nest schedule synthesis (loop-compressed programs) — Qwen 75 instructions from 728 kernels; tiling in SCHEDULE descriptors. *(The `13,400x vs ABI 2.5` ratio this entry used to quote is computed by nothing in the repository, so it is dropped rather than restated at the new counts.)* <!-- figure: 75 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.instruction_count" name="Qwen HBM instructions" --> <!-- figure: 728 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.kernels" name="Qwen kernels, W4.3" -->
- [x] W4.4 Descriptor + program emission (ABI 3.0) — `compiler/backends/hbm_sram/lower.py`
- [x] W4.5 Independent legality checker (reconstructs the plan without reusing the generator) — `compiler/backends/hbm_sram/check.py`, does not import the generator
- [~] W4.6 Qwen single-node deployment
- [~] W4.7 DeepSeek 32-node sharded deployment (experts, sparse gather, collectives, coordinated commit)

## W5 — ROM backends

- [x] W5.1 Common ROM contracts (immutable regions, repair map, inverse reconstruction) — `compiler/backends/rom/common/image.py` incl. repair map
- [x] W5.2 Qwen conventional single-chip ROM partition + images + schedules + deployment — the deployed Qwen ROM program admits at 75 instructions and 239 descriptors (`results/abi3/qwen3_rom_ta-qw-chat-1_execution.json`), while the storage-class equivalence build lowers the same graph to 31 instructions and 210 descriptors on both storage classes (`results/abi3/storage_class_equivalence_qwen3.json`) — two different builds, and [OI-19] is the distance between them; 14 role-striped banks, 16,381,470,720 B <!-- figure: 75 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.instruction_count" name="Qwen ROM deployed instructions" --> <!-- figure: 239 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen ROM deployed descriptors" --> <!-- figure: 31 src="results/abi3/storage_class_equivalence_qwen3.json#instruction_count.rom" name="Qwen ROM equivalence-build instructions" --> <!-- figure: 210 src="results/abi3/storage_class_equivalence_qwen3.json#descriptor_count.rom" name="Qwen ROM equivalence-build descriptors" -->
- [x] W5.3 DeepSeek wafer-scale reticle/tile ROM placement + on-wafer fabric + distributed HBM state + deployment — DeepSeek ROM wafer 322 instructions, 172 regions, 9,300 tiles of 37 reticles, 18 link instructions. *(Those four are the wafer build as it stood when this item closed and nothing republishes them: the region count is stated as 228 in the segmented-binding finding below, and the wafer program in the executed record carries 881 instructions and 13 link descriptors.)* <!-- figure: 881 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.notes.verification.instruction_count" name="DeepSeek ROM wafer instructions, recorded" --> <!-- figure: 13 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.counters['engine.link.descriptors']" name="DeepSeek ROM link descriptors, recorded" -->
- [x] W5.4 Inverse proof: ROM image → original weights bit-exact — inverse proof passes bit-identically over 16.4 GB and 156 GB
- [~] W5.5 Independent schedule checker

## W6 — Real end-to-end execution (the correctness spine)

- [x] W6.1 Qwen-HBM: short prompt → prefill → decode → real tokens — **token-identical to the reference oracle**, and **decode reaches a real EOS**. `TA-QW-AGENT-1` ran 112 prompt tokens to the natural stop at token 151645 after 23 tokens (`results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json`) <!-- figure: 112 src="results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json#record.workload.prompt_token_count" name="TA-QW-AGENT-1 prompt tokens" --> <!-- figure: 23 src="results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json#record.generated_token_count" name="TA-QW-AGENT-1 decoded tokens" --> <!-- figure: 151645 src="results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json#record.generated_token_ids[22]" name="TA-QW-AGENT-1 final token is EOS" -->, `TA-QW-CHAT-1` ran 24 tokens (`..._ta-qw-chat-1_...`); both agree with the oracle at every position, with no legitimacy problems and every admission check passing — 27 of them on the agent record and 29 on the chat record, whose set is the agent's plus `block_extent` and `block_scale`, so it is a check set that grew between the two runs and not a run that skipped two
- [x] W6.2 Qwen-ROM: identical token sequence from the ROM deployment — **re-verified with evidence in the repository** (`results/abi3/qwen3_rom_ta-qw-chat-1_execution.json`, status pass, 24 tokens, `reference_agreement` true, no divergence index). The 24 tokens are identical to `qwen3_hbm_ta-qw-chat-1_execution.json` position for position, which is the claim this item makes. Both admit at 75 instructions; the ROM lane emits 239 descriptors against HBM's 218 and declares 2,105 retired work against 22,715, because the two lanes block the token loop differently — see [OI-19] — 75 instructions, 239 descriptors, admitted; **24 tokens token-for-token identical to the external oracle and to the HBM target**. All 27 distinct prefill kernels diffed kernel-by-kernel against HBM through the `on_issue` hook: bit-identical, output hash for output hash, including the KV window and the final logits. Storage-class equivalence re-proved after every change: 17 descriptors differ, all `MEMORY_OBJECT`, all 17 ROM→HBM, none beyond storage class <!-- figure: 17 src="results/abi3/storage_class_equivalence_qwen3.json#differing_descriptor_count" name="Qwen storage-class differing descriptors" --> <!-- figure: 17 src="results/abi3/storage_class_equivalence_qwen3.json#storage_class_transitions['ROM->HBM']" name="Qwen ROM to HBM transitions" --> <!-- figure: 75 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.instruction_count" name="Qwen ROM instructions, TA-QW-CHAT-1" --> <!-- figure: 239 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen ROM descriptors" --> <!-- figure: 218 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen HBM descriptors" --> <!-- figure: 2,105 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.declared_retired_work" name="Qwen ROM declared retired work" --> <!-- figure: 22,715 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.declared_retired_work" name="Qwen HBM declared retired work" -->
- [ ] W6.3 DeepSeek-HBM (32 node): short prompt → real tokens — **still zero tokens, and the committed record is superseded.** What the repository holds is `results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json`, last written at `8dfddac`: the deployment **ADMITS** at **11,049 instructions**, **23,297 descriptors**, work **6,177,966**/6,177,966 proved exactly, **zero verifier errors**, all 32 admission checks passing including `event_count_bound`, and an event count of **3,989** against a 4,096 cap; it then retires **251** instructions before failing with `prefill failed: reduction output view 2327 holds 425984 elements, expected 16384`. <!-- figure: 11,049 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.instruction_count" name="DeepSeek HBM instructions, recorded" --> <!-- figure: 23,297 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.descriptor_count" name="DeepSeek HBM descriptors, recorded" --> <!-- figure: 6,177,966 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.declared_retired_work" name="DeepSeek HBM declared work, recorded" --> <!-- figure: 6,177,966 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.proved_retired_work" name="DeepSeek HBM proved work, recorded" --> <!-- figure: 3,989 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.event_count" name="DeepSeek HBM event count, recorded" --> <!-- figure: 251 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.counters['instructions.retired']" name="DeepSeek HBM retired, recorded" --> <!-- figure: "prefill failed: reduction output view 2327 holds 425984 elements, expected 16384" src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.failure" name="DeepSeek HBM recorded failure" --> **That record predates amendment A17 and its own check list says so** — there is no `join_axis` entry, which is the check A17 added — so everything after it here is the lane's history as its commits report it, evidenced by commit messages and by no artifact. A17 (`742faa4`) made a feature-axis join expressible, took operand-arity faults 42 → 0 and recorded 12,100 instructions, 25,129 descriptors, work 50,339,327 and 3,863 events, because emitting the amended operator costs 167 events where the hand-expansion into per-column-window `DMA.TRANSFER`s cost 502. Consuming it (`a2cb06a`) then found the event budget was dead loops — 42 bands emitted for 43 layers — and took the same deployment to 1,239 instructions and 434 events of the 4,096 cap, retiring 299. `88b3bcd` cleared seven walls to 1,896 retired and stopped in layer 0's routed MoE gate on a sharded MXFP4 scale object 1,664 codes short. **The program was over-allocating, and the fix made it smaller rather than needing a wider scoreboard** — that conclusion survives all three measurements, and is the one thing here that does not wait on a re-run. **A fresh DeepSeek-HBM execution record is needed; until it lands, no figure after 11,049 is evidence.** Admission is not execution and this lane has still produced no token; the 32-node question below is unchanged. *(Historical note: the entry below described the state before the node dimension landed.)* the functional device had no node dimension, so no token was reachable on a 32-node capability however the operands were fixed. The deployment admits (996 instructions, 2,307 descriptors, work 4,587,224 proved exactly) and the cycle model covers it; it cannot run — **no tokens yet, and two of the three remaining blockers are decisions, not bugs.** The deployment admits (996 instructions, 2,307 descriptors, work bound proved exactly) and `HYPER_CONNECT_PRE` now executes against the frozen `VECTOR.MHC` operand row. It stops at the branch reduction the ABI leaves to `REDUCTION.EXPERT_SUM`, which provably cannot carry per-token weights over a token block (**OI-28**). Behind that: the functional simulator binds no `NODE_ID`, so the mandated 32-node capability cannot execute at all (**OI-27**), and the `attention_kv_view` row space needs an extent no view can present (**OI-26**). Landed on the way: the mHC pre/post split, the axis-1 index concatenations (**OI-20**, whose per-column-window lowering is now **superseded by A17** — a feature-axis join is one operator on both backends instead of two spellings), and one epsilon-encoding defect (**OI-29**)
- [ ] W6.4 DeepSeek-ROM (wafer): identical token sequence — **still zero tokens, and the committed record is superseded.** `results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json`, last written at `61bd0d6`, records `TA-DS-CHAT-1` at **104** prompt tokens retiring **5,789 instructions** (**2,952** issued) from a program admitted at 881 instructions and 2,883 descriptors, and failing with `prefill failed: the residual add contract is BF16 in and BF16 out`. <!-- figure: 5,789 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.counters['instructions.retired']" name="DeepSeek ROM retired, recorded" --> <!-- figure: 2,952 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.counters['instructions.issued']" name="DeepSeek ROM issued, recorded" --> <!-- figure: 2,883 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.notes.verification.descriptor_count" name="DeepSeek ROM descriptors, recorded" --> <!-- figure: 104 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.workload.prompt_token_count" name="TA-DS-CHAT-1 prompt tokens" --> <!-- figure: "prefill failed: the residual add contract is BF16 in and BF16 out" src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.failure" name="DeepSeek ROM recorded failure" --> **The entry that stood here claimed 5,883 retired and 2,974 issued and declared that same wall gone, while citing the record whose failure text is the wall.** Both statements were true at different moments — the record predates the fix — but an entry that cites evidence contradicting it is precisely the defect this program has spent the session finding in other people's work, so it is corrected here rather than renumbered. What holds now, from an artifact: the exporter emits **no `ADD` kernels at all** — the DeepSeek kind census in `results/abi3/program_status.json` has no `ADD` entry and carries **86** `HYPER_CONNECT_PRE` and 86 `HYPER_CONNECT_POST` instead — because the residual is carried by `VECTOR.MHC`. <!-- figure: 86 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.kind_census.HYPER_CONNECT_PRE" name="DeepSeek HYPER_CONNECT_PRE kernels" --> Where the lane has reached since is recorded in commit messages only: `0f40b8b` 685 → 761 retired, `123a916` 761 → 785, `e466a46` → 793, and amendment A19 (`29e50c2`) **6,393 → 9,189 retired**, stopping on the A18 predicate trap at ratio 128 — a predicate the exporter declares and no backend lowers. **A fresh ROM DeepSeek execution record is needed; until one lands, 9,189 is a commit message and not evidence**, and [OI-41], now closed, is why the record on disk shows the last rung that could complete rather than the current one — sparse attention was the wall when that record was written and has since gone from 12.5 ms per (head, row) to 0.2% of the prefill. **This is still the reachable DeepSeek execution path**, because a wafer-scale logical device is one node (`node_count` **1**, `topology_class` 2 on that record) and needs no multi-node simulation; its tile-scoped collectives are what amendment A14 makes expressible <!-- figure: 1 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.target.node_count" name="DeepSeek ROM wafer node count" --> <!-- figure: 2 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.target.topology_class" name="DeepSeek ROM wafer topology class" -->
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
- [~] W8.3 Representative engine datapaths (DMA, tensor MAC array, vector, selection) — **four land bit-exact against the functional simulator's *real* engines**: `TENSOR.MATMUL`, `DMA.GATHER`/`SCATTER`, `VECTOR.ADD` and `SELECTION.ARGMAX` in `rtl/abi3/`, correlated over 31 generated ABI 3.0 programs <!-- figure: 31 src="results/rtl/abi3_engine_campaign.json#correlation.case_count" name="engine RTL cases, W8.3" --> executed by `runtime.sim.device.Device` with nothing stubbed — 10,025 result words compared <!-- figure: 10025 src="results/rtl/abi3_engine_campaign.json#correlation.result_word_count" name="engine RTL result words, W8.3" --> element by element on two simulators, 59,868 multiply-accumulates <!-- figure: 59868 src="results/rtl/abi3_engine_campaign.json#correlation.mac_count" name="engine RTL MACs, W8.3" -->, 9 refusals <!-- figure: 9 src="results/rtl/abi3_engine_campaign.json#correlation.fault_case_count" name="engine RTL faults, W8.3" --> matched by fault class with the destination proved untouched, and 2,576 exhaustive <!-- figure: 2576 src="results/rtl/abi3_engine_campaign.json#correlation.decode_probe_count" name="engine RTL decode probes, W8.3" --> storage-format decode probes and 3,696 <!-- figure: 3696 src="results/rtl/abi3_engine_campaign.json#correlation.arith_probe_count" name="engine RTL arithmetic probes, W8.3" --> binary32 add/multiply/round probes against the exact `fractions.Fraction` reference; 26,381 checks per simulator <!-- figure: 26381 src="results/rtl/abi3_engine_campaign.json#checks_per_simulator.iverilog" name="engine RTL checks, W8.3" --> (`results/rtl/abi3_engine_campaign.json`). Covers BF16 x BF16, FP8 E4M3FN x FP8 E4M3FN and block-scaled MXFP4 E2M1 x FP8 E4M3FN under `bf16_bf16_fp32_sequential_rne_v1`, including amendment A15's two-dimensional scale block. **Still open, and named rather than implied:** the other nine VECTOR subopcodes, ATTENTION, ROUTE, REDUCTION, LINK and STATE have no datapath RTL; the *blocked* contraction contract is out of scope by construction; a fault that first appears after the first output element is a known divergence, not a covered case; and these datapaths are not wired to the W8.6 sequencer. The campaign is mutation-tested: of five injected defects it catches four, and **the one it first missed is why two cases exist** — reordering a binary32 reduction perturbs the accumulator by one part in 2**24 and the BF16 output resolves one part in 2**8, so a reversed lane passed until two catastrophic-cancellation cases were added. **Three of the four datapaths are fully routed on SKY130 HD**, each meeting setup and hold with **0** DRC errors <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.drc_errors" name="selection DRC, W8.3" --> and **0** antenna violations <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.antenna_violating_nets" name="selection antenna, W8.3" -->: `ot_a3_selection_argmax`, the block that decides the token, closes at 12 ns with **3.348** ns of slack <!-- figure: 3.348 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.setup_wns_ns" name="selection routed setup slack, W8.3" --> in a die of **47,430.3** um2 <!-- figure: 47,430.3 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.die_area_um2" name="selection die area, W8.3" -->; `ot_a3_vector_add` at 100 ns in **122,766** um2 <!-- figure: 122,766 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.die_area_um2" name="vector add die area, W8.3" -->; and `ot_a3_dma_index_mover` at 25 ns in **268,200** um2 <!-- figure: 268,200 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.die_area_um2" name="dma die area, W8.3" -->. **`ot_a3_mac_lane` is not routed:** its flow reached global routing and its driver was terminated before it could record, so the contraction lane's routed area, timing and power are unmeasured; what the run did show is that it does *not* close at 60 ns, on the scale-address divider rather than the accumulator. **No frequency from a 130 nm open PDK may be scaled to N6/N5/N4 and none of this retires `power.fabric_clock_hz = 1e9`, which stays `assumed`.** `docs/ABI3_ENGINE_DATAPATH_RTL.md` states the boundary
- [~] W8.4 Inter-chip endpoint RTL (packets, credits, retry, collectives) — **the endpoint exists, and the traversal count the headline is priced on is now measured rather than derived.** `rtl/abi3/ot_a3_link_channel.sv` is one directed hop: a bounded credit window (`COMMUNICATION.credit_bound`), CRC32C per flit (`integrity_mode`), a monotone sequence, and go-back-N replay bounded by `retry_bound` and `timeout_class`. `ot_a3_mesh_router.sv` is a five-port X-then-Y dimension-ordered router; `ot_a3_collective_engine.sv` runs SUM/MAX/MIN all-reduce, BROADCAST, ALL_GATHER and a barrier; `ot_a3_link_node.sv` assembles them into a mesh node. Six geometries x ten cases, **cycle-for-cycle identical** on Icarus 11.0 and Verilator 5.050, with every reduced binary32 code checked at every participant: 41,010 checks on the 8x8 mesh <!-- figure: 41,010 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].simulators[name=iverilog].checks" name="A3 link checks, 8x8" --> and 2,610 on the 4x4 <!-- figure: 2,610 src="results/rtl/a3_link_campaign.json#configurations[name=mesh4x4_vec16_hop1].simulators[name=verilator].checks" name="A3 link checks, 4x4" --> (`results/rtl/a3_link_campaign.json`).
  **What it measures, and why it was built.** A mesh all-reduce walks **exactly the mesh diameter** under recursive doubling — **14** traversals on the 8x8 mesh <!-- figure: 14 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].cases[label=allreduce_sum_recursive_doubling].measured.traversals" name="measured all-reduce traversals, 8x8" --> against the **15.4** `src/opentallas/roofline.py` charges <!-- figure: 15.4 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].model_charged_traversals" name="model-charged traversals, 8x8" --> — and **exactly twice the diameter**, **12** on the 4x4 mesh <!-- figure: 12 src="results/rtl/a3_link_campaign.json#configurations[name=mesh4x4_vec16_hop1].cases[label=allreduce_sum_halving_doubling].measured.traversals" name="measured halving/doubling traversals, 4x4" -->, under Rabenseifner halving/doubling. Those are two different algorithms and the model charges the **latency of the first and the bandwidth of the second** in the same event (`link_event_cost_s`: `depth = collective_traversals(...)` beside `payload = activation_bytes * 3 * (span-1)/span`). No single algorithm delivers both. Separately, a barrier's cycles are exactly linear in the declared hop occupancy: **6.000** cycles per hop-cycle <!-- figure: 6.000 src="results/rtl/a3_link_campaign.json#hop_latency_regression[label=barrier].cycles_per_hop_cycle" name="measured cycles per hop cycle, barrier" --> on a diameter-6 mesh, zero residual, on top of a **43.0**-cycle per-collective fixed cost <!-- figure: 43.0 src="results/rtl/a3_link_campaign.json#hop_latency_regression[label=barrier].fixed_cycles" name="measured per-collective fixed cycles" --> that the analytical model has no term for at all. Under a payload larger than the credit window the same all-reduce costs 18.5 cycles per hop-cycle, not 6, so `traversals x hop_latency` is the right form only while a collective fits inside its credit window.
  **What it refuses, and why that is the finding.** A binary32 SUM runs only under a reduction order the chosen algorithm can actually produce: recursive doubling folds the lowest participant bit first and is `PAIRWISE_TREE`; halving/doubling folds the highest first, which coincides with `BLOCKED_ASCENDING` only at sixteen participants. **No mesh algorithm that finishes in O(sqrt(P)) traversals produces `SEQUENTIAL_ASCENDING`** — and `compiler/backends/rom/common/program.py:5634` hard-codes `SEQUENTIAL_ASCENDING` for **every** arithmetic collective the ROM backend emits, including the on-wafer expert all-reduce the headline prices. The engine therefore traps (class 11) rather than returning different bits under the same name. The divergence is measured, not asserted: on the 8x8 vector set **54** of 64 reduced elements differ between the two orders <!-- figure: 54 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].sequential_vs_tree_differing_elements" name="elements differing between declared and achievable reduction order" -->.
  **Physical, and it found something a cycle model cannot.** The endpoint is placed and routed in the installed IHP SG13G2 open foundry PDK with OpenROAD — **zero** detailed-route DRC violations <!-- figure: 0 src="results/rtl/a3_link_physical.json#implementation.detailed_route_drc_violations" name="A3 link endpoint route DRC violations" -->, **138,206** um2 of design area <!-- figure: 138,206 src="results/rtl/a3_link_physical.json#metrics.design_area_um2" name="A3 link endpoint routed design area" --> — and it **does not close timing** at a 10 ns period, missing by **-10.26** ns <!-- figure: -10.26 src="results/rtl/a3_link_physical.json#metrics.worst_setup_slack_ns" name="A3 link endpoint worst setup slack at 10 ns" -->; the archived failing path runs from `rx_w_flit[1]` through about forty XNOR/XOR stages, which is the single-cycle CRC32C over a 64-bit flit. At a 25 ns period the same block closes at **+0.24** ns <!-- figure: 0.24 src="results/rtl/a3_link_physical_25ns.json#metrics.worst_setup_slack_ns" name="A3 link endpoint worst setup slack at 25 ns" --> with zero total negative slack, so the integrity check — not the credit or replay logic — is what sets this endpoint's clock, and a parallel or pipelined CRC is the named next step. The whole mesh node synthesises at **1,034,069** um2 of cell area <!-- figure: 1,034,069 src="results/rtl/a3_link_node_synthesis.json#design.yosys_statistics.cell_area_um2" name="A3 link node synthesised cell area" --> (`results/rtl/a3_link_node_synthesis.json`, synthesis only, a flip-flop receive bank sized for clarity and not an area claim) and the router alone at **19,915** um2 <!-- figure: 19,915 src="results/rtl/a3_link_router_synthesis.json#design.yosys_statistics.cell_area_um2" name="A3 mesh router synthesised cell area" -->. IHP SG13G2 is a 130 nm open foundry PDK: no area or delay here may be scaled to N6/N5/N7/N4 (`docs/METHODOLOGY.md` section 9).
  **Still open, named rather than implied:** this endpoint does **not** measure wire delay, so `links.on_wafer`'s 125 ns stays derived from published geometry and the audit's open measurement #1 is only half answered — the traversal count now has an implementation, the nanoseconds do not. The COMMUNICATION descriptor is not decoded in RTL (op, algorithm, order and root are ports). There are no virtual channels, no wormhole flow control and no adaptive routing, so nothing here speaks to congestion. `CONCAT`, `REDUCE_SCATTER` as a standalone op, `LINK.SEND`/`RECEIVE`/`REMOTE_DMA` and multi-node scope resolution have no RTL. The engine is not wired to the W8.6 microsequencer, and `runtime/cycle/fabric.py` still runs a ring (`2(P-1)` rounds) where `roofline.py` charges `1.1 x` diameter — two algorithms for one machine, and nothing reconciles them
- [~] W8.5 ROM service RTL (Qwen chip, DeepSeek wafer tile) — **the read path is implemented and correlated on two simulators, and it contains no ROM array.** `rtl/rom/ot_rom_read_service.sv` turns `(object_id, byte_offset, byte_length)` into a physical access against the compiled region plan the deployment publishes as `notes.rom_plan`: object lookup, shard walk to a placement resource and an address inside it, row-redundancy translation, region masking, fail-closed quarantine and column-repair refusal, row-activation accounting against a persistent row buffer, and the column mux onto the operand bus. Three vector sets, all read back out of real ROM deployments — never hand written — and replayed under Icarus and Verilator through independently written checkers (`results/rtl/rom_service_campaign.json`):
  - `qwen_chip`: the **executed** ROM read stream of the Qwen ROM deployment on `runtime.sim.device.Device`, both accounting sites instrumented and reconciled against the device's own `rom.bytes_read`; **349** requests, **2,499,996** sense beats, **159,997,856** bytes and **39,213** row activations replayed beat by beat <!-- figure: 349 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.requests.count" name="Qwen ROM service requests" --> <!-- figure: 2,499,996 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.beats" name="Qwen ROM service beats" --> <!-- figure: 159,997,856 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.bytes" name="Qwen ROM service bytes" --> <!-- figure: 39,213 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.activations" name="Qwen ROM service activations" -->
  - `qwen_chip_degraded`: the same deployment recompiled against a BIST defect list, so the repair map comes from the real planner, plus a masked region and a quarantined bank as runtime health inputs — **363** requests and **168** refusals <!-- figure: 363 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.requests.count" name="Qwen degraded ROM service requests" --> <!-- figure: 168 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.totals.faults" name="Qwen degraded ROM service refusals" -->
  - `deepseek_wafer`: **10,833** requests over **9,527** shards on **9,300** placement resources, every shard boundary the plan declares crossed by one request, and **9,172** of the 9,300 resources entered by a served read -- the 128 that are not are the 127 owned only by the deliberately masked expert bank plus the one deliberately quarantined <!-- figure: 9,172 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.totals.placement_resources_entered" name="DeepSeek wafer resources entered" -->; **88** of its 228 regions are distributed over more than one resource and the largest spans **1,280** <!-- figure: 10,833 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.requests.count" name="DeepSeek wafer ROM service requests" --> <!-- figure: 9,527 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.shard_count" name="DeepSeek wafer ROM shards" --> <!-- figure: 9,300 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.resource_count" name="DeepSeek wafer ROM resources" --> <!-- figure: 88 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.distributed_region_count" name="DeepSeek wafer distributed regions" --> <!-- figure: 1,280 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.max_shards_in_one_region" name="DeepSeek wafer largest region shard count" -->. **This set is derived from the compiled plan, not executed**, because that lane has produced no tokens (W6.4), and the artifact says so rather than letting it read as an executed stream.
  - **Why it stays `[~]`:** there is no ROM array in the RTL under test. The array sits behind a sense request/response interface and is supplied by the testbench, so this is a control and addressing claim — it establishes nothing about ROM cell area, read energy, sense margin, wordline or bitline delay, retention or defect rate, and the sense-granule width is a declared parameter of the block rather than a macro property. Column redundancy is refused rather than implemented; the view-to-byte-range walk and descriptor admission are out of scope; a whole decode step reads about fifteen gigabytes and is not replayed beat by beat. `docs/ROM_SERVICE_RTL.md` states the boundary
  - **What it found.** Both products declare ROM-class memory objects that the region plan does not place — generated rotary, `arange`, ring-index and constant tables — carrying `bank_or_tile` 0xFFFF and `base_address` 0 while their traffic is still counted by `rom.bytes_read`. **111** of the **265** replayed executed Qwen reads are to two such objects <!-- figure: 111 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.refusals_by_origin.executed" name="Qwen unplaced-object refusals from the executed stream" --> <!-- figure: 265 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.requests.by_origin.executed" name="Qwen executed reads replayed" --> and the wafer plan leaves six of them unplaced. The service refuses them rather than inventing a bank. That is a finding about `compiler/backends/rom`, which this item does not own
- [x] W8.6 Verilator co-simulation vs functional simulator on generated programs — 64 cases, 182 issue events, 454 resolved tensor views (amendments A4, A13 and A18), 11 traps matched on two simulators, 4,383 checks each <!-- figure: 64 src="results/rtl/abi3_campaign.json#correlation.case_count" name="RTL correlation cases" --> <!-- figure: 182 src="results/rtl/abi3_campaign.json#correlation.issue_event_count" name="RTL issue events" --> <!-- figure: 454 src="results/rtl/abi3_campaign.json#correlation.view_resolution_count" name="RTL resolved views" --> <!-- figure: 11 src="results/rtl/abi3_campaign.json#correlation.trap_count" name="RTL traps" --> <!-- figure: 4,383 src="results/rtl/abi3_campaign.json#cases[name=iverilog].checks" name="RTL checks per simulator" -->
- [x] W8.7 Fault/stall/backpressure/reset campaigns — 17 negative cases incl. CRC, illegal opcode, loop overrun, mid-transaction trap <!-- figure: 17 src="results/rtl/abi3_campaign.json#correlation.negative_case_count" name="RTL negative cases" -->

## W9 — Physical (SKY130 implementation view, ASAP7 predictive view)

- [x] W9.1 Inventory available PDKs/tools; record what can actually run offline — `docs/ABI3_PHYSICAL_VIEWS.md`
- [x] W9.2 SKY130 synthesis + place/route of RTL 3.0 blocks; area/timing/power — SKY130 HD full place-and-route, 0 DRC, 0 antenna
- [x] W9.3 ASAP7 synthesis (predictive) of the same blocks — ASAP7 full place-and-route; archived case reproduced bit-for-bit
- [ ] W9.4 SRAM/ROM macro methodology per view
- [ ] W9.5 Feed characterized capability back into cycle model; recompile; rerun

## W10 — Mandatory workload campaigns

- [~] W10.1 Qwen exactly 8,000 natural prompt tokens → decode to first EOS (HBM) — **executed**: 8,000 prompt tokens, 193 decoded in 14,982 s (`results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json`). <!-- figure: 8,000 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.workload.prompt_token_count" name="TA-QW-8K-1 prompt tokens" --> <!-- figure: 193 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.generated_token_count" name="TA-QW-8K-1 decoded tokens" --> <!-- figure: 137 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.notes.first_divergence_index" name="TA-QW-8K-1 first divergence" --> The first **137 tokens are identical to the reference oracle**, and the continuation is coherent Melville pastiche. It did not reach EOS for two separate reasons, both recorded: one argmax flip at index 137 (see [OI-33]) and a hard stop at index 193 (see [OI-34]). **The ROM lane is now running the same workload at `max_new_tokens` 192**, which is the largest decode budget an 8,000-token prompt can have inside a declared 8,192-position context — 8,000 + 192 = 8,192 exactly. That gives a lane-to-lane comparison at the sweet spot against the HBM record's first 192 tokens without first having to reopen the specification question in [OI-34]
- [~] W10.2 Qwen repeated-special-token stress run — **executed, and it diverged**: 8,000 prompt tokens (one distinct id), 32 decoded in 11,942 s, recorded `status: diverged` at index 2 (`results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json`). <!-- figure: 32 src="results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json#record.generated_token_count" name="TA-QW-STRESS-1 decoded tokens" --> <!-- figure: 2 src="results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json#record.notes.first_divergence_index" name="TA-QW-STRESS-1 first divergence" --> <!-- figure: "diverged" src="results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json#status" name="TA-QW-STRESS-1 status" --> The run itself is complete and the workload has served its purpose — see [OI-33]. Whether the divergence is acceptable is a numeric-contract question, not an execution one
- [x] W10.3 Qwen chat workload (pinned template) — `TA-QW-CHAT-1`, 93 prompt tokens, 24 decoded tokens, token-identical to the oracle; <!-- figure: 93 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.workload.prompt_token_count" name="TA-QW-CHAT-1 prompt tokens" --> <!-- figure: 24 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.generated_token_count" name="TA-QW-CHAT-1 decoded tokens, W10.3" --> the model is mid-derivation at the token cap (`We are given:\n\n- **Ship 1** (from Port A) leaves at **06:00**`), so this record proves token fidelity, not answer correctness, and W10.1 carries the run to EOS
- [x] W10.4 Qwen agentic workload — `TA-QW-AGENT-1` decoded a **complete, well-formed tool call and stopped at a real EOS** entirely on the accelerator: ```bash / awk -F',' '{sum += $2} END {print sum}' inventory.txt / ```. Token-identical to the oracle. Feeding the result back through the sandbox loop is `tools/run_qwen3_agent_episode.py`
- [x] W10.5 DeepSeek long-context campaign — **all five declared rungs have executed** — 1,000 / 8,000 / 32,000 / 128,000 / 200,000 tokens — so the largest context actually executed is **200,000** tokens (`results/abi3/deepseek_v4_reference_oracle_context_ladder.json`). <!-- figure: 200,000 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.largest_context_executed" name="largest DeepSeek context executed" --> The three upper rungs needed exactly the chunked prefill the projection called for and record `prefill_tiled` true; at 200,000 tokens peak device memory is **9.27** GB, the measured KV read is **317,435,904** B per decode step, and that is **0.9999** of the corrected profile's prediction. <!-- figure: 9.27 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[workload=TA-DS-CTX-200K-1].peak_device_bytes" scale="1e-9" name="200K rung peak device GB" --> <!-- figure: 317,435,904 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[workload=TA-DS-CTX-200K-1].measured_kv_bytes_per_decode_step" name="200K rung measured KV bytes per step" --> <!-- figure: 0.9999 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[workload=TA-DS-CTX-200K-1].measured_over_predicted" name="200K rung measured over predicted" --> The projection that motivated the rewrite stands as recorded and is why it was needed: unchunked, `hc_post` alone is **48.8** GiB at that context and the indexer term **2.33** TiB, while persistent KV state is only **2.32** GiB (`results/abi3/deepseek_v4_long_context_projection.json`). <!-- figure: 48.8 src="results/abi3/deepseek_v4_long_context_projection.json#derived.memory.hc_post_mix_intermediate_bytes" scale="0.000000000931322574615478515625" name="hc_post intermediate, GiB" --> <!-- figure: 2.33 src="results/abi3/deepseek_v4_long_context_projection.json#derived.memory.indexer_score_unchunked_bytes" scale="0.0000000000009094947017729282379150390625" name="unchunked indexer score, TiB" --> <!-- figure: 2.32 src="results/abi3/deepseek_v4_long_context_projection.json#derived.memory.persistent_kv_and_rope_bytes_measured" scale="0.000000000931322574615478515625" name="persistent KV and rope, GiB" --> *(This is the reference-oracle GPU lane, not the accelerator.)*
- [x] W10.6 DeepSeek agentic scenario — 47 tokens to EOS, well-formed DSML tool call, byte-identical across independent process invocations

## W13 — The end-to-end requirement, stated plainly

The stated requirement is that **every** design runs the real model end to end
and produces validated real tokens, on reasoning *and* agentic tasks. Against
that, the position is:

- [x] W13.1 Qwen3-8B **HBM** lane — 24 tokens, oracle-identical <!-- figure: 24 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.generated_token_count" name="Qwen HBM generated tokens, TA-QW-CHAT-1" -->
- [x] W13.2 Qwen3-8B **ROM** lane — 24 tokens, oracle-identical, and identical to <!-- figure: 24 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.generated_token_count" name="Qwen ROM generated tokens, TA-QW-CHAT-1" -->
  the HBM lane position for position
- [ ] W13.3 DeepSeek-V4-Flash **HBM** (32 node) — **zero tokens.** The node
  dimension now exists and the committed record retires **251** instructions <!-- figure: 251 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.counters['instructions.retired']" name="DeepSeek HBM retired, W13.3" -->
  (`results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json`);
  `a2cb06a` reports 299 and `88b3bcd` reports 1,896 with no record re-recorded, and
  the static audit of 21 defect groups across 1,173 of 3,230 operators predates all
  three. See W6.3 for what here is evidence and what is a commit message
- [ ] W13.4 DeepSeek-V4-Flash **ROM** (wafer) — **zero tokens.** Nine blockers
  climbed; the committed record still stops at the residual-add wall, the commit
  trail reaches 9,189 retired at `29e50c2` and stops on an A18 predicate at ratio
  128, and [OI-41] — now closed — named `ATTENTION.SPARSE`'s scalar reference as the standing
  cost. No artifact republishes any of it — see W6.4
- [x] W13.5 Qwen **reasoning** generation with thinking enabled — **closed.**
  `TA-QW-REASON-1` is the chat question rendered with thinking enabled, and the
  accelerator decoded **512** tokens of the model's own `<think>` block on the HBM <!-- figure: 512 src="results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json#record.generated_token_count" name="TA-QW-REASON-1 tokens" -->
  lane: status `pass`, `reference_agreement` true, no divergence index <!-- figure: "pass" src="results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json#status" name="TA-QW-REASON-1 status" -->
  (`results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json`).
  The external oracle ran the same workload to **3,072** tokens and the <!-- figure: 3,072 src="results/abi3/qwen3_reference_oracle_reasoning.json#results.TA-QW-REASON-1.generated_token_count" name="reasoning oracle tokens" -->
  accelerator matches it token for token over the 512 it decoded, then stopped at
  its decode budget rather than at EOS. So what closes is *reasoning generation
  with thinking enabled*, evidenced; a reasoning run carried to its own EOS is
  not, and neither lane has one
- [x] W13.6 Qwen **closed-loop agentic episode** — **closed.** `TA-QW-AGENT-2`
  closed the loop entirely on the accelerator: **2** turns, **1** command actually <!-- figure: 2 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#turn_count" name="agent episode turns" --> <!-- figure: 1 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#executed_command_count" name="agent episode commands executed" -->
  executed in the sandbox (`awk -F, '{sum += $2} END {print sum}' inventory.txt`,
  exit 0, stdout `239`), the observation fed back, and the second turn answered
  **239**, which equals the task's `expected_total`; `task_solved` true <!-- figure: 239 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#expected_total" name="agent episode expected total" --> <!-- figure: "239" src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#answer" name="agent episode answer" -->
  (`results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json`).
  Every command executed was produced by the accelerator and parsed fail-closed;
  the harness never writes or repairs one. **The record's own status is
  `diverged`, not `pass`**, and the reason is the token horizon of [OI-33] rather <!-- figure: "diverged" src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#status" name="agent episode status" -->
  than the loop: turn 0 leaves the oracle episode at generated index **286** and <!-- figure: 286 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#turns[0].oracle_comparison.first_generated_divergence_index" name="agent episode first divergence" -->
  turn 1 at index 23, with both prompts matching exactly and both episodes
  reaching the same command and the same answer. The closed loop is what closes;
  the oracle-identity claim at this length does not, and W11.1 states that horizon

W13.3 and W13.4 are the two that remain open, and both are DeepSeek. The honest
summary is that **two of four designs run the model end to end** — both Qwen
lanes, token-identical to the oracle and to each other at 24 tokens, with the ROM
lane also oracle-identical over **192** tokens at the 8,000-token context — and <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.generated_token_count" name="Qwen ROM 8K tokens" -->
the performance comparison — W12 — rests on those two, under the horizon W11.1
states.

## Findings of 2026-08-30 — three defects that passed every check

Three defects landed tonight that share one shape: **the verification was
self-consistent with the defect**, so nothing failed. They are recorded together
because the pattern matters more than any of them.

- **Both backends placed only the first segment of a segmented binding.** The
  256-expert stacked weights are bound as 256 authenticated ranges; both
  backends read `binding.path/offset/bytes` and ignored `binding.segments`, so
  each stack was placed as **one 1 GiB range from expert zero's offset** — 255
  of every 256 experts named by an address holding another expert's bytes. The
  byte totals reconciled and the digests were computed over what *was* placed
  rather than over what *should* have been, so every check passed. Fixed: 2,424
  → **68,214** authenticated ranges, the ROM deployment's 228 regions and
  156,015,698,140 payload bytes unmoved, and exactly **24 region content digests
  changed** — the 12 expert banks and their 12 scales.

- **The HBM lowering read a generation-policy key the IR does not emit.** It
  asked for `max_new_tokens` where the IR emits `maximum_new_tokens`, so the
  lookup always missed and every HBM deployment silently carried the 512
  default while the ROM backend read 8,192 from the same IR. **Two backends
  carrying different generation policies for one IR is the divergence a shared
  IR exists to prevent**, and it is invisible until a generation runs long
  enough to hit the smaller cap, where it looks like the model stopping early.
  Five synthetic test graphs declared the same wrong key, so they passed by
  agreeing with the defect rather than with the IR — the same shape as the block
  loop tests that asserted `step == bound_divisor` and pinned [OI-22] in place.
  Neither backend defaults now: a graph that appends tokens without declaring a
  budget is a graph whose decode length nobody chose.

- **The cycle model reported zero bytes for every storage class.** `8dfddac`
  gave the functional device a node dimension, and `_issue_nodes` rebinds
  `ctx.views` to the uninstrumented node-0 resolver before every engine issue —
  overwriting the recording resolver `TracingDevice` had installed. It stayed
  quiet because the *architectural* counters come from a different path
  (`EngineContext._account_read/_account_write`) and remained correct
  throughout, so the counter-agreement test stayed green while the memory report
  read zero. The same commit also made `run_node` time all 32 nodes and call it
  one: 17,986 per-node compute cycles against 564 for the identical program on
  one chip, then multiplied by 32 again in the aggregate. **A 32× timing error
  and a zeroed memory report, in the one component that models time at all.**

The common lesson is in the third: a check that passes because two paths agree
proves only that they agree. The memory report and the architectural counters
were never reconciled against each other, and the test that does that now is the
test that would have caught it on the day.

## OI-39 — the sparse KV model was 3x low, in the term the whole argument rests on

**Found by measuring, and it cost us our headline number.** The DeepSeek-V4-Flash
profile under-predicted KV read traffic by **2.72x at 32,000 tokens and 3.13x at
128,000**, with the error growing with context. It went unnoticed because
nothing had ever executed this model far enough to compare — the reference
oracle's context ladder declared five rungs and had run two.

The profile's **structure was correct and is unchanged**. The engine's per-layer
pair counts match it exactly at both contexts: `csa` reads `top_k + window` main
entries and scans `context/4` index entries, `hca` reads `context/128 + window`,
`window` reads 128. Two per-entry constants were wrong:

| | was | measured | factor |
|---|---:|---:|---:|
| `entry_bytes` (all groups) | 583 | **1,024** | 1.756 |
| `index_entry_bytes` (csa) | 68 | **256** | 3.765 |

Corrected, the profile predicts 64,800,000 B/step where the engine read
64,774,144 (**0.9996**) and 209,184,000 where it read 209,158,144 (**0.9999**).

**The root cause is a precision disagreement, not a transcription slip.** 583 is
an FP8 assumption — 576 elements (512 latent + 64 rope) at one byte plus scale
bytes — and the released implementation reads the 512-wide latent at BF16, which
is 1,024. A deployment that genuinely stored an FP8 latent *would* read 512
bytes; that is a design choice, it must then apply to both sides of a
comparison, and it is recorded in the profile rather than assumed.

**What it cost.** The weight-to-KV read ratio is the figure of merit for the
entire ROM case, and it was overstated:

| model | context | was | now | overstated |
|---|---:|---:|---:|---:|
| Flash | 8,192 | 853.2:1 | 387.3:1 | 2.20x |
| Flash | 200,000 | **113.2:1** | **35.3:1** | **3.20x** |
| Pro | 1,000,000 | 58.9:1 | 18.0:1 | 3.27x |

Every DeepSeek roofline number is stale in a known direction: KV is three times
heavier, so it binds earlier, the weight-bound regime in which a sparse model
batches for free ends at a lower batch, and the long-context advantage shrinks.
Qwen is unaffected — its KV term was already exact against executed hardware.

Pro carried the identical constants from the identical derivation and has been
corrected by analogy, graded `assumed_by_analogy` in the profile because no Pro
rung has ever been executed. **That grade is load-bearing on one of the three
headline claims and only a Pro execution retires it.**

`tools/validate_kv_model_against_oracle.py` makes this checkable. It reports
positions, bytes-per-position and the total *separately*, because a structural
error and an entry-size error look identical in the total and have completely
different fixes — that separation is what turned "the model is 3x off" into
"these two constants are wrong and the structure is right." Two regression
tests: both rungs within 1%, and the historical 583/68 pair rejected including
its growth with context, which a pure scale error would not show.

- **OI-40 — the IR binds 6.5% fewer weight bytes than the profile claims.** The
  neutral IR binds 156,015,698,140 bytes across its weight tensors where
  `checkpoint_bytes` declares 166,878,536,440, a 10.86 GB gap. This is
  *conservative* — it would size ROM larger than the executed graph needs — so
  it is not a flattering error, but it is unexplained, and after OI-39 an
  unexplained gap in the other half of the same ratio should not be left
  standing. Likely candidates: multi-token-prediction layers or other tensors
  the exporter correctly drops. Not yet investigated.

## W12 — First-principles roofline model *(the actual deliverable)*

### Where the model stands, 2026-08-30

Every W12 item is built and every published number has been re-derived at least
once tonight. **Each correction moved the result against us, and each was found
by measuring rather than by arguing.**

| the claim | was | is | why it moved |
|---|---:|---:|---|
| Pro @1M, 554,700 mm², batch 1 | 54.2× → 35.4× | **8.3×** | GPU denied a topology; then per-user latency conflated with throughput | <!-- figure: 8.3 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after" table="latency separation" where="Model=DeepSeek-V4-Pro-0813;mm2=554700" name="Pro batch-1 iso-area ratio at 554,700 mm2, N6" -->
| Flash weight:KV @200K | 113.2:1 | **35.3:1** | two KV entry sizes read off the implementation, not measured | <!-- figure: 35.3 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].weight_to_kv_read_ratio_b1" name="Flash W:KV at 200K" -->
| Pro weight:KV @1M | 58.9:1 | **18.0:1** | the same two constants, by analogy | <!-- figure: 18.0 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].weight_to_kv_read_ratio_b1" name="Pro W:KV at 1M" -->
| on-wafer tensor-parallel | 116,278 tok/s | **6,000–7,200** | an all-reduce charged one flat hop however far it reached | <!-- figure: 7,200 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1" tol="1%" name="on-wafer tensor hard ceiling, Qwen3-8B" why="the row states a deliberately rounded band; the artifact's Qwen on-wafer hard ceiling is 7,215.0 tok/s and Flash's is 6,040.5. The tolerance is the rounding the band declares, not slack." -->
| N5 vs B200, Pro @1M | 27.3× | **4.01×** | both of the above | <!-- figure: 4.01 src="results/roofline/n5_vs_b200/REPORT.md#Ratio after" table="latency separation" where="Model=DeepSeek-V4-Pro-0813;mm2=554700" name="Pro batch-1 iso-area ratio at 554,700 mm2, N5" -->
| per-region over broadcast @b64 | 27× | **3.19×** | mean engaged-region load where the physics is the busiest | <!-- figure: 3.19 src="results/roofline/n6_vs_a100/REPORT.md#Per-region over broadcast" table="batch-amortisation" where="Model=DeepSeek-V4-Flash-0731;B=64;Spare silicon=sram" name="per-region over broadcast, Flash b64 sram" -->

**Two conclusions inverted rather than shrank**, which matters more than the
magnitudes:

- *"The ROM advantage erodes with batch"* holds only for the **dense** model.
  Qwen goes 8.24× at batch 1 to **0.98× at 256** — the GPU wins outright. Both <!-- figure: 8.24 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=Qwen3-8B;B=1;Pick=fastest" name="Qwen per-user iso-area ratio at B=1" --> <!-- figure: 0.98 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=Qwen3-8B;B=256;Pick=fastest" name="Qwen per-user iso-area ratio at B=256" -->
  sparse models now **rise**: Flash 8.57× → **35.13×**, because a GPU's per-user <!-- figure: 8.57 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=DeepSeek-V4-Flash-0731;B=1;Pick=fastest" name="Flash per-user iso-area ratio at B=1" --> <!-- figure: 35.13 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=DeepSeek-V4-Flash-0731;B=256;Pick=fastest" name="Flash per-user iso-area ratio at B=256" -->
  rate collapses faster than a ROM machine's once KV dominates. The original
  thesis — that sparsity is what makes ROM worth building — survives in a
  stronger form than it was stated.
- *"Bigger is better"* is false for latency. ROM per-user throughput falls
  **monotonically** with area, 6,505 tok/s at one wafer to 3,447 at twelve, so <!-- figure: 6,505 src="results/roofline/n6_vs_a100/REPORT.md#ROM after" table="latency separation" where="Model=Qwen3-8B;mm2=46225" name="Qwen ROM user tok/s at one wafer" --> <!-- figure: 3,447 src="results/roofline/n6_vs_a100/REPORT.md#ROM after" table="latency separation" where="Model=Qwen3-8B;mm2=554700" name="Qwen ROM user tok/s at twelve wafers" -->
  the best latency machine is the **smallest one that holds the model**.

**What the gates say.** The A100 gate is arithmetic and holds at 1.000000× <!-- figure: 1.000000 src="results/roofline/n6_vs_a100/REPORT.md#Ratio" table="Validation gates" where="Gate=A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2" name="A100 validation gate ratio" -->
through every correction. The Taalas HC1 gate now **under**-predicts at 0.72×, <!-- figure: 0.72 src="results/roofline/n6_vs_a100/REPORT.md#Ratio" table="Validation gates" where="Gate=Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user" name="Taalas HC1 validation gate ratio" -->
having over-predicted at 1.23× before the corrections — a reversal, not a
tuning, and the per-layer fixed cost was deliberately derived from primitives
rather than fitted to close it. The value that *would* have closed it is
negative, so no setting of that term could have.

**What is still wrong and is not hidden.** Every watt is 7–9× low against both
published parts, and the cause is structural rather than a missing multiplier —
an A100 driven at peak bandwidth *and* peak compute simultaneously still comes
out 4.7× low. No *rate* depends on it: `thermal_scale` is exactly 1.0 at all
feasible points, and that is shown structurally rather than asserted. It is
therefore a gap in what we may claim, not an error in what we do claim, and no
watt should be quoted until it is fixed.


The program's purpose is a quantitative ROM-versus-HBM comparison. The functional
lanes are a precondition for it, not the product. These items are the product.

- [x] W12.1 `src/opentallas/roofline.py` — area-constrained roofline: a silicon
  area budget is allocated across ROM array, compute, SRAM, interconnect and HBM
  PHY, and capacity, bandwidth and compute roof are **derived outputs**. Replaces
  the placeholder profiles whose capacity and compute roof were independent free
  parameters with nothing tying either to area
- [x] W12.2 `configs/hardware/technology.json` — every density, latency and
  energy figure graded `measured`/`published`/`derived`/`assumed` with a source
- [x] W12.3 Latency model for distributed decode — decode is sequential across
  tokens *and* layers, and at batch 1 a pipelined array supplies no parallelism
  at all, so topology is chosen by hop latency against the per-token budget:
  single chip (0 hops), array with pipeline parallelism (N−1 serial hops), array
  with tensor parallelism (2 × layers collectives), wafer (on-wafer hops)
- [x] W12.4 MoE utilisation term — ROM weights are local to compute, so an
  unselected expert region contributes neither bandwidth nor compute. Engagement
  is `1 − (1 − k/N)^B`, not a constant
- [x] W12.5 **Validation gate: the model must reproduce Taalas HC1** — an 8B
  model on 815 mm² at N6 near ~17,000 tok/s per user, as a named test that fails
  loudly. A model that cannot reproduce a shipping part must not be used to
  predict one that does not exist. Second gate: an A100 on an 8B model at batch 1
  must come out weight-bound at ~254 tok/s, which is pure arithmetic
- [x] W12.6 Iso-area studies with the silicon area stated on **both** sides, both
  topologies where viable, and the latency crossover reported rather than a
  topology assumed
- [x] W12.8 **The model is validated by the executed machine, not asserted.**
  `tools/validate_model_against_execution.py` checks an analytical prediction
  against the counters a real token-producing run recorded. On Qwen3-8B at 8,192
  tokens the analytical weight traffic is 15,136,811,008 B per step; the ROM lane
  measured **15,244,065,514** (ratio 1.007) and the HBM lane **15,262,287,257**
  (1.008), and the two lanes performed **identical arithmetic** —
  820,644,937,728 multiplications each. The 0.7–0.8% excess is the scales, index
  tables, rotary coefficients and activations the analytical weight model does
  not count; a *shortfall* would be a failure rather than a tolerance, and the
  tool treats it that way.

  This is what separates the performance work from arithmetic on a whiteboard. A
  reviewer is entitled to ask whether a projected speedup accounted for the whole
  system, and the only answer that settles it is a machine that ran the model end
  to end and moved the same bytes the projection assumed. It also makes the
  storage-class thesis a measurement: the two lanes differ only in which memory
  the bytes came from, and the arithmetic is bit-identical.

  What it does not validate is *time* — the functional device has no clock. It
  validates the quantities a roofline consumes, so that the time a roofline
  computes from them is a statement about hardware rather than about unexamined
  traffic.

  **The KV term is now checked too, and it comes out exact.** Until tonight the
  tool predicted KV traffic and never compared it to anything, which left the
  most important number in the model resting on nothing: at the 8,000-token
  sweet spot KV is the term that decides the ROM argument. It is checked in two
  halves because they catch different failures. The count of (layer, position)
  pairs attention visited is compared against the causal triangle a prompt of
  *P* tokens and *D* decode steps requires, which catches a machine that
  recomputes, caches across queries, or attends to a window instead of the whole
  past. The byte count is then compared against the profile's own entry size,
  which catches a row read at the wrong precision or width. Unlike weight
  traffic this term admits no allowance in either direction — nothing rides
  along with a KV row — so the tolerance is 0.1%, not 15%.

  | run | causal pairs | ratio | KV bytes | ratio | B per layer-position |
  |---|---:|---:|---:|---:|---:|
  | `TA-QW-CHAT-1` HBM | 244,296 | 1.0000 | 1,000,636,416 | 1.0000 | 4,096 | <!-- figure: 244,296 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.counters['attention.context_positions']" name="chat HBM causal pairs" --> <!-- figure: 1,000,636,416 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.counters['attention.kv_bytes_read']" name="chat HBM KV bytes" -->
  | `TA-QW-CHAT-1` ROM | 244,296 | 1.0000 | 1,000,636,416 | 1.0000 | 4,096 | <!-- figure: 244,296 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.counters['attention.context_positions']" name="chat ROM causal pairs" --> <!-- figure: 1,000,636,416 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.counters['attention.kv_bytes_read']" name="chat ROM KV bytes" -->
  | `TA-QW-8K-1` HBM | 1,208,107,008 | 1.0000 | 4,948,406,304,768 | 1.0000 | 4,096 | <!-- figure: 1,208,107,008 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.counters['attention.context_positions']" name="8K HBM causal pairs" --> <!-- figure: 4,948,406,304,768 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.counters['attention.kv_bytes_read']" name="8K HBM KV bytes" -->

  The 8,000-token row is the one that matters: a machine that generated 193 real
  tokens at the stated sweet spot moved **4.95 TB of KV** and visited
  **1,208,107,008** (layer, position) pairs, and both are the analytical formula
  to the byte. The roofline's own Qwen designs size SRAM for 1,207,959,552 B of
  resident KV — 100.4 mm² of an 815 mm² die at N6 — from the same 4,096 bytes
  per layer-position that the machine was just measured reading. The prediction
  and the measurement are not merely close; they are the same number arrived at
  from opposite directions.

  The entry size is derived from the profile's traffic model rather than restated
  in the tool, so editing a profile cannot silently pass the check, and two
  mutation tests in `tests/test_execution_validation.py` halve the KV bytes and
  narrow the attention span to prove the check can fail. A validator nobody can
  fail is decoration.

- [x] W12.7 `tools/run_roofline_studies.py` and `results/roofline/` — canonical
  JSON, rendered report, consistency audit

## W11 — Governed comparison and release

- [~] W11.1 Qwen ROM vs HBM — **produced at 24 tokens, and QUALIFIED at 192.** At the
  8,000-token sweet spot with a matched 192-token budget the two lanes **disagree**:
  ROM matches the reference oracle on all 192, HBM diverges at index 137, emitting <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.generated_token_count" name="Qwen ROM 8K tokens, W11.1" --> <!-- figure: 137 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.notes.first_divergence_index" name="Qwen HBM 8K divergence index" -->
  " world" where ROM and the oracle emit " universe". The mechanism is countable
  rather than speculative. The two lanes perform the same arithmetic to the
  operation — `tensor.multiplications` 57,012,268,302,336 on both, identical <!-- figure: 57,012,268,302,336 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.counters['tensor.multiplications']" name="Qwen ROM 8K multiplications" --> <!-- figure: 57,012,268,302,336 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.counters['tensor.multiplications']" name="Qwen HBM 8K multiplications" -->
  `attention.context_positions`, `kv_bytes_read` and `vector.elements` — while
  `control.loop_iterations` differs, 138,816 against 149,121. Same operations, <!-- figure: 138,816 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.counters['control.loop_iterations']" name="Qwen ROM 8K loop iterations" --> <!-- figure: 149,121 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.counters['control.loop_iterations']" name="Qwen HBM 8K loop iterations" -->
  different tiling, different accumulation order, different last-ULP logits: A7
  working as specified, since the blocked association is fixed by (library,
  version, device, **shape**, thread count) and the storage class determines the
  shape. What decides index 137 is `selection.tie_multiplicity` — 192 over 192
  tokens on ROM, **193 over 192 on HBM**. Exactly one HBM token has two candidates <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.counters['selection.tie_multiplicity']" name="Qwen ROM 8K tie multiplicity" --> <!-- figure: 193 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.counters['selection.tie_multiplicity']" name="Qwen HBM 8K tie multiplicity" -->
  at the argmax and the tie rule takes the lowest id, 1879 over 15494.

  **So the thesis holds for traffic and arithmetic and does not extend to the
  token stream at long context.** *"The two deployments differ only in where the
  bytes live"* is demonstrated at 24 tokens and false at 192, because where the
  bytes live determines the tiling. A token-identity claim between two backends
  has a horizon and the horizon must be stated: 137 tokens here, 286 on the
  agentic workload. This is a qualification of the claim, not a defect in either
  lane — both are correct under their declared contracts, and the analytical model
  validates against both at ratio 1.0000 on KV traffic and causal pairs.

  The original 24-token result stands as recorded: **produced, and it is the
  storage-class thesis in executed counters** (`results/abi3/comparison_qwen_rom_vs_hbm.json`). Both lanes decoded 24 tokens matching the oracle, the two token sequences are identical, evidence class `functional_artifact_only`, `depends_on_assumption` false. **Five counters differ and all five are memory traffic**: the ROM target reads 363,485,791,728 B from ROM and the HBM target reads 366,294,894,160 B from HBM <!-- figure: 363,485,791,728 src="results/abi3/comparison_qwen_rom_vs_hbm.json#counter_deltas['rom.bytes_read'].left" name="ROM target ROM bytes read" --> <!-- figure: 366,294,894,160 src="results/abi3/comparison_qwen_rom_vs_hbm.json#counter_deltas['hbm.bytes_read'].right" name="HBM target HBM bytes read" -->, and the ROM target moves 437 MB / 61 MB through SRAM where the HBM target moves none. Nothing else in the 121-counter registry differs. That is the claim — *the two deployments differ only in where the bytes live* — demonstrated on executed counters rather than argued. The DeepSeek half waits on W6.3/W6.4
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
  short. The correlation campaign compares 454 resolved views against <!-- figure: 454 src="results/rtl/abi3_campaign.json#correlation.view_resolution_count" name="RTL resolved views, OI-16" -->
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

- **OI-35 — the cluster sharding plan replicates the experts, so a 256-expert
  MoE produces no expert-dispatch traffic at all.** Under
  `shard_axis = output_columns` the expert-dispatch (42 sites), sparse-gather
  (210) and reduction (126) kernels hold identical operands on every node and
  move nothing, so the lowering emits no collective for them — recorded in
  `deployment.notes["replicated_link_sites"]`. That is the honest thing to emit:
  gathering 32 identical buffers into a destination nothing reads would put
  messages and bytes into the very comparison this program exists to make
  honest. **But it must be said out loud in any ROM-versus-HBM write-up**, because
  it flatters the HBM cluster: a real deployment shards experts across nodes and
  pays dispatch traffic for it. The absence is a property of this sharding plan,
  not of the model, and the fix is to shard the experts rather than to declare
  the transfer.

- **OI-36 — `main.lm_head.select` gathers the first token of the span, not the
  last, and no engine check can catch it.** It selects row `position_offset`
  where it must select the final position. Every operand check passes: the
  shapes are right, the dtypes are right, the view is in bounds. It is simply
  the wrong row. Latent today because the lane fails earlier, and it would
  produce logits for the wrong token the moment the operands above it are fixed
  — which is exactly the class of defect that survives to the end and then
  produces fluent, wrong output. Amendment A12 exists for this
  (`SPAN_LAST_INDEX`); the exporter has not adopted it here.

- **OI-37 — a static audit found 21 defect groups affecting 1,173 of 3,230
  DeepSeek operators (36%), none span-dependent.** Roughly 705 sit in the HBM
  backend, 426 in the shared exporter and neutral IR, and 42 in the engines. Two
  are cross-cutting and worth more than the individual repairs: **nothing
  anywhere compares `len(kernel.inputs)` against `engine_for(kind).inputs`**, so
  four defect groups reach the simulator as `NO_ID` in a mandatory slot instead
  of failing at compile time; and `lowering.py` declares `EXPERT_DISPATCH` with
  two outputs while `route.py` never writes `output_view_1`, so a plane the plan
  believes exists does not. The first of those is a one-off check that would
  have turned four runtime mysteries into four compile errors.

- **OI-34 — the mandatory Qwen workload does not fit the context the capability
  declares, and the device said so exactly where it should.** `TA-QW-8K-1`
  stopped at decode step 193 with

      DMA index view 45 names row 8192, outside the 8192 rows of the addressed view

  which is arithmetic, not a bug: 8,000 prompt tokens plus 192 decoded is 8,192,
  and `max_context_positions` is 8,192. The 193rd token needs row 8,192 and there
  is no such row. It failed closed at precisely the right position rather than
  wrapping, truncating or quietly computing against stale rows.

  The workload contract asks for 8,000 natural prompt tokens decoded **to first
  EOS**, with `max_new_tokens` 256. That needs 8,256 positions. The two documents
  have never been reconciled: the mandatory prompt length was fixed at 8,000 and
  the capability's context at 8,192, leaving 192 tokens of headroom for a
  contract that asks for up to 256. Either the declared context rises to 8,256 or
  beyond, or the contract states a decode budget the context can hold. **This is
  a specification question and it is mine, not an implementation defect** — and
  it went unnoticed because until tonight nothing had ever run long enough at
  that context to reach the boundary.

- **OI-33 — the accelerator's tokens diverge from the oracle on the
  repeated-token stress workload, and this is the first token divergence this
  program has produced.** `TA-QW-STRESS-1` ran to completion — 8,000 prompt
  tokens, 32 decoded, 11,941 s — and was recorded `status: diverged`, not
  `pass`, which is the reference gate doing exactly the job it was given this
  morning. Under the campaign runner as it stood twelve hours ago this would
  have been recorded as a pass, because nothing compared the tokens to anything.

  The divergence is small and highly structured, and the structure is the
  finding:

  | | |
  |---|---|
  | prompt | 8,000 tokens, **one distinct token id** — maximally degenerate |
  | first divergence | index 2: accelerator `279` (" the"), oracle `264` (" a") |
  | then | the oracle emits a third `271` newline; the accelerator emits two |
  | after that | accelerator `[3:12]` **equals** oracle `[4:13]` exactly — a nine-token aligned run at shift +1 |
  | ties | `selection.tie_multiplicity` 33 over 32 tokens, so exactly one genuine tie |
  | legitimacy | no problems; every token in vocabulary |

  So the two are producing the *same continuation*, offset by one, after a
  single word choice flipped between near-tied candidates. This is not a broken
  computation; it is an argmax flip in a regime where the logits are nearly
  degenerate by construction.

  **What it falsifies is a claim this program has been resting on.** Amendment
  A7's justification measured the blocked contract against the sequential one
  and found 0.012–0.089% of elements differing by 1–5 ULP with *zero* vocabulary
  argmax changes. That measurement was taken on natural prompts. It does not
  hold here, and a workload of 8,000 identical tokens is precisely the instrument
  for finding that out — which is what the mandatory stress contract is for.

  **The discriminating experiment has now answered: degeneracy, not context
  length.** `TA-QW-8K-1` is natural prose at the same 8,000-token context. It
  agreed with the oracle for **137 consecutive tokens**, then substituted
  ` world` for ` universe` in *"the whole of the ___ and its inhabitants"* — two
  interchangeable words after an identical 137-token prefix — and **realigned
  immediately**, agreeing again from index 138. No ties were involved anywhere:
  `selection.tie_multiplicity` is 193 over 193 tokens, multiplicity one each.

  So A7's claim is **qualified, not withdrawn**. Zero argmax changes over 137
  tokens of natural prose at the mandatory context; an argmax flip at index 2 on
  a prompt of 8,000 identical tokens. The contract is sound for the inputs it
  was measured on and the stress workload marks the boundary — which is what it
  is for. The honest statement is that the blocked contract preserves the
  argmax on natural text and does not preserve it under engineered degeneracy,
  and A7 should say so rather than claiming a general invariance.

- **OI-32 — one capability, two sources of truth, and they have now diverged.**
  `configs/hardware/abi3_capability/hbm_sram_single_chip.json` and
  `compiler.backends.hbm_sram.capability.PROFILES['single-chip']` both claim to
  be the shared single chip. They no longer agree: the code-built profile lists
  `deepseek_rmsnorm_binary32_v1` and the file on disk lists
  `normalization_rms_norm_bf16_v1`, so their digests are `7afce65b…` and
  `b2a1af21…`. The campaign runner takes the JSON; the tests and the checkers
  take the code.

  It surfaced because a byte-identity claim did not survive checking. Adopting
  A8's frozen RMSNorm contract name in the DeepSeek exporter changed the derived
  contract union, which changed the code-built capability, which changed **Qwen's
  deployment digest** — `11d825368add0494` → `bd80131488912974` — while Qwen's
  program body and descriptor table stayed byte-identical (all 75 instructions
  equal, table digest `7d599fdcd8c017ce` on both sides). The agent that made the
  change deliberately left the JSON alone *because* editing it would move Qwen's
  digest, and the digest moved anyway through the other source. That is the
  whole hazard in one sentence.

  Nothing here is wrong in itself: a deployment binds the capability it was
  admitted against, so a capability change *should* change its digest. What is
  wrong is that there are two capabilities with one name, and a change to either
  is invisible from the other. **One must be generated from the other, with a
  check that fails when they drift** — `tools/publish_abi3_capabilities.py`,
  added for this, makes the code profile the definition and the JSON a published
  artifact. It currently reports both files drifted
  (`hbm_sram_single_chip` profile `7afce65b…` against published `b2a1af21…`;
  `hbm_sram_cluster_32` profile `93fe2c66…` against published `3afaa0fa…`).
  **Republishing is deliberately deferred**: the two 8,000-token Qwen workloads
  are executing against the published files right now, and rewriting them
  mid-run would leave those records citing a capability digest the repository no
  longer contains. It is a one-command step once they land, and it will change
  the deployment digest of everything admitted against them — which is correct,
  and is exactly why it should be a deliberate act rather than a silent one — the same discipline `loop_trip_count` now
  enforces for the trip formula (OI-22) and for the same reason: two
  restatements of one thing is how two of them come apart.

- **OI-31 — a vector set can rot into agreeing with the implementation instead
  of checking it.** Refining A13 changed what `a13_nested_blocks` resolved to,
  and the obvious response — re-record the golden — would have been wrong: that
  case exists to exercise the `min()` fold of two clamping loops, and under the
  refined rule its second loop no longer qualified, so re-recording would have
  kept the test green while deleting what it tested. It was repaired instead, by
  changing the loop's block *and* its stride together.

  `a13_four_terms` had the identical defect and nobody had noticed. Its golden
  would have silently become `[4, 4, 1, 1]` on the next regeneration, with its
  docstring still describing a fold that no longer happened. It was found by
  someone reading the case, not by any test.

  The general point is worth keeping: a golden regenerated from the
  implementation it checks is only as good as the reason the case was written,
  and that reason lives in prose. When a rule changes, every case that depended
  on the old rule has to be re-read, not re-recorded. The two new cases here —
  the mHC shape and the mixed-axis view — had **no** coverage before, and the
  mutation evidence shows it: dropping the stride condition survives cases 0
  through 23 and dies only at case 24.

- **OI-30 — commit `8841b95` carries another change's admission proofs.** A14's
  two `participant_scope` refusals were staged into my A13 clamp fix, because I
  staged `runtime/abi3/verifier.py` whole while an agent was adding to it. The
  code is correct and present in HEAD; only the history misattributes it. This is
  the third time tonight that staging a file rather than a change has muddled a
  commit, and it is the reason a `git add <path>` on a shared file is not
  actually safer than `git add -A` while anyone else is writing.

- **OI-28 — the DeepSeek 32-node HBM lane cannot produce a token, and the
  reason is upstream of every operand issue: the functional device has no node
  dimension.** 96 tensor views in the `cluster_32` lowering carry a `NODE_ID`
  term. `Symbol.NODE_ID` and `Symbol.NODE_COUNT` exist in the registry, and
  neither `runtime/driver.py` nor `runtime/sim/device.py` mentions either —
  only the verifier and the cycle model do. Binding `NODE_ID = 0` would not
  rescue it: one device would compute a thirty-second of every contraction and
  the LINK all-gather would have no peer.

  **This changes which DeepSeek target is reachable, and the answer is the
  wafer.** `rom_deepseek_v4` declares `topology_class = 2` with `max_nodes = 1`
  — a wafer-scale logical device is *one node*, which is the whole content of
  that topology class — so it needs no multi-node simulation at all. Its
  collectives are tile-scoped, which is exactly what amendment A14 makes
  expressible. `hbm_sram_cluster_32` declares 32 nodes and genuinely does need a
  simulator that has more than one.

  So W6.4 (wafer) is the DeepSeek execution path that can close, and W6.3
  (32-node) is blocked on functional multi-node execution that does not exist.
  The 32-node deployment still admits, still proves its work bound, and is still
  covered by the cycle model; what it cannot do is produce a token. A report must
  say that in those words rather than let "admitted" stand in for "ran".

- **OI-29 — `REDUCTION.EXPERT_SUM` cannot express the mHC branch reduction.**
  It reduces the *leading* axis of `in0` and takes one weight per leading index,
  and the mHC branch weights vary per token **and** per stream. Four framings
  were tried and each is refused for a different structural reason, including
  one per-token descriptor, which A13's own admission rule now forbids because
  `dim0 > bound_divisor`. Two resolutions are on the table: apply the weight
  before the reduction under amendment A10 — bit-exact, since the reference is
  four binary32 products reduced by a balanced tree and converted once, not a
  fused product-add — at the cost of a materialised `[span, 4, 4096]` binary32
  intermediate and a stream-major view whose leading axis is no longer the token
  axis, which **silently** defeats A13 when `span mod block` is 1, 2 or 3; or
  amend the operand row so the weight may match the first two axes.

  **Deliberately not decided.** The lane it would unblock is blocked upstream by
  OI-28, so choosing now would settle a question whose answer cannot be used or
  tested yet. The word that decides it is *silently*: a resolution that defeats
  A13 without saying so is the shape of defect this program has spent its whole
  effort removing, so the operand-row amendment is the likely answer — but it
  should be made against a lane that can execute and prove it.

- **OI-27 — the governed comparison tool cannot produce a comparison. Any
  comparison.** *(Fixed; the first comparison now exists — see W11.1.)* `tools/build_comparison_report.py` exists to compare Qwen ROM
  against Qwen HBM and the DeepSeek wafer against the DeepSeek cluster. Run on
  the first pair that has ever had two real records, it refuses on three counts,
  and two of them are structural — no pair of distinct deployments can ever
  satisfy them.

  1. **`generation_policy_digest` digests deployment-local identifiers.** The
     two Qwen lanes are semantically identical — `selection_mode` 0, `tie_rule`
     0, the same two EOS tokens, the same vocabulary size, zero RNG seed. They
     differ on `token_ring_object_id` (36 vs 24), which two deployments *must*
     assign differently; on a declared `max_new_tokens` bound (512 vs 8192),
     which is a capability limit rather than the run's limit; and on
     `counter_class_id`. Comparing the whole record's digest therefore refuses
     every pair, forever. The gate should compare the policy's *semantics*.
  2. **The `technology_view` gate forbids the study.** "No number crosses views"
     is the right principle for the wrong field: it exists so a SKY130 number is
     never compared with an ASAP7 one. But the capability's `technology_view`
     conflates the *characterization* view with the *memory technology* —
     `single_chip_rom_declared_v1` against `shared-hbm-sram-chip-v3` — and the
     memory technology is the study's independent variable. It has to differ.
     The two axes need separating: gate on characterization, report both memory
     technologies side by side and never normalise them away, exactly as the
     tool already promises for topology cost.
  3. **`tokenizer_sha256` is empty on one side**, and that one is real but
     small: two different evidence writers source it differently. The campaign
     runner reads `workload.metadata.tokenizer_sha256`, which the workload files
     do not carry, while the earlier wrapper read it from the oracle. One
     source, and it should be the workload.

  That the tool has never run is itself the finding. W11.1 and W11.2 were
  blocked on something nobody had tried, and the gate — which is otherwise a
  good gate, and refused for exactly the reasons a good gate should look at —
  had never been exercised against two real records.

- **OI-26 — two agents worked the DeepSeek lane at once and the evidence file
  became a moving target.** `results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json`
  was written at 20:02:11 describing one failure, while the exporter that
  produced it was edited at 20:03:02 and the IR rebuilt at 20:03:31. The record
  on disk is therefore stale against the very tree that wrote it, and a second
  run would have captured a third transient state rather than correcting it. The
  file currently reads `reduction output view 413 holds 425984 elements, expected
  16384` — a shape mismatch in the new reduction path, `104 × 4096` against an
  expected `4 × 4096`.

  This is a coordination failure of mine, not a defect in anyone's code. I gave
  two agents overlapping ownership of one lane, and the visible cost is a
  results file that cannot be trusted to describe any state the repository ever
  had. Evidence files are single-writer artifacts; a lane needs one owner at a
  time. Their *code* did not conflict — the broadcast work, the slot
  permutation, the aux ids and the arena fix all survived — only the record did.

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

- **OI-29 — the measured DeepSeek prefill ladder beyond OI-28.** Because
  OI-28 stops the real graph at the third kernel, the rest of the
  prefill was walked with a *diagnostic* graph in which the branch reduction is
  replaced by a `SELECT` of stream 0 — structurally identical, numerically
  wrong, never published — on the single-chip capability (OI-27 rules out the
  cluster). It admits (911 instructions, 2,114 descriptors) and fails in this
  order (steps 1 and 3 were walked with the mismatch patched locally and the
  patch discarded; only step 2's fix is landed):

  1. `numeric profile 418 names no RMSNorm contract this engine implements` —
     **open, with the fix identified.** Amendment A8 gives the vector engine two
     RMSNorm contracts, names them `qwen3_rmsnorm_fp32_bf16_v1` and
     `deepseek_rmsnorm_binary32_v1`, and makes the engine dispatch on the one
     the NUMERIC descriptor names. Qwen took its name; the DeepSeek exporter
     still names `normalization_rms_norm_bf16`, which is not either of them, so
     the engine refuses all 235 of its RMSNorms rather than guess. The fix is
     the exporter adopting A8's name — one line in
     `CONTRACT_BASE_BY_SOURCE_KIND` — plus adding the already-qualified
     `deepseek_rmsnorm_binary32_v1` to the two HBM capability files and the ROM
     one, and regenerating `spec/abi3/numeric_contract_union.json`. It is
     deliberately **not** an `EXECUTION_CONTRACT` substitution in the HBM
     lowering: that map is executable code, and
     `test_lowering_never_names_a_model` correctly refuses to let a model name
     reach it. Tried that way first; the test caught it, which is the test
     working.
  2. `numeric profile 456 declares epsilon 0x358637bd; the unweighted head
     RMSNorm contract requires the BF16 encoding 0x3586` — **closed.** The
     released *unweighted* head norm is qualified against
     `head_rms_norm_bf16`, which takes a BF16 epsilon code because the kernel
     adds it to a BF16 mean. The NUMERIC field is otherwise a binary32 pattern,
     so the backend now narrows it for that one operand shape. Qwen's head norm
     passes a gain vector, takes the weighted path, and keeps binary32 — the
     narrowing is keyed on the operand arity, not on a model.
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
  `main.layer00.hc_attn_pre.branch_reduce`. Everything before it now runs, and
  the counters say so rather than the absence of an error:
  `vector.mhc_sites = 104` for a 104-token prompt (so `HYPER_CONNECT_PRE`
  executed over exactly the span, with A13's clamp doing its job on a 512-row
  block), `dma.transfers = 3` (the hyper-connection expansion plus the two
  coefficient-plane selects) and `engine.reduction.descriptors = 1` — the one
  that trapped.

- **OI-27 — no multi-node deployment can execute functionally: `NODE_ID` is
  never bound.** The 32-node capability makes every large contraction
  column-sharded (`shard_columns = cols // 32`), and 96 of the resulting tensor
  views carry a `RUNTIME_SYMBOL` term on `NODE_ID`. `runtime/driver.py` binds `SPAN_TOKENS`,
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

- **OI-35 — the DeepSeek compressor's decode position is off by `ratio - 1`, and
  the descriptor has no way to say otherwise.** The released compressor pools
  `ratio` tokens into one row and rotates that row at the position of the
  *first* token it pooled. In prefill that is `g * ratio` for group `g`, which
  is exactly what a strided view of the position range yields; in decode the
  vendor supplies `start_pos + 1 - ratio`, and the same view yields
  `start_pos`. The compressed KV write has the matching gap: its row is the
  completed group's ordinal, which prefill gets right as `g` and decode gets
  wrong as `start_pos`.

  A tensor view offsets by `symbol * stride` and cannot subtract a constant, so
  the two placements cannot be one descriptor. Three ways out, in order of
  preference: split the compressor's kernels by phase, which the neutral IR
  already supports (`phases`) and which no exporter currently uses; add a
  runtime symbol for the completed-group ordinal; or admit a signed dynamic
  term. Not reachable by `TA-DS-CHAT-1` at two decoded tokens — `should_compress`
  is `(start_pos + 1) % ratio == 0` and is false at both steps, so the
  compressor's rotation and write do not fire — but it will be reachable by any
  workload that decodes past a ratio boundary, which is every longer one.

- **OI-36 — the two backends disagree about what `VECTOR.ROPE`'s `aux_id_0`
  holds.** `compiler/backends/rom/common/program.py` falls back to the
  iteration domain's `head_dim`; `compiler/backends/hbm_sram/plan.py` falls back
  to the coefficient view's width, which is twice it. Both write the graph's
  `rotary_width` when it states one, so DeepSeek agrees across backends and
  Qwen — which states none — does not: 128 from one and 256 from the other, for
  the same operator of the same model.

  It surfaced the moment amendment A16 made the slot load-bearing: an engine
  that checked `aux_id_0` against the axis it rotates admitted the ROM
  deployment and refused the HBM one. The engine now reads the slot only under
  the partial-rotation contracts, which is correct — the whole-axis contract's
  result does not depend on it — but that leaves a frozen field carrying two
  different meanings depending on which backend emitted it, which is the same
  hazard as OI-32 in a smaller field. One fallback should be deleted, not
  reconciled: the graph states `rotary_width` or the operator does not rotate
  partially.

- **OI-37 — the partial quantiser's operand view is narrowed in one backend
  only.** DeepSeek quantises the 448 non-rotary channels of a 512-wide KV
  vector, and amendment A16 section 16.2 puts the narrowing in the view: same
  row stride, fewer elements of it. `compiler/backends/rom/common/program.py`
  does that; `compiler/backends/hbm_sram/lower.py` does not, so the shared-chip
  DeepSeek lowering still presents the full row to a code output that is 448
  wide and the vector engine refuses it. The ROM wafer lane reached this rung
  first because it is further along; the HBM lane will reach the identical one.

- **OI-38 — amendment A16 invalidated the retained RTL evidence binding, exactly
  as that binding is designed to.** `tools/rtl_abi3_campaign.py` hashes
  `docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md` into the campaign artifact
  "so that a change to the ABI invalidates this evidence instead of silently
  outdating it". Adding A16's row to the section 14 amendment index changed that
  document, so `tests/compiler/test_rtl_abi3.py::test_retained_campaign_artifact_is_bound_to_these_sources`
  now fails on `docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md changed since the
  campaign was recorded`. The mechanism worked; the evidence needs re-recording.

  The campaign was re-run to confirm the RTL itself is unaffected: **iverilog
  PASS, verilator PASS**, and the only differences from the retained artifact
  are that one document digest and the text of Verilator's compile log (a
  `PINCONNECTEMPTY` warning whose rendering is not byte-stable between runs).
  Every case, every check count and every correlation figure is identical.
  Re-recording is `python3 tools/rtl_abi3_campaign.py --force`, and it is left
  to the RTL lane rather than done here: `results/rtl/abi3_campaign.json` is
  that lane's evidence, and an evidence file with two writers is OI-26.

  **Closed.** The RTL lane re-recorded it. Three of the thirty bound sources had
  moved, not one: the A16 index row in the wire format, and `runtime/sim/device.py`
  and `runtime/sim/memory.py` from the node-dimension commit. None of A13–A16
  needed an RTL change — A13 was already implemented in `ot_a3_view_resolver.sv`
  including the `stride0 * bound_divisor` leading-axis test, and A14, A15 and A16
  all land in fields the ABI 3.0 microsequencer never reads. The re-recording
  therefore added vectors that *say* so rather than asserting it: the set now
  issues LINK (it never had), carries a `participant_scope` of 2 and 1 at
  COMMUNICATION payload offset 80 against an otherwise identical NODE-scoped
  program, carries a `scale_block_rows` of 2 at TENSOR_VIEW payload offset 104 on
  a view A13 also clamps, and populates the three operand-multiplexer arms — a
  third input, a second output, a nonzero `aux_id_0` — that A16's conventions are
  the first to need and that nothing had ever selected. The marker moved from
  `cases=43 headers=43 programs=36 issues=143 views=368 traps=11` to
  `cases=50 headers=50 programs=41 issues=154 views=391 traps=11`, checks from
  3,017 to 3,282, both simulators identical.

  The same pass re-recorded the other stale retained RTL artifact,
  `testdata/compiler/tensor_accelerator/qwen3_rtl_rope_vectors.json`, which bound
  `runtime/tensor_accelerator/rope.py` and went stale on OI-34's
  `MAX_POSITIONS` 8000 → 8192. Exactly two fields moved — the oracle digest and
  the derived `vector_set_id`, now
  `3a792b0dec8dd7277540841409accca66521f2f05f977c1cd6b6d9e5361f4f76` — and every
  coefficient and output code is byte-identical, because `MAX_POSITIONS` is an
  input to `coefficient_table_bf16` and not to `rope_bf16`. That the digest could
  move without anything checking whether the deployed table still followed is now
  fixed at the source: the builder reproduces the shard's 8,000 rows from
  `coefficient_table_bf16(8000)` and compares them byte-for-byte, so the bound
  and the four near-midpoint corrections are load-bearing here rather than
  merely hashed. Re-derived at 200 decimal digits over the whole extended domain,
  **8,000..8,191 introduces no fifth correction**; and 8,191 is not a position
  these vectors can hold, because the deployed coefficient table is 8,000 rows
  and 7,999 remains its edge.

- **OI-41 — CLOSED. `ATTENTION.SPARSE` was made data-bearing at `97c5fb6`, and
  this entry asserted otherwise for fourteen hours afterwards.**
  `runtime/sim/engines/attention.py:150` imports
  `runtime.tensor_accelerator.sparse_attention.sparse_attention_bf16_codes` and
  calls it; the scalar reference is kept only for the paths the kernel refuses.
  Measured head-to-head against the reference on the same operands, outputs
  compared as raw uint16: **682x** at 64 selected rows and **802x** at 128,
  bit-identical in both. The 12.5 ms per (head, row) this entry quoted
  reproduces exactly on the reference, so the defect was real when written.

  At the production shape on the ROM lane -- span 104 x 64 heads x 512, ~5,900
  gathered rows per site -- attention costs **0.29-0.33 s per site**, about
  **13.2 s** across 43 sites. It is **0.2% of the prefill** and does not appear
  in the profile. The oracle at that shape would be 1.36 h per site and 58.4 h
  for one prefill, so this entry's conclusion -- that no token was reachable
  through it -- was correct and had already been acted on.

  **The failure was mine and it belongs on the record rather than being quietly
  closed.** I renumbered this entry at `84f1194` to resolve a collision I had
  created, and renumbered it without reading whether it was still true. An entry
  in the register of record asserting a defect fixed half a day earlier is the
  same class as a document quoting a retracted figure, and the same class as
  W6.4 citing a record whose failure text contradicted it. Editing an entry is
  not verifying it, and touching one without checking it is how a register
  becomes fiction.

  What the work found in its place is where the time actually goes:
  `TENSOR.ROUTED_MATMUL` is **80.5%** of the prefill, 38% of it MXFP4 operand
  widening. That is [OI-42].

- **OI-42 — `TENSOR.ROUTED_MATMUL` is 80.5% of a DeepSeek prefill, and 38% of
  that is widening operands it will use once.** With `top_k` 6 over 256 experts,
  104 tokens make 624 assignments over about 552 (slot, expert) pairs, so a
  contraction averages **~1.1 rows** — and each one widens a full
  `[2048, 4096]` MXFP4 weight. That is 4.6e9 nibble decodes against 5.2e9 MACs
  per site: the widening is comparable to the arithmetic it feeds.

  **The sequential contract is not the wall, which was checked rather than
  assumed.** At the routed shape `np.matmul` under the blocked association is
  only 1.0–4.7x faster, against 5.3x at the dense shape, because the work is
  bandwidth-bound on the weight. Changing the MoE association would buy single
  digits, not orders of magnitude, so no contract needs weakening. Threading was
  tried and rejected: bit-exact at 4, 8 and 16 workers and 0.02–1.8x.

  The fix is expert-outer iteration in `runtime/sim/engines/tensor.py` — one
  partial per slot, widening each expert once — and it is bit-exact, since the
  ascending-slot combination is untouched. Worth about 20% of the prefill. It
  moves `rom.bytes_read` and the scale-multiplication accounting, both
  load-bearing figures, so it belongs to that engine's owner and wants
  re-recording with it.

- **OI-43 — two simulators disagreed about the same source text, and only the
  two-simulator rule made it visible.** Under Icarus 11, a wildcard-imported
  package identifier that appears *only* inside a module-instance
  port-connection expression is not resolved against the import: Icarus creates
  an implicit one-bit net of that name, and that net then shadows the constant
  **for the whole module**. In `rtl/abi3/ot_a3_engine_array.sv`, `DMA_SCATTER`
  read as `z`, every `DMA.SCATTER` dispatched as unimplemented, and
  `DMA_GATHER` — which never appears in a port connection — kept working. Three
  of twenty-nine cases failed and twenty-six passed; **Verilator resolved the
  constant correctly**, so the disagreement was between the simulators, not
  between the RTL and the model.

  The signature is the program's usual one: legal values, no trap, nothing
  refused. A single-simulator campaign would have recorded either a pass or a
  narrow failure and neither would have named the cause.

  **Closed.** Every file in the engine RTL now refers to package members as
  `pkg::name` and carries no `import`, pinned by
  `tests/compiler/test_rtl_abi3_engine.py::test_engine_rtl_carries_no_wildcard_package_import`.
  The same change is what makes those blocks synthesisable at all: the pinned
  Yosys 0.68 Verilog frontend rejects `import` in a module header and in a
  module body alike, so **every existing `rtl/abi3/` block that still carries a
  wildcard import — `ot_a3_microsequencer.sv`, `ot_a3_view_resolver.sv`,
  `ot_a3_state_controller.sv`, `ot_a3_event_scoreboard.sv`,
  `ot_a3_loop_stack.sv`, `ot_a3_program_header.sv`,
  `ot_a3_instruction_decoder.sv`, `ot_a3_collective_engine.sv` — cannot be
  synthesised or routed by this toolchain today.** That is why W9 has physical
  numbers for the ABI 2.5 blocks and none for the ABI 3.0 control plane, and it
  is a two-line change per file rather than a design problem.

- **OI-44 — the shared binary32 *adder* is the critical path, and it is a
  coding shape rather than a technology limit.** Measured on SKY130 HD
  `tt_025C_1v80`, each operation synthesised alone as one combinational cloud
  between registers with the pinned Yosys 0.68 + ABC mapping and OpenSTA:
  `ot_fp32_rne_pkg::fp32_add_rne` needs a clock period of **66.97** ns <!-- figure: 66.97 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#static_timing.fmax_search.min_clock_period_ns" name="fp32 add min period, OI-44" -->
  in a cell area of **13,868.7** µm² <!-- figure: 13,868.7 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#synthesis.cell_area_um2" name="fp32 add cell area, OI-44" -->,
  while `fp32_mul_rne` needs **29.385** ns <!-- figure: 29.385 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#static_timing.fmax_search.min_clock_period_ns" name="fp32 mul min period, OI-44" -->
  in **33,660.4** µm² <!-- figure: 33,660.4 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#synthesis.cell_area_um2" name="fp32 mul cell area, OI-44" -->
  — the adder is 2.28x slower and 41% of the area. `fp32_to_bf16_rne` needs
  **3.84 ns** <!-- figure: 3.84 src="results/physical_abi3/sky130hd/a3_numeric_probes/bf16_round.json#static_timing.fmax_search.min_clock_period_ns" name="bf16 round min period, OI-44" -->
  and the whole storage-format decoder **2.62 ns** <!-- figure: 2.62 src="results/physical_abi3/sky130hd/a3_numeric_probes/format_decode.json#static_timing.fmax_search.min_clock_period_ns" name="decode min period, OI-44" -->.
  That adder is what sets `ot_a3_mac_lane`'s minimum period. Artifacts:
  `results/physical_abi3/sky130hd/a3_numeric_probes/*.json`, from
  `rtl/test/ot_a3_numeric_probes.sv` through
  `tools/run_abi3_physical.py --view sky130hd --stages synth,sta --fmax-search`.

  The cause is a 27-iteration cancellation-normalisation loop whose iterations
  are *dependent*, so it synthesises to twenty-seven conditional one-bit shifts
  and twenty-seven exponent decrements in series; `shift_right_jam_28`'s
  28-iteration sticky reduction has the same shape. A leading-zero count
  followed by one barrel shift is functionally identical and far shorter.

  **Not changed here, deliberately.** `rtl/ot_fp32_rne_pkg.sv` is shared with
  the ABI 2.5 production blocks and physical campaigns over those blocks were
  in flight while this was measured; editing a shared numeric package under
  another campaign's feet is how a correlated artifact quietly stops matching
  its sources. It belongs to that file's owner, and any rewrite must re-run
  `tools/rtl_abi3_engine_campaign.py`, which compares 10,000 result words
  bit for bit and is exactly the check that would catch a rewrite that moved
  one.

  **This does not retire `power.fabric_clock_hz = 1e9`.** SKY130 is a 130 nm
  open foundry PDK and `docs/OPEN_PDK_SELECTION.md` forbids feature-size
  scaling from it, so no frequency here transfers to N6, N5 or N4. That
  constant stays `assumed`. What does transfer is the structural statement:
  the lane's period is set by one unpipelined binary32 addition written as a
  serial shift chain, and that is true at any node.
