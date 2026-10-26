`default_nettype none
// Opt-in physical landing bank. Stage instances are stable placement identities;
// preserve them even when another bank has an equal logical prefix.
(* keep_hierarchy = 1, dont_touch = 1 *)
module ot_dp_landing_ff(input wire clk, input wire d, output wire q);
    (* keep = 1, dont_touch = 1 *) reg r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule
(* keep_hierarchy = 1, dont_touch = 1 *)
module ot_dp_landing_bank #(parameter integer W=1, parameter integer D=1)
    (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    initial if (W != 1 || D < 1) $fatal(1, "native landing bank requires W=1,D>=1");
    wire [D:0] stage;
    assign stage[0] = d[0];
    genvar j;
    generate for (j=0; j<D; j=j+1) begin : g_stage
        (* keep = 1, dont_touch = 1 *) ot_dp_landing_ff u_ff
            (.clk(clk), .d(stage[j]), .q(stage[j+1]));
    end endgenerate
    assign q[0] = stage[D];
endmodule
`default_nettype wire
