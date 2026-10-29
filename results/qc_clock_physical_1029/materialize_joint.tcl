# Reviewed fixed infrastructure import only; no placement, STA, GRT or DRT.
read_db /input/source.odb
set blk [ord::get_db_block]
foreach net [$blk getNets] {
  if {[$net getWire] != "NULL" || [llength [$net getSWires]]} {
    error "source must be the exact connected-unrouted ODB: [$net getName] has wires"
  }
}
source /prebuild/fixed_pg.tcl
source /prebuild/fixed_clock_only.tcl
set clock_nets 0
set clock_iterms 0
foreach net [$blk getNets] {
  if {[$net getSigType] eq "CLOCK"} {
    if {[$net getWire] == "NULL"} {error "clock net lacks physical dbWire: [$net getName]"}
    incr clock_nets
    incr clock_iterms [llength [$net getITerms]]
  }
}
write_db /out/clock_raw.odb
puts "OT_CLOCK_RAW nets=$clock_nets native_clock_iterms=$clock_iterms"
puts "NOT_SIGNED: native PG access, exact clock extraction, reset and die gates remain separate"
