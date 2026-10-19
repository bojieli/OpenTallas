# S81 physical HBM clock correction

The PHY has a 900 ps minimum period. Its clock and the 16 controller ckh pins previously shared the 833.333 ps core root, despite the existing asynchronous FIFO boundary. The binding contract now declares ck_hbm at 900 ps; controller core logic and every streaming path keep 833.333 ps. The die generator applies the same contract to netlist and STA clocks.

The bound-netlist check in binding.json found one PHY and 16 controller instances, with all ckh pins on ck_hbm and controller clk pins on core roots. A missing physical domain port is rejected. This is a binding check, not a die timing closure claim.

SS reports remain sensitivity only. A generated-classifier regression with TT/FF windows +5/+6 ps and SS -100 ps preserves the SS sensitivity and keeps the TT/FF window PASS.

The prior physical chain at ot-epyc5 /srv/opentallas-scratch/claude/s81die8/case_p4l3_rv finished 2026-10-18 19:38 with GRT rc 3 before global routing: forwarded-clock audit 122/3112 mismatches. All prior outputs remain preserved.
