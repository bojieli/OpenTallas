# QC-A0-KITS-3 parent: measured A0 NK/NL parent CTS insertion (one native ck, centre entry) -- 2026-10-28

Run dir intel2:/srv/opentallas-scratch2/claude/qc-a0-kits-3-1028/parent/{nk,nl} (ORFS make cts, openroad/orfs:asap7lock, via ot-run).
Inputs: Codex parent synth sources codex-qc-a0-2157/parent_rawcut{,_nl} with VERILOG_DEFINES = -DSYNTHESIS only
(OT_A0_CK_TAPS* removed; the tap ports had no RTL loads -> same 64,205 / 61,550 cells); children = Codex fixture
codex-die-qc-0359-1028/a0_child_fixture (placement-RC trial ETMs with min/max_clock_tree_path, at_exact origins);
ck = ONE M5 pin at (228.972, 578.88) (centre, track-snapped); parent PDN = fixture parent_{nk,nl}_pdn.tcl with M6/M7
stripe width 0.12 -> 0.16 (0.12 is an illegal M6/M7 width, PDN-0114: fixture defect); RC = fixture setRC_rcx.tcl
(same as the child ETM export; it carries no # OT_RC_CAL record). Data pins: E face, place_pins (UNCHECKED vs plan).
CTS = ORFS default TritonCTS (BUFx24, sink clustering, macro tree + register tree, SKIP_CTS_REPAIR_TIMING=1).
Measurement: propagated clock, estimate_parasitics -placement, per-corner STA (measure.tcl); total to child flops =
parent arrival at child clk pin + child internal register insertion from fixture ck_{tt,ff}.json (mean/min/max).

| | parent regs TT mean (min..max) | child pins TT | child flops TT mean (min..max) | FF regs mean | FF child flops mean |
|---|---|---|---|---|---|
| NK (15,013 regs, 19 children) | 619.2 (557.5..729.9) | 378.6..589.5 | rom 624.5 / raw 636.1 / node 669.9 (527..755) | 507.5 | 525.6 / 528.1 / 552.0 |
| NL (13,982 regs, 18 children) | 605.5 (549.4..774.5) | 366.1..522.1 | rom 618.3 / raw 584.7 (519..711) | 494.8 | 514.0 / 481.7 |

Cells after CTS: NK 86,912 / NL 79,429 (incl. resizer 6,779 / 5,233 buffers, IO buffers 2,343 / 801, CTS 1,446 / 1,395).
vs 12.14 estimate (UNCHECKED, NK 325-394 TT / NL 294-378): measured ~+230 ps higher. Cause: the estimate counted only
the child pins; the parent itself has 15.0k / 14.0k glue registers spread over the 457.92 x 1157.76 outline, and the
default TritonCTS (10-11 buffers per path, 3 levels) balances every sink to the slowest; register skew in the parent
alone is ~170-225 ps TT. This is the DEFAULT-CTS number, not a plan-built trunk; a 12.8 plan trunk/mesh is required.
No hold, route or A0 boundary FF hold number (no IO/vclk context in this trial SDC).
