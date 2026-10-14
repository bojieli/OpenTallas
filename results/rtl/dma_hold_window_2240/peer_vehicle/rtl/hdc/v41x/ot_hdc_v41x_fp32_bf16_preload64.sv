`timescale 1ns/1ps
// Registered boundary between four bank-major 512-bit VM reads and one
// 64-element ME activation preload.  All 64 conversions use the same target
// FP32->BF16 RNE, finite saturation, nonfinite fault, and +0 rule as the core.
// Metadata advances with the data; a consumer writes out_d to the selected
// group/position on out_v.  One conversion cycle is charged after VM read.
module ot_hdc_v41x_fp32_bf16_preload64 #(
    parameter integer EW = 13,
    parameter integer PW = 2
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  in_v,
    input  wire [PW-1:0]         in_p,
    input  wire [EW-1:0]         in_e,
    input  wire [2047:0]         in_d,
    output reg                   out_v,
    output reg  [PW-1:0]         out_p,
    output reg  [EW-1:0]         out_e,
    output reg  [1023:0]        out_d,
    output reg                   out_fault,
    output reg                   out_saturated
);
    // Keep this physical boundary self-contained for the Yosys/ORFS flow.
    // This is bit-for-bit the fp32_to_bf16_rne rule in ot_fp32_rne_pkg.
    function automatic [18:0] cv_rne(input [31:0] code);
        reg [15:0] rounded;
        reg saturated;
        reg increment;
        begin
            rounded=0; saturated=0; increment=0;
            if (code[30:23] == 8'hff) cv_rne={2'b01,1'b0,16'b0};
            else begin
                increment=(code[15:0] > 16'h8000) ||
                          ((code[15:0] == 16'h8000) && code[16]);
                rounded=code[31:16]+{15'b0,increment};
                if (rounded[14:7] == 8'hff) begin
                    rounded={code[31],8'hfe,7'h7f};
                    saturated=1;
                end
                if (rounded[14:0] == 0) rounded=0;
                cv_rne={2'b00,saturated,rounded};
            end
        end
    endfunction
    wire [18:0] cv [0:63];
    genvar i;
    generate for (i=0;i<64;i=i+1) begin : g_cv
        assign cv[i] = cv_rne(in_d[i*32 +:32]);
    end endgenerate
    integer j;
    reg fault_d, saturated_d;
    always @* begin
        fault_d=0;
        saturated_d=0;
        for (integer k=0;k<64;k=k+1) begin
            fault_d = fault_d | (cv[k][18:17] != 2'b00);
            saturated_d = saturated_d | cv[k][16];
        end
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            out_v <= 0;
            out_p <= '0;
            out_e <= '0;
            out_d <= '0;
            out_fault <= 0;
            out_saturated <= 0;
        end else begin
            out_v <= in_v;
            out_p <= in_p;
            out_e <= in_e;
            out_fault <= in_v && fault_d;
            out_saturated <= in_v && saturated_d;
            for (j=0;j<64;j=j+1) out_d[j*16 +:16] <= cv[j][15:0];
        end
    end
endmodule
