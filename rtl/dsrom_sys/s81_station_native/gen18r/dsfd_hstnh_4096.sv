module dsfd_hstnh_4096 (
    input wire [0:0] ck,
    input wire [4095:0] di,
    output wire [4095:0] dq
);
    wire fck;   // common clock: the stage captures on negedge fclk_i = posedge ck
    ot_fwd_clk_inv u_ck (.a(ck[0]), .y(fck));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_0 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[511:0]), .fclk_o(), .o_v(), .o_d(dq[511:0]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_1 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[1023:512]), .fclk_o(), .o_v(), .o_d(dq[1023:512]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_2 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[1535:1024]), .fclk_o(), .o_v(), .o_d(dq[1535:1024]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_3 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[2047:1536]), .fclk_o(), .o_v(), .o_d(dq[2047:1536]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_4 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[2559:2048]), .fclk_o(), .o_v(), .o_d(dq[2559:2048]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_5 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[3071:2560]), .fclk_o(), .o_v(), .o_d(dq[3071:2560]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_6 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[3583:3072]), .fclk_o(), .o_v(), .o_d(dq[3583:3072]));
    ot_fwd_link_stage #(.W(512), .ENABLE(1'b1)) u_7 (.fclk_i(fck), .rst_n(1'b1), .i_v(1'b1), .i_d(di[4095:3584]), .fclk_o(), .o_v(), .o_d(dq[4095:3584]));
endmodule
