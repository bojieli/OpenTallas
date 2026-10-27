# HBM-CORES-R6 (2026-10-27): collar FF reference + slew, EP probe false success + rp2 re-kit, KITS-1 collect

## 1. collar_idx256r (R5 attempt 3 NOT SIGNED)
* Root cause ff_ref_missing (CHECKED): `physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py` dropped `insertion_ff_ps`
  from the kit's `sdc_lint.json` (stale comment: "only lint() keywords"; `lint()` takes `insertion_ff_ps`). signoff.py
  then had no per-corner bound and timed FF hold against the single TT vclk, while the flow repaired against OT_VCLK_FF.
* Fix (shared tools): the generator keeps `insertion_ff_ps` (drops only `insertion_basis`); `sdc_lint.lint_kit_files`
  fails closed pre-synth when config.mk `OT_VCLK_FF` and `sdc_lint.json insertion_ff_ps` are missing or disagree.
  Tests: `tools/die_plan/test_sdc_lint_ff_binding.py` (6) + test_sdc_lint + test_signoff, 88 PASS. The new check
  flags the actual R5 collar kit (regression evidence).
* Re-sign-off of the attempt-3 ROUTED view with the binding (kit sdc_lint.json + insertion_ff_ps 202.5, main signoff.py):
  NOT SIGNED. TT setup +16.06; FF hold -1.42 ps / 3 endpoints (was -22.31 / 1231 against the TT vclk; outputs prm/pw_data);
  slew 65 TT / 41 FF; lec_superset FAIL (the R5 kit lec.py wrote no `all_shown`: n_extra 0 receipt, pre-ROOT-MERGE-30).
* Slew root cause (probe log collar_a4/attempt3_slew_net2568_probe.log): net2568 = BUFx3 place2569 at (33,76) driving 12 AO21
  loads spread over x 13-68 / y 7-34 (28.7 fF wire). GRT-RC repair_design saw 0 violations; routed RCX 358 ps = GRT->RCX gap.
* Attempt 4 (collar_a4/config.mk): SLEW_MARGIN 20 (all repair_design steps), OT_HOLD_FF_MARGIN 5 -> 10 (data-path hold
  repair, 12.4a a1), kit sdc_lint.json with insertion_ff_ps 202.5, routed LEC with main lec.py (writes all_shown). Clock and trunk unchanged.

## 2. EP repack
* The outer rc 0 was false because probe.sh echoed PROBE_GRT rc and exited with the place/CTS rc. Fixed ep_rp2/probe.sh: the exit code is
  the GRT probe's. PASS needs OT_PROBE_GRT_DONE + GRT-0096 + total overflow 0 at ITERS >= 50, else it exits non-zero with
  PROBE_VERDICT FAIL|ERROR. grt_probe.tcl reads the std-cell liberty before setRC and exits 3 on any setup error.
  Negative test: negtest_probe_grt.log (missing ODB -> outer rc 3, PROBE_VERDICT ERROR).
* rp2 kit = gen_core_kit_hbm.py on QUAD5 planU5e_r ep_N0 table (sha 2548bdf764f2: sd_rx/sd_tx/rx_pin_flit/tx_frame all E face
  M4; 4 instances ep_N0/S0/S1/N2) + the rp1 SRAM re-pack verbatim. Clock pin: the plan entry (125.28,185.76) lies over SRAM1
  (y 121.50-199.28) in the rp1 pack and is off the M5 track. The rp1 centre-band entry (125.256,204.66) is kept as .048x.48
  (TRIAL; QUAD5 must move the plan entry).
