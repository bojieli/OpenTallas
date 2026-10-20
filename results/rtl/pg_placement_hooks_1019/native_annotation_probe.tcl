set libroot /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach pattern {*AO_RVT_TT* *INVBUF_RVT_TT* *OA_RVT_TT* *SEQ_RVT_TT* *SIMPLE_RVT_TT*} {
 foreach lib [glob $libroot/$pattern] {read_liberty $lib}
}
set db [lindex [glob /orig/results/asap7/*/base/3_place.odb] 0]
read_db $db
read_sdc [file rootname $db].sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set scene [sta::cmd_scene]
puts "SCENE $scene cmds=[info commands sta::*scene*]"
proc census {} {
 set pins [get_pins -hierarchical *]
 foreach port [get_ports *] {lappend pins [sta::get_port_pin $port]}
 set yes 0; set no 0; set err 0
 foreach p $pins {
  set code [catch {sta::parasitics_annotated $p [sta::cmd_scene]} result]
  if {$code} {incr err; if {$err < 3} {puts "PIN_ERR $p $result"}} elseif {$result} {incr yes} else {incr no}
 }
 puts "GRT_ROUTES [grt::have_routes]"
 puts "PIN_CENSUS annotated=$yes unannotated=$no errors=$err"
}
census
estimate_parasitics -placement
census
set net [[ord::get_db_block] findNet clk]
set probe [odb::dbInst_create [ord::get_db_block] [[ord::get_db] findMaster BUFx4_ASAP7_75t_R] rc_probe]
set it [$probe findITerm A]
$it connect $net
set endpoint "[[$it getInst] getName]:[[$it getMTerm] getName]"
set fh [open /proof/partial.spef w]
puts $fh {*SPEF "IEEE 1481-1998"
*DESIGN "ot_hbm_static_cfg_collar_idx256"
*DATE "2026-10-19"
*VENDOR "OpenTallas"
*PROGRAM "causal probe"
*VERSION "1"
*DESIGN_FLOW "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]
*T_UNIT 1 PS
*C_UNIT 1 FF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY}
puts $fh "*D_NET clk 0.1\n*CONN\n*P clk I\n*I $endpoint I\n*CAP\n1 $endpoint 0.1\n*RES\n1 clk $endpoint 1\n*END"
close $fh
read_spef /proof/partial.spef
census
exit
