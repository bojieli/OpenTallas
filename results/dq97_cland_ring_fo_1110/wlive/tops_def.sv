// DIE-QC-97 RSTREP-1 default-parameter LEC: the old ot_dp_clk_landing_ca.sv (gold) vs the new one (gate), legacy
// instances exactly as bound today (rst_xn unconnected): cas as slw_fe_v2 u_cland_dd_ei, and the plain strap-less ca.
module lec_top (input wire fclk, t_rst_n, clk, rst_n, input wire [5:0] strap_k, input wire [548:0] d, input wire [39:0] d2,
                output wire [548:0] q, output wire ready, fault, output wire [39:0] q2, output wire ready2, fault2);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
    ot_dp_clk_landing_ca #(.W(40), .DEPTH(8), .K(5)) u2 (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .d(d2), .q(q2), .ready(ready2), .fault(fault2));
endmodule
