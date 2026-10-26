`timescale 1ns/1ps
`default_nettype none
// H-MTP2/sudma 2026-10-16: P-row (R = P positions) successor of ot_hbm_su_indexed_scalar (that module is unchanged).
// ISA form, no new opcode: an indexed SU.VOP record (route gather A[I] -> O) carries R rows; each descriptor steps by
// its row stride (m = R; stride 0 = broadcast); row r runs with I = index_word + r*i_stride, A window
// [score_base, score_limit) + r*a_stride, O = dest_word + r*o_stride.  Static schedule, compiler-fixed, no queues,
// credits or ready: row r issues its index read on busy phase r, samples it at r+READ_SAMPLE, issues the dependent
// score read at r+SCORE_ISSUE, samples it at r+SCORE_SAMPLE, issues the O write at r+WRITE_ISSUE; done at
// END_EDGE + R - 1 (II = 1).  Index reads (phases 0..R-1) and score reads (13..13+R-1) never share an edge for
// R <= SCORE_ISSUE, so each edge carries at most one RG0 read and one WG0 write (the compiler's reserved slots).
// rows = 1 is edge-for-edge the single-row engine (phase 34 done, same pins).
// Per-row state: row counters / address accumulators (I, A window, O) + per-row 8-bit {bank, word} sample tags.
// MUT (bench only): 1 I row stride dropped; 2 O row stride dropped; 3 score value pipeline one edge short.
module ot_hbm_su_indexed_scalar_rows #(
 parameter integer READ_SAMPLE=11,WRITE_COMMIT=8,MAX_ROWS=8,MUT=0
)(input wire clk,rst_n,start,
 input wire[3:0]rows,
 input wire[23:0]index_word,score_base,score_limit,dest_word,
 input wire[23:0]i_stride,a_stride,o_stride,
 input wire[23:0]dyn_mul,
 input wire[32*257-1:0]rr,
 output reg[32*17-1:0]rq,output reg[32*281-1:0]wq,
 output reg busy,done,fault);
 localparam SCORE_ISSUE=READ_SAMPLE+2;
 localparam SCORE_SAMPLE=SCORE_ISSUE+READ_SAMPLE;
 localparam WRITE_ISSUE=SCORE_SAMPLE+2;
 localparam END_EDGE=WRITE_ISSUE+WRITE_COMMIT;
 initial if(READ_SAMPLE<7||WRITE_COMMIT<4||MAX_ROWS<1||MAX_ROWS>SCORE_ISSUE||MAX_ROWS>15)$fatal(1,"bad fixed latency/rows");
 reg[15:0]phase;
 reg[3:0]nr;
 reg[23:0]ia,ba,la,da,mul,ist,ast,ost,score_address;
 reg[31:0]index_value,v0,v1;
 reg[7:0]itag[0:MAX_ROWS-1],stag[0:MAX_ROWS-1];   // {bank5, word3} of each row's index / score sample
 wire[55:0]product=56'(index_value)*56'(mul)+56'(ba);
 integer k;reg[15:0]sector;reg[4:0]bank;
 function automatic[4:0]bank_of(input[23:0]word_address);
  bank_of={word_address[17:16],word_address[5:3]};endfunction
 // row whose index / score read samples at this phase (R <= SCORE_ISSUE keeps the two windows disjoint)
 wire[15:0]pi=phase-16'(READ_SAMPLE),ps=phase-16'(SCORE_SAMPLE),pa=phase-16'(READ_SAMPLE+1);
 wire[15:0]pq=phase-16'(SCORE_ISSUE),pw=phase-16'(WRITE_ISSUE);
 wire si=busy&&phase>=READ_SAMPLE&&pi<16'(nr);
 wire ss=busy&&phase>=SCORE_SAMPLE&&ps<16'(nr);
 wire sa=busy&&phase>=READ_SAMPLE+1&&pa<16'(nr);
 wire sq=busy&&phase>=SCORE_ISSUE&&pq<16'(nr);
 wire sw=busy&&phase>=WRITE_ISSUE&&pw<16'(nr);
 wire sx=busy&&phase<16'(nr);
 wire[7:0]it=itag[pi[3:0]],st_=stag[ps[3:0]];
 // last-row bounds (strides are non-negative, so the last row bounds every row)
 wire[3:0]rm1=rows-4'd1;
 wire[31:0]ix_last=32'(index_word)+32'(rm1)*32'(i_stride);
 wire[31:0]lim_last=32'(score_limit)+32'(rm1)*32'(a_stride);
 wire[31:0]dst_last=32'(dest_word)+32'(rm1)*32'(o_stride);
 always @(posedge clk)begin
  if(!rst_n)begin rq<=0;wq<=0;busy<=0;done<=0;fault<=0;phase<=0;nr<=0;end
  else begin
   rq<=0;wq<=0;done<=0;
   if(start)begin
    if(busy)fault<=1;
    else begin
     ia<=index_word;ba<=score_base;la<=score_limit;da<=dest_word;mul<=dyn_mul;nr<=rows;
     ist<=i_stride;ast<=a_stride;ost<=o_stride;
     busy<=1;phase<=0;
     if(rows==0||rows>MAX_ROWS||ix_last>=262144||score_base>=score_limit||lim_last>262144||dst_last>=262144||dyn_mul!=1)
      fault<=1;
    end
   end
   if(busy)begin
    phase<=phase+1;
    for(k=0;k<32;k=k+1)begin
     if(rr[k*257+256]!==((si&&k==it[7:3])||(ss&&k==st_[7:3])))fault<=1;
    end
    if(sx)begin                                       // row phase: index read
     sector=ia[18:3];bank=bank_of(ia);
     rq[bank*17+:17]<={1'b1,sector};
     itag[phase[3:0]]<={bank,ia[2:0]};
     if(MUT!=1)ia<=ia+ist;
    end
    if(si)index_value<=rr[it[7:3]*257+it[2:0]*32+:32];
    if(sa)begin                                       // row pa: dependent A address in its own window
     score_address<=product[23:0];
     stag[pa[3:0]]<={bank_of(product[23:0]),product[2:0]};
     if(product>=56'(la)||product<56'(ba)||product>=262144)fault<=1;
     ba<=ba+ast;la<=la+ast;
    end
    if(sq)begin
     sector=score_address[18:3];bank=bank_of(score_address);
     rq[bank*17+:17]<={1'b1,sector};
    end
    if(ss)v0<=rr[st_[7:3]*257+st_[2:0]*32+:32];
    v1<=v0;
    if(sw)begin
     sector=da[18:3];bank=bank_of(da);
     wq[bank*281+:281]<={1'b1,sector,{8{(MUT==3)?v0:v1}},8'd1<<da[2:0]};
     if(MUT!=2)da<=da+ost;
    end
    if(phase==16'(END_EDGE)+16'(nr)-16'd1)begin busy<=0;done<=1;end
   end
  end
 end
endmodule
`default_nettype wire
