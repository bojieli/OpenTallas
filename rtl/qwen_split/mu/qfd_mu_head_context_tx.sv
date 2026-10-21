`timescale 1ns/1ps
// Actual recurring filler head contexts. Slots/users come from the sole paired OVL calendar.
// Capture is one edge; record producer is one edge. Transport/parent landing ages are separate.
module qfd_mu_head_context_tx(
 input wire ck,rst_n,
 input wire descriptor_v,input wire[58:0]descriptor_tag,input wire[1:0]descriptor_generation,
 input wire send_slot,input wire[1:0]send_user,
 input wire program_ready,installed_fusedcap,input wire[15:0]program_epoch,input wire[63:0]program_digest,
 output reg tx_v,output reg[547:0]tx_record,output reg fault
);
 reg[3:0]held;reg[58:0]tag[0:3];reg[1:0]generation[0:3];
 wire[1:0]owner=descriptor_tag[44:43];
 wire source_ok=held[send_user]&&program_ready&&installed_fusedcap&&!fault;
 wire[511:0]data={370'd0,program_digest,program_epoch,installed_fusedcap,generation[send_user],tag[send_user]};
 integer u;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin
   held<=0;tx_v<=0;tx_record<=0;fault<=0;
   for(u=0;u<4;u=u+1)begin tag[u]<=0;generation[u]<=0;end
  end else begin
   tx_v<=send_slot&&source_ok;
   if(descriptor_v)begin
    if(held[owner]||descriptor_tag[42:37]!=0||descriptor_tag[5:0]!=0||descriptor_tag[36:19]>=151936)fault<=1;
    tag[owner]<=descriptor_tag;generation[owner]<=descriptor_generation;held[owner]<=1;
   end
   if(send_slot)begin
    tx_record<={5'd0,4'd12,6'd63,tag[send_user][58:43],5'd0,data};
    held[send_user]<=0;
    if(source_ok!==1'b1||(descriptor_v&&owner==send_user))fault<=1;
   end
  end
endmodule
