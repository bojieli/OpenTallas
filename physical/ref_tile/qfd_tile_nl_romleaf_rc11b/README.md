# qfd_tile_nl_romleaf_rc11b -- A0 ROM leaf rc11 (QW-CB16A0-3 10-20) = qfd_tile_nl_romleaf_rc10b + Codex land32 V6 source, ALL landing data SINGLE-CYCLE

CRITICAL (A0): gate + coordinator review only (no REVIEW.json, no submit).
Structural change vs qfd_tile_nl_romleaf_rc10b: (1) sources ot_qwen_rom_tile_w12_land32.sv / ot_qwen_w12_matvec_land32.sv / ot_qw_land4_n32(_select).sv
(Codex d458ed683): landing writers bounded to <= 32 loads per same-edge copy (reset rqd split from pointer/valid), split-tier
2/3 mux consumers on the same-edge 4-bit copy (SPLIT_CP under REGROOT 9); 0 added data/reset edges, +6 t_out vs REGROOT 8
retained (priced). (2) land_mcp.sdc REMOVED: every u_qlw* -> u_qlr* path is timed single-cycle (ROOT 07:32: no data MCP).
Everything else (floorplan, macros on 43.2, pins, fences, regions, CTS roots, io_hold) identical to qfd_tile_nl_romleaf_rc10b.

## Safe-design checklist + pre-gate native census
1 Pins: PASS (unchanged rc10: all pins registered, reset 2-stage landing).
2 Reach: unchanged rc10 floorplan; gate measures placed reach.
3 Fanout: V6 full NK native census (actual ORFS synth, gate libs/flags) PASS max 32 / 148,004 roots / 0 violations / 0 role
  errors (ep5 full_native/orfs_r5/native_census.json); rc10 failed 155/685 (writer slot enables / reset). NL: in-flow census
  (limit 32, refuse) is the first NL measurement -> a WARN hiding a violation = FAIL.
4 Depth: unchanged rc10 (REGROOT 9 landing = registered).
5 Storage: weights in ROM / SRAM macros; landing rings 4-slot (contract D4).
6 Floorplan: unchanged rc10.
7 Clock: regional roots ck / ck_dw / ck_de / ck_tx[g]; crossings now single-cycle timed -> gate --cts must show TT/FF pin-flop
  spread <= 80 per root and setup/hold >= 0 WITHOUT MCP. If single-cycle fails: structural repartition / clock design (never MCP).
8 Schedule: static; +6 t_out (results/arch/qw_a0_land32_0720/latency.json).
Bench: V6 full positive tb_full_rr9_n32 PASS checks 29899 (MUT0); MUT60-65 all FAIL (ep5 full_proof_v6/run_6x.log).
