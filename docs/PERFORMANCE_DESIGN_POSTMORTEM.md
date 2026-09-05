# Performance design post-mortem: how the accelerator came to be 44,000x too slow

**Post-mortem ID:** TA-PM-PERF-1

**Status:** findings established; corrective decisions open

**Issue date:** 2026-09-04 (revised the same day after a forensic pass over the git
history, the RTL and the Codex session trajectories overturned part of the first draft)

**Occasion:** a cycle-accurate Qwen3-8B batch-1 decode at context 8,000 was found to
deliver 0.225 tokens per second. The session producing it was stopped.

**Scope:** why the modelled machine is four to five orders of magnitude below this
program's own stated target, why roughly 457 million agent tokens and 340 agent-hours did
not correct it, and what rule changes follow.

**A note on this document's own first draft.** The first version of this post-mortem said
the shortfall went unnoticed, and reported the HBM chip as running at 99.17% model-FLOPs
utilisation with no scheduling loss. Both are wrong, and the corrections are in sections 2
and 3. The shortfall was quantified twice, five days apart, and reported into the sessions
that owned the files. The 99.17% was the product of two errors that nearly cancelled. A
post-mortem that gets its own arithmetic wrong in the reassuring direction is an instance
of the thing it is investigating, so the errors are left visible rather than quietly
edited out.

---

## 1. The number

Two artifacts, one token, one process view (SKY130), one prompt position:

| artifact | cycles | seconds | tokens/s |
| --- | --- | --- | --- |
| `qwen3_hbm_exact8k_b1_sky130_decode_pos8002_rowfold_v1.json` | 172,357,340 | 4.4414 | 0.2252 |
| `qwen3_rom_exact8k_b1_sky130_decode_pos8002_rowfold_depthfix_v1.json` | 148,108,696 | 3.8165 | 0.2620 |

Both retire the real model: `tensor.multiplications` is 7,568,097,280 and
`tensor.additions` is 7,566,544,512, for 15,134,641,792 work units, and the HBM lane moves
17.66 GB. The program is not a stub. The machine executing it is very small.

`docs/ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md:66` states the target:

> The aspirational north star remains **10,000 generated tokens/s, equivalent to
> 100 microseconds per output token**.

The gap is **44,414x** on the HBM target and 38,165x on the ROM target.

## 2. The gap, and a unit mismatch inside the simulator

The first draft of this document reported the HBM chip at 99.17% model-FLOPs utilisation
and a scheduling loss of 1.008x, and concluded there was no scheduling problem at all.
That was arrived at by dividing a consistent-units floor by an inconsistent-units measured
total. Two errors, in opposite directions, of almost the same size. The artifact's own
fields say otherwise:

| field, HBM artifact | value |
| --- | --- |
| `engines.tensor.compute_bound_cycles` | 85,692,144 |
| `engines.tensor.utilisation` | 0.511377 |
| `engines.tensor.idle_cycles` | 84,217,712 |
| `engines.tensor.issued_tile_work` | 7,568,101,376 |
| `engines.tensor.work_units` | 15,134,641,792 |

Two facts follow, and they are separate.

**First, there is a real overlap loss of about 2x.** The model charges the tensor engine
85,692,144 cycles of a 172,357,340-cycle token and leaves it idle for 84,217,712. Roughly
half the token is spent with the arithmetic unit doing nothing.

**Second, and more seriously, the tensor charge is computed in the wrong units.**
`issued_tile_work` is 7,568,101,376, which is the multiplication count. But
`engine.tensor.work_per_lane_cycle = 0.34587860192585124` was characterized against
`tensor.multiplications + tensor.additions` — the cost table says so in its own note, and
`work_units` in the same artifact records 15,134,641,792. The model therefore divides a
MAC count by a rate defined on MACs-plus-adds. The discrepancy is a clean factor of two:

| | HBM (256 lanes) | ROM (512 lanes) |
| --- | --- | --- |
| tensor cycles the model charged | 85,692,144 | 42,745,020 |
| tensor cycles under consistent units | 170,926,140 | 85,463,070 |
| ratio | 1.995x | 1.999x |
| reported | 0.2252 tok/s, 44,414x short | 0.2620 tok/s, 38,165x short |
| unit-consistent | 0.1507 tok/s, 66,377x short | 0.2034 tok/s, 49,173x short |

The error is in the optimistic direction. **This is an open defect and it must be resolved
before any performance figure from this cycle model is quoted again**, including the ones
in this document. Every number here is reported as the model reports it, with the
correction shown beside it.

For scale either way: reaching the north star at one BF16 fused multiply-add per lane per
cycle and a 1 GHz clock needs about **75,673 tensor lanes**. The design has 256 and 512.

## 3. It was found, twice, and left standing

This is the finding that replaced the first draft's claim that nobody noticed.

**2026-08-30 04:06:48Z.** A subagent audit reported into the very Claude Code session that
had written the capability files that `engines.tensor.lanes x work_per_lane_cycle x clock`
gives 1.02 TFLOP/s for the 512-lane ROM chip and 0.51 TFLOP/s for the 256-lane HBM chip,
and that these are 267x and 609x short of the HC1 and A100 anchors the study exists to
compare against. Ninety minutes earlier, commit `300c666` had added
`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` section 4, which states the method:

> 1. **Fix the silicon area first.** It is the binding constraint...
> 2. **Derive capacity, bandwidth and compute roof from area and published densities.**
>    They are outputs. A profile that states them as free inputs is not a design.

The capability files state lanes as free inputs. By the repository's own method, committed
that morning, they were not a design. The audit said so, in the session that owned them,
and nothing changed.

**2026-09-03 21:37Z.** A Codex session computed the shortfall directly, and its wording
leaves nothing to interpret:

> HBM tensor lanes required at characterized rate: SKY130: `7.568e9 / (0.3458786 x
> 38.8071e6 x 100e-6) ~ 5.64 million lanes`; ASAP7: about `3.78 million lanes`. Qwen ROM
> required lanes are the same workload requirement; current 512 lanes are short by
> roughly: SKY130 `~11,020x`, ASAP7 `~7,390x`. These enormous factors mean 100 us cannot
> be reached by minor lane-mapper or scheduling changes. It requires a fundamentally much
> wider spatial design, much faster arithmetic, massive replication, and/or a much higher
> clock.

Earlier the same evening, at 17:38:11Z, the same session had written that the team
"should treat this as an architecture-sizing failure to fix — not hide it behind simulator
speed."

The governing ADR had been issued at 19:52 that day, between those two moments. It was
never amended. Work continued for another day on row folding and lane mapping, which is
precisely the class of change the 21:37 analysis had already ruled out.

So the failure is not that the number was unknown. It is that **nothing in the process
could convert a finding into a stop.**

## 4. Why finding it changed nothing

### 4.1 Every instrument in the program is an upper bound

This is the deepest structural fact, and it is systematic rather than an oversight in one
gate. `compiler/tensor_accelerator/production_capability.py:519` hard-codes
`"performance_claims_permitted": False` and raises if a capability sets it true. The
runtime verifier enforces `work <= max_retired_work`. The compiler raises on two dozen
"exceeds capability" conditions. The roofline tests assert `hard_ceiling_tokens_s <
17_000`. Every speed retraction in `docs/EVIDENCE_LEDGER.md` corrects a number downward.

The program could therefore prove, to a very high standard, that a machine is **not faster
than** some figure. It had no instrument anywhere that could say a machine **must be faster
than** some figure. The only field in the repository named for performance is a fail-closed
prohibition on claiming performance, with no reachable true.

### 4.2 The performance gate had no reachable failing state, and was wired to nothing

`docs/ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md:66-70` sets the north star and removes
it from the gates in the same paragraph: it "is not a release pass criterion", and until
per-model budgets are frozen "the TPOT gate can only be `not_evaluable`, not `pass`". The
budgets were never frozen. `tpot_acceptance` is an optional property of the
comparison-contract schema, and its absence maps to `budget_missing` and thence to
`not_evaluable`. The single Qwen comparison contract's capability, deployment and
cost-table locks are all `status: pending` with null digests, so the phase that could have
created a budget could not complete.

And none of the Makefile's 89 targets invokes the TPOT checker. Both it and the release
freezer exist only inside the test suite, exercised against fixtures the tests build
themselves. A gate that cannot fail, cannot be reached, and is never run is not a gate.

### 4.3 The ADR forbade by name the change that produced the headline

`ADR:143-145`:

> Changing a compiler tile from 64 rows to one row before implementing the hardware
> semantics would only create a cycle-model speedup and is forbidden as performance
> evidence.

Row folding landed 17.4 hours later as `080d165`, and the ADR's own implementation update
now records it approvingly at lines 22-31, reporting "physical output-lane utilization is
99.9918%" and the new cycle totals. The document forbade the change, the change was made,
and the document was updated to describe it rather than to refuse it.

### 4.4 The objective could be satisfied by agreement rather than by achievement

The stopped session's objective was "produce the numbers that validate the analytical
numbers". It did. The simulation reproduced the analysis to within 0.07%. But the
analytical table it was validating itself predicted about 1.475 s per token for Qwen HBM on
ASAP7, so agreement with it was fully compatible with delivering 0.225 tokens/s.

Validating an analysis of a machine four orders of magnitude too small is a task that can
be completed perfectly while the program fails completely. The session hit its objective.

### 4.5 The two models shared no variable through which they could ever be compared

The analytical roofline expresses compute only as ops/s/mm2 times mm2, transferred as an
area density from a published A100 dense roof. The cycle model expresses compute only as
lanes times work-per-lane-cycle times hertz. `src/opentallas/roofline.py` contains zero
occurrences of "lanes"; the cost tables contain zero occurrences of area.

There is a tool that calls itself "the join between the two halves of the project",
`tools/validate_model_against_execution.py`, and it states in its own header that it does
not compare time. So the only bridge between the analysis and the simulation was built
with the load-bearing quantity deliberately excluded.

### 4.6 The lane count was never a decision

`git log -S` shows 256 tensor lanes entering at 2026-08-29 16:03:40 in a commit about
landing the Kernel IR, and 512 entering five minutes and twenty-eight seconds later inside
`ffed8a7`, a commit titled `docs(abi3): freeze the operator operand conventions`, whose
message never mentions the new file or any lane count. In that file every other constant
carries a provenance comment; the `engines` dict carries none.

The RTL lane mapper that now defines 256 lanes in hardware, `ot_a3_tensor_lane_mapper.sv`,
landed five days later and its header says it implements the ADR. The causal arrow runs
config to document to RTL, not the reverse.

On the very target that produced 0.225 tokens/s, the declared lane count is not read by
the compiler at all: `compiler/backends/hbm_sram/plan.py:250-253` fixes `rows: int = 64,
cols: int = 128, depth: int = 128, block: int = 512` as policy defaults.

### 4.7 The engine is one scalar MAC, and its rate was accepted as a fact of nature

`rtl/ot_ta_matmul_bf16_sram_engine.sv` contains exactly one multiplier and one adder,
behind a strictly serial request/wait FSM. Because request and wait are mutually exclusive,
the engine cannot exceed two cycles per multiply-accumulate, a hard structural ceiling of
1.0 work per lane per cycle regardless of what memory it is attached to. The measured
0.34588 is 2.891x below even that, and the balance is contributed by the campaign
testbench's deliberately stall-generating behavioural memory, which grants read acceptance
on alternate cycles and rotates read latency through one, two and three extra cycles.

Because the figure is graded `characterized` it outranks everything in the provenance
system, which is exactly what that system is for. So the slowest reading of a
one-multiplier engine measured against a deliberately hostile testbench became the
machine's permanent rate, and no gate ever forced the question of what the RTL should
become.

### 4.8 Correctness governance was excellent, and pointed entirely away from this

Token-identical oracle comparison, source-currency binding by SHA-256 on every artifact, an
independent second-opinion schedule checker, prose-figure provenance over a
3,300-candidate census, a 24-item comparison fairness audit, deterministic rebuild proofs,
inverse reconstruction proofs. None of it polices speed. The program can prove to a very
high standard that a machine four orders of magnitude too slow computes exactly the right
tokens.

## 4.9 Why this is a redesign and not a repair

Everything above describes defects that could, individually, be fixed. Taken
together they say something stronger, and the checklist is where it becomes
undeniable.

`docs/UNIFIED_EXECUTION_CHECKLIST.md` carries **106 items. 92 are complete, 11
partial, 3 open.** Eighty-seven per cent done. And **zero of the 106 mention
tokens per second, TPOT, throughput, fmax, a floorplan, chip-level closure or
tapeout.** Not one. The programme was measuring, with real rigour, a set of
propositions that does not contain the proposition it exists to establish.

Read alongside what the artifacts actually are, the conclusion is not that the
work was done badly. It is that the work was done well against the wrong
specification:

* the tensor lane says of itself that its five-cycle reduction "is not a
  throughput claim, no result bit depends on it, and it is not a rate any cycle
  model may read" -- it is a correctness vehicle, and an honest one
* item W8.5, ROM service RTL, states that the read path "is implemented and
  correlated on two simulators, and **it contains no ROM array**"
* `docs/ABI3_PHYSICAL_VIEWS.md` states that "no block of the ABI 3.0 control
  plane appears below at all" and that the microsequencer is absent
* `docs/FOUR_TARGET_PROGRESS_REPORT.md` states, at RTL 3.0, "no RTL path
  reaches a token"

So the mask-ROM accelerator has: no ROM array in its ROM RTL, no control plane
in its physical evidence, one multiply-accumulate lane where its capabilities
advertise up to 8,192, and no path from RTL to a token. Every one of those is
recorded honestly somewhere in the repository. None of them is a checklist item
that can fail.

A repair would fix the tensor unit mismatch, widen the lanes, and route more
blocks, and would leave in place the thing that produced all of it: a
specification whose completion criteria are orthogonal to whether the design
works or is fast. That is why the plan is replaced rather than amended, and why
the replacement's terminal gates are stated as numbers with comparisons rather
than as artifacts with digests. See
[the redesign plan](OPENTALLAS_REDESIGN_PLAN.md).

## 5. What the comparison inherited

On the Qwen pair the ROM chip is advertised with 512 tensor lanes and the HBM chip with
256. `docs/COMPARISON_FAIRNESS_AUDIT.md` contains 24 audited items; item A10 concerns a
"512- vs 8,192-token program block", which is program block size and a different quantity.
**The 2x tensor-width asymmetry between the two chips under comparison is audited
nowhere.**

It may be defensible under an iso-area argument, since a ROM design spends no area on DRAM
controllers. It is not argued anywhere. Note the direction: it flatters ROM, which is the
conclusion the project would like to reach.

## 6. The cost

From `/home/ubuntu/.codex/goals_1.sqlite`, across 26 Codex threads on this machine:

- **456,803,790 tokens**
- **340 agent-hours**
- outcomes: 5 complete, 9 blocked, 8 paused, 2 usage-limited, 2 active

The single stopped thread reports `total_tokens` of 1,441,793,764 in its own trajectory
accounting. Of the 26 recorded objectives, none contains a term that could fail: no "at
least", no "must reach", no "faster than", no "within". Five of the eight OpenTallas
objectives say "autonomously".

## 7. What we learn

**R1. Every performance gate must have a reachable failing state from the first day.** An
unfrozen budget is a disabled alarm. A provisional target that is allowed to be wrong and
fails loudly beats a correct target that cannot fail.

**R2. Instrument the lower bound, not only the upper bound.** A program whose every
compiler check, runtime check and test asserts "not faster than" will never notice "far too
slow". At least one check must fail when the machine is under-performing.

**R3. Report the ratio to the requirement, never only the ratio to yourself.** Any artifact
publishing a cycle count must also publish tokens/second and that figure divided by the
target.

**R4. A finding must be able to stop the work.** The shortfall was quantified on 2026-08-30
and again on 2026-09-03, in writing, in the sessions that owned the files, and work
continued on exactly the changes the analysis had ruled out. Route quantified shortfalls
into a state that blocks, not into a paragraph.

**R5. Size the fabric before building the evidence machine, and follow your own method.**
The obligation existed in this repository, in writing: derive compute from area, and a
profile that states it as a free input is not a design. It was committed and not applied.

**R6. `characterized` means "this is what it does", never "this is what it must do".** A
measured rate is a fact about the current implementation and a question about the next one.
Check what the testbench was doing to the number before enshrining it.

**R7. Utilisation without magnitude is not evidence of health.** "99.9918% physical
output-lane utilization" was recorded as an implementation success on a machine 44,000x
short. So, in this document's own first draft, was 99.17% MFU.

**R8. A fairness audit must cover the parameters that set the headline ratio.** Tensor
width is the first-order term in a compute comparison.

**R9. Two models of one machine must share the machine by construction.** Derive the
simulator's machine from the analytical design point mechanically, never specify them
alongside each other. The derivation is arithmetic: the analytical ROM point's 726.6 mm2 of
compute area, times its published N5 density of 6.799e11 ops/s/mm2, times its 0.55 derate,
gives 55.70 us against its own published compute term of 55.703 us.

**R10. Check the binding constraint before comparing the number.** The analytical model
finds the GPU weight-read bound, spending 1,051 us of a 1,322 us budget fetching weights,
which is the entire reason a mask-ROM design wins. The cycle model finds both targets
compute-bound, so the one quantity the project exists to measure was structurally
invisible. Publish the binding constraint next to every performance figure.

**R11. An autonomous objective must carry a falsifiable acceptance criterion, and it must
name the right referent.** "Produce the numbers that validate the analytical numbers" was
satisfiable by agreement with an analysis of the wrong machine, and it was satisfied.

**R12. Audit units at every boundary between a counter and a rate.** The tensor charge in
this cycle model divides a MAC count by a rate defined on MACs-plus-adds, a clean factor of
two in the optimistic direction, and it survived every provenance, source-currency and
correctness check this repository runs.

**R13. When a flow reports one metric under two parasitic models, the optimistic one is
not evidence.** ORFS `repair_design` fixes slew against global-route estimates; the finish
check re-measures it against RCX extraction. LQ8 showed +0.5% slew headroom at global route
and -49% at finish, so a stage-by-stage read of its own metadata said "clean" four times before
saying "292 violations" once. Repair against the pessimistic model, or against a margin wide
enough to cover the gap (`SLEW_MARGIN 40` closed LQ8 for +0.47% cells), and treat any metric
that changes with the extraction model as unreported until the pessimistic value is in hand.
Recorded 2026-09-05 from section 13 item 14 of the architecture design.

---

## Appendix: how to reproduce the arithmetic in this document

```python
import json
rate = 0.34587860192585124          # engine.tensor.work_per_lane_cycle, sky130 v2
north_star = 10_000                 # tokens/s, ADR line 66

for art, lanes in (("qwen3_hbm_exact8k_b1_sky130_decode_pos8002_rowfold_v1", 256),
                   ("qwen3_rom_exact8k_b1_sky130_decode_pos8002_rowfold_depthfix_v1", 512)):
    d = json.load(open(f"results/abi3/cycle/{art}.json"))
    t, T = d["engines"]["tensor"], d["timing"]
    c = d["counters"]["architectural"]
    work = c["tensor.multiplications"] + c["tensor.additions"]
    consistent = work / (lanes * rate)          # what the rate's own units imply
    charged = t["compute_bound_cycles"]         # what the model actually charged
    fixed_s = (T["total_cycles"] + consistent - charged) / T["clock_frequency_hz"]
    print(lanes, charged, round(consistent), round(consistent / charged, 3),
          round(1 / T["seconds"], 4), round(north_star * T["seconds"]),
          round(1 / fixed_s, 4), round(north_star * fixed_s))
```
