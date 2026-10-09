`timescale 1ns/1ps
// kv-die 2026-10-09: the KV die's end of the ROM die <-> KV die link (die master qkd_d2d): ot_qkvd_d2d configured as the
// KV end (TX RES / EMBD / HCTL = classes 4-6, RX CTL / Q / KVN / EMBQ = classes 0-3; buffers per CONTRACT.md).  The
// forwarded PLL clock and reset to the ROM die leave through their own bump cell (qkd_ckbump), not through this block.
module ot_qkvd_kv_end #(
    parameter integer W   = 528,
    parameter integer FW  = 548,
    parameter integer QD  = 48,                // sequencer Q buffer (= the adapter's Q die-face credits)
    parameter integer UCX = 48,                // RES / EMBD die-face buffers (cover the seq relay loop)
    parameter integer FCR_RES = 32,            // the ROM end's RES receive buffer
    parameter integer MUT = 0                  // bench only (ot_qkvd_d2d MUT)
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [2:0]      t_v,
    input  wire [3*W-1:0]  t_d,
    output wire [2:0]      t_cr,
    output wire [3:0]      r_v,
    output wire [4*W-1:0]  r_d,
    input  wire [3:0]      r_cr,
    input  wire            tx_up,
    output wire            tx_v,
    output wire [FW-1:0]   tx_flit,
    input  wire            rx_v,
    input  wire [FW-1:0]   rx_flit,
    output wire            fault,
    output wire [4:0]      fault_cause
);
    ot_qkvd_d2d #(.NT(3), .NR(4), .TXB(4), .RXB(0), .W(W), .IBD({8'd8, 8'd4, 8'(UCX), 8'(UCX)}),
                  .FCR({8'd0, 8'd4, 8'd32, 8'(FCR_RES)}), .RBD({8'd32, 8'd8, 8'd32, 8'd4}),
                  .OCR({8'd32, 8'd8, 8'(QD), 8'd4}), .MUT(MUT)) u_d2d (
        .clk(clk), .rst_n(rst_n), .t_v(t_v), .t_d(t_d), .t_cr(t_cr), .r_v(r_v), .r_d(r_d), .r_cr(r_cr),
        .tx_up(tx_up), .tx_v(tx_v), .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .fault(fault),
        .fault_cause(fault_cause));
endmodule
