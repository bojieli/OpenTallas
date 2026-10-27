# HBM-CORES-R8 (2026-10-27) -- base claude/hbm-cores-r7-1027@1531b26cb4

## collar_idx256r attempt 4 max-slew root cause (CHECKED, routed 6_final.odb + spef probe, scripts/slew_driver_probe_tail.tcl)
All 32 TT violators sit on 8 nets: bank9 net2565/2566/2568/2569/2574, bank4 net2486/2491, bank8 net2557.
Each = cd[k] (INVx1 _15xx_ at the N edge, y~76) -> placement-repair BUFx3 place25xx (src=TIMING, next to the INV, y 74-77)
-> 12-13 AO21 A2 payload-word loads spread over x 8-73 / y 7-76 (most at y 7-40). Not dont_touch (net/inst dt=0), not clock.
Routed length 158-205 um per net (DEF), ~80 % on M2/M3 (scripts/deflen.py). GRT-stage repair_design -slew_margin 20 saw
1 slew violation in the whole design: setRC_rcx.tcl is calibrated on clock nets and (its own caveat) under-estimates
signal-net C on M2-M5, so GRT RC slew < 256 ps while RCX is 330-369 ps. SLEW_MARGIN cannot close a ~45 % estimate gap.
## Fix (attempt 5): wire-length repeater insertion at placement (POST_RESIZE_TCL = collar_a5/max_wire_repair.tcl,
repair_design -max_wire_length 60). Trial on a4 3_4_place_resized.odb: 297 nets / 608 buffers (L=40: 455 / 1245);
every failing net split (net2568 13 -> 2 iterms). Clock/trunk unchanged. Flow-level note for FLOW lane: signal-net C under-estimate in setRC_rcx.tcl.
