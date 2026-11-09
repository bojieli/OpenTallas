`timescale 1ns/1ps
// HBM-TRANSPORT-1 (11-09): bound-depth bench for the HBM SU-face VM lane-group class.
// REAL RTL: 2 x ot_hbm_su_static_vm_bank_leaf (SU slice face), ot_hbm_vm_lg_pair_tap (SU tap), 2 x
// hfd_vms_bank_native_q0_faces (VM bank, real SRAM model + SECDED). Bench models only: the command issue, the calendar
// programme (selector rows lg_local_read/write and bank owner rows rslot/wslot), and the bound lanes as shift registers.
// Run-time depths (plusargs, all in edges, from bind_lat_vJ bus_groups landed_stages):
//   +D_CMD   pgp command -> SU leaf su_rq/su_wq          +D_CAL  calendar lg_local_read/write -> tap
//   +D_REQ   tap near_rq/near_wq -> bank rq0/wq0          +D_RESP bank rr0/wq_done0 -> tap near_rr/near_w_done
//   +RR/+WR  READ_RETURN/WRITE_RETURN of tap AND leaf (bound RTL value; compile-time via -P)
// Compiler model (native_su_calendar.py form): command issue c; selector row = c - SEL_ADV; owner row = c + OWN_LAG.
//   as-built / wave compiler: SEL_ADV=0, OWN_LAG=2 ("two-edge LG request path", request_lane_edges=0).
//   transport-correct:        SEL_ADV=D_CAL-D_CMD, OWN_LAG=D_CMD+2+D_REQ.
// Oracle: every read returns the last written data of its row, 0 faults (tap, both leaves, both banks), 0 far returns.
module tb_vmlg_su_bound;
 parameter integer RR=10, WR=7, QID=1, G=1;   // G = tap index in the quarter: banks 2G, 2G+1
 integer D_CMD=0, D_CAL=0, D_REQ=0, D_RESP=0, SEL_ADV=0, OWN_LAG=2, NOPS=4000, SEED=1;
 // +EPOCH: cx_layer_1021.epoch_calendar form = ONE constant row (all selectors + owners) over calendar edges [E0, E1);
 // commands only at c in [E0+GUARD, E1-TAIL).  Needed at bound depth: GUARD >= D_CAL-D_CMD, TAIL >= D_CMD+2+D_REQ.
 integer EPOCH=0, E0=0, E1=0, GUARD=0, TAIL=0, cbeg=0, cend=0;
 localparam integer T=8192, MAXD=160;
 reg clk=0, rst_n=0; always #0.5 clk=~clk;
 integer cyc=0;
 // ---------------- programme arrays (absolute cycle index)
 reg [16:0]  su_rq_at [0:T-1][0:1];
 reg [280:0] su_wq_at [0:T-1][0:1];
 reg [1:0]   cal_rd_at[0:T-1], cal_wr_at[0:T-1];
 reg [1:0]   own_r_at [0:T-1], own_w_at[0:T-1];
 // expected read data per (bank,row): written value
 reg [255:0] mem [0:1][0:1023]; reg mem_ok[0:1][0:1023];
 // per issued read: expected data at leaf due time
 reg [255:0] exp_rd [0:T-1][0:1]; reg exp_v [0:T-1][0:1];
 // ---------------- lanes
 reg [33:0]  cmd_rq_l [0:MAXD]; reg [561:0] cmd_wq_l[0:MAXD];
 reg [1:0]   cal_rd_l [0:MAXD], cal_wr_l[0:MAXD];
 reg [33:0]  req_rq_l [0:MAXD]; reg [561:0] req_wq_l[0:MAXD];
 reg [513:0] rsp_rr_l [0:MAXD]; reg [1:0]   rsp_dn_l[0:MAXD];
 wire [33:0]  tap_near_rq; wire [561:0] tap_near_wq;
 wire [513:0] tap_local_rr, tap_far_rr; wire [1:0] tap_local_done, tap_far_done; wire tap_fault;
 wire [256:0] bk_rr0 [0:1]; wire bk_wd0 [0:1]; wire [17:0] bk_status[0:1];
 // lane outputs (depth 0 = combinational pass-through)
 wire [33:0]  su_rq_now = {su_rq_at[cyc%T][1], su_rq_at[cyc%T][0]};
 wire [561:0] su_wq_now = {su_wq_at[cyc%T][1], su_wq_at[cyc%T][0]};
 wire [33:0]  leaf_rq  = (D_CMD==0)? su_rq_now : cmd_rq_l[D_CMD];
 wire [561:0] leaf_wq  = (D_CMD==0)? su_wq_now : cmd_wq_l[D_CMD];
 wire [1:0]   tap_lrd  = (D_CAL==0)? cal_rd_at[cyc%T] : cal_rd_l[D_CAL];
 wire [1:0]   tap_lwr  = (D_CAL==0)? cal_wr_at[cyc%T] : cal_wr_l[D_CAL];
 wire [33:0]  bk_rq    = (D_REQ==0)? tap_near_rq : req_rq_l[D_REQ];
 wire [561:0] bk_wq    = (D_REQ==0)? tap_near_wq : req_wq_l[D_REQ];
 wire [513:0] tap_nrr  = (D_RESP==0)? {bk_rr0[1],bk_rr0[0]} : rsp_rr_l[D_RESP];
 wire [1:0]   tap_ndn  = (D_RESP==0)? {bk_wd0[1],bk_wd0[0]} : rsp_dn_l[D_RESP];
 integer k;
 initial for(k=0;k<=MAXD;k=k+1) begin cmd_rq_l[k]=0; cmd_wq_l[k]=0; cal_rd_l[k]=0; cal_wr_l[k]=0; req_rq_l[k]=0; req_wq_l[k]=0; rsp_rr_l[k]=0; rsp_dn_l[k]=0; end
 always @(posedge clk) begin
  cmd_rq_l[1]<=su_rq_now; cmd_wq_l[1]<=su_wq_now; cal_rd_l[1]<=cal_rd_at[cyc%T]; cal_wr_l[1]<=cal_wr_at[cyc%T];
  req_rq_l[1]<=tap_near_rq; req_wq_l[1]<=tap_near_wq; rsp_rr_l[1]<={bk_rr0[1],bk_rr0[0]}; rsp_dn_l[1]<={bk_wd0[1],bk_wd0[0]};
  for(k=2;k<=MAXD;k=k+1) begin
   cmd_rq_l[k]<=cmd_rq_l[k-1]; cmd_wq_l[k]<=cmd_wq_l[k-1]; cal_rd_l[k]<=cal_rd_l[k-1]; cal_wr_l[k]<=cal_wr_l[k-1];
   req_rq_l[k]<=req_rq_l[k-1]; req_wq_l[k]<=req_wq_l[k-1]; rsp_rr_l[k]<=rsp_rr_l[k-1]; rsp_dn_l[k]<=rsp_dn_l[k-1];
  end
 end
 // ---------------- REAL RTL
 wire [16:0] lg_rq [0:1]; wire [280:0] lg_wq[0:1]; wire [256:0] su_rr[0:1]; wire su_wd[0:1]; wire leaf_fault[0:1];
 for(genvar b=0;b<2;b=b+1) begin:g_leaf
  ot_hbm_su_static_vm_bank_leaf #(.QID(QID),.B(2*G+b),.READ_RETURN(RR),.WRITE_RETURN(WR)) leaf(
   .clk(clk),.rst_n(rst_n),.su_rq(leaf_rq[b*17+:17]),.su_wq(leaf_wq[b*281+:281]),.su_rr(su_rr[b]),.su_w_done(su_wd[b]),
   .lg_rq(lg_rq[b]),.lg_wq(lg_wq[b]),.lg_rr(tap_local_rr[b*257+:257]),.lg_w_done(tap_local_done[b]),.fault(leaf_fault[b]));
 end
 ot_hbm_vm_lg_pair_tap #(.READ_RETURN(RR),.WRITE_RETURN(WR)) tap(.clk(clk),.rst_n(rst_n),
  .local_rq({lg_rq[1],lg_rq[0]}),.far_rq(34'd0),.local_wq({lg_wq[1],lg_wq[0]}),.far_wq(562'd0),
  .local_read(tap_lrd),.local_write(tap_lwr),.near_rq(tap_near_rq),.near_wq(tap_near_wq),
  .near_rr(tap_nrr),.near_w_done(tap_ndn),.local_rr(tap_local_rr),.far_rr(tap_far_rr),
  .local_w_done(tap_local_done),.far_w_done(tap_far_done),.fault(tap_fault));
 for(genvar b=0;b<2;b=b+1) begin:g_bank
  hfd_vms_bank_native_q0_faces bank(
   .rq0(bk_rq[b*17+:17]),.rr0(bk_rr0[b]),.rq1(17'd0),.rr1(),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
   .wq0(bk_wq[b*281+:281]),.wq_done0(bk_wd0[b]),.wq1(281'd0),.wq_done1(),
   .bid(3'(2*G+b)),.sid(2'(QID)),.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
   .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),
   .rslot_v(own_r_at[cyc%T][b]),.rslot(3'd0),.wslot_v(own_w_at[cyc%T][b]),.wslot(3'd0),
   .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),
   .pq(285'd0),.pr(),.status(bk_status[b]));
 end
 // ---------------- programme
 function automatic [255:0] rnd256(input integer dummy); integer q; reg [255:0] t; begin for(q=0;q<256;q=q+32) t[q+:32]=$urandom; rnd256=t; end endfunction
 integer i,b,c,t0,row,nrd=0,nwr=0,bad_data=0,good_data=0,far_bad=0,miss=0,err_total=0;
 reg [15:0] sec; reg [255:0] d;
 reg [9:0] wrow [0:1][0:255]; integer nw[0:1]; integer wtime[0:1][0:255]; integer pick,tries;
 task automatic put_rd(input integer cc, input integer bb, input integer rw);
  reg [15:0] s; begin
  s = {1'b0, 2'(QID), rw[9:0], 3'(2*G+bb)};
  su_rq_at[cc][bb] = {1'b1, s};                       // command issued at c; the D_CMD lane delivers it to the leaf
  if(!EPOCH) begin
  cal_rd_at[cc-SEL_ADV][bb] = 1'b1;                   // calendar selector row
  own_r_at[cc+OWN_LAG][bb] = 1'b1;                    // calendar bank owner row (rslot_v, rslot=0 = SU face)
  end
  exp_rd[cc+D_CMD+RR+1][bb] = mem[bb][rw]; exp_v[cc+D_CMD+RR+1][bb] = 1'b1;
  nrd=nrd+1; end endtask
 task automatic put_wr(input integer cc, input integer bb, input integer rw, input [255:0] dd);
  reg [15:0] s; begin
  s = {1'b0, 2'(QID), rw[9:0], 3'(2*G+bb)};
  su_wq_at[cc][bb] = {1'b1, s, dd, 8'hFF};
  if(!EPOCH) begin cal_wr_at[cc-SEL_ADV][bb] = 1'b1; own_w_at[cc+OWN_LAG][bb] = 1'b1; end
  mem[bb][rw] = dd; mem_ok[bb][rw] = 1'b1;
  nwr=nwr+1; end endtask
 initial begin
  if(!$value$plusargs("D_CMD=%d",D_CMD)) D_CMD=0; if(!$value$plusargs("D_CAL=%d",D_CAL)) D_CAL=0;
  if(!$value$plusargs("D_REQ=%d",D_REQ)) D_REQ=0; if(!$value$plusargs("D_RESP=%d",D_RESP)) D_RESP=0;
  if(!$value$plusargs("SEL_ADV=%d",SEL_ADV)) SEL_ADV=0; if(!$value$plusargs("OWN_LAG=%d",OWN_LAG)) OWN_LAG=2;
  if($test$plusargs("ZERO")) begin D_CMD=0; D_CAL=0; D_REQ=0; D_RESP=0; end
  EPOCH=$test$plusargs("EPOCH"); if(!$value$plusargs("GUARD=%d",GUARD)) GUARD=0; if(!$value$plusargs("TAIL=%d",TAIL)) TAIL=0;
  if(!$value$plusargs("NOPS=%d",NOPS)) NOPS=4000; if(!$value$plusargs("SEED=%d",SEED)) SEED=1;
  void'($urandom(SEED));
  for(i=0;i<T;i=i+1) begin su_rq_at[i][0]=0; su_rq_at[i][1]=0; su_wq_at[i][0]=0; su_wq_at[i][1]=0;
   cal_rd_at[i]=0; cal_wr_at[i]=0; own_r_at[i]=0; own_w_at[i]=0; exp_v[i][0]=0; exp_v[i][1]=0; end
  for(b=0;b<2;b=b+1) begin nw[b]=0; for(i=0;i<1024;i=i+1) mem_ok[b][i]=0; end
  // schedule: command edges start at t0 (well after reset and after the earliest selector row c-SEL_ADV >= 0)
  t0 = 200 + (SEL_ADV>0?SEL_ADV:0);
  if(EPOCH) begin  // calendar epoch [E0,E1): constant selector + owner rows; commands kept inside the guard/tail window
   E0 = 200; E1 = E0 + GUARD + NOPS + TAIL; t0 = E0 + GUARD;
   for(i=E0;i<E1;i=i+1) begin cal_rd_at[i]=2'b11; cal_wr_at[i]=2'b11; own_r_at[i]=2'b11; own_w_at[i]=2'b11; end
  end
  // phase 1: writes to fresh rows (one read and one write slot per bank per edge, compiler-reserved), phase 2: mixed
  for(c=t0;c<t0+NOPS;c=c+1) begin
   for(b=0;b<2;b=b+1) begin
    if(EPOCH && (c==t0 || c==t0+NOPS-1) && nw[b]<256) begin row=$urandom%1024; while(mem_ok[b][row]) row=(row+1)%1024;
      d=rnd256(0); put_wr(c,b,row,d); wrow[b][nw[b]]=row; wtime[b][nw[b]]=c; nw[b]=nw[b]+1; end
    else if(EPOCH && c==t0+NOPS-2 && nw[b]>0) begin row=wrow[b][0]; put_rd(c,b,row); end
    else if(c<t0+NOPS/4 || ($urandom%3)==0) begin
     if(($urandom%2)==0 && nw[b]<256) begin row=$urandom%1024; while(mem_ok[b][row]) row=(row+1)%1024;
      d=rnd256(0); put_wr(c,b,row,d); wrow[b][nw[b]]=row; wtime[b][nw[b]]=c; nw[b]=nw[b]+1; end
    end
    if(!(EPOCH && c==t0+NOPS-2) && c>=t0+NOPS/4 && ($urandom%2)==0 && nw[b]>0) begin  // one read per bank per edge
     // read a row written at least 64 edges ago (no in-flight write hazard in the reference)
     pick=$urandom%nw[b]; tries=0; while(wtime[b][pick]>c-64 && tries<300) begin pick=$urandom%nw[b]; tries=tries+1; end
     if(wtime[b][pick]<=c-64) begin row=wrow[b][pick]; put_rd(c,b,row); end
    end
   end
  end
  repeat(3) @(negedge clk); rst_n=1;
 end
 always @(posedge clk) cyc<=cyc+1;
 // ---------------- checks at the leaf's su_rr (data) and every fault output
 integer done=0;
 always @(negedge clk) if(rst_n) begin
  for(b=0;b<2;b=b+1) begin
   if(exp_v[cyc%T][b]) begin
    if(su_rr[b][256]!==1'b1 || su_rr[b][255:0]!==exp_rd[cyc%T][b]) begin bad_data=bad_data+1; if(bad_data<4) $display("DATA b%0d cyc %0d v=%b", b, cyc, su_rr[b][256]); end
    else good_data=good_data+1;
   end
   if(tap_far_rr[b*257+256]===1'b1 || tap_far_done[b]===1'b1) far_bad=far_bad+1;
  end
 end
 initial begin
  wait(rst_n); repeat(t0+NOPS+MAXD+400) @(posedge clk); #0.2;
  err_total = bad_data + far_bad + tap_fault + leaf_fault[0] + leaf_fault[1] + bk_status[0][17] + bk_status[1][17];
  if(EPOCH) $display("VMLG_EPOCH GUARD=%0d TAIL=%0d", GUARD, TAIL);
  $display("VMLG %s D_CMD=%0d D_CAL=%0d D_REQ=%0d D_RESP=%0d RR=%0d WR=%0d SEL_ADV=%0d OWN_LAG=%0d reads=%0d writes=%0d good=%0d bad_data=%0d far=%0d fault tap=%0d leaf=%0d%0d bank=%0d%0d",
   err_total==0 && good_data==nrd ? "PASS":"FAIL", D_CMD,D_CAL,D_REQ,D_RESP,RR,WR,SEL_ADV,OWN_LAG,nrd,nwr,good_data,bad_data,far_bad,
   tap_fault,leaf_fault[0],leaf_fault[1],bk_status[0][17],bk_status[1][17]);
  $finish;
 end
endmodule
