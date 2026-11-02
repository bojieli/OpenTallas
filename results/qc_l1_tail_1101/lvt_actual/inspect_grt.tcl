read_db /work/input.odb
source /work/pg_connect.tcl
ot_pg_require_bound l1_lvt_grt_review
set b [ord::get_db_block]
set f [open /work/route_census.tsv w]
puts $f "name\tsig\tspecial\titerms\tbterms\tguides\twire\tswires"
foreach n [$b getNets] {
 if {[$n getSigType] ni {CLOCK SIGNAL}} continue
 puts $f [join [list [$n getName] [$n getSigType] [$n isSpecial] [llength [$n getITerms]] [llength [$n getBTerms]] [llength [$n getGuides]] [expr {[$n getWire] ne "NULL"}] [llength [$n getSWires]]] "\t"]
}
close $f
write_def /work/lvt_grt_native.def
source /work/geom_dump.tcl
puts L1_LVT_ACTUAL_GRT_REVIEW_COMPLETE
