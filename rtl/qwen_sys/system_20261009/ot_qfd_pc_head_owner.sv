`timescale 1ns/1ps
// Per-PC finite decoded-head queue. No raw sector metadata is synthesized:
// the qualified adapter must supply the entire304-bit decoded payload.
// payload={need2,tail_lanes4,tail,isk,sel1_2,sel0_2,loc1_7,loc0_7,tile1_11,tile0_11,data256}.
module ot_qfd_pc_head_owner #(parameter integer ENABLE=0,PC=0,MUT_ECC=0)(
 input wire clk,rst_n,input wire in_v,input wire [303:0] in_payload,
 input wire [2:0] ack_v,input wire [212:0] ack_data,
 output wire head_v,output wire [303:0] head_payload,output wire [63:0] head_id,
 output wire credit_return,output wire fault,output wire ce
);
 reg [431:0] mem[0:15];
 (* keep *) reg [3:0] wp[0:2],rp[0:2];
 (* keep *) reg [4:0] count[0:2];
 (* keep *) reg [63:0] ordinal[0:2],hid[0:2];
 (* keep *) reg [303:0] hp[0:2];
 (* keep *) reg [1:0] done[0:2];
 (* keep *) reg hv[0:2],loading[0:2],enc_v[0:2],raw_v[0:2],cr[0:2],poisoned[0:2];
 wire [383:0] encoded_input={16'd0,ordinal[0],in_payload};wire[431:0]encoded;
 wire [383:0]decoded;wire[5:0]dec_v,dec_ce,dec_ue;
 reg[431:0]raw;
 genvar s;generate for(s=0;s<6;s=s+1)begin:g_ecc
  ot_secded_enc #(.K(64),.R(8),.MUT(MUT_ECC)) u_enc(.clk(clk),.d(encoded_input[s*64+:64]),.q(encoded[s*72+:72]));
  ot_secded_dec #(.K(64),.R(8)) u_dec(.clk(clk),.rst_n(rst_n),.v(raw_v[0]),.w(raw[s*72+:72]),
    .ov(dec_v[s]),.d(decoded[s*64+:64]),.ce(dec_ce[s]),.ue(dec_ue[s]),.n_ce(),.n_ue());
 end endgenerate
 reg disagreement;integer a;
 always @*begin
  disagreement=0;
  for(integer j=1;j<3;j=j+1)
   if(wp[0]!=wp[j]||rp[0]!=rp[j]||count[0]!=count[j]||ordinal[0]!=ordinal[j]||
      hid[0]!=hid[j]||hp[0]!=hp[j]||done[0]!=done[j]||hv[0]!=hv[j]||loading[0]!=loading[j]||
      enc_v[0]!=enc_v[j]||raw_v[0]!=raw_v[j]||cr[0]!=cr[j]||poisoned[0]!=poisoned[j])disagreement=1;
 end
 reg[1:0]ack_mask;reg ack_bad;reg[63:0]ai;reg[4:0]ap;reg[1:0]am;
 always @*begin
  ack_mask=0;ack_bad=0;ai=0;ap=0;am=0;
  for(integer j=0;j<3;j=j+1)if(ack_v[j])begin
   {ai,ap,am}=ack_data[j*71+:71];
   if(ap==PC)begin
    if(!hv[0]||ai!=hid[0]||am==0||(am&~hp[0][303:302])!=0||
       (am&(done[0]|ack_mask))!=0)ack_bad=1;
    ack_mask=ack_mask|am;
   end
  end
 end
 wire retired=hv[0]&&((done[0]|ack_mask)==hp[0][303:302]);
 wire decoder_bad=(|dec_v)&&((dec_v!=6'b111111)||(|dec_ue)||decoded[383:368]!=0||decoded[303:302]==0);
 wire input_bad=in_v&&(count[0]>=16||ordinal[0]==64'hffffffffffffffff||in_payload[303:302]==0);
 wire fail=disagreement||ack_bad||decoder_bad||input_bad;
 wire safe=ENABLE&&!poisoned[0]&&!fail;
 wire take=safe&&in_v;
 // count includes the encoder pipeline reservation. A just-written first
 // word is not read on the same edge as its actual memory commit.
 wire issue=safe&&!hv[0]&&!loading[0]&&(count[0]>{4'd0,enc_v[0]});
 assign head_v=safe&&hv[0];assign head_payload=hp[0];assign head_id=hid[0];
 assign credit_return=safe&&cr[0];assign fault=poisoned[0]||fail;
 assign ce=safe&&(&dec_v)&&(|dec_ce);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   raw<=0;
   for(a=0;a<3;a=a+1)begin wp[a]<=0;rp[a]<=0;count[a]<=0;ordinal[a]<=1;hid[a]<=0;hp[a]<=0;done[a]<=0;
    hv[a]<=0;loading[a]<=0;enc_v[a]<=0;raw_v[a]<=0;cr[a]<=0;poisoned[a]<=0;end
  end else begin
   if(safe&&enc_v[0])mem[wp[0]-1'b1]<=encoded;
   if(issue)raw<=mem[rp[0]];
   for(a=0;a<3;a=a+1)begin
    poisoned[a]<=poisoned[0]||(ENABLE&&fail);enc_v[a]<=take;raw_v[a]<=issue;cr[a]<=safe&&retired;
    if(safe)begin
     case({take,retired})2'b10:count[a]<=count[0]+1'b1;2'b01:count[a]<=count[0]-1'b1;default:count[a]<=count[0];endcase
     if(take)begin wp[a]<=wp[0]+1'b1;ordinal[a]<=ordinal[0]+1'b1;end
     if(issue)loading[a]<=1;
     if(&dec_v)begin hp[a]<=decoded[303:0];hid[a]<=decoded[367:304];hv[a]<=1;done[a]<=0;loading[a]<=0;end
     if(hv[0])done[a]<=done[0]|ack_mask;
     if(retired)begin hv[a]<=0;done[a]<=0;rp[a]<=rp[0]+1'b1;end
    end
   end
  end
 end
endmodule
