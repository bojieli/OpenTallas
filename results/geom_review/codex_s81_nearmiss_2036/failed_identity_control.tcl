set rk 0
set ::RB BUFx4f_ASAP7_75t_R
set cells {slweco_09370 ot_nm_repeater_0}
set nets {ot_nm_repeater_1_n}
proc get_cells {args} {global cells; set pat [lindex $args end]; set result {}; foreach c $cells {if {[string match $pat $c]} {lappend result $c}}; return $result}
proc get_nets {args} {global nets; set pat [lindex $args end]; set result {}; foreach c $nets {if {[string match $pat $c]} {lappend result $c}}; return $result}
proc get_pins {x} {return $x}
proc get_full_name {x} {return $x}
proc insert_buffer {args} {global cells nets; set i [lsearch -exact $args -buffer_name]; set nm [lindex $args [expr {$i+1}]]; if {[lsearch -exact $cells $nm]>=0} {error COLLISION}; lappend cells $nm; lappend nets ${nm}_n}
proc ib {net loads x y} {
  global rk; set nm "slweco_$rk"; incr rk
  insert_buffer -buffer_cell $::RB -net $net -load_pins [get_pins $loads] -location [list $x $y] -buffer_name $nm -net_name ${nm}_n
  set b [lindex [get_cells ${nm}*] 0]; set bn [get_full_name $b]
  puts "ECO REPEATER $bn net $net at ([format %.1f $x],[format %.1f $y]) loads [llength $loads]"
  return $bn
}
set selected [ib original {target/A} 187.2 5.1]
if {$selected ne "ot_nm_repeater_2"} {error "WRONG EXISTING BUFFER $selected"}
set selected2 [ib original [list $selected/A] 223.3 5.0]
if {$selected2 ne "ot_nm_repeater_3"} {error "WRONG SECOND BUFFER $selected2"}
puts "PASS exact new-cell identity, existing cell collision and existing net collision skipped"
