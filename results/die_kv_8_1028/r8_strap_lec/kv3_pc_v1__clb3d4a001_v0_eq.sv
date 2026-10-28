// kv3_pc_v1__clb3d4a001 variant 0 instances ['pc_ES_6', 'pc_WN_6', 'pc_WS_6']
module gold (
    input wire clk,
    input wire [14:0] d0,
    input wire [15:0] d1,
    input wire [17:0] d2,
    output wire [14:0] q0,
    output wire [15:0] q1,
    output wire [17:0] q2
);
    assign q0 = d0;
    assign q1 = d1;
    assign q2 = d2;
endmodule
module gate (
    input wire clk,
    input wire [14:0] d0,
    input wire [15:0] d1,
    input wire [17:0] d2,
    output wire [14:0] q0,
    output wire [15:0] q1,
    output wire [17:0] q2
);
    wire [3:0] t0 = 4'd0;
    ot_dp_dly_cnt #(.W(15), .DMAX(4)) u0 (.clk(clk), .strap_cnt(t0), .d(d0), .q(q0));
    wire [3:0] t1 = 4'd0;
    ot_dp_dly_cnt #(.W(16), .DMAX(1)) u1 (.clk(clk), .strap_cnt(t1), .d(d1), .q(q1));
    wire [3:0] t2 = 4'd0;
    ot_dp_dly_cnt #(.W(18), .DMAX(9)) u2 (.clk(clk), .strap_cnt(t2), .d(d2), .q(q2));
endmodule
