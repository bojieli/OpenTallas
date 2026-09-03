# Four-target implementation progress report

**Report ID:** `TA-PROGRESS-4T-2026-09-03`

**Status date:** 2026-09-03

**Input baseline:** `main` through `35884c9` before this report refresh; this
includes the fail-closed DeepSeek exact-200K oracle and accelerator-pair
checkers, operation-derived ABI feature requirements, refreshed zero-`STATE`
deployments, and the shipped-program RTL prefix through Qwen RMSNorm and
DeepSeek transfer

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
- production acceptance validators: implemented for Qwen, the DeepSeek
  exact-200K external oracle, and the final DeepSeek ROM/HBM accelerator pair;
  all still reject the incomplete current evidence;
- RTL control plane and bounded arithmetic blocks: independently correlated;
- sequencer-to-arithmetic integration: the exact shipped-program prefix through
  `DMA.GATHER`, `TENSOR.EMBED_LOOKUP`, and then Qwen `VECTOR.RMS_NORM` or
  DeepSeek `DMA.TRANSFER` is closed; complete operator RTL remains open;
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
| RTL 3.0 | partial | shipped control replay and 11 bounded arithmetic pairs independently correlate; a source-bound prefix campaign now drives 6 gathers, 4 embedding lookups, 2 Qwen RMSNorms, and 2 DeepSeek transfers from all four decode images on Icarus and Verilator | the witness next stops at Qwen MATMUL, DeepSeek ROM LINK.MULTICAST, or DeepSeek HBM VECTOR.MHC; the full operator set and whole-token path are incomplete |
| Mandatory workloads | open | exact prompt artifacts and tokenizer/oracle machinery exist | fresh Qwen exact-8K pairs and both DeepSeek exact-200K executions are absent; the DeepSeek oracle stops after eight tokens |
| SKY130 and ASAP7 | partial | several bounded blocks have process-specific reports | neither view characterizes a complete target; ASAP7 readiness has 15 fail-closed blockers |
| Governed comparison | partial | short historical ROM/HBM comparisons retain topology and counter evidence | no source-current mandatory-workload pair or complete same-view system cost exists |

### 1.2 Source-current execution readiness

At this checkpoint no long accelerator capture is active or accepted. Long jobs
are serialized until their source and output identities are committed and one
measured run establishes memory and I/O headroom.

- Qwen natural capture A launched from committed source `b27dc801e171` after an
  empty source-diff preflight. It was last observed healthy after at least
  2:28:07 at about 120% host CPU and 13.4 GB RSS, with zero major faults, while
  still in exact-8,000 prefill. The attached process later disappeared: stdout
  ends at the execution-start line, the timing file is empty, and no result JSON
  exists. No accessible kernel or journal record identifies an OOM or signal.
  This incomplete attempt establishes no token, verdict, exact wall time, peak
  RSS, resource headroom, or TPOT. A fresh capture A must use the final frozen
  identity and a durable detached service; capture B remains gated on A passing.

- Qwen HBM deployment `a6d98d47ff80…` passes its 21/21 certificate and the
  independent 43/43 admission checks. It spans 18.53 GB of admitted HBM and has
  exact prefill/decode entrypoints, 215 descriptors, 74 instructions, and zero
  `STATE` records. A source-map audit found that `runtime/sim/weight_cache.py`
  participates in execution but was not mandatory in the W10 checker. It is now
  part of the required source map. The terminated attempt bound that committed
  checker identity, but subsequent mandatory builder changes make a fresh
  final-identity capture necessary regardless of how it terminated.
- Qwen ROM deployment `d8a6f8edaaac…` passes 61/61 schedule checks with 236
  descriptors, 74 instructions, and zero `STATE` records. Operation-derived
  feature cleanup is integrated: every production program omits
  `TRANSACTIONAL_STATE`, Qwen also omits `INTEGRITY_RETRY`, and only actual
  DeepSeek link descriptors request packet-local integrity/replay. Capability
  compatibility bits remain unchanged.
- DeepSeek prompt/source/checkpoint preflight confirms the pinned exact-200,000
  prompt identity and checkpoint topology/size boundary. Commit `9303615` adds
  one fail-closed `--gate-b-production` launch profile. It admits only
  `TA-DS-CTX-200K-1`, fixes the generation horizon at first official EOS or
  exactly 256 tokens, allocates 200,320 aligned KV positions, forces the
  qualified tiled-prefill geometry, rejects alternate or stale inputs before
  model construction, verifies the full 166.9 GB checkpoint before importing
  the model stack, validates the locked packages/device/numeric adaptations,
  and rehashes producer and input identities at completion. Focused tests pass,
  so the launcher is ready at tooling scope. The expensive full-byte hash and
  real production oracle execution have not run. The canonical retained
  preflight still correctly reports 41 problems and rejects the eight-token
  record; no 200K accelerator job should start before a replacement oracle
  passes.
- `check_deepseek_v4_200k_accelerator_acceptance.py` now provides the final
  fail-closed accelerator-pair gate, covered by 26 focused tests. After an
  accepted Gate-B oracle, it independently authenticates one exact ROM-wafer
  record and one exact 32-node-HBM record, requires the exact 200,000-token
  prompt and first-EOS-included-or-256 termination, checks zero `STATE`, current
  identities, exact token IDs/text, per-step semantics, counters, implementation
  identity, and association equality after 32-node normalization. Its presence
  is tooling readiness only; no production exact-200K pair exists.
- Commit `f7d78d4` extends the retained, source-bound RTL milestone. All four
  shipped decode images enter the real sequencer. The campaign launches 6 FP32
  `DMA.GATHER`, 4 BF16 `TENSOR.EMBED_LOOKUP`, 2 Qwen BF16
  `VECTOR.RMS_NORM`, and 2 DeepSeek stride-zero BF16 `DMA.TRANSFER`
  operations. It compares 58,368 exact result words—1,024 RoPE, 16,384
  embedding, 8,192 RMSNorm, and 32,768 transfer—through 52 resolved views and
  authenticates 49,152 selected-range checkpoint bytes: four 8 KiB embedding
  rows and two 8 KiB RMS gain ranges. Icarus and Verilator each pass 124,189
  checks. Qwen next refuses `TENSOR.MATMUL` at PC 11 (descriptors 59/72);
  DeepSeek ROM next refuses `LINK.MULTICAST` at PC 13 (descriptor 368), and
  DeepSeek HBM next refuses `VECTOR.MHC` at PC 14 (descriptor 546). Each is a
  precise `CAPABILITY` trap without unsupported retirement, event publication,
  compatibility-state activity, or post-fault write. This remains a decode
  prefix witness, not prefill, a whole transaction or token, EOS, timing, area,
  or power evidence.

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
- The DeepSeek Gate-B command is now a single production profile rather than a
  collection of caller-selected switches. It validates the exact workload,
  snapshot, hashes, 200,320-position allocation, 256-token terminal contract,
  tiling and qualified execution stack before construction, then checks the
  same source and inputs again at completion. This makes an invalid launch fail
  early; it does not make the still-unrun external oracle complete.
- The shipped RTL bridge now executes generated-RoPE gather, exact BF16
  embedding lookup, Qwen RMSNorm, and DeepSeek stride-zero transfer. Its four
  selected 8 KiB embedding rows and two selected 8 KiB RMS gain ranges are
  individually authenticated and tied to certified deployments. This is
  deliberately smaller than full-segment or full-shard authentication and the
  embedding lookup deliberately uses synthetic token ID 0.

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
permission, geometry, and numeric descriptors before allowing the sequencer's
initial generated-RoPE gathers, embedding lookups, Qwen RMSNorms, and DeepSeek
transfers to launch the bounded datapaths. The 14 launches produce 58,368
checked words through 52 resolved views, with 124,189 checks per simulator.
Engine faults are precise: a failed operation neither retires nor publishes its
completion event.

The campaign intentionally refuses the next operation rather than simulating it
as a no-op: Qwen stops at `TENSOR.MATMUL`; DeepSeek ROM stops at
`LINK.MULTICAST`; and DeepSeek HBM stops at `VECTOR.MHC`. Its embedding index
is legal token ID 0, selected solely as a bounded deterministic probe; it is not
a tokenizer-driven model output and does not establish even one whole token
step. It therefore establishes the sequencer/view/engine handshake and real
data movement only for that prefix. No current RTL simulation executes a whole
model or produces an accepted output token.

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

The checker is ready, but HBM natural capture A terminated without a result
after at least 2:28:07 while still in prefill. It produced no output token or
timing footer, so neither capture A nor the required independent capture B is
accepted. Existing older local W10 captures are diagnostic because they bind
the superseded pre-live-buffer/runtime source identity. The older stress capture
also diverges and there is no accepted ROM stress partner.

### 7.2 DeepSeek

The governed natural workload has exactly 200,000 prompt tokens. Both the ROM
wafer and 32-node HBM cluster must continue to first official EOS or exactly 256
generated tokens. The retained external context-ladder artifact reaches the
prompt length but contains only an eight-token oracle prefix; no accelerator
artifact currently executes that full prompt. Neither can close acceptance.

The immediate DeepSeek blockers are execution of the new fail-closed production
oracle through complete EOS-or-256, including its pre-run and completion
full-byte/input checks, followed by two genuine long-context accelerator
executions. The launcher and final pair checker are implemented and focused-test
complete, but neither the full oracle run nor either accelerator run has
occurred. Performance instrumentation and decoded weight caching make those
runs more tractable but do not reduce the workload or the required arithmetic.

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

Correct tokens and TPOT are the two highest-priority acceptance gates, in that
order. A performance point is admissible only if the same execution first
passes exact oracle token equality, legal-ID and decoded-text checks,
first-EOS-included-or-exact-cap stopping, and no-post-EOS execution. Its measured
record must then retain prefill latency/TTFT, each decode-step latency (or a
lossless distribution plus raw samples), warm and steady-state TPOT, aggregate
throughput, and all workload/topology/process/capability/deployment/source
identities. Existing batch-size roofline tables generate no tokens; they remain
projections and cannot be presented as executed TPOT or correctness evidence.

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
2. Freeze the final source/deployment identity and relaunch Qwen HBM exact-8K
   natural capture A as a durable detached service with a unique result, log,
   timing, and deployment path. Require legal IDs, exact tokenizer and text
   round trips, exact external-oracle equality, correct first-EOS-or-256
   stopping, complete provenance, and a strict W10 checker pass.
3. Only after the fresh capture A establishes resource headroom and passes,
   launch the
   independent capture B. Then complete the assigned source-current Qwen ROM,
   reasoning/chat, stress, and closed-loop agentic cells.
4. Execute the DeepSeek `--gate-b-production` external oracle when the required
   GPU, checkpoint I/O, and host-memory resources are available. Require both
   the pre-run full-byte hash and the completion identity rehash; do not promote
   the retained eight-token prefix.
5. Preserve the integrated operation-derived feature invariant:
   `TRANSACTIONAL_STATE` in no production program and `INTEGRITY_RETRY` only
   for actual DeepSeek communication descriptors.
6. Extend the proven RTL prefix from Qwen `TENSOR.MATMUL`, DeepSeek ROM
   `LINK.MULTICAST`, and DeepSeek HBM `VECTOR.MHC`, then continue through every
   required operator, memory service, communication primitive, argmax, token
   append, and EOS path.
7. Run short integrated token diagnostics on all four targets; then run exact
   200K accelerator execution on one DeepSeek ROM wafer and exactly 32 shared
   HBM/SRAM chips, publishing complete tokens, text, counters, topology, and
   source identities and passing the exact-200K accelerator-pair checker.
8. Only after a run is token-correct, measure and report its TPOT. For every
   later batch point, require correct-token count, first divergence, stop
   reason, TTFT, per-step latency, steady-state TPOT, and aggregate throughput
   from the same execution; keep analytical projections separate.
9. Complete separate SKY130 and ASAP7 full-system characterization and feed
   measured limits back into the cycle model before publishing the same-view
   ROM-versus-HBM comparison.

Every new long simulation must start from one frozen, committed source,
deployment, workload, oracle, topology, and output identity. The terminated
Qwen attempt is retained only as diagnostic provenance and must not be promoted
or used to derive TPOT.

## 10. Bottom line

The architecture is no longer waiting for ABI design. ABI 3.0, the neutral IR,
all four compilation paths, and the functional simulator provide the correct
foundation. The remaining work is implementation closure and evidence: integrate
the RTL datapaths, execute the mandatory long workloads on the actual simulated
targets, verify their complete decoded outputs, and characterize the complete
systems on both required process views.
