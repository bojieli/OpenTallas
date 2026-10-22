# qfd_n59_qbank13a (QE3-N59 10-21) -- structural successor of qbank12a

Failures fixed: qbank12a gate FAIL clock_rule (one TritonCTS root, 13,775 sinks over 950x475 um, TT/FF pin-flop spread
166.9/145.6 ps > 80; GRT RC0 overflow 0; packet 93cfaede1); qbank12b gate FAIL GRT-0183 net39744 (read-result cone net,
125.7 um span in the 55.6-um channel just below SRAM row 1, driver M2/M4/M6 saturated; packet 626bba997 / 8e7f037db).
RTL / params / benches identical to qbank12a (rtl/qwen_split/qfd_native59_qbank.sv cfdf2a1c, QB_WLOCAL=1, 47c14228d).
Geometry: 950.4 x 518.4 (12a + middle row channel 55.6 -> 98.8 um; row-1 macros +43.2); col channels 38.2/81.4/38.2 as 12a (12a GRT RC0 overflow 0); macro fill ~48 %. Macro halo 5.4 um.
Clock: "clock": "spine" -- pre-placed balanced clock spine (physical/common_flow/clock_spine.tcl): sinks binned into
<= 8-sink leaves (60-um bins), each SRAM clk pin its own leaf (OT_SPINE_MACRO_LEAF=1), recursive bisection tree of
macro-avoiding repeated L edges, leaves padded to equal MEASURED arrival (3 rounds) => regional leaf trees per macro
column / channel, no single sink-driven tree. Same mechanism closes dma_core_m5_window (11.1k sinks, clock PASS).

## SAFE 8-point review
1 Pins: flop-first RTL unchanged (i_* S face, o_* N face), pin bands centred on the central channel; reset landing 2 x32. PASS
2 Reach: S face -> w1 -> w2 (beside macro) -> pins, two registered hops <= ~720 um Manhattan to the far macro. PASS (gate measures)
3 Fanout: <= 32 loads per driver (native census PASS max 32 on 12a, RTL unchanged). PASS
4 Depth: w2 -> macro pin wire only; 12a placement-RC diag macro->reg -206 / reg->reg -129 ps: CHECK at CTS gate (route repair)
5 Storage: 8 x 32x546 SRAM macros on the 43.2 lattice, std-cell channels between every macro column/row. PASS
6 Floorplan: outline enlarged (above), channels >= 38.2 um everywhere, middle row channel 98.8 um. PASS
7 Clock: balanced spine (regional leaves, equal measured arrival) replaces the 166.9-ps single tree. CHECK at --cts gate
8 Reset: only ce (valid) reset; data/mask/addr unreset; reset landing 2 stages x32 copies. PASS
