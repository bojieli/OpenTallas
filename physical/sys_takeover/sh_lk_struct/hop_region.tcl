# Structural SH: exact 291-bit kept payload hop in the central standard-cell band.
set shb [ord::get_db_block]
set shdbu [$shb getDbUnitsPerMicron]
set shcells [dict create]
foreach net [$shb getNets] {
 set name [string map [list "\\" ""] [$net getName]]
 if {![regexp {(^|\.)u_sd\.sd_hop_payload\[[0-9]+\]$} $name]} {continue}
 foreach it [$net getITerms] {
  if {[$it getIoType] ne "OUTPUT"} {continue}
  set inst [$it getInst]
  if {![[$inst getMaster] isSequential]} {error "SH hop payload has nonsequential driver $name"}
  dict set shcells [$inst getName] $inst
 }
}
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
