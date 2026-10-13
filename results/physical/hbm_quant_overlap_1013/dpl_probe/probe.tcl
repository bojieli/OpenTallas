read_db /work/results/asap7/opentallas_ot_hgi_quant_wide_ov_asap7_ref_qw_ov_ref_ov1_cx_c8c47022e/base/3_5_place_dp-failed.odb
set pb [ord::get_db_block]
set pu [[ord::get_db_tech] getDbUnitsPerMicron]
set pf [open /diag/placed_cells.txt r]
set pn [split [string trim [read $pf]] \n]
close $pf
set po [open /diag/cells.tsv w]
puts $po "name\tmaster\tx0\ty0\tx1\ty1\twidth\tstatus"
foreach name $pn {
 set pi [$pb findInst $name]
 if {$pi eq "NULL"} {continue}
 set box [$pi getBBox]
 set pm [$pi getMaster]
 puts $po "$name\t[$pm getName]\t[expr {[$box xMin]/double($pu)}]\t[expr {[$box yMin]/double($pu)}]\t[expr {[$box xMax]/double($pu)}]\t[expr {[$box yMax]/double($pu)}]\t[expr {[$pm getWidth]/double($pu)}]\t[$pi getPlacementStatus]"
}
close $po
set pc 0
set pw 0
set pwn ""
foreach i [$pb getInsts] {
 if {[string match clkbuf_sp_* [$i getName]]} {incr pc}
 if {! [[$i getMaster] isBlock]} {
  set w [expr {[[$i getMaster] getWidth]/double($pu)}]
  if {$w > $pw} {set pw $w;set pwn [[$i getMaster] getName]}
 }
}
puts "QW_PROBE offending [llength $pn] spine_cells $pc max_std_width $pw master $pwn"
exit
