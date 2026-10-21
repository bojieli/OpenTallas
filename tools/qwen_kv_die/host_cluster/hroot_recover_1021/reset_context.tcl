# Exact existing reset-landing context, diagnostic until bound to a real kit.
# This adds the SAME two plain clocked landing stages as the old s1 spec; it
# delays assertion and release by two core edges. No async-bank stages changed.
set ::env(DESIGN_NAME) qkd_hr_ingest_qm
set ::env(RESULTS_DIR) /work/controller_onebank/reset_context
set ::env(OT_PIN_REGS) 0
set ::env(OT_PIN_REGS_CLOCK) ck_core,ck_host,ck_ingest
set ::env(OT_PIN_REGS_RESET_PORTS) host_rst_n
set ::env(OT_RST_LAND) 1
set ::env(OT_RST_LAND_STAGES) 2
set ::env(OT_RST_LAND_COPIES) host_rst_n=16
set ::env(OT_RST_COPIES_MAX) 32
set ::env(OT_RST_COPIES_RE) {host_rst_n__ot_rlv$}
# Full canonical hook supplies kept-register bit techmap before reset copies.
source /work/helpers/ot_keep_regs.tcl
