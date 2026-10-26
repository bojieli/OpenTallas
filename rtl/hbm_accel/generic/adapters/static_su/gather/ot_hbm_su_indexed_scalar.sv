`timescale 1ns/1ps
`default_nettype none
// Compiler reserves all RG0/WG0 bank slots throughout this fixed transaction.
// Index values select data addresses, never ownership, timing or arbitration.
// Requests/returns are registered pins. READ_SAMPLE is the issue-pin to engine
// sample distance, including actual bank+tap registers. WRITE_COMMIT similarly
// covers the write pin to real SRAM commit. Faults latch and never defer slots.
module ot_hbm_su_indexed_scalar #(
 parameter integer READ_SAMPLE=11,WRITE_COMMIT=8,MUT_INDEX=0,MUT_ADDRESS=0,MUT_PHASE=0
)(input wire clk,rst_n,start,
 input wire[23:0]index_word,score_base,score_limit,dest_word,
 input wire[23:0]dyn_mul,
 input wire[32*257-1:0]rr,
 output reg[32*17-1:0]rq,output reg[32*281-1:0]wq,
 output reg busy,done,fault);
 localparam SCORE_ISSUE=READ_SAMPLE+2;
 localparam SCORE_SAMPLE=SCORE_ISSUE+READ_SAMPLE;
 localparam WRITE_ISSUE=SCORE_SAMPLE+2;
 localparam END_EDGE=WRITE_ISSUE+WRITE_COMMIT;
 reg[15:0]phase;
 reg[23:0]ix,base,limit,dst,mul,score_address;
 reg[31:0]index_value,value;
 wire[55:0]product=56'(index_value)*56'(mul)+56'(base);
 integer k;reg[15:0]sector;reg[4:0]bank;reg[31:0]selected;
 function automatic[4:0]bank_of(input[23:0]word_address);
 bank_of={word_address[17:16],word_address[5:3]};endfunction
 initial if(READ_SAMPLE<7||WRITE_COMMIT<4||END_EDGE>65535)$fatal(1,"bad fixed latency");
 always @(posedge clk)begin
  if(!rst_n)begin rq<=0;wq<=0;busy<=0;done<=0;fault<=0;phase<=0;end
  else begin
   rq<=0;wq<=0;done<=0;
   if(start)begin
    if(busy)fault<=1;
    else begin
     ix<=index_word;base<=score_base;limit<=score_limit;dst<=dest_word;mul<=dyn_mul;
     busy<=1;phase<=0;
     if(index_word>=262144||score_base>=score_limit||score_limit>262144||dest_word>=262144||dyn_mul!=1)fault<=1;
    end
   end
   if(busy)begin
    phase<=phase+1;
    // Every unsolicited or missing bank response is an identity/phase fault.
    for(k=0;k<32;k=k+1)begin
     if(rr[k*257+256]!==((phase==READ_SAMPLE&&k==bank_of(ix))||
          (phase==SCORE_SAMPLE&&k==bank_of(score_address))))fault<=1;
    end
    if(phase==0)begin
     sector=ix[18:3];bank=bank_of(ix);
     rq[bank*17+:17]<={1'b1,sector};
    end
    if(phase==READ_SAMPLE+MUT_PHASE)begin
     selected=rr[bank_of(ix)*257+ix[2:0]*32+:32];
     index_value<=selected^(MUT_INDEX!=0?32'd1:32'd0);
    end
    if(phase==READ_SAMPLE+1)begin
     score_address<=product[23:0]^(MUT_ADDRESS!=0?24'd8:24'd0);
     if(product>=56'(limit)||product<56'(base)||product>=262144)fault<=1;
    end
    if(phase==SCORE_ISSUE)begin
     sector=score_address[18:3];bank=bank_of(score_address);
     rq[bank*17+:17]<={1'b1,sector};
    end
    if(phase==SCORE_SAMPLE)value<=rr[bank_of(score_address)*257+score_address[2:0]*32+:32];
    if(phase==WRITE_ISSUE)begin
     sector=dst[18:3];bank=bank_of(dst);
     wq[bank*281+:281]<={1'b1,sector,{8{value}},8'd1<<dst[2:0]};
    end
    if(phase==END_EDGE)begin busy<=0;done<=1;end
   end
  end
 end
endmodule
`default_nettype wire
