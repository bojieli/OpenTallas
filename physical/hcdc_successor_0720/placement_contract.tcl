# Kit-local pre-GPL contract; no movement or shared-helper change.
set pc_b [ord::get_db_block]
set pc_u [$pc_b getDbUnitsPerMicron]
set pc_rows [dict create]
foreach rr [$pc_b getRows] {
 lassign [$rr getOrigin] xx yy
 dict lappend pc_rows $yy [list $xx [$rr getSpacing] [$rr getSiteCount] [[$rr getSite] getWidth]]
}
set pc_n 0
foreach pc_file {ot_out_flop_at_pins.txt ot_inhold_firm.txt} {
 set pc_f [open [file join $::env(RESULTS_DIR) $pc_file] r]
 foreach nm [split [read $pc_f] "\n"] {
  if {$nm eq ""} continue
  set i [$pc_b findInst $nm]
  if {$i eq "NULL"} {error "HCDC_PLAN: missing anchor $nm"}
  incr pc_n
  set bb [$i getBBox]
  set xx [$bb xMin]; set yy [$bb yMin]
  set ok 0
  if {[dict exists $pc_rows $yy]} {
   foreach row [dict get $pc_rows $yy] {
    lassign $row rx sp nc sw
    if {$xx >= $rx && [$bb xMax] <= $rx+$sp*($nc-1)+$sw && ($xx-$rx)%$sp==0} {set ok 1;break}
   }
  }
  if {!$ok} {error "HCDC_PLAN: anchor $nm not on actual row/site lattice"}
  if {!([$bb xMax] <= 27.0*$pc_u || [$bb xMin] >= 448.2*$pc_u || [$bb yMin] >= 513.0*$pc_u)} {
   error "HCDC_PLAN: anchor $nm outside dedicated boundary corridors"
  }
 }
 close $pc_f
}
if {$pc_n < 600} {error "HCDC_PLAN: implausible anchor count $pc_n"}
puts "HCDC_PLAN actual anchor grid/corridors PASS count=$pc_n"
