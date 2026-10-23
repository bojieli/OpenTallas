set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $plat/lib/NLDM/*INVBUF*RVT_TT*] {read_liberty $l}
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /test/protect_api.v
link_design protect_api
set b [ord::get_db_block]
set i [$b findInst u_ck]
set a [$i findITerm A]
set old [$a getNet]
set n [odb::dbNet_create $b fixture_reparent]
set_dont_touch [get_cells u_ck]
puts "PROTECT flag=[$i isDoNotTouch] inputnetprotected=[$old isDoNotTouch]"
set rc [catch {$a disconnect; $a connect $n} msg]
puts "PROTECTED_REPARENT rc=$rc msg=$msg"
if {$rc} {
 $i setDoNotTouch 0
 $a disconnect
 $a connect $n
 $i setDoNotTouch 1
 puts "EXACT_RELEASE_RESTORE PASS flag=[$i isDoNotTouch]"
}
puts "PROTECT_API_DONE"
exit
