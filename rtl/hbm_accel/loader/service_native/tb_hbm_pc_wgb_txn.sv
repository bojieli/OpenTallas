`timescale 1ps/1fs
// BUS-GEAR-1 (2026-11-12) transaction-level equivalence of the PC write-data gearbox: the counted h9b form
// (WGB=1, the reference) and WGB=2 (+ W_GAP=2 in the controller, 2 x 144-b write beats, ot_hbm_pc_phy_gear_rx at the
// PHY side, whole command bundle +1 edge) receive the SAME request stream and the SAME per-edge consumer readiness
// and each drives its own in-order DRAM (read beat = hash of the read-column sequence number, 14 edges after the
// read column as the PHY sees it).  Every write column (bank, col, data, strb), every k_wr_done and every response
// beat (tag, beat, data) must agree in ORDER and CONTENT; faults stay 0.  WRH = write share in 1/8 (1 = the h9b
// bench mix, 6 = write-heavy, so back-to-back writes occur and W_GAP engages).  The gear side must finish within
// 5% + 64 edges of the reference.  MUT: 1 = controller W_GAP off with WGB=2 (overlap -> beats corrupt / fault),
// 2 = RX side-band not delayed (command one edge ahead of its data).
module tb;
  parameter integer NREQ=6000, WRH=1, MUT=0;
  reg clk=0; always #416 clk=~clk;
  reg rst_n=0; reg [4:0] pc_id=5'd9; reg [7:0] refresh_reload=8'd151;
  reg [29:0] ra[0:NREQ-1]; reg [3:0] rl[0:NREQ-1]; reg rw[0:NREQ-1]; reg [16:0] rt[0:NREQ-1];
  reg [255:0] rd[0:NREQ-1]; reg [31:0] rs[0:NREQ-1];
  reg [31:0] rng=32'h1d872b41; function [31:0] nx(input [31:0] r); nx={r[30:0],r[31]^r[21]^r[1]^r[0]}; endfunction
  reg offer=0, r_now=0;
  reg r_now_q=0; always @(posedge clk) r_now_q<=r_now;   // h9b: ready-latency-1 (beat transfers on kr_v && kr_rdy(t-1))
  integer idx[0:1]; wire [1:0] k_rdy,kr_v,k_wr_done,pc_fault; wire [5:0] of[0:1];
  wire [16:0] kr_tag[0:1]; wire [3:0] kr_beat[0:1]; wire [255:0] kr_data[0:1];
  // PHY-side view of each DUT (after the RX for the gear DUT)
  wire [1:0] row_v,col_v,col_we; wire [2:0] row_op[0:1]; wire [4:0] row_bank[0:1],col_bank[0:1],col_col[0:1];
  wire [18:0] row_row[0:1]; wire [255:0] col_data[0:1]; wire [31:0] col_strb[0:1];
  reg dv[0:1]; reg [255:0] dd[0:1];
  wire [1:0] kv; assign kv[0]=offer&&idx[0]<NREQ; assign kv[1]=offer&&idx[1]<NREQ;
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b__fcore a(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),
    .k_v(kv[0]),.k_rdy(k_rdy[0]),.k_we(rw[idx[0]%NREQ]),.k_addr(ra[idx[0]%NREQ]),.k_len(rl[idx[0]%NREQ]),.k_tag(rt[idx[0]%NREQ]),
    .k_wdata(rd[idx[0]%NREQ]),.k_wstrb(rs[idx[0]%NREQ]),.kr_v(kr_v[0]),.kr_rdy(r_now),.kr_tag(kr_tag[0]),.kr_beat(kr_beat[0]),
    .kr_data(kr_data[0]),.k_wr_done(k_wr_done[0]),.row_v(row_v[0]),.row_op(row_op[0]),.row_bank(row_bank[0]),.row_row(row_row[0]),
    .col_v(col_v[0]),.col_we(col_we[0]),.col_bank(col_bank[0]),.col_col(col_col[0]),.col_data(col_data[0]),.col_strb(col_strb[0]),
    .dram_rvalid(dv[0]),.dram_rdata(dd[0]),.pc_fault(pc_fault[0]),.owner_fault_split(of[0]));
  // gear DUT: PC pins (narrow) -> RX -> PHY view
  wire g_row_v,g_col_v,g_col_we; wire [2:0] g_row_op; wire [4:0] g_row_bank,g_col_bank,g_col_col; wire [18:0] g_row_row;
  wire [127:0] g_col_data; wire [15:0] g_col_strb;
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b__fcore #(.WGB(2)) b(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),
    .k_v(kv[1]),.k_rdy(k_rdy[1]),.k_we(rw[idx[1]%NREQ]),.k_addr(ra[idx[1]%NREQ]),.k_len(rl[idx[1]%NREQ]),.k_tag(rt[idx[1]%NREQ]),
    .k_wdata(rd[idx[1]%NREQ]),.k_wstrb(rs[idx[1]%NREQ]),.kr_v(kr_v[1]),.kr_rdy(r_now),.kr_tag(kr_tag[1]),.kr_beat(kr_beat[1]),
    .kr_data(kr_data[1]),.k_wr_done(k_wr_done[1]),.row_v(g_row_v),.row_op(g_row_op),.row_bank(g_row_bank),.row_row(g_row_row),
    .col_v(g_col_v),.col_we(g_col_we),.col_bank(g_col_bank),.col_col(g_col_col),.col_data(g_col_data),.col_strb(g_col_strb),
    .dram_rvalid(dv[1]),.dram_rdata(dd[1]),.pc_fault(pc_fault[1]),.owner_fault_split(of[1]));
  generate if (MUT == 1) begin : m1
    initial force tb.b.controller.on.wgap_blk = 1'b0;   // W_GAP spacing removed: write columns back to back under WGB=2
  end endgenerate
  wire x_row_v,x_col_v,x_col_we; wire [2:0] x_row_op; wire [4:0] x_row_bank,x_col_bank,x_col_col; wire [18:0] x_row_row;
  ot_hbm_pc_phy_gear_rx u_phy_rx(.clk(clk),.rst_n(rst_n),.i_row_v(g_row_v),.i_row_op(g_row_op),.i_row_bank(g_row_bank),
    .i_row_row(g_row_row),.i_col_v(g_col_v),.i_col_we(g_col_we),.i_col_bank(g_col_bank),.i_col_col(g_col_col),
    .i_col_data(g_col_data),.i_col_strb(g_col_strb),.row_v(x_row_v),.row_op(x_row_op),.row_bank(x_row_bank),
    .row_row(x_row_row),.col_v(x_col_v),.col_we(x_col_we),.col_bank(x_col_bank),.col_col(x_col_col),
    .col_data(col_data[1]),.col_strb(col_strb[1]));
  // MUT 2: the PHY sees the PC's command pins directly (not delayed) next to the re-assembled data
  assign row_v[1]   = (MUT==2) ? g_row_v   : x_row_v;   assign row_op[1]  = (MUT==2) ? g_row_op  : x_row_op;
  assign row_bank[1]= (MUT==2) ? g_row_bank: x_row_bank;assign row_row[1] = (MUT==2) ? g_row_row : x_row_row;
  assign col_v[1]   = (MUT==2) ? g_col_v   : x_col_v;   assign col_we[1]  = (MUT==2) ? g_col_we  : x_col_we;
  assign col_bank[1]= (MUT==2) ? g_col_bank: x_col_bank;assign col_col[1] = (MUT==2) ? g_col_col : x_col_col;
  reg [276:0] beat_log[0:1][0:60000]; integer nb[0:1]; reg [297:0] wcol_log[0:1][0:60000]; integer nw[0:1];
  integer nwd[0:1]; integer rq[0:1][0:255]; integer rqw[0:1],rqr[0:1]; integer now=0, done_at[0:1], b2b=0;
  integer d,i,errors=0; reg we_prev=0;
  always @(posedge clk) begin
    now=now+1;
    for(d=0;d<2;d=d+1) if(!rst_n) begin dv[d]<=0; end else begin
      if(kv[d]&&k_rdy[d]) idx[d]<=idx[d]+1;
      if(col_v[d]===1'b1&&col_we[d]===1'b0) begin rq[d][rqw[d]%256]=now+14; rqw[d]=rqw[d]+1; end
      if(col_v[d]===1'b1&&col_we[d]===1'b1) begin wcol_log[d][nw[d]]={col_bank[d],col_col[d],col_strb[d],col_data[d]}; nw[d]=nw[d]+1; end
      if(rqr[d]!=rqw[d] && rq[d][rqr[d]%256]<=now) begin dv[d]<=1; dd[d]<={8{32'(rqr[d])*32'h9e3779b1^32'h5a5a0000}}; rqr[d]=rqr[d]+1; end
      else dv[d]<=0;
      if(k_wr_done[d]) nwd[d]=nwd[d]+1;
      if(kr_v[d] && r_now_q) begin beat_log[d][nb[d]]={kr_tag[d],kr_beat[d],kr_data[d]}; nb[d]=nb[d]+1; end
      if(pc_fault[d]||(|of[d])) begin errors=errors+1; if(errors<5) $display("WGB_TXN_FAULT dut%0d of=%b edge%0d",d,of[d],now); end
      if(idx[d]>=NREQ && done_at[d]==0 && rqr[d]==rqw[d] && !kr_v[d]) done_at[d]=now;
    end
    if(rst_n) begin if(col_we[0]===1'b1 && we_prev) b2b=b2b+1; we_prev<=col_we[0]; end
  end
  integer nrd=0;
  initial begin
    for(d=0;d<2;d=d+1) begin idx[d]=0;nb[d]=0;nw[d]=0;nwd[d]=0;rqw[d]=0;rqr[d]=0;done_at[d]=0; end
    for(i=0;i<NREQ;i=i+1) begin : gen
      reg [29:0] a; reg [3:0] l; reg [4:0] x;
      rng=nx(rng); rw[i]=(rng[5:3]<WRH); rng=nx(rng); a=rng[29:0]; a[29:15]=15'(5+((i/97)%2)); rng=nx(rng);
      l=rw[i]?4'd1:4'(1+rng[1:0]); a[1:0]=2'(rng[3:2]%(5-l)); x=pc_id^a[11:7]^a[16:12]; a[6:2]=x;
      ra[i]=a; rl[i]=l; rt[i]=17'(i); rng=nx(rng); rs[i]=rng; rd[i]={8{rng^32'h3c3c3c3c}}; if(!rw[i]) nrd=nrd+l;
    end
    $display("WGB_TXN cfg WRH=%0d MUT=%0d controller.W_GAP=%0d",WRH,MUT,b.controller.W_GAP);
    rst_n=0; repeat(6)@(posedge clk); @(negedge clk); #1 rst_n=1;
    while(!(done_at[0]!=0 && done_at[1]!=0) && now<600000 && errors<64) begin   // a faulting mutant stops early
      @(negedge clk); #1 rng=nx(rng); offer=(rng[2:0]!=0)&&now>24; rng=nx(rng); r_now=(rng[3:0]!=0);
    end
    @(negedge clk); #1 offer=0; r_now=1;   // drain: consumer always ready
    repeat(400)@(negedge clk);
    if(nb[0]!=nb[1]||nw[0]!=nw[1]||nwd[0]!=nwd[1]) begin errors=errors+1; $display("WGB_TXN_COUNT beats %0d/%0d wcols %0d/%0d wdone %0d/%0d",nb[0],nb[1],nw[0],nw[1],nwd[0],nwd[1]); end
    for(i=0;i<nb[0]&&i<nb[1];i=i+1) if(beat_log[0][i]!==beat_log[1][i]) begin errors=errors+1; if(errors<5) $display("WGB_TXN_BEAT_MISMATCH i%0d",i); end
    for(i=0;i<nw[0]&&i<nw[1];i=i+1) if(wcol_log[0][i]!==wcol_log[1][i]) begin errors=errors+1; if(errors<5) $display("WGB_TXN_WCOL_MISMATCH i%0d",i); end
    if(nb[0]<nrd/2 || nw[0]<100) begin errors=errors+1; $display("WGB_TXN_VACUOUS beats%0d wcols%0d",nb[0],nw[0]); end
    if(done_at[0]==0||done_at[1]==0||done_at[1]>done_at[0]+done_at[0]/20+64) begin errors=errors+1; $display("WGB_TXN_RATE ref %0d gear %0d",done_at[0],done_at[1]); end
    if(b.gb_fault!==1'b0) $display("WGB_TXN_GEAR_FAULT (beat overlap) seen");
    if(errors) $display("WGB_TXN FAIL errors=%0d WRH=%0d MUT=%0d b2b=%0d", errors, WRH, MUT, b2b);
    else $display("WGB_TXN PASS reqs=%0d beats=%0d wcols=%0d wdone=%0d ref_b2b_writes=%0d edges_ref=%0d edges_gear=%0d WRH=%0d",NREQ,nb[1],nw[1],nwd[1],b2b,done_at[0],done_at[1],WRH);
    $finish;
  end
endmodule
