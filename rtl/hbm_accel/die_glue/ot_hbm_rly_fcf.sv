// HBM die relay, F1 FORWARDED-CLOCK FORK form (DIE-CLOCK rule 2026-10-16: a fork of a forwarded-clock chain is a relay
// tile with N branches; a clock-only fork tile would break the data / clock driver match).
// hbfd_rly_<W>_<flow>_fc_f<N> = the SAME register stage (ot_hbm_rly, unchanged) on clk_in, plus per branch k < N:
//   clk_out<k> = clk_in through ONE kept buffer (u_fcb_ck<k>; held off the CTS tree like fc2, reconnected to the root);
//   o<k>[b]    = r[b] through ONE kept buffer of the SAME cell (u_fcb_o<k>), side by side with clk_out<k> on the
//                branch's face.  Each branch drives one downstream station (one clk_in pin + <= 405 um).
// Buffers: explicit BUFx12f under SYNTHESIS ((* keep *); dont_touch by physical/hbm_rly_fc/fcf_dont_touch.tcl), identity
// in simulation.  Bench hooks: OT_HBM_RLY_MUT (in ot_hbm_rly), OT_HBM_RLY_FCF_MUT_CLKOUT=<k> (clk_out<k> held low).
`default_nettype none
module ot_hbm_rly_fcf #(
    parameter int W = 136,
    parameter int N = 2
) (
    input  wire           clk_in,
    input  wire           rs,
    input  wire [W-1:0]   i,
    output wire [N*W-1:0] o,
    output wire [N-1:0]   clk_out
);
    wire [W-1:0] q;
    ot_hbm_rly #(.W(W)) u_stage (.ck(clk_in), .rs(rs), .i(i), .o(q));
    genvar k, b;
    generate
        for (k = 0; k < N; k = k + 1) begin : g_br
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
