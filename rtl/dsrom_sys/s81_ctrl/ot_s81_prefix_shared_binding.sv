`timescale 1ns/1ps
// Native engine-specific binding: no generic descriptor/opcode reinterpretation.
// Caller supplies existing opaque transaction identity and sorted expert IDs.
// Prefix/shared start atomically; ownership ends at actual primary outlast,
// returned to the stream command domain through a finite completion CDC.
module ot_s81_prefix_shared_binding #(parameter integer ENABLE=0)(
 input wire stream_clk,serial_clk,rst_n,
 input wire start_valid,output wire start_ready,input wire[73:0] start_identity,
 input wire[26:0] start_ids,
 input wire[1:0] expert_valid,output wire[1:0] expert_ready,
 input wire[147:0] expert_identity,input wire[17:0] expert_id,
 input wire[1:0] expert_last,input wire[13:0] expert_word,input wire[1023:0] expert_data,
 input wire shared_valid,output wire shared_ready,input wire[511:0] shared_data,
 input wire[73:0] shared_identity,input wire[6:0] shared_word,
 input wire shared_last,shared_fmt_fp32,shared_error,
 output wire out_valid,input wire out_ready,output wire[511:0] out_data,
 output wire[73:0] out_identity,output wire[6:0] out_word,output wire out_last,
 output wire done,busy,fault
);
 generate if(!ENABLE)begin:disabled
 assign start_ready=0;assign expert_ready=0;assign shared_ready=0;
 assign out_valid=0;assign out_data=0;assign out_identity=0;assign out_word=0;assign out_last=0;
 assign done=0;assign busy=0;assign fault=0;
 end else begin:enabled
 reg owned;reg serial_fault_meta,serial_fault_stream;
 wire prefix_ready,prefix_v,prefix_r,prefix_fault,prefix_last;
 wire[511:0] prefix_data;wire[73:0] prefix_identity;wire[6:0] prefix_word;
 wire shared_cmd_ready,sv,sr,sl,sfault;
 wire[511:0] sd;wire[73:0] st;wire[6:0] sw;
 wire serial_done,serial_busy,serial_fault,return_done,done_space;wire[0:0] done_data;
 assign start_ready=!owned&&prefix_ready&&shared_cmd_ready&&!fault;
 wire fire=start_valid&&start_ready;
 assign busy=owned;assign done=return_done;assign fault=prefix_fault||sfault||serial_fault_stream;
 ot_mtp_p2_prefix_path #(.ENABLE(1)) prefix(.clk(stream_clk),.rst_n(rst_n),
 .start_v(fire),.start_r(prefix_ready),.start_identity(start_identity),.start_ids(start_ids),
 .in_v(expert_valid),.in_r(expert_ready),.in_identity(expert_identity),.in_expert(expert_id),
 .in_shared(2'b00),.in_last(expert_last),.in_word(expert_word),.in_data(expert_data),
 .out_v(prefix_v),.out_r(prefix_r),.out_data(prefix_data),.out_identity(prefix_identity),
 .out_word(prefix_word),.out_last(prefix_last),.abort(1'b0),.done(),.fault(prefix_fault),.corrected());
 ot_s81_shared_publisher_plain #(.ENABLE(1)) publisher(.clk(stream_clk),.rst_n(rst_n),
 .cmd_valid(fire),.cmd_ready(shared_cmd_ready),.cmd_context(start_identity),
 .in_valid(shared_valid),.in_ready(shared_ready),.in_data(shared_data),.in_context(shared_identity),
 .in_word(shared_word),.in_last(shared_last),.in_fmt_fp32(shared_fmt_fp32),.in_error(shared_error),
 .out_valid(sv),.out_ready(sr),.out_data(sd),.out_context(st),.out_word(sw),.out_last(sl),
 .out_corrected(),.busy(),.fault(sfault));
 ot_s81_primary_shared_receive #(.ENABLE(1)) primary(.stream_clk(stream_clk),.serial_clk(serial_clk),
 .rst_n(rst_n),.p_valid(prefix_v),.p_ready(prefix_r),.p_data(prefix_data),.p_tag(prefix_identity),
 .p_word(prefix_word),.p_last(prefix_last),.s_valid(sv),.s_ready(sr),.s_data(sd),.s_tag(st),
 .s_word(sw),.s_last(sl),.out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),
 .out_tag(out_identity),.out_word(out_word),.out_last(out_last),
 .context_done(serial_done),.busy(serial_busy),.fault(serial_fault));
 ot_s81_pulse_cdc #(.W(1),.QD(8)) completion(.i_clk(serial_clk),.o_clk(stream_clk),
 .rst_n(rst_n),.i_v(serial_done),.i_d(1'b1),.i_accept(done_space),
 .o_v(return_done),.o_r(1'b1),.o_d(done_data));
 always @(posedge stream_clk or negedge rst_n)begin
 if(!rst_n)begin owned<=0;serial_fault_meta<=0;serial_fault_stream<=0;end
 else begin
 serial_fault_meta<=serial_fault;serial_fault_stream<=serial_fault_meta;
 if(fire)owned<=1;
 if(return_done)owned<=0;
 end
 end
 end endgenerate
endmodule
