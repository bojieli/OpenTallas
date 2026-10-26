# INFRA-FIRST-R5: clock arrivals at the 35 q52sw tap ports from a given SPEF (propagated clock, clock defined at the root-net sinks)
# env: OT_ODB OT_SPEF OT_CORNER (TT|FF) OT_OUT
read_db $::env(OT_ODB)
set c $::env(OT_CORNER)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${c}_nldm_*.lib*] { read_liberty $f }
set blk [ord::get_db_block]
set src {}
foreach n [$blk getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set dr 0; foreach it [$n getITerms] { if {[$it isOutputSignal]} { incr dr } }
  if {$dr == 0 && [llength [$n getBTerms]] == 0} { puts "ROOT_NET [$n getName]"; foreach it [$n getITerms] { lappend src "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
}
puts "ROOT_SINKS [llength $src]"
create_clock -name clk -period 833 [get_pins $src]
set_propagated_clock [all_clocks]
read_spef $::env(OT_SPEF)
set_output_delay 0 -clock clk [all_outputs]
