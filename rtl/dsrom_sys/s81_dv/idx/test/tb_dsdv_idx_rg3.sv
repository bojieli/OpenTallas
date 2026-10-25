`timescale 1ps/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-IDX3R (10-20, MU.BAL.SX.3): exact + throughput gate of the NON-INLINE paired index reader dsdv_idx_rg3 at the
//   mu7 production shape -- generated from tb_dsdv_idx_rg2 (S81-L20RD3) by results/rtl/s81_idx3r_1020/mk_tb3.py:
//   8 x dsdv_idx_rg3 in two corner-strip groups (W readers 0..3, E readers 4..7) as static-slot clients of
//   16 x dsfd_ctrl_rg3 (rg2 + reader lanes); svc traffic drives the controllers' rq / rd directly.  The die's relay
//   stations are modelled as registered hops: SD[p] stations each way on reader p's 4 request + 4 response lanes
//   (pair distance 1.07 / 3.19 / 5.31 / 7.43 mm at 405 um: 3 / 8 / 13 / 18; +SDX= extra stations on every lane) and
//   XD (21) stations on the query + score chains between the W and E groups (8.5 mm crossing).
//   +SLOTHIT=1: one slice word inside the reader window (a schedule violation) -> the controller fault must FAIL it.
//   +SLICE2=1 (default): the slice phase runs again after the window (svc resumes on the controllers).
//   Former rg2 bench text (checks unchanged):
//   16 x dsfd_ctrl_rg2 (UNCHANGED regional HBM
//   controller, real CDC to ckh) + the refresh-aware per-PC HBM model ot_hdc_v41x_idx_hbm (NPC 32 = one HBM3E stack, the
//   model of the S81-SCAND / W11 reader measurements).  The die's controller takes PC-LOCAL sector addresses; the model
//   hashes a flat native address onto its PCs, so a bench adapter per PC maps (PC P, local L) to the native sector
//   s = {L[24:2], P ^ L[6:2] ^ L[11:7], L[1:0]} (pc_of(s) == P) and splits a request at 4-sector native boundaries
//   (pieces tagged with their beat offset; beats renumbered on return).  Bench-side only: the die has no adapter.
//   Reference: an independent ot_hdc_v41x_idx_engine (NK 16, the certified exact engine) scores every expected
//   candidate from the bench's own key table before the job; the chain output is decoded by the selector's REAL V
//   ingress decoder dsdv_bk_vin (dsdv_bk_v.sv) and every lane word is compared bit-exact: headers (type 1, tag, base, k,
//   qslot), BEAT words (type 2, tag, 16 BF16 scores, lane valid, last, fault flag 0), the 3 empty quarters.
//   Also checked: qo == qi delayed (2 + OH) x 8 edges + XD (every frame forwarded), a non-index frame skipped, slice traffic passing
//   the station both ways (data / beat / tag, rk count == slice requests) before the job and NO response / rk leaking
//   to the slice during it, every region's sticky fault 0 after the window end.
//   S81-L20RD3: nopen counts mismatching lane words whose in-band fault flag is 0 (a fail-OPEN word); closed_* campaign
//   cases (an over-rate window) must FAIL with nopen 0.
// Plusargs: none (parameters by -G).  Prints TB_IDXRD PASS / FAIL and a TB_IDXRD_STATS line.
// ---------------------------------------------------------------------------------------------------------------------
module tb_dsdv_idx_rg3;
    // runtime knobs (plusargs, one build serves every size / window): +N= +GATHER= +B= +PMAX= +KB= +T0= +P= +K= +SEED=
    // +SLICE=;  build-time: MUT, SRAM_MACRO, CKH_PS
    integer N = 4096;                      // scan: keys; gather: blocks (8 keys each)
    integer GATHER = 0;
    integer B = 13;                        // scan base position
    integer PMAX = 131072;                 // gather: positions drawn from [0, PMAX)
    integer KB = 64;                       // index-key base (PC-local sector)
    integer T0 = 400;
    integer P = 2;
    integer K = 512;
    integer SEED = 1;
    integer SLICE = 1;
    integer TRW = 0, TRN = 0;
    integer OPEN = 0;                      // S81-L20DIE: spec om (open lanes 1..3 -> no HDR / empty BEAT expected)
    integer SLOTHIT = 0, SLICE2 = 1;
    initial begin
        void'($value$plusargs("TRW=%d", TRW)); void'($value$plusargs("TRN=%d", TRN));
        void'($value$plusargs("N=%d", N)); void'($value$plusargs("GATHER=%d", GATHER)); void'($value$plusargs("B=%d", B));
        void'($value$plusargs("PMAX=%d", PMAX)); void'($value$plusargs("KB=%d", KB)); void'($value$plusargs("T0=%d", T0));
        void'($value$plusargs("P=%d", P)); void'($value$plusargs("K=%d", K)); void'($value$plusargs("SEED=%d", SEED));
        void'($value$plusargs("SLICE=%d", SLICE)); void'($value$plusargs("OPEN=%d", OPEN));
        void'($value$plusargs("SLOTHIT=%d", SLOTHIT)); void'($value$plusargs("SLICE2=%d", SLICE2));
    end
    parameter integer MUT = 0;
    parameter bit SRAM_MACRO = 1;
    parameter integer CKH_PS = 900;
    // S81-L20 10-19: request-depth probe (default 8 / 8 = the record controller and reader, byte-identical behaviour):
    // DQC = dsfd_ctrl_rg2 request buffer entries a PC, DQR = the reader's outstanding-request cap (<= DQC - 1 so a
    // slice request can never meet a full owner FIFO)
    parameter integer DQC = 8;
    parameter integer DQR = 24;            // reader budget = controller landing FIFO entries (RFD)
    parameter integer CMUT = 0;            // dsfd_ctrl_rg3 MUT
    parameter integer XD = 21;             // W -> E chain crossing stations
    parameter integer SDX = 0;             // extra lane stations (latency sweep)
    parameter integer SQD = 256;
    parameter integer IQD = 512;
    parameter integer OH = 2;              // reader output relay hops (S81-COLLECT2/L20KIT): q / s chain +OH a reader
    parameter integer RH = 2;
    parameter integer IH = 0;              // STW-S81c-COLLA 10-22: reader input relay hops (q / s chain +IH a reader)
    parameter integer KR = 0;              // reader engine-input relay hops (engine latency +KR, absorbed by T0)              // reader response relay hops (lane latency +RH, absorbed by T0)
    localparam integer NRD = 8;
    localparam integer R = 16, MW = 1 << 20, NWMAX = 16384, IK = 5, TAG = 8'h5A, SL0 = 20000, NS = 6;

    // ------------------------------------------------------------------ clocks / reset
    reg ck = 0, ckh = 0, rst = 0;
    always begin #417 ck = 1; #416 ck = 0; end
    always #(CKH_PS / 2) ckh = ~ckh;
    longint cyc = 0;
    integer fail = 0, nerr = 0, nopen = 0;   // nopen: mismatching lane words WITHOUT the in-band fault flag (fail-open)
    always @(posedge ck) cyc <= cyc + 1;

    function automatic [3:0] hj(input [15:0] j); hj = j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12]; endfunction
    function automatic [31:0] mix(input longint a);
        longint z; z = a * 64'h9E3779B97F4A7C15 + 64'(SEED) * 64'hBF58476D1CE4E5B9;
        z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9; z = (z ^ (z >> 27)) * 64'h94D049BB133111EB; z = z ^ (z >> 31);
        mix = z[31:0];
    endfunction
    function automatic [543:0] key(input longint p);              // {4 UE8M0 scales, 128 E2M1 codes}
        reg [543:0] k_; integer w;
        for (w = 0; w < 16; w = w + 1) k_[32 * w +: 32] = mix(p * 64 + w);
        for (w = 0; w < 4; w = w + 1) k_[512 + 8 * w +: 8] = 8'(120 + (mix(p * 64 + 32 + w) % 15));
        key = k_;
    endfunction
    function automatic [29:0] xl(input [29:0] l, input [4:0] pc);
        xl = {l[24:2], pc ^ l[6:2] ^ l[11:7], l[1:0]};
    endfunction

    // ------------------------------------------------------------------ query
    reg [511:0] qc [0:31]; reg [31:0] qs [0:31]; reg [15:0] qw [0:31];
    integer h_;
    initial begin #0; for (h_ = 0; h_ < 32; h_ = h_ + 1) begin : g_q
        integer w; reg [15:0] wl [0:5];
        wl[0] = 16'h3F80; wl[1] = 16'hBF00; wl[2] = 16'h3E80; wl[3] = 16'h4000; wl[4] = 16'h3F00; wl[5] = 16'hBE40;
        for (w = 0; w < 16; w = w + 1) qc[h_][32 * w +: 32] = mix(64'h7000_0000 + h_ * 64 + w);
        for (w = 0; w < 4; w = w + 1) qs[h_][8 * w +: 8] = 8'(124 + (mix(64'h7100_0000 + h_ * 8 + w) % 7));
        qw[h_] = wl[mix(64'h7200_0000 + h_) % 6];
    end end

    // ------------------------------------------------------------------ job geometry + gather blocks
    integer j0, j1, nw, nlw;
    reg [16:0] blk [0:8191];
    integer o_, b_;
    initial begin
        #0;
        if (GATHER != 0) begin
            b_ = mix(64'h7300_0000) % 64;
            for (o_ = 0; o_ < N; o_ = o_ + 1) begin                 // strictly ascending, gaps 1..(2 PMAX / 8 N)
                blk[o_] = 17'(b_);
                b_ = b_ + 1 + (mix(64'h7400_0000 + o_) % ((2 * PMAX) / (8 * N) > 1 ? (2 * PMAX) / (8 * N) - 1 : 1));
            end
            j0 = 0; nw = (N + 1) / 2; j1 = nw - 1; nlw = (N + 15) / 16;
        end else begin
            j0 = B / 16; j1 = (B + N - 1) / 16; nw = j1 - j0 + 1; nlw = 0;
        end
    end
    function automatic longint pos_of(input integer w, input integer i, output bit v);   // candidate of word w lane i
        longint c, p;
        if (GATHER != 0) begin
            c = 16 * w + i; v = (c >> 3) < N; p = v ? 8 * longint'(blk[c >> 3]) + (c & 7) : 0;
        end else begin
            p = 16 * (j0 + w) + i; v = p >= B && p < B + N;
        end
        pos_of = p;
    endfunction

    // ------------------------------------------------------------------ DUT chain
    reg  [512:0] qin = 0;
    wire [512:0] qch [0:NRD];
    wire [275:0] sch [0:NRD];
    wire [561:0] rd_c [0:R-1], rd_s [0:R-1];
    wire [91:0]  lrq_r [0:R-1], lrq_c [0:R-1];      // request lanes at the reader / at the controller
    wire [543:0] lrd_c [0:R-1], lrd_r [0:R-1];      // response lanes at the controller / at the reader
    function automatic integer sd_of(input integer p_); sd_of = SDX + ((p_ < 4) ? 3 + 5 * p_ : 3 + 5 * (7 - p_)); endfunction
    wire [512:0] qx; wire [275:0] sx;              // W -> E crossing outputs
    // S81/PORTFIX-FLT 10-25: the reader's port is the 1-bit sticky fault (was st[9:0] = {fc, act, fault}); act is tapped
    wire [NRD-1:0] flt, act_v;
    reg  [681:0] rq_tb [0:R-1];
    assign qch[0] = qin;
    assign sch[0] = 276'd0;
    // PHY buses (32 PCs)
    wire [31:0] k_v, k_rdy, k_we, k_wr_done, kr_v, kr_rdy;
    wire [32*30-1:0] k_addr; wire [32*4-1:0] k_len, kr_beat; wire [32*17-1:0] k_tag, kr_tag;
    wire [32*256-1:0] k_wdata, kr_data; wire [32*32-1:0] k_wstrb;
    genvar r;
    generate for (r = 0; r < NRD; r = r + 1) begin : g_p
        wire [512:0] qi_ = (r == 4) ? qx : qch[r];
        wire [275:0] si_ = (r == 4) ? sx : sch[r];
        dsdv_idx_rg3 #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .SQD(SQD), .IQD(IQD), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (
            .ck(ck), .rst(rst), .sid(4'(2 * r)), .qi(qi_), .qo(qch[r + 1]), .si(si_), .so(sch[r + 1]),
            .rqo({lrq_r[2 * r + 1], lrq_r[2 * r]}), .rri({lrd_r[2 * r + 1], lrd_r[2 * r]}), .fault(flt[r]));
        assign act_v[r] = u.act;
        // relay stations (registered hops) on the lanes of both controllers of the pair
        tb_idx3_dly #(.W(92),  .D(sd_of(r))) u_q0 (.ck(ck), .d(lrq_r[2 * r]),     .q(lrq_c[2 * r]));
        tb_idx3_dly #(.W(92),  .D(sd_of(r))) u_q1 (.ck(ck), .d(lrq_r[2 * r + 1]), .q(lrq_c[2 * r + 1]));
        tb_idx3_dly #(.W(544), .D(sd_of(r))) u_d0 (.ck(ck), .d(lrd_c[2 * r]),     .q(lrd_r[2 * r]));
        tb_idx3_dly #(.W(544), .D(sd_of(r))) u_d1 (.ck(ck), .d(lrd_c[2 * r + 1]), .q(lrd_r[2 * r + 1]));
    end endgenerate
    tb_idx3_dly #(.W(513), .D(XD)) u_xq (.ck(ck), .d(qch[4]), .q(qx));
    tb_idx3_dly #(.W(276), .D(XD)) u_xs (.ck(ck), .d(sch[4]), .q(sx));
    generate for (r = 0; r < R; r = r + 1) begin : g_r
        wire ck_o_unused;
        dsfd_ctrl_rg3 #(.DQ(DQC), .RFD(DQR), .MUT(CMUT)) u_c (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(rq_tb[r]), .rd(rd_c[r]),
            .ck_o(ck_o_unused), .rrq(lrq_c[r]), .rrd(lrd_c[r]),
            .k_v(k_v[2 * r +: 2]), .k_rdy(k_rdy[2 * r +: 2]), .k_addr(k_addr[60 * r +: 60]), .k_len(k_len[8 * r +: 8]),
            .k_tag(k_tag[34 * r +: 34]), .k_we(k_we[2 * r +: 2]), .k_wdata(k_wdata[512 * r +: 512]),
            .k_wstrb(k_wstrb[64 * r +: 64]), .k_wr_done(k_wr_done[2 * r +: 2]), .kr_v(kr_v[2 * r +: 2]),
            .kr_rdy(kr_rdy[2 * r +: 2]), .kr_tag(kr_tag[34 * r +: 34]), .kr_beat(kr_beat[8 * r +: 8]),
            .kr_data(kr_data[512 * r +: 512]));
        assign rd_s[r] = rd_c[r];
    end endgenerate

    // ------------------------------------------------------------------ PC adapters + HBM model
    wire [31:0] m_v, m_rdy;
    wire [32*30-1:0] m_addr; wire [32*4-1:0] m_len, m_beat; wire [32*20-1:0] m_tag, m_rtag;
    genvar pc;
    generate for (pc = 0; pc < 32; pc = pc + 1) begin : g_a
        reg busy = 0; reg [29:0] la; reg [3:0] rem, off; reg [16:0] tg_; reg we_;
        wire [3:0] plen = (4'(4) - 4'(la[1:0])) < rem ? (4'(4) - 4'(la[1:0])) : rem;
        assign k_rdy[pc] = rst && !busy;
        assign m_v[pc] = busy;
        assign m_addr[30 * pc +: 30] = xl(la, 5'(pc));
        assign m_len[4 * pc +: 4] = plen;
        assign m_tag[20 * pc +: 20] = {off[2:0], tg_};
        always @(posedge ckh)
            if (!rst) busy <= 0;
            else if (!busy && k_v[pc]) begin
                busy <= 1; la <= k_addr[30 * pc +: 30]; rem <= k_len[4 * pc +: 4]; off <= 0; tg_ <= k_tag[17 * pc +: 17];
                we_ <= k_we[pc];
                if (k_we[pc] || k_len[4 * pc +: 4] == 0) begin $display("TB_IDXRD FAIL write / zero-length request on PC %0d", pc); fail = 1; end
            end else if (busy && m_rdy[pc]) begin
                la <= la + 30'(plen); off <= off + plen; rem <= rem - plen; if (rem == plen) busy <= 0;
            end
        assign kr_tag[17 * pc +: 17] = m_rtag[20 * pc +: 17];
        assign kr_beat[4 * pc +: 4] = m_beat[4 * pc +: 4] + 4'(m_rtag[20 * pc + 17 +: 3]);
        assign k_wr_done[pc] = 1'b0;
    end endgenerate
    ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .DW(256), .MEM_WORDS(MW), .TAGW(20), .LENW(4), .BEATW(4), .CLK_PS(CKH_PS),
                          .QD(64), .REFPB(3), .MEM_MODE(0)) u_hbm (
        .clk(ckh), .rst_n(rst), .req_v(m_v), .req_rdy(m_rdy), .req_addr(m_addr), .req_len(m_len), .req_tag(m_tag),
        .req_we(32'd0), .req_wdata({32*256{1'b0}}), .req_wstrb({32*32{1'b0}}), .wr_done(),
        .rsp_v(kr_v), .rsp_rdy(kr_rdy), .rsp_tag(m_rtag), .rsp_beat(m_beat), .rsp_data(kr_data));

    // ------------------------------------------------------------------ HBM preload (keys at the compiler layout, slice data)
    task automatic place(input longint p);
        reg [543:0] k_; integer j, i, rg, g, pcl, n, c, Pp; reg [29:0] a;
        k_ = key(p); j = p >> 4; i = p & 15; rg = i ^ hj(16'(j)); g = j >> 4; pcl = g & 1; n = g >> 1; c = j & 15;
        Pp = 2 * rg + pcl; a = 30'(KB + 34 * n);
        u_hbm.mem[xl(a + 30'(2 * c), 5'(Pp)) % MW] = k_[255:0];
        u_hbm.mem[xl(a + 30'(2 * c + 1), 5'(Pp)) % MW] = k_[511:256];
        u_hbm.mem[xl(a + 30'(32 + (c >> 3)), 5'(Pp)) % MW][32 * (c & 7) +: 32] = k_[543:512];
    endtask
    function automatic [255:0] spat(input integer l, input integer p_);
        spat = {8{mix(64'h7500_0000 + l * 64 + p_)}};
    endfunction
    initial begin : g_pre
        integer w, i, l, p_; bit v; longint p;
        #1;
        for (w = 0; w < nw; w = w + 1) for (i = 0; i < 16; i = i + 1) begin p = pos_of(w, i, v); if (v) place(p); end
        for (p_ = 0; p_ < 32; p_ = p_ + 1) for (l = SL0; l < SL0 + 64; l = l + 1) u_hbm.mem[xl(30'(l), 5'(p_)) % MW] = spat(l, p_);
    end

    // ------------------------------------------------------------------ reference engine (expected scores)
    reg rq_v = 0; reg [7:0] rq_h; reg [511:0] rq_c_; reg [31:0] rq_s_; reg [15:0] rq_w_;
    reg rk_v = 0; reg [15:0] rk_kv; reg [16*544-1:0] rk_key; wire rk_rdy;
    wire ro_v; wire [15:0] ro_kv, ro_f; wire [255:0] ro_s;
    ot_hdc_v41x_idx_engine #(.NK(16), .IH(32), .NB(4), .FD(64)) u_ref (
        .clk(ck), .rst_n(rst), .ql_v(rq_v), .ql_head(rq_h), .ql_codes(rq_c_), .ql_sc(rq_s_), .ql_w(rq_w_),
        .k_valid(rk_v), .k_ready(rk_rdy), .k_kv(rk_kv), .k_keep(16'hFFFF), .k_key(rk_key),
        .o_valid(ro_v), .o_ready(1'b1), .o_kv(ro_kv), .o_score(ro_s), .o_fault(ro_f),
        .cnt_keys_scored(), .cnt_headsums_fused(), .cnt_faults());
    reg [255:0] exp_s [0:NWMAX-1]; reg [15:0] exp_v [0:NWMAX-1];
    integer ro_n = 0;
    always @(posedge ck) if (ro_v) begin
        exp_s[ro_n] <= ro_s; exp_v[ro_n] <= ro_kv; ro_n <= ro_n + 1;
        if ((ro_f & ro_kv) != 0) begin $display("TB_IDXRD FAIL reference score fault word %0d (bench data)", ro_n); fail = 1; end
    end

    // ------------------------------------------------------------------ output decode (selector's V ingress) + checks
    wire [4*515-1:0] ln; wire dr_v_u, vin_f; wire [7:0] dr_n_u, dr_d_u;
    dsdv_bk_vin #(.V(276), .MUT(0)) u_vin (.clk(ck), .rst_n(rst), .ik(3'(IK)), .uid(8'hFF), .dl_nv(sch[NRD][0]),
        .dl_n(sch[NRD]), .dl_sv(1'b0), .dl_s(276'd0), .lanes(ln), .dr_v(dr_v_u), .dr_n(dr_n_u), .dr_d(dr_d_u), .fault(vin_f));
    integer lw_n [0:3];
    longint t_hdr0 = -1, t_end = -1, t_last = -1;
    initial for (int l = 0; l < 4; l++) lw_n[l] = 0;
    function automatic [511:0] hdr_w(input integer base, input integer q);
        hdr_w = {4'd1, 8'(TAG), 244'd0, 224'd0, 2'(q), 10'(K), 20'(base)};
    endfunction
    always @(posedge ck) if (rst) begin : g_chk
        integer l, i; reg [511:0] d, e; reg [255:0] m;
        for (l = 0; l < 4; l = l + 1) if (ln[515 * l]) begin
            d = ln[515 * l + 1 +: 512];
            if (lw_n[l] == 0) e = hdr_w(l == 0 ? 16 * j0 : 16 * (j1 + 1), l);
            else if (l != 0) e = {4'd2, 8'(TAG), 227'd0, 1'b1, 16'd0, 256'd0};
            else begin
                for (i = 0; i < 16; i = i + 1) m[16 * i +: 16] = {16{exp_v[lw_n[0] - 1][i]}};
                e = {4'd2, 8'(TAG), 227'd0, 1'(lw_n[0] == nw), exp_v[lw_n[0] - 1], exp_s[lw_n[0] - 1] & m};
            end
            if (d !== e || ln[515 * l + 514] || (l != 0 && lw_n[l] > 1) || (l == 0 && lw_n[0] > nw) ||
                (l != 0 && OPEN[l - 1])) begin
                nerr = nerr + 1;
                if (!ln[515 * l + 514]) nopen = nopen + 1;
                if (nerr <= 8) $display("TB_IDXRD MISMATCH cyc %0d lane %0d word %0d fault %0d got %h exp %h", cyc, l,
                                        lw_n[l], ln[515 * l + 514], d, e);
            end
            lw_n[l] <= lw_n[l] + 1;
            if (l == 0 && lw_n[0] == nw) t_last <= cyc;
        end
    end

    // ------------------------------------------------------------------ qo forwarding check
    reg [512:0] qdl [0:63];
    integer qerr = 0;
    always @(posedge ck) begin : g_qf
        integer i;
        qdl[0] <= qin; for (i = 1; i < 64; i = i + 1) qdl[i] <= qdl[i - 1];
        if (rst && cyc > 80 && qch[NRD][0] !== qdl[(2 + OH + IH) * NRD + XD - 1][0] || (qch[NRD][0] && qch[NRD] !== qdl[(2 + OH + IH) * NRD + XD - 1])) qerr = qerr + 1;
    end

    // ------------------------------------------------------------------ slice traffic (station pass-through)
    integer s_rv [0:R-1][0:1], s_rk [0:R-1][0:1], s_exp [0:R-1][0:1], s_rkx [0:R-1][0:1], s_err = 0;
    reg job_on = 0;
    initial for (int a = 0; a < R; a++) begin
        for (int b = 0; b < 2; b++) begin s_rv[a][b] = 0; s_rk[a][b] = 0; s_exp[a][b] = 0; s_rkx[a][b] = 0; end
        rq_tb[a] = 682'd0;
    end
    always @(posedge ck) if (rst) begin : g_sl
        integer a, b; reg [16:0] t; reg [3:0] bt; integer k_, ln_;
        for (a = 0; a < R; a = a + 1) for (b = 0; b < 2; b = b + 1) begin
            if (rd_s[a][280 * b + 277]) begin
                t = rd_s[a][280 * b + 256 +: 17]; bt = rd_s[a][280 * b + 273 +: 4];
                k_ = t[9:0]; ln_ = 1 + (k_ % 4);
                s_rv[a][b] = s_rv[a][b] + 1;
                if (job_on || t[16:15] != 2'b00 || t[14:11] != 4'(a) || t[10] != b || bt >= 4'(ln_) ||
                    rd_s[a][280 * b +: 256] !== spat(SL0 + 8 * k_ + bt, 2 * a + b)) begin
                    s_err = s_err + 1;
                    if (s_err <= 4) $display("TB_IDXRD SLICE-RSP-ERR cyc %0d r %0d pc %0d tag %h beat %0d job %0d", cyc, a, b, t, bt, job_on);
                end
            end
            if (rd_s[a][280 * b + 278]) begin
                s_rk[a][b] = s_rk[a][b] + 1;
                if (job_on) begin s_err = s_err + 1; if (s_err <= 4) $display("TB_IDXRD SLICE-RK-LEAK cyc %0d r %0d pc %0d", cyc, a, b); end
            end
        end
    end

    task automatic slice_phase();
        integer k_, a, b, ln_;
        for (k_ = 0; k_ < NS; k_ = k_ + 1) begin
            @(negedge ck);
            for (a = 0; a < R; a = a + 1) for (b = 0; b < 2; b = b + 1) begin
                ln_ = 1 + (k_ % 4);
                rq_tb[a][341 * b +: 341] = {256'd0, 32'd0, {2'b00, 4'(a), 1'(b), 10'(k_)}, 4'(ln_), 30'(SL0 + 8 * k_), 1'b0, 1'b1};
                s_exp[a][b] = s_exp[a][b] + ln_;
                s_rkx[a][b] = s_rkx[a][b] + 1;
            end
            @(negedge ck); for (a = 0; a < R; a = a + 1) rq_tb[a] = 682'd0;
        end
        repeat (1500) @(posedge ck);
        for (a = 0; a < R; a = a + 1) for (b = 0; b < 2; b = b + 1)
            if (s_rv[a][b] != s_exp[a][b] || s_rk[a][b] != s_rkx[a][b]) begin
                s_err = s_err + 1;
                if (s_err <= 8) $display("TB_IDXRD SLICE-COUNT-ERR r %0d pc %0d rv %0d/%0d rk %0d/%0d", a, b, s_rv[a][b], s_exp[a][b], s_rk[a][b], s_rkx[a][b]);
            end
    endtask
    // ------------------------------------------------------------------ stimulus
    function automatic [511:0] job_hdr();
        reg [511:0] h; integer len;
        len = (GATHER != 0) ? 64 + nlw : 64;
        h = 512'd0;
        h[511:508] = (GATHER != 0) ? 4'd8 : 4'd4; h[502:495] = 8'(TAG); h[491:480] = 12'(len); h[458:449] = 10'd3;
        h[19:0] = (GATHER != 0) ? 20'd0 : 20'(B); h[40:20] = 21'(N); h[50:41] = 10'(K); h[80:51] = 30'(KB);
        h[96:81] = 16'(T0); h[100:97] = 4'(P); h[103:101] = 3'(IK); h[106:104] = 3'(OPEN);
        job_hdr = h;
    endfunction
    initial begin : g_run
        integer w, i, a, b, k_, ln_; bit v; longint p; reg [16*544-1:0] kk; reg [15:0] kv;
        repeat (20) @(posedge ck);
        rst = 1;
        repeat (40) @(posedge ck);
        // reference: q load, then every expected word
        for (i = 0; i < 32; i = i + 1) begin
            @(negedge ck); rq_v = 1; rq_h = 8'(i); rq_c_ = qc[i]; rq_s_ = qs[i]; rq_w_ = qw[i];
        end
        @(negedge ck); rq_v = 0;
        repeat (6) @(negedge ck);
        for (w = 0; w < nw; w = w + 1) begin
            for (i = 0; i < 16; i = i + 1) begin p = pos_of(w, i, v); kv[i] = v; kk[544 * i +: 544] = v ? key(p) : 544'd0; end
            rk_kv = kv; rk_key = kk; rk_v = 1;
            @(posedge ck); while (!rk_rdy) @(posedge ck);
            @(negedge ck);
        end
        rk_v = 0;
        while (ro_n < nw) @(posedge ck);
        // slice phase: NS reads per PC, tags [16:15] = 0
        if (SLICE != 0) slice_phase();
        job_on = 1;
        // a non-index frame (type 1, len 3): skipped by every region, forwarded
        @(negedge ck); qin = {512'd0, 1'b1}; qin[512:509] = 4'd1; qin[492:481] = 12'd3;
        for (i = 0; i < 3; i = i + 1) begin @(negedge ck); qin = {{16{32'hA5A5_0000 + 32'(i)}}, 1'b1}; end
        @(negedge ck); qin = 0;
        repeat (5) @(negedge ck);
        // the index job
        qin = {job_hdr(), 1'b1}; t_hdr0 = cyc;
        for (i = 0; i < 32; i = i + 1) begin
            @(negedge ck); qin = {qc[i], 1'b1};
            @(negedge ck); qin = {464'd0, qw[i], qs[i], 1'b1};
        end
        for (w = 0; w < nlw; w = w + 1) begin
            @(negedge ck); qin = 0; qin[0] = 1'b1;
            for (i = 0; i < 16; i = i + 1) if (16 * w + i < N) qin[1 + 32 * i +: 17] = blk[16 * w + i];
        end
        @(negedge ck); qin = 0; t_end = cyc;
        // SLOTHIT: one slice read on controller 0 PC 0 inside the reader window (its rq is a reader slot there now)
        if (SLOTHIT != 0) begin
            repeat (40) @(negedge ck);
            rq_tb[0][340:0] = {256'd0, 32'd0, 17'h00123, 4'd1, 30'(SL0), 1'b0, 1'b1};
            @(negedge ck); rq_tb[0] = 682'd0;
        end
        // wait for the window: T0 + 10 + P nw after END at the first region, + 32 chain edges + decode
        while (cyc < t_end + T0 + 10 + P * nw + 200 && lw_n[0] <= nw) @(posedge ck);
        repeat (100) @(posedge ck);
        for (a = 0; a < NRD; a = a + 1) if (flt[a] || act_v[a]) begin
            fail = 1; $display("TB_IDXRD reader %0d fault %b active %b", a, flt[a], act_v[a]);
        end
        for (i = 0; i < 4; i = i + 1) if (lw_n[i] != (i == 0 ? nw + 1 : (OPEN[i - 1] ? 0 : 2))) begin
            fail = 1; $display("TB_IDXRD lane %0d words %0d expected %0d", i, lw_n[i], i == 0 ? nw + 1 : (OPEN[i - 1] ? 0 : 2));
        end
        if (vin_f) begin fail = 1; $display("TB_IDXRD selector V-ingress protocol fault"); end
        for (a = 0; a < R; a = a + 1) if (rd_c[a][561] || !rd_c[a][560]) begin
            fail = 1; $display("TB_IDXRD controller %0d status {fault, live} %b", a, rd_c[a][561:560]);
        end
        job_on = 0;
        if (SLICE != 0 && SLICE2 != 0) slice_phase();
        if (nerr != 0 || qerr != 0 || s_err != 0) fail = 1;
        $display("TB_IDXRD_STATS3 sdx %0d xd %0d dqr %0d cmut %0d slothit %0d", SDX, XD, DQR, CMUT, SLOTHIT);
        $display("TB_IDXRD_STATS gather %0d N %0d keys %0d words %0d T0 %0d P %0d mut %0d sram %0d ckh %0d hdr_to_last %0d end_to_last %0d nerr %0d nopen %0d qerr %0d slice_err %0d",
                 GATHER, N, GATHER != 0 ? 8 * N : N, nw, T0, P, MUT, SRAM_MACRO, CKH_PS, t_last - t_hdr0, t_last - t_end, nerr, nopen, qerr, s_err);
        if (fail) $display("TB_IDXRD FAIL"); else $display("TB_IDXRD PASS");
        $finish;
    end
endmodule

// registered hops (relay stations) of the bench's die-link model; D = 0 is a wire
module tb_idx3_dly #(parameter integer W = 1, parameter integer D = 1) (input wire ck, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (D == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        reg [W-1:0] sr [0:D-1];
        integer i;
        initial for (i = 0; i < D; i = i + 1) sr[i] = '0;
        always @(posedge ck) begin sr[0] <= d; for (i = 1; i < D; i = i + 1) sr[i] <= sr[i - 1]; end
        assign q = sr[D-1];
    end endgenerate
endmodule
