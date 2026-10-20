`timescale 1ns/1ps
module ot_hbm_hc_tail_reset_local (
    input wire clk, rst_n_in,
    output wire [2:0] rst_n
);
    (* async_reg = "true", keep = "true", dont_touch = "true" *) reg [1:0] sync_q;
    (* keep = "true", dont_touch = "true" *) reg [2:0] region_q;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) sync_q <= 2'b00;
        else sync_q <= {sync_q[0], 1'b1};
    always @(posedge clk or negedge sync_q[0])
        if (!sync_q[0]) region_q <= 3'b000;
        else region_q <= {3{sync_q[1]}};
    assign rst_n = region_q;
endmodule
`default_nettype wire
