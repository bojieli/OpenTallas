read_db [lindex [glob /work/results/asap7/*/base/4_1_cts.odb] 0]
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set base [lindex [glob /work/results/asap7/*/base] 0]
set fi [open $base/s81_forward_drive.tsv r];gets $fi header
set f [open /probe/drive_geometry.tsv w]
puts $f "output\tflop\tstage\tmaster\tQ_x\tQ_y\tA_x\tA_y\tQ_to_A_manhattan_um"
set n 0;set worst 0
while {[gets $fi line]>=0} {
 lassign [split $line "\t"] output ff lead upstream phase lx ly
 set inst [$b findInst $ff];set q [$inst findITerm QN];if {$q eq "NULL"} {set q [$inst findITerm Q]}
 lassign [$q getAvgXY] ok qx qy
 foreach name [split $upstream ,] {
  set st [$b findInst $name];set a [$st findITerm A];lassign [$a getAvgXY] ok ax ay
  set dist [expr {(abs($qx-$ax)+abs($qy-$ay))/double($dbu)}]
  set worst [expr {max($worst,$dist)}]
  puts $f "$output\t$ff\t$name\t[[$st getMaster] getName]\t[expr {$qx/double($dbu)}]\t[expr {$qy/double($dbu)}]\t[expr {$ax/double($dbu)}]\t[expr {$ay/double($dbu)}]\t$dist"
 }
 incr n
}
close $fi;close $f
if {$n!=1464} {error "Expected1464 forwarded drive chains, got$n"}
puts "ACTUAL_FORWARD_DRIVE chains $n max_Q_to_original_INV_or_lead_A_manhattan_um $worst"
exit
