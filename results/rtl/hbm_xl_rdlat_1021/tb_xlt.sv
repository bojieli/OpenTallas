`timescale 1ns/1ps
module tb_xlt;
  reg [255:0] ents [0:31]; integer nent; reg [8*64-1:0] fn;
`ifndef EXTRA
`define EXTRA 7
`endif
`ifndef ENT
`define ENT 136'ha0000000020140000000040000000000a
`endif
  localparam integer N0=30,N1=33,N2=20,N3=22,N4=46,N5=48,N6=36,N7=38;
  localparam [63:0] RDL = {8'(N7+`EXTRA),8'(N6+`EXTRA),8'(N5+`EXTRA),8'(N4+`EXTRA),8'(N3+`EXTRA),8'(N2+`EXTRA),8'(N1+`EXTRA),8'(N0+`EXTRA)};
  localparam integer NP [0:7] = '{N0,N1,N2,N3,N4,N5,N6,N7};
  reg clk=0, rst_n=0; always #1 clk=~clk;
  reg cfg_v=0, desc_v=0, launch_v=0; reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0; reg [255:0] cfg_data=0;
  reg [11:0] desc_base=0; reg [12:0] desc_limit=0; reg [15:0] desc_loops=0;
  wire configured, fault, active, rn_o; wire [8*17-1:0] rq; wire [8*257-1:0] rr;
  wire [1023:0] c_d; wire [3:0] c_wce; wire c_mhi,c_mlo; wire [6:0] c_wa; wire [7:0] r_ce; wire [6:0] r_a; wire [2047:0] l_d_o;
  wire qv_lo,qv_hi,qo_lo,qo_hi,qf_lo,qf_hi; wire [15:0] r_wsel; wire zlo,zhi; wire [25:0] bsel; wire [63:0] lane_en;
  wire [7:0] eg_ed5; wire [16:0] eg_ede; wire eg_bqv,eg_bqlast; wire [6:0] eg_bqaddr,eg_bqb;
  ot_hgi_sm_xload_cl2_ctlx #(.PMAX(8),.RD_LAT(RDL),.NR(32),.LEAD(8)) dut(
    .clk(clk),.clk_cal(clk),.rst_n(rst_n),.tgt(8'd100),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
    .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
    .configured(configured),.fault(fault),.active(active),.rq(rq),.rr(rr),.rn_o(rn_o),.c_d(c_d),.c_wce(c_wce),.c_mhi(c_mhi),.c_mlo(c_mlo),
    .c_wa(c_wa),.r_ce(r_ce),.r_a(r_a),.l_d_o(l_d_o),.qv_lo(qv_lo),.qv_hi(qv_hi),.qo_lo(qo_lo),.qo_hi(qo_hi),.qf_lo(qf_lo),.qf_hi(qf_hi),
    .r_wsel(r_wsel),.zlo(zlo),.zhi(zhi),.bsel(bsel),.lane_en(lane_en),.eg_ed5(eg_ed5),.eg_ede(eg_ede),.eg_bqv(eg_bqv),.eg_bqlast(eg_bqlast),
    .eg_bqaddr(eg_bqaddr),.eg_bqb(eg_bqb));
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0),.MUT(0)) aqlo(.clk(clk),.rst_n(rn_o),.v(qv_lo),.x(l_d_o[1023:0]),.vo(qo_lo),.q(),.e(),.y(),.fault(qf_lo));
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0),.MUT(0)) aqhi(.clk(clk),.rst_n(rn_o),.v(qv_hi),.x(l_d_o[2047:1024]),.vo(qo_hi),.q(),.e(),.y(),.fault(qf_hi));
  genvar b;
  for (b=0;b<8;b=b+1) begin : g_b
    wire [16:0] po; wire [17:0] st;
    hbfd_pad #(.W(17),.N(NP[b])) pad(.ck(clk),.rs(rst_n),.i(rq[b*17+:17]),.o(po));
    hfd_vms_bank_native_q0_faces bk(.rq0(17'd0),.rr0(),.rq1(17'd0),.rr1(),.rq2(po),.rr2(rr[b*257+:257]),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
      .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.bid(3'(b)),.sid(2'd0),.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
      .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.rslot_v(1'b1),.rslot(3'd2),.wslot_v(1'b0),.wslot(3'd0),
      .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(st));
  end
  integer cyc=0; always @(posedge clk) cyc<=cyc+1;
  wire rb = dut.u_w.u_ctl.resp_bad, bf = dut.u_w.u_ctl.bd_fault, xf = dut.u_w.u_ctl.x_fault;
  wire mv = dut.u_w.u_ctl.m_v; wire [7:0] rvs = dut.u_w.u_ctl.rr_v_seen;
  integer nshow=0, nrq=0; reg [7:0] qv;
  always @(posedge clk) begin
    for (integer k=0;k<8;k=k+1) qv[k]=rq[k*17+16];
    if (qv!=0 && nrq<12) begin $display("C%0d rq_v=%b", cyc, qv); nrq=nrq+1; end
    if ((mv || rvs!=0) && nshow<24) begin $display("C%0d m_v=%b rr_v_seen=%b resp_bad=%b", cyc, mv, rvs, rb); nshow=nshow+1; end
    if (dut.u_w.u_ctl.cmd_v) $display("C%0d ctl cmd_v (x_busy=%b c_bad=%b)", cyc, dut.u_w.u_ctl.x_busy, dut.u_w.u_ctl.c_bad);
    if (rb) $display("C%0d RESP_BAD m_v=%b seen=%b", cyc, mv, rvs);
    if (bf) $display("C%0d BD_FAULT", cyc);
    if (fault && !$past(fault)) $display("C%0d XL_FAULT rises (x_fault=%b)", cyc, xf);
  end
  task automatic cfgw(input [7:0] t, input [11:0] a, input [255:0] d);
    @(negedge clk); cfg_target=t; cfg_addr=a; cfg_data=d; cfg_v=1; @(negedge clk); cfg_v=0; repeat(6) @(negedge clk);
  endtask
  integer done_c=-1;
  initial begin
    repeat(10) @(negedge clk); rst_n=1; repeat(30) @(negedge clk);
    if (!$value$plusargs("ENT=%s", fn)) $fatal(1,"ENT"); if (!$value$plusargs("N=%d", nent)) $fatal(1,"N"); $readmemh(fn, ents);
    for (integer i=0;i<nent;i=i+1) cfgw(8'd100, 12'h800+12'(i), ents[i]);
    @(negedge clk); cfg_target=100; desc_base=0; desc_limit=13'(nent); desc_loops=1; desc_v=1; @(negedge clk); desc_v=0; repeat(10) @(negedge clk);
    $display("C%0d configured=%b fault=%b, LAUNCH", cyc, configured, fault);
    launch_v=1; @(negedge clk); launch_v=0;
    repeat(40000) begin @(negedge clk); if (!active && done_c<0) done_c=cyc; end
    $display("END fault=%b active=%b x_fault=%b done_c=%0d EXTRA=%0d", fault, active, xf, done_c, `EXTRA);
    for (integer k=0;k<8;k=k+1) ;
    $finish;
  end
endmodule
