`timescale 1ns/1ps
module tb_seq;
  localparam FLIT=512, NW=21, UW=10, DW=UW+3+NW, SW=UW+3*NW+4;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0; reg r_valid=0, w_valid=0, q_valid=0, t_ready=0, s_ready=0, h_ready=0;
  reg [FLIT-1:0] r_data=0; reg [UW-1:0] w_user=0; reg [DW-1:0] q_data=0;
  reg [NW-1:0] plen=4, glen=40;
  wire [1:0] rr_, wr_, qr_, tv_, sv_, hv_, av_, fl_; wire [FLIT-1:0] td0, td1; wire [SW-1:0] sd0, sd1; wire [DW-1:0] hd0, hd1;
  wire [UW-1:0] au0, au1; wire [2:0] aa0, aa1; wire [NW-1:0] ac0, ac1, ay0, ay1;
  wire rrz, wrz, qrz, tvz, svz, hvz, avz, flz; wire [FLIT-1:0] tdz; wire [SW-1:0] sdz; wire [DW-1:0] hdz; wire [UW-1:0] auz; wire [2:0] aaz; wire [NW-1:0] acz, ayz;
  ot_dsrom_mtp_seq_fan_O #(.DATA_RST(1)) u0 (.clk(clk),.rst_n(rst_n),.cfg_plen(plen),.cfg_glen(glen),.r_valid(r_valid),.r_ready(rr_[0]),.r_data(r_data),
    .t_valid(tv_[0]),.t_ready(t_ready),.t_data(td0),.s_valid(sv_[0]),.s_ready(s_ready),.s_data(sd0),.w_valid(w_valid),.w_ready(wr_[0]),.w_user(w_user),
    .h_valid(hv_[0]),.h_ready(h_ready),.h_data(hd0),.q_valid(q_valid),.q_ready(qr_[0]),.q_data(q_data),.acc_v(av_[0]),.acc_u(au0),.acc_a(aa0),.acc_c(ac0),.acc_y(ay0),.fault(fl_[0]));
  `NEWMOD #(.DATA_RST(1),.EX_PRE(1)) u1 (.clk(clk),.rst_n(rst_n),.cfg_plen(plen),.cfg_glen(glen),.r_valid(r_valid),.r_ready(rr_[1]),.r_data(r_data),
    .t_valid(tv_[1]),.t_ready(t_ready),.t_data(td1),.s_valid(sv_[1]),.s_ready(s_ready),.s_data(sd1),.w_valid(w_valid),.w_ready(wr_[1]),.w_user(w_user),
    .h_valid(hv_[1]),.h_ready(h_ready),.h_data(hd1),.q_valid(q_valid),.q_ready(qr_[1]),.q_data(q_data),.acc_v(av_[1]),.acc_u(au1),.acc_a(aa1),.acc_c(ac1),.acc_y(ay1),.fault(fl_[1]));
  `NEWMOD #(.DATA_RST(1),.EX_PRE(0)) u2 (.clk(clk),.rst_n(rst_n),.cfg_plen(plen),.cfg_glen(glen),.r_valid(r_valid),.r_ready(rrz),.r_data(r_data),
    .t_valid(tvz),.t_ready(t_ready),.t_data(tdz),.s_valid(svz),.s_ready(s_ready),.s_data(sdz),.w_valid(w_valid),.w_ready(wrz),.w_user(w_user),
    .h_valid(hvz),.h_ready(h_ready),.h_data(hdz),.q_valid(q_valid),.q_ready(qrz),.q_data(q_data),.acc_v(avz),.acc_u(auz),.acc_a(aaz),.acc_c(acz),.acc_y(ayz),.fault(flz));
  wire [2000:0] o0 = {rr_[0],wr_[0],qr_[0],tv_[0],td0,sv_[0],sd0,hv_[0],hd0,av_[0],au0,aa0,ac0,ay0,fl_[0]};
  wire [2000:0] o1 = {rr_[1],wr_[1],qr_[1],tv_[1],td1,sv_[1],sd1,hv_[1],hd1,av_[1],au1,aa1,ac1,ay1,fl_[1]};
  wire [2000:0] o2 = {rrz,wrz,qrz,tvz,tdz,svz,sdz,hvz,hdz,avz,auz,aaz,acz,ayz,flz};
  integer cyc=0, nacc=0, nclose=0, nsq=0, nex=0, seed, NC, mism=0, nfault=0;
  integer anchor[0:7]; integer u; reg [UW-1:0] wq[0:15]; reg [DW-1:0] qq[0:15]; integer ww=0, wr=0, qw=0, qr=0;
  initial begin
    if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("n=%d",NC)) NC=200000;
    repeat(6) @(posedge clk); rst_n=1;
  end
  reg tk_s=0, tk_h=0, tk_w=0, tk_q=0, tk_r=0; reg [SW-1:0] tk_sd=0; reg [DW-1:0] tk_hd=0;
  always @(posedge clk) begin tk_s = sv_[0] && s_ready; tk_h = hv_[0] && h_ready; tk_w = w_valid && wr_[0]; tk_q = q_valid && qr_[0]; tk_r = r_valid && rr_[0]; tk_sd = sd0; tk_hd = hd0; end
  always @(negedge clk) begin
    cyc=cyc+1;
    if (rst_n && o0 !== o1) begin mism=mism+1; if (mism<5) $display("MISMATCH new-on cycle %0d", cyc); end
    if (rst_n && o0 !== o2) begin mism=mism+1; if (mism<5) $display("MISMATCH new-off cycle %0d", cyc); end
    if (u1.st==3'd3) begin nex=nex+1; if (u1.e_acc) nacc=nacc+1; if (u1.e_close) nclose=nclose+1; if (u1.e_sq) nsq=nsq+1; end
    // stimulus (hold while valid and not taken)
    if (cyc > 12 && (!r_valid || tk_r)) begin
      r_valid = ($random(seed) & 7) == 0;
      r_data = 0; r_data[16 +: 4] = (($random(seed) & 4095)==0) ? 4'd3 : 4'd2;
      u = $random(seed) & 3; if (($random(seed)&31)==0) u = 9;
      r_data[32 +: 8] = u; r_data[0 +: 16] = (($random(seed)&4095)==0) ? 16'h1234 : 16'h0201;
      r_data[40 +: NW] = (($random(seed) & 31) == 0) ? ($random(seed) & 63) : (u0.u_b[u&7] + ({$random(seed)} % (u0.u_g[u&7] + 1)));
      r_data[61 +: NW] = $random(seed) & 1; r_data[82 +: 32] = $random(seed);
    end
    // reactive drafter (FIFOs): a taken seed -> rows-ready for that user; a taken draft-head step -> its result
    if (tk_s) begin wq[ww] = tk_sd[SW-1 -: UW]; ww = (ww + 1) % 16; end
    if (tk_h) begin qq[qw] = 0; qq[qw][DW-1 -: UW] = tk_hd[DW-1 -: UW]; qq[qw][NW +: 3] = tk_hd[NW +: 3]; qq[qw][NW-1:0] = $random(seed) & 1; qw = (qw + 1) % 16; end
    if (tk_w) w_valid = 0;
    if (!w_valid && wr != ww && ($random(seed) & 1)) begin w_valid = 1; w_user = wq[wr]; wr = (wr + 1) % 16; end
    else if (!w_valid && ($random(seed) & 4095) == 0) begin w_valid = 1; w_user = $random(seed) & 3; end
    if (tk_q) q_valid = 0;
    if (!q_valid && qr != qw && ($random(seed) & 1)) begin q_valid = 1; q_data = qq[qr]; qr = (qr + 1) % 16; end
    else if (!q_valid && ($random(seed) & 4095) == 0) begin q_valid = 1; q_data[NW +: 3] = $random(seed); end
    t_ready = ($random(seed) & 3) != 0; s_ready = ($random(seed) & 1); h_ready = ($random(seed) & 1);
    if (fl_[0]) nfault = nfault + 1;
    if (cyc == NC) $display("DBG st %0d tq_n %0d sq_v %0d hq_v %0d ph0 %0d ph1 %0d", u1.st, u1.tq_n, u1.sq_v, u1.hq_v, u1.u_ph[0], u1.u_ph[1]);
    if (cyc == NC) begin
      $display("SEQ seed %0d cycles %0d mismatches %0d S_EX %0d acc %0d close %0d sq %0d fault_cycles %0d", seed, cyc, mism, nex, nacc, nclose, nsq, nfault);
      if (mism==0 && nacc>0 && nclose>0 && nsq>0) $display("SEQ_PASS"); else $display("SEQ_FAIL");
      $finish;
    end
  end
endmodule
