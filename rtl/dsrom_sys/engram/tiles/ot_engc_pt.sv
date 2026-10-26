`timescale 1ns/1ps
// ot_engc_pt (el1011-ds-misc/engram, 2026-10-11): PAIR TILE of the bank-1 chain of the all-tile dsfd_engram_c
// (replaces the 691 um band tile T_PBB, class 1).  Two ot_sram_1r1w_256x256_m2_r2c2 = groups 2k / 2k+1 of bank 1,
// k = 2 - pos (pos = hops from the T_IO end of the chain: P2 pos 0 / P1 pos 1 / P0 pos 2; a static strap, tied at the
// top).  Physical spec: el1011-ds-misc.log "PHYSICAL SPEC bank-1 PAIR CHAIN".
//   write + transit  W face pin flops -> E face (registered pass-through, no logic) ; own groups -> per-macro W3
//   read request     E face pin flops -> W face (registered pass-through)          ; own groups -> per-macro R2
//   read data        capture -> pair select (own, 4 edges after the request pin flop) -> delay 4 / 2 / 0 (pos 0/1/2)
//                    -> OR with rd_in (the west neighbour's r_d) -> r_d out flop (E face).  The delays make the three
//                    pairs' data meet the chain wavefront: r_d of P2 = request at P2's pin + 9 edges for every pair.
module ot_engc_pt (
    input  wire         ck,
    input  wire         rst,
    input  wire [1:0]   pos,
    input  wire [5:0]   wi_oh,
    input  wire [7:0]   wi_a,
    input  wire [255:0] wi_d,
    input  wire [319:0] xi_d,
    output wire [5:0]   wo_oh,
    output wire [7:0]   wo_a,
    output wire [255:0] wo_d,
    output wire [319:0] xo_d,
    input  wire [5:0]   rq_oh,
    input  wire [7:0]   rq_a,
    output wire [5:0]   rqo_oh,
    output wire [7:0]   rqo_a,
    input  wire [255:0] rd_in,
    output reg  [255:0] r_d
);
    reg [1:0] rs_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    // pin flops (datapath unreset; one-hots reset)
    reg [5:0] woh_p, roh_p; reg [7:0] wa_p, ra_p; reg [255:0] wd_p; reg [319:0] xd_p; reg [1:0] pos_q;
    always @(posedge ck or negedge rn) if (!rn) begin woh_p <= 6'd0; roh_p <= 6'd0; end
                                       else begin woh_p <= wi_oh; roh_p <= rq_oh; end
    always @(posedge ck) begin wa_p <= wi_a; ra_p <= rq_a; wd_p <= wi_d; xd_p <= xi_d; pos_q <= pos; end
    assign wo_oh = woh_p; assign wo_a = wa_p; assign wo_d = wd_p; assign xo_d = xd_p;
    assign rqo_oh = roh_p; assign rqo_a = ra_p;
    // own pair's selects (pos is static)
    wire [1:0] wsel = (pos_q == 2'd0) ? woh_p[5:4] : (pos_q == 2'd1) ? woh_p[3:2] : (pos_q == 2'd2) ? woh_p[1:0] : 2'b00;
    wire [1:0] rsel = (pos_q == 2'd0) ? roh_p[5:4] : (pos_q == 2'd1) ? roh_p[3:2] : (pos_q == 2'd2) ? roh_p[1:0] : 2'b00;
    wire [255:0] cap [0:1]; wire [1:0] sel3;
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_grp
        wire w3_v, r2_v; wire [7:0] w3_a, r2_a; wire [255:0] w3_d, rd_out;
        ot_v41_kreg #(.W(264), .AR(0)) u_w3d (.clk(ck), .arst_n(rn), .d({wd_p, wa_p}), .q({w3_d, w3_a}));
        ot_v41_kreg #(.W(1), .AR(1)) u_w3v (.clk(ck), .arst_n(rn), .d(wsel[g]), .q(w3_v));
        ot_v41_kreg #(.W(8), .AR(0)) u_r2a (.clk(ck), .arst_n(rn), .d(ra_p), .q(r2_a));
        ot_v41_kreg #(.W(1), .AR(1)) u_r2v (.clk(ck), .arst_n(rn), .d(rsel[g]), .q(r2_v));
        ot_sram_1r1w_256x256_m2_r2c2 u_sram(
            .clk(ck), .r_ce_in(r2_v), .r_addr_in(r2_a), .rd_out(rd_out),
            .w_ce_in(w3_v), .w_addr_in(w3_a), .wd_in(w3_d), .w_mask_in({256{1'b1}}),
            .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(16'd0));
        reg [255:0] cap_q; reg sm_q, s3_q;
        always @(posedge ck) cap_q <= rd_out;
        always @(posedge ck or negedge rn) if (!rn) begin sm_q <= 1'b0; s3_q <= 1'b0; end
                                           else begin sm_q <= r2_v; s3_q <= sm_q; end
        assign cap[g] = cap_q; assign sel3[g] = s3_q;
    end endgenerate
    reg [255:0] p_q, d1, d2, d3, d4;
`ifdef OT_ENGC_PB_MUT
    always @(posedge ck) p_q <= (sel3[0] | sel3[1]) ? cap[0] : 256'd0;      // negative control: odd group reads the even
`else
    always @(posedge ck) p_q <= (cap[0] & {256{sel3[0]}}) | (cap[1] & {256{sel3[1]}});
`endif
    always @(posedge ck) begin d1 <= p_q; d2 <= d1; d3 <= d2; d4 <= d3; end
    wire [255:0] own = (pos_q == 2'd0) ? d4 : (pos_q == 2'd1) ? d2 : p_q;
    always @(posedge ck) r_d <= own | rd_in;
endmodule

// two views of the same tile (pin plans differ: the head takes write + transit on its N face from T_WS)
module ot_engc_t_pth (input wire ck, rst, input wire [1:0] pos, input wire [5:0] wi_oh, input wire [7:0] wi_a,
    input wire [255:0] wi_d, input wire [319:0] xi_d, output wire [5:0] wo_oh, output wire [7:0] wo_a,
    output wire [255:0] wo_d, output wire [319:0] xo_d, input wire [5:0] rq_oh, input wire [7:0] rq_a,
    output wire [5:0] rqo_oh, output wire [7:0] rqo_a, input wire [255:0] rd_in, output wire [255:0] r_d);
    ot_engc_pt u_p (.ck(ck), .rst(rst), .pos(pos), .wi_oh(wi_oh), .wi_a(wi_a), .wi_d(wi_d), .xi_d(xi_d), .wo_oh(wo_oh),
        .wo_a(wo_a), .wo_d(wo_d), .xo_d(xo_d), .rq_oh(rq_oh), .rq_a(rq_a), .rqo_oh(rqo_oh), .rqo_a(rqo_a),
        .rd_in(rd_in), .r_d(r_d));
endmodule
module ot_engc_t_ptb (input wire ck, rst, input wire [1:0] pos, input wire [5:0] wi_oh, input wire [7:0] wi_a,
    input wire [255:0] wi_d, input wire [319:0] xi_d, output wire [5:0] wo_oh, output wire [7:0] wo_a,
    output wire [255:0] wo_d, output wire [319:0] xo_d, input wire [5:0] rq_oh, input wire [7:0] rq_a,
    output wire [5:0] rqo_oh, output wire [7:0] rqo_a, input wire [255:0] rd_in, output wire [255:0] r_d);
    ot_engc_pt u_p (.ck(ck), .rst(rst), .pos(pos), .wi_oh(wi_oh), .wi_a(wi_a), .wi_d(wi_d), .xi_d(xi_d), .wo_oh(wo_oh),
        .wo_a(wo_a), .wo_d(wo_d), .xo_d(xo_d), .rq_oh(rq_oh), .rq_a(rq_a), .rqo_oh(rqo_oh), .rqo_a(rqo_a),
        .rd_in(rd_in), .r_d(r_d));
endmodule
