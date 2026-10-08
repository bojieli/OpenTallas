# Per-BIT output load (coordinator 2026-10-06): OpenSTA types a mixed-direction bus by ONE direction, so
# `set_load 2.0 [all_outputs]` in the station SDCs missed the odb-OUTPUT bits of buses typed input (11 station views).
# Re-applies the same 2.0 load to every bit the odb holds as OUTPUT / INOUT.
foreach p [concat [all_inputs -no_clocks] [all_outputs]] {
  if {[catch {set bt [[ord::get_db_block] findBTerm [get_full_name $p]]}] || $bt eq "NULL"} { continue }
  if {[$bt getIoType] in {OUTPUT INOUT}} { set_load 2.0 $p }
}
