set p /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $p/lef/asap7_tech_1x_201209.lef
read_lef $p/lef/asap7sc7p5t_28_R_1x_220121a.lef
define_corners tt ff
foreach corner {TT FF} scene {tt ff} {
 foreach stem {AO_RVT_%s_nldm_211120.lib.gz INVBUF_RVT_%s_nldm_220122.lib.gz OA_RVT_%s_nldm_211120.lib.gz SEQ_RVT_%s_nldm_220123.lib SIMPLE_RVT_%s_nldm_211120.lib.gz} {set f [format $stem $corner]; read_liberty -corner $scene $p/lib/NLDM/asap7sc7p5t_$f}
}
read_db /placed/placed.odb
set b [ord::get_db_block]
set f [open /audit/graph.tsv w]
puts $f "META	units	[$b getDbUnitsPerMicron]"
puts $f "META	die	[[$b getDieArea] xMin]	[[$b getDieArea] yMin]	[[$b getDieArea] xMax]	[[$b getDieArea] yMax]"
foreach i [$b getInsts] {
 set m [$i getMaster]; set box [$i getBBox]
 puts $f "CELL	[$i getName]	[$m getName]	[$i getOrient]	[$i getPlacementStatus]	[$box xMin]	[$box yMin]	[$box xMax]	[$box yMax]"
 foreach t [$i getITerms] {
  set n [$t getNet]; set nn {}; if {$n ne "NULL"} {set nn [$n getName]}
  set mt [$t getMTerm]; set xy [$t getAvgXY]
  puts $f "PIN	[$i getName]/[$mt getName]	[$mt getIoType]	[$mt getSigType]	$nn	[join $xy \t]"
 }
}
foreach t [$b getBTerms] {
 set n [$t getNet]; set nn {}; if {$n ne "NULL"} {set nn [$n getName]}
 foreach bp [$t getBPins] {foreach bb [$bp getBoxes] {puts $f "PORT	[$t getName]	[$t getIoType]	[$t getSigType]	$nn	[[$bb getTechLayer] getName]	[$bb xMin]	[$bb yMin]	[$bb xMax]	[$bb yMax]"}}
}
foreach r [$b getRows] {puts $f "ROW	[$r getName]	[$r getOrigin]	[$r getSiteCount]	[$r getSpacing]	[[$r getSite] getWidth]	[[$r getSite] getHeight]	[$r getDirection]"}
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} {continue}
 puts $f "PGNET	[$n getName]	[llength [$n getITerms]]	[llength [$n getSWires]]"
 foreach sw [$n getSWires] {foreach sb [$sw getWires] {if {[$sb isVia]} {puts $f "PGVIA	[$n getName]	[$sb xMin]	[$sb yMin]	[$sb xMax]	[$sb yMax]"} else {puts $f "PGBOX	[$n getName]	[[$sb getTechLayer] getName]	[$sb xMin]	[$sb yMin]	[$sb xMax]	[$sb yMax]"}}}
}
close $f
# Source/native identity validation from original import contract.
source /input/verify_import.tcl
create_clock -name core_clk -period 833.333 [get_ports ck]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
source $p/setRC.tcl
estimate_parasitics -placement
report_checks -from [all_registers -clock_pins] -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout input_pin net} > /audit/functional_setup_tt.txt
report_checks -from [get_pins c2203/Y] -to [get_pins cpo216_ff/D] -path_delay max -format full_clock_expanded -fields {slew cap fanout input_pin net} > /audit/downstream_tt.txt
puts "READONLY_AUDIT_FINISHED"
exit
