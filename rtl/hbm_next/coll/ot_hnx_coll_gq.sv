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
//   HNX-GQ s3: quantiser = ot_hnx_coll_aq14 (S0 @10, output registers @23 = the old pin-capture edge, no separate
//   capture register) | payload P @24 unchanged. Descriptor fire = launch sample + 4 + loop * period + t_start (was + 3).
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
//
// HBM-NEXT-UNITS-COLL (10-19, next-release HBM die at P = 4, HGI-1R ROWX, CMTP isa_rows.md R1/R4): FORK of
// rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv (ot_hgi_coll_* -> ot_hnx_coll_*) with the N-ROW MESSAGE TRAIN.
// A descriptor row now carries N = nm1 + 1 rows (1..16) and two signed per-row strides (VM words, sector-local 13-b add):
//   [104:101] nm1   [120:105] rs_A (source row stride)   [136:121] rs_O (destination row stride)
// R1: the train equals the N single-row gathers (row r: src + r rs_A, dst + r rs_O, same F/Bs/stride/ring split) bit for
// bit, in row order. R4: they share ONE fire, one issue stream and one drain: the train's ring indices are
// t = r K + k (K = ceil(F / R) a row, k the row-local ring index), and the slot / direction / tag / inject / arrival
// schedule above is a function of t exactly as it is of k for one gather of N K ring indices (so the link proof holds),
// while the addresses use (r, k): flit i = flit_i(k, ring) of row r. Each further row costs 3 K / 2 issue edges
// (the 3-edge {even, odd, idle} pattern), not a new fire + 40-edge drain. Bank-conflict freedom of the landing writes
// needs rs_O = R K (mod 8) when N > 1 (then bank(dst + r rs_O + R k + ring) = bank(dst + R t + ring), the single
// gather's banks); the descriptor check faults otherwise. N = 1 (nm1 = 0, strides ignored) is the d4g gather bit for bit.
// Event entry {r[3:0], k[9:0], t[2:0]} (17 b) replaces k (10 b) in the issue pipeline and on ld_ev_k; ld_desc carries rs_O.
// QBG exponent words need no per-row reset: every row has the same Bs, so its Bs exponent bytes are all rewritten by
// its own code flits before its first exponent flit leaves (bytes >= Bs stay 0 from the fire).
module ot_hnx_coll_gq_issue #(
    parameter integer MUT = 0       // bench mutants: 1 rx src of h=1 uses the CW table on CCW, 2 exponent bias 126,
                                    // 3 publish lands at i+1, 4 self-land skipped, 5 ring-B command one edge late,
                                    // HNX: 6 source ignores the row stride, 7 landing ignores the row stride,
                                    // 8 the row counter never advances (row-local k runs on as t: one flat gather),
                                    // HNX-GQ: 9 quantiser element line one slot short (s3: SRAM ring read 6 behind)
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
    output reg  [68:0]   ld_desc,      // {r2, self, qbg, F[9:0], Bs[7:0], dst[15:0], stride[15:0], rs_O[15:0]}
    output wire          ld_ev_v,
    output wire [16:0]   ld_ev_k,      // HNX event entry {row[3:0], k[9:0], t[2:0]}
    output wire [1:0]    ld_p_v,
    output wire [511:0]  ld_p_d
);
    localparam integer ND = 40;                      // event pipeline depth (last use: ev[36])
    localparam integer S_QR = 0, S_PR = 15, S_QCAP = 8, S_PCAP = 23, S_P = 24;
    localparam integer S_BLP = 24, S_BRD = 25, S_BINJ = 27, S_BRX = 27;   // + 2h
    // ------------------------------------------------------------------ reset relay (3 edges) + straps
    // HNX-GQ s3 (SAFE-DESIGN items 1/3): the port lands in 2 registered face stages (kit reset_landing), then this relay
    // gives one KEPT copy per region, each loading <= ~37 async clears (n2: one relay flop drove every reset flop):
    //  0 calendar valids | 1 calendar indices | 2 tl/per | 3 lps + ld_fire/flt | 4,5 event valids | 6 small valid pipes |
    //  7-10 VM read request (2 banks each) | 11 read expectations | 12,13 read expectation line | 14 ring-A cmd |
    //  15 ring-B cmd | 16 ring-B late cmd | 17 ring-A merge outputs | 18,19 ISA capture | 20,21 quantisers 0/1.
    // Index / one-hot copies, row registers and data registers carry no reset (loaded before use: launch / fire).
    wire [23:0] rl;
    ot_rst_relay #(.REGIONS(24)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rn = rl[0];
    reg flt_q; wire flt_n = flt_q;
    reg [135:0] vm_rq; wire [2055:0] vm_rr = {vm_rr_hi, vm_rr_lo};
    assign vm_rq_lo = vm_rq[67:0]; assign vm_rq_hi = vm_rq[135:68];
    // quantisers: HNX-GQ s3 (L2H-P3/GQ 10-19): two ot_hnx_coll_aq14 (rtl/hbm_next/coll/ot_hnx_coll_aq14.sv) = the
    // ot_hdc_actquant numerics with S9 split (signed exponent | dd / clamp / shift count; per-element kept exponent
    // copies), LATENCY 14, the 1,024 x 9 element line on a 4-macro SRAM ring, and the biased exponent byte e + 127
    // formed in its output registers (EBC = 4 kept copies). n2 had a zero-logic 512 + 16-b capture register (aq_q_q /
    // aq_eb_q) behind ot_hgi_coll_aq13's own output registers (FF -12.95 hold, u_aq1.q -> aq_q_q): that copy is removed
    // and the code assembly (P, below) reads the quantiser's output registers through its registered one-hot AND-OR,
    // so the +1 quantiser edge is absorbed: x @9, quantiser S0 @10, output @23, P @24 exactly as n2 (0 calendar edges).
    reg [1:0] aq_v; reg [2047:0] aq_x; wire [1:0] aq_vo, aq_fault; wire [511:0] aq_q; wire [19:0] aq_e; wire [1023:0] aq_y;
    wire [31:0] aq_eb [0:1];
    ot_hnx_coll_aq14 #(.LMUT(MUT == 9), .EBIAS((MUT == 2) ? 126 : 127), .EBC(4)) u_aq0(.clk(clk), .rst_n(rl[20]), .v(aq_v[0]),
        .fp4(1'b0), .x(aq_x[1023:0]), .vo(aq_vo[0]), .q(aq_q[255:0]), .e(aq_e[9:0]), .y(aq_y[511:0]), .eb(aq_eb[0]),
        .fault(aq_fault[0]));
    ot_hnx_coll_aq14 #(.LMUT(MUT == 9), .EBIAS((MUT == 2) ? 126 : 127), .EBC(4)) u_aq1(.clk(clk), .rst_n(rl[21]), .v(aq_v[1]),
        .fp4(1'b0), .x(aq_x[2047:1024]), .vo(aq_vo[1]), .q(aq_q[511:256]), .e(aq_e[19:10]), .y(aq_y[1023:512]), .eb(aq_eb[1]),
        .fault(aq_fault[1]));
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
    localparam integer DW = 137;   // HNX: + nm1 [104:101], rs_A [120:105], rs_O [136:121]
    reg [DW-1:0] rf [0:15];
    always @(posedge clk) if (p_we && p_wa < 8'd16) rf[p_wa[3:0]] <= p_wd[DW-1:0];
    // ------------------------------------------------------------------ calendar
    // HNX-GQ s3 (SAFE-DESIGN item 5, registered single read): the 16 x 137 b row file (2,192 b, written only by the F20
    // target) has ONE read port, a one-hot AND-OR on NRC = 5 kept copies of the row one-hot (each copy bit loads <= 28 row
    // bits), and no combinational consumer: every reader uses the registered current row R (loaded from the read port
    // every edge, from B at a period wrap) or the registered base row B (= row b0, loaded one edge after the launch, kept
    // current by a write to row b0). The launch read (n2: per <= rf[p_sb], a second runtime-indexed read) is gone: the
    // launch lands one edge (lq) and the calendar starts from the read port. +1 EDGE: fire edge = launch sample + 4 +
    // loop * period + t_start (was + 3; tools/hbm_next/hnx_coll_gq_train.py FIRE_FROM_LAUNCH, the tb's FFL).
    // Compiler rule (new, recorded for HNEXT.CMTP): a descriptor row must not be rewritten in the edge just before its
    // fire edge (R is the row one edge old); two fires of one master are always >= 2 edges apart (busy faults otherwise).
    localparam integer NRC = 5, RCW = 28;
    reg run; reg [3:0] cur, b0; reg [4:0] lim; reg [15:0] tl, per, lps;
    reg lq, rv;                                       // launch landed (calendar starts), R valid (no fire edge just before)
    reg [15:0] b0_oh;
    wire [15:0] cur_ohc [0:NRC-1];                    // kept copies of the current row one-hot (ot_hnx_coll_aq_cff)
    reg [DW-1:0] rd_t, R, B;
    always @* begin : nb_rc
        rd_t = '0;
        for (integer j = 0; j < 16; j = j + 1)
            for (integer x = 0; x < DW; x = x + 1) rd_t[x] = rd_t[x] | (rf[j][x] & cur_ohc[x / RCW][j]);
    end
    wire [DW-1:0] rc = R;
    wire wrap = run && !lq && tl == per - 16'd1;
    wire wrap_ld = wrap && lps > 16'd1;               // period wrap that restarts the rows at b0
    wire fire = run && rv && {1'b0, cur} < lim && tl == rc[18:3];
    always @(posedge clk) begin
        R <= wrap_ld ? B : rd_t;
        if (lq) B <= rd_t;
        else if (p_we && p_wa < 8'd16 && p_wa[3:0] == b0) B <= p_wd[DW-1:0];
    end
    generate for (genvar c = 0; c < NRC; c = c + 1) begin : g_cur_oh
        wire [15:0] d = p_sv ? (16'd1 << p_sb[3:0]) : (run && !lq && wrap_ld) ? b0_oh :
                        (run && !lq && fire) ? {cur_ohc[c][14:0], cur_ohc[c][15]} : cur_ohc[c];
        ot_hnx_coll_aq_cff #(.W(16)) u_ff(.clk(clk), .d(d), .q(cur_ohc[c]));
    end endgenerate
    always @(posedge clk) if (p_sv) b0_oh <= 16'd1 << p_sb[3:0];
    // gather state (held while busy)
    reg busy; reg g_qbg, g_r2, g_self; reg [9:0] g_f; reg [7:0] g_bs; reg [15:0] g_src, g_dst, g_str;
    reg [9:0] g_kn;                                   // ring indices K = ceil(F / R)
    reg iss; reg [9:0] ik; reg [1:0] iph; reg [5:0] drain;
    // HNX train state: row counter ir (0 .. nm1), train index t (low 3 bits: tag / direction), held nm1 / row strides
    reg [3:0] ir, g_n; reg [2:0] it3; reg [15:0] g_rsa, g_rso; reg [9:0] kx;
    wire [9:0] f_kn = rc[1] ? 10'((rc[28:19] + 10'd1) >> 1) : rc[28:19];
    wire [7:0] f_es = 8'((rc[36:29] + 8'd31) >> 5);
    wire [2:0] f_rk = rc[1] ? {f_kn[1:0], 1'b0} : f_kn[2:0];          // R K mod 8
    wire f_bad = rc[28:19] == 10'd0 || |rc[71:69] ||
                 (rc[0] && (rc[36:29] == 8'd0 || rc[36:29] > 8'd64 || {2'b0, rc[28:19]} != {2'b0, rc[36:29]} + {4'b0, f_es})) ||
                 (rc[104:101] != 4'd0 && rc[123:121] != f_rk);          // HNX: rs_O = R K (mod 8) for N > 1
    wire ev_in_v = iss && iph != 2'd2;
    // calendar valids (region 0)
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            run <= 1'b0; busy <= 1'b0; iss <= 1'b0; fault <= 1'b0; active <= 1'b0; done <= 1'b0; drain <= 6'd0; lq <= 1'b0;
            rv <= 1'b0; lim <= 5'd0;
        end else begin
            done <= 1'b0;
            active <= run || busy || p_sv || lq;
            if (active && !(run || busy || p_sv || lq)) done <= 1'b1;
            lq <= p_sv;
            rv <= lq || wrap_ld || !fire;
            if (p_sv) begin
                if (run || busy || lq || p_sl > 9'd16) fault <= 1'b1;
                lim <= p_sl[4:0];
            end else if (lq) begin
                if (rd_t[100:85] == 16'd0) fault <= 1'b1;
                run <= 1'b1;
            end else if (run) begin
                if (wrap) begin
                    if (lps <= 16'd1) run <= 1'b0;
                    if ({1'b0, cur} + (fire ? 5'd1 : 5'd0) != lim) fault <= 1'b1;   // a row never fired this period
                end
            end
            if (fire) begin
                if (busy || f_bad) fault <= 1'b1;
                busy <= 1'b1; iss <= 1'b1;
            end else if (iss) begin
                if (ev_in_v && kx == g_kn - 10'd1 && ir == g_n) begin iss <= 1'b0; drain <= 6'(ND - 1); end
            end else if (busy) begin
                if (drain == 6'd0) busy <= 1'b0; else drain <= drain - 6'd1;
            end
            if (|(aq_fault & aq_vo)) fault <= 1'b1;
            if (flt_n) fault <= 1'b1;
        end
    end
    // calendar indices (region 1): row index, base row, issue indices
    always @(posedge clk or negedge rl[1]) begin
        if (!rl[1]) begin
            cur <= 4'd0; b0 <= 4'd0; ik <= 10'd0; iph <= 2'd0; ir <= 4'd0; it3 <= 3'd0; kx <= 10'd0;
        end else begin
            if (p_sv) begin cur <= p_sb[3:0]; b0 <= p_sb[3:0]; end
            else if (run && !lq) begin
                if (wrap_ld) cur <= b0;
                else if (fire) cur <= cur + 4'd1;
            end
            if (fire) begin
                ik <= 10'd0; iph <= 2'd0; ir <= 4'd0; it3 <= 3'd0; kx <= 10'd0;
            end else if (iss) begin
                if (ev_in_v) begin
                    // HNX train: row-local k restarts at each row (MUT 8: it runs on), t advances every entry
                    ik <= ik + 10'd1; kx <= kx + 10'd1; it3 <= it3 + 3'd1;
                    if (kx == g_kn - 10'd1) begin
                        kx <= 10'd0;
                        if (ir != g_n) begin ir <= ir + 4'd1; if (MUT != 8) ik <= 10'd0; end
                    end
                end
                iph <= (iph == 2'd2) ? 2'd0 : iph + 2'd1;
            end
        end
    end
    // period counter (region 2) and loop counter (region 3)
    always @(posedge clk or negedge rl[2]) begin
        if (!rl[2]) begin tl <= 16'd0; per <= 16'd0; end
        else if (p_sv) tl <= 16'd0;
        else if (lq) begin tl <= 16'd0; per <= rd_t[100:85]; end
        else if (run) begin
            if (wrap) begin if (lps > 16'd1) tl <= 16'd0; end
            else tl <= tl + 16'd1;
        end
    end
    always @(posedge clk or negedge rl[3]) begin
        if (!rl[3]) lps <= 16'd0;
        else if (p_sv) lps <= p_lp;
        else if (wrap_ld) lps <= lps - 16'd1;
    end
    always @(posedge clk or negedge rl[3]) if (!rl[3]) ld_fire <= 1'b0; else ld_fire <= fire;
    always @(posedge clk) ld_desc <= {rc[1], rc[2], rc[0], rc[28:19], rc[36:29], rc[68:53], rc[84:69], rc[136:121]};
    always @(posedge clk) if (fire) begin
        g_qbg <= rc[0]; g_r2 <= rc[1]; g_self <= rc[2]; g_f <= rc[28:19]; g_bs <= rc[36:29];
        g_src <= rc[52:37]; g_dst <= rc[68:53]; g_str <= rc[84:69]; g_kn <= f_kn;
        g_n <= rc[104:101]; g_rsa <= rc[120:105]; g_rso <= rc[136:121];
    end
    // HNX source row bases sb[r] = low 13 b of g_src + r rs_A (sector-local), registered one edge after the fire. HNX-GQ
    // (n1 route TT -112 soff -> 13-b add -> bank decode -> ld_p_d): the table holds the full row base (one add, from held
    // registers), and it is read only by the one-edge-ahead pre-stages below (entries reach them >= 7 edges after issue);
    // the issue-edge QBG request reads the running sums qa (row change: nb = next row's base, kept by one add per row).
    reg [12:0] sb [0:15];
    always @(posedge clk) for (integer r = 0; r < 16; r = r + 1) sb[r] <= g_src[12:0] + ((MUT == 6) ? 13'd0 : 13'(r * g_rsa));
    function automatic [15:0] row_src(input [3:0] r); row_src = {g_src[15:13], sb[r]}; endfunction
    // ------------------------------------------------------------------ event pipeline {v, k}
    // HNX-GQ (as GQISSUE2): the flit flags fv / is_code of each ring are decoded ONCE, on the issue edge, from registered
    // shadows of the row-local k (sfv / scd below) and travel with the entry (ev_f / ev_c); no later stage decodes them
    // from g_f / g_bs / g_r2 again (n1 route: g_f -> rb_rx_* -76, g_f -> ld_p_d -82, ik / g_r2 -> vm_rq -74).
    reg [ND-1:0] ev_v; reg [16:0] ev_k [0:ND-1];         // HNX entry {row[3:0], k[9:0], t[2:0]}
    reg [1:0] ev_f [0:ND-1], ev_c [0:ND-1];
    reg [1:0] sfv, scd;                                 // = fv(ik, r), is_code(flit_i(ik, r)) at every edge of a gather
    always @(posedge clk or negedge rl[4])
        if (!rl[4]) ev_v[19:0] <= '0; else ev_v[19:0] <= {ev_v[18:0], ev_in_v};
    always @(posedge clk or negedge rl[5])
        if (!rl[5]) ev_v[ND-1:20] <= '0; else ev_v[ND-1:20] <= ev_v[ND-2:19];
    always @(posedge clk) begin
        ev_k[0] <= {ir, ik, it3}; ev_f[0] <= sfv; ev_c[0] <= scd;
        for (integer s = 1; s < ND; s = s + 1) begin ev_k[s] <= ev_k[s-1]; ev_f[s] <= ev_f[s-1]; ev_c[s] <= ev_c[s-1]; end
    end
    // flit decode of an entry; HNX entry fields
    function automatic [9:0] ek(input [16:0] e); ek = e[12:3]; endfunction
    function automatic [3:0] er(input [16:0] e); er = e[16:13]; endfunction
    function automatic [2:0] et(input [16:0] e); et = e[2:0]; endfunction
    function automatic [10:0] flit_i(input [9:0] k, input integer r); flit_i = g_r2 ? {k, 1'(r)} : (r == 0 ? {1'b0, k} : 11'h7ff); endfunction
    function automatic fv(input [9:0] k, input integer r);     // flit (k, r) exists
        reg [10:0] i; i = flit_i(k, r); fv = (r == 0 || g_r2) && i < {1'b0, g_f};
    endfunction
    function automatic is_code(input [10:0] i); is_code = !g_qbg || i < {3'b0, g_bs}; endfunction
    function automatic [15:0] sec_add(input [15:0] s, input [12:0] a); sec_add = {s[15:13], s[12:0] + a}; endfunction
    function automatic [7:0] oh8(input [2:0] b); oh8 = 8'd1 << b; endfunction
    // ------------------------------------------------------------------ issue-edge shadows of ik (HNX-GQ, as GQISSUE2)
    // Updated on ik's edges: at fire (ik <= 0, row 0) from the fired row rc, on every issue edge from the held gather
    // state with the NEXT row-local index kn (0 at a row change; MUT 8 keeps ik + 1 as ik does). qa[4r+w] = low 13 b of
    // the QBG read address sec_add(row_src(ir), {flit_i(ik,r),2'b00} + w): +4 per index (+8 with two rings) inside a row,
    // reloaded at a row change from nb (= next row's base, nb <= nb + rs_A per row; loaded at fire from rc so row 1 may
    // start one edge after the fire). The QBG request of the issue edge is then a 3-to-8 decode of registered addresses.
    reg [12:0] qa [0:7]; reg [12:0] nb;
    wire i_adv = ev_in_v && kx == g_kn - 10'd1 && ir != g_n;     // this issue edge starts the next row
    wire [9:0] i_kn = (i_adv && MUT != 8) ? 10'd0 : ik + 10'd1;  // ik after this issue edge
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) begin sfv <= 2'd0; scd <= 2'd0; end
        else if (fire) begin
            for (integer r = 0; r < 2; r = r + 1) begin : nb_s0
                reg [10:0] i0; i0 = rc[1] ? 11'(r) : (r == 0 ? 11'd0 : 11'h7ff);
                sfv[r] <= (r == 0 || rc[1]) && i0 < {1'b0, rc[28:19]};
                scd[r] <= !rc[0] || i0 < {3'b0, rc[36:29]};
            end
        end else if (ev_in_v)
            for (integer r = 0; r < 2; r = r + 1) begin : nb_s1
                sfv[r] <= fv(i_kn, r); scd[r] <= is_code(flit_i(i_kn, r));
            end
    always @(posedge clk)
        if (fire) begin
            nb <= rc[49:37] + ((MUT == 6) ? 13'd0 : rc[117:105]);
            for (integer r = 0; r < 2; r = r + 1) begin : nb_q0
                reg [10:0] i0; i0 = rc[1] ? 11'(r) : (r == 0 ? 11'd0 : 11'h7ff);
                for (integer w = 0; w < 4; w = w + 1) qa[r*4+w] <= rc[49:37] + 13'({i0, 2'b00} + w);
            end
        end else if (i_adv) begin
            nb <= nb + ((MUT == 6) ? 13'd0 : g_rsa[12:0]);
            for (integer r = 0; r < 2; r = r + 1) begin : nb_q1
                reg [10:0] i1; i1 = flit_i(i_kn, r);
                for (integer w = 0; w < 4; w = w + 1) qa[r*4+w] <= nb + 13'({i1, 2'b00} + w);
            end
        end else if (ev_in_v)
            for (integer q = 0; q < 8; q = q + 1) qa[q] <= qa[q] + (g_r2 ? 13'd8 : 13'd4);
    // plain-read pre-stage (@S_PR-2 -> request @S_PR-1) and quantiser-feed pre-stage (@S_QCAP-1 -> x @S_QCAP): address /
    // bank one-hots registered one edge ahead from the entry's row base (held for the whole train)
    reg [1:0] pr_v; reg [15:0] pr_s [0:1];
    reg [1:0] qc_v; reg [7:0] qc_ohd [0:7];
    // HNX-GQ s3 (item 3): the quantiser-feed bank one-hots as 8 KEPT copies per 256-b word (one per 32 bits; n2: one
    // one-hot bit loaded 256 AND gates of the aq_x feed)
    wire [7:0] qc_ohq [0:7][0:7];
    generate for (genvar q = 0; q < 8; q = q + 1) begin : g_qc
        for (genvar c = 0; c < 8; c = c + 1) begin : g_c
            ot_hnx_coll_aq_cff #(.W(8)) u_ff(.clk(clk), .d(qc_ohd[q]), .q(qc_ohq[q][c]));
        end
    end endgenerate
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) begin pr_v <= 2'd0; qc_v <= 2'd0; end
        else for (integer r = 0; r < 2; r = r + 1) begin
            pr_v[r] <= ev_v[S_PR-2] && ev_f[S_PR-2][r];
            qc_v[r] <= ev_v[S_QCAP-1] && g_qbg && ev_f[S_QCAP-1][r] && ev_c[S_QCAP-1][r];
        end
    always @(posedge clk) for (integer r = 0; r < 2; r = r + 1) begin : nb_pq
        pr_s[r] <= sec_add(row_src(er(ev_k[S_PR-2])), 13'(flit_i(ek(ev_k[S_PR-2]), r)));
    end
    always @* for (integer r = 0; r < 2; r = r + 1) begin : nb_pqd
        reg [10:0] i; reg [15:0] s;
        i = flit_i(ek(ev_k[S_QCAP-1]), r);
        for (integer w = 0; w < 4; w = w + 1) begin s = sec_add(row_src(er(ev_k[S_QCAP-1])), 13'({i, 2'b00} + w)); qc_ohd[r*4+w] = oh8(s[2:0]); end
    end
    // ------------------------------------------------------------------ VM reads (issue) + response check
    reg [7:0] rd_exp;
    reg [135:0] vm_rq_d;
    always @* begin : nb_rqd
        vm_rq_d = '0;
        if (g_qbg && ev_in_v) begin
            for (integer r = 0; r < 2; r = r + 1) begin : nb_1
                reg [15:0] s;
                if (sfv[r] && scd[r])
                    for (integer w = 0; w < 4; w = w + 1) begin
                        s = {g_src[15:13], qa[r*4+w]};
                        for (integer b = 0; b < 8; b = b + 1) if (s[2:0] == 3'(b)) vm_rq_d[b*17 +: 17] = {1'b1, s};
                    end
            end
        end
        if (!g_qbg && ev_v[S_PR-1]) begin
            for (integer r = 0; r < 2; r = r + 1) begin : nb_2
                if (pr_v[r]) for (integer b = 0; b < 8; b = b + 1) if (pr_s[r][2:0] == 3'(b)) vm_rq_d[b*17 +: 17] = {1'b1, pr_s[r]};
            end
        end
    end
    generate for (genvar b = 0; b < 8; b = b + 1) begin : g_rq
        always @(posedge clk or negedge rl[7 + b / 2])
            if (!rl[7 + b / 2]) vm_rq[b*17 +: 17] <= 17'd0; else vm_rq[b*17 +: 17] <= vm_rq_d[b*17 +: 17];
    end endgenerate
    // expected response valids (one edge before the capture register is loaded)
    always @(posedge clk or negedge rl[11])
        if (!rl[11]) rd_exp <= 8'd0; else for (integer b = 0; b < 8; b = b + 1) rd_exp[b] <= vm_rq[b*17+16];
    // read latency: rq register @n -> bank samples n+1 -> registered response n+7 -> pin capture n+8.
    reg [7:0] rdx [0:7];
    always @(posedge clk or negedge rl[12])
        if (!rl[12]) for (integer d = 0; d < 4; d = d + 1) rdx[d] <= 8'd0;
        else begin rdx[0] <= rd_exp; for (integer d = 1; d < 4; d = d + 1) rdx[d] <= rdx[d-1]; end
    always @(posedge clk or negedge rl[13])
        if (!rl[13]) for (integer d = 4; d < 8; d = d + 1) rdx[d] <= 8'd0;
        else for (integer d = 4; d < 8; d = d + 1) rdx[d] <= rdx[d-1];
    reg [2055:0] rr_q; reg [7:0] rrv_q;
    function automatic [255:0] rdw_oh(input [7:0] oh);  // captured read word through a one-hot AND-OR (registered one-hot select)
        rdw_oh = 256'd0;
        for (integer j = 0; j < 8; j = j + 1) rdw_oh = rdw_oh | (rr_q[j*257 +: 256] & {256{oh[j]}});
    endfunction
    always @(posedge clk) rr_q <= vm_rr;
    always @(posedge clk or negedge rl[11])
        if (!rl[11]) rrv_q <= 8'd0; else for (integer b = 0; b < 8; b = b + 1) rrv_q[b] <= vm_rr[b*257+256];
    // rdx[6] holds the expectation of the response captured in rr_q this edge
    wire rd_bad = rrv_q != rdx[6];
    // ------------------------------------------------------------------ quantiser feed (@9) and capture (@23)
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) aq_v <= 2'd0;
        else aq_v <= qc_v;
    function automatic [31:0] rdw32(input [7:0] oh, input integer c);   // 32-b chunk c of the one-hot selected read word
        rdw32 = 32'd0;
        for (integer j = 0; j < 8; j = j + 1) rdw32 = rdw32 | (rr_q[j*257 + 32*c +: 32] & {32{oh[j]}});
    endfunction
    always @(posedge clk) for (integer q = 0; q < 8; q = q + 1) for (integer c = 0; c < 8; c = c + 1)
        aq_x[q*256 + 32*c +: 32] <= rdw32(qc_ohq[q][c], c);
    // HNX-GQ s3: no capture register behind the quantisers: aq_q / aq_eb ARE the quantisers' output registers (one edge
    // later than ot_hgi_coll_aq13's, i.e. at n2's aq_q_q / aq_eb_q edge); aq_vo / aq_fault likewise.
    // ------------------------------------------------------------------ payload P (@24) + exponent words
    reg [511:0] ex;                                    // exponent words 0, 1 (bytes = e + 127)
    reg [511:0] ex_n;                                  // with this edge's blocks merged (forwarding)
    // HNX-GQ (as GQISSUE2): every select of P is decoded one edge ahead from ev[S_P-2] into registered one-hots (pp_*):
    // the 64-byte exponent merge mask, the raw-read bank (from the entry's row base) and the code / exponent-word-0 /
    // exponent-word-1 kind (n1 route: soff / ev_k / g_f -> 13-b add / compare -> decode -> 512-b mux, -112 / -98 / -82).
    // HNX-GQ s3 (item 3): the per-ring selects {raw bank one-hot, code, exponent word 0, word 1} are 8 KEPT copies (one
    // per 32 bits of P; n2: one select bit loaded 256 AND gates); the exponent merge reads byte j from eb copy j / 16.
    reg [1:0] pp_v; reg [63:0] pp_em [0:1]; reg [10:0] pp_d [0:1];
    wire [10:0] pp_sel [0:1][0:7];                     // {raw[7:0], code, lo, hi}
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) pp_v <= 2'd0;
        else for (integer r = 0; r < 2; r = r + 1) pp_v[r] <= ev_v[S_P-2] && ev_f[S_P-2][r];
    always @(posedge clk) for (integer r = 0; r < 2; r = r + 1) begin : nb_pp
        reg [10:0] i; i = flit_i(ek(ev_k[S_P-2]), r);
        pp_em[r] <= (ev_v[S_P-2] && g_qbg && ev_f[S_P-2][r] && ev_c[S_P-2][r]) ? (64'd1 << i[5:0]) : 64'd0;
    end
    always @* for (integer r = 0; r < 2; r = r + 1) begin : nb_ppd
        reg [10:0] i; reg [15:0] s; i = flit_i(ek(ev_k[S_P-2]), r); s = sec_add(row_src(er(ev_k[S_P-2])), 13'(i));
        pp_d[r] = {g_qbg ? 8'd0 : oh8(s[2:0]), g_qbg && ev_c[S_P-2][r], g_qbg && !ev_c[S_P-2][r] && i == {3'b0, g_bs},
                   g_qbg && !ev_c[S_P-2][r] && i != {3'b0, g_bs}};
    end
    generate for (genvar r = 0; r < 2; r = r + 1) begin : g_pp
        for (genvar c = 0; c < 8; c = c + 1) begin : g_c
            ot_hnx_coll_aq_cff #(.W(11)) u_ff(.clk(clk), .d(pp_d[r]), .q(pp_sel[r][c]));
        end
    end endgenerate
    always @* begin : nb_5
        ex_n = ex;
        for (integer r = 0; r < 2; r = r + 1)
            for (integer j = 0; j < 64; j = j + 1) if (pp_em[r][j]) ex_n[j*8 +: 8] = aq_eb[r][8*(j/16) +: 8];
    end
    reg [1:0] p_v; reg [255:0] p_d [0:1];
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) p_v <= 2'd0;
        else p_v <= pp_v;
    always @(posedge clk) begin
        if (fire) ex <= '0; else ex <= ex_n;
        for (integer r = 0; r < 2; r = r + 1)
            for (integer c = 0; c < 8; c = c + 1) begin : nb_pc
                reg [10:0] sl; sl = pp_sel[r][c];
                p_d[r][32*c +: 32] <= rdw32(sl[10:3], c) | (aq_q[r*256 + 32*c +: 32] & {32{sl[2]}}) |
                                      (ex_n[32*c +: 32] & {32{sl[1]}}) | (ex_n[256 + 32*c +: 32] & {32{sl[0]}});
            end
    end
    // ------------------------------------------------------------------ ring B commands (lp @24, read @25, inject @27, rx @27+2h)
    // and ring-A gather commands (same edges into A1, merge register one edge later)
    reg [290:0] cb [0:1];      // per ring: {lp_we, lp_tag, lp_data, rd, rd_tag, inj2, fwd2, tag3, ttl4, rx2, kind4, src4, rtag6}
    always @* begin : nb_8
        for (integer r = 0; r < 2; r = r + 1) begin : nb_9
            reg lpw; reg [2:0] lpt; reg [255:0] lpd; reg rd; reg [2:0] rdt; reg [1:0] inj, fwd, rx; reg [2:0] ttg;
            reg [3:0] ttl, kind, src; reg [5:0] rtag; reg [9:0] k; reg [2:0] t;
            lpw = 0; lpt = 0; lpd = 0; rd = 0; rdt = 0; inj = 0; fwd = 0; rx = 0; ttg = 0; ttl = 0; kind = 0; src = 0; rtag = 0;
            // lp write of the payload: computed with P (ev[23]); P itself is the data
            k = ek(ev_k[S_BLP-1]); t = et(ev_k[S_BLP-1]);
            if (ev_v[S_BLP-1] && ev_f[S_BLP-1][r]) begin lpw = 1; lpt = t; end
            k = ek(ev_k[S_BRD-1]); t = et(ev_k[S_BRD-1]);
            if (ev_v[S_BRD-1] && ev_f[S_BRD-1][r]) begin rd = 1; rdt = t; end
            k = ek(ev_k[S_BINJ-1]); t = et(ev_k[S_BINJ-1]);
            if (ev_v[S_BINJ-1] && ev_f[S_BINJ-1][r]) begin inj[t[0]] = 1; ttg = t; ttl[t[0]*2 +: 2] = 2'd3; end
            for (integer h = 1; h <= 3; h = h + 1) begin
                k = ek(ev_k[S_BRX + 2*h - 1]); t = et(ev_k[S_BRX + 2*h - 1]);
                if (ev_v[S_BRX + 2*h - 1] && ev_f[S_BRX + 2*h - 1][r]) begin
                    rx[t[0]] = 1; kind[t[0]*2 +: 2] = 2'd3; src[t[0]*2 +: 2] = srcq(q_id, t[0], h); rtag[t[0]*3 +: 3] = t;
                    if (h < 3) fwd[t[0]] = 1;
                end
            end
            cb[r] = {lpw, lpt, 256'd0, rd, rdt, inj, fwd, ttg, ttl, rx, kind, src, rtag};
        end
    end
    // P is loaded on the lp edge, so the lp data of the registered command word is P (r).
    reg [290:0] a1;             // ring-A gather command (ring B timing)
    reg [290:0] b1;             // ring B command register (MUT 5: one more edge)
    always @(posedge clk or negedge rl[14]) if (!rl[14]) a1 <= '0; else a1 <= cb[0];
    always @(posedge clk or negedge rl[15]) if (!rl[15]) b1 <= '0; else b1 <= cb[1];
    wire [255:0] a1_d = p_d[0], b1_d = p_d[1];
    assign ld_ev_v = ev_v[0]; assign ld_ev_k = ev_k[0]; assign ld_p_v = p_v; assign ld_p_d = {p_d[1], p_d[0]};
    reg [290:0] b2; reg [255:0] b2_d;
    always @(posedge clk or negedge rl[16]) if (!rl[16]) b2 <= '0; else b2 <= b1;
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
    always @(posedge clk or negedge rl[18]) if (!rl[18]) isa_q[28:0] <= '0; else isa_q[28:0] <= isa_ring[28:0];
    always @(posedge clk or negedge rl[19]) if (!rl[19]) isa_q[57:29] <= '0; else isa_q[57:29] <= isa_ring[57:29];
    always @(posedge clk) isa_d_q <= isa_lp_data;
    reg merge_bad;
    always @(posedge clk or negedge rl[17]) begin
        if (!rl[17]) begin
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
    always @(posedge clk or negedge rl[3])
        if (!rl[3]) flt_q <= 1'b0; else flt_q <= rd_bad || merge_bad;
endmodule

// Landing leaf: captures both rings' publishes and the local payload P, and writes the quadrant VM through the COLL
// kq port (via the kq share). Every input pin-registered, every output a register. Stages as the issue leaf's.
module ot_hnx_coll_gq_land #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire          ld_fire,
    input  wire [68:0]   ld_desc,      // HNX: + rs_O [15:0]
    input  wire          ld_ev_v,
    input  wire [16:0]   ld_ev_k,      // HNX entry {row[3:0], k[9:0], t[2:0]}
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
    reg f_q; reg [68:0] d_q; reg [1:0] pl_v; reg [511:0] pl_d;
    reg [NL-1:0] le_v; reg [16:0] le_k [0:NL-1];
    always @(posedge clk or negedge rn)
        if (!rn) begin f_q <= 1'b0; pl_v <= 2'd0; le_v <= '0; end
        else begin f_q <= ld_fire; pl_v <= ld_p_v; le_v <= {le_v[NL-2:0], ld_ev_v}; end
    always @(posedge clk) begin
        d_q <= ld_desc; pl_d <= ld_p_d; le_k[0] <= ld_ev_k;
        for (integer j = 1; j < NL; j = j + 1) le_k[j] <= le_k[j-1];
    end
    // descriptor (held for the gather; gathers never overlap: the issue leaf faults a fire while busy)
    reg g_r2, g_self, g_qbg; reg [9:0] g_f; reg [7:0] g_bs; reg [15:0] g_dst, g_str, g_rso;
    always @(posedge clk) if (f_q) {g_r2, g_self, g_qbg, g_f, g_bs, g_dst, g_str, g_rso} <= d_q;
    function automatic [9:0] ek(input [16:0] e); ek = e[12:3]; endfunction
    function automatic [3:0] er(input [16:0] e); er = e[16:13]; endfunction
    function automatic [2:0] et(input [16:0] e); et = e[2:0]; endfunction
    // HNX destination row offsets roff[r] = r rs_O (13-b sector-local), registered from the held descriptor like base_q
    // (first use >= 23 edges after the fire); MUT 7 drops them.
    reg [12:0] roff [0:15];
    always @(posedge clk) for (integer r = 0; r < 16; r = r + 1) roff[r] <= (MUT == 7) ? 13'd0 : 13'(r * g_rso);
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
            reg [9:0] k; reg [2:0] t; reg [3:0] rw; reg [10:0] i; reg [1:0] sq; reg [15:0] s;
            for (integer h = 1; h <= 3; h = h + 1)
                for (integer r = 0; r < 2; r = r + 1) begin
                    k = ek(le_k[S_KQ + 2*h - 3]); t = et(le_k[S_KQ + 2*h - 3]); rw = er(le_k[S_KQ + 2*h - 3]);
                    i = flit_i(k, r); sq = srcq(q_id, t[0], h);
                    s = {base_q[sq][15:13], base_q[sq][12:0] + roff[rw] + 13'(i) + ((MUT == 3) ? 13'd1 : 13'd0)};
                    ln_en[(h-1)*2 + r] <= le_v[S_KQ + 2*h - 3] && fv(k, r);
                    ln_bk[(h-1)*2 + r] <= 8'd1 << s[2:0]; ln_s[(h-1)*2 + r] <= s;
                    ln_sq[(h-1)*2 + r] <= sq; ln_d[(h-1)*2 + r] <= t[0];
                end
            for (integer r = 0; r < 2; r = r + 1) begin
                k = ek(le_k[23]); rw = er(le_k[23]); i = flit_i(k, r);
                s = {base_q[q_id][15:13], base_q[q_id][12:0] + roff[rw] + 13'(i)};
                ln_en[6 + r] <= g_self && MUT != 4 && le_v[23] && fv(k, r);
                ln_bk[6 + r] <= 8'd1 << s[2:0]; ln_s[6 + r] <= s;
            end
        end
    reg [2247:0] kq_n; reg kq_bad, pub_bad;
    always @* begin : nb_11
        reg [3:0] lane_exp; reg [7:0] act; reg [7:0] seen; reg [255:0] gd [0:7];
        reg v; reg [1:0] gs; reg [2:0] gt; reg [2:0] kk; integer l;
        kq_n = '0; kq_bad = 1'b0; pub_bad = 1'b0; lane_exp = 4'd0; seen = 8'd0; act = 8'd0; v = 1'b0; gs = 2'd0; gt = 3'd0;
        for (integer m = 0; m < 8; m = m + 1) gd[m] = '0;
        for (integer h = 1; h <= 3; h = h + 1)
            for (integer r = 0; r < 2; r = r + 1) begin
                l = (h-1)*2 + r;
                kk = et(le_k[S_KQ + 2*h - 2]);      // HNX: the tag is the train index t mod 8
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
    always @(posedge clk or negedge rn)
        if (!rn) begin vm_kq <= '0; fault <= 1'b0; end
        else begin vm_kq <= kq_n; if (kq_bad || pub_bad) fault <= 1'b1; end
endmodule
// The gather master as placed per quadrant: issue leaf (F20 target, calendar, VM reads, quantisers, payload, ring-A merge
// register, ring-B commands) + landing leaf (publish capture, VM writes). Wires only.
module ot_hnx_coll_gq #(parameter integer MUT = 0)(
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
    wire ld_fire, ld_ev_v; wire [68:0] ld_desc; wire [16:0] ld_ev_k; wire [1:0] ld_p_v; wire [511:0] ld_p_d;
    ot_hnx_coll_gq_issue #(.MUT(MUT)) u_issue(.clk(clk_issue), .rst_n(rst_n), .qid(qid), .tgt(tgt), .cfg_v(cfg_v),
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
    ot_hnx_coll_gq_land #(.MUT(MUT)) u_land(.clk(clk_land), .rst_n(rst_n), .qid(qid), .ld_fire(ld_fire), .ld_desc(ld_desc),
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
module ot_hnx_coll_kq_share2_leaf #(parameter integer MUT = 0)(
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
module ot_hnx_coll_kq_share2 #(parameter integer MUT = 0)(
    input  wire [3:0] clk_pair, input wire rst_n,
    input  wire [2247:0] a_kq, b_kq,
    output wire [2247:0] vm_kq,
    output wire fault
);
    wire [3:0] f;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        ot_hnx_coll_kq_share2_leaf #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n), .a_kq(a_kq[562*p +: 562]),
            .b_kq(b_kq[562*p +: 562]), .vm_kq(vm_kq[562*p +: 562]), .fault(f[p]));
    end
    assign fault = |f;
endmodule
`default_nettype wire
