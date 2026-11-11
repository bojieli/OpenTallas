# CPL-QC-2 clean-slate cb placement (11-11, DO_NOT_COUNT, advisory)

delta_cb_qc.json: positions/orients-only delta {type: {inst: [x, y, orient]}} for the 15 QC A0-tile cb types
(cbf_q00 x2, cbf_q01, cbf_q01_s2, cbf_q11, cbn_q00 x3, cbn_q01 x3, cbn_q11 x2, cbx_q10 x2). Base plan = DIE-QC-97
lineage head aace4c2668fc. Orients R0/MY only (MX/R180 put NK/NL M4 face pins half a pitch off the grid).
Apply with tools/die_plan/cleanslate_qc/cslate_apply.py PLAN delta_cb_qc.json OUT (moves cores, re-derives the
inst.pin clock taps, core_resets and the same number of FIRM internal_stations regs street-first; nets, pins,
outlines, buses, ft slots unchanged, so EQ holds by construction). Clone groups share one delta.
Model: tools/die_plan/cleanslate_qc/cslate.py (17.28-um grid, negotiated-congestion bundle router on route_supply x0.6
street derate, detail-LEF free fraction over tiles). Probes: run_probe.sh/cp_probe.tcl (place + GRT only).
