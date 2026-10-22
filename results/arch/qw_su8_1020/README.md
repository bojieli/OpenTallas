# QW-SU8 10-20: slice2 SU control leaf qfd_dv_s5_su8_rst3 (kits qfd_dv_s5_su8 main / qfd_dv_s5_su8b fallback)
Source: Codex e4f168a75 (codex/qw-suvm8-pickup-0720) SU8 = SUVM7 control minus VM (VM8 group) and BTAB payload, with the
rst3 reset (rs0 -> rs1 two-stage landing + kept local leaves, 2 raw reset contacts). Adopted under OWNER 10-20 09:05
(reset only control/valid; datapath unreset; standard equivalence, no native formal); header comment updated only.
Bench r4 source 7253acb58 (Verilator 5.050, fleet ep5, bench/): lockstep vs SUVM7 control projection with priced delays (c_su 2 -> 6):
MUT0 zero-init PASS 11,787 compares; MUT0 --x-initial unique PASS (control/valid bits every cycle, full vector after
first start); MUT1 wrong stride FAIL 11,757; MUT2 early accept FAIL 23,102 (witnesses run_1_0.log / run_2_0.log).
Pre-gate native census r1 source (native/, Codex recipe; the IN-FLOW gate census refused r1-r3, fixed r2-r4 -- see gate_r1/): PASS 0 > 32, max 32, rst_n 2 loads, 4,655 FF,
26,993 cells, 2,895.37 um2, depth 470.1 ps / 15 lv, textbook PASS (no in->out, reset landed 2).
SAFE checklist: see tools/ref_tile/specs_qw_su8/*.json safe_design_checklist (1-8 PASS; 6 pin-bound util 13-14%).
Price (NOTICE TOK.QW.SCHED): command/record visible c_su +4 (2 -> 6); reset release +1 boot edge; BTAB bypasses SU.
r2-r4 (gate_r1/): in-flow ORFS census refused r1 (stride accept mux 33-52 loads), r2 (ABC-pushed selects 93-112), r3 (9 selects 35-40) -> r4 per-lane kept stride enable register + own pin copy + 16 select replicas: gate r4 in-flow census PASS max 32 / 0 violations.
