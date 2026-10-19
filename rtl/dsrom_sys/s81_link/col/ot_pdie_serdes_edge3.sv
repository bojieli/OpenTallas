// BENCH CANDIDATE ONLY: edge-timed seams; physical integration remains blocked.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_pdie_serdes_col (TW-S81/SERDES 2026-10-19): ot_pdie_serdes as ONE hardened LANDED COLUMN parent, the die master
// that replaces the pin-only PHY abstract in the S81 lk_* slots (decision results/arch/s81_dv_1016/p4l_lkcol/
// lk_slot_decision.json; plan results/arch/s81_link_col_1019/serdes_column_plan.json).  SAME PORTS as ot_pdie_serdes.
//   259.2 um wide along the die edge: analog PMA abstracts u_ptx / u_prx (2 x ~125 x 2250, modelled: owner rule, hard PHY analog may be
//   behavioural) at one end, then N-S the closed digital tiles dsyn, ddly, dchn, dout, rate_match, enc (link attach end).
//   The kp4_dec 2x2 parent level is retired: its four tiles are direct children here, in their own rck clock REGIONS
//   (syn / dly / chn / out) with every seam LANDED (ot_s81_kp4_dec_native_flat_lp, lp.py: 11 landings D 4 / E 2, fixed
//   latency, no backpressure) -- landed-regions-standard-1018 (the 2x2 one-spine p2 gate failed the clock rule 83.5 /
//   87.2 ps > 80).  Region tx (clk): u_enc, the TX lane relay rows, the rate matcher read side, status.
//   rck <-> clk only through u_rm (gray FIFO) and the 2-flop status syncs, as ot_pdie_serdes.
// Latency vs ot_pdie_serdes (fixed, static schedule; the link layer above skips IDLE beats, the rate matcher absorbs it):
//   TX +TXL (2 relay rows over the ~1.1 mm enc -> PMA lane, reach 405 um); RX decoder +2 face pads +6 landing edges.
// MUT (bench only, 0 in every kit): passed to the landed decoder (1 = landing 0 bypassed, 2 = landing 0 read K+1,
//   3 = pad 0 short, 4 = syn reset run long); 8 = TX relay one row short (PMA sees the lane one cycle early: no effect on
//   data, kept as a probe only).
// ---------------------------------------------------------------------------------------------------------------
module ot_pdie_serdes_col #(parameter integer PMA_LAT = 4, parameter integer TXL = 2, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck
);
    // ---- resets: one synchroniser per clock domain (rs_t in region tx, rs_r in region syn beside the PMA)
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    // ---- transmit: FEC encoder (closed tile) -> TX lane relay rows (clk) -> PMA TX
    wire e_v; wire [543:0] e_d; wire e_flt;
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    wire [544:0] l_q;
    ot_pl_pad #(.W(545), .N((MUT == 8) ? TXL - 1 : TXL)) u_txl (.ck(clk), .d({e_v, e_d}), .q(l_q));
    // ---- analog PMA: two abstracts side by side along the edge (rx W half beside the dsyn W channel, tx E half under the
    //      TX lane drop), each with ONE clock (tx: the forwarded lane clock; rx: the recovered clock)
    wire [543:0] r_d;
    ot_s81_pma_txm #(.LAT(PMA_LAT)) u_ptx (.ck(clk), .d_v(l_q[544]), .d(l_q[543:0]), .pma_tx(pma_tx), .pma_tck(pma_tck));
    ot_s81_pma_rxm #(.LAT(PMA_LAT)) u_prx (.pma_rck(pma_rck), .pma_rx(pma_rx), .q(r_d));
    // ---- receive: landed KP4 decoder (4 rck regions) -> rate matcher -> clk
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81_kp4_dec_edge3 #(.MUT((MUT >= 1 && MUT <= 4) ? MUT : 0)) u_dec (.rst_n(rn_r), .p_v(rn_r), .p_d(r_d),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock),
        .n_corr(n_corr), .n_unc(n_unc), .n_relock(n_rl),
        .ck_syn(pma_rck), .ck_dly(pma_rck), .ck_chn(pma_rck), .ck_out(pma_rck));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx),
        .fault(rm_flt));
    // ---- status (clk)
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt};
    assign st = st_q;
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81_pma_txm / ot_s81_pma_rxm: the S81 SerDes ANALOG PMA as two hard abstracts (each ~125 x 2250 um, side by side in the
// column: pads on the die-edge face, digital face toward the KP4 stack), one clock each.  Behavioural model = the two
// ot_s81_pma_bm of ot_pdie_serdes: TX one 544-b word a cycle -> pads LAT cycles later, TX pad clock = the lane clock;
// RX pads -> recovered side LAT cycles later on the recovered clock pma_rck.  Not synthesis targets (abstracts in the kit).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_pma_txm #(parameter integer LAT = 4) (
    input  wire          ck,
    input  wire          d_v,
    input  wire [543:0]  d,
    output wire [543:0]  pma_tx,
    output wire          pma_tck
);
    ot_s81_pma_bm #(.W(544), .LAT(LAT)) u_m (.clk(ck), .d_v(d_v), .d(d), .q(pma_tx));
    assign pma_tck = ck;
endmodule

module ot_s81_pma_rxm #(parameter integer LAT = 4) (
    input  wire          pma_rck,
    input  wire [543:0]  pma_rx,
    output wire [543:0]  q
);
    ot_s81_pma_bm #(.W(544), .LAT(LAT)) u_m (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(q));
endmodule
