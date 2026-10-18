// HBM die relay, F1 FORWARDED-CLOCK FORK form with the stage register REPLICATED per branch (ff3, 2026-10-16).
// ot_hbm_rly_fcf (one flop per bit driving all N branch buffers) fails the native launch budget on the wide class:
// the N branch groups sit 109-218 um apart along the face, so Q crosses that span before the far group's buffer
// (624 f3 launch 307 ps, f2 236.5 ps > 220).  Here every branch k has its OWN copy of the unchanged stage
// (ot_hbm_rly u_stage on clk_in, same reset relay, same OT_HBM_RLY_MUT hook) beside its own matched buffers:
// o<k> = r_k through one kept BUFx12f, clk_out<k> = clk_in through one kept BUFx12f (off the CTS tree).  Function is
// identical (every copy samples the same i on the same clk_in edge, same clear); i fans out to the N copies.
`default_nettype none
module ot_hbm_rly_fcfr #(
    parameter int W = 624,
    parameter int N = 2
) (
    input  wire           clk_in,
    input  wire           rs,
    input  wire [W-1:0]   i,
    output wire [N*W-1:0] o,
    output wire [N-1:0]   clk_out
);
    genvar k, b;
    generate
        for (k = 0; k < N; k = k + 1) begin : g_br
            wire [W-1:0] q;
            ot_hbm_rly #(.W(W)) u_stage (.ck(clk_in), .rs(rs), .i(i), .o(q));
`ifdef OT_HBM_RLY_FCF_MUT_CLKOUT
            if (k == `OT_HBM_RLY_FCF_MUT_CLKOUT) begin : g_mut
                assign clk_out[k] = 1'b0;
            end else begin : g_ck
                ot_hbm_rly_fc_buf u_fcb_ck (.a(clk_in), .y(clk_out[k]));
            end
`else
            ot_hbm_rly_fc_buf u_fcb_ck (.a(clk_in), .y(clk_out[k]));
`endif
            for (b = 0; b < W; b = b + 1) begin : g_ob
                ot_hbm_rly_fc_buf u_fcb_o (.a(q[b]), .y(o[k * W + b]));
            end
        end
    endgenerate
endmodule
`default_nettype wire
