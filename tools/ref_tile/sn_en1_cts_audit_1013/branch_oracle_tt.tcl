set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_TT*] {read_liberty $f}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qfd_vm_face_sn_e1/signoff.sdc
puts "SN_CTS_CONTEXT tt actual4_1_cts placementRC unqualified; original source SLEW/waveform/IO preserved"
puts "SN_CTS_SLACK tt setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
set block [ord::get_db_block]
foreach name {_1738_ ot_ohdrv_00260_0 ot_outhold_00260_1 ot_ohdrv_00260_2 output774 place1268} {
 set inst [$block findInst $name]
 foreach it [$inst getITerms] {
  if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
  set net [$it getNet]
  puts "SN_BRANCH_DRIVER $name/[[$it getMTerm] getName] net=[$net getName]"
  foreach sink [$net getITerms] {puts "SN_BRANCH_TERM [[$sink getInst] getName]/[[$sink getMTerm] getName] [[$sink getMTerm] getIoType]"}
 }
}
puts "SN_BRANCH_PASS"
exit
