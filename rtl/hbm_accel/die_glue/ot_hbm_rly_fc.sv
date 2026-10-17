// HBM die relay, F1 FORWARDED-CLOCK form (owner decision 2026-10-16 neighbour-relative clocking; form agreed with
// DIE-CLOCK: clk_in / clk_out, one in-tile clock buffer, matched output buffer, sink-root re-time at region boundaries).
// hbfd_rly_<W>_<flow>_fc = the SAME register stage as hbfd_rly_<W>_<flow> (ot_hbm_rly, instantiated unchanged: r <= i
// on posedge, asynchronous active-low clear rs, registered reset relay above 256 b, OT_HBM_RLY_MUT bench hook), clocked
// by clk_in, plus:
//   clk_out = clk_in through ONE kept clock buffer (OT_FC_CELL), the clock of the NEXT station on the chain;
//   o[b]    = r[b] through ONE kept buffer of the SAME cell, so data and clock leave the tile through identical drivers
//             side by side on the downstream face (per-hop hold ~ clk2q - t_hold, independent of the hop length).
// The buffers are explicit ASAP7 cells under SYNTHESIS ((* keep *); dont_touch at PRE_FLOORPLAN by
// physical/hbm_rly_fc/fc_dont_touch.tcl so remove_buffers / repair / resizing cannot alter or bypass them); in
// simulation they are identity.  OT_HBM_RLY_FC_MUT_CLKOUT (bench only): clk_out not driven by clk_in (held low).
`default_nettype none
module ot_hbm_rly_fc #(
    parameter int W = 136
) (
    input  wire         clk_in,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o,
    output wire         clk_out
);
    wire [W-1:0] q;
    ot_hbm_rly #(.W(W)) u_stage (.ck(clk_in), .rs(rs), .i(i), .o(q));
`ifdef OT_HBM_RLY_FC_MUT_CLKOUT
    assign clk_out = 1'b0;
`else
    ot_hbm_rly_fc_buf u_fcb_ck (.a(clk_in), .y(clk_out));
`endif
    genvar b;
    generate
        for (b = 0; b < W; b = b + 1) begin : g_ob
            ot_hbm_rly_fc_buf u_fcb_o (.a(q[b]), .y(o[b]));
        end
    endgenerate
endmodule

// the one forwarding / output driver cell (same master for clk_out and every o bit)
module ot_hbm_rly_fc_buf (input wire a, output wire y);
`ifdef SYNTHESIS
    (* keep *) BUFx12f_ASAP7_75t_R u_cell (.A(a), .Y(y));
`else
    assign y = a;
`endif
endmodule
`default_nettype wire
