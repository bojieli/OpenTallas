# Full-grid R0 core actual clock failure

qfd_io_collective_safe_r0 native gate on ot-epyc7 reached CTS and failed actual TT glue-root clk pin-flop spread277.3ps (>80ps). Boundary scope6628 of10196 sinks, noFF/native linked TTsetup/FFhold acceptance. Raw SRAM clock-entry wires are147.71065..147.75697um with native Liberty arcs retained; all17 hard entries remain independent. These clock wire lengths do not prove maximum data-route reach or pin access/DRC.

The734.4x1036.8 candidate uses all17 R0 child origins on43.2um lattice, eight folds/nine rawSRAMs and full-width softband950.4..1036.8. This removes the comparison's inherited off-lattice rawmacro origins; the actual glue-clock ownership still fails. The comparison candidate failed451.7ps; neither is acceptable. No placement/CTS knob retry, delay mask or live-source retime was applied. Structural core ownership remains open, including cmd_free status boundary and actual CRC/fault ownership contracts in regional_model.

Native CTS log preserved here; source-bound gate_result/floorplanPNG in physical/ref_tile/qfd_io_collective_safe_r0 are collected separately. No REVIEW.json or submit.

Floorplan PNG visually inspected after terminal copyback:17 children, fill46.3%, N1127 pins over386.9um(53%), W2271 over864um(83%), E3293 over812.2um(78%), S0. Full-width y950.4..1036.8 is free of child macros; inherited flow OT_PK_FRAC0.5/ABOVE_ONLY confines soft placement above the half-height boundary, not exclusively to that free strip. Actual top/boundary density and structural clock ownership still need a new model; no claim of a physically qualified production view. TrialGRT also produced no congestion table (rc2); linked cross-clock analysis incomplete. Gate generated2026-10-19T10:02:03-0700.
