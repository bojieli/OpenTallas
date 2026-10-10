`timescale 1ns/1ps
// sys-takeover 2026-10-09: qfd_hbm_ecc_provider exact bench.  ot_qfd_emb_pcport KVW=1 encodes KV write data into the
// HBM3E ECC side-band (288 b per beat); a behavioural HBM PC stores the full 288-b word; reads return it in issue order
// (with optional injected bit flips) through kv_d into ot_qfd_kv_landing_ecc.  Phases: clean (0 CE), single-bit flips in
// every word lane at data and check positions (all corrected, CE counted), double-bit flip (UE: no delivery, sticky fault).
module tb_qfd_hbm_ecc_provider;
 parameter integer MUT = 0;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0;
 reg col_v=0,col_we=0,col_sr=0,w_v=0,kw_v=0,r_v=0;
 reg [255:0] w_d=0,kw_d=0; reg [287:0] r_d=0;
 wire [287:0] wd,kv_d; wire kv_v,em_v,pfault; wire [257:0] em_d;
 ot_qfd_emb_pcport #(.KVW(1),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.col_v(col_v),.col_we(col_we),.col_sr(col_sr),
  .w_v(w_v),.w_d(w_d),.wd(wd),.kw_v(kw_v),.kw_d(kw_d),.r_v(r_v),.r_d(r_d),.kv_v(kv_v),.kv_d(kv_d),.em_v(em_v),.em_d(em_d),.fault(pfault));
 wire o_v,ce,ue,lfault; wire [255:0] o_data; wire [16:0] o_sec; wire [7:0] o_row; wire [31:0] ce_count;
 ot_qfd_kv_landing_ecc #(.ENABLE(1)) land(.hclk(clk),.h_rst_n(rst_n),.i_v(kv_v),.i_code(kv_d),.i_sec(17'd0),.i_row(8'd0),
  .o_v(o_v),.o_data(o_data),.o_sec(o_sec),.o_row(o_row),.ce(ce),.ue(ue),.fault(lfault),.ce_count(ce_count));
 localparam integer N = 64;
 reg [287:0] mem [0:N-1];
 reg [255:0] gold [0:N-1];
 integer qd [0:1023];
 integer qh, qt;
 integer i, got, exp_ce, nce, nue;
 function [255:0] pat(input integer k); integer j; begin for (j=0;j<8;j=j+1) pat[j*32+:32]=(32'h9e3779b9*(k*8+j+1))^(k<<j); end endfunction
 always @(posedge clk) begin
  if (o_v) begin
   if (o_data !== gold[qd[qh]]) begin $display("FATAL data mismatch entry %0d", qd[qh]); $fatal(1); end
   qh = qh + 1; got = got + 1;
  end
  if (ce) nce = nce + 1;
  if (ue) nue = nue + 1;
 end
 task write_all; begin
  for (i=0;i<N;i=i+1) begin
   gold[i]=pat(i);
   @(negedge clk); kw_v=1; kw_d=gold[i];
   @(negedge clk); kw_v=0; col_v=1; col_we=1; col_sr=0;
   #0.1 mem[i]=wd;            // the PHY samples the write data with the KV WR
   @(negedge clk); col_v=0; col_we=0;
  end
 end endtask
 // read entry k with flip mask f (a stored-bit upset / PHY error)
 task rd(input integer k, input [287:0] f); begin
  @(negedge clk); col_v=1; col_we=0; col_sr=0; qd[qt]=k; qt=qt+1;
  @(negedge clk); col_v=0;
  repeat(3) @(negedge clk);
  r_v=1; r_d=mem[k]^f;
  @(negedge clk); r_v=0;
 end endtask
 integer w, b;
 initial begin
  got=0; nce=0; nue=0; qh=0; qt=0;
  repeat(4) @(negedge clk); rst_n=1;
  write_all;
  if (pfault) begin $display("FATAL port fault on writes"); $fatal(1); end
  for (i=0;i<N;i=i+1) rd(i, 288'd0);
  repeat(8) @(negedge clk);
  if (got!=N || nce!=0 || nue!=0) begin $display("FATAL clean phase got=%0d ce=%0d ue=%0d", got, nce, nue); $fatal(1); end
  $display("PASS clean: %0d KV beats written with the side-band, read back exact, 0 CE", N);
  exp_ce=0;
  for (w=0; w<4; w=w+1) for (b=0; b<72; b=b+9) begin rd((w*8+b)%N, 288'd1 << (w*72+b)); exp_ce=exp_ce+1; end
  for (w=0; w<4; w=w+1) begin rd(w, 288'd1 << (w*72+71)); exp_ce=exp_ce+1; end
  repeat(8) @(negedge clk);
  if (got!=N+exp_ce || nce!=exp_ce || nue!=0 || lfault) begin $display("FATAL CE phase got=%0d ce=%0d/%0d ue=%0d", got-N, nce, exp_ce, nue); $fatal(1); end
  $display("PASS CE: %0d single-bit side-band/data upsets corrected and counted", exp_ce);
  rd(5, (288'd1 << 3) | (288'd1 << 40));
  repeat(8) @(negedge clk);
  if (nue!=1 || !lfault || got!=N+exp_ce || pfault) begin $display("FATAL UE phase ue=%0d fault=%0d", nue, lfault); $fatal(1); end
  $display("PASS UE: double-bit upset quarantined (no delivery, sticky fault)");
  $display("PASS_ALL qfd_hbm_ecc_provider");
  $finish;
 end
 initial begin #200000; $display("FATAL watchdog"); $fatal(1); end
endmodule
