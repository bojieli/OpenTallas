// MESO-COUNT-1 tree-crossing bench: the child's count origin comes from the parent's forwarded start through
// ot_dp_landing_origin; the ring's reader uses that origin.  The C++ driver sweeps the child clock phase.
module tb_ca_tree #(parameter integer K = -2, parameter bit EDGE_FALL = 0) (
    input wire fclk, clk, p_start, rst_raw_n,
    input wire [31:0] d,
    output wire [31:0] q,
    output wire ready, fault, start
);
    ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(EDGE_FALL)) u_origin (.clk(clk), .rst_raw_n(rst_raw_n), .p_start(p_start), .start(start));
    ot_dp_clk_landing_ca #(.W(32), .DEPTH(4), .K(K)) u_landing (
        .fclk(fclk), .t_rst_n(p_start), .clk(clk), .rst_n(start), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
