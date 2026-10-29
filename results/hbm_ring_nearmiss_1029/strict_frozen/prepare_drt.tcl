source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
source /work/core_grt_post.tcl
write_db $::env(RESULTS_DIR)/5_1_grt.odb
exit
