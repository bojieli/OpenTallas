// kv3_pc_v3 variant 1 instances ['pc_EN_7', 'pc_WN_7']
module gold (
    input wire clk,
    input wire [0:0] d0,
    input wire [14:0] d1,
    output wire [0:0] q0,
    output wire [14:0] q1
);
    assign q0 = d0;
    ot_dp_dly #(.W(15), .D(2)) u1 (.clk(clk), .d(d1), .q(q1));
endmodule
module gate (
    input wire clk,
    input wire [0:0] d0,
    input wire [14:0] d1,
    output wire [0:0] q0,
    output wire [14:0] q1
);
    wire [3:0] t0 = 4'd0;
    ot_dp_dly_cnt #(.W(1), .DMAX(1)) u0 (.clk(clk), .strap_cnt(t0), .d(d0), .q(q0));
    wire [3:0] t1 = 4'd2;
    ot_dp_dly_cnt #(.W(15), .DMAX(2)) u1 (.clk(clk), .strap_cnt(t1), .d(d1), .q(q1));
endmodule
