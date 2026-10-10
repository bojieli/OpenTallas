`timescale 1ns/1ps
// DS-ROM Engram lookup bench: ot_dsrom_engram_idwin -> 2 layers x 4 ranks of
// ot_dsrom_engram_lookup (each on its own behavioural HBM region) -> a
// behavioural TP4 all-gather -> 2 x 4 ot_dsrom_engram_rowsink -> prefetch
// buffers.  tools/rtl_dsrom_engram_lookup_campaign.py writes the vectors and
// checks every dumped buffer against the golden.
//
// Vectors (+VEC): one event per line, hex: "kind user first dead cid w0 w1 w2 w3"
// (kind 1 = MTP rejected-draft rewind of user by cid = n; its window fields are unused)
// (w* = the official NgramHashState window, checked here against idwin;
// the engines receive idwin's windows).
// Output (+OUT): per (token, layer) "T t L l P perr" + 192 words of rank 0's
// buffer; the bench itself checks that the 4 ranks' buffers are identical.
//
// HBM model (one per engine): request queue of QD; each request is served from
// LAT + random(0..JIT) cycles after it was accepted; with REORD=1 the model
// picks a random due request and a random unsent atom of it each cycle (any
// order across and within requests), else oldest-first in order.  GAP: percent
// of cycles with no response; STALL: percent of cycles hq_ready is low.
// Content: global row r of layer l = tools/hdc_v41_engram_shipped.row_bytes
// (word j = splitmix64(l << 40 | r << 6 | j)), scale byte at 256, CRC-32/MPEG-2
// of bytes 0..256 at 257..260 (little-endian), 0 at 261..263, 0xEE between
// columns.  ERR=1 flips one bit of atom 2 of row 0 of every 7th window of rank
// 0's engines (window index mod 7 == 3): the bench reports those as poisoned.
// All-gather: engine r -> sink d is an in-order pipelined link (up to 128 in flight) of AGLAT +
// random(0..AGJIT) cycles (LOCLAT for d == r); a row status rides the same
// queue behind its row's beats.  Consumer: per layer in token order, after
// CDEL random cycles, then releases the slot on all 4 sinks (the engines'
// credit).  SPACED=1: one token in flight at a time (isolated latency).
module tb_dsrom_engram_lookup #(parameter integer NSLOT = 2, parameter integer PIPE = 0, parameter integer WRAP = 0)
    (input wire clk);
    import ot_hdc_engram_tables_shipped_pkg::*;
    localparam integer MAXV = 1 << 13;
    localparam integer NR = 4, NL = 2, NE = NL * NR, CPR = 6, NU = 8;
    localparam integer QW = ENG_RES_W, RW = ENG_ROW_W, IDW = ENG_ID_W;
    localparam integer SLW = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer BAW = SLW + 8, QD = 8, AQ = 128;
    localparam integer ABW = 36;

    reg [7:0]      vuser [0:MAXV-1];
    reg            vkind [0:MAXV-1];        // 0 token, 1 MTP rewind (cid field = n)
    reg            vfirst[0:MAXV-1], vdead[0:MAXV-1];
    reg [IDW-1:0]  vcid  [0:MAXV-1];
    reg [4*IDW-1:0] vwin [0:MAXV-1];
    integer nvec = 0, ntok = 0, fd, fo, rc, k;
    reg [31:0] fld;
    integer LAT, JIT, STALL, GAP, REORD, BUB, CDEL, SPACED, AGLAT, AGJIT, LOCLAT, ERR;

    function automatic [63:0] smix(input [63:0] x);
        reg [63:0] z;
        begin
            z = x + 64'h9E3779B97F4A7C15;
            z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9;
            z = (z ^ (z >> 27)) * 64'h94D049BB133111EB;
            smix = z ^ (z >> 31);
        end
    endfunction
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    function automatic [31:0] crcb(input [31:0] c, input [7:0] b);
        integer i;
        reg [31:0] x;
        begin
            x = c;
            for (i = 7; i >= 0; i = i - 1) x = {x[30:0], 1'b0} ^ ((x[31] ^ b[i]) ? 32'h04C11DB7 : 32'd0);
            crcb = x;
        end
    endfunction
    function automatic [7:0] scale_of(input [63:0] key);
        reg [63:0] w;
        begin
            w = smix(key | 64'd32);
            scale_of = w[8] ? w[7:0] : 8'd107 + (w[7:0] % 41);
        end
    endfunction
    function automatic [31:0] row_crc(input [63:0] key);
        integer i, b;
        reg [63:0] w;
        reg [31:0] c;
        begin
            c = 32'hFFFFFFFF;
            for (i = 0; i < 32; i = i + 1) begin
                w = smix(key | i);
                for (b = 0; b < 8; b = b + 1) c = crcb(c, w[8*b +: 8]);
            end
            row_crc = crcb(c, scale_of(key));
        end
    endfunction
    function automatic [63:0] colbase(input integer l, input integer r, input integer j);
        integer i;
        reg [63:0] acc, sz;
        begin
            acc = 0;
            for (i = 0; i < j; i = i + 1) begin
                sz = ENG_PRIME[QW*(l*ENG_COLS + r*CPR + i) +: QW] * 64'd264;
                acc = acc + ((sz + 31) & ~64'd31);
            end
            colbase = acc;
        end
    endfunction
    // one byte of engine (l, r)'s region
    reg [63:0] cbt [0:NE-1][0:CPR];
    function automatic [7:0] byte_at(input integer l, input integer r, input [63:0] a);
        integer j, c;
        reg [63:0] off, res, bi, grow, key, w, q;
        reg [31:0] cr;
        begin
            byte_at = 8'hEE;
            for (j = 0; j < CPR; j = j + 1) begin
                c = l * ENG_COLS + r * CPR + j;
                q = ENG_PRIME[QW*c +: QW];
                if (a >= cbt[l*NR + r][j] && a < cbt[l*NR + r][j] + q * 264) begin
                    off = a - cbt[l*NR + r][j];
                    res = off / 264; bi = off % 264;
                    grow = res + ENG_OFFSET[RW*c +: RW];
                    key = ({56'd0, l[7:0]} << 40) | (grow << 6);
                    if (bi < 256) begin w = smix(key | (bi >> 3)); byte_at = w[8*(bi % 8) +: 8]; end
                    else if (bi == 256) byte_at = scale_of(key);
                    else if (bi <= 260) begin cr = row_crc(key); byte_at = cr[8*(bi - 257) +: 8]; end
                    else byte_at = 8'd0;
                end
            end
        end
    endfunction

    reg rst_n = 1'b0;
    // ---- idwin --------------------------------------------------------------------------
    reg t_valid = 0, t_first = 0, t_dead = 0;
    reg [2:0] t_user = 0;
    reg [IDW-1:0] t_cid = 0;
    wire w_valid, w_dead;
    wire [4*IDW-1:0] w_ids;
    ot_dsrom_engram_idwin #(.NUSER(NU), .ID_W(IDW), .PAD(ENG_PAD)) u_idwin (
        .clk(clk), .rst_n(rst_n), .t_valid(t_valid), .t_user(t_user), .t_cid(t_cid), .t_first(t_first),
        .t_dead(t_dead), .rb_valid(rb_v), .rb_user(rb_u), .rb_n(rb_n), .win_valid(w_valid), .win_ids(w_ids), .win_dead(w_dead));

    // ---- engines, HBM, all-gather, sinks ------------------------------------------------
    wire [NE-1:0] e_wrdy, e_hqv, e_ov, e_stv, e_stb, e_fault;
    reg  [NE-1:0] e_wv = 0, e_hqr = 0, e_hrv = 0, e_or = 0;
    wire [NE*(ABW-5)-1:0] e_hqa;
    wire [NE*3-1:0] e_hqt;
    reg  [NE*3-1:0] e_hrt = 0;
    reg  [NE*4-1:0] e_hri = 0;
    reg  [NE*256-1:0] e_hrd = 0;
    wire [NE*5-1:0] e_oc;
    wire [NE*3-1:0] e_ob;
    wire [NE*SLW-1:0] e_os, e_sts;
    wire [NE*264-1:0] e_od;
    reg  [NE*NR-1:0] e_rel = 0;
    wire [NE-1:0] e_wc;                       // WRAP: window credit returns
    reg  [NE-1:0] e_hqc = 0, e_occ = 0;       // WRAP: HBM request / beat credit returns
    integer wcred [0:NE-1];
    reg  [4*IDW-1:0] e_win [0:NE-1];
    // sinks: sink s = l*NR + d, port r
    reg  [NE*NR-1:0] s_iv = 0, s_stv = 0, s_stb = 0;
    wire [NE*NR-1:0] s_ir;
    reg  [NE*NR*5-1:0] s_ic = 0;
    reg  [NE*NR*3-1:0] s_ib = 0;
    reg  [NE*NR*SLW-1:0] s_is = 0, s_sts = 0;
    reg  [NE*NR*264-1:0] s_id = 0;
    wire [NE-1:0] s_we;
    wire [NE*BAW-1:0] s_wa;
    wire [NE*512-1:0] s_wd;
    wire [NE*NSLOT-1:0] s_rdy, s_perr;
    reg  [NE-1:0] s_rel = 0;
    reg  [SLW-1:0] s_rels [0:NE-1];
    genvar ge;
    generate
        for (ge = 0; ge < NE; ge = ge + 1) begin : g_e
            localparam integer L_ = ge / NR, R_ = ge % NR;
            if (WRAP == 0) begin : g_core
                ot_dsrom_engram_lookup #(.NR(NR), .CPR(CPR), .NSLOT(NSLOT), .ABW(ABW), .PIPE(PIPE)) u_e (
                    .clk(clk), .rst_n(rst_n), .cfg_layer(L_[0]), .cfg_rank(R_[1:0]), .win_valid(e_wv[ge]),
                    .win_ready(e_wrdy[ge]), .win_ids(e_win[ge]), .rel_valid(e_rel[NR*ge +: NR]),
                    .hq_valid(e_hqv[ge]), .hq_ready(e_hqr[ge]), .hq_atom(e_hqa[(ABW-5)*ge +: ABW-5]), .hq_len(),
                    .hq_tag(e_hqt[3*ge +: 3]), .hr_valid(e_hrv[ge]), .hr_ready(), .hr_tag(e_hrt[3*ge +: 3]),
                    .hr_idx(e_hri[4*ge +: 4]), .hr_data(e_hrd[256*ge +: 256]),
                    .o_valid(e_ov[ge]), .o_ready(e_or[ge]), .o_col(e_oc[5*ge +: 5]), .o_beat(e_ob[3*ge +: 3]),
                    .o_slot(e_os[SLW*ge +: SLW]), .o_data(e_od[264*ge +: 264]),
                    .st_valid(e_stv[ge]), .st_slot(e_sts[SLW*ge +: SLW]), .st_bad(e_stb[ge]), .fault(e_fault[ge]));
                assign e_wc[ge] = 1'b0;
            end else begin : g_wrap
                dsfd_engram_lkp #(.PIPE(PIPE), .NSLOT(NSLOT), .HQ_CRED(QD), .O_CRED(16), .SLW(SLW)) u_e (
                    .ck(clk), .rst_n(rst_n), .cfg_layer(L_[0]), .cfg_rank(R_[1:0]),
                    .win_v(e_wv[ge]), .win_ids(e_win[ge]), .win_cred(e_wc[ge]), .rel(e_rel[NR*ge +: NR]),
                    .hq_v(e_hqv[ge]), .hq_atom(e_hqa[(ABW-5)*ge +: ABW-5]), .hq_tag(e_hqt[3*ge +: 3]), .hq_cred(e_hqc[ge]),
                    .hr_v(e_hrv[ge]), .hr_tag(e_hrt[3*ge +: 3]), .hr_idx(e_hri[4*ge +: 4]), .hr_d(e_hrd[256*ge +: 256]),
                    .o_v(e_ov[ge]), .o_col(e_oc[5*ge +: 5]), .o_beat(e_ob[3*ge +: 3]), .o_slot(e_os[SLW*ge +: SLW]),
                    .o_d(e_od[264*ge +: 264]), .o_cred(e_occ[ge]),
                    .st_v(e_stv[ge]), .st_slot(e_sts[SLW*ge +: SLW]), .st_bad(e_stb[ge]), .fault(e_fault[ge]));
                assign e_wrdy[ge] = 1'b0;
            end
            ot_dsrom_engram_rowsink #(.NSRC(NR), .NC(ENG_COLS), .NSLOT(NSLOT)) u_s (
                .clk(clk), .rst_n(rst_n), .in_valid(s_iv[NR*ge +: NR]), .in_ready(s_ir[NR*ge +: NR]),
                .in_col(s_ic[5*NR*ge +: 5*NR]), .in_beat(s_ib[3*NR*ge +: 3*NR]), .in_slot(s_is[SLW*NR*ge +: SLW*NR]),
                .in_data(s_id[264*NR*ge +: 264*NR]), .st_valid(s_stv[NR*ge +: NR]), .st_slot(s_sts[SLW*NR*ge +: SLW*NR]),
                .st_bad(s_stb[NR*ge +: NR]), .wr_en(s_we[ge]), .wr_addr(s_wa[BAW*ge +: BAW]), .wr_data(s_wd[512*ge +: 512]),
                .rdy(s_rdy[NSLOT*ge +: NSLOT]), .perr(s_perr[NSLOT*ge +: NSLOT]), .rel_valid(s_rel[ge]), .rel_slot(s_rels[ge]));
        end
    endgenerate

    initial begin : load
        reg [8*512-1:0] path;
        integer l, r, j;
        if (!$value$plusargs("VEC=%s", path)) path = "engram_lookup_vectors.txt";
        if (!$value$plusargs("LAT=%d", LAT)) LAT = 240;
        if (!$value$plusargs("JIT=%d", JIT)) JIT = 0;
        if (!$value$plusargs("STALL=%d", STALL)) STALL = 0;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("REORD=%d", REORD)) REORD = 0;
        if (!$value$plusargs("BUB=%d", BUB)) BUB = 0;
        if (!$value$plusargs("CDEL=%d", CDEL)) CDEL = 0;
        if (!$value$plusargs("SPACED=%d", SPACED)) SPACED = 0;
        if (!$value$plusargs("AGLAT=%d", AGLAT)) AGLAT = 4;
        if (!$value$plusargs("AGJIT=%d", AGJIT)) AGJIT = 0;
        if (!$value$plusargs("LOCLAT=%d", LOCLAT)) LOCLAT = 2;
        if (!$value$plusargs("ERR=%d", ERR)) ERR = 0;
        for (l = 0; l < NL; l = l + 1) for (r = 0; r < NR; r = r + 1) for (j = 0; j <= CPR; j = j + 1)
            cbt[l*NR + r][j] = colbase(l, r, j);
        fd = $fopen(path, "r");
        if (fd == 0) begin $display("cannot open vectors"); $finish; end
        rc = 1;
        while (rc > 0 && nvec < MAXV) begin
            rc = $fscanf(fd, "%h", fld);
            if (rc > 0) begin
                vkind[nvec] = fld[0];
                rc = $fscanf(fd, "%h", fld);
                vuser[nvec] = fld[7:0];
                rc = $fscanf(fd, "%h", fld); vfirst[nvec] = fld[0];
                rc = $fscanf(fd, "%h", fld); vdead[nvec] = fld[0];
                rc = $fscanf(fd, "%h", fld); vcid[nvec] = fld[IDW-1:0];
                for (k = 0; k < 4; k = k + 1) begin
                    rc = $fscanf(fd, "%h", fld); vwin[ntok][IDW*k +: IDW] = fld[IDW-1:0];
                end
                if (!vkind[nvec]) ntok = ntok + 1;
                nvec = nvec + 1;
            end
        end
        $fclose(fd);
        if (!$value$plusargs("OUT=%s", path)) path = "engram_lookup_out.txt";
        fo = $fopen(path, "w");
    end

    reg [31:0] seed = 32'h1234_5678, hseed = 32'h0BAD_5EED, aseed = 32'hA11_6A7E, cseed = 32'h5EED_0001;
    integer cyc = 0, sent = 0, tsent = 0, wgot = 0, werr = 0;
    reg rb_v = 0;
    reg [2:0] rb_u = 0, rb_n = 0;
    integer tw [0:MAXV-1];
    reg [4*IDW-1:0] wq [0:MAXV-1];      // idwin's windows, as the engines receive them
    integer ct [0:NL-1];
    // ---- driver --------------------------------------------------------------------------
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        seed = xs(seed);
        t_valid <= 1'b0;
        rb_v <= 1'b0;
        if (rst_n && sent < nvec && vkind[sent]) begin
            rb_v <= 1'b1; rb_u <= vuser[sent][2:0]; rb_n <= vcid[sent][2:0];
            sent <= sent + 1;
        end else if (rst_n && sent < nvec && (seed % 100) >= BUB && (SPACED == 0 || (ct[0] == tsent && ct[1] == tsent))
            && tsent - ct[0] < 64 && tsent - ct[1] < 64) begin
            t_valid <= 1'b1; t_user <= vuser[sent][2:0]; t_first <= vfirst[sent]; t_dead <= vdead[sent];
            t_cid <= vcid[sent];
            sent <= sent + 1;
            tsent <= tsent + 1;
        end
        if (rst_n && w_valid) begin
            if (w_ids !== vwin[wgot]) begin
                if (werr < 5) $display("WINDOW MISMATCH token=%0d got=%h exp=%h", wgot, w_ids, vwin[wgot]);
                werr = werr + 1;
            end
            tw[wgot] = cyc;
            wq[wgot] = w_ids;
            wgot = wgot + 1;
        end
    end
    // ---- window broadcast: engine e takes window ep[e] when it is ready ----------------
    integer ep [0:NE-1];
    integer e, d, i2;
    initial for (e = 0; e < NE; e = e + 1) begin ep[e] = 0; wcred[e] = 2; end
    always @(posedge clk) begin
        for (e = 0; e < NE; e = e + 1) begin
            if (WRAP != 0) begin
                if (e_wc[e]) wcred[e] = wcred[e] + 1;
                e_wv[e] <= 1'b0;
                if (rst_n && wcred[e] > 0 && ep[e] < wgot) begin
                    e_wv[e] <= 1'b1; e_win[e] <= wq[ep[e]]; ep[e] = ep[e] + 1; wcred[e] = wcred[e] - 1;
                end
            end else if (e_wv[e] && e_wrdy[e]) begin e_wv[e] <= 1'b0; ep[e] = ep[e] + 1; end
            else if (!e_wv[e] && ep[e] < wgot) begin e_wv[e] <= 1'b1; e_win[e] <= wq[ep[e]]; end
        end
    end
    // ---- HBM models ----------------------------------------------------------------------
    reg [ABW-6:0] qa [0:NE-1][0:QD-1];
    reg [2:0]     qt [0:NE-1][0:QD-1];
    integer       qdue [0:NE-1][0:QD-1];
    reg [8:0]     qsent [0:NE-1][0:QD-1];
    reg           qv [0:NE-1][0:QD-1];
    integer       qn [0:NE-1], wseen [0:NE-1], rows_in_w [0:NE-1];
    integer slt, cand, ai, b, pick, ncand, injected = 0, ovf = 0;
    reg [255:0] atom;
    reg [63:0] abase;
    initial for (e = 0; e < NE; e = e + 1) begin
        qn[e] = 0; wseen[e] = 0; rows_in_w[e] = 0;
        for (slt = 0; slt < QD; slt = slt + 1) qv[e][slt] = 0;
    end
    reg inj_tok [0:MAXV-1];
    initial for (i2 = 0; i2 < MAXV; i2 = i2 + 1) inj_tok[i2] = 0;
    always @(posedge clk) begin
        for (e = 0; e < NE; e = e + 1) begin
            e_hrv[e] <= 1'b0;
            e_hqc[e] <= 1'b0;
            hseed = xs(hseed);
            if (rst_n && (hseed % 100) >= GAP) begin
                // pick a due request (oldest or random) and an atom of it
                pick = -1; ncand = 0;
                for (slt = 0; slt < QD; slt = slt + 1)
                    if (qv[e][slt] && cyc >= qdue[e][slt]) begin
                        ncand = ncand + 1;
                        if (pick < 0) pick = slt;
                        else if (REORD != 0) begin hseed = xs(hseed); if (hseed % ncand == 0) pick = slt; end
                        else if (qdue[e][slt] < qdue[e][pick]) pick = slt;
                    end
                if (pick >= 0) begin
                    ai = -1; ncand = 0;
                    for (b = 0; b < 9; b = b + 1) if (!qsent[e][pick][b]) begin
                        ncand = ncand + 1;
                        if (ai < 0) ai = b;
                        else if (REORD != 0) begin hseed = xs(hseed); if (hseed % ncand == 0) ai = b; end
                    end
                    abase = {28'd0, qa[e][pick], 5'd0} + 32 * ai;
                    for (b = 0; b < 32; b = b + 1) atom[8*b +: 8] = byte_at(e / NR, e % NR, abase + b);
                    if (ERR != 0 && e % NR == 0 && qt[e][pick] == 0 && ai == 2 && (qsent[e][pick] & 9'h1FF) != 9'h1FF) begin
                        // the request's window index: requests are issued per window in order
                        if (((wseen[e] - 1) % 7) == 3) begin atom[5] = ~atom[5]; inj_tok[wseen[e] - 1] = 1; end
                    end
                    e_hrv[e] <= 1'b1; e_hrt[3*e +: 3] <= qt[e][pick]; e_hri[4*e +: 4] <= ai[3:0];
                    e_hrd[256*e +: 256] <= atom;
                    qsent[e][pick][ai] = 1'b1;
                    if (qsent[e][pick] == 9'h1FF) begin qv[e][pick] = 0; qn[e] = qn[e] - 1; e_hqc[e] <= 1'b1; end
                end
            end
            if (e_hqv[e] && (WRAP != 0 || e_hqr[e])) begin
                for (slt = 0; slt < QD && qv[e][slt]; slt = slt + 1) ;
                if (slt >= QD) begin $display("HBM QUEUE OVERFLOW engine %0d", e); slt = 0; ovf = ovf + 1; end
                qv[e][slt] = 1; qa[e][slt] = e_hqa[(ABW-5)*e +: ABW-5]; qt[e][slt] = e_hqt[3*e +: 3];
                qsent[e][slt] = 9'd0;
                hseed = xs(hseed);
                qdue[e][slt] = cyc + LAT + (JIT > 0 ? hseed % (JIT + 1) : 0);
                qn[e] = qn[e] + 1;
                if (e_hqt[3*e +: 3] == 0) wseen[e] = wseen[e] + 1;
            end
            hseed = xs(hseed);
            e_hqr[e] <= rst_n && (qn[e] + (e_hqv[e] && e_hqr[e]) < QD) && ((hseed % 100) >= STALL);
        end
    end
    // ---- all-gather: queue (e -> d), entries {kind, payload, due} --------------------------
    localparam integer PW = 1 + 5 + 3 + SLW + 264;
    reg [PW-1:0] aq [0:NE*NR-1][0:AQ-1];
    integer      adue [0:NE*NR-1][0:AQ-1];
    integer      ah [0:NE*NR-1], an [0:NE*NR-1];
    integer lq, src, dst, si, last_due [0:NE*NR-1];
    initial for (lq = 0; lq < NE * NR; lq = lq + 1) begin ah[lq] = 0; an[lq] = 0; last_due[lq] = 0; end
    always @(posedge clk) begin
        for (e = 0; e < NE; e = e + 1) begin
            // engine e = (l, r) feeds the sinks (l, d) port r through queue e*NR + d
            if (e_ov[e] && (WRAP != 0 || e_or[e])) begin
                for (d = 0; d < NR; d = d + 1) begin
                    lq = e * NR + d; aseed = xs(aseed);
                    if (an[lq] >= AQ) begin $display("LINK OVERFLOW %0d", lq); ovf = ovf + 1; end
                    aq[lq][(ah[lq] + an[lq]) % AQ] = {1'b0, e_oc[5*e +: 5], e_ob[3*e +: 3], e_os[SLW*e +: SLW], e_od[264*e +: 264]};
                    adue[lq][(ah[lq] + an[lq]) % AQ] = cyc + ((d == e % NR) ? LOCLAT : AGLAT + (AGJIT > 0 ? aseed % (AGJIT + 1) : 0));
                    if (adue[lq][(ah[lq] + an[lq]) % AQ] < last_due[lq]) adue[lq][(ah[lq] + an[lq]) % AQ] = last_due[lq];
                    last_due[lq] = adue[lq][(ah[lq] + an[lq]) % AQ];
                    an[lq] = an[lq] + 1;
                end
            end
            if (e_stv[e]) begin
                for (d = 0; d < NR; d = d + 1) begin
                    lq = e * NR + d;
                    aq[lq][(ah[lq] + an[lq]) % AQ] = {1'b1, 5'd0, 2'd0, e_stb[e], e_sts[SLW*e +: SLW], 264'd0};
                    adue[lq][(ah[lq] + an[lq]) % AQ] = (cyc + 1 > last_due[lq]) ? cyc + 1 : last_due[lq];
                    last_due[lq] = adue[lq][(ah[lq] + an[lq]) % AQ];
                    an[lq] = an[lq] + 1;
                end
            end
        end
        for (e = 0; e < NE; e = e + 1) begin
            e_or[e] <= 1'b1;
            for (d = 0; d < NR; d = d + 1) if (an[e * NR + d] > AQ - 4) e_or[e] <= 1'b0;
        end
        // sink side: sink s = (l, d), port r <- queue (l*NR + r)*NR + d
        for (e = 0; e < NE; e = e + 1) e_occ[e] <= 1'b0;
        for (si = 0; si < NE; si = si + 1) begin
            for (src = 0; src < NR; src = src + 1) begin
                lq = ((si / NR) * NR + src) * NR + (si % NR);
                dst = si * NR + src;
                s_stv[dst] <= 1'b0;
                if (s_iv[dst] && s_ir[dst]) begin
                    s_iv[dst] <= 1'b0; ah[lq] = (ah[lq] + 1) % AQ; an[lq] = an[lq] - 1;
                    if (src == si % NR) e_occ[(si / NR) * NR + src] <= 1'b1;   // credit on the local copy's delivery
                end
                else if (!s_iv[dst] && an[lq] > 0 && cyc >= adue[lq][ah[lq]]) begin
                    if (aq[lq][ah[lq]][PW-1]) begin
                        s_stv[dst] <= 1'b1; s_stb[dst] <= aq[lq][ah[lq]][264 + SLW];
                        s_sts[SLW*dst +: SLW] <= aq[lq][ah[lq]][264 +: SLW];
                        ah[lq] = (ah[lq] + 1) % AQ; an[lq] = an[lq] - 1;
                    end else begin
                        s_iv[dst] <= 1'b1;
                        {s_ic[5*dst +: 5], s_ib[3*dst +: 3], s_is[SLW*dst +: SLW], s_id[264*dst +: 264]} <= aq[lq][ah[lq]][PW-2:0];
                    end
                end
            end
        end
    end
    // ---- buffers -------------------------------------------------------------------------
    reg [511:0] buffer [0:NE-1][0:(1<<BAW)-1];
    always @(posedge clk)
        for (si = 0; si < NE; si = si + 1)
            if (s_we[si]) buffer[si][s_wa[BAW*si +: BAW]] <= s_wd[512*si +: 512];
    // ---- consumer ------------------------------------------------------------------------
    integer wt [0:NL-1], lmin [0:NL-1], lmax [0:NL-1], lsum [0:NL-1];
    integer dumped = 0, xerr = 0, pois = 0, idle = 0, l, a, s, lat, allr, anyp;
    initial for (l = 0; l < NL; l = l + 1) begin ct[l] = 0; wt[l] = -1; lmin[l] = 1 << 30; lmax[l] = 0; lsum[l] = 0; end
    always @(posedge clk) begin
        for (e = 0; e < NE; e = e + 1) e_rel[NR*e +: NR] <= {NR{1'b0}};
        s_rel <= {NE{1'b0}};
        for (l = 0; l < NL; l = l + 1) begin
            if (rst_n && ct[l] < ntok) begin
                s = ct[l] % NSLOT;
                allr = 1; anyp = 0;
                for (d = 0; d < NR; d = d + 1) begin
                    if (!s_rdy[NSLOT*(l*NR + d) + s]) allr = 0;
                    if (s_perr[NSLOT*(l*NR + d) + s]) anyp = 1;
                end
                if (allr) begin
                    if (wt[l] < 0) begin
                        cseed = xs(cseed); wt[l] = CDEL > 0 ? cseed % (CDEL + 1) : 0;
                        lat = cyc - tw[ct[l]];
                        if (lat < lmin[l]) lmin[l] = lat;
                        if (lat > lmax[l]) lmax[l] = lat;
                        lsum[l] = lsum[l] + lat;
                    end
                    if (wt[l] == 0) begin
                        $fwrite(fo, "T %0d L %0d P %0d\n", ct[l], l, anyp);
                        for (a = 0; a < ENG_COLS * 8; a = a + 1) begin
                            $fwrite(fo, "%0128h\n", buffer[l*NR][{s[SLW-1:0], a[7:0]}]);
                            for (d = 1; d < NR; d = d + 1)
                                if (buffer[l*NR + d][{s[SLW-1:0], a[7:0]}] !== buffer[l*NR][{s[SLW-1:0], a[7:0]}]) xerr = xerr + 1;
                        end
                        dumped = dumped + 1;
                        pois = pois + anyp;
                        for (d = 0; d < NR; d = d + 1) begin
                            s_rel[l*NR + d] <= 1'b1; s_rels[l*NR + d] <= s[SLW-1:0];
                        end
                        for (e = l * NR; e < l * NR + NR; e = e + 1) e_rel[NR*e +: NR] <= {NR{1'b1}};
                        wt[l] = -1;
                        ct[l] = ct[l] + 1;
                    end else wt[l] = wt[l] - 1;
                end
            end
        end
        idle = (ct[0] >= ntok && ct[1] >= ntok) ? idle + 1 : 0;
        if (idle > 20 || cyc > 4000 * MAXV) begin
            $display("ENGRAM tokens=%0d windows=%0d window_errors=%0d dumped=%0d xrank_errors=%0d poisoned=%0d injected=%0d faults=%b cycles=%0d lat0_min=%0d lat0_max=%0d lat0_sum=%0d lat1_min=%0d lat1_max=%0d lat1_sum=%0d",
                     ntok, wgot, werr, dumped, xerr, pois, injected, e_fault, cyc, lmin[0], lmax[0], lsum[0], lmin[1], lmax[1], lsum[1]);
            for (i2 = 0; i2 < ntok; i2 = i2 + 1) if (inj_tok[i2]) $display("INJ %0d", i2);
            if (werr == 0 && xerr == 0 && ovf == 0 && wgot == ntok && dumped == NL * ntok) $display("DONE"); else $display("FAIL");
            $fclose(fo);
            $finish;
        end
    end
endmodule
