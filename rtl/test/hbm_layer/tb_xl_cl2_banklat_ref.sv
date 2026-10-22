`timescale 1ns/1ps
// STEWARD-TOK-HBM 10-21: reference latency of the cl2 x-load ctl (ot_hgi_sm_xload_cl2_ctlx) against ot_vms_bank_static
// wired directly (no die stages) -- the RD_LAT the die-latency checker (tools/hbm_die_v16/d4g_bank_latency.py) must use
// as the ctl's reference.  One x-load command (DS L0 wq_a: base 16384, n 5120, p 1, fmt 1 FP8 block-dot) from the MODE 1
// table; prints RESP_BAD (ctl resp_bad: a wave's 8 bank answers not on the edge md[RLM+1] expects) and XL_REF PASS|FAIL.
// Run (Verilator 5.050): -GRDL=6 -> FAIL (first wave answers one edge after the check), -GRDL=7 -> PASS.
//   build: --binary --timing --top-module tb_xl_cl2_banklat_ref -GRDL=7 <die files> ot_vms_bank_static.sv this.sv
module tb_xl_cl2_banklat_ref #(parameter integer RDL = 7);
  reg clk = 0; always #1 clk = ~clk;
  reg rst_n = 0;
  reg cfg_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
  reg desc_v = 0; reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0; reg launch_v = 0;
  wire configured, fault, active, rn_o, qv_lo, qv_hi;
  wire [135:0] rq; wire [8*257-1:0] rr; wire [2047:0] l_d_o;
  wire qo_lo, qo_hi, qf_lo, qf_hi;
  ot_hgi_sm_xload_cl2_ctlx #(.PMAX(8), .RD_LAT(64'(RDL)), .NR(32), .LEAD(8)) xl (
    .clk(clk), .clk_cal(clk), .rst_n(rst_n), .tgt(8'd100), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
    .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
    .launch_v(launch_v), .configured(configured), .fault(fault), .active(active), .rq(rq), .rr(rr), .rn_o(rn_o),
    .c_d(), .c_wce(), .c_mhi(), .c_mlo(), .c_wa(), .r_ce(), .r_a(), .l_d_o(l_d_o), .qv_lo(qv_lo), .qv_hi(qv_hi),
    .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi), .r_wsel(), .zlo(), .zhi(), .bsel(), .lane_en(),
    .eg_ed5(), .eg_ede(), .eg_bqv(), .eg_bqlast(), .eg_bqaddr(), .eg_bqb());
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0), .MUT(0)) aqlo (.clk(clk), .rst_n(rn_o), .v(qv_lo), .x(l_d_o[1023:0]), .vo(qo_lo), .q(), .e(), .y(), .fault(qf_lo));
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0), .MUT(0)) aqhi (.clk(clk), .rst_n(rn_o), .v(qv_hi), .x(l_d_o[2047:1024]), .vo(qo_hi), .q(), .e(), .y(), .fault(qf_hi));
  genvar b;
  generate for (b = 0; b < 8; b = b + 1) begin : g_b
    wire [16:0] rq_p = rq[b*17 +: 17];
    wire [3*257-1:0] rrs;
    assign rr[b*257 +: 257] = rrs[2*257 +: 257];
    ot_vms_bank_static #(.RG(3), .WG(2)) vmb (.clk(clk), .rst_n(rst_n), .bid(3'(b)), .sid(2'd0), .rslot_v(1'b1), .rslot(2'd2), .wslot_v(1'b0), .wslot(3'd0),
     .rq({rq[b*17 +: 17], 34'd0}), .rr(rrs), .wq(562'd0), .wq_done(), .dq(281'd0), .dq_done(), .kq(281'd0), .kq_done(), .xq(276'd0), .xq_done(), .xq2(276'd0), .xq2_done(), .eg(), .pq(285'd0), .pr(), .status());
  end endgenerate
  task cfgw(input [11:0] a, input [255:0] d);
    begin @(negedge clk); cfg_v = 1; cfg_target = 8'd100; cfg_addr = a; cfg_data = d; @(negedge clk); cfg_v = 0; repeat (4) @(negedge clk); end
  endtask
  integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
  integer t_launch = 0;
  initial begin
    repeat (10) @(negedge clk); rst_n = 1; repeat (20) @(negedge clk);
        cfgw(12'd2048, 256'h0000000000000000000000000000000a0000000020140000000040000000000a);
    @(negedge clk); desc_v = 1; cfg_target = 8'd100; desc_base = 0; desc_limit = 13'd1; desc_loops = 16'd1; @(negedge clk); desc_v = 0;
    repeat (6) @(negedge clk); launch_v = 1; t_launch = cyc; @(negedge clk); launch_v = 0;
    repeat (600) @(negedge clk);
    $display("XL_REF RD_LAT=%0d %s fault=%0d", RDL, (fault || nbad != 0) ? "FAIL" : "PASS", fault); $finish;
  end
  // probes
  reg pf = 0, pxf = 0; integer nbad = 0;
  always @(posedge clk) begin
    if (xl.u_w.u_ctl.cmd_v) $display("CMD cyc=%0d rel=%0d bad=%0d busy=%0d fmt=%0d n=%0d", cyc, cyc - t_launch, xl.u_w.u_ctl.c_bad, xl.u_w.u_ctl.x_busy, xl.u_w.u_ctl.c_fmt, xl.u_w.u_ctl.c_n);
    if (xl.u_w.u_ctl.resp_bad) nbad = nbad + 1;
    if (xl.u_w.u_ctl.resp_bad && nbad < 4) $display("RESP_BAD cyc=%0d rel=%0d m_v=%0d seen=%b", cyc, cyc - t_launch, xl.u_w.u_ctl.m_v, xl.u_w.u_ctl.rr_v_seen);
    if (xl.u_w.u_ctl.bd_fault) $display("BD_FAULT cyc=%0d rel=%0d", cyc, cyc - t_launch);
    if (xl.u_w.u_ctl.x_fault && !pxf) $display("X_FAULT cyc=%0d rel=%0d", cyc, cyc - t_launch);
    if (fault && !pf) $display("FAULT cyc=%0d rel=%0d", cyc, cyc - t_launch);
    if (xl.u_w.u_ctl.x_done) $display("X_DONE cyc=%0d rel=%0d", cyc, cyc - t_launch);
    pf <= fault; pxf <= xl.u_w.u_ctl.x_fault;
  end
endmodule
