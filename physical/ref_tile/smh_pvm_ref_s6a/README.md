# smh_pvm_ref_s6a -- PVM distributed source (H.STA.BLK.14.3.1, L2H-SMATT/PVMD 10-19)
Parallel twins smh_pvm_ref_s6a / smh_pvm_ref_s6b (same RTL). Bind the first to close; cancel the other.
Successor of smh_pvm_ref_s5a/s5b (same geometry): s5 gates WARN/GRT0 but census FAIL (160 adder roots); r4 source fixes it.
Why (s5): smh_pvm_ref_s4a (SAFE2) CLOSED but carried the waived single-source ev / tag_d[14] input-pin capture (~1,500 loads);
the coordinator rejected that waiver. RTL ot_hbm_sm_pv_merge_distributed (+_core): Codex fae1ece6e reviewed and fixed,
see results/arch/hbm_pvm_distributed_source_1019/README.md.
Floorplan: 345.6 x 302.4: macro (171.3 x 153.9, R180) at x 86.4 / y 43.2; W band 84 um, E band 86 um beside the two data-contact faces, N band 103 um (s4a geometry, CLOSED TT +50.14 / FF +8.16); single centre root.
SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS (source-registered) -- every input captured at the pin in RTL then kept second copies; every output one RTL
  register; flow pin_regs OFF with reason (a flow reg would add a third input edge). Reset: RTL lands rst_n in 2 stages
  (2 first -> 8 second) then 54 third-level groups; flow reset_landing OFF with reason.
2 Reach: PASS -- pin->first capture anchored at the pins (io_flop_at_pins), copies drive band-local cones (gate PNG check).
3 Fanout: PASS -- r4 (HBM-SMATT5 10-20) FAN32=1: Codex-qualified LAT7 native fan32 adders replace the waived shared-adder
  internals; r3's 8 bp decode roots (41..43) fixed by per-reader kept bp role counters. MANDATORY native32 census (042aa171b,
  actual 5 TT Liberties + SRAM Liberty, keep hook): PASS, 63,873 roots, max dynamic loads 32, 0 violations, 0 role errors,
  reset drivers included; mapped sha256 581dfaa1..., 78,003 cells / 16,019 FF / 9,058.9 um2 std
  (results/arch/pvmd_native32_1020/r4). No waiver.
4 Depth: PASS -- SAFE2 core (operand registers, LAT7 adders), 8-bit slice selects shorten the operand cones.
5 Storage: PASS -- 32,768-bit stack = one 64x512 p192 SRAM; no new indexed storage.
6 Floorplan: PASS/WAIVED -- macro on the 43.2 lattice, std bands at both contact faces + N, continuous rows; util low
  (macro-bound) WAIVED as s4a.
7 Clock: PASS -- single centre root (s4a spread 27.8/26.7 ps); io_hold_margin 0.03.
8 Schedule: PRICED -- +1 input/result edge (DS +40 cycles/token 0.0069%, Qwen +72 0.0057%; price.json) + 1 cold release
  edge; benches exact/tight/reassert/stopclk/xrand PASS vs SAFE2 at +1 age; 12 mutant witnesses FAIL.
smh_pvm is not a critical prefix: submit after a clean gate.
