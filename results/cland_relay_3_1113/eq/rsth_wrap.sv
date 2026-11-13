
module rsth_wrap #(parameter integer N = 10, parameter integer W = 568, parameter integer DEPTH = 4,
                   parameter bit WREG = 1, parameter integer DSREP = 8, parameter bit PLACEREP = 1,
                   parameter integer WRITE_CHUNK = 64, parameter bit STATUS_REG = 0) (
    input wire fclk, input wire t_rst_n, input wire clk, input wire start, input wire raw_n,
    input wire [$clog2(DEPTH)+3:0] strap_k, input wire [W-1:0] d,
    output wire [W-1:0] q, output wire ready, output wire fault);
    wire rs_q; wire [N-1:0] rs_x;
    ot_dp_landing_relay_rep #(.N(N)) u_rs (.clk(clk), .rst_raw_n(raw_n), .d(start), .q(rs_q), .qx(rs_x));
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(DEPTH), .WREG(WREG), .DSREP(DSREP), .WRITE_CHUNK(WRITE_CHUNK),
                            .STATUS_REG(STATUS_REG), .RSTREP(N), .PLACEREP(PLACEREP)) u_ring (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rs_q), .rst_xn(rs_x), .strap_k(strap_k), .d(d), .q(q),
        .ready(ready), .fault(fault));
endmodule
