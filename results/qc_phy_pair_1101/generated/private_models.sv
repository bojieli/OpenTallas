`timescale 1ns/1fs
// SIMULATION MODEL of the ot_qkvd_ucie_x64_phy hard macro (tools/qwen_kv_die/phy_gen.py): the far end is a second macro;
// a flit launched on tx_* appears on the FAR macro's rx_* 5 FDI cycles later (link_* ports carry it between the
// pair).  tx_up rises UP cycles after reset.  Not synthesised.
// REGISTERED FDI PINS, as the lib states (setup/hold on every input, clk->q on every output; PATH-QC-PHYB 10-25): tx_*
// is captured by the macro's input register and leaves on the line side (link_*) from it; the far macro's LAT-1 stage
// pipe ends in its rx output register.  Pin-to-pin (tx_* -> far rx_*) stays LAT cycles (LAT >= 2).  A die binder
// may use these registers as the partition's boundary registers (tools/die_plan/hard_pinreg.py).
module ot_qkvd_ucie_x64_phy_model #(parameter integer LAT = 5, parameter integer UP = 16, parameter integer FW = 583) (
    input  wire clk, input wire rst_n,
    output reg  tx_up,
    input  wire tx_v, input wire [FW-1:0] tx_flit,
    output wire rx_v, output wire [FW-1:0] rx_flit,
    output wire link_v, output wire [FW-1:0] link_flit,      // to the far macro
    input  wire far_v,  input  wire [FW-1:0] far_flit
);
    reg [(LAT-1)*(FW+1)-1:0] pipe;
    reg          tx_v_q;
    reg [FW-1:0] tx_flit_q;
    integer n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pipe <= 0; n <= 0; tx_up <= 1'b0; tx_v_q <= 1'b0; tx_flit_q <= {FW{1'b0}}; end
        else begin
            pipe <= {pipe, far_v, far_flit}; n <= n + 1; if (n >= UP) tx_up <= 1'b1;
            tx_v_q <= tx_v; tx_flit_q <= tx_flit;
        end
    assign {rx_v, rx_flit} = pipe[(LAT-1)*(FW+1)-1 -: (FW+1)];
    assign link_v = tx_v_q; assign link_flit = tx_flit_q;
endmodule

`timescale 1ns/1fs
// SIMULATION MODEL of the ot_qfd_serdes_112g_x12_phy_s597 hard macro (tools/qwen_missing/link_phy_gen.py): the far end is a second macro;
// a flit launched on tx_* appears on the FAR macro's rx_* 223 FDI cycles later (link_* ports carry it between the
// pair).  tx_up rises UP cycles after reset.  Not synthesised.
// REGISTERED FDI PINS, as the lib states (setup/hold on every input, clk->q on every output; PATH-QC-PHYB 10-25): tx_*
// is captured by the macro's input register and leaves on the line side (link_*) from it; the far macro's LAT-1 stage
// pipe ends in its rx output register.  Pin-to-pin (tx_* -> far rx_*) stays LAT cycles (LAT >= 2).  A die binder
// may use these registers as the partition's boundary registers (tools/die_plan/hard_pinreg.py).
module ot_qfd_serdes_112g_x12_phy_s597_model #(parameter integer LAT = 223, parameter integer UP = 16, parameter integer FW = 597) (
    input  wire clk, input wire rst_n,
    output reg  tx_up,
    input  wire tx_v, input wire [FW-1:0] tx_flit,
    output wire rx_v, output wire [FW-1:0] rx_flit,
    output wire link_v, output wire [FW-1:0] link_flit,      // to the far macro
    input  wire far_v,  input  wire [FW-1:0] far_flit
);
    reg [(LAT-1)*(FW+1)-1:0] pipe;
    reg          tx_v_q;
    reg [FW-1:0] tx_flit_q;
    integer n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pipe <= 0; n <= 0; tx_up <= 1'b0; tx_v_q <= 1'b0; tx_flit_q <= {FW{1'b0}}; end
        else begin
            pipe <= {pipe, far_v, far_flit}; n <= n + 1; if (n >= UP) tx_up <= 1'b1;
            tx_v_q <= tx_v; tx_flit_q <= tx_flit;
        end
    assign {rx_v, rx_flit} = pipe[(LAT-1)*(FW+1)-1 -: (FW+1)];
    assign link_v = tx_v_q; assign link_flit = tx_flit_q;
endmodule

`ifdef STALE_UCIE
`timescale 1ns/1fs
// SIMULATION MODEL of the ot_qfd_ucie_x64_phy hard macro (tools/qwen_missing/link_phy_gen.py): the far end is a second macro;
// a flit launched on tx_* appears on the FAR macro's rx_* 4 FDI cycles later (link_* ports carry it between the
// pair).  tx_up rises UP cycles after reset.  Not synthesised.
module ot_qfd_ucie_x64_phy_model #(parameter integer LAT = 4, parameter integer UP = 16, parameter integer FW = 1043, parameter real LCLK_HALF_NS = 0.5) (
    output reg  lclk,                                       // QW-GEN5: PHY FDI clock output (own 1.0 GHz)
    input  wire clk, input wire rst_n,
    output reg  tx_up,
    input  wire tx_v, input wire [FW-1:0] tx_flit,
    output wire rx_v, output wire [FW-1:0] rx_flit,
    output wire link_v, output wire [FW-1:0] link_flit,      // to the far macro
    input  wire far_v,  input  wire [FW-1:0] far_flit
);
    initial lclk = 1'b0;
    always #(LCLK_HALF_NS) lclk = ~lclk;                   // free-running PHY clock (cycle model only)
    reg [LAT*(FW+1)-1:0] pipe;
    integer n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pipe <= 0; n <= 0; tx_up <= 1'b0; end
        else begin pipe <= {pipe, far_v, far_flit}; n <= n + 1; if (n >= UP) tx_up <= 1'b1; end
    assign {rx_v, rx_flit} = pipe[LAT*(FW+1)-1 -: (FW+1)];
    assign link_v = tx_v; assign link_flit = tx_flit;
endmodule

`endif

`timescale 1ns/1fs
// ot_qfd_ucie_x64_phy: licensed link PHY abstract, core-facing top FDI, boundary timing only (ASSUMED registered pins)
// Blackbox view for synthesis and place-and-route (the hard macro).

module ot_qfd_ucie_x64_phy (
    output wire lclk,   // QW-GEN5 10-20: the PHY FDI clock output (1.0 GHz), root of the die clk_ucie tree
    input wire clk,
    input wire rst_n,
    output wire tx_up,
    input wire tx_v,
    input wire [1042:0] tx_flit,
    output wire rx_v,
    output wire [1042:0] rx_flit
);

    // Private peer nets, connected only by tb_pair; no constant far endpoint.
    wire far_v, link_v;
    wire [1042:0] far_flit, link_flit;
`ifdef STALE_UCIE
    ot_qfd_ucie_x64_phy_model #(.FW(1043),.LAT(4),.UP(16)) u_transport (
        .lclk(lclk),.clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
        .rx_v(rx_v),.rx_flit(rx_flit),.link_v(link_v),.link_flit(link_flit),
        .far_v(far_v),.far_flit(far_flit));
`else
    reg generated_lclk=0;
    always #0.5 generated_lclk=~generated_lclk;
    assign lclk=generated_lclk;
    ot_qkvd_ucie_x64_phy_model #(.FW(1043),.LAT(4),.UP(16)) u_transport (
        .clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
        .rx_v(rx_v),.rx_flit(rx_flit),.link_v(link_v),.link_flit(link_flit),
        .far_v(far_v),.far_flit(far_flit));
`endif
endmodule

`timescale 1ns/1fs
// ot_qfd_serdes_112g_x12_phy_s597: licensed link PHY abstract, core-facing top FDI, boundary timing only (ASSUMED registered pins)
// Blackbox view for synthesis and place-and-route (the hard macro).

module ot_qfd_serdes_112g_x12_phy_s597 (
    input wire clk,
    input wire rst_n,
    output wire tx_up,
    input wire tx_v,
    input wire [596:0] tx_flit,
    output wire rx_v,
    output wire [596:0] rx_flit
);

    // Private peer nets, connected only by tb_pair; no constant far endpoint.
    wire far_v, link_v;
    wire [596:0] far_flit, link_flit;
    ot_qfd_serdes_112g_x12_phy_s597_model #(.FW(597),.LAT(223),.UP(16)) u_transport (
        .clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
        .rx_v(rx_v),.rx_flit(rx_flit),.link_v(link_v),.link_flit(link_flit),
        .far_v(far_v),.far_flit(far_flit));
endmodule
