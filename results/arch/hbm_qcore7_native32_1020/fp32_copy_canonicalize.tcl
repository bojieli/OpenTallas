# Own source prototype only: keep source copies, bit-map logic, then invoke unchanged exact-copy proof/splitter.
# This performs no gate or threshold relaxation. Actual native census must pass after ABC.
set ot_qcore_copy_max $::env(OT_RST_COPIES_MAX)
unset ::env(OT_RST_COPIES_MAX)
source /src/physical/common_flow/ot_keep_regs.tcl
set ::env(OT_RST_COPIES_MAX) $ot_qcore_copy_max
yosys techmap
yosys opt_clean
source /src/physical/common_flow/ot_rst_copies.tcl
