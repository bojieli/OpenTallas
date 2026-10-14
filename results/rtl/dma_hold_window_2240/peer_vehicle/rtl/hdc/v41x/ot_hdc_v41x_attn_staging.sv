`timescale 1ns/1ps
// One read and one write per row lane. A packed row contains D/32 groups of
// 265 bits; the physical option stripes each lane across 256-bit 1R1W macros.
// Both implementations return the old row one cycle after rd_addr is sampled.
module ot_hdc_v41x_attn_staging #(
    parameter integer D = 512,
    parameter integer NL = 4,
    parameter integer TROWS = 640,
    parameter bit SRAM_MACRO = 0
) (
    input  wire clk,
    input  wire [NL-1:0] wr_en,
    input  wire [$clog2((TROWS+NL-1)/NL)-1:0] wr_addr,
    input  wire [NL*(D/32)*265-1:0] wr_data,
    input  wire [$clog2((TROWS+NL-1)/NL)-1:0] rd_addr,
    output wire [NL*(D/32)*265-1:0] rd_data
);
    localparam integer DEPTH = (TROWS + NL - 1) / NL;
    localparam integer AW = $clog2(DEPTH);
    localparam integer ROWW = (D / 32) * 265;
    localparam integer NB = (ROWW + 255) / 256;
    genvar l, b;
    generate if (SRAM_MACRO) begin : g_macro
        initial begin
            if (DEPTH > 256 || AW > 8 || D % 32 != 0)
                $fatal(1, "attention staging macro requires DEPTH<=256, D%%32=0");
        end
        for (l = 0; l < NL; l = l + 1) begin : g_lane
            wire [NB*256-1:0] padded_in;
            wire [NB*256-1:0] padded_out;
            assign padded_in = {{(NB*256-ROWW){1'b0}}, wr_data[l*ROWW +: ROWW]};
            assign rd_data[l*ROWW +: ROWW] = padded_out[ROWW-1:0];
            for (b = 0; b < NB; b = b + 1) begin : g_slice
                ot_sram_1r1w_256x256_m2_r2c2 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in({{(8-AW){1'b0}}, rd_addr}),
                    .rd_out(padded_out[b*256 +: 256]),
                    .w_ce_in(wr_en[l]), .w_addr_in({{(8-AW){1'b0}}, wr_addr}),
                    .wd_in(padded_in[b*256 +: 256]),
                    .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0),
                    .cr_en(2'b0), .cr_sel(16'b0));
            end
        end
    end else begin : g_behavioural
        for (l = 0; l < NL; l = l + 1) begin : g_lane
            reg [ROWW-1:0] mem [0:DEPTH-1];
            reg [ROWW-1:0] q;
            always @(posedge clk) begin
                if (wr_en[l]) mem[wr_addr] <= wr_data[l*ROWW +: ROWW];
                q <= mem[rd_addr];
            end
            assign rd_data[l*ROWW +: ROWW] = q;
        end
    end endgenerate
endmodule
