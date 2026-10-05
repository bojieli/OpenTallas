# TA-A3-ARCH-0 disposition and plan revision

**Record ID:** TA-A3-ARCH-0-REV-1
**Date:** 2026-08-29
**Reviewer/owner:** single unified implementation owner
**Baseline:** `main@c83e543`

## 1. Disposition

`TA-ADR-003` (ABI 3.0 / RTL 3.0 architecture decision) is **ACCEPTED** with the
amendments in section 2. `TA-ABI3-WIRE-1` (frozen wire format) is **ACCEPTED**
with amendments A1–A5. `TA-A3-ARCH-0` is **CLOSED**. Implementation of ABI 3.0
compiler, simulator and RTL is unblocked.

The gate's own exit criteria in ADR-003 section 20 are met as follows.

| Criterion | Disposition |
|---|---|
| Four target boundaries and reuse rules | accepted unchanged |
| Qwen 1-chip / DeepSeek 32-node HBM / DeepSeek wafer ROM profiles | accepted unchanged; one chip elaboration proven by construction — all four targets consume one simulator and one engine set, and the two HBM deployments differ only in a topology descriptor |
| Firmware vs microsequencer responsibility | accepted unchanged |
| Host / deployment / micro-ISA layering | accepted; realised as `runtime/abi3` with three independent codecs |
| Instruction families, loops, predicates, events, state, EOS, traps, counters | accepted; amendments A3–A5 supply the missing predicate and loop-parametric-addressing mechanisms |
| Qwen+DeepSeek capability union | accepted; the union is enumerated in `spec/abi3/capability_union.json` and mechanically checked against both exporters |
| Cluster/wafer topology, collectives, repair, degraded behaviour | accepted unchanged |
| Public NVLink/Cerebras envelopes source-locked | carried; these remain **external reference envelopes**, never OpenTallas achieved values |
| SKY130 mature view, ASAP7 predictive view | **REVISED** — see section 3 |
| ROM/HBM lowering does not leak into neutral IR | accepted; enforced by a neutrality checker |
| ABI 2.5 migration and equivalence criteria | accepted; revised in section 4 |
| Qwen 8,000 / DeepSeek 200,000 acceptance boundaries | **REVISED** — see section 5 |
| No unresolved decision changes an externally visible ABI semantic | met after A1–A5 |

## 2. Wire-format amendments made at freeze

The wire-format draft was internally inconsistent with ADR-003 in five places.
All five are repaired *before* release rather than carried as debt.

**A1 — completion carries the final token and EOS reason.** ADR-003 6.3 requires
"final selected token and EOS reason when applicable"; the draft completion
record had no field for either. Bytes 104–108 of the former 20-byte reserved
span now carry `final_token_id` (u32) and `eos_reason` (u8).

**A2 — completion carries retired work.** The program header proves a maximum
retired-work bound; without a matching completion field that proof is
unobservable. Bytes 112–119 carry `retired_work` (u64).

**A3 — descriptor type `PREDICATE = 0x000f` is assigned.** Every instruction has
a `predicate_id` and ADR-003 5.2 mandates architectural predicates, but the
descriptor registry defined no predicate record. Assigning a previously unused
type value is additive under the minor-version rule.

**A4 — tensor views carry up to four dynamic index terms.** ADR-003 5.1 requires
loop-compressed programs ("they do not repeat one instruction per element or DMA
burst"). A loop over tiles can only move its window if a descriptor can be a
function of the induction variable. Each term contributes
`selector_value * element_stride` elements to the view's offset, where the
selector is a loop induction variable or a bound runtime symbol. Without A4,
ABI 3.0 would reproduce the ABI 2.5 failure mode of 924,386 flat records per
forward step.

**A5 — the runtime-symbol registry is frozen.** ADR-003 5.2 names the
request-bound scalars a predicate may read in prose only. `Symbol` assigns them
stable numbers so loop bounds, predicates and A4 terms share one namespace.

## 3. Revision: physical verification views

**Superseded by evidence. The original two-view plan stands.**

This section first replaced the ASAP7 predictive view, on the finding that
ASAP7 existed nowhere on this filesystem, `openroad` was not installed, and the
`openroad/orfs` container the archived results came from was absent — so
`results/asap7_physical/` could not be regenerated. That reasoning was correct
about the state of the machine and wrong about the conclusion, because the
machine has network access and the missing pieces were fetchable.

Both were fetched and both now run. The decisive check: the ASAP7
`reduction_s8_g2` case was re-run and reproduced the archived result
**bit-for-bit**, with every metric identical and a matching `6_final.v`
SHA-256. The archived campaign is reproducible in fact, not merely in
principle, and is reinstated as valid evidence.

The two views are therefore:

| View | Role | Node | Flow | Reproducible offline |
|---|---|---|---|---|
| **SKY130 HD** | mature implementation view | 130 nm manufacturable foundry PDK | Yosys 0.68 + ABC -> `sky130_fd_sc_hd` (18 liberty corners) -> OpenSTA 3.1.0 -> full ORFS place-and-route | yes |
| **ASAP7** | predictive view | 7 nm predictive academic | same flow inside the pinned `openroad/orfs` container | yes |

Both do **full place-and-route**, not synthesis and static timing only. All
four block runs closed with zero detailed-route DRC and zero antenna
violations.

IHP SG13G2 was considered and rejected for the digital views, not because it is
inadequate — its PDK is complete and it retains the ROM-bitcell SPICE evidence
and the `ot_ta_add_bf16_sram_engine` place-and-route result — but because it is
*also* 130 nm, so pairing it with SKY130 would have given two views at one node
and no scaling comparison at all. Nangate45 was rejected as a generic
educational library rather than a foundry process.

What genuinely does not reproduce is narrower and is stated in
`docs/ABI3_PHYSICAL_VIEWS.md`: there is no foundry signoff DRC or LVS in either
view (ORFS DRC counts are the router's own checks), neither characterised block
contains a macro so SRAM macro placement is untested, and `openroad/orfs:latest`
is a mutable tag, so a future pull is not guaranteed to yield the pinned image.

A note on how this section reached the wrong conclusion, since the failure mode
matters more than the fact: it inferred a permanent constraint from an
observation about the current filesystem, and proposed replacing a *plan target*
to fit a *tooling gap*. The correct order is to test whether the gap is
removable first. It was, in about twenty minutes.

## 4. Revision: concurrency and ownership

The master plan's four-parallel-top-level-owner model is **withdrawn**. It is
the recorded cause of the previous divergence: four owners with no shared IR and
no shared ABI produced four non-comparable result sets.

Replaced by: **one owner of all contracts**, with implementation fan-out only
*behind frozen interfaces*. Specifically, one program owns
`runtime/abi3`, `compiler/ir/v3`, `runtime/sim` interfaces and the evidence
schema. Parallel workers implement engine bodies, backend lowering passes,
exporters, RTL and physical flows against those interfaces, and every worker's
output is admitted only by the shared verifier.

The structural guarantee of comparability is stronger than a process rule: all
four targets are executed by **one** simulator binary consuming **one** ABI 3.0
deployment format with **one** engine set and **one** counter registry. A target
is a set of descriptors, not a code path.

## 5. Revision: workload contracts

The workload targets are retained as the program's goals but are restated with
their *evidence class* so that no report can silently substitute one for
another.

| Contract | Target | Class |
|---|---|---|
| `TA-QW-SHORT` | Qwen chat/agent prompt → decode to first EOS | functional acceptance, both Qwen backends |
| `TA-QW-8K` | Qwen exactly 8,000 natural prompt tokens → decode to first EOS | functional acceptance, both Qwen backends |
| `TA-QW-STRESS` | Qwen repeated-special-token stress | functional acceptance |
| `TA-DS-SHORT` | DeepSeek prompt → decode to first EOS | functional acceptance, both DeepSeek backends |
| `TA-DS-LONG` | DeepSeek long context toward 200,000 | functional acceptance at the **achieved** context, which every report must state numerically |
| `TA-*-CYCLE` | all four at their full mandatory context | cycle-model result over the executed operation trace, labelled as such |

One correction to the mandatory DeepSeek figure itself: **200,000 is not an
admissible deployment context.** A deployment context must be a whole number of
128-token sliding windows, so the nearest admissible value is 200,064. The
prompt contract is unchanged — 200,000 natural prompt tokens — but it sits
inside a 200,064-token context, and a report should say so rather than round.

Rationale, now measured rather than estimated. The reference oracle executes
DeepSeek-V4-Flash on this machine by streaming the released 156 GB checkpoint
layer by layer through a GPU shared with other tenants, and produces correct
tokens: the pinned chat workload runs to a real EOS in 333 tokens and reaches
the correct answer, and the agent workload emits a well-formed tool call. Decode
costs 0.85-1.19 s per token at a peak device footprint of 0.39 GiB.

**The largest context actually executed is 8,000 tokens**, and the reason 200,000
does not run is specific and worth recording, because it is not the reason
anyone assumed:

| Context | Result |
|---:|---|
| 1,000 | prefill 35.1 s, peak 0.66 GiB |
| 8,000 | prefill 47.7 s, peak 5.09 GiB |
| 32,000 | out of memory in `hc_post` |
| 128,000 | out of memory in `hc_pre` |
| 200,000 | out of memory in the hyper-connection expansion |

The wall is the **mHC hyper-connection, not the sparse indexer**. At 200,000
tokens `hc_post`'s `[b, s, 4, 4, 4096]` binary32 intermediate is 48.8 GiB and is
allocated twice per layer across 43 layers; the indexer's unchunked score tensor
would be 2.33 TiB. The persistent KV and RoPE state is only 2.32 GiB, measured —
that was never the constraint. **A 200,000-token prefill requires a chunked
rewrite of the vendor prefill path on any GPU**: even an empty 95 GiB card
cannot hold `hc_post` plus the indexer term. Once chunked the time is about 58
seconds, so the blocker is memory and vendor code structure, not throughput.

This is why the workload contract separates the functional gate from the
capacity result. The correctness gate closes on real tokens at the context that
runs; the capacity and cost comparison comes from the cycle model over a real
executed trace, with the extrapolation visible instead of hidden.

One further result belongs here because it nearly went the other way. The
released TileLang `fp4_gemm` kernel is **wrong on this GPU architecture**,
giving a maximum absolute error of 6.52 against a signal whose mean magnitude is
1.28. Two mutually independent references agree with each other to half a
bfloat16 ulp and disagree with it. Because the routed experts are most of the
model, it did not crash — it produced fluent, on-topic, semantically empty text,
which is precisely the failure mode this program's rules exist to catch:
*exact failures remain failures even when output text is semantically
plausible*. The oracle uses the release's own documented FP8 recast instead, and
re-proves the check at every start.

## 6. Revision: what is reused and what is abandoned

Reused, because it is real and validated:

- Qwen 617-operation Model Graph v2 / Kernel IR and the six bit-exact NumPy
  kernel modules (`bf16`, `rmsnorm`, `rope`, `elementwise`, `attention`,
  `selection`) — these become ABI 3.0 engine datapaths;
- `hbm_shards.py` content-addressed image store;
- `compiler/frontend/checkpoint.py` locked-checkpoint reader;
- the DeepSeek 2,136-node / 46-operator semantic graph and the 46 qualified
  target-precision references in `runtime/reference/`;
- the Qwen and DeepSeek tokenizer/template/encoding modules; and
- the RTL numeric library, CDC primitives, and campaign drivers.

Abandoned as a *result* basis, retained as historical evidence only:

- every ABI 2.5 command program, deployment, execution report and counter set —
  they are not ABI 3.0 and are not comparable;
- the ABI 1.0 fixture ISA, Qwen microcode ABI 1.0, the nine DeepSeek
  operator-local fixture ABIs, and the unreferenced `hardware_isa.py` draft;
- the PyTorch-backed Qwen ROM service engine as an execution claim; and
- archived ASAP7 physical numbers, per section 3.

## 7. Engine arithmetic substrate (frozen decision)

The functional simulator implements each engine's datapath explicitly, reading
its operands through descriptors from simulated device memory and writing
results back through descriptors. NumPy — and, where a target's scale requires
it, PyTorch — is the *arithmetic substrate* of a simulated engine, exactly as a
C++ simulator would call a BLAS kernel. This is legal and is what
"artifact-only functional execution" means.

What remains prohibited, unchanged from ADR-003 section 18: calling a framework
*model* (`transformers`, the vendor `inference/model.py`) to produce any
activation, logit, route or token; injecting a precomputed intermediate; host-
side argmax; and Python sequencing of individual device operations. Sequencing
comes from the ABI 3.0 microsequencer executing the compiled program. Every
engine result must reproduce its declared numeric contract, and a bit-exact
scalar oracle exists for every contract.

## 8. Consequences for the other plan documents

- `FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md` sections 6, 7, 15 (agent charters,
  launch waves, four writers) are superseded by section 4 above.
- `TENSOR_ACCELERATOR_EXECUTION_PLAN.md` remains the historical ABI 2.5 evidence
  ledger. Its open gates are superseded by `docs/UNIFIED_EXECUTION_CHECKLIST.md`.
- The three lane plans remain valid as *requirement* sources for their targets;
  their ownership and scheduling sections are superseded.
- `docs/UNIFIED_EXECUTION_CHECKLIST.md` is the single progress record.
