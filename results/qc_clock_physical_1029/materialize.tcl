# Use only after a zero-error jointly PG-reserved prebuild and viewed render.
# Parent wrapper mounts readonly source ODB at /i/clock_grafted.odb,
# prebuild outputs at /p, approved power access at /a/power_access.tcl,
# output directory at /o. No placement, guide synthesis, P&R or timing here.
read_db /i/clock_grafted.odb
set blk [ord::get_db_block]
foreach net [$blk getNets] {
  if {[$net getWire] != "NULL" || [llength [$net getSWires]]} {
    error "source must be exact connected-unrouted ODB: [$net getName] has wires"
  }
}
source /p/fixed_pg.tcl
source /a/power_access.tcl
source /p/fixed_clock_only.tcl
set clock_nets 0
set clock_iterms 0
set physical_pg_nets 0
foreach net [$blk getNets] {
  if {[$net getSigType] eq "CLOCK"} {
    if {[$net getWire] == "NULL"} {error "clock net lacks physical dbWire: [$net getName]"}
    incr clock_nets
    incr clock_iterms [llength [$net getITerms]]
  }
  if {[$net getName] eq "VDD" || [$net getName] eq "VSS"} {
    if {![llength [$net getSWires]]} {error "power net lacks physical special wire"}
    incr physical_pg_nets
  }
}
if {$physical_pg_nets != 2} {error "physical supply nets incomplete"}
write_db /o/clock_physical.odb
write_def /o/clock_physical.def
puts "OT_CLOCK_MATERIALIZED nets=$clock_nets clock_iterms=$clock_iterms pg_nets=$physical_pg_nets"
puts "NOT_SIGNED: actual-wire continuity/extraction, duty/variation, reset, signals and die gates remain required"
