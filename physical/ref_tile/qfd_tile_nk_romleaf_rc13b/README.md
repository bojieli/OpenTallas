# qfd_tile_nk_romleaf_rc13b -- A0 ROM leaf rc13 (QW-A0-13 10-21) = qfd_tile_nk_romleaf_rc11b (+ rc12 k-means cluster roots) + L9 ring writers fenced on the operand-root side

CRITICAL (A0): gate + coordinator review only (no REVIEW.json, no submit).

## Why (measured, rc12 gates 10-20/21)
rc12 (k-means cluster roots + padding on ck_dw/ck_de) 4 gates: NK rc12 CTS PASS (dw 72.7 / de 72.3 TT, live in post-CTS
analysis); NK rc12b FAIL ck_de 89.2; NL rc12 FAIL ck_de 97.1 (dw 78.1); NL rc12b clocks PASS (dw 42.6 / de 25.2) but DPL-0033
(91 overlaps) after ~60k hold buffers.  Spread is placement-luck dependent because ck_dw / ck_de own TEN masses over
266 x 517 um (per-sink dump scratch/qw-cb16r/dump): gutter operand column (L1 ring readers + mq_wrom + csel, 2,728 FF at
x 216-230), hub g_tx9.tc copies (512 at x 395-431), and the eight per-leaf L9 ring WRITERS (u_qlw2w / u_qlw2e, 381 FF each)
that rc11's FREE land_rings group let GPL put beside each READER ck_tx[g] (x 348-482, y 146-663).  Padding all clusters to
the latest arrival also pushed insertion to 612-930 ps.
## Change (fences only; same RTL / ports / pins / outline / cycles)
tools/qwen_romleaf/rc13/<kit>_regions.tcl: the L9 writers leave the FREE group and get one EXCLUSIVE block per operand root in
the centre channel beside the hub (dwr x 376/377-387.6/388.4, der x 446-457.4, 340 um tall, centred on the hub; free lanes kept
to the tx lanes and the hub; NK dwr stops 1.2 um short of the node child).  The L9 landing ring (ot_qw_lw slots on the
operand root, ot_qw_lr read on ck_tx[g], K=2, D=4) now sits ON the region boundary: write side compact with the operand root,
read side beside the leaf; bank + vld (4 x 64 + 12 wires a leaf and side) run inside the centre channel (<= ~340 um, within the
405 um reach; no LSL-column crossing).  Each operand root becomes 2 compact masses (gutter column + hub block) instead of 10;
the rc12 k-means cluster roots stay for balance (small pads now).  Ring sizing: D=4/K=2 tolerates +-1 cycle (833 ps) of phase;
measured inter-root phase after entry compensation is within-root spread (<= 80 ps) -> margin > 700 ps.  0 added cycles.
## Safe-design checklist + pre-gate native census (unchanged from qfd_tile_nk_romleaf_rc11b (+ rc12 k-means cluster roots) unless stated)
1 Pins: PASS (rc10/rc11: all pins registered, reset 2-stage landing).
2 Reach: ring bank wires hub block -> reader <= ~340 um (< 405); gate measures placed reach.
3 Fanout: V7 source unchanged -> NK full native census PASS max 32 / 148,004 roots / 0 viol; NL in-flow census rc11/rc12 PASS max 32.
4 Depth: unchanged (REGROOT 9 landing = registered; ring read = 4:1 AND-OR + wire into the reader register).
5 Storage: unchanged (weights in ROM/SRAM macros; 4-slot landing rings).
6 Floorplan: macros/children unchanged on 43.2; two new EXCLUSIVE writer sub-lanes (seq fill ~0.23-0.25 of capacity).
7 Clock: FIXED structurally -- ck_dw / ck_de regions compacted to 2 masses (writers moved to the operand-root side of the L9
  ring); k-means cluster roots kept; other roots unchanged (rc12 measured ck_rn/rs/rsw/rnw 15-79, ck_tx 14-37, ck_fa 6-9 ps).
  Crossings L1 (rsw/rnw -> dw) and L9 (dw/de -> ck_tx[g]) are the existing 4-slot landing rings, timed single-cycle (no MCP).
8 Schedule: static; 0 added cycles; rc11 +6 t_out pricing retained.
Bench: source identical to rc11 V7 (full positive tb_full_rr9_n32 PASS 29899; MUT60-65 FAIL; results/arch/qw_a0_rc11_1020/v7_proof).
