read_db /work/1_synth_tie_split.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set index [dict create]
foreach inst [$b getInsts] {
 regsub -all {\\} [$inst getName] {} normalized
 if {[dict exists $index $normalized]} {error "ambiguousnormalizedinstance $normalized"}
 dict set index $normalized $inst
}
set f [open /critical_cells.txt r];set cells [split [string trim [read $f]] \n];close $f
set f [open /work/critical_cell_areas.tsv w];puts $f "instance\tmaster\tarea_um2\tis_block"
foreach name $cells {
 if {![dict exists $index $name]} {error "missingexactcell $name"};set i [dict get $index $name]
 set m [$i getMaster];set a [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
 puts $f "$name\t[$m getName]\t$a\t[$m isBlock]"
}
close $f
exit
