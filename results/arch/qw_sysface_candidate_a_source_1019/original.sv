`timescale 1ns/1ps
module qfd_host_native_context_rx(
 input wire ck,rst_n,receive_slot,rx_v,input wire[547:0]rx_record,
 input wire program_begin_v,program_ready,installed_fusedcap,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,input wire native_active,
 output reg accepted_v,output reg host_epoch_valid,output wire[15:0]host_epoch,
 output reg[58:0]host_tag,output reg[1:0]host_gen,
 output reg host_fusedcap,output reg[15:0]host_image_epoch,output reg[63:0]host_image_digest,
 output reg fault
);
 wire[58:0]tag=rx_record[58:0];
 wire structure_ok=rx_record[547:543]==0&&rx_record[542:539]==12&&rx_record[538:533]==63&&rx_record[516:512]==0&&rx_record[511:142]==0&&tag[42:37]==0&&tag[5:0]==0&&tag[36:19]<151936&&rx_record[532:517]==tag[58:43];
 wire image_ok=program_ready&&rx_record[77:62]==program_epoch&&rx_record[141:78]==program_digest&&rx_record[61]==installed_fusedcap;
 assign host_epoch=host_tag[58:43];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin accepted_v<=0;host_epoch_valid<=0;host_tag<=0;host_gen<=0;host_fusedcap<=0;host_image_epoch<=0;host_image_digest<=0;fault<=0;end
  else begin
   accepted_v<=0;
   if(program_begin_v)begin host_epoch_valid<=0;if(native_active)fault<=1;end
   if(rx_v!==receive_slot)begin fault<=1;host_epoch_valid<=0;end
   if(receive_slot)begin
    if(rx_v!==1'b1||structure_ok!==1'b1||image_ok!==1'b1||native_active!==1'b0||program_begin_v!==1'b0||fault)begin fault<=1;host_epoch_valid<=0;end
    else begin accepted_v<=1;host_epoch_valid<=1;host_tag<=tag;host_gen<=rx_record[60:59];host_fusedcap<=rx_record[61];host_image_epoch<=rx_record[77:62];host_image_digest<=rx_record[141:78];end
   end
   if(host_epoch_valid&&(!program_ready||program_epoch!=host_image_epoch||program_digest!=host_image_digest||installed_fusedcap!=host_fusedcap))begin host_epoch_valid<=0;if(native_active)fault<=1;end
   if(head_context_v&&head_stage>=1&&head_stage<=36)
    if(!host_epoch_valid||!host_fusedcap||head_token!=host_tag[36:19]||head_position>=8192||head_position[12:0]!=host_tag[18:6])fault<=1;
  end
 end
endmodule
