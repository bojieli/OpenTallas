`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81hd_mesh_ep_core (HEAD-RTL 2026-10-26): u_core of plan type hd_mesh (wrapper ot_s81hd_mesh_ep = gen.py rtl) (physical/die_plan/s81_head/die_plan.json,
// 3 replicas mesh0S / mesh7S / mesh7N): the TP4 mesh endpoint of ONE peer rank for the rank argmax all-gather.
// Plan contents note: "2 x dsfd_coll_lane_w_safe8_ntf (closed lane sub-children s81hd_lsc_*) + 64-b static adapter".
// Sources of the function (no new mechanism): historical ctl results/arch/s81_head_source_1025/hsf0_reference (3 TP4
// pairs = 3 peer ranks, BOTH lanes of a pair carry the same HSF0 BEST record, the copies are compared in the rank
// merge), ot_s81hd_rank_merge_hsf0 (6 inputs = 2 copies x 3 peers, full 97-bit header + BEST record), ot_s81hd_best64
// (BEST over the 64-wire lane in 2 registered beats), ot_s81hd_lane (static core adapter protocol) and its STACKED
// MAIN form ot_s81hd_lane_sc6 (results/rtl/s81_head_lsc_import_1022, closed children s81hd_lsc_t9/t8/r0m/r1m).
//
// Buses = the plan buses exactly (no extra IO):
//   coll_ia [513:0] / coll_oa [511:0]  SerDes pair a (copy A), coll514 = {live, fault, beat512} as the layer die
//   coll_ib [513:0] / coll_ob [511:0]  SerDes pair b (copy B)
//   m_tx_i  [63:0]  from hd_ctl: ot_s81hd_best64_tx beats of the OWN canonical BEST frame (2 beats, <= 1 / 2 cycles)
//   m_rx_o  [63:0]  to hd_ctl:   ot_s81hd_beat_tx (W 110, N 2, P 62) words, decoded by ot_s81hd_mesh64_rx below
// TX: m_tx_i -> best64 decode -> the identical 553-b frame into BOTH lanes on the same edge (copy A on a, copy B on b).
// RX: each lane's flits land in the adapter pin flops; a canonical BEST (last 1, type 1, payload[551:97] 0) is held in
//   its copy slot; the slots drain to hd_ctl one word per 2 cycles, A first.  Word (110 b) =
//   {ep_fault[11:0], copy, header+BEST[96:0]}, copy 0 = lane a, 1 = lane b.  Two words a position (4 lane cycles); the
//   static position period (>= 8,357 cycles) is far above it.  The copies are NOT compared here: both reach the rank
//   merge, which owns the copy check (copy_fault), exactly as the historical controller.
// ep_fault (sticky, control reset only) is carried IN-BAND on every word, so the endpoint status is live at hd_ctl
//   without a new plan bus: [3:0] lane a flt {adapter, meso, gearbox, endpoint}, [7:4] lane b flt, [8] m_tx_i decode
//   fault (beat order / pad / non-BEST), [9] non-canonical lane frame (dropped), [10] copy slot overwrite (a second
//   record landed before the first drained; the slot keeps the newer one), [11] m_rx_o word rate fault.  A dead link delivers no
//   word: hd_ctl's rank merge then never fires for that position, which hd_ctl must flag at the position's compiled
//   date (hd_ctl obligation, recorded in the ASK; no completion or credit is fed back here).
// Flow control exists only inside the lanes (off-die boundary, owner 10-14); the core faces are valid-only, fixed phase.
// Latency (off-die elastic, compiler-known nominal): m_tx_i beat 1 -> lane tx_v 1 edge (best64 decode) + lane adapter
//   5 edges; lane rx_v -> word start 3 edges (landed hold, slot flag, decision) + 2 beats (+1 when both copies land on
//   the same edge, copy B waits one word slot).
// Reset: rst_n -> ot_rst_relay_tree3 (release on edge 3, the lane children's own trees release on edge 3 too);
//   only control / valid bits are reset; data holds are unreset.
// MUT (bench negative controls; 0 = production): 1 copy id stuck at 0, 2 copy-B identity bit 96 flipped,
//   3 lane b never transmits, 4 ep_fault not carried (zeros in the word).
// ---------------------------------------------------------------------------------------------------------------------

// The stacked MAIN head lane block (byte-equivalent composition of the archived ot_s81hd_lane_sc6 MAIN parent, renamed
// so that no archived parent enters the canonical readset): one dsfd_coll_lane_w_safe8_ntf + the closed static-adapter
// sub-children ot_s81hd_lsc_t9 x3 / t8 / r0m / r1m (rtl/dsrom_sys/s81_head/ot_s81hd_lsc_parts.sv).
module ot_s81hd_mesh_lane (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          chb,
    input  wire [513:0]  rx,
    output wire [511:0]  tx,
    input  wire          tx_v,
    input  wire [552:0]  tx_d,
    output wire          rx_v,
    output wire [552:0]  rx_d,
    output wire [3:0]    flt
);
    wire r_lane, r_misc;
    reg rxen;
    always @(posedge ck or negedge r_misc) if (!r_misc) rxen <= 1'b0; else rxen <= 1'b1;
    wire [514:0] lrx = {rx[512], rx[513], rx[511:0], rxen};
    wire lo_v, lo_r, li_v, li_r; wire [552:0] lo_d, li_d; wire [2:0] lf;
    dsfd_coll_lane_w_safe8_ntf u_ln (.ck(ck), .rs(r_lane), .chb(chb), .rx(lrx), .tx(tx), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(lf));
    wire [3:0] tvk, crk; wire ovf_t;
    ot_s81hd_lsc_t9 u_t0 (.ck(ck), .rst_n(rst_n), .td(tx_d[143:0]),   .tvk(tvk[0]), .crk(crk[0]), .lod(lo_d[143:0]));
    ot_s81hd_lsc_t9 u_t1 (.ck(ck), .rst_n(rst_n), .td(tx_d[287:144]), .tvk(tvk[1]), .crk(crk[1]), .lod(lo_d[287:144]));
    ot_s81hd_lsc_t9 u_t2 (.ck(ck), .rst_n(rst_n), .td(tx_d[431:288]), .tvk(tvk[2]), .crk(crk[2]), .lod(lo_d[431:288]));
    ot_s81hd_lsc_t8 u_t3 (.ck(ck), .rst_n(rst_n), .td(tx_d[552:432]), .tvk(tvk[3]), .crk(crk[3]), .lod(lo_d[552:432]),
        .lv(lo_v), .ovf(ovf_t));
    ot_s81hd_lsc_r0m u_r0 (.ck(ck), .rst_n(rst_n), .tx_v(tx_v), .lo_r(lo_r), .tvk(tvk), .crk(crk), .li_v(li_v), .li_r(li_r),
        .li_d(li_d[287:0]), .rx_d(rx_d[287:0]), .rx_v(rx_v), .lf(lf), .ovf_t(ovf_t), .flt(flt), .r_lane(r_lane),
        .r_misc_o(r_misc));
    ot_s81hd_lsc_r1m u_r1 (.ck(ck), .li_d(li_d[552:288]), .rx_d(rx_d[552:288]));
endmodule

module ot_s81hd_mesh_ep_core #(
    parameter [1:0]   CH_B = 2'b11,          // board-lane straps of lanes a / b (as ot_s81hd_lep0N_core CH_B)
    parameter integer MUT  = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [513:0]  coll_ia,
    output wire [511:0]  coll_oa,
    input  wire [513:0]  coll_ib,
    output wire [511:0]  coll_ob,
    input  wire [63:0]   m_tx_i,
    output wire [63:0]   m_rx_o
);
    localparam integer WW = 110;
    wire [1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(2)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    wire r_tx = rr[0], r_rx = rr[1];
    // ------------------------------------------------------------------ TX: own BEST -> both lanes
    wire        own_v, own_f;
    wire [552:0] own_frame;
    ot_s81hd_best64_rx u_own (.ck(ck), .rn(r_tx), .lane(m_tx_i), .v(own_v), .frame(own_frame), .fault(own_f));
    wire        tv_b = (MUT == 3) ? 1'b0 : own_v;
    // ------------------------------------------------------------------ the two lanes
    wire        rv_a, rv_b;
    wire [552:0] rd_a, rd_b;
    wire [3:0]  fl_a, fl_b;
    ot_s81hd_mesh_lane u_la (.ck(ck), .rst_n(rst_n), .chb(CH_B[0]), .rx(coll_ia), .tx(coll_oa),
        .tx_v(own_v), .tx_d(own_frame), .rx_v(rv_a), .rx_d(rd_a), .flt(fl_a));
    ot_s81hd_mesh_lane u_lb (.ck(ck), .rst_n(rst_n), .chb(CH_B[1]), .rx(coll_ib), .tx(coll_ob),
        .tx_v(tv_b), .tx_d(own_frame), .rx_v(rv_b), .rx_d(rd_b), .flt(fl_b));
    // ------------------------------------------------------------------ RX: canonical BEST -> copy slots
    wire can_a = rd_a[552] && rd_a[3:0] == 4'd1 && !(|rd_a[551:97]);
    wire can_b = rd_b[552] && rd_b[3:0] == 4'd1 && !(|rd_b[551:97]);
    wire en_a = rv_a && can_a, en_b = rv_b && can_b;
    wire [127:0] da = {31'd0, rd_a[96:0]}, db = {31'd0, rd_b[96:0]};
    wire [127:0] qa, qb;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_slot
        ot_s81hd_hreg32 u_ha (.ck(ck), .en(en_a), .d(da[32*g +: 32]), .q(qa[32*g +: 32]));
        ot_s81hd_hreg32 u_hb (.ck(ck), .en(en_b), .d(db[32*g +: 32]), .q(qb[32*g +: 32]));
    end endgenerate
    reg  la, lb, pa, pb;                      // landed enables (aligned with the hold), slot pending
    reg  iss_q;                               // a word was issued on the previous decision edge
    (* keep = "true" *) reg [3:0] selb;       // kept copies of "this word is copy B" (<= 28 mux bits each)
    wire dec  = !iss_q && (pa || pb);
    wire tk_a = dec && pa;
    wire tk_b = dec && !pa;
    reg  [11:0] fv;
    reg  ovw_q, ncan_q;
    always @(posedge ck or negedge r_rx)
        if (!r_rx) begin
            la <= 1'b0; lb <= 1'b0; pa <= 1'b0; pb <= 1'b0; iss_q <= 1'b0; selb <= 4'd0; ovw_q <= 1'b0; ncan_q <= 1'b0;
        end else begin
            la <= en_a; lb <= en_b;
            pa <= (pa && !tk_a) || la;
            pb <= (pb && !tk_b) || lb;
            iss_q <= dec;
            if (dec) selb <= {4{tk_b}};
            ovw_q  <= (la && pa && !tk_a) || (lb && pb && !tk_b);
            ncan_q <= (rv_a && !can_a) || (rv_b && !can_b);
        end
    // ------------------------------------------------------------------ word to hd_ctl
    wire [96:0] body;
    assign body[27:0]  = selb[0] ? qb[27:0]  : qa[27:0];
    assign body[55:28] = selb[1] ? qb[55:28] : qa[55:28];
    assign body[83:56] = selb[2] ? qb[83:56] : qa[83:56];
    assign body[96:84] = selb[3] ? (qb[96:84] ^ ((MUT == 2) ? 13'h1000 : 13'h0)) : qa[96:84];
    wire copy = (MUT == 1) ? 1'b0 : selb[0];
    wire wf;
    wire [11:0] fv_word = (MUT == 4) ? 12'd0 : fv;
    ot_s81hd_beat_tx #(.W(WW), .N(2), .P(62)) u_wtx (.ck(ck), .rn(r_rx), .v(iss_q), .d({fv_word, copy, body}),
        .o(m_rx_o), .fault(wf));
    always @(posedge ck or negedge r_rx)
        if (!r_rx) fv <= 12'd0;
        else fv <= fv | {wf, ovw_q, ncan_q, own_f, fl_b, fl_a};
endmodule

// hd_ctl-side receiver of m_rx_o (one per peer): copy A / copy B valids on the shared 553-b canonical frame, exactly the
// ot_s81hd_rank_merge_hsf0 mrx_v[2p] / mrx_v[2p+1] / mrx_d slot inputs, plus the live endpoint fault vector.
module ot_s81hd_mesh64_rx (
    input  wire          ck,
    input  wire          rn,
    input  wire [63:0]   lane,
    output wire          va,
    output wire          vb,
    output wire [552:0]  frame,
    output reg  [11:0]   ep_fault,         // sticky copy of the endpoint's in-band fault vector
    output wire          fault             // word-level fault: beat order / pad / non-BEST word
);
    wire wv, bf; wire [109:0] w;
    ot_s81hd_beat_rx #(.W(110), .N(2), .P(62)) u_rx (.ck(ck), .rn(rn), .i(lane), .v(wv), .d(w), .fault(bf));
    wire best = w[3:0] == 4'd1;
    reg tf;
    always @(posedge ck or negedge rn)
        if (!rn) begin tf <= 1'b0; ep_fault <= 12'd0; end
        else begin
            if (wv && !best) tf <= 1'b1;
            if (wv) ep_fault <= ep_fault | w[109:98];
        end
    assign va = wv && best && !w[97];
    assign vb = wv && best && w[97];
    assign frame = {1'b1, 455'd0, w[96:0]};
    assign fault = bf | tf;
endmodule
`default_nettype wire
