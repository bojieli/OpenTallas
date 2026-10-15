`timescale 1ns/1ps
// KVN-only fixed-slot transport. Each seat retains the actual producer's
// TAG59 and HOSTgen2 with its word; a future context cannot relabel queued data.
// Occupancy checks expose a malformed compiled schedule without rescheduling.
module qfd_kvn_static_transport(
 input wire ck,rst_n,
 input wire word_v,input wire[10:0]word_tag,input wire[511:0]word_data,
 input wire[58:0]word_identity,input wire[1:0]word_generation,
 input wire slot_v,
 output reg[523:0]x3,output reg[58:0]x3_identity,output reg[1:0]x3_generation,
 output reg fault
);
 reg[583:0]seat[0:1];reg rp,wp;reg[1:0]n;
 wire pop=slot_v&&n!=0&&!fault;
 wire push=word_v&&(n<2||pop)&&!fault;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin rp<=0;wp<=0;n<=0;x3<=0;x3_identity<=0;x3_generation<=0;fault<=0;end
  else begin
   x3[523]<=pop;
   if((slot_v&&n==0)||(word_v&&!push)||(word_v&&word_tag[10:8]!=2))fault<=1;
   if(push)begin seat[wp]<={word_generation,word_identity,word_tag,word_data};wp<=!wp;end
   if(pop)begin {x3_generation,x3_identity,x3[522:0]}<=seat[rp];rp<=!rp;end
   case({push,pop})2'b10:n<=n+1'b1;2'b01:n<=n-1'b1;default:;endcase
  end
 end
endmodule
