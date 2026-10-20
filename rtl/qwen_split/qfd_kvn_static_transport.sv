`timescale 1ns/1ps
// KVN-only fixed-slot transport. Each seat retains the actual producer's
// TAG59 and HOSTgen2 with its word; a future context cannot relabel queued data.
// Occupancy checks expose a malformed compiled schedule without rescheduling.
module qfd_kvn_static_transport #(parameter integer LOCAL32=0,LOCAL_MUT=0)(
 input wire ck,rst_n,
 input wire word_v,input wire[10:0]word_tag,input wire[511:0]word_data,
 input wire[58:0]word_identity,input wire[1:0]word_generation,
 input wire slot_v,
 input wire[15:0]word_ctl_pub,input wire[3:0]slot_pub,
 output reg[523:0]x3,output reg[58:0]x3_identity,output reg[1:0]x3_generation,
 output reg fault
);
 reg[583:0]seat[0:1];reg rp,wp;reg[1:0]n;
 wire pop=slot_v&&n!=0&&!fault;
 wire push=word_v&&(n<2||pop)&&!fault;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin rp<=0;wp<=0;n<=0;x3[523]<=0;fault<=0;end
  else begin
   x3[523]<=pop;
   if((slot_v&&n==0)||(word_v&&!push)||(word_v&&word_tag[10:8]!=2))fault<=1;
   if(push)wp<=!wp;
   if(pop)rp<=!rp;
   case({push,pop})2'b10:n<=n+1'b1;2'b01:n<=n-1'b1;default:;endcase
  end
 end
 // Fixed 11-bit payload groups each own their pointer, occupancy and fault feedback.
 // The four incoming control publications are captured at the ORIGINAL producer edge.
 generate if(LOCAL32)begin:g_local
  wire[583:0]data_in={word_generation,word_identity,word_tag,word_data};
  wire[583:0]data_out;
  for(genvar g=0;g<54;g=g+1)begin:g_word
   localparam integer LO=11*g,W=(584-LO<11)?584-LO:11,R=g/14;
   (* keep = "true" *) reg lr,lw,lf;
   (* keep = "true" *) reg[1:0]ln;
   reg[W-1:0]s0,s1,out_q;
   wire sv=slot_pub[R],wv=(LOCAL_MUT==2&&g==0)?1'b0:word_ctl_pub[4*R+3];
   wire lp=sv&&ln!=0&&!lf;
   wire lpush=wv&&(ln<2||lp)&&!lf;
   wire rsel=(LOCAL_MUT==1&&g==0)?!lr:lr;
   always @(posedge ck or negedge rst_n)begin
    if(!rst_n)begin lr<=0;lw<=0;lf<=0;ln<=0;out_q<=0;end
    else begin
     if((sv&&ln==0)||(wv&&!lpush)||(wv&&word_ctl_pub[4*R+:3]!=2))lf<=1;
     if(lpush)lw<=!lw;
     if(lp)begin out_q<=rsel?s1:s0;lr<=!lr;end
     case({lpush,lp})2'b10:ln<=ln+1'b1;2'b01:ln<=ln-1'b1;default:;endcase
    end
   end
   always @(posedge ck)begin
    if(rst_n&&lpush&&!lw)s0<=data_in[LO+:W];
    if(rst_n&&lpush&&lw)s1<=data_in[LO+:W];
   end
   assign data_out[LO+:W]=out_q;
  end
  assign {x3_generation,x3_identity,x3[522:0]}=data_out;
 end else begin:g_legacy
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin x3[522:0]<=0;x3_identity<=0;x3_generation<=0;end
   else if(pop){x3_generation,x3_identity,x3[522:0]}<=seat[rp];
  end
  always @(posedge ck)if(rst_n&&push)seat[wp]<={word_generation,word_identity,word_tag,word_data};
 end endgenerate
endmodule
