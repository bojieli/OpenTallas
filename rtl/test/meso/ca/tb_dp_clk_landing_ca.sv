// MESO-COUNT-1 bench wrapper: a count-aligned landing with a sender count stamp as data.  The C++ driver places the
// sender origin (t_rst_n release, forwarded with fclk) and the receiver origin (rst_n release) so the lag
// L = t(receiver origin edge) + K*T - t(sender word 0 write) takes the value under test, at 1 ps resolution.
// HEAD-RINGHOLD-1 WFALL=1: the driver presents word n at fclk rise n (= its real launch edge) and the writer samples it
// on the fclk FALL T/2 later, so the driver's L is from the launch edge and the clean window is [1, DEPTH] T.  With the
// rising writer the driver's L is from the write edge = launch + T (window [0.5, DEPTH-0.5] T, i.e. [1.5, DEPTH+0.5] T
// from the launch): the fall write is T/2 earlier, every lag +T/2 (count_align_bind.verify(fall_ports)).
module tb_dp_clk_landing_ca #(parameter integer DEPTH = 4, parameter integer K = 2, parameter integer GUARD_HI = DEPTH,
                              parameter bit WFALL = 0) (
    input wire fclk, clk, t_rst_n, rst_n,
    input wire [31:0] d,
    output wire [31:0] q,
    output wire ready, fault
);
    ot_dp_clk_landing_ca #(.W(32), .DEPTH(DEPTH), .K(K), .GUARD_LO(0), .GUARD_HI(GUARD_HI), .WFALL(WFALL)) u_landing (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
