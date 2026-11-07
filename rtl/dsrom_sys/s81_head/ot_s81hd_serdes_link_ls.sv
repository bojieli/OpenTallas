`timescale 1ns/1ps
// HEAD SerDes link adapter with the OWNER 2026-11-02 17:55 warm-reset contract:
// "SerDes soft warm reset = a local reset sequencer holding reset >= 64 edges after
// the PMA clock restarts". The sequencer is the shared, already-gated
// ot_pdie_pma_reset_hold (rtl/dsrom_sys/s81_link/ot_pdie_serdes_locksafe.sv,
// codex/serdes-locksafe-2047): async assert on rst_n low or pma_lock loss, two
// recovered-clock synchronizer edges, then HOLD_EDGES recovered edges before the
// unchanged ot_pdie_serdes sees its reset released. Mission path unchanged: zero
// added pipeline cycles; cost 9 FF (2 sync + 6 count + 1 ready) per link.
// ot_s81hd_serdes_link stays byte-identical for the existing kits. The core keeps
// instance name u_link so the counted hard child u_phy.u_link.u_dec.u_chn
// (ot_s81_kp4_dchn) keeps its path. LOCKSAFE=0 forwards rst_n (identity).
module ot_s81hd_serdes_link_ls #(
    parameter integer PMA_LAT = 4,
    parameter integer LOCKSAFE = 1,
    parameter integer HOLD_EDGES = 64
) (
    input wire ck,
    input wire rst_n,
    input wire pma_lock,
    input wire [511:0] coll_i0,
    output wire [513:0] coll_o0,
    output wire [543:0] pma_tx,
    output wire pma_tck,
    input wire [543:0] pma_rx,
    input wire pma_rck
);
    wire core_rst_n;
    generate if (LOCKSAFE != 0) begin : g_guard
        wire hold_ready;
        ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD_EDGES)) u_hold
            (.rst_n(rst_n), .pma_lock(pma_lock), .pma_rck(pma_rck),
             .core_rst_n(core_rst_n), .hold_ready(hold_ready));
    end else begin : g_legacy
        assign core_rst_n = rst_n;
    end endgenerate
    wire [511:0] rx;
    wire [1:0] st;
`ifdef OT_S81HD_SERDES_SC
    // DH81-SEQ 11-07: same sequencer on the opt-in SC form (ot_s81hd_serdes_sc.sv), same define and instance name as
    // ot_s81hd_serdes_link, so the hard children u_tx, u_dec.u_syn.u_bm0..2, u_dec.u_chn keep their paths. core_rst_n
    // reaches the rs_r/rs_t/rm_r/rm_l synchronisers and u_tx.rst; u_chn.rst_n stays rn_r = rs_r[1], edge 68.
    ot_s81hd_pdie_sc #(.PMA_LAT(PMA_LAT)) u_link (
        .clk(ck), .rst(core_rst_n), .tx(coll_i0), .rx(rx), .st(st),
        .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck)
    );
`else
    ot_pdie_serdes #(.PMA_LAT(PMA_LAT)) u_link (
        .clk(ck), .rst(core_rst_n), .tx(coll_i0), .rx(rx), .st(st),
        .pma_tx(pma_tx), .pma_tck(pma_tck), .pma_rx(pma_rx), .pma_rck(pma_rck)
    );
`endif
    assign coll_o0 = {st, rx};
endmodule
