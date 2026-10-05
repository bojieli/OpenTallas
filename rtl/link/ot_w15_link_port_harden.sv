`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_w15_link_port_harden: hardening top for W15's link layer -- one die's port of
// one link: the transmit half of its outgoing direction and the receive half
// of its incoming direction (ot_w15_link_tx + ot_w15_link_rx), with every clock domain
// (core, link, recovered link) tied to ONE clock port.  Constraining all of
// them at the core period is conservative: each real domain runs at that
// period or slower (UCIe FDI 1.0 ns, board PCS 0.934 ns, core 0.92 ns), and the
// CDC paths are timed as if synchronous.  The hub-to-edge wire stages are NOT
// here (WIRE = 0 / 1): they are a routed repeated-wire crossing, hardened as
// ot_rom_express_link at the record width.  The PHY encoder/decoder pipelines
// (ENC/DEC stages) are hard IP stand-ins and excluded, except one decoder
// output register (DEC_STAGES 1) so the receive CRC is timed register to
// register (with --false-path-io an input-fed CRC would not be timed at all).
// ---------------------------------------------------------------------------
module ot_w15_link_port_harden #(
    parameter integer NVC          = 1,
    parameter integer PW           = 547,
    parameter integer CW           = 2,
    parameter integer TSW          = 16,
    parameter integer NL           = 2,
    parameter integer FRAME_CYCLES = 2,
    parameter integer AW_TX        = 3,
    parameter integer AW_RX        = 4,
    parameter integer HUBFC        = 0,
    parameter [NVC-1:0] GATED      = {{(NVC-1){1'b0}}, 1'b1},
    parameter integer BW           = TSW + NVC + CW + NVC * PW,
    parameter integer FRW          = FRAME_CYCLES * NL * (BW + 1) + 32
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [TSW-1:0]       now,
    // transmit
    input  wire [NVC-1:0]       tx_vc_valid,
    output wire [NVC-1:0]       tx_vc_ready,
    input  wire [NVC*PW-1:0]    tx_vc_rec,
    input  wire [CW-1:0]        tx_cr_pulse,
    output wire                 tx_f_valid,
    output wire [FRW-1:0]       tx_f_data,
    output wire                 tx_fault,
    // receive
    input  wire                 rx_f_valid,
    input  wire [FRW-1:0]       rx_f_data,
    input  wire                 det,
    input  wire [TSW-1:0]       drel,
    output wire [NVC-1:0]       rx_vc_valid,
    output wire [NVC*PW-1:0]    rx_vc_rec,
    output wire [CW-1:0]        rx_cr_pulse,
    output wire                 rx_fault
);
    wire f1, f2, f3;
    ot_w15_link_tx #(.NVC(NVC), .PW(PW), .CW(CW), .TSW(TSW), .WIRE(0), .AW(AW_TX), .NL(NL),
                 .FRAME_CYCLES(FRAME_CYCLES), .ENC_STAGES(0), .GATED(GATED), .HUBFC(HUBFC)) u_tx (
        .clk(clk), .rst_n(rst_n), .now(now), .vc_valid(tx_vc_valid), .vc_ready(tx_vc_ready), .vc_rec(tx_vc_rec),
        .cr_pulse(tx_cr_pulse), .lclk(clk), .lrst_n(rst_n), .f_valid(tx_f_valid), .f_data(tx_f_data),
        .fault(tx_fault), .stat_bundles(), .stat_gated_stall());
    ot_w15_link_rx #(.NVC(NVC), .PW(PW), .CW(CW), .TSW(TSW), .WIRE(1), .AW(AW_RX), .NL(NL),
                 .FRAME_CYCLES(FRAME_CYCLES), .DEC_STAGES(1)) u_rx (
        .rclk(clk), .rrst_n(rst_n), .f_valid(rx_f_valid), .f_data(rx_f_data), .clk(clk), .rst_n(rst_n),
        .now(now), .det(det), .drel(drel), .vc_valid(rx_vc_valid), .vc_rec(rx_vc_rec), .cr_pulse(rx_cr_pulse),
        .fault_crc(f1), .fault_late(f2), .fault_ovf(f3), .stat_min_age(), .stat_max_age(), .stat_max_wait(),
        .stat_bundles());
    assign rx_fault = f1 | f2 | f3;
endmodule
