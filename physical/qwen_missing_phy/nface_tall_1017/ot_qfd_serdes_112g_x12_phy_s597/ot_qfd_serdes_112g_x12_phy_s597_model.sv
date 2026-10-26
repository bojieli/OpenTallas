`timescale 1ns/1ps
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
