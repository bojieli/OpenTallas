# Production ORFS synthesis unchanged. Add only mapped-state census artifacts.
source $::env(SCRIPTS_DIR)/synth.tcl
write_json $::env(RESULTS_DIR)/full_mapped.json
write_rtlil $::env(RESULTS_DIR)/full_mapped.rtlil
tee -o $::env(REPORTS_DIR)/full_mapped_stat.json stat -json -hierarchy {*}$lib_args
