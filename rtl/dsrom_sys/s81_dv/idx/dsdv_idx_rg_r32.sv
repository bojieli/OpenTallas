// S81-L20RD (10-20, SAFE checklist 1/3/4/5/8 after the 2a006c746 ENG=1 native census FAIL: 16,122 flops, 276 nets > 32
// loads, reset 3,892 loads, 29-level stage; the remainder was READER CONTROL).  Structural rework, same function:
//   * RESET: the rst port drives only ot_rst_relay (2 sync + 1 kept relay stage, NRL regional leaves).  Only control
//     state is reset (synchronous trailing override, <= 32 bits a leaf); job / landing / slot-field / queue data and
//     pulses fed from reset state carry no reset (set at allocation / header, or zero within the reset period).
//   * FANOUT: no runtime-indexed flop array and no comb decision drives a wide register: wide data registers load
//     unconditionally and are qualified by a valid; selects are REGISTERED ONE-HOT kept copies (<= 32 loads each), and
//     a decision with many targets is formed once per target group from a KEPT COPY of its state register (walker
//     state, wdone, score-head count), so each copy is a distinct gate: query-load / header-capture enables (stage B,
//     +1 edge), the rq data select (copies of the rq valid pin flop), landing arrival bits (registered slot / cell
//     one-hots from the response tag), slot fields (registered allocation strobes), read-job queues (one-hot tokens,
//     registered write enables), item / score head rings (4 entries, registered write enables, kept read tokens), the
//     word assembler (ping-pong word buffers, registered lane one-hots) and the emission (decided ONE CYCLE EARLY into
//     registered beat / take copies: the chain beats leave at the same edges as the record design).
//   * DEPTH: the scan valid mask is registered (one walker edge a group); the gather list word is pre-decoded into
//     per-entry fields at load and the next owned entry is a registered one-hot (no priority encoder in the take path);
//     the emission's own-key test runs on a registered absolute word.
//   * STORAGE: the scale row cache is gone; scales land in their own 1024 x 256 macro a PC (11 macros a reader).  The
//     list prefetch reads the list macro's held output (no 512-b copy).  ENG 1: the slices' 104-deep valid line is a
//     128-entry ring (2-level one-hot tokens); the chunk-sum tail is the CLOSED ot_hbm_idx_tail_native view
//     (hidx_tail_native_rr, NKT 4: key lane 0 used, spare lanes 1..3 idle at kv / keep 0).
//   * SCHEDULE: chain timing unchanged (qo 2 edges a hop, so 2 edges a hop, beats at END + T0 + ...).  Internal latency:
//     +1 edge query load, +1 walker edge a scan group, +1 edge landing arrival, +1 edge word ready, emission decided one
//     cycle before its beat; all inside the reader run-ahead (the x_t0_* bench cases measure it): 0 calendar edges.
//     New job check: T0 >= 2 (the header one-hot starts 2 cycles ahead).
module dsdv_idx_rg_r32 #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQ = 8,           // controller request buffer entries a PC (dsfd_ctrl_rg2 DQ)
    parameter integer LG = 8,           // landing slots a PC (16 key cells each)
    parameter integer IQD = 256,        // key items in flight (item queue macro)
    parameter integer SQD = 64,         // keys in the engine + scores waiting for the assembler
    parameter integer LFD = 256,        // candidate-list words held (gather)
    parameter integer RQD = 16,         // read jobs queued a PC
    parameter integer ENG = 0           // 1 = hardened head-key slices + closed tail view; 0 = record flat engine
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,            // query chain {d 512, v}
    output reg  [512:0]  qo,
    input  wire [275:0]  si,            // score chain (BK V beats)
    output reg  [275:0]  so,
    input  wire [681:0]  rqi,           // from dsdv_svc_rs
    output reg  [681:0]  rqo,           // to dsfd_ctrl_rg2
    input  wire [561:0]  rdi,           // from dsfd_ctrl_rg2
    output reg  [561:0]  rdo,           // to dsdv_svc_rs
    output reg  [9:0]    st             // {fault cause 8, busy, fault}
);
    localparam integer SLW = 3;
    initial if (LG != 8) $fatal(1, "dsdv_idx_rg: LG must be 8 (3-bit tag slot field)");
    initial if (RQD != 16) $fatal(1, "dsdv_idx_rg: RQD must be 16 (one-hot read-job tokens)");
    initial if (LFD > 1024 || IQD > 1024 || SQD > 1024) $fatal(1, "dsdv_idx_rg: queue memories are 1024 words");
    localparam integer IQW = $clog2(IQD), SQW = $clog2(SQD), LFW = $clog2(LFD);

    // ------------------------------------------------------------------ reset: regional leaves
    localparam integer NRL = 32;
    localparam integer R_PIN = 0, R_JOB = 1, R_HBM = 2, R_RSP = 3, R_SLOT = 4, R_RJW0 = 5, R_RJW1 = 6, R_ISS = 7,
                       R_RJR0 = 8, R_RJR1 = 9, R_WALK = 10, R_LIST = 11, R_HEAD = 12, R_CONS = 13, R_ENG = 14,
                       R_MQ = 21, R_SQ = 22, R_SH = 23, R_ASM = 24, R_EOH = 25, R_SLT = 26, R_P1 = 27, R_WD = 28,
                       R_FC = 29, R_WALK2 = 30, R_WALK3 = 31;
    wire [NRL-1:0] rl;
    ot_rst_relay #(.REGIONS(NRL), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst), .rst_n(rl));
    // sid strap copies (one per use group); the strap is static, so no reset
    (* keep = "true" *) reg [3:0] me_v, me_o, me_g, me_w, me_e;
    always @(posedge ck) begin me_v <= sid; me_o <= sid; me_g <= sid; me_w <= sid; me_e <= sid; end

    function automatic [3:0] hj(input [15:0] j);
        hj = j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12];
    endfunction
    function automatic [7:0] oh8(input [2:0] x);
        oh8 = 8'd1 << x;
    endfunction
    function automatic [15:0] oh16(input [3:0] x);
        oh16 = 16'd1 << x;
    endfunction
    function automatic [15:0] low1(input [15:0] m);   // lowest set bit, one-hot
        low1 = m & (~m + 16'd1);
    endfunction
    function automatic [3:0] enc16(input [15:0] o);
        integer k_; enc16 = 4'd0;
        for (k_ = 0; k_ < 16; k_ = k_ + 1) if (o[k_]) enc16 = enc16 | 4'(k_);
    endfunction
    function automatic [4:0] popcnt16(input [15:0] m);
        integer k_; popcnt16 = 5'd0;
        for (k_ = 0; k_ < 16; k_ = k_ + 1) popcnt16 = popcnt16 + 5'(m[k_]);
    endfunction
    function automatic [31:0] sel8l(input [255:0] d, input [7:0] o);
        integer k_; sel8l = 32'd0;
        for (k_ = 0; k_ < 8; k_ = k_ + 1) sel8l = sel8l | ({32{o[k_]}} & d[32 * k_ +: 32]);
    endfunction
    function automatic [275:0] bk(input [2:0] kind, input [1:0] lane, input part, input single, input [11:0] tt,
                                  input [255:0] dd);
        bk = {dd, tt, single, part, lane, kind, 1'b1};
    endfunction

    // ------------------------------------------------------------------ pin registers / chains
    reg [512:0] qr;
    reg [275:0] sr;
    reg [681:0] rqr;
    reg [561:0] rdr;
    (* keep = "true" *) reg [10:0] avk0, avk1;  // copies of the rq valid pin flops: the rqo data select (340 b a PC)
    always @(posedge ck) begin
        qr <= qi; qo <= qr; sr <= si; rqr <= rqi; rdr <= rdi;
        avk0 <= {11{rqi[0]}}; avk1 <= {11{rqi[341]}};
        if (!rl[R_PIN]) begin qr[0] <= 1'b0; qo[0] <= 1'b0; sr[0] <= 1'b0; rqr[0] <= 1'b0; rqr[341] <= 1'b0;
                              rdr[277] <= 1'b0; rdr[278] <= 1'b0; rdr[279] <= 1'b0; rdr[557] <= 1'b0; rdr[558] <= 1'b0;
                              rdr[559] <= 1'b0; end
    end

    // ------------------------------------------------------------------ forward declarations
    reg         wdone_p, wdone;
    (* keep = "true" *) reg [3:0] wdk;       // wdone copies (emission decision groups)
    reg  [7:0]  fc_set;
    reg         fw0_r, fw1_r;
    reg  [7:0]  fc;
    wire        fault = |fc;
    reg  [2:0]  ws;
    wire        ipop;
    reg         c_v;
    reg  [IQW:0] iq_n;
    reg  [SQW:0] infl;

    // ------------------------------------------------------------------ STAGE A: frame tracking at the q pin register
    reg        act, infr, isj;
    reg [11:0] left, pw;
    wire       q_v = qr[0];
    wire [511:0] q_d = qr[512:1];
    wire       is_h = q_v && !infr;
    wire       is_p = q_v && infr;
    wire       hdr_job = is_h && (q_d[511:508] == 4'd4 || q_d[511:508] == 4'd8);
    wire       hdr_go = hdr_job && !act;
    wire       pay_job = is_p && isj;
    wire       end_w = pay_job && left == 12'd1;
    wire       q_ld0 = pay_job && pw < 12'd64 && !pw[0];
    wire       q_ld1 = pay_job && pw < 12'd64 && pw[0];
    reg        ended;
    reg [19:0] tc;
    reg [2:0]  qset;
    reg        q_done;
    reg        ql_v;
    reg [7:0]  ql_h;
    reg        hgo;                          // header accepted (stage B control pulse)
    always @(posedge ck) begin
        if (is_h) begin
            left <= q_d[491:480]; pw <= 12'd0; infr <= q_d[491:480] != 12'd0; isj <= hdr_job;
            if (hdr_go) act <= 1'b1;
        end else if (is_p) begin
            left <= left - 12'd1; pw <= pw + 12'd1;
            if (left == 12'd1) infr <= 1'b0;
        end
        if (hgo) begin q_done <= 1'b0; ended <= 1'b0; tc <= 20'd0; end
        if (ql_v && ql_h == 8'd31) qset <= 3'd5;
        else if (qset != 0) begin qset <= qset - 3'd1; if (qset == 3'd1) q_done <= 1'b1; end
        if (end_w && act) begin ended <= 1'b1; tc <= 20'd0; end
        else if (ended && !wdone) tc <= tc + 20'd1;
        if (wdone_p) act <= 1'b0;
        if (!rl[R_JOB]) begin act <= 1'b0; infr <= 1'b0; isj <= 1'b0; ended <= 1'b0; qset <= 3'd0; q_done <= 1'b0; end
    end

    // ------------------------------------------------------------------ STAGE B: header capture + query load (+1 edge)
    reg  [511:0] q_d1;
    (* keep = "true" *) reg [16:0] hg;        // hgo copies for the field / state loads
    (* keep = "true" *) reg [15:0] qe_h;      // even-word hold enable copies
    (* keep = "true" *) reg [17:0] qe_l;      // odd-word load enable copies
    reg  [511:0] qhold;
    reg  [511:0] ql_c;
    reg  [31:0]  ql_s;
    reg  [15:0]  ql_w;
    reg          gat;
    reg  [19:0]  jb;
    reg  [20:0]  jn, jend;
    reg  [9:0]   jk;
    reg  [29:0]  kb;
    reg  [15:0]  t0;
    reg  [3:0]   pp;
    reg  [2:0]   ik, om;
    reg  [7:0]   tg;
    reg  [15:0]  j0, j1, j1p, nw, nwm1, nlw;
    wire [20:0]  b_n = q_d1[40:20];
    wire [20:0]  b_end = 21'(q_d1[19:0]) + b_n - 21'd1;
    wire [15:0]  b_j0 = q_d1[511] ? 16'd0 : q_d1[19:4];
    wire [15:0]  b_j1 = q_d1[511] ? 16'(((b_n + 21'd1) >> 1) - 21'd1) : b_end[19:4];
    wire [15:0]  b_nw = q_d1[511] ? 16'((b_n + 21'd1) >> 1) : 16'(b_end[19:4] - q_d1[19:4] + 16'd1);
    always @(posedge ck) begin : g_stb
        integer k;
        q_d1 <= q_d;
        hgo <= hdr_go; hg <= {17{hdr_go}};
        qe_h <= {16{q_ld0}}; qe_l <= {18{q_ld1}};
        ql_v <= q_ld1; ql_h <= 8'(pw[6:1]);
        for (k = 0; k < 16; k = k + 1) begin
            if (qe_h[k]) qhold[32 * k +: 32] <= q_d1[32 * k +: 32];
            if (qe_l[k]) ql_c[32 * k +: 32] <= qhold[32 * k +: 32];
        end
        if (qe_l[16]) ql_s <= q_d1[31:0];
        if (qe_l[17]) ql_w <= q_d1[47:32];
        if (hg[0]) begin gat <= q_d1[511]; jb <= q_d1[19:0]; ik <= q_d1[103:101]; om <= q_d1[106:104]; end
        if (hg[1]) begin jn <= b_n; jk <= q_d1[50:41]; end
        if (hg[2]) kb <= q_d1[80:51];
        if (hg[3]) begin t0 <= q_d1[96:81]; pp <= q_d1[100:97]; tg <= q_d1[502:495]; end
        if (hg[4]) j0 <= b_j0;
        if (hg[5]) j1 <= b_j1;
        if (hg[6]) begin nw <= b_nw; nlw <= q_d1[511] ? 16'((b_n + 21'd15) >> 4) : 16'd0; end
        if (hg[7]) jend <= 21'(q_d1[19:0]) + b_n;
        if (hg[8]) begin j1p <= b_j1 + 16'd1; nwm1 <= b_nw - 16'd1; end
        if (!rl[R_JOB]) begin hgo <= 1'b0; ql_v <= 1'b0; end
    end

    // ------------------------------------------------------------------ HBM faces: owner FIFOs, credits, rd filter
    reg  [1:0]  i_v;
    reg  [29:0] i_a [0:1];
    reg  [3:0]  i_l [0:1];
    reg  [16:0] i_t [0:1];
    reg  [15:0] own [0:1];                   // owner FIFO (1 = this reader); bits >= own_n are don't-care
    reg  [4:0]  own_n [0:1];
    wire [1:0]  av_ = {rqr[341], rqr[0]};
    wire [1:0]  can = {(own_n[1] < 5'(DQ)) && !av_[1], (own_n[0] < 5'(DQ)) && !av_[0]};
    wire [1:0]  rk_in = {rdr[280 + 278], rdr[278]};
    wire [1:0]  rv_in = {rdr[280 + 277], rdr[277]};
    wire [16:0] rt [0:1];
    assign rt[0] = rdr[272:256];
    assign rt[1] = rdr[280 + 256 +: 17];
    wire [1:0]  mine_rv;
    assign mine_rv[0] = rv_in[0] && rt[0][16:15] == 2'b11;
    assign mine_rv[1] = rv_in[1] && rt[1][16:15] == 2'b11;
    wire [1:0]  iss = i_v & can;
    always @(posedge ck) begin : g_face
        integer p;
        for (p = 0; p < 2; p = p + 1) begin : g_pc
            reg push, pop, ob;
            push = av_[p] || iss[p];
            pop = rk_in[p];
            ob = own[p][0];
            rqo[341 * p] <= push;
            if (MUT == 2) rdo[280 * p + 278] <= rk_in[p];
            else rdo[280 * p + 278] <= rk_in[p] && (own_n[p] != 0) && !ob;
            rdo[280 * p + 279] <= rdr[280 * p + 279];
            if (MUT == 5) rdo[280 * p + 277] <= rv_in[p] && !mine_rv[p] && !rt[p][0];
            else rdo[280 * p + 277] <= rv_in[p] && !mine_rv[p];
            if (pop && !push) begin own[p] <= own[p] >> 1; own_n[p] <= own_n[p] - 5'd1; end
            else if (push && !pop) begin own[p][own_n[p][3:0]] <= iss[p]; own_n[p] <= own_n[p] + 5'd1; end
            else if (push && pop) begin own[p] <= own[p] >> 1; own[p][own_n[p][3:0] - 4'd1] <= iss[p]; end
        end
        if (!rl[R_HBM]) begin rqo[0] <= 1'b0; rqo[341] <= 1'b0; rdo[277] <= 1'b0; rdo[278] <= 1'b0; rdo[279] <= 1'b0;
                              rdo[557] <= 1'b0; rdo[558] <= 1'b0; rdo[559] <= 1'b0; own_n[0] <= 5'd0; own_n[1] <= 5'd0; end
    end
    wire [339:0] rq_rd [0:1];
    assign rq_rd[0] = {256'd0, 32'd0, i_t[0], i_l[0], i_a[0], 1'b0};
    assign rq_rd[1] = {256'd0, 32'd0, i_t[1], i_l[1], i_a[1], 1'b0};
    always @(posedge ck) begin : g_rqd
        integer k;
        for (k = 0; k < 340; k = k + 1) begin
            rqo[1 + k] <= avk0[k / 32] ? rqr[1 + k] : rq_rd[0][k];
            rqo[342 + k] <= avk1[k / 32] ? rqr[342 + k] : rq_rd[1][k];
        end
        rdo[276:0] <= rdr[276:0]; rdo[556:280] <= rdr[556:280]; rdo[561:560] <= rdr[561:560];
    end

    // ------------------------------------------------------------------ response decode (R1, registered from the pins)
    // per PC: code beat -> landing write (half bt[0]) + arrival bit; scale beat -> scale macro row write + scale bits;
    // every beat -> the slot's received count.  All targets are registered one-hots.
    reg  [3:0]   lw_v;                       // code macro write (index 2 pc + half)
    reg  [SLW+3:0] lw_a [0:3];
    reg  [255:0] lw_dd [0:1];                // response data a PC (both halves take it)
    reg  [7:0]   r1_c0 [0:1], r1_c1 [0:1];   // slot one-hot of a half-0 / half-1 code beat
    reg  [15:0]  r1_cc [0:1];                // its cell one-hot
    reg  [7:0]   r1_rs [0:1];                // slot one-hot of any beat (received count)
    reg  [1:0]   sw_v;                       // scale macro write
    reg  [3:0]   sw_r [0:1];                 // row {slot, cell[3]}
    reg  [255:0] sw_raw [0:1];
    (* keep = "true" *) reg [7:0] sw_gd0, sw_gd1, sw_gm0, sw_gm1;   // gather-form copies (data / mask lanes)
    reg  [7:0]   sw_by [0:1];                // gather: byte-group one-hot of the scale in the sector
    reg  [7:0]   sw_lm [0:1];                // gather: lane one-hot (mask)
    reg  [15:0]  r1_sr [0:1];                // scale row one-hot (scale-valid bits)
    reg  [7:0]   r1_sl [0:1];                // scale lane mask (scale-valid bits)
    reg  [1:0]   fw_rsp;
    always @(posedge ck) begin : g_r1
        integer p;
        for (p = 0; p < 2; p = p + 1) begin : g_r0
            reg g; reg [SLW-1:0] s_; reg [3:0] cl, cc; reg sc; reg [2:0] by; reg [3:0] bt;
            g = rt[p][14]; s_ = rt[p][11 +: SLW]; cl = rt[p][10:7]; sc = rt[p][6]; by = rt[p][5:3];
            bt = (p == 0) ? rdr[276:273] : rdr[280 + 273 +: 4];
            cc = g ? cl : cl + {3'd0, bt[1]};
            lw_dd[p] <= (p == 0) ? rdr[255:0] : rdr[280 +: 256];
            sw_raw[p] <= (p == 0) ? rdr[255:0] : rdr[280 +: 256];
            lw_v[2 * p] <= mine_rv[p] && !sc && !bt[0];
            lw_v[2 * p + 1] <= mine_rv[p] && !sc && bt[0];
            lw_a[2 * p] <= {s_, cc}; lw_a[2 * p + 1] <= {s_, cc};
            r1_c0[p] <= (mine_rv[p] && !sc && !bt[0]) ? oh8(s_) : 8'd0;
            r1_c1[p] <= (mine_rv[p] && !sc && bt[0]) ? oh8(s_) : 8'd0;
            r1_cc[p] <= oh16(cc);
            r1_rs[p] <= mine_rv[p] ? oh8(s_) : 8'd0;
            sw_v[p] <= mine_rv[p] && sc;
            sw_r[p] <= g ? {s_, cl[3]} : {s_, bt[0]};
            sw_by[p] <= oh8(by ^ ((MUT == 3) ? 3'd1 : 3'd0));
            sw_lm[p] <= oh8(cl[2:0]);
            r1_sr[p] <= (mine_rv[p] && sc) ? oh16(g ? {s_, cl[3]} : {s_, bt[0]}) : 16'd0;
            r1_sl[p] <= g ? oh8(cl[2:0]) : 8'hff;
        end
        sw_gd0 <= {8{rt[0][14]}}; sw_gm0 <= {8{rt[0][14]}};
        sw_gd1 <= {8{rt[1][14]}}; sw_gm1 <= {8{rt[1][14]}};
        fw_rsp <= {rk_in[1] && own_n[1] == 0, rk_in[0] && own_n[0] == 0};
        if (!rl[R_RSP]) begin lw_v <= 4'd0; sw_v <= 2'd0; fw_rsp <= 2'd0; end
    end
    // scale macro write data / mask (from the R1 registers): scan = the whole sector (8 scales of cells c3*8 ..), gather
    // = one scale (byte group by of its sector) into lane cl[2:0]
    wire [255:0] sw_d [0:1];
    wire [255:0] sw_m [0:1];
    genvar gq, ge;
    generate for (gq = 0; gq < 2; gq = gq + 1) begin : g_sw
        wire [31:0] gsel = sel8l(sw_raw[gq], sw_by[gq]);
        wire [7:0]  gd = (gq == 0) ? sw_gd0 : sw_gd1;
        wire [7:0]  gm = (gq == 0) ? sw_gm0 : sw_gm1;
        for (ge = 0; ge < 8; ge = ge + 1) begin : g_l
            localparam integer EP = (MUT == 3) ? (ge ^ 1) : ge;
            assign sw_d[gq][32 * EP +: 32] = gd[ge] ? gsel : sw_raw[gq][32 * ge +: 32];
            assign sw_m[gq][32 * ge +: 32] = gm[ge] ? {32{sw_lm[gq][ge]}} : 32'hffff_ffff;
        end
    end endgenerate

    // ------------------------------------------------------------------ landing + scale macros
    wire [255:0] lr_d [0:3];
    reg  [3:0]   lr_e;
    reg  [SLW+3:0] lr_a;                      // the head item's {slot, cell} (all four take it)
    wire [255:0] sr_d [0:1];
    reg  [1:0]   sre;
    reg  [3:0]   sra;                         // the head item's scale row {slot, cell[3]}
    genvar gp;
    generate for (gp = 0; gp < 4; gp = gp + 1) begin : g_land
        dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mem (
            .ck(ck), .re(lr_e[gp]), .ra(10'(lr_a)), .rd(lr_d[gp]),
            .we(lw_v[gp]), .wa(10'(lw_a[gp])), .wd(lw_dd[gp / 2]), .wm({256{1'b1}}));
    end
    for (gp = 0; gp < 2; gp = gp + 1) begin : g_scm
        dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mem (
            .ck(ck), .re(sre[gp]), .ra(10'(sra)), .rd(sr_d[gp]),
            .we(sw_v[gp]), .wa(10'(sw_r[gp])), .wd(sw_d[gp]), .wm(sw_m[gp]));
    end endgenerate

    // ------------------------------------------------------------------ arrival bits + slot fields (per PC)
    // c0 / c1: code half landed, sv: scale landed (cell = 16 s + c); cleared by the registered allocation strobes
    reg  [127:0] c0 [0:1], c1 [0:1], sv [0:1];
    reg  [7:0]   sb [0:1];                   // slot busy (reset)
    reg  [7:0]   scl_d [0:1];
    reg  [4:0]   sni [0:1][0:7], snc [0:1][0:7];
    reg  [5:0]   sne [0:1][0:7], snr [0:1][0:7];
    // allocation strobes (registered by the walker): new / update / close one-hots a PC, shared field data
    reg  [7:0]   al_new [0:1], al_upd [0:1], al_cls [0:1];
    reg  [4:0]   al_n;
    reg  [5:0]   al_e;
    reg          al_scl;
    (* keep = "true" *) reg [7:0] cls0_0, cls1_0, cls2_0, cls0_1, cls1_1, cls2_1;      // cleared slot one-hot
    (* keep = "true" *) reg [15:0] clm0, clm1, clm2;                                    // cleared cell mask
    reg  [7:0]   rel [0:1];                  // consumer release strobes (one-hot slot a PC)
    always @(posedge ck) begin : g_slots
        integer p, s, c;
        for (p = 0; p < 2; p = p + 1) begin
            for (s = 0; s < 8; s = s + 1) begin
                for (c = 0; c < 16; c = c + 1) begin
                    if (r1_c0[p][s] && r1_cc[p][c]) c0[p][16 * s + c] <= 1'b1;
                    else if ((p == 0 ? cls0_0[s] : cls0_1[s]) && clm0[c]) c0[p][16 * s + c] <= 1'b0;
                    if (r1_c1[p][s] && r1_cc[p][c]) c1[p][16 * s + c] <= 1'b1;
                    else if ((p == 0 ? cls1_0[s] : cls1_1[s]) && clm1[c]) c1[p][16 * s + c] <= 1'b0;
                    if (r1_sr[p][2 * s + c / 8] && r1_sl[p][c % 8]) sv[p][16 * s + c] <= 1'b1;
                    else if ((p == 0 ? cls2_0[s] : cls2_1[s]) && clm2[c]) sv[p][16 * s + c] <= 1'b0;
                end
                if (r1_rs[p][s]) snr[p][s] <= snr[p][s] + 6'd1;
                if (rel[p][s]) snc[p][s] <= snc[p][s] + 5'd1;
                if (al_upd[p][s]) begin sni[p][s] <= al_n; sne[p][s] <= al_e; end
                if (al_cls[p][s]) scl_d[p][s] <= 1'b1;
                if (al_new[p][s]) begin
                    sb[p][s] <= 1'b1; scl_d[p][s] <= al_scl; sni[p][s] <= al_n; sne[p][s] <= al_e;
                    snc[p][s] <= 5'd0; snr[p][s] <= 6'd0;
                end else if (sb[p][s] && scl_d[p][s] && snc[p][s] == sni[p][s] && snr[p][s] == sne[p][s] && !rel[p][s])
                    sb[p][s] <= 1'b0;
            end
        end
        if (!rl[R_SLOT]) begin sb[0] <= 8'd0; sb[1] <= 8'd0; end
    end
    // a beat for a slot that expects none (checked one edge after the response, before its count lands); rk with no
    // request
    reg [7:0] nexp [0:1];
    always @* begin : g_nexp
        integer p, s;
        for (p = 0; p < 2; p = p + 1) for (s = 0; s < 8; s = s + 1) nexp[p][s] = !sb[p][s] || snr[p][s] >= sne[p][s];
    end
    always @(posedge ck) begin
        fw1_r <= |(r1_rs[0] & nexp[0]) || |(r1_rs[1] & nexp[1]) || (|fw_rsp);
        if (!rl[R_SLOT]) fw1_r <= 1'b0;
    end

    // ------------------------------------------------------------------ list memory (gather)
    wire        lf_push = pay_job && pw >= 12'd64;
    reg  [LFW:0] lf_wn, lf_rn;
    reg          lfr_e;
    reg  [LFW-1:0] lfr_a;
    wire [511:0] lf_q;                         // held until the next read: the prefetched word itself
    genvar hh;
    generate for (hh = 0; hh < 2; hh = hh + 1) begin : g_lm
        dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mem (
            .ck(ck), .re(lfr_e), .ra(10'(lfr_a)), .rd(lf_q[256 * hh +: 256]),
            .we(lf_push), .wa(10'(lf_wn[LFW-1:0])), .wd(q_d[256 * hh +: 256]), .wm({256{1'b1}}));
    end endgenerate

    // ------------------------------------------------------------------ read-job queues (per PC, one-hot tokens)
    // entry {gather, slot, cell, block base 30, key cell 4}; written two edges after the walker's push (registered
    // address add, registered entry enables in two copies), read through kept read-token copies
    localparam integer JW = 1 + SLW + 4 + 30 + 4;
    reg  [JW-1:0] rjq [0:1][0:15];
    reg  [15:0]   rwt [0:1];                   // write token
    (* keep = "true" *) reg [15:0] rrta0, rrtb0, rrta1, rrtb1;   // read-token copies (entry select, 21 b each)
    (* keep = "true" *) reg [15:0] rwea0, rweb0, rwea1, rweb1;   // registered entry write enables
    reg  [1:0]    rjp_v;                       // walker push (a PC)
    reg  [SLW-1:0] rjp_s; reg [3:0] rjp_c; reg rjp_g; reg [14:0] rjp_row; reg [3:0] rjp_k;   // its job (shared)
    reg  [JW-1:0] rjd;
    reg  [1:0]    rjd_v;
    reg  [4:0]    rj_n [0:1];
    reg  [3:0]    rj_k [0:1];
    wire [JW-1:0] rjh [0:1];
    generate for (gq = 0; gq < 2; gq = gq + 1) begin : g_rjh
        wire [15:0] ta = (gq == 0) ? rrta0 : rrta1;
        wire [15:0] tb = (gq == 0) ? rrtb0 : rrtb1;
        reg [JW-1:0] h_;
        always @* begin : g_m
            integer k_;
            h_ = '0;
            for (k_ = 0; k_ < 16; k_ = k_ + 1) begin
                h_[20:0] = h_[20:0] | ({21{ta[k_]}} & rjq[gq][k_][20:0]);
                h_[JW-1:21] = h_[JW-1:21] | ({(JW-21){tb[k_]}} & rjq[gq][k_][JW-1:21]);
            end
        end
        assign rjh[gq] = h_;
    end endgenerate
    always @(posedge ck) begin : g_rjw
        integer k;
        rjd <= {rjp_g, rjp_s, rjp_c, kb + 30'({rjp_row, 5'd0}) + 30'({rjp_row, 1'b0}), rjp_k};
        rjd_v <= rjp_v;
        rwea0 <= rjp_v[0] ? rwt[0] : 16'd0; rweb0 <= rjp_v[0] ? rwt[0] : 16'd0;
        rwea1 <= rjp_v[1] ? rwt[1] : 16'd0; rweb1 <= rjp_v[1] ? rwt[1] : 16'd0;
        if (rjp_v[0]) rwt[0] <= {rwt[0][14:0], rwt[0][15]};
        if (rjp_v[1]) rwt[1] <= {rwt[1][14:0], rwt[1][15]};
        for (k = 0; k < 16; k = k + 1) begin
            if (rwea0[k]) rjq[0][k][20:0] <= rjd[20:0];
            if (rweb0[k]) rjq[0][k][JW-1:21] <= rjd[JW-1:21];
            if (rwea1[k]) rjq[1][k][20:0] <= rjd[20:0];
            if (rweb1[k]) rjq[1][k][JW-1:21] <= rjd[JW-1:21];
        end
        if (!rl[R_RJW0]) begin rwt[0] <= 16'd1; rjd_v <= 2'd0; end
        if (!rl[R_RJW1]) rwt[1] <= 16'd1;
    end
    // issuers: the head job's next request whenever the request register is free
    always @(posedge ck) begin : g_iss
        integer p;
        reg [1:0] po;
        for (p = 0; p < 2; p = p + 1) begin : g_ip
            reg jg; reg [SLW-1:0] js; reg [3:0] jc, jk_; reg [29:0] jb_;
            {jg, js, jc, jb_, jk_} = rjh[p];
            po[p] = 1'b0;
            if (iss[p]) i_v[p] <= 1'b0;
            if (rj_n[p] != 0 && (!i_v[p] || iss[p])) begin
                i_v[p] <= 1'b1;
                if (!jg) begin
                    if (rj_k[p] == 4'd0) begin i_a[p] <= jb_ + 30'd32; i_l[p] <= 4'd2;
                                               i_t[p] <= {2'b11, 1'b0, 3'(js), 4'd0, 1'b1, 3'd0, 3'd0}; end
                    else begin i_a[p] <= jb_ + 30'(4 * (rj_k[p] - 4'd1)); i_l[p] <= 4'd4;
                               i_t[p] <= {2'b11, 1'b0, 3'(js), 4'(2 * (rj_k[p] - 4'd1)), 1'b0, 3'd0, 3'd0}; end
                end else begin
                    if (rj_k[p] == 4'd0) begin i_a[p] <= jb_ + 30'(2 * jk_); i_l[p] <= 4'd2;
                                               i_t[p] <= {2'b11, 1'b1, 3'(js), jc, 1'b0, 3'd0, 3'd0}; end
                    else begin i_a[p] <= jb_ + 30'd32 + 30'(jk_[3]); i_l[p] <= 4'd1;
                               i_t[p] <= {2'b11, 1'b1, 3'(js), jc, 1'b1, jk_[2:0], 3'd0}; end
                end
                if (rj_k[p] == (jg ? 4'd1 : 4'd8)) begin rj_k[p] <= 4'd0; po[p] = 1'b1; end
                else rj_k[p] <= rj_k[p] + 4'd1;
            end
            rj_n[p] <= rj_n[p] + (rjd_v[p] ? 5'd1 : 5'd0) - (po[p] ? 5'd1 : 5'd0);
        end
        if (po[0]) begin rrta0 <= {rrta0[14:0], rrta0[15]}; rrtb0 <= {rrtb0[14:0], rrtb0[15]}; end
        if (po[1]) begin rrta1 <= {rrta1[14:0], rrta1[15]}; rrtb1 <= {rrtb1[14:0], rrtb1[15]}; end
        if (!rl[R_ISS]) begin i_v <= 2'd0; rj_k[0] <= 4'd0; rj_k[1] <= 4'd0; rj_n[0] <= 5'd0; rj_n[1] <= 5'd0; end
        if (!rl[R_RJR0]) begin rrta0 <= 16'd1; rrtb0 <= 16'd1; end
        if (!rl[R_RJR1]) begin rrta1 <= 16'd1; rrtb1 <= 16'd1; end
    end

    // ------------------------------------------------------------------ walker (items + read jobs)
    // item word (item queue macro): [28:0] {pc, slot, cell, w, lane, lw} (the record layout) + [36:29] slot one-hot if
    // PC 0, [44:37] slot one-hot if PC 1, [60:45] cell one-hot
    // states: 0 idle, 1 scan mask, 4 scan allocate, 2 scan items, 3 gather list word, 7 gather load, 6 gather keys, 5 done
    // Decisions with many targets are formed per target group from the group's KEPT state copy (wsk / gpc / socp /
    // ocp): each copy feeds its own gates, so no decision net drives more than one group.
    localparam integer IW = 1 + SLW + 4 + 16 + 4 + 1;
    localparam integer IWX = IW + 32;
    localparam integer NWK = 20;
    localparam integer NGK = 4;
    (* keep = "true" *) reg [3*NWK-1:0] wskv;       // walker state copies
    (* keep = "true" *) reg [NGK-1:0]   gpck;       // the next gather key's PC (copies)
    (* keep = "true" *) reg [2*NGK-1:0] socp;       // sopen copies
    (* keep = "true" *) reg [10*NGK-1:0] ocpv;      // ocnt copies
    reg          ipush;
    reg [IWX-1:0] ipd;
    reg [IQW-1:0] iq_w;
    reg  [15:0]  wg;
    (* keep = "true" *) reg [11:0] wgk0, wgk1, wgk2, wgk3;   // copies of wg[11:0] for the 16 cell compares
    reg  [15:0]  wvm;
    reg  [4:0]   wc;
    reg          wpc;
    reg  [SLW-1:0] wsl;
    reg  [SLW-1:0] sa [0:1];
    reg  [15:0]  gw;
    reg  [15:0]  gm, goh;                    // owned entries left / the next one (one-hot)
    reg  [19:0]  le [0:15];                  // entry {lw, pc, row 11, key cell 4, lane x 3}
    reg  [19:0]  gfr;                        // the next owned entry's fields (registered with goh)
    reg  [3:0]   glo;                        // its index
    (* keep = "true" *) reg [15:0] lk;       // list-word load enable copies (one an entry)
    reg          ln_v;
    reg          lfd1, lfd2;
    reg  [SLW-1:0] so_ [0:1];
    // scan valid mask of group wg (registered in state 1)
    reg  [15:0]  s_vm;
    always @* begin : g_vm
        integer c;
        for (c = 0; c < 16; c = c + 1) begin : g_c
            reg [15:0] jj; reg [20:0] pos; reg [11:0] wq;
            wq = (c < 4) ? wgk0 : (c < 8) ? wgk1 : (c < 12) ? wgk2 : wgk3;
            jj = {wq, 4'(c)};
            pos = {1'b0, jj, (MUT == 1) ? (me_v ^ hj(jj) ^ 4'd1) : (me_v ^ hj(jj))};
            s_vm[c] = (jj >= j0) && (jj <= j1) && (pos >= 21'(jb)) && (pos < jend);
        end
    end
    // gather: entries of the held list word this region owns a key of, and their pre-decoded fields
    reg  [15:0]  n_om;
    reg  [19:0]  n_le [0:15];
    always @* begin : g_om
        integer c;
        for (c = 0; c < 16; c = c + 1) begin : g_c
            reg [16:0] bb; reg [3:0] x, xg;
            bb = lf_q[32 * c +: 17];
            x = me_o ^ hj(16'(bb >> 1));
            xg = me_g ^ hj(16'(bb >> 1));
            n_om[c] = (21'({gw, 4'(c)}) < jn) && (x[3] == bb[0]);
        end
        for (c = 0; c < 16; c = c + 1) begin : g_f
            reg [16:0] bb; reg [3:0] xg;
            bb = lf_q[32 * c +: 17];
            xg = me_g ^ hj(16'(bb >> 1));
            // lw: this region's last key of the selector word (entry pairs 2 v, 2 v + 1 share a word)
            n_le[c] = {((c % 2) == 1) || !n_om[c | 1], bb[5], bb[16:6], bb[4:1], xg[2:0]};
        end
    end
    function automatic [19:0] lsel(input [15:0] o, input [319:0] f);
        integer k_; lsel = 20'd0;
        for (k_ = 0; k_ < 16; k_ = k_ + 1) lsel = lsel | ({20{o[k_]}} & f[20 * k_ +: 20]);
    endfunction
    reg  [319:0] n_lev, lev;
    always @* begin : g_lev
        integer c;
        for (c = 0; c < 16; c = c + 1) begin n_lev[20 * c +: 20] = n_le[c]; lev[20 * c +: 20] = le[c]; end
    end
    wire [15:0] goh_l = low1(n_om);              // first owned entry of a new word
    wire [15:0] goh_t = low1(gm & ~goh);         // next owned entry after a take
    wire [19:0] gfl = lsel(goh_l, n_lev);
    wire [19:0] gft = lsel(goh_t, lev);
    wire [15:0] g_w = {gw[12:0], glo[3:1]};
    wire [3:0]  g_ln = {glo[0], gfr[2:0]};
    wire        g_lw = gfr[19];
    wire [1:0]  sfree = {!sb[1][sa[1]], !sb[0][sa[0]]};
    wire        s_pc = wg[0];
    wire [14:0] s_n = wg[15:1];
    wire [4:0]  sp_ = popcnt16(wvm);
    // per-group copies of the gather PC / open-slot state
    wire [NGK-1:0] g_newk;
    genvar gk;
    generate for (gk = 0; gk < NGK; gk = gk + 1) begin : g_gn
        wire [1:0] so_c = socp[2 * gk +: 2];
        wire [4:0] oc0 = ocpv[10 * gk +: 5], oc1 = ocpv[10 * gk + 5 +: 5];
        assign g_newk[gk] = gpck[gk] ? (!so_c[1] || oc1 == 5'd16) : (!so_c[0] || oc0 == 5'd16);
    end endgenerate
    wire [4:0]  ocA = gpck[0] ? ocpv[5 +: 5] : ocpv[0 +: 5];
    wire [4:0]  ocC = gpck[2] ? ocpv[25 +: 5] : ocpv[20 +: 5];
    // shared decision terms (a few loads each); every target group ANDs its own state copy
    wire        g_cond = gm != 16'd0 && (g_newk[0] ? sfree[gpck[0]] : 1'b1) && iq_n < (IQW+1)'(IQD - 1) &&
                         rj_n[gpck[0]] < 5'(RQD - 3);
    wire        s_cond = wvm != 16'd0 && sfree[s_pc] && iq_n <= (IQW+1)'(IQD - 16) && rj_n[s_pc] < 5'(RQD - 3);
    wire [NWK-1:0] gtk, stk, s4k, s2k, s6k, s3k, s7k;
    generate for (gk = 0; gk < NWK; gk = gk + 1) begin : g_wk
        wire [2:0] w_ = wskv[3 * gk +: 3];
        assign s4k[gk] = w_ == 3'd4;
        assign s2k[gk] = w_ == 3'd2;
        assign s6k[gk] = w_ == 3'd6;
        assign s3k[gk] = w_ == 3'd3;
        assign s7k[gk] = w_ == 3'd7;
        assign gtk[gk] = s6k[gk] && g_cond;
        assign stk[gk] = s4k[gk] && s_cond;
    end endgenerate
    wire [3:0]  s_cell = wc[3:0];
    wire [15:0] s_j = {wg[11:0], s_cell};
    wire        g_end = gw >= nlw;
    // next walker state
    reg  [2:0]  ws_n;
    always @* begin
        ws_n = ws;
        if (hgo) ws_n = q_d1[511] ? 3'd3 : 3'd1;
        else case (ws)
            3'd1: ws_n = (wg > {4'd0, j1[15:4]}) ? 3'd5 : 3'd4;
            3'd4: ws_n = (wvm == 16'd0) ? 3'd1 : (s_cond ? 3'd2 : 3'd4);
            3'd2: ws_n = (wc == 5'd15) ? 3'd1 : 3'd2;
            3'd3: ws_n = g_end ? 3'd5 : (ln_v ? 3'd7 : 3'd3);
            3'd7: ws_n = 3'd6;
            3'd6: ws_n = (gm == 16'd0) ? 3'd3 : 3'd6;
            default: ;
        endcase
        if (wdone_p) ws_n = 3'd0;
    end
    // gather candidate slot / cell (data; used only under a take), from group C's copies
    wire [SLW-1:0] g_s = g_newk[2] ? sa[gpck[2]] : so_[gpck[2]];
    wire [3:0]  g_cl = g_newk[2] ? 4'd0 : ocC[3:0];
    always @(posedge ck) begin : g_walk
        integer k, p;
        ws <= ws_n; wskv <= {NWK{ws_n}};
        // ---- group 0: scan group counter + scan item state
        if (hg[9]) wg <= {4'd0, q_d1[19:8]};
        else if ((s4k[0] && wvm == 16'd0) || (s2k[0] && wc == 5'd15)) wg <= wg + 16'd1;
        if (s4k[0]) begin wpc <= s_pc; wsl <= sa[s_pc]; wc <= 5'd0; end
        else if (s2k[0]) wc <= wc + 5'd1;
        // ---- group 1 / 2: wg copies
        if (hg[10]) begin wgk0 <= q_d1[19:8]; wgk1 <= q_d1[19:8]; end
        else if ((s4k[1] && wvm == 16'd0) || (s2k[1] && wc == 5'd15)) begin wgk0 <= wgk0 + 12'd1; wgk1 <= wgk1 + 12'd1; end
        if (hg[11]) begin wgk2 <= q_d1[19:8]; wgk3 <= q_d1[19:8]; end
        else if ((s4k[2] && wvm == 16'd0) || (s2k[2] && wc == 5'd15)) begin wgk2 <= wgk2 + 12'd1; wgk3 <= wgk3 + 12'd1; end
        // ---- scan mask (state 1)
        if (wskv[3 * 18 +: 3] == 3'd1) wvm <= s_vm;
        // ---- group 3: new-slot strobes + slot allocation pointer (gather PC copy 1)
        al_new[0] <= 8'd0; al_new[1] <= 8'd0;
        for (p = 0; p < 2; p = p + 1) begin
            if (stk[3] && s_pc == p[0]) begin al_new[p] <= oh8(sa[p]); sa[p] <= sa[p] + 1'b1; end
            if (gtk[3] && g_newk[1] && gpck[1] == p[0]) begin al_new[p] <= oh8(sa[p]); sa[p] <= sa[p] + 1'b1; end
        end
        // ---- group 4: update / close strobes (gather PC copy 1)
        al_upd[0] <= 8'd0; al_upd[1] <= 8'd0; al_cls[0] <= 8'd0; al_cls[1] <= 8'd0;
        for (p = 0; p < 2; p = p + 1) begin
            if (gtk[4] && gpck[1] == p[0]) begin
                if (!g_newk[1]) al_upd[p] <= oh8(so_[p]);
                else if (socp[2 + p]) al_cls[p] <= oh8(so_[p]);
            end
            if (s3k[4] && g_end && !hgo && socp[2 + p]) al_cls[p] <= oh8(so_[p]);
        end
        // ---- group 12: field data (shared by both PCs: one allocation a cycle)
        al_scl <= s4k[12];                   // scan slots are closed at allocation, gather slots open
        al_n <= s4k[12] ? sp_ : (g_newk[3] ? 5'd1 : ocA + 5'd1);
        al_e <= s4k[12] ? 6'd34 : (g_newk[3] ? 6'd3 : 6'(3 * (ocA + 5'd1)));
        clm2 <= s4k[12] ? 16'hffff : oh16(g_cl);
        // ---- group 11: cell masks (data)
        clm0 <= s4k[11] ? 16'hffff : oh16(g_cl); clm1 <= s4k[11] ? 16'hffff : oh16(g_cl);
        // ---- group 5 / 6: cell clears (slot one-hot copies)
        cls0_0 <= 8'd0; cls1_0 <= 8'd0; cls2_0 <= 8'd0; cls0_1 <= 8'd0; cls1_1 <= 8'd0; cls2_1 <= 8'd0;
        if (stk[5] && !s_pc) begin cls0_0 <= oh8(sa[0]); cls1_0 <= oh8(sa[0]); end
        if (stk[5] && s_pc) begin cls0_1 <= oh8(sa[1]); cls1_1 <= oh8(sa[1]); end
        if (gtk[5] && !gpck[2]) begin cls0_0 <= oh8(g_s); cls1_0 <= oh8(g_s); end
        if (gtk[5] && gpck[2]) begin cls0_1 <= oh8(g_s); cls1_1 <= oh8(g_s); end
        if (stk[6] && !s_pc) cls2_0 <= oh8(sa[0]);
        if (stk[6] && s_pc) cls2_1 <= oh8(sa[1]);
        if (gtk[6] && !gpck[2]) cls2_0 <= oh8(g_s);
        if (gtk[6] && gpck[2]) cls2_1 <= oh8(g_s);
        // ---- group 9: read-job push
        rjp_v[0] <= (stk[9] && !s_pc) || (gtk[9] && !gpck[3]);
        rjp_v[1] <= (stk[9] && s_pc) || (gtk[9] && gpck[3]);
        // ---- group 13: job data (shared by both PCs: one push a cycle)
        if (s4k[13]) begin rjp_g <= 1'b0; rjp_s <= sa[s_pc]; rjp_c <= 4'd0; rjp_row <= s_n; rjp_k <= 4'd0; end
        else begin rjp_g <= 1'b1; rjp_s <= g_s; rjp_c <= g_cl; rjp_row <= {4'd0, gfr[17:7]}; rjp_k <= gfr[6:3]; end
        // ---- open gather slot state: so_ (group 6) and the per-group copies of sopen / ocnt (groups 14..17), alike
        for (p = 0; p < 2; p = p + 1) if (gtk[6] && gpck[3] == p[0] && g_newk[3]) so_[p] <= sa[p];
        for (k = 0; k < NGK; k = k + 1) for (p = 0; p < 2; p = p + 1) if (gtk[14 + k] && gpck[k] == p[0]) begin
            if (g_newk[k]) begin socp[2 * k + p] <= 1'b1; ocpv[10 * k + 5 * p +: 5] <= 5'd1; end
            else ocpv[10 * k + 5 * p +: 5] <= ocpv[10 * k + 5 * p +: 5] + 5'd1;
        end
        for (k = 0; k < NGK; k = k + 1) if (s3k[14 + k] && g_end && !hgo) socp[2 * k +: 2] <= 2'd0;
        // ---- group 7: gather entry masks + the next entry (registered)
        if (hg[12]) begin gw <= 16'd0; gm <= 16'd0; end
        else begin
            if (s7k[7]) begin gm <= n_om; goh <= goh_l; end
            else if (gtk[7]) begin gm <= gm & ~goh; goh <= goh_t; end
            if (s6k[7] && gm == 16'd0) gw <= gw + 16'd1;
        end
        if (s7k[8]) begin gfr <= gfl; glo <= enc16(goh_l); gpck <= {NGK{gfl[18]}}; end
        else if (gtk[8]) begin gfr <= gft; glo <= enc16(goh_t); gpck <= {NGK{gft[18]}}; end
        lk <= {16{ws == 3'd3 && !g_end && ln_v && !hgo}};
        for (k = 0; k < 16; k = k + 1) if (lk[k]) le[k] <= n_le[k];
        // ---- group 8 / 10: item push (+ its data)
        ipush <= (s2k[8] && wvm[s_cell]) || gtk[8];
        begin : g_ipd
            reg [IWX-1:0] gi, si_;
            gi = {oh16(g_cl), gpck[3] ? oh8(g_s) : 8'd0, gpck[3] ? 8'd0 : oh8(g_s), gpck[3], g_s, g_cl, g_w, g_ln, g_lw};
            si_ = {oh16(s_cell), wpc ? oh8(wsl) : 8'd0, wpc ? 8'd0 : oh8(wsl), wpc, wsl, s_cell, 16'(s_j - j0),
                   (MUT == 1) ? (me_w ^ hj(s_j) ^ 4'd1) : (me_w ^ hj(s_j)), 1'b1};
            ipd[30:0] <= s6k[10] ? gi[30:0] : si_[30:0];
            ipd[IWX-1:31] <= s6k[19] ? gi[IWX-1:31] : si_[IWX-1:31];
        end
        if (ipush) iq_w <= iq_w + 1'b1;
        iq_n <= iq_n + (ipush ? 1'b1 : 1'b0) - (c_v ? 1'b1 : 1'b0);
        if (!rl[R_WALK]) begin ws <= 3'd0; sa[0] <= 3'd0; sa[1] <= 3'd0; iq_w <= '0; iq_n <= '0; end
        if (!rl[R_WALK2]) begin wskv[29:0] <= '0; socp <= '0; end
        if (!rl[R_WALK3]) wskv[59:30] <= '0;
    end
    // list memory: written as the list arrives; one word held ahead of the walker (the macro output)
    always @(posedge ck) begin
        if (lf_push) lf_wn <= lf_wn + 1'b1;
        fw0_r <= lf_push && lf_wn == (LFW+1)'(LFD);       // list longer than the list memory
        if (hg[13]) begin lf_wn <= '0; lf_rn <= '0; end
        lfr_e <= 1'b0; lfd1 <= lfr_e; lfd2 <= lfd1;
        if (gat && act && !ln_v && !lfr_e && !lfd1 && !lfd2 && lf_rn < lf_wn && 16'(lf_rn) < nlw) begin
            lfr_e <= 1'b1; lfr_a <= lf_rn[LFW-1:0]; lf_rn <= lf_rn + 1'b1;
        end
        if (lfd2) ln_v <= 1'b1;
        if (ws == 3'd3 && gw < nlw && ln_v && !lfd2) ln_v <= 1'b0;
        if (hgo) ln_v <= 1'b0;
        if (!rl[R_LIST]) begin lfr_e <= 1'b0; lfd1 <= 1'b0; lfd2 <= 1'b0; ln_v <= 1'b0; fw0_r <= 1'b0; end
    end

    // ------------------------------------------------------------------ consumer: item queue -> landing -> engine
    wire [255:0] iq_q;
    reg  [IQW-1:0] iq_r;
    reg  [IQW:0]  im_n;
    reg           ir_f;
    reg  [IWX-1:0] he [0:3];                 // head ring: 4 entries
    reg  [2:0]     hq_n;
    reg  [3:0]     hwt;
    (* keep = "true" *) reg [3:0] hwea, hweb, hrta, hrtb;   // registered entry write enables / read-token copies
    wire           ir_e = (im_n != 0) && ({1'b0, hq_n} + {3'b0, ir_f} <= 4'd3);
    dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_iq (
        .ck(ck), .re(ir_e), .ra(10'(iq_r)), .rd(iq_q),
        .we(ipush), .wa(10'(iq_w)), .wd({{(256-IWX){1'b0}}, ipd}), .wm({256{1'b1}}));
    reg  [IWX-1:0] hd;
    always @* begin : g_hd
        integer k;
        hd = '0;
        for (k = 0; k < 4; k = k + 1) begin
            hd[30:0] = hd[30:0] | ({31{hrta[k]}} & he[k][30:0]);
            hd[IWX-1:31] = hd[IWX-1:31] | ({(IWX-31){hrtb[k]}} & he[k][IWX-1:31]);
        end
    end
    always @(posedge ck) begin : g_hq
        integer k;
        ir_f <= ir_e;
        if (ir_e) begin iq_r <= iq_r + 1'b1; hwt <= {hwt[2:0], hwt[3]}; end
        hwea <= ir_e ? hwt : 4'd0; hweb <= ir_e ? hwt : 4'd0;
        for (k = 0; k < 4; k = k + 1) begin
            if (hwea[k]) he[k][30:0] <= iq_q[30:0];
            if (hweb[k]) he[k][IWX-1:31] <= iq_q[IWX-1:31];
        end
        im_n <= im_n + (ipush ? 1'b1 : 1'b0) - (ir_e ? 1'b1 : 1'b0);
        hq_n <= hq_n - (ipop ? 3'd1 : 3'd0) + (ir_f ? 3'd1 : 3'd0);
        if (ipop) begin hrta <= {hrta[2:0], hrta[3]}; hrtb <= {hrtb[2:0], hrtb[3]}; end
        if (!rl[R_HEAD]) begin iq_r <= '0; im_n <= '0; ir_f <= 1'b0; hq_n <= 3'd0; hwt <= 4'd1; hrta <= 4'd1; hrtb <= 4'd1; end
    end
    wire [IW-1:0]  ih = hd[IW-1:0];
    wire           h_pc = ih[IW-1];
    wire [SLW-1:0] h_sl = ih[IW-2 -: SLW];
    wire [3:0]     h_cl = ih[IW-2-SLW -: 4];
    wire [7:0]     h_s0 = hd[36:29], h_s1 = hd[44:37];
    wire [15:0]    h_co = hd[60:45];
    reg  [15:0]    h_row;                     // landed cells of the head's slot (the item's PC)
    always @* begin : g_row
        integer c, s;
        for (c = 0; c < 16; c = c + 1) begin
            h_row[c] = 1'b0;
            for (s = 0; s < 8; s = s + 1) begin
                if (h_s0[s] && c0[0][16 * s + c] && c1[0][16 * s + c] && sv[0][16 * s + c]) h_row[c] = 1'b1;
                if (h_s1[s] && c0[1][16 * s + c] && c1[1][16 * s + c] && sv[1][16 * s + c]) h_row[c] = 1'b1;
            end
        end
    end
    wire           h_land = (hq_n != 0) && |(h_row & h_co);
    wire           h_ready = h_land;
    wire           room = infl < (SQW+1)'(SQD - 2);
    assign ipop = h_ready && q_done && room && act;
    // stage c (macro read edge), stage f (data), stage k (engine input register); data registers load every cycle
    reg  [15:0]  c_w; reg [3:0] c_ln; reg c_lw; reg c_pc; reg [2:0] c_l3;
    reg  [7:0]   c_s0, c_s1;
    (* keep = "true" *) reg [1:0] c_vk;
    reg          f1; reg [15:0] f_w; reg [3:0] f_ln; reg f_lw;
    (* keep = "true" *) reg [16:0] f_pck;      // PC select copies (code 512 b + scale 32 b)
    (* keep = "true" *) reg [7:0]  f_lo0, f_lo1; // scale lane one-hot a PC
    reg          k_v;
    (* keep = "true" *) reg [3:0] k_vc;        // k_v copies (valid ring)
    reg  [543:0] k_key;
    reg  [20:0]  k_m;
    always @(posedge ck) begin : g_cons
        integer k;
        c_v <= ipop; c_vk <= {2{ipop}};
        lr_e <= ipop ? (h_pc ? 4'b1100 : 4'b0011) : 4'b0000;
        sre <= ipop ? (h_pc ? 2'b10 : 2'b01) : 2'b00;
        lr_a <= {h_sl, h_cl}; sra <= {h_sl, h_cl[3]};
        c_w <= ih[20:5]; c_ln <= ih[4:1]; c_lw <= ih[0]; c_pc <= h_pc; c_l3 <= h_cl[2:0];
        c_s0 <= h_s0; c_s1 <= h_s1;
        rel[0] <= c_vk[0] ? c_s0 : 8'd0; rel[1] <= c_vk[1] ? c_s1 : 8'd0;
        f1 <= c_v; f_w <= c_w; f_ln <= c_ln; f_lw <= c_lw;
        f_pck <= {17{c_pc}}; f_lo0 <= oh8(c_l3); f_lo1 <= oh8(c_l3);
        k_v <= f1; k_vc <= {4{f1}};
        k_m <= {f_w, f_ln, f_lw};
        for (k = 0; k < 8; k = k + 1) begin
            k_key[32 * k +: 32] <= f_pck[k] ? lr_d[2][32 * k +: 32] : lr_d[0][32 * k +: 32];
            k_key[256 + 32 * k +: 32] <= f_pck[k] ? lr_d[3][32 * k +: 32] : lr_d[1][32 * k +: 32];
        end
        k_key[543:512] <= f_pck[16] ? sel8l(sr_d[1], f_lo1) : sel8l(sr_d[0], f_lo0);
        if (!rl[R_CONS]) begin c_v <= 1'b0; lr_e <= 4'd0; sre <= 2'd0; rel[0] <= 8'd0; rel[1] <= 8'd0; f1 <= 1'b0;
                               k_v <= 1'b0; end
    end

    // ------------------------------------------------------------------ engine
    wire        o_v;
    wire [15:0] o_s;
    wire        o_f;
    wire        k_ready;
    generate if (ENG == 0) begin : g_e0
        wire [0:0] o_kv_, o_f_;
        ot_hdc_v41x_idx_engine #(.NK(1), .IH(32), .NB(4), .FD(56)) u_eng (
            .clk(ck), .rst_n(rl[R_ENG]), .ql_v(ql_v), .ql_head(ql_h), .ql_codes(ql_c), .ql_sc(ql_s), .ql_w(ql_w),
            .k_valid(k_v), .k_ready(k_ready), .k_kv(1'b1), .k_keep(1'b1), .k_key(k_key),
            .o_valid(o_v), .o_ready(1'b1), .o_kv(o_kv_), .o_score(o_s), .o_fault(o_f_),
            .cnt_keys_scored(), .cnt_headsums_fused(), .cnt_faults());
        assign o_f = o_f_[0];
    end else begin : g_e1
        dsdv_idx_e32 u_e (.ck(ck), .rl(rl[R_ENG + 6 : R_ENG]), .ql_v(ql_v), .ql_h(ql_h), .ql_c(ql_c), .ql_s(ql_s),
            .ql_w(ql_w), .k_vc(k_vc), .k_key(k_key), .o_v(o_v), .o_s(o_s), .o_f(o_f));
        // a q-load beat reaches the slices' query registers 3 edges after it is presented; keys wait for it
        reg [1:0] qst;
        always @(posedge ck) begin
            if (ql_v) qst <= 2'd3;
            else if (qst != 0) qst <= qst - 2'd1;
            if (!rl[R_ENG]) qst <= 2'd0;
        end
        assign k_ready = !ql_v && qst == 0;
    end endgenerate
    // metadata ring (macro): written with the key, read with its score (fixed order), data one edge later
    wire [255:0] mq_q;
    reg  [9:0]   mq_w, mq_r;
    reg          o_v1; reg o_f1; reg [15:0] o_s1;
    dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mq (
        .ck(ck), .re(o_v), .ra(mq_r), .rd(mq_q),
        .we(k_v), .wa(mq_w), .wd({235'd0, k_m}), .wm({256{1'b1}}));
    // score queue (macro) + 4-entry head ring
    wire [255:0] sq_q;
    reg  [9:0]   sq_w, sq_r;
    reg  [10:0]  sm_n;
    reg          sr_f;
    reg  [37:0]  sh [0:3];
    reg  [2:0]   sh_n;
    (* keep = "true" *) reg [2:0] shk;       // sh_n copy (the second sq_pop gate)
    reg  [3:0]   swt;
    (* keep = "true" *) reg [3:0] swea, sweb, srta, srtb;
    wire         s_re = (sm_n != 0) && ({1'b0, sh_n} + {3'b0, sr_f} <= 4'd3);
    dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_sq (
        .ck(ck), .re(s_re), .ra(sq_r), .rd(sq_q),
        .we(o_v1), .wa(sq_w), .wd({218'd0, mq_q[20:0], o_f1, o_s1}), .wm({256{1'b1}}));
    reg  [37:0]  t_q;
    always @* begin : g_tq
        integer k;
        t_q = 38'd0;
        for (k = 0; k < 4; k = k + 1) begin
            t_q[18:0] = t_q[18:0] | ({19{srta[k]}} & sh[k][18:0]);
            t_q[37:19] = t_q[37:19] | ({19{srtb[k]}} & sh[k][37:19]);
        end
    end
    // assembler state (declared here: the pop condition)
    reg          pa, aa;                     // assembling buffer / a word in progress
    reg  [1:0]   bv;                         // buffer ready (emission takes it)
    wire         sq_pop  = (sh_n != 3'd0) && (aa || !bv[pa]);   // queue side + lane / meta registers
    wire         sq_pop2 = (shk != 3'd0) && (aa || !bv[pa]);    // the same decision: buffer-clear copies
    always @(posedge ck) begin : g_sq
        integer k;
        o_f1 <= o_f; o_s1 <= o_s;
        if (k_v) mq_w <= mq_w + 1'b1;
        if (o_v) mq_r <= mq_r + 1'b1;
        o_v1 <= o_v;
        if (o_v1) sq_w <= sq_w + 1'b1;
        sr_f <= s_re;
        if (s_re) begin sq_r <= sq_r + 1'b1; swt <= {swt[2:0], swt[3]}; end
        swea <= s_re ? swt : 4'd0; sweb <= s_re ? swt : 4'd0;
        for (k = 0; k < 4; k = k + 1) begin
            if (swea[k]) sh[k][18:0] <= sq_q[18:0];
            if (sweb[k]) sh[k][37:19] <= sq_q[37:19];
        end
        sm_n <= sm_n + (o_v1 ? 1'b1 : 1'b0) - (s_re ? 1'b1 : 1'b0);
        sh_n <= sh_n - (sq_pop ? 3'd1 : 3'd0) + (sr_f ? 3'd1 : 3'd0);
        shk <= shk - (sq_pop2 ? 3'd1 : 3'd0) + (sr_f ? 3'd1 : 3'd0);
        if (sq_pop) begin srta <= {srta[2:0], srta[3]}; srtb <= {srtb[2:0], srtb[3]}; end
        if (!rl[R_MQ]) begin mq_w <= 10'd0; mq_r <= 10'd0; o_v1 <= 1'b0; end
        if (!rl[R_SQ]) begin sq_w <= 10'd0; sq_r <= 10'd0; sr_f <= 1'b0; sm_n <= 11'd0; end
        if (!rl[R_SH]) begin sh_n <= 3'd0; shk <= 3'd0; swt <= 4'd1; srta <= 4'd1; srtb <= 4'd1; end
    end

    // ------------------------------------------------------------------ word assembler: ping-pong word buffers
    // a score pops into the assembling buffer pa (a new word needs pa free); the lanes land one edge later (registered
    // lane one-hot), and the word becomes ready (bv) with its last lane
    reg  [15:0]  bw [0:1];
    reg  [15:0]  blv [0:1];
    reg  [255:0] bs [0:1];
    reg  [1:0]   bf;
    reg          pe;                         // next buffer to emit
    (* keep = "true" *) reg [7:0] pe_k;      // its copies (score select), kept identical to pe
    reg          pp_last, pp_f;
    (* keep = "true" *) reg [1:0] pp_nw;     // "new word" a buffer (copies)
    reg  [15:0]  pp_loh, pp_w, pp_sc;
    (* keep = "true" *) reg [7:0] pp_n0, pp_n1;   // "new word" clears a buffer (copies, 2 lanes each)
    (* keep = "true" *) reg [1:0] pp_vl, pp_vm;   // lane / meta write a buffer
    reg          take_d;                     // emission took buffer pe (one edge after the decision)
    always @(posedge ck) begin : g_asm
        integer k, b;
        infl <= infl + (c_v ? 1'b1 : 1'b0) - ((|pp_vm) ? 1'b1 : 1'b0);
        pp_nw <= {2{!aa}}; pp_last <= t_q[17]; pp_f <= t_q[16];
        pp_loh <= oh16(t_q[21:18]); pp_sc <= t_q[15:0]; pp_w <= t_q[37:22];
        pp_n0 <= {8{sq_pop2 && !aa && !pa}}; pp_n1 <= {8{sq_pop2 && !aa && pa}};
        pp_vl <= {sq_pop && pa, sq_pop && !pa}; pp_vm <= {sq_pop && pa, sq_pop && !pa};
        if (sq_pop) begin
            if (t_q[17]) begin aa <= 1'b0; pa <= ~pa; end
            else aa <= 1'b1;
        end
        for (k = 0; k < 16; k = k + 1) begin
            if (pp_vl[0] && pp_loh[k]) bs[0][16 * k +: 16] <= pp_sc; else if (pp_n0[k / 2]) bs[0][16 * k +: 16] <= 16'd0;
            if (pp_vl[1] && pp_loh[k]) bs[1][16 * k +: 16] <= pp_sc; else if (pp_n1[k / 2]) bs[1][16 * k +: 16] <= 16'd0;
        end
        for (b = 0; b < 2; b = b + 1) if (pp_vm[b]) begin
            blv[b] <= pp_loh | (pp_nw[b] ? 16'd0 : blv[b]);
            bf[b] <= pp_f | (!pp_nw[b] && bf[b]);
            if (pp_nw[b]) bw[b] <= pp_w;
            if (pp_last) bv[b] <= 1'b1;
        end
        if (take_d) begin bv[pe] <= 1'b0; pe <= ~pe; pe_k <= ~pe_k; end
        if (!rl[R_ASM]) begin infl <= '0; pp_vl <= 2'd0; pp_vm <= 2'd0; pp_n0 <= 8'd0; pp_n1 <= 8'd0; aa <= 1'b0;
                              pa <= 1'b0; bv <= 2'd0; pe <= 1'b0; pe_k <= 8'd0; end
    end
    // tb trace aliases (the record names)
    wire          r_v = bv[pe];
    wire [15:0]   r_w = bw[pe];
    wire          a_v = aa;
    wire [15:0]   a_w = bw[pa];

    // ------------------------------------------------------------------ emission (the compiled window)
    // Every beat is DECIDED one cycle before its edge (tc == etm = et - 1; header one-hot e_oh) into registered copies;
    // so (the chain register) takes them at the same edge as the record design.
    reg  [15:0]  ew;
    reg  [15:0]  ej;                         // absolute word ew + j0
    reg  [19:0]  etm;                        // (beat cycle - 1) of word ew
    reg  [9:0]   e_oh;                       // header beat k is decided in the cycle e_oh[k]
    (* keep = "true" *) reg [9:0] e_ohc, e_ohd;   // its copies (control / data fields)
    reg          own_r;                      // word ew holds this region's key (scan)
    wire         slot_b = ended && ew < nw && tc == etm;     // shared term; a group ANDs its wdone copy
    wire [3:0]   slot_g = {4{slot_b}} & ~wdk;
    wire         slot_e = slot_g[3];
    wire         take_e = slot_e && bv[pe] && bw[pe] == ew;
    wire         late_e = slot_e && ((own_r && !take_e) || (bv[pe] && bw[pe] < ew));
    reg          slot_q;
    (* keep = "true" *) reg [8:0] slot_k;    // part-0 beat gating copies
    (* keep = "true" *) reg [8:0] tk_k;      // take copies (256-b score gating; [8] part 1)
    reg  [255:0] d0_q;                       // the taken buffer's scores
    reg  [15:0]  lv_q; reg f_q; reg late_q; reg last_q;
    reg  [275:0] hb_q;
    reg          hv_q;
    reg          p1, p1_d;
    (* keep = "true" *) reg [8:0] p1_k, p1d_k;
    reg  [15:0]  p1_lv; reg p1_f; reg p1_last;
    // header beats (identical in every region); om: no HDR / empty BEAT of an open lane
    reg  [275:0] hb_n;
    reg  [9:0]   ec, ed;
    always @* begin
        ec = e_ohc; ed = e_ohd;
        if (MUT != 6) begin
            if (om[0]) begin ec[3:1] = 3'd0; ed[3:1] = 3'd0; end
            if (om[1]) begin ec[6:4] = 3'd0; ed[6:4] = 3'd0; end
            if (om[2]) begin ec[9:7] = 3'd0; ed[9:7] = 3'd0; end
        end
        hb_n = '0;
        hb_n[19:0] = ({20{ec[0]}} & bk(ik, 2'd0, 1'b0, 1'b1, {4'd1, tg}, 256'd0)) |
                     ({20{ec[1]}} & bk(ik, 2'd1, 1'b0, 1'b1, {4'd1, tg}, 256'd0)) |
                     ({20{ec[2]}} & bk(ik, 2'd1, 1'b0, 1'b0, {4'd2, tg}, 256'd0)) |
                     ({20{ec[3]}} & bk(ik, 2'd1, 1'b1, 1'b0, 12'd0, 256'd0)) |
                     ({20{ec[4]}} & bk(ik, 2'd2, 1'b0, 1'b1, {4'd1, tg}, 256'd0)) |
                     ({20{ec[5]}} & bk(ik, 2'd2, 1'b0, 1'b0, {4'd2, tg}, 256'd0)) |
                     ({20{ec[6]}} & bk(ik, 2'd2, 1'b1, 1'b0, 12'd0, 256'd0)) |
                     ({20{ec[7]}} & bk(ik, 2'd3, 1'b0, 1'b1, {4'd1, tg}, 256'd0)) |
                     ({20{ec[8]}} & bk(ik, 2'd3, 1'b0, 1'b0, {4'd2, tg}, 256'd0)) |
                     ({20{ec[9]}} & bk(ik, 2'd3, 1'b1, 1'b0, 12'd0, 256'd0));
        hb_n[275:20] = ({256{ed[0]}} & {224'd0, 2'd0, jk, 20'({j0, 4'd0})}) |
                       ({256{ed[1]}} & {224'd0, 2'd1, jk, 20'({j1p, 4'd0})}) |
                       ({256{ed[3]}} & {4'd2, tg, 227'd0, 1'b1, 16'd0}) |
                       ({256{ed[4]}} & {224'd0, 2'd2, jk, 20'({j1p, 4'd0})}) |
                       ({256{ed[6]}} & {4'd2, tg, 227'd0, 1'b1, 16'd0}) |
                       ({256{ed[7]}} & {224'd0, 2'd3, jk, 20'({j1p, 4'd0})}) |
                       ({256{ed[9]}} & {4'd2, tg, 227'd0, 1'b1, 16'd0});
    end
    wire [20:0]  my_pos = {1'b0, ej, me_e ^ hj(ej)};
    wire [19:0]  th = 20'(t0);
    wire [15:0]  b_ej = q_d1[511] ? 16'd0 : q_d1[19:4];
    always @(posedge ck) begin : g_emit
        integer k;
        fc_set <= 8'd0; wdone_p <= 1'b0;
        own_r <= !gat && (my_pos >= 21'(jb)) && (my_pos < jend);
        // header one-hot: e_oh[k] in the cycle tc == th + k - 1 (T0 >= 2)
        e_oh <= {e_oh[8:0], ended && !wdone && tc + 20'd2 == th};
        e_ohc <= {e_oh[8:0], ended && !wdk[0] && tc + 20'd2 == th};
        e_ohd <= {e_oh[8:0], ended && !wdk[1] && tc + 20'd2 == th};
        hb_q <= hb_n; hv_q <= |ec;
        slot_q <= slot_e; slot_k <= {9{slot_e}};
        tk_k <= {9{take_e}}; take_d <= take_e;
        lv_q <= blv[pe]; f_q <= bf[pe]; late_q <= late_e; last_q <= ew == nwm1;
        for (k = 0; k < 16; k = k + 1) d0_q[16 * k +: 16] <= pe_k[k / 2] ? bs[1][16 * k +: 16] : bs[0][16 * k +: 16];
        if (hg[14]) ew <= 16'd0; else if (slot_g[0]) ew <= ew + 16'd1;
        if (hg[15]) ej <= b_ej; else if (slot_g[1]) ej <= ej + 16'd1;
        if (hg[16]) etm <= 20'(q_d1[96:81]) + 20'd9; else if (slot_g[2]) etm <= etm + 20'(pp);
        // the beat edge: part 1 follows part 0 by one edge
        p1 <= slot_q; p1_k <= {9{slot_q}}; p1_d <= p1; p1d_k <= p1_k;
        if (slot_q) begin p1_lv <= tk_k[8] ? lv_q : 16'd0; p1_f <= (tk_k[8] && f_q) || late_q || fault; p1_last <= last_q; end
        if (late_e) fc_set[2] <= 1'b1;
        if (take_e && bf[pe]) fc_set[3] <= 1'b1;
        if (k_v && !k_ready) fc_set[4] <= 1'b1;
        if (hdr_job && act) fc_set[5] <= 1'b1;
        if (hdr_go && (q_d[100:97] < 4'd2 || q_d[40:20] == 21'd0 || q_d[50:41] > 10'd512 || q_d[96:81] < 16'd2 ||
            (q_d[511] ? q_d[491:480] != 12'(64 + ((q_d[40:20] + 21'd15) >> 4)) : q_d[491:480] != 12'd64))) fc_set[6] <= 1'b1;
        if (ended && !wdone && ew == nw && !slot_q && !p1 && !p1_d) begin
            wdone <= 1'b1; wdk <= 4'hf; wdone_p <= 1'b1;
            if (iq_n != 0 || infl != 0 || aa || bv != 2'd0 || (ws != 3'd5 && ws != 3'd0)) fc_set[7] <= 1'b1;
        end
        if (hgo) begin wdone <= 1'b0; wdk <= 4'h0; end
        if (!rl[R_EOH]) begin e_oh <= 10'd0; e_ohc <= 10'd0; e_ohd <= 10'd0; hv_q <= 1'b0; end
        if (!rl[R_SLT]) begin slot_q <= 1'b0; slot_k <= 9'd0; tk_k <= 9'd0; take_d <= 1'b0; end
        if (!rl[R_P1]) begin p1 <= 1'b0; p1_k <= 9'd0; p1_d <= 1'b0; p1d_k <= 9'd0; end
        if (!rl[R_WD]) begin wdone <= 1'b0; wdk <= 4'h0; wdone_p <= 1'b0; fc_set <= 8'd0; end
    end
    // tb trace alias: the beat decision
    wire         slot = slot_e;
    // the chain register: OR of the passing beat, the header beat, part 0 (scores) and part 1 (valid / last / fault)
    wire [275:0] ins0 = bk(ik, 2'd0, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
    wire [275:0] ins1 = bk(ik, 2'd0, 1'b1, 1'b0, {11'd0, p1_f}, {4'd2, tg, 227'd0, p1_last, p1_lv});
    wire [8:0]   p1g = (MUT == 4 && me_e == 4'd0) ? p1d_k : p1_k;
    wire         p1_due = (MUT == 4 && me_e == 4'd0) ? p1_d : p1;
    always @(posedge ck) begin : g_so
        integer k;
        so[0] <= sr[0] | hv_q | slot_q | p1_due;
        for (k = 1; k < 20; k = k + 1)
            so[k] <= sr[k] | hb_q[k] | (slot_k[k / 32] & ins0[k]) | (p1g[k / 32] & ins1[k]);
        for (k = 20; k < 276; k = k + 1)
            so[k] <= sr[k] | hb_q[k] | (slot_k[k / 32] & ins0[k]) | (p1g[k / 32] & ins1[k]) | (tk_k[(k - 20) / 32] & d0_q[k - 20]);
        if (!rl[R_PIN]) so[0] <= 1'b0;
    end
    // sticky faults + status pins
    always @(posedge ck) begin
        fc <= fc | fc_set | {6'd0, fw1_r, fw0_r};
        st <= {fc, act, fault};
        if (!rl[R_FC]) begin fc <= 8'd0; st <= 10'd0; end
    end
endmodule

module dsdv_idx_e32 #(
    parameter integer NB  = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
) (
    input  wire          ck,
    input  wire [6:0]    rl,               // reset leaves: 0..3 slice columns, 4 tail, 5 ring write, 6 ring read
    input  wire          ql_v,
    input  wire [7:0]    ql_h,
    input  wire [511:0]  ql_c,
    input  wire [31:0]   ql_s,
    input  wire [15:0]   ql_w,
    input  wire [3:0]    k_vc,             // k_v copies
    input  wire [543:0]  k_key,
    output wire          o_v,
    output wire [15:0]   o_s,
    output wire          o_f
);
    localparam integer HC = 8;
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer XLAT   = FPL + 16;
    localparam integer LATE   = LAT_T + FPL * (HC - 1) + XLAT;
    wire [3:0]  cv;
    wire [127:0] csum;
    wire [3:0]  cfl;
    genvar g, h;
    generate for (g = 0; g < 4; g = g + 1) begin : g_col
        // the column's input registers (as chunk_el)
        reg rql_v; reg [7:0] rql_head; reg [NB*128-1:0] rql_codes; reg [NB*8-1:0] rql_sc; reg [15:0] rql_w;
        reg [KW-1:0] rkey;
        always @(posedge ck) begin
            rql_v <= ql_v; rql_head <= ql_h; rql_codes <= ql_c; rql_sc <= ql_s; rql_w <= ql_w; rkey <= k_key;
            if (!rl[g]) rql_v <= 1'b0;
        end
        wire qv [0:HC]; wire [7:0] qh [0:HC]; wire [NB*128-1:0] qc [0:HC]; wire [NB*8-1:0] qs [0:HC]; wire [15:0] qw [0:HC];
        wire [KW-1:0] ky [0:HC]; wire [31:0] cs [0:HC]; wire cf [0:HC];
        assign qv[0] = rql_v; assign qh[0] = rql_head; assign qc[0] = rql_codes; assign qs[0] = rql_sc; assign qw[0] = rql_w;
        assign ky[0] = rkey; assign cs[0] = 32'd0; assign cf[0] = 1'b0;
        for (h = 0; h < HC; h = h + 1) begin : g_s
`ifdef OT_IDX_HSLICE_HARD
            ot_hdc_v41x_idx_hslice u_s (.clk(ck),
`else
            ot_hdc_v41x_idx_hslice #(.NB(NB), .FPL(FPL), .FML(FML), .QL(QL)) u_s (.clk(ck),
`endif
                .rst_n(rl[g]), .hid(8'(8 * g + h)), .first(h == 0),
                .ql_v(qv[h]), .ql_head(qh[h]), .ql_codes(qc[h]), .ql_sc(qs[h]), .ql_w(qw[h]),
                .qo_v(qv[h+1]), .qo_head(qh[h+1]), .qo_codes(qc[h+1]), .qo_sc(qs[h+1]), .qo_w(qw[h+1]),
                .k_key(ky[h]), .ko_key(ky[h+1]), .cs_in(cs[h]), .cf_in(cf[h]), .cs_out(cs[h+1]), .cf_out(cf[h+1]));
        end
        reg [31:0] c_sum; reg c_fault;
        always @(posedge ck) begin c_sum <= cs[HC]; c_fault <= cf[HC]; end
        assign csum[32 * g +: 32] = c_sum;
        assign cfl[g] = c_fault;
    end endgenerate
    // c_v = k_v + 1 (input register) + LATE + 1 (output register)
    wire c_v;
    dsdv_idx_vring #(.D(LATE + 2)) u_vr (.ck(ck), .rnw(rl[5]), .rnr(rl[6]), .d(k_vc), .q(c_v));
    wire [3:0]  t_kv, t_f;
    wire [63:0] t_s;
    wire        t_v;
    // spare key lanes 1..3 of the closed NKT 4 tail: kv / keep 0, sums 0 (their outputs are unused)
    ot_hbm_idx_tail_native u_t (.clk(ck), .rst_n(rl[4]), .i_v(c_v), .i_kv(4'b0001), .i_keep(4'b0001),
        .i_sum({384'd0, csum}), .i_fault({12'd0, cfl}), .o_v(t_v), .o_kv(t_kv), .o_score(t_s), .o_fault(t_f));
    assign o_v = t_v;
    assign o_s = t_s[15:0];
    assign o_f = t_f[0];
endmodule

// ===================================================================================================================
// dsdv_idx_vring (S81-L20RD): q(t) = d(t - D) for one bit, D < 128, as a 128-entry ring (16 rows x 8 columns) with
// one-hot row / column tokens for the write and the read position (read = write - D); no flop delay line.  d comes as
// NC = 4 identical copies (32 cells each).  The cells carry no reset: q is masked until D cycles after reset.
// ===================================================================================================================
module dsdv_idx_vring #(
    parameter integer D = 106
) (
    input  wire       ck,
    input  wire       rnw,
    input  wire       rnr,
    input  wire [3:0] d,
    output wire       q
);
    initial if (D < 1 || D > 127) $fatal(1, "dsdv_idx_vring: D must be 1..127");
    localparam integer RP = 128 - D;          // read position at reset release
    reg [127:0] cell;
    reg [15:0]  wr, rr;
    reg [7:0]   wc, rc;
    reg [6:0]   wn;
    reg         warm;
    integer k;
    always @(posedge ck) begin
        for (k = 0; k < 128; k = k + 1) if (wr[k / 8] && wc[k % 8]) cell[k] <= d[k / 32];
        wc <= {wc[6:0], wc[7]}; if (wc[7]) wr <= {wr[14:0], wr[15]};
        rc <= {rc[6:0], rc[7]}; if (rc[7]) rr <= {rr[14:0], rr[15]};
        if (!warm) begin wn <= wn + 7'd1; if (wn == 7'(D - 1)) warm <= 1'b1; end
        if (!rnw) begin wr <= 16'd1; wc <= 8'd1; wn <= 7'd0; warm <= 1'b0; end
        if (!rnr) begin rr <= 16'd1 << (RP / 8); rc <= 8'd1 << (RP % 8); end
    end
    reg rq;
    always @* begin
        rq = 1'b0;
        for (k = 0; k < 128; k = k + 1) rq = rq | (cell[k] & rr[k / 8] & rc[k % 8]);
    end
    assign q = warm && rq;
endmodule
