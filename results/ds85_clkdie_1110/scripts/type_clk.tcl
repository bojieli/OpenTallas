# CLKDIE-S81 (DS85, DO_NOT_COUNT): ring rclk/tclk pin and fclk_out port clock arrivals of ONE routed partition type.
# Env: CORNER TT|FF, TOP (module), V (6_final.v), SPEF, LIBS (space list), OUT (file), PORTS (space list of clock ports),
#      TAPSLEW (ps).  Each clock port i is driven as DATA from a virtual clock: source RISE launches at OFF*i, source FALL
#      at OFF*i + HALF, so an arrival at any pin decodes to (source port, source edge) with no fanin walk; the source
#      RISE-derived arrival is the one whose offset is OFF*i.
set t0 [clock seconds]
foreach f $::env(LIBS) { read_liberty $f }
read_verilog $::env(V)
link_design $::env(TOP)
read_spef $::env(SPEF)
puts "DS85_T loaded [expr {[clock seconds]-$t0}]"
set OFF 20000.0
set HALF 5000.0
set ports $::env(PORTS)
create_clock -name vclk -period [expr {$OFF*([llength $ports]+2)}]
set i 0
set fh [open $::env(OUT) w]
puts $fh "# DS85 type_clk v1 corner $::env(CORNER) top $::env(TOP) off $OFF half $HALF"
foreach p $ports {
  incr i
  set po [get_ports -quiet $p]
  if {$po eq ""} { puts $fh "MISSINGPORT $p"; continue }
  set r [expr {$OFF*$i}]
  set f [expr {$OFF*$i + $HALF}]
  set_input_delay -clock vclk -rise -max $r $po
  set_input_delay -clock vclk -rise -min $r $po
  set_input_delay -clock vclk -fall -max $f $po
  set_input_delay -clock vclk -fall -min $f $po
  set_input_transition $::env(TAPSLEW) $po
  puts $fh "P $i $p"
}
foreach o [get_ports -quiet fclk_out_*] { set_load 2.0 $o; set_output_delay -clock vclk 0 $o }
report_checks -path_delay max -group_path_count 1 -format end > /dev/null
puts "DS85_T timed [expr {[clock seconds]-$t0}]"
set n 0
foreach c [all_registers -cells] {
  set nm [get_full_name $c]
  if {![string match *u_cland_* $nm]} { continue }
  foreach p [get_pins -of_objects $c] {
    set lp [get_property $p lib_pin_name]
    if {$lp ne "CLK"} { continue }
    puts $fh "R [get_property [get_lib_cells -of_objects $c] name] $nm [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall]"
    incr n
  }
}
foreach o [get_ports -quiet fclk_out_*] {
  set nm [get_full_name $o]
  set per [get_property [get_clocks vclk] period]
  puts $fh "O $nm [expr {$per - [get_property $o slack_max_rise]}] [get_property $o slack_min_rise] [expr {$per - [get_property $o slack_max_fall]}] [get_property $o slack_min_fall]"
}
close $fh
puts "DS85_T done regs $n [expr {[clock seconds]-$t0}]"
puts DS85_DONE
