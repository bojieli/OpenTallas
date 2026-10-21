# Actual uncapped XFIN native failure

Both completion gates at source4951125de (RTL0618133cbc unchanged) are terminal
FAIL before layout: actual loaded-Liberty native maximum1119, 4815 violating
drivers, zero role errors. Largest drivers are g_cp[0..3].u_e.go_t at1119,
1062,1069,1039 loads; largest combinational drivers995/994. Original complete
native reports and mapped netlists remain immutable on ot-epyc9, with exact
paths, source netlist hashes, full-Liberty hashes and raw report hashes in
these summaries. Every violating driver/count is retained; endpoint samples
remain in original reports.

These are actual source failures, separate from earlier default2700-second
synthesis infrastructure timeouts retained in the parent evidence directory.
No layout PNG, coordinator review or submission exists for this candidate.
Parent CODEX-S81-1021 owns structural source/model repair; do not retry unchanged.
Top ot_s81dv_xfin NS16/NVL5, defaultLM5/LA6, no defines. Source file
rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv. Existing norm16 and xfin_eng positive and
causal runner contracts remain in physical/ref_tile/s81dv_xfin_e2/job.json.
