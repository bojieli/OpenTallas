`timescale 1ns/1ps
// Finite protected framing. Full73 owner stays live until matching downstream
// data drain, finish and persistent completion handshakes. Cold POR cancels;
// warm request drains existing ownership, without clearing state or payload.
module ot_hbm_compute_frame1024 #(parameter integer ENABLE=0,IW=2083,OW=2081)(
 input wire clk,por_n,source_permit,warm_req,output wire warm_ack,
 input wire rx_v,output wire rx_r,input wire [1023:0] rx_d,
 input wire owner_valid,input wire [72:0] rx_owner,input wire rx_first,rx_last,
 output wire tx_v,input wire tx_r,output wire [1023:0] tx_d,
 output wire [72:0] tx_owner,output wire [3:0] tx_index,output wire tx_last,
 output wire finish_v,input wire finish_r,input wire [72:0] finish_owner,
 output wire complete_v,input wire complete_r,input wire [72:0] complete_owner,
 output wire [72:0] retained_owner,
 output wire child_req_v,input wire child_req_r,output wire [IW-1:0] child_req_d,
 input wire child_rsp_v,output wire child_rsp_r,input wire [OW-1:0] child_rsp_d,
 input wire child_fault,output wire fault
);
 generate if(!ENABLE)begin:g_off
  assign {warm_ack,rx_r,tx_v,tx_d,tx_owner,tx_index,tx_last,finish_v,complete_v,
          retained_owner,child_req_v,child_req_d,child_rsp_r,fault}=0;
 end else begin:g_on
  localparam integer RI=(IW+1023)/1024,RO=(OW+1023)/1024;
  localparam integer B=IW+80,W=(B+63)/64;
  localparam [2:0] IDLE=0,BUILD=1,ISSUE=2,RETURN=3,FINISH=4,COMPLETE=5;
  wire [W*64-1:0] q;reg [W*64-1:0] d;reg load;
  wire normal,bank_fault,repairing;
  wire [2:0] phase=q[IW+77+:3];wire [3:0] idx=q[IW+73+:4];
  wire [72:0] owner=q[IW+:73];wire [IW-1:0] partial=q[0+:IW];
  assign fault=bank_fault|child_fault;
  wire permission=normal&&!fault;
  assign rx_r=permission&&source_permit&&((phase==IDLE&&!warm_req)||phase==BUILD);
  wire rx_take=rx_v&&rx_r;
  wire bad_rx=rx_take&&(!owner_valid||
      (phase==IDLE?(!rx_first||(rx_last!=(RI==1))):
       (rx_first||rx_owner!=owner||rx_last!=(idx==RI-1))));
  assign child_req_v=permission&&phase==ISSUE;
  assign child_req_d=partial;
  assign tx_v=permission&&phase==RETURN&&child_rsp_v;
  assign tx_d=({{(RO*1024-OW){1'b0}},child_rsp_d}>>(1024*idx));
  assign tx_owner=owner;assign retained_owner=owner;assign tx_index=idx;
  assign tx_last=idx==RO-1;
  wire tx_take=tx_v&&tx_r;
  assign child_rsp_r=tx_take&&tx_last;
  assign finish_v=permission&&phase==FINISH;
  assign complete_v=permission&&phase==COMPLETE;
  assign warm_ack=permission&&warm_req&&phase==IDLE;
  wire bad_state=normal&&(phase>COMPLETE||
       (phase==BUILD&&idx>=RI)||(phase==RETURN&&idx>=RO));
  always @*begin
   d=q;load=0;
   if(rx_take&&!bad_rx)begin
    if(phase==IDLE)begin
     d=0;d[IW+:73]=rx_owner;
     for(integer j=0;j<IW&&j<1024;j=j+1)d[j]=rx_d[j];
     d[IW+73+:4]=RI==1?0:1;d[IW+77+:3]=RI==1?ISSUE:BUILD;
    end else begin
     for(integer j=0;j<IW;j=j+1)
      if(j>=1024*idx&&j<1024*(idx+1))d[j]=rx_d[j-1024*idx];
     d[IW+73+:4]=rx_last?0:idx+1'b1;d[IW+77+:3]=rx_last?ISSUE:BUILD;
    end
    load=1;
   end else if(child_req_v&&child_req_r)begin
    d[IW+77+:3]=RETURN;d[IW+73+:4]=0;load=1;
   end else if(tx_take)begin
    d[IW+73+:4]=tx_last?0:idx+1'b1;
    d[IW+77+:3]=tx_last?FINISH:RETURN;load=1;
   end else if(finish_v&&finish_r)begin d[IW+77+:3]=COMPLETE;load=1;
   end else if(complete_v&&complete_r)begin d=0;load=1;end
  end
  ot_hbm_w2_protected_bank #(.WORDS(W)) u_frame(
   .clk(clk),.por_n(por_n),.load(load&&permission),.load_encoded(1'b0),
   .fatal(bad_rx||bad_state||(finish_v&&finish_r&&finish_owner!=owner)||
          (complete_v&&complete_r&&complete_owner!=owner)),.d(d),.encoded_d({W*72{1'b0}}),
   .q(q),.encoded_q(),.normal(normal),.fault(bank_fault),.repairing(repairing));
 end endgenerate
endmodule
