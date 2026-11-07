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
// LOCKSAFE (S81.RESET, OWNER 2026-11-02 17:55 "SerDes soft warm reset = a local reset sequencer holding reset >= 64 edges
//   after the PMA clock restarts"; default 0 = the released column, pma_lock unused): 1 = the SHARED, gated sequencer
//   ot_pdie_pma_reset_hold (rtl/dsrom_sys/s81_link/ot_pdie_serdes_locksafe.sv, codex/serdes-locksafe-2047, the same module
//   HEAD's ot_s81hd_serdes_link_ls uses) holds the whole column reset: async assert on rst low or pma_lock low, release 2
//   recovered-clock (pma_rck) synchroniser edges + HOLD_EDGES recovered edges later (guard rck edge 66, native rs_r 68).
//   It sits inside the column so every child path (u_ptx, u_prx, u_enc, u_dec.*, u_rm) is unchanged; == the gated wrapper
//   ot_pdie_serdes_col_locksafe(LOCKSAFE=1) every edge (results/rtl/s81_reset_locksafe_1102).  9 FF, 0 mission cycles.
//   pma_lock = the PMA lock authority (S81 die IO lk_*_pma_lock from the modelled PMA, as HEAD's hd_serdes pad pma_lock).
module ot_pdie_serdes_col #(parameter integer PMA_LAT = 4, parameter integer TXL = 2, parameter integer MUT = 0,
                            parameter integer LOCKSAFE = 0, parameter integer HOLD_EDGES = 64) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck,
    input  wire          pma_lock
);
`ifdef OT_S81_RCK_RELAY4
    // The outer rate matcher keeps its native immediate reset. Its existing
    // lock guard must hold it reset while the delayed decoder calendar flushes.
    initial if (LOCKSAFE != 1 || HOLD_EDGES < 64)
        $error("RCK relay4 requires LOCKSAFE=1 and HOLD_EDGES>=64");
`endif
`ifdef OT_S81_SERDES_COL_PIN
    initial if (LOCKSAFE != 1 || HOLD_EDGES < 64)
        $error("TX PIN form requires LOCKSAFE=1 and HOLD_EDGES>=64");
`endif
    // ---- S81.RESET warm-reset sequencer (LOCKSAFE=1 only; region syn, on pma_rck)
    wire rst_g;
    generate if (LOCKSAFE != 0) begin : g_locksafe
        wire hold_ready;
        ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD_EDGES)) u_hold
            (.rst_n(rst), .pma_lock(pma_lock), .pma_rck(pma_rck), .core_rst_n(rst_g), .hold_ready(hold_ready));
    end else begin : g_legacy
        assign rst_g = rst;
    end endgenerate
    // ---- resets: one synchroniser per clock domain (rs_t in region tx, rs_r in region syn beside the PMA)
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst_g) if (!rst_g) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst_g) if (!rst_g) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
`ifdef OT_S81_SERDES_COL_RST_LOCAL
    // Same edge and async assertion as rs_t[1], local to each TX consumer.
    // No added mission or reset-calendar cycles; HOLD_EDGES contract unchanged.
    wire [2:0] rn_t_local;
    ot_s81_serdes_col_rst_local u_rst_t_local
        (.clk(clk), .rst_n(rst_g), .first_stage(rs_t[0]), .q(rn_t_local));
    wire rn_t_enc=rn_t_local[0], rn_t_rm=rn_t_local[1], rn_t_status=rn_t_local[2];
`else
    wire rn_t_enc=rn_t, rn_t_rm=rn_t, rn_t_status=rn_t;
`endif
    // ---- transmit: FEC encoder (closed tile) -> TX lane relay rows (clk) -> PMA TX
    wire e_v; wire [543:0] e_d; wire e_flt;
`ifdef OT_S81_SERDES_COL_PIN
    // Private RCK successor: three coherent TX input PIN cycles.  Reset is
    // registered by the same three edges, so the FEC frame calendar moves with
    // data and valid.  TXL is independently priced in the private kit profile.
    ot_s81_serdes_col_tx_pin #(.N(3)) u_tx_pin
        (.clk(clk), .rst_n(rn_t_enc), .tx_v(rn_t_enc), .tx_d(tx),
         .p_v(e_v), .p_d(e_d), .fault(e_flt));
`else
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(rn_t_enc), .tx_v(rn_t_enc), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
`endif
    wire [544:0] l_q;
    ot_pl_pad #(.W(545), .N((MUT == 8) ? TXL - 1 : TXL)) u_txl (.ck(clk), .d({e_v, e_d}), .q(l_q));
    // ---- analog PMA: two abstracts side by side along the edge (rx W half beside the dsyn W channel, tx E half under the
    //      TX lane drop), each with ONE clock (tx: the forwarded lane clock; rx: the recovered clock)
    wire [543:0] r_d;
`ifdef SYNTHESIS
    // S81-SERDES-PHY-2 10-31: the PMA hard macros (tools/mem_compiler/s81_pma_gen.py abstracts) have ONE fixed latency 4
    // and an unparameterised black box; PMA_LAT is a bench knob of the behavioural model only
    if (PMA_LAT != 4) begin : g_pma_lat_must_be_4
        initial $error("ot_pdie_serdes_col: PMA_LAT %0d != 4 has no hard PMA macro", PMA_LAT);
    end
    ot_s81_pma_txm u_ptx (.ck(clk), .d_v(l_q[544]), .d(l_q[543:0]), .pma_tx(pma_tx), .pma_tck(pma_tck));
    ot_s81_pma_rxm u_prx (.pma_rck(pma_rck), .pma_rx(pma_rx), .q(r_d));
`else
    ot_s81_pma_txm #(.LAT(PMA_LAT)) u_ptx (.ck(clk), .d_v(l_q[544]), .d(l_q[543:0]), .pma_tx(pma_tx), .pma_tck(pma_tck));
    ot_s81_pma_rxm #(.LAT(PMA_LAT)) u_prx (.pma_rck(pma_rck), .pma_rx(pma_rx), .q(r_d));
`endif
    // ---- receive: landed KP4 decoder (4 rck regions) -> rate matcher -> clk
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81_kp4_dec_native_flat_lp #(.MUT((MUT >= 1 && MUT <= 4) ? MUT : 0)) u_dec (.rst_n(rn_r), .p_v(rn_r), .p_d(r_d),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock),
        .n_corr(n_corr), .n_unc(n_unc), .n_relock(n_rl),
        .ck_syn(pma_rck), .ck_dly(pma_rck), .ck_chn(pma_rck), .ck_out(pma_rck));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t_rm), .r_d(rx),
        .fault(rm_flt));
    // ---- status (clk)
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t_status)
        if (!rn_t_status) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t_status) if (!rn_t_status) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt};
    assign st = st_q;
endmodule

`ifdef OT_S81_SERDES_COL_PIN
// One actual FEC encoder behind a coherent, fixed-latency input pipeline.
// The existing LOCKSAFE/HOLD_EDGES>=64 parent contract supplies the reset
// flush. Datapath stages have no reset; control/reset travel one edge per hop.
// N is fixed to 3 in the physical form; the parameter supports a small bench
// and seeded bypass mutant without changing the production encoder arithmetic.
module ot_s81_serdes_col_tx_pin #(parameter integer N = 3) (
    input wire clk,
    input wire rst_n,
    input wire tx_v,
    input wire [511:0] tx_d,
    output wire p_v,
    output wire [543:0] p_d,
    output wire fault
);
    initial if (N < 1) $error("TX PIN pipeline requires N>=1");
    (* keep *) reg [511:0] pin_q [0:N-1];
    reg [N-1:0] pin_v, pin_rst_n;
    integer j;
    always @(posedge clk) begin
        pin_q[0] <= tx_d;
        pin_v[0] <= tx_v;
        pin_rst_n[0] <= rst_n;
        for (j = 1; j < N; j = j + 1) begin
            pin_q[j] <= pin_q[j-1];
            pin_v[j] <= pin_v[j-1];
            pin_rst_n[j] <= pin_rst_n[j-1];
        end
    end
    ot_s81_kp4_enc u_enc
        (.clk(clk), .rst_n(pin_rst_n[N-1]), .tx_v(pin_v[N-1]), .tx_d(pin_q[N-1]),
         .p_v(p_v), .p_d(p_d), .fault(fault));
endmodule
`endif

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

`ifdef OT_S81_SERDES_COL_RST_LOCAL
// Three kept copies of the existing second synchronizer stage; this is not
// a new synchronizer depth. Consumer indices: encoder0, rate-matcher1, status2.
module ot_s81_serdes_col_rst_local (
    input wire clk, input wire rst_n, input wire first_stage,
    (* keep *) output reg [2:0] q
);
    (* keep *) always @(posedge clk or negedge rst_n)
        if (!rst_n) q <= 3'b000;
        else q <= {3{first_stage}};
endmodule
`endif
