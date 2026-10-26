# Restore the core's original reset input in our COPY of c3q 3_place.
# Remove only the unpriced island reset relay and its face-flop clones.
read_db $::env(ODB)
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set old [$b findNet rst_n]
if {$old eq "NULL"} { error "missing c3q core reset net" }
foreach i [$b getInsts] {
  if {[regexp {^u_isl_rst(_otdup[0-9]+)?$|^u_isl_rstb(_otdup[0-9]+)?$|^u_isl_m1$} [$i getName]]} {
    puts "V4Q_REMOVE [$i getName]"
    $i setDoNotTouch 0
    odb::dbInst_destroy $i
  }
}
set bt [odb::dbBTerm_create $old rst_n]
$bt setIoType INPUT
$bt setSigType SIGNAL
set bp [odb::dbBPin_create $bt]
set l [[ord::get_db_tech] findLayer M5]
odb::dbBox_create $bp $l [expr {int(159.744*$u)}] [expr {int(157.584*$u)}] [expr {int(159.936*$u)}] [expr {int(157.776*$u)}]
$bp setPlacementStatus FIRM
set n [$b findNet ft_rst_o]
if {$n eq "NULL"} { set n [odb::dbNet_create $b ft_rst_o] }
set out [$b findBTerm ft_rst_o]
$out disconnect
$out connect $n
set m [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
set i [odb::dbInst_create $b $m u_isl_rstft]
[$i findITerm A] connect [$b findNet ft_rst_i]
[$i findITerm Y] connect $n
foreach it [$i getITerms] {
  set sig [[$it getMTerm] getSigType]
  if {$sig eq "POWER" || $sig eq "GROUND"} {
    set pn [expr {$sig eq "POWER" ? "VDD" : "VSS"}]
    set net [$b findNet $pn]
    if {$net eq "NULL"} { error "missing core PG net $pn" }
    $it connect $net
  }
}
$i setLocation [expr {int(157.14*$u)}] [expr {int(158.22*$u)}]
$i setPlacementStatus LOCKED
$i setDoNotTouch 1
write_db $::env(ODB)
puts "V4Q_RESET restored rst_n, dedicated BUF, zero added reset cycles"
