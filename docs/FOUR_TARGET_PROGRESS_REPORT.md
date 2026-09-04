# Four-target implementation progress report

**Report ID:** `TA-PROGRESS-4T-2026-09-04`

**Status date:** 2026-09-04

**Retained simulation implementation:** `080d165` adds resolved-active-extent,
row-folded tensor timing and `686ec6c` removes false reduction depth from ROM
non-reducing operators. The result set now contains direct Qwen exact-8K decode
simulations for HBM/SRAM and ROM/HBM at B=1/2/4/8 under both ASAP7 and SKY130
views. Longer functional and prefill simulations listed below are still
running.

**Operating decision:** remain on ABI 3.0 and stop expanding the
correctness-qualified tooling. There is no ABI 3.1, durable-state, rollback,
restart, or retry work on the critical path. The active work is to run the
model and publish numbers. Correctness needs only the following direct checks:
the workload/checkpoint/deployment identities match, output token IDs equal the
independent oracle, IDs are in the legal vocabulary, decoded text is sensible,
the first official EOS is included when produced, and no transaction follows
EOS. Performance comes directly from the event-driven cycle simulator for the
same model, deployment, context, phase, and batch point. Functional retired
instruction ticks and host or RTL-simulator wall time are not TPOT.

**Role:** current narrative status and handoff report. Machine-readable result
artifacts and the [unified execution checklist](UNIFIED_EXECUTION_CHECKLIST.md)
remain authoritative when a copied count or status differs.

## 1. Executive status

There are exactly two highest-priority release outcomes, and they are ordered.
All compiler, RTL, physical-design, and simulator milestones below are enabling
evidence for these outcomes rather than substitutes for them.

| Priority release gate | Current status | Source-current acceptance evidence | Closure condition |
|---|---|---|---|
| 1. Correct output tokens | **open; exact-8K oracle is retained and a source-current HBM run is active** | Qwen's independent exact-8K oracle produced `[18, 24, 16, 151645]`, raw text `391<|im_end|>`, visible text `391`, and official-EOS stop; an older HBM/SRAM functional execution matched it exactly | complete the active source-current HBM run, then run the same prompt on ROM; repeat on distinct chat/reasoning/agentic lanes and B=2/4/8 |
| 2. Desired TPOT | **open; corrected B=1/2/4/8 timing diagnostics retained, no token-correct TPOT yet** | B=1 HBM/SRAM: 2.973824 s ASAP7 and 4.441387 s SKY130; B=1 ROM/HBM: 2.555418 s ASAP7 and 3.816536 s SKY130. Shared-resource B=2/4/8 sweeps peak at 0.507005 token/s for HBM/SRAM and 0.699000 token/s for ROM/HBM on ASAP7 | finish the exact prompt-state execution, measure TTFT and decode ticks from that token-correct run, close remaining attention/vector inefficiency and architecture width, then compare with an explicit numerical SLO |

The 10,000-token/s or 100-microsecond-per-token figure remains an aspirational
north star, not a silently assumed pass threshold. The current simulations are
many orders of magnitude slower and therefore plainly do not reach that
aspiration. A more elaborate checker would not change that conclusion.

The row-folded lane implementation has removed the dominant tensor pathology:
Qwen tensor issued work now equals its 7,568,101,376 useful work units, while
437,583,605,760 units of old rectangular schedule capacity are masked rather
than executed. Physical tensor output-lane utilization is 99.9918%. Total
remaining padding is 11.9039% for HBM/SRAM and 28.3938% for ROM/HBM; attention
is now the largest padded family. The tensor portion measures 85,692,144 cycles
(1.4785 s) on the ASAP7 HBM/SRAM target and 42,745,020 cycles (0.7375 s) on the
ASAP7 ROM/HBM target, closely reproducing the prior compute-only lower bounds.
The next performance iteration is therefore wider/faster real datapaths plus
attention/vector and memory/fabric closure, not more acceptance tooling.

### 1.0.1 Corrected B=1 decode simulation numbers

All four rows below execute one complete ABI 3.0 decode transaction at the
position immediately following an 8,000-token context. They use the corrected
row-folded tensor mapping and the fixed ROM non-reducing schedules.

| Deployment | Process view | Cycles/token | Clock | Modelled TPOT | Aggregate rate |
|---|---|---:|---:|---:|---:|
| HBM + SRAM single chip | ASAP7 | 172,359,893 | 57.959 MHz | 2.973824 s | 0.336267 token/s |
| HBM + SRAM single chip | SKY130 | 172,357,340 | 38.8071 MHz | 4.441387 s | 0.225155 token/s |
| ROM + HBM single chip | ASAP7 | 148,109,458 | 57.959 MHz | 2.555418 s | 0.391325 token/s |
| ROM + HBM single chip | SKY130 | 148,108,696 | 38.8071 MHz | 3.816536 s | 0.262018 token/s |

Relative to the retained padded baseline, HBM/SRAM improves 29.56 times and
ROM/HBM improves 60.07 times on architectural cycles. ROM/HBM is now 1.164
times faster than HBM/SRAM at B=1 on either process view. These are
event-driven simulator outputs with successful ABI transactions and one token
append per transaction. Their overall provenance class remains `assumed`: only
six or seven parameters are characterized and one HBM parameter is
datasheet-derived, while more than one hundred machine parameters remain
assumptions. They are design-simulation numbers, not measurements of fabricated
silicon.

### 1.0.2 Shared-resource batch timing diagnostics

The B=2/4/8 rows use distinct ABI sessions concurrently scheduled over one set
of modeled sequencers, queues, engines, memories, and ports. `service s/token`
is batch makespan divided by B; it is useful for throughput comparison but is
not an individual sequence's latency. Per-lane completion cycles are retained
losslessly in
`results/abi3/cycle/qwen3_exact8k_decode_batch_rowfold_diagnostic_v1.json`.

| Deployment | View | B | Batch makespan cycles | Batch makespan | Service s/token | Aggregate token/s |
|---|---|---:|---:|---:|---:|---:|
| HBM + SRAM | ASAP7 | 1 | 172,359,893 | 2.973824 s | 2.973824 | 0.336267 |
| HBM + SRAM | ASAP7 | 2 | 233,108,723 | 4.021959 s | 2.010980 | 0.497270 |
| HBM + SRAM | ASAP7 | 4 | 457,266,087 | 7.889475 s | 1.972369 | 0.507005 |
| HBM + SRAM | ASAP7 | 8 | 931,705,271 | 16.075248 s | 2.009406 | 0.497660 |
| ROM + HBM | ASAP7 | 1 | 148,109,458 | 2.555418 s | 2.555418 | 0.391325 |
| ROM + HBM | ASAP7 | 2 | 176,158,214 | 3.039359 s | 1.519680 | 0.658033 |
| ROM + HBM | ASAP7 | 4 | 334,095,422 | 5.764341 s | 1.441085 | 0.693922 |
| ROM + HBM | ASAP7 | 8 | 663,335,793 | 11.444914 s | 1.430614 | 0.699000 |
| HBM + SRAM | SKY130 | 1 | 172,357,340 | 4.441387 s | 4.441387 | 0.225155 |
| HBM + SRAM | SKY130 | 2 | 233,106,032 | 6.006788 s | 3.003394 | 0.332957 |
| HBM + SRAM | SKY130 | 4 | 457,260,705 | 11.782914 s | 2.945728 | 0.339475 |
| HBM + SRAM | SKY130 | 8 | 931,697,385 | 24.008426 s | 3.001053 | 0.333216 |
| ROM + HBM | SKY130 | 1 | 148,108,696 | 3.816536 s | 3.816536 | 0.262018 |
| ROM + HBM | SKY130 | 2 | 176,154,731 | 4.539240 s | 2.269620 | 0.440602 |
| ROM + HBM | SKY130 | 4 | 334,089,117 | 8.608969 s | 2.152242 | 0.464632 |
| ROM + HBM | SKY130 | 8 | 663,323,114 | 17.092829 s | 2.136604 | 0.468033 |

The throughput curves saturate by B=4. On ASAP7, HBM/SRAM peaks at 0.507005
token/s at B=4, while ROM/HBM reaches 0.699000 token/s at B=8. ROM's aggregate
throughput advantage grows from 1.164 times at B=1 to 1.405 times at B=8.

These batch rows intentionally expose, rather than hide, their correctness
failure: every fresh-state lane selected legal vocabulary ID `565`; the exact
prompt oracle begins with ID `18` and ends with `[18, 24, 16, 151645]`.
Therefore these are shared-resource saturation measurements, not end-to-end
token-correct TPOT. They also clone the same diagnostic shape rather than run
the eight distinct natural/reasoning/agentic workloads, so the mandatory
heterogeneous B=2/4/8 campaign remains open.

The exact-8K natural-chat reference uses a Moby-Dick context followed by
“What is 17 multiplied by 23? Give only the number.” The independent Qwen
checkpoint produced token IDs `[18, 24, 16, 151645]`, raw text
`391<|im_end|>`, and visible text `391`; token `151645` is the included
official EOS. The active source-current HBM functional simulation is checking
that exact sequence and EOS behavior. Until it finishes, this checkpoint does
not relabel the cycle transaction's synthetic selected ID as correctness
evidence.

For DeepSeek-V4 Flash, the available 32-token/four-output diagnostics all
produce `[13806, 345, 7472, 55560]`, which decodes and re-encodes exactly as
` pump C alone empt`. The 32-chip HBM/SRAM, 32-node ROM array, and single-wafer
ROM functional simulators all match the independent four-token oracle prefix
with legal IDs and successful transactions. Their host wall times are
4,015.484 s, 8,470.543 s, and 3,066.736 s respectively; those host times are
simulation cost, not architectural TPOT. This is P32 diagnostic evidence only.
It does not stand in for the mandatory exact-200,000-token-context run.

Still running at this checkpoint are Qwen exact-8K HBM functional execution,
Qwen HBM and ROM prefill timing under both process views, and a current-source
DeepSeek 32-chip HBM P32 repeat. Shared-resource B=2, B=4, and B=8 timing
diagnostics now exist, but no prompt-initialized, distinct-workload,
token-correct batch timing number exists yet.

The common compiler and functional-simulator stack is real and shared by both
models and both storage backends. Both complete model graphs lower through the
same Model Graph IR, Tensor Kernel IR, and ABI 3.0 records. Current deployment
certificates admit all four intended topologies, and every current deployment
contains zero ABI `STATE` descriptors and zero `STATE` instructions.

The project is not yet at final acceptance. The Qwen exact-8,000 external
oracle and one full causal HBM/SRAM functional accelerator execution both
produce `[18, 24, 16, 151645]`, raw text `391<|im_end|>`, visible text `391`,
and stop on the included official EOS with no later model transaction. The
accelerator run is a genuine end-to-end serialized-deployment execution, but it
is retained as a frozen-source diagnostic because dynamic-batch and authenticated
request-symbol changes landed while it ran. It is not the final current-release
HBM-A/HBM-B/ROM acceptance triplet. There is not yet a source-current DeepSeek
exact-200,000 accelerator
execution, a fully integrated RTL datapath capable of producing those tokens,
or a complete same-view SKY130/ASAP7 physical comparison of all four systems.
A newly completed frozen-source DeepSeek wafer-ROM diagnostic did execute the
real compiled model for the natural P32 prompt, match four oracle tokens, and
retire its final ABI transaction with device-reported `MAX_NEW_TOKENS`. It is
still only a 32-token prompt/four-output prefix run, predates current
execution-authoritative sources and decoded-text capture, and therefore remains
positive arithmetic, termination, and token-path diagnosis rather than a
Gate-1 pass.

The present boundary is therefore:

- compiler and deployment architecture: implemented and independently checked;
- full-model functional simulator: implemented, with prior short token evidence;
- full-shape DeepSeek HBM `HC_PRE` functional qualification: the first exact
  T=512 issue is bitwise closed, but it is one operator and produces no token;
- DeepSeek main sparse-attention phase layout: compiler and interacting-operator
  repair closed over prefill/decode, ratios 0/4/128, circular wrap, and absolute
  position 200,000; this is bounded synthetic/operator evidence and produces no
  checkpoint-backed token;
- lightweight result checks are sufficient for the active simulation phase.
  Existing production validators remain available but are not being extended
  and are not on the critical path. The scalar accelerator runner hashes and loads
  the pinned checkpoint tokenizer, proves prompt decode and re-encode
  round-trip against the retained natural context, and retains raw/visible
  decoded output with oracle-horizon equality; a mismatch makes the run fail;
- governed heterogeneous execution evidence: commits `bb2ddf2`, `fd5dd1f`,
  and `daf6205` add strict request/result schemas and one ABI 3.0 batch runner.
  It loads one deployment, executes genuinely distinct B=1/2/4/8 lanes with
  shared immutable and private mutable storage, validates every lane's legal
  token IDs, complete oracle equality, raw/visible decoded text, independent
  EOS-or-cap retirement, and no post-terminal transaction, and retains raw
  request/token-commit ticks from that same execution. The focused suite
  covers all four batch sizes and fail-closed tampering cases. No production
  model batch has used this path yet, so it contributes zero accepted model
  tokens and zero TPOT points. The singular-workload comparison/TPOT contract
  must be extended to bind a heterogeneous workload set before B>1 timing can
  be promoted;
- Qwen heterogeneous Gate-1 inputs: commits `706f613`, `befc377`, `d071483`,
  and `01231ec` freeze eight distinct, nested B=1/2/4/8 exact-8,000-token
  workloads covering natural chat, reasoning, TerminalBench-style agent/tool,
  and stress cases. Their tokenizer/template/source identities, legal IDs,
  prompt round trips, non-cloning rule, 256-token cap, and first-official-EOS
  rule are authenticated. This is preparation evidence only: all eight
  independent singleton oracles remain pending except the arithmetic B=1 lane,
  no runnable physical batch was emitted, and no B>1 model or accelerator
  batch was executed;
- event-driven cycle simulation: the first Qwen exact-8K B=1 HBM/SRAM and ROM
  decode points now exist for ASAP7 and SKY130. They expose a severe padding
  problem and are the active performance baseline;
- genuine shared batch execution and timing substrate: implemented for ABI 3.0
  scalar sessions at B=1/2/4/8. The production batch driver accepts distinct
  per-lane prompts and generation caps, submits every active lane once per
  wave, preserves canonical session-scoped transactions, and retires each lane
  only on device-reported EOS or cap. Each transaction's request and
  token-commit ticks are immutably bound to its functional submission, trace,
  result, and completion. Focused fixtures prove ragged prompts, independent
  EOS/cap retirement, no post-terminal transaction, B=1 compatibility, and
  cycle-scheduler tick propagation. This is scheduler qualification, not a
  full-model B>1 token result or a characterized TPOT point;
- RTL control plane and bounded arithmetic blocks: independently correlated;
  the row-folding mapper, Sinkhorn tail, and certifying FP32 exp/sigmoid engine
  are standalone blocks and are not yet wired into a token-producing
  full-system path;
- sequencer-to-arithmetic integration: the exact shipped-program Qwen prefix through
  `DMA.GATHER`, `TENSOR.EMBED_LOOKUP`, Qwen `VECTOR.RMS_NORM`, all three
  layer-zero Q/K/V `TENSOR.MATMUL` operations, and query/key
  `VECTOR.HEAD_RMS_NORM` and query/key `VECTOR.ROPE`, or through the DeepSeek
  `DMA.TRANSFER`, is closed;
  a focused Qwen continuation executes the exact PC-32/35 KV appends and
  fixed-context-17 PC-38 GQA for ROM and HBM, making PC 41 output projection
  the next shipped operation without a connected datapath; its prior KV rows
  are synthetic, so it is operator evidence rather than model-context or token
  evidence;
  exact DeepSeek wafer multicast is dual-simulator qualified and integrated
  into that shared prefix, where the ROM path now reaches PC 15 `VECTOR.MHC`;
  exact ROM/HBM `HC_PRE` descriptor admission and tile scheduling are also
  dual-simulator qualified. A new T=1 continuation composes exact
  BF16-by-FP32 fused accumulation, balanced 16,384-element RMS, 24-row
  projection, and the complete coefficient tail behind both current semantic
  configurations. It matches all 74 authenticated checkpoint boundaries and
  both profiles' 24 public words on two simulators. Shipped-prefix control
  integration, multi-token/full-shape execution, downstream layers, and the
  token path remain open;
- exact mandatory long executions: open; the authenticated Qwen oracle and one
  frozen-source HBM/SRAM capture have completed with exact tokens, while an
  earlier HBM attempt remains a no-result `SIGTERM` diagnostic; final
  current-release HBM-A/HBM-B/ROM, workload-matrix, and DeepSeek captures remain
  absent; and
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
| Common IR and four backend builds | closed for current graphs | Qwen and DeepSeek lower through the shared Model Graph and Tensor Kernel IR into HBM and ROM bundles; HBM head norms now encode 32/8 Qwen rows and 64 DeepSeek rows from the neutral IR | rebuild whenever an execution-authoritative source changes |
| Functional execution | partial | the complete functional engine exists; one frozen-source Qwen HBM/SRAM run executed the exact 8K prompt end to end and matched all four oracle tokens through EOS; frozen-source DeepSeek 32-node HBM, 32-node ROM-array, and single-wafer ROM P32 diagnostics each execute the compiled model and match the same four-token oracle prefix; the latest wafer run also retires on the device-reported request cap; the first exact T=512 DeepSeek HBM `HC_PRE` issue matches an independent service on all 12,288 FP32 output words | the Qwen result predates current runtime changes and lacks its independent HBM-B/ROM peers; every DeepSeek token result uses only 32 prompt tokens and a four-token prefix contract, the latest wafer run predates current execution-authoritative sources and decoded-text capture, and the `HC_PRE` result is operator qualification rather than a token |
| RTL 3.0 | partial | shipped control replay and bounded arithmetic pairs independently correlate; the integrated prefix drives Qwen through query/key RoPE and both exact key/value KV scatters, and DeepSeek ROM through wafer multicast; the focused Qwen continuation executes fixed-context-17 PC-38 GQA; current ROM/HBM `HC_PRE` T=1 semantic configurations now execute exact fused projection/RMS and the full coefficient tail with authenticated 74-word agreement; the standalone 256-lane mapper, MAC lane, and multicast transport also have dual-simulator evidence | Qwen must generalize GQA through the governed 8K context and continue at PC 41 output projection; DeepSeek T=1 arithmetic must enter the ordinary shipped-prefix/memory path, generalize to T=512/T=320/all 200K prompt positions, and continue through every layer, logits, selection, append and EOS-or-cap control; no RTL path reaches a token |
| Mandatory workloads | open | the original Qwen exact-8K rendered official-chat prompt is frozen and reproducible; its authenticated external oracle and one frozen-source HBM/SRAM execution both produce `391` followed by EOS. Eight distinct exact-8K B=1/2/4/8 campaign inputs are also frozen and authenticated, but their oracles are pending | a single current-release HBM-A/HBM-B/ROM triplet, all eight Qwen singleton oracles, Qwen natural chat/reasoning/agentic and genuine B=1/2/4/8 accelerator cells, and both DeepSeek exact-200K executions are absent; the retained DeepSeek oracle stops after eight tokens |
| SKY130 and ASAP7 | partial | several bounded blocks have process-specific reports | neither view characterizes a complete target; ASAP7 readiness has 15 fail-closed blockers |
| Governed comparison | partial | all three DeepSeek P32 functional deployments produce the same four oracle-prefix tokens; Qwen HBM/SRAM and ROM now have directly comparable B=1/2/4/8 decode timing diagnostics under ASAP7 and SKY130 | DeepSeek evidence is P32 rather than exact 200K; Qwen source-current functional confirmation and prefill timing are still running; B=2/4/8 timing uses fresh diagnostic state rather than the distinct token-correct workloads, and complete same-view physical characterization is absent |

#### 1.1.1 Gate-eligible token and TPOT matrix

The output-token counts below deliberately separate complete mandatory-workload
evidence from short diagnostics and scheduler fixtures.

| Required production cell | Best retained output evidence | Gate 1 now | Gate 2 now |
|---|---|---|---|
| Qwen HBM/SRAM, exact 8K, B=1 | 4/4 oracle-identical IDs through official EOS, including exact raw/visible text; frozen-source; source-current repeat active | no | diagnostic decode: 2.973824 s ASAP7, 4.441387 s SKY130; selected token `565`, so not token-correct TPOT |
| Qwen ROM, exact 8K, B=1 | no exact-8K current-release functional result; older shorter-workload records exist | no | diagnostic decode: 2.555418 s ASAP7, 3.816536 s SKY130; selected token `565`, so not token-correct TPOT |
| Qwen HBM/SRAM and ROM, exact 8K, B=2/4/8 | 0 correct mandatory-workload output tokens at every batch size; real shared-resource scheduling now produces fresh-state timing diagnostics only | no | diagnostic batch makespans and aggregate rates exist for both views; every lane selects `565`, so no Gate-2 TPOT |
| DeepSeek 32-chip HBM/SRAM, exact 200K, B=1 | 0 generated tokens on the mandatory prompt; a separate P32 diagnostic has 4/4 oracle-prefix IDs | no | no TPOT |
| DeepSeek wafer ROM, exact 200K, B=1 | 0 generated tokens on the mandatory prompt; a separate P32 diagnostic has 4/4 oracle-prefix IDs and correct device-cap retirement | no | no TPOT |

Thus no batch-size row currently combines a source-current, prompt-initialized,
token-correct functional result with fully characterized architectural timing.
B=1/2/4/8 cycle diagnostics now exist; correct heterogeneous B=2/4/8 execution
remains absent.

### 1.2 Source-current execution readiness

At this checkpoint one governed Qwen exact-8K HBM/SRAM capture has completed
with exact oracle tokens, legal independent decoding, and correct EOS control,
but it is not current-release acceptance. Its execution-authoritative hashes
all match captured Git tree `008bf765e212c061f930d5a2726563f7ddeba740`.
Current `main` has since changed six required runtime sources, so the result is
quarantined as positive frozen-source evidence while the final three-capture
campaign waits for one deliberately frozen release snapshot. The stale short-threshold,
32-node DeepSeek ROM-array rerun was deliberately stopped after more than two
hours without a result because it predates the sparse-layout, liveness, and
ordered-product fixes and cannot close either release gate. High-memory model
jobs are required to remain serialized; the Qwen launch started with 143 GiB
available memory, zero used swap, and no competing governed model or cycle
process. A separate session subsequently launched a DeepSeek ROM-array
threshold job in the same root worktree. That post-launch contention is an
operational-governance incident, but the completed result reports zero swaps
and retains its resource observations. Neither its 5,659.73-second host wall
time nor its retired-instruction counter is architectural TPOT.

A later serialized DeepSeek single-wafer ROM P32 run completed in 3,066.736
host seconds and matched the first four external-oracle token IDs exactly. Its
final completion carries device-reported `EosReason.MAX_NEW_TOKENS`, and the
selection engine records one length stop. It is retained specifically as a
frozen-source P32 diagnostic: it predates current execution-authoritative
sources and decoded-text capture, uses only 32 prompt tokens and four outputs,
and is neither current-release Gate 1 nor a source for TPOT.

- Commit `969cb52` replaces the old plain-prose Qwen long workload with one
  governed prompt rendered through the official Qwen chat template. It has
  exactly 8,000 input token IDs and ends with the canonical authenticated
  question, “What is 17 multiplied by 23? Give only the number.” The expected
  visible answer is `391`, but no output-token sequence is embedded or treated
  as an oracle. Gate 1 requires a separately generated external oracle, two
  independently materialized HBM captures, and one ROM capture. All three must
  match every token ID and decoded text, accept only legal vocabulary IDs,
  include and stop at the first official EOS or reach exactly 256 tokens, and
  show no model transaction after termination. The authenticated oracle has
  now completed after verifying all 16,381,470,720 checkpoint payload bytes.
  It produces IDs `[18, 24, 16, 151645]`, raw text `391<|im_end|>`, visible text
  `391`, and `stop_reason=eos`. This is valid external expected-output evidence,
  not accelerator correctness or target TPOT.
- Commit `9faf23f` adds a governed, create-once production-attempt boundary for
  the Qwen oracle, HBM A, independent HBM B, and ROM lanes. It preserves unique
  result/deployment/log/time paths, requires at least 100 GiB available memory,
  zero used swap and exclusive governed-model ownership at launch, and marks
  any failure or termination ineligible for both release gates. Attempt
  `hbm-a-20260904T003035Z-1bb6e3af8e0f4aa4` completed after admitting all 74
  instructions and 215 descriptors. Its canonical result is
  `results/abi3/w10/qwen3_8b_hbm_natural_a.json`, SHA-256
  `8d5615337ffb548cb18aaca489899ccca4107626abba8ca93b395dd08a7c7e62`.
  It produced exactly `[18, 24, 16, 151645]`, raw text
  `391<|im_end|>`, and visible text `391`; token `151645` is the official EOS.
  All four per-step tokens equal the oracle, transaction IDs strictly increase,
  EOS is included, no post-EOS transaction exists, vocabulary IDs are legal,
  and independent tokenizer decode/encode round-trip checks pass. The result
  SHA differs from the oracle artifact SHA
  `22a51d7d8f220a471623038dd10296a434df957e7e60176e685e93738831d33b`
  because they are independently structured evidence artifacts, not because
  their token streams differ.
- The independent W10 checker accepts all token, text, serialized-deployment,
  admission, terminal, counter, association, and captured-source facts for that
  HBM row. Against current `main`, it fails only the expected source-current
  checks for `runtime/abi3/constants.py`, `runtime/abi3/verifier.py`,
  `runtime/driver.py`, `runtime/sim/device.py`, `runtime/sim/engine.py`, and
  `runtime/sim/memory.py`. HBM-B and ROM must not be paired with this older
  capture for final acceptance; all three final runs must use one frozen release.
- An earlier Qwen HBM natural capture A ran as the durable user service
  `opentallas-qwen-w10-natural-a-r1.service`. It launched from committed source
  `2270889bd9716a918e5a0193e90af3bfa60be7f9`, the exact 8,000-token workload,
  74 instructions, and 215 admitted descriptors, with first-EOS-or-256
  termination. At 19:11:24 UTC it received `SIGTERM` after 1:53:08 wall time
  and 2:21:48 accounted CPU time. Peak RSS was 9,935,412 KiB, and there were 355
  major faults and no swaps. No result JSON was written; stdout ends at the
  execution-start line. The unit had no runtime limit, and the three assigned
  project agents report that they did not signal it, so the source of the
  external termination is not established. This run proves no output token,
  acceptance verdict, or TPOT. It remains diagnostic provenance only.

- Qwen HBM deployment `0d7897457e14…` passes its 21/21 certificate and the
  independent 43/43 admission checks. It spans 18.53 GB of admitted HBM and has
  exact prefill/decode entrypoints, 215 descriptors, 74 instructions, and zero
  `STATE` records. A source-map audit found that `runtime/sim/weight_cache.py`
  participates in execution but was not mandatory in the W10 checker. It is now
  part of the required source map. The terminated durable run bound its launch
  source and output identity; any replacement must bind a newly frozen identity
  rather than silently folding later source changes into the failed run.
- Commit `197a714` removes a correctness-critical HBM lowering default. The
  neutral IR declares the logical head rows, but the old HBM path encoded
  `aux0=1` after flattening the physical operand. The source-current Qwen bundle
  now encodes 32 query heads and 8 key heads, and all four compressed DeepSeek
  descriptors encode 64 heads. Real-model regressions and missing/zero-head
  fail-closed cases pass; Qwen's rebuilt bundle is deterministic, admitted, and
  independently passes all 21 certificate checks. This repair is required
  compiler evidence, not a generated token.
- Commit `04cceeb` parallelizes the eight numerically independent Qwen GQA KV
  heads in the host functional simulator without changing an individual
  head's reduction order, outputs, counters, descriptor semantics, or fault
  ordering. A representative exact-8K-shape attention benchmark improved from
  5.6503 s to 1.6968 s (3.33x) with an identical output digest and counters;
  34 focused tests pass. These seconds describe campaign turnaround only and
  are categorically not target TPOT.
- Commits `9da5999` and `c85b418` give every ABI session private mutable
  HBM/SRAM/HOST state while sharing immutable deployment and checkpoint
  objects, then add fail-closed B=2/4/8 batch waves with per-lane active masks,
  completion, token, transaction, commit-tick, EOS, and length retirement.
  Commit `9ea330b` removes the remaining Python symbol side channel: all 15
  request symbols now travel in a CRC32C- and SHA-256-authenticated descriptor
  named only by the existing `request_descriptor_id` field. Missing, corrupt,
  duplicate, stale, replayed, cross-session, cross-generation, and
  cross-transaction descriptors fail before engine work. This makes genuine
  batched Gate-1 runs structurally possible. Commits `2e6dcdc`, `6247ab5`, and
  `e6d3a24` then replay those exact functional trace spans through one bounded,
  shared-resource target-cycle scheduler and bind every transaction's request
  and token-commit tick to its deployment, capability, cost table, session,
  request descriptor, submission, trace, result, and completion identities.
  Twenty-six focused batch tests and eight affected cycle-model tests pass; a
  heterogeneous B=2 fixture retires one EOS lane after wave zero while the
  other lane completes wave one. Full-model heterogeneous inputs, governed
  timing-trace export, characterized SKY130/ASAP7 timing, and every B>1 model
  result remain absent, so these commits create no correctness or TPOT claim.
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
- Commit `a877cfe` removes the false main-attention KV union. The neutral graph
  now selects `current || compressed-prefix` in prefill and
  `physical-window[128] || compressed-prefix` in decode using existing ABI 3.0
  phase predicates and forward branches. Its fresh 3,956-kernel graph is
  `6c281c3b7f1bcf3366b9e572c553b6bddae8d13a6ac8056676a2a70166898834`.
  Independent admission accepts the ROM image at 1,329 instructions and 3,861
  descriptors and the HBM image at 1,292 instructions and 3,293 descriptors,
  with zero errors. The 82 compiler/interacting-operator cases, 105 affected
  engine cases, and 16 direct neutral-admission checks pass. The matrix covers
  prefill spans 1/32/129/160/256, decode positions 1/127/128/129/200,000, and
  ratios 0/4/128, including bit-exact BF16 sparse output. This closes a concrete
  Gate-1 prerequisite only: it executes no checkpoint-backed full model,
  produces no output token or EOS decision, and supplies no TPOT sample.
- `check_deepseek_v4_200k_accelerator_acceptance.py` now provides the final
  fail-closed accelerator-pair gate, covered by 26 focused tests. After an
  accepted Gate-B oracle, it independently authenticates one exact ROM-wafer
  record and one exact 32-node-HBM record, requires the exact 200,000-token
  prompt and first-EOS-included-or-256 termination, checks zero `STATE`, current
  identities, exact token IDs/text, per-step semantics, counters, implementation
  identity, and association equality after 32-node normalization. Its presence
  is tooling readiness only; no production exact-200K pair exists.
- Commit `1be6e8d` extends the retained source-bound prefix. All four shipped
  decode images enter the real sequencer. Its 16 launches include 6 FP32
  `DMA.GATHER`, 4 BF16 `TENSOR.EMBED_LOOKUP`, 2 Qwen BF16
  `VECTOR.RMS_NORM`, 2 complete Qwen layer-zero query `TENSOR.MATMUL`, and 2
  DeepSeek stride-zero BF16 `DMA.TRANSFER` operations. The two 4,096-by-4,096
  query projections consume every code of the authenticated 32 MiB checkpoint
  matrix, perform 33,554,432 MACs, and reproduce all 8,192 BF16 outputs. The
  integrated Verilator replay passes 136,496 checks over 66,560 result words.
  The unchanged serial MAC lane is additionally bound to the retained Icarus
  and Verilator qualification, but Icarus did not run either complete
  4,096-by-4,096 integrated transaction. At that commit Qwen refused the key
  projection at PC 14. DeepSeek ROM and HBM refused `LINK.MULTICAST` at PC 13 and
  `VECTOR.MHC` at PC 14 in this shared prefix.
- Commit `60478c0` advances both shipped Qwen images through the complete
  descriptor-driven layer-zero query, key, and value projection family. Across
  ROM and HBM it executes six MATMUL launches: two 4,096-output query matrices
  and four 1,024-output key/value matrices, for 50,331,648 ordered MACs and
  12,288 exact BF16 result words. The complete four-target prefix now has 20
  real engine launches, 70 resolved views, 70,656 result words, and 100,712,448
  authenticated selected checkpoint bytes. Its integrated Verilator replay
  passes 144,708 comparisons; the unchanged MAC lane remains separately
  qualified under Icarus and Verilator. Qwen now fails closed at PC 20
  `VECTOR.HEAD_RMS_NORM`, while the DeepSeek boundaries are unchanged. This is
  authenticated intermediate-tensor RTL evidence, not a decoded token, EOS,
  end-to-end model correctness, or TPOT result.
- Commit `4ee1f25` advances the Qwen prefix through query/key
  `VECTOR.HEAD_RMS_NORM`. The campaign now executes 24 real launches and checks
  80,896 output words; the isolated retained Verilator campaign passed 163,169
  comparisons before later build-artifact drift invalidated a root-worktree
  source-current rerun. The next unsupported Qwen instruction is
  `VECTOR.ROPE` at PC 26. This is still prefix evidence: it produces no logit,
  token, EOS decision, or TPOT sample.
- Commit `55ca192` advances both Qwen images through the query and key
  `VECTOR.ROPE` operations at PCs 26 and 29. The retained standard campaign has
  28 launches, 91,136 exact words, and 189,820 integrated checks; Qwen now
  fails closed at PC 32 `DMA.SCATTER`. The combined multicast overlay has 29
  launches and resolves 100 views. These are checkpoint-backed intermediate
  tensors at positions 0 and 7,999, not a complete layer, selected token, EOS,
  or TPOT sample. Commit `6633a3b` canonically regenerates the affected
  deployments, certificates, vectors, standalone multicast qualification, and
  both prefix campaigns after the runtime and DeepSeek scheduler integrations.
- Commits `93b6234` and `586616a` add focused Qwen continuations beyond that
  shared bridge. The first executes the exact ROM/HBM PC-32 key and PC-35 value
  scatters. The second executes fixed-context-17 PC-38 `ATTENTION.GQA`: one ROM
  and one backpressured HBM case each match all 4,096 BF16 output words from an
  independent scalar oracle. Icarus and pinned Verilator agree on 20,565 checks
  per simulator, including 8,192 computed-word comparisons and 12,288
  fail-closed sentinel checks; generic Yosys elaboration reports zero problems.
  The current Q/K/V row is an authentic causal RTL result, but prior KV rows
  0 through 15 are synthetic transformations because no authentic history was
  retained. This closes only bounded operator arithmetic. It produces no layer,
  token, EOS, architectural token-commit tick, physical timing, or TPOT result;
  PC 41 output projection is next.
- Commit `0b928e5` independently qualifies the exact DeepSeek ROM PC-13 wafer
  multicast on Icarus and Verilator: 256 participants, 255 tree messages,
  4,177,920 payload flits, 4,194,304 exact destination writes, one injected CRC
  error recovered by one bounded replay, and 37 fail-closed mutations. It is not
  yet instantiated by the shared issue bridge and is transport evidence only.
- Commit `2e6d352` integrates that unchanged adapter into the shared shipped
  prefix behind an explicit verification-profile parameter. A frozen overlay
  binds the prior vector hashes and full multicast records, then the real
  sequencer retires PC-13 `LINK.MULTICAST` and reaches PC-15 `VECTOR.MHC`.
  Independent streaming checkers validate every destination write, tree parent,
  source/destination stall, and CRC replay. Its earlier stale-certificate
  boundary is preserved as history; commit `6633a3b` replaces it with the
  source-current bounded-prefix-only artifact. It adds no accepted token or
  TPOT point.
- Commit `256b568` independently qualifies the first exact DeepSeek HBM PC-14
  `VECTOR.MHC` / `HC_PRE` issue at T=512. It authenticates the official first
  512 prompt embeddings and complete relevant checkpoint shards, composes 128
  independent four-token service calls, executes one admitted full-shape ABI
  functional-engine operation, and compares all 12,288 FP32 output words
  bitwise with zero mismatches. It accounts for 201,326,592 ordered projection
  fused product-adds. This is full operator-level functional evidence only: it
  is not RTL execution, token generation, EOS completion, architectural timing,
  or TPOT. Commit `601a108` subsequently qualifies a correctly rounded finite
  FP32 divider and atomic post-stable-softmax 4x4 Sinkhorn-20 tail on Icarus and
  Verilator: 6,641 division cases, 81 matrices, and 73,040 exact checks, plus
  clean generic Yosys elaboration. Commit `79b6a19` then adds a synthesizable,
  fail-closed FP32 engine for correctly rounded finite nonpositive exponential
  and direct sigmoid. Its 4,200 exact-rational cases produce 4,155 certified
  results and 45 intentional refusals; Icarus 11.0 and pinned Verilator 5.050
  agree across 169,962 checks, and pinned Yosys 0.68 reports zero elaboration
  problems. Commit `9c527e5` composes row max, FP32
  subtraction, that exponential, balanced summation, exact division, and
  per-element epsilon into an atomic source-major 4x4 stable-softmax block.
  Icarus and Verilator agree on 2,394,764 checks per simulator across 853
  matrices, including all 512 first-block and 320 final-block checkpoint
  matrices. The subsequent atomic stable-softmax/Sinkhorn composition passes
  19,313,653 checks per simulator on the same 853 cases, performs 528,528
  exact Sinkhorn divisions, and reproduces the authenticated first T=512 final
  combination output byte-for-byte. Its manifest binds the current ROM PC-15
  descriptor 381 and HBM PC-14 descriptor 545, but does not execute either.
  Commit `0da6107` supplies the subsequent T=1 integration: exact
  BF16-by-FP32 fused accumulation, balanced projection/RMS, and the full
  coefficient tail behind both derived semantic configurations. Icarus and
  pinned Verilator agree on
  1,379,450 checks and all 74 authenticated checkpoint boundary words for each
  profile. Full-shape execution including the other 389 prefill blocks and
  ordinary shipped-prefix integration remain open, so this is still not a
  model-token result.
- Commits `17fbb27`, `874b48e`, and `ff5fcb8` add and qualify the exact
  DeepSeek `HC_PRE` tile scheduler. Its refreshed vectors admit ROM PC 15
  descriptor 381 and current HBM PC 14 descriptor 545 while proving semantic
  equivalence to the prior authenticated descriptor 546; they cover ROM T=1
  and HBM T=512/T=320/T=1, and explicitly
  covers the exact-200K partition `390 * 512 + 320`. Icarus and Verilator agree
  on 688,188 emitted tiles and 11,346,434 checks; 181,605 backpressure cycles
  preserve stable metadata and counters, while all 18 malformed cases fail
  before work. The separate T=1 arithmetic continuation now computes one
  authentic coefficient transaction behind these semantic configurations, but
  the scheduler campaign itself remains schedule-only and neither path
  produces a token, EOS decision, architectural timing, or TPOT.
- Commit `081161b` adds the correctness-qualified TPOT request, raw timing-trace,
  report schemas, and checker. It requires exact independent-oracle tokens and
  EOS/cap behavior before consuming raw token-commit ticks from the same bound
  execution. It categorically excludes functional and RTL simulator wall time,
  projections, and unprovenanced cycles. No real model timing trace or numerical
  ROM/HBM SLO was added, so current production TPOT remains not evaluable.
- Commit `f3cab35` additionally binds request-start and every token-commit tick
  to the exact token-execution record and makes the checker reconcile an
  external timing trace with those events. This closes a measurement-integrity
  hole but adds no correctness-qualified TPOT point.
- Commit `cbaecf0` records the shared tensor-datapath production decision. One
  256-lane, four-group, maskable and row-foldable datapath remains the baseline
  for both models; a separate narrow decode engine is only a same-process PPA
  fallback. The decision defines full artifact-driven functional execution,
  an explicitly labeled RTL-bound accelerated full-system co-simulation tier,
  and monolithic full RTL as distinct evidence classes. Its normative rule
  forbids publishing TPOT unless that exact batch/source/checkpoint/tokenizer/
  workload/IR/deployment/implementation/process execution first passes complete
  tokens, legal decoding, EOS-or-cap, and no-post-EOS checks.
- Commits `473d0fb` and `5256f5c` qualify the standalone synthesizable 256-lane,
  four-group deterministic row-folding mapper and replace its general divider
  with exact quotient-boundary comparisons. Icarus and Verilator agree over 34
  cases, 2,065 waves, 498,429 logical coordinates, and 1,663,558 checks per
  simulator. This closes lane-coordinate control in isolation; the mapper is
  not yet integrated with the tensor datapath, memory ports, or token path.
- The first 32-node DeepSeek ROM-array functional attempt on
  `TA-DS-CTX-129-1` ran for 2 h 45 min wall time and about 5 h of CPU at 64 GB
  RSS, but its owning session stopped while execution was still in progress.
  It wrote no result and proves no token. A replacement began at 22:00:44 UTC;
  its live command writes to a session-temporary
  `scratchpad/array_ctx129_rerun.json`, not directly to the canonical
  `results/abi3` path. Completion, artifact preservation, and validation must
  all be confirmed before even this short diagnostic may be cited.
- The first 32-node DeepSeek ROM-array cycle attempt was admitted, then killed
  by the kernel OOM killer after about 155 min wall time and 29 CPU-hours at
  84 GB RSS. It produced no cycle artifact. That historical deployment assigned
  a distinct physical object to every logical activation and declared 1.2 TB
  of HBM per node, so its failure does not characterize the current build.
- The source-current backend-neutral liveness allocator preserves every IR
  extent but reuses exact-size, exact-dtype mutable buffers whose closed
  program-order lifetimes do not overlap. On the sparse-corrected 3,956-kernel
  graph it reduces 1,073,359,364,104 logical activation bytes to an
  83-slot, 172,292,907,016-byte arena. The 32-node ROM array now uses
  178,281,603,216 of its physically declared 180,000,000,000 HBM bytes per
  node, leaving 1,718,396,784 bytes, and admits deterministically with 1,346
  instructions, 3,429 descriptors, and zero `STATE` resources. The wafer build
  also admits, and the HBM planner's refactor is byte-identical to its prior
  placement for the same graph. The retained evidence is
  `results/abi3/deepseek_v4_activation_liveness_capacity.json`. This closes the
  artificial capacity declaration, not Gate 1: no new full-model token or
  cycle/TPOT result was produced, and host-resident behavior still needs a new
  measured run.

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
- ABI 3.0 now enforces the authenticated request's active generation cap on the
  device. The immutable generation policy remains the ceiling; an oversized
  request is refused before work, while a narrower request returns
  `MAX_NEW_TOKENS` on the completion that commits its final non-EOS token and
  retires that session. A heterogeneous B=2 test proves independent one-token
  and two-token cap retirement with no post-terminal host write or model
  transaction. This closes a production batch-runner prerequisite, not a
  full-model B>1 token result or TPOT point.
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
remaining general operator surface—including non-HC softmax and other
transcendental forms—is still incomplete; the separately qualified HC 4x4
stable-softmax block is not wired into this engine array. The shipped programs reach 37 distinct opcode pairs: 11 have
bounded correlated datapaths and 26 still have no correlated datapath RTL at
this boundary.

### 5.3 First shipped-program engine prefix

The separate shipped-prefix campaign closes one narrow connection between the
two evidence classes above. It validates the real operator, tensor-view, dtype,
permission, geometry, and numeric descriptors before allowing the sequencer's
initial generated-RoPE gathers, embedding lookups, Qwen RMSNorms, complete
layer-zero Q/K/V projections, head normalizations, query/key RoPE, and DeepSeek
transfers to launch the bounded datapaths. The base campaign's 28 launches
produce 91,136 checked compact result words through 94 resolved views, with
189,820 integrated Verilator comparisons. The unchanged MAC lane and RoPE core
are separately bound to retained Icarus and Verilator arithmetic qualification;
the complete integrated prefix itself is Verilator-only. Engine faults are
precise: a failed operation neither retires nor publishes its completion event.

The frozen-identity multicast overlay in
`results/rtl/abi3_shipped_prefix_multicast_campaign.json` advances only the
DeepSeek ROM case. It retires the exact PC-13 `LINK.MULTICAST`, checks
4,194,304 writes of a deterministic nonzero 64-KiB live scratch payload across
all 256 participants, validates per-participant ordering and every binomial-tree
parent, and exercises CRC/NAK/replay plus source and destination backpressure.
The full four-case Verilator replay passes 12,756,653 checks and the focused
DeepSeek-ROM Icarus replay passes 12,587,599 checks with the same normalized
case record. The new DeepSeek ROM boundary is PC 15 `VECTOR.MHC` descriptor
381; within this shared prefix Qwen stops at PC 32 `DMA.SCATTER`, and DeepSeek
HBM still stops at PC 14
`VECTOR.MHC`. Totals are 29 launches, 91,136 compact result words, and 100
resolved views.

Commit `6633a3b` canonically rebuilds the deployment chain and refreshes the
retained source identities after the dynamic-batch, request-symbol, DeepSeek
scheduler, and release-profile integrations. The artifact is now explicitly
`source_current_bounded_prefix_only`, not a full-execution promotion.
Its embedding index remains legal token ID 0, selected solely as a bounded
deterministic probe; it is not a tokenizer-driven model output and establishes
neither a whole token step nor architectural TPOT. No current RTL simulation
executes a whole model or produces an accepted output token.

Separate source-bound Qwen campaigns extend only that model's bounded decode
slice. `results/rtl/a3_qwen_kv_scatter_campaign.json` executes the PC-32/35 KV
appends, and `results/rtl/a3_qwen_gqa_campaign.json` executes the exact PC-38
context-17 arithmetic for ROM and HBM. The latter compares 8,192 computed BF16
words against an independent oracle on each of Icarus and pinned Verilator and
proves zero publication in three fault cases. Its authentic current Q/K/V row
does not make the synthetic prior-context rows authentic. The new bounded Qwen
boundary is PC 41 `TENSOR.MATMUL`; context generalization, layer completion,
token selection, EOS, architectural tick tracing, and TPOT all remain open.

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

The authenticated external oracle is complete: it verified the full pinned
checkpoint, consumed exactly 8,000 prompt tokens, produced IDs
`[18, 24, 16, 151645]`, decoded to visible text `391`, included the official
EOS, and stopped immediately. One governed HBM/SRAM execution from captured
tree `008bf765e212c061f930d5a2726563f7ddeba740` produced the same full sequence
and terminal behavior through the serialized ABI 3.0 deployment. That is a
successful frozen-source functional-accelerator diagnostic, not final W10
acceptance on current `main`: runtime changes merged while it ran, and HBM-B
plus ROM do not yet exist from the same frozen release. The retained older local
pair contains 256-token sequences for a superseded plain-text
prompt and oracle identity. Those files were preserved under an ignored legacy
directory and removed from the production canonical paths so they cannot be
mistaken for, overwrite, or block the authenticated official-chat campaign.
The older stress capture also diverges and has no accepted ROM stress partner.

### 7.2 DeepSeek

The governed natural workload has exactly 200,000 prompt tokens. Both the ROM
wafer and 32-node HBM cluster must continue to first official EOS or exactly 256
generated tokens. The retained external context-ladder artifact reaches the
prompt length but contains only an eight-token oracle prefix; no accelerator
artifact currently executes that full prompt. Neither can close acceptance.

The 32-node ROM-array controlled variant has a frozen-source short-rung
diagnostic: on the 32-token natural chat prefix it generated
`[13806, 345, 7472, 55560]`, exactly matching the independent oracle prefix and
decoding to ` pump C alone empt`. All 55 recorded execution-source identities
rehash against its captured source set, all token IDs are legal, and the backend-aware context gate independently
matches every per-node and cluster-total sparse-attention counter. This closes
that variant's 32-token/four-output diagnostic rung only. It is not the required
wafer-ROM target, did not run 200,000 input tokens, and stopped at its four-token
diagnostic cap rather than EOS or the production 256-token cap.

The immediate DeepSeek production blockers are execution of the new fail-closed production
oracle through complete EOS-or-256, including its pre-run and completion
full-byte/input checks, followed by two genuine long-context accelerator
executions. The launcher and final pair checker are implemented and focused-test
complete, but neither the full oracle run nor either accelerator run has
occurred. Performance instrumentation and decoded weight caching make those
runs more tractable but do not reduce the workload or the required arithmetic.
The stale 129-token ROM-array rerun was stopped without a result after it had
served its resource-diagnosis purpose. Even a successful eight-token rerun
would not substitute for the exact-200K wafer-ROM or 32-node-HBM executions.

The desired single-wafer ROM topology has also completed the same P32
diagnostic. It generated `[13806, 345, 7472, 55560]`, which the pinned tokenizer
decodes as ` pump C alone empt`, and an independent audit confirms exact
four-position equality with the external oracle and exact prompt-text
round-trip. This is a full compiled-model functional execution for the stated
32-token/four-output request, which is what `functional_artifact_only` means;
it is not full production acceptance. It does not execute the exact-200K
prompt, contains no RTL-bound or characterized target timing, and predates the
current execution-authoritative sources and decoded-text evidence contract.
Its last completion does correctly report `MAX_NEW_TOKENS`; that closes the
short diagnostic's termination check only. Gate 1 therefore remains open and
Gate 2 remains blocked.

### 7.3 Tokens, stopping, and speed actually established

The current evidence supports only the following carefully scoped statements:

- The source-current Qwen external oracle processed the exact authenticated
  8,000-token official-chat prompt and generated `[18, 24, 16, 151645]`, raw
  text `391<|im_end|>`, and visible text `391`, stopping at EOS after 13.76 s.
  That duration is external-oracle host/GPU execution time, not accelerator
  simulation speed or target TPOT.
- The frozen-source Qwen HBM/SRAM accelerator diagnostic generated the same
  `[18, 24, 16, 151645]`, raw text `391<|im_end|>`, and visible text `391`.
  It included official EOS and submitted no later transaction. Total functional
  host wall time was 5,659.73 s; prompt plus first token took 5,607.388119 s and
  later steps took 19.784995 s, 16.409743 s, and 16.144489 s. These values are
  useful only for campaign planning. Recorded completion ticks are
  `[22714, 24818, 26922, 29026]`, with a 2,104-tick delta for each later token,
  but this functional device currently advances that counter by retired
  instructions. It is not a characterized architectural cycle timebase, so
  neither the ticks nor host seconds are accelerator TPOT.
- The retained DeepSeek external reference did process the exact 200,000-token
  natural prompt. It generated token IDs `[14, 412, 855, 260, 836, 881, 3495,
  204]`, decoded as `", as if a man were able\r"`, and stopped because its
  configured eight-token limit was reached—not because EOS occurred. It took
  435.266 s including a 405.05 s tiled prefill. This is GPU external-oracle
  speed, not ROM-wafer or 32-chip simulator speed.
- The frozen-source DeepSeek 32-node ROM-array diagnostic produced
  `[13806, 345, 7472, 55560]` on the 32-token pump prompt. Those tokens exactly
  match the independently produced prefix, have no legitimacy problem, and
  decode to ` pump C alone empt`, coherently continuing the input. Every one of
  its 32 per-node sparse-attention counter sets and its independent cluster
  totals equal the closed-form context model; the retained context-gate artifact
  is `results/abi3/deepseek_v4_rom_array_p32_context_gate.json`. The run stopped
  at the requested four-token prefix cap after 8,745.571 host seconds. Its
  completion ticks `[26337, 38756, 51175, 63594]` remain functional-device
  counters rather than a characterized process clock. This is therefore a
  valid short functional diagnostic, not exact-200K Gate 1 and not TPOT.
- The frozen-source DeepSeek 32-chip HBM/SRAM diagnostic independently ran the
  same natural P32 prompt through its own compiled ABI 3.0 deployment and
  produced the same legal IDs `[13806, 345, 7472, 55560]`, with no oracle
  divergence and decoded text ` pump C alone empt`. The refreshed
  `results/abi3/deepseek_v4_context_gate.json` revalidates the execution-source
  hashes and exactly reconciles all four sparse-attention quantities on every
  one of 32 nodes and at cluster total. It stopped at the requested four-token
  prefix cap after 4,015.484 host seconds. Completion ticks
  `[26800, 38442, 50084, 61726]` advance by functional-device bookkeeping, not
  a characterized SKY130 or ASAP7 clock. The governed
  `results/abi3/comparison_deepseek_rom_array_vs_hbm.json` therefore establishes
  identical functional output over this short horizon, but explicitly makes
  no exact-200K, wafer-ROM, RTL, timing, TPOT, or silicon claim.
- The frozen-source DeepSeek single-wafer ROM diagnostic ran the same P32
  natural prompt and produced the same legal IDs
  `[13806, 345, 7472, 55560]`, decoded as ` pump C alone empt`, with exact oracle
  prefix equality. Its host wall time was 3,066.736 s and its completion ticks
  were `[26102, 38286, 50470, 62654]`. Host time is simulator campaign speed;
  those ticks are retired-work bookkeeping rather than SKY130/ASAP7 target
  cycles. Its final completion correctly reports device-side
  `MAX_NEW_TOKENS`, but the run is only P32/four outputs and predates current
  execution-authoritative sources and decoded-text capture. It therefore
  closes no release gate and supplies no TPOT point.
- The new DeepSeek HBM PC-14 qualification produces intermediate `HC_PRE`
  tensors, not vocabulary logits or a selected token. Its 12,288 output words
  match bitwise and are useful for localizing the next RTL work, but they add
  zero generated tokens to the acceptance count and provide no TPOT sample.
- The retained Qwen HBM exact-8K attempt generated 193 tokens in 14,982 s, or
  about 77.6 wall seconds per generated token when its prefill cost is averaged
  over that partial output. It diverged from the oracle at generated index 137
  and then encountered the historical capacity boundary. The number describes
  an obsolete functional-simulator build; it is not a production throughput
  result.
- An earlier source-frozen Qwen HBM attempt ran for 1:53:08, then received
  `SIGTERM` before writing its result JSON. It emitted no retained output token,
  so its host runtime cannot be divided into a TPOT and it establishes neither
  correctness nor target performance.

No source-current mandatory accelerator run has yet produced a defensible
target tokens-per-second figure. Functional host time, cycle-model time, RTL simulator
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
The detailed implementation and evidence order is frozen in the
[ABI 3.0 tensor-datapath decode-utilization decision](ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md).
Its 100-microsecond-per-token figure is an aspirational north star, not a
release pass criterion; the actual SLO remains to be frozen separately for
each model, role, process/PVT view, batch/concurrency point, statistic, and
eligible evidence class.

Commit `8a7160d` exposed the original fixed-tile performance blocker. Commits
`473d0fb` and `5256f5c` then proved the active-row and deterministic folding
coordinate rule in standalone RTL. Commit `080d165` now applies those resolved
active extents and the same row-folded wave counting in the cycle model: Qwen
tensor issued work equals 7,568,101,376 useful work units, tensor executed
padding is zero, and only 128 of 1,556,992 physical output-lane slots are
masked. Commit `686ec6c` separately prevents embedding and vector operations
from inheriting a weight tensor's reduction depth; this reduces ROM vector
compute from 3,814,686,112 to 6,550,800 cycles.

The corrected B=1 total is 172,359,893 cycles for HBM/SRAM and 148,109,458
cycles for ROM/HBM on ASAP7. The standalone lane mapper and cycle model now
agree on the scheduling rule, but a complete 256/512-lane RTL engine with
accumulators, SRAM/HBM ports, all operators, selection, token append, and EOS
is still absent. The cycle results therefore remain architectural design
simulations rather than full-system RTL token execution.

Even granting perfect removal of every padded issue, perfect overlap, no
bubbles or conflicts, and the characterized 0.3458786 useful work per
lane-cycle, the source-current useful-work inventory gives these optimistic
*compute-only lower bounds* for one batch decode step. They are design
feasibility projections, not executed TPOT:

| Target and physical tensor lanes | Process proxy | B=1 | B=2 | B=4 | B=8 |
|---|---|---:|---:|---:|---:|
| Qwen HBM, 256 | SKY130, 38.8071 MHz | 2.202 s | 4.405 s | 8.810 s | 17.620 s |
| Qwen HBM, 256 | ASAP7, 57.959 MHz | 1.475 s | 2.949 s | 5.899 s | 11.798 s |
| Qwen ROM, 512 | SKY130, 38.8071 MHz | 1.101 s | 2.202 s | 4.405 s | 8.810 s |
| Qwen ROM, 512 | ASAP7, 57.959 MHz | 0.737 s | 1.475 s | 2.949 s | 5.899 s |
| DeepSeek 32-chip HBM, 8,192 global | SKY130 proxy | 0.1085 s | 0.2169 s | 0.4339 s | 0.8677 s |
| DeepSeek 32-chip HBM, 8,192 global | ASAP7 proxy | 0.0726 s | 0.1453 s | 0.2905 s | 0.5810 s |
| DeepSeek wafer ROM, 8,192 | SKY130 proxy | 0.1085 s | 0.2169 s | 0.4339 s | 0.8677 s |
| DeepSeek wafer ROM, 8,192 | ASAP7 proxy | 0.0726 s | 0.1453 s | 0.2905 s | 0.5810 s |

The Qwen rows used the then-retained 7,568,097,280-work inventory. The corrected
execution now reports 7,568,101,376 useful tensor work units and measures
1.4785 s of HBM/SRAM tensor compute and 0.7375 s of ROM/HBM tensor compute on
ASAP7, within about 0.3% and 0.1% respectively of those analytical B=1 rows.
The analytical tensor lower bound is therefore validated; the larger total
TPOT comes from attention, vector, movement, memory stalls, and serialization.
The DeepSeek rows use a static 11,926,769,664-work contraction-volume projection
from the source-current 200K-capacity IR, not an executed model counter. At the
first Qwen decode step, 16,381,470,720 certified weight bytes plus 1,179,795,456
KV bytes impose a separate optimistic 43.06 ms floor on one 407.8 GB/s HBM
stack, assuming perfect service and reuse of one weight sweep across the batch.

If 100 microseconds is promoted from north star to a mandatory B=1 target, the
current baseline is not a near miss. At the characterized rate it would require
about 5.64 million Qwen tensor lanes on the SKY130 proxy or 3.78 million on the
ASAP7 proxy, versus 256 HBM lanes; ideal Qwen HBM weight service alone would
require 163.8 TB/s. DeepSeek would require about 8.89 million or 5.95 million
global lanes, versus 8,192. Preserving 100 microseconds per sequence at larger
batches multiplies the compute requirement by B. Therefore folding is
necessary, but a mandatory 100-microsecond SLO would require a fundamentally
wider spatial design and memory/fabric system rather than another scheduling
tweak.

The ROM timing inputs also have an unresolved structural mismatch. The Qwen
ROM capability declares 16 banks and the DeepSeek wafer capability declares
12,288 banks, while the cycle loader asks for `memory.rom.arrays`; neither
capability supplies that field, so both fall back to the cost table's eight
arrays at 32 bytes/cycle each. Banks cannot be silently relabeled as independent
arrays. The intended bank-to-port/array organization and its arbitration must
be represented in the capability, correlated in RTL, and characterized in each
process view before a ROM bandwidth or TPOT claim is credible.

The 2026-09-03 launch preflight observed 202.4 GB host RAM with 165.1 GB
available, 99.4 GB free filesystem space, and an RTX PRO 6000 with 97,887 MiB
total but only 12,353 MiB free. A later live check during the ROM-array rerun
showed about 129 GiB available RAM, 83 GiB free filesystem space, and swap still
fully occupied at 8 GiB. The DeepSeek
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

1. Keep ABI 3.0 frozen. Do not add ABI 3.1, durable-state, rollback, retry, or
   more correctness-qualified tooling.
2. Finish the simulations already running. Publish the Qwen exact-8K HBM token
   IDs/text/EOS result and HBM/ROM TTFT under ASAP7 and SKY130.
3. Run the same exact-8K Qwen functional workload on ROM. The direct acceptance
   check is exact token equality with `[18, 24, 16, 151645]`, legal decoding to
   `391<|im_end|>`, first-EOS stop, and no transaction after EOS.
4. Carry the now-modeled row-folded lane rule into the complete tensor RTL and
   retain the same cycles/counters. Then remove the remaining attention/vector
   padding, characterize memory service and every engine, and widen or
   replicate the datapath enough to address the multi-order-of-magnitude TPOT
   gap. The corrected four B=1 cells and diagnostic B=2/4/8 sweeps are retained
   as the new baseline.
5. Generate the remaining seven Qwen singleton oracles serially, then run real
   natural-chat, reasoning, agentic-tool, and stress prompts. Execute genuinely
   distinct B=2, B=4, and B=8 batches; the completed cloned-shape saturation
   sweep cannot substitute for them. For every lane publish output IDs, text,
   stop reason, TTFT, per-sequence TPOT, and aggregate tokens/s.
6. Use the completing DeepSeek P32 HBM repeat only as a short diagnostic. The
   production comparison remains one exact-200K wafer-ROM execution versus one
   exact-200K execution on exactly 32 HBM/SRAM chips with NVLink-class links.
   Both must publish full tokens/text and event-driven cycle timing.
7. Continue RTL integration through every required operator, memory service,
   communication primitive, argmax, token append, token-commit counter, and EOS
   path. RTL simulator wall time remains verification cost, not TPOT.
8. Replace assumed cycle-model parameters with separate SKY130 and ASAP7
   characterization as blocks close physically. Never scale SKY130 into ASAP7
   or commercial-node claims.

Each long simulation records its committed source, deployment, workload,
checkpoint, process view, batch, and output path so the number can be
reproduced. No additional release/checker ceremony is required. Terminated or
older-source attempts remain diagnostics and are not substituted for a
completed source-current run.

## 10. Bottom line

The architecture is no longer waiting for ABI design. ABI 3.0, the neutral IR,
all four compilation paths, and the functional simulator provide the correct
foundation. The remaining work is implementation closure and evidence: integrate
the RTL datapaths, execute the mandatory long workloads on the actual simulated
targets, verify their complete decoded outputs, and characterize the complete
systems on both required process views.
