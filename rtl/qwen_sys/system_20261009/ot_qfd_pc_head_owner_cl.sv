`timescale 1ns/1ps
// drive-0158 dual-track "-cl" of ot_qfd_pc_head_owner (REVIEW_20261009 Q6 + addendum 02:35; templates D + S4 removal).
// Failure fixed: qfd_pc_head_owner-0cce9d18f EARLY_FAIL_SETUP TT -683: input->out ack_data[36] -> ce (-746) and
// -> head_v (-568): every output was gated by the same-cycle fail decode of the ack inputs (input->output, no flop).
// Changes (function, payload format, ports and the SECDED72 x 6 SRAM word unchanged):
//  * REGISTERED OUTPUTS: head_v / credit_return / ce are gated by the registered poison only (ce from the decoder's
//    output registers); fault = poison (a
//    failure is reported 1 edge after its cause, +1 status cycle; the state already stops updating in the cause cycle).
//  * Q6 / S4: the triplicated pointer/count/ordinal/head/half-owner copies and the "disagreement" mirror check are
//    removed (one copy). SECDED stays on the SRAM-resident payload only.  ID64 is kept as the interface carries it
//    (dropping it changes the ack producer's port; owner decision, listed in review_queue/drive-0158.md).
module ot_qfd_pc_head_owner_cl #(parameter integer ENABLE=0,PC=0,MUT_ECC=0)(
 input wire clk,rst_n,input wire in_v,input wire [303:0] in_payload,
 input wire [2:0] ack_v,input wire [212:0] ack_data,
 output wire head_v,output wire [303:0] head_payload,output wire [63:0] head_id,
 output wire credit_return,output wire fault,output wire ce
);
 reg [431:0] mem[0:15];
 reg [3:0] wp[0:0],rp[0:0];
 reg [4:0] count[0:0];
 reg [63:0] ordinal[0:0],hid[0:0];
 reg [303:0] hp[0:0];
 reg [1:0] done[0:0];
 reg hv[0:0],loading[0:0],enc_v[0:0],raw_v[0:0],cr[0:0],poisoned[0:0];
 wire [383:0] encoded_input={16'd0,ordinal[0],in_payload};wire[431:0]encoded;
 wire [383:0]decoded;wire[5:0]dec_v,dec_ce,dec_ue;
 reg[431:0]raw;
 genvar s;generate for(s=0;s<6;s=s+1)begin:g_ecc
  ot_secded_enc #(.K(64),.R(8),.MUT(MUT_ECC)) u_enc(.clk(clk),.d(encoded_input[s*64+:64]),.q(encoded[s*72+:72]));
  ot_secded_dec #(.K(64),.R(8)) u_dec(.clk(clk),.rst_n(rst_n),.v(raw_v[0]),.w(raw[s*72+:72]),
    .ov(dec_v[s]),.d(decoded[s*64+:64]),.ce(dec_ce[s]),.ue(dec_ue[s]),.n_ce(),.n_ue());
 end endgenerate
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
 wire fail=ack_bad||decoder_bad||input_bad;
 wire safe=ENABLE&&!poisoned[0]&&!fail;     // state update gate (input -> register only)
 wire ok=ENABLE&&!poisoned[0];              // output gate (registers only)
 wire take=safe&&in_v;
 wire issue=safe&&!hv[0]&&!loading[0]&&(count[0]>{4'd0,enc_v[0]});
 assign head_v=ok&&hv[0];assign head_payload=hp[0];assign head_id=hid[0];
 assign credit_return=ok&&cr[0];assign fault=poisoned[0];
 assign ce=ok&&(&dec_v)&&(|dec_ce);   // dec ov / ce are decoder registers
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   raw<=0;wp[0]<=0;rp[0]<=0;count[0]<=0;ordinal[0]<=1;hid[0]<=0;hp[0]<=0;done[0]<=0;
   hv[0]<=0;loading[0]<=0;enc_v[0]<=0;raw_v[0]<=0;cr[0]<=0;poisoned[0]<=0;
  end else begin
   if(safe&&enc_v[0])mem[wp[0]-1'b1]<=encoded;
   if(issue)raw<=mem[rp[0]];
   poisoned[0]<=poisoned[0]||(ENABLE&&fail);enc_v[0]<=take;raw_v[0]<=issue;cr[0]<=safe&&retired;
   if(safe)begin
    case({take,retired})2'b10:count[0]<=count[0]+1'b1;2'b01:count[0]<=count[0]-1'b1;default:count[0]<=count[0];endcase
    if(take)begin wp[0]<=wp[0]+1'b1;ordinal[0]<=ordinal[0]+1'b1;end
    if(issue)loading[0]<=1;
    if(&dec_v)begin hp[0]<=decoded[303:0];hid[0]<=decoded[367:304];hv[0]<=1;done[0]<=0;loading[0]<=0;end
    if(hv[0])done[0]<=done[0]|ack_mask;
    if(retired)begin hv[0]<=0;done[0]<=0;rp[0]<=rp[0]+1'b1;end
   end
  end
 end
endmodule
