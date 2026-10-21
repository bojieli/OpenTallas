`timescale 1ns/1ps
// SOURCE CANDIDATE: no extra operand edge. See s81_merge_sram_1021/MODEL.md.
// Caller refills all DPT entries before consuming ring state after reset.
module ot_hdc_v41x_merge_ring_sram #(
    parameter integer W = 528, parameter integer DPT = 8,
    parameter integer MUT = 0
) (
    input wire clk, rst_n, v, store,
    input wire [W-1:0] data,
    output wire [W-1:0] head
);
    localparam integer AW = (DPT <= 2) ? 1 : $clog2(DPT);
    localparam integer NB = (W + 127) / 128;
    reg [AW-1:0] ptr;
    wire advance = (MUT == 2) ? 1'b1 : v;
    wire [AW-1:0] next_ptr = advance ? ((ptr == AW'(DPT-1)) ? AW'(0) : ptr + AW'(1)) : ptr;
    wire [4:0] ra = !rst_n ? 5'd0 : (MUT == 3) ? 5'(ptr) : 5'(next_ptr);
    wire [4:0] wa = (MUT == 1) ? ((ptr == AW'(DPT-1)) ? 5'd0 : 5'(ptr + AW'(1))) : 5'(ptr);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ptr <= '0;
        else ptr <= next_ptr;
    wire [NB*128-1:0] payload = {{(NB*128-W){1'b0}}, data};
    wire [NB*128-1:0] read_data;
    genvar b;
    generate for (b=0; b<NB; b=b+1) begin : g_bank
        ot_sram_1r1w_32x128_m1 u_mem (
            .clk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(read_data[128*b +:128]),
            .w_ce_in(rst_n && v && store), .w_addr_in(wa), .wd_in(payload[128*b +:128]), .w_mask_in({128{1'b1}}));
    end endgenerate
    assign head = read_data[W-1:0];
    initial begin
        if (DPT < 2 || DPT > 32 || W < 1) $error("merge ring SRAM requires 2<=DPT<=32, W>=1");
    end
endmodule
