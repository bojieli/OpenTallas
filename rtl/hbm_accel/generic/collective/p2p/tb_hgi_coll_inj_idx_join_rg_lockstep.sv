`timescale 1ns/1ps
// Lockstep: ot_hgi_coll_inj_idx_join_rg vs the original ot_hgi_coll_inj_idx_join, random legal AND illegal traffic
// (partial emits, duplicate slots, stale reads, bad hi addresses), inj_d and fault compared every edge incl. a mid-run
// reset. MUT=1: clk_r1 of the rg arrives SKEW late (a mis-bound regional root) -> must FAIL; MUT=2: rg select mutant 3.
module tb_hgi_coll_inj_idx_join_rg_lockstep;
 parameter integer MUT=0;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 wire clk_r1; generate if(MUT==1) begin:g_s assign #(1.2) clk_r1=clk; end else begin:g_n assign clk_r1=clk; end endgenerate
 reg [1:0] inj_rd=0; reg [31:0] inj_idx=0; reg [159:0] inj_addr=0; reg [1023:0] su=0; reg [3:0] tx_v=0; reg [2179:0] tx=0;
 wire [1023:0] a_d, b_d; wire a_f, b_f;
 ot_hgi_coll_inj_idx_join #(.INJLAT(12)) ref_(.clk(clk),.rst_n(rst_n),.inj_rd(inj_rd),.inj_idx(inj_idx),.inj_addr(inj_addr),
  .su_inj_d(su),.idx_tx_v(tx_v),.idx_tx(tx),.inj_d(a_d),.fault(a_f));
 ot_hgi_coll_inj_idx_join_rg_flat #(.INJLAT(12),.MUT(MUT==2?3:0)) dut(.clk_r0(clk),.clk_r1(clk_r1),.rst_n(rst_n),.inj_rd(inj_rd),
  .inj_idx(inj_idx),.inj_addr(inj_addr),.su_inj_d(su),.idx_tx_v(tx_v),.idx_tx(tx),.inj_d(b_d),.fault(b_f));
 integer n, errors=0, checks=0, k, faults=0;
 reg [39:0] lo;
 initial begin
  repeat(3) @(negedge clk); rst_n=1;
  for(n=0;n<30000;n=n+1) begin
   @(negedge clk);
   if(n==15000) begin rst_n=0; @(negedge clk); rst_n=1; end
   for(k=0;k<1024;k=k+32) su[k+:32]=$urandom;
   for(k=0;k<2180;k=k+1) tx[k]=$urandom;
   tx_v = ($urandom%8==0) ? $urandom : (($urandom%3==0) ? 4'hf : 4'h0);
   for(k=0;k<4;k=k+1) begin tx[k*545+544]=($urandom%50)!=0; if(($urandom%20)!=0) tx[k*545+512+:3]=k+4*(n%2); end
   inj_rd=$urandom; inj_idx=$urandom & 32'h00070007;
   for(k=0;k<2;k=k+1) begin lo={($urandom%2==0),7'd0,32'($urandom)}; inj_addr[80*k+:40]=lo; inj_addr[80*k+40+:40]=($urandom%30==0)?lo:lo+40'd8; end
   #0.5;
   checks=checks+1; faults=faults+a_f;
   if(a_d!==b_d || a_f!==b_f) begin errors=errors+1; if(errors<4) $display("mismatch n=%0d d=%0d f=%0d/%0d",n,a_d!==b_d,a_f,b_f); end
  end
  if(errors) begin $display("CIJ_RG_LOCKSTEP FAIL checks=%0d errors=%0d",checks,errors); $fatal(1); end
  $display("CIJ_RG_LOCKSTEP PASS checks=%0d fault_edges=%0d",checks,faults); $finish;
 end
endmodule
