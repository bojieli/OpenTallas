`timescale 1ns/1ps
module tb_hgi_att_scaled;
 `include "sizes.svh"
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,v=0;reg[1023:0] x='x;
 wire vo,vold,fault,fold;wire[511:0] y,yold;wire[264:0] packed_word,off_word;
 reg[1023:0] im[0:N-1];reg[776:0] em[0:N-1];reg[31:0] sm[0:N-1];
 wire[511:0] decoded;wire[31:0] deq_fault;
 ot_hgi_fp4qdq #(.PACKED(1)) u(clk,rst_n,v,x,vo,y,fault,packed_word);
 ot_hgi_fp4qdq old(clk,rst_n,v,x,vold,yold,fold,off_word);
 genvar g;
 generate for(g=0;g<32;g=g+1)begin:d
  wire[17:0] elem={1'b0,packed_word[264],4'd0,packed_word[4*g+:4],packed_word[128+8*(g/16)+:8]};
  ot_hdc_v41x_attn_deq deq(elem,decoded[16*g+:16],deq_fault[g]);
 end endgenerate
 reg ld=0,iv=0;reg[143:0] ib=0;wire ov;wire[31:0] oy;wire oflt;
 ot_hdc_v41x_attn_tile #(.H(1),.TD(8)) tile(
  .clk(clk),.rst_n(rst_n),.ld_v(ld),.ld_mode(1'b0),.ld_bank(2'd0),.ld_grp(8'd0),
  .ld_w({8{16'h3f80}}),.ld_w2v(1'b0),.iv(iv),.ibank(2'd0),.ib(ib),.ov(ov),.oy(oy),.oflt(oflt));
 integer i,j,cycle=0,t0,producer_latency;
 always @(posedge clk)cycle<=cycle+1;
 initial begin
  $readmemh("input.mem",im);$readmemh("expected.mem",em);$readmemh("sum.mem",sm);
  repeat(3)@(negedge clk);rst_n=1;ld=1;@(negedge clk);ld=0;repeat(3)@(negedge clk);
  for(i=0;i<N;i=i+1)begin
   x=im[i];v=1;t0=cycle;@(negedge clk);v=0;x='x;
   while(!vo)@(negedge clk);
   producer_latency=cycle-t0;
   if(!vold || y!==yold || fault!==fold || fault || y!==em[i][776:265] || packed_word!==em[i][264:0] ||
      decoded!==y || deq_fault!==0 || off_word!==0) $fatal(1,"producer/dequant block%0d mismatch",i);
   if(i==0)$display("counterexample exact BF16=%h,%h; producerlatency=%0d",decoded[15:0],decoded[31:16],producer_latency);
   for(j=0;j<8;j=j+1) ib[18*j+:18]={1'b0,packed_word[264],4'd0,packed_word[4*j+:4],packed_word[135:128]};
`ifdef MUT_SCALE
   ib[7:0]=8'h38;
`endif
   iv=1;@(negedge clk);iv=0;
   while(!ov)@(negedge clk);
   if(oflt || oy!==sm[i])$fatal(1,"actualchunk8 block%0d got%h expected%h",i,oy,sm[i]);
   @(negedge clk);
  end
  $display("ATT_SCALED PASS %0d blocks producer/dequant/actualchunk8",N);$finish;
 end
endmodule
