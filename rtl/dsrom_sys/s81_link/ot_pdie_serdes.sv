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
    // ---- transmit: FEC encoder (ck) -> PMA TX model
    wire e_v; wire [543:0] e_d; wire e_flt;
    ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
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
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx),
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
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_g; rp_g2 <= rp_g1; end
    always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_g; wp_g2 <= wp_g1; end
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
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp <= 0; rp_g <= 0; r_d <= 512'd2; end
        else if (!empty) begin r_d <= mem[rp[2:0]]; rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
        else r_d <= 512'd2;                        // IDLE beat: bit 1 set, no marker, no reverse frame, no slot bits
    reg f1, f2; always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
