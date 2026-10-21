read_db /work/input_place.odb
set ::env(OT_CKKM_K) 8
set ::env(OT_CKKM_PORT) clk
source /src/physical/common_flow/clock_split_km.tcl
source /src/physical/s81_ctrl_rg3/clock_split_hclk.tcl
set ::env(OT_CTRL_RC_APPLY) 1
source /work/reset_cohort.tcl
