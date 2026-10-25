`timescale 1ns/1ps
`ifndef KVS_FAR
`define KVS_FAR tb_kvslice   // the bench top holding the link far ends (sub-benches override)
`endif
// TOKj-KV 10-23: BENCH MODELS of the two off-die link PHYs of the KV die (owner 10-14: only PHY / off-chip modelled).
// Same ports as the as-built black boxes, compiled INSTEAD of them; the far ends live in the bench top (tb_kvslice):
//   ot_qfd_serdes_112g_x6_phy (host SerDes half; sys_SW W=522 = flit[521:0], sys_SE W=521 = flit[1042:522]):
//     die TX: tx_v/tx_flit are read by the bench (tb_kvslice deskews the halves by order on clk_phy, ot_fdi_join2 = the
//     board PHY's lane deskew, then the board port);
//     die RX: rx_v/rx_flit = the bench host's FDI flit (tb_kvslice.h2d_v / h2d_flit) after LAT (+ per-half skew) edges of
//     this PHY clock (= clk_phy, TOK-QK/C 10-24).
//     tx_up rises UP edges after rst_n.
//   ot_qkvd_ucie_x64_phy (UCIe d2d to the Qwen compute die, sys_c): rx = tb_kvslice.c2k_v / c2k_flit after LAT edges;
//     die TX visible to the bench on the ports (tb_kvslice samples tx_v/tx_flit).  tx_up rises UP edges after rst_n.
// No other logic: the PHY passes flits unchanged at a fixed latency (static link; flow control lives in the RTL ends).
module ot_qfd_serdes_112g_x6_phy #(parameter integer W = 522, parameter integer LAT = 4, parameter integer UP = 16,
                                   parameter integer MAXSK = 8) (
    input  wire         clk,
    input  wire         rst_n,
    output reg          tx_up,
    input  wire         tx_v,
    input  wire [W-1:0] tx_flit,
    output wire         rx_v,
    output wire [W-1:0] rx_flit
);
    // TOK-QK/C 10-24 (C2): clk is the PHY's OWN clock clk_phy (the bound sys_SW / sys_SE partitions now clock the PHY with
    // clk_clk_phy, behind ot_fdi_phy_cdc); the board far end (tb_kvslice.h2d_*) runs on the same clk_phy.  Each x6 half
    // has its own lane-to-lane skew: RX latency = LAT + SK phy cycles, SK = +PHY_SKEW_W / +PHY_SKEW_E (0..MAXSK, default 0;
    // +PHY_SKEW_RAND=<seed> draws both), fixed per run (in-order) -- the die must deskew the halves by order (ot_fdi_join2).
    localparam integer LO = (W == 522) ? 0 : 522;
    localparam integer N = LAT + MAXSK;
    reg [W:0] pipe [0:N-1];
    integer n, sk = 0, seed;
    initial begin
        if (W == 522) void'($value$plusargs("PHY_SKEW_W=%d", sk)); else void'($value$plusargs("PHY_SKEW_E=%d", sk));
        if ($value$plusargs("PHY_SKEW_RAND=%d", seed)) begin
            seed = seed + ((W == 522) ? 17 : 91);
            sk = $urandom(seed) % (MAXSK + 1);
        end
        if (sk < 0 || sk > MAXSK) $fatal(1, "PHY_SKEW %0d outside 0..%0d", sk, MAXSK);
        $display("SERDES_PHY_MODEL W %0d LAT %0d skew %0d", W, LAT, sk);
    end
    wire [W:0] src = {`KVS_FAR.h2d_v, `KVS_FAR.h2d_flit[LO +: W]};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin n <= 0; tx_up <= 1'b0; for (int i = 0; i < N; i++) pipe[i] <= '0; end
        else begin
            n <= n + 1; if (n >= UP) tx_up <= 1'b1;
            pipe[0] <= src; for (int i = 1; i < N; i++) pipe[i] <= pipe[i-1];
        end
    assign {rx_v, rx_flit} = pipe[LAT - 1 + sk];
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
