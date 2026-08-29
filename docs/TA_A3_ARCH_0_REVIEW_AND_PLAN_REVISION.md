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

**The ASAP7 predictive view as specified cannot be executed on this system and
is therefore replaced.**

Verified facts: ASAP7 does not exist anywhere on this filesystem; it lives only
inside an `openroad/orfs` container image that is not present in the local
Docker daemon; `openroad` is not installed. The archived
`results/asap7_physical/` evidence was produced with that image and **cannot be
regenerated here**. The IHP SG13G2 digital place-and-route flow is blocked for
the same reason. Continuing to plan against ASAP7 would guarantee an
unreproducible number in the final comparison — exactly the failure this program
exists to avoid.

The two technology views become:

| View | Role | Technology | Flow | Reproducible offline |
|---|---|---|---|---|
| **IHP SG13G2** | mature implementation view | 130 nm open foundry PDK | Yosys 0.68 + ABC -> `sg13g2_stdcell` (slow 1.08 V/125 C, typ 1.20 V/25 C, fast 1.32 V/-40 C) -> OpenSTA 3.1.0; real `sg13g2_sram` macros with liberty timing | yes |
| **Nangate45** | predictive scaled view | 45 nm academic library | Yosys 0.68 + ABC -> Nangate45 typical -> OpenSTA 3.1.0 | yes |

IHP SG13G2 replaces SKY130 as the mature *digital* view for a decisive reason:
the installed `sky130A` tree contains only `libs.ref/sky130_fd_pr` (SPICE device
primitives). It has **no standard-cell liberty and no SRAM macros**, so no
digital synthesis or static timing can be performed against it here. IHP SG13G2
ships the complete `sg13g2_stdcell` liberty set at three corners plus
characterised single-port SRAM macros from 256x8 through 2048x64 with liberty,
LEF, GDS and CDL. That closes the `qualified_sram_macro: false` gap that every
previous physical report had to carry open.

SKY130A is retained for what it can actually support and already evidences: the
ROM-bitcell layout, DRC, LVS, parasitic-extraction and PVT/mismatch SPICE
campaigns. The existing IHP SG13G2 ROM-slice SPICE evidence and the
`ot_ta_add_bf16_sram_engine` IHP place-and-route result also remain valid for
the blocks they cover.

Both digital views produce gate-level area, cell counts, macro counts and static
timing from the *same* RTL 3.0 sources. Neither claims place-and-route closure
for the full chip, and no number is carried across views. Archived ASAP7 results
are reclassified **historical, non-reproducible**; they may not appear in a new
comparison table.

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

Rationale: DeepSeek-V4-Flash is a 156 GB, 43-layer, 256-expert model with a
learned sparse indexer, a two-rate compressor, 20-iteration Sinkhorn hyper-
connections and FP4 experts. A functionally exact 200,000-token prefill is a
compute campaign, not a correctness gate. Separating the two lets the
correctness gate close on real tokens now and lets the capacity/cost comparison
be produced by the cycle model over a real executed trace, with the extrapolation
visible instead of hidden. **A functional claim is never made from a cycle
result, and a cycle result always names the executed trace it extends.**

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
