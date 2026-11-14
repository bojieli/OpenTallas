# Unused BKSEL HLAT/R1C8 source profile

This is an additive, unused source package for the exact `bksel_vC8e` RTL that passed native equivalence. No existing recipe selects it. The active canonical and `bksplit_1108` source copies remain unchanged.

This package includes the existing HLAT implementation and the default-off `OT_BKQ_R1C8` control-copy option together. It is not a qualification of a new control-copy hunk against the older source that has no HLAT parameter. `profile.json` records the exact source order, include path, defines, black boxes, and top parameters used for the qualified form: `dsdv_bksel_q`, `OLL=2`, `RFH=2`, `HLAT=1`. Selecting that recorded profile enables `OT_BKQ_R1C8`; otherwise the source option remains off. Latency change is zero cycles.

The option gives each group of at most eight H2 payload bits its own kept replay/memory select registers and existing negative-level lockups. The original sign-control pair and every payload/control sampling edge remain unchanged.

`source_manifest.json` binds all 25 RTL files to the exact proved bytes. The explicit list is self-contained, including the macro black-box declarations. No constructor, floorplan, pin plan, clock steering, FIFO forwarding change, or automatic profile selection is included.

## Evidence

- Native record: E4 `/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC8e/lec/lec.json`; compact result and record digest are in `proof/native_lec_summary.json`. All 45,318 compare points proved, zero differences or undecided points. The native check used different synthesis and reference frontends.
- Focused actual H2-block miter: `proof/r1c8_probe.sv`. It passed 2,048 cycles covering 592 payload bits and 22 sign-control pairs. The deliberately wrong control copy produced 1,899 mismatches. Intel2 log: `~/s81-residual-logs/bksel_r1c8_exact_mutant.log`.
- The same native result was independently collected for the identical RTL in C8c and C8d. This is functional/source qualification, not physical signoff: the C8e layout still has the separately diagnosed input-hop setup and forwarding hold work.

The focused vehicle can be compiled with `iverilog -g2012 -s tb`; define `OT_BKQ_R1C8_MUT` for its negative control. Run simulations through the normal `ot-run` admission wrapper. A physical recipe must explicitly select the package and independently pass its normal constraints, layout review, clock contracts, native proof, and signoff gates.
