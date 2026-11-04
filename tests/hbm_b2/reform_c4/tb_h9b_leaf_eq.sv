`timescale 1ps/1fs
// DIE-HBM-61 RE-FORM C4 round 2 (2026-11-03): cycle lockstep ot_hbm_svc_pc_ctrl_leaf_cfg_h9b (new: QLATE=1, EREG=1 +
// controller WP_REG=1) vs origin/main (_old). Declared cycle shift 0: every output pin on every edge, plus head_q / push_q.
// Stimulus: legal K traffic (tb_hbm_pc_h9b_txn generator), random consumer stalls, per-DUT in-order DRAM (14 edges).
module tb;
  parameter integer T=0, NREQ=6000;
  reg clk=0; always #512 clk=~clk;
  reg rst_n=0; reg [4:0] pc_id=5'd9; reg [7:0] refresh_reload=8'd151;
  reg [29:0] ra[0:NREQ-1]; reg [3:0] rl[0:NREQ-1]; reg rw[0:NREQ-1]; reg [16:0] rt[0:NREQ-1];
  reg [255:0] rd[0:NREQ-1]; reg [31:0] rs[0:NREQ-1];
  reg [31:0] rng=32'h1d872b41; function [31:0] nx(input [31:0] r); nx={r[30:0],r[31]^r[21]^r[1]^r[0]}; endfunction
  reg offer=0, r_now=0;
  integer idx[0:1]; wire [1:0] k_rdy,kr_v,k_wr_done,row_v,col_v,col_we,pc_fault; wire [5:0] of[0:1];
  wire [16:0] kr_tag[0:1]; wire [3:0] kr_beat[0:1]; wire [255:0] kr_data[0:1],col_data[0:1]; wire [31:0] col_strb[0:1];
  wire [2:0] row_op[0:1]; wire [4:0] row_bank[0:1],col_bank[0:1],col_col[0:1]; wire [18:0] row_row[0:1];
  reg dv[0:1]; reg [255:0] dd[0:1];
  wire [1:0] kv; assign kv[0]=offer&&idx[0]<NREQ; assign kv[1]=offer&&idx[1]<NREQ;
`define LEAFC(D) .clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload), \
    .k_v(kv[D]),.k_rdy(k_rdy[D]),.k_we(rw[idx[D]%NREQ]),.k_addr(ra[idx[D]%NREQ]),.k_len(rl[idx[D]%NREQ]),.k_tag(rt[idx[D]%NREQ]), \
    .k_wdata(rd[idx[D]%NREQ]),.k_wstrb(rs[idx[D]%NREQ]),.kr_v(kr_v[D]),.kr_rdy(r_now),.kr_tag(kr_tag[D]),.kr_beat(kr_beat[D]), \
    .kr_data(kr_data[D]),.k_wr_done(k_wr_done[D]),.row_v(row_v[D]),.row_op(row_op[D]),.row_bank(row_bank[D]),.row_row(row_row[D]), \
    .col_v(col_v[D]),.col_we(col_we[D]),.col_bank(col_bank[D]),.col_col(col_col[D]),.col_data(col_data[D]),.col_strb(col_strb[D]), \
    .dram_rvalid(dv[D]),.dram_rdata(dd[D]),.pc_fault(pc_fault[D]),.owner_fault_split(of[D])
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.TIMING_833(T)) dn(`LEAFC(0));
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_old #(.TIMING_833(T)) dold(`LEAFC(1));
  wire [700:0] o0={k_rdy[0],kr_v[0],k_wr_done[0],row_v[0],col_v[0],col_we[0],pc_fault[0],of[0],kr_tag[0],kr_beat[0],kr_data[0],
                   col_data[0],col_strb[0],row_op[0],row_bank[0],col_bank[0],col_col[0],row_row[0]};
  wire [700:0] o1={k_rdy[1],kr_v[1],k_wr_done[1],row_v[1],col_v[1],col_we[1],pc_fault[1],of[1],kr_tag[1],kr_beat[1],kr_data[1],
                   col_data[1],col_strb[1],row_op[1],row_bank[1],col_bank[1],col_col[1],row_row[1]};
  integer rdseq[0:1]; integer rq[0:1][0:255]; integer rqw[0:1],rqr[0:1]; integer now=0;
  integer d,i,errors=0,ncol=0,nwc=0,nbeat=0,nhit=0,checks=0;
  always @(posedge clk) begin
    now=now+1;
    for(d=0;d<2;d=d+1) if(!rst_n) begin dv[d]<=0; end else begin
      if(kv[d]&&k_rdy[d]) idx[d]<=idx[d]+1;
      if(col_v[d]&&!col_we[d]) begin rq[d][rqw[d]%256]=now+14; rqw[d]=rqw[d]+1; end
      if(rqr[d]!=rqw[d] && rq[d][rqr[d]%256]<=now) begin dv[d]<=1; dd[d]<={8{32'(rqr[d])*32'h9e3779b1^32'h5a5a0000}}; rqr[d]=rqr[d]+1; end
      else dv[d]<=0;
    end
  end
  always @(negedge clk) if(rst_n && now>8) begin
    checks=checks+1;
    if(o0!==o1 || dn.head_q!==dold.head_q || dn.push_q!==dold.push_q) begin
      errors=errors+1; if(errors<6) $display("ERR edge %0d pins_eq=%0d head_eq=%0d push_eq=%0d",now,o0===o1,dn.head_q===dold.head_q,dn.push_q===dold.push_q); end
    if(col_v[1]) ncol=ncol+1; if(col_v[1]&&col_we[1]) nwc=nwc+1; if(kr_v[1]&&r_now) nbeat=nbeat+1;
    if(dn.cv && dn.count>1) nhit=nhit+1;
    if(pc_fault[1]||(|of[1])) begin errors=errors+1; if(errors<6) $display("FAULT edge %0d of=%b",now,of[1]); end
  end
  initial begin
    for(d=0;d<2;d=d+1) begin idx[d]=0;rqw[d]=0;rqr[d]=0; end
    for(i=0;i<NREQ;i=i+1) begin : gen
      reg [29:0] a; reg [3:0] l; reg [4:0] x;
      rng=nx(rng); rw[i]=(rng[5:3]==0)||(rng[5:3]==1&&(i/500)%2); rng=nx(rng); a=rng[29:0]; a[29:15]=15'(5+((i/97)%3)); rng=nx(rng);
      l=rw[i]?4'd1:4'(1+rng[1:0]); a[1:0]=2'(rng[3:2]%(5-l)); x=pc_id^a[11:7]^a[16:12]; a[6:2]=x;
      ra[i]=a; rl[i]=l; rt[i]=17'(i); rng=nx(rng); rs[i]=rng; rd[i]={8{rng^32'h3c3c3c3c}};
    end
    rst_n=0; repeat(6)@(posedge clk); @(negedge clk); #1 rst_n=1;
    while(idx[1]<NREQ && now<300000) begin
      @(negedge clk); #1 rng=nx(rng); offer=(rng[2:0]!=0)&&now>24; rng=nx(rng);
      r_now=((now/3000)%2) ? (rng[3:0]!=0) : (rng[1:0]==0);   // phases of light / heavy consumer stalls
    end
    repeat(300)@(negedge clk);
    $display("H9B_LEAF_EQ T=%0d checks=%0d errors=%0d reqs=%0d cols=%0d wcols=%0d beats=%0d busy_pops=%0d %s",T,checks,errors,idx[1],
             ncol,nwc,nbeat,nhit,(errors==0 && idx[1]==NREQ && nwc>300 && nbeat>3000 && nhit>1000)?"PASS":"FAIL");
    $finish;
  end
endmodule
