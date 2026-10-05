`timescale 1ns/1ps
// Actual field-X caller -> retained related FIFO -> full native VM -> caller.
// Cold reset is initialisation only. Transport reset quarantines accepted owner;
// no warm reset, empty test or engine-done signal erases service debt.
// Raw functional component; mutable-state protection/parent physical still open.
module ot_ds_field_x_related_native #(parameter ENABLE=0)(
 input wire fast_clk,slow_clk,cold_n,fast_rst_n,slow_rst_n,abort_fast,abort_slow,
 input wire req_v,output wire req_ready,input wire [29:0] req_addr,
 input wire [16:0] req_cookie,input wire [134:0] descriptor,
 output wire reply_v,input wire reply_ready,output wire [2047:0] reply_data,
 output wire [16:0] reply_cookie,output wire debt,quarantine,output reg fault,
 input wire [3:0] init_wr_v,input wire [59:0] init_wr_addr,
 input wire [2047:0] init_wr_data,input wire [63:0] init_wr_mask,
 output wire [3:0] init_wr_accept,init_wr_visible
);
 reg [31:0] epoch;reg [15:0] batch;reg [10:0] rid;
 wire [227:0] generated_owner={17'b0,descriptor,req_cookie,epoch,batch,rid};
 wire in_rdy,fwd_v;wire [30:0] request;
 wire [227:0] request_owner;wire [227:0] unused_owner;
 reg req_retire;wire req_retire_ready;
 wire req_debt,req_quarantine;
 reg [227:0] active_owner;
 wire exhausted=epoch==32'hffffffff && rid==11'h7ff;
 assign req_ready=in_rdy&&!exhausted&&!fault;
 always @(posedge fast_clk) begin
  if(!cold_n)begin epoch<=0;batch<=0;rid<=0;end
  else if(req_v&&req_ready)begin
   if(rid==11'h7ff)begin rid<=0;epoch<=epoch+1'b1;batch<=batch+1'b1;end else rid<=rid+1'b1;
  end
 end
 ot_ds_owned_ratio_boundary #(.W(31),.ENABLE(ENABLE)) request_crossing(
 .sclk(fast_clk),.dclk(slow_clk),.cold_n(cold_n),.srst_n(fast_rst_n),.drst_n(slow_rst_n),
 .abort_s(abort_fast),.abort_d(abort_slow),.in_v(req_v&&!exhausted&&!fault),.in_ready(in_rdy),
 .in_data({1'b1,req_addr}),.in_owner(generated_owner),.out_v(fwd_v),.out_ready(state==IDLE),
 .out_data(request),.out_owner(request_owner),.retire_v(req_retire),.retire_ready(req_retire_ready),
 .retire_owner(active_owner),.reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),
 .pending(req_debt),.quarantined(req_quarantine),.pending_owner(unused_owner));
 localparam IDLE=0,ISSUE=1,WAIT_DATA=2,SEND=3,WAIT_OWNED=4,WAIT_RETIRE=5,RETIRE_REQ=6,HOLD_ERROR=7;
 reg [3:0] state;
 reg [29:0] address;reg [14:0] base_word;
 reg [4095:0] buffer;
 reg second_read;wire [2047:0] ordered_native;
 wire rsp_in_ready,rsp_debt,rsp_quarantine;wire [227:0] response_owner;
 wire rsp_retire_ready,raw_reply_v;
 assign reply_v=raw_reply_v&&rsp_retire_ready;
 wire native_rd_out,native_rd_accept;wire [2047:0] native_data;wire [1:0] native_rot;
 wire [227:0] native_owner;wire rd_fault,wr_fault,collision;
 wire [911:0] init_owner={4{228'b0}};
 wire native_rd=ENABLE&&cold_n&&slow_rst_n&&!abort_slow&&state==ISSUE;
 wire [3:0] allowed_init=(state==IDLE&&!fwd_v&&!req_debt) ? init_wr_v:4'b0;
 ot_v41_vm_bank4_macro_pipe_masked_visible_r2 #(.MASKED_VISIBLE(1),.DEPTH_GROUPS(16),.AW(15),.TAG_W(228)) native_VM(
 .clk(slow_clk),.rst_n(cold_n),.rd_v(native_rd),.rd_base_word(base_word),.rd_owner(active_owner),
 .rd_accept_v(native_rd_accept),.rd_out_v(native_rd_out),.rd_out_rot(native_rot),.rd_out_bank_words(native_data),
 .rd_out_owner(native_owner),.rd_fault(rd_fault),.wr_v(allowed_init),.wr_word_addr(init_wr_addr),
 .wr_word_data(init_wr_data),.wr_lane_mask(init_wr_mask),.wr_owner(init_owner),.wr_accept_v(init_wr_accept),
 .wr_ack_v(init_wr_visible),.wr_ack_owner(),.wr_ack_word_addr(),.wr_ack_lane_mask(),.wr_fault(wr_fault),.rw_collision_fault(collision));
 genvar w;
 generate for(w=0;w<4;w=w+1)begin: reorder
  assign ordered_native[w*512+:512]=native_data[((native_rot+w)%4)*512+:512];
 end endgenerate
 wire [2047:0] packed_reply=buffer >> (address[3:0]*32);
 ot_ds_owned_ratio_boundary #(.W(2048),.ENABLE(ENABLE)) response_crossing(
 .sclk(slow_clk),.dclk(fast_clk),.cold_n(cold_n),.srst_n(slow_rst_n),.drst_n(fast_rst_n),
 .abort_s(abort_slow),.abort_d(abort_fast),.in_v(state==SEND),.in_ready(rsp_in_ready),.in_data(packed_reply),
 .in_owner(active_owner),.out_v(raw_reply_v),.out_ready(reply_ready&&rsp_retire_ready),.out_data(reply_data),.out_owner(response_owner),
 .retire_v(reply_v&&reply_ready),.retire_ready(rsp_retire_ready),.retire_owner(response_owner),
 .reconcile_v(1'b0),.allcopies_fenced(1'b0),.reconcile_owner(228'b0),.pending(rsp_debt),
 .quarantined(rsp_quarantine),.pending_owner());
 // A reply cannot be consumed unless its actual capture also enters reverse receipt.
 // The response receiver is one-credit; receipt FIFO is empty for the unique owner.
 assign reply_cookie=response_owner[75:59];
 assign debt=req_debt||rsp_debt||state!=IDLE;
 assign quarantine=req_quarantine||rsp_quarantine||state==HOLD_ERROR;
 always @(posedge slow_clk) begin
  if(!cold_n)begin state<=IDLE;fault<=0;req_retire<=0;address<=0;base_word<=0;second_read<=0;active_owner<=0;buffer<=0;end
  else begin
   req_retire<=0;
   if(rd_fault||wr_fault||collision)begin fault<=1;state<=HOLD_ERROR;end
   else if(abort_slow||!slow_rst_n)begin if(state!=IDLE)state<=HOLD_ERROR;end
   else case(state)
    IDLE:if(fwd_v)begin
     address<=request[29:0];active_owner<=request_owner;second_read<=0;
     if(!request[30]||request[29:19]!=0||request[18:0]>19'h7ffc0)begin fault<=1;state<=HOLD_ERROR;end
     else begin base_word<=request[18:4];state<=ISSUE;end
    end
    ISSUE:if(native_rd_accept)state<=WAIT_DATA;
    WAIT_DATA:if(native_rd_out)begin
     if(native_owner!=active_owner)begin fault<=1;state<=HOLD_ERROR;end
     else if(!second_read)begin
      buffer[2047:0]<=ordered_native;buffer[4095:2048]<=0;
      if(address[3:0]!=0)begin base_word<= (base_word>15'd32760) ? 15'd32764 : base_word+15'd4;second_read<=1;state<=ISSUE;end else state<=SEND;
     end else begin buffer[4095:2048]<=ordered_native >> (({1'b0,address[18:4]}+16'd4-{1'b0,base_word})*512);state<=SEND;end
    end
    SEND:if(rsp_in_ready)state<=WAIT_OWNED;
    WAIT_OWNED:if(rsp_debt)state<=WAIT_RETIRE;
    WAIT_RETIRE:if(!rsp_debt)state<=RETIRE_REQ;
    RETIRE_REQ:if(req_retire_ready)begin req_retire<=1;state<=IDLE;end
    default:state<=HOLD_ERROR;
   endcase
  end
 end
endmodule
