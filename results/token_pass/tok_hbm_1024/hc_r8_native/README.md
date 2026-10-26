# HC native XRD = XRU = 10 exact gate (adopted Codex job, intel1)

Codex's gate (intel1 scratch2 codex-hbm/hc_r8_unit/gate, binary Vring, bin.sha256) built, then the run aborted:
`%Error: prog.mem:0: $readmem file syntax error` (codex_gate_run_infrafail.log) = INFRA FAIL: with --ding 12 the
generator tools/rtl_hbm_hc_eng_static_gate.py put the 4 phase-A ingest events at t = T0 + q - 12 = -4..-1 (T0 = 8),
written as negative hex words. Fix: new --t0 (default 8, auto-raised to ding+1 for split; ding <= 7 byte-identical).
- --t0 13 (first event t = 1): HC_ENG_FAULT t=5 seq=1 (t0_13_run_case.log) -> programme needs first event >= 6.
- --t0 18 (first event t = 6, same as the ding 2 / T0 8 original), RAW0 198, RS 104, same binary:
  positive (DING 12): HC_ENG PASS, 24/24 mixes, 4/4 outs exact vs single-block golden, HC_MIX_CYCLES 1029
  (= 996 at RAW0 165 + 33); mutant (DING 2, wrong ingest lead): HC_ENG_FAULT t=34 -> CAUGHT (rc 1).
Unit-level only: the bound die (r18h5 die.v) still needs equal-depth root<->quarter relays + the XRD/XRU bind
(HBM-ARCH die generator) before HC_MIX records can pass on the slice.
