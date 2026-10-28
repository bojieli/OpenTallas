// kv3_pc__cl87611e8b variant 1 instances ['pc_ES_0']
module gold (
    input wire clk,
    input wire [17:0] d0,
    output wire [17:0] q0
);
    ot_dp_dly #(.W(18), .D(1)) u0 (.clk(clk), .d(d0), .q(q0));
endmodule
module gate (
    input wire clk,
    input wire [17:0] d0,
    output wire [17:0] q0
);
    wire [3:0] t0 = 4'd1;
    ot_dp_dly_cnt #(.W(18), .DMAX(1)) u0 (.clk(clk), .strap_cnt(t0), .d(d0), .q(q0));
endmodule
