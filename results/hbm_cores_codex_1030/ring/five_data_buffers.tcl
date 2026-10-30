# Narrow measured candidate ONLY for codex-hbm-cores-1030/ring_slew50.
# Apply after shared clock freeze and before ordinary DPL/GRT/MM hold/route.
# Routed TT RCX probe: seven slew violations -> zero. Calibrated FF hold remains +1.63 ps.
# No clock, sequential master, interface, cycle or constraint change.
foreach {name net} {
  place9777 net9776
  place10432 net10431
  place10414 net10413
  place9760 net9759
  place10359 net10358
} {
  set inst [[ord::get_db_block] findInst $name]
  if {$inst eq "NULL" || $inst eq ""} {error "RING_DATA5 missing $name"}
  if {[[$inst getMaster] getName] ne "BUFx3_ASAP7_75t_R"} {error "RING_DATA5 unexpected master $name"}
  set yn [[$inst findITerm Y] getNet]
  if {[$yn getName] ne $net || [$yn getSigType] ne "SIGNAL"} {error "RING_DATA5 unexpected signal $name/$net"}
  set lc [get_lib_cells -quiet */BUFx6f_ASAP7_75t_R]
  if {[llength $lc] != 1} {error "RING_DATA5 ambiguous replacement"}
  replace_cell [get_cells $name] [lindex $lc 0]
  puts "RING_DATA5 $name $net BUFx3_ASAP7_75t_R -> BUFx6f_ASAP7_75t_R"
}
