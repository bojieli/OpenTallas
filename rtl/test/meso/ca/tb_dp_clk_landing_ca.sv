// MESO-COUNT-1 bench wrapper: a count-aligned landing with a sender count stamp as data.  The C++ driver places the
// sender origin (t_rst_n release, forwarded with fclk) and the receiver origin (rst_n release) so the lag
// L = t(receiver origin edge) + K*T - t(sender word 0 write) takes the value under test, at 1 ps resolution.
module tb_dp_clk_landing_ca #(parameter integer DEPTH = 4, parameter integer K = 2, parameter integer GUARD_HI = DEPTH) (
    input wire fclk, clk, t_rst_n, rst_n,
    input wire [31:0] d,
    output wire [31:0] q,
    output wire ready, fault
);
    ot_dp_clk_landing_ca #(.W(32), .DEPTH(DEPTH), .K(K), .GUARD_LO(0), .GUARD_HI(GUARD_HI)) u_landing (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
