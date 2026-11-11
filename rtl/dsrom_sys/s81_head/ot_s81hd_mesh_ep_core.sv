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
//   its copy FIFO (BQ records); the FIFOs drain to hd_ctl one word per 2 cycles, A first.  Word (110 b) =
//   {ep_fault[11:0], copy, header+BEST[96:0]}, copy 0 = lane a, 1 = lane b.  Two words a position (4 lane cycles); the
//   static position period (>= 8,357 cycles) is far above it.  The copies are NOT compared here: both reach the rank
//   merge, which owns the copy check (copy_fault), exactly as the historical controller.
// ep_fault (sticky, control reset only) is carried IN-BAND on every word, so the endpoint status is live at hd_ctl
//   without a new plan bus: [3:0] lane a flt {adapter, meso, gearbox, endpoint}, [7:4] lane b flt, [8] m_tx_i decode
//   fault (beat order / pad / non-BEST), [9] non-canonical lane frame (dropped), [10] copy FIFO overflow (a record
//   landed into a full BQ-record FIFO; HEAD-RTL-4: it is dropped, order kept), [11] m_rx_o word rate fault.  A dead link delivers no
//   word: hd_ctl's rank merge then never fires for that position, which hd_ctl must flag at the position's compiled
//   date (hd_ctl obligation, recorded in the ASK; no completion or credit is fed back here).
// Flow control exists only inside the lanes (off-die boundary, owner 10-14); the core faces are valid-only, fixed phase.
// Latency (off-die elastic, compiler-known nominal): m_tx_i beat 1 -> lane tx_v 1 edge (best64 decode) + lane adapter
//   5 edges; lane rx_v -> word start 3 edges (landed hold, slot flag, decision) + 2 beats (+1 when both copies land on
//   the same edge, copy B waits one word slot).
// Reset: rst_n -> ot_rst_relay_tree3 (release on edge 3, the lane children's own trees release on edge 3 too);
//   only control / valid bits are reset; data holds are unreset.
// MUT (bench negative controls; 0 = production): 1 copy id stuck at 0, 2 copy-B identity bit 96 flipped,
//   3 lane b never transmits, 4 ep_fault not carried (zeros in the word), 7 burst FIFO one record short (BQ - 1).
// HEAD-RTL-4: the 1-entry copy slot is now a BQ-record burst FIFO per copy (see the RX section).
// ---------------------------------------------------------------------------------------------------------------------

// The stacked MAIN head lane block (byte-equivalent composition of the archived ot_s81hd_lane_sc6 MAIN parent, renamed
// so that no archived parent enters the canonical readset): one dsfd_coll_lane_w_safe8_ntf + the closed static-adapter
// sub-children ot_s81hd_lsc_t9 x3 / t8 / r0m / r1m (rtl/dsrom_sys/s81_head/ot_s81hd_lsc_parts.sv).
module ot_s81hd_mesh_lane #(parameter integer RBL = 0) (
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
    dsfd_coll_lane_w_safe8_ntf_hd #(.RBL(RBL)) u_ln (.ck(ck), .rs(r_lane), .chb(chb), .rx(lrx), .tx(tx), .lo_v(lo_v), .lo_r(lo_r),
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
    parameter integer BQ   = 7,              // per-copy burst FIFO depth (HEAD-RTL-4 bound, see the RX section)
    parameter integer RBL  = 0,              // opt-in shared replay landing: +1 TX edge
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
    ot_s81hd_mesh_lane #(.RBL(RBL)) u_la (.ck(ck), .rst_n(rst_n), .chb(CH_B[0]), .rx(coll_ia), .tx(coll_oa),
        .tx_v(own_v), .tx_d(own_frame), .rx_v(rv_a), .rx_d(rd_a), .flt(fl_a));
    ot_s81hd_mesh_lane #(.RBL(RBL)) u_lb (.ck(ck), .rst_n(rst_n), .chb(CH_B[1]), .rx(coll_ib), .tx(coll_ob),
        .tx_v(tv_b), .tx_d(own_frame), .rx_v(rv_b), .rx_d(rd_b), .flt(fl_b));
    // ------------------------------------------------------------------ RX: canonical BEST -> copy slots
    // DIE-HEAD-65: the canonical test crossed the whole lane register (455-bit zero test, 6 wire buffers, l48ub GRT -100).
    // One registered RX stage: header and 8 zero-test bands register next to their bits, the decision and the landing
    // register take the next edge. +1 RX data cycle on m_rx_o, one more edge before the slot edges below.
    localparam integer NZB = 8;
    reg  [NZB-1:0] nz_a, nz_b;
    reg  hdr_a, hdr_b, v0_a, v0_b;
    reg  [96:0] l0_a, l0_b;
    integer zk;
    always @(posedge ck) begin
        hdr_a <= rd_a[552] && rd_a[3:0] == 4'd1;
        hdr_b <= rd_b[552] && rd_b[3:0] == 4'd1;
        for (zk = 0; zk < NZB; zk = zk + 1) begin
            nz_a[zk] <= |(rd_a[97 + zk * 57 +: 57] & ((zk == NZB - 1) ? 57'h0ffffffffffffff : 57'h1ffffffffffffff));
            nz_b[zk] <= |(rd_b[97 + zk * 57 +: 57] & ((zk == NZB - 1) ? 57'h0ffffffffffffff : 57'h1ffffffffffffff));
        end
        l0_a <= rd_a[96:0];
        l0_b <= rd_b[96:0];
    end
    wire can_a = hdr_a && !(|nz_a);
    wire can_b = hdr_b && !(|nz_b);
    wire en_a = v0_a && can_a, en_b = v0_b && can_b;
    // HEAD-RTL-4 (RULING HEAD-RTL-3 ASK2): per-copy BURST FIFO of BQ records (was a 1-entry hold slot).  After a lane
    // replay the link delivers the replayed backlog back to back (lsc_r0m li_r = li_v registered, gearbox 3 flits / 4
    // edges) while the shared word port drains one word per 2 edges, A first; BQ = the worst replay backlog of
    // results/arch/head_rtl4_1026/README.md (tools/s81_head/mesh_bq_bound.py: replay window N = floor(S / T) + 1 records
    // at stall S and record spacing T, delivered 3 per 4 edges against the copy-B drain gap; S 79 / T 7 -> 7; the
    // production position period T >= 8,357 > any NAK or ACK-timeout stall gives N = 1).  Static storage: flops, one-hot write / read
    // pointers, no flow control towards the lane (the closed lsc_r0m child is unchanged).  A landing into a full FIFO
    // is DROPPED (order kept) and sets the sticky ep_fault[10].  Same edges as the slot: landing register (edge 1),
    // FIFO write + count (edge 2), decision -> word register (edge 3).  MUT 7 = BQ - 1 (bench negative control).
    localparam integer BQE = (MUT == 7) ? BQ - 1 : BQ;
    localparam integer BCW = $clog2(BQE + 1);
    reg  la, lb;                              // landed enables (aligned with the landing registers)
    reg  [96:0] ld_a, ld_b;                   // landing registers (data, unreset)
    always @(posedge ck) begin ld_a <= l0_a; ld_b <= l0_b; end
    reg  [96:0] fq_a [0:BQE-1];
    reg  [96:0] fq_b [0:BQE-1];
    reg  [BQE-1:0] wp_a, wp_b, rp_a, rp_b;    // one-hot pointers
    reg  [BCW-1:0] na, nb;                    // records held
    reg  iss_q;                               // a word was issued on the previous decision edge
    (* keep = "true" *) reg [3:0] selb;       // kept copies of "this word is copy B"
    wire pa = (na != 0), pb = (nb != 0);
    wire dec  = !iss_q && (pa || pb);
    wire tk_a = dec && pa;
    wire tk_b = dec && !pa;
    wire wa = la && ((na - (tk_a ? 1'b1 : 1'b0)) < BQE);   // room after this edge's read
    wire wb = lb && ((nb - (tk_b ? 1'b1 : 1'b0)) < BQE);
    reg  [11:0] fv;
    reg  [8:0]  ff_q;
    reg  ovw_q, ncan_q;
    function automatic [BQE-1:0] rot(input [BQE-1:0] p);
        rot = (BQE == 1) ? p : {p[BQE-2:0], p[BQE-1]};
    endfunction
    function automatic [96:0] pick(input [97*BQE-1:0] m, input [BQE-1:0] p);
        integer j; begin pick = 97'd0; for (j = 0; j < BQE; j = j + 1) pick = pick | (m[97*j +: 97] & {97{p[j]}}); end
    endfunction
    wire [97*BQE-1:0] fa_flat, fb_flat;
    genvar g;
    generate for (g = 0; g < BQE; g = g + 1) begin : g_fq
        assign fa_flat[97*g +: 97] = fq_a[g];
        assign fb_flat[97*g +: 97] = fq_b[g];
        always @(posedge ck) begin
            if (wa && wp_a[g]) fq_a[g] <= ld_a;
            if (wb && wp_b[g]) fq_b[g] <= ld_b;
        end
    end endgenerate
    reg  [96:0] ow;                           // the word being sent (copy A or B head)
    always @(posedge ck) if (dec) ow <= tk_a ? pick(fa_flat, rp_a) : pick(fb_flat, rp_b);
    always @(posedge ck or negedge r_rx)
        if (!r_rx) begin
            v0_a <= 1'b0; v0_b <= 1'b0; la <= 1'b0; lb <= 1'b0; na <= 0; nb <= 0; iss_q <= 1'b0; selb <= 4'd0; ovw_q <= 1'b0; ncan_q <= 1'b0;
            wp_a <= 1; wp_b <= 1; rp_a <= 1; rp_b <= 1;
        end else begin
            v0_a <= rv_a; v0_b <= rv_b; la <= en_a; lb <= en_b;
            na <= na + (wa ? 1'b1 : 1'b0) - (tk_a ? 1'b1 : 1'b0);
            nb <= nb + (wb ? 1'b1 : 1'b0) - (tk_b ? 1'b1 : 1'b0);
            if (wa) wp_a <= rot(wp_a);
            if (wb) wp_b <= rot(wp_b);
            if (tk_a) rp_a <= rot(rp_a);
            if (tk_b) rp_b <= rot(rp_b);
            iss_q <= dec;
            if (dec) selb <= {4{tk_b}};
            ovw_q  <= (la && !wa) || (lb && !wb);
            ncan_q <= (v0_a && !can_a) || (v0_b && !can_b);
        end
    // ------------------------------------------------------------------ word to hd_ctl
    wire [96:0] body = {ow[96:84] ^ ((MUT == 2 && selb[3]) ? 13'h1000 : 13'h0), ow[83:0]};
    wire copy = (MUT == 1) ? 1'b0 : selb[0];
    wire wf;
    wire [11:0] fv_word = (MUT == 4) ? 12'd0 : fv;
    ot_s81hd_beat_tx #(.W(WW), .N(2), .P(62), .IDLE_ZERO(1)) u_wtx (.ck(ck), .rn(r_rx), .v(iss_q), .d({fv_word, copy, body}),
        .o(m_rx_o), .fault(wf));
    always @(posedge ck or negedge r_rx)
        if (!r_rx) begin fv <= 12'd0; ff_q <= 9'd0; end
        else begin
            ff_q <= {own_f, fl_b, fl_a};  // DIE-HEAD-65: same +1 as the RX data, in-band fault position unchanged
            fv <= fv | {wf, ovw_q, ncan_q, ff_q};
        end
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

// ================================================================================================================
// HEAD-92 11-09 (COORD 08:1x): HEAD-LOCAL copies of the RBL-capable collector modules from codex/head-mesh-collector-1113@b6d8c0d798e
// (ot_s81ph_coll_lane_safe4 + dsfd_coll_lane_w_safe8_ntf, ot_s81ph_link_ep_safe4, ot_s81ph_link_gbx_safe3), renamed *_hd, verbatim
// otherwise.  Only hd_mesh (u_ln above) uses them; rtl/dsrom_sys/s81_ph/ is unchanged, so S81 bind6 and hd_lep0N keep the
// shared modules.  Helper cells (ot_s81ph_kff4_*, kp4_20, rewind4, mem1r1w, ...) stay shared from rtl/dsrom_sys/s81_ph/.
// ================================================================================================================
// Changes, all cycle-identical at every port (lane miter against the legacy P1 lane):
//  * replay buffer and receive FIFO on ot_sram_oldread_b64 (2 x 9 ot_sram_1r1w2c_256x64_m1 each; 2.56 pins/um faces);
//  * a_rep (1,106 loads: b_pay replay/in select) -> kept same-edge copies per ARS-bit slice, fed by two kept copies of
//    rep_r (same D);
//  * S2 reverse-frame stage: s2 data registers load every cycle (all consumers are qualified by the S2 valid), so
//    p_take drives no wide enable; ack_ok / rr_ok are kept REGISTERED copies per consumer group (same edge as s2v,
//    D = p_take && !bad, the original s2v && !s2bad); una has a kept copy for the S2 subtracts;
//  * ready/replay next state: (sndnx == nxt) evaluated as parallel compares selected by rewind / skip (same function,
//    shorter cone than the 16-level snd -> sub -> compare -> mux -> compare -> ready_r path);
//  * reset: RN same-depth reset leaves (rst_v), <= ~32 reset pins each, instead of one 191-load leaf;
//  * out_ready: ORN copies (caller registered flags), groups split across them.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81ph_link_ep (CLAUDE S81-PH collective, 2026-10-06): one die's END of a reliable link pair, derived from
// ot_dsrom_link_ct (rtl/dsrom_sys/ot_dsrom_link_ct.sv, unchanged).  Protocol, frame formats, invariants, fault codes
// and the three build-time mutants are ct's.  What changes:
//
//  (E) EXTERNAL CHANNEL.  ct holds sender, receiver and BOTH channel models of one direction.  Here the two
//      ot_dsrom_link_chan instances are replaced by ports, so the instance is the sender of this die's OUTBOUND
//      link plus the receiver of its INBOUND link:  f_tx (forward frames out) / f_rx (the peer's forward frames in),
//      r_tx (this receiver's reverse frames out) / r_rx (the peer receiver's reverse frames in).  Two ep instances
//      cross-wired through channels == two ct instances (one per direction), cycle for cycle
//      (tb_s81ph_link_ep: lockstep against ct).
//  (M) SRAM = 1: replay buffer and receive FIFO in ot_s81ph_mem1r1w (512x128 macros).  ct's replay read is
//      already a registered read (address = next cycle's index, same-cycle write forwarded); the receive FIFO's
//      registered output becomes the macro read register (read enable = drain, address = head).
//  (T) MARGIN-FIRST timing, no behaviour change: forward CRC generated over two cycles (TX_STAGES >= 2: partial
//      CRCs of the two payload halves registered in TX stage 0, XORed into stage 1 -- the CRC is affine in the
//      data); forward CRC check over two cycles (RX_STAGES >= 3); reverse-frame CRC check computed on the input
//      and registered beside the frame; pacer compare precomputed; replay index add as a wrap add (RP a power
//      of two).  The status counters stay (die tops leave them unloaded, synthesis removes them).
// ---------------------------------------------------------------------------
module ot_s81ph_link_ep_safe4_hd #(
    parameter integer FLIT_BYTES     = 69,
    parameter integer TX_STAGES      = 2,     // >= 2
    parameter integer CHANNEL_CYCLES = 60,    // used only to derive the ACK timeout (as ct)
    parameter integer CHANNEL_CYCLES_B = CHANNEL_CYCLES,   // CLAUDE S81-PH coll v2: second timeout basis, chosen by the static pin ch_b (one lane tile master serves UCIe and board lanes)
    parameter integer RX_STAGES      = 3,     // >= 3
    parameter integer CREDITS        = 512,
    parameter integer SEQW           = 10,
    parameter integer REPLAY         = 0,
    parameter integer ACK_TIMEOUT    = 0,
    parameter integer MAX_RETRY      = 8,
    parameter integer KEEPALIVE      = 16,
    parameter integer PHY_NUM        = 0,
    parameter integer PHY_DEN        = 1,
    parameter integer SRAM           = 0,
    // RXPIPE (ds-1010 2026-10-10, opt-in; RX_STAGES >= 3): the receive sequence classification is precomputed one stage
    // early against the NEXT expected sequence (exp_seq + this cycle's accept, both arms in parallel, selected at the
    // flop), so c_acc = registered in-order flag && !full: the 10-bit seq subtract / compare no longer sits in front of
    // fill / tail / exp_seq / the landing SRAM write in one cycle (coll lane lcrpe TT -560 exp_seq -> fill).  0 cycles.
    // TOREG (ds-1010 2026-10-10, opt-in): the ACK timeout limit (static ch_b select) is registered and the timer keeps a
    // registered at-limit flag, so timeout = occ && !progress && at_lim (coll lane lcrpg TT -470 = ch_b_q -> limit mux ->
    // timer == limit compare -> retry / rewind across the tile).  0 cycles.
    // MWR (ds-1010/coll-tu 2026-10-11, opt-in): the replay buffer and the receive FIFO use ot_s81ph_mem1r1w WREG = 1
    // (registered write ports beside the macros, read-after-write forwarded inside the wrapper; caller-visible timing
    // unchanged), and the replay forward word rb_fwd_d loads every cycle (it is read only when rb_fwd, i.e. right after an
    // accept, so its accept load enable was redundant): accept no longer drives 553-bit enables or macro pins directly
    // (lane lcrpi: hold stuck -68 at u_rb w_addr_in = nxt_i, a setup-critical register).  0 cycles.
    parameter integer MWR            = `ifdef OT_S81PH_EP_MWR 1 `else 0 `endif,
    parameter integer OLDREAD = 0,
    parameter integer MEM_NS = (FLIT_BYTES*8+1+7)/8,
    parameter integer MEM_NA = (MEM_NS+3)/4,
    parameter integer TOREG          = `ifdef OT_S81PH_EP_TOREG 1 `else 0 `endif,
    parameter integer RXPIPE         = `ifdef OT_S81PH_EP_RXPIPE 1 `else 0 `endif,
    // DNR (S81-SAFE-FIX/COLL 2026-10-19, opt-in, default 0 = same netlist): the frame DATA registers (TX pipe tp_f /
    // tp_lo / tp_hi, RX pipe xp_f, RX CRC partials p_lo / p_hi / p_got, reverse frames rr_f / rg_f) load every cycle in
    // reset-free processes.  Written inside the async-reset processes without a reset value, yosys kept them "hold during
    // reset" = one rst_n-gated enable per bit: the lane's reset synchroniser drove 6,837 loads (5,700 NAND2 / OA21 data
    // enables + the async clears; dscoll_lane_w_ltr gate textbook.high_fanout).  Every consumer is qualified by its
    // reset valid (tp_v / xp_v / rr_v / rg_v), so the transfer function after reset is unchanged.  0 cycles.
    parameter integer DNR            = 0,
    parameter integer PIPE           = 0,     // CLAUDE S81-PH coll lane v3: 1 = sender pipelined (see the PIPE notes below)
                                              // CLAUDE s81-blocks 2026-10-07: 2 = PIPE 1 + (a) the freed-count difference
                                              // d_fr registered in S2 (fr_seen only changes in S2-apply cycles, as una for
                                              // s2dack), (b) rdy_r / rep_r / credits / snd / snd_i computed for accept = 0
                                              // and 1 in parallel and selected by accept at the flop (lane e -489 / w -408)
    // derived frame widths (ports)
    parameter integer FFW_P = SEQW + 1 + FLIT_BYTES * 8 + 32,
    parameter integer RFW_P = 1 + SEQW + $clog2(CREDITS + 1) + 32,
    parameter integer ARS = 24,               // a_rep copy slice
    parameter integer RN = 12,                // reset leaves
    parameter integer ORN = 3,                // out_ready copies
    // FCOPY (S81-TILES-E 10-20, opt-in, default 0 = unchanged netlist): the freed-count snapshot enable (fr_seen <= rr_fr)
    // takes its own kept copy of ok_f (ok_f3, same d / edge), so ok_f keeps <= 32 loads when the lane REACH=1 netlist
    // shifts ABC's mapping (s7 pre-gate census: ok_f 39).  0 cycles.
    parameter integer FCOPY = 0,
    // WRL (S81-COLL8 10-20, opt-in, default 0 = unchanged netlist): RX FIFO write LANDING, 2 registered edges between the
    // receive decision (c_acc: c_diff / c_crc_ok / xp_v at the receive control) and the 18 FIFO address groups beside
    // their banks (s7 GRT native reach: 4.8k of 5,379 pairs > 405 um = c_diff/c_crc_ok/xp_v -> count_r/wp_r/u_m valid_r,
    // max 765 um, one cycle).  Edge 1: 3 kept copies of c_acc (one per 6 groups); edge 2: one kept copy per group (its own
    // group reset leaf), so no single-cycle wire spans the tile.  Data {c_last, c_data} follows in 2 reset-free stages.
    // The logical occupancy fill (c_full / overflow) still counts c_acc at once; the physical occupancy fillw / tail /
    // drain count the landed write (acc_p = c_acc 2 edges later), so a read never precedes its landed write (OLD-read
    // forwarding unchanged).  Credits return 2 edges later (freed counts drains).  +2 receive edges, priced in the kit.
    parameter integer WRL = 0,
    // RBL (FORM-COLL 11-05, opt-in, default 0 = unchanged netlist): REPLAY BUFFER LANDING, the whole replay memory subsystem
    // one registered edge behind the central send control, so the next-state cone (credits / una / nxt -> rdy, snd_i) stops
    // at the central flops and no longer crosses the tile to the 18 replay address groups (rf4 TT: 16 of 32 setup misses
    // ended on g_address.ready_r, -82.7, ~280 ps of it this broadcast).  Each group holds: ready_r = accept one edge late
    // (the group write enable), rp_r = snd_i one edge late, wp_r = local count of that enable; write data = a_in (already
    // {in_last,in_data} one edge late).  Every memory input is its RBL = 0 value delayed by exactly one edge, so rb_q is the
    // RBL = 0 rb_q one edge late; the TX pipe stage A outputs (a_v, a_snd, a_in, a_rep selects) take one more edge to stay
    // aligned.  Central control state is cycle-identical to RBL = 0 from the same inputs.  +1 TX edge (launch -> f_tx), in the
    // TOK ledger.  ATO deliberately keeps its RBL = 0 value: its margin (2 * KEEPALIVE + 32) absorbs the extra edge.
    parameter integer RBL = 0
) (
    input  wire                     clk,
    input  wire [RN-1:0]            rst_v,
    input wire [2*(MEM_NS+MEM_NA)-1:0] mem_rst_n,
    input  wire                     ch_b,      // static: 1 = ACK timeout from CHANNEL_CYCLES_B
    input  wire                     in_valid,
    output wire                     in_ready,
    input  wire [FLIT_BYTES*8-1:0]  in_data,
    input  wire                     in_last,
    output wire                     out_valid,
    input  wire [ORN-1:0]           out_ready_v,
    output wire [FLIT_BYTES*8-1:0]  out_data,
    output wire                     out_last,
    // external channels
    output wire                     f_tx_v,
    output wire [FFW_P-1:0]         f_tx,
    input  wire                     f_rx_v,
    input  wire [FFW_P-1:0]         f_rx,
    output wire                     r_tx_v,
    output wire [RFW_P-1:0]         r_tx,
    input  wire                     r_rx_v,
    input  wire [RFW_P-1:0]         r_rx,
    output reg  [31:0]              credit_stalls,
    output reg                      fault,
    output reg  [3:0]               fault_code,
    output reg  [31:0]              st_flits_tx,
    output reg  [31:0]              st_flits_rx_ok,
    output reg  [31:0]              st_crc_err,
    output reg  [31:0]              st_naks,
    output reg  [31:0]              st_replays,
    output reg  [31:0]              st_timeouts,
    output reg  [31:0]              st_retx_flits,
    output reg  [31:0]              st_max_replay_occ
);
    wire rst_n = rst_v[0];                       // only for non-synthesis checks below
    wire out_ready = out_ready_v[0];
    localparam integer W    = FLIT_BYTES * 8;
    localparam integer RP   = (REPLAY == 0) ? CREDITS : REPLAY;
    localparam integer CW   = $clog2(CREDITS + 1);
    localparam integer IW   = (RP > 1) ? $clog2(RP) : 1;
    localparam integer FPW  = SEQW + 1 + W;
    localparam integer FFW  = FPW + 32;
    localparam integer RVW  = 1 + SEQW + CW;
    localparam integer RFW  = RVW + 32;
    localparam integer RTT  = 2 * CHANNEL_CYCLES + TX_STAGES + 2 * PIPE + RX_STAGES + 6;
    localparam integer RTTB = 2 * CHANNEL_CYCLES_B + TX_STAGES + 2 * PIPE + RX_STAGES + 6;
    localparam integer ATO  = (ACK_TIMEOUT == 0) ? (RTT + 2 * KEEPALIVE + 32) : ACK_TIMEOUT;
    localparam integer ATOB = (ACK_TIMEOUT == 0) ? (RTTB + 2 * KEEPALIVE + 32) : ACK_TIMEOUT;
    localparam integer TW   = $clog2(((ATOB > ATO) ? ATOB : ATO) + 2);
    localparam integer RCW  = $clog2(MAX_RETRY + 2);
    localparam integer KW   = $clog2(KEEPALIVE + 1);
    localparam [SEQW-1:0] HALF = {1'b1, {(SEQW-1){1'b0}}};
    localparam [SEQW-1:0] RPS  = RP[SEQW-1:0];
    localparam integer    PW   = (CREDITS > 1) ? $clog2(CREDITS) : 1;
    localparam [31:0]     PLAST32 = CREDITS - 1;
    localparam [31:0]     CRED32  = CREDITS;
    localparam [31:0]     ATO32   = ATO - 1;
    localparam [31:0]     ATOB32  = ATOB - 1;
    localparam [31:0]     MR32    = MAX_RETRY;
    localparam [PW-1:0]   PLAST  = PLAST32[PW-1:0];
    localparam [CW:0]     CRED_W = CRED32[CW:0];
    localparam [TW-1:0]   ATO_WA = ATO32[TW-1:0];
    localparam [TW-1:0]   ATO_WB = ATOB32[TW-1:0];
    reg ch_b_q;                                // static pin, registered
    always @(posedge clk) ch_b_q <= ch_b;
    wire [TW-1:0]         ATO_W  = ch_b_q ? ATO_WB : ATO_WA;
    reg  [TW-1:0]         ato_q;                 // TOREG: registered limit (static after reset)
    always @(posedge clk) ato_q <= ATO_W;
    reg                   at_lim;                // TOREG: timer == limit, registered with the timer
    wire [TW-1:0]         ATO_S  = TOREG ? ato_q : ATO_W;
    localparam [RCW-1:0]  MR_W   = MR32[RCW-1:0];
    localparam integer    HB   = FPW / 2;           // CRC split point

`ifndef SYNTHESIS
    initial begin
        if (TX_STAGES < 2 || RX_STAGES < 3) $fatal(1, "ot_s81ph_link_ep: TX_STAGES >= 2 and RX_STAGES >= 3");
        if (RP < 1 || RP > (1 << (SEQW - 1)) || (1 << IW) != RP) $fatal(1, "ot_s81ph_link_ep: REPLAY must be a power of two <= 2^(SEQW-1)");
        if ((1 << PW) != CREDITS) $fatal(1, "ot_s81ph_link_ep: CREDITS must be a power of two");
        if (FFW != FFW_P || RFW != RFW_P) $fatal(1, "ot_s81ph_link_ep: frame width parameters");
        if (PHY_NUM < 0 || PHY_DEN < 1 || PHY_NUM > FLIT_BYTES * PHY_DEN) $fatal(1, "ot_s81ph_link_ep: PHY_NUM");
    end
`endif

`ifndef SYNTHESIS
    initial if(OLDREAD!=0 && (PIPE!=2 || MWR!=1 || SRAM!=1 || IW!=9 || PW!=9))
      $fatal(1,"COLL safe oldread requires current512-row PIPE2/MWR1 SRAM contract");
`endif
    // RP is a power of two: (x + d) mod RP for x < RP, d <= RP is the IW-bit wrap add (ct: 32-bit add and compare)
    function automatic [IW-1:0] idx_add(input [IW-1:0] x, input [SEQW-1:0] d);
        idx_add = x + d[IW-1:0];
    endfunction

    // ======================================================================== sender
    reg  [SEQW-1:0] una, snd, nxt;
`ifdef OT_COLL_NATIVE32
    // Independent complete same-edge state copies for consumer cones. Four
    // extra same-depth reset leaves separate copies from the state leaf.
    wire [SEQW-1:0] nxt_rw, nxt_ready, una_rw, una_skip;
    ot_s81ph_kff4_10 u_k_nxt_rw (.clk(clk),.rst_n(rst_v[12]),.d(nxt_nx),.q(nxt_rw));
    ot_s81ph_kff4_10 u_k_nxt_ready (.clk(clk),.rst_n(rst_v[12]),.d(nxt_nx),.q(nxt_ready));
    ot_s81ph_kff4_10 u_k_una_rw (.clk(clk),.rst_n(rst_v[13]),.d(una_n),.q(una_rw));
`ifdef OT_COLL_NATIVE32_OFF
    assign una_skip = una_rw;   // v8: only the unloaded legacy snd_off / ack_skip / snd_nx cones use this name
`else
    ot_s81ph_kff4_10 u_k_una_skip (.clk(clk),.rst_n(rst_v[13]),.d(una_n),.q(una_skip));
`endif
`else
    wire [SEQW-1:0] nxt_rw=nxt, nxt_ready=nxt, una_rw=una, una_skip=una;
`endif
    // safe4: kept copy of snd for the ready / skip compares, in its own kept hierarchy (ot_s81ph_kff4_10,
    // SYNTH_KEEP_MODULES): a same-D (* keep *) reg was merged back into snd by Yosys (mapped census 10-19: 33 loads)
    wire [SEQW-1:0] snd_c;
`ifdef OT_COLL_NATIVE32_OFF
`ifndef OT_COLL_NATIVE32
    initial $fatal(1, "OT_COLL_NATIVE32_OFF requires OT_COLL_NATIVE32");
`endif
    // v8 (S81-COLL4 10-20): the sender offset snd - una is STATE, kept as two same-edge registers (off_s: sender /
    // replay-index skip cone; off_r: ready cone), updated from the same next-state selects as snd / una.  The skip
    // compare d_ack > (snd + launch - una) becomes d_ack > off (+1 by the exact identity below): no subtract and no
    // increment sit in front of the replay address / ready registers.  0 added cycles, same transfer function.
    wire [SEQW-1:0] off_s, off_r;
`endif
    reg  [IW-1:0]   una_i, snd_i, nxt_i;
    reg  [CW-1:0]   credits;
    reg  [CW-1:0]   fr_seen;
    reg  [TW-1:0]   timer;
    reg  [RCW-1:0]  retry;

    localparam integer PCOST = FLIT_BYTES * PHY_DEN;
    localparam integer PAW   = $clog2(2 * PCOST + PHY_NUM + 1);
    localparam [PAW-1:0] PCOST_W = PCOST[PAW-1:0];
    localparam [PAW-1:0] PNUM_W  = PHY_NUM[PAW-1:0];
    localparam [PAW-1:0] PTH2    = 2 * PCOST - PHY_NUM;        // pace - PCOST + PNUM >= PCOST
    reg  [PAW-1:0]  pace;
    reg             pace_ok_r;
    wire            pace_ok = (PHY_NUM == 0) || pace_ok_r;

    wire [SEQW-1:0] occ = nxt_rw - una_rw;
    // PIPE (coll lane v3, s81ph-dsfd_coll_lane_w-34b3e75dd SS -971: nxt -> occ / ack compare -> una_i add ->
    // replay read address -> SRAM -> CRC -> tp, 30 levels, one cycle):
    //  (1) in_ready and replaying are REGISTERS computed from the next-state values (same function, one flop)
    //  (2) the replay read address is the snd_i register (read data one cycle later), payload registered (stage A
    //      launch, stage B payload), CRC from registers: +2 TX cycles (RTT / ACK timeout include them)
    //  (3) reverse frames: pin register -> pending slot P (newest frame wins; NAK sticky until taken) -> stage S2
    //      (ack / credit differences against una / fr_seen, which only change when S2 applies) -> applied: one
    //      reverse frame applied every other cycle at most; ACKs and freed counts are cumulative, so merging is exact
    //      for the protocol (go-back-N recovers any NAK merged into a newer ACK)
    //  (4) index registers are seq[IW-1:0] (RP a power of two): una_i_n = ack[IW-1:0], no add
    (* keep = "true" *) reg [3:0] rdy_k;
    (* keep = "true" *) reg [1:0] rep_ra;
    // LEC-COLL-1 11-03: same-D / same-reset-leaf duplicates are wires from the kept copy (synthesis merged them, the
    // LEC then paired the gold-only duplicate with a different sibling); 0 cycles, identical function from reset.
    wire            rdy_r = rdy_k[0], rep_r = rep_ra[0];
    wire            replaying = PIPE ? rep_r : (snd != nxt);
    // safe4: in_ready is a kept copy of rdy_r (the caller's pop), and accept is evaluated per consumer group from
    // kept rdy_r copies (a: snd / snd_i / rdy / rep, b: nxt / credits, c: launch / pace / faults) -- same edge, same D.
    // (rdy_k declared above)
    assign in_ready = rdy_k[3];
    wire            accept_a = in_valid && rdy_k[0], accept_b = in_valid && rdy_k[1], accept_c = in_valid && rdy_k[2];
    wire            accept = accept_c;
    wire            launch = (replaying && pace_ok) || accept_c;
    // replay storage: registered read of next cycle's index, same-cycle write forwarded
    wire [W:0]      rb_q;
    reg             rb_fwd;
    reg  [W:0]      rb_fwd_d;
    wire [W-1:0]    rd_data = rb_fwd ? rb_fwd_d[W-1:0] : rb_q[W-1:0];
    wire            rd_last = rb_fwd ? rb_fwd_d[W] : rb_q[W];
    wire [W-1:0]    l_data = replaying ? rd_data : in_data;
    wire            l_last = replaying ? rd_last : in_last;
    wire [FPW-1:0]  l_pay  = {snd, l_last, l_data};
    // PIPE TX stages A (launch, replay select, in word) / B (payload from the registered replay read)
    reg             a_v, b_v; reg [SEQW-1:0] a_snd; reg [W:0] a_in; reg [FPW-1:0] b_pay;
    // RBL: a0_* = the extra landing edge after stage A (RBL = 0: not used, ax_* = stage A)
    reg             a0_v; reg [SEQW-1:0] a0_snd; reg [W:0] a0_in;
    wire            ax_v   = (RBL != 0) ? a0_v : a_v;
    wire [SEQW-1:0] ax_snd = (RBL != 0) ? a0_snd : a_snd;
`ifdef OT_COLL_RBL_MUT_IN
    wire [W:0]      ax_in  = a_in;     // mutant: the fresh-word path misses the landing edge
`else
    wire [W:0]      ax_in  = (RBL != 0) ? a0_in : a_in;
`endif
    always @(posedge clk or negedge rst_v[0]) if (!rst_v[0]) begin a_v <= 1'b0; b_v <= 1'b0; a0_v <= 1'b0; end else begin a_v <= launch; b_v <= ax_v; a0_v <= (RBL != 0) && a_v; end
    always @(posedge clk) begin
        a_snd <= snd; a_in <= {in_last, in_data};
        a0_snd <= (RBL != 0) ? a_snd : {SEQW{1'b0}}; a0_in <= (RBL != 0) ? a_in : {(W+1){1'b0}};
        b_pay[FPW-1 -: SEQW] <= ax_snd;
    end
    // a_rep: kept copies, one per ARS payload bits, from two kept copies of rep_r (same D as rep_r)
    localparam integer NAR = (W + 1 + ARS - 1) / ARS;
    // (rep_ra declared above)
    generate for (genvar ar = 0; ar < NAR; ar = ar + 1) begin : g_arep
        localparam integer LO = ar * ARS, HI = ((ar + 1) * ARS > W + 1) ? W + 1 : (ar + 1) * ARS;
        (* keep = "true" *) reg a_rep_c, a_in_c;   // one-hot {replay, in} select copies: one AND-OR term per bit each
        reg a0_rep_c, a0_in_c;                     // RBL: the selects land with rb_q one edge later
`ifdef OT_COLL_RBL_MUT_SEL
        wire ax_rep = a_rep_c, ax_inc = a_in_c;    // mutant: the selects miss the landing edge
`else
        wire ax_rep = (RBL != 0) ? a0_rep_c : a_rep_c, ax_inc = (RBL != 0) ? a0_in_c : a_in_c;
`endif
        always @(posedge clk) begin
            a_rep_c <= rep_ra[(2 * ar) / NAR];
            a_in_c  <= !rep_ra[(2 * ar) / NAR];
            a0_rep_c <= (RBL != 0) && a_rep_c; a0_in_c <= (RBL != 0) && a_in_c;
            b_pay[HI-1:LO] <= ({(HI-LO){ax_rep}} & rb_q[HI-1:LO]) | ({(HI-LO){ax_inc}} & ax_in[HI-1:LO]);
        end
    end endgenerate
    wire [FPW-1:0]  t_pay    = PIPE ? b_pay : l_pay;
    wire            t_launch = PIPE ? b_v : launch;
    // (T) two-cycle forward CRC: partial CRCs of the halves (the CRC is affine: crc(a ^ b) = crc(a) ^ crc(b) ^ crc(0))
    wire [31:0]     l_crc_lo, l_crc_hi, crc_zero;
    ot_link_crc32 #(.W(FPW)) u_tx_crc_lo (.d({{(FPW-HB){1'b0}}, t_pay[HB-1:0]}), .crc(l_crc_lo));
    ot_link_crc32 #(.W(FPW)) u_tx_crc_hi (.d({t_pay[FPW-1:HB], {HB{1'b0}}}), .crc(l_crc_hi));
    ot_link_crc32 #(.W(FPW)) u_crc_zero (.d({FPW{1'b0}}), .crc(crc_zero));

    // reverse-frame receive register; (T) its CRC check is computed on the input and registered beside it
    // LEC-COLL-1 11-03: rr_v / rr_crc_ok = kept copy bit 0 (same D, same reset leaf rst_v[8]); 0 cycles
    (* keep = "true" *) reg [1:0] rrv_k, rrc_k;    // safe4: kept copies of rr_v / rr_crc_ok for the pending-slot enables
    reg  [RFW-1:0]  rr_f;
    wire            rr_v = rrv_k[0], rr_crc_ok = rrc_k[0];
    wire [31:0]     r_rx_crc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_chk (.d(r_rx[RFW-1:32]), .crc(r_rx_crc));
    wire            rr_ok0  = rr_v && rr_crc_ok;
    wire            rr_bad  = rr_v && !rr_crc_ok;
    reg  [RFW-1:0]  rrn_f;                       // DNR: reset-free reverse frame (qualified by rr_v)
    always @(posedge clk) rrn_f <= r_rx;
    wire [RFW-1:0]  rr_fs   = (DNR != 0) ? rrn_f : rr_f;
    wire            rr_nak0 = rr_fs[RFW-1];
    wire [SEQW-1:0] rr_ack0 = rr_fs[RFW-2 -: SEQW];
    wire [CW-1:0]   rr_fr0  = rr_fs[32 +: CW];
    // PIPE: pending slot P and decode stage S2
    (* keep = "true" *) reg ok_f;
    wire            s2v = ok_f;                  // LEC-COLL-1 11-03: same D (p_take) / reset leaf rst_v[0] as the kept ok_f
    reg             pv, pnak, s2nak, s2bad; reg [SEQW-1:0] pack, s2ack, s2dack; reg [CW-1:0] pfr, s2fr, s2dfr;
    wire            p_take = pv && !s2v;
    // kept registered copies, same edge as s2v: ok_u = ack_ok for una / una_i; ok_c = ack_ok for control; ok_f = rr_ok
    // for the freed-credit path.  una_s = kept copy of una for the S2 subtracts.
    // ok_u / ok_v / ok_c: same-edge copies of (p_take && !p_bad), each in its own kept hierarchy (ot_s81ph_kff4_1):
    // the (* keep *) regs were partially merged by Yosys (mapped census 10-19: ok_u 37 loads)
    wire ok_u, ok_v, ok_c;   // (ok_f declared above)
    (* keep = "true" *) reg [SEQW-1:0] una_s;
    wire [SEQW-1:0] p_dack = pack - una_s;
    wire            p_bad  = p_dack > (nxt_rw - una_s);
    wire ok_d = p_take && !p_bad;
`ifdef OT_COLL_NATIVE32_OFF
    reg [SEQW-1:0] s2dackm1; reg s2dnz;      // = s2dack - 1, s2dack != 0 (same edge, same inputs)
    always @(posedge clk) begin s2dackm1 <= pack + ~una_s; s2dnz <= (pack != una_s); end
`endif
    ot_s81ph_kff4_1 u_k_oku (.clk(clk), .rst_n(rst_v[0]), .d(ok_d), .q(ok_u));
    ot_s81ph_kff4_1 u_k_okv (.clk(clk), .rst_n(rst_v[0]), .d(ok_d), .q(ok_v));
    ot_s81ph_kff4_1 u_k_okc (.clk(clk), .rst_n(rst_v[0]), .d(ok_d), .q(ok_c));
`ifdef OT_COLL_NATIVE32
    wire ok_ready;
    ot_s81ph_kff4_1 u_k_ok_ready (.clk(clk), .rst_n(rst_v[15]), .d(ok_d), .q(ok_ready));
`ifdef OT_COLL_NATIVE32_OFF
    // v8d: own copies for the offset update (ok_o), the credit sum consumers (ok_f2 = ok_f) and the ready/state rewind
    // cones (nxt_rw2 / una_rw2), so ABC's per-bit mux expansion cannot push v3 roots past 32 (v8c census: ok_f 37,
    // nxt_rw[6] 36, ok_ready 35).
    wire ok_o, ok_o2, ok_f2; wire [SEQW-1:0] nxt_rw2, una_rw2;   // v8e: ok_o / ok_o2 one 10-bit select each (v8d ok_o 33)
    ot_s81ph_kff4_1 u_k_ok_o (.clk(clk), .rst_n(rst_v[14]), .d(ok_d), .q(ok_o));
    ot_s81ph_kff4_1 u_k_ok_o2 (.clk(clk), .rst_n(rst_v[15]), .d(ok_d), .q(ok_o2));
    ot_s81ph_kff4_1 u_k_ok_f2 (.clk(clk), .rst_n(rst_v[15]), .d(p_take), .q(ok_f2));
    ot_s81ph_kff4_10 u_k_nxt_rw2 (.clk(clk),.rst_n(rst_v[15]),.d(nxt_nx),.q(nxt_rw2));
    ot_s81ph_kff4_10 u_k_una_rw2 (.clk(clk),.rst_n(rst_v[14]),.d(una_n),.q(una_rw2));
`else
    wire ok_f2 = ok_f; wire [SEQW-1:0] nxt_rw2 = nxt_rw, una_rw2 = una_rw;
`endif
    wire ok_f3;
    generate if (FCOPY != 0) begin : g_fcopy
        ot_s81ph_kff4_1 u_k_ok_f3 (.clk(clk), .rst_n(rst_v[RN-1]), .d(p_take), .q(ok_f3));
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_v[0] && ok_f3 !== ok_f) $fatal(1, "COLL FCOPY ok_f3 copy differs");
`endif
    end else begin : g_nofcopy
        assign ok_f3 = ok_f;
    end endgenerate
`else
    wire ok_ready=ok_c;
`endif
    always @(posedge clk or negedge rst_v[0])
        if (!rst_v[0]) begin pv <= 1'b0; pnak <= 1'b0; ok_f <= 1'b0; una_s <= 0; end
        else begin
            ok_f <= p_take;
            una_s <= una_n;
            if (rr_ok0) begin pv <= 1'b1; pnak <= rr_nak0 | (pv && !p_take && pnak); end
            else if (p_take) begin pv <= 1'b0; pnak <= 1'b0; end
        end
    // S2 data: loaded every cycle (read only in S2-valid cycles, which follow a p_take edge)
    always @(posedge clk) begin
        if (rrv_k[0] && rrc_k[0]) pack <= rr_ack0;
        if (rrv_k[1] && rrc_k[1]) pfr <= rr_fr0;
        s2ack <= pack; s2fr <= pfr; s2nak <= pnak; s2dack <= p_dack; s2bad <= p_bad; s2dfr <= pfr - fr_seen;
    end
    wire            rr_ok   = PIPE ? s2v : rr_ok0;
    wire            rr_nak  = PIPE ? s2nak : rr_nak0;
    wire [SEQW-1:0] rr_ack  = PIPE ? s2ack : rr_ack0;
    wire [CW-1:0]   rr_fr   = PIPE ? s2fr : rr_fr0;
    wire [SEQW-1:0] d_ack   = PIPE ? s2dack : (rr_ack - una);
    wire [CW-1:0]   d_fr    = (PIPE >= 2) ? s2dfr : (rr_fr - fr_seen);
    wire            ack_bad = rr_ok && (PIPE ? s2bad : (d_ack > occ));   // fault code only (ok_* carry the control)
    wire [CW:0]     cred_sum = {1'b0, credits} + {1'b0, d_fr};
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            fr_bad  = 1'b0;
`else
    wire            fr_bad  = ok_f && (cred_sum > CRED_W);
`endif
    wire            ack_ok  = ok_c;                                 // = rr_ok && !ack_bad (registered copy)
    wire            progress = ack_ok && (d_ack != 0);
    wire [SEQW-1:0] una_n   = ok_u ? rr_ack : una;
    wire [IW-1:0]   una_i_n = ok_u ? rr_ack[IW-1:0] : una_i;     // = una_i + d_ack (indices are seq mod RP)
`ifdef OT_S81PH_EP_TOREG_MUT
    wire            timeout = (occ != 0) && !progress && (TOREG ? 1'b0 : (timer == ATO_W));  // mutant: the registered timeout never fires
`else
    wire            timeout = (occ != 0) && !progress && (TOREG ? at_lim : (timer == ATO_W));
`endif
`ifdef OT_DSROM_LINK_MUT_NOREPLAY
    wire            rewind  = 1'b0;
`else
    wire            rewind  = (ack_ok && rr_nak) || timeout;
`endif
    wire rewind_sender, rewind_ready;
`ifdef OT_S81PH_EP_TOREG_MUT
    wire rewind_at_limit = 1'b0;
`else
    wire rewind_at_limit = at_lim;
`endif
    ot_s81ph_rewind4 u_rw_sender (.nxt(nxt_rw), .una(una_rw), .ack_ok(ack_ok), .nak(rr_nak), .d_ack(d_ack), .at_lim(rewind_at_limit), .y(rewind_sender));
    ot_s81ph_rewind4 u_rw_ready (.nxt(nxt_rw2), .una(una_rw2), .ack_ok(ok_ready), .nak(rr_nak), .d_ack(d_ack), .at_lim(rewind_at_limit), .y(rewind_ready));
`ifdef OT_COLL_NATIVE32
    wire rewind_sender_state;
    ot_s81ph_rewind4 u_rw_sender_state (.nxt(nxt_rw2), .una(una_rw2), .ack_ok(ok_ready), .nak(rr_nak), .d_ack(d_ack), .at_lim(rewind_at_limit), .y(rewind_sender_state));
`else
    wire rewind_sender_state=rewind_sender;
`endif
    wire [SEQW-1:0] snd_l   = launch ? snd + 1'b1 : snd;
    wire [IW-1:0]   snd_i_l = launch ? idx_add(snd_i, 1) : snd_i;
    wire [SEQW-1:0] snd_off = snd_l - una_skip;
    wire            retry_exh = rewind && !progress && (retry >= MR_W);
    wire            ack_skip  = ack_ok && (d_ack > snd_off);
    wire [IW-1:0]   snd_i_nx  = (rewind_sender || ack_skip) ? una_i_n : snd_i_l;

    generate if(OLDREAD!=0) begin:g_rb_safe
        wire [MEM_NA*IW-1:0] wa_copy,ra_copy;
        wire [MEM_NA-1:0] wr_group;
`ifdef OT_COLL_NATIVE32_OFF
        // v8: the per-group write/accept term in_valid && ready_r crosses a kept boundary (ot_s81ph_kp4_20), so ABC
        // cannot fold in_valid into every rp_r / ready_r mux bit (v8 mapped census before this: in_valid 112 loads
        // = 105 AND3 mux terms; with the boundary in_valid drives one AND2 per group).
        wire [MEM_NA-1:0] wr_raw; wire [19:0] wr_kp;
        ot_s81ph_kp4_20 u_kp_wr (.a({{(20-MEM_NA){1'b0}}, wr_raw}), .y(wr_kp));
`ifndef SYNTHESIS
        initial if (MEM_NA > 20) $fatal(1, "COLL native32 v8: MEM_NA > 20 write-group boundary");
`endif
`endif
        for(genvar mg=0;mg<MEM_NA;mg=mg+1) begin:g_address
            (* keep="true" *) reg [IW-1:0] wp_r,rp_r;
            (* keep="true" *) reg ready_r;
`ifdef OT_COLL_NATIVE32_OFF
            assign wr_raw[mg]=(RBL != 0) ? 1'b0 : (in_valid && ready_r);
            wire wr=(RBL != 0) ? ready_r : wr_kp[mg];
`else
            wire wr=in_valid && ready_r;
`endif
            assign wr_group[mg]=wr;
            assign wa_copy[IW*mg+:IW]=wp_r;
            assign ra_copy[IW*mg+:IW]=rp_r;
            // RBL: ready_r holds the landed write enable (accept one edge late), rp_r the landed read index (snd_i one edge
            // late); both D are central registered / accept terms, no next-state cone.
`ifdef OT_COLL_RBL_MUT_WR
            wire rbl_wr_d = (mg == 0) ? 1'b0 : accept;     // mutant: group 0 never writes
`else
            wire rbl_wr_d = accept;
`endif
`ifdef OT_COLL_RBL_MUT_RP
            wire [IW-1:0] rbl_rp_d = accept_a ? sndinx_1k : sndinx_0k;     // mutant: the read index misses the landing edge
`else
            wire [IW-1:0] rbl_rp_d = snd_i;
`endif
            always @(posedge clk or negedge mem_rst_n[MEM_NS+mg])
              if(!mem_rst_n[MEM_NS+mg]) begin wp_r<=0;rp_r<=0;ready_r<=(RBL == 0);end
              else begin
                wp_r<=wp_r+IW'(wr);
                rp_r<=(RBL != 0) ? rbl_rp_d : (wr?sndinx_1k:sndinx_0k);
                ready_r<=(RBL != 0) ? rbl_wr_d : (wr?rdy_1k:rdy_0k);
              end
`ifndef SYNTHESIS
            always @(posedge clk) if(RBL == 0 && rst_n && mem_rst_n[MEM_NS+mg])
              if({wp_r,rp_r,ready_r,wr,rdy_k} !== {nxt_i,snd_i,rdy_r,accept,{4{rdy_r}}})
                $fatal(1,"COLL replay group state differs group%0d",mg);
`endif
        end
        ot_sram_oldread_b64 #(.W(W+1),.AW(IW),.SB(8),.GA(4),.GROUP_IO(1),
`ifdef OT_S81PH_OLDREAD_MUT
          .MUT(1)
`elsif OT_S81PH_B64_COLLIDE_MUT
          .MUT(2)
`else
          .MUT(0)
`endif
        ) u_m(.clk(clk),.rst_n(mem_rst_n[0+:MEM_NS]),.we(accept),.we_group(wr_group),
          .wa(wa_copy),.wd((RBL != 0) ? a_in : {in_last,in_data}),.re(1'b1),.re_group({MEM_NA{1'b1}}),.ra(ra_copy),.q(rb_q));
    end else begin:g_rb_legacy
    ot_s81ph_mem1r1w #(.W(W + 1), .DEPTH(RP), .SRAM(SRAM), .WREG(MWR)) u_rb (.clk(clk), .rst_n(rst_n),
        .we(accept), .wa(nxt_i), .wd({in_last, in_data}), .re(1'b1), .ra(PIPE ? snd_i : snd_i_nx), .q(rb_q));
    end endgenerate


    // TX pipe: stage 0 = {payload, partial CRCs}; stage 1 = {payload, CRC}; stages 2.. copies
    reg             tp_v [0:TX_STAGES-1];
    reg  [FFW-1:0]  tp_f [0:TX_STAGES-1];
    reg  [31:0]     tp_lo, tp_hi;
    genvar gi;
    generate for (gi = 0; gi < TX_STAGES; gi = gi + 1) begin : g_tx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= t_launch; tp_f[gi] <= {t_pay, 32'd0}; tp_lo <= l_crc_lo; tp_hi <= l_crc_hi; end
        end else if (gi == 1) begin : g_crc
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= {tp_f[gi-1][FFW-1:32], tp_lo ^ tp_hi
`ifndef OT_S81PH_EP_MUT_NOZERO
                    ^ crc_zero
`endif
                    }; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= tp_f[gi-1]; end
        end
    end endgenerate
    assign f_tx_v = tp_v[TX_STAGES-1];
    reg  [FFW-1:0]  tpn_f [0:TX_STAGES-1];       // DNR: reset-free frame data
    reg  [31:0]     tpn_lo, tpn_hi;
    generate if (DNR != 0) begin : g_tx_dnr
        for (gi = 0; gi < TX_STAGES; gi = gi + 1) begin : g_s
            if (gi == 0) begin : g_first
                always @(posedge clk) begin tpn_f[gi] <= {t_pay, 32'd0}; tpn_lo <= l_crc_lo; tpn_hi <= l_crc_hi; end
            end else if (gi == 1) begin : g_crc
                always @(posedge clk) tpn_f[gi] <= {tpn_f[gi-1][FFW-1:32], tpn_lo ^ tpn_hi
`ifndef OT_S81PH_EP_MUT_NOZERO
                    ^ crc_zero
`endif
                    };
            end else begin : g_rest
                always @(posedge clk) tpn_f[gi] <= tpn_f[gi-1];
            end
        end
    end endgenerate
    assign f_tx   = (DNR != 0) ? tpn_f[TX_STAGES-1] : tp_f[TX_STAGES-1];

    // ======================================================================== receiver
    reg             xp_v [0:RX_STAGES-1];
    reg  [FFW-1:0]  xp_f [0:RX_STAGES-1];
    generate for (gi = 0; gi < RX_STAGES; gi = gi + 1) begin : g_rx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= f_rx_v; xp_f[gi] <= f_rx; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= xp_v[gi-1]; xp_f[gi] <= xp_f[gi-1]; end
        end
    end endgenerate

    wire            c_v    = xp_v[RX_STAGES-1];
    reg  [FFW-1:0]  xpn_f [0:RX_STAGES-1];       // DNR: reset-free frame data
    generate if (DNR != 0) begin : g_rx_dnr
        for (gi = 0; gi < RX_STAGES; gi = gi + 1) begin : g_s
            if (gi == 0) begin : g_first
                always @(posedge clk) xpn_f[gi] <= f_rx;
            end else begin : g_rest
                always @(posedge clk) xpn_f[gi] <= xpn_f[gi-1];
            end
        end
    end endgenerate
    wire [FFW-1:0]  c_f    = (DNR != 0) ? xpn_f[RX_STAGES-1] : xp_f[RX_STAGES-1];
    // (T) CRC of RX stage RX_STAGES-3 in two halves, registered beside stage RX_STAGES-2, compared into the flag
    // registered beside the last stage (ct: one cycle, stage RX_STAGES-2)
    wire [FFW-1:0]  q_f    = (DNR != 0) ? xpn_f[RX_STAGES-3] : xp_f[RX_STAGES-3];
    wire [31:0]     q_lo, q_hi;
    ot_link_crc32 #(.W(FPW)) u_rx_crc_lo (.d({{(FPW-HB){1'b0}}, q_f[32 +: HB]}), .crc(q_lo));
    ot_link_crc32 #(.W(FPW)) u_rx_crc_hi (.d({q_f[FFW-1:32+HB], {HB{1'b0}}}), .crc(q_hi));
    reg  [31:0]     p_lo, p_hi, p_got;
    reg             c_crc_ok_r;
    wire [31:0]     p_lo_s, p_hi_s, p_got_s;
    always @(posedge clk or negedge rst_v[1])
        if (!rst_v[1]) begin c_crc_ok_r <= 1'b0; p_lo <= 0; p_hi <= 0; p_got <= 0; end
        else begin
            p_lo <= q_lo; p_hi <= q_hi; p_got <= q_f[31:0];
            c_crc_ok_r <= ((p_lo_s ^ p_hi_s ^ crc_zero) == p_got_s);
        end
    reg  [31:0]     pn_lo, pn_hi, pn_got;        // DNR: reset-free CRC partials
    always @(posedge clk) begin pn_lo <= q_lo; pn_hi <= q_hi; pn_got <= q_f[31:0]; end
    assign p_lo_s = (DNR != 0) ? pn_lo : p_lo;
    assign p_hi_s = (DNR != 0) ? pn_hi : p_hi;
    assign p_got_s = (DNR != 0) ? pn_got : p_got;
`ifdef OT_DSROM_LINK_MUT_NOCRC
    wire            c_crc_ok = 1'b1;
`else
    wire            c_crc_ok = c_crc_ok_r;
`endif
    wire [SEQW-1:0] c_seq  = c_f[FFW-1 -: SEQW];
    wire            c_last = c_f[32 + W];
    wire [W-1:0]    c_data = c_f[32 +: W];

    reg  [SEQW-1:0] exp_seq;
    reg             nak_sent, nak_req, dup_req;
    reg  [CW-1:0]   freed;
    reg  [CW-1:0]   fill;
    wire            acc_p;                       // physical (landed) FIFO write: c_acc (WRL 0) or c_acc 2 edges later
    wire [CW-1:0]   fill_p;                      // physical occupancy (drain side)
    reg  [PW-1:0]   head, tail;
    reg             out_valid_r;
    wire [W:0]      fifo_q;
    assign out_valid = out_valid_r;
    assign out_data  = fifo_q[W-1:0];
    assign out_last  = fifo_q[W];

    wire [SEQW-1:0] c_diff, c_back;
    wire            c_acc;
    generate if (RXPIPE != 0) begin : g_rxp
        // seq of the flit entering the last RX stage next edge, against exp_seq as it will be after this edge
        wire [FFW-1:0]  n_f   = (DNR != 0) ? xpn_f[RX_STAGES-2] : xp_f[RX_STAGES-2];
        wire [SEQW-1:0] n_seq = n_f[FFW-1 -: SEQW];
        reg  [SEQW-1:0] d_q;
`ifdef OT_S81PH_EP_RXPIPE_MUT
        always @(posedge clk or negedge rst_v[1]) if (!rst_v[1]) d_q <= 0; else d_q <= n_seq - exp_seq;   // mutant: ignores this cycle's accept
`else
        always @(posedge clk or negedge rst_v[1]) if (!rst_v[1]) d_q <= 0; else d_q <= c_acc ? (n_seq - exp_seq - 1'b1) : (n_seq - exp_seq);
`endif
        assign c_diff = d_q;
        assign c_back = {SEQW{1'b0}} - d_q;
    end else begin : g_rxc
        assign c_diff = c_seq - exp_seq;
        assign c_back = exp_seq - c_seq;
    end endgenerate
    wire            c_good   = c_v && c_crc_ok;
    wire            c_crcerr = c_v && !c_crc_ok;
    wire            c_inord  = c_good && (c_diff == 0);
    wire            c_full   = (fill == CREDITS[CW-1:0]);
    assign          c_acc    = c_inord && !c_full;
    wire            c_ovf    = c_inord && c_full;
    wire            c_ahead  = c_good && (c_diff != 0) && (c_diff < HALF);
    wire            c_behind = c_good && (c_diff >= HALF);
    wire            c_unexpl = (c_ahead && (c_diff >= RPS)) || (c_behind && (c_back > RPS));
    wire            c_nak    = (c_crcerr || c_ahead) && !nak_sent;
    wire            drain    = (fill_p != 0) && (!out_valid_r || out_ready);
    wire [MEM_NA-1:0] wl_g;                      // WRL: landed per-group write enables
    wire [W:0]      wl_d;                        // WRL: landed write data {last, data}
    generate if (WRL != 0) begin : g_wl
        localparam integer NL1 = 3;
        wire [NL1-1:0] wl1;
        wire acd1, acd2;
        for (gi = 0; gi < NL1; gi = gi + 1) begin : g_l1
            ot_s81ph_kff4_1 u_k_wl1 (.clk(clk), .rst_n(rst_v[RN-1]), .d(c_acc), .q(wl1[gi]));
        end
        for (gi = 0; gi < MEM_NA; gi = gi + 1) begin : g_l2
`ifdef OT_COLL_REACH_MUT_WL
            // mutant: group 0's landed write copy never fires
            ot_s81ph_kff4_1 u_k_wl2 (.clk(clk), .rst_n(mem_rst_n[MEM_NS+MEM_NA+MEM_NS+gi]), .d((gi == 0) ? 1'b0 : wl1[(gi*NL1)/MEM_NA]), .q(wl_g[gi]));
`else
            ot_s81ph_kff4_1 u_k_wl2 (.clk(clk), .rst_n(mem_rst_n[MEM_NS+MEM_NA+MEM_NS+gi]), .d(wl1[(gi*NL1)/MEM_NA]), .q(wl_g[gi]));
`endif
        end
        ot_s81ph_kff4_1 u_k_acd1 (.clk(clk), .rst_n(rst_v[RN-1]), .d(c_acc), .q(acd1));
        ot_s81ph_kff4_1 u_k_acd2 (.clk(clk), .rst_n(rst_v[RN-1]), .d(acd1), .q(acd2));
        reg [W:0] wd1, wd2;
        always @(posedge clk) begin wd1 <= {c_last, c_data}; wd2 <= wd1; end
        reg [CW-1:0] fillw;
        always @(posedge clk or negedge rst_v[RN-1])
            if (!rst_v[RN-1]) fillw <= 0;
            else fillw <= fillw + {{(CW-1){1'b0}}, acd2} - {{(CW-1){1'b0}}, drain};
        assign acc_p = acd2; assign fill_p = fillw; assign wl_d = wd2;
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_n && rst_v[RN-1] && (fill < fillw || fill - fillw > 2))
            $fatal(1, "COLL WRL logical/physical occupancy out of range fill=%0d fillw=%0d", fill, fillw);
`ifdef OT_COLL_REACH_MUT_WL
        localparam integer Q0 = 1;                   // the mutant's dropped copy is left to the FIFO group check
`else
        localparam integer Q0 = 0;
`endif
        always @(posedge clk) if (rst_n && rst_v[RN-1]) for (int q = Q0; q < MEM_NA; q++)
            if (wl_g[q] !== acd2) $fatal(1, "COLL WRL landed write copy %0d differs", q);
        initial if (RN < 13) $fatal(1, "ot_s81ph_link_ep_safe4_hd: WRL needs its own reset leaf rst_v[RN-1] (RN >= 13)");
`endif
    end else begin : g_nowl
        assign acc_p = c_acc; assign fill_p = fill; assign wl_g = {MEM_NA{1'b0}}; assign wl_d = {c_last, c_data};
    end endgenerate

    generate if(OLDREAD!=0) begin:g_fifo_safe
        localparam integer RB=MEM_NS+MEM_NA;
        wire [MEM_NA*PW-1:0] wa_copy,ra_copy;
        wire [MEM_NA-1:0] wr_group,rd_group;
`ifdef OT_COLL_NATIVE32_OFF
        // v8: per-group receive write term through a kept boundary (as the replay write groups): c_inord drives one
        // AND2 per group, not every wp_r / count_r bit term (v8b mapped census: c_inord-side OR2 33 loads).
        wire [MEM_NA-1:0] fwr_raw; wire [19:0] fwr_kp;
        ot_s81ph_kp4_20 u_kp_fwr (.a({{(20-MEM_NA){1'b0}}, fwr_raw}), .y(fwr_kp));
`endif
        for(genvar mg=0;mg<MEM_NA;mg=mg+1) begin:g_address
            (* keep="true" *) reg [PW-1:0] wp_r,rp_r;
            (* keep="true" *) reg [CW-1:0] count_r;
            (* keep="true" *) reg valid_r;
            wire ordy=out_ready_v[1+(mg*(ORN-1))/MEM_NA];   // out_ready copy for this group
            wire rd=(count_r!=0)&&(!valid_r||ordy);
`ifdef OT_COLL_NATIVE32_OFF
            assign fwr_raw[mg]=(WRL!=0)?1'b0:(c_inord&&(count_r!=CW'(CREDITS)));
            wire wr=(WRL!=0)?wl_g[mg]:fwr_kp[mg];
`else
            wire wr=(WRL!=0)?wl_g[mg]:(c_inord&&(count_r!=CW'(CREDITS)));
`endif
            assign wr_group[mg]=wr; assign rd_group[mg]=rd;
            assign wa_copy[PW*mg+:PW]=wp_r;assign ra_copy[PW*mg+:PW]=rp_r;
            always @(posedge clk or negedge mem_rst_n[RB+MEM_NS+mg])
              if(!mem_rst_n[RB+MEM_NS+mg]) begin wp_r<=0;rp_r<=0;count_r<=0;valid_r<=0;end
              else begin
                wp_r<=(wp_r==PLAST&&wr)?PW'(0):wp_r+PW'(wr);
                rp_r<=(rp_r==PLAST&&rd)?PW'(0):rp_r+PW'(rd);
                count_r<=count_r+CW'(wr)-CW'(rd);
                if(rd) valid_r<=1;else if(valid_r&&ordy) valid_r<=0;
              end
`ifndef SYNTHESIS
            always @(posedge clk) if(rst_n && mem_rst_n[RB+MEM_NS+mg])
              if({wp_r,rp_r,count_r,valid_r,wr,rd} !== {tail,head,fill_p,out_valid_r,acc_p,drain})
                $fatal(1,"COLL FIFO group state differs group%0d",mg);
`endif
        end
        ot_sram_oldread_b64 #(.W(W+1),.AW(PW),.SB(8),.GA(4),.GROUP_IO(1),
`ifdef OT_S81PH_OLDREAD_MUT
          .MUT(1)
`elsif OT_S81PH_B64_COLLIDE_MUT
          .MUT(2)
`else
          .MUT(0)
`endif
        ) u_m(.clk(clk),.rst_n(mem_rst_n[RB+:MEM_NS]),.we(acc_p),.we_group(wr_group),
          .wa(wa_copy),.wd(wl_d),.re(drain),.re_group(rd_group),.ra(ra_copy),.q(fifo_q));
    end else begin:g_fifo_legacy
    ot_s81ph_mem1r1w #(.W(W + 1), .DEPTH(CREDITS), .SRAM(SRAM), .WREG(MWR)) u_fifo (.clk(clk), .rst_n(rst_n),
        .we(c_acc), .wa(tail), .wd({c_last, c_data}), .re(drain), .ra(head), .q(fifo_q));
    end endgenerate


    reg  [SEQW-1:0] tx_ack;
    reg  [CW-1:0]   tx_fr;
    reg  [KW-1:0]   ka;
    wire            rg_need = nak_req || dup_req || (exp_seq != tx_ack) || (freed != tx_fr) || (ka == 0);
    wire [RVW-1:0]  rg_pay  = {nak_req, exp_seq, freed};
    wire [31:0]     rg_crc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_gen (.d(rg_pay), .crc(rg_crc));
    reg             rg_v;
    reg  [RFW-1:0]  rg_f;
    assign r_tx_v = rg_v;
    reg  [RFW-1:0]  rgn_f;                       // DNR: reset-free reverse frame (qualified by rg_v)
    always @(posedge clk) rgn_f <= {rg_pay, rg_crc};
    assign r_tx   = (DNR != 0) ? rgn_f : rg_f;

    // ======================================================================== state
    reg  [3:0] fault_n;
    always @* begin
        fault_n = 4'd0;
        if      (retry_exh)                  fault_n = 4'd1;
        else if (ack_bad)                    fault_n = 4'd2;
        else if (c_ovf)                      fault_n = 4'd3;
        else if (accept && (occ >= RPS))     fault_n = 4'd4;
        else if (fr_bad)                     fault_n = 4'd5;
        else if (c_unexpl)                   fault_n = 4'd6;
    end
    wire pace_ok_launch = (pace >= PTH2);
    wire pace_ok_inc    = ({1'b0, pace} + {1'b0, PNUM_W}) >= {1'b0, PCOST_W};
    wire [SEQW-1:0] nxt_nx = accept ? nxt + 1'b1 : nxt;
    wire [SEQW-1:0] snd_nx = rewind_sender_state ? una_n : (ack_skip ? rr_ack : snd_l);
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            cred_ok_nx = 1'b1;
`else
    wire [CW-1:0]   cred_nx = credits - {{(CW-1){1'b0}}, accept} + ((ok_f && !fr_bad) ? d_fr : {CW{1'b0}});
    wire            cred_ok_nx = cred_nx != 0;
`endif
    wire            pace_ok_nx = (PHY_NUM == 0) ? 1'b1 : (launch ? pace_ok_launch : (!pace_ok ? pace_ok_inc : pace_ok_r));
    wire [SEQW-1:0] occ_nx = nxt_nx - una_n;
    // PIPE 2: the same next-state functions for accept = 0 (_0) and accept = 1 (_1)
    wire            lnch_0 = replaying && pace_ok;
    wire [SEQW-1:0] sndl_0 = lnch_0 ? snd + 1'b1 : snd, sndl_1 = snd + 1'b1;
    wire [IW-1:0]   sndil_0 = lnch_0 ? idx_add(snd_i, 1) : snd_i, sndil_1 = idx_add(snd_i, 1);
`ifdef OT_COLL_NATIVE32_OFF
    // L > ((D + 1) mod 2^W)  ==  (L != 0) && ((D == 2^W-1) || ((L - 1) > D))   (Codex v6 identity, SAT-proved 31 inputs)
    wire            gto_s0 = d_ack > off_s, gto_s1 = s2dnz && ((&off_s) || (s2dackm1 > off_s));
    wire            skip_0 = ack_ok && (lnch_0 ? gto_s1 : gto_s0), skip_1 = ack_ok && gto_s1;
`else
    wire            skip_0 = ack_ok && (d_ack > (sndl_0 - una_skip)), skip_1 = ack_ok && (d_ack > (sndl_1 - una_skip));
`endif
    wire [SEQW-1:0] sndnx_0 = rewind_sender_state ? una_n : (skip_0 ? rr_ack : sndl_0);
    wire [SEQW-1:0] sndnx_1 = rewind_sender_state ? una_n : (skip_1 ? rr_ack : sndl_1);
    wire [IW-1:0]   sndinx_0 = (rewind_sender || skip_0) ? una_i_n : sndil_0;
    wire [IW-1:0]   sndinx_1 = (rewind_sender || skip_1) ? una_i_n : sndil_1;
    wire [SEQW-1:0] nxtnx_1 = nxt + 1'b1;
    wire [CW-1:0]   cred_r  = credits + ((ok_f2 && !fr_bad) ? d_fr : {CW{1'b0}});
    wire [CW-1:0]   cred_1  = cred_r - 1'b1;
    wire            pok_0   = (PHY_NUM == 0) ? 1'b1 : (lnch_0 ? pace_ok_launch : (!pace_ok ? pace_ok_inc : pace_ok_r));
    wire            pok_1   = (PHY_NUM == 0) ? 1'b1 : pace_ok_launch;
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            cok_0 = 1'b1, cok_1 = 1'b1;
`else
    wire            cok_0 = cred_r != 0, cok_1 = cred_1 != 0;
`endif
    // safe4: the same rdy / rep functions with every 10-bit compare evaluated in parallel on registers and the
    // rewind / skip / launch / ack selects applied to 1-bit results (no compare behind a 10-bit mux)
    // A distinct same-edge UNA register owns the subtraction cone; no buffered fanout claim.
`ifdef OT_COLL_NATIVE32
    wire rst_una_so=rst_v[14], rst_una_cmp=rst_v[15];
`else
    wire rst_una_so=rst_v[2], rst_una_cmp=rst_v[2];
`endif
`ifdef OT_COLL_NATIVE32_OFF
    wire            gt_so0  = d_ack > off_r, gt_so1 = s2dnz && ((&off_r) || (s2dackm1 > off_r));
`else
    wire [SEQW-1:0] una_so;
    ot_s81ph_kff4_10 u_k_una_so (.clk(clk), .rst_n(rst_una_so), .d(una_n), .q(una_so));
    wire [SEQW-1:0] so      = snd_c - una_so;
    wire            gt_so0  = d_ack > so, gt_so1 = d_ack > (so + 1'b1);
`endif
    wire            skp_0   = ok_ready && (lnch_0 ? gt_so1 : gt_so0), skp_1 = ok_ready && gt_so1;
    // una_c: kept same-edge copy of una (ot_s81ph_kff4_10) for the una_n == / < compares (mapped census 10-19: una[0] 43)
    wire [SEQW-1:0] una_c;
    ot_s81ph_kff4_10 u_k_una (.clk(clk), .rst_n(rst_una_cmp), .d(una_n), .q(una_c));
    wire            unq_0   = ok_v ? (rr_ack == nxt_ready) : (una_c == nxt_ready);           // una_n == nxt_ready
    wire            unq_1   = ok_v ? (rr_ack == (nxt_ready + 1'b1)) : (una_c == (nxt_ready + 1'b1));   // una_n == nxt_ready + 1
    wire            snq     = snd_c == nxt_ready, snq1 = (snd_c + 1'b1) == nxt_ready;
    wire            eq_0    = rewind_ready ? unq_0 : (skp_0 ? (rr_ack == nxt_ready) : (lnch_0 ? snq1 : snq));
    wire            eq_1    = rewind_ready ? unq_1 : (skp_1 ? (rr_ack == (nxt_ready + 1'b1)) : snq);
    wire            lt_0    = ok_v ? ((nxt_ready - rr_ack) < RPS) : ((nxt_ready - una_c) < RPS);
    wire            lt_1    = ok_v ? (((nxt_ready + 1'b1) - rr_ack) < RPS) : (((nxt_ready + 1'b1) - una_c) < RPS);
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            ck_0 = 1'b1, ck_1 = 1'b1;
`else
    wire            fr_use  = ok_f2 && !fr_bad;
    wire            ck_0    = fr_use ? (cred_sum[CW-1:0] != 0) : (credits != 0);
    wire            ck_1    = fr_use ? (cred_sum[CW-1:0] != 1) : (credits != 1);
`endif
    wire            rdy_0 = ck_0 && lt_0 && eq_0 && pok_0;
    wire            rdy_1 = ck_1 && lt_1 && eq_1 && pok_1;
    wire            rep_0 = !eq_0, rep_1 = !eq_1;
    // kept hierarchy boundary (ot_s81ph_kp4_20, SYNTH_KEEP_MODULES): the replay index / ready next states that the 18
    // replay-group copies load are computed ONCE; synthesis cannot re-derive the rewind / skip select inside every group
    // (mapped census: the select drove 156 group D loads).
    wire [IW-1:0]   sndinx_0k, sndinx_1k; wire rdy_0k, rdy_1k;
    ot_s81ph_kp4_20 u_kp_next (.a({sndinx_0, sndinx_1, rdy_0, rdy_1}), .y({sndinx_0k, sndinx_1k, rdy_0k, rdy_1k}));
`ifdef OT_COLL_NATIVE32_OFF
    // offset next state: own same-edge accept (nrdy_o = !rdy_r) and launch (rep_o = rep_r) copies, so accept_a /
    // lnch_0 / ok_u keep their v3 loads.  off' = 0 on rewind or skip (snd' = una' = rr_ack / una_n); else
    // off + launch - (ok ? d_ack : 0), d_ack = rr_ack - una exactly in an S2-apply cycle (una is frozen the cycle before).
    wire nrdy_o, rep_o;
    ot_s81ph_kff4_1 u_k_nrdy_o (.clk(clk), .rst_n(rst_v[14]), .d(!(accept_a ? rdy_1k : rdy_0k)), .q(nrdy_o));
    ot_s81ph_kff4_1 u_k_rep_o (.clk(clk), .rst_n(rst_v[14]), .d(accept_a ? rep_1 : rep_0), .q(rep_o));
    wire            accept_o = in_valid && !nrdy_o, lnch_o = rep_o && pace_ok;
    wire [SEQW-1:0] off_p1 = off_s + 1'b1, off_md = off_s - d_ack, off_md1 = off_s - s2dackm1;
    wire [SEQW-1:0] off_t1 = ok_o ? off_md1 : off_p1, off_t0 = ok_o2 ? off_md : off_s;
    wire [SEQW-1:0] offnx_0 = (rewind_sender_state || skip_0) ? {SEQW{1'b0}} : (lnch_o ? off_t1 : off_t0);
    wire [SEQW-1:0] offnx_1 = (rewind_sender_state || skip_1) ? {SEQW{1'b0}} : off_t1;
    wire [SEQW-1:0] off_d = accept_o ? offnx_1 : offnx_0;
    ot_s81ph_kff4_10 u_k_off_s (.clk(clk), .rst_n(rst_v[13]), .d(off_d), .q(off_s));
    ot_s81ph_kff4_10 u_k_off_r (.clk(clk), .rst_n(rst_v[14]), .d(off_d), .q(off_r));
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && rst_v[2] && rst_v[3] && rst_v[13] && rst_v[14]) begin
        if (off_s !== snd - una || off_r !== snd - una || nrdy_o !== !rdy_r || rep_o !== rep_r)
            $fatal(1, "COLL native32 v8 offset/accept copy differs");
        if (skip_0 !== (ack_ok && (d_ack > (sndl_0 - una))) || skip_1 !== (ack_ok && (d_ack > (sndl_1 - una))))
            $fatal(1, "COLL native32 v8 skip predicate differs");
        if (ok_u && (d_ack !== rr_ack - una)) $fatal(1, "COLL native32 v8 d_ack != rr_ack - una in an apply cycle");
        if (ok_o !== ok_u || ok_o2 !== ok_u || ok_f2 !== ok_f || nxt_rw2 !== nxt || una_rw2 !== una) $fatal(1, "COLL native32 v8 state copy differs");
    end
`endif
`endif
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && ({rdy_0, rdy_1, rep_0, rep_1, skp_0, skp_1} !==
        {cok_0 && ((nxt - una_n) < RPS) && (sndnx_0 == nxt) && pok_0, cok_1 && ((nxtnx_1 - una_n) < RPS) && (sndnx_1 == nxtnx_1) && pok_1,
         sndnx_0 != nxt, sndnx_1 != nxtnx_1, skip_0, skip_1}))
        $fatal(1, "COLL safe4 ready/replay restructure differs");
`endif

    // safe4 state: the original single reset process split per reset leaf (same statements, PIPE 2 / MWR 1 only)
    always @(posedge clk or negedge rst_v[2])
        if (!rst_v[2]) begin una <= 0; una_i <= 0; rdy_k <= 4'hf; rep_ra <= 2'b00; end
        else begin
            una <= una_n; una_i <= una_i_n;
            
            rdy_k <= {4{accept_a ? rdy_1k : rdy_0k}};
            
            rep_ra <= {2{accept_a ? rep_1 : rep_0}};
        end
    always @(posedge clk or negedge rst_v[3])
        if (!rst_v[3]) begin snd <= 0; snd_i <= 0; end
        else begin snd <= accept_a ? sndnx_1 : sndnx_0; snd_i <= accept_a ? sndinx_1k : sndinx_0k; end
    ot_s81ph_kff4_10 u_k_snd (.clk(clk), .rst_n(rst_v[3]), .d(accept_a ? sndnx_1 : sndnx_0), .q(snd_c));
    always @(posedge clk or negedge rst_v[4])
        if (!rst_v[4]) begin nxt <= 0; nxt_i <= 0; end
        else if (accept_b) begin nxt <= nxt + 1'b1; nxt_i <= idx_add(nxt_i, 1); end
    always @(posedge clk or negedge rst_v[5])
        if (!rst_v[5]) begin credits <= CREDITS[CW-1:0]; fr_seen <= 0; end
        else begin
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
            credits <= credits;
`else
            credits <= accept_b ? cred_1 : cred_r;
`endif
            if (ok_f3) fr_seen <= rr_fr;
        end
    always @(posedge clk or negedge rst_v[6])
        if (!rst_v[6]) begin timer <= 0; at_lim <= 1'b0; retry <= 0; end
        else begin
            if (occ == 0 || progress || rewind) begin timer <= 0; at_lim <= 1'b0; end
            else if (TOREG ? !at_lim : (timer != ATO_W)) begin timer <= timer + 1'b1; at_lim <= (timer + 1'b1 == ATO_S); end
            if (progress) retry <= {{(RCW-1){1'b0}}, rewind};
            else if (rewind && retry <= MR_W) retry <= retry + 1'b1;
        end
    always @(posedge clk or negedge rst_v[7])
        if (!rst_v[7]) begin pace <= PCOST_W; pace_ok_r <= 1'b1; end
        else if (PHY_NUM != 0) begin
            if (launch)        begin pace <= pace - PCOST_W + PNUM_W; pace_ok_r <= pace_ok_launch; end
            else if (!pace_ok) begin pace <= pace + PNUM_W;           pace_ok_r <= pace_ok_inc;    end
        end
    always @(posedge clk or negedge rst_v[8])
        if (!rst_v[8]) begin rrv_k <= 2'b00; rrc_k <= 2'b00; rg_v <= 1'b0; fault <= 1'b0; fault_code <= 4'd0; tx_ack <= 0; end
        else begin
            
            rrv_k <= {2{r_rx_v}}; rrc_k <= {2{r_rx_crc == r_rx[31:0]}};
            rg_v <= rg_need;
            if (rg_need) tx_ack <= exp_seq;
            if (fault_n != 0 && !fault) begin fault <= 1'b1; fault_code <= fault_n; end
        end
    always @(posedge clk or negedge rst_v[9])
        if (!rst_v[9]) begin exp_seq <= 0; nak_sent <= 1'b0; nak_req <= 1'b0; dup_req <= 1'b0; freed <= 0; end
        else begin
            if (c_acc) begin exp_seq <= exp_seq + 1'b1; nak_sent <= 1'b0; end
            else if (c_nak) nak_sent <= 1'b1;
            if (drain) freed <= freed + 1'b1;
            if (rg_need) begin nak_req <= 1'b0; dup_req <= 1'b0; end
            if (c_nak) nak_req <= 1'b1;
            if (c_behind) dup_req <= 1'b1;
        end
    always @(posedge clk or negedge rst_v[10])
        if (!rst_v[10]) begin fill <= 0; head <= 0; tail <= 0; out_valid_r <= 1'b0; end
        else begin
            if (acc_p) tail <= (tail == PLAST) ? {PW{1'b0}} : tail + 1'b1;
            if (drain) begin head <= (head == PLAST) ? {PW{1'b0}} : head + 1'b1; out_valid_r <= 1'b1; end
            else if (out_valid_r && out_ready) out_valid_r <= 1'b0;
            fill <= fill + {{(CW-1){1'b0}}, c_acc} - {{(CW-1){1'b0}}, drain};
        end
    always @(posedge clk or negedge rst_v[11])
        if (!rst_v[11]) begin
            tx_fr <= 0; ka <= KEEPALIVE[KW-1:0] - 1'b1; credit_stalls <= 0;
            st_flits_tx <= 0; st_flits_rx_ok <= 0; st_crc_err <= 0; st_naks <= 0;
            st_replays <= 0; st_timeouts <= 0; st_retx_flits <= 0; st_max_replay_occ <= 0;
        end else begin
            if (rg_need) begin tx_fr <= freed; ka <= KEEPALIVE[KW-1:0] - 1'b1; end
            else ka <= ka - 1'b1;
            if (in_valid && !in_ready) credit_stalls <= credit_stalls + 1;
            if (launch) st_flits_tx <= st_flits_tx + 1;
            if (launch && replaying) st_retx_flits <= st_retx_flits + 1;
            if (c_acc) st_flits_rx_ok <= st_flits_rx_ok + 1;
            st_crc_err <= st_crc_err + {31'd0, c_crcerr} + {31'd0, rr_bad};
            if (rg_need && nak_req) st_naks <= st_naks + 1;
            if (rewind) st_replays <= st_replays + 1;
            if (timeout) st_timeouts <= st_timeouts + 1;
            if ({{(32-SEQW){1'b0}}, occ} > st_max_replay_occ) st_max_replay_occ <= {{(32-SEQW){1'b0}}, occ};
        end
`ifndef SYNTHESIS
    initial if (PIPE != 2 || MWR != 1 || SRAM != 1 || OLDREAD != 1 || DNR != 1 || RN < 12 || ORN < 3)
        $fatal(1, "ot_s81ph_link_ep_safe4_hd: requires PIPE 2, MWR 1, SRAM 1, OLDREAD 1, DNR 1, RN >= 12, ORN >= 3");
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_link_gbx_safe3_hd (S81-COLL bank64 safe source, LEAD-S81 decision 10-19): the FMT 1 beat format of
// ot_s81ph_link_gbx (fixed 3-slots-in-4-beats group format), cycle-for-cycle identical at every port, rebuilt to the
// owner safe-design checklist.  ot_s81ph_link_gbx is unchanged (legacy tiles keep it).
//   (1) storage: the 4 x 595-bit runtime-indexed slot FIFO sf[sh] (2,380 flop bits, sh[0] drove 2,382 loads) becomes
//       ot_sram_showahead_b64 (ten ot_sram_1r1w2c_32x64_m1 banks, rows 0..3 used; registered write port, show-ahead read
//       of the NEXT head with current / previous logical write forwarding, physical same-address read suppressed).
//   (2) fanout: every wide select is a REGISTERED ONE-HOT computed from the next control state at the edge the
//       original control state is written, and replicated per SL-bit slice as kept flops (TX: 6 payload selects per
//       slice of the beat, 2 rem selects per slice of rem; RX: 3 cut selects per slice of f_rx, 3 hold selects per
//       slice of hold).  Each select flop drives <= SL data gates; each central next-state net drives <= 25 copies.
//       No select is computed from a wide shared combinational enable.  Same edges: no added data or control cycle.
//   (3) reset: control flops reset from RN same-depth copies (rst_n[0]: TX control, [1]: RX control, [2..]: copies);
//       payload (beat bits 3.., rem, bg, hold, f_rx, r_rx) carries no reset, as the original.
// Proof of equivalence (induction): each select copy is reset to f(reset state) and loaded with f(next state) at
// every edge the state is loaded with its next state, so at every cycle select == f(state), i.e. the original
// combinational select; the data muxes are the original case statements written as AND-OR of those selects.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_link_gbx_safe3_hd #(
    parameter integer FFW = 595,
    parameter integer RFW = 53,
    parameter integer IDLE_P = 1024,
    parameter integer BW = 512,
    parameter integer G = BW - 3 - RFW,
    parameter integer S = FFW + 1,
    parameter integer SL = 24,                       // data bits per select copy
    parameter integer NSH = (FFW + 15) / 16,         // slot-store forwarding slices (ot_sram_showahead_b64 NS)
    parameter integer RL = 24,                       // max flops per reset leaf
    // reset leaves: [0] TX control, [1] RX control, then select copies (ps 6 / rs 2 / hs 3 / cs 3 flops each), then
    // slot-store flag slices (8 slices x 2 flags per leaf)
    parameter integer NPC = (G + SL - 1) / SL, NRC = (3 * (S - G) + SL - 1) / SL, NHC = (G + SL - 1) / SL,
    parameter integer NCC = (FFW + SL - 1) / SL,
    parameter integer KP = RL / 6, KR = RL / 2, KH = RL / 4, KC = RL / 3,
    parameter integer OP = 2, OR = OP + (NPC + KP - 1) / KP, OH = OR + (NRC + KR - 1) / KR, OC = OH + (NHC + KH - 1) / KH,
    parameter integer OS = OC + (NCC + KC - 1) / KC,
    parameter integer RN = OS + (NSH + 7) / 8,       // reset leaves the caller supplies (same release depth)
    parameter integer MUT = 0                        // bench mutants: 1 = TX rem select one cycle stale, 2 = RX hold select stale
) (
    input  wire            clk,
    input  wire [RN-1:0]   rst_n,
    input  wire            f_tx_v,
    input  wire [FFW-1:0]  f_tx,
    input  wire            r_tx_v,
    input  wire [RFW-1:0]  r_tx,
    output reg  [BW-1:0]   beat_tx,
    input  wire            beat_rx_v,
    input  wire [BW-1:0]   beat_rx,
    output reg             f_rx_v,
    output reg  [FFW-1:0]  f_rx,
    output reg             r_rx_v,
    output reg  [RFW-1:0]  r_rx,
    output reg             locked,
    output reg             fault
);
    localparam integer K1 = S - G;                   // 140 at S 596 / G 456
    localparam integer IB1 = $clog2(IDLE_P + 1);
`ifndef SYNTHESIS
    initial if (3 + RFW + G != BW || 3 * S > 4 * G || 3 * K1 > G || SL < 1 || RL < 6 || RN != OS + (NSH + 7) / 8)
        $fatal(1, "ot_s81ph_link_gbx_safe3_hd: geometry");
`endif
    // ============================================================== TX central control (the original FMT 1 control)
    reg  [1:0]     sh, st, ph;
    reg  [2:0]     sn;
    reg  [IB1-1:0] ic;
    reg            idle_q;
    wire           need = !idle_q && (ph != 2'd3);
    wire           take = need && (sn != 0);
    // next control state
    wire           idle_n = !idle_q && (ic == IDLE_P - 2);
    wire [1:0]     ph_n   = idle_q ? ph : ph + 1'b1;
    wire [2:0]     sn_n   = sn + (f_tx_v ? 3'd1 : 3'd0) - (take ? 3'd1 : 3'd0);
    wire [1:0]     sh_n   = take ? sh + 1'b1 : sh;
    wire           need_n = !idle_n && (ph_n != 2'd3);
    wire           take_n = need_n && (sn_n != 0);
    // registered one-hot payload selects for the next beat: {t0, t1, t2, r1, r2, r3}
    //   t_k: slot (shifted k*K1) is taken in group phase k; r_k: rem's top k*K1 bits fill the low bits in phase k
    wire [5:0]     psel_n = {take_n && ph_n == 2'd0, take_n && ph_n == 2'd1, take_n && ph_n == 2'd2,
                             !idle_n && ph_n == 2'd1, !idle_n && ph_n == 2'd2, !idle_n && ph_n == 2'd3};
    wire [1:0]     rsel_n = {take_n, !need_n};             // {load slot, keep}: rem <= slot when need (0 when not taken)
    always @(posedge clk or negedge rst_n[0]) begin
        if (!rst_n[0]) begin
            sh <= 0; st <= 0; sn <= 0; ph <= 0; ic <= 0; idle_q <= (IDLE_P == 1); beat_tx[2:0] <= 3'd0; fault <= 1'b0;
        end else begin
            if (f_tx_v) st <= st + 1'b1;
            sn <= sn_n;
            sh <= sh_n;
            if (f_tx_v && sn == 4 && !take) fault <= 1'b1;
            ic <= idle_q ? 0 : ic + 1'b1;
            idle_q <= idle_n;
            beat_tx[2:0] <= idle_q ? {r_tx_v, 1'b1, 1'b0} : {r_tx_v, 1'b0, ph == 2'd0};
            ph <= ph_n;
        end
    end
    // slot store: q = sf[sh] (show-ahead of the head; the caller-side read address is the NEXT head)
    wire [FFW-1:0] q;
    wire [NSH-1:0] sh_rst_n;
    genvar c, i;
    generate for (c = 0; c < NSH; c = c + 1) begin : g_shr
        assign sh_rst_n[c] = rst_n[OS + c / 8];
    end endgenerate
    ot_sram_showahead_b64 #(.W(FFW), .AW(2), .WREG(1), .NS(NSH), .LOCAL_HIT(1)) u_sf (
        .clk(clk), .rst_n(sh_rst_n), .we(f_tx_v), .wa(st), .wd(f_tx), .ra(sh_n), .q(q));
    wire [S-1:0]   slotv = {q, 1'b1};                // slot when taken (bit 0 = slot valid)
    // TX payload: beat bits [BW-1:3] = {gpay, r_tx}; gpay[i] per the original case (ph) with slot = take ? {sf, 1} : 0
    localparam integer RLO = S - 3 * K1;              // lowest rem bit any phase reads (176)
    localparam integer RW  = 3 * K1;                  // rem bits kept (420)
    reg  [RW-1:0]  rem;                               // = original rem[S-1:RLO] (lower bits never read)
    wire [G-1:0]   gpay;
    generate for (c = 0; c < NPC; c = c + 1) begin : g_pc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > G) ? G : (c + 1) * SL;
        (* keep = "true" *) reg [5:0] ps;            // {t0, t1, t2, r1, r2, r3} copy
        always @(posedge clk or negedge rst_n[OP + c / KP])
            if (!rst_n[OP + c / KP]) ps <= 6'd0;   // reset state: take 0, ph 0
            else ps <= psel_n;
        for (i = LO; i < HI; i = i + 1) begin : g_b
            // LEC-COLL-1 11-03: one expression, no named a0..a3 terms: where slotv[.] = 1 (slot valid bit 0) a term is the
            // kept ps bit itself, and the named wire took over the flop's name (KEEP FAIL ps[5]/[4]/[3] -> a0/a1/a2).
            assign gpay[i] = (ps[5] & slotv[i])
                           | ((i >= K1)     ? (ps[4] & slotv[(i >= K1) ? i - K1 : 0])         : (ps[2] & rem[(i < K1) ? i + 2 * K1 : 0]))
                           | ((i >= 2 * K1) ? (ps[3] & slotv[(i >= 2 * K1) ? i - 2 * K1 : 0]) : (ps[1] & rem[(i < 2 * K1) ? i + K1 : 0]))
                           | ((i < 3 * K1)  ? (ps[0] & rem[(i < 3 * K1) ? i : 0]) : 1'b0);
        end
    end endgenerate
    // rem (original: if (!idle_q && need) rem <= slot): original bit j = RLO + k
    generate for (c = 0; c < NRC; c = c + 1) begin : g_rc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > RW) ? RW : (c + 1) * SL;
        (* keep = "true" *) reg [1:0] rs;            // {load, keep} copy (neither: clear); one AND-OR term per bit each
        always @(posedge clk or negedge rst_n[OR + c / KR])
            if (!rst_n[OR + c / KR]) rs <= 2'b00;   // reset state: need 1, take 0 -> clear
            else rs <= (MUT == 1) ? {take, !need} : rsel_n;
        always @(posedge clk)
            rem[HI-1:LO] <= ({(HI-LO){rs[1]}} & slotv[RLO + LO +: (HI - LO)]) | ({(HI-LO){rs[0]}} & rem[HI-1:LO]);
    end endgenerate
    always @(posedge clk) beat_tx[BW-1:3] <= {gpay, r_tx};
    // ============================================================== RX
    reg            bv, bm, bi;
    reg  [G-1:0]   bg;
    reg  [1:0]     hunt;
    reg  [1:0]     mc;
    reg  [G-1:0]   hold;
    wire           gb  = bv && !bi;
    wire           due = (mc == 2'd3);
    wire [1:0]     rph = due ? 2'd0 : mc + 1'b1;
    // next control state (the original reset process)
    wire           bv_n = beat_rx_v, bm_n = beat_rx[0], bi_n = beat_rx[1];
    reg  [1:0]     hunt_n, mc_n;
    reg            locked_n, fv_n;
    always @(*) begin
        hunt_n = hunt; mc_n = mc; locked_n = locked; fv_n = 1'b0;
        if (gb) begin
            mc_n = (bm || due) ? 2'd0 : mc + 1'b1;
            if (hunt != 2) begin
                locked_n = 1'b0;
                if (bm) begin
                    if (hunt == 1 && due) begin hunt_n = 2; locked_n = 1'b1; end
                    else hunt_n = 1;
                end else if (hunt == 1 && due) hunt_n = 0;
            end else if (bm != due) begin
                hunt_n = bm ? 2'd1 : 2'd0; locked_n = 1'b0;
            end else begin
                if (rph != 2'd0) fv_n = hold[0];    // original: f_rx_v <= cut[0]; cut[0] = hold[0] in every phase
            end
        end
    end
    wire           gb_n  = bv_n && !bi_n;
    wire           due_n = (mc_n == 2'd3);
    wire [1:0]     rph_n = due_n ? 2'd0 : mc_n + 1'b1;
    wire           lk_n  = gb_n && hunt_n == 2'd2 && (bm_n == due_n);
    // hold selects {h0, h1, h2}: hold <= bg (phase 0, or the locking second marker), bg >> K1 (phase 1), bg >> 2K1 (phase 2)
    wire [2:0]     hsel_n = {(lk_n && rph_n == 2'd0) || (gb_n && hunt_n == 2'd1 && bm_n && due_n),
                             lk_n && rph_n == 2'd1, lk_n && rph_n == 2'd2};
    // cut selects {c1, c2, c0}
    wire [2:0]     csel_n = {rph_n == 2'd1, rph_n == 2'd2, rph_n == 2'd0 || rph_n == 2'd3};
    always @(posedge clk or negedge rst_n[1]) begin
        if (!rst_n[1]) begin
            bv <= 0; bm <= 0; bi <= 0; hunt <= 0; mc <= 0; locked <= 0; f_rx_v <= 0; r_rx_v <= 0;
        end else begin
            bv <= bv_n; bm <= bm_n; bi <= bi_n;
            r_rx_v <= beat_rx_v && beat_rx[2];
            hunt <= hunt_n; mc <= mc_n; locked <= locked_n; f_rx_v <= fv_n;
        end
    end
    always @(posedge clk) begin bg <= beat_rx[BW-1 -: G]; r_rx <= beat_rx[3 +: RFW]; end
    // hold slices
    generate for (c = 0; c < NHC; c = c + 1) begin : g_hc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > G) ? G : (c + 1) * SL;
        (* keep = "true" *) reg [3:0] hs;          // {h0, h1, h2, none}: one-hot, each drives one AND-OR term per bit
        always @(posedge clk or negedge rst_n[OH + c / KH])
            if (!rst_n[OH + c / KH]) hs <= 4'b0001;   // reset state: bv 0 -> hold
            else hs <= (MUT == 2) ? hs : {hsel_n, hsel_n == 3'd0};
        for (i = LO; i < HI; i = i + 1) begin : g_b
            wire s1 = (i + K1 < G)     ? bg[(i + K1 < G) ? i + K1 : 0]         : 1'b0;
            wire s2 = (i + 2 * K1 < G) ? bg[(i + 2 * K1 < G) ? i + 2 * K1 : 0] : 1'b0;
            always @(posedge clk)
                hold[i] <= (hs[3] & bg[i]) | (hs[2] & s1) | (hs[1] & s2) | (hs[0] & hold[i]);
        end
    end endgenerate
    // f_rx slices: f_rx <= cut[1 +: FFW]; cut[j] = phase 1: j < G ? hold[j] : bg[j - G];
    //   phase 2: j < G - K1 ? hold[j] : bg[j - G + K1]; phase 0/3: j < G - 2K1 ? hold[j] : bg[j - G + 2K1]
    generate for (c = 0; c < NCC; c = c + 1) begin : g_cc
        localparam integer LO = c * SL, HI = ((c + 1) * SL > FFW) ? FFW : (c + 1) * SL;
        (* keep = "true" *) reg [2:0] cs;
        always @(posedge clk or negedge rst_n[OC + c / KC])
            if (!rst_n[OC + c / KC]) cs <= 3'b100;   // reset state: mc 0 -> rph 1
            else cs <= csel_n;
        for (i = LO; i < HI; i = i + 1) begin : g_b
            localparam integer J = i + 1;
            wire v1 = (J < G)          ? hold[(J < G) ? J : 0]                   : bg[(J >= G) ? J - G : 0];
            wire v2 = (J < G - K1)     ? hold[(J < G - K1) ? J : 0]              : bg[(J >= G - K1) ? J - G + K1 : 0];
            wire v0 = (J < G - 2 * K1) ? hold[(J < G - 2 * K1) ? J : 0]          : bg[(J >= G - 2 * K1) ? J - G + 2 * K1 : 0];
            always @(posedge clk) f_rx[i] <= (cs[2] & v1) | (cs[1] & v2) | (cs[0] & v0);
        end
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_coll_lane_safe4_hd (S81-COLL bank64 safe source, LEAD-S81 decision 10-19): the collective link lane tile
// rebuilt to the owner safe-design checklist, cycle-identical at every port to the legacy P1 lane
// (ot_s81ph_coll_lane GFMT 1 / EPPIPE 2 / LCR 1 / RXSRAM 1; lane-pair miter tb_coll_safe4_boundary).  Fixed
// configuration (the production tile options): FB 69, SEQW 10, CREDITS 512, UPGATE 1, SAFE reset relays.
// All storage on the 64-bit native bank family (<= 6 pins/um faces):
//   endpoint replay 553x512 + receive FIFO 553x512: ot_sram_oldread_b64, 2 x 18 ot_sram_1r1w2c_256x64_m1
//   core landing (credit rx) 553x8:                  ot_link_credit_rx_b64,   9 ot_sram_1r1w2c_32x64_m1
//   gearbox slot store 595x4:                        ot_s81ph_link_gbx_safe3_hd, 10 ot_sram_1r1w2c_32x64_m1
// = 55 macros (was 10 x 512x128 + 5 x 32x128 + a 2,380-bit runtime-indexed flop array).
// Control fanout: registered one-hot selects / kept same-edge copies (see the gearbox and endpoint safe4 headers);
// credit tx DFREE with registered ready copies.  Reset: one balanced 3-edge tree (ot_rst_relay_tree3, same release
// depth as safe2: edges 1/2/3), every leaf drives <= ~32 reset pins.  0 added data / control cycles vs P1.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_coll_lane_safe4_hd #(
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 700,
    parameter integer IDLE_P = 1024,
    parameter integer TF_CLEANUP = 0,
    // REACH (S81-TILES-E 10-20, opt-in, default 0 = the v8 safe4 netlist): forwarded relay hops so no single-cycle wire
    // crosses the tile (s6c actual GRT native reach: 5,403 pairs > 405 um, max 757 um, receive control c_diff / c_crc_ok /
    // xp_v at the gearbox -> the 18 RX FIFO address groups at the core face).  REACH = 1:
    //   rx landing 2 stages (lr -> lr2, pin flop at the link face, second flop beside the gearbox)            +1 RX
    //   endpoint RX_STAGES 3 -> 5 (two forwarded frame hops gearbox -> receive control beside the RX FIFO)       +2 RX
    //   reverse (ACK / credit) frame relay 2 stages endpoint -> gearbox (reset-free; consumed only under lk1)   +2 ACK
    //   core landing lo_v / lo_d 1 stage at the core face before the credit-rx landing flops                    +1 core->link
    // Every hop is a plain register (no flow control); the credit / ACK protocol absorbs the extra edges (ACK timeout
    // derives from RTT incl. RX_STAGES, margin 2*KEEPALIVE+32 >> 2; core credits 8 >> landing RTT).
    // REACH = 2 (S81-COLL8 10-20): REACH 1 + the endpoint RX FIFO write landing (ot_s81ph_link_ep_safe4_hd WRL = 2: c_acc ->
    // 3 kept copies -> 18 per-group kept copies beside the FIFO banks, data 2 reset-free stages; its own reset leaf, EP_RN
    // + 1).  s7 GRT reach audit: 4.8k of 5,379 pairs > 405 um were this one-cycle cone.  +2 receive edges.
    parameter integer REACH = 0,
    // RBL (FORM-COLL 11-05, opt-in, default 0 = unchanged netlist): see ot_s81ph_link_ep_safe4_hd; +1 TX edge per lane.
    parameter integer RBL = 0,
    parameter integer CORE_CRED = 8 // opt-in matched endpoint credit/buffer depth, legacy8 unchanged
) (
    input  wire          clk,
    input  wire          rs_n,
    input  wire          ch_b,
    input  wire [514:0]  rx,
    output wire [511:0]  tx,
    output wire          tf,
    input  wire          lo_v,
    output wire          lo_r,
    input  wire [552:0]  lo_d,
    output wire          li_v,
    input  wire          li_r,
    output wire [552:0]  li_d,
    output reg  [2:0]    flt
);
    localparam integer FB = 69, CREDITS = 512, SEQW = 10;
    localparam integer W = FB * 8;
    localparam integer FFW = SEQW + 1 + W + 32;
    localparam integer RFW = 1 + SEQW + $clog2(CREDITS + 1) + 32;
    localparam integer PNUM = FB * 3 * (IDLE_P - 1);
    localparam integer PDEN = 4 * IDLE_P;
    // reset leaves
    localparam integer HEAD_NS = (W + 1 + 15) / 16;          // credit rx forwarding slices (35)
    localparam integer HEAD_RL = (HEAD_NS + 7) / 8;          // leaves for them (8 slices x 2 flags each)
    localparam integer MEM_NS = (W + 1 + 7) / 8, MEM_NA = (MEM_NS + 3) / 4, MEM_RST = 2 * (MEM_NS + MEM_NA);
    `ifdef OT_COLL_NATIVE32
    localparam integer EP_RN = (REACH >= 2) ? 17 : 16, GB_RN = 22;
`else
    localparam integer EP_RN = (REACH >= 2) ? 13 : 12, GB_RN = 22;
`endif   // = ot_s81ph_link_gbx_safe3_hd RN (checked there)
    localparam integer R_LOC = 0, R_CRX = 1, R_CTX = 2, R_HEAD = 3, R_EP = R_HEAD + HEAD_RL, R_MEM = R_EP + EP_RN,
                       R_GB = R_MEM + MEM_RST, NREG = R_GB + GB_RN;
    wire [NREG-1:0] rr;
`ifdef OT_HE_EPC
    // HEAD-92/H2 11-10: u_rr + u_ep live in the hard core u_epc (ot_s81hd_he_epc, same params / names / wiring);
    // the leaves this module uses come back as rr_lo / rr_gb, the EP / MEM leaves stay inside the core.
    wire [R_EP-1:0] epc_rr_lo; wire [GB_RN-1:0] epc_rr_gb;
    assign rr[R_EP-1:0] = epc_rr_lo;
    assign rr[R_GB +: GB_RN] = epc_rr_gb;
    assign rr[R_GB-1:R_EP] = {(R_GB-R_EP){1'b1}};   // unused here (read only inside the core)
    generate if (CH_UCIE != 100 || CH_BOARD != 700 || IDLE_P != 1024 || REACH != 2 || RBL != 0) begin : g_epc_param_check
        ot_s81hd_he_epc_param_mismatch u_bad ();   // the hard core is built for these values only
    end endgenerate
`else
    ot_rst_relay_tree3 #(.REGIONS(NREG)) u_rr (.clk(clk), .rst_n_in(rs_n), .rst_n(rr));
`endif
    wire rst_n = rr[R_LOC];
    wire [HEAD_NS-1:0] head_rst_n;
    genvar k;
    generate for (k = 0; k < HEAD_NS; k = k + 1) begin : g_hr
        assign head_rst_n[k] = rr[R_HEAD + k / 8];
    end endgenerate
    // rx pin landing: reset only on the three flag bits
    reg [2:0] lr_f0; reg [511:0] lr_d0;
    always @(posedge clk or negedge rst_n) if (!rst_n) lr_f0 <= 3'b000; else lr_f0 <= {rx[514], rx[513], rx[0]};
    always @(posedge clk) lr_d0 <= rx[512:1];
    wire [2:0] lr_f; wire [511:0] lr_d;
    generate if (REACH != 0) begin : g_lr2
        reg [2:0] lr_f2; reg [511:0] lr_d2;
        always @(posedge clk or negedge rst_n) if (!rst_n) lr_f2 <= 3'b000; else lr_f2 <= lr_f0;
`ifdef OT_COLL_REACH_MUT_LR
        always @(posedge clk) lr_d2 <= lr_d2;   // mutant: the second rx landing hop never loads its beat
`else
        always @(posedge clk) lr_d2 <= lr_d0;
`endif
        assign lr_f = lr_f2; assign lr_d = lr_d2;
    end else begin : g_lr1
        assign lr_f = lr_f0; assign lr_d = lr_d0;
    end endgenerate
    // core -> link: credit landing on bank64 SRAM
    wire iv, ir, il; wire [W-1:0] id;
    reg  lk1, up;
    wire ir_g = ir && up;
    wire lcf;
    wire lo_vl; wire [W:0] lo_dl;
    generate if (REACH != 0) begin : g_lo2
        reg lo_vq; reg [W:0] lo_dq;
        always @(posedge clk or negedge rr[R_CRX]) if (!rr[R_CRX]) lo_vq <= 1'b0; else lo_vq <= lo_v;
`ifdef OT_COLL_REACH_MUT_LO
        always @(posedge clk) lo_dq <= lo_dq;   // mutant: landing data never loads
`else
        always @(posedge clk) lo_dq <= lo_d;
`endif
        assign lo_vl = lo_vq; assign lo_dl = lo_dq;
    end else begin : g_lo1
        assign lo_vl = lo_v; assign lo_dl = lo_d;
    end endgenerate
    ot_link_credit_rx_b64 #(.W(W + 1), .DEPTH(CORE_CRED), .WFREE(1), .LOCAL_HIT(1), .LOCAL_POP((CORE_CRED==12)||(RBL!=0))) u_ski (
        .clk(clk), .rst_n(rr[R_CRX]), .head_rst_n(head_rst_n), .l_valid(lo_vl), .l_data(lo_dl),
        .l_credit(lo_r), .o_valid(iv), .o_ready(ir_g), .o_data({il, id}), .fault(lcf));
    // link -> core: credit tx with registered ready copies
    wire ov, ol; wire [W-1:0] od; wire [2:0] orr;
    ot_link_credit_tx_rc #(.W(W + 1), .CRED(CORE_CRED), .NR(3)) u_sko (.clk(clk), .rst_n(rr[R_CTX]), .i_valid(ov), .i_ready(orr),
        .i_data({ol, od}), .l_valid(li_v), .l_data(li_d), .l_credit(li_r));
    wire ftv, rtv, rtv0, frv, rrv; wire [FFW-1:0] ft, fr; wire [RFW-1:0] rt, rt0, rrf; wire ep_f, gb_f, gb_l;
    generate if (REACH != 0) begin : g_rt2
        // reverse frame relay, reset-free: the gearbox consumes r_tx_v only under lk1 (cleared by every lane reset and
        // set only once the gearbox has locked, many edges after the 2-stage relay has flushed)
        reg rv1, rv2; reg [RFW-1:0] rf1, rf2;
`ifdef OT_COLL_REACH_MUT_RT
        always @(posedge clk) begin rv1 <= rtv0; rv2 <= 1'b0; rf1 <= rt0; rf2 <= rf1; end   // mutant: the relay drops every reverse frame
`else
        always @(posedge clk) begin rv1 <= rtv0; rv2 <= rv1; rf1 <= rt0; rf2 <= rf1; end
`endif
        assign rtv = rv2; assign rt = rf2;
    end else begin : g_rt1
        assign rtv = rtv0; assign rt = rt0;
    end endgenerate
`ifdef OT_HE_EPC
    ot_s81hd_he_epc u_epc (.clk(clk), .rst_n(rs_n), .ch_b(ch_b),
        .in_valid(iv && up), .in_ready(ir), .in_data(id), .in_last(il),
        .out_valid(ov), .out_ready_v(orr), .out_data(od), .out_last(ol),
        .f_tx_v(ftv), .f_tx(ft), .f_rx_v(frv), .f_rx(fr), .r_tx_v(rtv0), .r_tx(rt0), .r_rx_v(rrv), .r_rx(rrf),
        .fault(ep_f), .rr_lo(epc_rr_lo), .rr_gb(epc_rr_gb));
`else
    ot_s81ph_link_ep_safe4_hd #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(REACH != 0 ? 5 : 3), .CHANNEL_CYCLES(CH_UCIE), .CHANNEL_CYCLES_B(CH_BOARD),
        .CREDITS(CREDITS), .SEQW(SEQW), .PHY_NUM(PNUM), .PHY_DEN(PDEN), .SRAM(1), .PIPE(2), .RXPIPE(1), .TOREG(1), .MWR(1),
        .DNR(1), .OLDREAD(1), .RN(EP_RN), .ORN(3), .FCOPY(REACH != 0 ? 1 : 0), .WRL(REACH >= 2 ? 2 : 0), .RBL(RBL)) u_ep (
        .clk(clk), .rst_v(rr[R_EP +: EP_RN]), .mem_rst_n(rr[R_MEM +: MEM_RST]), .ch_b(ch_b),
        .in_valid(iv && up), .in_ready(ir), .in_data(id), .in_last(il),
        .out_valid(ov), .out_ready_v(orr), .out_data(od), .out_last(ol),
        .f_tx_v(ftv), .f_tx(ft), .f_rx_v(frv), .f_rx(fr), .r_tx_v(rtv0), .r_tx(rt0), .r_rx_v(rrv), .r_rx(rrf),
        .credit_stalls(), .fault(ep_f), .fault_code(), .st_flits_tx(), .st_flits_rx_ok(), .st_crc_err(),
        .st_naks(), .st_replays(), .st_timeouts(), .st_retx_flits(), .st_max_replay_occ());
`endif
    ot_s81ph_link_gbx_safe3_hd #(.FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P), .RN(GB_RN),
`ifdef OT_S81PH_GBX3_MUT
        .MUT(`OT_S81PH_GBX3_MUT)
`else
        .MUT(0)
`endif
    ) u_gb (
        .clk(clk), .rst_n(rr[R_GB +: GB_RN]), .f_tx_v(ftv), .f_tx(ft), .r_tx_v(rtv && lk1), .r_tx(rt), .beat_tx(tx),
        .beat_rx_v(lr_f[0] && lr_f[1]), .beat_rx(lr_d), .f_rx_v(frv), .f_rx(fr), .r_rx_v(rrv), .r_rx(rrf),
        .locked(gb_l), .fault(gb_f));
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 3'b000; else flt <= {lr_f[2], gb_f, ep_f};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lk1 <= 1'b0; up <= 1'b0; end
        else begin if (gb_l) lk1 <= 1'b1; if (rrv) up <= 1'b1; end
    generate if (TF_CLEANUP == 0) begin : g_tf_legacy
        ot_s81ph_ckbuf u_tf (.a(clk), .y(tf));
    end else begin : g_no_tf
        assign tf = 1'b0;
    end endgenerate
endmodule

module dsfd_coll_lane_w_safe8_ntf_hd #(parameter integer CORE_CRED = 8, parameter integer RBL = 0) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    wire tf_unused;
    ot_s81ph_coll_lane_safe4_hd #(.CH_BOARD(700), .TF_CLEANUP(1), .REACH(2), .CORE_CRED(CORE_CRED), .RBL(RBL)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf_unused), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
