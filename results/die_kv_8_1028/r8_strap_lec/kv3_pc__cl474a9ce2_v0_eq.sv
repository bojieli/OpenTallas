// kv3_pc__cl474a9ce2 variant 0 instances ['pc_WN_0']
module gold (
    input wire clk,
    input wire [17:0] d0,
    output wire [17:0] q0
);
    assign q0 = d0;
endmodule
module gate (
    input wire clk,
    input wire [17:0] d0,
    output wire [17:0] q0
);
    wire [3:0] t0 = 4'd0;
    ot_dp_dly_cnt #(.W(18), .DMAX(4)) u0 (.clk(clk), .strap_cnt(t0), .d(d0), .q(q0));
endmodule
