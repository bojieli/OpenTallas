# m3 copy: also drops the boundary generated clock clk_io before the stage SDC is written
# POST_{CTS,GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: restore the plain boundary so the written stage SDC can be
# loaded by the next stage (a -reference_pin SDC crashes load_design).
read_sdc $::env(QSS_SDC_DIR)/io_plain.sdc
if {[llength [get_clocks -quiet clk_io]]} { delete_generated_clock [get_clocks clk_io] }
set sta_crpr_enabled 1
