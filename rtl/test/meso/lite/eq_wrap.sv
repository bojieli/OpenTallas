// RING-LITE-1 EQ wrappers: the ring with ONLY its data port q observed (ready / fault are the declared difference of
// the lite form and are checked by the lock-step tb_lite).  Same wrapper for gold (LT 0) and gate (LT 1).
module eq_lite_cas #(parameter integer W = 2, parameter integer DEPTH = 4, parameter bit SR = 0, parameter bit WF = 0,
                     parameter bit WR = 0, parameter bit FR = 0, parameter bit NR = 1, parameter bit LT = 0) (
    input wire fclk, t_rst_n, clk, rst_n, input wire [$clog2(DEPTH)+3:0] strap_k, input wire [W-1:0] d,
    output wire [W-1:0] q);
    wire ready, fault;
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(DEPTH), .STATUS_REG(SR), .GUARD_REG(SR), .WFALL(WF), .WREG(WR), .FREG(FR), .NARROW(NR), .LITE(LT)) u_dut (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(1'b1), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module eq_lite_ca #(parameter integer W = 2, parameter integer DEPTH = 4, parameter integer K = 2, parameter bit NR = 1, parameter bit LT = 0) (
    input wire fclk, t_rst_n, clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    wire ready, fault;
    ot_dp_clk_landing_ca #(.W(W), .DEPTH(DEPTH), .K(K), .NARROW(NR), .LITE(LT)) u_dut (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
