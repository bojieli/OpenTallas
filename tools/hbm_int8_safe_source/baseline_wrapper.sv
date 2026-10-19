module ot_smh_int8_tile_safe (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,          // packet[1098] & command[116] (the parent's mark)
    input  wire [9:0]    i_tag,        // packet[1097:1088]
    input  wire [1023:0] i_codes,      // packet[1023:0]: 128 INT8 codes, low 64 first
    output wire          o_v,
    output wire [9:0]    o_tag,
    output wire [1023:0] o_data,       // 64 BF16 lanes
    output wire [34:0]   o_sel         // kept copies of o_v for the parent's 1099-bit merge select (<= 32 bits each)
);
    (* keep *) reg reset_first,reset_final;
    always @(posedge clk) begin reset_first<=rst_n; reset_final<=reset_first; end
    ot_smh_int8_tile base (.clk(clk),.rst_n(reset_final),.i_v(i_v),.i_tag(i_tag),.i_codes(i_codes),.o_v(o_v),.o_tag(o_tag),.o_data(o_data),.o_sel(o_sel));
endmodule
