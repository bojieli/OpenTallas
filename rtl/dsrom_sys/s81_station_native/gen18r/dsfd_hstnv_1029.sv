module dsfd_hstnv_1029 (
    input wire [0:0] ck,
    input wire [1028:0] di,
    output wire [1028:0] dq
);
    wire fck;   // common clock: the stage captures on negedge fclk_i = posedge ck
    ot_fwd_clk_inv u_ck (.a(ck[0]), .y(fck));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_0 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[511:0]), .fclk_o(), .o_v(), .o_d(dq[511:0]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_1 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[1023:512]), .fclk_o(), .o_v(), .o_d(dq[1023:512]));
    ot_fwd_link_stage #(.W(5), .ENABLE(1'b1)) u_2 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[1028:1024]), .fclk_o(), .o_v(), .o_d(dq[1028:1024]));
endmodule
