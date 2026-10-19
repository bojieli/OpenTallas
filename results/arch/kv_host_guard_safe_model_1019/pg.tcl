set p /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $p/lef/asap7_tech_1x_201209.lef
read_lef $p/lef/asap7sc7p5t_28_R_1x_220121a.lef
define_corners tt ff
foreach corner {TT FF} scene {tt ff} {
 foreach stem {AO_RVT_%s_nldm_211120.lib.gz INVBUF_RVT_%s_nldm_220122.lib.gz OA_RVT_%s_nldm_211120.lib.gz SEQ_RVT_%s_nldm_220123.lib SIMPLE_RVT_%s_nldm_211120.lib.gz} {set f [format $stem $corner]; read_liberty -corner $scene $p/lib/NLDM/asap7sc7p5t_$f}
}
read_lef /source/physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.lef
read_db /odb/$::env(ODBFILE)
set b [ord::get_db_block]
set f [open /audit/$::env(ODBFILE).pg.tsv w]
puts $f "instance	master	pin	role	actual_net	actual_role	protected	missing_iterm"
set masters [dict create]
foreach inst [$b getInsts] {
 set master [$inst getMaster]; dict set masters [$master getName] $master
 foreach mt [$master getMTerms] {
  set role [$mt getSigType]; if {$role ni {POWER GROUND}} continue
  set pin [$mt getName];set term [$inst findITerm $pin];set an "";set ar "";set missing 0
  if {$term eq "NULL"} {set missing 1} else {set net [$term getNet];if {$net ne "NULL"} {set an [$net getName];set ar [$net getSigType]}}
  puts $f [join [list [$inst getName] [$master getName] $pin $role $an $ar [$inst isDoNotTouch] $missing] "\t"]
 }
}
close $f
set f [open /audit/$::env(ODBFILE).master_pg.tsv w]
dict for {name master} $masters {
 foreach mt [$master getMTerms] {
  if {[$mt getSigType] ni {POWER GROUND}} continue
  set geo {};foreach mp [$mt getMPins] {foreach box [$mp getGeometry] {lappend geo [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
  puts $f [join [list $name [$master getWidth] [$master getHeight] [$mt getName] [$mt getSigType] $geo] "\t"]
 }
}
close $f
set f [open /audit/$::env(ODBFILE).global_rules.tsv w]
foreach rule [$b getGlobalConnects] {set r [$rule getRegion];if {$r ne "NULL"} {set r [$r getName]};puts $f [join [list [$rule getInstPattern] [$rule getPinPattern] [[$rule getNet] getName] $r] "\t"]}
close $f
puts "READ_ONLY_PG_COMPLETE"
exit
