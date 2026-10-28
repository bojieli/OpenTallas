`timescale 1ns/1ps
// Head SerDes digital-link adapter. Exact reuse of the layer-die KP4/link
// implementation: coll_o0 is {live, fault, rx[511:0]}. PMA pads stay explicit;
// a physical head binding must publish them at its PHY boundary, never tie them.
// This adapter adds no register or latency cycle on the data path. Only the analog PMA remains
// behavioural, as in the existing released link bench.
//
// DIE-HEAD-9 PHY CDC form (COORD 06:09/06:30 rulings, 2026-10-28): the head instantiates ot_s81hd_pdie_serdes,
// a HEAD-local copy of ot_pdie_serdes (the shared file stays byte-identical: S81/HBM bundles pin it) whose every
// pma_rck <-> clk dependence sits in ONE crossing shell, ot_s81hd_serdes_cdc, in an already-approved form:
//   #1-#4  ot_s81_rate_match (reviewed Gray FIFO, unchanged shared source): pointer (a), storage (b), flt level
//   #5     lock  -> lk_s[0] -> lk_s[1]   1-bit level synchroniser (d); lock is captured by a shell-local pma_rck flop
//          lock_r first (+1 pma_rck cycle on the status bit `live` only, no data-path cycle), so the source is a flop
//          of the shell itself
//   #6     unc_r -> uf_s[0] -> uf_s[1]   1-bit level synchroniser (d)
//   #7     rst   -> ot_reset_sync u_rs_r (pma_rck) / u_rs_t (clk): reset pipe (c), replacing the inline rs_r / rs_t
//          (same 2-stage async-assert / synchronous-release logic)
// The shell is the CDC proof vehicle of tools/s81_head/head_serdes_cdc.py (reviewed_gray_fifos engine).
module ot_s81hd_serdes_link #(
    parameter integer PMA_LAT = 4
) (
    input wire ck,
    input wire rst_n,
    input wire [511:0] coll_i0,
    output wire [513:0] coll_o0,
    output wire [543:0] pma_tx,
    output wire pma_tck,
    input wire [543:0] pma_rx,
    input wire pma_rck
);
    wire [511:0] rx;
    wire [1:0] st;
    ot_s81hd_pdie_serdes #(.PMA_LAT(PMA_LAT)) u_link (
        .clk(ck), .rst(rst_n), .tx(coll_i0), .rx(rx), .st(st),
        .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck)
    );
`ifdef OT_S81HD_SERDES_MUT_STATUS
    assign coll_o0 = {st[0], st[1], rx};
`else
    assign coll_o0 = {st, rx};
`endif
endmodule

// HEAD-local ot_pdie_serdes: identical encoder / PMA / decoder / rate matcher; crossings in ot_s81hd_serdes_cdc.
module ot_s81hd_pdie_serdes #(parameter integer PMA_LAT = 4) (
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
    wire rn_t, rn_r;
    // ---- transmit: FEC encoder (ck) -> PMA TX model; pma_tck is the forwarded TX word clock (generated from clk)
    wire e_v; wire [543:0] e_d; wire e_flt;
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_ptx (.clk(clk), .d_v(e_v), .d(e_d), .q(pma_tx));
    assign pma_tck = clk;
    // ---- receive: PMA RX model (recovered word clock pma_rck) -> FEC decoder -> crossing shell -> ck
    wire [543:0] r_d;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81_kp4_dec u_dec (.clk(pma_rck), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .q_v(q_v), .q_d(q_d),
        .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc),
        .n_relock(n_rl));
    ot_s81hd_serdes_cdc u_cdc (.clk(clk), .pma_rck(pma_rck), .rst(rst), .rn_t(rn_t), .rn_r(rn_r), .q_v(q_v), .q_d(q_d),
        .q_first(q_first), .q_unc(q_unc), .lock(lock), .e_flt(e_flt), .rx(rx), .st(st));
endmodule

// Every pma_rck <-> clk dependence of the head SerDes link (the CDC proof vehicle).
module ot_s81hd_serdes_cdc #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          pma_rck,
    input  wire          rst,
    output wire          rn_t,
    output wire          rn_r,
    input  wire          q_v,
    input  wire [511:0]  q_d,
    input  wire          q_first,
    input  wire          q_unc,
    input  wire          lock,
    input  wire          e_flt,
    output wire [511:0]  rx,
    output wire [1:0]    st
);
    // #7 reset pipes (c): one ot_reset_sync per clock domain
    ot_reset_sync #(.ASYNC_STAGES(2)) u_rs_t (.clk(clk), .async_rst_n(rst), .sync_rst_n(rn_t));
    wire rn_r_sync;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_rs_r (.clk(pma_rck), .async_rst_n(rst), .sync_rst_n(rn_r_sync));
    reg [1:0] rs_r_mut;                    // MUT 6: the old inline pma_rck reset pipe (not the reviewed reset-pipe form)
    always @(posedge pma_rck or negedge rst) if (!rst) rs_r_mut <= 2'b00; else rs_r_mut <= {rs_r_mut[0], 1'b1};
    assign rn_r = (MUT == 6) ? rs_r_mut[1] : rn_r_sync;
    // pma_rck-side status sources (flops of this shell)
    reg lock_r, unc_r;
    always @(posedge pma_rck or negedge rn_r)
        if (!rn_r) begin lock_r <= 1'b0; unc_r <= 1'b0; end
        else begin lock_r <= lock; if (q_v && q_first && q_unc) unc_r <= 1'b1; end
    // #1-#4 reviewed rate matcher
    wire rm_flt;
    wire [511:0] rm_d;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rm_d),
        .fault(rm_flt));
    reg q_v_r; always @(posedge pma_rck) q_v_r <= q_v;          // MUT 4 only: a pma_rck data register outside the FIFO
    reg [511:0] rx_q;                                             // MUT 4: it reaches a clk register (unapproved)
    always @(posedge clk) rx_q <= {rm_d[511:1], rm_d[0] ^ q_v_r};
    assign rx = (MUT == 4) ? rx_q : rm_d;
    // #5 / #6 level synchronisers (d), clk side
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin
            lk_s <= {(MUT == 1) ? lk_s[0] ^ lock_r : lk_s[0], (MUT == 2) ? lock : lock_r};   // MUT 1 logic in stage 2 path; MUT 2 unsynchronised port
            uf_s <= {uf_s[0], unc_r};
        end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) st_q <= 2'b00;
        else st_q <= {(MUT == 3) ? lk_s[0] : lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt};   // MUT 3: metastable stage consumed
    assign st = st_q;
endmodule
