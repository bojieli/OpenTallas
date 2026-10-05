// Named payload facade for source-selected caller integration. No legacy core rewritten.
module ot_ds_seven_class_port_swap #(parameter ENABLE=0)(
input wire fast_clk,slow_clk,cold_n,fast_rst_n,slow_rst_n,
input wire [13:0] abort_s,abort_d,in_v,out_ready,retire_v,reconcile_v,allcopies_fenced,
output wire [13:0] in_ready,out_v,retire_ready,pending,quarantined,
input wire [14*228-1:0] in_owner,retire_owner,reconcile_owner,
output wire [14*228-1:0] out_owner,pending_owner,
input wire [16127:0] su_kv_staging_source, output wire [16127:0] su_kv_staging_destination,
input wire [2235:0] me_result_write_source, output wire [2235:0] me_result_write_destination,
input wire [30:0] field_x_request_source, output wire [30:0] field_x_request_destination,
input wire [2047:0] field_x_reply_source, output wire [2047:0] field_x_reply_destination,
input wire [30:0] field_id_request_source, output wire [30:0] field_id_request_destination,
input wire [31:0] field_id_reply_source, output wire [31:0] field_id_reply_destination,
input wire [8063:0] field_row_write_source, output wire [8063:0] field_row_write_destination,
input wire [15:0] collective_read_request_source, output wire [15:0] collective_read_request_destination,
input wire [511:0] collective_read_reply_source, output wire [511:0] collective_read_reply_destination,
input wire [2111:0] collective_write_source, output wire [2111:0] collective_write_destination,
input wire [123:0] index_query_request_source, output wire [123:0] index_query_request_destination,
input wire [127:0] index_query_reply_source, output wire [127:0] index_query_reply_destination,
input wire [123:0] selector_read_request_source, output wire [123:0] selector_read_request_destination,
input wire [2047:0] selector_read_reply_source, output wire [2047:0] selector_read_reply_destination);
wire [14*16128-1:0] in_data,out_data;
assign in_data[0*16128+:16128]=su_kv_staging_source;
assign su_kv_staging_destination=out_data[0*16128+:16128];
assign in_data[1*16128+:2236]=me_result_write_source;
assign me_result_write_destination=out_data[1*16128+:2236];
assign in_data[1*16128+2236+:13892]='0;
assign in_data[2*16128+:31]=field_x_request_source;
assign field_x_request_destination=out_data[2*16128+:31];
assign in_data[2*16128+31+:16097]='0;
assign in_data[3*16128+:2048]=field_x_reply_source;
assign field_x_reply_destination=out_data[3*16128+:2048];
assign in_data[3*16128+2048+:14080]='0;
assign in_data[4*16128+:31]=field_id_request_source;
assign field_id_request_destination=out_data[4*16128+:31];
assign in_data[4*16128+31+:16097]='0;
assign in_data[5*16128+:32]=field_id_reply_source;
assign field_id_reply_destination=out_data[5*16128+:32];
assign in_data[5*16128+32+:16096]='0;
assign in_data[6*16128+:8064]=field_row_write_source;
assign field_row_write_destination=out_data[6*16128+:8064];
assign in_data[6*16128+8064+:8064]='0;
assign in_data[7*16128+:16]=collective_read_request_source;
assign collective_read_request_destination=out_data[7*16128+:16];
assign in_data[7*16128+16+:16112]='0;
assign in_data[8*16128+:512]=collective_read_reply_source;
assign collective_read_reply_destination=out_data[8*16128+:512];
assign in_data[8*16128+512+:15616]='0;
assign in_data[9*16128+:2112]=collective_write_source;
assign collective_write_destination=out_data[9*16128+:2112];
assign in_data[9*16128+2112+:14016]='0;
assign in_data[10*16128+:124]=index_query_request_source;
assign index_query_request_destination=out_data[10*16128+:124];
assign in_data[10*16128+124+:16004]='0;
assign in_data[11*16128+:128]=index_query_reply_source;
assign index_query_reply_destination=out_data[11*16128+:128];
assign in_data[11*16128+128+:16000]='0;
assign in_data[12*16128+:124]=selector_read_request_source;
assign selector_read_request_destination=out_data[12*16128+:124];
assign in_data[12*16128+124+:16004]='0;
assign in_data[13*16128+:2048]=selector_read_reply_source;
assign selector_read_reply_destination=out_data[13*16128+:2048];
assign in_data[13*16128+2048+:14080]='0;
ot_ds_seven_class_boundary_bank #(.ENABLE(ENABLE)) boundary_bank(.*);
endmodule
