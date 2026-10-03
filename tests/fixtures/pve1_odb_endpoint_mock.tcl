# Finite synthetic graph; never starts or communicates with a timing engine.
set scenario [lindex $argv 0]
set ::env(OT_AUDIT_ROWS) [lindex $argv 2]
set ::env(OT_AUDIT_SDC) [lindex $argv 3]
set sdc_source [lindex $argv 4]
namespace eval sta {}
namespace eval ord {}
proc get_full_name {obj} {return $obj}
proc ord::get_db_block {} {return block}
proc block {method args} {
  switch -- $method {
    getBTerms {return {clk rst_n x y}}
    getInsts {return reg}
    findInst {return reg}
    default {error "unsupported block method $method"}
  }
}
foreach port {clk rst_n x y} {proc $port {method} {if {$method ne "getName"} {error $method}; return [lindex [info level 0] 0]}}
proc reg {method args} {
 switch -- $method {
  getMaster {return master}
  getName {return reg}
  getITerms {return {D CLK Q RN}}
  default {error "unsupported instance method $method"}
 }
}
proc master {method args} {
 global scenario
 switch -- $method {
  getName {return DFF}
  getType {if {$scenario eq "macro"} {return BLOCK}; return CORE}
  getMTerms {return {D CLK Q RN VDD}}
  default {error "unsupported master method $method"}
 }
}
foreach pin {D CLK Q RN VDD} {
 proc $pin {method} {
  switch -- $method {
   getMTerm {return [lindex [info level 0] 0]}
   getName {return [lindex [info level 0] 0]}
   getSigType {if {[lindex [info level 0] 0] eq "VDD"} {return POWER}; return SIGNAL}
   default {error "unsupported pin method $method"}
  }
 }
}
proc get_cells {args} {return reg}
proc get_property {obj property} {
 global scenario
 switch -- $property {
  is_memory {return 0}
  filename {if {$obj eq "SS/DFF"} {return cell_SS_model.lib}; return cell_FF_model.lib}
  clocks {if {$scenario eq "unclocked"} {return {}}; return core_clk}
  slack {if {$scenario eq "negative"} {return -1}; return 4}
  default {error "unsupported property $property"}
 }
}
proc get_lib_cells {args} {return {SS/DFF FF/DFF}}
proc get_lib_pins {args} {
 global scenario
 set name [lindex $args end]
 if {$scenario eq "missing_lib_pin" && $name eq "FF/DFF/D"} {return {}}
 return $name
}
proc all_inputs {} {return {clk rst_n x}}
proc all_outputs {} {return y}
proc all_registers {flag} {
 global scenario
 switch -- $flag {
  -clock_pins {return reg/CLK}
  -data_pins {return reg/D}
  -async_pins {if {$scenario in {reset_only mixed_reset_no_path}} {return reg/RN}; return {}}
  default {error "unsupported register flag $flag"}
 }
}
proc sta::find_timing {} {}
proc sta::endpoints {} {if {$::scenario eq "missing_endpoint"} {return y}; return {reg/D y}}
proc sta::vertex_iterator {} {set ::vi 0; return vertices}
proc vertices {method} {
 switch -- $method {
  has_next {return [expr {$::vi < 1}]}
  next {incr ::vi; return vertex}
  finish {incr ::finished_vertices}
  default {error $method}
 }
}
proc vertex {method} {if {$method ne "in_edge_iterator"} {error $method}; set ::ei 0; return edges}
proc edges {method} {
 switch -- $method {
  has_next {return [expr {$::ei < 2}]}
  next {incr ::ei; return edge$::ei}
  finish {incr ::finished_edges}
  default {error $method}
 }
}
foreach edge {edge1 edge2} {
 proc $edge {method args} {
  global scenario
  set self [lindex [info level 0] 0]
  switch -- $method {
   role {if {$self eq "edge1"} {return setup}; return hold}
   from_pin {return reg/CLK}
   to_pin {return reg/D}
   is_disabled_constraint {return [expr {$scenario eq "disabled_constraint"}]}
   is_disabled_loop - is_disabled_constant {return 0}
   disabled_constant_pins {return {}}
   to_string {return "$self disabled check"}
   timing_arcs {return arc0}
   arc_delay_strings {
    if {$args ne "arc0 0 12"} {error "wrong arc delay signature $args"}
    return "WC max clk-q 12; BC min clk-q 4"
   }
   default {error "unsupported edge method $method"}
  }
 }
}
proc sta::timing_role_is_check {role} {return [expr {$role in {setup hold}}]}
proc get_ports {name} {return $name}
proc get_fanout {args} {
 if {$args ne "-from rst_n -flat -endpoints_only -trace_arcs timing"} {error "fanout signature $args"}
 if {$::scenario in {reset_only mixed_reset_no_path}} {return reg/RN}; return {}
}
proc get_fanin {args} {
 if {[lrange $args 2 end] ne "-flat -startpoints_only -trace_arcs timing"} {error "fanin signature $args"}
 set endpoint [lindex $args 1]
 if {$endpoint eq "reg/RN"} {
  if {$::scenario eq "mixed_reset_no_path"} {return {rst_n x}}; return rst_n
 }
 if {$endpoint eq "y"} {return reg/Q}; return x
}
proc find_timing_paths {args} {
 if {[llength $args] != 6 || [lindex $args 0] ne "-to" || [lindex $args 2] ne "-corner" || [lindex $args 4] ne "-path_delay"} {error "path signature $args"}
 set corner [lindex $args 3]; set mode [lindex $args 5]
 if {![expr {($corner eq "WC" && $mode eq "max") || ($corner eq "BC" && $mode eq "min")}]} {error "wrong corner/mode"}
 if {[lindex $args 1] eq "reg/RN" || ($::scenario eq "missing_corner" && $corner eq "BC")} {return {}}
 return path
}
proc path {method} {if {$method ne "is_unconstrained"} {error $method}; return [expr {$::scenario eq "unconstrained"}]}
proc check_setup {args} {if {$args ne "-verbose"} {error $args}; return [expr {$::scenario ne "check_setup_failure"}]}
proc write_sdc {flag target} {
 if {$flag ne "-no_timestamp"} {error $flag}
 set in [open $::sdc_source r]; set content [read $in]; close $in
 set out [open $target w]; puts -nonewline $out $content
 puts $out {set_propagated_clock [all_clocks]}; close $out
}
set finished_vertices 0
set finished_edges 0
if {$scenario eq "unsupported_api"} {rename sta::vertex_iterator {}}
source [lindex $argv 1]
if {$finished_vertices != 1 || $finished_edges != 1} {error "iterator lifecycle incomplete"}
