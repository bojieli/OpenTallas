# OpenTallas redesign plan

**Plan ID:** TA-RP-1

**Status:** proposed; supersedes the performance and physical-closure portions of
[the four-target master plan](FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md) and
[the unified execution checklist](UNIFIED_EXECUTION_CHECKLIST.md)

**Issue date:** 2026-09-04

**Cause:** [TA-PM-PERF-1](PERFORMANCE_DESIGN_POSTMORTEM.md). The modelled machine is four
to five orders of magnitude below this programme's own north star; the checklist is 87%
complete and contains no item that could have said so.

---

## 0. Why this replaces the plan rather than amending it

The previous plan's completion criteria are orthogonal to whether the design works or is
fast. Its 106 items are 92 complete, and **none of them mentions tokens per second, TPOT,
throughput, fmax, a floorplan, chip-level closure or tapeout.** Amending it would add
items to a structure that already proved it can reach 87% while the following are all
simultaneously true and all separately documented in this repository:

| what the repository says | where |
| --- | --- |
| the tensor lane's rate "is not a throughput claim" | `rtl/abi3/ot_a3_mac_lane.sv` header |
| the ROM service RTL "contains no ROM array" | checklist W8.5 |
| "no block of the ABI 3.0 control plane appears below at all" | `ABI3_PHYSICAL_VIEWS.md` |
| "no RTL path reaches a token" | `FOUR_TARGET_PROGRESS_REPORT.md`, RTL 3.0 |

Each is honest. Together they describe a project that has validated, rigorously, a
machine nobody has built. The replan's first principle follows from that:

> **Every gate states a number, a comparison, and a reachable failing state.** An artifact
> with a digest is not a gate. A budget that is unfrozen is not deferred, it is disabled.

## 1. The design

### 1.1 The lane: pipelined, interleaved, bit-identical

The present lane spends five cycles per multiply-accumulate — address, memory latency,
scale, multiply, accumulate — deliberately, to keep one binary32 operation per stage. Those
are five *operations*, and the contract that serialises them is per-output-element: each
element accumulates its own K products in strictly ascending K.

Ascending-K order is a property of **one element's** accumulator chain. Interleaving
**different** output elements through a pipelined adder therefore reorders nothing, and the
result is bit-identical by construction rather than by measurement. With an adder pipelined
to `L` stages and `L` output elements in flight, the lane retires **1 MAC per cycle**, a 5x
gain at zero numeric change.

`L` is set by the adder, which is the critical path and is already characterised:
`fp32_add_rne` measures 59.5725 ns and 13,868.7 um2 as a single combinational cloud in
sky130, against 29.4884 ns for `fp32_mul`. The adder is pipelined; the multiplier is
replaced.

### 1.2 The multiplier: exact BF16, not general binary32

Both operands widen from BF16, so the product's 16-bit significand always fits binary32's
24 exactly. Over 1,500,149 random normal-range BF16 products, **zero were inexact**: the
RNE rounding hardware in `fp32_mul_rne` can only fire in the binary32 subnormal range. An
8x8 significand multiply plus an exponent add is bit-identical on the normal range, with a
narrow subnormal and nonfinite path retained and still failing closed. This removes 5,165
cells and 33,660 um2 per lane and takes the multiplier off the critical path.

### 1.3 The operand path: the port that already exists

The matmul engine reads operands **2 bytes at a time** while the DMA engine beside it in the
same sequencer writes **16**, and the cost table already assumes
`sram.bytes_per_cycle_per_port = 16`. One 16 B/cycle port feeds eight BF16 lanes at 1
MAC/cycle each. The mutually exclusive request/wait states go, so reads can be outstanding;
that pair of states alone caps the present engine at 2 cycles per MAC with a perfect memory.

### 1.4 The array: the thing that does not exist yet

There is no `LANES` parameter, no generate loop and no replication anywhere in the ABI 3.0
engine hierarchy. The capabilities advertise 512, 256 and 8,192 lanes; the silicon has one.
The array is introduced as a parameterised generate over the lane of 1.1, with the operand
port of 1.3 shared across each group of eight.

Sizing is **derived, not chosen**, per the method this repository already committed:
"derive capacity, bandwidth and compute roof from area and published densities; a profile
that states them as free inputs is not a design". The derived N5 design point implies
**135,870 MAC/cycle at 1 GHz** across the 3,260 mm2 four-device ROM design, so about
**33,968 MAC/cycle per device**. That is the array to build, and it is what the analytical
comparison has been pricing all along.

### 1.5 The control plane, which has never been routed

`ABI3_PHYSICAL_VIEWS.md` records that no ABI 3.0 control-plane block appears in the physical
results and that the microsequencer is absent, for the reason in [OI-43]. A chip cannot be
shown without it. The microsequencer, the descriptor path, the event scoreboard and the
memory system enter the physical scope here; until they do, no figure in this repository
describes a chip.

### 1.6 What is deliberately not changed

The numeric contract. Every failure mode the present lane fails closed on — nonfinite BF16,
reserved E4M3FN or E8M0, a product or accumulation leaving binary32 range, a scale
application leaving it — is preserved and separately tested. The existing sequential lane is
**not modified**: it becomes the reference the new datapath is proved against.

## 2. The validation layers, and what each may claim

The previous programme's central confusion was letting one layer's number stand for
another's. Each layer below states what it may claim and what it may not.

| layer | what it establishes | may claim | may **not** claim |
| --- | --- | --- | --- |
| **L0** numeric contract | operation-level bit exactness | correctness of an operation | any rate |
| **L1** block RTL vs functional reference | a block computes the contract | bit-identity, and cycles **for that block** | a machine rate, a chip area |
| **L2** integrated RTL to a token | the design runs a real program | functional completeness | timing at any node |
| **L3** cycle model, calibrated to L1 | machine-level timing | tokens/s **of the modelled machine** | silicon timing |
| **L4** analytical roofline, anchored to L3 | design-space exploration | ratios and trends | a measurement |
| **L5** physical: synthesis, STA, P&R | implementation cost | area, period, power **at the routed node** | any figure at another node |

Three rules bind them together, each one a defect from the post-mortem turned into a rule:

- **L3 derives its machine from L4's design point mechanically** (`tools/derive_cycle_machine.py`),
  so the two describe one machine by construction. Where they disagree, the residual is
  attributed, never fitted.
- **L5 may not be scaled across nodes.** `METHODOLOGY.md` section 9 already forbids taking a
  130 nm or predictive-7 nm figure to N6/N5/N7/N4. The node-portable figures are **per-MAC
  area and per-MAC period**, and those are what say whether the design improved.
- **Every published number carries its binding constraint.** Two models that disagree about
  what limits the machine are not measuring the same thing.

## 3. The gates

Replacing 106 artifact-shaped items. Each states a number, a comparison and a failing state.

### Terminal gates

| gate | statement | fails when |
| --- | --- | --- |
| **G1 token** | the integrated RTL produces the oracle's token IDs for the governed workload on each of ROM and HBM, established compositionally over the closed verification ladder G1a–G1f | any rung fails, or the certificate does not bind every issued instance to a rung that proved it |
| **G2 chip** | a routed netlist exists containing the datapath array, the memory system **and** the microsequencer, at one named PDK, DRC 0 and antenna 0 | any block of the control plane is absent |
| **G3 speed** | measured TPOT against a **frozen** per-model budget, composed from RTL-**measured** per-operator and per-boundary cycles over the issue trace G1e certified | TPOT exceeds budget, no budget is frozen, the cycles are not RTL-measured, or the trace is not certified |
| **G4 fidelity** | the cycle model reproduces L1's measured block cycles within a stated band, and the derived machine reproduces L4's design point | either exceeds its band |

**G3 is the gate the previous programme could not fail.** It is armed by a provisional
budget from day one. A provisional budget that is wrong and fails loudly is worth more than
a correct one that cannot fail.

### The verification ladder under G1, and why it is not a whole-network run

Measured on 2026-09-05, not estimated: the integrated RTL runs at **200,231 simulated
cycles/s** and **5.0164 cycles per MAC** (`ot_a3_mac_lane` is a five-state sequential FSM),
so MATMUL is 99.7 % of simulated time. One Qwen3-8B decode step is 7,573,110,784 MACs =
**2.2 days**; the governed workload's 19 passes are 143,889,104,896 MACs = **41.7 days per
storage class**. Width does not rescue it, and that was measured too: eight lanes deliver
**1.14× lane-ops per CPU-second**, because a cycle-accurate simulator's cost tracks
evaluated logic × cycles.

No chip company verifies an accelerator that way. Pre-silicon sign-off rests on a
**verification pyramid** — block-level equivalence against a reference model, then cluster,
then system bring-up — with **coverage closure** as the sign-off criterion, and the full
workload run on **emulation** (roughly 1–3 MHz for a design this size) or an **FPGA
prototype** (10–100 MHz), four to five orders of magnitude faster than software RTL
simulation. This project has neither an emulator nor a prototype board. It says so, and
substitutes the thing that is actually sound: **composition**.

Composition is valid when three things hold, and each is a rung:

| rung | what it establishes | measured cost per store |
| --- | --- | ---: |
| **G1a** operator equivalence | every (family, shape, contract) class the decode program issues is bit-exact against golden, on real checkpoint weights, with nothing trapped as CAPABILITY | bounded by the largest operator |
| **G1b** layer closure | one complete transformer layer, no golden value injected inside it — the operator *sequence*, the residual plumbing, the KV write and read | 1.34 h |
| **G1c** composition | two layers with an RTL→RTL handoff, plus the loop property: exactly the model's layer count of structurally identical invocations | 2.69 h |
| **G1d** head and token | final norm, LM head and argmax in RTL, emitting the oracle's first generated id | 1.08 h in four concurrent row shards |
| **G1e** control end to end | all 19 passes through the real RTL control plane, engine results injected only at the engine boundary, issue trace equal to golden's element for element, EOS raised, post-EOS refused | ~3 h |
| **G1f** reduced full run | the whole workload run whole at reduced dimension with nothing injected | minutes |

G1b is the base case, G1c the inductive step, and the loop property closes the induction over
all 36 layers — assume–guarantee reasoning, with the loop count and the structural identity
of the invocations both mechanically checked rather than asserted. G1e supplies the factor
usually hand-waved in a composition argument: that the RTL issues *the same sequence* the
reference model does. It is affordable precisely because the control plane is 0.3 % of
integrated cycles, so the workload's control is cheap even though its arithmetic is not —
standard hybrid co-simulation, the real sequencer driving fetch, decode, view resolution,
predicates, the loop and issue, while the datapath results come from the model whose
bit-exactness G1a–G1d establish. G1f is the industry's small-config nightly regression.

**About 6.8 h sequential per store, about 3 h wall with the independent legs concurrent,
against 41.7 days for the run it replaces — and it is the harder gate**: six falsifiable
rungs plus a mechanically derived certificate, against one boolean in one globbed file.

What it does not establish is written into G1's `does_not_establish` and must stay there: a
single uninterrupted full-dimension run, dual-simulator agreement on the integrated path,
any rate, or silicon behaviour.

### Design gates

| gate | statement | fails when |
| --- | --- | --- |
| **D1 bit-identity** | the new datapath equals the sequential lane bit for bit over the swept space | one bit differs |
| **D2 rate** | measured MAC/lane/cycle >= 1.0 | the lane does not reach it |
| **D3 replication** | the synthesised netlist contains N lanes for a declared N | the netlist has one lane while the capability advertises more |
| **D4 per-MAC cost** | per-MAC area and per-MAC period both improve against the recorded `matmul_bf16_sram_engine` baseline at the same PDK | either regresses |
| **D5 fail-closed** | every preserved failure mode still traps distinctly | any becomes silent |

### Comparison gates

| gate | statement | fails when |
| --- | --- | --- |
| **C1 comparability** | ROM and HBM machines come from one derivation and differ only inside a cited weight-path allowlist | any parameter outside it differs |
| **C2 deployment parity** | the compiled deployments do not hand either side an advantage — tile shape, column group, tile depth, DMA tile count | any asymmetry is unexplained |
| **C3 regime** | the cycle model and the analytical model find the same binding constraint | they disagree |
| **C4 plausibility** | no published run sits more than a stated factor above its own bandwidth floor | it does |

C1 and C2 exist because the shipped comparison handed the ROM side a 2x tensor-lane
advantage and a 16x column-group advantage and reported the result as a ROM win.

## 4. Sequencing

The critical path is **D1-D5 → G1 → G2 → G3**. G4, C1-C4 run alongside.

1. **Datapath.** Pipelined lane, exact BF16 multiplier, wide operand path, generate array.
   Proved by D1-D5 against the untouched sequential reference.
2. **Control plane to RTL.** The microsequencer and descriptor path, which G2 needs and
   which no physical result has ever contained.
3. **Integration to a token.** G1's ladder on the governed workload, both storage classes:
   operator equivalence, layer closure, the inductive step, the RTL-emitted token, the
   certified control trace, and the reduced full run — then the composition certificate.
4. **Chip-scale physical.** G2 at one named PDK; per-MAC figures for D4; no cross-node
   scaling.
5. **Calibrate and re-anchor.** G4: the cycle model's block cycles against L1; the derived
   machine against L4.
6. **Freeze budgets and measure.** G3, per model, per storage class, per context.
7. **Re-run the matrix.** All three models, both storage classes, under C1-C4.

Steps 1 and 5 are already in flight. Step 7's harness exists
(`tools/derive_cycle_machine.py`); its inputs do not yet.

## 5. What is retired

- **The 10,000 tok/s north star as an unevaluable aspiration.** It becomes G3's provisional
  budget, with a reachable failing state, or it is replaced by a budget that has one.
- **Row folding and lane mapping as performance work.** A 2026-09-03 analysis established
  that "100 us cannot be reached by minor lane-mapper or scheduling changes"; the ADR that
  forbade the tile change by name then recorded it as an implementation update. Scheduling
  work resumes only after D2 and G2.
- **Utilisation as a headline.** 99.9918% physical output-lane utilisation was recorded as
  success on a machine 44,000x short. Utilisation may appear beside an absolute figure and
  its binding constraint, never alone.
- **Any physical figure cited for a machine it does not implement.** The recorded blocks
  remain valid for what they are: engine datapaths and numeric probes, at their own nodes,
  correlated against the cases `results/rtl/abi3_deployment_campaign.json` names.

## 6. Debt this plan inherits

Recorded so it is scheduled rather than rediscovered:

- 17 failures in `tests/runtime/test_abi3_cycle.py`, all "capability does not implement
  required feature bits [10]" against synthetic fixtures; reproduce at `3d93980` and
  `d0b078b`, so they predate the redesign
- `test_every_kernel_reaches_an_operator` in the HBM backend suite, likewise pre-existing
- `test_governed_v2_report_binds_sources_and_stays_below_the_thresholds` in
  `tests/sim/test_deepseek_context_gate_model.py`: the governed context-gate report binds a
  source that has since moved; reproduces at `cc9c97c` in a clean worktree, so it predates
  the matrix and datapath work. Regenerating it is a governed run, not an edit
- `test_exact_200k_rom_hbm_pair_passes` in
  `tests/test_deepseek_v4_200k_accelerator_acceptance.py`: rejects its own synthetic
  passing pair at clean `146ef7c`; pre-existing
- the eight retained cycle artifacts predate the tensor unit fix and are 2x optimistic on
  their tensor term; they are evidence of a failure, not performance figures
- no speculative deployment admits; the build stops at a declared physical HBM bound that
  was deliberately not widened
- 7 open issues carried in the checklist, [OI-43] among them, which is why the
  microsequencer is absent from every physical result
- token records bind `runtime/evidence.py` -- the module that *reports* and *compares*
  records -- among the 54 sources that fix their identity. A fix to comparison logic
  (`146ef7c`) therefore invalidated three five-hour records it was written to compare.
  Identity should bind what produced the tokens, never what formats the report; until
  that is separated, every reporting fix costs a full re-run, which is the treadmill the
  previous programme ran on
