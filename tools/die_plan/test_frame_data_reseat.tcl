source [lindex $argv 0]

proc install_obj {name fields} {
  interp alias {} $name {} dispatch_obj $name
  dict set ::objects $name $fields
}
proc dispatch_obj {name method args} {
  set result [dict get $::objects $name $method]
  if {$method eq "findITerm"} { return [dict get $result [lindex $args 0]] }
  return $result
}
proc assert_error {script expected} {
  if {![catch {uplevel 1 $script} result] || ![string match "*$expected*" $result]} {
    error "Expected $expected, got '$result'"
  }
}
proc pin {name inst type net mt} {
  install_obj $name [dict create getMTerm $mt getInst $inst getNet $net isInputSignal [expr {$type eq "I"}] isOutputSignal [expr {$type eq "O"}]]
}
proc signal {net terms} {
  install_obj $net [dict create getITerms $terms getBTerms {} getSigType SIGNAL getName $net]
}
proc cell {name master pins data {status PLACED}} {
  install_obj $name [dict create getMaster $master getITerms $pins findITerm [dict create D $data] getName $name getPlacementStatus $status]
}
foreach m {Q QN D RESET A Y} { install_obj mt_$m [dict create getName $m] }
install_obj ff [dict create getName DFFHQNx1_ASAP7_75t_R]
install_obj inverter [dict create getName INVx2_ASAP7_75t_R]
install_obj buffer [dict create getName BUFx2_ASAP7_75t_R]
install_obj nand [dict create getName NAND2x1_ASAP7_75t_R]
cell src ff {q} NULL
cell cap ff {d reset} d
cell arbitrary_instance_1 inverter {a y} NULL
cell unrelated_load ff {other_d} other_d
pin q src O first mt_QN
pin a arbitrary_instance_1 I first mt_A
pin y arbitrary_instance_1 O last mt_Y
pin d cap I last mt_D
pin reset cap I reset_net mt_RESET
pin other_d unrelated_load I last mt_D
signal first {q a}
signal last {y d}
if {[ot_frame_reseat::trace src cap 1] ne {arbitrary_instance_1}} { error "Selector lost renamed inverter" }

# Fresh repair_design adds a BUF without changing the reviewed endpoints or polarity.
cell newly_added buffer {ba by} NULL
pin ba newly_added I first mt_A
pin by newly_added O middle mt_Y
pin a arbitrary_instance_1 I middle mt_A
signal first {q ba}
signal middle {by a}
if {[ot_frame_reseat::trace src cap 1] ne {newly_added arbitrary_instance_1}} { error "Selector lost inserted buffer" }
assert_error {ot_frame_reseat::trace src cap 0} parity
assert_error {ot_frame_reseat::trace unrelated_load cap 1} nontransparent

signal last {y d other_d}
assert_error {ot_frame_reseat::trace src cap 1} shared
signal last {y d}
dict set ::objects arbitrary_instance_1 getPlacementStatus LOCKED
assert_error {ot_frame_reseat::trace src cap 1} fixed
dict set ::objects arbitrary_instance_1 getPlacementStatus PLACED
dict set ::objects arbitrary_instance_1 getMaster nand
assert_error {ot_frame_reseat::trace src cap 1} nontransparent
dict set ::objects arbitrary_instance_1 getMaster inverter
dict set ::objects last getSigType CLOCK
assert_error {ot_frame_reseat::trace src cap 1} nonlocal
dict set ::objects last getSigType SIGNAL
dict set ::objects last getBTerms port
assert_error {ot_frame_reseat::trace src cap 1} nonlocal
dict set ::objects last getBTerms {}
dict set ::objects cap findITerm D NULL
assert_error {ot_frame_reseat::trace src cap 1} {actual D pin}
dict set ::objects cap findITerm D d
dict set ::objects mt_QN getName SE
assert_error {ot_frame_reseat::trace src cap 1} {Q pin}
dict set ::objects mt_QN getName QN

set rows [dict create 0 {{0 100 R0}} 10 {{0 100 MX}}]
set occupied [dict create 0 {{40 50}}]
if {[ot_frame_reseat::seat $rows occupied 5 10 0 45 5 10 30 70] ne {50 0 R0}} { error "Fixed footprint seat" }
if {[ot_frame_reseat::seat $rows occupied 5 10 0 45 5 10 30 70] ne {30 0 R0}} { error "Peer footprint seat" }
dict set occupied 10 {{0 100}}
assert_error {ot_frame_reseat::seat $rows occupied 5 10 0 45 5 20 40 45} {no disjoint row site}

puts "FRAME data native selector and legal-slot tests passed"
