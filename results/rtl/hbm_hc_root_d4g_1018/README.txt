ELEM-GAPS/HBMB 2026-10-18: HC ROOT ot_hbm_hc_root_static in its d4g die configuration (QDRLY 2, XRD = XRU = 0) inside the U-ring
form (hub DRLY 2, U relay XRLY 1) -- rtl/test/run_hbm_hc_root_uring.sh, ot-epyc5 /srv/opentallas-scratch/claude/eg-hbmb-hcroot.
  hcroot_m0      MUT 0 QDRLY 2 RAW0 167: HC_ENG PASS, 24 mixes / 4 outs bit-exact, HC_MIX_CYCLES 998 (rc 0)
  hcroot_mut2    MUT 2 (root tail unit 0 pre-sigmoid eps dropped): outbad 16, HC_ENG FAIL (rc 1)
  hcroot_qd1     QDRLY 1 (root not told about the hub relay): HC_ENG_FAULT ps=1 (rc 1)
  hcroot_raw165  RAW0 165 (ring-form compiler constant): HC_ENG_FAULT core=1 (rc 1)
<name>.log = driver output (fail_witness / pass evidence); <name>_run.log = simulator log.
  r2 2026-10-18 (decoded RTL ffa402dda, Verilator 5.050 on ot-epyc4): all four driver logs byte-identical to the above.
