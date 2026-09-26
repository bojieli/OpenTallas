# ASAP7 predictive physical campaign

This campaign implements selected OpenTallas public RTL through synthesis,
floorplanning, placement, clock-tree synthesis, detailed routing, parasitic
extraction, and final GDS generation in the public ASAP7 platform carried by a
pinned OpenROAD-flow-scripts container.

It is deliberately separate from the SKY130 custom-ROM work. The campaign does
not modify, consume, or scale any SKY130 result.

## Reproduce

The runner requires Docker and the immutable image recorded in
`configs/pdk/asap7_physical_lock.json`. If it is not already present, pull the
exact digest printed in that file. Then validate every executable and platform
file before starting a long run:

```bash
python3 tools/run_asap7_physical.py --check-only
```

Run one case while developing:

```bash
python3 tools/run_asap7_physical.py --case numeric_e1_l16_tc
```

The locked ASAP7 Liberty files declare time in picoseconds. OpenROAD therefore
also interprets the generated SDC in picoseconds: the runner multiplies every
governed `clock_period_ns` value by 1,000 before writing `create_clock` and I/O
delays. Both the requested nanoseconds and emitted picoseconds are recorded in
each result. This conversion is an audited part of the campaign; a bare SDC
value of `1.25` would mean 1.25 ps, not 1.25 ns.

A governed clean-baseline campaign runs all cases without `--allow-dirty`:

```bash
python3 tools/run_asap7_physical.py
```

`--allow-dirty` is available only for useful intermediate work while unrelated
concurrent sessions own the working tree. Such a result is source-hashed but is
explicitly marked noncanonical and cannot close the clean-baseline gate.

## Initial scope

The three initial cases are a 16-lane signed-integer DV dot product, a 64-term
scaling point, and an eight-source tagged reduction endpoint. They constrain
cell area, achievable timing, routed wirelength, congestion, and extraction for
those exact public RTL blocks.

They do not implement the target MXFP4 × FP8, FP8 × FP8, BF16, FP4-index, or
FP32 datapaths. They also contain no ROM or SRAM macro. All FakeRAM and SRAM
names are forbidden in source and generated logical netlists.

Every passing case requires:

- locked source, container, executable, liberty, LEF, GDS, RCX, and DRC hashes;
- RTL-to-mapped and RTL-to-final sequential equivalence;
- zero setup and hold violations at its declared clock;
- zero detailed-route DRC and antenna violations;
- final DEF, GDS, ODB, SDC, SPEF, and Verilog artifacts; and
- a placeholder-memory audit proving FakeRAM was not used.

The numeric blocks are feed-forward apart from their output registers. Their
equivalence check replaces every RTL and mapped output register with its next
state, requires zero remaining sequential cells and zero combinational SCCs,
then asks the pinned ABC executable to prove every named observable point.

The reduction endpoint is stateful. It uses an exact one-step transition-
relation proof over inputs, current state, outputs, and next state. The RTL has
634 state bits and the mapped design has 620. The 14 removed bits are governed
aliases: `expected[g][1:7]` equal `expected[g][0]` for each of the two groups.
No other state mismatch is accepted. The proof also establishes and preserves
that relation across reset. Mapped ASAP7 flops that expose an inverted `QN`
state receive an explicit, audited polarity bridge before comparison. For both
methods, the AIGER interfaces must have unique, identical symbol-name sets;
post-route port reordering is therefore matched by name rather than position.

## Measured timing points

Each case has a preserved failed target and a measured passing target. These
are measurements of the exact proxy RTL, pinned flow, nominal ASAP7 TC
libraries, and declared constraints—not generic frequency estimates for
OpenTallas.

| Case | Requested period | Result | Setup WNS / TNS | Hold WNS / TNS | Routed checks | Reported fmax |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| `numeric_e1_l16_tc` | 1.25 ns (800 MHz) | FAIL | -2.12138 / -50.0845 ns | +0.202679 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 296.614 MHz |
| `numeric_e1_l16_tc` | 4.25 ns (235.294 MHz) | PASS | +0.136856 / 0 ns | +0.805138 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 243.123 MHz |
| `numeric_e4_l16_tc` | 2.00 ns (500 MHz) | FAIL | -7.60565 / -217.837 ns | +0.361685 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 104.105 MHz |
| `numeric_e4_l16_tc` | 12.00 ns (83.333 MHz) | PASS | +0.0413225 / 0 ns | +2.36354 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 83.6213 MHz |
| `reduction_s8_g2_tc` (stale) | 1.25 ns (800 MHz) | FAIL | -0.870789 / -15.3251 ns | +0.0565153 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 471.523 MHz |
| `reduction_s8_g2_tc` (stale) | 2.25 ns (444.444 MHz) | STALE | +0.0534617 / 0 ns | +0.0557746 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 455.262 MHz |

| Passing case | Standard-cell area | Core area | Routed wire | Vias | Mapped / post-route proof |
| --- | ---: | ---: | ---: | ---: | --- |
| `numeric_e1_l16_tc` | 632.335 um^2 | 1,644.62 um^2 | 10,832 um | 42,366 | 38 / 38 named points equivalent |
| `numeric_e4_l16_tc` | 2,603.30 um^2 | 6,790.42 um^2 | 80,823 um | 202,497 | 38 / 38 named points equivalent |
| `reduction_s8_g2_tc` (stale) | 845.509 um^2 | 2,240.22 um^2 | 22,184 um | 61,473 | 687 / 687 transition points equivalent |

**The two `reduction_s8_g2_tc` rows are stale.** They route the serial-chain
reduction that commit `4690d6ce` replaced with balanced per-group add trees
hoisted out of the clocked process, which is a synthesised-logic change.
`70604b86` later added only a comment and a Verilator lint pragma. The lock
names the current `rtl/ot_reduction_tree.sv`, and declares the archived record
stale under `archived_evidence`. The runner shows that record as STALE and
does not count it. Re-qualification was attempted on 2026-09-26 and did not
close: the flow stopped at the mapped transition-relation proof, before place
and route (see the lock for the measured engine results). The current tree
has been routed only by the ungoverned `tools/run_abi3_physical.py` lane
(`results/physical_abi3/asap7/operating_points/reduction_s8_g2_2p25.json`),
which carries no gate-level equivalence proof.

The 12-ns scaling-point target was selected from the 2-ns run's extracted
9.629-ns worst data arrival and then reimplemented; it was not estimated from
the smaller block. The reduction target was likewise selected from the
1.25-ns run's 2.188-ns worst arrival. The small positive passing margins make
the selected periods measured closure boundaries for these runs. They do not
imply that a pipelined implementation should use the same periods.

The results falsify an important analytical shortcut: the current one-cycle,
unpipelined proxy RTL does not support the 0.8-1.1-GHz whole-product clock
assumptions used in exploratory system envelopes. Pipelining and architectural
restructuring must be implemented and physically remeasured before such a
frequency can enter a performance claim.

The complete DEF, GDS, ODB, SDC, SPEF, logical netlists, reports, and proof
artifacts are archived under each passing case directory. Failed targets are
kept separately under `results/asap7_physical/diagnostics/` so a relaxed
passing constraint cannot erase a failed point.

The final passing runs are marked `canonical: true`. All three were regenerated
in one campaign from a clean detached worktree at commit `bc8089f`, after the
periods and failed targets were committed. Since the reduction source changed,
the aggregate record reports `all_pass: false`, `all_canonical: false`,
`stale_cases: ["reduction_s8_g2_tc"]`, and 2/3 current passing cases. The
clean-baseline gate holds for the two numeric proxy blocks only; it
does not broaden the evidence boundary below.

## Claim boundary

ASAP7 is a realistic predictive academic PDK, not a manufacturable foundry kit.
Its numerical results have no calibrated error bar against TSMC N7 or N4. A
passing run is therefore reproducible predictive digital evidence, not an N7
silicon measurement. It does not validate ROM density, sensing, read energy,
PVT margin, full-array current, package, HBM, power delivery, thermal behavior,
yield, repair, or cost.

## Why the comparison is ASAP7 against N7 silicon, and what would close it

The density and frequency comparisons in
[`../docs/DATAPATH_PIPELINE_REDESIGN.md`](DATAPATH_PIPELINE_REDESIGN.md) and
`tools/audit_chip_level_density.py` put routed ASAP7 blocks against a fabricated
A100 on TSMC N7. That is an asymmetric comparison and it is deliberate, because
the symmetric one is not available:

* **A foundry N7 PDK cannot be used here.** It is distributed under NDA, cannot be
  committed to a public repository, and cannot be re-run by anyone reading this.
  Every result in this project is required to be reproducible from the repository
  by a third party, and an NDA PDK is the one input that makes that impossible.
* **ASAP7 is the accepted substitute for exactly this purpose.** It is a 7 nm
  predictive PDK built by ASU and ARM to let academic work reason about a 7 nm
  FinFET node without foundry access. It is the standard vehicle in published
  accelerator work for the same reason it is used here.
* **The node family matches; the confidence does not.** ASAP7 has no calibrated
  error bar against N7. So a ratio between a routed ASAP7 block and A100 silicon
  is a comparison of *two models of a 7 nm-class part*, and the ASAP7 side is a
  prediction. It is not a silicon result and no amount of place-and-route makes it
  one.

### What this does and does not license

It licences a statement about **design structure**: that a pipelined,
carry-save, output-stationary datapath with hardware descriptor fan-out lands
within an order of magnitude of a same-generation GPU's arithmetic density, rather
than three orders away, and that the previous unpipelined design did not. That
conclusion depends on ratios between blocks measured in the *same* flow, and it is
robust to a uniform ASAP7-to-N7 offset because such an offset cancels.

It does not licence an absolute figure. "0.768 TFLOP/s per mm²" is what this flow
predicts for this design on this predictive PDK. The true N7 number could be
meaningfully different in either direction, and nothing here bounds by how much.

### What would close the gap

In descending order of value, and none of them are RTL work:

1. **Route the same RTL on a foundry 7 nm or 5 nm PDK** and publish the ratio to
   the ASAP7 result, not the absolute numbers. One such ratio would calibrate every
   ASAP7 figure in this repository at once. Needs foundry access; the *ratio* is
   publishable even when the PDK is not.
2. ~~**Route on a second open node and check the trend.**~~ **Done, for three
   changes.** See below.

### The second-node check, done

The worry that ASAP7 might be *flattering these particular changes* — that a
predictive PDK could reward removing a carry chain more than a real node would — does
not need foundry access to test. SKY130 is a **fabricable** 130 nm open PDK sharing
nothing with ASAP7: different library, different metal stack, different device
generation, roughly an order of magnitude slower. Each change was re-routed there
end to end, before and after
(`tools/audit_cross_node_reproducibility.py`):

| change | ASAP7 | SKY130 | agree to |
|---|---:|---:|---:|
| normalise cascade → leading-zero count | 1.39× | 1.77× | 1.28× |
| combinational → five-stage pipeline | 3.95× | 5.06× | 1.28× |
| serial accumulation → balanced tree | 2.83× | 2.56× | 1.11× |

All three reproduce. The area ratios are the sharper evidence: the balanced tree
lands **0.73× the area on ASAP7 and 0.72× on SKY130**, and the LZC restructure
roughly halves area on both. A PDK artefact would not track that closely.

The tool also **measures** the assumption the ratio argument rests on instead of
asserting it. "A uniform node offset cancels out of a within-node ratio" is only
sound if the offset is roughly uniform, so the offset is computed on the same design
across both nodes: spread **1.54× across six measurements**. That is moderate rather
than tight — it weakens the argument somewhat without overturning it, and the number
is published so a reader can judge by how much.

**This is still not an N7 calibration.** Two open nodes agreeing shows a change is
about circuit structure rather than about one PDK. It says nothing about what TSMC N7
would measure.
3. **Add a power and thermal budget.** The A100 sustains 312 TFLOP/s inside 400 W.
   Nothing in this project is power-constrained, and an unconstrained design can
   always win on area. This is probably the largest unmodelled term in the
   comparison and it is fully reachable with open tools.

