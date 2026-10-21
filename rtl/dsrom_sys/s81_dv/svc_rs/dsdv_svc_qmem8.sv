`timescale 1ns/1ps
// Source prototype only: selected by dsdv_svc_att.QMEM_SRAM, default 0.
// Native registered rd_out replaces eq_w, with no extra payload capture.
// Payload/rd_out are not reset; parent valid/lifetime state qualifies use.
module dsdv_svc_qmem8 (
    input wire clk,
    input wire wr_v,
    input wire [3:0] wr_head,
    input wire [511:0] wr_data,
    input wire [3:0] rd_head,
    output wire [511:0] rd_data
);
    genvar b;
    generate for (b=0; b<8; b=b+1) begin : g_bank
        ot_sram_1r1w_32x64_m1 u_mem (
            .clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0,rd_head}),
            .rd_out(rd_data[64*b +: 64]), .w_ce_in(wr_v),
            .w_addr_in({1'b0,wr_head}), .wd_in(wr_data[64*b +: 64]),
            .w_mask_in(64'hffffffffffffffff));
    end endgenerate
endmodule
