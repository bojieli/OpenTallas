`timescale 1ns/1ps
// P10 head vs frozen P9 head (S-ELEM-PQ 2026-10-15). P10 launches i0/i1/rq one edge later (separate W capture / E
// launch flops), so its banks answer one edge later: the P10 instance sees rd_data delayed one edge. Expected:
// wr/wq identical on the same edge; i/rq/hq/he/fault of P10 = P9's one edge later. Under random
// consume/hw_sv/index/rd_data/loader stimulus. The loader contract is the static schedule: a metadata
// row is not read within GAP edges of a write to it, and not rewritten within GAP edges of a read.
module tb_s81_pq_headpc_p10_equiv;
 parameter integer GAP = 8, EDGES = 200000, SEED = 1;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0, consume=0; reg [9:0] aqi=0; reg [15:0] h0=0,h1=0; reg [1:0] sv=0;
 reg [1023:0] rd=0; reg [19:0] ae=0; reg [9:0] ap=0;
 wire [6:0] a_wr0,a_wr1,b_wr0,b_wr1; wire [3:0] a_wq0,a_wq1,b_wq0,b_wq1,a_rq0,a_rq1,b_rq0,b_rq1;
 wire [15:0] a_i0,a_i1,b_i0,b_i1; wire [255:0] a_q0,a_q1,b_q0,b_q1; wire [9:0] a_e0,a_e1,b_e0,b_e1; wire a_f,b_f;
 reg [1023:0] rd_d=0; always @(posedge clk) rd_d <= rd;
 ot_s81_pq_qb_headpc_native dut(.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi),.h_b0(h0),.h_b1(h1),.hw_sv(sv),
  .rd_data(rd_d),.aq_e(ae),.aq_p(ap),.wr0(a_wr0),.wr1(a_wr1),.wq0(a_wq0),.wq1(a_wq1),.i0(a_i0),.i1(a_i1),.rq0(a_rq0),.rq1(a_rq1),
  .hq0(a_q0),.hq1(a_q1),.he0(a_e0),.he1(a_e1),.fault(a_f));
 ot_s81_pq_qb_headpc_native_p9ref ref9(.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi),.h_b0(h0),.h_b1(h1),.hw_sv(sv),
  .rd_data(rd),.aq_e(ae),.aq_p(ap),.wr0(b_wr0),.wr1(b_wr1),.wq0(b_wq0),.wq1(b_wq1),.i0(b_i0),.i1(b_i1),.rq0(b_rq0),.rq1(b_rq1),
  .hq0(b_q0),.hq1(b_q1),.he0(b_e0),.he1(b_e1),.fault(b_f));
 // last write / read edge per logical index 0..383
 integer lw[0:383], lr[0:383]; integer cyc=0, checks=0, nrd=0, nwr=0, seed=SEED, t, idx, blk, par, x, y, k, tries;
 reg ok;
 function automatic integer rnd(input integer n); rnd = $unsigned($random(seed)) % n; endfunction
 reg [15:0] d_i0=0,d_i1=0; reg [3:0] d_rq0=0,d_rq1=0; reg [255:0] d_q0=0,d_q1=0; reg [9:0] d_e0=0,d_e1=0; reg d_f=0;
 always @(posedge clk) begin d_i0<=b_i0;d_i1<=b_i1;d_rq0<=b_rq0;d_rq1<=b_rq1;d_q0<=b_q0;d_q1<=b_q1;d_e0<=b_e0;d_e1<=b_e1;d_f<=b_f; end
 always @(negedge clk) if (rst_n) begin
  if ({a_wr0,a_wr1,a_wq0,a_wq1,a_i0,a_i1,a_rq0,a_rq1,a_q0,a_q1,a_e0,a_e1,a_f} !==
      {b_wr0,b_wr1,b_wq0,b_wq1,d_i0,d_i1,d_rq0,d_rq1,d_q0,d_q1,d_e0,d_e1,d_f}) begin
   $display("PQ_HEADPC_P10_EQUIV FAIL edge=%0d i0 %h/%h rq0 %h/%h he0 %h/%h he1 %h/%h hq0 %0h/%0h fault %b/%b",
            cyc,a_i0,d_i0,a_rq0,d_rq0,a_e0,d_e0,a_e1,d_e1,a_q0[15:0],d_q0[15:0],a_f,d_f);
   $fatal(1,"P10 differs from P9 + 1 edge");
  end
  checks = checks + 2*7+4*4+4*16+2*256+2*10+1;
 end
 initial begin
  if (!$value$plusargs("seed=%d", seed)) seed = SEED;
  for (k=0;k<384;k=k+1) begin lw[k] = -1000000; lr[k] = -1000000; end
  repeat(8) @(negedge clk); rst_n=1; repeat(8) @(negedge clk);
  // Fill every row once so reads see written metadata (loader prologue).
  for (par=0; par<2; par=par+1) for (blk=0; blk<192; blk=blk+2) begin
   aqi={1'b1,8'(blk),1'(par)}; ae=$random(seed); ap=$random(seed); rd={32{$random(seed)}}; @(negedge clk); cyc=cyc+1;
   aqi=0; @(negedge clk); cyc=cyc+1;
  end
  repeat(GAP) begin @(negedge clk); cyc=cyc+1; end
  for (t=0; t<EDGES; t=t+1) begin
   rd = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
   rd = {4{rd[255:0]}} ^ {32{$random(seed)}};
   ae=$random(seed); ap=$random(seed);
   consume = rnd(8)!=0; sv = rnd(4);
   // reads: pick indices whose last write is >= GAP edges old
   for (x=0;x<2;x=x+1) begin
    tries=0; ok=0;
    while(!ok && tries<64) begin idx=rnd(384); ok = (cyc-lw[idx] >= GAP); tries=tries+1; end
    if (!ok) idx = 0;
    if (x==0) h0=16'(idx); else h1=16'(idx);
    if (ok && consume && sv[x]) begin lr[idx]=cyc; nrd=nrd+1; end
    if (!(consume && sv[x])) begin if (x==0) h0=16'($random(seed)) & 16'h01ff; else h1=16'($random(seed)) & 16'h01ff; if ((x==0?h0:h1)>=384) begin if(x==0) h0=0; else h1=0; end end
   end
   // write: a legal pair (index w, w+1) whose rows were not read within GAP edges
   aqi = 0;
   if (rnd(4)==0) begin
    par=rnd(2); blk=2*rnd(96); y=(par?192:0)+blk; // w0n = 192*aqi[0] + aqi[8:1], w1n = w0n+1
    ok = (cyc-lr[y] >= GAP) && (cyc-lr[y+1] >= GAP) && (cyc-lw[y] >= GAP) && (cyc-lw[y+1] >= GAP)
         && !(h0==y || h0==y+1 || h1==y || h1==y+1);
    if (ok) begin aqi={1'b1,8'(blk),1'(par)}; lw[y]=cyc; lw[y+1]=cyc; nwr=nwr+1; end
   end
   @(negedge clk); cyc=cyc+1;
  end
  sv=0; consume=0; aqi=0; repeat(12) @(negedge clk);
  $display("PQ_HEADPC_P10_EQUIV PASS edges=%0d reads=%0d writes=%0d checked_bits=%0d gap=%0d", EDGES, nrd, nwr, checks, GAP);
  $finish;
 end
endmodule
