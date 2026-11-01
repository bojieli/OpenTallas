Planned source review 2026-11-01 12:15:47 PST

Personally LOOK-viewed planned.png. PASS-CONDITIONAL for fresh synthesis/LEC and placement prototype only, then stop for actual placed LOOK. The frozen388.8x172.8 slot and5513 plan pins remain unchanged. Wide quarter-status/count bundles stay on their existing N/S faces; E output/control band and clock/reset entry remain as declared. No macro or macro wall, new external bus or pipeline stage is introduced. The native PDN recipe remains unchanged; its physical connectivity is not established by this pin-only diagram.

The inherited aspect2.25 is a frozen parent-slot constraint, not a new geometry choice or a blanket release waiver. No timing, routing, locality or arrival-band result is claimed. R1 adds no state. R2 A+B has68 declared selector bits across two SUs; removing unused bit0s and mergeable bit15s predicts about60 live FF, conservatively budget64 (~19.6um² vs19056.3um² mapped source). Each live mask bit drives at most21 data bits. Input widths, memory ports, cycle dates and source/control startup contract are unchanged. Fresh actual clock-sink census must cover every surviving new register.

Actual r2r/channel/pin/PDN and CTS geometry are normal later gates. No CTS/GRT/route is authorized by this pin diagram; fresh native whole-kit LEC remains required for the source-modified profiles.
