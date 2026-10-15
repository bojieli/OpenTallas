module dsfd_hstnv_2 (
    input wire [0:0] ck,
    input wire [1:0] di,
    output wire [1:0] dq
);
    wire fck;   // common clock: the stage captures on negedge fclk_i = posedge ck
    ot_fwd_clk_inv u_ck (.a(ck[0]), .y(fck));
    ot_fwd_link_stage #(.W(2), .ENABLE(1'b1)) u_0 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[1:0]), .fclk_o(), .o_v(), .o_d(dq[1:0]));
endmodule
