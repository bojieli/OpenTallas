`timescale 1ns/1ps
// SIMULATION MODEL of the ot_qkvd_ucie_x64_phy hard macro (tools/qwen_kv_die/phy_gen.py): the far end is a second macro;
// a flit launched on tx_* appears on the FAR macro's rx_* 5 FDI cycles later (link_* ports carry it between the
// pair).  tx_up rises UP cycles after reset.  Not synthesised.
module ot_qkvd_ucie_x64_phy_model #(parameter integer LAT = 5, parameter integer UP = 16) (
    input  wire clk, input wire rst_n,
    output reg  tx_up,
    input  wire tx_v, input wire [547:0] tx_flit,
    output wire rx_v, output wire [547:0] rx_flit,
    output wire link_v, output wire [547:0] link_flit,      // to the far macro
    input  wire far_v,  input  wire [547:0] far_flit
);
    reg [LAT*549-1:0] pipe;
    integer n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pipe <= 0; n <= 0; tx_up <= 1'b0; end
        else begin pipe <= {pipe, far_v, far_flit}; n <= n + 1; if (n >= UP) tx_up <= 1'b1; end
    assign {rx_v, rx_flit} = pipe[LAT*549-1 -: 549];
    assign link_v = tx_v; assign link_flit = tx_flit;
endmodule
