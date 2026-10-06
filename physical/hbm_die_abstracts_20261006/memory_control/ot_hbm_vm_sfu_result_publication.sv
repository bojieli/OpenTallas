`timescale 1ps/1fs
`default_nettype none
// Default OFF. Actual SFU64 result ABI is2081b: {tag32,error1,data2048}.
// Hold both data beats until the actual tail validates tag/error/full73.
// Publish through the existing VM parent; only its real SRAM readback ACKs
// authorize completion. No new VM, arithmetic, private provider, or clock.
// Prebuild: sfu_result_publication_prebuild.json, composed existing models.
module ot_hbm_vm_sfu_result_publication #(parameter integer ENABLE=0)(
 input wire clk_sm,por_n,warm_req,output wire warm_ack,
 input wire enroll_v,output wire enroll_r,
 input wire [72:0] enroll_frame,input wire [31:0] enroll_base_word,enroll_tag,
 input wire owner_valid,input wire [72:0] owner_frame,
 input wire rx_v,output wire rx_r,input wire [1023:0] rx_data,
 input wire [72:0] rx_frame,input wire [3:0] rx_index,input wire rx_last,
 output wire result_pub_v,input wire result_pub_r,
 output wire [1023:0] result_pub_data,output wire [72:0] result_pub_frame,
 output wire [31:0] result_pub_addr,
 input wire result_ACK_v,output wire result_ACK_r,
 input wire [72:0] result_ACK_frame,input wire [31:0] result_ACK_addr,
 output wire publication_done,output wire complete_v,input wire complete_r,
 output wire [72:0] complete_frame,output wire [31:0] complete_tag,
 output wire retained,drained,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
 assign warm_ack=0;assign enroll_r=0;assign rx_r=0;assign result_pub_v=0;
 assign result_pub_data=0;assign result_pub_frame=0;assign result_pub_addr=0;
 assign result_ACK_r=0;assign publication_done=0;assign complete_v=0;
 assign complete_frame=0;assign complete_tag=0;assign retained=0;assign drained=1;assign fault=0;
 end else begin:on
 localparam [3:0] IDLE=0,RX0=1,RX1=2,TAIL=3,PUB0=4,ACK0=5,PUB1=6,ACK1=7,DONE=8,FAIL=15;
 reg [71:0] meta_code[0:2],data_code[0:31];
 wire [191:0] meta;wire [2047:0] data;
 wire [2:0] meta_ce,meta_ue;wire [31:0] data_ce,data_ue;
 for(genvar k=0;k<3;k=k+1)begin:context_decode
  wire [65:0] d=decode64(meta_code[k]);
  assign meta[k*64+:64]=d[63:0];assign meta_ce[k]=d[64];assign meta_ue[k]=d[65];
 end
 for(genvar k=0;k<32;k=k+1)begin:payload_decode
  wire [65:0] d=decode64(data_code[k]);
  assign data[k*64+:64]=d[63:0];assign data_ce[k]=d[64];assign data_ue[k]=d[65];
 end
 wire [3:0] phase=meta[140:137];
 wire [31:0] base=meta[104:73],tag=meta[136:105];wire [72:0] frame=meta[72:0];
 wire bad=(|meta_ue)||(phase!=IDLE&&(|data_ue));wire ce=(|meta_ce)||(|data_ce);
 assign fault=bad||phase==FAIL;
 assign drained=phase==IDLE&&!bad&&!ce;
 assign retained=!drained;
 assign warm_ack=warm_req&&drained;
 wire [32:0] end_word={1'b0,enroll_base_word}+33'd64;
 wire shape=enroll_base_word[4:0]==0&&!end_word[32];
 assign enroll_r=drained&&!warm_req&&owner_valid&&owner_frame==enroll_frame&&shape;
 wire receiving=phase==RX0||phase==RX1||phase==TAIL;
 assign rx_r=receiving&&!fault&&!ce;
 wire [3:0] expected_index=phase==RX0?0:phase==RX1?1:2;
 wire rx_match=rx_frame==frame&&rx_index==expected_index&&rx_last==(phase==TAIL);
 wire tail_match=rx_data[1023:33]==0&&rx_data[32:1]==tag&&!rx_data[0];
 assign result_pub_v=(phase==PUB0||phase==PUB1)&&!fault&&!ce;
 assign result_pub_data=phase==PUB1?data[2047:1024]:data[1023:0];
 assign result_pub_frame=frame;
 assign result_pub_addr=base+((phase==PUB1||phase==ACK1)?32'd32:32'd0);
 wire waiting_ACK=phase==ACK0||phase==ACK1;
 wire ACK_match=result_ACK_frame==frame&&result_ACK_addr==result_pub_addr;
 assign result_ACK_r=waiting_ACK&&!fault&&!ce&&ACK_match;
 assign publication_done=phase==DONE&&!fault&&!ce;
 assign complete_v=publication_done;assign complete_frame=frame;assign complete_tag=tag;
 reg [191:0] next_meta;
 always @*begin
  next_meta=meta;
  if(bad)next_meta[140:137]=FAIL;
  else if(!ce)case(phase)
   IDLE:if(enroll_v&&enroll_r)next_meta={51'b0,RX0,enroll_tag,enroll_base_word,enroll_frame};
   RX0,RX1,TAIL:if(rx_v&&rx_r)begin
    if(!rx_match||(phase==TAIL&&!tail_match))next_meta[140:137]=FAIL;
    else next_meta[140:137]=phase==RX0?RX1:phase==RX1?TAIL:PUB0;
   end
   PUB0:if(result_pub_v&&result_pub_r)next_meta[140:137]=ACK0;
   PUB1:if(result_pub_v&&result_pub_r)next_meta[140:137]=ACK1;
   ACK0,ACK1:if(result_ACK_v)begin
    if(!ACK_match)next_meta[140:137]=FAIL;
    else if(result_ACK_r)next_meta[140:137]=phase==ACK0?PUB1:DONE;
   end
   DONE:if(complete_v&&complete_r)next_meta[140:137]=IDLE;
   FAIL:next_meta=meta;
   default:next_meta[140:137]=FAIL;
  endcase
 end
 always @(posedge clk_sm or negedge por_n)begin
  if(!por_n)begin
   for(integer k=0;k<3;k=k+1)meta_code[k]<=encode64(0);
   for(integer k=0;k<32;k=k+1)data_code[k]<=encode64(0);
  end else if(!bad)begin
   for(integer k=0;k<3;k=k+1)meta_code[k]<=encode64(next_meta[k*64+:64]);
   if(rx_v&&rx_r&&rx_match&&(phase==RX0||phase==RX1))
    for(integer k=0;k<16;k=k+1)data_code[(phase==RX1?16:0)+k]<=encode64(rx_data[64*k+:64]);
   else if(ce)for(integer k=0;k<32;k=k+1)data_code[k]<=encode64(data[k*64+:64]);
  end
 end
 end endgenerate
endmodule
`default_nettype wire
