`timescale 1ns/1ps
// Same block, MAX_ROWS=1 -> 128-entry array instead of 512. Decides whether the
// register-array crossbar is the critical path.
module ot_probe_had1 (
    input wire clk, input wire rst_n, input wire start,
    input wire [15:0] cfg_rows, input wire [15:0] cfg_cols, input wire [31:0] cfg_count,
    input wire [7:0] cfg_dtype_a, input wire [31:0] cfg_a_base, input wire [31:0] cfg_out_base,
    output wire a_rd_en, output wire [31:0] a_rd_addr, input wire [31:0] a_rd_data,
    output wire out_we, output wire [31:0] out_addr, output wire [31:0] out_data,
    output wire busy, output wire done, output wire [7:0] error_code, output wire [31:0] out_count
);
    ot_a3_vector_hadamard #(.MAX_ROWS(16'd1)) u (.*);
endmodule
