`timescale 1ns/1ps
`default_nettype none
module tb;
  logic [0:0] clk;
  logic [0:0] rst_n;
  logic [544:0] u_body_g_q3_arg_out_data;
  logic [2047:0] u_body_vm_as_il;
  logic [0:0] u_body_g_qcap_10_u_cap_src_v;
  logic [0:0] u_body_g_qcap_9_u_cap_src_v;
  logic [544:0] u_body_g_qcap_9_u_cap_src_d;
  logic [0:0] u_body_g_qcap_4_u_cap_src_v;
  logic [544:0] u_body_g_qcap_4_u_cap_src_d;
  logic [0:0] u_body_g_qcap_3_u_cap_src_v;
  logic [544:0] u_body_g_qcap_3_u_cap_src_d;
  logic [0:0] u_body_g_qcap_2_u_cap_src_v;
  logic [544:0] u_body_g_qcap_2_u_cap_src_d;
  logic [2:0] u_body_g_q3_n_u_fj_u_fj_u_link_abort;
  logic [1:0] qid;
  logic [0:0] cfg_v;
  logic [7:0] cfg_target;
  logic [11:0] cfg_addr;
  logic [255:0] cfg_data;
  logic [0:0] desc_v;
  logic [11:0] desc_base;
  logic [12:0] desc_limit;
  logic [15:0] desc_loops;
  logic [0:0] launch_v;
  logic [0:0] rc_v;
  logic [2:0] rc_tag;
  logic [1023:0] inj_d;
  logic [7:0] vm_rr;
  logic [0:0] tkx_busy;
  logic [0:0] tkx_done;
  logic [0:0] tkx_fault;
  logic [0:0] u_body_g_q3_n_u_fj_u_fj_u_reduce_fault;
  logic [0:0] u_body_g_q3_n_u_fj_u_fj_u_writer_fault;
  logic [0:0] u_body_g_q3_n_u_fj_u_fj_u_ring_fault;
  logic [0:0] u_body_arg_fault;
  wire [11:0] r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d, d_u_body_g_qout_17_g3_n_o_u_out_u_dst_d;
  wire [383:0] r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_16_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_15_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_14_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_13_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_12_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_5_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_4_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_11_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_10_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_9_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_8_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_7_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_6_g3_w_o_u_out_u_dst_d;
  wire [5:0] r_u_body_u_upipe_SL_3_u_d3, d_u_body_u_upipe_SL_3_u_d3;
  wire [13:0] r_u_body_u_upipe_SL_4_u_d3, d_u_body_u_upipe_SL_4_u_d3;
  wire [87:0] r_u_body_u_upipe_SL_6_u_d3, d_u_body_u_upipe_SL_6_u_d3;
  wire [74:0] r_u_body_u_upipe_SL_7_u_d3, d_u_body_u_upipe_SL_7_u_d3;
  wire [95:0] r_u_body_u_upipe_SL_8_u_d3, d_u_body_u_upipe_SL_8_u_d3;
  wire [9:0] r_u_body_u_upipe_SL_9_u_d3, d_u_body_u_upipe_SL_9_u_d3;
  wire [14:0] r_u_body_u_upipe_SL_15_u_d3, d_u_body_u_upipe_SL_15_u_d3;
  wire [15:0] r_u_body_g_ariter_t_idx, d_u_body_g_ariter_t_idx;
  wire [3:0] r_u_body_g_ariter_t_pb, d_u_body_g_ariter_t_pb;
  wire [3:0] r_u_body_g_ariter_t_pa, d_u_body_g_ariter_t_pa;
  wire [3:0] r_u_body_g_ariter_t_read, d_u_body_g_ariter_t_read;
  wire [3:0] r_u_body_g_ariter_t_load, d_u_body_g_ariter_t_load;
  wire [511:0] r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_3_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_2_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_1_g3_w_o_u_out_u_dst_d;
  wire [511:0] r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d, d_u_body_g_qout_0_g3_w_o_u_out_u_dst_d;
  wire [15:0] r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v, d_u_body_g_qout_0_g3_w_o_u_out_u_dst_v;
  wire [15:0] r_fault_cause, d_fault_cause;
  wire [1:0] r_inj_rd, d_inj_rd;
  wire [31:0] r_inj_idx, d_inj_idx;
  wire [159:0] r_hgi_inj_addr, d_hgi_inj_addr;
  wire [159:0] r_hgi_del_obase, d_hgi_del_obase;
  wire [159:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin;
  wire [47:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin;
  wire [47:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin;
  wire [47:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin;
  wire [31:0] r_stat_cycles, d_stat_cycles;
  wire [127:0] r_vm_rq, d_vm_rq;
  wire [7:0] r_vm_rq_, d_vm_rq_;
  wire [23:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80;
  wire [7:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0;
  wire [7:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1;
  wire [7:0] r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2, d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2;
  wire [0:0] r_program_configured, d_program_configured;
  wire [0:0] r_program_init_busy, d_program_init_busy;
  wire [0:0] r_program_fault, d_program_fault;
  wire [0:0] r_fault, d_fault;
  wire [0:0] r_hgi_busy, d_hgi_busy;
  wire [0:0] r_done, d_done;
  ot_hfd_coll_q3_body_core u_ref (.clk(clk), .rst_n(rst_n), .u_body_g_q3_arg_out_data(u_body_g_q3_arg_out_data), .u_body_vm_as_il(u_body_vm_as_il), .u_body_g_qcap_10_u_cap_src_v(u_body_g_qcap_10_u_cap_src_v), .u_body_g_qcap_9_u_cap_src_v(u_body_g_qcap_9_u_cap_src_v), .u_body_g_qcap_9_u_cap_src_d(u_body_g_qcap_9_u_cap_src_d), .u_body_g_qcap_4_u_cap_src_v(u_body_g_qcap_4_u_cap_src_v), .u_body_g_qcap_4_u_cap_src_d(u_body_g_qcap_4_u_cap_src_d), .u_body_g_qcap_3_u_cap_src_v(u_body_g_qcap_3_u_cap_src_v), .u_body_g_qcap_3_u_cap_src_d(u_body_g_qcap_3_u_cap_src_d), .u_body_g_qcap_2_u_cap_src_v(u_body_g_qcap_2_u_cap_src_v), .u_body_g_qcap_2_u_cap_src_d(u_body_g_qcap_2_u_cap_src_d), .u_body_g_q3_n_u_fj_u_fj_u_link_abort(u_body_g_q3_n_u_fj_u_fj_u_link_abort), .qid(qid), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .rc_v(rc_v), .rc_tag(rc_tag), .inj_d(inj_d), .vm_rr(vm_rr), .tkx_busy(tkx_busy), .tkx_done(tkx_done), .tkx_fault(tkx_fault), .u_body_g_q3_n_u_fj_u_fj_u_reduce_fault(u_body_g_q3_n_u_fj_u_fj_u_reduce_fault), .u_body_g_q3_n_u_fj_u_fj_u_writer_fault(u_body_g_q3_n_u_fj_u_fj_u_writer_fault), .u_body_g_q3_n_u_fj_u_fj_u_ring_fault(u_body_g_q3_n_u_fj_u_fj_u_ring_fault), .u_body_arg_fault(u_body_arg_fault), .u_body_g_qout_17_g3_n_o_u_out_u_dst_d(r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d), .u_body_g_qout_16_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d), .u_body_g_qout_15_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d), .u_body_g_qout_14_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d), .u_body_g_qout_13_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d), .u_body_g_qout_12_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d), .u_body_g_qout_5_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d), .u_body_g_qout_4_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d), .u_body_g_qout_11_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d), .u_body_g_qout_10_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d), .u_body_g_qout_9_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d), .u_body_g_qout_8_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d), .u_body_g_qout_7_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d), .u_body_g_qout_6_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d), .u_body_u_upipe_SL_3_u_d3(r_u_body_u_upipe_SL_3_u_d3), .u_body_u_upipe_SL_4_u_d3(r_u_body_u_upipe_SL_4_u_d3), .u_body_u_upipe_SL_6_u_d3(r_u_body_u_upipe_SL_6_u_d3), .u_body_u_upipe_SL_7_u_d3(r_u_body_u_upipe_SL_7_u_d3), .u_body_u_upipe_SL_8_u_d3(r_u_body_u_upipe_SL_8_u_d3), .u_body_u_upipe_SL_9_u_d3(r_u_body_u_upipe_SL_9_u_d3), .u_body_u_upipe_SL_15_u_d3(r_u_body_u_upipe_SL_15_u_d3), .u_body_g_ariter_t_idx(r_u_body_g_ariter_t_idx), .u_body_g_ariter_t_pb(r_u_body_g_ariter_t_pb), .u_body_g_ariter_t_pa(r_u_body_g_ariter_t_pa), .u_body_g_ariter_t_read(r_u_body_g_ariter_t_read), .u_body_g_ariter_t_load(r_u_body_g_ariter_t_load), .u_body_g_qout_3_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d), .u_body_g_qout_2_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d), .u_body_g_qout_1_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d), .u_body_g_qout_0_g3_w_o_u_out_u_dst_d(r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d), .u_body_g_qout_0_g3_w_o_u_out_u_dst_v(r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v), .fault_cause(r_fault_cause), .inj_rd(r_inj_rd), .inj_idx(r_inj_idx), .hgi_inj_addr(r_hgi_inj_addr), .hgi_del_obase(r_hgi_del_obase), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin), .stat_cycles(r_stat_cycles), .vm_rq(r_vm_rq), .vm_rq_(r_vm_rq_), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2(r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2), .program_configured(r_program_configured), .program_init_busy(r_program_init_busy), .program_fault(r_program_fault), .fault(r_fault), .hgi_busy(r_hgi_busy), .done(r_done));
  ot_hfd_coll_q3_body_core__split #(.MUT(1)) u_dut (.clk(clk), .rst_n(rst_n), .u_body_g_q3_arg_out_data(u_body_g_q3_arg_out_data), .u_body_vm_as_il(u_body_vm_as_il), .u_body_g_qcap_10_u_cap_src_v(u_body_g_qcap_10_u_cap_src_v), .u_body_g_qcap_9_u_cap_src_v(u_body_g_qcap_9_u_cap_src_v), .u_body_g_qcap_9_u_cap_src_d(u_body_g_qcap_9_u_cap_src_d), .u_body_g_qcap_4_u_cap_src_v(u_body_g_qcap_4_u_cap_src_v), .u_body_g_qcap_4_u_cap_src_d(u_body_g_qcap_4_u_cap_src_d), .u_body_g_qcap_3_u_cap_src_v(u_body_g_qcap_3_u_cap_src_v), .u_body_g_qcap_3_u_cap_src_d(u_body_g_qcap_3_u_cap_src_d), .u_body_g_qcap_2_u_cap_src_v(u_body_g_qcap_2_u_cap_src_v), .u_body_g_qcap_2_u_cap_src_d(u_body_g_qcap_2_u_cap_src_d), .u_body_g_q3_n_u_fj_u_fj_u_link_abort(u_body_g_q3_n_u_fj_u_fj_u_link_abort), .qid(qid), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .rc_v(rc_v), .rc_tag(rc_tag), .inj_d(inj_d), .vm_rr(vm_rr), .tkx_busy(tkx_busy), .tkx_done(tkx_done), .tkx_fault(tkx_fault), .u_body_g_q3_n_u_fj_u_fj_u_reduce_fault(u_body_g_q3_n_u_fj_u_fj_u_reduce_fault), .u_body_g_q3_n_u_fj_u_fj_u_writer_fault(u_body_g_q3_n_u_fj_u_fj_u_writer_fault), .u_body_g_q3_n_u_fj_u_fj_u_ring_fault(u_body_g_q3_n_u_fj_u_fj_u_ring_fault), .u_body_arg_fault(u_body_arg_fault), .u_body_g_qout_17_g3_n_o_u_out_u_dst_d(d_u_body_g_qout_17_g3_n_o_u_out_u_dst_d), .u_body_g_qout_16_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_16_g3_w_o_u_out_u_dst_d), .u_body_g_qout_15_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_15_g3_w_o_u_out_u_dst_d), .u_body_g_qout_14_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_14_g3_w_o_u_out_u_dst_d), .u_body_g_qout_13_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_13_g3_w_o_u_out_u_dst_d), .u_body_g_qout_12_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_12_g3_w_o_u_out_u_dst_d), .u_body_g_qout_5_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_5_g3_w_o_u_out_u_dst_d), .u_body_g_qout_4_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_4_g3_w_o_u_out_u_dst_d), .u_body_g_qout_11_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_11_g3_w_o_u_out_u_dst_d), .u_body_g_qout_10_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_10_g3_w_o_u_out_u_dst_d), .u_body_g_qout_9_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_9_g3_w_o_u_out_u_dst_d), .u_body_g_qout_8_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_8_g3_w_o_u_out_u_dst_d), .u_body_g_qout_7_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_7_g3_w_o_u_out_u_dst_d), .u_body_g_qout_6_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_6_g3_w_o_u_out_u_dst_d), .u_body_u_upipe_SL_3_u_d3(d_u_body_u_upipe_SL_3_u_d3), .u_body_u_upipe_SL_4_u_d3(d_u_body_u_upipe_SL_4_u_d3), .u_body_u_upipe_SL_6_u_d3(d_u_body_u_upipe_SL_6_u_d3), .u_body_u_upipe_SL_7_u_d3(d_u_body_u_upipe_SL_7_u_d3), .u_body_u_upipe_SL_8_u_d3(d_u_body_u_upipe_SL_8_u_d3), .u_body_u_upipe_SL_9_u_d3(d_u_body_u_upipe_SL_9_u_d3), .u_body_u_upipe_SL_15_u_d3(d_u_body_u_upipe_SL_15_u_d3), .u_body_g_ariter_t_idx(d_u_body_g_ariter_t_idx), .u_body_g_ariter_t_pb(d_u_body_g_ariter_t_pb), .u_body_g_ariter_t_pa(d_u_body_g_ariter_t_pa), .u_body_g_ariter_t_read(d_u_body_g_ariter_t_read), .u_body_g_ariter_t_load(d_u_body_g_ariter_t_load), .u_body_g_qout_3_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_3_g3_w_o_u_out_u_dst_d), .u_body_g_qout_2_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_2_g3_w_o_u_out_u_dst_d), .u_body_g_qout_1_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_1_g3_w_o_u_out_u_dst_d), .u_body_g_qout_0_g3_w_o_u_out_u_dst_d(d_u_body_g_qout_0_g3_w_o_u_out_u_dst_d), .u_body_g_qout_0_g3_w_o_u_out_u_dst_v(d_u_body_g_qout_0_g3_w_o_u_out_u_dst_v), .fault_cause(d_fault_cause), .inj_rd(d_inj_rd), .inj_idx(d_inj_idx), .hgi_inj_addr(d_hgi_inj_addr), .hgi_del_obase(d_hgi_del_obase), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin), .stat_cycles(d_stat_cycles), .vm_rq(d_vm_rq), .vm_rq_(d_vm_rq_), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1), .u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2(d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2), .program_configured(d_program_configured), .program_init_busy(d_program_init_busy), .program_fault(d_program_fault), .fault(d_fault), .hgi_busy(d_hgi_busy), .done(d_done));
  integer cyc = 0, checks = 0, errs = 0, tog = 0; logic clk0 = 0;
  always_comb clk = {1{clk0}};
  always #1 clk0 = ~clk0;
  logic [11:0] last_u_body_g_qout_17_g3_n_o_u_out_u_dst_d; logic [11:0] tg_u_body_g_qout_17_g3_n_o_u_out_u_dst_d;
  logic [383:0] last_u_body_g_qout_16_g3_w_o_u_out_u_dst_d; logic [383:0] tg_u_body_g_qout_16_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_15_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_15_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_14_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_14_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_13_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_13_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_12_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_12_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_5_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_5_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_4_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_4_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_11_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_11_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_10_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_10_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_9_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_9_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_8_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_8_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_7_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_7_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_6_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_6_g3_w_o_u_out_u_dst_d;
  logic [5:0] last_u_body_u_upipe_SL_3_u_d3; logic [5:0] tg_u_body_u_upipe_SL_3_u_d3;
  logic [13:0] last_u_body_u_upipe_SL_4_u_d3; logic [13:0] tg_u_body_u_upipe_SL_4_u_d3;
  logic [87:0] last_u_body_u_upipe_SL_6_u_d3; logic [87:0] tg_u_body_u_upipe_SL_6_u_d3;
  logic [74:0] last_u_body_u_upipe_SL_7_u_d3; logic [74:0] tg_u_body_u_upipe_SL_7_u_d3;
  logic [95:0] last_u_body_u_upipe_SL_8_u_d3; logic [95:0] tg_u_body_u_upipe_SL_8_u_d3;
  logic [9:0] last_u_body_u_upipe_SL_9_u_d3; logic [9:0] tg_u_body_u_upipe_SL_9_u_d3;
  logic [14:0] last_u_body_u_upipe_SL_15_u_d3; logic [14:0] tg_u_body_u_upipe_SL_15_u_d3;
  logic [15:0] last_u_body_g_ariter_t_idx; logic [15:0] tg_u_body_g_ariter_t_idx;
  logic [3:0] last_u_body_g_ariter_t_pb; logic [3:0] tg_u_body_g_ariter_t_pb;
  logic [3:0] last_u_body_g_ariter_t_pa; logic [3:0] tg_u_body_g_ariter_t_pa;
  logic [3:0] last_u_body_g_ariter_t_read; logic [3:0] tg_u_body_g_ariter_t_read;
  logic [3:0] last_u_body_g_ariter_t_load; logic [3:0] tg_u_body_g_ariter_t_load;
  logic [511:0] last_u_body_g_qout_3_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_3_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_2_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_2_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_1_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_1_g3_w_o_u_out_u_dst_d;
  logic [511:0] last_u_body_g_qout_0_g3_w_o_u_out_u_dst_d; logic [511:0] tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_d;
  logic [15:0] last_u_body_g_qout_0_g3_w_o_u_out_u_dst_v; logic [15:0] tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_v;
  logic [15:0] last_fault_cause; logic [15:0] tg_fault_cause;
  logic [1:0] last_inj_rd; logic [1:0] tg_inj_rd;
  logic [31:0] last_inj_idx; logic [31:0] tg_inj_idx;
  logic [159:0] last_hgi_inj_addr; logic [159:0] tg_hgi_inj_addr;
  logic [159:0] last_hgi_del_obase; logic [159:0] tg_hgi_del_obase;
  logic [159:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin; logic [159:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin;
  logic [47:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin; logic [47:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin;
  logic [47:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin; logic [47:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin;
  logic [47:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin; logic [47:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin;
  logic [31:0] last_stat_cycles; logic [31:0] tg_stat_cycles;
  logic [127:0] last_vm_rq; logic [127:0] tg_vm_rq;
  logic [7:0] last_vm_rq_; logic [7:0] tg_vm_rq_;
  logic [23:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80; logic [23:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80;
  logic [7:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0; logic [7:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0;
  logic [7:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1; logic [7:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1;
  logic [7:0] last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2; logic [7:0] tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2;
  logic [0:0] last_program_configured; logic [0:0] tg_program_configured;
  logic [0:0] last_program_init_busy; logic [0:0] tg_program_init_busy;
  logic [0:0] last_program_fault; logic [0:0] tg_program_fault;
  logic [0:0] last_fault; logic [0:0] tg_fault;
  logic [0:0] last_hgi_busy; logic [0:0] tg_hgi_busy;
  logic [0:0] last_done; logic [0:0] tg_done;

  localparam int NRW = 32, RS = 72, T0 = 100, T1 = T0 + NRW*RS + 16, T2 = T1 + 280, LP = 400, DIR_END = T2 + 16*LP;
  logic [1535:0] prow [0:NRW-1]; logic [63:0] pmeta [0:NRW-1]; int rowrnd = 0;
  int sel_chg = 0, done_n = 0, cfg_seen = 0; logic [63:0] sel_last = '0;
  initial begin
    if (!$value$plusargs("ROWRND=%d", rowrnd)) rowrnd = 0;
    for (int r = 0; r < NRW; r++) begin
      prow[r] = '0;
      if (rowrnd != 0) for (int w = 0; w < 48; w++) prow[r][w*32 +: 32] = $urandom();
      for (int d = 0; d < 16; d++) prow[r][26 + d*4 +: 4] = 4'($urandom() % 11);
      pmeta[r] = '0;
      pmeta[r][5:0] = 6'(r + 1);
      if (r == NRW-1) begin pmeta[r][5:0] = 6'd0; pmeta[r][44] = 1'b1; end
    end
  end
  always @(posedge clk0) begin
    if (u_dut.u_col0.sel !== sel_last) begin sel_chg <= sel_chg + 1; sel_last <= u_dut.u_col0.sel; end
    if (r_done === 1'b1) done_n <= done_n + 1;
    if (r_program_configured === 1'b1) cfg_seen <= 1;
    if (cyc == DIR_END-1) $display("DIRECTED end cyc=%0d sel_changes=%0d done=%0d configured_seen=%0d program_fault=%b fault=%b fault_cause=%h errs=%0d", cyc, sel_chg, done_n, cfg_seen, r_program_fault, r_fault, r_fault_cause, errs);
  end
  initial begin
    tg_u_body_g_qout_17_g3_n_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_16_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_15_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_14_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_13_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_12_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_5_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_4_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_11_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_10_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_9_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_8_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_7_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_6_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_u_upipe_SL_3_u_d3 = '0;
    tg_u_body_u_upipe_SL_4_u_d3 = '0;
    tg_u_body_u_upipe_SL_6_u_d3 = '0;
    tg_u_body_u_upipe_SL_7_u_d3 = '0;
    tg_u_body_u_upipe_SL_8_u_d3 = '0;
    tg_u_body_u_upipe_SL_9_u_d3 = '0;
    tg_u_body_u_upipe_SL_15_u_d3 = '0;
    tg_u_body_g_ariter_t_idx = '0;
    tg_u_body_g_ariter_t_pb = '0;
    tg_u_body_g_ariter_t_pa = '0;
    tg_u_body_g_ariter_t_read = '0;
    tg_u_body_g_ariter_t_load = '0;
    tg_u_body_g_qout_3_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_2_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_1_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_d = '0;
    tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_v = '0;
    tg_fault_cause = '0;
    tg_inj_rd = '0;
    tg_inj_idx = '0;
    tg_hgi_inj_addr = '0;
    tg_hgi_del_obase = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin = '0;
    tg_stat_cycles = '0;
    tg_vm_rq = '0;
    tg_vm_rq_ = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80 = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0 = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1 = '0;
    tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2 = '0;
    tg_program_configured = '0;
    tg_program_init_busy = '0;
    tg_program_fault = '0;
    tg_fault = '0;
    tg_hgi_busy = '0;
    tg_done = '0;
  end
  always @(negedge clk0) begin
    cyc <= cyc + 1;
    rst_n <= (cyc < 64) ? '0 : '1;
    u_body_g_q3_arg_out_data <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    u_body_vm_as_il <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    u_body_g_qcap_10_u_cap_src_v <= ($urandom() % 8) == 0;
    u_body_g_qcap_9_u_cap_src_v <= ($urandom() % 8) == 0;
    u_body_g_qcap_9_u_cap_src_d <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    u_body_g_qcap_4_u_cap_src_v <= ($urandom() % 8) == 0;
    u_body_g_qcap_4_u_cap_src_d <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    u_body_g_qcap_3_u_cap_src_v <= ($urandom() % 8) == 0;
    u_body_g_qcap_3_u_cap_src_d <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    u_body_g_qcap_2_u_cap_src_v <= ($urandom() % 8) == 0;
    u_body_g_qcap_2_u_cap_src_d <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    u_body_g_q3_n_u_fj_u_fj_u_link_abort <= {$urandom()};
    qid <= {$urandom()};
    cfg_v <= ($urandom() % 8) == 0;
    cfg_target <= ($urandom() % 2) ? 8'd52 : 8'($urandom());
    cfg_addr <= {$urandom()};
    cfg_data <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    desc_v <= ($urandom() % 8) == 0;
    desc_base <= {$urandom()};
    desc_limit <= {$urandom()};
    desc_loops <= {$urandom()};
    launch_v <= ($urandom() % 8) == 0;
    rc_v <= ($urandom() % 8) == 0;
    rc_tag <= {$urandom()};
    inj_d <= {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
    vm_rr <= {$urandom()};
    tkx_busy <= ($urandom() % 8) == 0;
    tkx_done <= ($urandom() % 8) == 0;
    tkx_fault <= ($urandom() % 8) == 0;
    u_body_g_q3_n_u_fj_u_fj_u_reduce_fault <= ($urandom() % 8) == 0;
    u_body_g_q3_n_u_fj_u_fj_u_writer_fault <= ($urandom() % 8) == 0;
    u_body_g_q3_n_u_fj_u_fj_u_ring_fault <= ($urandom() % 8) == 0;
    u_body_arg_fault <= ($urandom() % 8) == 0;

    // directed phase: load a program through the native host frames, then launch it, so sink_select really moves.
    // Faults and other control inputs stay quiet until DIR_END; after it the random stress above takes over.
    if (cyc < DIR_END) begin
      qid <= 2'd0; cfg_v <= 1'b0; cfg_target <= 8'd52; desc_v <= 1'b0; launch_v <= 1'b0; rc_v <= 1'b0;
      u_body_g_q3_n_u_fj_u_fj_u_link_abort <= 3'd0;
      tkx_busy <= 1'b0; tkx_done <= 1'b0; tkx_fault <= 1'b0;
      u_body_g_q3_n_u_fj_u_fj_u_reduce_fault <= 1'b0; u_body_g_q3_n_u_fj_u_fj_u_writer_fault <= 1'b0;
      u_body_g_q3_n_u_fj_u_fj_u_ring_fault <= 1'b0; u_body_arg_fault <= 1'b0;
      desc_base <= 12'd0; desc_limit <= 13'(NRW); desc_loops <= 16'd1;
      if (cyc >= T0 && cyc < T0 + NRW*RS && ((cyc-T0) % RS) < 7) begin
        automatic int r = (cyc-T0)/RS; automatic int w = (cyc-T0)%RS;
        cfg_v <= 1'b1; cfg_addr <= 12'(r*8+w);
        cfg_data <= (w < 6) ? prow[r][w*256 +: 256] : {192'd0, pmeta[r]};
      end
      if (cyc == T1) desc_v <= 1'b1;
      if (cyc >= T2 && ((cyc-T2) % LP) == 0) launch_v <= 1'b1;
    end
  end
  always @(posedge clk0) begin
    if (cyc > 80) begin
      for (int b = 0; b < 12; b++) if (r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d[b] !== d_u_body_g_qout_17_g3_n_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_17_g3_n_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d[b], d_u_body_g_qout_17_g3_n_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_17_g3_n_o_u_out_u_dst_d |= (r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d ^ last_u_body_g_qout_17_g3_n_o_u_out_u_dst_d);
      for (int b = 0; b < 384; b++) if (r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_16_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_16_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_16_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_16_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_16_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_15_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_15_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_15_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_15_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_15_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_14_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_14_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_14_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_14_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_14_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_13_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_13_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_13_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_13_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_13_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_12_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_12_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_12_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_12_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_12_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_5_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_5_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_5_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_5_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_5_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_4_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_4_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_4_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_4_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_4_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_11_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_11_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_11_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_11_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_11_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_10_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_10_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_10_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_10_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_10_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_9_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_9_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_9_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_9_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_9_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_8_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_8_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_8_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_8_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_8_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_7_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_7_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_7_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_7_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_7_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_6_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_6_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_6_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_6_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_6_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 6; b++) if (r_u_body_u_upipe_SL_3_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_3_u_d3[b] !== d_u_body_u_upipe_SL_3_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_3_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_3_u_d3[b], d_u_body_u_upipe_SL_3_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_3_u_d3 |= (r_u_body_u_upipe_SL_3_u_d3 ^ last_u_body_u_upipe_SL_3_u_d3);
      for (int b = 0; b < 14; b++) if (r_u_body_u_upipe_SL_4_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_4_u_d3[b] !== d_u_body_u_upipe_SL_4_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_4_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_4_u_d3[b], d_u_body_u_upipe_SL_4_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_4_u_d3 |= (r_u_body_u_upipe_SL_4_u_d3 ^ last_u_body_u_upipe_SL_4_u_d3);
      for (int b = 0; b < 88; b++) if (r_u_body_u_upipe_SL_6_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_6_u_d3[b] !== d_u_body_u_upipe_SL_6_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_6_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_6_u_d3[b], d_u_body_u_upipe_SL_6_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_6_u_d3 |= (r_u_body_u_upipe_SL_6_u_d3 ^ last_u_body_u_upipe_SL_6_u_d3);
      for (int b = 0; b < 75; b++) if (r_u_body_u_upipe_SL_7_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_7_u_d3[b] !== d_u_body_u_upipe_SL_7_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_7_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_7_u_d3[b], d_u_body_u_upipe_SL_7_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_7_u_d3 |= (r_u_body_u_upipe_SL_7_u_d3 ^ last_u_body_u_upipe_SL_7_u_d3);
      for (int b = 0; b < 96; b++) if (r_u_body_u_upipe_SL_8_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_8_u_d3[b] !== d_u_body_u_upipe_SL_8_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_8_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_8_u_d3[b], d_u_body_u_upipe_SL_8_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_8_u_d3 |= (r_u_body_u_upipe_SL_8_u_d3 ^ last_u_body_u_upipe_SL_8_u_d3);
      for (int b = 0; b < 10; b++) if (r_u_body_u_upipe_SL_9_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_9_u_d3[b] !== d_u_body_u_upipe_SL_9_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_9_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_9_u_d3[b], d_u_body_u_upipe_SL_9_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_9_u_d3 |= (r_u_body_u_upipe_SL_9_u_d3 ^ last_u_body_u_upipe_SL_9_u_d3);
      for (int b = 0; b < 15; b++) if (r_u_body_u_upipe_SL_15_u_d3[b] !== 1'bx && r_u_body_u_upipe_SL_15_u_d3[b] !== d_u_body_u_upipe_SL_15_u_d3[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_u_upipe_SL_15_u_d3[%0d] ref=%b dut=%b", cyc, b, r_u_body_u_upipe_SL_15_u_d3[b], d_u_body_u_upipe_SL_15_u_d3[b]); end
      checks++; tg_u_body_u_upipe_SL_15_u_d3 |= (r_u_body_u_upipe_SL_15_u_d3 ^ last_u_body_u_upipe_SL_15_u_d3);
      for (int b = 0; b < 16; b++) if (r_u_body_g_ariter_t_idx[b] !== 1'bx && r_u_body_g_ariter_t_idx[b] !== d_u_body_g_ariter_t_idx[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_ariter_t_idx[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_ariter_t_idx[b], d_u_body_g_ariter_t_idx[b]); end
      checks++; tg_u_body_g_ariter_t_idx |= (r_u_body_g_ariter_t_idx ^ last_u_body_g_ariter_t_idx);
      for (int b = 0; b < 4; b++) if (r_u_body_g_ariter_t_pb[b] !== 1'bx && r_u_body_g_ariter_t_pb[b] !== d_u_body_g_ariter_t_pb[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_ariter_t_pb[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_ariter_t_pb[b], d_u_body_g_ariter_t_pb[b]); end
      checks++; tg_u_body_g_ariter_t_pb |= (r_u_body_g_ariter_t_pb ^ last_u_body_g_ariter_t_pb);
      for (int b = 0; b < 4; b++) if (r_u_body_g_ariter_t_pa[b] !== 1'bx && r_u_body_g_ariter_t_pa[b] !== d_u_body_g_ariter_t_pa[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_ariter_t_pa[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_ariter_t_pa[b], d_u_body_g_ariter_t_pa[b]); end
      checks++; tg_u_body_g_ariter_t_pa |= (r_u_body_g_ariter_t_pa ^ last_u_body_g_ariter_t_pa);
      for (int b = 0; b < 4; b++) if (r_u_body_g_ariter_t_read[b] !== 1'bx && r_u_body_g_ariter_t_read[b] !== d_u_body_g_ariter_t_read[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_ariter_t_read[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_ariter_t_read[b], d_u_body_g_ariter_t_read[b]); end
      checks++; tg_u_body_g_ariter_t_read |= (r_u_body_g_ariter_t_read ^ last_u_body_g_ariter_t_read);
      for (int b = 0; b < 4; b++) if (r_u_body_g_ariter_t_load[b] !== 1'bx && r_u_body_g_ariter_t_load[b] !== d_u_body_g_ariter_t_load[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_ariter_t_load[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_ariter_t_load[b], d_u_body_g_ariter_t_load[b]); end
      checks++; tg_u_body_g_ariter_t_load |= (r_u_body_g_ariter_t_load ^ last_u_body_g_ariter_t_load);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_3_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_3_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_3_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_3_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_3_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_2_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_2_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_2_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_2_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_2_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_1_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_1_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_1_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_1_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_1_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 512; b++) if (r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d[b] !== 1'bx && r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d[b] !== d_u_body_g_qout_0_g3_w_o_u_out_u_dst_d[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_0_g3_w_o_u_out_u_dst_d[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d[b], d_u_body_g_qout_0_g3_w_o_u_out_u_dst_d[b]); end
      checks++; tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_d |= (r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d ^ last_u_body_g_qout_0_g3_w_o_u_out_u_dst_d);
      for (int b = 0; b < 16; b++) if (r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v[b] !== 1'bx && r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v[b] !== d_u_body_g_qout_0_g3_w_o_u_out_u_dst_v[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_qout_0_g3_w_o_u_out_u_dst_v[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v[b], d_u_body_g_qout_0_g3_w_o_u_out_u_dst_v[b]); end
      checks++; tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_v |= (r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v ^ last_u_body_g_qout_0_g3_w_o_u_out_u_dst_v);
      for (int b = 0; b < 16; b++) if (r_fault_cause[b] !== 1'bx && r_fault_cause[b] !== d_fault_cause[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d fault_cause[%0d] ref=%b dut=%b", cyc, b, r_fault_cause[b], d_fault_cause[b]); end
      checks++; tg_fault_cause |= (r_fault_cause ^ last_fault_cause);
      for (int b = 0; b < 2; b++) if (r_inj_rd[b] !== 1'bx && r_inj_rd[b] !== d_inj_rd[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d inj_rd[%0d] ref=%b dut=%b", cyc, b, r_inj_rd[b], d_inj_rd[b]); end
      checks++; tg_inj_rd |= (r_inj_rd ^ last_inj_rd);
      for (int b = 0; b < 32; b++) if (r_inj_idx[b] !== 1'bx && r_inj_idx[b] !== d_inj_idx[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d inj_idx[%0d] ref=%b dut=%b", cyc, b, r_inj_idx[b], d_inj_idx[b]); end
      checks++; tg_inj_idx |= (r_inj_idx ^ last_inj_idx);
      for (int b = 0; b < 160; b++) if (r_hgi_inj_addr[b] !== 1'bx && r_hgi_inj_addr[b] !== d_hgi_inj_addr[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d hgi_inj_addr[%0d] ref=%b dut=%b", cyc, b, r_hgi_inj_addr[b], d_hgi_inj_addr[b]); end
      checks++; tg_hgi_inj_addr |= (r_hgi_inj_addr ^ last_hgi_inj_addr);
      for (int b = 0; b < 160; b++) if (r_hgi_del_obase[b] !== 1'bx && r_hgi_del_obase[b] !== d_hgi_del_obase[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d hgi_del_obase[%0d] ref=%b dut=%b", cyc, b, r_hgi_del_obase[b], d_hgi_del_obase[b]); end
      checks++; tg_hgi_del_obase |= (r_hgi_del_obase ^ last_hgi_del_obase);
      for (int b = 0; b < 160; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin);
      for (int b = 0; b < 48; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin);
      for (int b = 0; b < 48; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin);
      for (int b = 0; b < 48; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin);
      for (int b = 0; b < 32; b++) if (r_stat_cycles[b] !== 1'bx && r_stat_cycles[b] !== d_stat_cycles[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d stat_cycles[%0d] ref=%b dut=%b", cyc, b, r_stat_cycles[b], d_stat_cycles[b]); end
      checks++; tg_stat_cycles |= (r_stat_cycles ^ last_stat_cycles);
      for (int b = 0; b < 128; b++) if (r_vm_rq[b] !== 1'bx && r_vm_rq[b] !== d_vm_rq[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d vm_rq[%0d] ref=%b dut=%b", cyc, b, r_vm_rq[b], d_vm_rq[b]); end
      checks++; tg_vm_rq |= (r_vm_rq ^ last_vm_rq);
      for (int b = 0; b < 8; b++) if (r_vm_rq_[b] !== 1'bx && r_vm_rq_[b] !== d_vm_rq_[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d vm_rq_[%0d] ref=%b dut=%b", cyc, b, r_vm_rq_[b], d_vm_rq_[b]); end
      checks++; tg_vm_rq_ |= (r_vm_rq_ ^ last_vm_rq_);
      for (int b = 0; b < 24; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80 |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80 ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80);
      for (int b = 0; b < 8; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0 |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0 ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0);
      for (int b = 0; b < 8; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1 |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1 ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1);
      for (int b = 0; b < 8; b++) if (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2[b] !== 1'bx && r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2[b] !== d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2[%0d] ref=%b dut=%b", cyc, b, r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2[b], d_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2[b]); end
      checks++; tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2 |= (r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2 ^ last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2);
      for (int b = 0; b < 1; b++) if (r_program_configured[b] !== 1'bx && r_program_configured[b] !== d_program_configured[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d program_configured[%0d] ref=%b dut=%b", cyc, b, r_program_configured[b], d_program_configured[b]); end
      checks++; tg_program_configured |= (r_program_configured ^ last_program_configured);
      for (int b = 0; b < 1; b++) if (r_program_init_busy[b] !== 1'bx && r_program_init_busy[b] !== d_program_init_busy[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d program_init_busy[%0d] ref=%b dut=%b", cyc, b, r_program_init_busy[b], d_program_init_busy[b]); end
      checks++; tg_program_init_busy |= (r_program_init_busy ^ last_program_init_busy);
      for (int b = 0; b < 1; b++) if (r_program_fault[b] !== 1'bx && r_program_fault[b] !== d_program_fault[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d program_fault[%0d] ref=%b dut=%b", cyc, b, r_program_fault[b], d_program_fault[b]); end
      checks++; tg_program_fault |= (r_program_fault ^ last_program_fault);
      for (int b = 0; b < 1; b++) if (r_fault[b] !== 1'bx && r_fault[b] !== d_fault[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d fault[%0d] ref=%b dut=%b", cyc, b, r_fault[b], d_fault[b]); end
      checks++; tg_fault |= (r_fault ^ last_fault);
      for (int b = 0; b < 1; b++) if (r_hgi_busy[b] !== 1'bx && r_hgi_busy[b] !== d_hgi_busy[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d hgi_busy[%0d] ref=%b dut=%b", cyc, b, r_hgi_busy[b], d_hgi_busy[b]); end
      checks++; tg_hgi_busy |= (r_hgi_busy ^ last_hgi_busy);
      for (int b = 0; b < 1; b++) if (r_done[b] !== 1'bx && r_done[b] !== d_done[b]) begin errs++; if (errs <= 10) $display("MISMATCH cyc=%0d done[%0d] ref=%b dut=%b", cyc, b, r_done[b], d_done[b]); end
      checks++; tg_done |= (r_done ^ last_done);
    end
    last_u_body_g_qout_17_g3_n_o_u_out_u_dst_d <= r_u_body_g_qout_17_g3_n_o_u_out_u_dst_d;
    last_u_body_g_qout_16_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_16_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_15_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_15_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_14_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_14_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_13_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_13_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_12_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_12_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_5_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_5_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_4_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_4_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_11_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_11_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_10_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_10_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_9_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_9_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_8_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_8_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_7_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_7_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_6_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_6_g3_w_o_u_out_u_dst_d;
    last_u_body_u_upipe_SL_3_u_d3 <= r_u_body_u_upipe_SL_3_u_d3;
    last_u_body_u_upipe_SL_4_u_d3 <= r_u_body_u_upipe_SL_4_u_d3;
    last_u_body_u_upipe_SL_6_u_d3 <= r_u_body_u_upipe_SL_6_u_d3;
    last_u_body_u_upipe_SL_7_u_d3 <= r_u_body_u_upipe_SL_7_u_d3;
    last_u_body_u_upipe_SL_8_u_d3 <= r_u_body_u_upipe_SL_8_u_d3;
    last_u_body_u_upipe_SL_9_u_d3 <= r_u_body_u_upipe_SL_9_u_d3;
    last_u_body_u_upipe_SL_15_u_d3 <= r_u_body_u_upipe_SL_15_u_d3;
    last_u_body_g_ariter_t_idx <= r_u_body_g_ariter_t_idx;
    last_u_body_g_ariter_t_pb <= r_u_body_g_ariter_t_pb;
    last_u_body_g_ariter_t_pa <= r_u_body_g_ariter_t_pa;
    last_u_body_g_ariter_t_read <= r_u_body_g_ariter_t_read;
    last_u_body_g_ariter_t_load <= r_u_body_g_ariter_t_load;
    last_u_body_g_qout_3_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_3_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_2_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_2_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_1_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_1_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_0_g3_w_o_u_out_u_dst_d <= r_u_body_g_qout_0_g3_w_o_u_out_u_dst_d;
    last_u_body_g_qout_0_g3_w_o_u_out_u_dst_v <= r_u_body_g_qout_0_g3_w_o_u_out_u_dst_v;
    last_fault_cause <= r_fault_cause;
    last_inj_rd <= r_inj_rd;
    last_inj_idx <= r_inj_idx;
    last_hgi_inj_addr <= r_hgi_inj_addr;
    last_hgi_del_obase <= r_hgi_del_obase;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin;
    last_stat_cycles <= r_stat_cycles;
    last_vm_rq <= r_vm_rq;
    last_vm_rq_ <= r_vm_rq_;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80 <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0 <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1 <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1;
    last_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2 <= r_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2;
    last_program_configured <= r_program_configured;
    last_program_init_busy <= r_program_init_busy;
    last_program_fault <= r_program_fault;
    last_fault <= r_fault;
    last_hgi_busy <= r_hgi_busy;
    last_done <= r_done;
    if (cyc == DIR_END + 5920) begin
      tog = 0;
      tog += $countones(tg_u_body_g_qout_17_g3_n_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_16_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_15_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_14_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_13_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_12_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_5_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_4_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_11_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_10_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_9_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_8_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_7_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_6_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_u_upipe_SL_3_u_d3);
      tog += $countones(tg_u_body_u_upipe_SL_4_u_d3);
      tog += $countones(tg_u_body_u_upipe_SL_6_u_d3);
      tog += $countones(tg_u_body_u_upipe_SL_7_u_d3);
      tog += $countones(tg_u_body_u_upipe_SL_8_u_d3);
      tog += $countones(tg_u_body_u_upipe_SL_9_u_d3);
      tog += $countones(tg_u_body_u_upipe_SL_15_u_d3);
      tog += $countones(tg_u_body_g_ariter_t_idx);
      tog += $countones(tg_u_body_g_ariter_t_pb);
      tog += $countones(tg_u_body_g_ariter_t_pa);
      tog += $countones(tg_u_body_g_ariter_t_read);
      tog += $countones(tg_u_body_g_ariter_t_load);
      tog += $countones(tg_u_body_g_qout_3_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_2_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_1_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_d);
      tog += $countones(tg_u_body_g_qout_0_g3_w_o_u_out_u_dst_v);
      tog += $countones(tg_fault_cause);
      tog += $countones(tg_inj_rd);
      tog += $countones(tg_inj_idx);
      tog += $countones(tg_hgi_inj_addr);
      tog += $countones(tg_hgi_del_obase);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rgx_addr_pin);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_wr_sequence_pin);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rd_sequence_pin);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_rx_sequence_pin);
      tog += $countones(tg_stat_cycles);
      tog += $countones(tg_vm_rq);
      tog += $countones(tg_vm_rq_);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_vm_select_pipe_80);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_0);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_1);
      tog += $countones(tg_u_body_g_q3_genblk1_n_u_control_r_u_control_u_u_link_epoch_2);
      tog += $countones(tg_program_configured);
      tog += $countones(tg_program_init_busy);
      tog += $countones(tg_program_fault);
      tog += $countones(tg_fault);
      tog += $countones(tg_hgi_busy);
      tog += $countones(tg_done);
      if (errs == 0) $display("LOCKSTEP PASS checks=%0d toggled_out_bits=%0d sel_changes=%0d done=%0d", checks, tog, sel_chg, done_n);
      else $display("LOCKSTEP FAIL errs=%0d checks=%0d toggled_out_bits=%0d sel_changes=%0d done=%0d", errs, checks, tog, sel_chg, done_n);
      $finish;
    end
  end
endmodule
