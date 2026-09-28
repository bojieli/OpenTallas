# Registered Qwen O4 scale-ingress cut

This is a follow-up physical probe, not a production `ot_hdc_matvec` change.
The ROM macro output (or a staged local HBM scale word) enters an unconditional
256-bit `raw_scale_q` capture register, then a common `scale_q` register. The
completed FP32 sums receive the same extra stage. The group read signal drives
the ROM chip enable and a local valid flop, rather than a 256-bit data hold
mux. Two 16-lane directed beats match the direct probe exactly after a
one-cycle shift, in both source modes.

Both modes use the same 16 FP32 multipliers, 240 × 240 µm outline, 0.92 ns
clock, 184 ps min/max input arrival, 184 ps output delay and pre-placement
fanout repair. The ROM cut includes one analytical 8192×266 macro. Its
centered placement has a macro-edge blockage, and `check_placement -verbose`
passes for both modes. The HBM cut starts at a staged local 256-bit word;
its controller, PHY, stack, 128 PC-local arbiters, 35-bit return tags,
cross-PC lane rotation and prefetch storage are outside this cut.

| ASAP7 global-route result | ROM source | Staged HBM source |
| --- | ---: | ---: |
| Source to raw capture, setup | +61.99 ps | +979.87 ps |
| Source to raw capture, hold | +629.66 ps | −171.15 ps |
| Group enable, setup | +1025.19 ps | +981.82 ps |
| Group enable, hold | −185.73 ps | −109.90 ps |
| Worst complete core setup | −690.21 ps | −324.98 ps |
| Worst complete core hold | −414.38 ps | −183.86 ps |
| Movable cell area | 5368.823 µm² | 5368.823 µm² |
| Analytical ROM macro area | 14629.499 µm² | 0 µm² |

The registered data path resolves the measured source-capture and enable
**setup** misses in the direct cut. The staged-HBM cut has now completed
detailed route with zero DRC violations. Its extracted source-to-raw-capture
setup is +925.00 ps, while source hold is −112.58 ps. Group-enable setup is
+934.12 ps and hold is −62.92 ps. The complete cut still misses 0.92 ns
setup by 114.13 ps on an internal register path, core hold by 33.41 ps at
the externally constrained completed-sum input, and reset removal by
20.73 ps. The ROM detailed route remains active. The source-pinned
`results/physical_hdc/asap7/qwen_o4_scale_ingress/registered/physical.json`
binds the measured paths, placement checks, DRC result, routed source report
and final ODB/SPEF hashes. The staged-HBM source still excludes the controller,
PHY, stack and prefetch; its 184 ps arrival remains an assumed condition.

The production matvec's synchronous scale word currently feeds `ot_hdc_fmul`
directly. Before adding this stage, its actual scale-word producer, completed
sum producer and multiplier consumer must be placed and timed together. The
extra cycle must shift result tag, valid, fault and writeback timing and pass
the exact post-TP scale test. The present 184 ps arrival is a test condition,
not an IO budget derived from that integrated path. No chip rate, energy or
ROM/HBM ratio follows from this cut.
