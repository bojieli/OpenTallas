`timescale 1ns/1ps
`default_nettype none
// HBM-COLLQ (10-18, d4g plan (b)): the per-quadrant COLL GATHER MASTER. It closes the two open gaps of the two-ring
// x all-gather: nothing drove the ring stops' command inputs (ring A gather fields, ring B 291 b) and nothing landed
// their publish outputs (ag_*, 2 x 524 b) in the quadrant VM.
//
// One master per quadrant, all four run the SAME descriptor timeline (symmetric gather; per-quadrant fields are only
// the VM sectors). Static: every VM read, quantiser issue, ring lp write / state read / inject / transit / arrival and
// every VM write is at a compiled edge that is a fixed function of (launch edge, descriptor); no queue, credit, ready,
// arbitration or data-dependent issue. Any mismatch (unexpected / missing read response, publish valid / src / tag,
// two writes to one bank in one edge, a descriptor firing while the previous gather is in flight, a malformed
// descriptor, a non-finite QBG element) raises the sticky fault and never changes timing.
//
// Programme: F20 host frames through the standard ot_static_program_target (TGT_PIN=1, target id = strap tgt). Rows
// 0..15 are descriptors (payload cfg_data[223:0], the target checks the c7a1/address header):
//   [0] qbg  [1] rings2  [2] self_land  [18:3] t_start  [28:19] F (flits per quadrant slice, incl. QBG exponent flits)
//   [36:29] Bs (QBG code blocks per slice)  [52:37] src sector  [68:53] dst sector  [84:69] stride (words, mult. of 8)
//   [100:85] period (used from the descriptor at desc_base only)
// desc frame: base = first row, limit = one past the last row, loops = number of periods. After launch the sequencer
// runs `loops` periods of `period` edges; in each, row d fires when the period counter equals t_start[d] (rows in order).
//
// Canonical two-ring schedule (= the RTL3 MODE-0 rule; tools/hgi_sim/collq_gather_1018.py is the compiler model):
// global flit i -> ring r = i % R (R = 1 or 2), ring index k = i / R, direction d = k & 1 (0 = CW), ttl 3,
// tag k % 8; the flits of one k on both rings share every edge. Issue slots follow the 3-edge pattern {k even, k odd,
// idle}: the ring-A inject edge of ring index k is c(k) = G + 3 (k >> 1) + (k & 1). Arrivals at a stop: c + 2h, h = 1..3
// hops (src = PREV^h(qid) on CW, NEXT^h(qid) on CCW; ring order q0 -> q1 -> q3 -> q2 -> q0). Every directed link is
// used at most once an edge, and with a slice stride that is a multiple of 8 the up to 6 VM writes of one edge
// (4 publishes + 2 self-land) hit distinct banks (bank = (dst + i) mod 8): checked for F < 400 by the compiler model.
//
// Stages, counted in edges after the ISSUE edge of k (the edge ev[0] is loaded), = the ring-A inject edge c - 29:
//   QBG read rq @0 (bank samples @1) | plain read rq @15 | rr pin capture @8 / @23 | quantiser x @9 (tile S0 @10,
//   output @22) | quantiser pin capture @23 | payload P @24 = ring-B lp_data (+ local self-land kq @24, bank @25)
//   ring B commands (CMD_PIPE stop: one edge earlier than ring A): lp @24, state read @25, inject @27, rx/fwd @27+2h
//   ring A commands (merge register, one edge after ring B's): lp @25, state read @26, inject @28, rx/fwd @28+2h
//   publish pin capture @30+2h, VM kq register @31+2h (bank samples @32+2h).
// QBG (quantize-before-gather, golden hdc_golden_v41.quant_fp8 / act_quant, 32-element blocks, UE8M0): code flit i < Bs
// = block i of the local FP32 slice (4 words at src + 4i .. + 3, element j of the block at bits [32j +: 32] of the
// 1,024-b quantiser input, 8 reads an edge for the two rings) through the CLOSED quantiser tile ot_hbm_xp_aq_tree13
// (= ot_hdc_actquant, 13 edges); exponent flit i = Bs + g carries byte k = e(block 32 g + k) + 127. The slice lands as
// a PRE-QUANTISED VM record (codes then exponent words) that the SM x-load pre-quantised mode reads.
// ISA pass-through: the COLL issuer's ring-A fields (p_ring[57:0]) and its lp data (rc_d) are captured at the pins and
// merged with the gather fields in the ring-A merge register: +2 edges on every ISA ring-A command relative to the
// v5 parent (the compiler adds 2 to every ring-A-relative constant: rr outputs, carry / result timing). A field driven
// by both in one edge is a fault.
module ot_hgi_coll_gq_issue #(
    parameter integer MUT = 0       // bench mutants: 1 rx src of h=1 uses the CW table on CCW, 2 exponent bias 126,
                                    // 3 publish lands at i+1, 4 self-land skipped, 5 ring-B command one edge late,
                                    // 6 quantiser element line one bank short (x one edge early)
)(
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire [7:0]    tgt,
    // F20 host frame
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    output wire          configured, tgt_fault,
    output reg           active, done,
    output reg           fault,
    // ISA ring-A fields from the COLL issuer (v5 p_ring[57:0] order) + its lp data
    input  wire [57:0]   isa_ring,
    input  wire [255:0]  isa_lp_data,
    // ring A (ot_hgi_coll_ring_ag) command ports, merged
    output reg           ra_lp_we,
    output reg  [2:0]    ra_lp_tag,
    output reg  [255:0]  ra_lp_data,
    output reg           ra_state_read_add, ra_state_read_tx, ra_state_read_rr,
    output reg  [2:0]    ra_state_add_tag, ra_state_tx_tag, ra_state_rr_tag,
    output reg  [1:0]    ra_state_add_src,
    output reg           ra_state_add_rhs_acc, ra_state_tx_acc,
    output reg           ra_add_v,
    output reg  [2:0]    ra_add_tag,
    output reg  [1:0]    ra_add_src,
    output reg           ra_add_rhs_acc,
    output reg  [1:0]    ra_tx_inject, ra_tx_forward,
    output reg  [2:0]    ra_tx_tag,
    output reg  [1:0]    ra_tx_dst,
    output reg           ra_tx_result, ra_tx_acc, ra_tx_gather,
    output reg  [3:0]    ra_tx_ttl,
    output reg  [1:0]    ra_rx_slot,
    output reg  [3:0]    ra_rx_kind, ra_rx_src,
    output reg  [5:0]    ra_rx_tag,
    output reg           ra_rr_local,
    output reg  [2:0]    ra_rr_local_tag,
    // ring B (ot_hgi_coll_ring_b_stop) command ports
    output reg           rb_lp_we,
    output reg  [2:0]    rb_lp_tag,
    output reg  [255:0]  rb_lp_data,
    output reg           rb_state_read_tx,
    output reg  [2:0]    rb_state_tx_tag,
    output reg  [1:0]    rb_tx_inject, rb_tx_forward,
    output reg  [2:0]    rb_tx_tag,
    output reg  [3:0]    rb_tx_ttl,
    output reg  [1:0]    rb_rx_slot,
    output reg  [3:0]    rb_rx_kind, rb_rx_src,
    output reg  [5:0]    rb_rx_tag,
    // quadrant VM read group (via the COLL read share); banks 0-3 / 4-7 on separate faces
    output wire [67:0]   vm_rq_lo, vm_rq_hi,
    input  wire [1027:0] vm_rr_lo, vm_rr_hi,
    // to the landing leaf: descriptor at fire, event stream (stage 0), payload P (stage 24)
    output reg           ld_fire,
    output reg  [52:0]   ld_desc,      // {r2, self, qbg, F[9:0], Bs[7:0], dst[15:0], stride[15:0]}
    output wire          ld_ev_v,
    output wire [9:0]    ld_ev_k,
    output wire [1:0]    ld_p_v,
    output wire [511:0]  ld_p_d
);
    localparam integer ND = 40;                      // event pipeline depth (last use: ev[36])
    localparam integer S_QR = 0, S_PR = 15, S_QCAP = 8, S_PCAP = 23, S_P = 24;
    localparam integer S_BLP = 24, S_BRD = 25, S_BINJ = 27, S_BRX = 27;   // + 2h
    // ------------------------------------------------------------------ reset relay (3 edges) + straps
    // r4 (TW7-GQISSUE, SAFE-DESIGN items 1/3): the port lands in 2 registered stages at the face (kit reset_landing ->
    // ot_pin_regs.tcl OT_RST_LAND), then this relay gives one kept copy per region (r3: one relay flop drove 1,154
    // async loads): rn0 calendar/control, rn1 event + valid pipes + read expectations, rn2 VM read request, rn3 ring
    // command / merge registers, rn4 / rn5 quantisers 0 / 1 (valid flops only). All copies release on the same edge.
    wire [5:0] rl;
    ot_rst_relay #(.REGIONS(6)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rn = rl[0], rn1 = rl[1], rn2 = rl[2], rn3 = rl[3];
    reg [1:0] aq_vo_q, aq_fault_q; reg flt_q; wire flt_n = flt_q;
    reg [135:0] vm_rq; wire [2055:0] vm_rr = {vm_rr_hi, vm_rr_lo};
    assign vm_rq_lo = vm_rq[67:0]; assign vm_rq_hi = vm_rq[135:68];
    // quantisers: two instances of ot_hgi_coll_aq13 = the CLOSED quantiser tile RTL (ot_hbm_xp_aq_tree13 = ot_hdc_actquant,
    // 13 edges, input S0 / output registers at its pins) with its 1,024 x 9 element shift line replaced by the hold-safe
    // ot_hdc_delay_hc (same edges; the shift line cost 64,598 CTS hold buffers in this leaf), synthesised flat in this
    // leaf (saves 2 x 1,290 leaf pins)
    reg [1:0] aq_v; reg [2047:0] aq_x; wire [1:0] aq_vo, aq_fault; wire [511:0] aq_q; wire [19:0] aq_e; wire [1023:0] aq_y;
    ot_hgi_coll_aq13 #(.LMUT(MUT == 7)) u_aq0(.clk(clk), .rst_n(rl[4]), .v(aq_v[0]), .fp4(1'b0), .x(aq_x[1023:0]), .vo(aq_vo[0]),
        .q(aq_q[255:0]), .e(aq_e[9:0]), .y(aq_y[511:0]), .fault(aq_fault[0]));
    ot_hgi_coll_aq13 #(.LMUT(MUT == 7)) u_aq1(.clk(clk), .rst_n(rl[5]), .v(aq_v[1]), .fp4(1'b0), .x(aq_x[2047:1024]), .vo(aq_vo[1]),
        .q(aq_q[511:256]), .e(aq_e[19:10]), .y(aq_y[1023:512]), .fault(aq_fault[1]));
    reg [1:0] q_id;
    always @(posedge clk) q_id <= qid;
    function automatic [1:0] nextq(input [1:0] q); case (q) 2'd0: nextq = 2'd1; 2'd1: nextq = 2'd3; 2'd3: nextq = 2'd2; default: nextq = 2'd0; endcase endfunction
    function automatic [1:0] prevq(input [1:0] q); case (q) 2'd0: prevq = 2'd2; 2'd1: prevq = 2'd0; 2'd3: prevq = 2'd1; default: prevq = 2'd3; endcase endfunction
    // arrival source of hop h on direction d at this stop
    function automatic [1:0] srcq(input [1:0] q, input integer d, input integer h);
        reg [1:0] s; s = q;
        for (integer j = 0; j < h; j = j + 1) begin
            if (d == 0 || (MUT == 1 && h == 1)) s = prevq(s); else s = nextq(s);
        end
        srcq = s;
    endfunction
    // ------------------------------------------------------------------ F20 target + descriptor rows
    wire p_we, p_sv; wire [7:0] p_wa, p_sb; wire [255:0] p_wd; wire [8:0] p_sl; wire [15:0] p_lp;
    ot_static_program_target #(.TARGET(8'hff), .PCW(8), .TGT_PIN(1), .CAP_CLK(0)) u_target(
        .clk(clk), .clk_cap(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .program_active(active), .program_cfg_we(p_we), .program_cfg_addr(p_wa),
        .program_cfg_data(p_wd), .program_start_v(p_sv), .program_start_base(p_sb), .program_start_limit(p_sl),
        .program_start_loops(p_lp), .configured(configured), .fault(tgt_fault));
    localparam integer DW = 101;
    reg [DW-1:0] rf [0:15];
    always @(posedge clk) if (p_we && p_wa < 8'd16) rf[p_wa[3:0]] <= p_wd[DW-1:0];
    // ------------------------------------------------------------------ calendar
    reg run; reg [3:0] cur, b0; reg [4:0] lim; reg [15:0] tl, per, lps;
    // GQISSUE2 (r2 route TT -32 cur -> ld_desc, -7 cur -> g_f): the row is read through a ONE-HOT AND-OR on a registered
    // one-hot copy of cur (cur_oh == 1 << cur at every edge; b0_oh likewise), not a 4-bit 16:1 mux whose 4 select bits
    // fan out to 1,616 mux inputs. Same row, same edge.
    reg [15:0] cur_oh, b0_oh;
    // r4: the row AND-OR reads 4 kept copies of cur_oh (each bit drives ~26 of the 101 row bits, was 101)
    (* keep = "true", dont_touch = "true" *) reg [15:0] cur_ohc [0:3];
    reg [DW-1:0] rc_t;
    always @* begin : nb_rc
        rc_t = '0;
        for (integer j = 0; j < 16; j = j + 1)
            for (integer c = 0; c < 4; c = c + 1)
                for (integer x = c * 26; x < (c * 26 + 26 < DW ? c * 26 + 26 : DW); x = x + 1)
                    rc_t[x] = rc_t[x] | (rf[j][x] & cur_ohc[c][j]);
    end
    wire [DW-1:0] rc = rc_t;
    wire fire = run && {1'b0, cur} < lim && tl == rc[18:3];
    // gather state (held while busy)
    reg busy; reg g_qbg, g_r2, g_self; reg [9:0] g_f; reg [7:0] g_bs; reg [15:0] g_src, g_dst, g_str;
    reg [9:0] g_kn;                                   // ring indices K = ceil(F / R)
    reg iss; reg [9:0] ik; reg [1:0] iph; reg [5:0] drain;
    wire [9:0] f_kn = rc[1] ? 10'((rc[28:19] + 10'd1) >> 1) : rc[28:19];
    wire [7:0] f_es = 8'((rc[36:29] + 8'd31) >> 5);
    wire f_bad = rc[28:19] == 10'd0 || |rc[71:69] ||
                 (rc[0] && (rc[36:29] == 8'd0 || rc[36:29] > 8'd64 || {2'b0, rc[28:19]} != {2'b0, rc[36:29]} + {4'b0, f_es}));
    wire ev_in_v = iss && iph != 2'd2;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            run <= 1'b0; busy <= 1'b0; iss <= 1'b0; fault <= 1'b0; active <= 1'b0; done <= 1'b0; drain <= 6'd0;
            cur <= 4'd0; b0 <= 4'd0; cur_oh <= 16'd1; b0_oh <= 16'd1; for (integer c = 0; c < 4; c = c + 1) cur_ohc[c] <= 16'd1; lim <= 5'd0; tl <= 16'd0; per <= 16'd0; lps <= 16'd0; ik <= 10'd0; iph <= 2'd0;
        end else begin
            done <= 1'b0;
            active <= run || busy || p_sv;
            if (active && !(run || busy || p_sv)) done <= 1'b1;
            if (p_sv) begin
                if (run || busy || p_sl > 9'd16 || rf[p_sb[3:0]][100:85] == 16'd0) fault <= 1'b1;
                run <= 1'b1; cur <= p_sb[3:0]; b0 <= p_sb[3:0]; cur_oh <= 16'd1 << p_sb[3:0]; b0_oh <= 16'd1 << p_sb[3:0]; for (integer c = 0; c < 4; c = c + 1) cur_ohc[c] <= 16'd1 << p_sb[3:0]; lim <= p_sl[4:0]; tl <= 16'd0; lps <= p_lp;
                per <= rf[p_sb[3:0]][100:85];
            end else if (run) begin
                if (fire) begin cur <= cur + 4'd1; cur_oh <= {cur_oh[14:0], cur_oh[15]}; for (integer c = 0; c < 4; c = c + 1) cur_ohc[c] <= {cur_ohc[c][14:0], cur_ohc[c][15]}; end
                if (tl == per - 16'd1) begin
                    if (lps <= 16'd1) run <= 1'b0;
                    else begin lps <= lps - 16'd1; tl <= 16'd0; cur <= b0; cur_oh <= b0_oh; for (integer c = 0; c < 4; c = c + 1) cur_ohc[c] <= b0_oh; end
                    if ({1'b0, cur} + (fire ? 5'd1 : 5'd0) != lim) fault <= 1'b1;   // a row never fired this period
                end else tl <= tl + 16'd1;
            end
            if (fire) begin
                if (busy || f_bad) fault <= 1'b1;
                busy <= 1'b1; iss <= 1'b1; ik <= 10'd0; iph <= 2'd0;
            end else if (iss) begin
                if (ev_in_v) begin
                    ik <= ik + 10'd1;
                    if (ik == g_kn - 10'd1) begin iss <= 1'b0; drain <= 6'(ND - 1); end
                end
                iph <= (iph == 2'd2) ? 2'd0 : iph + 2'd1;
            end else if (busy) begin
                if (drain == 6'd0) busy <= 1'b0; else drain <= drain - 6'd1;
            end
            if (|(aq_fault_q & aq_vo_q)) fault <= 1'b1;
            if (flt_n) fault <= 1'b1;
        end
    end
    always @(posedge clk or negedge rn) if (!rn) ld_fire <= 1'b0; else ld_fire <= fire;
    (* keep = "true", dont_touch = "true" *) reg fire_q;   // r4: = ld_fire (own kept copy for the exponent-word clear)
    always @(posedge clk or negedge rn) if (!rn) fire_q <= 1'b0; else fire_q <= fire;
    always @(posedge clk) ld_desc <= {rc[1], rc[2], rc[0], rc[28:19], rc[36:29], rc[68:53], rc[84:69]};
    always @(posedge clk) if (fire) begin
        g_qbg <= rc[0]; g_r2 <= rc[1]; g_self <= rc[2]; g_f <= rc[28:19]; g_bs <= rc[36:29];
        g_src <= rc[52:37]; g_dst <= rc[68:53]; g_str <= rc[84:69]; g_kn <= f_kn;
    end
    // ------------------------------------------------------------------ event pipeline {v, k}
    // GQISSUE2: the flit flags fv / is_code of each ring are decoded ONCE, on the issue edge, from registered shadows of ik
    // (sfv / scd below) and travel with the entry (ev_f / ev_c); no later stage decodes them from g_f / g_bs / g_r2 again
    // (r2 route: g_f -> rb_rx_* -30, g_f -> vm_rq -32, g_f / g_bs -> ld_p_d -50 / -98).
    reg [ND-1:0] ev_v; reg [9:0] ev_k [0:ND-1]; reg [1:0] ev_f [0:ND-1], ev_c [0:ND-1];
    reg [1:0] sfv, scd;                               // = fv(ik, r), is_code(flit_i(ik, r)) at every edge of a gather
    always @(posedge clk or negedge rn1)
        if (!rn1) ev_v <= '0; else ev_v <= {ev_v[ND-2:0], ev_in_v};
    always @(posedge clk) begin
        ev_k[0] <= ik; ev_f[0] <= sfv; ev_c[0] <= scd;
        for (integer s = 1; s < ND; s = s + 1) begin ev_k[s] <= ev_k[s-1]; ev_f[s] <= ev_f[s-1]; ev_c[s] <= ev_c[s-1]; end
    end
    // flit decode of an entry
    function automatic [10:0] flit_i(input [9:0] k, input integer r); flit_i = g_r2 ? {k, 1'(r)} : (r == 0 ? {1'b0, k} : 11'h7ff); endfunction
    function automatic fv(input [9:0] k, input integer r);     // flit (k, r) exists
        reg [10:0] i; i = flit_i(k, r); fv = (r == 0 || g_r2) && i < {1'b0, g_f};
    endfunction
    function automatic is_code(input [10:0] i); is_code = !g_qbg || i < {3'b0, g_bs}; endfunction
    function automatic [15:0] sec_add(input [15:0] s, input [12:0] a); sec_add = {s[15:13], s[12:0] + a}; endfunction
    function automatic [7:0] oh8(input [2:0] b); oh8 = 8'd1 << b; endfunction
    // ------------------------------------------------------------------ issue-edge shadows of ik (GQISSUE2)
    // Updated on the same edges as ik: at fire (ik <= 0) from the fired row rc (the row the gather state g_* loads), on
    // every issue edge (ik <= ik + 1) from the held gather state. qa[4r+w] = low 13 b of
    // sec_add(g_src, {flit_i(ik,r),2'b00} + w) (+4 per index, +8 with two rings; ring 1 of a one-ring gather never issues,
    // sfv[1] = 0). The QBG read request of the issue edge is then a 3-to-8 decode of registered addresses (was
    // g_r2 -> flit mux -> 13-b add -> decode in one edge, r2 route -50).
    reg [12:0] qa [0:7];
    always @(posedge clk or negedge rn)
        if (!rn) begin sfv <= 2'd0; scd <= 2'd0; end
        else if (fire) begin
            for (integer r = 0; r < 2; r = r + 1) begin : nb_s0
                reg [10:0] i0; i0 = rc[1] ? 11'(r) : (r == 0 ? 11'd0 : 11'h7ff);
                sfv[r] <= (r == 0 || rc[1]) && i0 < {1'b0, rc[28:19]};
                scd[r] <= !rc[0] || i0 < {3'b0, rc[36:29]};
            end
        end else if (ev_in_v)
            for (integer r = 0; r < 2; r = r + 1) begin : nb_s1
                reg [9:0] kn; kn = ik + 10'd1;
                sfv[r] <= fv(kn, r); scd[r] <= is_code(flit_i(kn, r));
            end
    always @(posedge clk)
        if (fire) begin
            for (integer r = 0; r < 2; r = r + 1) begin : nb_q0
                reg [10:0] i0; i0 = rc[1] ? 11'(r) : (r == 0 ? 11'd0 : 11'h7ff);
                for (integer w = 0; w < 4; w = w + 1) qa[r*4+w] <= rc[49:37] + 13'({i0, 2'b00} + w);
            end
        end else if (ev_in_v)
            for (integer q = 0; q < 8; q = q + 1) qa[q] <= qa[q] + (g_r2 ? 13'd8 : 13'd4);
    // plain-read pre-stage (@S_PR-2 -> request @S_PR-1) and quantiser-feed pre-stage (@S_QCAP-1 -> x @S_QCAP): address /
    // bank one-hots registered one edge ahead (g_src is held for the whole gather, so the result is the same)
    reg [1:0] pr_v; reg [15:0] pr_s [0:1];
    reg [1:0] qc_v;
    // r4: 8 kept copies (one per 32-b slice of the 256-b word) of every feed / P one-hot: each bit drives 32 AND legs
    // (r3: 256)
    (* keep = "true", dont_touch = "true" *) reg [7:0] qc_ohc [0:63];      // [q*8 + slice]
    always @(posedge clk or negedge rn1)
        if (!rn1) begin pr_v <= 2'd0; qc_v <= 2'd0; end
        else for (integer r = 0; r < 2; r = r + 1) begin
            pr_v[r] <= ev_v[S_PR-2] && ev_f[S_PR-2][r];
            qc_v[r] <= ev_v[S_QCAP-1] && g_qbg && ev_f[S_QCAP-1][r] && ev_c[S_QCAP-1][r];
        end
    always @(posedge clk) for (integer r = 0; r < 2; r = r + 1) begin : nb_pq
        reg [10:0] i; reg [15:0] s;
        pr_s[r] <= sec_add(g_src, 13'(flit_i(ev_k[S_PR-2], r)));
        i = flit_i(ev_k[S_QCAP-1], r);
        for (integer w = 0; w < 4; w = w + 1) begin
            s = sec_add(g_src, 13'({i, 2'b00} + w));
            for (integer c = 0; c < 8; c = c + 1) qc_ohc[(r*4+w)*8 + c] <= oh8(s[2:0]);
        end
    end
    // ------------------------------------------------------------------ VM reads (issue) + response check
    reg [7:0] rd_exp; reg [7:0] rd_exp_q;
    always @(posedge clk or negedge rn2) begin
        if (!rn2) begin vm_rq <= '0; rd_exp <= 8'd0; rd_exp_q <= 8'd0; end
        else begin
            vm_rq <= '0;
            if (g_qbg && ev_in_v) begin
                for (integer r = 0; r < 2; r = r + 1) begin : nb_1
                    reg [15:0] s;
                    if (sfv[r] && scd[r])
                        for (integer w = 0; w < 4; w = w + 1) begin
                            s = {g_src[15:13], qa[r*4+w]};
                            for (integer b = 0; b < 8; b = b + 1) if (s[2:0] == 3'(b)) vm_rq[b*17 +: 17] <= {1'b1, s};
                        end
                end
            end
            if (!g_qbg && ev_v[S_PR-1]) begin
                for (integer r = 0; r < 2; r = r + 1) begin : nb_2
                    if (pr_v[r]) for (integer b = 0; b < 8; b = b + 1) if (pr_s[r][2:0] == 3'(b)) vm_rq[b*17 +: 17] <= {1'b1, pr_s[r]};
                end
            end
            // expected response valids (one edge before the capture register is loaded)
            rd_exp <= 8'd0;
            for (integer b = 0; b < 8; b = b + 1) if (vm_rq[b*17+16]) rd_exp[b] <= 1'b1;
        end
    end
    // read latency: rq register @n -> bank samples n+1 -> registered response n+7 -> pin capture n+8.
    reg [7:0] rdx [0:7];
    always @(posedge clk or negedge rn1)
        if (!rn1) for (integer d = 0; d < 8; d = d + 1) rdx[d] <= 8'd0;
        else begin rdx[0] <= rd_exp; for (integer d = 1; d < 8; d = d + 1) rdx[d] <= rdx[d-1]; end
    reg [2055:0] rr_q; reg [7:0] rrv_q;
    function automatic [255:0] rdw_oh(input [7:0] oh);  // same word through a one-hot AND-OR (registered one-hot select)
        rdw_oh = 256'd0;
        for (integer j = 0; j < 8; j = j + 1) rdw_oh = rdw_oh | (rr_q[j*257 +: 256] & {256{oh[j]}});
    endfunction
    function automatic [31:0] rdw_oh32(input [7:0] oh, input integer c);  // 32-b slice c of rdw_oh (one copy's legs)
        rdw_oh32 = 32'd0;
        for (integer j = 0; j < 8; j = j + 1) rdw_oh32 = rdw_oh32 | (rr_q[j*257 + 32*c +: 32] & {32{oh[j]}});
    endfunction
    always @(posedge clk) rr_q <= vm_rr;
    always @(posedge clk or negedge rn1)
        if (!rn1) rrv_q <= 8'd0; else for (integer b = 0; b < 8; b = b + 1) rrv_q[b] <= vm_rr[b*257+256];
    // rdx[6] holds the expectation of the response captured in rr_q this edge
    wire rd_bad = rrv_q != rdx[6];
    // ------------------------------------------------------------------ quantiser feed (@9) and capture (@23)
    always @(posedge clk or negedge rn1)
        if (!rn1) aq_v <= 2'd0;
        else aq_v <= qc_v;
    always @(posedge clk) for (integer q = 0; q < 8; q = q + 1) for (integer c = 0; c < 8; c = c + 1)
        aq_x[q*256 + 32*c +: 32] <= rdw_oh32(qc_ohc[q*8 + c], c);
    // exponent byte (e + 127) formed at the capture register (was added in front of the 512-b ex forwarding mux)
    reg [511:0] aq_q_q;
    (* keep = "true", dont_touch = "true" *) reg [7:0] aq_ebc [0:3];      // r4: [r*2 + half] (32 byte lanes each, was 64)
    always @(posedge clk or negedge rn1) if (!rn1) begin aq_vo_q <= 2'd0; aq_fault_q <= 2'd0; end else begin aq_vo_q <= aq_vo; aq_fault_q <= aq_fault; end
    always @(posedge clk) begin
        aq_q_q <= aq_q;
        for (integer r = 0; r < 2; r = r + 1) begin
            for (integer c = 0; c < 2; c = c + 1) aq_ebc[r*2 + c] <= 8'(aq_e[r*10 +: 10] + ((MUT == 2) ? 10'sd126 : 10'sd127));
        end
    end
    // ------------------------------------------------------------------ payload P (@24) + exponent words
    reg [511:0] ex;                                    // exponent words 0, 1 (bytes = e + 127)
    reg [511:0] ex_n;                                  // with this edge's blocks merged (forwarding)
    // GQISSUE2: every select of P is decoded one edge ahead from ev[S_P-2] into registered one-hots (pp_*): the 64-byte
    // exponent merge mask, the raw-read bank, and the code / exponent-word-0 / exponent-word-1 kind (was g_bs / g_src /
    // ev_k -> compare / 13-b add -> decode -> 512-b mux in one edge, r2 route -98).
    reg [1:0] pp_v; reg [63:0] pp_em [0:1];
    (* keep = "true", dont_touch = "true" *) reg [7:0] pp_rawc [0:15];     // r4: [r*8 + slice] copies
    (* keep = "true", dont_touch = "true" *) reg [7:0] pp_codec [0:1];   // [r][slice]
    (* keep = "true", dont_touch = "true" *) reg [7:0] pp_loc [0:1];
    (* keep = "true", dont_touch = "true" *) reg [7:0] pp_hic [0:1];
    always @(posedge clk or negedge rn1)
        if (!rn1) pp_v <= 2'd0;
        else for (integer r = 0; r < 2; r = r + 1) pp_v[r] <= ev_v[S_P-2] && ev_f[S_P-2][r];
    always @(posedge clk) for (integer r = 0; r < 2; r = r + 1) begin : nb_pp
        reg [10:0] i; reg [15:0] s; i = flit_i(ev_k[S_P-2], r); s = sec_add(g_src, 13'(i));
        pp_em[r] <= (ev_v[S_P-2] && g_qbg && ev_f[S_P-2][r] && ev_c[S_P-2][r]) ? (64'd1 << i[5:0]) : 64'd0;
        for (integer c = 0; c < 8; c = c + 1) begin
            pp_rawc[r*8 + c] <= g_qbg ? 8'd0 : oh8(s[2:0]);
            pp_codec[r][c] <= g_qbg && ev_c[S_P-2][r];
            pp_loc[r][c] <= g_qbg && !ev_c[S_P-2][r] && i == {3'b0, g_bs};
            pp_hic[r][c] <= g_qbg && !ev_c[S_P-2][r] && i != {3'b0, g_bs};
        end
    end
    always @* begin : nb_5
        ex_n = ex;
        for (integer r = 0; r < 2; r = r + 1)
            for (integer j = 0; j < 64; j = j + 1) if (pp_em[r][j]) ex_n[j*8 +: 8] = aq_ebc[r*2 + j/32];
    end
    reg [1:0] p_v; reg [255:0] p_d [0:1];
    always @(posedge clk or negedge rn1)
        if (!rn1) p_v <= 2'd0;
        else p_v <= pp_v;
    always @(posedge clk) begin
        // r4: the exponent words clear one edge after fire (fire_q; was on fire: 512 loads on the calendar compare). No
        // exponent flit of the new gather merges before S_P >= 24 edges later, and the previous gather has drained.
        if (fire_q) ex <= '0; else ex <= ex_n;
        for (integer r = 0; r < 2; r = r + 1)
            for (integer c = 0; c < 8; c = c + 1)
                p_d[r][32*c +: 32] <= rdw_oh32(pp_rawc[r*8 + c], c) | (aq_q_q[r*256 + 32*c +: 32] & {32{pp_codec[r][c]}}) |
                                      (ex_n[32*c +: 32] & {32{pp_loc[r][c]}}) | (ex_n[256 + 32*c +: 32] & {32{pp_hic[r][c]}});
    end
    // ------------------------------------------------------------------ ring B commands (lp @24, read @25, inject @27, rx @27+2h)
    // and ring-A gather commands (same edges into A1, merge register one edge later)
    reg [290:0] cb [0:1];      // per ring: {lp_we, lp_tag, lp_data, rd, rd_tag, inj2, fwd2, tag3, ttl4, rx2, kind4, src4, rtag6}
    always @* begin : nb_8
        for (integer r = 0; r < 2; r = r + 1) begin : nb_9
            reg lpw; reg [2:0] lpt; reg [255:0] lpd; reg rd; reg [2:0] rdt; reg [1:0] inj, fwd, rx; reg [2:0] ttg;
            reg [3:0] ttl, kind, src; reg [5:0] rtag; reg [9:0] k;
            lpw = 0; lpt = 0; lpd = 0; rd = 0; rdt = 0; inj = 0; fwd = 0; rx = 0; ttg = 0; ttl = 0; kind = 0; src = 0; rtag = 0;
            // lp write of the payload: computed with P (ev[23]); P itself is the data
            k = ev_k[S_BLP-1];
            if (ev_v[S_BLP-1] && ev_f[S_BLP-1][r]) begin lpw = 1; lpt = k[2:0]; end
            k = ev_k[S_BRD-1];
            if (ev_v[S_BRD-1] && ev_f[S_BRD-1][r]) begin rd = 1; rdt = k[2:0]; end
            k = ev_k[S_BINJ-1];
            if (ev_v[S_BINJ-1] && ev_f[S_BINJ-1][r]) begin inj[k[0]] = 1; ttg = k[2:0]; ttl[k[0]*2 +: 2] = 2'd3; end
            for (integer h = 1; h <= 3; h = h + 1) begin
                k = ev_k[S_BRX + 2*h - 1];
                if (ev_v[S_BRX + 2*h - 1] && ev_f[S_BRX + 2*h - 1][r]) begin
                    rx[k[0]] = 1; kind[k[0]*2 +: 2] = 2'd3; src[k[0]*2 +: 2] = srcq(q_id, k[0], h); rtag[k[0]*3 +: 3] = k[2:0];
                    if (h < 3) fwd[k[0]] = 1;
                end
            end
            cb[r] = {lpw, lpt, 256'd0, rd, rdt, inj, fwd, ttg, ttl, rx, kind, src, rtag};
        end
    end
    // P is loaded on the lp edge, so the lp data of the registered command word is P (r).
    reg [290:0] a1;             // ring-A gather command (ring B timing)
    reg [290:0] b1;             // ring B command register (MUT 5: one more edge)
    always @(posedge clk or negedge rn3)
        if (!rn3) begin a1 <= '0; b1 <= '0; end
        else begin a1 <= cb[0]; b1 <= cb[1]; end
    wire [255:0] a1_d = p_d[0], b1_d = p_d[1];
    assign ld_ev_v = ev_v[0]; assign ld_ev_k = ev_k[0]; assign ld_p_v = p_v; assign ld_p_d = {p_d[1], p_d[0]};
    reg [290:0] b2; reg [255:0] b2_d;
    always @(posedge clk or negedge rn3) if (!rn3) b2 <= '0; else b2 <= b1;
    always @(posedge clk) b2_d <= b1_d;
    wire [290:0] bo = (MUT == 5) ? b2 : b1;
    wire [255:0] bo_d = (MUT == 5) ? b2_d : b1_d;
    always @* begin : nb_10
        {rb_lp_we, rb_lp_tag} = bo[290:287]; rb_lp_data = bo_d;
        {rb_state_read_tx, rb_state_tx_tag, rb_tx_inject, rb_tx_forward, rb_tx_tag, rb_tx_ttl, rb_rx_slot, rb_rx_kind,
         rb_rx_src, rb_rx_tag} = bo[30:0];
    end
    // ------------------------------------------------------------------ ring-A merge register (ISA +2 edges)
    reg [57:0] isa_q; reg [255:0] isa_d_q;
    always @(posedge clk or negedge rn3) if (!rn3) isa_q <= '0; else isa_q <= isa_ring;
    always @(posedge clk) isa_d_q <= isa_lp_data;
    reg merge_bad;
    always @(posedge clk or negedge rn3) begin
        if (!rn3) begin
            {ra_lp_we, ra_state_read_add, ra_state_read_tx, ra_state_read_rr, ra_add_v, ra_tx_inject, ra_tx_forward,
             ra_tx_gather, ra_rx_slot, ra_rr_local} <= '0;
            merge_bad <= 1'b0;
        end else begin
            ra_lp_we <= isa_q[0] | a1[290];
            ra_state_read_add <= isa_q[4];
            ra_state_read_tx <= isa_q[11] | a1[30];
            ra_state_read_rr <= isa_q[16];
            ra_add_v <= isa_q[20];
            ra_tx_inject <= isa_q[28:27] | a1[26:25];
            ra_tx_forward <= isa_q[30:29] | a1[24:23];
            ra_tx_gather <= |a1[26:25];
            ra_rx_slot <= isa_q[39:38] | a1[15:14];
            ra_rr_local <= isa_q[54];
            merge_bad <= (isa_q[0] && a1[290]) || (isa_q[11] && a1[30]) || |(isa_q[28:27] & a1[26:25]) ||
                         |(isa_q[30:29] & a1[24:23]) || |(isa_q[39:38] & a1[15:14]) ||
                         (|a1[26:25] && |isa_q[28:27]);
        end
    end
    always @(posedge clk) begin
        ra_lp_tag <= isa_q[3:1] | a1[289:287];
        ra_lp_data <= a1[290] ? a1_d : isa_d_q;
        ra_state_add_tag <= isa_q[7:5]; ra_state_add_src <= isa_q[9:8]; ra_state_add_rhs_acc <= isa_q[10];
        ra_state_tx_tag <= isa_q[14:12] | a1[29:27]; ra_state_tx_acc <= isa_q[15];
        ra_state_rr_tag <= isa_q[19:17];
        ra_add_tag <= isa_q[23:21]; ra_add_src <= isa_q[25:24]; ra_add_rhs_acc <= isa_q[26];
        ra_tx_tag <= isa_q[33:31] | a1[22:20]; ra_tx_dst <= isa_q[35:34]; ra_tx_result <= isa_q[36]; ra_tx_acc <= isa_q[37];
        ra_tx_ttl <= a1[19:16];
        ra_rx_kind <= isa_q[43:40] | a1[13:10]; ra_rx_src <= isa_q[47:44] | a1[9:6]; ra_rx_tag <= isa_q[53:48] | a1[5:0];
        ra_rr_local_tag <= isa_q[57:55];
    end
    always @(posedge clk or negedge rn1)
        if (!rn1) flt_q <= 1'b0; else flt_q <= rd_bad || merge_bad;
endmodule

// Landing leaf: captures both rings' publishes and the local payload P, and writes the quadrant VM through the COLL
// kq port (via the kq share). Every input pin-registered, every output a register. Stages as the issue leaf's.
module ot_hgi_coll_gq_land #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire          ld_fire,
    input  wire [52:0]   ld_desc,
    input  wire          ld_ev_v,
    input  wire [9:0]    ld_ev_k,
    input  wire [1:0]    ld_p_v,
    input  wire [511:0]  ld_p_d,
    input  wire [1:0]    pa_v, pb_v,
    input  wire [3:0]    pa_src, pb_src,
    input  wire [5:0]    pa_tag, pb_tag,
    input  wire [511:0]  pa_d, pb_d,
    output wire [1123:0] vm_kq_lo, vm_kq_hi,      // banks 0-3 / 4-7 on separate faces
    output reg           fault
);
    reg [2247:0] vm_kq; assign vm_kq_lo = vm_kq[1123:0]; assign vm_kq_hi = vm_kq[2247:1124];
    localparam integer NL = 36;      // le[j] = the entry of issue stage j + 1
    localparam integer S_KQ = 31;    // publish kq register @31+2h (entry at stage 30+2h = le[29+2h]); self-land kq @26
    wire [0:0] rl;
    ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rn = rl[0];
    reg [1:0] q_id; always @(posedge clk) q_id <= qid;
    function automatic [1:0] nextq(input [1:0] q); case (q) 2'd0: nextq = 2'd1; 2'd1: nextq = 2'd3; 2'd3: nextq = 2'd2; default: nextq = 2'd0; endcase endfunction
    function automatic [1:0] prevq(input [1:0] q); case (q) 2'd0: prevq = 2'd2; 2'd1: prevq = 2'd0; 2'd3: prevq = 2'd1; default: prevq = 2'd3; endcase endfunction
    function automatic [1:0] srcq(input [1:0] q, input integer d, input integer h);
        reg [1:0] s; s = q;
        for (integer j = 0; j < h; j = j + 1) begin
            if (d == 0 || (MUT == 1 && h == 1)) s = prevq(s); else s = nextq(s);
        end
        srcq = s;
    endfunction
    // pin registers
    reg f_q; reg [52:0] d_q; reg [1:0] pl_v; reg [511:0] pl_d;
    reg [NL-1:0] le_v; reg [9:0] le_k [0:NL-1];
    always @(posedge clk or negedge rn)
        if (!rn) begin f_q <= 1'b0; pl_v <= 2'd0; le_v <= '0; end
        else begin f_q <= ld_fire; pl_v <= ld_p_v; le_v <= {le_v[NL-2:0], ld_ev_v}; end
    always @(posedge clk) begin
        d_q <= ld_desc; pl_d <= ld_p_d; le_k[0] <= ld_ev_k;
        for (integer j = 1; j < NL; j = j + 1) le_k[j] <= le_k[j-1];
    end
    // descriptor (held for the gather; gathers never overlap: the issue leaf faults a fire while busy)
    reg g_r2, g_self, g_qbg; reg [9:0] g_f; reg [7:0] g_bs; reg [15:0] g_dst, g_str;
    always @(posedge clk) if (f_q) {g_r2, g_self, g_qbg, g_f, g_bs, g_dst, g_str} <= d_q;
    function automatic [10:0] flit_i(input [9:0] k, input integer r); flit_i = g_r2 ? {k, 1'(r)} : (r == 0 ? {1'b0, k} : 11'h7ff); endfunction
    function automatic fv(input [9:0] k, input integer r);
        reg [10:0] i; i = flit_i(k, r); fv = (r == 0 || g_r2) && i < {1'b0, g_f};
    endfunction
    function automatic [15:0] sec_add(input [15:0] s, input [12:0] a); sec_add = {s[15:13], s[12:0] + a}; endfunction
    // ------------------------------------------------------------------ publish capture (@30+2h) and VM landing (@31+2h)
    reg [1:0] pav_q, pbv_q; reg [3:0] pas_q, pbs_q; reg [5:0] pat_q, pbt_q; reg [511:0] pad_q, pbd_q;
    always @(posedge clk or negedge rn) if (!rn) begin pav_q <= 2'd0; pbv_q <= 2'd0; end else begin pav_q <= pa_v; pbv_q <= pb_v; end
    always @(posedge clk) begin pas_q <= pa_src; pbs_q <= pb_src; pat_q <= pa_tag; pbt_q <= pb_tag; pad_q <= pa_d; pbd_q <= pb_d; end
    // Landing address pre-stage (HBM-COLLQ3 10-18: the CTS gate measured -323.9 ps on q_id -> sector add -> bank
    // decode -> 8-way bank mux -> vm_kq; 17 levels). Everything that is a function of the descriptor, q_id and the
    // entry's k is computed one edge EARLY from le[j-1] (the shift register holds the same entry there one edge before)
    // and registered per lane: enable, bank one-hot, sector, source quadrant, d. The landing edge keeps only the
    // capture compare, the bank-collision OR and an AND-OR bank select. vm_kq timing is unchanged (same edge).
    // Sector bases g_dst + g_str * q are registered from the held descriptor (gathers never overlap; the first use is
    // >= 23 edges after the descriptor fires).
    reg [15:0] base_q [0:3];
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) base_q[q] <= sec_add(g_dst, 13'(g_str * q));
    // lanes 0..5 = publish (h - 1) * 2 + r, lanes 6..7 = self-land r
    reg [7:0] ln_en; reg [7:0] ln_bk [0:7]; reg [15:0] ln_s [0:7]; reg [1:0] ln_sq [0:5]; reg [5:0] ln_d;
    always @(posedge clk or negedge rn)
        if (!rn) ln_en <= 8'd0;
        else begin : nb_pre
            reg [9:0] k; reg [10:0] i; reg [1:0] sq; reg [15:0] s;
            for (integer h = 1; h <= 3; h = h + 1)
                for (integer r = 0; r < 2; r = r + 1) begin
                    k = le_k[S_KQ + 2*h - 3]; i = flit_i(k, r); sq = srcq(q_id, k[0], h);
                    s = {base_q[sq][15:13], base_q[sq][12:0] + 13'(i) + ((MUT == 3) ? 13'd1 : 13'd0)};
                    ln_en[(h-1)*2 + r] <= le_v[S_KQ + 2*h - 3] && fv(k, r);
                    ln_bk[(h-1)*2 + r] <= 8'd1 << s[2:0]; ln_s[(h-1)*2 + r] <= s;
                    ln_sq[(h-1)*2 + r] <= sq; ln_d[(h-1)*2 + r] <= k[0];
                end
            for (integer r = 0; r < 2; r = r + 1) begin
                k = le_k[23]; i = flit_i(k, r);
                s = {base_q[q_id][15:13], base_q[q_id][12:0] + 13'(i)};
                ln_en[6 + r] <= g_self && MUT != 4 && le_v[23] && fv(k, r);
                ln_bk[6 + r] <= 8'd1 << s[2:0]; ln_s[6 + r] <= s;
            end
        end
    reg [2247:0] kq_n; reg kq_bad, pub_bad;
    always @* begin : nb_11
        reg [3:0] lane_exp; reg [7:0] act; reg [7:0] seen; reg [255:0] gd [0:7];
        reg v; reg [1:0] gs; reg [2:0] gt; reg [9:0] kk; integer l;
        kq_n = '0; kq_bad = 1'b0; pub_bad = 1'b0; lane_exp = 4'd0; seen = 8'd0; act = 8'd0; v = 1'b0; gs = 2'd0; gt = 3'd0;
        for (integer m = 0; m < 8; m = m + 1) gd[m] = '0;
        for (integer h = 1; h <= 3; h = h + 1)
            for (integer r = 0; r < 2; r = r + 1) begin
                l = (h-1)*2 + r;
                kk = le_k[S_KQ + 2*h - 2];
                act[l] = ln_en[l];
                if (ln_en[l]) begin
                    lane_exp[r*2 + ln_d[l]] = 1'b1;
                    v = r ? pbv_q[ln_d[l]] : pav_q[ln_d[l]];
                    gs = r ? (ln_d[l] ? pbs_q[3:2] : pbs_q[1:0]) : (ln_d[l] ? pas_q[3:2] : pas_q[1:0]);
                    gt = r ? (ln_d[l] ? pbt_q[5:3] : pbt_q[2:0]) : (ln_d[l] ? pat_q[5:3] : pat_q[2:0]);
                    if (!v || gs != ln_sq[l] || gt != kk[2:0]) pub_bad = 1'b1;
                end
                gd[l] = r ? (ln_d[l] ? pbd_q[511:256] : pbd_q[255:0]) : (ln_d[l] ? pad_q[511:256] : pad_q[255:0]);
            end
        if ({pbv_q, pav_q} & ~lane_exp) pub_bad = 1'b1;        // unexpected publish
        for (integer r = 0; r < 2; r = r + 1) begin act[6 + r] = ln_en[6 + r] && pl_v[r]; gd[6 + r] = pl_d[r*256 +: 256]; end
        // two writes to one bank in one edge: fault; the last lane (original order) wins the bank
        for (integer m = 0; m < 8; m = m + 1) if (act[m]) begin
            if (seen & ln_bk[m]) kq_bad = 1'b1;
            seen = seen | ln_bk[m];
        end
        for (integer b = 0; b < 8; b = b + 1)
            for (integer m = 0; m < 8; m = m + 1)
                if (act[m] && ln_bk[m][b]) kq_n[b*281 +: 281] = {1'b1, ln_s[m], gd[m], 8'hff};
    end
    // the publish lanes are evaluated with the entry one stage past the capture (le[S_KQ+2h-2] = issue stage 30+2h, the
    // entry whose publish was captured on the previous edge); both register into kq.
    // sticky fault flop beside the landing logic, then a FACE register at the E fault pin (NATIVE-SWEEP 10-18: the
    // routed view hcoll_gq_land_1018-r1-b7918441e launched fault at O-R 228.0 > 220 ps from the interior flop). +1 edge
    // on the fault report only (sticky, off the token path; no data / VM edge moves). MUT 6 (bench): the face register
    // never forwards.
    reg flt_r;
    always @(posedge clk or negedge rn)
        if (!rn) begin vm_kq <= '0; flt_r <= 1'b0; fault <= 1'b0; end
        else begin vm_kq <= kq_n; if (kq_bad || pub_bad) flt_r <= 1'b1; fault <= flt_r && MUT != 6; end
endmodule
// The gather master as placed per quadrant: issue leaf (F20 target, calendar, VM reads, quantisers, payload, ring-A merge
// register, ring-B commands) + landing leaf (publish capture, VM writes). Wires only.
module ot_hgi_coll_gq #(parameter integer MUT = 0)(
    input  wire clk_issue, clk_land, rst_n,
    input  wire [1:0] qid, input wire [7:0] tgt,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire configured, tgt_fault, active, done, fault, land_fault,
    input  wire [57:0] isa_ring, input wire [255:0] isa_lp_data,
    output wire ra_lp_we, output wire [2:0] ra_lp_tag, output wire [255:0] ra_lp_data,
    output wire ra_state_read_add, ra_state_read_tx, ra_state_read_rr,
    output wire [2:0] ra_state_add_tag, ra_state_tx_tag, ra_state_rr_tag, output wire [1:0] ra_state_add_src,
    output wire ra_state_add_rhs_acc, ra_state_tx_acc, ra_add_v, output wire [2:0] ra_add_tag, output wire [1:0] ra_add_src,
    output wire ra_add_rhs_acc, output wire [1:0] ra_tx_inject, ra_tx_forward, output wire [2:0] ra_tx_tag,
    output wire [1:0] ra_tx_dst, output wire ra_tx_result, ra_tx_acc, ra_tx_gather, output wire [3:0] ra_tx_ttl,
    output wire [1:0] ra_rx_slot, output wire [3:0] ra_rx_kind, ra_rx_src, output wire [5:0] ra_rx_tag,
    output wire ra_rr_local, output wire [2:0] ra_rr_local_tag,
    output wire rb_lp_we, output wire [2:0] rb_lp_tag, output wire [255:0] rb_lp_data, output wire rb_state_read_tx,
    output wire [2:0] rb_state_tx_tag, output wire [1:0] rb_tx_inject, rb_tx_forward, output wire [2:0] rb_tx_tag,
    output wire [3:0] rb_tx_ttl, output wire [1:0] rb_rx_slot, output wire [3:0] rb_rx_kind, rb_rx_src, output wire [5:0] rb_rx_tag,
    input  wire [1:0] pa_v, pb_v, input wire [3:0] pa_src, pb_src, input wire [5:0] pa_tag, pb_tag, input wire [511:0] pa_d, pb_d,
    output wire [135:0] vm_rq, input wire [2055:0] vm_rr, output wire [2247:0] vm_kq
);
    wire ld_fire, ld_ev_v; wire [52:0] ld_desc; wire [9:0] ld_ev_k; wire [1:0] ld_p_v; wire [511:0] ld_p_d;
    ot_hgi_coll_gq_issue #(.MUT(MUT)) u_issue(.clk(clk_issue), .rst_n(rst_n), .qid(qid), .tgt(tgt), .cfg_v(cfg_v),
        .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured), .tgt_fault(tgt_fault),
        .active(active), .done(done), .fault(fault), .isa_ring(isa_ring), .isa_lp_data(isa_lp_data),
        .ra_lp_we(ra_lp_we), .ra_lp_tag(ra_lp_tag), .ra_lp_data(ra_lp_data), .ra_state_read_add(ra_state_read_add),
        .ra_state_read_tx(ra_state_read_tx), .ra_state_read_rr(ra_state_read_rr), .ra_state_add_tag(ra_state_add_tag),
        .ra_state_tx_tag(ra_state_tx_tag), .ra_state_rr_tag(ra_state_rr_tag), .ra_state_add_src(ra_state_add_src),
        .ra_state_add_rhs_acc(ra_state_add_rhs_acc), .ra_state_tx_acc(ra_state_tx_acc), .ra_add_v(ra_add_v),
        .ra_add_tag(ra_add_tag), .ra_add_src(ra_add_src), .ra_add_rhs_acc(ra_add_rhs_acc), .ra_tx_inject(ra_tx_inject),
        .ra_tx_forward(ra_tx_forward), .ra_tx_tag(ra_tx_tag), .ra_tx_dst(ra_tx_dst), .ra_tx_result(ra_tx_result),
        .ra_tx_acc(ra_tx_acc), .ra_tx_gather(ra_tx_gather), .ra_tx_ttl(ra_tx_ttl), .ra_rx_slot(ra_rx_slot),
        .ra_rx_kind(ra_rx_kind), .ra_rx_src(ra_rx_src), .ra_rx_tag(ra_rx_tag), .ra_rr_local(ra_rr_local),
        .ra_rr_local_tag(ra_rr_local_tag), .rb_lp_we(rb_lp_we), .rb_lp_tag(rb_lp_tag), .rb_lp_data(rb_lp_data),
        .rb_state_read_tx(rb_state_read_tx), .rb_state_tx_tag(rb_state_tx_tag), .rb_tx_inject(rb_tx_inject),
        .rb_tx_forward(rb_tx_forward), .rb_tx_tag(rb_tx_tag), .rb_tx_ttl(rb_tx_ttl), .rb_rx_slot(rb_rx_slot),
        .rb_rx_kind(rb_rx_kind), .rb_rx_src(rb_rx_src), .rb_rx_tag(rb_rx_tag), .vm_rq_lo(vm_rq[67:0]), .vm_rq_hi(vm_rq[135:68]),
        .vm_rr_lo(vm_rr[1027:0]), .vm_rr_hi(vm_rr[2055:1028]),
        .ld_fire(ld_fire), .ld_desc(ld_desc), .ld_ev_v(ld_ev_v), .ld_ev_k(ld_ev_k), .ld_p_v(ld_p_v), .ld_p_d(ld_p_d));
    ot_hgi_coll_gq_land #(.MUT(MUT)) u_land(.clk(clk_land), .rst_n(rst_n), .qid(qid), .ld_fire(ld_fire), .ld_desc(ld_desc),
        .ld_ev_v(ld_ev_v), .ld_ev_k(ld_ev_k), .ld_p_v(ld_p_v), .ld_p_d(ld_p_d), .pa_v(pa_v), .pb_v(pb_v), .pa_src(pa_src),
        .pb_src(pb_src), .pa_tag(pa_tag), .pb_tag(pb_tag), .pa_d(pa_d), .pb_d(pb_d), .vm_kq_lo(vm_kq[1123:0]),
        .vm_kq_hi(vm_kq[2247:1124]), .fault(land_fault));
endmodule

// COLL write-port static owner split (kq of one bank pair): A = the COLL v6 writer, B = the gather master. Same idea
// as ot_hbm_idx_vm_share2_static on the read side: the compiler books each bank/edge for at most one writer; a double
// booking faults and writes neither. No arbitration, ready or credit: the select is the valid bit of the one booked word.
// HBM-NSFIX/KQS 10-18: REGISTERED FACES (was a combinational port-to-port feed-through, which cannot close as a hardened
// tile -- cf. hidx_rootctl_am r2 EARLY_FAIL_SETUP from comb share faces). Both writer faces land in pin flops, the
// owner select is an AND-OR of those registers, the vm_kq face leaves output flops:
//   KQ_SHARE_EDGES = 2: a word the writer presents at edge C (formerly sampled by the bank kq pin flop at C) now
//   leaves vm_kq after edge C+1 and is sampled by the bank at C+2. Same +2 for writer A and writer B, so the relative
//   booking (and the static conflict proof) is unchanged; every COLL kq calendar reservation moves 2 words later.
//   fault (sticky, diagnostic only) is evaluated from the pin flops: rises after edge C+1 (was C) for a double
//   booking presented at C.
// RESET: rst_n drives only ot_rst_relay; only the 4 valid flops (+2 out) and fault are reset (data flops are gated by
// the valid flops, so an unreset data word never reaches vm_kq as valid).
// Bench mutants (tb_hgi_coll_kq_share2): 1 no collision check (a double booking passes A, no fault); 2 latency 3
// (extra output stage); 3 latency 1 (no output flop); 4 owner swap (A-booked edge writes B's word and vice versa);
// 5 double booking writes neither but never faults.
module ot_hgi_coll_kq_share2_leaf #(parameter integer MUT = 0)(
    input  wire clk, rst_n,
    input  wire [561:0] a_kq, b_kq,
    output wire [561:0] vm_kq,
    output reg  fault
);
    wire rst_c;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rst_c));
    wire [1:0] dbl;
    for (genvar k = 0; k < 2; k = k + 1) begin : g_b
        reg [279:0] a_d, b_d; reg a_v, b_v;                       // writer pin flops
        always @(posedge clk) begin a_d <= a_kq[281*k +: 280]; b_d <= b_kq[281*k +: 280]; end
        always @(posedge clk or negedge rst_c)
            if (!rst_c) begin a_v <= 1'b0; b_v <= 1'b0; end
            else begin a_v <= a_kq[281*k+280]; b_v <= b_kq[281*k+280]; end
        wire pa = (a_v & ~b_v) | (MUT == 1 && a_v);
        wire pb = b_v & ~a_v & !(MUT == 1 && a_v);
        wire [279:0] s_d = ({280{pa}} & (MUT == 4 ? b_d : a_d)) | ({280{pb}} & (MUT == 4 ? a_d : b_d));
        wire s_v = pa | pb;
        assign dbl[k] = a_v & b_v;
        reg [279:0] o_d; reg o_v;                                 // vm_kq output flops
        if (MUT == 3) begin : g_l1
            always @* begin o_d = s_d; o_v = s_v; end
        end else if (MUT == 2) begin : g_l3
            reg [279:0] x_d; reg x_v;
            always @(posedge clk) begin x_d <= s_d; o_d <= x_d; end
            always @(posedge clk or negedge rst_c) if (!rst_c) begin x_v <= 1'b0; o_v <= 1'b0; end else begin x_v <= s_v; o_v <= x_v; end
        end else begin : g_l2
            always @(posedge clk) o_d <= s_d;
            always @(posedge clk or negedge rst_c) if (!rst_c) o_v <= 1'b0; else o_v <= s_v;
        end
        assign vm_kq[281*k +: 281] = {o_v, o_d};
    end
    always @(posedge clk or negedge rst_c)
        if (!rst_c) fault <= 1'b0;
        else if (|dbl && MUT != 1 && MUT != 5) fault <= 1'b1;
endmodule

// Soft parent: one leaf per bank pair (pair p = banks 2p, 2p+1 = vm_kq[562p +: 562]), each on its own clk_pair[p].
module ot_hgi_coll_kq_share2 #(parameter integer MUT = 0)(
    input  wire [3:0] clk_pair, input wire rst_n,
    input  wire [2247:0] a_kq, b_kq,
    output wire [2247:0] vm_kq,
    output wire fault
);
    wire [3:0] f;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        ot_hgi_coll_kq_share2_leaf #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n), .a_kq(a_kq[562*p +: 562]),
            .b_kq(b_kq[562*p +: 562]), .vm_kq(vm_kq[562*p +: 562]), .fault(f[p]));
    end
    assign fault = |f;
endmodule
`default_nettype wire
