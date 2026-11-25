# QC-RC97-BT2 handoff (Opus 5.5, sub-lane of QC-ALLFIX, started 11-24 17:37 PST). Report to COORD, cc QC-ALLFIX, QC-CB-C1L.
Job: rc97 row for C1n = st_a_v2 region hard cores at BT_LAT=2 + registered btab read (OT_BTAB_S4R) + latency priced;
private core kits to sign-off + LEC; then st_a_v2 (+ paired st_b_v2) type launches under the anti-churn rule.
Lane dirs: epyc7 + epyc2 + epyc10 /srv/opentallas-scratch2/claude/QC-RC97-BT2 (epyc7: wt lane clone, bin/, rows/;
epyc2: cores/, views/; epyc10: c/ = C1l fork + bind).

## Status 11-24 19:4x
- ROW pushed main 06b5820ed0 (commit 6874f8b235): btab_safe_r + btab_s4 ifdef OT_BTAB_S4R, bench PASS (12000 cyc,
  nodelay mutant FAILs), bind hook qc_fabric_transport bt_lat (slice-wide, fail closed) + 4 tests, stn_transport_params,
  generator tools/die_plan/qc_rc97_bt2_row.py d89536ec63ca. Row plan (C1l base) 4de40be104e5, delta 73802380c585.
- Latency: 0 lane/station/boundary changes; +1 edge on in-slice bt round trip (stn result +1, busy +1) on E1 E3 E5 W1 W3 W5.
- CORE: 3/3 SIGNED + LEC EQUIVALENT (epyc2 cores/<m>/kits/<m>_synth0): h17_n7_s8_bt2 TT +35.1, h18_n7_s8_bt2 TT +30.27,
  h15_n9_s11_bt2 TT +23.02; DRC 0; internal FF hold PASS (port-start hold only, to parent). Views: epyc2 views/<m>/,
  overlaid into epyc10 c/ov/physical/die_plan/qwen_compute/qcviews_rc97bt2/.
- BIND: epyc10 c/bindR.sh (C1l fork of QC-CB-C1L tree + ov + row plan; PRE, elab, strict R8 loop + LATCHECK),
  log c/bindR.log (ends BIND_DONE rc=N); started 19:20.
- Anti-churn (19:3x + QC-ALLFIX correction): live kits on all 6 st_b_v2 types, slw_st_a_v2 cl9f076a5c, and sle_st_a_v2
  pvd2ec7769 / pv4242de79 (QC-ALLFIX C1k private kits). Candidates after bind PASS: sle_st_a_v2__pv30dda31f__pv88773f93
  (E5) and slw_st_a_v2__clf4365a62 (W5) only. Note: a slice runs at BT_LAT 2 only when its st_a AND st_b are built on the
  rc97 plan; st_b relaunches wait for their live kits to end.

## Next
1. bind PASS -> kit_wave private-spec + run-item for E5 + W5 st_a (launch_c1j pattern, tree/bind = epyc10 c/) -> TYPE post.
2. QC-CB-C1L: rerun tools/die_plan/qc_rc97_bt2_row.py on C1m (ba1b4156d859) for C1n (views + hook from main).
