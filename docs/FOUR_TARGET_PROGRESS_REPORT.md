# Four-target implementation progress report

**Report ID:** `TA-PROGRESS-4T-2026-09-03`

**Status date:** 2026-09-03

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
- production acceptance validators: implemented for Qwen and specified for
  DeepSeek;
- RTL control plane and bounded arithmetic blocks: independently correlated;
- sequencer-to-arithmetic integration and complete operator RTL: open;
- exact mandatory long executions: open; and
- final process-specific performance comparison: open.

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
  embedding ROM/HBM addresses or a target-specific instruction stream.
- The HBM/SRAM, Qwen ROM, and DeepSeek ROM backends lower that IR to serialized
  ABI 3.0 programs, descriptors, capabilities, and deployment bundles.
- The functional device executes the serialized program through the same
  microsequencer semantics used for RTL correlation. Engines cover tensor,
  vector, attention, routing, reduction, DMA, communication, on-device argmax,
  token append, and EOS handling.
- The 32-node HBM topology preserves node-local memories and explicit LINK
  operations; it is not flattened into one host array. The wafer target uses a
  distinct on-wafer topology while retaining the same ABI and numerical
  contracts.
- The token runner records serialized deployment identity, source hashes,
  per-step transactions, architectural counters, per-node counters, executed
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

Two different RTL evidence classes must remain separate.

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

This establishes the published bounded datapaths only. The blocks are not yet
wired to the shipped-deployment microsequencer. Correctly rounded RTL for the
remaining operator surface—including softmax and other transcendental forms—is
still incomplete, and no current RTL simulation executes a whole model to
produce the accepted output tokens.

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
tokenizer round trips, no post-EOS transaction, and two independent HBM
captures. The required chat/reasoning and simple agentic workload matrix must
also be source-current on the target to which each claim is assigned.

The checker is ready; the fresh long captures are not. Existing local W10
captures are diagnostic because they bind the superseded state-based/runtime
source identity. The older stress capture also diverges and there is no accepted
ROM stress partner.

### 7.2 DeepSeek

The governed natural workload has exactly 200,000 prompt tokens. Both the ROM
wafer and 32-node HBM cluster must continue to first official EOS or exactly 256
generated tokens. The retained external context-ladder artifact reaches the
prompt length but contains only an eight-token oracle prefix; no accelerator
artifact currently executes that full prompt. Neither can close acceptance.

The immediate DeepSeek blockers are a complete EOS-or-256 external oracle,
source-current deployments bound to the final runtime, and two genuine
long-context accelerator executions. Performance instrumentation and decoded
weight caching make those runs more tractable but do not reduce the workload or
the required arithmetic.

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
2. Regenerate all source-bound RTL and deployment artifacts after the numerical
   repair and performance tranche; reject any stale result.
3. Wire the ABI issue/view/event interface to the bounded engine array, then add
   the missing model-required datapaths without changing the ABI or numerical
   contracts.
4. Run short integrated token diagnostics on all four targets and require exact
   identity before spending resources on long campaigns.
5. Produce the complete DeepSeek external EOS-or-256 oracle.
6. Run fresh Qwen exact-8,000 natural and required agentic/reasoning acceptance,
   stopping at official EOS or cap and publishing the decoded text.
7. Run DeepSeek exact-200,000 on the wafer ROM and exactly 32 HBM/SRAM chips,
   publishing complete tokens, text, counters, topology, and source identities.
8. Complete separate SKY130 and ASAP7 characterization and feed measured limits
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
