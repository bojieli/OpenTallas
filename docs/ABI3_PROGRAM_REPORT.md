# ABI 3.0 program report

**Report ID:** TA-ABI3-REPORT-1
**Date:** 2026-08-29
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

The pinned chat workload — rendered through the official template, tokenized by
the pinned tokenizer — is compiled from the neutral IR into a 75-instruction
ABI 3.0 deployment, admitted by the independent verifier, and executed entirely
by the microsequencer and engines: embedding, thirty-six layers, GQA attention,
transactional KV state, vocabulary projection, and **on-device argmax and token
append**. Its output is token-identical to a reference the accelerator did not
compute, over 24 tokens, with no divergence at any index:

```
(1654, 525, 2661, 1447, 12, 3070, 29624, 220, 16, 334, 320, 1499,
 5776, 362, 8, 10901, 518, 3070, 15, 21, 25, 15, 15, 334)
```

Three independent runs agree, two of them from a different process than the one
that built the deployment.

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

### 2.2 ROM and HBM differ only in storage class

This is the property the comparison rests on, and it is now checked
mechanically rather than argued:

| | Qwen3-8B | DeepSeek-V4-Flash |
|---|---|---|
| Instruction bytes identical | yes | yes |
| Descriptors | 210 each | 2,206 each |
| Differing | 17 | 225 |
| Differing by type | all `MEMORY_OBJECT` | all `MEMORY_OBJECT` |
| Transitions | all ROM→HBM | all ROM→HBM |
| **Differing beyond storage class** | **0** | **0** |

Not one operand view, numeric profile, schedule or operator differs. Had any
differed, a measured gap between the two targets would have been
unattributable — the study would have been measuring the compiler rather than
the memory technology.

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
The Qwen deployment bundle is 223 KB addressing 16.38 GB; the DeepSeek bundle is
30.9 MB addressing 156.0 GB. Twelve tensors across three layers were read back
through the device at their placement offsets and matched the checkpoint
byte for byte.

### 2.5 DeepSeek-V4-Flash executes

The 156 GB released checkpoint streams layer by layer through a GPU shared with
other tenants at 0.85–1.19 s per token and a 0.39 GiB peak device footprint. The
chat workload runs to a real EOS in 333 tokens and reaches the correct answer;
the agent workload emits a well-formed tool call. Both agree completely with the
vendor's own temperature-zero argmax and reproduce byte-identically across
processes.

### 2.6 Fail-closed behaviour

Against the real deployment, eight cases: body bit flip, header bit flip,
descriptor bit flip, illegal opcode, truncated program and missing terminal
completion are all refused at admission; a mid-transaction fault leaves the
committed cursor and generation exactly where they were and leaves no prepared
state open. All eight refused.

### 2.7 RTL and physical

RTL 3.0 correlates 30 programs, 99 engine-issue events and 12 traps
field-for-field against the functional device on two independent simulators,
with 17 negative cases. Both physical views — SKY130 HD at 130 nm and ASAP7 at
7 nm — complete synthesis, multi-corner static timing and full place-and-route
with zero detailed-route DRC and zero antenna violations. The archived ASAP7
case was reproduced bit-for-bit.

## 3. What is not established

- **No accelerator result at the mandatory contexts.** The Qwen 8,000-token
  campaign and the DeepSeek long-context campaign have not run on the
  accelerator. The reference oracle has reached 8,000 tokens for both models.
- **No comparison table.** A performance comparison may not precede correct
  end-to-end execution on both sides of the pair, and the ROM target has not yet
  produced tokens.
- **No silicon, no full-chip place-and-route, no foundry signoff DRC or LVS.**
  The physical evidence covers representative blocks.
- **No governed cycle result on a real model.** The cycle model agrees with the
  functional device on every architectural counter, but its machine parameters
  are overwhelmingly `assumed`, and every report says so at the top level.

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

One error went the other way and is worth the same candour: chasing a token
divergence, an activation was read back *after* a transaction and found wrong by
a factor of a thousand. It was not wrong. Arena slots are reused, and the tensor
being read shares a slot with thirty-six others. The reading produced a
confident, detailed and completely wrong diagnosis in about ninety seconds. The
bisection tool now samples in flight, at the moment the producing engine writes.

## 6. Open issues

Fifteen are tracked in [`UNIFIED_EXECUTION_CHECKLIST.md`](UNIFIED_EXECUTION_CHECKLIST.md).
The two that gate results are OI-15, where every operation is wrapped in a
per-token loop so a 93-token prefill issues roughly 63,600 engine dispatches,
and OI-4, where no governed stochastic sampling contract exists — deliberately
left open, because inventing an RNG to close it would make every future result
irreproducible.
