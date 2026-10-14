`default_nettype none
module vm_ck4_data(input wire ck,rst_n,capture_i,check_i,write_i,
 input wire [287:0] sample_i,expected_i,output wire error_o,valid_o,output wire [287:0] repaired_o);
 vm_ck4 u_ck(.ck(ck),.rst_n(rst_n),.capture_i(capture_i),.check_i(check_i),.write_i(write_i),
 .capture_regions_i(8'd0),.check_regions_i(8'd0),.sample_i(sample_i),.expected_i(expected_i),.owner_mask_i(256'd0),.padding_mask_i(256'd0),
 .error_o(error_o),.valid_o(valid_o),.repaired_o(repaired_o));
endmodule
module vm_ck4_owner(input wire ck,rst_n,capture_i,check_i,write_i,
 input wire [287:0] sample_i,expected_i,output wire error_o,valid_o,output wire [287:0] repaired_o);
 vm_ck4 u_ck(.ck(ck),.rst_n(rst_n),.capture_i(capture_i),.check_i(check_i),.write_i(write_i),
 .capture_regions_i(8'd0),.check_regions_i(8'd0),.sample_i(sample_i),.expected_i(expected_i),.owner_mask_i(({256{1'b1}}>>64)<<15),
 .padding_mask_i({{49{1'b1}},207'd0}),.error_o(error_o),.valid_o(valid_o),.repaired_o(repaired_o));
endmodule
`default_nettype wire
