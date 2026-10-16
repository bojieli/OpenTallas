`timescale 1ns/1ps
// Two independently hardened FULL-shape port macros. No seam traffic or
// glue pipeline: queue arbitration, SRAM protection, credits and clocks belong
// to each half. Requires the protected/face-clock half ABI at source3b90d75fa.
// Legacy pair0ECC/oneclock evidence is not closure for this protected pairing.
module ot_hcoll_port2_tiles #(
    parameter integer PWT = 545, PAYLOAD_ECC=0, FACE_CK=0, MUT_MAP=0
) (
    input  wire             clk,
    input  wire             rst_n,
    input wire [1:0] ckf,
    output wire [1:0] ecc_ce,
    output wire [3:0] rx_ecc_drop,
    input  wire [1:0]       qp_push,
    input  wire [2*PWT-1:0] qp_din,
    input  wire [1:0]       qr_push,
    input  wire [2*PWT-1:0] qr_din,
    input  wire [1:0]       sw_cr_ret,
    output wire [1:0]       ph_tx_v,
    output wire [2*PWT-1:0] ph_tx_flit,
    input  wire [1:0]       ph_rx_v,
    input  wire [2*PWT-1:0] ph_rx_flit,
    output wire [1:0]       rb_v,
    output wire [2*PWT-1:0] rb_d,
    input  wire [1:0]       rb_cr,
    output wire [1:0]       stall,
    output wire [1:0]       fault
);
    for (genvar h = 0; h < 2; h = h + 1) begin : g_h
        (* keep_hierarchy *) ot_hcoll_port #(.PWT(PWT),.PAYLOAD_ECC(PAYLOAD_ECC),.FACE_CK(FACE_CK)) u_port (.clk(clk), .ckf(ckf[h]), .rst_n(rst_n), .ecc_ce(ecc_ce[h]), .rx_ecc_drop(rx_ecc_drop[h*2+:2]),
            .qp_push(qp_push[h]), .qp_din(qp_din[h*PWT +: PWT]), .qr_push(qr_push[h]), .qr_din(qr_din[h*PWT +: PWT]),
            .sw_cr_ret(sw_cr_ret[h]), .ph_tx_v(ph_tx_v[h]), .ph_tx_flit(ph_tx_flit[h*PWT +: PWT]),
            .ph_rx_v(ph_rx_v[h]), .ph_rx_flit(ph_rx_flit[(MUT_MAP ? 1-h : h)*PWT +: PWT]),
            .rb_v(rb_v[h]), .rb_d(rb_d[h*PWT +: PWT]), .rb_cr(rb_cr[h]), .stall(stall[h]), .fault(fault[h]));
    end
endmodule
