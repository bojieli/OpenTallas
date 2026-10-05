# ABI 3.0 program report

**Report ID:** TA-ABI3-REPORT-1
**Date:** 2026-09-02
**Baseline:** `main` at the commit this document is committed with
**Generated companion:** [`PROGRAM_STATUS.md`](PROGRAM_STATUS.md) is regenerated
from artifacts on disk; this document is the narrative and the judgement.

## 1. What this program set out to fix

The previous structure had four parallel top-level owners, no shared IR and no
shared ABI. It produced four result sets that could not be compared with each
other, which is the one thing a ROM-versus-HBM study exists to do. Reorganising
the owners would not have fixed that, because the incomparability was structural
rather than procedural.

So the fix is structural. There is now one wire format, one deployment builder,
one independent verifier, one functional device, one counter registry and one
backend-neutral IR. **A target is a set of descriptors, not a code path.** Every
claim below rests on that.

## 2. What is established

### 2.1 The Qwen accelerator produces correct tokens

The last retained source-locked pinned chat workload — rendered through the
official template and tokenized by the pinned tokenizer — was compiled from the
neutral IR into both 75-instruction Qwen deployments, admitted by the
independent verifier, and executed entirely by the microsequencer and engines:
embedding, thirty-six layers, GQA attention, mutable KV buffers, vocabulary
projection, and **on-device argmax and token append**. Qwen ROM (`925351…`) and
HBM (`8e1185…`) each reproduce the same four-token oracle prefix:

```
(1654, 525, 2661, 1447)
```

The hardened records bind the exact deployment, checkpoint ranges, source
files, tokenizer artifacts, workload and oracle. They bind the pre-W10 source
map: the later 8,256-position and association-manifest tranche changes governed
files, so these records remain prior-head milestone evidence rather than a
current-source claim for the new head. A retained historical capture extends
the match to 24 tokens:

```
(1654, 525, 2661, 1447, 12, 3070, 29624, 220, 16, 334, 320, 1499,
 5776, 362, 8, 10901, 518, 3070, 15, 21, 25, 15, 15, 334)
```

That longer record predates those four-token deployment identities and hardened
source-map schema. It remains milestone evidence, not a source-current
24-token claim.

Host software tokenizes, stages a bounded input span, submits real 128-byte ABI
records, and reads token IDs back. It does not sequence device operations,
select a token, or supply an activation.

Getting here took six lowering corrections and one amendment. Two of the
lowering bugs are worth recording because no single component could have
revealed either: the band's loop-carried residual used two buffers, so
thirty-six layers collapsed into one layer applied thirty-six times; and state
reads went to the *committed* image, which is empty mid-transaction, so
attention was attending to a context that did not yet contain the current
tokens.

### 2.2 The governed storage-and-placement transition is separable within one backend

The property the comparison rests on has two halves, and only the first is
proven. This section reports the first and is explicit about the second.

**Current-source proof: within one backend, only the governed storage and
placement fields change.** The v2 equivalence builder lowers each current
neutral graph twice through the ROM product backend, once with immutable
weights in ROM and once with them in HBM. ROM-local bank addresses are not
valid flat-HBM addresses, so every comparison-HBM object must use the ABI's
unplaced sentinel (`bank_or_tile = NO_NODE`, `base_address = 0`). The proof
normalizes exactly that coupled transition plus the pre-existing explicit
`integrity_mode` exception; it permits no other descriptor-header or payload
change:

| | Qwen3-8B | DeepSeek-V4-Flash |
|---|---:|---:|
| Instructions, each build | 75 | 1,171 | <!-- figure: 75 src="results/abi3/storage_class_equivalence_qwen3.json#instruction_count.rom" name="Qwen v2 equivalence instructions" --> <!-- figure: 1171 src="results/abi3/storage_class_equivalence_deepseek_v4.json#instruction_count.rom" name="DeepSeek v2 equivalence instructions" -->
| Descriptors, each build | 239 | 3,403 | <!-- figure: 239 src="results/abi3/storage_class_equivalence_qwen3.json#descriptor_count.rom" name="Qwen v2 equivalence descriptors" --> <!-- figure: 3403 src="results/abi3/storage_class_equivalence_deepseek_v4.json#descriptor_count.rom" name="DeepSeek v2 equivalence descriptors" -->
| Differing descriptors | 18 | 318 | <!-- figure: 18 src="results/abi3/storage_class_equivalence_qwen3.json#differing_descriptor_count" name="Qwen v2 differing descriptors" --> <!-- figure: 318 src="results/abi3/storage_class_equivalence_deepseek_v4.json#differing_descriptor_count" name="DeepSeek v2 differing descriptors" -->
| ROM-local placement → HBM unplaced | 16 | 312 | <!-- figure: 16 src="results/abi3/storage_class_equivalence_qwen3.json#placement_transitions.rom_placement_to_hbm_unplaced" name="Qwen v2 placed to unplaced transitions" --> <!-- figure: 312 src="results/abi3/storage_class_equivalence_deepseek_v4.json#placement_transitions.rom_placement_to_hbm_unplaced" name="DeepSeek v2 placed to unplaced transitions" -->
| Already-unplaced ROM → HBM unplaced | 2 | 6 | <!-- figure: 2 src="results/abi3/storage_class_equivalence_qwen3.json#placement_transitions.already_unplaced_to_hbm_unplaced" name="Qwen v2 already-unplaced transitions" --> <!-- figure: 6 src="results/abi3/storage_class_equivalence_deepseek_v4.json#placement_transitions.already_unplaced_to_hbm_unplaced" name="DeepSeek v2 already-unplaced transitions" -->
| Differing by type | all `MEMORY_OBJECT` | all `MEMORY_OBJECT` |
| Storage transition | all ROM→HBM | all ROM→HBM |
| **Outside the permitted transition** | **0** | **0** |

Both generated deployments admit and each certificate reports `holds: true`.
Instruction bodies, decoded instructions, object sources, entrypoints and
required features are identical; the only program-header differences are the
two derived deployment/descriptor-table digests. Neither run exercised a
model: these are current static build proofs, not token-execution evidence.

**Not proven: that the two product backends emit the same program.** The table
above varies storage and placement inside one equivalence backend. The current
shipped Qwen programs each contain 75 instructions, but ROM emits 239
descriptors and HBM emits 218. The v2 equivalence pair emits 75 instructions
and 239 descriptors on both sides; its HBM-labelled member is the ROM backend's
comparison build, not the shipped HBM-backend program.

Until product lowering agrees, a measured gap between the two targets is partly
a measurement of the compiler rather than of memory technology, which is
precisely the failure this property exists to exclude. Tracked as OI-19. The
current v2 certificates close the stale-proof problem, but not this
cross-product-backend comparability gap.

### 2.3 Loop compression

One Qwen forward step is 75 instructions. The same step under ABI 2.5 was
924,386 flat commands.

The instruction count was never the whole story, though, and it is worth saying
how that was nearly missed. An early lowering wrapped every operation in its own
per-token loop: the program looked compressed at 69 instructions while a
93-token prefill issued about 63,600 engine dispatches and retired 11,256,539
units of work — the ABI 2.5 failure in different clothes, one dispatch per token
rather than one command per tile.

The cause was a gap in the ABI, not in the backend. A tensor view states static
extents, so a 512-token block over a 93-token span could not express its
partial final iteration, and a backend that wanted to stay correct had no choice
but to emit one dispatch per token. Amendment A13 states the resolved extent
normatively. With it: about 700 dispatches and 22,715 retired work.

### 2.4 Zero-copy weights

No weight image is written anywhere. A memory object references authenticated
byte ranges of the locked checkpoint, and tiling is expressed by view strides.
The deployment directories contain only manifests, programs, and descriptors;
checkpoint bytes stay external and authenticated. Exact serialized bundle size
is not a retained program claim because no committed artifact publishes that
aggregate. Twelve tensors across three layers were read back through the device
at their placement offsets and matched the checkpoint byte for byte.

### 2.5 DeepSeek-V4-Flash executes

The 156 GB released checkpoint streams layer by layer through a GPU shared with
other tenants at 0.85–1.19 s per token and a 0.39 GiB peak device footprint. The
chat workload runs to a real EOS in 333 tokens and reaches the correct answer;
the agent workload emits a well-formed tool call. Both agree completely with the
vendor's own temperature-zero argmax and reproduce byte-identically across
processes.

The two current accelerator deployments also execute the governed 32-token
prefix through one prefill and three decode transactions. ROM (`fa9077…`) and
the 32-node HBM cluster (`294319…`) both produce
`[13806, 345, 7472, 55560]`, matching the external oracle at all four positions
and each other. These hardened captures bind the exact deployment, checkpoint
content, source files, workload, tokenizer and oracle. They establish the
current short correctness spine; they do not extend the accelerator claim to
the longer reference-only EOS or agentic runs.

### 2.6 Fail-closed behaviour

Against the real deployment, eight cases: body bit flip, header bit flip,
descriptor bit flip, illegal opcode, truncated program and missing terminal
completion are all refused at admission; a mid-transaction fault leaves the
committed cursor and generation exactly where they were and leaves no prepared
state open. All eight refused.

### 2.7 Checkpoint/restart exactness

All four governed restart lanes passed against their retained prior-head source
map: Qwen HBM
(`8e1185…`), Qwen ROM (`925351…`), DeepSeek ROM (`fa9077…`) and DeepSeek HBM
(`a72c87…`). Each
runs a three-token uninterrupted baseline, interrupts another process after two
tokens, and reproduces the final token in a fresh process loaded only from the
checkpoint. Tokens, retired work, aggregate counters and all per-node counters
match exactly. STATE erasure changes the resumed token, while the complementary
STATE-only checkpoint still matches and is reported separately rather than
used as a pass gate.

Every phase and control is a distinct process bound to the same deployment,
implementation, node count and complete 288-file source map over `compiler/`,
`runtime/` and the restart driver, digest `ee08b43d…`; all 27 guards pass. The
current DeepSeek ROM checkpoint represents 1,078,248,644,744 logical mutable
bytes in 143,255,560 logical stored payload bytes. The 32-node DeepSeek HBM
checkpoint represents 2,447,390,804,224 logical mutable bytes in 5,136,187,520
logical stored payload bytes across 8,992 writable objects. It writes in 24.53
seconds and restores normally in 99.724 seconds. Those are sparse simulator
checkpoint quantities, not physical storage or performance evidence. The HBM
baseline and fresh resume both produce `[13806, 345, 7472]`; the STATE-erased
negative produces `[13806, 345, 7249]` and diverges at index two, while the
reported-only state-only control matches. The complete 2:56:39 campaign and
independent artifact audit pass source, deployment, five-PID, exactness,
all-32-node counter and 27-guard checks. The four-artifact source-current
regression also passed at that head. W6.6 is closed, taking the checklist to
83/94. The later W10 compiler and runtime changes intentionally make all four
records non-current for the new head; refreshing them is an explicit remaining
task, not an implied extension of their evidence horizon.

This is a 93-token Qwen / 32-token DeepSeek, 2+1 generated-token functional
restart result. It is not long-context, performance, RTL, physical, silicon or
committed-durability evidence; OI-23 remains in force.

### 2.8 RTL and physical

RTL 3.0 correlates 53 programs over 65 cases, 185 engine-issue events, 460
resolved operand views and 11 traps field-for-field against the functional
device on two independent simulators, with 17 negative cases
(`results/rtl/abi3_campaign.json`). Those are programs built for the campaign.
Run on the **programs this repository actually ships**
(`results/rtl/abi3_deployment_campaign.json`), all four deployments — Qwen3-8B
ROM single chip, Qwen3-8B HBM single chip, DeepSeek-V4-Flash ROM wafer, and
DeepSeek-V4-Flash HBM 32-node cluster — correlate exactly on both entrypoints
at whole-transaction depth. Each Qwen case retires 2,104 instructions with 691
engine issues and 2,143 resolved operand views. DeepSeek ROM retires 19,999 /
12,929 instructions on prefill / decode, with 7,866 / 4,490 issues and 23,395 /
13,221 views; DeepSeek HBM retires 20,048 / 12,379 instructions, with 8,388 /
5,342 issues and 24,010 / 14,511 views. Every case ends in COMPLETE rather than
at a work bound, identically on Icarus 11.0 and Verilator 5.050. **The artifact's `correlated_cases` field remains the
authority**, since it moves whenever a sequencer bound or shipped image moves.
At commit `518260f` it did not include DeepSeek: the RTL trapped after eight
retirements on `A3_STATE_SLOTS`, a bound nothing then expressed at admission.

The separate retained ROM read-service campaign reports `status: pass` <!-- figure: "pass" src="results/rtl/rom_service_campaign.json#status" name="ROM service campaign status, program report" -->
for nominal and degraded executed Qwen streams and plan-derived DeepSeek
boundary coverage on Icarus and Verilator. It correlates object/shard lookup,
addressing, masking, repair translation, refusal classes, sense beats, operand
alignment, and accounting. It contains no ROM array and establishes no cell
area, read energy, sense margin, retention, defect, or macro-timing evidence.

A third, source-bound shipped-prefix campaign is the current narrow exception
to the control campaign's recording-no-op boundary. Across the four decode
images, it executes 6 FP32 `DMA.GATHER`, 4 BF16 `TENSOR.EMBED_LOOKUP`, 2 Qwen
BF16 `VECTOR.RMS_NORM`, and 2 DeepSeek stride-zero BF16 `DMA.TRANSFER`
operations. Icarus and Verilator each compare 58,368 exact words through 52
resolved views with 124,189 checks, while authenticating four selected 8 KiB
embedding rows and two selected 8 KiB RMS gain ranges. It next traps precisely
at Qwen `TENSOR.MATMUL` PC 11, DeepSeek ROM `LINK.MULTICAST` PC 13, or DeepSeek
HBM `VECTOR.MHC` PC 14. This is a data-bearing decode prefix, not a whole
transaction, model token, EOS, timing, or performance result.

Individual retained block cases in SKY130 HD at 130 nm and predictive ASAP7 at
7 nm complete synthesis, static timing and place-and-route; these are not two
matched, complete target implementations. The archived ASAP7 case was
reproduced bit-for-bit. **The routed blocks comprise ABI 2.5 engines, three ABI
3.0 datapaths in SKY130, and numeric probes.** The fourth ABI 3.0 datapath, the
MAC lane, is pre-layout/unrouted and did not meet its 60 ns constraint. The ABI
3.0 microsequencer/control plane has not been synthesised or routed. A separate ROM read-service
addressing/control proxy has been routed in IHP SG13G2, but it contains no ROM
array and is not full-target or ASAP7 evidence. A physical number resting on this
RTL may be presented as the cost of hardware that runs exactly the deployments
the deployment campaign records correlating — no others.

## 3. What is not established

- **Mandatory-context accelerator coverage is incomplete.** The Qwen HBM lane
  did execute the 8,000-token prompt, but diverged from the oracle at generated
  token 137 and failed at its historical context boundary after token 193
  without EOS. That capacity cause is repaired in current source: the adapter,
  neutral IR, KV resources, RoPE, workload validation and ROM capability now
  share 8,256 positions, while HBM retains its 262,144-position endpoint. Both
  products use 512-row blocks; the ROM allocator covers the padded 8,704-row
  final block, and fresh temporary one-token HBM/ROM diagnostics admit, match
  the oracle and record byte-identical executed-shape manifests. The frozen
  natural terminal rule is first official EOS or exactly 256 oracle-identical
  generated tokens, enforced by the producer and an independent two-record
  validator. The matched historical ROM lane completed its 192-token comparison
  horizon and matched the oracle throughout, but neither historical record is
  current-source acceptance. The stress lane likewise remains open: its old HBM
  record diverges at token two, and no retained source-current HBM/ROM 32-token
  pair has passed the new same-association gate.
  A replacement natural capture A was attempted from a later frozen identity,
  observed healthy for at least 2:28:07 while still in prefill, and then
  terminated with no result JSON or timing footer. It establishes no token,
  acceptance verdict, exact wall time, peak RSS, TPOT, or resource headroom; a
  fresh durable capture A and independent B remain open.
  DeepSeek's 200,000-token rung remains reference-oracle GPU evidence: the
  governed accelerator context gate currently reaches only 35 tokens, below
  both sparse-attention thresholds. The exact-200K accelerator-pair checker is
  implemented and covered by 26 focused tests, but no production ROM-wafer or
  exactly-32-node HBM record exists for it to accept.
- **Every-design reasoning and agentic coverage is incomplete.** Retained Qwen
  reasoning and closed-loop agentic captures exercise the HBM backend only.
  Qwen ROM lacks both cells, and neither DeepSeek accelerator backend has a
  reasoning or agentic capture. W13.4 owns these six missing cells.
- **No characterized DeepSeek performance comparison yet.** The governed
  functional ROM-versus-HBM comparison now exists: both DeepSeek targets execute one
  prefill plus three decode transactions and produce
  `[13806, 345, 7472, 55560]`, identical to the oracle and to each other.
  `results/abi3/comparison_deepseek_rom_vs_hbm.json` records that four-token
  common prefix, no assumptions, and the one-wafer-versus-32-node topology
  difference. Its own claim boundary says `timing_or_performance: false`; no
  characterized ROM/HBM performance pair follows from it. A separate governed
  HBM-only P32 prefill cycle artifact now exists, but it depends predominantly
  on assumed machine values and cannot supply that comparison.
- **No correctness-qualified executed TPOT sweep yet.** Correct output tokens
  are the first acceptance gate and desired TPOT is the second. Existing
  multi-batch rate tables are analytical projections and generate no model
  tokens. A future TPOT point counts only when the same execution records
  oracle-identical legal IDs and decoded text, correct first-EOS-or-cap behavior,
  no post-EOS step, TTFT, raw decode-step latencies, and complete execution and
  implementation identities.
- **No silicon, no full-chip place-and-route, no foundry signoff DRC or LVS.**
  The physical evidence covers representative blocks.
- **The ROM read-service pass is a bounded control/addressing claim.** The
  correlated block contains no ROM array or macro and therefore supplies no
  cell area, read energy, sense margin, retention, wordline/bitline timing, or
  defect evidence. Column repair is refused, the resolved-view-to-byte-range
  walk is outside the block, full decode traffic is not replayed, and the
  DeepSeek request set remains plan-derived rather than executed.
- **RTL coverage of the shipped deployments is a list, and it is the
  artifact's.** `results/rtl/abi3_deployment_campaign.json` →
  `correlated_cases` names the deployments the microsequencer RTL is known to
  reproduce. The current list contains both Qwen3-8B builds, the
  DeepSeek-V4-Flash ROM wafer build, and the DeepSeek-V4-Flash HBM 32-node
  cluster build. At commit `518260f` it contained only the
  Qwen builds: DeepSeek trapped after eight retirements on a sequencer bound
  (`A3_STATE_SLOTS`) that nothing expressed at admission, so a shipped
  deployment passed every admission gate and was refused in hardware instead
  (checklist W8.8/W8.9).
- **No complete engine arithmetic under the sequencer.** Both control-plane
  campaigns bind every engine to a recording no-op, and the standalone bounded
  datapaths remain separately correlated. The shipped-prefix campaign is a
  narrow data-bearing exception through gather, embedding, Qwen RMSNorm, and
  DeepSeek transfer. Every later operator and the complete token path remain
  unwired.
- **The governed real-deployment cycle result is schedule/counter evidence, not
  token or performance evidence.**
  `results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json` executes the
  shipped 32-node HBM deployment for one 32-token prefill, exits `SUCCESS` /
  `NONE`, agrees with an independently rerun functional device on all **66** <!-- figure: 66 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#functional_agreement.counters_compared" name="DeepSeek HBM cycle counters reconciled, report" -->
  compared architectural counters, and completes its **447** <!-- figure: 447 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#schedule_audit.operators_checked" name="DeepSeek HBM cycle operators audited, report" -->-operator schedule
  audit with no findings or contract gaps. Its **244,691,019,251** <!-- figure: 244,691,019,251 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#timing.total_cycles" name="DeepSeek HBM modeled prefill cycles, report" -->-cycle result is
  governed by **124** <!-- figure: 124 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#provenance.counts.assumed" name="DeepSeek HBM assumed cycle parameters, report" --> assumed and **5** <!-- figure: 5 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#provenance.counts.characterized" name="DeepSeek HBM characterized cycle parameters, report" --> characterized parameters, so the artifact
  class is `assumed` and the reported **244.691** <!-- figure: 244.691 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#timing.seconds" name="DeepSeek HBM modeled prefill seconds, report" --> seconds is not a performance
  claim. The cycle request does not stage the governed prompt payload or compare
  its produced token with the external oracle, and the artifact binds the
  deployment, capability and cost table but carries no full Python source map.

## 4. Judgements worth recording

**Two numeric contracts, not one.** The exact sequential-K kernel measures
0.353 GMAC/s, which is 47.6 hours for one 8,000-token prefill — the mandatory
workload could not have run at all. `SEQUENTIAL_ASCENDING` was never the
hardware contract anyway: the accelerator being designed contracts a
4,096-element reduction on a lane array, and a strictly sequential 4,096-step
dependency chain is the one thing such hardware provably does not do. So the
sequential contract stays as the qualification oracle and a blocked contract
whose association is fixed by a recorded implementation identity does execution.
The gap is measured, not asserted: after the single BF16 output rounding,
0.012–0.089 % of elements differ by 1–5 ULP, and vocabulary argmax changes at
both heads: **zero**.

**The 200,000-token contract is a memory-and-code problem, not a throughput
one.** The wall is the mHC hyper-connection, not the sparse indexer:
`hc_post`'s binary32 intermediate is 48.8 GiB at that context, allocated twice
per layer across 43 layers, and the indexer's unchunked score tensor would be
2.33 TiB, while persistent KV state is 2.32 GiB. A 200,000-token prefill needs a
chunked rewrite of the vendor prefill path on any GPU. Chunked, it is about 58
seconds. Also: 200,000 is not an admissible deployment context, because it must
be a whole number of 128-token sliding windows; 200,064 is the nearest.

**A vendor kernel is silently wrong on this GPU.** The released TileLang
`fp4_gemm` gives a maximum absolute error of 6.52 against a signal of mean
magnitude 1.28 on sm_120, confirmed against two mutually independent references
that agree with each other to half a bfloat16 ulp. Because the routed experts
are most of the model it does not crash — it produces fluent, on-topic,
semantically empty text. Anything in this program that runs routed experts
through TileLang FP4 on this architecture is wrong today unless it repeats the
check.

## 5. How the errors were found

Almost every defect in this program was found by one component meeting another's
expectations, not by inspection of either alone. That is worth recording because
it is the argument for the structure.

- Running **two models against one schema** found that the exporters disagreed
  on token type, that the rotary coefficient table was undeclarable by either,
  and that `KV_APPEND` meant different things to each.
- Running **RTL against the functional device** found that the retired-work
  bound under-counted `LOOP_SETUP` in three independent implementations, that
  staged commits were capacity-checked against the wrong quantity, and that
  control instructions could not publish events.
- Running an **independent conformance suite** found that a `MATMUL` could name
  a ROM object as its write destination, and that a bundle could be admitted
  with no on-device selection at all.
- Running the **cycle model** found that operators carried no tile mapping and
  that every object presented at address zero.
- Running a **fail-closed campaign against the real deployment** found that an
  abort left prepared state open — a case the fixture cannot produce, because it
  prepares one resource where the real graph prepares thirty-six.

Three defects, though, were found by asking what a *field in a report* actually
promised, and they are the ones a reader should be most suspicious of, because
nothing was failing when they were found:

- **`status: pass` meant "the script finished".** The campaign runner marked a
  run as passing whenever it neither crashed nor emitted an illegitimate token.
  Nothing compared the tokens to anything. This program has already seen a
  released vendor kernel decode fluent, well-formed, semantically empty text and
  pass every liveness check it had, so an unchecked decode reported as `pass` is
  the exact shape of a miss. `pass` is now reserved for a run compared against
  the oracle and matching; a run with no reference is `executed_unverified`.
- **The implementation identity gap is repaired in the producer, not yet in a
  retained long pair.** A7 says two runs of one identity are bit-identical.
  Thread count was added after Qwen measurements at 1, 4 and 16 threads produced
  three different results. The W10 preflight then found and repaired the
  remaining gap: each run now publishes a canonical counted manifest of the
  implementation plus every executed activation/weight/output shape, and both
  product schedules use 512-row blocks. The independent gate requires two
  nonempty manifests to be byte-identical. Short HBM/ROM diagnostics satisfy
  it; the mandatory 8K natural and stress captures have not yet run under it.
- **The storage-and-placement proof is narrower than the sentence once built on
  it.** It varies governed storage and placement within one backend; the
  comparison needs the two product backends to emit the same program, and they
  do not (§2.2).

None of the three would have produced a failing test. All three would have
produced a confident number in a report.

One error went the other way and is worth the same candour: chasing a token
divergence, an activation was read back *after* a transaction and found wrong by
a factor of a thousand. It was not wrong. Arena slots are reused, and the tensor
being read shares a slot with thirty-six others. The reading produced a
confident, detailed and completely wrong diagnosis in about ninety seconds. The
bisection tool now samples in flight, at the moment the producing engine writes.

## 6. Open issues

The authoritative status is the top-level marker table in
[`UNIFIED_EXECUTION_CHECKLIST.md`](UNIFIED_EXECUTION_CHECKLIST.md); the generated
companion republishes those marker counts. Its 54 `OI-*` headings are a durable
findings log, not a count of currently open defects; many are explicitly closed
and retained to record what invalidated earlier evidence. OI-15's per-token
loop, for example, is closed by A13 block extents. OI-4's lack of a governed
stochastic sampling contract remains deliberate: inventing an RNG merely to
close it would make future results unreproducible.
