# HC root SAFE 1 (HBM-HC5 10-20, H.STA.BLK.1.1): SRAM mix store

Source cf412ecc2 (claude/hbm-hc5-1020).  Landed d4g smoke params (XRD/XRU 11, XRDQ 060b060b, XRUQ 050a070b, QDRLY 2),
Verilator 5.050, rtl/test/run_hbm_hc_root_landed.sh with HC_SAFE env (fleet ot-epyc5):
- bench_s0m0: SAFE 0 regression, HC_ENG PASS, HC_MIX_CYCLES 1020 (= the 88f1fa301 witness).
- bench_s1m0: SAFE 1 HC_ENG PASS (24 mixes, 4 outs exact).  The tb's t is the programme counter, which stops at the last
  event (the emit), so HC_MIX_CYCLES prints 1020 for both; the SAFE result pins are TD = 2 edges after the emit by
  construction (ledger HC_MIX + 2).
- bench_s1m21: MUT 21 (SRAM lane write mask dropped) -> TAIL_MISMATCH x92, HC_ENG FAIL (fail witness).
Native32 census (tools/ref_tile/native_census.py, actual ASAP7 RVT TT Liberty + SRAM libs; plain yosys 0.68 synth):
- census_xr2_gate_netlist.summary.json: the xr2 --cts gate netlist (SAFE 0, 182f5f067): FAIL 6,197 drivers > 32.
- census_root_safe1_tailbb_cf412ecc2.summary.json: SAFE 1 root with both tail units black-boxed: 471 drivers > 32
  (u_core 207, result emit/unit copies 189 -> resized in 7aec24602, programme/table targets + start logic ~50, reset relay
  cohorts 67..595, cfg_we 512, table hold enables 448, seq 15).  Tail units censused separately (pending).
