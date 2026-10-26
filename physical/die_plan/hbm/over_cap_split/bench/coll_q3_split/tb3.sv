`timescale 1ns/1ps
module tb;
  reg clk = 0; reg [3:0] mut = 0; integer cyc = 0, errs = 0, seed = 1, ncyc = 4000, dens = 8;
  reg [31:0] r;
  reg [0:0] rst_n = 0;
  reg [1:0] qid = 0;
  wire [0:0] clk_program = {1{clk}};
  wire [0:0] clk_control = {1{clk}};
  wire [15:0] clk_vmasm = {16{clk}};
  wire [15:0] clk_upipe = {16{clk}};
  wire [0:0] clk_issue = {1{clk}};
  wire [28:0] clk_qslots = {29{clk}};
  wire [16:0] clk_ring = {17{clk}};
  wire [32:0] clk_reduce = {33{clk}};
  wire [0:0] clk_arg = {1{clk}};
  wire [15:0] clk_vmwrite = {16{clk}};
  wire [14:0] clk_link = {15{clk}};
  reg [0:0] cfg_v = 0;
  reg [7:0] cfg_target = 0;
  reg [11:0] cfg_addr = 0;
  reg [255:0] cfg_data = 0;
  reg [0:0] desc_v = 0;
  reg [11:0] desc_base = 0;
  reg [12:0] desc_limit = 0;
  reg [15:0] desc_loops = 0;
  reg [0:0] launch_v = 0;
  wire [0:0] ref_program_configured, dut_program_configured;
  wire [0:0] ref_program_init_busy, dut_program_init_busy;
  wire [0:0] ref_program_fault, dut_program_fault;
  wire [0:0] ref_hgi_busy, dut_hgi_busy;
  wire [0:0] ref_hgi_done, dut_hgi_done;
  wire [0:0] ref_hgi_fault, dut_hgi_fault;
  wire [1:0] ref_inj_rd, dut_inj_rd;
  wire [31:0] ref_inj_idx, dut_inj_idx;
  wire [159:0] ref_hgi_inj_addr, dut_hgi_inj_addr;
  reg [1023:0] inj_d = 0;
  wire [3:0] ref_del_valid, dut_del_valid;
  wire [2179:0] ref_del_flit, dut_del_flit;
  wire [159:0] ref_hgi_del_obase, dut_hgi_del_obase;
  reg [0:0] rc_v = 0;
  reg [2:0] rc_tag = 0;
  reg [255:0] rc_d = 0;
  wire [0:0] ref_rr_v, dut_rr_v;
  wire [2:0] ref_rr_tag, dut_rr_tag;
  wire [255:0] ref_rr_d, dut_rr_d;
  reg [2:0] phy_up = 0;
  wire [2:0] ref_tx_pin_v, dut_tx_pin_v;
  wire [1835:0] ref_tx_pin_flit, dut_tx_pin_flit;
  reg [2:0] rx_pin_v = 0;
  reg [1835:0] rx_pin_flit = 0;
  wire [2:0] ref_retry_requested, dut_retry_requested;
  reg [279:0] pr_cw_i = 0;
  reg [279:0] pr_ccw_i = 0;
  wire [279:0] ref_pr_cw_o, dut_pr_cw_o;
  wire [279:0] ref_pr_ccw_o, dut_pr_ccw_o;
  wire [57:0] ref_isa_ring, dut_isa_ring;
  wire [255:0] ref_isa_lp_data, dut_isa_lp_data;
  reg [0:0] ra_lp_we = 0;
  reg [2:0] ra_lp_tag = 0;
  reg [255:0] ra_lp_data = 0;
  reg [0:0] ra_state_read_add = 0;
  reg [0:0] ra_state_read_tx = 0;
  reg [0:0] ra_state_read_rr = 0;
  reg [2:0] ra_state_add_tag = 0;
  reg [2:0] ra_state_tx_tag = 0;
  reg [2:0] ra_state_rr_tag = 0;
  reg [1:0] ra_state_add_src = 0;
  reg [0:0] ra_state_add_rhs_acc = 0;
  reg [0:0] ra_state_tx_acc = 0;
  reg [0:0] ra_add_v = 0;
  reg [2:0] ra_add_tag = 0;
  reg [1:0] ra_add_src = 0;
  reg [0:0] ra_add_rhs_acc = 0;
  reg [1:0] ra_tx_inject = 0;
  reg [1:0] ra_tx_forward = 0;
  reg [2:0] ra_tx_tag = 0;
  reg [1:0] ra_tx_dst = 0;
  reg [0:0] ra_tx_result = 0;
  reg [0:0] ra_tx_acc = 0;
  reg [0:0] ra_tx_gather = 0;
  reg [3:0] ra_tx_ttl = 0;
  reg [1:0] ra_rx_slot = 0;
  reg [3:0] ra_rx_kind = 0;
  reg [3:0] ra_rx_src = 0;
  reg [5:0] ra_rx_tag = 0;
  reg [0:0] ra_rr_local = 0;
  reg [2:0] ra_rr_local_tag = 0;
  wire [1:0] ref_ag_v, dut_ag_v;
  wire [3:0] ref_ag_src, dut_ag_src;
  wire [5:0] ref_ag_tag, dut_ag_tag;
  wire [511:0] ref_ag_d, dut_ag_d;
  wire [135:0] ref_vm_rq, dut_vm_rq;
  reg [2055:0] vm_rr = 0;
  wire [2247:0] ref_vm_kq, dut_vm_kq;
  wire [0:0] ref_tkx_start, dut_tkx_start;
  wire [0:0] ref_tkx_arg_mode, dut_tkx_arg_mode;
  wire [11:0] ref_tkx_cfg_n, dut_tkx_cfg_n;
  wire [12:0] ref_tkx_cfg_k, dut_tkx_cfg_k;
  wire [12:0] ref_tkx_cfg_nout, dut_tkx_cfg_nout;
  wire [7:0] ref_tkx_cfg_g, dut_tkx_cfg_g;
  wire [7:0] ref_tkx_cfg_gbase, dut_tkx_cfg_gbase;
  wire [15:0] ref_tkx_cfg_pf, dut_tkx_cfg_pf;
  wire [39:0] ref_tkx_cfg_obase, dut_tkx_cfg_obase;
  wire [39:0] ref_tkx_cfg_rbase, dut_tkx_cfg_rbase;
  wire [0:0] ref_tkx_cfg_has_r, dut_tkx_cfg_has_r;
  wire [3:0] ref_tkx_del_slot, dut_tkx_del_slot;
  wire [3:0] ref_tkx_del_valid, dut_tkx_del_valid;
  wire [2179:0] ref_tkx_del_flit, dut_tkx_del_flit;
  reg [0:0] tkx_w_v = 0;
  reg [39:0] tkx_w_addr = 0;
  reg [15:0] tkx_w_mask = 0;
  reg [511:0] tkx_w_data = 0;
  reg [0:0] tkx_busy = 0;
  reg [0:0] tkx_done = 0;
  reg [0:0] tkx_fault = 0;
  wire [0:0] ref_fault, dut_fault;
  wire [15:0] ref_fault_cause, dut_fault_cause;
  wire [0:0] ref_done, dut_done;
  wire [31:0] ref_stat_cycles, dut_stat_cycles;
  ot_hfd_coll_q3_hard_v8x_s #(.NLINK(3), .TP(192), .AR_ITER(1), .ROWS(256), .VM_RT(81)) u_ref (
    .rst_n(rst_n),
    .qid(qid),
    .clk_program(clk_program),
    .clk_control(clk_control),
    .clk_vmasm(clk_vmasm),
    .clk_upipe(clk_upipe),
    .clk_issue(clk_issue),
    .clk_qslots(clk_qslots),
    .clk_ring(clk_ring),
    .clk_reduce(clk_reduce),
    .clk_arg(clk_arg),
    .clk_vmwrite(clk_vmwrite),
    .clk_link(clk_link),
    .cfg_v(cfg_v),
    .cfg_target(cfg_target),
    .cfg_addr(cfg_addr),
    .cfg_data(cfg_data),
    .desc_v(desc_v),
    .desc_base(desc_base),
    .desc_limit(desc_limit),
    .desc_loops(desc_loops),
    .launch_v(launch_v),
    .program_configured(ref_program_configured),
    .program_init_busy(ref_program_init_busy),
    .program_fault(ref_program_fault),
    .hgi_busy(ref_hgi_busy),
    .hgi_done(ref_hgi_done),
    .hgi_fault(ref_hgi_fault),
    .inj_rd(ref_inj_rd),
    .inj_idx(ref_inj_idx),
    .hgi_inj_addr(ref_hgi_inj_addr),
    .inj_d(inj_d),
    .del_valid(ref_del_valid),
    .del_flit(ref_del_flit),
    .hgi_del_obase(ref_hgi_del_obase),
    .rc_v(rc_v),
    .rc_tag(rc_tag),
    .rc_d(rc_d),
    .rr_v(ref_rr_v),
    .rr_tag(ref_rr_tag),
    .rr_d(ref_rr_d),
    .phy_up(phy_up),
    .tx_pin_v(ref_tx_pin_v),
    .tx_pin_flit(ref_tx_pin_flit),
    .rx_pin_v(rx_pin_v),
    .rx_pin_flit(rx_pin_flit),
    .retry_requested(ref_retry_requested),
    .pr_cw_i(pr_cw_i),
    .pr_ccw_i(pr_ccw_i),
    .pr_cw_o(ref_pr_cw_o),
    .pr_ccw_o(ref_pr_ccw_o),
    .isa_ring(ref_isa_ring),
    .isa_lp_data(ref_isa_lp_data),
    .ra_lp_we(ra_lp_we),
    .ra_lp_tag(ra_lp_tag),
    .ra_lp_data(ra_lp_data),
    .ra_state_read_add(ra_state_read_add),
    .ra_state_read_tx(ra_state_read_tx),
    .ra_state_read_rr(ra_state_read_rr),
    .ra_state_add_tag(ra_state_add_tag),
    .ra_state_tx_tag(ra_state_tx_tag),
    .ra_state_rr_tag(ra_state_rr_tag),
    .ra_state_add_src(ra_state_add_src),
    .ra_state_add_rhs_acc(ra_state_add_rhs_acc),
    .ra_state_tx_acc(ra_state_tx_acc),
    .ra_add_v(ra_add_v),
    .ra_add_tag(ra_add_tag),
    .ra_add_src(ra_add_src),
    .ra_add_rhs_acc(ra_add_rhs_acc),
    .ra_tx_inject(ra_tx_inject),
    .ra_tx_forward(ra_tx_forward),
    .ra_tx_tag(ra_tx_tag),
    .ra_tx_dst(ra_tx_dst),
    .ra_tx_result(ra_tx_result),
    .ra_tx_acc(ra_tx_acc),
    .ra_tx_gather(ra_tx_gather),
    .ra_tx_ttl(ra_tx_ttl),
    .ra_rx_slot(ra_rx_slot),
    .ra_rx_kind(ra_rx_kind),
    .ra_rx_src(ra_rx_src),
    .ra_rx_tag(ra_rx_tag),
    .ra_rr_local(ra_rr_local),
    .ra_rr_local_tag(ra_rr_local_tag),
    .ag_v(ref_ag_v),
    .ag_src(ref_ag_src),
    .ag_tag(ref_ag_tag),
    .ag_d(ref_ag_d),
    .vm_rq(ref_vm_rq),
    .vm_rr(vm_rr),
    .vm_kq(ref_vm_kq),
    .tkx_start(ref_tkx_start),
    .tkx_arg_mode(ref_tkx_arg_mode),
    .tkx_cfg_n(ref_tkx_cfg_n),
    .tkx_cfg_k(ref_tkx_cfg_k),
    .tkx_cfg_nout(ref_tkx_cfg_nout),
    .tkx_cfg_g(ref_tkx_cfg_g),
    .tkx_cfg_gbase(ref_tkx_cfg_gbase),
    .tkx_cfg_pf(ref_tkx_cfg_pf),
    .tkx_cfg_obase(ref_tkx_cfg_obase),
    .tkx_cfg_rbase(ref_tkx_cfg_rbase),
    .tkx_cfg_has_r(ref_tkx_cfg_has_r),
    .tkx_del_slot(ref_tkx_del_slot),
    .tkx_del_valid(ref_tkx_del_valid),
    .tkx_del_flit(ref_tkx_del_flit),
    .tkx_w_v(tkx_w_v),
    .tkx_w_addr(tkx_w_addr),
    .tkx_w_mask(tkx_w_mask),
    .tkx_w_data(tkx_w_data),
    .tkx_busy(tkx_busy),
    .tkx_done(tkx_done),
    .tkx_fault(tkx_fault),
    .fault(ref_fault),
    .fault_cause(ref_fault_cause),
    .done(ref_done),
    .stat_cycles(ref_stat_cycles));
  q3_asm3 u_dut (.lockstep_mut(mut),
    .rst_n(rst_n),
    .qid(qid),
    .clk_program(clk_program),
    .clk_control(clk_control),
    .clk_vmasm(clk_vmasm),
    .clk_upipe(clk_upipe),
    .clk_issue(clk_issue),
    .clk_qslots(clk_qslots),
    .clk_ring(clk_ring),
    .clk_reduce(clk_reduce),
    .clk_arg(clk_arg),
    .clk_vmwrite(clk_vmwrite),
    .clk_link(clk_link),
    .cfg_v(cfg_v),
    .cfg_target(cfg_target),
    .cfg_addr(cfg_addr),
    .cfg_data(cfg_data),
    .desc_v(desc_v),
    .desc_base(desc_base),
    .desc_limit(desc_limit),
    .desc_loops(desc_loops),
    .launch_v(launch_v),
    .program_configured(dut_program_configured),
    .program_init_busy(dut_program_init_busy),
    .program_fault(dut_program_fault),
    .hgi_busy(dut_hgi_busy),
    .hgi_done(dut_hgi_done),
    .hgi_fault(dut_hgi_fault),
    .inj_rd(dut_inj_rd),
    .inj_idx(dut_inj_idx),
    .hgi_inj_addr(dut_hgi_inj_addr),
    .inj_d(inj_d),
    .del_valid(dut_del_valid),
    .del_flit(dut_del_flit),
    .hgi_del_obase(dut_hgi_del_obase),
    .rc_v(rc_v),
    .rc_tag(rc_tag),
    .rc_d(rc_d),
    .rr_v(dut_rr_v),
    .rr_tag(dut_rr_tag),
    .rr_d(dut_rr_d),
    .phy_up(phy_up),
    .tx_pin_v(dut_tx_pin_v),
    .tx_pin_flit(dut_tx_pin_flit),
    .rx_pin_v(rx_pin_v),
    .rx_pin_flit(rx_pin_flit),
    .retry_requested(dut_retry_requested),
    .pr_cw_i(pr_cw_i),
    .pr_ccw_i(pr_ccw_i),
    .pr_cw_o(dut_pr_cw_o),
    .pr_ccw_o(dut_pr_ccw_o),
    .isa_ring(dut_isa_ring),
    .isa_lp_data(dut_isa_lp_data),
    .ra_lp_we(ra_lp_we),
    .ra_lp_tag(ra_lp_tag),
    .ra_lp_data(ra_lp_data),
    .ra_state_read_add(ra_state_read_add),
    .ra_state_read_tx(ra_state_read_tx),
    .ra_state_read_rr(ra_state_read_rr),
    .ra_state_add_tag(ra_state_add_tag),
    .ra_state_tx_tag(ra_state_tx_tag),
    .ra_state_rr_tag(ra_state_rr_tag),
    .ra_state_add_src(ra_state_add_src),
    .ra_state_add_rhs_acc(ra_state_add_rhs_acc),
    .ra_state_tx_acc(ra_state_tx_acc),
    .ra_add_v(ra_add_v),
    .ra_add_tag(ra_add_tag),
    .ra_add_src(ra_add_src),
    .ra_add_rhs_acc(ra_add_rhs_acc),
    .ra_tx_inject(ra_tx_inject),
    .ra_tx_forward(ra_tx_forward),
    .ra_tx_tag(ra_tx_tag),
    .ra_tx_dst(ra_tx_dst),
    .ra_tx_result(ra_tx_result),
    .ra_tx_acc(ra_tx_acc),
    .ra_tx_gather(ra_tx_gather),
    .ra_tx_ttl(ra_tx_ttl),
    .ra_rx_slot(ra_rx_slot),
    .ra_rx_kind(ra_rx_kind),
    .ra_rx_src(ra_rx_src),
    .ra_rx_tag(ra_rx_tag),
    .ra_rr_local(ra_rr_local),
    .ra_rr_local_tag(ra_rr_local_tag),
    .ag_v(dut_ag_v),
    .ag_src(dut_ag_src),
    .ag_tag(dut_ag_tag),
    .ag_d(dut_ag_d),
    .vm_rq(dut_vm_rq),
    .vm_rr(vm_rr),
    .vm_kq(dut_vm_kq),
    .tkx_start(dut_tkx_start),
    .tkx_arg_mode(dut_tkx_arg_mode),
    .tkx_cfg_n(dut_tkx_cfg_n),
    .tkx_cfg_k(dut_tkx_cfg_k),
    .tkx_cfg_nout(dut_tkx_cfg_nout),
    .tkx_cfg_g(dut_tkx_cfg_g),
    .tkx_cfg_gbase(dut_tkx_cfg_gbase),
    .tkx_cfg_pf(dut_tkx_cfg_pf),
    .tkx_cfg_obase(dut_tkx_cfg_obase),
    .tkx_cfg_rbase(dut_tkx_cfg_rbase),
    .tkx_cfg_has_r(dut_tkx_cfg_has_r),
    .tkx_del_slot(dut_tkx_del_slot),
    .tkx_del_valid(dut_tkx_del_valid),
    .tkx_del_flit(dut_tkx_del_flit),
    .tkx_w_v(tkx_w_v),
    .tkx_w_addr(tkx_w_addr),
    .tkx_w_mask(tkx_w_mask),
    .tkx_w_data(tkx_w_data),
    .tkx_busy(tkx_busy),
    .tkx_done(tkx_done),
    .tkx_fault(tkx_fault),
    .fault(dut_fault),
    .fault_cause(dut_fault_cause),
    .done(dut_done),
    .stat_cycles(dut_stat_cycles));
  always #1 clk = ~clk;
  task automatic drive; begin
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) qid[i+j] = r[j]; end
    cfg_v = {1{1'b0}}; for (int i = 0; i < 1; i++) cfg_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 8; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 8; j++) cfg_target[i+j] = r[j]; end
    for (int i = 0; i < 12; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 12; j++) cfg_addr[i+j] = r[j]; end
    for (int i = 0; i < 256; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 256; j++) cfg_data[i+j] = r[j]; end
    desc_v = {1{1'b0}}; for (int i = 0; i < 1; i++) desc_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 12; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 12; j++) desc_base[i+j] = r[j]; end
    for (int i = 0; i < 13; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 13; j++) desc_limit[i+j] = r[j]; end
    for (int i = 0; i < 16; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 16; j++) desc_loops[i+j] = r[j]; end
    launch_v = {1{1'b0}}; for (int i = 0; i < 1; i++) launch_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 1024; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 1024; j++) inj_d[i+j] = r[j]; end
    rc_v = {1{1'b0}}; for (int i = 0; i < 1; i++) rc_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) rc_tag[i+j] = r[j]; end
    for (int i = 0; i < 256; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 256; j++) rc_d[i+j] = r[j]; end
    phy_up = {3{1'b0}}; for (int i = 0; i < 3; i++) phy_up[i] = ($urandom % dens) == 0;
    rx_pin_v = {3{1'b0}}; for (int i = 0; i < 3; i++) rx_pin_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 1836; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 1836; j++) rx_pin_flit[i+j] = r[j]; end
    for (int i = 0; i < 280; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 280; j++) pr_cw_i[i+j] = r[j]; end
    for (int i = 0; i < 280; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 280; j++) pr_ccw_i[i+j] = r[j]; end
    ra_lp_we = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_lp_we[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_lp_tag[i+j] = r[j]; end
    for (int i = 0; i < 256; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 256; j++) ra_lp_data[i+j] = r[j]; end
    ra_state_read_add = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_state_read_add[i] = ($urandom % dens) == 0;
    ra_state_read_tx = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_state_read_tx[i] = ($urandom % dens) == 0;
    ra_state_read_rr = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_state_read_rr[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_state_add_tag[i+j] = r[j]; end
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_state_tx_tag[i+j] = r[j]; end
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_state_rr_tag[i+j] = r[j]; end
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) ra_state_add_src[i+j] = r[j]; end
    ra_state_add_rhs_acc = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_state_add_rhs_acc[i] = ($urandom % dens) == 0;
    ra_state_tx_acc = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_state_tx_acc[i] = ($urandom % dens) == 0;
    ra_add_v = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_add_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_add_tag[i+j] = r[j]; end
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) ra_add_src[i+j] = r[j]; end
    ra_add_rhs_acc = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_add_rhs_acc[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) ra_tx_inject[i+j] = r[j]; end
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) ra_tx_forward[i+j] = r[j]; end
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_tx_tag[i+j] = r[j]; end
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) ra_tx_dst[i+j] = r[j]; end
    ra_tx_result = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_tx_result[i] = ($urandom % dens) == 0;
    ra_tx_acc = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_tx_acc[i] = ($urandom % dens) == 0;
    ra_tx_gather = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_tx_gather[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 4; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 4; j++) ra_tx_ttl[i+j] = r[j]; end
    for (int i = 0; i < 2; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2; j++) ra_rx_slot[i+j] = r[j]; end
    for (int i = 0; i < 4; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 4; j++) ra_rx_kind[i+j] = r[j]; end
    for (int i = 0; i < 4; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 4; j++) ra_rx_src[i+j] = r[j]; end
    for (int i = 0; i < 6; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 6; j++) ra_rx_tag[i+j] = r[j]; end
    ra_rr_local = {1{1'b0}}; for (int i = 0; i < 1; i++) ra_rr_local[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 3; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 3; j++) ra_rr_local_tag[i+j] = r[j]; end
    for (int i = 0; i < 2056; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 2056; j++) vm_rr[i+j] = r[j]; end
    tkx_w_v = {1{1'b0}}; for (int i = 0; i < 1; i++) tkx_w_v[i] = ($urandom % dens) == 0;
    for (int i = 0; i < 40; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 40; j++) tkx_w_addr[i+j] = r[j]; end
    for (int i = 0; i < 16; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 16; j++) tkx_w_mask[i+j] = r[j]; end
    for (int i = 0; i < 512; i += 32) begin r = $urandom; for (int j = 0; j < 32 && i + j < 512; j++) tkx_w_data[i+j] = r[j]; end
    tkx_busy = {1{1'b0}}; for (int i = 0; i < 1; i++) tkx_busy[i] = ($urandom % dens) == 0;
    tkx_done = {1{1'b0}}; for (int i = 0; i < 1; i++) tkx_done[i] = ($urandom % dens) == 0;
    tkx_fault = {1{1'b0}}; for (int i = 0; i < 1; i++) tkx_fault[i] = ($urandom % dens) == 0;
  end endtask
  initial begin
    if ($value$plusargs("seed=%d", seed)) ; if ($value$plusargs("mut=%d", mut)) ; if ($value$plusargs("cycles=%d", ncyc)) ;
    if ($value$plusargs("dens=%d", dens)) ; r = $urandom(seed); rst_n = 0; qid = 0;
  end
  always @(posedge clk) begin cyc <= cyc + 1;
    if (cyc == 16) rst_n <= 1; else if (cyc > 16 && (cyc % 997) == 0) rst_n <= 0; else if ((cyc % 997) == 8) rst_n <= 1;
    drive();
    if (cyc >= ncyc) begin $display("LOCKSTEP %s mut=%0d seed=%0d dens=%0d cycles=%0d errors=%0d", errs ? "FAIL" : "PASS", mut, seed, dens, cyc, errs); $finish; end
  end
  always @(negedge clk) if (cyc > 2) begin
    if (ref_program_configured !== dut_program_configured) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d program_configured", cyc); end
    if (ref_program_init_busy !== dut_program_init_busy) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d program_init_busy", cyc); end
    if (ref_program_fault !== dut_program_fault) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d program_fault", cyc); end
    if (ref_hgi_busy !== dut_hgi_busy) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d hgi_busy", cyc); end
    if (ref_hgi_done !== dut_hgi_done) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d hgi_done", cyc); end
    if (ref_hgi_fault !== dut_hgi_fault) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d hgi_fault", cyc); end
    if (ref_inj_rd !== dut_inj_rd) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d inj_rd", cyc); end
    if (ref_inj_idx !== dut_inj_idx) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d inj_idx", cyc); end
    if (ref_hgi_inj_addr !== dut_hgi_inj_addr) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d hgi_inj_addr", cyc); end
    if (ref_del_valid !== dut_del_valid) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d del_valid", cyc); end
    if (ref_del_flit !== dut_del_flit) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d del_flit", cyc); end
    if (ref_hgi_del_obase !== dut_hgi_del_obase) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d hgi_del_obase", cyc); end
    if (ref_rr_v !== dut_rr_v) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d rr_v", cyc); end
    if (ref_rr_tag !== dut_rr_tag) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d rr_tag", cyc); end
    if (ref_rr_d !== dut_rr_d) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d rr_d", cyc); end
    if (ref_tx_pin_v !== dut_tx_pin_v) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tx_pin_v", cyc); end
    if (ref_tx_pin_flit !== dut_tx_pin_flit) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tx_pin_flit", cyc); end
    if (ref_retry_requested !== dut_retry_requested) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d retry_requested", cyc); end
    if (ref_pr_cw_o !== dut_pr_cw_o) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d pr_cw_o", cyc); end
    if (ref_pr_ccw_o !== dut_pr_ccw_o) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d pr_ccw_o", cyc); end
    if (ref_isa_ring !== dut_isa_ring) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d isa_ring", cyc); end
    if (ref_isa_lp_data !== dut_isa_lp_data) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d isa_lp_data", cyc); end
    if (ref_ag_v !== dut_ag_v) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d ag_v", cyc); end
    if (ref_ag_src !== dut_ag_src) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d ag_src", cyc); end
    if (ref_ag_tag !== dut_ag_tag) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d ag_tag", cyc); end
    if (ref_ag_d !== dut_ag_d) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d ag_d", cyc); end
    if (ref_vm_rq !== dut_vm_rq) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d vm_rq", cyc); end
    if (ref_vm_kq !== dut_vm_kq) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d vm_kq", cyc); end
    if (ref_tkx_start !== dut_tkx_start) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_start", cyc); end
    if (ref_tkx_arg_mode !== dut_tkx_arg_mode) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_arg_mode", cyc); end
    if (ref_tkx_cfg_n !== dut_tkx_cfg_n) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_n", cyc); end
    if (ref_tkx_cfg_k !== dut_tkx_cfg_k) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_k", cyc); end
    if (ref_tkx_cfg_nout !== dut_tkx_cfg_nout) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_nout", cyc); end
    if (ref_tkx_cfg_g !== dut_tkx_cfg_g) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_g", cyc); end
    if (ref_tkx_cfg_gbase !== dut_tkx_cfg_gbase) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_gbase", cyc); end
    if (ref_tkx_cfg_pf !== dut_tkx_cfg_pf) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_pf", cyc); end
    if (ref_tkx_cfg_obase !== dut_tkx_cfg_obase) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_obase", cyc); end
    if (ref_tkx_cfg_rbase !== dut_tkx_cfg_rbase) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_rbase", cyc); end
    if (ref_tkx_cfg_has_r !== dut_tkx_cfg_has_r) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_cfg_has_r", cyc); end
    if (ref_tkx_del_slot !== dut_tkx_del_slot) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_del_slot", cyc); end
    if (ref_tkx_del_valid !== dut_tkx_del_valid) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_del_valid", cyc); end
    if (ref_tkx_del_flit !== dut_tkx_del_flit) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d tkx_del_flit", cyc); end
    if (ref_fault !== dut_fault) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d fault", cyc); end
    if (ref_fault_cause !== dut_fault_cause) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d fault_cause", cyc); end
    if (ref_done !== dut_done) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d done", cyc); end
    if (ref_stat_cycles !== dut_stat_cycles) begin errs = errs + 1; if (errs <= 20) $display("MISMATCH cyc %0d stat_cycles", cyc); end
  end
endmodule
