module s81_egress_min(input wire clk, rst_n, input wire [275:0] raw, output wire [276:0] xtier_o0);
    ot_dp_st #(.W(276)) u_bout_xtier_o0 (.clk(clk), .rst_n(rst_n), .d(xtier_o0_is1_q), .ea(xtier_o0_is1_eq), .q(xtier_o0[275:0]), .eq(xtier_o0[276]));
    wire [275:0] xtier_o0_is0_q;
    wire xtier_o0_is0_eq;  // kit_istations
    wire [275:0] xtier_o0_is1_q;
    wire xtier_o0_is1_eq;  // kit_istations
    ot_dp_st #(.W(276)) u_ist_xtier_o0_0 (.clk(clk), .rst_n(rst_n), .d(raw), .ea(rst_n), .q(xtier_o0_is0_q), .eq(xtier_o0_is0_eq));  // kit_istations: FIRM plan station
    ot_dp_st #(.W(276)) u_ist_xtier_o0_1 (.clk(clk), .rst_n(rst_n), .d(xtier_o0_is0_q ^ 276'h1), .ea(xtier_o0_is0_eq), .q(xtier_o0_is1_q), .eq(xtier_o0_is1_eq));  // kit_istations: FIRM plan station
endmodule
