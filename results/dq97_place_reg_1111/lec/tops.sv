// DIE-QC-97 PLACEREP LEC wrappers: real QC ring (slw_fe_v2 u_cland_dd_ei: cas W=549 DEPTH 4 WFALL 1 WREG 1 STATUS_REG 1 DSREP 2 RSTREP 4)
// gold = fanout_max 32 form without PLACEREP; gate = + PLACEREP(1); strap_k is a constant (tied strap)
module lec_gold_k5 (input wire fclk, t_rst_n, clk, rst_n, input wire [3:0] rst_xn, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .STATUS_REG(1), .DSREP(2), .RSTREP(4)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(6'd5), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gate_k5 (input wire fclk, t_rst_n, clk, rst_n, input wire [3:0] rst_xn, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .STATUS_REG(1), .DSREP(2), .RSTREP(4), .PLACEREP(1)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(6'd5), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gold_k13 (input wire fclk, t_rst_n, clk, rst_n, input wire [3:0] rst_xn, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .STATUS_REG(1), .DSREP(2), .RSTREP(4)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(6'd13), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gate_k13 (input wire fclk, t_rst_n, clk, rst_n, input wire [3:0] rst_xn, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .STATUS_REG(1), .DSREP(2), .RSTREP(4), .PLACEREP(1)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(6'd13), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gold_k38 (input wire fclk, t_rst_n, clk, rst_n, input wire [3:0] rst_xn, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .STATUS_REG(1), .DSREP(2), .RSTREP(4)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(6'd38), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gate_k38 (input wire fclk, t_rst_n, clk, rst_n, input wire [3:0] rst_xn, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .STATUS_REG(1), .DSREP(2), .RSTREP(4), .PLACEREP(1)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(6'd38), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
