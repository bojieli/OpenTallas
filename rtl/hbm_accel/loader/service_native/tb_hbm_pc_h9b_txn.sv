`timescale 1ps/1fs
// H9b transaction-level equivalence (H-PC Claude 2026-10-16). H9 (edge-exact to the original specialized controller,
// proven by the all32/safety/full benches) and H9b (pin-registered K/KR boundary: +1 K edge, kr_rdy ready-latency-1)
// receive the SAME request stream, the SAME per-edge consumer readiness r(t) and their own in-order DRAM (read beat =
// hash of the read-column sequence number, 14 edges later). Every accepted request, every write column (bank, col,
// data, strb), every k_wr_done and every response beat (tag, beat, data) must agree in ORDER and CONTENT; H9 transfers a
// response at t on kr_v(t)&&r(t), H9b on kr_v(t)&&r(t-1) (the consumer's 1-entry slot). Faults must stay 0 (legal
// traffic; ring overflow/underflow is a fault class). Throughput: H9b must finish within 5% + 64 edges of H9 (owner per-unit ledger bound; measured 3.2% under 1/16 random consumer stalls).
// +RMUT via parameter: 1 K ring slice skew, 2 KR ring slice skew, 3 k_rdy credit off by one.
module tb;
  parameter integer RMUT=0, NREQ=6000;
  reg clk=0; always #512 clk=~clk;
  reg rst_n=0; reg [4:0] pc_id=5'd9; reg [7:0] refresh_reload=8'd151;
  reg [29:0] ra[0:NREQ-1]; reg [3:0] rl[0:NREQ-1]; reg rw[0:NREQ-1]; reg [16:0] rt[0:NREQ-1];
  reg [255:0] rd[0:NREQ-1]; reg [31:0] rs[0:NREQ-1];
  reg [31:0] rng=32'h1d872b41; function [31:0] nx(input [31:0] r); nx={r[30:0],r[31]^r[21]^r[1]^r[0]}; endfunction
  reg offer=0, r_now=0, r_prev=0;
  integer idx[0:1]; wire [1:0] k_rdy,kr_v,k_wr_done,row_v,col_v,col_we,pc_fault; wire [5:0] of[0:1];
  wire [16:0] kr_tag[0:1]; wire [3:0] kr_beat[0:1]; wire [255:0] kr_data[0:1],col_data[0:1]; wire [31:0] col_strb[0:1];
  wire [2:0] row_op[0:1]; wire [4:0] row_bank[0:1],col_bank[0:1],col_col[0:1]; wire [18:0] row_row[0:1];
  reg dv[0:1]; reg [255:0] dd[0:1];
  wire [1:0] kv; assign kv[0]=offer&&idx[0]<NREQ; assign kv[1]=offer&&idx[1]<NREQ;
  wire [1:0] krr; assign krr[0]=r_now; assign krr[1]=r_now;   // H9b registers kr_rdy itself (ready-latency-1)
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9 a(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),
    .k_v(kv[0]),.k_rdy(k_rdy[0]),.k_we(rw[idx[0]%NREQ]),.k_addr(ra[idx[0]%NREQ]),.k_len(rl[idx[0]%NREQ]),.k_tag(rt[idx[0]%NREQ]),
    .k_wdata(rd[idx[0]%NREQ]),.k_wstrb(rs[idx[0]%NREQ]),.kr_v(kr_v[0]),.kr_rdy(krr[0]),.kr_tag(kr_tag[0]),.kr_beat(kr_beat[0]),
    .kr_data(kr_data[0]),.k_wr_done(k_wr_done[0]),.row_v(row_v[0]),.row_op(row_op[0]),.row_bank(row_bank[0]),.row_row(row_row[0]),
    .col_v(col_v[0]),.col_we(col_we[0]),.col_bank(col_bank[0]),.col_col(col_col[0]),.col_data(col_data[0]),.col_strb(col_strb[0]),
    .dram_rvalid(dv[0]),.dram_rdata(dd[0]),.pc_fault(pc_fault[0]),.owner_fault_split(of[0]));
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.RMUT(RMUT)) b(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),
    .k_v(kv[1]),.k_rdy(k_rdy[1]),.k_we(rw[idx[1]%NREQ]),.k_addr(ra[idx[1]%NREQ]),.k_len(rl[idx[1]%NREQ]),.k_tag(rt[idx[1]%NREQ]),
    .k_wdata(rd[idx[1]%NREQ]),.k_wstrb(rs[idx[1]%NREQ]),.kr_v(kr_v[1]),.kr_rdy(krr[1]),.kr_tag(kr_tag[1]),.kr_beat(kr_beat[1]),
    .kr_data(kr_data[1]),.k_wr_done(k_wr_done[1]),.row_v(row_v[1]),.row_op(row_op[1]),.row_bank(row_bank[1]),.row_row(row_row[1]),
    .col_v(col_v[1]),.col_we(col_we[1]),.col_bank(col_bank[1]),.col_col(col_col[1]),.col_data(col_data[1]),.col_strb(col_strb[1]),
    .dram_rvalid(dv[1]),.dram_rdata(dd[1]),.pc_fault(pc_fault[1]),.owner_fault_split(of[1]));
  // per-DUT logs
  reg [276:0] beat_log[0:1][0:40000]; integer nb[0:1]; reg [298:0] wcol_log[0:1][0:20000]; integer nw[0:1];
  integer nwd[0:1]; integer rdseq[0:1]; integer rq[0:1][0:255]; integer rqw[0:1],rqr[0:1]; integer now=0, done_at[0:1];
  integer d,i,errors=0;
  always @(posedge clk) begin
    now=now+1;
    for(d=0;d<2;d=d+1) if(!rst_n) begin dv[d]<=0; end else begin
      if(kv[d]&&k_rdy[d]) idx[d]<=idx[d]+1;   // NBA: the DUT samples the current request on this edge
      if(col_v[d]&&!col_we[d]) begin rq[d][rqw[d]%256]=now+14; rqw[d]=rqw[d]+1; end
      if(col_v[d]&&col_we[d]) begin wcol_log[d][nw[d]]={col_bank[d],col_col[d],col_strb[d],col_data[d]}; nw[d]=nw[d]+1; end
      if(rqr[d]!=rqw[d] && rq[d][rqr[d]%256]<=now) begin dv[d]<=1; dd[d]<={8{32'(rqr[d])*32'h9e3779b1^32'h5a5a0000}}; rqr[d]=rqr[d]+1; end
      else dv[d]<=0;
      if(k_wr_done[d]) nwd[d]=nwd[d]+1;
      if(kr_v[d] && (d==0 ? r_now : r_prev)) begin beat_log[d][nb[d]]={kr_tag[d],kr_beat[d],kr_data[d]}; nb[d]=nb[d]+1; end
      if(pc_fault[d]||(|of[d])) begin errors=errors+1; if(errors<5) $display("H9B_TXN_FAULT dut%0d of=%b edge%0d",d,of[d],now); end
      if(idx[d]>=NREQ && done_at[d]==0 && rqr[d]==rqw[d] && !kr_v[d]) done_at[d]=now;
    end
    r_prev<=r_now;
  end
  integer nrd=0;
  initial begin
    for(d=0;d<2;d=d+1) begin idx[d]=0;nb[d]=0;nw[d]=0;nwd[d]=0;rqw[d]=0;rqr[d]=0;done_at[d]=0; end
    for(i=0;i<NREQ;i=i+1) begin : gen
      reg [29:0] a; reg [3:0] l; reg [4:0] x;
      rng=nx(rng); rw[i]=(rng[5:3]==0); rng=nx(rng); a=rng[29:0]; a[29:15]=15'(5+((i/97)%2)); rng=nx(rng);
      l=rw[i]?4'd1:4'(1+rng[1:0]); a[1:0]=2'(rng[3:2]%(5-l)); x=pc_id^a[11:7]^a[16:12]; a[6:2]=x;
      ra[i]=a; rl[i]=l; rt[i]=17'(i); rng=nx(rng); rs[i]=rng; rd[i]={8{rng^32'h3c3c3c3c}}; if(!rw[i]) nrd=nrd+l;
    end
    rst_n=0; repeat(6)@(posedge clk); @(negedge clk); #1 rst_n=1;
    while(!(done_at[0]!=0 && done_at[1]!=0) && now<400000) begin
      @(negedge clk); #1 rng=nx(rng); offer=(rng[2:0]!=0)&&now>24; rng=nx(rng); r_now=(rng[3:0]!=0);   // offers start after every reset region released
    end
    repeat(200)@(negedge clk);
    if(nb[0]!=nb[1]||nw[0]!=nw[1]||nwd[0]!=nwd[1]) begin errors=errors+1; $display("H9B_TXN_COUNT beats %0d/%0d wcols %0d/%0d wdone %0d/%0d",nb[0],nb[1],nw[0],nw[1],nwd[0],nwd[1]); end
    for(i=0;i<nb[0]&&i<nb[1];i=i+1) if(beat_log[0][i]!==beat_log[1][i]) begin errors=errors+1; if(errors<5) $display("H9B_TXN_BEAT_MISMATCH i%0d h9 tag%h beat%h d%h h9b tag%h beat%h d%h",i,beat_log[0][i][276:260],beat_log[0][i][259:256],beat_log[0][i][31:0],beat_log[1][i][276:260],beat_log[1][i][259:256],beat_log[1][i][31:0]); end
    for(i=0;i<nw[0]&&i<nw[1];i=i+1) if(wcol_log[0][i]!==wcol_log[1][i]) begin errors=errors+1; if(errors<5) $display("H9B_TXN_WCOL_MISMATCH i%0d",i); end
    if(nb[0]<nrd/2 || nw[0]<100) begin errors=errors+1; $display("H9B_TXN_VACUOUS beats%0d wcols%0d",nb[0],nw[0]); end
    if(done_at[0]==0||done_at[1]==0||done_at[1]>done_at[0]+done_at[0]/20+64) begin errors=errors+1; $display("H9B_TXN_RATE h9 %0d h9b %0d",done_at[0],done_at[1]); end
    if(errors) $fatal(1,"H9B_TXN FAIL errors=%0d RMUT=%0d",errors,RMUT);
    $display("H9B_TXN PASS reqs=%0d beats=%0d wcols=%0d wdone=%0d edges_h9=%0d edges_h9b=%0d",NREQ,nb[1],nw[1],nwd[1],done_at[0],done_at[1]);
    $finish;
  end
endmodule
