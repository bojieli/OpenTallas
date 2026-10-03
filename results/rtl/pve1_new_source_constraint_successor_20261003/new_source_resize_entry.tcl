# NEW constraint lineage; reviewed terminal ODB and fresh lease required.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 3_3_place_gp.odb new_source_constraint.sdc
source $::env(SCRIPTS_DIR)/resize.tcl
