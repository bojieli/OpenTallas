// ot_dp_dly_cnt: max-capacity reset-less delay bank whose delay is a declared STATIC pad-count strap (OWNER 2026-10-28
// KV R8 decision: R8 data-alignment pad counts may be tied strap pins).  DMAX kept register stages (every copy of a
// partition type carries the same bank = the largest pad any copy needs, so the type is hardened once); strap_cnt is
// tied to a constant per instance at the parent and selects tap strap_cnt (0 = straight through, d).  A count above
// DMAX selects the last stage (defined function; the G0 tie audit allows only the declared counts).  Every used
// (W, DMAX, count) constant is LEC'd against ot_dp_dly #(W, D=count) (results/die_kv_7_1028/r8_strap/run_lec.py).
// Not a runtime selector: the strap is a parent-level constant, like the ID / K straps (OWNER 10-25 B, 12.15a).
(* keep_hierarchy = 1 *)
module ot_dp_dly_cnt #(parameter integer W = 1, parameter integer DMAX = 1) (
    input  wire         clk,
    input  wire [3:0]   strap_cnt,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* keep = 1 *) reg [W-1:0] r [0:DMAX-1];
    wire [W-1:0] tap [0:DMAX];
    assign tap[0] = d;
    genvar j;
    generate
        for (j = 0; j < DMAX; j = j + 1) begin : g_st
            if (j == 0) begin : g_first
                always @(posedge clk) r[0] <= d;
            end else begin : g_next
                always @(posedge clk) r[j] <= r[j-1];
            end
            assign tap[j+1] = r[j];
        end
    endgenerate
    assign q = (strap_cnt > DMAX) ? tap[DMAX] : tap[strap_cnt];
endmodule
