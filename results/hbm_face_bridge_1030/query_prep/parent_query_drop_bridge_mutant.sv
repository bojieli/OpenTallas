module parent_query_drop_bridge (
    input wire clk,
    input wire clk_quant,
    input wire clk_quant_delay,
    input wire [3:0] clk_bank,
    input wire rst_n,
    input wire frame_start,
    input wire block_v,
    input wire [4:0] block_head,
    input wire [1:0] block_number,
    input wire [1023:0] block_data,
    input wire [15:0] head_weight,
    input wire emit_v,
    input wire [4:0] emit_head,
    output wire ql_v,
    output wire [7:0] ql_head,
    output wire [511:0] ql_codes,
    output wire [31:0] ql_sc,
    output wire [15:0] ql_w,
    output wire fault
);
wire [4:0] physical_head;
(* keep *) reg[2:0] cold_core,cold_native_pin,cold_outer_pin;
always @(posedge clk) begin cold_core<=3'b0;cold_native_pin<=cold_core;cold_outer_pin<=cold_native_pin;end
assign ql_head={3'b0,physical_head};
physical_query_drop3 child(.clk(clk),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_bank),.rst_n(rst_n),.frame_start(frame_start),.block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),.emit_v(emit_v),.emit_head(emit_head),.ql_v(ql_v),.ql_head(physical_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.fault(fault));
endmodule
