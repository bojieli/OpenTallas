`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX wide adapter, TILED form (ot_hgi_idx_index_wt): QCORE leaf.
// Frame command registers and FSM, chunk walker / issuer (the reference's static streams B -> C id/value pairs -> A),
// the group-order log, the 2:1 chunk merge, head weights, the query ring (16 sectors = 4 blocks, read in aligned blocks)
// and the fs / qb launch.  SPEC results/arch/hbm_b2_idx_ixw1_1013/SPEC.md "Tiled redesign".
//   S1  a descriptor goes to the lane leaf of its group while that leaf's log has room (LGD un-popped descriptors);
//       the leaf reports each chunk READY once landed; a ready chunk at the head of the group-order log is POPPED once
//       its consumer slot is reserved (B, C id: always; C value: a K-result credit; A: ring room for its sectors).
//       The popped beat arrives exactly 4 cycles after the pop decision, so beats arrive in pop order, never stall, and
//       every select / load-enable of the arrival cycle is a registered copy prepared the cycle before.
//   S2  C chunks leave in a registered beat to KEEP; KEEP returns one credit a drained K result and kin_sent.
//   S4  start / abort / flush pulses and the static frame fields to BEAT and WR; their status comes back registered.
// Every input lands in a flop, every output leaves a flop; only control flops are reset (the ring pointers and the
// ring counts are reset by rst_n only: a completed frame leaves them block-aligned and empty).
// MUT 1 (inherited): head weight of the next head.  MUT 13 (bench): the first ready credit of lane leaf 0 in a frame is
// counted twice (a credit seam returns a credit twice; must FAIL).
module ot_hgi_idxw_qcore #(
    parameter integer MUT = 0,
    parameter integer LGD = 8,      // lane-leaf chunk log depth
    parameter integer KFD = 8       // KEEP result FIFO depth = K-result credits
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go_i,
    input  wire [11:0]   k_i,
    input  wire          cand_en_i, keep_en_i,
    input  wire [31:0]   n_i,
    input  wire [6:0]    rank_i,
    input  wire [19:0]   pos_i,
    input  wire [17:0]   a_base_i, b_base_i, c_base_i, o_base_i, r_base_i, d_base_i,
    input  wire [17:0]   d_stride_i,
    input  wire [17:0]   c_stride_i,
    input  wire [11:0]   c_n_i,
    input  wire          has_r_i,
    output reg           done_o,
    output reg           fault_o,
    output reg           rg_req_o,
    output reg  [89:0]   fs_o,
    output wire [1047:0] qb_o,
    input  wire          qbr_i,
    input  wire [1:0]    ev_i,
    // S1 (lane leaves 0 / 1)
    output wire [18:0]   dsc0_o, dsc1_o,
    output reg           pop0_o, pop1_o,
    input  wire [1023:0] ob0_i, ob1_i,
    input  wire          ob0_v_i, ob1_v_i,
    input  wire          rdy0_i, rdy1_i,
    // S2 (KEEP)
    output wire [1023:0] kc_d_o,
    output reg           kc_ci_o, kc_cv_o, kc_last_o,
    output reg  [1:0]    kc_slot_o,
    output reg  [2:0]    kc_cnt_o,
    output reg  [12:0]   kc_shi_o,
    output reg           kstart_o,
    output reg           keep_en_o,
    output reg  [6:0]    rank_o,
    output reg  [17:0]   c_base_o,
    output reg  [11:0]   c_n_o,
    input  wire          kcr_i,
    input  wire          kin_sent_i,
    // S4 (BEAT)
    output reg           bstart_o,
    output reg           cand_en_o,
    input  wire          b_idle_i,
    input  wire          b_bad_i,
    // S4 (WR)
    output reg           wstart_o, flush_o, wabort_o,
    output reg           has_r_o,
    output reg  [17:0]   o_base_o, r_base_o, d_base_o, dv_base_o,
    input  wire          w_done_i
);
    localparam [1:0] K_B = 2'd0, K_CI = 2'd1, K_CV = 2'd2, K_A = 2'd3;
    localparam integer LCB = $clog2(LGD) + 1, KCB = $clog2(KFD) + 1;
    integer i, l;
    genvar gi, gj, gc, gr;
    // ---- reset
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    wire [2:0] rnc;
    generate for (gr = 0; gr < 3; gr = gr + 1) begin : g_rn
        reg r;
        (* keep = "true" *) always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rn;
        assign rnc[gr] = r;
    end endgenerate
    // ---- pin flops: frame command (held by the record station for the whole frame) and status
    reg go; reg [11:0] k; reg cand_en, keep_en; reg [31:0] n; reg [6:0] rank; reg [19:0] pos;
    reg [17:0] a_base, b_base, c_base, o_base, r_base, d_base, d_stride, c_stride; reg [11:0] c_n; reg has_r;
    reg qbr_q, kcr_q, kin_sent_q, b_idle_q, b_bad_q, w_done_q; reg [1:0] ev_q, rdy_q, ib_v;
    always @(posedge clk or negedge rnc[0])
        if (!rnc[0]) begin go <= 1'b0; qbr_q <= 1'b0; kcr_q <= 1'b0; kin_sent_q <= 1'b0; b_idle_q <= 1'b0; b_bad_q <= 1'b0;
            w_done_q <= 1'b0; ev_q <= 2'd0; rdy_q <= 2'd0; ib_v <= 2'd0; end
        else begin go <= go_i; qbr_q <= qbr_i; kcr_q <= kcr_i; kin_sent_q <= kin_sent_i; b_idle_q <= b_idle_i;
            b_bad_q <= b_bad_i; w_done_q <= w_done_i; ev_q <= ev_i; rdy_q <= {rdy1_i, rdy0_i}; ib_v <= {ob1_v_i, ob0_v_i}; end
    reg [2047:0] ib;                        // the two lane-leaf chunk beats (leaf g lane l at bits (4g + l) * 256)
    always @(posedge clk) begin
        k <= k_i; cand_en <= cand_en_i; keep_en <= keep_en_i; n <= n_i; rank <= rank_i; pos <= pos_i;
        a_base <= a_base_i; b_base <= b_base_i; c_base <= c_base_i; o_base <= o_base_i; r_base <= r_base_i;
        d_base <= d_base_i; d_stride <= d_stride_i; c_stride <= c_stride_i; c_n <= c_n_i; has_r <= has_r_i;
        ib <= {ob1_i, ob0_i};
        // static frame fields to the other leaves (free-running; they are stable from the go cycle)
        keep_en_o <= keep_en; rank_o <= rank; c_base_o <= c_base; c_n_o <= c_n; cand_en_o <= cand_en; has_r_o <= has_r;
        o_base_o <= o_base; r_base_o <= r_base; d_base_o <= d_base; dv_base_o <= d_base + d_stride;
    end
    // ---- frame state
    localparam [1:0] S_IDLE = 2'd0, S_RUN = 2'd1, S_FLUSH = 2'd2, S_ABORT = 2'd3;
    reg [1:0] st; reg bad, sel_done, fs_pend, wbad;
    // ---- chunk walker (the reference's two-stage issuer: walk into a registered descriptor, issue on room)
    reg is_on, is_cv; reg [1:0] is_kind; reg [14:0] is_sec, is_end, c_s0, c_s1, a_s0, cs8;
    reg [1:0] nx_kind; reg [14:0] nx_sec; reg [2:0] nx_cnt, room; reg nx_last;
    reg pd_v; reg [1:0] ch_kind; reg [14:0] ch_sec; reg [2:0] ch_cnt; reg ch_lastc;
    always @* begin
        nx_kind = (is_kind == K_CI && is_cv) ? K_CV : is_kind;
        room = 3'd4 - {1'b0, is_sec[1:0]};
        if (is_kind == K_B) nx_cnt = 3'd1;
        else if ({12'd0, room} > is_end - is_sec) nx_cnt = 3'(is_end - is_sec + 15'd1);
        else nx_cnt = room;
        nx_sec = (nx_kind == K_CV) ? is_sec + cs8 : is_sec;
        nx_last = is_sec + {12'd0, nx_cnt} > is_end;
    end
    // group-order log {lastC, group, kind, slot, count, sector[14:2]} and the per-leaf counts
    localparam integer GW = 22;
    reg [GW-1:0] glog [0:15]; reg [3:0] gh, gh_b, gt; reg [4:0] gn;   // gh / gh_b: head pointer copies (one a half entry)
    reg [LCB-1:0] lcnt [0:1];               // descriptors sent to leaf g and not yet popped
    reg [LCB-1:0] rdyc [0:1];               // chunks leaf g reported ready and not yet popped
    reg [KCB-1:0] kcred;                    // K-result credits
    reg [4:0] rfree;                        // ring sectors not reserved
    reg [4:0] rcnt;                         // ring sectors stored
    reg m13;
    wire ch_g = ch_sec[2];
    wire ch_go = pd_v && st == S_RUN && !bad && lcnt[ch_g] != LCB'(LGD) && gn != 5'd16;
    wire wk_go = st == S_RUN && is_on && !bad && (!pd_v || ch_go);
    wire [GW-1:0] gq_a = glog[gh], gq_b = glog[gh_b];
    wire [GW-1:0] gq = {gq_b[GW-1:11], gq_a[10:0]};
    wire h_last = gq[21], h_g = gq[20]; wire [1:0] h_kind = gq[19:18], h_slot = gq[17:16];
    wire [2:0] h_cnt = gq[15:13]; wire [12:0] h_shi = gq[12:0];
    wire h_av = rdyc[h_g] != '0 || rdy_q[h_g];
    wire h_rs = h_kind == K_B || h_kind == K_CI || (h_kind == K_CV && kcred != '0) || (h_kind == K_A && rfree >= {2'd0, h_cnt});
    wire pop = st == S_RUN && !bad && gn != 5'd0 && h_av && h_rs;
    // pop pipeline: the beat popped in cycle t is in the pin flops ib in cycle t + 4 (stage p4)
    reg p1_v, p2_v, p3_v, p4_v; reg [GW-1:0] p1, p2, p3; reg [GW-1:0] p4;
    wire p3_g = p3[20]; wire [1:0] p3_kind = p3[19:18], p3_slot = p3[17:16]; wire [2:0] p3_cnt = p3[15:13];
    wire p4_g = p4[20]; wire [1:0] p4_kind = p4[19:18]; wire [2:0] p4_cnt = p4[15:13];
    // ---- arrival-cycle selects, prepared in p3 as registered copies (one a 64-bit slice)
    //   C: 2:1 merge into the KEEP beat
    generate for (gc = 0; gc < 16; gc = gc + 1) begin : g_kc
        reg s; reg [63:0] d;
        (* keep = "true" *) always @(posedge clk) s <= p3_g;
        always @(posedge clk) d <= s ? ib[1024 + gc*64 +: 64] : ib[gc*64 +: 64];
        assign kc_d_o[gc*64 +: 64] = d;
    end endgenerate
    //   B: the chunk's one sector into xs
    wire [255:0] xs;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_xs
        reg [2:0] s; reg [63:0] d, v; integer e;
        (* keep = "true" *) always @(posedge clk) s <= {p3_g, p3_slot};
        always @* begin v = 64'd0; for (e = 0; e < 8; e = e + 1) if (s == 3'(e)) v = v | ib[e*256 + gc*64 +: 64]; end
        always @(posedge clk) d <= v;
        assign xs[gc*64 +: 64] = d;
    end endgenerate
    //   A: ring entry j takes sector (slot + (j - rw3) mod 4) of leaf g when (j - rw3) mod 16 < count
    reg [3:0] rw3;                          // ring write pointer of the chunk in p3
    wire [16*256-1:0] rgf;
    generate for (gj = 0; gj < 16; gj = gj + 1) begin : g_rg
        wire [3:0] dj = 4'(gj) - rw3;
        wire en_d = p3_v && p3_kind == K_A && {1'b0, dj} < {2'd0, p3_cnt};
        wire [2:0] sel_d = {p3_g, 2'(p3_slot + dj[1:0])};
        for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
            reg en; reg [2:0] s; reg [63:0] d, v; integer e;
            (* keep = "true" *) always @(posedge clk) begin en <= en_d; s <= sel_d; end
            always @* begin v = 64'd0; for (e = 0; e < 8; e = e + 1) if (s == 3'(e)) v = v | ib[e*256 + gc*64 +: 64]; end
            always @(posedge clk) if (en) d <= v;
            assign rgf[gj*256 + gc*64 +: 64] = d;
        end
    end endgenerate
    // ---- head weights (B chunks arrive in sector order: chunk j holds words b_base[2:0] + i with (b3 + i) >> 3 == j)
    reg xb_v; reg [2:0] xb_j, bj;
    reg [15:0] wts [0:31];
    wire [31:0] wb;
    generate for (gi = 0; gi < 8; gi = gi + 1) begin : g_b3
        for (gj = 0; gj < 4; gj = gj + 1) begin : g_w
            reg [2:0] b3;                   // one copy of the static word offset a weight
            (* keep = "true" *) always @(posedge clk) b3 <= b_base[2:0];
            wire [5:0] bq = {3'd0, b3} + 6'(gi*4 + gj);
            wire hit = xb_v && xb_j == bq[5:3];
            always @(posedge clk) if (hit) wts[gi*4 + gj] <= xs[{bq[2:0], 5'd16} +: 16];
            assign wb[gi*4 + gj] = hit && xs[{bq[2:0], 5'd0} +: 16] != 16'd0;
        end
    end endgenerate
    // ---- query blocks out: block read pointer as registered copies, the qb data register loads the block every cycle
    reg [7:0] qsent; reg [2:0] qcred; reg qb_v; reg [6:0] qb_h; reg [15:0] qb_w;
    wire q_send = st == S_RUN && rcnt >= 5'd4 && qcred != 3'd0 && qsent != 8'd128 &&
                  (qsent != 8'd127 || !keep_en || kin_sent_q);
    generate for (gc = 0; gc < 16; gc = gc + 1) begin : g_qb
        reg [1:0] rb; reg [63:0] d, v; integer e;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1]) rb <= 2'd0; else if (q_send) rb <= rb + 2'd1;
        always @* begin
            v = 64'd0;
            for (e = 0; e < 4; e = e + 1) if (rb == 2'(e)) v = v | rgf[(e*4 + gc/4)*256 + (gc%4)*64 +: 64];
        end
        always @(posedge clk) d <= v;
        assign qb_o[8 + gc*64 +: 64] = d;
    end endgenerate
    assign qb_o[0] = qb_v; assign qb_o[7:1] = qb_h; assign qb_o[1047:1032] = qb_w;
    wire [4:0] q_head = (MUT == 1) ? 5'(qsent[6:2] + 5'd1) : qsent[6:2];
    always @(posedge clk) begin qb_h <= {qsent[1:0], qsent[6:2]}; qb_w <= wts[q_head]; end
    // descriptor payloads (free-running; valid only with the v bit)
    reg [1:0] dsc_v; reg [17:0] dsc_d;
    assign dsc0_o = {dsc_v[0], dsc_d}; assign dsc1_o = {dsc_v[1], dsc_d};
    always @(posedge clk) dsc_d <= {ch_sec[1:0], ch_cnt, ch_sec[14:2]};
    always @(posedge clk) if (ch_go) glog[gt] <= {ch_lastc, ch_g, ch_kind, ch_sec[1:0], ch_cnt, ch_sec[14:2]};
    always @(posedge clk) begin
        p1 <= gq; p2 <= p1; p3 <= p2; p4 <= p3;
        kc_last_o <= p4[21]; kc_slot_o <= p4[17:16]; kc_cnt_o <= p4[15:13]; kc_shi_o <= p4[12:0];
        xb_j <= bj;
        if (wk_go) begin ch_kind <= nx_kind; ch_sec <= nx_sec; ch_cnt <= nx_cnt; ch_lastc <= nx_kind == K_CV && nx_last; end
    end
    (* keep = "true" *) always @(posedge clk) if (!rnc[2]) gh_b <= 4'd0; else if (pop) gh_b <= gh_b + 4'd1;
    wire rd_idle = !is_on && !pd_v && gn == 5'd0 && !p1_v && !p2_v && !p3_v && !p4_v;
    wire a_arr = p4_v && p4_kind == K_A;
    // ---- main sequential block (control)
    always @(posedge clk) begin
        if (!rnc[2]) begin
            st <= S_IDLE; done_o <= 1'b0; fault_o <= 1'b0; rg_req_o <= 1'b0; fs_o[0] <= 1'b0; bad <= 1'b0; sel_done <= 1'b0;
            fs_pend <= 1'b0; wbad <= 1'b0; is_on <= 1'b0; is_cv <= 1'b0; pd_v <= 1'b0; gh <= 4'd0; gt <= 4'd0; gn <= 5'd0;
            lcnt[0] <= '0; lcnt[1] <= '0; rdyc[0] <= '0; rdyc[1] <= '0; kcred <= KCB'(KFD); rfree <= 5'd16; rcnt <= 5'd0;
            m13 <= 1'b0; p1_v <= 1'b0; p2_v <= 1'b0; p3_v <= 1'b0; p4_v <= 1'b0; rw3 <= 4'd0; xb_v <= 1'b0; bj <= 3'd0;
            qsent <= 8'd0; qcred <= 3'd4; qb_v <= 1'b0; dsc_v <= 2'd0; pop0_o <= 1'b0; pop1_o <= 1'b0;
            kc_ci_o <= 1'b0; kc_cv_o <= 1'b0; kstart_o <= 1'b0; bstart_o <= 1'b0; wstart_o <= 1'b0; flush_o <= 1'b0;
            wabort_o <= 1'b0;
        end else begin
            done_o <= 1'b0; fault_o <= 1'b0; fs_o[0] <= 1'b0; kstart_o <= 1'b0; bstart_o <= 1'b0; wstart_o <= 1'b0;
            flush_o <= 1'b0; wabort_o <= 1'b0;
            if (ev_q[0] && st != S_IDLE) sel_done <= 1'b1;
            wbad <= |wb;
            if ((ev_q[1] || b_bad_q || wbad) && st != S_IDLE) bad <= 1'b1;
            // arrival check (fail closed): exactly the expected leaf's beat, and no beat when none is expected
            if (st != S_IDLE && ib_v != (p4_v ? (p4_g ? 2'b10 : 2'b01) : 2'b00)) bad <= 1'b1;
            // ---- issue
            dsc_v <= {ch_go && ch_g, ch_go && !ch_g};
            if (ch_go) gt <= gt + 4'd1;
            if (wk_go) pd_v <= 1'b1; else if (ch_go) pd_v <= 1'b0;
            if (wk_go) begin
                if (nx_kind == K_CI) is_cv <= 1'b1;
                else begin
                    is_cv <= 1'b0;
                    if (nx_last) begin
                        if (is_kind == K_B && keep_en) begin is_kind <= K_CI; is_sec <= c_s0; is_end <= c_s1; end
                        else if (is_kind != K_A) begin is_kind <= K_A; is_sec <= a_s0; is_end <= a_s0 + 15'd511; end
                        else is_on <= 1'b0;
                    end else is_sec <= is_sec + {12'd0, nx_cnt};
                end
            end
            // ---- pop (merge order) and reservations
            pop0_o <= pop && !h_g; pop1_o <= pop && h_g;
            if (pop) gh <= gh + 4'd1;
            gn <= gn + 5'(ch_go) - 5'(pop);
            for (l = 0; l < 2; l = l + 1) begin
                lcnt[l] <= lcnt[l] + LCB'(ch_go && ch_g == 1'(l)) - LCB'(pop && h_g == 1'(l));
                rdyc[l] <= rdyc[l] + LCB'(rdy_q[l]) + LCB'(MUT == 13 && l == 0 && rdy_q[0] && !m13) - LCB'(pop && h_g == 1'(l));
            end
            if (rdy_q[0]) m13 <= 1'b1;
            kcred <= kcred + KCB'(kcr_q) - KCB'(pop && h_kind == K_CV);
            rfree <= rfree - ((pop && h_kind == K_A) ? {2'd0, h_cnt} : 5'd0) + (q_send ? 5'd4 : 5'd0);
            rcnt <= rcnt + (a_arr ? {2'd0, p4_cnt} : 5'd0) - (q_send ? 5'd4 : 5'd0);
            p1_v <= pop; p2_v <= p1_v; p3_v <= p2_v; p4_v <= p3_v;
            if (p3_v && p3_kind == K_A) rw3 <= rw3 + {1'b0, p3_cnt};
            // ---- arrivals: C to KEEP, B to the weights
            kc_ci_o <= p4_v && p4_kind == K_CI; kc_cv_o <= p4_v && p4_kind == K_CV;
            xb_v <= p4_v && p4_kind == K_B;
            if (p4_v && p4_kind == K_B) bj <= bj + 3'd1;
            // ---- query blocks
            qb_v <= q_send;
            if (q_send) qsent <= qsent + 8'd1;
            qcred <= qcred - 3'(q_send) + 3'(qbr_q);
            // ---- frame FSM
            case (st)
                S_IDLE: if (go) begin
                    if (k == 12'd0 || k > 12'd512 || n > 32'd10944 || rank >= 7'd96 || a_base[2:0] != 3'd0 ||
                        (keep_en && c_stride[4:0] != 5'd0)) fault_o <= 1'b1;
                    else begin
                        st <= S_RUN; bad <= 1'b0; sel_done <= 1'b0; wbad <= 1'b0;
                        is_on <= 1'b1; is_cv <= 1'b0; pd_v <= 1'b0; is_kind <= K_B; is_sec <= b_base[17:3];
                        is_end <= 15'((b_base + 18'd31) >> 3);
                        c_s0 <= c_base[17:3]; c_s1 <= 15'((c_base + {6'd0, c_n} - 18'd1) >> 3); a_s0 <= a_base[17:3];
                        cs8 <= c_stride[17:3];
                        rg_req_o <= 1'b1; fs_pend <= 1'b1; qsent <= 8'd0; qcred <= 3'd4; kcred <= KCB'(KFD); bj <= 3'd0;
                        m13 <= 1'b0; kstart_o <= 1'b1; bstart_o <= 1'b1; wstart_o <= 1'b1;
                    end
                end
                S_RUN: begin
                    if (fs_pend) begin
                        fs_pend <= 1'b0;
                        fs_o <= {keep_en, cand_en, k[9:0], n[13:0], rank, pos, 4'd0, 32'd0, 1'b1};
                    end
                    if (rd_idle) rg_req_o <= 1'b0;
                    if (bad) begin st <= S_ABORT; fault_o <= 1'b1; wabort_o <= 1'b1; end
                    else if (sel_done && b_idle_q && qsent == 8'd128 && rd_idle && !xb_v) begin
                        st <= S_FLUSH; flush_o <= 1'b1;
                    end
                end
                S_FLUSH: if (w_done_q) begin st <= S_IDLE; done_o <= 1'b1; rg_req_o <= 1'b0; end
                // fault: the read group is released only when every descriptor already sent has been issued and has
                // landed (the lane leaves issue from their own logs; no request may follow the release)
                default: if (lcnt[0] == rdyc[0] && lcnt[1] == rdyc[1] && dsc_v == 2'd0 && rdy_q == 2'd0) begin
                    st <= S_IDLE; rg_req_o <= 1'b0;
                end
            endcase
        end
    end
endmodule
`default_nettype wire
