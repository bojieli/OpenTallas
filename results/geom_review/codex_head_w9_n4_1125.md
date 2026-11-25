# HEAD W9 hd_st_n4 placed review

Viewed the exact detailed-placement layout and density renders from epyc12 `HEAD-W9-FP/hd_st_n4_1125121013`, plan `96f94e38b8d4`.

**BAD, keep route held.** The macro-free 959.04 × 993.6 µm block has a continuous central corridor. Boundary flops form thick west bars near y140 and y680, peaking at 76.3% local occupancy. The rendered southeast reset and run entries drive branches north and west. The position-spread audit shows 732.6 µm for `u_rst_in` and 732.4 µm for `u_run_in`. The detailed placed branch trace is running in `head-allfix/w9_cut_1125/n4_placed_branches` to measure those branches through buffers. The static C27 fix closed the raw-export legs.
