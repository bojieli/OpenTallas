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
