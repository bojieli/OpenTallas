`timescale 1ns/1ps
// Notification is observed at the real registered INTx output, or successful
// MSI DMA response. A polling completion explicitly requires no notification.
module qkd_host_notification_observer(
 input wire ck,rst_n,
 input wire cq_v,cq_required,cq_msi,input wire[15:0]cq_client,
 input wire[7:0]cq_slot,input wire[17:0]cq_pos,cq_token,
 input wire irq_pin,msi_commit_v,msi_commit_bad,
 output reg notify_v,notify_required,output reg[15:0]notify_client,
 output reg[7:0]notify_slot,output reg[17:0]notify_pos,notify_token,
 output reg fault);
 reg pending,msi;reg[15:0]client;reg[7:0]slot;reg[17:0]pos,token;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin pending<=0;msi<=0;client<=0;slot<=0;pos<=0;token<=0;
   notify_v<=0;notify_required<=0;notify_client<=0;notify_slot<=0;notify_pos<=0;notify_token<=0;fault<=0;end
  else begin
   notify_v<=0;
   if(msi_commit_bad)fault<=1;
   if(cq_v)begin
    if(pending)fault<=1;
    else if(!cq_required)begin
     notify_v<=1;notify_required<=0;notify_client<=cq_client;notify_slot<=cq_slot;notify_pos<=cq_pos;notify_token<=cq_token;
    end else begin pending<=1;msi<=cq_msi;client<=cq_client;slot<=cq_slot;pos<=cq_pos;token<=cq_token;end
   end
   if(msi_commit_v&&(!pending||!msi))fault<=1;
   if(pending&&((msi&&msi_commit_v)||(!msi&&irq_pin))&&!msi_commit_bad)begin
    pending<=0;notify_v<=1;notify_required<=1;notify_client<=client;notify_slot<=slot;notify_pos<=pos;notify_token<=token;
   end
  end
 end
endmodule

// Physical DMA write pins: AW and W may retire independently. A response is
// evidence only after both handshakes. Idle-high BREADY is not pending traffic.
module qkd_host_dma_write_observer(
 input wire ck,rst_n,aw_v,aw_ready,w_v,w_ready,b_v,b_ready,
 input wire[1:0]b_resp,input wire source_cq_idle,
 output wire drained,output reg fault);
 reg[2:0]addresses,data;
 wire aw=aw_v&&aw_ready,wd=w_v&&w_ready,br=b_v&&b_ready;
 assign drained=source_cq_idle&&addresses==0&&data==0&&!aw_v&&!w_v&&!b_v&&!fault;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin addresses<=0;data<=0;fault<=0;end
  else begin
   if(br&&((addresses==0&&!aw)||(data==0&&!wd)||b_resp!=0))fault<=1;
   if((aw&&!br&&addresses==7)||(wd&&!br&&data==7))fault<=1;
   case({aw,br})2'b10:addresses<=addresses+1'b1;2'b01:if(addresses!=0)addresses<=addresses-1'b1;default:;endcase
   case({wd,br})2'b10:data<=data+1'b1;2'b01:if(data!=0)data<=data-1'b1;default:;endcase
  end
 end
endmodule
