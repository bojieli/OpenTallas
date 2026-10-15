# Materialize structural Verilog straps as real ASAP7 tie cells before PA.
# one_/zero_ implicit POWER/GROUND nets are not signal wiring. Never relabel
# those nets or suppress router power errors. This is pre-PDN mapping only:
# mapped cells still require real M1 supply rails/upconnect in the die PDN.
proc ot_die_constant_cells {} {
  set platform /OpenROAD-flow-scripts/flow/platforms/asap7
  if {![llength [get_lib_pins -quiet TIEHIx1_ASAP7_75t_R/H]] ||
      ![llength [get_lib_pins -quiet TIELOx1_ASAP7_75t_R/L]]} {
    foreach lib [glob $platform/lib/NLDM/*SIMPLE*RVT_TT*.lib*] { read_liberty $lib }
  }
  set block [ord::get_db_block]
  set macros {}
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] isBlock]} {
      dict set macros [$inst getName] [list [$inst getLocation] [$inst getOrient]]
    }
  }
  foreach pin {TIEHIx1_ASAP7_75t_R/H TIELOx1_ASAP7_75t_R/L} {
    if {[llength [get_lib_pins -quiet */$pin]] != 1} { error "OT_CONST: missing actual ASAP7 tie pin $pin" }
    insert_tiecells $pin
    repair_tie_fanout -separation 1 -max_fanout 1 $pin
  }
  add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
  add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
  global_connect
  set count 0
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] in {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} { incr count }
  }
  if {$count} { detailed_placement }
  dict for {name original} $macros {
    set inst [$block findInst $name]
    if {[list [$inst getLocation] [$inst getOrient]] ne $original} {
      error "OT_CONST: constant legalization moved hard macro $name"
    }
  }
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] ni {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} continue
    foreach pin {VDD VSS} {
      set it [$inst findITerm $pin]
      if {$it eq "NULL" || [$it getNet] eq "NULL" || ![[$it getNet] isSpecial]} {
        error "OT_CONST: missing logical supply binding [$inst getName]/$pin"
      }
    }
  }
  foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND} && ![$net isSpecial]} {
      error "OT_CONST: unmapped power/ground signal net [$net getName]"
    }
  }
  puts "OT_CONST MAPPED cells=$count hard_macros_unchanged=[dict size $macros]"
  if {$count} {
    puts "OT_CONST PG_OPEN: actual M1 supply rails and upconnect require PDN connectivity qualification"
  }
}
ot_die_constant_cells
