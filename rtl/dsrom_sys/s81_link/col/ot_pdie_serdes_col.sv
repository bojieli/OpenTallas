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
// RST_TREE (S81-SERDES-RST-TREE, DIE-S81-85 2026-11-09; default 1 only under `define OT_S81_SERDES_RST_TREE, else 0 = the
//   released column, byte-identical behaviour): the clk-domain reset rn_t = rs_t[1] was ONE flop driving every clk reset
//   pin of the column (u_rm read side 530 FF across ~1.3 mm, u_enc, status): serdes__t14 attempt_11 GRT TT recovery
//   rs_t[1] -> u_rm.r_d[495] -286 ps, 34 buffers.  1 = a REGISTERED fan-out tree: rs_t[1] -> 11 kept leaf flops (u_enc 1,
//   status 1, u_rm read control 1, u_rm r_d 8 x 64 bits), each a plain clk flop placed by its <= 64 loads; the whole clk
//   domain leaves reset exactly ONE clk edge later (a 3-stage synchroniser in effect).  The leaves have no reset of their
//   own: assertion reaches the loads one clk edge after rs_t clears (the die / LOCKSAFE reset holds >= 64 edges).  u_enc
//   takes rst_n AND tx_v from the same leaf, so its frame calendar moves with the TX beat stream by that one edge (lock-step
//   proof tb_s81_col_rst_tree: pma_tx(new, t+1) == pma_tx(old, t) with tx delayed one edge; RX beat sequence identical).
//   2 = bench mutant only (u_enc rst_n left on rs_t[1], tx_v on the leaf: frame calendar off by one -> lock-step FAIL).
//   Under OT_S81_RM_STAGED (+ RM_LOCAL4 / WFULL8, + RCK_RELAY4): u_rm is ot_s81_rate_match #(.RLEAF(1)) fed rn_t, its read-side
//   leaves (control 1 + rsel 8 x 64) live inside it (ot_pdie_serdes.sv); the column keeps the u_enc / status leaves.  The same
//   +1 clk edge for the whole clk domain; RELAY4's lock guard (LOCKSAFE=1, HOLD_EDGES >= 64) is unchanged and >> 1 edge.
//   3 (form vC, default under `define OT_S81_SERDES_RST_TREE2) = TWO registered stages: rs_t[1] -> 2 kept mid flops (rt_me ->
//   u_enc / status leaves, rt_mr -> u_rm read-side leaves) -> leaves; the whole clk domain +2 clk edges (serdes__t14 vB
//   residual: the 1.1 mm rs_t -> u_rm leaf trunk, ECO probe -234).  4 = bench mutant (vC with u_enc rst_n on the mid stage).
// RST_RT (form vC, default 1 under `define OT_S81_SERDES_RST_RETIME, LOCKSAFE != 0 only; 0 = unchanged): rs_t's clear is
//   no longer the u_hold AND (lock_sync[1] & rst_sync[1] & hold_ready, pma_rck flops in region syn: attempt_11 TT
//   lock_sync -> rs_t[0] recovery -83) but ONE kept pma_rck flop rq_t (async assert by that AND, release on the next
//   pma_rck edge) beside rs_t: the clk domain releases one pma_rck edge later; rs_r and the rck domain are unchanged.
//   0 data cycles (reset release only).
// LANE (HARD-S81-SERDES-1 2026-11-13; all four default 0 = the column unchanged, flop for flop): registered LANE ROWS for
//   the serdes lots whose PMA pair lies along the shore (2885.76 x 1226.88: the PMA digital face is 2.2 mm wide and
//   ~0.7 mm from the KP4 island, the coll pins ~1.3 mm from it).  serdes__t2 attempt_27: every worst path was a bare wire
//   (u_txl r[0] -> q 1674 ps of buffers, PMA face -> u_syn 4018 ps, u_rm r_d -> u_bout, u_bin -> u_enc).  Each lane gets
//   one ot_pl_pad row per 405 um hop (the kit hook serdes_lanes.tcl places every row FIRM on its per-bit lane):
//   LANE_PIN  clk rows coll pin register -> encoder (u_lpin; data, tx_v AND the encoder reset move together, as the
//             TX PIN form: needs LOCKSAFE=1, HOLD_EDGES >= 64).  pma_tx +LANE_PIN clk.
//   LANE_TXA  extra u_txl rows encoder -> PMA TX (on top of TXL / TXL4).  pma_tx +LANE_TXA clk.
//   LANE_RXI  pma_rck rows PMA RX q -> decoder (u_lrxi).  The rck reset synchroniser rs_r grows by LANE_RXI stages
//             (same async assert), so decoder, unc_r and the u_rm write side all release LANE_RXI edges later and see
//             the SAME words: the whole rck domain is the old one shifted by LANE_RXI pma_rck edges.
//   LANE_RXO  clk rows u_rm r_d / st -> rx / st ports (u_lrxo, no reset: rx reaches IDLE LANE_RXO edges after a reset).
//             rx, st +LANE_RXO clk.
//   `define OT_S81_SERDES_LANE (plan type verilog_defines) = the shore-lot set PIN 3 / TXA 4 / RXI 5 / RXO 3;
//   OT_S81_SERDES_LANE_<row>=<n> overrides one value (benches).
//   MUT 9 / 10 (bench only): 9 = rck reset not moved with the LANE_RXI rows, 10 = encoder reset not moved with LANE_PIN.
//   Lock-step proof tb_s81_col_lane (tools/s81_link/run_serdes_lane_bench.sh).
module ot_pdie_serdes_col #(parameter integer PMA_LAT = 4, parameter integer TXL = 2, parameter integer MUT = 0,
                            parameter integer LOCKSAFE = 0, parameter integer HOLD_EDGES = 64,
`ifdef OT_S81_SERDES_RST_TREE2
                            parameter integer RST_TREE = 3,
`elsif OT_S81_SERDES_RST_TREE
                            parameter integer RST_TREE = 1,
`else
                            parameter integer RST_TREE = 0,
`endif
`ifdef OT_S81_SERDES_RST_RETIME
                            parameter integer RST_RT = 1
`else
                            parameter integer RST_RT = 0
`endif
                            ,
`ifdef OT_S81_SERDES_LANE_PIN
                            parameter integer LANE_PIN = `OT_S81_SERDES_LANE_PIN,
`elsif OT_S81_SERDES_LANE
                            parameter integer LANE_PIN = 3,
`else
                            parameter integer LANE_PIN = 0,
`endif
`ifdef OT_S81_SERDES_LANE_TXA
                            parameter integer LANE_TXA = `OT_S81_SERDES_LANE_TXA,
`elsif OT_S81_SERDES_LANE
                            parameter integer LANE_TXA = 4,
`else
                            parameter integer LANE_TXA = 0,
`endif
`ifdef OT_S81_SERDES_LANE_RXI
                            parameter integer LANE_RXI = `OT_S81_SERDES_LANE_RXI,
`elsif OT_S81_SERDES_LANE
                            parameter integer LANE_RXI = 5,
`else
                            parameter integer LANE_RXI = 0,
`endif
`ifdef OT_S81_SERDES_LANE_RXO
                            parameter integer LANE_RXO = `OT_S81_SERDES_LANE_RXO
`elsif OT_S81_SERDES_LANE
                            parameter integer LANE_RXO = 3
`else
                            parameter integer LANE_RXO = 0
`endif
                            ) (
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
`ifdef OT_S81_RCK_REFORM
`ifndef OT_S81_SERDES_COL_PIN
    initial $error("RCK RE-FORM requires the TX PIN form (OT_S81_SERDES_COL_PIN)");
`endif
`endif
`ifdef OT_S81_SERDES_COL_PIN
    initial if (LOCKSAFE != 1 || HOLD_EDGES < 64)
        $error("TX PIN form requires LOCKSAFE=1 and HOLD_EDGES>=64");
`endif
    // ---- S81.RESET warm-reset sequencer (LOCKSAFE=1 only; region syn, on pma_rck)
    wire rst_g, rst_g_t;
    generate if (LOCKSAFE != 0) begin : g_locksafe
        wire hold_ready;
        ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD_EDGES)) u_hold
            (.rst_n(rst), .pma_lock(pma_lock), .pma_rck(pma_rck), .core_rst_n(rst_g), .hold_ready(hold_ready));
        if (RST_RT != 0) begin : g_rst_rt
            (* keep *) reg rq_t;
            always @(posedge pma_rck or negedge rst_g) if (!rst_g) rq_t <= 1'b0; else rq_t <= 1'b1;
            assign rst_g_t = rq_t;
        end else begin : g_rst_nort
            assign rst_g_t = rst_g;
        end
    end else begin : g_legacy
        if (RST_RT != 0) begin : g_rt_needs_ls
            initial $error("RST_RT requires LOCKSAFE != 0");
        end
        assign rst_g = rst; assign rst_g_t = rst;
    end endgenerate
    // ---- resets: one synchroniser per clock domain (rs_t in region tx, rs_r in region syn beside the PMA)
    initial if (LANE_PIN != 0 && (LOCKSAFE != 1 || HOLD_EDGES < 64))
        $error("LANE_PIN requires LOCKSAFE=1 and HOLD_EDGES>=64");
    reg [1:0] rs_t; reg [1+LANE_RXI:0] rs_r;
    always @(posedge clk or negedge rst_g_t) if (!rst_g_t) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst_g) if (!rst_g) rs_r <= {(2+LANE_RXI){1'b0}}; else rs_r <= {rs_r[LANE_RXI:0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[(MUT == 9) ? 1 : 1 + LANE_RXI];
    // ---- clk reset fan-out (RST_TREE): rn_te (TX encoder rst_n + tx_v), rn_ts (status), rn_tc / rn_td (u_rm read side)
    localparam integer RT_ND = 8;
    wire rn_te, rn_te_rst, rn_ts, rn_tc, rn_trm; wire [RT_ND-1:0] rn_td;
    generate if (RST_TREE != 0) begin : g_rst_tree
        wire rn_me, rn_mr;                                   // stage-1 sources: rn_t (1, 2) or the kept mid flops (3, 4)
        if (RST_TREE >= 3) begin : g_mid
            (* keep *) reg rt_me, rt_mr;
            always @(posedge clk) begin rt_me <= rn_t; rt_mr <= rn_t; end
            assign rn_me = rt_me; assign rn_mr = rt_mr;
        end else begin : g_nomid
            assign rn_me = rn_t; assign rn_mr = rn_t;
        end
        (* keep *) reg rt_e, rt_s;
        always @(posedge clk) begin rt_e <= rn_me; rt_s <= rn_me; end
        assign rn_te = rt_e; assign rn_ts = rt_s;
`ifdef OT_S81_RM_STAGED
        assign rn_tc = rn_mr; assign rn_td = {RT_ND{rn_mr}};    // u_rm makes its own read-side leaves (RLEAF) from rn_trm
`else
        (* keep *) reg rt_c;
        (* keep *) reg [RT_ND-1:0] rt_d;
        always @(posedge clk) begin rt_c <= rn_mr; rt_d <= {RT_ND{rn_mr}}; end
        assign rn_tc = rt_c; assign rn_td = rt_d;
`endif
        assign rn_trm = rn_mr;
        // 2 / 4 = bench mutants: encoder reset one stage early versus tx_v
        assign rn_te_rst = (RST_TREE == 2) ? rn_t : (RST_TREE == 4) ? rn_me : rt_e;
    end else begin : g_rst_flat
        assign rn_te = rn_t; assign rn_te_rst = rn_t; assign rn_ts = rn_t; assign rn_tc = rn_t; assign rn_td = {RT_ND{rn_t}};
        assign rn_trm = rn_t;
    end endgenerate
    // ---- transmit: FEC encoder (closed tile) -> TX lane relay rows (clk) -> PMA TX
    wire e_v; wire [543:0] e_d; wire e_flt;
`ifdef OT_S81_SERDES_COL_PIN
    initial if (LANE_PIN != 0) $error("LANE_PIN and the TX PIN form (OT_S81_SERDES_COL_PIN) are alternatives");
    // Private RCK successor: three coherent TX input PIN cycles.  Reset is
    // registered by the same three edges, so the FEC frame calendar moves with
    // data and valid.  TXL is independently priced in the private kit profile.
`ifdef OT_S81_RCK_REFORM
    // S81-RCK-11 RE-FORM: the same 3 PIN stages + encoder as the TX hard core ot_s81_rck_tx (ot_s81_rck_reform.sv)
    ot_s81_rck_tx u_tx_pin
        (.clk(clk), .rst_n(rn_te_rst), .tx_v(rn_te), .tx_d(tx),
         .p_v(e_v), .p_d(e_d), .fault(e_flt));
`else
    ot_s81_serdes_col_tx_pin #(.N(3)) u_tx_pin
        (.clk(clk), .rst_n(rn_te_rst), .tx_v(rn_te), .tx_d(tx),
         .p_v(e_v), .p_d(e_d), .fault(e_flt));
`endif
`else
    // LANE_PIN rows (0 = wires): data, valid and the encoder reset on the same edges
    wire [511:0] lp_d; wire lp_v, lp_rst;
    ot_pl_pad #(.W(514), .N(LANE_PIN)) u_lpin (.ck(clk), .d({rn_te_rst, rn_te, tx}), .q({lp_rst, lp_v, lp_d}));
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n((MUT == 10) ? rn_te_rst : lp_rst), .tx_v(lp_v), .tx_d(lp_d), .p_v(e_v), .p_d(e_d),
        .fault(e_flt));
`endif
    wire [544:0] l_q;
`ifdef OT_S81_SERDES_TXL4
    // S81-SERDES-TXL4 (DIE-S81-85 2026-11-09): opt-in, two more u_txl relay rows (TX +2 clk).  Measured on serdes 4_cts/G2 kits:
    // the row 0 -> last row hop spans up to 2.2-2.4 mm and takes data 1020-1514 ps (833 ps period); wirelength-driven GPL
    // leaves the rows at the encoder and at the pad.  Rows 1 and 2 are the hop stations (place at 1/3 and 2/3 of the span).
    localparam integer TXL_N = TXL + 2;
`else
    localparam integer TXL_N = TXL;
`endif
    ot_pl_pad #(.W(545), .N(((MUT == 8) ? TXL_N - 1 : TXL_N) + LANE_TXA)) u_txl (.ck(clk), .d({e_v, e_d}), .q(l_q));
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
    // ---- LANE_RXI rows (0 = wires): PMA RX face -> decoder, one 544-b word an edge; rs_r carries the same edges
    wire [543:0] r_dl;
    ot_pl_pad #(.W(544), .N(LANE_RXI)) u_lrxi (.ck(pma_rck), .d(r_d), .q(r_dl));
    // ---- receive: landed KP4 decoder (4 rck regions) -> rate matcher -> clk
    wire [511:0] rx_m;
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
`ifdef OT_S81_RCK_REFORM
    // S81-RCK-11 RE-FORM: same ports / cycles, regrouped into the RX-SYN + RX-BACK hard cores (ot_s81_rck_reform.sv)
    ot_s81_rck_dec #(.MUT((MUT >= 1 && MUT <= 4) ? MUT : 0)) u_dec (
`else
    ot_s81_kp4_dec_native_flat_lp #(.MUT((MUT >= 1 && MUT <= 4) ? MUT : 0)) u_dec (
`endif
        .rst_n(rn_r), .p_v(rn_r), .p_d(r_dl),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock),
        .n_corr(n_corr), .n_unc(n_unc), .n_relock(n_rl),
        .ck_syn(pma_rck), .ck_dly(pma_rck), .ck_chn(pma_rck), .ck_out(pma_rck));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
`ifdef OT_S81_RM_STAGED
    ot_s81_rate_match #(.RLEAF((RST_TREE != 0) ? 1 : 0)) u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk),
        .rrst_n(rn_trm), .r_d(rx_m), .fault(rm_flt));
`elsif OT_S81_SERDES_RST_TREE
    // same instance name; with RST_TREE=0 every leaf input is rn_t (== ot_s81_rate_match, tb_s81_col_rst_tree RM compare)
    ot_s81_rate_match_rt #(.NRD(RT_ND)) u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk),
        .rrst_nc(rn_tc), .rrst_nd(rn_td), .r_d(rx_m), .fault(rm_flt));
`else
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx_m),
        .fault(rm_flt));
`endif
    // ---- status (clk)
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_ts)
        if (!rn_ts) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_ts) if (!rn_ts) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt};
    // ---- LANE_RXO rows (0 = wires): u_rm read side / status -> the coll_o pin register
    ot_pl_pad #(.W(514), .N(LANE_RXO)) u_lrxo (.ck(clk), .d({st_q, rx_m}), .q({st, rx}));
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

`ifdef OT_S81_SERDES_RST_TREE
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_rate_match_rt (S81-SERDES-RST-TREE): ot_s81_rate_match (ot_pdie_serdes.sv, base form) with the read-side reset split
// over the column's reset leaves: rrst_nc = read control (wp_g1/wp_g2, rp, rp_g, fault sync f1/f2), rrst_nd[j] = r_d slice j
// (512/NRD bits each, one leaf per slice, <= 64 reset pins a leaf).  Same registers, same next-state logic, same reset
// values; all rrst_n* tied together == ot_s81_rate_match every edge.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_rate_match_rt #(parameter integer NRD = 8) (
    input  wire            wclk, wrst_n,
    input  wire            w_v,
    input  wire [511:0]    w_d,
    input  wire            rclk, rrst_nc,
    input  wire [NRD-1:0]  rrst_nd,
    output wire [511:0]    r_d,
    output wire            fault
);
    localparam integer SW = 512 / NRD;
    initial if (SW * NRD != 512) $error("ot_s81_rate_match_rt: NRD must divide 512");
    reg  [511:0] mem [0:7];
    reg  [3:0] wp, rp, wp_g, rp_g;
    reg  [3:0] rp_g1, rp_g2, wp_g1, wp_g2;
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_g; rp_g2 <= rp_g1; end
    always @(posedge rclk or negedge rrst_nc) if (!rrst_nc) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_g; wp_g2 <= wp_g1; end
    wire [3:0] fill_w = wp - g2b(rp_g2);
    wire idle = w_d[1] && !w_d[0];
    wire full = fill_w == 4'd8;
    wire push = w_v && !full && !(idle && fill_w >= 4'd6);
    reg flt;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end
        else begin
            if (push) begin mem[wp[2:0]] <= w_d; wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    wire empty = g2b(wp_g2) == rp;
    always @(posedge rclk or negedge rrst_nc)
        if (!rrst_nc) begin rp <= 0; rp_g <= 0; end
        else if (!empty) begin rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
    wire [511:0] rd_n = empty ? 512'd2 : mem[rp[2:0]];   // IDLE beat: bit 1 set, no marker, no reverse frame, no slot bits
    genvar gs;
    generate for (gs = 0; gs < NRD; gs = gs + 1) begin : g_rd
        reg [SW-1:0] q;
        always @(posedge rclk or negedge rrst_nd[gs])
            if (!rrst_nd[gs]) q <= 512'd2 >> (gs * SW);
            else q <= rd_n[gs * SW +: SW];
        assign r_d[gs * SW +: SW] = q;
    end endgenerate
    reg f1, f2; always @(posedge rclk or negedge rrst_nc) if (!rrst_nc) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
`endif
