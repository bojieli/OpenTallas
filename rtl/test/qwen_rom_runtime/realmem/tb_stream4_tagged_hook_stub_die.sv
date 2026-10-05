`timescale 1ns/1ps
// Compile check of tools/runtime/qwen_combined/stream4_tagged_rows_hook.cpp: a stub with EXACTLY the
// tagged row boundary of rtl/qwen_sys/combined/ot_qwen_rom_combined_stream4_die.sv (names, directions,
// widths), Verilated with prefix Vdie; the real backend ot_qwen_hbm_stream4_tagged is Verilated as Vhbm.
module tb_stream4_tagged_hook_stub_die (
    input  wire clk, rst_n, hclk, hrst_n,
    output reg  [3:0] h_req_v, h_req_we, input wire [3:0] h_req_ready,
    output reg  [95:0] h_req_addr, output reg [19:0] h_req_len,
    output reg  [51:0] h_req_tag, output reg [1023:0] h_req_wdata,
    input  wire [127:0] h_pc_room, h_rsp_v, h_rsp_wr,
    output reg  [127:0] h_rsp_ready,
    input  wire [1663:0] h_rsp_tag, input wire [511:0] h_rsp_beat,
    input  wire [32767:0] h_rsp_data,
    output reg  [31:0] seen
);
    always @(posedge hclk or negedge hrst_n)
        if (!hrst_n) begin h_req_v <= 0; h_req_we <= 0; h_req_addr <= 0; h_req_len <= 0; h_req_tag <= 0; h_req_wdata <= 0;
                           h_rsp_ready <= 0; seen <= 0; end
        else begin
            h_rsp_ready <= {128{1'b1}};
            seen <= seen + {31'd0, |(h_rsp_v & h_pc_room & ~h_rsp_wr)} + {31'd0, ^h_rsp_tag[12:0]} + {31'd0, ^h_rsp_beat} +
                    {31'd0, ^h_rsp_data[255:0]} + {31'd0, |h_req_ready};
        end
endmodule
