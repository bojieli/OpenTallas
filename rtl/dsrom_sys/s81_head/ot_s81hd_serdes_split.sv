`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DH58-RFRTL 2026-11-03 (HEAD RE-FORM batch l48rf, OWNER TWO-STRIKES; CLOSURE-LIST HEAD-029): hd_serdes split on its
// natural module boundary, the TX and RX halves of ot_pdie_serdes (OWNER 10-29 (A): ONE shared KP4 codeword over the six
// analog lanes is kept -- no decoder clones; this is a cut between the encoder side and the decoder side, nothing else):
//   hd_serdes_tx = ot_s81hd_serdes_tx: reset sync (ck) + ot_s81_kp4_enc + PMA TX model -> pads pma_tx / pma_tck
//   hd_serdes_rx = ot_s81hd_serdes_rx: reset syncs (ck, pma_rck) + PMA RX model + ot_s81_kp4_dec (incl the signed
//                  kp4_dchn core) + unc flag + ot_s81_rate_match (pma_rck -> ck) + status -> coll_o0 {st, rx}
// Instances, parameters and nets are the ones of ot_pdie_serdes (unchanged file, still used by S81), so the TX and RX
// data paths are bit- and cycle-exact; every edge of coll_o0 data / st live equals the unsplit core.
// Seam (one plan bus): e_flt_o (1 b, tx -> rx), the encoder's sticky-able fault, registered at the tx face and landed in
// rx: the status fault bit sees e_flt 2 edges later than in ot_pdie_serdes (fixed latency contract, fault-only; HEAD
// crossing latency table hd_serdes row).  rst_n reaches both halves (each has its own 2-flop ck synchroniser, released
// on the same edge as the unsplit rs_t; the reset relay delivers rst_n to both slots on the same edge).
// SPLIT_MUT (bench negative controls, 0 = production): 1 e_flt not landed, 2 e_flt seam one edge short (landing
// bypassed), 3 one extra PMA RX model edge.  The two ck reset synchronisers have no mutant: both release on the unsplit
// rs_t edge by construction, and every path they reset is idle (no decoded word, no fault) for many edges after it.
// coll_i0 (tx 512 b) lands in hd_serdes_tx, coll_o0 (514 b) leaves hd_serdes_rx.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_serdes_tx #(parameter integer PMA_LAT = 4, parameter integer EMUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [511:0]  coll_i0,
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    output wire          e_flt_o
);
    reg [1:0] rs_t;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    wire rn_t = rs_t[1];
    wire e_v; wire [543:0] e_d; wire e_flt;
    ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(ck), .rst_n(rn_t), .tx_v(rn_t), .tx_d(coll_i0), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_ptx (.clk(ck), .d_v(e_v), .d(e_d), .q(pma_tx));
    assign pma_tck = ck;
    (* keep = "true" *) reg ef_q;
    always @(posedge ck or negedge rn_t) if (!rn_t) ef_q <= 1'b0; else ef_q <= e_flt;
    assign e_flt_o = ef_q;
endmodule

module ot_s81hd_serdes_rx #(parameter integer PMA_LAT = 4, parameter integer DMUT = 0, parameter integer SPLIT_MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    output wire [513:0]  coll_o0,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck,
    input  wire          e_flt_i
);
    reg [1:0] rs_t, rs_r;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst_n) if (!rst_n) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    (* keep = "true" *) reg ef_l;
    always @(posedge ck or negedge rn_t) if (!rn_t) ef_l <= 1'b0; else ef_l <= (SPLIT_MUT == 1) ? 1'b0 : e_flt_i;
    wire [543:0] r_d;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT + ((SPLIT_MUT == 3) ? 1 : 0))) u_prx (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81_kp4_dec #(.MUT(DMUT)) u_dec (.clk(pma_rck), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .q_v(q_v), .q_d(q_d),
        .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc),
        .n_relock(n_rl));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt; wire [511:0] rx;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(ck), .rrst_n(rn_t), .r_d(rx),
        .fault(rm_flt));
    reg [1:0] lk_s, uf_s;
    always @(posedge ck or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge ck or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | ((SPLIT_MUT == 2) ? e_flt_i : ef_l)};
`ifdef OT_S81HD_SERDES_MUT_STATUS
    assign coll_o0 = {st_q[0], st_q[1], rx};
`else
    assign coll_o0 = {st_q, rx};
`endif
endmodule

// Bench / LEC reference composition (the die abuts the two halves; NOT a plan type).
module ot_s81hd_serdes_split_ref #(parameter integer PMA_LAT = 4, parameter integer EMUT = 0, parameter integer DMUT = 0,
                                   parameter integer SPLIT_MUT = 0) (
    input wire ck, input wire rst_n, input wire [511:0] coll_i0, output wire [513:0] coll_o0,
    output wire [543:0] pma_tx, output wire pma_tck, input wire [543:0] pma_rx, input wire pma_rck
);
    wire ef;
    ot_s81hd_serdes_tx #(.PMA_LAT(PMA_LAT), .EMUT(EMUT)) u_tx (.ck(ck), .rst_n(rst_n), .coll_i0(coll_i0), .pma_tx(pma_tx),
        .pma_tck(pma_tck), .e_flt_o(ef));
    ot_s81hd_serdes_rx #(.PMA_LAT(PMA_LAT), .DMUT(DMUT), .SPLIT_MUT(SPLIT_MUT)) u_rx (.ck(ck), .rst_n(rst_n),
        .coll_o0(coll_o0), .pma_rx(pma_rx), .pma_rck(pma_rck), .e_flt_i(ef));
endmodule
