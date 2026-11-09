`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// S81 die-to-die link macros as REAL digital link layers over a behavioural analog PMA (s81-die-rtl-bind 2026-10-14,
// die item F10; owner rule 08:05: "Hard PHY analog cores may be behavioural models, but their digital link /
// controller layer must be real RTL").  They replace the pin-only shells physical/asap7_v41x_pdie_macros_v2/
// ot_pdie_{serdes,ucie}/*_bb.v as the die masters' RTL.
//
// Above these macros (already real RTL in the collective lane tiles, results/rtl/s81_ph_20261006/collective/
// contract.json link_layer): ot_s81ph_link_ep (sequence, CRC-32, go-back-N replay, ACK/NAK, cumulative credits) and
// ot_s81ph_link_gbx (512-b beat: marker, idle, reverse frame, forward slot gearbox).  Inside the macro:
//
//   ot_pdie_serdes (board / cable links: full KP4 FEC, owner 2026-10-06)
//     tx 512 b a cycle (ck) -> ot_s81_kp4_enc (RS(544,514) frame of 10 beats + 20-b header) -> PMA TX model
//     -> pads pma_tx[543:0] + pma_tck (the serial lanes, modelled one 544-b PMA word a cycle)
//     pads pma_rx / pma_rck (the far die) -> PMA RX model (CDR: recovered clock = pma_rck) -> ot_s81_kp4_dec (align,
//     correct t = 15, flag uncorrectable) -> rate matcher (recovered clock -> ck: drops IDLE beats (bit 1) when the
//     crossing FIFO is nearly full, presents an IDLE beat when it is empty -- the gearbox skips IDLE beats, the
//     two dies' clocks are plesiochronous) -> rx 512 b a cycle (ck)
//   ot_pdie_ucie (in-package UCIe: no FEC -- UCIe keeps its own spec; its adapter CRC / retry is the link_ep above)
//     tx -> PMA TX model -> pads pma_tx[512:0] = {valid, beat}; pads -> PMA RX model -> rate matcher -> rx
// st = {live (FEC locked / UCIe receiving), fault (sticky: uncorrectable frame, rate-match overflow)} (ck domain).
// rst: the die stream reset (active low), released after the clocks run.
// ---------------------------------------------------------------------------------------------------------------
module ot_pdie_serdes #(parameter integer PMA_LAT = 4, parameter integer EMUT = 0, parameter integer DMUT = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    // die pads (behavioural PMA lanes)
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck
);
    // ---- resets: one synchroniser per clock domain
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
`ifdef OT_S81_SERDES_RST_COPIES
    // S81-RCK-4 11-07: kept identical copies of the last reset synchroniser stage, one per consumer (TT rs_t -> u_rm/u_enc recovery -264..-700)
    (* keep *) reg rs_t_enc, rs_t_rm;
    always @(posedge clk or negedge rst) if (!rst) begin rs_t_enc <= 1'b0; rs_t_rm <= 1'b0; end else begin rs_t_enc <= rs_t[0]; rs_t_rm <= rs_t[0]; end
    wire rn_t_enc = rs_t_enc, rn_t_rm = rs_t_rm;
`else
    wire rn_t_enc = rn_t, rn_t_rm = rn_t;
`endif
    // ---- transmit: FEC encoder (ck) -> PMA TX model
    wire e_v; wire [543:0] e_d; wire e_flt;
    ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(clk), .rst_n(rn_t_enc), .tx_v(rn_t_enc), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_ptx (.clk(clk), .d_v(e_v), .d(e_d), .q(pma_tx));
    assign pma_tck = clk;
    // ---- receive: PMA RX model (recovered clock) -> FEC decoder -> rate matcher -> ck
    wire [543:0] r_d;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81_kp4_dec #(.MUT(DMUT)) u_dec (.clk(pma_rck), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .q_v(q_v), .q_d(q_d),
        .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc),
        .n_relock(n_rl));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t_rm), .r_d(rx),
        .fault(rm_flt));
    // ---- status (ck)
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt};
    assign st = st_q;
endmodule

module ot_pdie_ucie #(parameter integer PMA_LAT = 2) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [512:0]  pma_tx,
    output wire          pma_tck,
    input  wire [512:0]  pma_rx,
    input  wire          pma_rck
);
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    reg [512:0] t_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) t_q <= 513'd0; else t_q <= {1'b1, tx};
    ot_s81_pma_bm #(.W(513), .LAT(PMA_LAT)) u_ptx (.clk(clk), .d_v(1'b1), .d(t_q), .q(pma_tx));
    assign pma_tck = clk;
    wire [512:0] r_d;
    ot_s81_pma_bm #(.W(513), .LAT(PMA_LAT)) u_prx (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(r_d[512]), .w_d(r_d[511:0]), .rclk(clk), .rrst_n(rn_t),
        .r_d(rx), .fault(rm_flt));
    reg [1:0] lv_s; reg seen;
    always @(posedge pma_rck or negedge rn_r) if (!rn_r) seen <= 1'b0; else if (r_d[512]) seen <= 1'b1;
    always @(posedge clk or negedge rn_t) if (!rn_t) lv_s <= 2'b00; else lv_s <= {lv_s[0], seen};
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lv_s[1], st_q[0] | rm_flt};
    assign st = st_q;
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81_pma_bm: BEHAVIOURAL analog PMA (serialiser + channel + CDR) of the S81 die links -- the hard analog core the
// owner rule allows as a model.  One parallel PMA word a cycle in, the same word LAT cycles later on the pads /
// recovered side (serialisation + flight latency).  Not a synthesis target.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_pma_bm #(parameter integer W = 544, parameter integer LAT = 4) (
    input  wire          clk,
    input  wire          d_v,
    input  wire [W-1:0]  d,
    output wire [W-1:0]  q
);
    reg [W-1:0] l [0:LAT-1];
    integer i;
    always @(posedge clk) begin
        l[0] <= d_v ? d : {W{1'b0}};
        for (i = 1; i < LAT; i = i + 1) l[i] <= l[i - 1];
    end
    assign q = l[LAT - 1];
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81_rate_match: recovered-clock -> local-clock crossing of the lane beats (real RTL).  An 8-deep gray-pointer
// FIFO; the write side drops an IDLE beat (bit 1 set, no gearbox bits) while the FIFO holds >= 6 beats, the read side
// presents an IDLE beat (512'b10) while it is empty, so a plesiochronous offset is absorbed on IDLE beats only.  A
// non-IDLE beat arriving to a full FIFO is a sticky fault (lost data).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_rate_match (
    input  wire          wclk, wrst_n,
    input  wire          w_v,
    input  wire [511:0]  w_d,
    input  wire          rclk, rrst_n,
    output reg  [511:0]  r_d,
    output wire          fault
);
    reg  [511:0] mem [0:7];
    reg  [3:0] wp, rp, wp_g, rp_g;
    reg  [3:0] rp_g1, rp_g2, wp_g1, wp_g2;
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
`ifdef OT_S81_RM_LOCAL4
    // Free credit follows actual r_m capture, not the preceding read select.
    // +1 rclk CONTROL-publication edge, no additional data-output stage.
    reg [3:0] rp_g_pub;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) rp_g_pub <= 4'd0; else rp_g_pub <= rp_g;
    wire [3:0] rp_to_write = rp_g_pub;
`else
    wire [3:0] rp_to_write = rp_g;
`endif
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_to_write; rp_g2 <= rp_g1; end
`ifdef OT_S81_RM_LOCAL4
`ifndef OT_S81_RM_STAGED
    initial $error("RM_LOCAL4 requires the explicit RM_STAGED base profile");
`endif
    // Publication follows the actual staged memory commit, not the pending
    // write. This adds one wclk producer PIN cycle versus RM_STAGED.
    reg [3:0] wp_g_pub;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) wp_g_pub <= 4'd0; else wp_g_pub <= wp_g;
    wire [3:0] wp_to_read = wp_g_pub;
`else
    wire [3:0] wp_to_read = wp_g;
`endif
    always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_to_read; wp_g2 <= wp_g1; end
    wire [3:0] fill_w = wp - g2b(rp_g2);
    wire idle = w_d[1] && !w_d[0];
    wire full = fill_w == 4'd8;
    wire push = w_v && !full && !(idle && fill_w >= 4'd6);
    reg flt;
`ifdef OT_S81_RM_STAGED
`ifdef OT_S81_RM_LOCAL4
    // Private RCK fallback: slice-local registered one-hot write/read decode.
    // Read select uses only fully synchronized wp_g2/empty, never wp_g1 lookahead.
    // Keep r_m by memory and two output relay rows for the 1.3mm BOUT reach.
    // Versus RM_STAGED: +1 wclk publication and +2 rclk (select + extra relay).
    // r_m/r_pipe/r_d have no reset: the >=64-edge parent reset flushes IDLE;
    // internal data flush is three rclk edges, reset release itself is unchanged.
    localparam integer RM_LOCAL_NS = 64;
    reg [511:0] w_dq;
    reg [511:0] r_m, r_pipe;
    (* keep *) reg [7:0] we_q [0:RM_LOCAL_NS-1];
    (* keep *) reg [7:0] rsel [0:RM_LOCAL_NS-1];
    genvar ws, wb, rs, rb;
`ifdef OT_S81_RM_WFULL8
    // S81-RCK-10 11-07 (vJ, RM write side): the vI probe's last RM class was rp_g2 -> g2b -> fill_w subtract -> full /
    // ge6 compare -> push -> 512 we_q (TT -133 ps, 427 ep, DEPTH + fanout).  Same push decision, re-expressed:
    //   full  <=> g2b(rp_g2) == wp - 8  <=> rp_g2 == G8,  G8 = gray(wp - 8)
    //   ge6   <=> fill_w in {6,7,8}     <=> rp_g2 in {G6, G7, G8}  (fill_w <= 8 always: push needs !full)
    // G6/G7/G8 and the write one-hot are REGISTERED from the next write pointer, so the crossing term is
    // rp_g2 -> 4-bit equality -> push; rp_g2 itself stays the 2nd synchroniser flop (no logic between sync stages).
    // 8 kept copies (one per 8-slice group = 64 we_q bits each) of {w_v, idle, wp, G6, G7, G8, one-hot}.
    // PIN CYCLE: w_v / w_d take one more wclk register at the RM input (w_v1 / w_d1): +1 wclk on the RX data path.
    // The credit loop (push -> wp_g -> read -> rp_g -> rp_g2 -> push) is unchanged: identical occupancy and fault rules.
    localparam integer RM_WG = 8;
    function automatic [3:0] b2g(input [3:0] b); begin b2g = b ^ (b >> 1); end endfunction
    reg [511:0] w_d1;
    always @(posedge wclk) w_d1 <= w_d;
    always @(posedge wclk) w_dq <= w_d1;
    (* keep *) reg [RM_WG-1:0] wv_c, idl_c;
    (* keep *) reg [3:0] wp_c [0:RM_WG-1];
    (* keep *) reg [3:0] g6_c [0:RM_WG-1];
    (* keep *) reg [3:0] g7_c [0:RM_WG-1];
    (* keep *) reg [3:0] g8_c [0:RM_WG-1];
    (* keep *) reg [7:0] oh_c [0:RM_WG-1];
    wire [RM_WG-1:0] push_c, full_c;
    genvar wg;
    generate for (wg=0; wg<RM_WG; wg=wg+1) begin : g_wgrp
        wire f8 = (rp_g2 == g8_c[wg]);
`ifdef RMW8_MUT_GE7
        wire f67 = (rp_g2 == g7_c[wg]);                       // MUTANT: occupancy 6 not shed
`else
        wire f67 = (rp_g2 == g6_c[wg]) | (rp_g2 == g7_c[wg]);
`endif
        assign full_c[wg] = f8;
        assign push_c[wg] = wv_c[wg] && !f8 && !(idl_c[wg] && f67);
`ifdef RMW8_MUT_STALEOH
        wire [3:0] wp_n = (wg == 5) ? wp_c[wg] : wp_c[wg] + {3'd0, push_c[wg]};   // MUTANT: group 5 one-hot never advances
`else
        wire [3:0] wp_n = wp_c[wg] + {3'd0, push_c[wg]};
`endif
        (* keep *) always @(posedge wclk or negedge wrst_n)
            if (!wrst_n) begin
                wv_c[wg] <= 1'b0; idl_c[wg] <= 1'b0; wp_c[wg] <= 4'd0;
                g6_c[wg] <= b2g(4'd10); g7_c[wg] <= b2g(4'd9); g8_c[wg] <= b2g(4'd8); oh_c[wg] <= 8'd1;
            end else begin
`ifdef RMW8_MUT_NOPIN
                wv_c[wg] <= w_v; idl_c[wg] <= w_d1[1] && !w_d1[0];   // MUTANT: idle from the later word
`else
                wv_c[wg] <= w_v; idl_c[wg] <= w_d[1] && !w_d[0];
`endif
                wp_c[wg] <= wp_n;
                g6_c[wg] <= b2g(wp_n - 4'd6);
                g7_c[wg] <= b2g(wp_n - 4'd7);
`ifdef RMW8_MUT_FULLOFF
                g8_c[wg] <= b2g(wp_n - 4'd7);                     // MUTANT: full one entry early
`else
                g8_c[wg] <= b2g(wp_n - 4'd8);
`endif
                oh_c[wg] <= 8'd1 << wp_n[2:0];
            end
        for (ws=wg*(RM_LOCAL_NS/RM_WG); ws<(wg+1)*(RM_LOCAL_NS/RM_WG); ws=ws+1) begin : g_local_write
            (* keep *) always @(posedge wclk or negedge wrst_n)
                if (!wrst_n) we_q[ws] <= 8'd0;
                else we_q[ws] <= push_c[wg] ? oh_c[wg] : 8'd0;
            for (wb=0; wb<8; wb=wb+1) begin : g_bank
                always @(posedge wclk)
                    if (we_q[ws][wb]) mem[wb][ws*8 +: 8] <= w_dq[ws*8 +: 8];
            end
        end
    end endgenerate
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp<=0; wp_g<=0; flt<=1'b0; end
        else begin
            if (push_c[0]) begin wp<=wp+1'b1; wp_g<=(wp+1'b1)^((wp+1'b1)>>1); end
            if (wv_c[0] && full_c[0] && !idl_c[0]) flt<=1'b1;
        end
`else
    always @(posedge wclk) w_dq <= w_d;
    generate for (ws=0; ws<RM_LOCAL_NS; ws=ws+1) begin : g_local_write
        (* keep *) always @(posedge wclk or negedge wrst_n)
            if (!wrst_n) we_q[ws] <= 8'd0;
            else we_q[ws] <= push ? (8'd1 << wp[2:0]) : 8'd0;
        for (wb=0; wb<8; wb=wb+1) begin : g_bank
            always @(posedge wclk)
                if (we_q[ws][wb]) mem[wb][ws*8 +: 8] <= w_dq[ws*8 +: 8];
        end
    end endgenerate
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp<=0; wp_g<=0; flt<=1'b0; end
        else begin
            if (push) begin wp<=wp+1'b1; wp_g<=(wp+1'b1)^((wp+1'b1)>>1); end
            if (w_v && full && !idle) flt<=1'b1;
        end
`endif
    wire empty = g2b(wp_g2) == rp;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp<=0; rp_g<=0; end
        else if (!empty) begin rp<=rp+1'b1; rp_g<=(rp+1'b1)^((rp+1'b1)>>1); end
    reg r_idle;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) r_idle<=1'b1; else r_idle<=empty;
    generate for (rs=0; rs<RM_LOCAL_NS; rs=rs+1) begin : g_local_read
        (* keep *) always @(posedge rclk or negedge rrst_n)
            if (!rrst_n) rsel[rs]<=8'd0;
            else rsel[rs]<=empty ? 8'd0 : (8'd1 << rp[2:0]);
        for (rb=0; rb<8; rb=rb+1) begin : g_bit
            localparam integer CB=rs*8+rb;
            always @(posedge rclk)
                r_m[CB] <= ((CB==1) & r_idle) | (|({mem[7][CB],mem[6][CB],mem[5][CB],mem[4][CB],mem[3][CB],mem[2][CB],mem[1][CB],mem[0][CB]} & rsel[rs]));
        end
    end endgenerate
    always @(posedge rclk) begin
        r_pipe<=r_m;
        r_d<=r_pipe;
    end
`else
    // S81-RCK-4 11-07 OT_S81_RM_STAGED: rate matcher form for the 2.9-mm serdes types (class: one enable/select across
    // 4096 mem bits, one reset to 512 flops; TT rp->r_d -300..-872, rp_g2->mem -99..-239).
    //  write: push decided as before; data + per-slice one-hot write enables take one wclk stage, mem written one wclk
    //    later.  wp/wp_g move on the old edge; the reader sees wp_g two rclk later and reads on the third: no PIN CYCLE.
    //  read:  r_m = mux stage beside mem; r_d = free stage for the hop to the output face: +1 rclk PIN CYCLE on r_d.
    //  r_m/r_d carry no reset: pointers reset => empty => IDLE after 2 rclk edges (reset low >= 64 clk, boot contract).
    localparam integer RM_NS = 8;           // write-enable copies: one per 64-bit slice
    reg  [511:0] w_dq;
    (* keep *) reg [7:0] we_q [0:RM_NS-1];
    integer rm_i, rm_j;
    reg  [511:0] r_m;
    reg  [511:0] mem_rd;
    always @(posedge wclk) w_dq <= w_d;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) for (rm_i = 0; rm_i < RM_NS; rm_i = rm_i + 1) we_q[rm_i] <= 8'd0;
        else for (rm_i = 0; rm_i < RM_NS; rm_i = rm_i + 1) we_q[rm_i] <= push ? (8'd1 << wp[2:0]) : 8'd0;
    always @(posedge wclk)
        for (rm_i = 0; rm_i < RM_NS; rm_i = rm_i + 1)
            for (rm_j = 0; rm_j < 8; rm_j = rm_j + 1)
                if (we_q[rm_i][rm_j]) mem[rm_j][rm_i*64 +: 64] <= w_dq[rm_i*64 +: 64];
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end
        else begin
            if (push) begin wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    wire empty = g2b(wp_g2) == rp;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp <= 0; rp_g <= 0; end
        else if (!empty) begin rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
    always @(posedge rclk) begin
        r_m <= empty ? 512'd2 : mem[rp[2:0]];
`ifdef RMMUT_NOSTAGE
        r_d <= empty ? 512'd2 : mem[rp[2:0]];
`else
        r_d <= r_m;
`endif
    end
`endif
`else
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end
        else begin
            if (push) begin mem[wp[2:0]] <= w_d; wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    wire empty = g2b(wp_g2) == rp;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp <= 0; rp_g <= 0; r_d <= 512'd2; end
        else if (!empty) begin r_d <= mem[rp[2:0]]; rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
        else r_d <= 512'd2;                        // IDLE beat: bit 1 set, no marker, no reverse frame, no slot bits
`endif
    reg f1, f2; always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
