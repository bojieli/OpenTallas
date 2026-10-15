module dsfd_stnv_3x1 (
    input wire [2:0] di0,
    output wire [2:0] do0,
    input wire [0:0] fi0,
    output wire [0:0] fo0
);
    ot_fwd_link_stage #(.W(3), .ENABLE(1'b1)) u_0_0 (.fclk_i(fi0[0]), .rst_n(1'b1), .i_v(1'b1), .i_d(di0[2:0]), .fclk_o(fo0[0]), .o_v(), .o_d(do0[2:0]));
endmodule
