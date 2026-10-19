# Comparison core physical failure

Native comparison gate qfd_io_collective_safe_lattice completed FAIL on ot-epyc5 at2026-10-19T09:26:59-0700. Exact source snapshot and errors are pinned in physical/ref_tile/qfd_io_collective_safe_lattice/gate_result.json; floorplan PNG in gate_layout was visually inspected.

The actual TT root clk pin-flop spread is451.7ps, boundary scope6628 of10196 sinks, exceeding80ps. This is the clock failure criterion; the separate10190-flop/large-outline advisory does not replace it. No FF/native linked signoff or routed TTsetup/FFhold acceptance is claimed. CTS terminal error is preserved in cts.log. Raw-clock wire429um is a reported clock concern, not a measured maximum data route.

This comparison keeps inherited off-lattice raw SRAM origins. The distinct734.4x1036.8 all-R0/all43.2-grid qfd_io_collective_safe_r0 gate continues independently. No source edit, CTS knob retry or delay mask was applied. The direct cmd_free combinational status boundary remains an independent structural contract issue, documented in regional_model.
