read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_db /work/results/asap7/opentallas_ot_hgi_sm_xload_cl2_bdring_asap7_ref_hgi_sm_xl2_bdring_cl2d_COMMIT_b0d45974d/base/6_final.odb
set b [ord::get_db_block]
set bt [$b findBTerm {bq_d[420]}]
set net [$bt getNet]
for {set k 0} {$k<20} {incr k} {
 set drv "NULL"
 foreach it [$net getITerms] {if {[$it isOutputSignal]} {set drv $it;break}}
 if {$drv eq "NULL"} {break}
 set inst [$drv getInst];set m [[$inst getMaster] getName]
 puts "CHAIN $k [$net getName] [$inst getName] $m [$inst getLocation]"
 if {[string match DFF* $m]} {break}
 set next "NULL"
 foreach it [$inst getITerms] {if {[$it isInputSignal] && [[$it getMTerm] getName] ne "CLK"} {set next [$it getNet];break}}
 if {$next eq "NULL"} {break};set net $next
}
exit
