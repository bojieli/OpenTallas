module ot_dp_landing_relay (
    input  wire clk,
    input  wire rst_raw_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk) begin
        if (!rst_raw_n) q <= 1'b0;
        else q <= d;
    end
endmodule
