# Model-Specific ROM Inference Silicon — Program Plan

**Status:** pre-architecture, pre-NDA program. Nothing here authorizes product silicon.
**Purpose:** define a serious chip-development program that can validate, refute, or refine the thesis with traceable evidence, then carry the design as far as public tools and open PDKs allow before foundry engagement.
**Companion artifacts:** `infersim.py` (analytical model), `run.py`, `decide.py`, `tornado.py` (drivers).

A note on numbers. This document deliberately avoids quoting specific throughput, cost, or density figures. Every such number in the exploratory work behind it was produced by hand and several were wrong — that is precisely why the analytical model exists. **All quantitative claims must be regenerated from `infersim.py` with measured inputs.** Where this document states a direction ("advantage falls with batch"), that direction is a structural property of the equations and can be relied on; where it would state a magnitude, it points to the model instead.

---

## 1. The decision

Should we build model-specific inference silicon that stores an LLM's weights in on-die mask ROM rather than streaming them from HBM, targeting a large sparse mixture-of-experts model with compressed attention?

The answer hinges on four things, in descending order of how much they should worry us:

1. Whether a model owner will commit a checkpoint for a multi-year service life (organizational, not technical)
2. Whether the ROM read path works as a circuit at the required port width and array size (settleable pre-NDA)
3. What the target model's actual per-token KV read volume is (measurable today from open weights)
4. Whether achievable ROM and MAC densities on a leading DUV node support the required floorplan (foundry-gated)

Note that the hardest item is first and is not an engineering question. Any plan that sequences the engineering before that conversation is mis-sequenced.

---

## 2. Background: what actually limits decode

A transformer generating one token at batch size B must move two categories of bytes:

- **Weight bytes.** Every parameter the router activates must be read once per forward pass. This cost is *shared* across the batch — one read serves all B tokens.
- **KV bytes.** Each user's attention cache must be read once per generated token. This cost is *private* — it scales linearly with B and never amortizes.

On a GPU both come from HBM, and at realistic batch sizes the weight term dominates. The machine spends most of its bandwidth re-reading the same parameters and converts a small fraction of its arithmetic. This is the memory wall, and it is a bandwidth problem, not a FLOPs problem.

The industry has attacked it from three directions:

- **More bandwidth** (HBM generations). Bounded by beachfront and pin rate; improves linearly and expensively.
- **Move weights on-die** (Groq's SRAM, Cerebras's wafer-scale SRAM). Removes the off-package traversal but pays SRAM's area cost per bit.
- **Reduce the bytes** (quantization, MoE sparsity, speculative decoding). Software-side, cheap, and improving fast.

The ROM approach is a fourth: **store weights in a read-only array whose density and bandwidth-per-area substantially exceed SRAM's, and whose access pattern in autoregressive decode is fully known at compile time.**

The observation that motivates it: LLM decode reads every activated weight exactly once, in a fixed order, with no writes and no reuse. Nearly the entire apparatus of a general memory system — tags, coherence, arbitration, write drivers, refresh, ECC against soft errors — exists to serve properties this workload does not have. A ROM deletes all of it.

---

## 3. Motivation: why now, and why this shape

Three things changed recently that make this worth revisiting.

**Latency became a product.** Agentic loops and real-time interfaces (voice, computer use, robotics planning) are bounded by decode speed in a way chat never was. A reasoning model that can emit hundreds of tokens inside a conversational turn is a different product from one that cannot. Providers have begun selling tiered speed at a premium, which is the first market signal that latency has a price.

**Model architecture moved in a favourable direction.** Latent KV compression, sparse top-k attention with a learned indexer, and hybrid linear-attention layers have each cut per-token KV traffic by roughly an order of magnitude relative to dense GQA at long context. That shifts the balance of the two byte categories above toward weights — the category ROM eliminates.

**Sparsity moved in an unfavourable direction.** Frontier MoE models activate a shrinking fraction of total parameters. ROM cost scales with *total* parameters while useful work scales with *active* parameters, so rising sparsity strands an increasing share of a very expensive resource. HBM has the same problem but at a much lower cost per stored gigabyte.

These two trends pull in opposite directions and their net is model-specific. Determining the sign for a given target is the analytical model's job.

---

## 4. Related work

**Taalas / AMD.** The closest prior art: a single-die part storing a small dense model in a mask-ROM recall fabric with paired SRAM, personalized by changing two masks, acquired by AMD in 2026 for integration alongside GPUs. Demonstrates that the ROM approach produces a working part at reticle scale with a small team and modest budget, that model-to-silicon turnaround can be short, and that the mask-personalization economics hold. Does not demonstrate MoE routing, multi-die scaling, wafer-scale integration, or long context.

**Cerebras.** The only proven wafer-scale silicon: reticle stitching, cross-scribe power delivery, redundancy and repair across a full wafer, and the cooling to match. Their limitation is exactly what ROM addresses — SRAM density caps on-wafer weight capacity well below what frontier models need. Their measured decode throughput sits far below their own on-wafer bandwidth roof, which is important evidence that **the memory wall is not the only thing limiting these machines**; dataflow, scheduling, and programmability overhead matter too. Any claim that removing the memory wall alone produces a large speedup must reckon with this.

**Groq / NVIDIA.** Large on-chip SRAM banks with retained programmability, acquired at very high valuation. This is the revealed preference of the best-informed party: they paid a great deal to escape HBM bandwidth *while keeping flexibility*, rather than far less to escape it *without* flexibility. Any thesis here is implicitly a bet that they mispriced flexibility for at least one workload.

**Graphcore.** Ran the closest available experiment — large on-die SRAM, no external memory — and lost commercially on capacity-per-dollar as models grew. Their interconnect is directly relevant: a flat, stateless, non-blocking all-to-all exchange with compile-time-scheduled routing under a bulk-synchronous execution model, achieving tens of nanoseconds tile-to-tile at reticle scale. **The topology does not scale to a wafer** (crossbar wiring cost, and the physical span alone costs meaningful propagation delay), but **the static-routing discipline does** and is exactly right for a workload whose traffic pattern is known at compile time.

**Software-side attack (model-system co-design).** Recent work has pushed a trillion-parameter MoE past a thousand tokens per second on a single commodity 8-GPU node using FP4 expert quantization, block-level speculative decoding with high acceptance length, and a persistent-core runtime that eliminates operator-launch overhead. **This is the most important related work in the list**, because it is the cheapest competing answer to the same problem, it requires no custom silicon, and parts of it are open-sourced. Any comparison that assumes GPUs *without* these techniques will overstate the case for custom silicon. The model must be run with speculative decoding enabled on both sides.

**Etched, and other fixed-function inference ASICs.** Same trade at a different point on the flexibility axis (transformer-specific rather than model-specific). Useful as a reference for how the market prices lost generality.

---

## 5. The analytical model

### 5.1 Core relationship

Both architectures move the same bytes; ROM removes the weight term from the memory tier. Define:

- `W(B)` = weight bytes read per step = `dense_bytes + routed_bytes · f(B)`, where `f(B) = 1 − (1 − k/N)^B` is the fraction of routed experts touched by a batch of B
- `K` = KV bytes read per token per user (a function of context length and attention mechanism)

Then the first-order advantage is:

```
advantage(B) = 1 + ρ(B),    ρ(B) = W(B) / (B · K)
```

Two limits matter:

- **ρ(1) = active_weight_bytes / K.** A pure model-architecture number containing no hardware. Call it ρ₁. It is the single best predictor of whether a given model is a viable target.
- **ρ(large B) → total_weight_bytes / (B · K).** At high batch every expert is touched, so the numerator saturates while the denominator keeps growing.

**ρ decreases monotonically in B.** This is the most important structural property in the whole analysis and it is easy to forget: the ROM advantage is largest at low batch and smallest at throughput-optimized batch. Any evaluation that reports only the max-batch operating point will understate the case; any evaluation that reports only batch 1 will overstate it. Report the curve.

### 5.2 What raises and lowers ρ₁

| Raises ρ₁ | Lowers ρ₁ |
|---|---|
| More active parameters (bigger numerator) | Longer context (K grows linearly) |
| Latent/low-rank KV compression | Plain GQA in full-attention layers |
| Sparse top-k attention (bounds the gather) | Dense attention over the full cache |
| Hybrid linear-attention layers (O(1) state) | High per-layer indexer cost |
| Aggressive KV quantization | Deep models (more KV-bearing layers) |

Counterintuitive consequences worth stating explicitly, because both were initially got backwards in the exploratory work:

- **Larger models are better targets, holding attention mechanism constant.** Active weight bytes grow with model size while compressed KV read barely does.
- **Attention mechanism dominates model size.** Swapping the attention mechanism at fixed model size moves ρ₁ by several times, in both directions. Swapping model size at fixed attention moves it less.

So the target-selection question is *not* "which model is the right size" but "which model has the most aggressively compressed attention, and among those, which is largest."

### 5.3 Constraints the model must enforce

The exploratory work produced repeated errors by omitting terms. Every one of these must remain enforced and must report when it binds:

| # | Constraint | Why it was missed by hand |
|---|---|---|
| C1 | Weight bytes with MoE coverage `f(B)` | Easy to use total instead of touched |
| C2 | KV bytes per token, attention-type dependent | Conflated "stored" with "read per token" — a large error source |
| C3 | **GPU engaged bandwidth at low batch.** Experts are placed on specific GPUs; at low batch only a few hold a selected expert and the rest contribute zero bandwidth | Naturally invisible if you divide by aggregate bandwidth |
| C4 | ROM full-array bandwidth (interleaved placement engages all lanes regardless of which experts are selected) | Asymmetry with C3 is the real low-batch advantage and is easy to miss |
| C5 | Compute (FLOPs) on both sides | Binds for high-active-parameter models |
| C6 | **Collective latency floor × n_layers.** Batch-independent, so it dominates at low batch | Repeatedly omitted; a collective is not one hop, it is O(log N) or O(N) serialized hops |
| C7 | HBM capacity → max concurrent users | |
| C8 | **ROM wafer HBM beachfront limit.** HBM attaches at the wafer edge; capacity scales with perimeter, not area. A GPU cluster's HBM scales with GPU count. This is a genuine structural disadvantage of wafer-scale | Entirely omitted initially |
| C9 | ROM capacity → wafer count → pipeline stage count | |
| C10 | **Pipeline: per-user latency = stages × stage_interval, but aggregate throughput = batch_per_stage / stage_interval.** Confusing these is a factor-of-S error | Made this error; it inverted a conclusion |
| C11 | Engineering derate (load imbalance, defect repair indirection, clock skew, sync jitter, pipeline fill) | Consistently under-weighted; sensitivity analysis later showed it is the single largest unknown |

### 5.4 Known limitations of the current model

The execution team should fix these before trusting outputs:

- **Speculative decoding is a pure multiplier.** Draft-generation cost is not modelled, so speculative results are optimistic — badly so at high acceptance rates where implied step times fall below the collective floor. This matters because speculative decoding is the primary competing approach.
- **No prefill.** Prefill is compute-bound and parallelizes across the sequence within a single request, so it behaves completely differently from decode. Prefill throughput is also strongly regime-dependent: at short prompts it is weight-load-bound (a fixed cost that does not shrink with prompt length), at long prompts compute-bound. Add both regimes.
- **No prefill/decode disaggregation**, including the KV handoff cost, which is small per step (delta only) but large for cold sessions and migration.
- **No prefix caching**, which in production dominates input token economics and therefore the prefill/decode mix.
- **Pipeline stages assumed balanced.** In a hybrid-attention model, layer groups differ in cost and the slowest stage sets the interval.
- **No thermal, power-delivery, or cooling model.**
- **Single derate constant** rather than separate, independently-measurable terms.

---

## 6. Architecture sketch

Not a specification. A starting point to be replaced by simulation output.

### 6.1 Weight storage

Via-programmed NOR-style mask ROM. One transistor per cell with the stored bit expressed as the presence or absence of a drain via, so all layers below the programming layer are shared across every product. This is what makes the personalization economics work and what makes late-stage differentiation possible.

Rejected alternatives and why:
- **NAND-style ROM.** Denser, but series-stack read current is far too low for the required port width.
- **Implant-programmed ROM.** Denser in some flows, but sits at the front of the line and destroys turnaround.
- **SRAM.** Significantly worse density per bit, needs write path and soft-error ECC, and pays area for state retention the workload never uses.

### 6.2 Placement: interleaved, not layer-local

**Critical decision.** Two options:

- **Layer-local:** each layer's weights occupy a contiguous region. Activations forward from region to region, so inter-layer communication is trivial. But only one region is readable at a time, so the effective read bandwidth is a small fraction of the array's. Pipelining across layers does not rescue this for a single autoregressive stream, because token *t+1* depends on token *t* completing every layer.
- **Interleaved:** every layer's weights are distributed across the whole array, so every read engages full bandwidth. The cost is that each layer becomes an array-wide broadcast of activations followed by an array-wide reduction of partial sums.

Interleaved wins by a large margin, but it converts the design's central problem from *bandwidth* into *collective latency*. This is the pivot the whole architecture turns on and it must be validated in simulation, not assumed.

### 6.3 Fabric

Hierarchical, using each technology where it is proven:
- **Within a reticle field:** flat, statically-scheduled, stateless exchange (Graphcore-style). Proven at that scale.
- **Between reticle fields:** static 2D mesh (Cerebras-style). The only wafer-scale fabric with production evidence.

Tile granularity is a first-class design variable, not an implementation detail. Coarse tiles reduce hop count sharply; fine tiles ease physical design and improve defect tolerance. The sweep over granularity is the primary output of the fabric simulation.

MoE routing is data-dependent, which conflicts with the compile-time-static dataflow that makes the ROM approach cheap. Under interleaved placement, expert selection can in principle become a *wordline mask* rather than a routing decision — activations are broadcast to everything and the array selects which weights participate. **If this works, it eliminates the dynamic-NoC risk entirely.** If it does not, a dynamic routing fabric with bounded tail latency is required, and that is the single largest unpriced engineering item in the program.

### 6.4 Multi-wafer

Pipeline across wafers, never tensor-parallel. Tensor parallelism across wafers requires a wafer-spanning collective per layer, which multiplies cross-wafer hops by orders of magnitude. Pipelining costs one crossing per stage boundary per token.

Consequences to model explicitly:
- Per-user latency is the sum of stage intervals; aggregate throughput is set by the stage interval alone (C10).
- Concurrency multiplies by stage count, which is usually favourable.
- KV shards by layer and never crosses a wafer boundary — only the activation vector does. Cross-wafer bandwidth is therefore small; only latency matters.
- Stage balance becomes a first-order concern.

### 6.5 KV tier

HBM, attached at the wafer perimeter. Two-tier by design where the model's attention mechanism permits it: keep the small, hot, O(L) indexer data on-die where the required bandwidth is unservable by HBM, and the large, cold KV bulk off-die where only the top-k gather touches it. This structure falls out naturally from sparse attention and should be exploited.

The beachfront limit (C8) is a hard structural constraint and is the main reason a wafer may need companion wafers for HBM capacity rather than for weight capacity.

### 6.6 Floorplan allocation rule

**Allocate ROM area from total parameters; allocate MAC area from active-parameter FLOP demand.** Do not allocate MAC from leftover area. Capacity-driven floorplans produce compute-starved machines on high-active-parameter models, and this error was made twice in the exploratory work. The dense portion of an MoE (attention projections, shared experts) occupies a tiny share of ROM but a large share of FLOPs, and needs MAC lanes provisioned accordingly.

---

## 7. Ranked uncertainties and ownership

From the sensitivity analysis. Regenerate with `tornado.py` once inputs are measured.

| Rank | Unknown | Owner | Settleable how |
|---|---|---|---|
| 1 | Engineering derate: MoE load imbalance, defect-repair indirection, clock skew, sync jitter, pipeline fill | **Us** | Trace-driven simulation |
| 2 | ROM read bandwidth per unit area at required port width | Foundry | SPICE, then test chip |
| 3 | MAC density achievable at required operand-delivery width | Foundry | Synthesis |
| 4 | Collective latency as a function of tile granularity | **Us** | NoC simulation |
| 5 | Target model's true per-token KV read volume | **Us** | Profile open weights |
| 6 | ROM cell density | Foundry | PDK, then test chip |
| 7 | HBM beachfront achievable | OSAT | Packaging study |
| 8 | Whether wordline-masked expert selection is viable | **Us**, then foundry | Circuit design |
| 9 | Reticle stitching yield and repair strategy | Foundry | Test vehicle |

**Four of the top five are ours to settle without a foundry NDA.** That should drive the sequencing.

Two observations from the sensitivity run that reorder intuition:
- The fabric question (rank 4) is *not* the critical path, despite appearing so early on. Its pessimistic and optimistic endpoints both leave a large advantage. It determines how good, not whether.
- No single unknown taken to its pessimistic bound eliminates the advantage. Only all of them simultaneously does. The program is therefore insuring against compound tail risk, not against a single point of failure.

---

## 8. Execution plan

Gated. Each phase produces reviewed artifacts, a requirements-traceability update,
and a go/no-go with explicit criteria. Architecture and specification precede
implementation RTL. Verification starts with the requirements and runs throughout
the program; it is not a testbench task appended after coding.

### 8.0 Engineering discipline and artifact control

This is a chip program, not a collection of demos. The following rules are mandatory:

- Every requirement receives a stable identifier and is traced to an architecture
  mechanism, implementation block, verification method, result, and any waiver.
- Every number is tagged `measured`, `published`, `derived`, `assumed`, or
  `synthetic`. A result cannot silently promote an assumption into evidence.
- Architecture models are executable golden references. RTL must match their
  externally visible behavior; performance models must consume measured RTL/NoC/
  circuit results as those become available.
- Interfaces, data formats, ordering, flow control, clocks, resets, power states,
  error behavior, repair behavior, debug, DFT, and observability are specified
  before implementation RTL is accepted.
- Changes after an architecture or interface freeze require an impact analysis and
  updated requirements, verification, performance, power, area, and schedule records.
- Generated results are reproducible from pinned inputs and tool versions. Waivers
  are explicit, owned, justified, and time-bounded; “tool limitation” is not a silent pass.
- Public-tool results are pre-NDA evidence only. They do not substitute for target-
  foundry libraries, ROM/HBM macros, extracted timing, commercial DFT/ATPG, signoff
  STA, EM/IR, SI, reliability, package, or foundry DRC/LVS.

The existing small RTL/circuit examples, if present before the architecture freeze,
are classified as **disposable feasibility scaffolds**. They may test a semantic idea
but are not an implementation baseline, do not satisfy a requirement by themselves,
and must not drive the architecture merely because code already exists.

### Phase 0 — Measure the target model
*Weeks. Trivial cost. No NDA. Start immediately.*

Extract from the open checkpoint: layer count, attention layer composition and ratio, compression factors, top-k, indexer dimensions, expert count and routing. Then **measure** — not estimate — per-token KV read volume across context lengths, and capture router traces for expert-selection statistics and load imbalance.

Deliverable: measured inputs replacing estimates in `infersim.py`, plus trace files for Phase 2.
**Gate:** ρ₁ at the target context, computed from measured K, exceeds the threshold below.

### Phase 1 — The two conversations
*Parallel with Phase 0. No cost.*

- **Model owner.** Will you commit this checkpoint for a multi-year service life? Everything downstream is contingent on this and it is the item most likely to kill the program.
- **Foundry business development, pre-NDA.** Two showstoppers: do you support via-programmed mask ROM, and will you support reticle stitching for a new customer?

**Gate:** both answers are yes, or a viable alternative party exists.

### Phase 2 — Requirements, architecture, and specification freeze
*Several months with system, architecture, circuit, NoC, physical-design, package,
DFT, DV, firmware, compiler, reliability, and operations owners participating. No NDA
is required for the first pass.*

No implementation RTL begins in this phase. Produce and review:

1. A system requirements specification covering Flash proof-vehicle and Pro product-
   target workloads at 200K/1M context, required batches, service-level latency,
   throughput, availability, power, cooling, cost, lifetime, and model-freeze policy.
2. An architecture specification defining tile/reticle/wafer/stage hierarchy; ROM,
   MAC, activation SRAM, KV/HBM and host memory responsibilities; interleaved weight
   layout; scheduling; collective algorithms; pipeline semantics; capacity accounting;
   and scale-up/scale-out boundaries.
3. Interface-control specifications for host, HBM, chiplet/wafer links, tile links,
   clocks, resets, interrupts, telemetry, debug, boot, configuration, and test access.
4. Exact numeric formats, quantization/scaling rules, accumulator widths, rounding,
   saturation, determinism, ordering, backpressure, deadlock freedom, and exception
   behavior.
5. RAS and repair specifications: ECC/parity boundaries, malformed-route handling,
   timeout/replay policy, spare rows/columns/tiles/links, defect maps, degradation,
   checkpoint identity/authentication, observability, and field diagnostics.
6. DFT requirements before floorplanning: scan domains and compression assumptions,
   memory/ROM BIST, JTAG/IJTAG access, at-speed test boundaries, repair loading,
   wafer probe, known-good-reticle strategy, burn-in, and package test.
7. Clock/reset/power intent: domain ownership, legal crossings, reset sequencing,
   clock gating, power gating if any, isolation/retention intent, DVFS states, safe
   shutdown, and thermal-throttle behavior.
8. A floorplan and budget specification with ROM/MAC/SRAM/NoC/repair/clock/power area,
   bandwidth, latency, frequency, power, thermal, HBM beachfront, bump, and package-
   escape budgets. Every budget carries optimistic/nominal/pessimistic values.
9. A firmware/compiler execution contract: model image identity, static schedule and
   timeslot generation, placement, routing masks, repair remapping, command queues,
   completion/error records, versioning, and reproducibility.
10. A verification plan and requirements-to-test matrix written with the architecture,
    including reference models, assertions, formal properties, constrained-random
    spaces, fault injection, performance tests, coverage closure, regressions, and
    acceptance thresholds.

**Gate:** a cross-discipline architecture review closes all blocking issues; every
must-have requirement is testable; interfaces and externally visible behavior are
frozen; performance/power/area budgets close at nominal and retain an explicit
contingency; no safety-, deadlock-, data-integrity-, DFT-, repair-, or package-critical
mechanism is left as “to be decided in RTL.”

### Phase 3 — Architecture risk retirement and open-PDK circuit work
*Runs in parallel workstreams after the Phase 2 architecture is coherent. No target-
foundry NDA is required.*

- Run cycle-approximate hierarchical NoC simulation (BookSim2/Garnet class or a
  validated purpose-built model), sweeping topology, tile granularity, link width,
  frequency, wire delay, arbitration, faults, repair detours, congestion, and tail
  latency with both synthetic and production traces when available.
- Perform trace-driven MoE load/stage balance and adversarial hotspot/deadlock tests.
- Design the via-programmed bitcell, decoder, wordline-mask path, sense path, repair
  indirection, and representative port on a legally compatible open PDK. Run extracted
  corners and Monte Carlo where the PDK/models support them; otherwise label the gap.
- Use OpenROAD/OpenLane-class flows and open standard-cell libraries for proxy PPA,
  congestion, clocking, power-grid, and timing experiments. These establish topology
  and methodology only, not target-node density or frequency.
- Build package/thermal/power-delivery spreadsheets or finite-element proxies with
  explicit boundary conditions; obtain an OSAT review before treating beachfront or
  cooling as feasible.

Exploratory synthesis may be used here to challenge architecture budgets, but it is
not implementation synthesis and cannot bless premature RTL.

**Gate:** the simulated fabric, circuit topology, repair scheme, package budgets, and
compound pessimistic sensitivity retain the required product margin. Any open-PDK
test macro has a documented mapping—and documented non-mapping—to the target node.

### Phase 4 — Implementation RTL and continuous verification
*Begins only after the Phase 2 specification gate. Verification is expected to be a
long pole and must be staffed accordingly.*

Implement bottom-up with versioned interface packages and machine-readable parameters.
For each block, the order is specification and reference model, assertions and test
plan, RTL, static checks, formal/unit verification, integration, then closure. Required
public-tool work includes, where supported:

- formatting and language-lawyer lint (Verible/Slang-class) plus Verilator warning-
  clean lint with reviewed, local waivers;
- independent elaboration/simulation with at least two engines (for example Verilator
  and Icarus) to catch tool-specific behavior;
- Yosys structural checks for undriven nets, latches, combinational loops, width/sign
  errors, inferred memories, multiply/accumulate structure, and parameter variants;
- assertion-based verification of protocols, ordering, masks, bounds, progress,
  credit conservation, pipeline alignment, repair remaps, and error containment;
- bounded/unbounded formal proofs with Yosys-SMTBMC/SymbiYosys and open SMT solvers for
  tractable blocks, plus cover properties that prevent vacuous proofs;
- constrained-random and directed tests against the executable golden model,
  including all legal numeric corner cases, reset at every pipeline phase,
  backpressure, simultaneous events, malformed commands, injected bit/link/tile
  faults, repair maps, and long-running liveness stress;
- functional, assertion, line, branch, toggle, FSM, and cross coverage where public
  tools support them; unsupported coverage is recorded as a gap, not reported as zero
  risk;
- structural CDC/RDC analysis supplemented by protocol assertions and deliberate
  metastability models. Public checks do not replace commercial signoff CDC/RDC;
- deterministic regressions with captured seeds, tool versions, logs, waveforms on
  failure, resource limits, and a triaged bug/waiver ledger.

Block, tile, reticle, pipeline-stage, and multi-stage verification environments are
separate closure levels. Performance tests check not only average throughput but
queue bounds, backpressure, head-of-line blocking, p95/p99 latency, hotspot traffic,
and degradation under repaired faults.

**RTL verification gate before implementation synthesis:** all must-have requirements
are traced to passing tests/proofs; zero unexplained lint/elaboration/structural errors;
all planned formal properties pass without vacuity; all planned functional bins close;
code/toggle/branch goals are met or individually justified; CDC/RDC crossings match the
frozen inventory; regressions pass across supported parameter sets and randomized
seeds; the reference-model equivalence suite is clean; no open severity-1/2 defect and
no unowned waiver remains.

### Phase 5 — Reproducible synthesis and open-PDK physical proxy
*After the Phase 4 RTL verification gate for the candidate baseline.*

Run reproducible technology-independent and open-library synthesis across parameter,
frequency, voltage/corner, and constraint sweeps. Check pre/post-synthesis equivalence
where public tooling supports the design. Preserve hierarchy and publish area/timing/
power contributors, inferred macro inventory, unconstrained paths, exceptions, and
constraint coverage. Then perform an open-PDK place/route proxy with floorplan,
congestion, CTS, extracted timing, antenna/density/DRC/LVS checks, and coarse IR-drop/
thermal experiments using only legally redistributable decks.

Do not scale one open-node result to a leading node with a single factor. Report it as
a methodology and topology check. ROM, HBM PHY, high-speed links, PLLs, sensors, ESD,
power delivery, scan compression, and other unavailable macros remain black-box risks
with explicit interface and budget models.

**Gate:** the verified RTL meets proxy constraints with contingency, synthesis and
simulation agree, no unconstrained or unreviewed exception remains, and all proxy-to-
target extrapolations are ranges with named evidence—not point claims.

### Phase 6 — Foundry/OSAT engagement and target-node re-baseline
*Begins after NDA; typically several months before a target-node RTL freeze.*

Replace every proxy library and macro with target collateral. Port and re-characterize
the ROM; obtain real SRAM/PLL/PHY/IO/DFT/package models; run target synthesis and
floorplanning; establish defect density and repair, reticle-stitching, mask-
personalization, direct-write, wafer probe, assembly, cooling, and reliability rules.
Re-run architecture and sensitivity gates with foundry/OSAT values before committing
to implementation scale.

Commercial signoff flows still required include target-qualified lint/CDC/RDC,
formal equivalence, DFT rule checking and ATPG/fault coverage, multi-mode multi-corner
STA with OCV, SI/crosstalk, extraction, EM/IR and power integrity, thermal/package co-
simulation, DRC/LVS/ERC/antenna/density/fill, reliability/aging/ESD/latch-up, and final
waiver review. Public tools cannot sign these off.

**Gate:** target-node PPA and physical closure retain product margin; test coverage,
yield/repair, personalization, package, power, cooling, reliability, schedule, and cost
are supportable; the model owner has made the checkpoint-freeze commitment.

### Phase 7 — Single-reticle target-node shuttle
*Typically 12–18 months after target engagement, depending on node and access.*

Build one reticle field before a stitched wafer. Include ROM characterization arrays,
mask variants, wordline masking, repair structures, clock/power monitors, representative
MAC/NoC paths, scan/MBIST/ROM-BIST, high-observability debug, and process monitors.
Pre-silicon verification, production test content, bring-up firmware, lab automation,
and correlation plans must be ready before tapeout.

**Gate:** silicon correlation closes against circuit, timing, power, thermal, repair,
test, and performance models within predeclared tolerances. Deviations are fed back
through the architecture model before any wafer-scale decision.

### Phase 8 — Wafer-scale product only after correlation

Reticle stitching, full-wafer repair, power delivery, cooling, HBM/package integration,
system firmware, compiler, production test, fleet RAS, security, and service operations
each receive independent qualification plans. A successful reticle is necessary but
not sufficient. Product authorization requires the complete foundry signoff record,
silicon-correlation report, manufacturing/yield plan, checkpoint commitment, business
case, and an independent design-readiness review.

### Sequencing rationale

Measure and architect before implementation RTL; verify before accepting an RTL
baseline; synthesize and physically probe the verified baseline before claiming PPA;
correlate a reticle before a wafer. Simulate before engaging deeply with foundries,
because four of the top five uncertainties are ours and precise questions produce much
better answers. Hold the two Phase 1 conversations immediately, because they are free
and either could end the program. Architecture, verification, and foundry conversations
overlap where they can, but their gates do not disappear merely to shorten the calendar.

---

## 9. Metrics and decision criteria

### Primary

| Metric | Definition | Why |
|---|---|---|
| **Advantage curve** | Cost per million output tokens, ROM vs GPU, **swept across batch** | Single-point comparisons mislead in both directions |
| **Speed-superiority band** | Range of batch sizes where ROM per-user throughput exceeds the *best achievable* GPU per-user throughput at any batch | If ROM is only cheaper, a price cut erases the advantage. If it is faster than any GPU configuration, that is a defensible product |
| **ρ₁ at target context** | Active weight bytes ÷ measured KV read per token | Target-selection screen; computable before any hardware work |
| **Binding constraint** | Which of C1–C11 sets the step time at each operating point | Tells you what to fix; a design bound by the wrong thing is mis-floorplanned |

### Secondary

Tokens per watt at matched per-user speed. Capital per concurrent user at target context. ROM area utilization (expect it to be low under high sparsity — the question is whether it is low enough to matter). Revenue per unit-year at published API prices, as a sanity check on whether the box earns back. NRE amortization as a share of cost per token at the volume actually expected.

### Comparison hygiene

These were violated repeatedly in the exploratory work and each violation changed a conclusion:

- **Compare against GPU cost, not GPU list price**, when the buyer is vertically integrated. Roughly two-thirds of a list-price advantage is vendor margin, not physics. Report both.
- **Enable speculative decoding on both sides.** The open competing stack exists; assuming GPUs without it flatters the case.
- **Match capacity, not unit count.** A comparison at equal GPU count but unequal concurrent-user capacity is not a comparison.
- **Use production operating points**, not dedicated-cluster figures. A single request occupying an entire cluster is a benchmark, not a deployment. This distinction accounts for order-of-magnitude discrepancies between first-principles estimates and observed production numbers.
- **Report per-user speed and cost per token together.** They trade against each other differently on the two architectures, and that difference — not raw speed — is the actual product claim.

### Threshold

The advantage against *GPU cost* (not list price), at the intended operating batch, with speculative decoding enabled on both sides, and with ROM per-user speed exceeding the GPU's best achievable per-user speed. A margin adequate to survive one GPU generation is the bar; below that, the program is betting on a lead that expires.

---

## 10. Risks

### Technical
- **Dynamic MoE routing versus static dataflow.** The cost advantage comes from compile-time-known traffic; data-dependent expert selection threatens it. The wordline-mask approach may dissolve this entirely, which is why validating it early matters so much.
- **Collective latency floor.** Batch-independent, so it caps per-user speed regardless of everything else. Sets the ceiling on the product claim.
- **Pipeline stage imbalance** in hybrid-attention models.
- **Wafer-scale integration** — stitching, cross-scribe power delivery, repair, cooling. Only one organization has done it.
- **Failure domain.** A wafer is a single unit; one failure takes down a model instance. Spare-wafer strategy required.
- **Beachfront limit** constrains KV capacity in a way GPU clusters do not experience.

### Commercial
- **Model churn.** Design and fab cycles are long relative to model service life. The program is a bet on architecture stability, not just on one checkpoint.
- **Sparsity trend.** Rising sparsity strands more ROM area. There is a sparsity ceiling beyond which the economics stop closing; find it and check the roadmap against it.
- **Software competition.** Model-system co-design on commodity GPUs is cheap, fast, improving, and partly open-sourced. It targets exactly the low-batch regime where ROM is strongest.
- **Demand concentration.** NRE amortizes only if one model carries sustained high volume. Better efficiency means fewer units sold, which works against amortization — a genuine tension worth modelling explicitly.
- **GPU generational improvement** erodes any advantage below roughly one generation's worth.

### Organizational
- **Checkpoint freezing.** A lab that revises weights continuously cannot commit to unpatchable silicon. This favours open-weight models and operators serving stable checkpoints, and disfavours frontier labs serving their own continuously-updated models.
- **Model owner and silicon owner must be the same entity or contractually fused**, since neither can strand the other's asset.
- **EDA licensing** dominates compute cost by a wide margin and should be budgeted first, not last.

---

## 11. Deliverables

**From the public pre-NDA work:**

1. Pinned model/hardware evidence inventories, executable analytical models, and
   regenerated advantage/cost/capacity curves with binding constraints.
2. System requirements, architecture, microarchitecture, interface-control, numeric-
   format, clock/reset/power, RAS/repair, DFT, firmware/compiler, floorplan-budget,
   verification, synthesis, and physical-proxy specifications.
3. A bidirectional requirements-traceability matrix linking requirements to evidence,
   architecture, RTL blocks, assertions/tests/proofs, coverage, results, bugs, and waivers.
4. CPU-capable routing/load-balance, stage-balance, NoC, fault/degradation, and
   sensitivity simulations, with synthetic and real traces never conflated.
5. Open-PDK ROM/read-path experiments and a documented target-node correlation gap.
6. Technology-independent implementation RTL only after architecture freeze, with
   golden models, assertions, formal harnesses, directed/constrained-random tests,
   coverage reports, CDC/RDC inventory, fault injection, deterministic regressions,
   and a bug/waiver ledger.
7. Reproducible verified-baseline synthesis and open-PDK physical proxies with complete
   constraints, reports, logs, tool versions, and explicit black boxes.
8. A pre-NDA readiness report that says which gates passed, failed, or remain impossible
   without a model owner, production traces, foundry/OSAT data, licensed IP, or a PDK.

**Expected after external engagement, in order:**

1. Production router/KV/runtime traces and measured GPU baselines.
2. Foundry/OSAT ROM, standard-cell, macro, link, HBM, package, thermal, defect, repair,
   test, yield, cost, and schedule inputs replacing every proxy.
3. Target-node re-synthesis, floorplan/implementation, DFT/ATPG, full commercial
   verification/signoff, and regenerated architecture/economic gates.
4. Single-reticle tapeout, production-test content, bring-up, characterization, and
   predeclared correlation report.
5. Only after correlation, a separately reviewed wafer-scale product plan.

**The model is the deliverable that matters.** Every number in the exploratory work should be regarded as provisional until regenerated from measured inputs. The value of what precedes this document is the structure — which constraints exist, which were forgotten, which direction each pushes, and which unknowns actually move the answer — not any specific figure.

---

## 12. Honest assessment

The physics are real: read-only storage is denser than SRAM, decode's access pattern is exactly the pattern a ROM serves best, and removing weight traffic from the memory tier is a genuine structural change rather than an incremental one.

The economics are model-dependent and sit on a small number of measurable quantities, all of which are now identified and most of which can be settled cheaply and without a foundry relationship.

The binding constraint is organizational. No amount of simulation resolves whether a model owner will freeze a checkpoint for years. That conversation is free, it gates everything, and it should happen first.

Finally: the exploratory analysis behind this plan produced a long sequence of corrections, and every one moved the estimated advantage in the same direction — downward — as omitted terms were priced in. The remaining unpriced terms are more likely to continue that pattern than to reverse it. Plan accordingly, weight the pessimistic bounds, and treat measurement as the point of the exercise rather than confirmation.
