# Four-target implementation progress report

**Report ID:** `TA-PROGRESS-4T-2026-09-03`

**Status date:** 2026-09-03

**Input baseline:** `main == origin/main` at `a7441df` before this report
refresh; this includes the Qwen W10 provenance repair, the strict DeepSeek
exact-200K external-oracle gate, and the first shipped-program RTL engine prefix

**Role:** current narrative status and handoff report. Machine-readable result
artifacts and the [unified execution checklist](UNIFIED_EXECUTION_CHECKLIST.md)
remain authoritative when a copied count or status differs.

## 1. Executive status

The common compiler and functional-simulator stack is real and shared by both
models and both storage backends. Both complete model graphs lower through the
same Model Graph IR, Tensor Kernel IR, and ABI 3.0 records. Current deployment
certificates admit all four intended topologies, and every current deployment
contains zero ABI `STATE` descriptors and zero `STATE` instructions.

The project is not yet at final acceptance. The strongest current end-to-end
model-token records are short or historical runs of the functional simulator.
There is not yet a source-current Qwen exact-8,000 natural-context acceptance
package, a source-current DeepSeek exact-200,000 accelerator execution, a fully
integrated RTL datapath capable of producing those tokens, or a complete
same-view SKY130/ASAP7 physical comparison of all four systems.

The present boundary is therefore:

- compiler and deployment architecture: implemented and independently checked;
- full-model functional simulator: implemented, with prior short token evidence;
- production acceptance validators: implemented for Qwen and for the DeepSeek
  exact-200K external oracle; both still reject the incomplete current evidence;
- RTL control plane and bounded arithmetic blocks: independently correlated;
- sequencer-to-arithmetic integration: the first exact shipped-program
  `DMA.GATHER` prefix is closed; complete operator RTL remains open;
- exact mandatory long executions: open; and
- final process-specific performance comparison: open.

The generated checklist snapshot is **83 of 94 top-level milestones done, 10
partial, and 1 not started**. This is milestone arithmetic, not an estimate that
88 percent of engineering effort is complete: the remaining exact-8K/exact-200K
runs, integrated full-operator RTL, and two complete physical views dominate
the remaining cost.

### 1.1 Gate summary

| Gate | Status | Evidence now | What still prevents closure |
|---|---|---|---|
| Architecture and ABI 3.0 | closed | frozen live-buffer/fence profile; zero `STATE` in all four deployments | no ABI 3.1 work is required |
| Common IR and four backend builds | closed for current graphs | Qwen and DeepSeek lower through the shared Model Graph and Tensor Kernel IR into HBM and ROM bundles | rebuild whenever an execution-authoritative source changes |
| Functional short execution | partial | complete functional engine exists; retained short token prefixes and historical workload evidence | current DeepSeek arithmetic repair and Qwen source profile make the retained captures non-promotable |
| RTL 3.0 | partial | shipped control replay and 11 bounded arithmetic pairs independently correlate; a source-bound prefix campaign now drives six real gathers from all four decode images through the engine array on Icarus and Verilator | the witness stops precisely at the first unsupported embed lookup; the full operator set and whole-token path are incomplete |
| Mandatory workloads | open | exact prompt artifacts and tokenizer/oracle machinery exist | fresh Qwen exact-8K pairs and both DeepSeek exact-200K executions are absent; the DeepSeek oracle stops after eight tokens |
| SKY130 and ASAP7 | partial | several bounded blocks have process-specific reports | neither view characterizes a complete target; ASAP7 readiness has 15 fail-closed blockers |
| Governed comparison | partial | short historical ROM/HBM comparisons retain topology and counter evidence | no source-current mandatory-workload pair or complete same-view system cost exists |

### 1.2 Source-current execution readiness

At this checkpoint one Qwen natural capture is active, but no long accelerator
campaign is being promoted as complete. Long jobs are serialized until their
source and output identities are committed and one measured run establishes
memory and I/O headroom.

- Qwen natural capture A launched from committed and pushed source
  `b27dc801e171` after an empty source-diff preflight. Its serialized deployment
  independently passed 54/54 W10 admission checks, exactly matched the standard
  HBM bundle, and contained zero `STATE` descriptors, instructions, storage
  objects, permissions, or verifier resources. At report time it was still in
  the exact-8,000 prefill and had produced no output token; this is execution in
  progress, not acceptance evidence.

- Qwen HBM deployment `a6d98d47ff80…` passes its 21/21 certificate and the
  independent 43/43 admission checks. It spans 18.53 GB of admitted HBM and has
  exact prefill/decode entrypoints, 215 descriptors, 74 instructions, and zero
  `STATE` records. A source-map audit found that `runtime/sim/weight_cache.py`
  participates in execution but was not mandatory in the W10 checker. It is now
  part of the required source map, and the active capture A binds that committed
  checker identity.
- Qwen ROM deployment `f8505cb6f702…` passes 61/61 schedule checks with 236
  descriptors, 74 instructions, and zero `STATE` records. Both current ROM
  bundles still require unused legacy transactional-state/integrity-retry
  feature bits even though neither emits a `STATE` record and model-operation
  retry is forbidden. This does not add ABI 3.1 machinery, but it is unnecessary
  profile surface. The next ROM rebuild must remove those required bits while
  retaining packet-local integrity only where a real link exists.
- DeepSeek prompt/source/checkpoint preflight confirms the pinned exact-200,000
  prompt identity and checkpoint topology/size boundary. The new source-current
  runner provenance boundary and strict EOS-or-256 checker are implemented. Its
  canonical preflight correctly rejects the retained oracle: it has only eight
  tokens, an invalid EOS-or-256 terminal condition, insufficient prompt-plus-cap
  KV allocation, no current producer/input identity, no explicit tiled-prefill
  enablement record, and no full checkpoint-byte verification. It additionally
  locks the qualified tiling/adaptation, head-split, FP8 fallback, package,
  CUDA/`sm_120`, TF32-off, and Hadamard execution stack. No 200K accelerator job
  should start before a replacement oracle passes.
- The first RTL integration milestone is now retained and source-bound. All four
  shipped decode images enter the real sequencer; six dense FP32
  `DMA.GATHER` launches run through `ot_a3_engine_array`; and 1,024 generated
  RoPE words match under independently written Icarus and Verilator checkers,
  each with 3,289 checks. Completion is held until the engine responds. The
  first unsupported `TENSOR.EMBED_LOOKUP` traps with `CAPABILITY` at Qwen PC 4
  and DeepSeek PC 7, without retirement, signal publication, compatibility-state
  activity, or a post-fault write. This is an exact decode-prefix witness, not a
  prefill, whole transaction, token, EOS, timing, area, or power result.

## 2. Frozen ABI 3.0 execution profile

ABI 3.0 is sufficient and is the only required ABI. The four products use the
simplest execution model consistent with an end-to-end accelerator simulation:

1. Immutable weights reside in ROM or HBM.
2. KV cache, compressed KV, compressor history, activations, intermediates, and
   token buffers are ordinary live HBM/SRAM memory objects.
3. ABI 3.0 operations address those objects through tensor views and write them
   directly.
4. Existing events order producers and consumers; the terminal token-step fence
   is the visibility boundary.
5. Execution is uninterrupted and fail-stop. A failed run is rejected and its
   buffers are discarded as a run; a model operation is not rolled back or
   retried.
6. CRC and bounded replay apply only to link packets, not to a layer or token.

There are no production “state members.” That phrase belonged to the withdrawn
ABI 3.1 proposal. Durable roots, journals, atomic durable publication,
checkpoint/restart, anti-rollback storage, and model-step retry are not part of
the four-target acceptance claim. The older ABI 3.0 compatibility state
controller may remain in source for legacy tests, but the shipped comparison
profile elaborates without it and refuses a nonzero state-resource count before
instruction fetch.

## 3. Status by target

| Target | Required topology | Compiler and deployment | Current execution evidence | Main acceptance gap |
|---|---|---|---|---|
| Qwen3-8B HBM/SRAM | one shared accelerator chip | HBM certificate passes 21/21 checks: 74 instructions, 215 descriptors, one node, no communication, zero `STATE` resources | Historical functional runs include natural, reasoning, agentic, and 8,000-token-context work; changed sources make them prior-build evidence | Two fresh exact-8,000 natural captures must pass complete token, EOS/cap, tokenizer, deployment-readback, source, and association checks |
| Qwen3-8B ROM | one Qwen-specific ROM chip | ROM schedule certificate passes 61/61 checks: 74 instructions, 236 descriptors, 26 schedules, zero `STATE` resources | Historical ROM chat and long-context prefixes matched their oracle at their recorded horizons | Fresh required natural/stress and reasoning/agentic coverage must be regenerated at the final source identity; physical target locks remain absent |
| DeepSeek-V4 Flash HBM/SRAM | exactly 32 identical copies of the Qwen-class chip with NVLink-class inter-chip communication | HBM certificate passes 36/36 checks: 1,267 instructions, 3,272 descriptors, 37 communication records, zero `STATE` resources | A prior 32-token-prompt run produced four oracle-identical tokens; the learned-index rounding repair makes old DeepSeek token records prior-build evidence | Execute the exact 200,000-token prompt through first official EOS or 256 tokens on the 32-node simulator, against a complete external oracle |
| DeepSeek-V4 Flash ROM | one wafer-scale ROM accelerator with on-wafer communication and distributed HBM | ROM schedule certificate passes 123/123 checks: 1,312 instructions, 3,841 descriptors, 439 schedules, 18 communication records, zero `STATE` resources | A prior short ROM run matched the same four-token DeepSeek prefix | Execute the same exact-200,000 workload and complete oracle on the wafer target, then compare it with the 32-node HBM result |

The certificate paths are
[`hbm_qwen_deployment_certificate.json`](../results/abi3/hbm_qwen_deployment_certificate.json),
[`hbm_deepseek_deployment_certificate.json`](../results/abi3/hbm_deepseek_deployment_certificate.json),
and [`rom_schedule_checks.json`](../results/abi3/rom_schedule_checks.json).
They prove deterministic compilation, admission, placement/scheduling, and
topology properties. They do not prove long-run token correctness, RTL
arithmetic, cycle performance, or physical closure.

## 4. Common software stack

### 4.1 Implemented

- Both models export to the same backend-neutral Model Graph IR and Tensor
  Kernel IR. The IR carries model semantics and numerical contracts without
  embedding ROM/HBM addresses or a target-specific instruction stream. The
  current Qwen artifact contains 728 kernels, 1,165 tensors, and
  16,381,470,720 bound weight bytes; DeepSeek contains 3,956 kernels, 7,047
  tensors, and 156,015,698,140 bound weight bytes.
- The HBM/SRAM, Qwen ROM, and DeepSeek ROM backends lower that IR to serialized
  ABI 3.0 programs, descriptors, capabilities, and deployment bundles.
- The functional device executes the serialized program through the same
  microsequencer semantics used for RTL correlation. Engines cover tensor,
  vector, attention, routing, reduction, DMA, communication, on-device argmax,
  token append, and EOS handling. The functional registry implements 46 of 47
  dispatched operations; only optional `SELECTION.SAMPLE` is absent, and the
  frozen four-target release uses deterministic `ARGMAX` instead.
- The 32-node HBM topology preserves node-local memories and explicit LINK
  operations; it is not flattened into one host array. The wafer target uses a
  distinct on-wafer topology while retaining the same ABI and numerical
  contracts.
- The token runner records serialized deployment identity, source hashes,
  per-step execution records, architectural counters, per-node counters, executed
  numerical associations, generated IDs, and stop reason.

### 4.2 Recent correctness and performance work

- Qwen acceptance now independently reopens and authenticates the serialized
  deployment, admits exact prefill/decode entrypoints, requires ordinary
  read/write HBM live buffers, and rejects every form of ABI `STATE` resource.
  It decodes and round-trips the exact prompt and output with the pinned
  tokenizer, checks official EOS/cap placement and legal token IDs, and emits
  the human-readable input and output text.
- DeepSeek `INDEX_SCORE` now performs one correctly rounded product-add instead
  of a split multiply/add rounding. The engine also publishes previously lost
  saturation counts for `INDEX_SCORE` and `HYPER_CONNECT_POST`. Because learned
  index scores can alter sparse-KV selection, earlier DeepSeek accelerator token
  artifacts must not be promoted as source-current results.
- The simulator now records host-only route, materialization, cache, association,
  RSS, and page-fault observations separately from architectural counters. An
  opt-in, centrally bounded cache can reuse authenticated immutable decoded
  expert weights; its default budget is zero. Focused differential tests prove
  cache-off/cache-on output, traps, counters, and association manifests remain
  identical. This is a simulator acceleration mechanism, not an ABI feature or
  a hardware-performance claim.

## 5. RTL status

Three complementary RTL evidence boundaries must remain separate: control
replay, standalone datapaths, and their first bounded integration prefix.

### 5.1 Shipped-deployment control plane

The ABI 3.0 microsequencer campaign loads both prefill and decode entrypoints
from each of the four real deployment images. Icarus and Verilator compare
instruction retirement, predicates, engine issue records, resolved operand
views, traps, and completion against the functional `Device`. The production
elaboration sets `STATE_COMPAT=0`, proves the compatibility state controller is
absent, and rejects a nonzero state count before fetch.

This establishes control-flow and addressing for the shipped images. Its engine
port is deliberately a recording boundary; it does not establish arithmetic or
token generation.

### 5.2 Standalone engine datapaths

The engine campaign correlates 11 bounded `(family, subopcode)` pairs over 135
ABI 3.0 programs on both simulators. It includes tensor matmul, gather/scatter,
argmax, residual add, and bounded convert, scale, Hadamard, learned-index,
compressor-project, and hyper-connection-post forms. Exact reference probes and
mutated-RTL runs guard arithmetic and descriptor admission.

This establishes the published bounded datapaths. Correctly rounded RTL for the
remaining operator surface—including softmax and other transcendental forms—is
still incomplete. The shipped programs reach 37 distinct opcode pairs: 11 have
bounded correlated datapaths and 26 still have no correlated datapath RTL at
this boundary.

### 5.3 First shipped-program engine prefix

The separate shipped-prefix campaign closes one narrow connection between the
two evidence classes above. It validates the real operator, tensor-view, dtype,
permission, geometry, and `exact_index_select_v1` descriptors before allowing
the sequencer's initial generated-RoPE gathers to launch the existing DMA
datapath. Engine faults are precise: a failed operation neither retires nor
publishes its completion event.

The campaign intentionally refuses the next operation rather than simulating it
as a no-op. It therefore establishes the sequencer/view/engine handshake and
real data movement only for that prefix. No current RTL simulation executes a
whole model or produces an accepted output token.

## 6. What “full execution” means

The project uses three different claims, and they are not interchangeable:

- **Full causal functional execution:** the serialized ABI 3.0 deployment runs
  every required model operation from the real checkpoint and prompt, performs
  on-device selection, and produces the complete EOS-or-cap token sequence. A
  framework may supply the external oracle, but it may not supply simulator
  activations, logits, routes, or selected tokens.
- **RTL control replay:** the RTL sequencer follows the same program, predicates,
  views, and issue stream, while arithmetic is recorded or checked elsewhere.
  This is valuable correlation, but it is not full RTL model execution.
- **Full RTL execution:** the sequencer, memories, communication, all required
  datapaths, and selection are integrated so the RTL simulation itself produces
  the complete accepted token sequence. This remains the final implementation
  goal and is not yet achieved.

“Artifact-driven” or “artifact-only” is full execution only when it means the
first definition: the serialized artifact drives every causal computation. A
structural artifact replay, trace-only replay, oracle-token injection, or
compiled-operator census is not full execution.

## 7. Workload and comparison gates

### 7.1 Qwen

The governed natural workload has exactly 8,000 prompt tokens and terminates at
the first official EOS or the frozen 256-token cap. Acceptance requires legal
IDs, complete external-oracle identity, exact token equality, decoded text,
tokenizer round trips, no post-EOS model step, and two independent HBM
captures. The required chat/reasoning and simple agentic workload matrix must
also be source-current on the target to which each claim is assigned.

The checker is ready; the fresh long captures are not. Existing local W10
captures are diagnostic because they bind the superseded pre-live-buffer/runtime
source identity. The older stress capture also diverges and there is no accepted
ROM stress partner.

### 7.2 DeepSeek

The governed natural workload has exactly 200,000 prompt tokens. Both the ROM
wafer and 32-node HBM cluster must continue to first official EOS or exactly 256
generated tokens. The retained external context-ladder artifact reaches the
prompt length but contains only an eight-token oracle prefix; no accelerator
artifact currently executes that full prompt. Neither can close acceptance.

The immediate DeepSeek blockers are a complete EOS-or-256 external oracle that
passes the new strict provenance gate, source-current deployments bound to the
final runtime, and two genuine
long-context accelerator executions. Performance instrumentation and decoded
weight caching make those runs more tractable but do not reduce the workload or
the required arithmetic.

### 7.3 Tokens, stopping, and speed actually established

The current evidence supports only the following carefully scoped statements:

- The retained DeepSeek external reference did process the exact 200,000-token
  natural prompt. It generated token IDs `[14, 412, 855, 260, 836, 881, 3495,
  204]`, decoded as `", as if a man were able\r"`, and stopped because its
  configured eight-token limit was reached—not because EOS occurred. It took
  435.266 s including a 405.05 s tiled prefill. This is GPU external-oracle
  speed, not ROM-wafer or 32-chip simulator speed.
- The retained DeepSeek accelerator HBM and ROM artifacts each produced only
  `[13806, 345, 7472, 55560]` on a short prompt and matched the old four-token
  oracle prefix. Those legal IDs predate the `INDEX_SCORE` single-rounding fix,
  so they are regression clues rather than current decoding acceptance.
- The retained Qwen HBM exact-8K attempt generated 193 tokens in 14,982 s, or
  about 77.6 wall seconds per generated token when its prefill cost is averaged
  over that partial output. It diverged from the oracle at generated index 137
  and then encountered the historical capacity boundary. The number describes
  an obsolete functional-simulator build; it is not a production throughput
  result.

No source-current mandatory accelerator run has yet produced a defensible
tokens-per-second figure. Functional host time, cycle-model time, RTL simulator
throughput, projected target cycles, and post-layout frequency will remain
separate fields; none will be converted into another by implication.

The 2026-09-03 launch preflight observed 202.4 GB host RAM with 165.1 GB
available, 99.4 GB free filesystem space, and an RTX PRO 6000 with 97,887 MiB
total but only 12,353 MiB free. Swap was effectively full. The DeepSeek
checkpoint manifest closes over 74 files totaling 166,898,661,074 bytes,
including 48 checkpoint shards. These observations make
serial high-memory campaigns mandatory on this host and are resource-safety
facts only, not accelerator capacity or performance evidence.

## 8. SKY130 and ASAP7 status

SKY130 is the mature open 130-nm implementation view; ASAP7 is the predictive
academic 7-nm view. Existing artifacts cover selected arithmetic, movement,
selection, reduction, link, and memory-service blocks. They are useful block
proxies, not complete four-target systems.

The final comparison still lacks complete, same-view characterization of the
control plane, every required engine family, SRAM/ROM macros, HBM/PHY boundary,
32-node cluster fabric, wafer fabric, system clock, area, energy, and uncertainty
model. The current ASAP7 readiness artifact is therefore correctly not ready.
No SKY130 result may be scaled into an ASAP7 or commercial-node claim, and ASAP7
is not foundry signoff.

## 9. Critical path from here

1. Keep ABI 3.0 frozen and retain the zero-`STATE`, live-buffer admission gates.
2. Remove the two unused legacy feature requirements from both ROM production
   bundles; keep integrity/replay only on a link-bearing endpoint and never as a
   model-operation retry contract.
3. Regenerate all source-bound RTL and deployment artifacts after the numerical
   repair and performance tranche; reject any stale result.
4. Extend the now-proven ABI issue/view/engine bridge beyond its exact gather
   prefix, adding the missing model-required datapaths and memory services
   without changing the ABI or numerical contracts.
5. Run short integrated token diagnostics on all four targets and require exact
   identity before spending resources on long campaigns.
6. Produce the complete DeepSeek external EOS-or-256 oracle.
7. Run fresh Qwen exact-8,000 natural and required agentic/reasoning acceptance,
   stopping at official EOS or cap and publishing the decoded text.
8. Run DeepSeek exact-200,000 on the wafer ROM and exactly 32 HBM/SRAM chips,
   publishing complete tokens, text, counters, topology, and source identities.
9. Complete separate SKY130 and ASAP7 characterization and feed measured limits
   back into the cycle model before publishing ROM-versus-HBM performance.

The long simulations should start only after steps 1–4 have one committed source
identity. Otherwise every multi-hour result becomes stale when the integration
or numerical source changes.

## 10. Bottom line

The architecture is no longer waiting for ABI design. ABI 3.0, the neutral IR,
all four compilation paths, and the functional simulator provide the correct
foundation. The remaining work is implementation closure and evidence: integrate
the RTL datapaths, execute the mandatory long workloads on the actual simulated
targets, verify their complete decoded outputs, and characterize the complete
systems on both required process views.
