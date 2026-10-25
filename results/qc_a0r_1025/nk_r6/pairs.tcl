# PATH-QC-NK2: FF hold paths of the top tap pairs, full clock (env PLIBS ODB SDC OUT PLATFORM_DIR); RC before the SDC
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
set fh [open $::env(OUT).pairs_in.txt]; set ls [split [string trim [read $fh]] "\n"]; close $fh
set o [open $::env(OUT).pairs.rpt w]; close $o
foreach l $ls {
  lassign [split $l "\t"] a b n sl s e
  set sp [get_pins [string map {\[ \\\[ \] \\\]} [string map {/QN /CLK /Q /CLK} $s]]]
  set ep [get_pins [string map {\[ \\\[ \] \\\]} $e]]
  report_checks -from $sp -to $ep -path_delay min -format full_clock_expanded -digits 1 >> $::env(OUT).pairs.rpt
}
