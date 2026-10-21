# qfd_tt_head_static_h16u -- h16t successor (QW-H16T 10-20), TOK.QW.LAYER.3.SEG head leaf

h16t gate FAIL (4 fail, all cross_clock; within-root spread 61.1/58.5 TT/FF PASS, GRT overflow 0, native census 32):
the eight head SRAMs were clocked from raw entries ck_pm0 (u_22617 + 4 FIFO banks) / ck_pm1 (u_22618 + 2 FIFO banks)
while all 7,908 flops sit on ck_head.  Every SRAM read/write was a direct reg<->macro path between roots:
ck_head->pm0 -111.1 (wd_in[53]), ->pm1 -21.8, pm0->ck_head -378.1 (rd_out[194] -> prog_q), pm1->ck_head -137.1 ps
(TT, signoff.sdc, 150-210 ps distinct-entry reserve).  Owner clock rule 10-20 08:55 forbids direct reg->reg paths between
regional clocks.

Analysis (placement-RC path reports on the h16t CTS ODB, scratch qwh16t_paths/p2 on ot-pve1):
- the SRAM "regions" are artificial: the parent qfd_tt_ctlm_dv u_hr drives .ck_head(ck), .ck_pm0(ck), .ck_pm1(ck) from
  the SAME net; ck_pm0/1 carried 5/3 raw macro sinks inside a 345.6 x 302.4 um leaf (below the 405 um reach), and the
  parent had to add 159/143 ps source latency to align them with ck_head (OT_ENTRIES COMP).
- a landing ring cannot sit between a register and a synchronous SRAM pin without moving the SRAM's address/data/CE
  registers onto the SRAM root (a new flop region) and adding >=2 edges to every program-store and FIFO access
  (prog_q read timing PRL2 and the FIFO two-edge-ahead read prediction would both be re-derived in RTL).
Fix (structural, 0 edges): ONE clock region.  results/rtl/qw_head_safe32_1020/h16u/make_1r.py deletes the two raw entries
from the committed bound_r4 native32 (module header + 2 port decls + 2 clock assigns; the 45,930-cell netlist is otherwise
byte-identical, sha in h16u/record.json) and clocks the SRAMs from ck_head.  One CTS root reaches 7,908 flops + 8 SRAM
clock pins; no region crossing remains, so no ring and no calendar offset; the 80 ps spread applies inside the region.
Parent: drop .ck_pm0/.ck_pm1 on u_hr (the bench vehicle prepare_bench.py does exactly that).

Known next blocker (NOT a clock issue, measured on h16t CTS ODB, ck_head->ck_head): ~30 endpoints u_224xx/u_178xx at
-280..-345 ps TT through a 40-level AND/AO21 ripple chain (u_22384 -> u_1769..u_2090 -> u_22470; ~1090 ps of logic).
ABC variant scripts (r4b/r4c) stayed at 40 levels: needs RTL pipelining / a prefix structure of that cone (README of
h16t: rom_cmd 37, fixed_issue sched_q 36 / cycle 33, ctrl_me dts_all 32 levels) before route timing can close.

## SAFE-DESIGN checklist
1 Pins: flow pin registers ON (ck_head); reset landed by the kit (2 stages) -- PASS (as h16t, census reset 1 sink)
2 Reach: 345.6 x 302.4 leaf, no wire > 405 um planned; gate measures -- gate
3 Fanout: bound_r4 load-cap 16; h16t gate native census PASS max 32 (same cells) -- PASS
4 Depth: 40-level ripple cone -345 ps TT (see above) -- OPEN (RTL successor owed)
5 Storage: FIFO in 6x 32x128 SRAM + 2x 64x512 programme store -- PASS
6 Floorplan: h16t geometry (8 macros on the 43.2 lattice), fill 38% lattice/pin-bound (E face 68% pin demand) -- WARN
7 Clock: single CTS root ck_head (flops + 8 SRAM clock pins), no region crossing; spread <=80 TT/FF -- gate
8 Schedule: 0 added data edges vs h16t; reset release +2 (constant, as h16t) -- PASS
Benches: img0/imgh PASS + BMUT3 FAIL on Verilator 5.050 with the 1r netlist (bench_witness/).
