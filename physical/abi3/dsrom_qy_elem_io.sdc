# DS-V4.1 ROM q-element QY routes (2026-10-04, design-owner decision): the W10 ping-pong multicycle (unchanged, from
# v41_w10_elem_pp_multicycle.sdc) plus the record of the corrected output hold budget.
#
# Output budget derivation (passed to the driver as --output-delay-min-ns / --output-delay-max-ns):
#   the outputs are captured by a sibling q element whose boundary registers sit behind the same clock insertion as
#   this block's.  The capture-edge offset of a port is that sibling's insertion AT THE CORNER BEING CHECKED:
#     setup (SS):  the sibling's SS insertion, as before (max -0.193 ns, unchanged);
#     hold  (FF):  the sibling's FF insertion: -0.322 ns (the FF clock latency of the free-clock boundary register
#                  g_qb.b_go measured on routed R_cap0, 321.8 ps; SS 553.2 ps).
#   The previous runs applied -0.56 ns (the sibling's SS insertion, 555.9 ps) to the FF hold check: a constraint bug
#   (infeasible for any RTL: FF/SS delay ratio 0.56 against the 0.646 the pair of budgets required).  Hold signoff is
#   at FF only, so the single -min value is the FF one.  Setup 60 ps and hold 25 ps uncertainty are unchanged; the
#   input budgets (0.36 / 0.727 ns) are unchanged.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]
