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
puts "SN_GEOMETRY_BEGIN"
set block [ord::get_db_block]
puts "SN_GEOMETRY_DBU [ord::dbu_to_microns 1000]"
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {[string first 334 $name] >= 0 || $name in {_1738_ ot_ohdrv_00260_0 ot_outhold_00260_1 ot_ohdrv_00260_2 output774 place1268}} {puts "SN_GEOMETRY_INST $name [$inst getLocation]"}
}
foreach term [$block getBTerms] {
 set name [$term getName]
 if {[string first 334 $name]<0} continue
 foreach pin [$term getBPins] {foreach box [$pin getBoxes] {puts "SN_GEOMETRY_PORT $name [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"}}
}
puts "SN_GEOMETRY_PASS"
exit
