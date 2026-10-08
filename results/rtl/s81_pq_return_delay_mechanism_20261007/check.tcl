read_lef /tmp/bf_phase_sta_fixture/asap7_tech_1x_201209.lef
read_lef /tmp/bf_phase_sta_fixture/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /home/ubuntu/OpenTallas/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /home/ubuntu/OpenTallas/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_verilog /tmp/pq-delay-eco-fixture/top.v
link_design top
initialize_floorplan -site asap7sc7p5t -die_area {0 0 30 30} -core_area {2.16 2.16 27.84 27.84}
set b [ord::get_db_block]
foreach {name x y} {source0 10000 10000 q0 13000 10000 source1 10000 16000 q1 13000 16000} {
 set i [$b findInst $name]; $i setLocation $x $y; $i setPlacementStatus PLACED
}
set pq_delay_plan {{q0 D source0 Y n0 3} {q1 D source1 Y n1 3}}
source /home/ubuntu/OpenTallas/physical/s81_pq_return_delay/insert.tcl
pq_delay_apply
detailed_placement
check_placement -verbose
pq_delay_check 1
write_db /tmp/pq-delay-eco-fixture/positive.odb
set d0 [[$b findInst q0] findITerm D];set d1 [[$b findInst q1] findITerm D]
set n0 [$d0 getNet];set n1 [$d1 getNet]
$d0 disconnect; $d1 disconnect; $d0 connect $n1; $d1 connect $n0
if {![catch {pq_delay_check 0} err]} {error "PQ_DELAY swapped capture mutant escaped"}
puts "PQ_DELAY_SWAP_MUTANT_REJECTED $err"
$d0 disconnect; $d1 disconnect; $d0 connect $n0; $d1 connect $n1
set broken [$b findInst pq_return_hold_e00000_s1]
unset_dont_touch [get_cells pq_return_hold_e00000_s1]
odb::dbInst_destroy $broken
if {![catch {pq_delay_check 0} err]} {error "PQ_DELAY removed cell mutant escaped"}
puts "PQ_DELAY_DROP_MUTANT_REJECTED $err"
puts "PQ_DELAY_MECHANISM_GATE_PASS"
exit
