# DIE-LAYOUT-HBM 11-12: ot_svgr_top place PLAN failure (DPL-0036), paper form + delta (no build)

Failure: kit-wave hbm d44v ot_svgr_top attempt_7 (epyc8 .../d44v/items/ot_svgr_top/attempt_7/gen/ot_svgr_top_c26588462899),
3_5_place_dp: DPL-0036, 568 cells unplaced: 485 u_bout_sm_packet__nl, 56 u_bin_seam_read_data, 27 u_bout_sm_command__nl.
Utilization is only 37-39 % (PLACE_DENSITY 0.4), so this is not an area problem.

Cause (plan core_macros.json, ot_svgr_top): u_program_lo (1024x256 SRAM, 174.744 x 70.488) sits at (116.64, 8.64), R0.
Its 4.32-um halo meets the 4.32-um core margin, so 0 placeable rows are left between the S face and the macro.
The S face carries sm_packet (1099 pins, x 190.8-297.5) and sm_command (83 pins, x 108.6-301.4).
Each pin has 2 face registers (face_reg + negedge face_nreg).
The E strip beside the macro is 2.4 um (298.08 - 291.384 - 4.32), and seam_read_data (2048 E pins, y 4.3-200.9) needs it for y 4-83.
The outline (302.4 x 639.36) and the pins are fine; the core's macro floorplan, as given by the plan, conflicts with them.

Form (core-shape freeze kept: outline, pins and every macro's master/orientation unchanged; one macro moved):
u_program_lo (116.64, 8.64) -> (116.64, 434.7), R0, between u_desc_hi (top 386.64) and u_program_hi (bottom 552.96);
halo gaps 48.06 / 47.79 um; no halo clash with any macro. This frees the whole SE corner, x 112-298 by y 4-246, for the
S-face and E-face face registers. Clock 833 ps; the macro moves about 426 um farther from the S face (u_program_hi is already 553 um away).
The W-channel advisory (cache column at x 8.64, 4.32 < 10.8) is left as it is: no W-face cell failed.

Delta: svgr_delta.json (compose format, core_macros.json only, 3 ops; sha 3b657b52; epyc7 hbm-cut-1111/deltas/
svgr_top_programlo_dlhbm_1112.json). Applies on any plan that carries the d44v ot_svgr_top entry (checked on base0+d6e+scorer).
G0 550 -> 550, 0 new. The kit must be regenerated (macro_placement.tcl comes from core_macros.json), so it is a fresh gen + place.
Render: svgr_top_place.png (before | after, failing face buses coloured).
