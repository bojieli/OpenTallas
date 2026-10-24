`timescale 1ps/1ps
// S81-RTLGAP/RG-ENG (10-21): composition bench of the Engram row-read path + join (dsdv_eng_rr.sv) on REAL RTL:
//   dsdv_eng_rr_c (window former + CLOSED-source dsfd_engram_lkp_static14 + head + XQ join) -> request chain through 16
//   dsdv_eng_tap (west end + 15) with CS relay stages a hop -> 16 dsfd_ctrl_rg3 (real controller RTL, svc face idle) ->
//   per-PC PHY models (in-order, LAT ckh cycles, k_rdy pattern) holding the Engram rows -> responses back through the
//   taps' response chain -> lookup -> XQ trains on both V rung directions.
// Concurrent traffic: a bench reader on tap/controller RD (both lanes, realistic dsdv_idx_rg3 tag codes incl. the
//   g 0 / sc 1 / cell 0 scale reads) in phases between the Engram windows, overlapping their HBM flight; rung pass-through
//   traffic (CTL single V beats both ways) before every window.
// Checks (TB_ENG_RR): windows = NgramHashState of the f_ks stream (synthetic id map in the ROM images, pos blocking);
//   every lookup row beat = the PHY image row (codes + scale byte); 24 XQ trains a window on EACH direction with the
//   rank's idx set; reader beats / tags / data / pops exact and no Engram beat leaks to the reader; rung pass-through
//   exact (+2 edges); every fault / status output 0.  Bit-exactness of the XQ payloads vs hdc_golden_v41
//   (decode_engram_rows -> quant_fp8) is checked by tools/s81_dv/eng_rr/check_eng_rr.py on the OB / XQ log lines.
// Mutants: XQ_MUT 1 (idx), 2 (e0 / e1 swapped) -> python FAIL; TAP_MUT 1 (demux without sc: steals reader scan beats),
//   2 (pops unfiltered) -> TB_ENG_RR FAIL.
module tb_dsdv_eng_rr;
    parameter integer XQ_MUT = 0;
    parameter integer TAP_MUT = 0;
    parameter integer RETURN_AGE = 640;      // S81-FIX2/ENG 10-21: ra640 (was 512)
    parameter integer CS = 2;                  // relay stages a chain hop (die stations between controller slots)
    parameter integer RD = 5;                  // controller of the bench reader
    parameter [1:0] RANK = 2'd2;
    localparam [29:0] PCBASE = 30'h1000_0000;
    integer SEED = 1, LAT = 100, NW = 6;
    initial begin
        void'($value$plusargs("SEED=%d", SEED)); void'($value$plusargs("LAT=%d", LAT)); void'($value$plusargs("NW=%d", NW));
    end
    reg ck = 0, ckh = 0, rst = 0;
    always begin #417 ck = 1; #416 ck = 0; end
    always #450 ckh = ~ckh;
    longint cyc = 0, hcyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    always @(posedge ckh) hcyc <= hcyc + 1;
    function automatic [31:0] mix(input longint a);
        longint z; z = a * 64'h9E3779B97F4A7C15 + 64'(SEED) * 64'hBF58476D1CE4E5B9;
        z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9; z = (z ^ (z >> 27)) * 64'h94D049BB133111EB; z = z ^ (z >> 31);
        mix = z[31:0];
    endfunction
    // ------------------------------------------------------------------ DUT cluster
    reg  [52:0]  f_ks = 0;
    wire [42:0]  rco_h; wire [267:0] pci_h;
    reg  [275:0] vi_s = 0, vi_n = 0; wire [275:0] vo_s, vo_n; wire [3:0] st;
    dsdv_eng_rr_c #(.RETURN_AGE(RETURN_AGE), .PCBASE(PCBASE), .XQ_MUT(XQ_MUT)) u_rr (.ck(ck), .rst_n(rst), .cfg_en(1'b1),
        .cfg_layer(1'b1), .cfg_rank(RANK), .f_ks(f_ks), .rco(rco_h), .pci(pci_h), .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n),
        .vo_n(vo_n), .st(st));
`ifdef OT_S81ENG_RR_SPLIT_LOCKSTEP
    // CORE-S81-ENG 10-23: the two-core split (dsdv_eng_rr_split = cores LK + XQ) runs in LOCKSTEP beside the monolith on
    // the same inputs; every output bit is compared on every edge after reset release (and the crossing against the
    // monolith's lookup -> xq nets).  SPLIT_MUT 1 / 2 = negative controls (crossing bit flip / one extra crossing stage).
    parameter integer SPLIT_MUT = 0;
    wire [42:0] rco_sp; wire [275:0] vo_s_sp, vo_n_sp; wire [3:0] st_sp;
    dsdv_eng_rr_split #(.RETURN_AGE(RETURN_AGE), .PCBASE(PCBASE), .XQ_MUT(XQ_MUT), .SPLIT_MUT(SPLIT_MUT)) u_sp (.ck(ck),
        .rst_n(rst), .cfg_en(1'b1), .cfg_layer(1'b1), .cfg_rank(RANK), .f_ks(f_ks), .rco(rco_sp), .pci(pci_h), .vi_s(vi_s),
        .vo_s(vo_s_sp), .vi_n(vi_n), .vo_n(vo_n_sp), .st(st_sp));
    longint lk_cyc = 0, lk_bad = 0, lk_xv = 0, lk_rco = 0, lk_vo = 0;
    always @(negedge ck) if (rst) begin
        lk_cyc <= lk_cyc + 1;
        if (u_sp.x_v) lk_xv <= lk_xv + 1;
        if (rco_h[0]) lk_rco <= lk_rco + 1;
        if (vo_s[0] || vo_n[0]) lk_vo <= lk_vo + 1;
        if (rco_sp !== rco_h || vo_s_sp !== vo_s || vo_n_sp !== vo_n || st_sp !== st ||
            {u_sp.x_v, u_sp.x_col, u_sp.x_beat, u_sp.x_d} !== {u_rr.o_v, u_rr.o_col, u_rr.o_beat, u_rr.o_d}) begin
            lk_bad <= lk_bad + 1;
            if (lk_bad < 4) $display("TB_ENG_RR_LOCKSTEP mismatch cyc %0d rco %0d vo_s %0d vo_n %0d st %b/%b", cyc,
                                     rco_sp !== rco_h, vo_s_sp !== vo_s, vo_n_sp !== vo_n, st_sp, st);
        end
    end
`endif
    // ------------------------------------------------------------------ taps, chains, controllers, PHY
    wire [42:0]  rci [0:15]; wire [42:0] rco [0:15]; wire [267:0] pci [0:15]; wire [267:0] pco [0:15];
    wire [91:0]  rqi [0:15]; wire [91:0] rqo [0:15]; wire [543:0] rri [0:15]; wire [543:0] rro [0:15];
    wire [15:0]  tf; wire [561:0] rd [0:15];
    reg  [91:0]  rdr_rq = 0;                   // bench reader lanes (controller RD)
    wire [1:0] kv [0:15], krdy [0:15], kwe [0:15], kwd [0:15], krv [0:15], krrdy [0:15];
    wire [59:0] kad [0:15]; wire [7:0] kln [0:15], krb [0:15]; wire [33:0] ktg [0:15], krt [0:15];
    wire [511:0] kwdat [0:15], krd [0:15]; wire [63:0] kws [0:15];
    // relay stages a hop (registers only)
    genvar k, s;
    generate for (k = 0; k < 16; k = k + 1) begin : g_c
        // request chain: head -> tap 15 -> ... -> tap 0 ; response chain: tap 0 -> ... -> tap 15 -> head
        reg [42:0] rq_d [0:CS]; reg [267:0] rp_d [0:CS];
        wire [42:0] rsrc = (k == 15) ? rco_h : rco[k + 1];
        wire [267:0] psrc = (k == 0) ? 268'd0 : pco[k - 1];
        always @(posedge ck) begin : g_rly
            integer i; rq_d[0] <= rsrc; rp_d[0] <= psrc;
            for (i = 1; i <= CS; i = i + 1) begin rq_d[i] <= rq_d[i - 1]; rp_d[i] <= rp_d[i - 1]; end
        end
        assign rci[k] = rq_d[CS]; assign pci[k] = rp_d[CS];
        assign rqi[k] = (k == RD) ? rdr_rq : 92'd0;
        dsdv_eng_tap_c #(.WEST(k == 0), .MUT(TAP_MUT)) u_t (.ck(ck), .rst_n(rst), .sid(4'(k)), .rci(rci[k]), .rco(rco[k]),
            .pci(pci[k]), .pco(pco[k]), .rqi(rqi[k]), .rqo(rqo[k]), .rri(rri[k]), .rro(rro[k]), .fault(tf[k]));
        dsfd_ctrl_rg3 #(.DQ(8), .RFD(24)) u_k (.clk(ck), .ckh(ckh), .rst_n(rst), .rq(682'd0), .rd(rd[k]), .ck_o(),
            .rrq(rqo[k]), .rrd(rri[k]),
            .k_v(kv[k]), .k_rdy(krdy[k]), .k_addr(kad[k]), .k_len(kln[k]), .k_tag(ktg[k]), .k_we(kwe[k]), .k_wdata(kwdat[k]),
            .k_wstrb(kws[k]), .k_wr_done(kwd[k]), .kr_v(krv[k]), .kr_rdy(krrdy[k]), .kr_tag(krt[k]), .kr_beat(krb[k]), .kr_data(krd[k]));
    end endgenerate
    reg [267:0] h_d [0:CS];
    always @(posedge ck) begin : g_hr
        integer i; h_d[0] <= pco[15]; for (i = 1; i <= CS; i = i + 1) h_d[i] <= h_d[i - 1];
    end
    assign pci_h = h_d[CS];
    // HBM image: Engram atoms written by the bench at request time; everything else = pdat
    reg [255:0] mem [longint];
    function automatic [255:0] pdat(input [29:0] a, input integer pc);
        pdat = {8{mix(64'h5100_0000 + 64'(a) * 64 + pc)}};
    endfunction
    function automatic [255:0] rdmem(input integer pc, input [29:0] a);
        longint key; key = (longint'(pc) << 32) | longint'(a);
        rdmem = mem.exists(key) ? mem[key] : pdat(a, pc);
    endfunction
    typedef struct packed { longint rdy_t; logic [29:0] a; logic [3:0] ln; logic [16:0] tg; } ent_t;
    genvar gp;
    generate for (k = 0; k < 16; k = k + 1) begin : g_phy
        for (gp = 0; gp < 2; gp = gp + 1) begin : g_pc
            ent_t q[$];
            reg [3:0] bt = 0; reg rv = 0; reg [16:0] rtg = 0; reg [3:0] rbt = 0; reg [255:0] rdat = 0;
            assign krdy[k][gp] = rst && (mix(64'h5200_0000 + hcyc * 32 + 2 * k + gp) % 4 != 0);
            assign krv[k][gp] = rv; assign krt[k][17 * gp +: 17] = rtg; assign krb[k][4 * gp +: 4] = rbt;
            assign krd[k][256 * gp +: 256] = rdat; assign kwd[k][gp] = 1'b0;
            always @(posedge ckh) begin
                if (kv[k][gp] && krdy[k][gp]) q.push_back('{hcyc + LAT, kad[k][30 * gp +: 30], kln[k][4 * gp +: 4], ktg[k][17 * gp +: 17]});
                if (rv && krrdy[k][gp]) rv <= 1'b0;
                if ((!rv || krrdy[k][gp]) && q.size() > 0 && q[0].rdy_t <= hcyc) begin
                    rv <= 1'b1; rtg <= q[0].tg; rbt <= bt; rdat <= rdmem(2 * k + gp, q[0].a + 30'(bt));
                    if (bt + 4'd1 == q[0].ln) begin bt <= 0; void'(q.pop_front()); end else bt <= bt + 4'd1;
                end
            end
        end
    end endgenerate
    // ------------------------------------------------------------------ Engram rows (written when the lookup requests)
    integer errs = 0, e_win = 0, e_ob = 0, e_xq = 0, e_rd = 0, e_rung = 0, e_flt = 0;
    integer win_n = 0, ob_n = 0, xq_n [0:1], rd_rq = 0, rd_beats = 0, rd_pops = 0, rung_n = 0;
    reg [7:0] rowb [0:5][0:271];
    integer req_j = 0;
    always @(negedge ck) if (rst && u_rr.hq_v) begin : g_fill
        integer j, kk, off; reg [31:0] crc, m; longint atom, key; reg [35:0] ba;
        j = u_rr.hq_tag;
        ba = u_rr.u_lkp.u_e.baddr[j];
        off = ba[4:0];
        if (ba[35:5] !== u_rr.hq_atom) begin e_ob = e_ob + 1; $display("TB_ENG_RR request atom %h != baddr %h", u_rr.hq_atom, ba); end
        crc = 32'hffffffff;
        for (kk = 0; kk < 264; kk = kk + 1) begin : g_b
            integer bi;
            m = mix(64'h6100_0000 + 64'(win_n) * 4096 + j * 300 + kk);
            if (kk < 256) rowb[j][kk] = (m[6:0] == 7'h7F) ? {m[7], 7'h7E} : m[7:0];            // no NaN code
            else rowb[j][kk] = 8'd110 + 8'(m % 26);                                           // scale 2^-17 .. 2^8
            for (bi = 7; bi >= 0; bi = bi - 1) crc = {crc[30:0], 1'b0} ^ ((crc[31] ^ rowb[j][kk][bi]) ? 32'h04c11db7 : 32'd0);
        end
        for (kk = 0; kk < 4; kk = kk + 1) rowb[j][264 + kk] = crc[8 * kk +: 8];
        for (kk = 268; kk < 272; kk = kk + 1) rowb[j][kk] = 8'd0;
        for (kk = 0; kk < 9; kk = kk + 1) begin : g_a
            reg [255:0] w; integer b;
            atom = longint'(ba[35:5]) + kk;
            key = (longint'(atom & 31) << 32) | longint'(PCBASE + 30'(atom >> 5));
            w = mem.exists(key) ? mem[key] : 256'd0;
            for (b = 0; b < 32; b = b + 1) if (32 * kk + b >= off && 32 * kk + b - off < 272) w[8 * b +: 8] = rowb[j][32 * kk + b - off];
            mem[key] = w;
        end
    end
    // lookup row beats: = the image row; logged for the python bit-exact check
    always @(negedge ck) if (rst && u_rr.o_v) begin : g_ob
        integer j, kk; reg [263:0] exp_;
        j = u_rr.o_col - 5'(6 * RANK);
        for (kk = 0; kk < 32; kk = kk + 1) exp_[8 * kk +: 8] = rowb[j][32 * u_rr.o_beat + kk];
        exp_[263:256] = rowb[j][256 + u_rr.o_beat];
        if (u_rr.o_d !== exp_) begin e_ob = e_ob + 1; if (e_ob <= 4) $display("TB_ENG_RR row beat mismatch col %0d beat %0d", u_rr.o_col, u_rr.o_beat); end
        $display("OB %0d %0d %0d %h", win_n - 1, u_rr.o_col, u_rr.o_beat, u_rr.o_d);
        ob_n = ob_n + 1;
    end
    // latency record (priced into the compiler schedule): f_ks start -> win_v / first request / max response age at the
    // lookup engine / first and last XQ fragment on the rung
    longint t_ks = 0, l_win = 0, l_rq = 0, l_x0 = 0, l_x1 = 0; integer age_max = 0, nfr = 0;
    always @(negedge ck) if (rst) begin
        if (f_ks[52]) begin t_ks = cyc; nfr = 0; end
        if (u_rr.win_v) l_win = cyc - t_ks;
        if (u_rr.hq_v && u_rr.hq_tag == 0) l_rq = cyc - t_ks;
        if (u_rr.u_lkp.u_e.hr_valid && u_rr.u_lkp.u_e.age > age_max) age_max = u_rr.u_lkp.u_e.age;
        if (u_rr.u_xq.tx) begin if (nfr == 0) l_x0 = cyc - t_ks; nfr = nfr + 1; l_x1 = cyc - t_ks; end
    end
    // ------------------------------------------------------------------ windows: NgramHashState model
    function automatic [16:0] cid(input [20:0] t); cid = 17'((longint'(t) * 7919 + 11) % 99092); endfunction
    reg [16:0] hist [0:63][0:2];
    reg [67:0] exp_win [$];
    always @(negedge ck) if (rst && u_rr.win_v) begin
        if (exp_win.size() == 0 || u_rr.win_ids !== exp_win[0]) begin
            e_win = e_win + 1; $display("TB_ENG_RR window %0d mismatch %h exp %h", win_n, u_rr.win_ids, exp_win.size() ? exp_win[0] : 68'd0);
        end
        if (exp_win.size()) void'(exp_win.pop_front());
        win_n = win_n + 1;
    end
    // ------------------------------------------------------------------ XQ trains on both directions
    reg [1103:0] fb [0:1]; integer fn [0:1];
    initial begin fn[0] = 0; fn[1] = 0; xq_n[0] = 0; xq_n[1] = 0; end
    reg [275:0] ps [0:1][0:1];
    always @(posedge ck) begin ps[0][0] <= vi_s; ps[0][1] <= ps[0][0]; ps[1][0] <= vi_n; ps[1][1] <= ps[1][0]; end
    reg prev_tx = 0;                           // tx during the previous cycle: vo carries that cycle's fragment
    always @(negedge ck) if (rst) begin : g_xq
        integer d; reg [275:0] v;
        // rung pass-through (+2 edges) whenever the previous cycle sent no own fragment
        if (!prev_tx && cyc > 40 && (vo_n !== ps[0][1] || vo_s !== ps[1][1])) begin
            e_rung = e_rung + 1; if (e_rung <= 4) $display("TB_ENG_RR rung pass-through mismatch cyc %0d", cyc);
        end
        for (d = 0; d < 2; d = d + 1) begin
            v = d ? vo_n : vo_s;
            if (prev_tx || fn[d] != 0) begin
                if (fn[d] == 0 && !(v[0] && v[3:1] == 3'd1)) begin e_xq = e_xq + 1; $display("TB_ENG_RR dir %0d train without XQ header", d); end
                fb[d][276 * fn[d] +: 276] = v;
                if (fn[d] == 3) begin
                    $display("XQ %0d %0d %0d %h", d, win_n - 1, fb[d][20:13], fb[d][552:21]);
                    if (fb[d][20:13] < 8'(24 * RANK) || fb[d][20:13] >= 8'(24 * RANK + 24)) begin e_xq = e_xq + 1; $display("TB_ENG_RR idx %0d outside the rank", fb[d][20:13]); end
                    xq_n[d] = xq_n[d] + 1; fn[d] = 0;
                end else fn[d] = fn[d] + 1;
            end
        end
        prev_tx = u_rr.u_xq.tx;
    end
    // ------------------------------------------------------------------ rung pass-through (+2 edges)
    // ------------------------------------------------------------------ bench reader (controller RD, both lanes)
    typedef struct packed { logic [29:0] a; logic [3:0] ln; logic [9:0] t; } rq_t;
    rq_t rqq [0:1][$];
    reg [3:0] rbeat [0:1]; integer own [0:1];
    initial begin rbeat[0] = 0; rbeat[1] = 0; own[0] = 0; own[1] = 0; end
    always @(negedge ck) if (rst) begin : g_rchk
        integer p; reg [271:0] l;
        for (p = 0; p < 2; p = p + 1) begin
            l = rro[RD][272 * p +: 272];
            if (l[1]) begin rd_pops = rd_pops + 1; own[p] = own[p] - 1; end
            if (l[0]) begin
                rd_beats = rd_beats + 1;
                if (rqq[p].size() == 0) begin e_rd = e_rd + 1; if (e_rd <= 4) $display("TB_ENG_RR reader beat with no request pc %0d tag %h", p, l[15:6]); end
                else begin
                    if (l[15:6] !== rqq[p][0].t || l[5:2] !== rbeat[p] || l[271:16] !== pdat(rqq[p][0].a + 30'(rbeat[p]), 2 * RD + p)) begin
                        e_rd = e_rd + 1; if (e_rd <= 4) $display("TB_ENG_RR reader beat mismatch pc %0d tag %h/%h", p, l[15:6], rqq[p][0].t);
                    end
                    if (rbeat[p] + 4'd1 == rqq[p][0].ln) begin rbeat[p] = 0; void'(rqq[p].pop_front()); end else rbeat[p] = rbeat[p] + 4'd1;
                end
            end
        end
    end
    function automatic [9:0] rtag(input integer n);       // dsdv_idx_rg3 tag10 codes {g, slot3, cell4, sc, s3}
        reg [31:0] m; m = mix(64'h6300_0000 + n);
        case (m[1:0])
            2'd0: rtag = {1'b0, m[4:2], 4'd0, 1'b1, m[5]};                     // scan k 0: scales (sc 1, cell 0)
            2'd1, 2'd2: rtag = {1'b0, m[4:2], {m[8:6], 1'b0}, 1'b0, m[5]};     // scan cells 0, 2, .. 14 (sc 0)
            default: rtag = {1'b1, m[4:2], m[9:6], m[10], m[5]};               // gather
        endcase
    endfunction
    // ------------------------------------------------------------------ stimulus
    localparam integer SP = RETURN_AGE + 64 + 400;     // edges between windows (> lookup II)
    initial begin : g_run
        integer w, u, p, n, kk, users [0:5], posn [0:63]; reg [20:0] tok; longint t0, tw;
        users[0] = 3; users[1] = 7; users[2] = 3; users[3] = 9; users[4] = 3; users[5] = 7;
        for (u = 0; u < 64; u = u + 1) posn[u] = 0;
        repeat (20) @(posedge ck); rst = 1; t0 = cyc;
        n = 0;
        for (w = 0; w < NW; w = w + 1) begin
            tw = t0 + 200 + w * SP;
            // rung traffic + reader burst before the window (reader responses still in flight when it starts)
            while (cyc < tw - 160) begin
                @(negedge ck);
                vi_s = 0; vi_n = 0; rdr_rq[0] = 0; rdr_rq[46] = 0;
                rdr_rq[1] = own[0] > 0; rdr_rq[47] = own[1] > 0;   // reader window: open while its requests are owed
                if (cyc >= tw - 250 && cyc < tw - 40 && cyc % 9 == 0) begin
                    vi_s[275:20] = {8{mix(cyc * 3 + 1)}}; vi_s[3:0] = 4'b0001; rung_n = rung_n + 1; end
                if (cyc >= tw - 250 && cyc < tw - 40 && cyc % 11 == 0) begin
                    vi_n[275:20] = {8{mix(cyc * 5)}}; vi_n[3:0] = 4'b0001; rung_n = rung_n + 1; end
            end
            while (cyc < tw - 20) begin
                @(negedge ck);
                vi_s = 0; vi_n = 0; rdr_rq[0] = 0; rdr_rq[46] = 0;
                rdr_rq[1] = 1; rdr_rq[47] = 1;
                for (p = 0; p < 2; p = p + 1) if (own[p] < 12 && mix(64'h5600_0000 + cyc * 2 + p) % 3 == 0) begin : g_i
                    rq_t r; reg [31:0] m;
                    m = mix(64'h5700_0000 + n);
                    r.a = 30'(50000 + 16 * n + p); r.ln = 4'(1 + m[1:0]); r.t = rtag(n);
                    rdr_rq[46 * p +: 46] = {r.t, r.ln, r.a, 1'b1, 1'b1};
                    rqq[p].push_back(r); own[p] = own[p] + 1; rd_rq = rd_rq + 1; n = n + 1;
                end
            end
            @(negedge ck); rdr_rq[0] = 0; rdr_rq[46] = 0; rdr_rq[1] = own[0] > 0; rdr_rq[47] = own[1] > 0;
            // the token start of user users[w % 6]
            u = users[w % 6]; tok = 21'(mix(64'h6200_0000 + w) % 129280);
            begin : g_exp
                reg [16:0] c; reg b1, b2, b3;
                c = cid(tok); b1 = posn[u] < 1; b2 = b1 | (posn[u] < 2); b3 = b2 | (posn[u] < 3);
                exp_win.push_back({b3 ? 17'd2 : hist[u][2], b2 ? 17'd2 : hist[u][1], b1 ? 17'd2 : hist[u][0], c});
                hist[u][2] = hist[u][1]; hist[u][1] = hist[u][0]; hist[u][0] = c;
            end
            f_ks = {1'b1, 10'(u), tok, 21'(posn[u])}; posn[u] = posn[u] + 1;
            @(negedge ck); f_ks = 0; rdr_rq[1] = own[0] > 0; rdr_rq[47] = own[1] > 0;
        end
        while (cyc < t0 + 200 + NW * SP) begin @(negedge ck); rdr_rq[1] = own[0] > 0; rdr_rq[47] = own[1] > 0; end
        // ------------------------------------------------------------------ verdict
        if (win_n != NW) begin e_win = e_win + 1; $display("TB_ENG_RR windows %0d != %0d", win_n, NW); end
        if (ob_n != 48 * NW) begin e_ob = e_ob + 1; $display("TB_ENG_RR row beats %0d != %0d", ob_n, 48 * NW); end
        if (xq_n[0] != 24 * NW || xq_n[1] != 24 * NW) begin e_xq = e_xq + 1; $display("TB_ENG_RR XQ trains %0d / %0d != %0d", xq_n[0], xq_n[1], 24 * NW); end
        if (rqq[0].size() != 0 || rqq[1].size() != 0) begin e_rd = e_rd + 1; $display("TB_ENG_RR reader requests unanswered %0d %0d", rqq[0].size(), rqq[1].size()); end
        if (rd_pops != rd_rq) begin e_rd = e_rd + 1; $display("TB_ENG_RR reader pops %0d != requests %0d", rd_pops, rd_rq); end
        if (st !== 4'd0 || tf !== 16'd0) begin e_flt = e_flt + 1; $display("TB_ENG_RR faults st %b taps %b", st, tf); end
        for (kk = 0; kk < 16; kk = kk + 1) if (rd[kk][561] !== 1'b0) begin e_flt = e_flt + 1; $display("TB_ENG_RR controller %0d status fault", kk); end
        errs = e_win + e_ob + e_xq + e_rd + e_rung + e_flt;
`ifdef OT_S81ENG_RR_SPLIT_LOCKSTEP
        $display("TB_ENG_RR_LOCKSTEP split_mut %0d cycles %0d crossing_beats %0d rco_words %0d rung_words %0d mismatches %0d",
                 SPLIT_MUT, lk_cyc, lk_xv, lk_rco, lk_vo, lk_bad);
        if (lk_bad != 0 || lk_xv == 0) errs = errs + 1;
`endif
        $display("TB_ENG_RR_LAT (edges from the f_ks start, last window) win_v %0d first_request %0d max_response_age %0d / RETURN_AGE %0d first_fragment %0d last_fragment %0d",
                 l_win, l_rq, age_max, RETURN_AGE, l_x0 + 1, l_x1 + 1);
        $display("TB_ENG_RR_STATS xq_mut %0d tap_mut %0d seed %0d lat %0d windows %0d row_beats %0d xq %0d/%0d reader rq %0d beats %0d pops %0d rung %0d errs win %0d ob %0d xq %0d rd %0d rung %0d flt %0d",
                 XQ_MUT, TAP_MUT, SEED, LAT, win_n, ob_n, xq_n[0], xq_n[1], rd_rq, rd_beats, rd_pops, rung_n, e_win, e_ob, e_xq, e_rd, e_rung, e_flt);
        if (errs != 0 || rd_rq == 0 || rung_n == 0) $display("TB_ENG_RR FAIL"); else $display("TB_ENG_RR PASS");
        $finish;
    end
endmodule
