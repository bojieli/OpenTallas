`timescale 1ns/1ps
// TOKj-KV 10-23: BENCH MODELS of the two off-die link PHYs of the KV die (owner 10-14: only PHY / off-chip modelled).
// Same ports as the as-built black boxes, compiled INSTEAD of them; the far ends live in the bench top (tb_kvslice):
//   ot_qfd_serdes_112g_x6_phy (host SerDes half; sys_SW W=522 = flit[521:0], sys_SE W=521 = flit[1042:522]):
//     die TX: tx_v/tx_flit are read by the bench (tb_kvslice.u_host joins the halves, rx_v = W.tx_v & E.tx_v);
//     die RX: rx_v/rx_flit = the bench host's FDI flit (tb_kvslice.h2d_v / h2d_flit) after LAT edges of this PHY clock.
//     tx_up rises UP edges after rst_n.
//   ot_qkvd_ucie_x64_phy (UCIe d2d to the Qwen compute die, sys_c): rx = tb_kvslice.c2k_v / c2k_flit after LAT edges;
//     die TX visible to the bench on the ports (tb_kvslice samples tx_v/tx_flit).  tx_up rises UP edges after rst_n.
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

module ot_qkvd_ucie_x64_phy #(parameter integer LAT = 5, parameter integer UP = 16) (
    input  wire         clk,
    input  wire         rst_n,
    output reg          tx_up,
    input  wire         tx_v,
    input  wire [582:0] tx_flit,
    output wire         rx_v,
    output wire [582:0] rx_flit
);
    reg [583:0] pipe [0:LAT-1];
    integer n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin n <= 0; tx_up <= 1'b0; for (int i = 0; i < LAT; i++) pipe[i] <= '0; end
        else begin
            n <= n + 1; if (n >= UP) tx_up <= 1'b1;
            pipe[0] <= {tb_kvslice.c2k_v, tb_kvslice.c2k_flit}; for (int i = 1; i < LAT; i++) pipe[i] <= pipe[i-1];
        end
    assign {rx_v, rx_flit} = pipe[LAT-1];
endmodule
