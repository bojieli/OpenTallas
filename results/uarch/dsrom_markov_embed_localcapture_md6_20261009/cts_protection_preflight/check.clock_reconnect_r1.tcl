set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
set M /evidence/physical/asap7_memory_macros/ot_rom_4096x274_m8
read_lef $M/ot_rom_4096x274_m8.lef
foreach l [glob $P/lib/NLDM/*RVT_TT_*.lib*] {read_liberty $l}
read_liberty $M/ot_rom_4096x274_m8_tt.lib
read_db /evidence/3_place.odb
read_sdc /evidence/3_place.sdc
source /src/physical/dsrom_markov_lookup_localcapture/electrical_env.tcl
set cells {}
foreach i [[ord::get_db_block] getInsts] {
 set n [string map [list "\\" ""] [$i getName]]
 if {[regexp {^cap[01]\[[0-9]+\]} $n]} {lappend cells $i}
}
if {[llength $cells]!=512} {error "capture count"}
set first [lindex $cells 0]
set clk [$first findITerm CLK];set cn [$clk getNet]
if {![catch {$clk disconnect} problem]} {error "negative protection control did not block disconnect"}
puts "OT_NEGATIVE_CTS_PROTECTION_BLOCKED $problem"
source /src/physical/dsrom_markov_lookup_localcapture/pre_cts.tcl
set reconnected 0
foreach i $cells {
 if {[$i getPlacementStatus] ne "FIRM"} {error "capture placement protection lost"}
 set clk [$i findITerm CLK];set cn [$clk getNet]
 if {$cn eq "NULL"} {error "missing original capture clock"}
 $clk disconnect
 $clk connect $cn
 if {[$clk getNet] ne $cn} {error "CLK failed reconnect"}
 incr reconnected
}
puts "OT_CTS_CLOCK_RECONNECTED $reconnected"
source /src/physical/dsrom_markov_lookup_localcapture/post_cts.tcl
set clk [$first findITerm CLK]
if {![catch {$clk disconnect} problem]} {error "capture instance protection not restored"}
puts "OT_POST_CTS_PROTECTION_RESTORED $problem"
set protected 0
foreach m [[ord::get_db_block] getInsts] {
 if {[[$m getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
 foreach q [$m getITerms] {
  if {![regexp {^rd_out\[([0-9]+)\]$} [[$q getMTerm] getName] -> bit] || $bit>=256} {continue}
  if {![[$q getNet] isDoNotTouch]} {error "direct data net protection lost"}
  incr protected
 }
}
puts "OT_DIRECT_DATA_NETS_PROTECTED $protected"
write_db /receipt/reconnected.odb
puts OT_CTS_PROTECTION_PREFLIGHT_PASS
