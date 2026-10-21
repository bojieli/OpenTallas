`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-IDX3R (10-20, tree MU.BAL.SX.3, LEAD9 decision 13:55 option (c)): dsdv_idx_rg3, the NON-INLINE paired index
// reader of the S81-DV p4l-MU die (mu7, 122 frames).  Same reader as dsdv_idx_rg2 (S81-L20RD3 69e03df35: walker, slot
// table, landing, hardened-slice engine, assembler, fail-closed gather slots, chains, beat format, MUT 1/3/4/6/7) --
// generated from it by results/rtl/s81_idx3r_1020/mk_rg3.py, which rewrites ONLY the HBM faces -- but placed in a PHY
// corner strip as a static-slot CLIENT of the two controllers of its pair (dsfd_ctrl_rg3), instead of in-line on the
// svc_rs <-> controller rq / rd links (those stay 682 / 562 b straight down, unchanged).
//
// HBM faces (u = 2 r + q: region r of the pair, pseudo-channel parity q; one lane a PC, no lane sharing, no arbiter):
//   rqo[46u +: 46] = {tag10, len 4, addr 30, sl, v}   request lane -> controller r, PC q (read-only command)
//                    tag10 = tag[14:5] of the reader tag {2'b11, g, slot 3, cell 4, sc, slot[3], 5'b0}
//                    sl    = the reader window (job active: header -> window done), the controller's compiled reader-
//                            slot calendar: inside it the controller feeds this lane's requests into the PC, svc_rs
//                            never issues there (a slice word in a reader slot is a controller fault)
//   rri[272u +: 272] = {data 256, tag10, beat 4, pop, v}   response lane <- controller r, PC q
//                    v / data / tag10 / beat: a response beat in the reader-tag range (tag[16:15] = 2'b11)
//                    pop: one request of this lane left the controller's landing FIFO (dsfd_ctrl_rg3 RFD entries)
// BUDGET: own_n = requests issued - pops seen; a request issues only while own_n < DQR (= the controller's RFD).  The
// pop returns over the fixed lane latency, so own_n >= the FIFO occupancy: the FIFO never overflows (static, no
// credits on the lane: the HBM boundary's elastic take stays inside the controller, owner 10-14/15).
// Latency vs dsdv_idx_rg2 (fixed per pair, set by the die's relay stations s each way): request +s + 3 controller
// edges, response +s + 1; absorbed by the run-ahead window T0 (static schedule; priced in lanes/S81-IDX3R.md).
// MUT (bench negative controls): 1 / 3 / 4 / 6 / 7 as dsdv_idx_rg2; 2 = budget ignored (controller FIFO overflow
// must raise the controller fault), 5 = response beats of odd cells lost (slot never ready: fail-closed late words).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_idx_rg3 #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,         // outstanding requests a PC lane: dsfd_ctrl_rg3 RFD (reader landing FIFO)
    parameter integer IQD = 512,        // items in flight (item queue macro: <= 1024)
    parameter integer SQD = 256,        // keys in the engine + scores waiting for the assembler (<= 1024)
    parameter integer LFD = 256,        // candidate-list words (gather)
    parameter integer EL = 124          // engine latency: key presented -> score valid (chunk 106 + tail 18 edges)
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,           // region A = sid (even), region B = sid + 1
    input  wire [512:0]  qi,
    output reg  [512:0]  qo,
    input  wire [275:0]  si,
    output reg  [275:0]  so,
    output reg  [183:0]  rqo,           // 4 x 46-b request lanes, u = 2 r + q: {tag10, len 4, addr 30, sl, v}
    input  wire [1087:0] rri,           // 4 x 272-b response lanes, u = 2 r + q: {data 256, tag10, beat 4, pop, v}
    output reg  [9:0]    st
);
    initial if (IQD > 1024 || SQD > 1024 || LFD > 1024 || DQR > 31 || DQR < 1) $fatal(1, "dsdv_idx_rg3: queue / budget sizes");
    localparam integer OW = 6;          // own_n width (DQR <= 31)
    localparam integer LFW = $clog2(LFD);
    localparam integer IW = 35;         // item {u 2, slot 4, cell 4, w 16, lane 4, lw, v, idx 3}
    localparam integer MW = 22;         // metadata {w 16, lane 4, lw, v}
    localparam integer RQD = 8, JW = 43, LG = 16;  // job entry {g [42], slot [41:38], cell [37:34], kc [33:30], base [29:0]}

    // ================================================================== reset: 2-flop landing + 2-level relay forest
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire [1:0]  r0;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    wire [39:0] rl;
    ot_rst_relay #(.REGIONS(20), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0[0]), .rst_n(rl[19:0]));
    ot_rst_relay #(.REGIONS(20), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r2 (.clk(ck), .rst_n_in(r0[1]), .rst_n(rl[39:20]));
    reg  [7:0] fc;                                  // sticky fault causes
    wire       fault = |fc;
    reg  [3:0] me;                                  // region A id (strap)
    always @(posedge ck) me <= {sid[3:1], 1'b0};

    // ================================================================== pin registers
    reg [512:0] qr;
    reg [275:0] sr;
    reg [3:0][271:0] rrr;                           // response lanes at the pin
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin qr[0] <= 1'b0; sr[0] <= 1'b0; end
        else begin qr[0] <= qi[0]; sr[0] <= si[0]; end
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin rrr[0][1:0] <= 2'd0; rrr[1][1:0] <= 2'd0; rrr[2][1:0] <= 2'd0; rrr[3][1:0] <= 2'd0; end
        else begin
            rrr[0][1:0] <= rri[1:0]; rrr[1][1:0] <= rri[273:272]; rrr[2][1:0] <= rri[545:544]; rrr[3][1:0] <= rri[817:816];
        end
    always @(posedge ck) begin
        qr[512:1] <= qi[512:1]; sr[275:1] <= si[275:1];
        rrr[0][271:2] <= rri[271:2]; rrr[1][271:2] <= rri[543:274]; rrr[2][271:2] <= rri[815:546]; rrr[3][271:2] <= rri[1087:818];
    end
    // pin copies: pop (budget counter + copies), query valid (payload counters)
    (* keep = "true" *) reg [3:0]  rkc;
    (* keep = "true" *) reg [1:0]  qvk;
    always @(posedge ck) begin
        rkc <= {rri[817], rri[545], rri[273], rri[1]};
        qvk <= {2{qi[0]}};
    end
    wire [3:0] rk_in = {rrr[3][1], rrr[2][1], rrr[1][1], rrr[0][1]};   // a request left the controller's landing FIFO
    wire [3:0] rv_in = {rrr[3][0], rrr[2][0], rrr[1][0], rrr[0][0]};
    wire [3:0][16:0] rt;
    wire [3:0][3:0]  rb;
    wire [3:0][255:0] rdd;
    genvar gu;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_rdw
        assign rt[gu]  = {2'b11, rrr[gu][15:6], 5'd0};   // the controller's reader-tag range: {11, tag10, 00000}
        assign rb[gu]  = rrr[gu][5:2];
        assign rdd[gu] = rrr[gu][271:16];
    end endgenerate
    // every lane response is this reader's (the controller's tag demux); MUT 5: responses of tag bit 0 of cell lost
    wire [3:0] mine;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_mine
        assign mine[gu] = rv_in[gu] && !(MUT == 5 && rt[gu][7]);
    end endgenerate

    // ================================================================== frame parser (query chain)
    reg        infr, isj, act;
    reg [11:0] left, pw;
    wire       q_v = qr[0];
    wire [511:0] q_d = qr[512:1];
    wire       is_h = q_v && !infr;
    wire       is_p = q_v && infr;
    wire       hdr_job = is_h && (q_d[511:508] == 4'd4 || q_d[511:508] == 4'd8);
    wire       pay_job = is_p && isj;
    wire       end_w = pay_job && left == 12'd1;
    reg        wdone_p;
    // a new job's header: qo holds it one edge after qr; kept copies latch its fields (+1), derived values (+2), start (+3)
    (* keep = "true" *) reg [14:0] hen;
    (* keep = "true" *) reg [5:0]  hj1;
    (* keep = "true" *) reg [11:0] hj2;
    (* keep = "true" *) reg [7:0]  hj3;
    (* keep = "true" *) reg [4:0]  hj4;
    reg        hbad1;
    always @(posedge ck) begin
        if (qvk[0] && !infr) left <= q_d[491:480]; else if (qvk[0]) left <= left - 12'd1;
        if (qvk[1] && !infr) pw <= 12'd0; else if (qvk[1]) pw <= pw + 12'd1;
    end
    // the copies carry no reset: during reset qr[0] is held 0, so they settle to 0 within 3 edges of the reset
    always @(posedge ck) begin hen <= {15{hdr_job && !act}}; hj1 <= {6{hdr_job && !act}}; hj2 <= {12{hj1[0]}}; hj3 <= {8{hj2[0]}}; hj4 <= {5{hj3[0]}}; end
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) begin infr <= 1'b0; isj <= 1'b0; act <= 1'b0; hbad1 <= 1'b0; end
        else begin
            hbad1 <= hdr_job && act;
            if (is_h) begin
                infr <= q_d[491:480] != 12'd0; isj <= hdr_job;
                if (hdr_job && !act) act <= 1'b1;
            end else if (is_p && left == 12'd1) infr <= 1'b0;
            if (wdone_p) act <= 1'b0;
        end
    // job fields (from qo); jn / jb twice (one copy for the derived values, one for the walker)
    reg        gat; reg [19:0] jb, jbd, jbe; reg [20:0] jn, jnd, jne; reg [9:0] jk; reg [29:0] kb; reg [15:0] t0; reg [3:0] pp;
    reg [2:0]  ik, om; reg [7:0] tg; reg [11:0] hlen;
    (* keep = "true" *) reg [7:0] gatd;             // gather bit copies for the derived values (8 bits a copy)
    always @(posedge ck) begin
        if (hen[0])  begin gat <= qo[512]; jb[14:0] <= qo[15:1]; end
        if (hen[1])  begin jb[19:15] <= qo[20:16]; jk <= qo[51:42]; end
        if (hen[2])  jn[15:0] <= qo[36:21];
        if (hen[3])  begin jn[20:16] <= qo[41:37]; pp <= qo[101:98]; ik <= qo[104:102]; om <= qo[107:105]; end
        if (hen[4])  jbd[15:0] <= qo[16:1];
        if (hen[5])  begin jbd[19:16] <= qo[20:17]; tg <= qo[503:496]; end
        if (hen[6])  jnd[15:0] <= qo[36:21];
        if (hen[7])  begin jnd[20:16] <= qo[41:37]; gatd <= {8{qo[512]}}; end
        if (hen[8])  kb[15:0] <= qo[67:52];
        if (hen[9])  kb[29:16] <= qo[81:68];
        if (hen[10]) t0 <= qo[97:82];
        if (hen[11]) hlen <= qo[492:481];
        if (hen[12]) jbe[15:0] <= qo[16:1];
        if (hen[13]) begin jbe[19:16] <= qo[20:17]; jne[11:0] <= qo[32:21]; end
        if (hen[14]) jne[20:12] <= qo[41:33];
    end
    (* keep = "true" *) reg [7:0] gatk;              // gather-mode select copies (data muxes)
    always @(posedge ck) gatk <= {8{gat}};
    // derived (from the second copy of the fields)
    reg [15:0] j0, j1, nw, nlw;
    reg [20:0] je;                                  // scan: last position B + N - 1
    reg [4:0]  lcnt;                                // gather: entries of the last list word (1..16)
    reg        spec_bad;
    reg [20:0] ds_e, ds_e2, ds_n1, ds_n15;          // stage 1 sums (+2): B + N - 1 (x2), N + 1, N + 15
    always @(posedge ck) begin
        if (hj2[0]) ds_e[15:0]  <= 16'(21'(jbd) + jnd - 21'd1);
        if (hj2[11]) ds_e[20:16] <= 5'((21'(jbd) + jnd - 21'd1) >> 16);
        if (hj2[1]) begin spec_bad <= pp < 4'd2 || jn == 21'd0 || jk > 10'd512 || t0 < 16'd4;
                          lcnt <= (jn[3:0] == 4'd0) ? 5'd16 : {1'b0, jn[3:0]}; end
        if (hj2[2]) ds_e2[15:0] <= 16'(21'(jbe) + jne - 21'd1);
        if (hj2[3]) ds_e2[20:16] <= 5'((21'(jbe) + jne - 21'd1) >> 16);
        if (hj2[4]) ds_n1[15:0] <= 16'(jne + 21'd1);
        if (hj2[5]) begin ds_n1[20:16] <= 5'((jne + 21'd1) >> 16); ds_n15[20:16] <= 5'((jn + 21'd15) >> 16); end
        if (hj2[6]) ds_n15[15:0] <= 16'(jn + 21'd15);
        // stage 2 (+3)
        if (hj3[0]) je[15:0] <= ds_e[15:0];
        if (hj3[1]) je[20:16] <= ds_e[20:16];
        if (hj3[2]) j0 <= gatd[0] ? 16'd0 : 16'(jbd >> 4);
        if (hj3[3]) nlw <= gatd[1] ? 16'(ds_n15 >> 4) : 16'd0;
        if (hj3[4]) begin j1[7:0]  <= gatd[2] ? 8'((ds_n1 >> 1) - 21'd1) : 8'(ds_e2 >> 4);
                          j1[15:8] <= gatd[4] ? 8'(((ds_n1 >> 1) - 21'd1) >> 8) : 8'(ds_e2 >> 12); end
        if (hj3[5]) begin nw[7:0]  <= gatd[3] ? 8'(ds_n1 >> 1) : 8'((ds_e2 >> 4) - 21'(jbe >> 4) + 21'd1);
                          nw[15:8] <= gatd[5] ? 8'(ds_n1 >> 9) : 8'(((ds_e2 >> 4) - 21'(jbe >> 4) + 21'd1) >> 8); end
    end

    // ================================================================== query load: the chain registers ARE the load data
    // at the edge where qr holds head h's second word (pw odd), qo holds its first word (codes): ql_c <= qo is an
    // unconditional register stage, valid / head / scales registered on the same edge (no payload-stage skew)
    reg         ql_v;
    reg  [7:0]  ql_h;
    reg  [511:0] ql_c;
    reg  [47:0] ql_sw;
    reg  [2:0]  qset;
    reg         q_done;
    reg  [1:0]  qst;
    always @(posedge ck) begin ql_c <= qo[512:1]; ql_sw <= q_d[47:0]; ql_h <= 8'(pw[6:1]); end
    always @(posedge ck or negedge rl[3])
        if (!rl[3]) begin ql_v <= 1'b0; qset <= 3'd0; q_done <= 1'b0; qst <= 2'd0; qo[0] <= 1'b0; end
        else begin
            ql_v <= pay_job && pw < 12'd64 && pw[0];
            if (hj1[0]) q_done <= 1'b0;
            if (ql_v && ql_h == 8'd31) qset <= 3'd5;
            else if (qset != 0) begin qset <= qset - 3'd1; if (qset == 3'd1) q_done <= 1'b1; end
            if (ql_v) qst <= 2'd3; else if (qst != 0) qst <= qst - 2'd1;
            qo[0] <= qr[0];
        end
    always @(posedge ck) qo[512:1] <= qr[512:1];

    // ================================================================== list memory (gather): written as it arrives
    wire        lf_push = pay_job && pw >= 12'd64;
    reg  [LFW:0] lf_wn, lf_rn;
    reg          lfr_e, lfd1, lfd2;
    reg  [LFW-1:0] lfr_a;
    wire [511:0] lf_q;
    genvar gh;
    generate for (gh = 0; gh < 2; gh = gh + 1) begin : g_lm
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mem (
            .ck(ck), .re(lfr_e), .ra(10'(lfr_a)), .rd(lf_q[256 * gh +: 256]),
            .we(lf_push), .wa(10'(lf_wn[LFW-1:0])), .wd(q_d[256 * gh +: 256]));
    end endgenerate

    // ================================================================== window clock
    reg        ended, wdone;
    reg [19:0] tc;
    always @(posedge ck) if (end_w && act) tc <= 20'd0; else if (ended && !wdone) tc <= tc + 20'd1;
    always @(posedge ck or negedge rl[3])
        if (!rl[3]) ended <= 1'b0;
        else if (hj1[1]) ended <= 1'b0;
        else if (end_w && act) ended <= 1'b1;

    // ================================================================== HBM faces: owner FIFOs, issuers, rd filter
    // read job queue per parity q (shared by both regions' issuers): {g, slot 3, cell 4, kc 4, base = KB + 34 n}
    reg  [1:0][RQD-1:0][JW-1:0] jq;
    reg  [1:0][RQD-1:0] jw_oh;                      // write pointer (one-hot) per parity
    reg  [1:0][3:0]     jw_n;                       // entries written (mod 16)
    (* keep = "true" *) reg [1:0][RQD-1:0] jwe_a, jwe_b, jwe_c;   // registered entry write enables (entry thirds)
    reg  [23:0]         jpd;                        // decision edge: {g, slot 4, cell, n 11, kc}
    reg  [JW-1:0]       jpd1;                       // write edge: {g, slot, cell, kc, base}
    (* keep = "true" *) reg [3:0][RQD-1:0] jra, jrb;   // read pointer (one-hot) per PC, 2 copies (entry halves)
    reg  [3:0][3:0]     jr_n;
    reg  [3:0][3:0]     jkk;                        // next request of the head job
    reg  [3:0]          jz;                         // jkk == 0
    reg  [3:0][5:0]     kos;                        // 4 (jkk - 1)
    reg  [3:0][3:0]     kcl;                        // 2 (jkk - 1)
    (* keep = "true" *) reg [3:0] ivk0, ivk3, ivk4;   // i_v copies [copy][u]
    (* keep = "true" *) reg [3:0] cnk0, cnk3, cnk4;   // own_n < DQR copies
    reg  [3:0][29:0]    i_a;
    reg  [3:0][3:0]     i_l;
    reg  [3:0][16:0]    i_t;
    reg  [3:0][OW-1:0]  own_n;                      // requests issued on the lane and not yet popped at the controller
    // issue: a request leaves on its own lane (no slice word to share the lane with: the controller merges the lanes
    // into its PCs in the static reader slots), within the budget; one copy a consumer group.  MUT 2: budget ignored.
    wire [3:0] cb0 = (MUT == 2) ? 4'hF : cnk0, cb3 = (MUT == 2) ? 4'hF : cnk3, cb4 = (MUT == 2) ? 4'hF : cnk4;
    wire [3:0] is0 = ivk0 & cb0;                    // rq valid, own_n
    wire [3:0] is3 = ivk3 & cb3;                    // issuer advance (k, count)
    wire [3:0] is4 = ivk4 & cb4;                    // head read pointers
    // head job of each PC (one-hot select)
    wire [3:0][JW-1:0] jh;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_jh
        reg [JW-1:0] x;
        integer e_;
        always @* begin
            x = '0;
            for (e_ = 0; e_ < RQD; e_ = e_ + 1) begin
                x[21:0]  = x[21:0]  | ({22{jra[gu][e_]}} & jq[gu % 2][e_][21:0]);
                x[42:22] = x[42:22] | ({21{jrb[gu][e_]}} & jq[gu % 2][e_][42:22]);
            end
        end
        assign jh[gu] = x;
    end endgenerate
    // request address = head base + offset: structured Kogge-Stone add (log-depth, bounded fanout)
    wire [3:0][29:0] ia_s;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_ia
        wire [5:0] off_ = jh[gu][JW-1] ? (jz[gu] ? {1'b0, jh[gu][33:30], 1'b0} : 6'd32 + {5'd0, jh[gu][33]})
                                       : (jz[gu] ? 6'd32 : kos[gu]);
        wire co_unused;
        ot_hdc_ksadd_k #(.W(30)) u_ia (.a(jh[gu][29:0]), .b({24'd0, off_}), .cin(1'b0), .s(ia_s[gu]), .cout(co_unused));
    end endgenerate
    // request registers: recomputed every edge from the head job (no load enable); an issue drops i_v for one edge.
    // One adder: address = kb + 34 n + offset(kind, k)
    integer u;
    always @(posedge ck) begin
        for (u = 0; u < 4; u = u + 1) begin : g_req
            reg jg_; reg [3:0] js_; reg [3:0] jc_, jkc_; reg [29:0] jba; reg [5:0] off; reg [3:0] ln_; reg [3:0] tc_; reg sc_;
            {jg_, js_, jc_, jkc_, jba} = jh[u];
            // k-derived terms are registers (jz: k == 0, kos: scan offset 4 (k - 1), kcl: scan cell 2 (k - 1))
            if (!jg_) begin                         // scan group: k 0 = scales (2 sectors), k 1..8 = 2 cells (4 sectors)
                off = jz[u] ? 6'd32 : kos[u];
                ln_ = jz[u] ? 4'd2 : 4'd4;  tc_ = jz[u] ? 4'd0 : kcl[u]; sc_ = jz[u];
            end else begin                          // gather key: k 0 = 2 code sectors, k 1 = its scale sector
                off = jz[u] ? {1'b0, jkc_, 1'b0} : 6'd32 + {5'd0, jkc_[3]};
                ln_ = jz[u] ? 4'd2 : 4'd1;  tc_ = jc_; sc_ = !jz[u];
            end
            i_a[u] <= ia_s[u];
            i_l[u] <= ln_;
            i_t[u] <= {2'b11, jg_, js_[2:0], tc_, sc_, js_[3], 5'd0};
        end
    end
    always @(posedge ck or negedge rl[4])
        if (!rl[4]) begin ivk0 <= 4'd0; ivk3 <= 4'd0; ivk4 <= 4'd0; end
        else begin : g_iv
            reg [3:0] nz;
            for (u = 0; u < 4; u = u + 1) nz[u] = jw_n[u % 2] != jr_n[u];
            ivk0 <= nz & ~is0; ivk3 <= nz & ~is3; ivk4 <= nz & ~is4;
        end
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_iss
        always @(posedge ck or negedge rl[5 + gu])
            if (!rl[5 + gu]) begin jkk[gu] <= 4'd0; jz[gu] <= 1'b1; kos[gu] <= 6'd0; kcl[gu] <= 4'd0; jr_n[gu] <= 4'd0;
                                   jra[gu] <= RQD'(1); jrb[gu] <= RQD'(1); end
            else begin
                if (is3[gu]) begin
                    if (jkk[gu] == (jh[gu][JW-1] ? 4'd1 : 4'd8)) begin
                        jkk[gu] <= 4'd0; jz[gu] <= 1'b1; kos[gu] <= 6'd0; kcl[gu] <= 4'd0; jr_n[gu] <= jr_n[gu] + 4'd1;
                    end else begin
                        jkk[gu] <= jkk[gu] + 4'd1; jz[gu] <= 1'b0;
                        kos[gu] <= jz[gu] ? 6'd0 : kos[gu] + 6'd4; kcl[gu] <= jz[gu] ? 4'd0 : kcl[gu] + 4'd2;
                    end
                end
                if (is4[gu] && jkk[gu] == (jh[gu][JW-1] ? 4'd1 : 4'd8)) begin
                    jra[gu] <= {jra[gu][RQD-2:0], jra[gu][RQD-1]}; jrb[gu] <= {jrb[gu][RQD-2:0], jrb[gu][RQD-1]};
                end
            end
        // budget: own_n = issued - popped (the pop returns on the response lane, after the fixed round trip, so own_n
        // >= the controller landing FIFO's occupancy for this lane: the FIFO can never overflow)
        always @(posedge ck or negedge rl[9 + gu])
            if (!rl[9 + gu]) own_n[gu] <= '0;
            else own_n[gu] <= own_n[gu] + (is0[gu] ? OW'(1) : OW'(0)) - (rkc[gu] ? OW'(1) : OW'(0));
        always @(posedge ck or negedge rl[13 + gu / 2])
            if (!rl[13 + gu / 2]) begin cnk0[gu] <= 1'b1; cnk3[gu] <= 1'b1; cnk4[gu] <= 1'b1; end
            else begin : g_cn
                reg [OW-1:0] nx;
                nx = own_n[gu] + (is0[gu] ? OW'(1) : OW'(0)) - (rk_in[gu] ? OW'(1) : OW'(0));
                cnk0[gu] <= nx < OW'(DQR); cnk3[gu] <= nx < OW'(DQR); cnk4[gu] <= nx < OW'(DQR);
            end
    end endgenerate
    // request lanes out: {tag10, len, addr, sl, v}; sl = the reader's window (job active: header -> window done),
    // the compiled reader slot calendar of the controller (svc_rs never issues on the pair's PCs inside it)
    (* keep = "true" *) reg [3:0] slk;
    always @(posedge ck or negedge rl[15])
        if (!rl[15]) slk <= 4'd0; else slk <= {4{act}};
    always @(posedge ck or negedge rl[15])
        if (!rl[15]) begin rqo[0] <= 1'b0; rqo[46] <= 1'b0; rqo[92] <= 1'b0; rqo[138] <= 1'b0; end
        else begin rqo[0] <= is0[0]; rqo[46] <= is0[1]; rqo[92] <= is0[2]; rqo[138] <= is0[3]; end
    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin
        rqo[46 * u + 1] <= slk[u];
        rqo[46 * u + 2 +: 44] <= {i_t[u][14:5], i_l[u], i_a[u]};
    end

    // ================================================================== slot table (per parity q, shared by A and B)
    // Each region owns an independent resettable word. Packed outer arrays
    // with dynamic bit writes make Yosys preserve the other region through an
    // asynchronous data-load, which ASAP7 cannot implement.
    reg [LG-1:0]          sb [0:1], scl [0:1];   // busy / closed, local reset
    reg [1:0][LG-1:0]     srdy;                 // both regions' beats landed
    reg [1:0][LG-1:0][4:0] sni, snc;               // items a region allocated / consumed (B items counted)
    reg [1:0][LG-1:0][5:0] sne;                    // beats expected a region
    reg [1:0][LG-1:0][5:0] snr0, snr1;             // beats received, region A / B
    reg [1:0][3:0]         sa;                     // next slot to allocate
    reg [1:0][3:0]         sop;                    // open gather slot
    reg [1:0]              sopen;
    reg [1:0][4:0]         socnt;                  // keys in the open gather slot

    // ================================================================== walker
    // ws: 0 idle, 1 scan group setup, 2 scan alloc, 3 scan items, 4 gather list word, 5 gather blocks, 6 done
    reg  [2:0]  ws;
    reg  [11:0] gg;                                 // scan group (16 words)
    reg  [3:0]  gk_hg, gk_cs, gk_ce;                // group constants: h(group), first / last in-range cell
    reg         gk_fg, gk_lg;
    reg  [15:0] gk_wb;                              // {gg, 0} - j0
    reg  [4:0]  gk_cnt;                             // in-range words of the group
    reg         wq, wr;
    reg  [3:0]  wsl;
    reg  [3:0]  wc;
    reg  [LFW:0] gw;                                // gather list word
    reg  [15:0] gm;                                 // owned entries of the list word not yet taken
    reg         gsv, gph;                           // a selected block waits; phase (0 decide / item A, 1 item B)
    (* keep = "true" *) reg [2:0] gsvk, gphk;       // copies for the selection enables (block low / mask / block high)
    reg  [3:0]  gse;
    reg  [16:0] gsb;
    reg  [3:0]  gsl; reg [3:0] gcl;
    reg         gnx;
    reg         ipush;
    reg  [IW-1:0] ipd_s, ipd_g;
    reg  [10:0] iq_n;
    // registered walker decisions (update stage): copies [0] slot table + pointers, [1] sni / sne, [2] snr, [3] snc,
    // [4] job queue
    (* keep = "true" *) reg [4:0] u_al;             // scan allocation
    (* keep = "true" *) reg [4:0] u_gt;             // gather take
    reg         u_need, u_q, u_full, u_cl;
    (* keep = "true" *) reg [4:0] uqk;              // decision parity copies (same groups as u_al / u_gt)
    reg  [4:0]  u_cnt;
    // landing responses (registered one edge after the pin)
    reg  [3:0]  lw_v, lw_h1;
    reg  [3:0][9:0] lw_a;
    reg  [3:0][255:0] lw_d;
    reg  [3:0][3:0] lw_sl;
    reg  [1:0]  cons_v; reg [1:0][3:0] cons_s;      // B items consumed (parity, slot)
    reg  [7:0]  fw;
    reg         iq_room32, iq_room2;
    reg  [1:0]  jq_room;
    wire [1:0]  sfree = {!sb[1][sa[1]], !sb[0][sa[0]]};
    // gather ownership of the fetched list word (block b of entry e, word j = b >> 1, x = A ^ h(j); A and B own it when
    // x[3] == b[0]) and the entry is inside the list
    wire [15:0] l_own;
    genvar ge;
    generate for (ge = 0; ge < 16; ge = ge + 1) begin : g_lo
        wire [16:0] bb = lf_q[32 * ge +: 17];
        wire [15:0] jj = bb[16:1];
        wire [3:0]  x = me ^ jj[3:0] ^ jj[7:4] ^ jj[11:8] ^ jj[15:12];
        assign l_own[ge] = (x[3] == bb[0]) && ((16'(gw) != nlw - 16'd1) || (5'(ge) < lcnt));
    end endgenerate
    wire [15:0] g_oh = gm & (~gm + 16'd1);          // lowest owned entry
    reg  [16:0] g_b; reg [3:0] g_e;
    integer e2;
    always @* begin
        g_b = 17'd0; g_e = 4'd0;
        for (e2 = 0; e2 < 16; e2 = e2 + 1) begin g_b = g_b | ({17{g_oh[e2]}} & lf_q[32 * e2 +: 17]); g_e = g_e | ({4{g_oh[e2]}} & 4'(e2)); end
    end
    wire [15:0] g_m1 = gm & ~g_oh;
    wire [15:0] gs_j = gsb[16:1];
    wire        gs_q = gs_j[4];
    wire [3:0]  gs_x = me ^ gs_j[3:0] ^ gs_j[7:4] ^ gs_j[11:8] ^ gs_j[15:12];
    wire        g_need = !sopen[gs_q] || socnt[gs_q] == 5'd16;
    wire [3:0]  g_sl = g_need ? sa[gs_q] : sop[gs_q];
    wire [3:0]  g_cl = g_need ? 4'd0 : socnt[gs_q][3:0];
    wire        g_take = ws == 3'd5 && gsv && !gph && (g_need ? sfree[gs_q] : 1'b1) && iq_room2 && jq_room[gs_q];
    wire        s_alloc = ws == 3'd2 && sfree[gg[0]] && iq_room32 && jq_room[gg[0]];
    wire        l_rd = ws == 3'd4 && 16'(gw) < nlw && !lfr_e && !lfd1 && !lfd2 && lf_rn == gw && lf_rn < lf_wn;
    integer q, s;
    // walker control (reset): state, phases, pushes, list read, decisions
    always @(posedge ck or negedge rl[16])
        if (!rl[16]) begin
            ws <= 3'd0; gsv <= 1'b0; gph <= 1'b0; ipush <= 1'b0; lfr_e <= 1'b0; lfd1 <= 1'b0; lfd2 <= 1'b0;
            u_al <= 5'd0; u_gt <= 5'd0; u_cl <= 1'b0;
        end else begin
            ipush <= 1'b0; u_al <= 5'd0; u_gt <= 5'd0; u_cl <= 1'b0;
            lfr_e <= l_rd; lfd1 <= lfr_e; lfd2 <= lfd1;
            if (hj4[0]) begin ws <= gat ? 3'd4 : 3'd1; gsv <= 1'b0; gph <= 1'b0; end
            else case (ws)
                3'd1: ws <= 3'd2;
                3'd2: if (s_alloc) begin u_al <= 5'h1F; ws <= 3'd3; end
                3'd3: begin
                    ipush <= 1'b1;
                    if (wr && wc == gk_ce) ws <= gk_lg ? 3'd6 : 3'd1;
                end
                3'd4: begin
                    if (16'(gw) >= nlw) begin ws <= 3'd6; u_cl <= 1'b1; end
                    else if (lfd2) ws <= 3'd5;
                end
                3'd5: begin
                    if (!gsv) begin                                    // select the first block of the word
                        if (gm == 16'd0) ws <= 3'd4; else gsv <= 1'b1;
                    end else if (!gph) begin                           // decide: take (item A) or stall (close open slots)
                        if (g_take) begin u_gt <= 5'h1F; ipush <= 1'b1; gph <= 1'b1; end
                        else u_cl <= 1'b1;
                    end else begin                                     // item B + select the next block
                        ipush <= 1'b1; gph <= 1'b0;
                        if (gm == 16'd0) begin gsv <= 1'b0; ws <= 3'd4; end
                    end
                end
                default: ;
            endcase
            if (wdone_p) ws <= 3'd0;
        end
    always @(posedge ck or negedge rl[16])
        if (!rl[16]) begin gsvk <= 3'b000; gphk <= 3'b000; end
        else begin : g_gk
            reg nsv, nph;
            nsv = gsv; nph = gph;
            if (hj4[0]) begin nsv = 1'b0; nph = 1'b0; end
            else if (ws == 3'd5) begin
                if (!gsv) begin if (gm != 16'd0) nsv = 1'b1; end
                else if (!gph) begin if (g_take) nph = 1'b1; end
                else begin nph = 1'b0; if (gm == 16'd0) nsv = 1'b0; end
            end
            gsvk <= {3{nsv}}; gphk <= {3{nph}};
        end
    // walker data (no reset: set at the job start / the decision edges)
    always @(posedge ck) begin
        if (hj4[1]) gg <= j0[15:4];
        if (hj4[2]) lf_rn <= '0; else if (l_rd) lf_rn <= lf_rn + 1'b1;
        lfr_a <= lf_rn[LFW-1:0];
        if (hj4[3]) gw <= '0;
        else if (ws == 3'd5 && ((!gsv && gm == 16'd0) || (gsv && gph && gm == 16'd0))) gw <= gw + 1'b1;
        if (hj4[4]) gm <= 16'd0;
        else if (ws == 3'd4 && lfd2) gm <= l_own;
        else if (ws == 3'd5 && ((!gsvk[1] && gm != 16'd0) || (gsvk[1] && gphk[1]))) gm <= g_m1;
        if (ws == 3'd2) begin wq <= gg[0]; wsl <= sa[gg[0]]; wc <= gk_cs; wr <= 1'b0; end
        // decision details for the update stage (unconditional: the update stage reads them one edge after the decision)
        u_q <= gatk[6] ? gs_q : gg[0]; uqk <= {5{gatk[7] ? gs_q : gg[0]}}; u_cnt <= gk_cnt;
        u_need <= g_need; u_full <= socnt[gs_q] == 5'd15 && !g_need; gsl <= g_sl; gcl <= g_cl;
        if (ws == 3'd3) begin
            wr <= !wr;
            if (wr) begin wc <= wc + 4'd1; if (wc == gk_ce && !gk_lg) gg <= gg + 12'd1; end
        end
        // gather selection (first block of a word, or the next one during item B)
        if (ws == 3'd5 && ((!gsvk[0] && gm != 16'd0) || (gsvk[0] && gphk[0]))) gsb[10:0] <= g_b[10:0];
        if (ws == 3'd5 && ((!gsvk[2] && gm != 16'd0) || (gsvk[2] && gphk[2]))) begin
            gsb[16:11] <= g_b[16:11]; gse <= g_e; gnx <= (g_e != 4'd15) && g_m1[g_e + 4'd1];
        end
        // job queue entry (written two edges later by the registered enables)
        // entry {g [23], slot [22:19], cell [18:15], n [14:4], kc [3:0]}
        jpd[11:0]  <= gatk[0] ? {gs_j[12:5], gs_j[3:0]} : {gg[8:1], 4'd0};
        jpd[23:12] <= gatk[3] ? {1'b1, g_sl, g_cl, gs_j[15:13]} : {1'b0, sa[gg[0]], 4'd0, gg[11:9]};
        // items: scan {u, slot, cell, w, lane, lw, v, idx}; gather A / B
        ipd_s <= {wr, wq, wsl, wc, gk_wb + 16'(wc), ({me[3:1], wr} ^ gk_hg ^ wc) ^ ((MUT == 1) ? 4'd1 : 4'd0),
                  wr, !((gk_fg && wc == gk_cs && (({me[3:1], wr} ^ gk_hg ^ wc) < jb[3:0])) ||
                        (gk_lg && wc == gk_ce && (({me[3:1], wr} ^ gk_hg ^ wc) > je[3:0]))),
                  wc[2:0] ^ ((MUT == 3) ? 3'd1 : 3'd0)};
        ipd_g <= {gph, gs_q, gph ? gsl : g_sl, gph ? gcl : g_cl, 16'({gw, gse[3:1]}),
                  {gse[0], gs_x[2:0] ^ {2'b00, gph} ^ ((MUT == 1) ? 3'd1 : 3'd0)}, gph && (gse[0] || !gnx), 1'b1,
                  gs_j[2:0] ^ ((MUT == 3) ? 3'd1 : 3'd0)};
    end
    // group constants (unconditional, from gg)
    always @(posedge ck) begin
        gk_hg <= gg[3:0] ^ gg[7:4] ^ gg[11:8];
        gk_fg <= gg == j0[15:4]; gk_lg <= gg == j1[15:4];
        gk_cs <= (gg == j0[15:4]) ? j0[3:0] : 4'd0;
        gk_ce <= (gg == j1[15:4]) ? j1[3:0] : 4'd15;
        gk_wb <= {gg, 4'd0} - j0;
        gk_cnt <= 5'((gg == j1[15:4]) ? j1[3:0] : 4'd15) - 5'((gg == j0[15:4]) ? j0[3:0] : 4'd0) + 5'd1;
    end
    // job queues: enables registered at the update stage (from decision copy 4), entry written on the next edge
    always @(posedge ck or negedge rl[17])
        if (!rl[17]) jwe_a <= '0;
        else for (q = 0; q < 2; q = q + 1) jwe_a[q] <= ((u_al[4] || u_gt[4]) && uqk[4] == q[0]) ? jw_oh[q] : RQD'(0);
    // copies b / c carry no reset (a stray power-on write lands in an entry no issuer reads before its real write)
    always @(posedge ck) for (q = 0; q < 2; q = q + 1) begin
        jwe_b[q] <= ((u_al[4] || u_gt[4]) && uqk[4] == q[0]) ? jw_oh[q] : RQD'(0);
        jwe_c[q] <= ((u_al[4] || u_gt[4]) && uqk[4] == q[0]) ? jw_oh[q] : RQD'(0);
    end
    always @(posedge ck) begin
        jpd1 <= {jpd[23:15], jpd[3:0], kb + {14'd0, jpd[14:4], 5'd0} + {18'd0, jpd[14:4], 1'b0}};
        for (q = 0; q < 2; q = q + 1) for (s = 0; s < RQD; s = s + 1) begin
            if (jwe_a[q][s]) jq[q][s][14:0]  <= jpd1[14:0];
            if (jwe_b[q][s]) jq[q][s][28:15] <= jpd1[28:15];
            if (jwe_c[q][s]) jq[q][s][42:29] <= jpd1[42:29];
        end
    end
    always @(posedge ck or negedge rl[18])
        if (!rl[18]) begin for (q = 0; q < 2; q = q + 1) begin jw_oh[q] <= RQD'(1); jw_n[q] <= 4'd0; end end
        else for (q = 0; q < 2; q = q + 1)
            if (jwe_a[q] != 0) begin jw_oh[q] <= {jw_oh[q][RQD-2:0], jw_oh[q][RQD-1]}; jw_n[q] <= jw_n[q] + 4'd1; end
    wire        ipop_c;
    always @(posedge ck or negedge rl[19])
        if (!rl[19]) begin jq_room <= 2'b11; iq_n <= 11'd0; iq_room32 <= 1'b1; iq_room2 <= 1'b1; end
        else begin
            for (q = 0; q < 2; q = q + 1)
                jq_room[q] <= (jw_n[q] - jr_n[q]) <= 4'(RQD - 4) && (jw_n[q] - jr_n[q + 2]) <= 4'(RQD - 4);
            iq_n <= iq_n + (ipush ? 11'd1 : 11'd0) - (ipop_c ? 11'd1 : 11'd0);
            iq_room32 <= iq_n <= 11'(IQD - 40);
            iq_room2 <= iq_n <= 11'(IQD - 8);
        end
    // slot table: update stage (one edge after the decision) + release
    generate for (gu = 0; gu < 2; gu = gu + 1) begin : g_st
        wire al0 = (u_al[0] || (u_gt[0] && u_need)) && uqk[0] == gu[0];   // (re)allocation of slot sa
        always @(posedge ck or negedge rl[20 + gu])
            if (!rl[20 + gu]) begin sb[gu] <= '0; scl[gu] <= '0; sopen[gu] <= 1'b0; end
            else begin : g_up
                integer s2;
                if (al0) begin
                    if (u_gt[0] && sopen[gu]) scl[gu][sop[gu]] <= 1'b1;
                    sb[gu][sa[gu]] <= 1'b1; scl[gu][sa[gu]] <= u_al[0]; if (u_gt[0]) sopen[gu] <= 1'b1;
                end else if (u_gt[0] && uqk[0] == gu[0] && u_full) begin scl[gu][sop[gu]] <= 1'b1; sopen[gu] <= 1'b0; end
                if (u_cl && sopen[gu]) begin scl[gu][sop[gu]] <= 1'b1; sopen[gu] <= 1'b0; end
                for (s2 = 0; s2 < LG; s2 = s2 + 1)
                    if (sb[gu][s2] && srdy[gu][s2] && snc[gu][s2] == sni[gu][s2] && !(cons_v[gu] && cons_s[gu] == 4'(s2)))
                        sb[gu][s2] <= 1'b0;
                if (hj4[0]) sopen[gu] <= 1'b0;
            end
        always @(posedge ck) begin
            if (al0) begin sa[gu] <= sa[gu] + 4'd1; sop[gu] <= sa[gu]; end
            if (u_gt[0] && uqk[0] == gu[0]) socnt[gu] <= u_need ? 5'd1 : socnt[gu] + 5'd1;
        end
        // counts (one-hot enables from the decision copies: 1 sni / sne, 2 snr, 3 snc)
        wire al1 = (u_al[1] || (u_gt[1] && u_need)) && uqk[1] == gu[0];
        wire ad1 = u_gt[1] && !u_need && uqk[1] == gu[0];
        wire al2 = (u_al[2] || (u_gt[2] && u_need)) && uqk[2] == gu[0];
        wire al3 = (u_al[3] || (u_gt[3] && u_need)) && uqk[3] == gu[0];
        always @(posedge ck) begin : g_cnt
            integer s3;
            for (s3 = 0; s3 < LG; s3 = s3 + 1) begin
                if (al1 && sa[gu] == 4'(s3)) begin sni[gu][s3] <= u_gt[1] ? 5'd1 : u_cnt; sne[gu][s3] <= u_gt[1] ? 6'd3 : 6'd34; end
                else if (ad1 && sop[gu] == 4'(s3)) begin sni[gu][s3] <= sni[gu][s3] + 5'd1; sne[gu][s3] <= sne[gu][s3] + 6'd3; end
                if (al2 && sa[gu] == 4'(s3)) begin snr0[gu][s3] <= 6'd0; snr1[gu][s3] <= 6'd0; end
                else begin
                    if (lw_v[gu] && lw_sl[gu] == 4'(s3)) snr0[gu][s3] <= snr0[gu][s3] + 6'd1;
                    if (lw_v[2 + gu] && lw_sl[2 + gu] == 4'(s3)) snr1[gu][s3] <= snr1[gu][s3] + 6'd1;
                end
                if (al3 && sa[gu] == 4'(s3)) snc[gu][s3] <= 5'd0;
                else if (cons_v[gu] && cons_s[gu] == 4'(s3)) snc[gu][s3] <= snc[gu][s3] + 5'd1;
                srdy[gu][s3] <= sb[gu][s3] && scl[gu][s3] && snr0[gu][s3] == sne[gu][s3] && snr1[gu][s3] == sne[gu][s3];
            end
        end
    end endgenerate
    // responses -> landing writes (registered: data unconditional)
    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin : g_rsp
        reg g; reg [3:0] s_; reg [3:0] cl; reg sc; reg [3:0] bt;
        g = rt[u][14]; s_ = {rt[u][5], rt[u][13:11]}; cl = rt[u][10:7]; sc = rt[u][6]; bt = rb[u];
        lw_d[u] <= rdd[u];
        lw_sl[u] <= s_;
        lw_h1[u] <= !sc && bt[0];
        if (!sc) lw_a[u] <= {2'b00, s_, g ? cl : cl + {3'd0, bt[1]}};
        else if (!g) lw_a[u] <= {5'b01000, s_, bt[0]};
        else lw_a[u] <= {2'b10, s_, cl};
    end
    always @(posedge ck or negedge rl[22])
        if (!rl[22]) begin lw_v <= 4'd0; fw <= 8'd0; lf_wn <= '0; end
        else begin
            lw_v <= mine;
            fw <= 8'd0;
            for (u = 0; u < 4; u = u + 1) begin
                if (mine[u] && !sb[u % 2][{rt[u][5], rt[u][13:11]}]) fw[1] <= 1'b1;   // a response to no slot
                if (rk_in[u] && own_n[u] == 0) fw[1] <= 1'b1;                      // pop with no request
                if (own_n[u] > OW'(DQR)) fw[1] <= 1'b1;                            // budget overflow
            end
            if (lf_push && lf_wn == (LFW+1)'(LFD)) fw[0] <= 1'b1;                    // list longer than the list memory
            if (hj1[2]) lf_wn <= '0; else if (lf_push) lf_wn <= lf_wn + 1'b1;
        end

    // ================================================================== landing memories (per PC: 2 halves)
    // consumer stages: S (scale row read on half 0) -> C (code read on both halves, scale extracted) -> K (key to engine)
    reg         s_v, c_v, k_v;
    reg  [IW-1:0] s_it, c_it, k_it;
    (* keep = "true" *) reg [1:0] su_a, su_b;      // S-stage PC copies (scale select / macro control)
    wire [3:0][255:0] h0q, h1q;
    wire [1:0]  c_u = c_it[34:33];
    (* keep = "true" *) reg [1:0] cu_a, cu_b;      // C-stage PC copies (key select halves)
    wire [9:0]  s_row = gatk[1] ? {2'b10, s_it[32:29], s_it[28:25]} : {5'b01000, s_it[32:29], s_it[28]};
    wire [9:0]  c_row = {2'b00, c_it[32:29], c_it[28:25]};
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_land
        wire rs0 = s_v && su_b == 2'(gu);
        wire rc  = c_v && c_u == 2'(gu);
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h0 (
            .ck(ck), .re(rs0 || rc), .ra(rs0 ? s_row : c_row), .rd(h0q[gu]),
            .we(lw_v[gu] && !lw_h1[gu]), .wa(lw_a[gu]), .wd(lw_d[gu]));
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h1 (
            .ck(ck), .re(rc), .ra(c_row), .rd(h1q[gu]),
            .we(lw_v[gu] && lw_h1[gu]), .wa(lw_a[gu]), .wd(lw_d[gu]));
    end endgenerate

    // ================================================================== item queue (macro) + 4-entry show-ahead head
    reg  [9:0]  iq_w, iq_r;
    reg  [10:0] im_n;
    reg         ir_f;
    reg  [3:0][IW-1:0] hq;
    (* keep = "true" *) reg [3:0] hwa, hwb, hwc;   // head write pointer copies (12 / 12 / 11 bits)
    (* keep = "true" *) reg [3:0] hra, hrb, hrc;   // head read pointer copies
    reg  [2:0]  hn;
    (* keep = "true" *) reg [2:0] hne;             // hn != 0 copies (pop groups)
    wire [255:0] iq_q;
    wire        ir_e = (im_n != 0) && ({1'b0, hn} + {3'b0, ir_f} <= 4'd2);
    wire [IW-1:0] ipd;
    assign ipd[11:0]  = gatk[2] ? ipd_g[11:0]  : ipd_s[11:0];
    assign ipd[23:12] = gatk[4] ? ipd_g[23:12] : ipd_s[23:12];
    assign ipd[34:24] = gatk[5] ? ipd_g[34:24] : ipd_s[34:24];
    dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_iq (
        .ck(ck), .re(ir_e), .ra(iq_r), .rd(iq_q), .we(ipush), .wa(iq_w), .wd({{(256-IW){1'b0}}, ipd}));
    integer e3;
    always @(posedge ck)
        for (e3 = 0; e3 < 4; e3 = e3 + 1) begin
            if (ir_f && hwa[e3]) hq[e3][11:0]  <= iq_q[11:0];
            if (ir_f && hwb[e3]) hq[e3][23:12] <= iq_q[23:12];
            if (ir_f && hwc[e3]) hq[e3][34:24] <= iq_q[34:24];
        end
    reg [IW-1:0] ih;
    always @* begin
        ih = '0;
        for (e3 = 0; e3 < 4; e3 = e3 + 1) begin
            ih[11:0]  = ih[11:0]  | ({12{hra[e3]}} & hq[e3][11:0]);
            ih[23:12] = ih[23:12] | ({12{hrb[e3]}} & hq[e3][23:12]);
            ih[34:24] = ih[34:24] | ({11{hrc[e3]}} & hq[e3][34:24]);
        end
    end
    // consumer pop: head present, its slot ready, query loaded, room in the score queue (3 copies by consumer group)
    reg  [10:0] infl;
    (* keep = "true" *) reg [2:0] room;
    wire        h_q = ih[33];
    wire [3:0]  h_s = ih[32:29];
    wire        h_rdy = srdy[h_q][h_s] && q_done && act;
    wire        ipop_a = hne[0] && h_rdy && room[0];       // head read pointers a / b
    wire        ipop_b = hne[1] && h_rdy && room[1];       // head read pointer c, hn, S stage
    assign      ipop_c = hne[2] && h_rdy && room[2];       // consumption counts, infl, iq_n
    always @(posedge ck or negedge rl[23])
        if (!rl[23]) begin iq_w <= 10'd0; iq_r <= 10'd0; im_n <= 11'd0; ir_f <= 1'b0; end
        else begin
            if (ipush) iq_w <= iq_w + 10'd1;
            ir_f <= ir_e;
            if (ir_e) iq_r <= iq_r + 10'd1;
            im_n <= im_n + (ipush ? 11'd1 : 11'd0) - (ir_e ? 11'd1 : 11'd0);
        end
    always @(posedge ck or negedge rl[24])
        if (!rl[24]) begin hn <= 3'd0; hne <= 3'd0; hwa <= 4'd1; hwb <= 4'd1; hwc <= 4'd1; hra <= 4'd1; hrb <= 4'd1; hrc <= 4'd1; end
        else begin : g_hn
            reg [2:0] n1;
            if (ir_f) begin hwa <= {hwa[2:0], hwa[3]}; hwb <= {hwb[2:0], hwb[3]}; hwc <= {hwc[2:0], hwc[3]}; end
            if (ipop_a) begin hra <= {hra[2:0], hra[3]}; hrb <= {hrb[2:0], hrb[3]}; end
            if (ipop_b) hrc <= {hrc[2:0], hrc[3]};
            n1 = hn + (ir_f ? 3'd1 : 3'd0) - (ipop_b ? 3'd1 : 3'd0);
            hn <= n1; hne <= {3{n1 != 3'd0}};
        end
    always @(posedge ck or negedge rl[25])
        if (!rl[25]) begin cons_v <= 2'b00; s_v <= 1'b0; c_v <= 1'b0; k_v <= 1'b0; end
        else begin
            cons_v <= 2'b00;
            if (ipop_c && ih[34]) cons_v[h_q] <= 1'b1;
            s_v <= ipop_b; c_v <= s_v; k_v <= c_v;
        end
    always @(posedge ck) begin
        cons_s[0] <= h_s; cons_s[1] <= h_s; s_it <= ih; su_a <= ih[34:33]; su_b <= ih[34:33]; c_it <= s_it; k_it <= c_it;
    end
    // scale extraction select (C stage: half-0 output of PC c_u, 32-b word idx): kept one-hot copies, registered at S
    (* keep = "true" *) reg [31:0] ssel;
    always @(posedge ck) begin : g_ss
        integer a_;
        for (a_ = 0; a_ < 32; a_ = a_ + 1) ssel[a_] <= su_a == 2'(a_ / 8) && s_it[2:0] == 3'(a_ % 8);
    end
    reg [31:0] k_sc;
    always @(posedge ck) begin : g_sc
        reg [31:0] x; integer a_;
        x = 32'd0;
        for (a_ = 0; a_ < 32; a_ = a_ + 1) x = x | ({32{ssel[a_]}} & h0q[a_ / 8][32 * (a_ % 8) +: 32]);
        k_sc <= x;
    end
    // key mux select (K stage: halves of PC k_u): 32 kept one-hot copies a PC (16 bits each), registered at C
    (* keep = "true" *) reg [31:0] ks0, ks1, ks2, ks3;
    always @(posedge ck) begin
        cu_a <= s_it[34:33]; cu_b <= s_it[34:33];
        ks0 <= {{16{cu_b == 2'd0}}, {16{cu_a == 2'd0}}}; ks1 <= {{16{cu_b == 2'd1}}, {16{cu_a == 2'd1}}};
        ks2 <= {{16{cu_b == 2'd2}}, {16{cu_a == 2'd2}}}; ks3 <= {{16{cu_b == 2'd3}}, {16{cu_a == 2'd3}}};
    end
    wire [543:0] k_key;
    genvar gk;
    generate for (gk = 0; gk < 32; gk = gk + 1) begin : g_km
        localparam integer H = gk / 16, O = 16 * (gk % 16);
        wire [15:0] d0_ = ({16{ks0[gk]}} & (H ? h1q[0][O +: 16] : h0q[0][O +: 16])) | ({16{ks1[gk]}} & (H ? h1q[1][O +: 16] : h0q[1][O +: 16])) |
                          ({16{ks2[gk]}} & (H ? h1q[2][O +: 16] : h0q[2][O +: 16])) | ({16{ks3[gk]}} & (H ? h1q[3][O +: 16] : h0q[3][O +: 16]));
        assign k_key[256 * H + O +: 16] = d0_;
    end endgenerate
    assign k_key[543:512] = k_sc;

    // ================================================================== engine: 4 chunk columns + tail (fixed latency)
    wire [3:0][31:0] csum;
    wire [3:0]       cfl;
    genvar gc;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_ch
        dsdv_idx_rg2_chunk u_c (.clk(ck), .rst_n(rl[26 + gc]), .hb(8'(8 * gc)), .ql_v(ql_v), .ql_head(ql_h),
            .ql_codes(ql_c), .ql_sc(ql_sw[31:0]), .ql_w(ql_sw[47:32]), .k_key(k_key), .c_sum(csum[gc]), .c_fault(cfl[gc]));
    end endgenerate
    wire [15:0] o_s;
    wire        o_f;
    dsdv_idx_rg2_tail u_t (.clk(ck), .i_sum({csum[3], csum[2], csum[1], csum[0]}), .i_fault(cfl), .o_score(o_s), .o_fault(o_f));

    // ================================================================== metadata ring: written every edge, read EL - 1 behind
    reg  [9:0]  mw;
    reg  [7:0]  warm_n; reg warm;
    wire [255:0] mq_q;
    dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mq (
        .ck(ck), .re(1'b1), .ra(mw - 10'(EL - 1)), .rd(mq_q), .we(1'b1), .wa(mw),
        .wd({{(256-MW-1){1'b0}}, k_v, k_it[24:3]}));
    always @(posedge ck or negedge rl[30])
        if (!rl[30]) begin mw <= 10'd0; warm_n <= 8'd0; warm <= 1'b0; end
        else begin
            mw <= mw + 10'd1;
            if (!warm) begin warm_n <= warm_n + 8'd1; if (warm_n == 8'(EL + 2)) warm <= 1'b1; end
        end
    reg         o_v1; reg [MW-1:0] o_m1; reg [15:0] o_s1; reg o_f1;
    always @(posedge ck or negedge rl[30]) if (!rl[30]) o_v1 <= 1'b0; else o_v1 <= mq_q[MW] && warm;
    always @(posedge ck) begin o_m1 <= mq_q[MW-1:0]; o_s1 <= o_s; o_f1 <= o_f; end

    // ================================================================== score queue (macro) + 4-entry show-ahead head
    localparam integer SW = MW + 17;                // {meta 22, fault, score 16}
    reg  [9:0]  sq_w, sq_r;
    reg  [10:0] sm_n;
    reg         sr_f;
    reg  [3:0][SW-1:0] sh;
    (* keep = "true" *) reg [3:0] swa, swb, swc;
    (* keep = "true" *) reg [3:0] sra, srb, src_;
    reg  [2:0]  shn;
    (* keep = "true" *) reg [3:0] she;
    wire [255:0] sq_q;
    wire        s_re = (sm_n != 0) && ({1'b0, shn} + {3'b0, sr_f} <= 4'd2);
    dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_sq (
        .ck(ck), .re(s_re), .ra(sq_r), .rd(sq_q), .we(o_v1), .wa(sq_w), .wd({{(256-SW){1'b0}}, o_m1, o_f1, o_s1}));
    always @(posedge ck)
        for (e3 = 0; e3 < 4; e3 = e3 + 1) begin
            if (sr_f && swa[e3]) sh[e3][12:0]  <= sq_q[12:0];
            if (sr_f && swb[e3]) sh[e3][25:13] <= sq_q[25:13];
            if (sr_f && swc[e3]) sh[e3][38:26] <= sq_q[38:26];
        end
    reg [SW-1:0] th;
    always @* begin
        th = '0;
        for (e3 = 0; e3 < 4; e3 = e3 + 1) begin
            th[12:0]  = th[12:0]  | ({13{sra[e3]}} & sh[e3][12:0]);
            th[25:13] = th[25:13] | ({13{srb[e3]}} & sh[e3][25:13]);
            th[38:26] = th[38:26] | ({13{src_[e3]}} & sh[e3][38:26]);
        end
    end
    // assembler buffer state (declared here: the score pop depends on it)
    reg  [1:0]  bact, bcmp;
    reg  [1:0][15:0] bw;
    reg  [1:0]  bf;
    reg         ap;
    (* keep = "true" *) reg [3:0] apk;             // assembling buffer copies
    (* keep = "true" *) reg [8:0] epk;             // emission buffer copies
    (* keep = "true" *) reg [3:0] afr;             // !bcmp[ap] (next-state register copies)
    wire        sq_pop_a = she[0] && afr[0];                // head pointers, shn
    wire        sq_pop_b = she[1] && afr[1];                // write stage, infl
    wire        sq_pop_c = she[2] && afr[2];                // assembler state
    wire        sq_pop_d = she[3] && afr[3];                // word index / fault flag
    always @(posedge ck or negedge rl[31])
        if (!rl[31]) begin sq_w <= 10'd0; sq_r <= 10'd0; end
        else begin if (o_v1) sq_w <= sq_w + 10'd1; if (s_re) sq_r <= sq_r + 10'd1; end
    always @(posedge ck or negedge rl[32])
        if (!rl[32]) begin sm_n <= 11'd0; sr_f <= 1'b0; shn <= 3'd0; she <= 4'd0; end
        else begin : g_sqc
            reg [2:0] n1;
            sr_f <= s_re;
            sm_n <= sm_n + (o_v1 ? 11'd1 : 11'd0) - (s_re ? 11'd1 : 11'd0);
            n1 = shn + (sr_f ? 3'd1 : 3'd0) - (sq_pop_a ? 3'd1 : 3'd0);
            shn <= n1; she <= {4{n1 != 3'd0}};
        end
    always @(posedge ck or negedge rl[33])
        if (!rl[33]) begin swa <= 4'd1; swb <= 4'd1; swc <= 4'd1; sra <= 4'd1; srb <= 4'd1; src_ <= 4'd1; end
        else begin
            if (sr_f) begin swa <= {swa[2:0], swa[3]}; swb <= {swb[2:0], swb[3]}; swc <= {swc[2:0], swc[3]}; end
            if (sq_pop_a) begin sra <= {sra[2:0], sra[3]}; srb <= {srb[2:0], srb[3]}; src_ <= {src_[2:0], src_[3]}; end
        end
    always @(posedge ck or negedge rl[34])
        if (!rl[34]) begin infl <= 11'd0; room <= 3'b111; end
        else begin : g_inf
            reg [10:0] ni;
            ni = infl + (ipop_c ? 11'd1 : 11'd0) - (sq_pop_b ? 11'd1 : 11'd0);
            infl <= ni; room <= {3{ni < 11'(SQD - 4)}};
        end

    // ================================================================== assembler: 2 word buffers (ping-pong)
    // score entry th = {w 16, lane 4, lw, v, fault, score 16}
    wire [15:0] t_w = th[38:23]; wire [3:0] t_ln = th[22:19]; wire t_lw = th[18]; wire t_kv = th[17];
    wire        t_f = th[16]; wire [15:0] t_s = th[15:0];
    // write stage (registered): per-buffer valid copies (8 lanes each), lane one-hot, score copies (one a buffer)
    (* keep = "true" *) reg [1:0] pwv0, pwv1;      // [copy] for buffer 0 / 1 lane enables (kv set)
    (* keep = "true" *) reg [1:0] pwb;             // buffer written this edge (lane-valid update)
    reg         pw_st, pw_kv;
    reg  [15:0] pw_oh;
    (* keep = "true" *) reg [15:0] pws0, pws1;     // score copies
    reg  [1:0][15:0] blv;
    reg  [1:0][255:0] bs;
    wire        take_n;
    always @(posedge ck or negedge rl[35])
        if (!rl[35]) begin bact <= 2'b00; bcmp <= 2'b00; ap <= 1'b0; apk <= 4'd0; epk <= 9'd0; afr <= 4'hF; pwv0 <= 2'b00; pwv1 <= 2'b00; pwb <= 2'b00; end
        else begin : g_asm
            reg [1:0] nact, ncmp; reg nap;
            nact = bact; ncmp = bcmp; nap = ap;
            pwv0 <= {2{sq_pop_b && !apk[1] && t_kv}}; pwv1 <= {2{sq_pop_b && apk[1] && t_kv}};
            pwb <= {sq_pop_b && apk[1], sq_pop_b && !apk[1]};
            if (sq_pop_c) begin
                nact[apk[2]] = 1'b1;
                if (t_lw) begin ncmp[apk[2]] = 1'b1; nap = !ap; end
            end
            if (take_n) begin nact[epk[4]] = 1'b0; ncmp[epk[4]] = 1'b0; epk <= ~epk; end
            if (hj1[3]) begin nact = 2'b00; ncmp = 2'b00; nap = 1'b0; epk <= 9'd0; end
            bact <= nact; bcmp <= ncmp; ap <= nap; apk <= {4{nap}}; afr <= {4{!ncmp[nap]}};
        end
    always @(posedge ck) begin
        if (sq_pop_d && !bact[apk[3]]) bw[apk[3]] <= t_w;
        if (sq_pop_d) bf[apk[3]] <= (bact[apk[3]] ? bf[apk[3]] : 1'b0) | (t_f && t_kv);
        pw_st <= !bact[apk[1]]; pw_kv <= t_kv; pw_oh <= 16'd1 << t_ln; pws0 <= t_s; pws1 <= t_s;
    end
    integer l_;
    always @(posedge ck) begin
        if (pwb[0]) blv[0] <= (pw_st ? 16'd0 : blv[0]) | (pw_kv ? pw_oh : 16'd0);
        if (pwb[1]) blv[1] <= (pw_st ? 16'd0 : blv[1]) | (pw_kv ? pw_oh : 16'd0);
        for (l_ = 0; l_ < 16; l_ = l_ + 1) begin
            if (pwv0[l_ / 8] && pw_oh[l_]) bs[0][16 * l_ +: 16] <= pws0;
            if (pwv1[l_ / 8] && pw_oh[l_]) bs[1][16 * l_ +: 16] <= pws1;
        end
    end

    // ================================================================== emission (the compiled window)
    // every so term is a register computed ahead (header beat 2 edges, part 0 / part 1 one edge)
    function automatic [275:0] bk(input [2:0] kind, input [1:0] lane, input part, input single, input [11:0] tt,
                                  input [255:0] dd);
        bk = {dd, tt, single, part, lane, kind, 1'b1};
    endfunction
    wire [19:0] th0 = 20'(t0);
    wire        endn = ended || (end_w && act);
    wire [19:0] tcn = (end_w && act) ? 20'd0 : (ended && !wdone) ? tc + 20'd1 : tc;
    // header: one-hot of the beat due two edges ahead (tc + 2), then the beat register (one edge ahead)
    wire [19:0] tc2 = (ended && !wdone) ? tc + 20'd2 : tc;
    wire [19:0] e2x = tc2 - th0;
    (* keep = "true" *) reg [9:0] hk0, hk1;        // header beat one-hot copies
    always @(posedge ck or negedge rl[36])
        if (!rl[36]) begin hk0 <= 10'd0; hk1 <= 10'd0; end
        else begin : g_hk
            reg [9:0] oh; integer i_;
            for (i_ = 0; i_ < 10; i_ = i_ + 1)
                oh[i_] = ended && !wdone && tc2 >= th0 && e2x == 20'(i_) &&
                         !(MUT != 6 && ((i_ >= 1 && i_ <= 3 && om[0]) || (i_ >= 4 && i_ <= 6 && om[1]) || (i_ >= 7 && i_ <= 9 && om[2])));
            hk0 <= oh; hk1 <= oh;
        end
    reg  [275:0] hb_r;
    always @(posedge ck) begin : g_hb
        reg [275:0] x;
        x = '0;
        if (hk0[0]) x = x | bk(ik, 2'd0, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd0, jk, 20'({j0, 4'd0})});
        if (hk0[1]) x = x | bk(ik, 2'd1, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd1, jk, 20'({j1 + 16'd1, 4'd0})});
        if (hk0[2]) x = x | bk(ik, 2'd1, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
        if (hk0[3]) x = x | bk(ik, 2'd1, 1'b1, 1'b0, 12'd0, {4'd2, tg, 227'd0, 1'b1, 16'd0});
        if (hk0[4]) x = x | bk(ik, 2'd2, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd2, jk, 20'({j1 + 16'd1, 4'd0})});
        if (hk1[5]) x = x | bk(ik, 2'd2, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
        if (hk1[6]) x = x | bk(ik, 2'd2, 1'b1, 1'b0, 12'd0, {4'd2, tg, 227'd0, 1'b1, 16'd0});
        if (hk1[7]) x = x | bk(ik, 2'd3, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd3, jk, 20'({j1 + 16'd1, 4'd0})});
        if (hk1[8]) x = x | bk(ik, 2'd3, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
        if (hk1[9]) x = x | bk(ik, 2'd3, 1'b1, 1'b0, 12'd0, {4'd2, tg, 227'd0, 1'b1, 16'd0});
        hb_r <= x;
    end
    // slots: part 0 of word ew at tc == et; et += P
    reg  [15:0] ew; reg [19:0] et;
    reg         slot_r;
    (* keep = "true" *) reg [3:0] srk;             // slot copies: ew, et, part-1 capture, part-0 header bits
    wire [15:0] ewn = ew + (srk[0] ? 16'd1 : 16'd0);
    wire [19:0] etn = et + (srk[1] ? 20'(pp) : 20'd0);
    wire        slot_n = endn && !wdone && ewn < nw && tcn == etn && !hj1[4] && !hj2[7];
    // take one edge before the slot: buffer ep complete and holding word ewn
    wire [15:0] bwe = {bw[epk[8]][15:8], bw[epk[0]][7:0]};
    assign take_n = slot_n && bcmp[epk[5]] && bwe == ewn;
    // S81-L20RD3 (10-20): FAIL-CLOSED gather slots.  A gather word the pair does not own is legitimately empty, but the
    // record rule (late only when a COMPLETE buffer holds an older word) let an OWNED word whose keys had not reached the
    // assembler pass as an empty word with fault 0 (bench2 gather P3: word 104 zeros, fault 0).  A gather slot is now
    // certified only when the assembler frontier is past it (items reach the assembler in word order, so every owned word
    // below gfr is complete in a buffer) or the reader is drained (walker done, item queue / in-flight / open buffers
    // empty).  An uncertified slot that is not taken is LATE (sticky fault + in-band flag).  gc_r is registered one edge
    // ahead from the stable ewn (P >= 2), with gfr / gdr one edge stale: conservative only.  MUT 7 = the record rule.
    reg  [15:0] gfr;                                // gather: words below gfr are complete or not owned
    reg         gd1, gdr, gc_r;
    always @(posedge ck) begin                      // data registers (no reset): gfr cleared at every job header
            if (hj1[3]) gfr <= 16'd0;
            else if (sq_pop_d) gfr <= t_lw ? t_w + 16'd1 : t_w;
            gd1 <= ws == 3'd6 && iq_n == 11'd0 && infl == 11'd0 && !ipush && (bact & ~bcmp) == 2'b00 && !hj1[3];
            gdr <= gd1 && ws == 3'd6 && !hj1[3];
            gc_r <= MUT == 7 || gdr || gfr > ewn;
    end
    wire        late_n = slot_n && (gat ? ((bcmp[epk[5]] && bwe < ewn) || (!take_n && !gc_r)) : !take_n);
    (* keep = "true" *) reg [1:0] tk0, tk1;        // part-0 data enables (2 x 8 lanes) per buffer
    reg         tk_r, late_r, p1_r, p1_d, p1_last, p1_f;
    reg  [15:0] p1_lv;
    always @(posedge ck) begin
        if (hj2[8]) ew <= 16'd0; else ew <= ewn;
        if (hj2[9]) et[15:0] <= th0[15:0] + 16'd10; else et[15:0] <= etn[15:0];
        if (hj2[10]) et[19:16] <= 4'd0 + 4'(({4'd0, th0[15:0]} + 20'd10) >> 16); else et[19:16] <= etn[19:16];
        if (srk[2]) begin p1_lv[7:0] <= tk_r ? blv[!epk[2]][7:0] : 8'd0; p1_lv[15:8] <= tk_r ? blv[!epk[6]][15:8] : 8'd0;
                          p1_last <= ew == nw - 16'd1; p1_f <= (tk_r && bf[!epk[7]]) || late_r || fault; end
    end
    always @(posedge ck or negedge rl[37])
        if (!rl[37]) begin slot_r <= 1'b0; srk <= 4'd0; tk_r <= 1'b0; late_r <= 1'b0; p1_r <= 1'b0; p1_d <= 1'b0; tk0 <= 2'd0; tk1 <= 2'd0; end
        else begin
            slot_r <= slot_n; srk <= {4{slot_n}}; tk_r <= take_n; late_r <= late_n;
            tk0 <= {2{take_n && !epk[1]}}; tk1 <= {2{take_n && epk[1]}};
            p1_r <= slot_r; p1_d <= p1_r;
        end
    // part 0: lanes of the taken buffer, masked by lane valid
    wire [255:0] d0;
    genvar gl;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_d0
        assign d0[16 * gl +: 16] = ({16{tk0[gl / 8] && blv[0][gl]}} & bs[0][16 * gl +: 16]) |
                                   ({16{tk1[gl / 8] && blv[1][gl]}} & bs[1][16 * gl +: 16]);
    end endgenerate
    wire [275:0] ins0 = (srk[3] ? bk(ik, 2'd0, 1'b0, 1'b0, {4'd2, tg}, 256'd0) : 276'd0) | {d0, 20'd0};
    wire         p1_due = (MUT == 4 && me == 4'd0) ? p1_d : p1_r;
    wire [275:0] ins1 = p1_due ? bk(ik, 2'd0, 1'b1, 1'b0, {11'd0, p1_f}, {4'd2, tg, 227'd0, p1_last, p1_lv}) : 276'd0;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) so[0] <= 1'b0; else so[0] <= sr[0] | hb_r[0] | ins0[0] | ins1[0];
    always @(posedge ck) so[275:1] <= sr[275:1] | hb_r[275:1] | ins0[275:1] | ins1[275:1];

    // ================================================================== window end, faults, status
    reg  [7:0] fc_set;
    always @(posedge ck or negedge rl[38])
        if (!rl[38]) begin wdone <= 1'b0; wdone_p <= 1'b0; fc_set <= 8'd0; end
        else begin
            fc_set <= 8'd0; wdone_p <= 1'b0;
            if (hj1[5]) wdone <= 1'b0;
            if (late_r && slot_r) fc_set[2] <= 1'b1;
            if (slot_r && tk_r && bf[!epk[3]]) fc_set[3] <= 1'b1;
            if (k_v && (ql_v || qst != 0)) fc_set[4] <= 1'b1;
            if (hbad1) fc_set[5] <= 1'b1;
            if (hj4[0] && (spec_bad || (gat ? hlen != 12'(64 + nlw) : hlen != 12'd64))) fc_set[6] <= 1'b1;
            if (pay_job && pw < 12'd64 && pw[0] && !qo[0]) fc_set[6] <= 1'b1;   // query word pair not contiguous
            if (ended && !wdone && ew == nw && !slot_r && !p1_r && !p1_d) begin
                wdone <= 1'b1; wdone_p <= 1'b1;
                if (iq_n != 0 || infl != 0 || bact != 2'b00 || (ws != 3'd6 && ws != 3'd0)) fc_set[7] <= 1'b1;
            end
        end
    always @(posedge ck or negedge rl[39])
        if (!rl[39]) begin fc <= 8'd0; st <= 10'd0; end else begin fc <= fc | fc_set | fw; st <= {fc, act, fault}; end
endmodule
