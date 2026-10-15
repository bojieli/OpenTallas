module dsfd_hstnv_515 (
    input wire [0:0] ck,
    input wire [514:0] di,
    output wire [514:0] dq
);
    wire fck;   // common clock: the stage captures on negedge fclk_i = posedge ck
    ot_fwd_clk_inv u_ck (.a(ck[0]), .y(fck));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_0 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[511:0]), .fclk_o(), .o_v(), .o_d(dq[511:0]));
    ot_fwd_link_stage #(.W(3), .ENABLE(1'b1)) u_1 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[514:512]), .fclk_o(), .o_v(), .o_d(dq[514:512]));
endmodule
