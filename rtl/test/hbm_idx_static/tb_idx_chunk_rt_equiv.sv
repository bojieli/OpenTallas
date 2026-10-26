`timescale 1ns/1ps
// IDX-SCORE (2026-10-17): cycle-exact equivalence of the retimed leaf core ot_hbm_idx_chunk_rt against the systolic
// ot_hbm_idx_chunk_owned_native, same inputs, every output compared on every edge after reset.
// Stimulus (seeded): query loads of 32 heads (8 of them this chunk's: hb=8), key streams with valid/kv/keep patterns,
// realistic E2M1 codes and UE8M0 scales (some refused scales -> faults), query reloads between key streams.
// Key-after-query spacing: GAPK edges between the last query beat and the next key (GAPK=2 is the HARDWARE boundary:
// the key's first dot samples the query written by the beat 2 edges earlier; the engine settle rule demands >= 4).
// Query-after-key spacing: >= GAPQ edges (default LAT_T+FPL*7+..: the compiler drains a frame before the next load).
// PASS: "CHUNK_RT_EQUIV PASS checks N"; any difference prints MISMATCH and fails.
module tb_idx_chunk_rt_equiv;
 localparam integer NB=4,NKT=4,KW=NB*136;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg ql_v=0; reg [7:0] ql_head=0; reg [NB*128-1:0] ql_codes=0; reg [NB*8-1:0] ql_sc=0; reg [15:0] ql_w=0;
 reg k_v=0; reg [NKT-1:0] k_kv=0; reg [NKT*KW-1:0] k_key=0;
 wire a_v,b_v,a_on,b_on; wire [NKT-1:0] a_kv,b_kv,a_f,b_f; wire [NKT*32-1:0] a_s,b_s;
 ot_hbm_idx_chunk_owned_native ref_c(.clk(clk),.clk_hslice({32{clk}}),.rst_n(rst_n),.hb(8'd8),
  .ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.k_v(k_v),.k_kv(k_kv),.k_key(k_key),
  .c_v(a_v),.c_kv(a_kv),.c_sum(a_s),.c_fault(a_f),.online(a_on));
`ifndef QLATE
`define QLATE 0
`endif
 ot_hbm_idx_chunk_rt #(.QLATE(`QLATE)) dut(.clk(clk),.clk_pair({16{clk}}),.rst_n(rst_n),.hb(8'd8),
  .ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.k_v(k_v),.k_kv(k_kv),.k_key(k_key),
  .c_v(b_v),.c_kv(b_kv),.c_sum(b_s),.c_fault(b_f),.online(b_on));
 integer seed=20261017, gapk=2, gapq=120, frames=6, nkeys=200;
 integer checks=0, errs=0, vouts=0, nzs=0, cyc=0;
 function automatic [7:0] scale(input integer s); integer r; begin r=$random(s)&255; scale = (r<8) ? 8'd254 : 8'(118 + (r%20)); end endfunction
 task automatic rnd_codes(output reg [NB*128-1:0] c, output reg [NB*8-1:0] s);
  integer j; begin for(j=0;j<NB*4;j=j+1) c[32*j+:32]=$random(seed); for(j=0;j<NB;j=j+1) s[8*j+:8]=scale(seed); end
 endtask
 reg [NB*128-1:0] tc; reg [NB*8-1:0] ts;
 always @(negedge clk) if (rst_n) begin
  cyc=cyc+1;
  if (a_on!==b_on || a_v!==b_v || (a_v && (a_kv!==b_kv || a_s!==b_s || a_f!==b_f))) begin
   errs=errs+1; if(errs<6) $display("MISMATCH cyc%0d on%b/%b v%b/%b kv%h/%h f%h/%h sum %h / %h",cyc,a_on,b_on,a_v,b_v,a_kv,b_kv,a_f,b_f,a_s,b_s);
  end
  checks=checks+1; if (a_v) begin vouts=vouts+1; if (|a_s) nzs=nzs+1; end
 end
 integer f,h,k,g,j;
 initial begin
  if($value$plusargs("GAPK=%d",gapk))begin end
  if($value$plusargs("GAPQ=%d",gapq))begin end
  if($value$plusargs("SEED=%d",seed))begin end
  repeat(5)@(negedge clk); rst_n=1;
  wait(a_on===1'b1 && b_on===1'b1); repeat(3)@(negedge clk);
  for(f=0;f<frames;f=f+1)begin
   // query load: all 32 heads (only 8..15 belong to this chunk), random order of this chunk's heads in the middle
   for(h=0;h<32;h=h+1)begin
    @(negedge clk); ql_v=1; ql_head=8'((h+5*f)%32); rnd_codes(tc,ts); ql_codes=tc; ql_sc=ts; ql_w=16'($random(seed));
    ql_w[14:7]=8'(120+($random(seed)&7));          // bf16 weight with a sane exponent
   end
   @(negedge clk); ql_v=0;
   repeat(gapk-1)@(negedge clk);                    // first key exactly gapk edges after the last beat
   for(k=0;k<nkeys;k=k+1)begin
    k_v=($random(seed)%8)!=0; k_kv=4'($random(seed)); if(k==0) begin k_v=1; k_kv=4'hf; end
    for(g=0;g<NKT;g=g+1)begin rnd_codes(tc,ts); k_key[g*KW+:KW]={ts,tc}; end
    @(negedge clk);
   end
   k_v=0; k_kv=0;
   repeat(gapq)@(negedge clk);
  end
  repeat(200)@(negedge clk);
  $display("CHUNK_RT_EQUIV checks %0d outputs %0d nonzero_sums %0d errors %0d gapk %0d qlate %0d",checks,vouts,nzs,errs,gapk,`QLATE);
  if(errs==0 && vouts>frames*nkeys/2 && nzs>0) $display("CHUNK_RT_EQUIV PASS checks %0d",checks);
  else $fatal(1,"CHUNK_RT_EQUIV FAIL");
  $finish;
 end
endmodule
