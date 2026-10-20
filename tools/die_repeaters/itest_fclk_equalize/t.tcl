set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l {SEQ_RVT_TT_nldm_220123.lib INVBUF_RVT_TT_nldm_220122.lib.gz SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $P/lib/NLDM/asap7sc7p5t_$l }
read_verilog /work/t.v
link_design t
initialize_floorplan -die_area {0 0 200 200} -core_area {2 2 198 198} -site asap7sc7p5t
place_inst -name src -location {10 10} -status PLACED
place_inst -name fwd -location {10 20} -status PLACED
place_inst -name cap -location {150 150} -status PLACED
source /work/die_repeaters.tcl
source /work/fclk_audit.tcl
ot_die_rep_fclk_snapshot
set blk [ord::get_db_block]; set m [[ord::get_db] findMaster BUFx8_ASAP7_75t_R]
proc chain {blk m netname capname pin n tag} {
  set it [[$blk findInst $capname] findITerm $pin]; set prev [$it getNet]; $it disconnect
  for {set j 0} {$j < $n} {incr j} {
    set bi [odb::dbInst_create $blk $m "${tag}_$j"]; set nn [odb::dbNet_create $blk "${tag}_${j}_y"]
    [$bi findITerm A] connect $prev; [$bi findITerm Y] connect $nn
    $bi setLocation [expr {20000 + 30000*$j}] 40000; $bi setPlacementStatus PLACED; set prev $nn
  }
  $it connect $prev
}
chain $blk $m d cap D 3 drep
chain $blk $m n_a_fck cap CLK 1 frep
set r0 [ot_die_rep_fclk_audit /work/out/a0 {n*_fck*} {BUFx8_ASAP7_75t_R}]
set u [ot_die_rep_fclk_equalize /work/out/eq {n*_fck*} {BUFx8_ASAP7_75t_R}]
set r1 [ot_die_rep_fclk_audit /work/out/a1 {n*_fck*} {BUFx8_ASAP7_75t_R}]
puts "EQTEST before=$r0 unfixable=$u after=$r1"
foreach i [$blk getInsts] { if {[string match fclkeq_* [$i getName]]} { puts "EQINST [$i getName] [$i getLocation] [$i getPlacementStatus]" } }
if {$r0 == 1 && $u == 0 && $r1 == 0} { puts EQTEST_PASS } else { puts EQTEST_FAIL; exit 1 }
