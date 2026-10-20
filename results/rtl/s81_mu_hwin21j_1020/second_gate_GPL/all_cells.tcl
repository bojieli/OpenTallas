read_db /work/3_3_place_gp-failed.odb
set b [ord::get_db_block];set f [open /out/all_cells.tsv w];set unowned 0;set outband 0
foreach i [$b getInsts] {
 set m [$i getMaster];if {[$m isBlock]} {continue}
 set g [$i getGroup];set owner NONE
 if {$g ne "NULL"} {set owner [$g getName]}
 if {$owner eq "NONE"} {incr unowned}
 set bb [$i getBBox]
 if {[$bb xMin]<2160 || [$bb xMax]>559440 || [$bb yMin]<163890 || [$bb yMax]>203850} {incr outband}
 lassign [$i getLocation] x y
 puts $f "$owner\t[$i getName]\t[$m getName]\t$x\t$y\t[$m getWidth]\t[$m getHeight]\t[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]"
}
close $f
puts "HWIN_ALL_CELL_AUDIT unowned=$unowned full_band_outside=$outband"
