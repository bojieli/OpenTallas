read_db /odb/clock_installed.odb
set b [ord::get_db_block];set tech [ord::get_db_tech]
set o [open /out/tech.tsv w];puts $o "layer\tdirection\twidth\tspacing\tpitch_x\tpitch_y\tgrid_x_first\tgrid_y_first"
foreach ln {M4 M5 M6 M7} {
 set l [$tech findLayer $ln];set gx {};set gy {}
 if {![catch {$b findTrackGrid $l} g] && $g ne "NULL"} {catch {set gx [$g getGridX]};catch {set gy [$g getGridY]}}
 puts $o "$ln\t[$l getDirection]\t[$l getWidth]\t[$l getSpacing]\t[$l getPitchX]\t[$l getPitchY]\t[lrange $gx 0 2]\t[lrange $gy 0 2]"
}
close $o
set f [open /out/manifest.tsv r];set o [open /out/clock_points.tsv w];puts $o "kind\tinstance\tpin\tmaster\tio\tx\ty\tnet\tndr"
set nets {};set n 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] kind name pin
 if {$kind eq "P"} {set it [$b findBTerm $name];if {$it eq "NULL"} {error "MISSING_PUBLIC_CLOCK $name"};set q [$it getBBox];set x [expr {([$q xMin]+[$q xMax])/2.}];set y [expr {([$q yMin]+[$q yMax])/2.}];set master port;set io [$it getIoType]} else {
  set i [$b findInst $name];if {$i eq "NULL"} {error "MISSING_CLOCK_INSTANCE $name"};set it [$i findITerm $pin];if {$it eq "NULL"} {error "MISSING_CLOCK_PIN $name/$pin"};set v [$it getAvgXY];if {[llength $v]==3} {lassign $v ok x y;if {!$ok} {error "BAD_CLOCK_POINT $name/$pin"}} elseif {[llength $v]==2} {lassign $v x y} else {error "BAD_CLOCK_POINT $name/$pin"};set master [[$i getMaster] getName];set io [[$it getMTerm] getIoType]
 }
 set net [$it getNet];if {$net eq "NULL"} {error "OPEN_CLOCK_PIN $name/$pin"};set nd [$net getNonDefaultRule];set ndr NONE;if {$nd ne "NULL" && $nd ne ""} {set ndr [$nd getName]};dict set nets [$net getName] $ndr
 puts $o "$kind\t$name\t$pin\t$master\t$io\t$x\t$y\t[$net getName]\t$ndr";incr n
}
close $f;close $o
set o [open /out/pg_upper.tsv w];puts $o "net\tlayer\tx0\ty0\tx1\ty1";set nv 0
foreach net [$b getNets] {
 if {[$net getSigType] ni {POWER GROUND}} continue
 foreach sw [$net getSWires] {foreach box [$sw getWires] {
  if {[$box isVia]} {incr nv;continue}
  set l [$box getTechLayer];if {$l eq "NULL"} continue
  set ln [$l getName];if {$ln ni {M6 M7}} continue
  puts $o "[$net getName]\t$ln\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
 }}
}
close $o
set o [open /out/hardchildren.tsv w];puts $o "instance\tmaster\torient\tx0\ty0\tx1\ty1\tobs_layers"
foreach i [$b getInsts] {
 set m [$i getMaster];if {![$m isBlock]} continue
 set layers {};foreach q [$m getObstructions] {set l [$q getTechLayer];if {$l ne "NULL"} {lappend layers [$l getName]}}
 set q [$i getBBox];puts $o "[$i getName]\t[$m getName]\t[$i getOrient]\t[$q xMin]\t[$q yMin]\t[$q xMax]\t[$q yMax]\t[lsort -unique $layers]"
}
close $o
puts "A0_UPPERMETAL_NATIVE_READONLY points=$n nets=[dict size $nets] PGvia_objects=$nv no_route_or_STA"
