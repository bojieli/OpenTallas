module cw_old(input clk,rst_n,input[265:0]unit_i0,output[264:0]cw,output epoch);
wire [264:0] unit_i0_q,unit_i0_is0_q; wire unit_i0_eq,unit_i0_is0_eq;
    ot_dp_st #(.W(265)) u_bin_unit_i0 (.clk(clk), .rst_n(rst_n), .d(unit_i0[264:0]), .ea(unit_i0[265]), .q(unit_i0_q), .eq(unit_i0_eq));
assign cw={unit_i0_q[264],unit_i0_q[263:8],unit_i0_q[7:0]}; assign epoch=unit_i0_eq;
endmodule
module cw_candidate(input clk,rst_n,input[265:0]unit_i0,output[264:0]cw,output epoch);
wire [264:0] unit_i0_q,unit_i0_is0_q; wire unit_i0_eq,unit_i0_is0_eq;
    ot_dp_st #(.W(265)) u_bin_unit_i0 (.clk(clk), .rst_n(rst_n), .d(unit_i0[264:0]), .ea(unit_i0[265]), .q(unit_i0_q), .eq(unit_i0_eq));
    ot_dp_st #(.W(265)) u_ist_unit_i0_0 (.clk(clk), .rst_n(rst_n), .d(unit_i0_q), .ea(unit_i0_eq), .q(unit_i0_is0_q), .eq(unit_i0_is0_eq));  // kit_istations: FIRM plan station
assign cw={unit_i0_is0_q[264],unit_i0_is0_q[263:8],unit_i0_is0_q[7:0]}; assign epoch=unit_i0_is0_eq;
endmodule
module cw_badreset(input clk,rst_n,input[265:0]unit_i0,output[264:0]cw,output epoch);
wire [264:0] unit_i0_q,unit_i0_is0_q; wire unit_i0_eq,unit_i0_is0_eq;
    ot_dp_st #(.W(265)) u_bin_unit_i0 (.clk(clk), .rst_n(rst_n), .d(unit_i0[264:0]), .ea(unit_i0[265]), .q(unit_i0_q), .eq(unit_i0_eq));
    ot_dp_st #(.W(265)) u_ist_unit_i0_0 (.clk(clk), .rst_n(1'b1), .d(unit_i0_q), .ea(unit_i0_eq), .q(unit_i0_is0_q), .eq(unit_i0_is0_eq));  // kit_istations: FIRM plan station
assign cw={unit_i0_is0_q[264],unit_i0_is0_q[263:8],unit_i0_is0_q[7:0]}; assign epoch=unit_i0_is0_eq;
endmodule
module cw_badpayload(input clk,rst_n,input[265:0]unit_i0,output[264:0]cw,output epoch);
wire [264:0] unit_i0_q,unit_i0_is0_q; wire unit_i0_eq,unit_i0_is0_eq;
    ot_dp_st #(.W(265)) u_bin_unit_i0 (.clk(clk), .rst_n(rst_n), .d(unit_i0[264:0]), .ea(unit_i0[265]), .q(unit_i0_q), .eq(unit_i0_eq));
    ot_dp_st #(.W(265)) u_ist_unit_i0_0 (.clk(clk), .rst_n(rst_n), .d(unit_i0_q ^ 265'b1), .ea(unit_i0_eq), .q(unit_i0_is0_q), .eq(unit_i0_is0_eq));  // kit_istations: FIRM plan station
assign cw={unit_i0_is0_q[264],unit_i0_is0_q[263:8],unit_i0_is0_q[7:0]}; assign epoch=unit_i0_is0_eq;
endmodule
