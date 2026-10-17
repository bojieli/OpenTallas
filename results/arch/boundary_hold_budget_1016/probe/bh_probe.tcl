# FLOW-HOLD boundary-hold-budget probe (STA only).  Env: BH_CORNER tt|ff, BH_BASE, BH_SDC (route signoff.sdc or ''),
# BH_C (sender launch-min credit ps), BH_U (tile hold uncertainty ps), BH_PORTS (file: input ports to detail), BH_LIBS.
set corner $::env(BH_CORNER)
foreach l [split $::env(BH_LEFS) " "] { if {$l ne ""} { read_lef $l } }
foreach l [split $::env(BH_LIBS) " "] { if {$l ne ""} { read_liberty $l } }
read_db $::env(BH_BASE)/6_final.odb
set ::ot_ce_corner $corner
read_sdc $::env(BH_BASE)/6_final.sdc
read_spef $::env(BH_BASE)/6_final.spef
set_propagated_clock [all_clocks]
if {$::env(BH_SDC) ne ""} { read_sdc $::env(BH_SDC) }
set_propagated_clock [all_clocks]
proc ws {check from to} {
  set w INF
  foreach p [find_timing_paths -path_delay $check -from $from -to $to -group_path_count 1] {
    set s [get_property $p slack]; if {$w eq "INF" || $s < $w} { set w $s } }
  return $w
}
proc pad_of {inst master} {
  if {[regexp {^HB} $master]} { return 1 }
  if {[regexp {^BUF} $master] && [regexp -nocase {(^|/|_)(in|out)?hold|^hold[0-9]} $inst]} { return 1 }
  return 0
}
# path detail: total pad delay, total buffer delay, cell list, port->D arrival
proc detail {pe} {
  set pts [get_property $pe points]
  set prev ""; set pad 0.0; set buf 0.0; set cells {}; set first ""; set last ""
  foreach pt $pts {
    set pin [get_property $pt pin]; set arr [get_property $pt arrival]
    if {$first eq ""} { set first $arr }
    set last $arr
    set inst [get_cells -quiet -of_objects $pin]
    if {[llength $inst] && [get_property $pin direction] eq "output" && $prev ne ""} {
      set m [get_property $inst ref_name]; set n [get_full_name $inst]
      set d [expr {$arr - $prev}]
      # include the input-pin wire into this stage: delay from previous output arrival
      if {[pad_of $n $m]} { set pad [expr {$pad + $d}] }
      if {[regexp {^(BUF|HB)} $m]} { set buf [expr {$buf + $d}] }
      lappend cells $m
    }
    if {[get_property $pin direction] eq "output" || [llength $inst] == 0} { set prev $arr }
  }
  return [list $pad $buf [expr {$last - $first}] $cells $last]
}
set clk [lindex [all_clocks] 0]
foreach c [all_clocks] { if {[get_full_name $c] eq "core_clk"} { set clk $c } }
# reference: same as io_ref_skew.sdc (median input pin flop) when its procs exist, else median of all register clocks
set ref {}
if {[llength [info procs ot_pf_ref]]} { set ref [ot_pf_ref [all_inputs -no_clocks]] }
if {![llength $ref]} {
  set a {}; foreach p [all_registers -clock_pins] { set v [get_property $p arrival_min_rise]; if {[string is double -strict $v]} { lappend a [list $v $p] } }
  set a [lsort -real -index 0 $a]; set ref [lindex [lindex $a [expr {[llength $a]/2}]] 1]
}
sta::worst_slack_cmd max
set lmin [get_property $ref arrival_min_rise]; set lmax [get_property $ref arrival_max_rise]
puts "BH_REF [get_full_name $ref] $lmin $lmax"
set ins [all_inputs -no_clocks]; set outs [all_outputs]
set regck [all_registers -clock_pins]; set regd [all_registers -data_pins]
if {$corner eq "ff"} {
  puts "BH_BEFORE ws=[sta::worst_slack_cmd min] i2r=[ws min $ins $regd] r2o=[ws min $regck $outs] r2r=[ws min $regck $regd]"
  # proposed rule: input min = L_min + C + U ; output min = U - (L_min + C)
  set c $::env(BH_C); set u $::env(BH_U)
  set_input_delay [expr {$lmin + $c + $u}] -min -clock $clk $ins
  set_output_delay [expr {$u - $lmin - $c}] -min -clock $clk $outs
  puts "BH_AFTER ws=[sta::worst_slack_cmd min] i2r=[ws min $ins $regd] r2o=[ws min $regck $outs] r2r=[ws min $regck $regd]"
  # per input port: slack after, pad delay on its worst min path
  set n 0
  if {[info exists ::env(BH_OUTONLY)]} { set ins_loop {} } else { set ins_loop $ins }
  foreach port $ins_loop {
    set pe [lindex [find_timing_paths -path_delay min -from $port -group_path_count 1] 0]
    if {$pe eq ""} continue
    set d [detail $pe]
    puts "BH_IN [get_full_name $port] [get_property $pe slack] [lindex $d 0] [lindex $d 1] [lindex $d 2] [join [lindex $d 3] ,]"
  }
  foreach port $outs {
    if {[catch {
    set pe [lindex [find_timing_paths -path_delay min -to $port -group_path_count 1] 0]
    if {$pe eq ""} continue
    set d [detail $pe]
    # launch min relative to the reference: data arrival at port - lmin
    puts "BH_OUT [get_full_name $port] [get_property $pe slack] [lindex $d 0] [lindex $d 1] [expr {[lindex $d 4] - $lmin}] [join [lindex $d 3] ,]"
    } err]} { puts "BH_OUTERR [get_full_name $port] $err" }
  }
} else {
  puts "BH_TT ws=[sta::worst_slack_cmd max] i2r=[ws max $ins $regd]"
  if {[info exists ::env(BH_OUTONLY)]} { set ins_loop {} } else { set ins_loop $ins }
  foreach port $ins_loop {
    set pe [lindex [find_timing_paths -path_delay max -from $port -group_path_count 1] 0]
    if {$pe eq ""} continue
    set d [detail $pe]
    puts "BH_IN [get_full_name $port] [get_property $pe slack] [lindex $d 0] [lindex $d 1] [lindex $d 2] [join [lindex $d 3] ,]"
  }
  foreach port $outs {
    if {[catch {
    set pe [lindex [find_timing_paths -path_delay max -to $port -group_path_count 1] 0]
    if {$pe eq ""} continue
    set d [detail $pe]
    puts "BH_OUT [get_full_name $port] [get_property $pe slack] [lindex $d 0] [lindex $d 1] [expr {[lindex $d 4] - $lmax}] [join [lindex $d 3] ,]"
    } err]} { puts "BH_OUTERR [get_full_name $port] $err" }
  }
}
exit
