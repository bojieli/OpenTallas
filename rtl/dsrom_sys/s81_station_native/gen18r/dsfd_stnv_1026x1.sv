module dsfd_stnv_1026x1 (
    input wire [1025:0] di0,
    output wire [1025:0] do0,
    input wire [0:0] fi0,
    output wire [0:0] fo0
);
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_0_0 (.fclk_i(fi0[0]), .rst_n(1'b1), .i_v(1'b1), .i_d(di0[511:0]), .fclk_o(fo0[0]), .o_v(), .o_d(do0[511:0]));
    wire fx0_1;
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_0_1 (.fclk_i(fi0[0]), .rst_n(1'b1), .i_v(1'b1), .i_d(di0[1023:512]), .fclk_o(fx0_1), .o_v(), .o_d(do0[1023:512]));
    wire fx0_2;
    ot_fwd_link_stage #(.W(2), .ENABLE(1'b1)) u_0_2 (.fclk_i(fi0[0]), .rst_n(1'b1), .i_v(1'b1), .i_d(di0[1025:1024]), .fclk_o(fx0_2), .o_v(), .o_d(do0[1025:1024]));
endmodule
