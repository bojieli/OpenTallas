
(* keep_hierarchy = "yes" *) module ot_dp_reserved_capture(input wire clk, input wire [2:0] d);
    (* keep = "true", dont_touch = "true" *) reg [2:0] q;
    always @(posedge clk) q <= d;
endmodule
