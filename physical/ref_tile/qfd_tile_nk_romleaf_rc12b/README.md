# qfd_tile_nk_romleaf_rc12b -- A0 ROM leaf rc12 (QW-CB16R 10-20) = qfd_tile_nk_romleaf_rc11b + ck_dw / ck_de regional clock distribution

CRITICAL (A0): gate + coordinator review only (no REVIEW.json, no submit).

## Why (measured)
rc11 x4 gates FAILED only on the glue operand roots: ck_dw TT pin-flop spread NK 124 / NL 190.6 ps (ck_de, never reached by the
gate, measured NK 272.8 / NL 144.7 ps).  A CTS rerun on the rc11 placed ODBs with a per-sink dump (results/arch/qw_a0_rc12_1020)
shows every ck_dw/ck_de sink MASS is tight but the masses are spread over 266 x 517 um: the 15-um operand column (L1 ring reads +
mq_wrom, 2,728 sinks; internal 100-245 ps under one tree), the s2_w copies at the hub (512, 3-15 ps) and the eight per-leaf L9
ring writers beside ck_tx[g] (381 each, 5-30 ps); one TritonCTS tree over the field put the masses 100-270 ps apart.
## Change (buffers only)
tools/qwen_romleaf/rc12/ck_km_split.tcl splits each of ck_dw / ck_de into 14 compact k-means clusters (one BUFx24 local root each);
ck_km_cts_nets.tcl hands the cluster nets to TritonCTS (one short tree per cluster) and pads the cluster roots to equal MEASURED
latest arrival (STA, placement parasitics; coarse HB4xp67 then fine BUFx2), as clock_spine.tcl does for its leaves.  Same ports,
clocks, flops, SDC, fences, pins, outline, cycles.  Rerun on the rc11 ODBs: ck_dw NK 124 -> 26.9, NL 190.6 -> 27.9 ps; ck_de NK
272.8 -> 36.8, NL 144.7 -> 29.8 ps (TT); insertion mean +100..150 ps (crossings into/out of ck_dw/de are the existing 4-slot
landing rings; L1 into ck_dw, L9 out to ck_tx[g]).
## Safe-design checklist + pre-gate native census (unchanged from qfd_tile_nk_romleaf_rc11b unless stated)
1 Pins: PASS (rc10/rc11: all pins registered, reset 2-stage landing).
2 Reach: unchanged floorplan; gate measures placed reach.
3 Fanout: V7 source unchanged -> NK full native census PASS max 32 / 148,004 roots / 0 viol; NL in-flow census rc11 PASS max 32.
4 Depth: unchanged (REGROOT 9 landing = registered).
5 Storage: unchanged (weights in ROM/SRAM macros; 4-slot landing rings).
6 Floorplan: unchanged (macros on 43.2, fences rc11).
7 Clock: FIXED -- ck_dw / ck_de regional distribution (above); other roots unchanged (rc11 measured ck_rn/rs/rsw/rnw 13-62,
  ck_tx 16-30, ck_fa 7-9 ps).  Single-cycle crossings (no MCP).
8 Schedule: static; 0 added cycles (buffers only); rc11 +6 t_out pricing retained.
Bench: source identical to rc11 V7 (full positive tb_full_rr9_n32 PASS 29899; MUT60-65 FAIL; results/arch/qw_a0_rc11_1020/v7_proof).
