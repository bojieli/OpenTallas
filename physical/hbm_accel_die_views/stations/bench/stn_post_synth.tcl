# POST_SYNTH hook for the CLAUDE HBM-ABSTRACTS station views (stn_route.sh).  A die master's bus mixes directions bit by
# bit (the r16g DIRECTION MODEL), so the generated Verilog declares such a bus inout.  ORFS never buffers an inout
# terminal, and two flow steps fail on an unbuffered inout: TritonCTS segfaults (separateMacroRegSinks) on a forwarded
# clock leaving through one, and the post-GRT repair stops with RSZ-0074 ("found route to 2 pins, expected 1") on an
# inout data bit (measured: 11/11 inout views of r1 failed, 0/22 input/output views).  Every inout terminal is given
# the direction its own netlist connection has (a cell output drives it -> OUTPUT, else INPUT), before 1_synth.odb is
# written, so the rest of the flow, the SDC and the exported LEF/ETM see per-bit directions.  Port names, bit indices
# and pin positions are unchanged.
set ot_blk [ord::get_db_block]
set ot_in 0; set ot_out 0
foreach ot_bt [$ot_blk getBTerms] {
  if {[$ot_bt getIoType] ne "INOUT"} { continue }
  set ot_net [$ot_bt getNet]
  set ot_drv 0
  if {$ot_net ne "NULL"} {
    foreach ot_it [$ot_net getITerms] { if {[$ot_it isOutputSignal]} { set ot_drv 1 } }
  }
  if {$ot_drv} { $ot_bt setIoType OUTPUT; incr ot_out } else { $ot_bt setIoType INPUT; incr ot_in }
}
puts "OT_STN: inout terminals retyped: $ot_out OUTPUT, $ot_in INPUT"
