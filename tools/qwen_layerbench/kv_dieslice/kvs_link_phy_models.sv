`timescale 1ns/1ps
// TOKj-KV 10-23: BENCH MODELS of the two off-die link PHYs of the KV die (owner 10-14: only PHY / off-chip modelled).
// Same ports as the as-built black boxes, compiled INSTEAD of them; the far ends live in the bench top (tb_kvslice):
//   ot_qfd_serdes_112g_x6_phy (host SerDes half; sys_SW W=522 = flit[521:0], sys_SE W=521 = flit[1042:522]):
//     die TX: tx_v/tx_flit are read by the bench (tb_kvslice.u_host joins the halves, rx_v = W.tx_v & E.tx_v);
//     die RX: rx_v/rx_flit = the bench host's FDI flit (tb_kvslice.h2d_v / h2d_flit) after LAT edges of this PHY clock.
//     tx_up rises UP edges after rst_n.
//   ot_qkvd_ucie_x64_phy (UCIe d2d to the Qwen compute die, sys_c): the hard macro's own model (below), line side on the
//     die top ports sys_c_link_* / sys_c_far_*.
// No other logic: the PHY passes flits unchanged at a fixed latency (static link; flow control lives in the RTL ends).
module ot_qfd_serdes_112g_x6_phy #(parameter integer W = 522, parameter integer LAT = 4, parameter integer UP = 16) (
    input  wire         clk,
    input  wire         rst_n,
    output reg          tx_up,
    input  wire         tx_v,
    input  wire [W-1:0] tx_flit,
    output wire         rx_v,
    output wire [W-1:0] rx_flit
);
    localparam integer LO = (W == 522) ? 0 : 522;
    reg [W:0] pipe [0:LAT-1];
    integer n;
    wire [W:0] src = {tb_kvslice.h2d_v, tb_kvslice.h2d_flit[LO +: W]};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin n <= 0; tx_up <= 1'b0; for (int i = 0; i < LAT; i++) pipe[i] <= '0; end
        else begin
            n <= n + 1; if (n >= UP) tx_up <= 1'b1;
            pipe[0] <= src; for (int i = 1; i < LAT; i++) pipe[i] <= pipe[i-1];
        end
    assign {rx_v, rx_flit} = pipe[LAT-1];
endmodule

// TOK-KV-1 10-28: the UCIe d2d PHY is a hard macro with line-side (bump) ports link_* / far_* (bind: sys_c bump_ucie_rom_*
// -> the die top sys_c_link_* / sys_c_far_*).  The bench uses the macro's OWN simulation model
// (physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv, registered FDI pins, pin-to-pin LAT) for
// this end AND for the compute-die end (kvs_compute_end u_cphy): the pair latency is the macro law on both sides, no bench
// copy and no hierarchical reference into the bench.  Same ports as the black box ot_qkvd_ucie_x64_phy_bb.v.
module ot_qkvd_ucie_x64_phy #(parameter integer LAT = 5, parameter integer UP = 16) (
    input  wire         clk,
    input  wire         rst_n,
    output wire         tx_up,
    input  wire         tx_v,
    input  wire [582:0] tx_flit,
    output wire         rx_v,
    output wire [582:0] rx_flit,
    output wire         link_v,
    output wire [582:0] link_flit,
    input  wire         far_v,
    input  wire [582:0] far_flit
);
    ot_qkvd_ucie_x64_phy_model #(.LAT(LAT), .UP(UP), .FW(583)) u_m (.clk(clk), .rst_n(rst_n), .tx_up(tx_up),
        .tx_v(tx_v), .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit),
        .link_v(link_v), .link_flit(link_flit), .far_v(far_v), .far_flit(far_flit));
endmodule
