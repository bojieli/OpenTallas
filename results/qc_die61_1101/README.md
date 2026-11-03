DIE-QC-61 11-01, tt_ctlm density-tap delta (delta_ttctlm_1101.py) evidence.
- ttctlm_delta_report_main.json: delta applied to main plan_qc52 (main tools) -> committed plan_qc52.json.
- ttctlm_delta_report_d90.json: the same delta on codex/qc-event-1131 d90 plan + sidecar with the d90 tools
  (intel2 /srv/opentallas-scratch2/claude/die-qc-61/src_ovC): 4 -> 63 taps, reset tree 10 -> 118 relays.
  Strict bind (asbuilt event1131_fixed, --strict): errors 0, unbound 0 (die-qc-61/bindC).
  G0C --completeness vs the d90 base: 0 new findings; 2 tt_ctlm WARNs gone (clock_tap_sinks 2300, clock_reach 316.7).
- Main tools with the d90 sidecar: strict bind FAILS on coll_ftm (not tt_ctlm): 'EMIT collector rst_n_t21: raw
  reset parent rst_rl_17 absent'. The main reset/taps tools no longer reproduce the stored coll_ftm sidecar tree.
