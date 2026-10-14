`timescale 1ns/1ps
// Proposed native-slot format v1. f_cfg is40b {commit,valid,index6,data32}.
// Five configuration words preserve all151 operand bits, followed by commit.
// t_w is545b {valid,header,31'b0,payload512}; header carries full40b address+16b mask.
// Format requires explicit native contract binding; no source field is truncated.
module ot_hfd_tkm_cfg_tx(
 input wire clk,rst_n,start,input wire[11:0]n,input wire[12:0]k,nout,
 input wire[7:0]g,gbase,input wire[15:0]pf,input wire[39:0]obase,rbase,input wire has_r,
 output reg[39:0]packet,output wire busy
);
 reg[159:0]cfg;
 reg[2:0]step;reg active;
 assign busy=active;
 always @(posedge clk)if(start&&!active)
  cfg<={rbase[31:0],obase[31:0],4'd0,rbase[39:32],obase[39:32],n,pf,gbase,g,5'd0,has_r,nout,k};
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin packet<=0;step<=0;active<=0;end
  else begin
   packet<=0;
   if(start&&!active)begin active<=1;step<=0;end
   else if(active)begin
    if(step<5)begin packet<={1'b0,1'b1,6'(step),cfg[32*step+:32]};step<=step+1'b1;end
    else begin packet<={1'b1,1'b0,38'd0};active<=0;end
   end
  end
endmodule
module ot_hfd_tkm_cfg_rx(
 input wire clk,rst_n,input wire[39:0]packet,
 output reg start,fault,output reg[11:0]n,output reg[12:0]k,nout,
 output reg[7:0]g,gbase,output reg[15:0]pf,output reg[39:0]obase,rbase,output reg has_r
);
 reg[39:0]pin_packet;reg[159:0]cfg;reg[4:0]seen;
 always @(posedge clk)pin_packet<=packet;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin start<=0;fault<=0;seen<=0;n<=0;k<=0;nout<=0;g<=0;gbase<=0;pf<=0;obase<=0;rbase<=0;has_r<=0;end
  else begin
   start<=0;
   if(pin_packet[38])begin
    if(pin_packet[37:32]<5)begin cfg[32*pin_packet[37:32]+:32]<=pin_packet[31:0];seen[pin_packet[37:32]]<=1;end
    else fault<=1;
   end
   if(pin_packet[39])begin
    if(seen==5'b11111)begin
     k<=cfg[12:0];nout<=cfg[25:13];has_r<=cfg[26];g<=cfg[39:32];gbase<=cfg[47:40];pf<=cfg[63:48];
     n<=cfg[75:64];obase<={cfg[83:76],cfg[127:96]};rbase<={cfg[91:84],cfg[159:128]};start<=1;
    end else fault<=1;
    seen<=0;
   end
  end
endmodule
// One logical write becomes two flits. Explicit flit ready supports an elastic credit adapter;
// that ready/credit binding is pending for the native40/545/8-slot interface.
module ot_hfd_tkm_write_tx(
 input wire clk,rst_n,w_v,input wire[39:0]w_addr,input wire[15:0]w_mask,input wire[511:0]w_data,
 output wire w_rdy,output reg[544:0]packet,input wire packet_rdy
);
 reg[39:0]addr[0:1];reg[15:0]mask[0:1];reg[511:0]data[0:1];
 reg[1:0]count;reg head,tail,header_sent;
 wire take_in=w_v&&w_rdy;
 wire take_out=count!=0&&(!packet[544]||packet_rdy);
 wire retire=take_out&&header_sent;
 assign w_rdy=count<2;
 always @(posedge clk)if(take_in)begin addr[tail]<=w_addr;mask[tail]<=w_mask;data[tail]<=w_data;end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin packet<=0;count<=0;head<=0;tail<=0;header_sent<=0;end
  else begin
   count<=count+2'(take_in)-2'(retire);
   if(take_in)tail<=!tail;
   if(packet[544]&&packet_rdy)packet<=0;
   if(take_out)begin
    if(!header_sent)begin packet<={1'b1,1'b1,31'd0,456'd0,mask[head],addr[head]};header_sent<=1;end
    else begin packet<={1'b1,1'b0,31'd0,data[head]};header_sent<=0;head<=!head;end
   end
  end

endmodule
module ot_hfd_tkm_write_rx(
 input wire clk,rst_n,input wire[544:0]packet,output wire packet_rdy,
 output reg w_v,output reg[39:0]w_addr,output reg[15:0]w_mask,output reg[511:0]w_data,
 input wire w_rdy,output reg fault
);
 reg header_valid;reg[39:0]addr;reg[15:0]mask;
 // This skid capture is an explicit protocol prototype, not yet a registered native credit seam.
 assign packet_rdy=!w_v||w_rdy;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin header_valid<=0;w_v<=0;w_addr<=0;w_mask<=0;w_data<=0;fault<=0;end
  else begin
   if(w_v&&w_rdy)w_v<=0;
   if(packet[544]&&packet_rdy)begin
    if(packet[543])begin
     if(header_valid)fault<=1;
     addr<=packet[39:0];mask<=packet[55:40];header_valid<=1;
    end else begin
     if(!header_valid)fault<=1;
     else begin w_addr<=addr;w_mask<=mask;w_data<=packet[511:0];w_v<=1;end
     header_valid<=0;
    end
   end
  end
endmodule
