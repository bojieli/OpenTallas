// param_wrap form: sle_cland_w515_n_301 = ot_dp_clk_landing_cas #(.W(515), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)). Pure pass-through wrapper.
module sle_cland_w515_n_301 (
    input  wire fclk,
    input  wire t_rst_n,
    input  wire clk,
    input  wire rst_n,
    input  wire [5:0] strap_k,
    input  wire [514:0] d,
    output wire [514:0] q,
    output wire ready,
    output wire fault
);
    ot_dp_clk_landing_cas #(.W(515), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)) u_w (.fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
