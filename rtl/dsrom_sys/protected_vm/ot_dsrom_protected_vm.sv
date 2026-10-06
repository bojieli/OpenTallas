`timescale 1ns/1ps
// Additive minimum WFC + collective native ports. Not the unprotected one-edge fixture.
// One accepted-edge bundle; old-data reads precede xa,xb0..3 writes. Default off.
// Positive row visibility is a protected backend fact, NEVER C8 retirement.
module ot_dsrom_protected_vm #(parameter integer ENABLE=0)(
 input wire fast_clk,slow_clk,cold_n,fast_rst_n,slow_rst_n,
 input wire request_v,output wire request_ready,input wire [46:0] request_owner,
 input wire [1:0] read_enable,input wire [29:0] read_addr,
 input wire [4:0] write_enable,input wire [74:0] write_addr,
 input wire [2559:0] write_data,input wire [79:0] write_mask,
 output wire reply_v,output wire [46:0] reply_owner,output wire [1023:0] read_data,
 output wire [4:0] row_visible,output wire [74:0] visible_addr,output wire [79:0] visible_mask,
 output wire corrected,
 input wire consume_v,input wire [46:0] consume_owner,input wire allcopies_fenced,
 output wire port_retired,output wire pending,quarantined,fault,initializing
);
 import ot_dsrom_vm_pkg::*;
 generate if(ENABLE!=0)begin:g_live
  request_t source_packet,source_check;
  reply_t held_reply,held_check,decoded_reply;
  reg [31:0] serial,serial_check;reg exhausted,exhausted_check;
  reg debt,debt_check,launch,launch_check,received,received_check,acked,acked_check;
  reg poison,poison_check,retired;
  reg backend_fault0,backend_fault1,init0,init1;
  wire [2:0] transport_fault;
  wire bad=source_packet!=~source_check||held_reply!=~held_check||serial!=~serial_check||exhausted!=~exhausted_check||
   debt!=~debt_check||launch!=~launch_check||received!=~received_check||acked!=~acked_check||poison!=~poison_check;
  assign fault=bad||poison||backend_fault1||(|transport_fault);assign quarantined=fault&&debt;
  assign pending=debt;assign port_retired=retired;assign initializing=init1;
  wire [REQ_CODE-1:0] encoded_request;wire [REQ_BITS-1:0] unused_req;
  wire unused_req_ce,unused_req_ue;
  ot_dsrom_vm_codec #(.BITS(REQ_BITS)) u_req_encode(.raw_in(source_packet),.encoded(encoded_request),
   .coded_in(REQ_CODE'(0)),.decoded(unused_req),.corrected(unused_req_ce),.uncorrectable(unused_req_ue));
  wire req_fifo_ready,req_s_v,req_s_ready;wire [REQ_CODE-1:0] req_s_code;
  ot_dsrom_vm_ratio_fifo #(.W(REQ_CODE),.DEPTH(2)) u_request(
   .wclk(fast_clk),.wrst_n(cold_n&&fast_rst_n),.w_v(launch&&!fault),.w_rdy(req_fifo_ready),.w_d(encoded_request),
   .rclk(slow_clk),.rrst_n(cold_n&&slow_rst_n),.r_v(req_s_v),.r_rdy(req_s_ready),.r_d(req_s_code),.w_live(),.r_live(),.control_fault(transport_fault[0]));
  wire rep_s_v,rep_s_ready,rep_f_v,rep_f_ready;wire [REP_CODE-1:0] rep_s_code,rep_f_code;
  ot_dsrom_vm_ratio_fifo #(.W(REP_CODE),.DEPTH(2)) u_reply(
   .wclk(slow_clk),.wrst_n(cold_n&&slow_rst_n),.w_v(rep_s_v),.w_rdy(rep_s_ready),.w_d(rep_s_code),
   .rclk(fast_clk),.rrst_n(cold_n&&fast_rst_n),.r_v(rep_f_v),.r_rdy(rep_f_ready),.r_d(rep_f_code),.w_live(),.r_live(),.control_fault(transport_fault[1]));
  wire rep_ce,rep_ue;wire [REP_CODE-1:0] unused_rep_encoded;
  ot_dsrom_vm_codec #(.BITS(REP_BITS)) u_reply_decode(.raw_in(REP_BITS'(0)),.encoded(unused_rep_encoded),
   .coded_in(rep_f_code),.decoded(decoded_reply),.corrected(rep_ce),.uncorrectable(rep_ue));
  wire [143:0] encoded_receipt;wire [79:0] unused_ack;
  wire unused_ack_ce,unused_ack_ue;
  ot_dsrom_vm_codec #(.BITS(80)) u_receipt_encode(.raw_in({source_packet.ordinal,source_packet.owner,allcopies_fenced}),
   .encoded(encoded_receipt),.coded_in(144'd0),.decoded(unused_ack),.corrected(unused_ack_ce),.uncorrectable(unused_ack_ue));
  wire ack_fifo_ready,ack_s_v,ack_s_ready;wire [143:0] ack_s_code;
  wire consume_ok=consume_v&&debt&&received&&!acked&&!fault&&fast_rst_n&&consume_owner==source_packet.owner&&allcopies_fenced;
  ot_dsrom_vm_ratio_fifo #(.W(144),.DEPTH(2)) u_receipt(
   .wclk(fast_clk),.wrst_n(cold_n&&fast_rst_n),.w_v(consume_ok),.w_rdy(ack_fifo_ready),.w_d(encoded_receipt),
   .rclk(slow_clk),.rrst_n(cold_n&&slow_rst_n),.r_v(ack_s_v),.r_rdy(ack_s_ready),.r_d(ack_s_code),.w_live(),.r_live(),.control_fault(transport_fault[2]));
  wire backend_debt,backend_fault,backend_init;
  ot_dsrom_vm_backend u_backend(.clk(slow_clk),.cold_n(cold_n),.rst_n(slow_rst_n),
   .req_v(req_s_v),.req_ready(req_s_ready),.req_code(req_s_code),
   .reply_v(rep_s_v),.reply_ready(rep_s_ready),.reply_code(rep_s_code),
   .receipt_v(ack_s_v),.receipt_ready(ack_s_ready),.receipt_code(ack_s_code),
   .initializing(backend_init),.debt(backend_debt),.fault(backend_fault));
  assign request_ready=cold_n&&fast_rst_n&&slow_rst_n&&!fault&&!debt&&!exhausted&&!initializing&&req_fifo_ready;
  assign rep_f_ready=cold_n&&fast_rst_n&&!fault&&debt;
  assign reply_v=cold_n&&fast_rst_n&&!fault&&debt&&received&&!acked;
  assign reply_owner=held_reply.owner;assign read_data=held_reply.data;
  assign row_visible=reply_v?held_reply.visible:5'd0;
  assign visible_addr=held_reply.wa;assign visible_mask=held_reply.wm;
  assign corrected=held_reply.corrected;
  task automatic fail;begin poison<=1;poison_check<=0;end endtask
  always @(posedge fast_clk)begin
   if(!cold_n)begin
    source_packet<=0;source_check<={REQ_BITS{1'b1}};held_reply<=0;held_check<={REP_BITS{1'b1}};
    serial<=0;serial_check<=32'hffffffff;exhausted<=0;exhausted_check<=1;
    debt<=0;debt_check<=1;launch<=0;launch_check<=1;received<=0;received_check<=1;acked<=0;acked_check<=1;
    poison<=0;poison_check<=1;retired<=0;backend_fault0<=0;backend_fault1<=0;init0<=1;init1<=1;
   end else begin
    retired<=0;backend_fault0<=backend_fault;backend_fault1<=backend_fault0;
    init0<=backend_init;init1<=init0;
    if(!fast_rst_n||!slow_rst_n)begin if(debt)fail();end
    else if(bad)fail();
    else if(!fault)begin
     if(request_v&&request_ready)begin
      source_packet<={serial,request_owner,read_enable,read_addr,write_enable,write_addr,write_data,write_mask};
      source_check<=~{serial,request_owner,read_enable,read_addr,write_enable,write_addr,write_data,write_mask};
      if(serial==32'hffffffff)begin exhausted<=1;exhausted_check<=0;end
      else begin serial<=serial+1;serial_check<=~(serial+32'd1);end
      debt<=1;debt_check<=0;launch<=1;launch_check<=0;received<=0;received_check<=1;acked<=0;acked_check<=1;
     end
     if(launch&&req_fifo_ready)begin launch<=0;launch_check<=1;end
     if(rep_f_v&&rep_f_ready)begin
      if(rep_ue||decoded_reply.ordinal!=source_packet.ordinal||decoded_reply.owner!=source_packet.owner||
       decoded_reply.re!=source_packet.re||decoded_reply.visible!=source_packet.we||decoded_reply.wa!=source_packet.wa||decoded_reply.wm!=source_packet.wm)fail();
      else if(decoded_reply.final_receipt)begin
       if(!received||!acked||decoded_reply.data!=held_reply.data)fail();
       else begin debt<=0;debt_check<=1;received<=0;received_check<=1;acked<=0;acked_check<=1;retired<=1;end
      end else if(received||acked)fail();
      else begin held_reply<=decoded_reply;held_check<=~decoded_reply;received<=1;received_check<=0;end
     end
     if(consume_v)begin
      if(!consume_ok||!ack_fifo_ready)fail();
      else begin acked<=1;acked_check<=0;end
     end
    end
   end
  end
 end else begin:g_off
  assign request_ready=0;assign reply_v=0;assign reply_owner=0;assign read_data=0;
  assign row_visible=0;assign visible_addr=0;assign visible_mask=0;assign corrected=0;
  assign port_retired=0;assign pending=0;assign quarantined=0;assign fault=0;assign initializing=0;
 end endgenerate
endmodule
