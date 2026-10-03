# NEW source-constraint lineage. Called only by an admitted fresh ODB-stage job.
# Installed binary/API compatibility is checked by calls themselves: any missing
# command or method aborts; no catch-and-ignore and no invented zero counts.
proc ot_row {kind args} {
  global ot_audit_file
  set fields [list $kind {*}$args]
  puts $ot_audit_file [join [lmap field $fields {binary encode hex [encoding convertto utf-8 $field]}] "\t"]
}
proc ot_names {objects} {return [lsort -unique [lmap obj $objects {get_full_name $obj}]]}
set ot_audit_file [open $::env(OT_AUDIT_ROWS) w]
sta::find_timing
set ot_block [ord::get_db_block]
set ot_masters [dict create]
set ot_macro_insts [dict create]
foreach port [$ot_block getBTerms] {ot_row odb_port [$port getName]}
foreach inst [$ot_block getInsts] {
  set master [$inst getMaster]
  dict set ot_masters [$master getName] $master
  if {[$master getType] eq "BLOCK"} {ot_row macro [$inst getName]; dict set ot_macro_insts [$inst getName] 1}
  foreach pin [$inst getITerms] {
    ot_row odb_pin "[$inst getName]/[[$pin getMTerm] getName]"
  }
}
foreach cell [get_cells -hier *] {
  if {[get_property $cell is_memory] && [[[$ot_block findInst [get_full_name $cell]] getMaster] getType] ne "BLOCK"} {
    ot_row macro [get_full_name $cell]
    dict set ot_macro_insts [get_full_name $cell] 1
  }
}
# Match every used functional master pin to both exact corner views.
dict for {name master} $ot_masters {
  foreach pin [$master getMTerms] {
    if {[$pin getSigType] in {POWER GROUND}} {continue}
    foreach corner {WC BC} label {SS FF} {
      set found 0
      foreach cell [get_lib_cells -quiet */$name] {
        set filename [get_property $cell filename]
        if {[string match "*_${label}_*" $filename]} {
          foreach port [get_lib_pins -quiet [get_full_name $cell]/[$pin getName]] {
            set found 1
          }
        }
      }
      ot_row master_pin $name [$pin getName] $corner $found
    }
  }
}
foreach port [all_inputs] {ot_row input [get_full_name $port]}
foreach port [all_outputs] {ot_row output [get_full_name $port]}
foreach pin [all_registers -clock_pins] {ot_row clock_pin [get_full_name $pin] [join [ot_names [get_property $pin clocks]] ","]}
set ot_required [lsort -unique [concat [ot_names [all_registers -data_pins]] [ot_names [all_registers -async_pins]] [ot_names [all_outputs]]]]
foreach name $ot_required {ot_row required_endpoint $name}
set ot_endpoints [sta::endpoints]
foreach pin $ot_endpoints {ot_row endpoint [get_full_name $pin]}
set ot_graph_names [ot_names $ot_endpoints]
foreach pin [concat [all_registers -data_pins] [all_registers -async_pins] [all_outputs]] {
  if {[get_full_name $pin] ni $ot_graph_names} {
    ot_row non_graph_endpoint [get_full_name $pin]
    lappend ot_endpoints $pin
  }
}
# Independent graph timing-check inventory (not inferred from returned paths).
set ot_vertices [sta::vertex_iterator]
while {[$ot_vertices has_next]} {
  set vertex [$ot_vertices next]
  set edges [$vertex in_edge_iterator]
  while {[$edges has_next]} {
    set edge [$edges next]
    set role [$edge role]
    set from_name [get_full_name [$edge from_pin]]
    set to_name [get_full_name [$edge to_pin]]
    set inst_name [join [lrange [split $to_name /] 0 end-1] /]
    set constraint_disabled [$edge is_disabled_constraint]
    set loop_disabled [$edge is_disabled_loop]
    set constant_disabled [$edge is_disabled_constant]
    if {$constraint_disabled || $loop_disabled || $constant_disabled} {
      ot_row disabled_arc $from_name $to_name $role $constraint_disabled $loop_disabled $constant_disabled
      foreach pin [$edge disabled_constant_pins] {ot_row disabled_constant_pin $from_name $to_name [get_full_name $pin]}
    }
    if {[dict exists $ot_macro_insts $inst_name]} {
      # Preserve every actual macro graph arc's role, endpoints and native
      # corner/min-max delay strings. SS clk-to-q/read-capture is not guessed
      # or replaced with zero; macro presence still requires explicit review.
      foreach arc [$edge timing_arcs] {
        ot_row macro_arc $inst_name $from_name $to_name $role [$edge arc_delay_strings $arc 0 12]
      }
    }
    if {[sta::timing_role_is_check $role]} {
      set disabled [expr {$constraint_disabled || $loop_disabled || $constant_disabled}]
      ot_row check_arc [get_full_name [$edge to_pin]] $role $disabled
      if {$disabled} {ot_row disabled_check [$edge to_string]}
    }
  }
  $edges finish
}
$ot_vertices finish
set ot_reset_targets [ot_names [get_fanout -from [get_ports rst_n] -flat -endpoints_only -trace_arcs timing]]
foreach endpoint $ot_endpoints {
  set name [get_full_name $endpoint]
  set starts [ot_names [get_fanin -to $endpoint -flat -startpoints_only -trace_arcs timing]]
  set functional [expr {[llength [lsearch -all -inline -not -exact $starts rst_n]] > 0}]
  set reset [expr {$name in $ot_reset_targets}]
  if {$reset} {ot_row reset_reachable rst_n $name}
  foreach start $starts {ot_row startpoint_pair $start $name}
  foreach corner {WC BC} mode {max min} {
    # A query for a single endpoint's worst slack covers all its native checks
    # at that corner/mode, without a top-N report or an arbitrary path bound.
    # -corner is supported by the pinned ORFS generation's OpenSTA interface.
    set paths [find_timing_paths -to $endpoint -corner $corner -path_delay $mode]
    if {[llength $paths] == 0} {
      set missing [expr {$starts eq "rst_n" && $reset ? "EXCEPTED_RESET_ONLY" : "Inf"}]
      ot_row timing $name $corner $mode $missing $functional $reset
    } else {
      set slack Inf
      foreach path $paths {
        if {[$path is_unconstrained]} {set slack Inf; break}
        set value [get_property $path slack]
        if {$value < $slack} {set slack $value}
      }
      ot_row timing $name $corner $mode $slack $functional $reset
    }
  }
}
ot_row check_setup [check_setup -verbose]
write_sdc -no_timestamp $::env(OT_AUDIT_SDC)
ot_row complete 1
close $ot_audit_file
