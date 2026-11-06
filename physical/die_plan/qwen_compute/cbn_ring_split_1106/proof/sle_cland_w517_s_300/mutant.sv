// param_wrap form: sle_cland_w517_s_300 = ot_dp_clk_landing_cas #(.W(517), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)). Pure pass-through wrapper.
module sle_cland_w517_s_300 (
    input  wire fclk,
    input  wire t_rst_n,
    input  wire clk,
    input  wire rst_n,
    input  wire [5:0] strap_k,
    input  wire [516:0] d,
    output wire [516:0] q,
    output wire ready,
    output wire fault
);
    wire [516:0] q_raw;
    assign q = q_raw ^ 1;
    ot_dp_clk_landing_cas #(.W(517), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)) u_w (.fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q_raw), .ready(ready), .fault(fault));
endmodule
