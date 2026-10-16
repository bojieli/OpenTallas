`timescale 1ns/1ps
// Stationed stress bench of the sequencer's partner ends (mtp-fixlat-1011): dsfd_cap_mtp_ep + dsfd_vm_mtp_ep on one
// side, the sequencer's link cells at dsfd_mtp_seq_rtt's own parameters on the other (u_r: lrx_rtt FWD_R/RET_R,
// u_w / u_q: lrx_rtt FWD_V/RET_V, u_h: ltx), registered relay stations at the head631 pin-to-pin counts in between.
// Four channels run at once (RESULT 512 b, rows-ready 10 b, draft-head step 34 b, draft-head result 34 b), every
// consumer stalls (incl. a 200-cycle window after steady traffic), payload + order checked, 1200 flits a channel.
//   default: PASS.   +OT_FIXLAT_MUT_LAT1: the VM end's receiver assumes a latency-1 link -> overflow (FAIL).
//   EP_FH / EP_RH: the hops the VM end is sized for (default = the stations): 9 / 10 = the stale chain-only count (FAIL).
module pep_relay #(parameter integer W=1, N=0)(input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
 generate if(N==0) begin: z assign q=d; end else begin: p
  reg [W-1:0] s[0:N-1]; integer i;
  always @(posedge clk) if(!rst_n) for(i=0;i<N;i=i+1) s[i]<='0; else begin s[0]<=d; for(i=1;i<N;i=i+1) s[i]<=s[i-1]; end
  assign q=s[N-1];
 end endgenerate
endmodule
module tb_mtp_partner_ep #(parameter integer FC=6, RC=7, FV=11, RV=11, EP_FH=-1, EP_RH=-1, SEED=1);
 localparam integer NW=21, USER_W=10, DW=USER_W+3+NW, FLIT=512, TOTAL=1200;
 localparam integer AFH = EP_FH<0 ? RV : EP_FH, ARH = EP_RH<0 ? FV : EP_RH;   // mtp->vm data = RV, vm->mtp grant = FV
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0;
 integer cycle=0;
 function automatic [31:0] mix(input [31:0] a, b); mix=(a^(b*32'h9e3779b9))*32'h85ebca6b ^ (a>>13); endfunction
 function automatic [FLIT-1:0] pay(input integer ch, n);
  integer k; begin for(k=0;k<FLIT/32;k=k+1) pay[32*k+:32]=mix(mix(ch,n),k); end
 endfunction
 // channel c: 0 RESULT cap->seq, 1 rows-ready vm->seq, 2 draft-head step seq->vm, 3 draft-head result vm->seq
 integer sent[0:3], rcvd[0:3];
 reg sv[0:3], cr[0:3];
 wire sr0, sr1, sr2, sr3, cv0, cv1, cv2, cv3;
 wire [FLIT-1:0] cd0; wire [USER_W-1:0] cd1; wire [DW-1:0] cd2, cd3;
 // ---- capture end -> 6 stations -> seq u_r (lrx_rtt 6 / 7, D 17 as in dsfd_mtp_seq_rtt)
 wire rv_e, rg_e, rv_s, rg_s; wire [FLIT-1:0] rd_e, rd_s;
 dsfd_cap_mtp_ep cap(.ck(clk), .rst(rst_n), .c_rv(sv[0]), .c_rr(sr0), .c_rd(pay(0,sent[0])), .t_rv(rv_e), .t_rd(rd_e), .f_rg(rg_e));
 pep_relay #(.W(FLIT+1),.N(FC)) a0(clk, rst_n, {rv_e,rd_e}, {rv_s,rd_s});
 pep_relay #(.W(1),.N(RC)) a0g(clk, rst_n, rg_s, rg_e);
 ot_dsrom_mtp_lrx_rtt #(.W(FLIT),.D(FC+RC+4),.ENABLE_RTT(1),.FORWARD_HOPS(FC),.RETURN_HOPS(RC)) s_r(.clk(clk),.rst_n(rst_n),
  .l_valid(rv_s),.l_ready(rg_s),.l_data(rd_s),.c_valid(cv0),.c_ready(cr[0]),.c_data(cd0));
 // ---- VM end
 wire wv_e, wg_e, wv_s, wg_s, qv_e, qg_e, qv_s, qg_s, hv_e, hg_e, hv_s, hg_s;
 wire [USER_W-1:0] wd_e, wd_s; wire [DW-1:0] qd_e, qd_s, hd_e, hd_s;
 dsfd_vm_mtp_ep #(.FWD_H(AFH),.RET_H(ARH),.D_H(RV+FV+4)) vme(.ck(clk), .rst(rst_n),
  .f_hv(hv_e), .f_hd(hd_e), .t_hg(hg_e), .c_hv(cv2), .c_hr(cr[2]), .c_hd(cd2),
  .c_wv(sv[1]), .c_wr(sr1), .c_wd(pay(1,sent[1])), .t_wv(wv_e), .t_wd(wd_e), .f_wg(wg_e),
  .c_qv(sv[3]), .c_qr(sr3), .c_qd(pay(3,sent[3])), .t_qv(qv_e), .t_qd(qd_e), .f_qg(qg_e));
 pep_relay #(.W(USER_W+1),.N(FV)) a1(clk, rst_n, {wv_e,wd_e}, {wv_s,wd_s});
 pep_relay #(.W(1),.N(RV)) a1g(clk, rst_n, wg_s, wg_e);
 pep_relay #(.W(DW+1),.N(FV)) a3(clk, rst_n, {qv_e,qd_e}, {qv_s,qd_s});
 pep_relay #(.W(1),.N(RV)) a3g(clk, rst_n, qg_s, qg_e);
 pep_relay #(.W(DW+1),.N(RV)) a2(clk, rst_n, {hv_s,hd_s}, {hv_e,hd_e});
 pep_relay #(.W(1),.N(FV)) a2g(clk, rst_n, hg_e, hg_s);
 ot_dsrom_mtp_lrx_rtt #(.W(USER_W),.D(FV+RV+4),.ENABLE_RTT(1),.FORWARD_HOPS(FV),.RETURN_HOPS(RV)) s_w(.clk(clk),.rst_n(rst_n),
  .l_valid(wv_s),.l_ready(wg_s),.l_data(wd_s),.c_valid(cv1),.c_ready(cr[1]),.c_data(cd1));
 ot_dsrom_mtp_lrx_rtt #(.W(DW),.D(FV+RV+4),.ENABLE_RTT(1),.FORWARD_HOPS(FV),.RETURN_HOPS(RV)) s_q(.clk(clk),.rst_n(rst_n),
  .l_valid(qv_s),.l_ready(qg_s),.l_data(qd_s),.c_valid(cv3),.c_ready(cr[3]),.c_data(cd3));
 ot_dsrom_mtp_ltx #(.W(DW)) s_h(.clk(clk),.rst_n(rst_n),.c_valid(sv[2]),.c_ready(sr2),.c_data(pay(2,sent[2])),
  .l_valid(hv_s),.l_ready(hg_s),.l_data(hd_s));
 // ---- traffic
 wire [3:0] srs = {sr3, sr2, sr1, sr0}, cvs = {cv3, cv2, cv1, cv0};
 integer c; reg [31:0] r;
 initial for(c=0;c<4;c=c+1) begin sent[c]=0; rcvd[c]=0; sv[c]=0; cr[c]=0; end
 always @(negedge clk) if(rst_n) for(c=0;c<4;c=c+1) begin
  r = mix(cycle*4+c, SEED);
  sv[c] = sent[c]<TOTAL && (cycle<300 || r[3:0]>1);
  cr[c] = !(cycle>=60+40*c && cycle<260+40*c) && !(cycle%400>=320) && r[7:5]!=0;
 end
 function automatic ok(input integer ch, input integer n);
  reg [FLIT-1:0] e; begin e = pay(ch,n);
  case(ch) 0: ok = cd0===e; 1: ok = cd1===e[USER_W-1:0]; 2: ok = cd2===e[DW-1:0]; default: ok = cd3===e[DW-1:0]; endcase
  end
 endfunction
 integer done_c;
 always @(posedge clk) if(rst_n) begin
  cycle<=cycle+1;
  for(c=0;c<4;c=c+1) begin
   if(sv[c] && srs[c]) sent[c]<=sent[c]+1;
   if(cvs[c] && cr[c]) begin
    if(rcvd[c]>=sent[c]) $fatal(1,"PEP ch%0d unexpected/duplicate flit %0d",c,rcvd[c]);
    if(!ok(c,rcvd[c])) $fatal(1,"PEP ch%0d payload/order mismatch flit %0d",c,rcvd[c]);
    rcvd[c]<=rcvd[c]+1;
   end
  end
  done_c=0; for(c=0;c<4;c=c+1) if(rcvd[c]==TOTAL) done_c=done_c+1;
  if(done_c==4) begin
   $display("PEP PASS FC=%0d RC=%0d FV=%0d RV=%0d VM-end hops %0d/%0d flits=4x%0d cycles=%0d",FC,RC,FV,RV,AFH,ARH,TOTAL,cycle);
   $finish;
  end
  if(cycle>60000) $fatal(1,"PEP timeout %0d %0d %0d %0d",rcvd[0],rcvd[1],rcvd[2],rcvd[3]);
 end
 initial begin repeat(8) @(negedge clk); rst_n=1; end
endmodule
