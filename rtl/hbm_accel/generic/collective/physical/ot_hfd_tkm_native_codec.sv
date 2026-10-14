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
 output wire w_rdy,output wire[544:0]packet,input wire packet_rdy
);
 reg packet_valid;reg[543:0]packet_payload;assign packet={packet_valid,packet_payload};
 reg[39:0]addr[0:1];reg[15:0]mask[0:1];reg[511:0]data[0:1];
 reg[1:0]count;reg head,tail,header_sent;
 wire take_in=w_v&&w_rdy;
 wire take_out=count!=0&&(!packet[544]||packet_rdy);
 wire retire=take_out&&header_sent;
 assign w_rdy=count<2;
 always @(posedge clk)if(take_in)begin addr[tail]<=w_addr;mask[tail]<=w_mask;data[tail]<=w_data;end
 always @(posedge clk)if(take_out)begin
  if(!header_sent)packet_payload<={1'b1,31'd0,456'd0,mask[head],addr[head]};
  else packet_payload<={1'b0,31'd0,data[head]};
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin packet_valid<=0;count<=0;head<=0;tail<=0;header_sent<=0;end
  else begin
   count<=count+2'(take_in)-2'(retire);
   if(take_in)tail<=!tail;
   if(packet_valid&&packet_rdy)packet_valid<=0;
   if(take_out)begin
    packet_valid<=1;
    if(!header_sent)begin header_sent<=1;end
    else begin header_sent<=0;head<=!head;end
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
// Proposed credit control word: {commit=0,valid=0,index=62,data32}.
// data[3:0] is DEL reservation bitmap; data[7:4] grants whole-write leases;
// data[8] acknowledges one actual sink write. A lease covers both 545b flits.
// Source completion waits acknowledgements, including writes still inside TX.
module ot_hfd_tkm_write_credit_tx # (parameter integer MUT=0)(
 input wire clk,rst_n,input wire[39:0]control,
 input wire w_v,input wire[39:0]w_addr,input wire[15:0]w_mask,input wire[511:0]w_data,
 output wire w_rdy,output wire[544:0]packet,
 input wire core_done,core_busy,core_fault,
 output reg done,output wire busy,output reg fault,
 output reg[15:0]outstanding,output reg[4:0]leases
);
 reg[39:0]control_pin;reg finishing;wire queue_rdy;
 wire ctl=(control_pin[39:38]==0)&&(control_pin[37:32]==62);
 wire[3:0]grant=ctl?control_pin[7:4]:4'd0;
 wire ack=ctl&&control_pin[8];
 wire admitted=w_v&&w_rdy;
 assign w_rdy=queue_rdy&&(leases!=0)&&!finishing;
 assign busy=core_busy||finishing||(outstanding!=0);
 ot_hfd_tkm_write_tx u_tx(.clk(clk),.rst_n(rst_n),.w_v(admitted),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),.w_rdy(queue_rdy),.packet(packet),.packet_rdy(1'b1));
 always @(posedge clk)control_pin<=control;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin done<=0;finishing<=0;fault<=0;outstanding<=0;leases<=0;end
  else begin
   done<=0;
   leases<=leases+5'(grant)-5'(admitted);
   outstanding<=outstanding+16'(admitted)-16'(ack);
   if((ack&&outstanding==0)||((6'(leases)+6'(grant))>8))fault<=1;
   if(core_fault)fault<=1;
   if(core_done)finishing<=1;
   // MUT1 demonstrates why local TX acceptance cannot stand for sink completion.
   if(finishing&&((MUT==1)||(outstanding==0&&!admitted)))begin done<=1;finishing<=0;end
  end
endmodule
// Bounded native destination. There is no ready sideband on native545: the
// source spends one granted queue slot before transmitting header and data.
module ot_hfd_tkm_write_credit_rx(
 input wire clk,rst_n,input wire[544:0]packet,
 output wire w_v,output wire[39:0]w_addr,output wire[15:0]w_mask,output wire[511:0]w_data,
 input wire w_rdy,output reg[3:0]grant,output reg ack,fault
);
 reg[544:0]packet_pin;reg header_valid;reg[39:0]addr;reg[15:0]mask;
 reg[39:0]qa[0:7];reg[15:0]qm[0:7];reg[511:0]qd[0:7];reg[3:0]count;reg[2:0]head,tail;
 reg initial_grant;
 wire pop=(count!=0)&&w_rdy;
 wire push=packet_pin[544]&&!packet_pin[543]&&header_valid;
 assign w_v=count!=0;assign w_addr=qa[head];assign w_mask=qm[head];assign w_data=qd[head];
 always @(posedge clk)begin
  packet_pin<=packet;
  if(push)begin qa[tail]<=addr;qm[tail]<=mask;qd[tail]<=packet_pin[511:0];end
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin header_valid<=0;addr<=0;mask<=0;count<=0;head<=0;tail<=0;grant<=0;ack<=0;fault<=0;initial_grant<=1;end
  else begin
   grant<=0;ack<=0;
   if(initial_grant)begin grant<=8;initial_grant<=0;end
   if(pop)begin head<=head+1'b1;ack<=1;grant<=1;end
   if(push)begin tail<=tail+1'b1;if(count==8&&!pop)fault<=1;end
   count<=count+4'(push)-4'(pop);
   if(packet_pin[544])begin
    if(packet_pin[543])begin
     if(header_valid)fault<=1;
     addr<=packet_pin[39:0];mask<=packet_pin[55:40];header_valid<=1;
    end else begin if(!header_valid)fault<=1;header_valid<=0;end
   end
  end
endmodule
// Proposed native40 reservation receiver. The sender must bind this two-edge
// pin-to-publication latency to the actual native545 DEL flight; no guessed
// DEL-valid delay is embedded here and no packet payload bit is repurposed.
module ot_hfd_tkm_reservation_rx #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire[39:0]control,output reg[3:0]del_reserve
);
 reg[39:0]control_pin;
 always @(posedge clk)control_pin<=control;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)del_reserve<=0;
  else if(control_pin[39:38]==0&&control_pin[37:32]==62)
   del_reserve<=(MUT==1)?{control_pin[2:0],control_pin[3]}:control_pin[3:0];
  else del_reserve<=0;
endmodule
