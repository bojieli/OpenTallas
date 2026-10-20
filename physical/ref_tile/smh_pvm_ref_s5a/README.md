# smh_pvm_ref_s5a -- PVM distributed source (H.STA.BLK.14.3.1, L2H-SMATT/PVMD 10-19)
Parallel twins smh_pvm_ref_s5a / smh_pvm_ref_s5b (same RTL). Bind the first to close; cancel the other.
Why: smh_pvm_ref_s4a (SAFE2) CLOSED but carried the waived single-source ev / tag_d[14] input-pin capture (~1,500 loads);
the coordinator rejected that waiver. RTL ot_hbm_sm_pv_merge_distributed (+_core): Codex fae1ece6e reviewed and fixed,
see results/arch/hbm_pvm_distributed_source_1019/README.md.
Floorplan: 345.6 x 302.4: macro (171.3 x 153.9, R180) at x 86.4 / y 43.2; W band 84 um, E band 86 um beside the two data-contact faces, N band 103 um (s4a geometry, CLOSED TT +50.14 / FF +8.16); single centre root.
SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS (source-registered) -- every input captured at the pin in RTL then kept second copies; every output one RTL
  register; flow pin_regs OFF with reason (a flow reg would add a third input edge). Reset: RTL lands rst_n in 2 stages
  (2 first -> 8 second) then 54 third-level groups; flow reset_landing OFF with reason.
2 Reach: PASS -- pin->first capture anchored at the pins (io_flop_at_pins), copies drive band-local cones (gate PNG check).
3 Fanout: FIXED -- fleet census (flow keep hook): every register outside the shared fp32 adder <= 32 loads; kept copies
  survive (keep_hierarchy paramods + keep). WAIVED: ot_hdc_fp32_add_lat internals (a1_swap 142 ...) = the closed shared
  adder, identical in s4a (CLOSED); a fanout-safe adder leaf is a separate item.
4 Depth: PASS -- SAFE2 core (operand registers, LAT7 adders), 8-bit slice selects shorten the operand cones.
5 Storage: PASS -- 32,768-bit stack = one 64x512 p192 SRAM; no new indexed storage.
6 Floorplan: PASS/WAIVED -- macro on the 43.2 lattice, std bands at both contact faces + N, continuous rows; util low
  (macro-bound) WAIVED as s4a.
7 Clock: PASS -- single centre root (s4a spread 27.8/26.7 ps); io_hold_margin 0.03.
8 Schedule: PRICED -- +1 input/result edge (DS +40 cycles/token 0.0069%, Qwen +72 0.0057%; price.json) + 1 cold release
  edge; benches exact/tight/reassert/stopclk/xrand PASS vs SAFE2 at +1 age; 12 mutant witnesses FAIL.
smh_pvm is not a critical prefix: submit after a clean gate.
