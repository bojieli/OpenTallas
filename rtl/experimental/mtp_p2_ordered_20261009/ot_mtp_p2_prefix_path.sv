`timescale 1ns/1ps
`default_nettype none
// Real finite transport -> exact arithmetic -> corrected native publisher.
// Context remains owned through the last native output handshake.
module ot_mtp_p2_prefix_path #(parameter integer ENABLE=0)(
 input wire clk,rst_n,start_v,output wire start_r,
 input wire [73:0] start_identity,input wire [26:0] start_ids,
 input wire [1:0] in_v,output wire [1:0] in_r,input wire [147:0] in_identity,
 input wire [17:0] in_expert,input wire [1:0] in_shared,in_last,
 input wire [13:0] in_word,input wire [1023:0] in_data,
 output wire out_v,input wire out_r,output wire [511:0] out_data,
 output wire [73:0] out_identity,output wire [6:0] out_word,output wire out_last,
 input wire abort,output wire done,fault,corrected
);
 generate if(!ENABLE)begin: disabled
 assign start_r=0;assign in_r=0;assign out_v=0;assign out_data=0;
 assign out_identity=0;assign out_word=0;assign out_last=0;
 assign done=0;assign fault=0;assign corrected=0;
 end else begin: enabled
 reg busy,busy_copy,done_q;
 wire tr_sr,ar_sr,tr_v,tr_r,tr_fault,ar_fault,pub_fault;
 wire [73:0] tr_id;wire [8:0] tr_expert;wire [6:0] tr_word;
 wire tr_shared,tr_last,tr_tlast;wire [575:0] tr_code;
 wire ar_v,ar_r,ar_last,ar_ce,pub_ce;wire [73:0] ar_id;
 wire [6:0] ar_word;wire [575:0] ar_code;
 wire broken=busy!=busy_copy;
 assign fault=tr_fault||ar_fault||pub_fault||broken;
 wire poison=abort||fault;
 assign start_r=!busy&&!poison&&tr_sr&&ar_sr;
 wire fire=start_v&&start_r;
 assign done=done_q;assign corrected=ar_ce||pub_ce;
 ot_mtp_p2_ordered_rows #(.ENABLE(1),.PRIMARY_SHARED(1)) transport(
 .clk(clk),.rst_n(rst_n),.start_v(fire),.start_r(tr_sr),
 .start_identity(start_identity),.start_ids(start_ids),
 .in_v(in_v),.in_r(in_r),.in_identity(in_identity),.in_expert(in_expert),
 .in_shared(in_shared),.in_last(in_last),.in_word(in_word),.in_data(in_data),
 .out_v(tr_v),.out_r(tr_r),.out_identity(tr_id),.out_expert(tr_expert),
 .out_shared(tr_shared),.out_row_last(tr_last),.out_transaction_last(tr_tlast),
 .out_word(tr_word),.out_secded(tr_code),.sink_abort(poison),.done(),.fault(tr_fault));
 ot_mtp_p2_prefix #(.ENABLE(1)) arithmetic(.clk(clk),.rst_n(rst_n),
 .start_v(fire),.start_r(ar_sr),.start_identity(start_identity),.start_ids(start_ids),
 .in_v(tr_v),.in_r(tr_r),.in_identity(tr_id),.in_expert(tr_expert),
 .in_shared(tr_shared),.in_row_last(tr_last),.in_transaction_last(tr_tlast),
 .in_word(tr_word),.in_secded(tr_code),.out_v(ar_v),.out_r(ar_r),
 .out_identity(ar_id),.out_word(ar_word),.out_last(ar_last),.out_secded(ar_code),
 .abort(poison),.done(),.fault(ar_fault),.corrected(ar_ce));
 ot_mtp_p2_prefix_native #(.ENABLE(1)) publisher(.clk(clk),.rst_n(rst_n),.abort(poison),
 .in_v(ar_v),.in_r(ar_r),.in_secded(ar_code),.in_identity(ar_id),
 .in_word(ar_word),.in_last(ar_last),.out_v(out_v),.out_r(out_r),
 .out_data(out_data),.out_identity(out_identity),.out_word(out_word),.out_last(out_last),
 .fault(pub_fault),.corrected(pub_ce));
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin busy<=0;busy_copy<=0;done_q<=0;end
 else begin done_q<=0;
 if(fire)begin busy<=1;busy_copy<=1;end
 if(out_v&&out_r&&out_last&&!poison)begin busy<=0;busy_copy<=0;done_q<=1;end
 end end
 end endgenerate
endmodule
`default_nettype wire
