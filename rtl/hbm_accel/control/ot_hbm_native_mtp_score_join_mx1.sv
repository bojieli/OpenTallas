// Golden order: actual stored draft logits + actual Markov matvec score.
// LAT3 FP32 addition belongs to the serial0.9GHz domain. Native1.2GHz score
// stream must terminate in a real finite CDC queue before this valid/ready input.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_native_mtp_score_join_mx1 #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire i_v,output wire i_ready,input wire [72:0] i_owner,
 input wire [16:0] i_token,input wire [31:0] i_score,
 output wire lg_req_v,input wire lg_req_ready,
 output wire [72:0] lg_req_owner,output wire [16:0] lg_req_token,
 input wire lg_rsp_v,output wire lg_rsp_ready,input wire [72:0] lg_rsp_owner,
 input wire [16:0] lg_rsp_token,input wire [31:0] lg_rsp_score,input wire lg_rsp_error,
 output wire o_v,input wire o_ready,output wire [72:0] o_owner,
 output wire [16:0] o_token,output wire [31:0] o_score,
 output reg fault,output wire drained_ready
);
 localparam IDLE=0,REQ=1,RSP=2,ADD=3,WAIT=4,OUT=5,FAILED=6;
 reg [2:0] state;reg [72:0] owner;reg [16:0] token;
 reg [31:0] markov,stored,result;
 wire add_v;wire [31:0] add_y;wire [1:0] add_error;
 assign i_ready=ENABLE && rst_n && state==IDLE && !fault;
 assign lg_req_v=ENABLE && rst_n && state==REQ && !fault;
 assign lg_req_owner=owner;assign lg_req_token=token;
 assign lg_rsp_ready=ENABLE && rst_n && state==RSP && !fault;
 assign o_v=ENABLE && rst_n && state==OUT && !fault;
 assign o_owner=owner;assign o_token=token;assign o_score=result;
 assign drained_ready=ENABLE && rst_n && state==IDLE && !fault;
 ot_hdc_fp32_add_lat #(.LAT(3)) add(.clk(clk),.rst_n(rst_n),
  .valid_in(ENABLE && state==ADD && !fault),.a(stored),.b(markov),
  .y(add_y),.err(add_error),.valid_out(add_v));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;owner<=0;token<=0;markov<=0;stored<=0;result<=0;fault<=0;end
  else if(ENABLE)begin
   case(state)
    IDLE:if(i_v && i_ready)begin
     if(i_token>=129280 || i_score[30:23]==8'hff)begin fault<=1;state<=FAILED;end
     else begin owner<=i_owner;token<=i_token;markov<=i_score;state<=REQ;end
    end
    REQ:if(lg_req_v && lg_req_ready)state<=RSP;
    RSP:if(lg_rsp_v && lg_rsp_ready)begin
     if(lg_rsp_owner!=owner || lg_rsp_token!=token || lg_rsp_error || lg_rsp_score[30:23]==8'hff)begin
      fault<=1;state<=FAILED;
     end else begin stored<=lg_rsp_score;state<=ADD;end
    end
    ADD:state<=WAIT;
    WAIT:if(add_v)begin
     if(add_error!=0)begin fault<=1;state<=FAILED;end
     else begin result<=add_y;state<=OUT;end
    end
    OUT:if(o_v && o_ready)state<=IDLE;
    default:begin end
   endcase
  end
 end
endmodule
`default_nettype wire
