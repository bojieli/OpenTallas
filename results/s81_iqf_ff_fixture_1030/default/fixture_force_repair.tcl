source /work/fixture_snapshot.tcl
file rename -force $::env(RESULTS_DIR)/fixture434_postresize.tsv $::env(RESULTS_DIR)/fixture434_preforced.tsv
puts "FIXTURE_FORCE_LAWFUL_DPIN_BUFFER_REPAIR max_wire_length50"
estimate_parasitics -placement
repair_design -max_wire_length 50 -verbose
source /work/fixture_snapshot.tcl
