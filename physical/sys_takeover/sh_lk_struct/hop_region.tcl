# Structural SH: exact 291-bit kept payload hop in the central standard-cell band.
set shb [ord::get_db_block]
set shdbu [$shb getDbUnitsPerMicron]
set shcells [dict create]
# Yosys maps positive Q through a QN inverter. Trace ONLY buffers/inverters
# backward from the kept net, then require a DFF output; arbitrary logic refuses.
proc sh_hop_driver {net depth} {
 if {$depth>4} {error "SH hop driver buffer depth exceeded"}
 set drivers {}
 foreach it [$net getITerms] {
  if {[$it getIoType] eq "OUTPUT"} {lappend drivers $it}
 }
 if {[llength $drivers]!=1} {error "SH hop requires one driver on [$net getName]"}
 set inst [[lindex $drivers 0] getInst];set mn [[$inst getMaster] getName]
 if {[regexp {^DFF} $mn]} {return $inst}
 if {![regexp {^(INV|BUF)} $mn]} {error "SH hop unexpected combinational driver $mn on [$net getName]"}
 set inputs {}
 foreach it [$inst getITerms] {if {[$it getIoType] eq "INPUT"} {lappend inputs $it}}
 if {[llength $inputs]!=1} {error "SH hop buffer must have one input: $mn"}
 return [sh_hop_driver [[lindex $inputs 0] getNet] [expr {$depth+1}]]
}
set shbits 0
foreach net [$shb getNets] {
 set name [string map [list "\\" ""] [$net getName]]
 if {![regexp {(^|\.)u_sd\.sd_hop_payload\[[0-9]+\]$} $name]} {continue}
 incr shbits
 set inst [sh_hop_driver $net 0]
 dict set shcells [$inst getName] $inst
}
if {$shbits!=291} {error "SH hop requires291 kept net bits, found $shbits"}
if {[dict size $shcells]!=291} {error "SH hop requires exactly291 mapped payload flops, found [dict size $shcells]"}
lassign {237.6 129.6 324.0 164.16} x0 y0 x1 y1
set reg [odb::dbRegion_create $shb sh_sd_hop]
$reg setRegionType EXCLUSIVE
odb::dbBox_create $reg [expr {round($x0*$shdbu)}] [expr {round($y0*$shdbu)}] [expr {round($x1*$shdbu)}] [expr {round($y1*$shdbu)}]
set grp [odb::dbGroup_create $reg sh_sd_hop]
set area 0.0
foreach inst [dict values $shcells] {
 if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} {error "SH hop cell already grouped: [$inst getName]"}
 $grp addInst $inst
 set m [$inst getMaster]
 set area [expr {$area+double([$m getWidth])*[$m getHeight]/($shdbu*$shdbu)}]
}
set capacity 0.0
foreach row [$shb getRows] {
 set bb [$row getBBox]
 set rx0 [expr {[$bb xMin]/double($shdbu)}];set ry0 [expr {[$bb yMin]/double($shdbu)}]
 set rx1 [expr {[$bb xMax]/double($shdbu)}];set ry1 [expr {[$bb yMax]/double($shdbu)}]
 set capacity [expr {$capacity+max(0.0,min($x1,$rx1)-max($x0,$rx0))*max(0.0,min($y1,$ry1)-max($y0,$ry0))}]
}
if {$capacity<=0 || $area/$capacity>.60} {error "SH hop cannot fit actual rows: $area / $capacity"}
puts "SH_SD_HOP_REGION cells291 area$area actual_row_capacity$capacity fill[expr {$area/$capacity}] bbox237.6,129.6,324,164.16"
