QC A0 helper measurement only; NOT a SIGNED/release contract.
Historical source views: intel2:/srv/opentallas-scratch2/claude/qc-plan/a0r/nk_r4/src/physical/ref_tile/
  qw_a0_rc14_children/node_nb1/ot_qwen_tile_node/{ot_qwen_tile_node_tt.lib,insertion.json}
  ot_qwen_tile_romleaf/views/ot_qwen_tile_romleaf/{ot_qwen_tile_romleaf_tt.lib,insertion.json}
  qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1/{ot_qwen_tile_lsl_fp1_tt.lib,insertion.json}
Measured boundary means TT/FF (ps): node245.9/199.6 (2058), romleaf206.9/173.9 (529), lsl165.7/133.9 (272).
All TT means below250ps; node ETM maximum267.63058 must not create17.63058ps early tap.
core_clock_contract.load(...,require_signed=False) explicitly diagnoses historical records;
strict default requires SIGNED matching mean; missing means, wrong view and wrong design fail.
First-route explicit budgets can use from_budget(lib,{pin:{tt:ps,ff:ps}},source), unsigned.
A view-local clock_contract.json binds selected liberty SHA and source/basis per corner.
Existing early_core_taps.add API stays legacy MAX_BOUND until batched adoption.
New add_from_means API and gen_phys.core_latency_files(mean_contract=True) are opt-in.
No RTL/cycle/SDC changes or P&R/STA launched for this helper.
