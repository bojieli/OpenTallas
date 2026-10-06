`timescale 1ns/1ps
// One outstanding operation. Every externally held payload and permissions
// live in the existing W2 SECDED bank; its repair/fail-closed rules are priced.
// Request ownership ends only on actual response consumption, not completion.
module ot_hbm_compute_held_exec #(parameter integer IW=1,OW=1)(
 input wire clk,rst_n,
 input wire req_v,output wire req_r,input wire [IW-1:0] req_d,
 output wire rsp_v,input wire rsp_r,output wire [OW-1:0] rsp_d,
 output wire launch,output wire engine_clk,output wire engine_error_seen,output wire [IW-1:0] engine_d,
 input wire engine_v,input wire [OW-1:0] engine_q,input wire engine_fault,
 output wire fault
);
 wire input_v,input_r,input_fault,input_empty,input_ready;
 wire result_v;
 wire result_r,result_fault,result_empty;
 wire [63:0] ctl;wire normal,ctl_fault,repairing;
 wire [1:0] state=ctl[1:0];
 wire release_op=rsp_v&&rsp_r;
 assign engine_error_seen=ctl[2];
 assign launch=normal&&!fault&&state==0&&input_v;
 assign input_r=normal&&!fault&&state==2&&release_op;
 wire receive=normal&&!fault&&input_v&&state==1&&engine_v&&result_r;
 wire illegal=normal&&(state==3||(engine_v&&state!=1));
 assign fault=input_fault|result_fault|ctl_fault;
 assign req_r=input_ready&&!fault&&normal;
 assign rsp_v=result_v&&!fault&&normal;
 // CE repair freezes the unchanged pipelines before held operands can change.
 // Gate/CTS/load cost is explicit and physically OPEN; no borrowed leaf clock.
 ot_hdc_cg u_engine_gate(.clk(clk),.en(!rst_n||(input_v&&normal&&!fault&&(state!=1||result_r))),.gclk(engine_clk));
 ot_hbm_w2_protected_cut #(.W(IW)) u_request(
  .clk(clk),.por_n(rst_n),.in_v(req_v&&!fault&&normal),.in_r(input_ready),.in_d(req_d),
  .out_v(input_v),.out_r(input_r),.out_d(engine_d),.empty(input_empty),.fault(input_fault));
 ot_hbm_w2_protected_cut #(.W(OW)) u_response(
  .clk(clk),.por_n(rst_n),.in_v(receive),.in_r(result_r),.in_d(engine_q),
  .out_v(result_v),.out_r(rsp_r&&!fault&&normal),.out_d(rsp_d),.empty(result_empty),.fault(result_fault));
 wire [1:0] next_state=launch?2'd1:receive?2'd2:release_op?2'd0:state;
 ot_hbm_w2_protected_bank #(.WORDS(1)) u_controller(
  .clk(clk),.por_n(rst_n),.load(normal&&(launch||receive||release_op||(state==1&&engine_fault))),
  .load_encoded(1'b0),.fatal(illegal||(receive&&!result_r)),
  .d({61'b0,(release_op?1'b0:ctl[2]|(state==1&&engine_fault)),next_state}),.encoded_d(72'b0),
  .q(ctl),.encoded_q(),.normal(normal),.fault(ctl_fault),.repairing(repairing));
endmodule
