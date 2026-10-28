// kv3_pc_v3 variant 2 instances ['pc_ES_7']
module gold (
    input wire clk,
    input wire [0:0] d0,
    input wire [14:0] d1,
    output wire [0:0] q0,
    output wire [14:0] q1
);
    ot_dp_dly #(.W(1), .D(1)) u0 (.clk(clk), .d(d0), .q(q0));
    assign q1 = d1;
endmodule
module gate (
    input wire clk,
    input wire [0:0] d0,
    input wire [14:0] d1,
    output wire [0:0] q0,
    output wire [14:0] q1
);
    wire [3:0] t0 = 4'd1;
    ot_dp_dly_cnt #(.W(1), .DMAX(1)) u0 (.clk(clk), .strap_cnt(t0), .d(d0), .q(q0));
    wire [3:0] t1 = 4'd0;
    ot_dp_dly_cnt #(.W(15), .DMAX(2)) u1 (.clk(clk), .strap_cnt(t1), .d(d1), .q(q1));
endmodule
