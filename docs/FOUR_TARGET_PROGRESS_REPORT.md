# Four-target implementation progress report

**Report ID:** `TA-PROGRESS-4T-2026-09-04`

**Status date:** 2026-09-04

**Input baseline:** Qwen token-path branch through `586616a`, based on `main`
through `6633a3b`; this includes the fail-closed
DeepSeek exact-200K oracle and accelerator-pair checkers, the DeepSeek
phase-selected sparse-KV layout repair, the shared activation-liveness
allocator and physical 180-GB ROM-array capacity boundary, and refreshed
zero-`STATE` deployments, the correctness-qualified TPOT and RTL-bound
co-simulation evidence gates, the exact DeepSeek wafer multicast and its
integration into the real shipped-program RTL prefix, the
shipped-program Qwen prefix through all three real checkpoint-backed
layer-zero Q/K/V projections and query/key head RMSNorm, the exact full-shape
first DeepSeek HBM `HC_PRE` functional issue, the standalone 256-lane
row-folding mapper and exact Sinkhorn numeric tail, the bit-exact Qwen
host-simulator attention acceleration, the corrected HBM `HEAD_RMS_NORM`
head-count lowering, the target-tick-to-token binding in the TPOT gate, the
governed exact-8K official-chat Qwen workload and three-capture acceptance
gate, the governed create-once Qwen production-attempt launcher, the exact
DeepSeek ordered-product host acceleration, the recorded no-artifact outcomes
of the first DeepSeek ROM-array functional and cycle attempts, per-session
mutable memory and fail-closed dynamic batch waves, authenticated ABI 3.0
request-symbol descriptors, the exact DeepSeek `HC_PRE` RTL tile scheduler,
the exact Qwen ROM/HBM PC-32/35 KV appends and fixed-context-17 PC-38 GQA
arithmetic, and the first frozen-source exact-token Qwen HBM/SRAM accelerator
diagnostic.

**Role:** current narrative status and handoff report. Machine-readable result
artifacts and the [unified execution checklist](UNIFIED_EXECUTION_CHECKLIST.md)
remain authoritative when a copied count or status differs.

## 1. Executive status

There are exactly two highest-priority release outcomes, and they are ordered.
All compiler, RTL, physical-design, and simulator milestones below are enabling
evidence for these outcomes rather than substitutes for them.

| Priority release gate | Current status | Source-current acceptance evidence | Closure condition |
|---|---|---|---|
| 1. Correct output tokens | **open; first positive frozen-source diagnostic retained** | one Qwen exact-8K HBM/SRAM execution produced `[18, 24, 16, 151645]`, visible text `391`, and exact EOS behavior against the independent oracle; it is bound to captured Git tree `008bf765e212c061f930d5a2726563f7ddeba740`, not the current release source | freeze one current release snapshot, then make each required target execute the complete governed model and prompt, match every legal token ID and decoded text against the independent oracle, include and stop at the first official EOS when present or stop at exactly 256 tokens, and prove no post-EOS model transaction |
| 2. Desired TPOT | **blocked by Gate 1; otherwise not evaluable** | zero correctness-qualified TPOT points exist for B=1/2/4/8 on either process view | the same token-correct execution must retain raw architectural token-commit ticks and use a characterized SKY130 or ASAP7 timebase, then pass a frozen numerical SLO for that workload and batch point |

The 10,000-token/s or 100-microsecond-per-token figure remains an aspirational
north star, not a silently assumed pass threshold. None of the three governed
comparison contracts currently contains `execution.tpot_acceptance`; therefore
no result can honestly be labeled “desired TPOT achieved” until numerical SLO
rows are frozen. Host simulator speed, RTL simulator wall time, isolated block
cycles, and analytical rooflines do not close Gate 2.

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

The present boundary is therefore:

- compiler and deployment architecture: implemented and independently checked;
- full-model functional simulator: implemented, with prior short token evidence;
- full-shape DeepSeek HBM `HC_PRE` functional qualification: the first exact
  T=512 issue is bitwise closed, but it is one operator and produces no token;
- DeepSeek main sparse-attention phase layout: compiler and interacting-operator
  repair closed over prefill/decode, ratios 0/4/128, circular wrap, and absolute
  position 200,000; this is bounded synthetic/operator evidence and produces no
  checkpoint-backed token;
- production acceptance validators: implemented for the governed Qwen
  exact-8K official-chat workload, the DeepSeek exact-200K external oracle,
  and the final ROM/HBM accelerator pairs; all still reject the incomplete
  current evidence;
- correctness-qualified TPOT validator: implemented and fail-closed when token
  evidence, target-cycle traces, process identities, or numerical budgets are
  absent;
- RTL control plane and bounded arithmetic blocks: independently correlated;
  the row-folding mapper and Sinkhorn tail are standalone blocks and are not yet
  wired into a token-producing full-system path;
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
  dual-simulator qualified, but the missing projection/RMS/transcendental
  arithmetic prevents a complete `HC_PRE` or token claim;
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
| Functional execution | partial | the complete functional engine exists; one frozen-source Qwen HBM/SRAM run executed the exact 8K prompt end to end and matched all four oracle tokens through EOS; the first exact T=512 DeepSeek HBM `HC_PRE` issue matches an independent service on all 12,288 FP32 output words | the Qwen result predates current runtime changes and lacks its independent HBM-B/ROM peers; the `HC_PRE` result is an operator qualification, not a token |
| RTL 3.0 | partial | shipped control replay and bounded arithmetic pairs independently correlate; the shared prefix drives Qwen through query/key RoPE and DeepSeek ROM through wafer multicast; focused Qwen continuations execute PC-32/35 KV appends and fixed-context-17 PC-38 GQA; exact ROM/HBM `HC_PRE` tile scheduling, the standalone 256-lane mapper, exact Sinkhorn tail, MAC lane, shared correctly rounded exponential, and multicast transport have dual-simulator evidence | Qwen must generalize GQA through the governed 8K context and continue at PC 41 output projection; DeepSeek `HC_PRE` still lacks full projection/RMS plus CR32 sigmoid and complete stable-softmax integration; no RTL path reaches a token |
| Mandatory workloads | open | the Qwen exact-8K rendered official-chat prompt is frozen and reproducible; its authenticated external oracle and one frozen-source HBM/SRAM execution both produce `391` followed by EOS | a single current-release HBM-A/HBM-B/ROM triplet, Qwen natural chat/reasoning/agentic and genuine B=1/2/4/8 cells, and both DeepSeek exact-200K executions are absent; the retained DeepSeek oracle stops after eight tokens |
| SKY130 and ASAP7 | partial | several bounded blocks have process-specific reports | neither view characterizes a complete target; ASAP7 readiness has 15 fail-closed blockers |
| Governed comparison | partial | short historical ROM/HBM comparisons retain topology and counter evidence; `081161b` adds a source/process/batch-bound correctness-qualified TPOT schema and checker; `8080d8f` adds the explicit RTL-bound accelerated co-simulation tier; `cbaecf0` freezes the shared-datapath production plan and exact-execution promotion rule | no source-current mandatory-workload pair, production-simulation token record, target token-commit trace, frozen numerical TPOT budget, or complete same-view system cost exists |

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
  batched Gate-1 runs structurally possible; transactions within a wave remain
  lane-serial, engine co-issue and shared-resource timing are not implemented,
  and no B>1 full-model token or TPOT result exists.
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
  clean generic Yosys elaboration. The exponential and sigmoid units, stable
  softmax front end, full-shape scheduling, and PC-14 bridge integration remain
  open, so this still is not complete `HC_PRE` or a model-token result.
- Commits `17fbb27`, `874b48e`, and `ff5fcb8` add and qualify the exact
  DeepSeek `HC_PRE` tile scheduler. It admits ROM PC 15 descriptor 381 and HBM
  PC 14 descriptor 546, covers ROM T=1 and HBM T=512/T=320/T=1, and explicitly
  covers the exact-200K partition `390 * 512 + 320`. Icarus and Verilator agree
  on 688,188 emitted tiles and 11,346,434 checks; 181,605 backpressure cycles
  preserve stable metadata and counters, while all 18 malformed cases fail
  before work. Full projection MAC/RMS and CR32 sigmoid, exponential, and
  stable-softmax arithmetic are still missing, so this is scheduler evidence
  only and produces no token, EOS decision, architectural timing, or TPOT.
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

The immediate DeepSeek blockers are execution of the new fail-closed production
oracle through complete EOS-or-256, including its pre-run and completion
full-byte/input checks, followed by two genuine long-context accelerator
executions. The launcher and final pair checker are implemented and focused-test
complete, but neither the full oracle run nor either accelerator run has
occurred. Performance instrumentation and decoded weight caching make those
runs more tractable but do not reduce the workload or the required arithmetic.
The stale 129-token ROM-array rerun was stopped without a result after it had
served its resource-diagnosis purpose. Even a successful eight-token rerun
would not substitute for the exact-200K wafer-ROM or 32-node-HBM executions.

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
- The retained DeepSeek accelerator HBM and ROM artifacts each produced only
  `[13806, 345, 7472, 55560]` on a short prompt and matched the old four-token
  oracle prefix. Those legal IDs predate the `INDEX_SCORE` single-rounding fix,
  so they are regression clues rather than current decoding acceptance.
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

Commit `8a7160d` exposed one performance blocker without changing a schedule or
cycle total. Across the 253 Qwen decode matmuls, the old fixed-tile mapping
reports 7,568,097,280 useful work units and 445,151,444,992 issued units:
437,583,347,712 padded units, or 98.2999 percent. Commits `473d0fb` and
`5256f5c` now prove the active-row and deterministic folding coordinate rule in
standalone RTL, so the required control mapping is no longer unspecified. It
has not yet been integrated with 256 physical MAC lanes, accumulators, SRAM/HBM
ports, or the cycle model. The old padded cycle total therefore remains
diagnostic, while a new integrated cycle total remains absent.

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

The Qwen rows use the retained 7,568,097,280-work inventory. The DeepSeek rows
use a static 11,926,769,664-work contraction-volume projection from the
source-current 200K-capacity IR, not an executed model counter. At the first
Qwen decode step, 16,381,470,720 certified weight bytes plus 1,179,795,456 KV
bytes impose a separate optimistic 43.06 ms floor on one 407.8 GB/s HBM stack,
assuming perfect service and reuse of one weight sweep across the batch.

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

1. Keep ABI 3.0 frozen and retain the zero-`STATE`, live-buffer admission gates.
2. Freeze explicit workload/process/PVT/B/statistic TPOT SLO rows before fixing
   the production lane and memory organization. If 100 microseconds is a
   mandatory rather than aspirational target, replace the present 256-lane
   single-chip baseline with a quantitatively feasible spatial architecture;
   do not spend the full physical-closure effort on a baseline whose optimistic
   lower bound already fails the target by orders of magnitude.
3. Do not spend the exclusive high-memory host on another obsolete DeepSeek
   threshold rerun. The next DeepSeek functional execution must use the
   source-current sparse-layout, liveness, and ordered-product implementation
   and must be selected because it advances the exact-200K gate.
4. Preserve the successful frozen-source Qwen HBM/SRAM result without promoting
   it. Finish the request-symbol, engine-co-issue, shared-cycle replay, genuine
   B=1/2/4/8, and RTL-session prerequisites, then freeze one committed release
   snapshot before any final long capture.
5. From that one snapshot, rerun HBM A, launch independent HBM B and ROM, and
   run the strict W10 checker over all three. Then complete natural chat,
   reasoning, deterministic closed-loop agentic, stress, and genuine
   heterogeneous B=2/4/8 cells. Require per-lane exact tokens and independent
   EOS retirement; do not clone one prompt merely to increase B.
6. Execute the DeepSeek `--gate-b-production` external oracle when the required
   GPU, checkpoint I/O, and host-memory resources are available. Require both
   the pre-run full-byte hash and the completion identity rehash; do not promote
   the retained eight-token prefix.
7. Treat the exact-200K attention/KV phase-layout blocker as repaired at
   compiler and interacting-operator scope by `a877cfe`. Carry that repair into
   the next checkpoint-backed integrated run and require exact generated-token
   equality before closing Gate 1; the 30-case bounded matrix is not a token
   substitute. Carry the admitted 180-GB liveness placement with it and measure
   host-resident behavior afresh; the prior 1.2-TB-declaration OOM is not a
   result for the new deployment. Preserve the operation-derived feature invariant:
   `TRANSACTIONAL_STATE` in no production program and `INTEGRITY_RETRY` only
   for actual DeepSeek communication descriptors.
8. Integrate the proven active-row/folding mapper with the selected production
   tensor lanes without changing reduction association, generalize Qwen GQA
   beyond its fixed context-17 proof, and extend the RTL path from Qwen PC-41
   `TENSOR.MATMUL`, DeepSeek ROM PC-15 `VECTOR.MHC`, and DeepSeek HBM PC-14
   `VECTOR.MHC` through every required operator, memory service,
   communication primitive, argmax, token append, token-commit counter, and EOS
   path. Bind every accelerated full-system co-simulation engine bit-for-bit and
   cycle-for-cycle to synthesizable RTL; do not label that tier monolithic RTL.
9. Run short integrated token diagnostics on all four targets; then run exact
   200K accelerator execution on one DeepSeek ROM wafer and exactly 32 shared
   HBM/SRAM chips, publishing complete tokens, text, counters, topology, and
   source identities and passing the exact-200K accelerator-pair checker.
10. Only after each run is token-correct, derive its TPOT from its own raw
   token-commit ticks and characterized target timebase. For every B=1/2/4/8
   point, retain correct-token count, first divergence, stop reason, TTFT,
   per-step latency, steady-state per-sequence TPOT, and aggregate throughput
   from that same execution; keep analytical projections separate.
11. Complete separate SKY130 and ASAP7 full-system characterization and feed
   measured limits back into the cycle model before publishing the same-view
   ROM-versus-HBM comparison.

Every new long simulation must start from one frozen, committed source,
deployment, workload, oracle, topology, and output identity. The terminated
Qwen attempts, the successful pre-current-main HBM/SRAM run, and the stale
historical acceptance pair are retained only as diagnostic provenance and must
not be promoted or used to derive TPOT.

## 10. Bottom line

The architecture is no longer waiting for ABI design. ABI 3.0, the neutral IR,
all four compilation paths, and the functional simulator provide the correct
foundation. The remaining work is implementation closure and evidence: integrate
the RTL datapaths, execute the mandatory long workloads on the actual simulated
targets, verify their complete decoded outputs, and characterize the complete
systems on both required process views.
