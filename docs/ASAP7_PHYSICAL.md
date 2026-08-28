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
| `reduction_s8_g2_tc` | 1.25 ns (800 MHz) | FAIL | -0.870789 / -15.3251 ns | +0.0565153 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 471.523 MHz |
| `reduction_s8_g2_tc` | 2.25 ns (444.444 MHz) | PASS | +0.0534617 / 0 ns | +0.0557746 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 455.262 MHz |

| Passing case | Standard-cell area | Core area | Routed wire | Vias | Mapped / post-route proof |
| --- | ---: | ---: | ---: | ---: | --- |
| `numeric_e1_l16_tc` | 632.335 um^2 | 1,644.62 um^2 | 10,832 um | 42,366 | 38 / 38 named points equivalent |
| `numeric_e4_l16_tc` | 2,603.30 um^2 | 6,790.42 um^2 | 80,823 um | 202,497 | 38 / 38 named points equivalent |
| `reduction_s8_g2_tc` | 845.509 um^2 | 2,240.22 um^2 | 22,184 um | 61,473 | 687 / 687 transition points equivalent |

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

The development passing runs are marked `canonical: false` because their lock
periods were being tuned in a dirty auxiliary worktree. The selected RTL was
independently hash-locked and unchanged, so those runs are valid intermediate
evidence, but they do not close the clean-baseline gate. All three final cases
must be regenerated from a clean committed worktree at the frozen periods.

## Claim boundary

ASAP7 is a realistic predictive academic PDK, not a manufacturable foundry kit.
Its numerical results have no calibrated error bar against TSMC N7 or N4. A
passing run is therefore reproducible predictive digital evidence, not an N7
silicon measurement. It does not validate ROM density, sensing, read energy,
PVT margin, full-array current, package, HBM, power delivery, thermal behavior,
yield, repair, or cost.
