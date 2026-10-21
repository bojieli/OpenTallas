# qkd_kvs_pc_h_sr10 (KV-PC10 10-20, structural successor of qkd_kvs_pc_h_sr9 after a failed route)

Why: route qkd_kvs_pc_h_sr9-sr9-596963735 (ot-epyc7) NEEDS_RTL: TT +53.5 / FF hold -57.0 ps (477 D pins, TNS -4.86 ns) / DRC 5.
Classification on its 6_final.odb (routed parasitics, FF):
- every worst hold path is a 1-gate flop -> flop path whose CAPTURE leaf is late: hclk removal ot_rrs_*u_port_hr_q -> u_port_v1
  RESETN -57.0 (leaf_895 101.8 ps), front_co[107] -> u_return.hd[81] -55.8 (leaf_914 102.0 ps vs 25 ps on the launch leaf),
  core_clk es_merged -> es_d_q -32.2.  Both late leaves (sinks at x 77-87) hang off H-tree tap clkbuf_7_14__f placed at
  (39.4, 69.7), WEST of column A (banks x 43.2-75.0): with M5 the top layer no horizontal wire crosses a bank (M2/M4 blocked),
  so the routed tap->leaf net detours to the nearest end/gap of the 5-bank stack (CTS estimated a straight wire).
  GRT then showed FF -51.6 and the loop skipped GRT hold repair (OT_HOLD_STOP carried over from the CTS stall).
- DRC 5 = M4 shorts on ONE net: net22951 = return-ring w_addr_in[1], a 110 um wire buffer down the stacked banks' pin face.
Fix (floorplan, RTL = r8 528d8460a unchanged, census r8/r9 PASS max 32): column A holds only front + return (10 banks) in
groups 3 / 2 / 3 / 2 (bases y 23.76 / 99.36 / 155.52 / 228.96) with three 21.5-23.6 um routing channels; the 2-bank tag
queue moves to column B, abutted on top of the CDC up stack (R0, read face W toward the centre).  No horizontal wire is
more than ~26 um from a channel through column A (was up to 45 um).  Kit otherwise = sr9 r9 (SKIP_GATE_CLONING/BUFFER_REMOVAL).

## SAFE-DESIGN checklist
1 Pins: PASS (= sr9: RTL pin stages; reset lands in 2 registered stages, 2 RESETN loads per port).
2 Reach: PASS by sr9 pin order (placed reach on PC_H sr9: 8 pairs 405-465 um, kick-word feed-through, accepted); recheck on gate.
3 Fanout: PASS, native census r8/r9 max 32 (same RTL); this gate's census is the receipt.
4 Depth: = sr9 (textbook ~607 ps WARN, timing decides; TT setup +53..+137 on sr9 route/gate).
5 Storage: PASS (23 SRAM banks).
6 Floorplan: FIXED: column A split into 4 groups with >= 21.5 um channels (gen channel rule), tq abutted in column B;
  util ~33 % waived (pin-bound die frame, fill_reason); faces <= 6 pins/um.
7 Clock: H-tree taps no longer detour around 5-bank stacks; io_hold_margin 0.03; spread checked on the CTS gate.
8 Schedule: static, 0 added edges.
Benches: = sr9 r8 receipts results/rtl/qwen_kv_die/kvpc_sram_sr9_1020 (Verilator 5.050, same RTL).
