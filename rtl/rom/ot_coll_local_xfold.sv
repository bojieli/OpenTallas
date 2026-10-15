`timescale 1ns/1ps
// Cross-fold source selection and the real rank-ordered FP32 fold share one
// physical wrapper. The four original RST=0 rank selects stay registered on
// ctl_ck; raw payloads reach the fold's existing input pin registers without
// another data edge. fold_ck is the original fold root. Their phi-R relation
// and all raw-input/fold-child routes require physical qualification.
// The archived ot_coll_fold_slice master and its views remain unchanged.
module ot_coll_local_xfold #(
    parameter integer MUT_RANK = 0
) (
    input wire ctl_ck,
    input wire fold_ck,
    input wire rst_n,
    input wire [1:0] pkg_s,
    input wire red_in,
    input wire [127:0] td,
    input wire [127:0] sr0,
    input wire [127:0] sr1,
    input wire [127:0] sr2,
    output wire [127:0] sum,
    output wire v_out,
    output wire e_out
);
    wire [511:0] src;
    genvar rank;
    generate for (rank = 0; rank < 4; rank = rank + 1) begin : g_rank
        wire [1:0] jqs = 2'(rank) - pkg_s + 2'd3;
        // RST=0 in the original ot_coll_rep_reg: no new data/control reset.
        (* keep = "true" *) reg [3:0] sel;
        always @(posedge ctl_ck)
            sel <= {2'(rank) == pkg_s,
                    (2'(rank) != pkg_s) && jqs == 2'd2,
                    (2'(rank) != pkg_s) && jqs == 2'd1,
                    (2'(rank) != pkg_s) && jqs == 2'd0};
        assign src[128*rank +: 128] = (td  & {128{sel[3]}})
                                           | (sr2 & {128{sel[2]}})
                                           | (sr1 & {128{sel[1]}})
                                           | (sr0 & {128{sel[0]}});
    end endgenerate
    // Same rejecting rank-1/rank-2 swap as OT_TP8S_MUT_RANK in the parent.
    wire [511:0] ranked_src = MUT_RANK ? {src[511:384], src[255:128], src[383:256], src[127:0]} : src;
    (* keep_hierarchy = "yes" *) ot_coll_fold_slice #(.N(4), .ADD_LAT(7), .SEAM(1)) u_fold (
        .clk(fold_ck), .rst_n(rst_n), .red_in(red_in), .src(ranked_src),
        .sum(sum), .v_out(v_out), .e_out(e_out));
endmodule
