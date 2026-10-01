`timescale 1ns/1ps
// Selected-CKV path of an indexed DeepSeek-V4.1 layer, end to end into the attention engine:
//   index final-select output (ot_hdc_v41x_sel out ports, 4 quarters x 16 lanes)
//     -> ot_chip_v41x_ckv_sel_ids (rank table + ownership)
//     -> ot_chip_v41x_ckv_sel_fetch x 4 dies (owned rows; PIPE selected-CKV DMA slots; behavioural HBM stacks)
//     -> all-gather links (behavioural: latency + row interval) -> die 0's ot_chip_v41x_ckv_sel_collect
//     -> ot_chip_v41x_ckv_stream_merge (+ window rows) -> ot_hdc_v41x_attn (ENGINE = 1) or a row checker (ENGINE = 0).
// Driven by tools/v41_ckv_sel_attn_vectors.py; vectors in +dir=<path>:
//   cfg.hex    32-bit words: wcount, nsel, npub, nhbm, T, qcount[0..3], base[0..3], count[0..3]
//   sel.hex    selected ids, rank order (the golden's sorted top-k)
//   win.hex    window rows, 4,224-bit packed FP8 (oldest first)
//   hkey.hex / hdat.hex   HBM sectors: key {die[1:0], stack[1:0], addr[29:0]}, 256-bit data (every die's copy of its rows)
//   kv.hex     the expected engine rows (16 x 265-bit group words) in golden row order
//   q.hex, p.hex, sc.hex, pv.hex   as tb_hdc_v41x_attn (ENGINE = 1)
// Plusargs: +lat=<HBM cycles> +llink=<board link cycles> +lucie=<die-1 link cycles> +ri=<cycles per row on a board link>
//           +seldelay=<cycles before the first selected id> +bub=<percent bubbles on sources/credits> +seed=<n>
// Prints  CKVSEL ...  (cycles and counters) and  V41XATTN ... / CKVROWS ... (checks).
module tb_chip_v41x_ckv_sel_attn (input wire clk);
    parameter integer H = 16;
    parameter integer D = 512;
    parameter integer TD = 32;
    parameter integer NL = 4;
    parameter integer TROWS = 640;
    parameter integer PWORDS = 2;
    parameter integer ENGINE = 1;
    parameter integer NSLOT = 64;
    parameter integer SCAN = 0;
    parameter integer WIDE = 0;            // 1: ot_chip_v41x_ckv_pc_fetch (PPS ports per stack, SPP slots per port)
    parameter integer PPS = 4;
    parameter integer SPP = 16;
    parameter integer SRAM_MACRO = 0;            // 1: fetch scans the whole rank table instead of its owned list
    parameter integer NSEL = 512;          // capacity of sel.hex
    parameter integer NHBM = 8192;         // capacity of the HBM image
    parameter integer MAXCYC = 400000;
    parameter integer P_DELAY = 0;
    localparam integer K = 512, KW = 10, POS_W = 21, SEC_W = 30, HAW = 30;
    localparam integer S = D / TD;
    localparam integer NT = NL * S;
    localparam integer DPT = D / NT;
    localparam integer G = D / 32;
    localparam integer ROWW = G * 265;
    localparam integer R = TD / H;
    localparam integer NPD = WIDE ? 4 * PPS : 4;          // HBM ports per die
    localparam integer NQ = 4 * NPD;
    localparam integer SW = WIDE ? ((SPP > 1) ? $clog2(SPP) : 1) : $clog2(NSLOT), TAGW = SW + 4;

    // ---------------- vectors ----------------
    reg [31:0] cfg [0:31];
    reg [31:0] selm [0:NSEL-1];
    reg [4223:0] winm [0:127];
    reg [63:0] hkey [0:NHBM-1];
    reg [255:0] hdat [0:NHBM-1];
    reg [ROWW-1:0] kvm [0:639];
    reg [D*16-1:0] qm [0:H-1];
    reg [TD*16-1:0] pm [0:639];
    reg [H*33-1:0] scm [0:639];
    reg [H*33-1:0] pvm [0:D-1];
    reg [255:0] hbm [longint];
    reg [1023:0] dir;
    integer seed = 1, lat = 100, llink = 142, lucie = 11, ri = 2, seldelay = 0, bubp = 0;
    integer wcount, nsel, npub, nhbm, T;
    integer qcnt [0:3];
    integer ii;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("lat=%d", lat)) ;
        if ($value$plusargs("llink=%d", llink)) ;
        if ($value$plusargs("lucie=%d", lucie)) ;
        if ($value$plusargs("ri=%d", ri)) ;
        if ($value$plusargs("seldelay=%d", seldelay)) ;
        if ($value$plusargs("bub=%d", bubp)) ;
        $readmemh({dir, "/cfg.hex"}, cfg);
        wcount = cfg[0]; nsel = cfg[1]; npub = cfg[2]; nhbm = cfg[3]; T = cfg[4];
        for (ii = 0; ii < 4; ii = ii + 1) qcnt[ii] = cfg[5 + ii];
        if (nsel > 0) $readmemh({dir, "/sel.hex"}, selm, 0, nsel - 1);
        if (wcount > 0) $readmemh({dir, "/win.hex"}, winm, 0, wcount - 1);
        $readmemh({dir, "/hkey.hex"}, hkey, 0, nhbm - 1);
        $readmemh({dir, "/hdat.hex"}, hdat, 0, nhbm - 1);
        for (ii = 0; ii < nhbm; ii = ii + 1) hbm[hkey[ii]] = hdat[ii];
        $readmemh({dir, "/kv.hex"}, kvm, 0, T - 1);
        if (ENGINE != 0) begin
            $readmemh({dir, "/q.hex"}, qm);
            $readmemh({dir, "/p.hex"}, pm, 0, (T + R - 1) / R - 1);
            $readmemh({dir, "/sc.hex"}, scm, 0, T - 1);
            $readmemh({dir, "/pv.hex"}, pvm);
        end
        $urandom(seed);
    end
    function automatic bit bub();
        bub = (bubp > 0) && (($urandom % 100) < bubp);
    endfunction

    reg rst_n = 1'b0;
    integer cyc = 0;
    wire [4*SEC_W-1:0] rbase = {30'(cfg[12]), 30'(cfg[11]), 30'(cfg[10]), 30'(cfg[9])};
    wire [4*SEC_W-1:0] rcount = {30'(cfg[16]), 30'(cfg[15]), 30'(cfg[14]), 30'(cfg[13])};

    // ---------------- selected-ID source: the final select's four output ports ----------------
    reg [3:0] s_valid = 0, s_last = 0; reg [4*16-1:0] s_lv = 0; reg [4*16*20-1:0] s_idx = 0;
    wire [3:0] s_ready;
    integer qsent [0:3];            // entries of quarter q already sent
    integer qbase [0:3];
    reg [3:0] qclosed = 0;
    reg job_go = 0;                 // one-cycle job start
    reg id_clr = 0;
    wire [KW-1:0] id_count; wire id_done; wire [31:0] id_cycles;
    wire [8*KW-1:0] rd_rank; wire [8*POS_W-1:0] rd_gid; wire [16-1:0] rd_die, rd_stack; wire [8*POS_W-1:0] rd_local;
    wire id_fault; wire [3:0] id_fc;
    wire [4*KW-1:0] own_count, own_idx, own_rank; wire [4*POS_W-1:0] own_gid;
    ot_chip_v41x_ckv_sel_ids #(.NRD(8), .OWN(4'b1111), .RDREG(WIDE != 0)) u_ids (
        .clk(clk), .rst_n(rst_n), .clr(id_clr), .exp_n(KW'(nsel)),
        .s_valid(s_valid), .s_ready(s_ready), .s_last(s_last), .s_lv(s_lv), .s_idx(s_idx),
        .count(id_count), .done(id_done), .done_cycle_count(id_cycles),
        .rd_rank(rd_rank), .rd_gid(rd_gid), .rd_die(rd_die), .rd_stack(rd_stack), .rd_local(rd_local),
        .own_count(own_count), .own_idx(own_idx), .own_rank(own_rank), .own_gid(own_gid),
        .fault(id_fault), .fault_code(id_fc));

    // ---------------- four dies' owned-row fetch + HBM stacks ----------------
    wire [3:0] f_ready, f_done, f_fault, f_ov;
    wire [4*KW-1:0] f_rank; wire [4*POS_W-1:0] f_gid; wire [4*2304-1:0] f_row;
    reg [3:0] f_or;
    wire [NQ-1:0] mv; reg [NQ-1:0] mrdy = 0; wire [NQ*HAW-1:0] maddr; wire [NQ*TAGW-1:0] mtag;
    reg [NQ-1:0] sv = 0; reg [NQ*TAGW-1:0] stag; reg [NQ*256-1:0] sdata;
    wire [4*32-1:0] f_owned; wire [4*3-1:0] f_fc;
    genvar d;
    generate for (d = 0; d < 4; d = d + 1) begin : g_die
        wire [KW-1:0] fidx;
        wire [KW-1:0] frank = SCAN ? fidx : own_rank[d*KW +: KW];
        wire [POS_W-1:0] fgid = SCAN ? rd_gid[d*POS_W +: POS_W] : own_gid[d*POS_W +: POS_W];
        assign rd_rank[d*KW +: KW] = fidx;
        assign own_idx[d*KW +: KW] = fidx;
        if (WIDE) begin : g_w
            ot_chip_v41x_ckv_pc_fetch #(.DIE_ID(d), .P(PPS), .S(SPP), .SRAM_MACRO(SRAM_MACRO != 0), .IDLAT(1)) u_f (
                .clk(clk), .rst_n(rst_n), .job_v(job_go), .job_ready(f_ready[d]),
                .window_count(8'(wcount)), .published_source_count(POS_W'(npub)),
                .region_base_sector(rbase), .region_sector_count(rcount),
                .id_count(SCAN ? id_count : own_count[d*KW +: KW]), .id_done(id_done), .id_idx(fidx),
                .id_rank_in(frank), .id_gid(fgid),
                .o_v(f_ov[d]), .o_ready(f_or[d]), .o_rank(f_rank[d*KW +: KW]), .o_gid(f_gid[d*POS_W +: POS_W]),
                .o_row(f_row[d*2304 +: 2304]), .done(f_done[d]), .fault(f_fault[d]), .fault_code(f_fc[d*3 +: 3]),
                .st_owned_rows(f_owned[d*32 +: 32]),
                .m_v(mv[d*NPD +: NPD]), .m_rdy(mrdy[d*NPD +: NPD]), .m_addr(maddr[d*NPD*HAW +: NPD*HAW]),
                .m_tag(mtag[d*NPD*TAGW +: NPD*TAGW]), .s_v(sv[d*NPD +: NPD]), .s_tag(stag[d*NPD*TAGW +: NPD*TAGW]),
                .s_beat({NPD*4{1'b0}}), .s_data(sdata[d*NPD*256 +: NPD*256]));
        end else begin : g_n
            assign f_fc[d*3 + 2] = 1'b0;
            ot_chip_v41x_ckv_sel_fetch #(.DIE_ID(d), .NSLOT(NSLOT)) u_f (
                .clk(clk), .rst_n(rst_n), .job_v(job_go), .job_ready(f_ready[d]),
                .window_count(8'(wcount)), .published_source_count(POS_W'(npub)),
                .region_base_sector(rbase), .region_sector_count(rcount),
                .id_count(SCAN ? id_count : own_count[d*KW +: KW]), .id_done(id_done), .id_idx(fidx),
                .id_rank_in(frank), .id_gid(fgid), .id_die(fgid[5:4]),
                .o_v(f_ov[d]), .o_ready(f_or[d]), .o_rank(f_rank[d*KW +: KW]), .o_gid(f_gid[d*POS_W +: POS_W]),
                .o_row(f_row[d*2304 +: 2304]), .done(f_done[d]), .fault(f_fault[d]), .fault_code(f_fc[d*3 +: 2]),
                .st_owned_rows(f_owned[d*32 +: 32]),
                .m_v(mv[d*4 +: 4]), .m_rdy(mrdy[d*4 +: 4]), .m_addr(maddr[d*4*HAW +: 4*HAW]),
                .m_tag(mtag[d*4*TAGW +: 4*TAGW]), .s_v(sv[d*4 +: 4]), .s_tag(stag[d*4*TAGW +: 4*TAGW]),
                .s_beat(16'd0), .s_data(sdata[d*4*256 +: 4*256]));
        end
    end endgenerate

    // behavioural HBM: per (die, stack) one request accepted per cycle, response lat cycles later, in order
    localparam integer HQ = 1024;
    integer hq_t [0:NQ-1][0:HQ-1];
    reg [TAGW-1:0] hq_tag [0:NQ-1][0:HQ-1];
    reg [255:0] hq_dat [0:NQ-1][0:HQ-1];
    integer hq_h [0:NQ-1], hq_n [0:NQ-1];
    integer hbm_reads = 0, hbm_missing = 0, hbm_max_q = 0;
    longint hk;
    integer p, e;

    // ---------------- all-gather links (die d -> die 0) ----------------
    localparam integer LQ = 1024;
    integer lk_t [1:3][0:LQ-1];
    reg [KW-1:0] lk_rank [1:3][0:LQ-1];
    reg [POS_W-1:0] lk_gid [1:3][0:LQ-1];
    reg [2303:0] lk_row [1:3][0:LQ-1];
    integer lk_h [1:3], lk_n [1:3], lk_free [1:3];
    reg [3:0] c_sv; reg [4*KW-1:0] c_srank; reg [4*POS_W-1:0] c_sgid; reg [4*2304-1:0] c_srow;

    // ---------------- collector (die 0) ----------------
    wire c_done, c_fault; wire [2:0] c_on, c_take; wire [KW-1:0] c_orank, c_ahead;
    wire [4*POS_W-1:0] c_ogid; wire [4*2304-1:0] c_orow;
    wire [2:0] c_fc;
    ot_chip_v41x_ckv_sel_collect #(.NSRC(4), .NOUT(4), .RDREG(WIDE != 0)) u_col (
        .clk(clk), .rst_n(rst_n), .clr(job_go), .exp_n(KW'(nsel)),
        .src_v(c_sv), .src_rank(c_srank), .src_gid(c_sgid), .src_row(c_srow),
        .tab_rank(rd_rank[4*KW +: 4*KW]), .tab_gid(rd_gid[4*POS_W +: 4*POS_W]),
        .o_n(c_on), .o_take(c_take), .o_rank(c_orank), .o_gid(c_ogid), .o_row(c_orow),
        .done(c_done), .max_present_ahead(c_ahead), .fault(c_fault), .fault_code(c_fc));

    // ---------------- merger ----------------
    reg w_v = 0; reg [3:0] w_m = 0; reg [4*4224-1:0] w_rows = 0; wire w_ready;
    wire m_jready, m_done, m_fault; wire [1:0] m_fc;
    wire kv_v, kv_ready; wire [3:0] kv_m; wire [NL*ROWW-1:0] kv_w;
    ot_chip_v41x_ckv_stream_merge u_mrg (
        .clk(clk), .rst_n(rst_n), .job_v(job_go), .job_ready(m_jready),
        .window_count(8'(wcount)), .n_sel(KW'(nsel)),
        .w_v(w_v), .w_ready(w_ready), .w_m(w_m), .w_rows(w_rows),
        .c_n(c_on), .c_take(c_take), .c_rank(c_orank), .c_rows(c_orow),
        .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w),
        .done(m_done), .fault(m_fault), .fault_code(m_fc));

    // ---------------- engine or row checker ----------------
    reg job_v = 0; reg [15:0] job_t = 0; wire job_ready;
    reg q_v = 0; reg [D*16-1:0] q_w = 0; wire q_ready;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    reg sc_cr = 0;
    reg p_v = 0; reg [PWORDS*TD*16-1:0] p_w = 0; wire p_ready;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    reg pv_cr = 0;
    wire qk_iss, pv_iss;
    reg chk_ready = 0;
    generate if (ENGINE != 0) begin : g_eng
        ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(TROWS), .PWORDS(PWORDS)) dut (
            .clk(clk), .rst_n(rst_n), .job_v(job_v), .job_t(job_t), .job_ready(job_ready),
            .q_v(q_v), .q_w(q_w), .q_ready(q_ready), .kv_v(kv_v), .kv_m(kv_m), .kv_w(kv_w), .kv_ready(kv_ready),
            .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
            .p_v(p_v), .p_w(p_w), .p_ready(p_ready), .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f),
            .pv_cr(pv_cr), .qk_iss(qk_iss), .pv_iss(pv_iss));
    end else begin : g_chk
        assign kv_ready = chk_ready;
        assign job_ready = 1'b1; assign q_ready = 1'b1; assign sc_v = 1'b0; assign sc_row = 0; assign sc_m = 0;
        assign sc_y = 0; assign sc_f = 0; assign p_ready = 1'b1; assign pv_v = 1'b0; assign pv_c = 0;
        assign pv_y = 0; assign pv_f = 0; assign qk_iss = 1'b0; assign pv_iss = 1'b0;
    end endgenerate

    // ---------------- bench state ----------------
    integer phase = 0;              // 0 reset, 1 running
    integer t_job = -1, t_first_id = -1, t_last_id = -1, t_first_row = -1, t_all_rows = -1;
    integer t_first_ckv_staged = -1, t_last_staged = -1, t_first_qk = -1, t_last_qk = -1, t_last_score = -1;
    integer t_last_p = -1, t_last_pv = -1, qk_beats_before_last_staged = 0, qk_beats = 0;
    integer rows_in = 0, kvr = 0, wsent = 0, qn = 0, pn = 0, pwait = 0, pnw, pstep, pw;
    integer row_err = 0, row_chk = 0, srows = 0, vdims = 0;
    integer sc_chk = 0, sc_err = 0, pv_chk = 0, pv_err = 0, nflt = 0, sc_pend = 0, pv_pend = 0;
    integer l, h, k, tt, n, qq, sent_ok;
    integer maxlk = 0;

    always @(posedge clk) begin
        cyc <= cyc + 1;
        job_go <= 1'b0; id_clr <= 1'b0; job_v <= 1'b0;
        if (cyc == 3) rst_n <= 1'b1;
        if (cyc == 6) begin
            job_go <= 1'b1; id_clr <= 1'b1; t_job = cyc + 1;
            if (ENGINE != 0) begin job_v <= 1'b1; job_t <= 16'(T); end
            for (qq = 0; qq < 4; qq = qq + 1) begin
                qsent[qq] = 0;
                qbase[qq] = (qq == 0) ? 0 : qbase[qq - 1] + qcnt[qq - 1];
            end
            for (p = 0; p < NQ; p = p + 1) begin hq_h[p] = 0; hq_n[p] = 0; end
            for (p = 1; p < 4; p = p + 1) begin lk_h[p] = 0; lk_n[p] = 0; lk_free[p] = 0; end
            phase = 1;
        end
        if (phase == 1) begin
            // ---- sel ports ----
            for (qq = 0; qq < 4; qq = qq + 1) if (s_valid[qq] && s_ready[qq]) begin
                n = 0; for (l = 0; l < 16; l = l + 1) if (s_lv[qq*16 + l]) n = n + 1;
                if (t_first_id < 0 && n > 0) t_first_id = cyc;
                qsent[qq] = qsent[qq] + n;
                if (s_last[qq]) qclosed[qq] = 1'b1;
                s_valid[qq] <= 1'b0;
            end
            for (qq = 0; qq < 4; qq = qq + 1)
                if (cyc >= t_job + seldelay && !qclosed[qq] && !(s_valid[qq] && !s_ready[qq]) && !bub()) begin
                    s_valid[qq] <= 1'b1;
                    n = qcnt[qq] - qsent[qq]; if (n > 16) n = 16;
                    for (l = 0; l < 16; l = l + 1) begin
                        s_lv[qq*16 + l] <= l < n;
                        s_idx[(qq*16 + l)*20 +: 20] <= (l < n) ? 20'(selm[qbase[qq] + qsent[qq] + l]) : 20'd0;
                    end
                    s_last[qq] <= (qsent[qq] + n == qcnt[qq]);
                end
            if (id_done && t_last_id < 0) t_last_id = cyc;
            // ---- HBM stacks ----
            for (p = 0; p < NQ; p = p + 1) begin
                // response (registered)
                sv[p] <= 1'b0;
                if (hq_n[p] > 0 && hq_t[p][hq_h[p]] <= cyc) begin
                    sv[p] <= 1'b1;
                    stag[p*TAGW +: TAGW] <= hq_tag[p][hq_h[p]];
                    sdata[p*256 +: 256] <= hq_dat[p][hq_h[p]];
                    hq_h[p] = (hq_h[p] + 1) % HQ; hq_n[p] = hq_n[p] - 1;
                end
                if (mv[p] && mrdy[p]) begin
                    hk = {26'd0, 2'(p / NPD), 2'((p % NPD) / (NPD / 4)), maddr[p*HAW +: 30]};
                    e = (hq_h[p] + hq_n[p]) % HQ;
                    hq_t[p][e] = cyc + lat; hq_tag[p][e] = mtag[p*TAGW +: TAGW];
                    if (hbm.exists(hk)) hq_dat[p][e] = hbm[hk];
                    else begin
                        hq_dat[p][e] = {256{1'b1}};
                        hbm_missing = hbm_missing + 1;
                        if (hbm_missing < 5) $display("HBM MISSING port %0d addr %0d", p, maddr[p*HAW +: 30]);
                    end
                    hq_n[p] = hq_n[p] + 1; hbm_reads = hbm_reads + 1;
                    if (hq_n[p] > hbm_max_q) hbm_max_q = hq_n[p];
                end
                mrdy[p] <= hq_n[p] < HQ - 2;
            end
            // ---- fetch outputs: die 0 direct, dies 1..3 onto their links ----
            c_sv <= 4'b0;
            if (f_ov[0] && f_or[0]) begin
                c_sv[0] <= 1'b1; c_srank[0 +: KW] <= f_rank[0 +: KW]; c_sgid[0 +: POS_W] <= f_gid[0 +: POS_W];
                c_srow[0 +: 2304] <= f_row[0 +: 2304];
                if (t_first_row < 0) t_first_row = cyc;
                rows_in = rows_in + 1; if (rows_in == nsel) t_all_rows = cyc;
            end
            f_or[0] <= !bub();
            for (p = 1; p < 4; p = p + 1) begin
                if (f_ov[p] && f_or[p]) begin
                    e = (lk_h[p] + lk_n[p]) % LQ;
                    lk_t[p][e] = cyc + ((p == 1) ? lucie : llink);
                    lk_rank[p][e] = f_rank[p*KW +: KW]; lk_gid[p][e] = f_gid[p*POS_W +: POS_W];
                    lk_row[p][e] = f_row[p*2304 +: 2304];
                    lk_n[p] = lk_n[p] + 1; if (lk_n[p] > maxlk) maxlk = lk_n[p];
                    lk_free[p] = cyc + ((p == 1) ? 1 : ri);
                end
                f_or[p] <= (cyc + 1 >= lk_free[p]) && lk_n[p] < LQ - 2;
                if (lk_n[p] > 0 && lk_t[p][lk_h[p]] <= cyc) begin
                    c_sv[p] <= 1'b1; c_srank[p*KW +: KW] <= lk_rank[p][lk_h[p]];
                    c_sgid[p*POS_W +: POS_W] <= lk_gid[p][lk_h[p]]; c_srow[p*2304 +: 2304] <= lk_row[p][lk_h[p]];
                    lk_h[p] = (lk_h[p] + 1) % LQ; lk_n[p] = lk_n[p] - 1;
                    if (t_first_row < 0) t_first_row = cyc;
                    rows_in = rows_in + 1; if (rows_in == nsel) t_all_rows = cyc;
                end
            end
            // ---- window rows into the merger ----
            if (w_v && w_ready) begin wsent = wsent + ((wcount - wsent) < 4 ? (wcount - wsent) : 4); w_v <= 1'b0; end
            if ((ENGINE == 0 || qn >= H) && wsent < wcount && !(w_v && !w_ready) && !bub()) begin
                w_v <= 1'b1;
                for (l = 0; l < 4; l = l + 1) begin
                    w_m[l] <= (wsent + l) < wcount;
                    w_rows[l*4224 +: 4224] <= ((wsent + l) < wcount) ? winm[wsent + l] : 4224'd0;
                end
            end
            // ---- rows entering the engine / checker ----
            if (kv_v && kv_ready) begin
                for (l = 0; l < NL; l = l + 1) if (kv_m[l]) begin
                    row_chk = row_chk + 1;
                    if (kv_w[l*ROWW +: ROWW] !== kvm[kvr + l]) begin
                        row_err = row_err + 1;
                        if (row_err < 6) $display("ROW MISMATCH row %0d", kvr + l);
                    end
                    if (kvr + l >= wcount && t_first_ckv_staged < 0) t_first_ckv_staged = cyc;
                    if (kvr + l == T - 1) t_last_staged = cyc;
                end
                kvr = kvr + NL;
            end
            chk_ready <= !bub();
            // ---- engine: q, probabilities, checks (as tb_hdc_v41x_attn) ----
            if (q_v && q_ready) begin qn = qn + 1; q_v <= 1'b0; end
            if (ENGINE != 0 && qn < H && !(q_v && !q_ready) && cyc > t_job) begin q_v <= 1'b1; q_w <= qm[qn]; end
            if (qk_iss) begin
                if (t_first_qk < 0) t_first_qk = cyc;
                t_last_qk = cyc; qk_beats = qk_beats + 1;
                if (t_last_staged < 0) qk_beats_before_last_staged = qk_beats_before_last_staged + 1;
            end
            if (p_v && p_ready) begin
                pnw = (T + R - 1) / R;
                pn = pn + ((pnw - pn < PWORDS) ? pnw - pn : PWORDS); p_v <= 1'b0; t_last_p = cyc;
            end
            if (ENGINE != 0 && srows >= T && pwait < P_DELAY) pwait = pwait + 1;
            pnw = (T + R - 1) / R;
            pstep = (pnw - pn < PWORDS) ? pnw - pn : PWORDS;
            if (ENGINE != 0 && srows >= T && pwait >= P_DELAY && pn < pnw && !(p_v && !p_ready)) begin
                p_v <= 1'b1;
                for (pw = 0; pw < PWORDS; pw = pw + 1)
                    p_w[pw*TD*16 +: TD*16] <= (pw < pstep) ? pm[pn + pw] : {TD*16{1'b1}};
            end
            sc_cr <= 1'b0;
            if (sc_v) begin
                sc_pend = sc_pend + 1;
                for (l = 0; l < NL; l = l + 1) if (sc_m[l]) begin
                    tt = sc_row + l;
                    for (h = 0; h < H; h = h + 1) begin
                        sc_chk = sc_chk + 1;
                        if (scm[tt][h*33 + 32]) begin
                            nflt = nflt + 1;
                            if (!sc_f[l*H + h]) sc_err = sc_err + 1;
                        end else if (sc_f[l*H + h] || sc_y[(l*H + h)*32 +: 32] !== scm[tt][h*33 +: 32]) begin
                            sc_err = sc_err + 1;
                            if (sc_err < 8) $display("SC MISMATCH row %0d head %0d got %08x exp %08x", tt, h,
                                                     sc_y[(l*H + h)*32 +: 32], scm[tt][h*33 +: 32]);
                        end
                    end
                    srows = srows + 1;
                    if (srows == T) t_last_score = cyc;
                end
            end
            if (sc_pend > 0) begin sc_cr <= 1'b1; sc_pend = sc_pend - 1; end
            pv_cr <= 1'b0;
            if (pv_v) begin
                pv_pend = pv_pend + 1;
                for (k = 0; k < NT; k = k + 1) begin
                    tt = k * DPT + pv_c;
                    for (h = 0; h < H; h = h + 1) begin
                        pv_chk = pv_chk + 1;
                        if (pvm[tt][h*33 + 32]) begin
                            nflt = nflt + 1;
                            if (!pv_f[k*H + h]) pv_err = pv_err + 1;
                        end else if (pv_f[k*H + h] || pv_y[(k*H + h)*32 +: 32] !== pvm[tt][h*33 +: 32]) begin
                            pv_err = pv_err + 1;
                            if (pv_err < 8) $display("PV MISMATCH dim %0d head %0d got %08x exp %08x", tt, h,
                                                     pv_y[(k*H + h)*32 +: 32], pvm[tt][h*33 +: 32]);
                        end
                    end
                end
                vdims = vdims + NT;
                if (vdims >= D) t_last_pv = cyc;
            end
            if (pv_pend > 0) begin pv_cr <= 1'b1; pv_pend = pv_pend - 1; end
        end
        if ((phase == 1 && ((ENGINE != 0) ? (vdims >= D) : (kvr >= T && m_done === 1'b1 || (kvr >= T && t_last_staged >= 0)))
             && cyc > t_job + 2) || cyc >= MAXCYC) begin
            $display("CKVSEL T=%0d wcount=%0d nsel=%0d npub=%0d nslot=%0d wide=%0d pps=%0d spp=%0d lat=%0d llink=%0d lucie=%0d ri=%0d seldelay=%0d t_job=%0d t_first_id=%0d t_last_id=%0d t_first_row=%0d t_all_rows=%0d t_first_ckv_staged=%0d t_last_staged=%0d t_first_qk=%0d t_last_qk=%0d t_last_score=%0d t_last_p=%0d t_last_pv=%0d qk_beats=%0d qk_beats_before_last_staged=%0d fetch_latency=%0d owned0=%0d owned1=%0d owned2=%0d owned3=%0d hbm_reads=%0d hbm_missing=%0d hbm_max_q=%0d link_max_q=%0d collect_max_ahead=%0d faults=%0d",
                     T, wcount, nsel, npub, NSLOT, WIDE, PPS, SPP, lat, llink, lucie, ri, seldelay, t_job, t_first_id, t_last_id, t_first_row,
                     t_all_rows, t_first_ckv_staged, t_last_staged, t_first_qk, t_last_qk, t_last_score, t_last_p, t_last_pv,
                     qk_beats, qk_beats_before_last_staged, t_last_staged - t_last_id,
                     f_owned[0 +: 32], f_owned[32 +: 32], f_owned[64 +: 32], f_owned[96 +: 32],
                     hbm_reads, hbm_missing, hbm_max_q, maxlk, c_ahead,
                     32'(id_fault) + 32'(|f_fault) + 32'(c_fault) + 32'(m_fault));
            $display("CKVROWS checked=%0d errors=%0d id_fc=%0d f_fc=%0h c_fc=%0d m_fc=%0d",
                     row_chk, row_err, id_fc, f_fc, c_fc, m_fc);
            $display("V41XATTN jobs=%0d sc_checked=%0d sc_errors=%0d pv_checked=%0d pv_errors=%0d faults=%0d cycles=%0d timeout=%0d",
                     (vdims >= D) ? 1 : 0, sc_chk, sc_err, pv_chk, pv_err, nflt, cyc, cyc >= MAXCYC);
            $finish;
        end
    end
endmodule
