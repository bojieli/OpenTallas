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

## Measured points so far

The first case has two preserved implementation points. These are measurements
of the exact signed-integer proxy RTL, pinned flow, nominal ASAP7 TC libraries,
and declared constraints—not generic frequency estimates for OpenTallas.

| Case | Requested period | Result | Setup WNS / TNS | Hold WNS / TNS | Routed checks | Reported fmax |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| `numeric_e1_l16_tc` | 1.25 ns (800 MHz) | FAIL | -2.12138 / -50.0845 ns | +0.202679 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 296.614 MHz |
| `numeric_e1_l16_tc` | 4.25 ns (235.294 MHz) | PASS | +0.136856 / 0 ns | +0.805138 / 0 ns | 0 DRC; 0 antenna; 0 unconstrained | 243.123 MHz |

At the passing point, the flow reports 632.335 um^2 of standard-cell area,
1,644.62 um^2 of core area, 10,832 um of routed wire, and 42,366 vias. Both the
mapped and post-route proofs cover 38 named points and report exact
equivalence. The complete DEF, GDS, ODB, SDC, SPEF, logical netlists, reports,
and proof artifacts are archived under
`results/asap7_physical/numeric_e1_l16_tc/`.

This result is marked `canonical: false` because unrelated concurrent work
made the primary worktree dirty. The selected RTL was independently
hash-locked and unchanged, so it is valid intermediate evidence, but it does
not close the campaign's clean-baseline gate. The final three-case results must
be regenerated from a clean committed worktree. The 1.25 ns failure is kept
separately under `results/asap7_physical/diagnostics/` so a relaxed passing
constraint cannot erase the failed target.

## Claim boundary

ASAP7 is a realistic predictive academic PDK, not a manufacturable foundry kit.
Its numerical results have no calibrated error bar against TSMC N7 or N4. A
passing run is therefore reproducible predictive digital evidence, not an N7
silicon measurement. It does not validate ROM density, sensing, read energy,
PVT margin, full-array current, package, HBM, power delivery, thermal behavior,
yield, repair, or cost.
