`timescale 1ps/1ps
// TOK-HBM-2: lane-local service edges of ONE native FUSED lane (ot_hnx_fused_lane, D 5120, KX 4, RR 10) + one native
// tree node (ot_hnx_fused_tnode, DELIVERED_RESET=1).  The command stream replays the root's MEASURED static schedule
// relative to GO (results/tok_hbm_2_1028/root_service.json: rows >= 2 beats at GO + 119 + per (p - 2), per 80 PRE /
// 100 POST at rgap 0).  The VM bank returns on the fixed edge (rr_v RR edges after rq_v).  PRE row r is returned
// +RD=<edges> after that row's last chunk sum leaves the lane (stands in for up legs + root 114 + down legs).
// Prints edges relative to the GO command at the lane pin.  Plusargs: +POST +N=<1..8> +RD=<edges> +RGAP=<edges>
module tb_lane_service;
 localparam integer RR = 10;
 reg clk=0; initial forever begin #416 clk=1; #417 clk=0; end
 reg rst_n=0; reg dn_v=0; reg [2:0] dn_op=0; reg [7:0] dn_x=0; reg [127:0] dn_d=0; reg r_v=0; reg [31:0] r_d=32'h3f800000;
 wire rq_v, wq_v, up_v, up_t, fin, flt; wire [15:0] rq_s, wq_s; wire [255:0] wq_d, up_d; wire [9:0] up_x;
 reg [RR-1:0] rp=0; always @(posedge clk) rp <= {rp[RR-2:0], rq_v};
 ot_hnx_fused_lane #(.RR(RR)) dut(.clk(clk),.rst_n(rst_n),.lid(5'd0),.rq_v(rq_v),.rq_s(rq_s),.rr_v(rp[RR-1]),.rr_d(256'd0),
  .wq_v(wq_v),.wq_s(wq_s),.wq_d(wq_d),.dn_v(dn_v),.dn_op(dn_op),.dn_x(dn_x),.dn_d(dn_d),.r_v(r_v),.r_d(r_d),
  .up_v(up_v),.up_t(up_t),.up_x(up_x),.up_d(up_d),.fin(fin),.flt(flt));
 // tree node: scalar / chunk sum / fin edges through one tnode (both children driven by the same lane outputs)
 wire [270:0] lu = {up_v, up_t, up_x, fin, fin, flt, up_d}; wire [270:0] tuo; wire [172:0] tda, tdb;
 reg [172:0] tdn=0;
 ot_hnx_fused_tnode #(.DELIVERED_RESET(1)) tn(.clk(clk),.rst_n(rst_n),.pad_k(6'd0),.pad_b(1'b0),.ua(lu),.ub(lu),.uo(tuo),.dn(tdn),.da(tda),.db(tdb));
 integer cyc=0, go=-1, scr=-1, scr_up=-1, ncs=0, nwq=0, fin_c=-1, last_wq=-1, flt_c=-1, nr=0, last_r=-1;
 integer t_lsc=-1, t_tsc=-1, t_lcs=-1, t_tcs=-1, t_lfin=-1, t_tfin=-1, t_dn=-1, t_da=-1;
 integer cs_last[0:15]; integer cs_cnt[0:15]; integer post, n, rd, row, rgap;
 always @(posedge clk) cyc <= cyc + 1;
 always @(negedge clk) begin
  if (up_v && !up_t && scr_up<0) scr_up=cyc;
  if (up_v && up_t) begin row=ncs/20; cs_last[row]=cyc; ncs=ncs+1; end
  if (wq_v) begin nwq=nwq+1; last_wq=cyc; end
  if (fin && fin_c<0) fin_c=cyc;
  if (flt && flt_c<0) flt_c=cyc;
  if (up_v && !up_t && t_lsc<0) t_lsc=cyc; if (tuo[270] && !tuo[269] && t_tsc<0) t_tsc=cyc;
  if (up_v && up_t && t_lcs<0) t_lcs=cyc; if (tuo[270] && tuo[269] && t_tcs<0) t_tcs=cyc;
  if (fin && t_lfin<0) t_lfin=cyc; if (tuo[258] && t_tfin<0) t_tfin=cyc;
  if (tda[172] && t_da<0) t_da=cyc;
 end
 task automatic tick; @(negedge clk); #1; endtask
 task automatic cmd(input [2:0] op, input [7:0] x, input [127:0] d); dn_v=1; dn_op=op; dn_x=x; dn_d=d; tick; dn_v=0; endtask
 // PRE r for row p: +RD edges after its last chunk sum (sequential rows)
 integer rsent=0;
 always @(negedge clk) begin
  #2; r_v = 0;
  if (!post && rsent < n && ncs >= 20*(rsent+1) && cyc == cs_last[rsent] + rd) begin r_v = 1; nr = nr + 1; last_r = cyc; rsent = rsent + 1; end
 end
 initial begin
  post=$test$plusargs("POST"); if(!$value$plusargs("N=%d",n)) n=1; if(!$value$plusargs("RD=%d",rd)) rd=150; if(!$value$plusargs("RGAP=%d",rgap)) rgap=0;
  repeat(5) tick; rst_n=1; repeat(40) tick;
  // tree down path: one command through the node
  tdn={1'b1,3'd0,8'd0,128'd0,1'b0,32'd0}; t_dn=cyc; tick; tdn=0;
  repeat(6) tick;
  // JOB: d = {rgap 8, rso 16, rsb 16, rsa 16, o_s 16, b_s 16, a_s 16, nm1 4, post 1}; strides one row = NM sectors x32 lanes
  cmd(3'd0, 8'd0, {19'd0, 8'(rgap), 16'd640, 16'd0, 16'd640, 16'd8192, 16'd4096, 16'd0, 4'(n-1), 1'(post)});
  // scalar sector read for this lane (prologue), then the WGT beats of rows 0 and 1 and GO, as the root issues them
  scr=cyc; cmd(3'd2, 8'd0, 128'd0); repeat(30) tick;
  for (integer p=0;p<n && p<2;p=p+1) for (integer b=0;b<(post?5:1);b=b+1) cmd(3'd1, {4'(p), 1'(p), 3'(b)}, 128'd0);
  go=cyc; cmd(3'd3, 8'd0, 128'd0);
  for (integer p=2;p<n;p=p+1) begin
   while (cyc < go + 119 + rgap + ((post?100:80)+rgap)*(p-2)) tick;
   for (integer b=0;b<(post?5:1);b=b+1) cmd(3'd1, {4'(p), 1'(p), 3'(b)}, 128'd0);
  end
  while (fin_c < 0 && cyc < go + 4000) tick;
  repeat(10) tick;
  $display("LANE_SERVICE rgap=%0d op=%s n=%0d rd=%0d scrd_to_up=%0d go_to_cs_last_row0=%0d go_to_cs_last_rowN=%0d ncs=%0d r_last_to_fin=%0d go_to_fin=%0d nwq=%0d nr=%0d flt=%0d tnode_up_scalar=%0d tnode_up_chunk=%0d tnode_up_fin=%0d tnode_down=%0d",
   rgap, post?"HC_POST":"HC_PRE", n, rd, scr_up-scr, (post||ncs<20)?-1:cs_last[0]-go, (post||ncs<20*n)?-1:cs_last[n-1]-go, ncs,
   post?-1:fin_c-last_r, fin_c-go, nwq, nr, flt_c<0?0:flt_c-go, t_tsc-t_lsc, t_tcs-t_lcs, t_tfin-t_lfin, t_da-t_dn);
  $finish;
 end
endmodule
