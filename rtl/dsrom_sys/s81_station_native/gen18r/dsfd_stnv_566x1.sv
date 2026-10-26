module dsfd_stnv_566x1 (
    input wire [565:0] di0,
    output wire [565:0] do0,
    input wire [0:0] fi0,
    output wire [0:0] fn0,
    output wire [0:0] fo0
);
    wire fnb0; ot_fwd_clk_inv u_fn0a (.a(fi0[0]), .y(fnb0)); ot_fwd_clk_inv u_fn0b (.a(fnb0), .y(fn0[0]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_0_0 (.fclk_i(fi0[0]), .rst_n(1'b1), .i_v(1'b1), .i_d(di0[511:0]), .fclk_o(fo0[0]), .o_v(), .o_d(do0[511:0]));
    wire fx0_1;
    ot_fwd_link_stage #(.W(54), .ENABLE(1'b1)) u_0_1 (.fclk_i(fi0[0]), .rst_n(1'b1), .i_v(1'b1), .i_d(di0[565:512]), .fclk_o(fx0_1), .o_v(), .o_d(do0[565:512]));
endmodule
