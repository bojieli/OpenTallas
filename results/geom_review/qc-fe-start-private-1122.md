# West FE +2 START geometry review, November 22

**ISSUES.** I viewed the actual closed placement from the private `slw_fe_v2__cle312294d` +2 START arm on Intel1. The middle of the tile contains a narrow, heavily loaded strip while 73.84% of the area is empty. The footprint is 622.08 by 1831.68 µm, 5.09% filled, with no macros. The 3,539 unregistered face bits and 6,556 register paths over 405 µm persist. The whole-placement reader completed at unit `1245257-1795379959`; the separate legacy setup read was +23.21 ps.

The three largest transport findings are `u_bound.u_core.se` to `u_bout_x_stm_o` at 1,117.53 µm across 544 bits, ring `u_cland_x_st_b_i` to its input register at 951 µm across 256 bits, and `u_cland_dd_ei` to its input register at 850 µm across 548 bits. The retained START arm stops before CTS and routing. Keep its latency result for the source fix and use the placed scan to design the next physical form.

Exact kit `intel1:/srv/opentallas-scratch2/claude/qc-plan-r12/fe_start_place/slw_fe_v2__cle312294d`. Viewed files `intel1:/srv/opentallas-scratch2/claude/qc-plan-r12/fe_start_place/read/{review_density.png,review_pins.png}`. The same directory contains the raw geometry and the scan.
