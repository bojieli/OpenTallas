yosys read_rtlil /work/front/upstream.il
yosys select -set ot_target {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8862} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8863} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8864} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8865} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8866} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8867} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8868} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8869} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8870} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8871} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8872} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8873} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8874} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8875} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8876} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8877} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8878} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8879} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8880} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$8881} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$9042} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$9043} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$9044} {qfd_qc_su_lane_w_l0/c:$auto$ff.cc:337:slice$9045}
yosys select -set ot_other * @ot_target %d
yosys opt_muxtree
yosys opt_reduce -full
yosys wreduce
yosys techmap
for {set i 0} {$i<12} {incr i} {
 yosys select -set ot_other * @ot_target %d
 yosys opt_expr -mux_undef -mux_bool -undriven -fine
 yosys opt_dff @ot_other
 yosys opt_clean
}
yosys write_json /work/front/upstream2.json
yosys write_rtlil /work/front/upstream2.il
