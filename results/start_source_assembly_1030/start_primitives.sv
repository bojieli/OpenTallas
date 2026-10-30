module ot_dp_landing_root #(
    parameter integer SETTLE = 64
) (
    input  wire clk,
    input  wire rst_raw_n,
    output reg  start,
    // DIE-HEAD-10 FSTART out: D-side of start (start_d(t) == start(t+1) while rst_raw_n is high), see origin_s
    output wire start_d
);
    localparam integer CW = $clog2(SETTLE + 1);
    reg [CW-1:0] n;
`ifdef OT_ROOT_MUTANT_EARLY
    assign start_d = (n == CW'(SETTLE - 1));   // MUTANT (fv only): one cycle early
`else
    assign start_d = (n == CW'(SETTLE));
`endif
    always @(posedge clk) begin
        if (!rst_raw_n) begin n <= 0; start <= 0; end
        else begin
            if (n != CW'(SETTLE)) n <= n + 1'b1;
            start <= (n == CW'(SETTLE));
        end
    end
`ifndef SYNTHESIS
    initial if (SETTLE < 1) $fatal(1, "root SETTLE must be >= 1");
`endif
endmodule

module ot_dp_landing_origin #(
    parameter integer PAD = 0,
    parameter bit EDGE_FALL = 0
) (
    input  wire clk,
    input  wire rst_raw_n,   // raw region reset (power-on / die reset), synchronous to clk
    input  wire p_start,     // parent's forwarded start (asynchronous to clk, monotonic 0 -> 1)
    output wire start        // region count origin: the ring readers' rst_n and the region's own start
);
    (* async_reg = "true" *) reg s0, s1;
    reg s2;
    wire s_in;
    if (EDGE_FALL) begin : g_fall
        (* async_reg = "true" *) reg sf;
        always @(negedge clk) sf <= p_start;
        assign s_in = sf;
    end else begin : g_rise
        assign s_in = p_start;
    end
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    if (PAD > 0) begin : g_pad
        reg [PAD-1:0] pd;
        always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PAD'({pd, s2});
        assign start = pd[PAD-1];
    end else begin : g_nopad
        assign start = s2;
    end
endmodule
