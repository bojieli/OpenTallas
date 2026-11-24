# QC-OPEN-COLL handoff (FAMILY lane under QC-ALLFIX; split from QC-ALLFIX-COLL 11-23 19:24 PST)
Job: coll_core rows of lanes/ALLFIX-QC.tsv: (1) coll_core 80 CLK-open reset copies (tools row main 32027184aff), (2) rc107 g_pf W hotspot, (3) rc109 shr_p_rx_i setup -97. All three are read from ONE coll_core GRT probe.
- Coll types byte-identical C4 = compose A f418c1b290f3 = C1b 62ce8aba0292 (checked partition_types, placement, 126 ports, 56 lanes, latency, tap_offset): epyc7 QC-ALLFIX-COLL/rows/colldiff_open.py. So ROW-REBASED onto C1b = no plan delta, PRE = C1b PRE.
- Probe: intel2 ~/coord/autopilot/private_specs/QC-OPEN-COLL/qwen_compute_coll_core_1123193232 (run-item pid 3805534 on intel2, launched 19:4x, OT_BIND_RT=0), gen epyc8 on cA tree+bind, hosts [epyc11], tools_rt c66090747375, goal grt.
  private-spec --rt c660 refused by hash guard (reset_tree.py vs bind rt 7f184148a02e; diff = OT_REPO_ROOT path only), so tools_rt patched in spec; semantic toolskew replay at run-item decides.
- GRT read to do: CLK-open count (expect 0), 5_1_grt.odb setup/hold, u_rrl_26 23-copy D net (-521 pre-repair at CTS), g_pf W hotspot, shr_p_rx_i path; full-cause census fe8a2a5.
