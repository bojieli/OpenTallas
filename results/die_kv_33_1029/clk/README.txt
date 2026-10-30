DIE-KV-33 2026-10-29 KV-006 clock check on the actual die source GRT0 (die-kv-32 src_phy access.odb; GRT settings = grt_loaded.tcl, re-run in-session).
Runs intel1:/srv/opentallas-scratch2/claude/die-kv-33-1029/clk. Readout = DIE-KV-26 combo recipe (vclk on root, 3 fF tap loads, rise+fall per tap).
BASE (clk.tcl): legs max 304.4 um, 0 >405 (legs.json); spread TT 490.7 / FF 447.8, 112/105 of 128 regions >150; duty 1775 TT / 1869 FF taps
  outside 45-55; MPW 0; clock-pin slew max 490 (clock_check.json, duty.json) -> FAIL.
ROOT CAUSE (probe3.py on grt.odb + route.guide): provider FFs on 1232 trunk legs; OpenROAD grt isNonLeafClock(): FF-loaded clock nets routed as
  signals -> 1124/1124 long leaf legs on M1-M5 only; 12767/12767 long non-leaf legs on M8/M9.
WHAT-IFS (estimate only, unlegalized centroid placement): B x16 pair: spread 120.3/111.5, duty FF 317 outside; B2 x5p33 pair: 88.4/81.9, duty 0,
  21 clock-pin slew viol; B3 x5p33->x16: 88.4/81.9, duty 0, clock DRV 0 (max provider CLK slew 317.8).
Provider DATA DRV: 9126 TT max-slew violations (drv_TT_head.rpt), open.
