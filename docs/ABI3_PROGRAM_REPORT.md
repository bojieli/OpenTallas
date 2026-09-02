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

The source-current pinned chat workload — rendered through the official
template and tokenized by the pinned tokenizer — is compiled from the neutral
IR into both current 75-instruction Qwen deployments, admitted by the
independent verifier, and executed entirely by the microsequencer and engines:
embedding, thirty-six layers, GQA attention, transactional KV state, vocabulary
projection, and **on-device argmax and token append**. Qwen ROM (`925351…`) and
HBM (`8e1185…`) each reproduce the same four-token oracle prefix:

```
(1654, 525, 2661, 1447)
```

The hardened records bind the exact deployment, checkpoint ranges, source
files, tokenizer artifacts, workload and oracle. A retained historical capture
extends the match to 24 tokens:

```
(1654, 525, 2661, 1447, 12, 3070, 29624, 220, 16, 334, 320, 1499,
 5776, 362, 8, 10901, 518, 3070, 15, 21, 25, 15, 15, 334)
```

That longer record predates the current deployment identities and hardened
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

### 2.2 Storage class is separable from the program

The property the comparison rests on has two halves, and only the first is
proven. This section reports the first and is explicit about the second.

**Retained proof: within one backend, storage class changed nothing else.** A
historical equivalence build lowered the same graph twice through the ROM
backend, varying only where the immutable weights lived:

| | Qwen3-8B | DeepSeek-V4-Flash |
|---|---|---|
| Instruction bytes identical | yes | yes |
| Descriptors | 210 each | 2,206 each |
| Differing | 17 | 225 |
| Differing by type | all `MEMORY_OBJECT` | all `MEMORY_OBJECT` |
| Transitions | all ROM→HBM | all ROM→HBM |
| **Differing beyond storage class** | **0** | **0** |

Not one operand view, numeric profile, schedule or operator differed in that
artifact. It predates the current source-lock schema and is not a current
rebuild.

**Not proven: that the two product backends emit the same program.** The table
above varies storage class inside one equivalence backend. The current shipped
Qwen programs each contain 75 instructions, but ROM emits 239 descriptors and
HBM emits 218. The separate equivalence-only build emits 31 instructions and
210 descriptors on both storage classes; it is not either shipped program.

Until product lowering agrees, a measured gap between the two targets is partly
a measurement of the compiler rather than of memory technology, which is
precisely the failure this property exists to exclude. Tracked as OI-19. The
equivalence build must also be regenerated under the current source and
provenance rules before it can support a release-current claim.

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

Three of the four governed restart lanes are now source-current and passing:
Qwen HBM (`8e1185…`), Qwen ROM (`925351…`) and DeepSeek ROM (`fa9077…`). Each
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
bytes in 143,255,560 logical stored payload bytes. Those are sparse simulator
checkpoint quantities, not physical storage. The current DeepSeek HBM rerun is
the sole remaining W6.6 lane and is executing serially because it is the
high-memory case. Its uninterrupted comparator has passed all three generated
tokens in 3,961.6 seconds. The interrupted process is now executing the
32-token prefill without an observed error; checkpoint at token two, fresh
resume, STATE-erased and STATE-only controls, aggregate artifact assembly, and
the independent 27-guard/source/deployment/PID/counter audit remain. The
checklist stays at 82/94 until that retained artifact passes.

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
at whole-transaction depth. Each Qwen case retires 2,105 instructions with 693
engine issues and 2,143 resolved operand views. DeepSeek ROM retires 18,491 /
11,714 instructions on prefill / decode, with 6,852 / 3,600 issues and 20,499 /
10,428 views; DeepSeek HBM retires 18,607 / 11,229 instructions, with 7,376 /
4,454 issues and 21,114 / 11,718 views. Every case ends in COMPLETE rather than
at a work bound, identically on Icarus 11.0 and Verilator 5.050. **The artifact's `correlated_cases` field remains the
authority**, since it moves whenever a sequencer bound or shipped image moves.
At commit `518260f` it did not include DeepSeek: the RTL trapped after eight
retirements on `A3_STATE_SLOTS`, a bound nothing then expressed at admission.

The separate source-current ROM read-service campaign reports `status: pass` <!-- figure: "pass" src="results/rtl/rom_service_campaign.json#status" name="ROM service campaign status, program report" -->
for nominal and degraded executed Qwen streams and plan-derived DeepSeek
boundary coverage on Icarus and Verilator. It correlates object/shard lookup,
addressing, masking, repair translation, refusal classes, sense beats, operand
alignment, and accounting. It contains no ROM array and establishes no cell
area, read energy, sense margin, retention, defect, or macro-timing evidence.

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
  without EOS; the matched ROM lane
  completed its 192-token comparison horizon and matched the oracle throughout.
  DeepSeek's 200,000-token rung remains reference-oracle GPU evidence: the
  governed accelerator context gate currently reaches only 35 tokens, below
  both sparse-attention thresholds.
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
- **No engine arithmetic under the sequencer.** Both control-plane campaigns
  bind every engine to a recording no-op; the four datapaths that are correlated
  arithmetically are correlated separately and are not wired to the sequencer.
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
- **The implementation identity did not identify the implementation.** A7 says
  two runs of one identity are bit-identical. Thread count was not in it, and at
  Qwen shapes 1, 4 and 16 threads give three different results. Two runs could
  have declared the same identity and disagreed.
- **The storage-class proof was narrower than the sentence built on it.** It
  varies storage class within one backend; the comparison needs the two backends
  to emit the same program, and they do not (§2.2).

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
companion republishes those marker counts. Its 53 `OI-*` headings are a durable
findings log, not a count of currently open defects; many are explicitly closed
and retained to record what invalidated earlier evidence. OI-15's per-token
loop, for example, is closed by A13 block extents. OI-4's lack of a governed
stochastic sampling contract remains deliberate: inventing an RNG merely to
close it would make future results unreproducible.
