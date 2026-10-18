`timescale 1ns/1ps
// S81U-SVC 2026-10-17: exact bench of the 16 regional service slices dsdv_svc_rs (2 x 8 grid, sid = 2 col + row,
// abutted faces; root slice 9 = dsdv_svc_rs_root) against the dsfd_svc_c GOLDEN (tools/v41_ckv_sel_attn_vectors.py,
// the vectors tb_dsfd_svc_c runs: window rows qdq_fp8 through OWN_ROW frames -> HBM -> the window load, selected rows
// qdq_fp4_e4m3 owned here from HBM / held elsewhere on ROWS frames, q, p; expected scores sc.hex and p.v pv.hex).
// The bench is the VM + host + 16 regional controllers: it arms the job on j (frame count, END source 0), sends the q
// frames into the ROOT's q pin (CFG, OWN_ROW x wcount, WIN_LOAD, SEL_IDS, ATTN_Q x 2, SMJ (SE job + 2 parameter rows),
// ROWS (shuffled), GO at a compiled cycle, then PV after the last root score), host sector writes on hw with the
// 8-credit hc contract, and models every slice's 2 PCs (request queue, DQ 8 credits, latency lat + rand, in-order
// beats) on the compiler's dim-sliced image (the owned compressed rows pre-written per slice; the window rows only
// through the slices' own OWN_ROW writes).
// Checks (PASS = all zero):
//   root   every complete score beat (16 heads x 4 rows) of the HELD rows bit-exact (flags as expected; value
//          unless flagged), beats in row order, exactly ceil(T / 4) beats;
//   SM     every slice's SE operand row (16 rows of its head = tile) equals the golden scores of the held rows;
//          SE rows = ceil(T / 16); the SM head writes one e row per SE row, no SM fault;
//   P.V    the 4 owner slices (tiles 4 ST ..): 8 beats each, every word bit-exact vs pv.hex (dims 32 t + 8 j + c);
//   job    one jd done, no jd fault, no slice fault (att / sx / stream / SM), host image + acks + credits,
//          HBM credit discipline (<= 8 per PC).
module tb_dsdv_svc_rs;
    parameter integer DIE = 0;
    parameter integer ST = 0;
    parameter integer MAXCYC = 400000;
    parameter integer GODLY = 400;
`ifndef MUT
`define MUT 0
`endif
`include "dsdv_svc_rs_roles.svh"
    localparam integer H = 16, D = 512, NHBM = 32768, WB = 30'h100, SB = 30'h1000, WFIRST = 1000, WUSER = 3;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst = 0;
    reg [31:0] cfg [0:31];
    reg [31:0] selm [0:511];
    reg [4223:0] winm [0:127];
    reg [63:0] hkey [0:NHBM-1];
    reg [255:0] hdat [0:NHBM-1];
    reg [D*16-1:0] qm [0:H-1];
    reg [511:0] pm [0:639];
    reg [H*33-1:0] scm [0:639];
    reg [H*33-1:0] pvm [0:D-1];
    reg [255:0] img [longint];            // vector image (die, stack, addr)
    reg [255:0] hbm [longint];            // slice HBM: ((2 sid + pc) << 32) | addr
    reg [1023:0] dir;
    integer seed = 1, lat = 40;
    integer wcount, nsel, T, nh;
    integer i, k, h, s;
    function automatic integer tile_of(input integer sd); reg [21:0] r; r = rs_role(4'(sd)); tile_of = r[3:0]; endfunction
    function automatic [1:0] odie(input integer g); odie = g[5:4]; endfunction
    function automatic [1:0] ostk(input integer g); ostk = g[7:6]; endfunction
    function automatic integer olocal(input integer g); olocal = ((g >> 8) << 4) | (g & 15); endfunction
    function automatic [2303:0] imgrow(input integer g);
        integer kk; longint key;
        imgrow = 0;
        for (kk = 0; kk < 9; kk = kk + 1) begin
            key = (longint'(odie(g)) << 32) | (longint'(ostk(g)) << 30) | longint'(cfg[9 + ostk(g)] + 9 * olocal(g) + kk);
            imgrow[256*kk +: 256] = img.exists(key) ? img[key] : 256'd0;
        end
    endfunction
    function automatic bit held_sel(input integer r); held_sel = ostk(selm[r]) == 2'(ST); endfunction
    function automatic bit own_sel(input integer r); own_sel = odie(selm[r]) == 2'(DIE) && ostk(selm[r]) == 2'(ST); endfunction
    function automatic bit held_row(input integer t);
        held_row = (t < wcount) ? (t % 4 == ST) : held_sel(t - wcount);
    endfunction
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("lat=%d", lat)) ;
        $readmemh({dir, "/cfg.hex"}, cfg);
        $readmemh({dir, "/sel.hex"}, selm);
        $readmemh({dir, "/win.hex"}, winm);
        $readmemh({dir, "/hkey.hex"}, hkey);
        $readmemh({dir, "/hdat.hex"}, hdat);
        $readmemh({dir, "/q.hex"}, qm);
        $readmemh({dir, "/p.hex"}, pm);
        $readmemh({dir, "/sc.hex"}, scm);
        $readmemh({dir, "/pv.hex"}, pvm);
        wcount = cfg[0]; nsel = cfg[1]; nh = cfg[3]; T = cfg[4];
        for (i = 0; i < nh; i = i + 1) img[hkey[i]] = hdat[i];
        void'($urandom(seed));
        // compiler layout: every owned compressed row's block (16 rows x 144 b per tile, 9 sectors on PC g[8])
        for (i = 0; i < nsel; i = i + 1) if (own_sel(i)) begin
            integer g0, kk, sd, t, b; reg [2303:0] blk; reg [2303:0] row;
            g0 = selm[i] & ~15;
            for (sd = 0; sd < 16; sd = sd + 1) begin
                t = tile_of(sd); blk = 0;
                for (kk = 0; kk < 16; kk = kk + 1) begin
                    row = imgrow(g0 | kk);
                    blk[144*kk +: 144] = {row[2048 + 16*t +: 16], row[128*t +: 128]};
                end
                for (b = 0; b < 9; b = b + 1)
                    hbm[(longint'(2 * sd + ((g0 >> 8) & 1)) << 32) | longint'(SB + 9 * (g0 >> 9) + b)] = blk[256*b +: 256];
            end
        end
    end

    // ---------------- 16 slices ----------------
    localparam integer W = 2132, SW = 1076, DW = 805, UW = 14;
    wire [3:0] gi_v [0:15], go_v [0:15], si_v [0:15], so_v [0:15];
    wire [4*W-1:0] gi_d [0:15], go_d [0:15]; wire [4*SW-1:0] si_d [0:15], so_d [0:15];
    wire [4*DW-1:0] dn_i [0:15], dn_o [0:15]; wire [4*UW-1:0] up_i [0:15], up_o [0:15];
    wire [2*341-1:0] rq [0:15]; reg [1:0] rk [0:15], wd [0:15], rv [0:15];
    reg [2*256-1:0] r_data [0:15]; reg [2*17-1:0] r_tag [0:15]; reg [2*4-1:0] r_beat [0:15];
    wire [15:0] pv_v, w_v; wire [512:0] pv_d [0:15]; wire [13:0] w_a [0:15]; wire [15:0] w_m [0:15];
    wire [511:0] w_d [0:15]; wire [11:0] w_st [0:15];
    reg [32:0] jcmd = 0; wire [1:0] jd; reg q_v = 0; reg [511:0] q_d = 0; reg [291:0] hw = 0; wire [8:0] hc; wire rflt;
    function automatic integer nb(input integer sd, input integer fc);
        integer r, c;
        r = sd % 2; c = sd / 2;
        case (fc)
            0: nb = (r == 0) ? 2*c + 1 : -1;
            1: nb = (c < 7) ? 2*(c+1) + r : -1;
            2: nb = (r == 1) ? 2*c : -1;
            default: nb = (c > 0) ? 2*(c-1) + r : -1;
        endcase
    endfunction
    genvar gs, gf;
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_s
        for (gf = 0; gf < 4; gf = gf + 1) begin : g_f
            localparam integer NBS = nb(gs, gf), OF = (gf + 2) % 4;
            if (NBS >= 0) begin : g_c
                assign gi_v[gs][gf] = go_v[NBS][OF]; assign gi_d[gs][W*gf +: W] = go_d[NBS][W*OF +: W];
                assign si_v[gs][gf] = so_v[NBS][OF]; assign si_d[gs][SW*gf +: SW] = so_d[NBS][SW*OF +: SW];
                assign dn_i[gs][DW*gf +: DW] = dn_o[NBS][DW*OF +: DW]; assign up_i[gs][UW*gf +: UW] = up_o[NBS][UW*OF +: UW];
            end else begin : g_e
                assign gi_v[gs][gf] = 1'b0; assign gi_d[gs][W*gf +: W] = '0;
                assign si_v[gs][gf] = 1'b0; assign si_d[gs][SW*gf +: SW] = '0;
                assign dn_i[gs][DW*gf +: DW] = '0; assign up_i[gs][UW*gf +: UW] = '0;
            end
        end
        if (gs == 9) begin : g_r
            dsdv_svc_rs_root #(.MUT(`MUT), .DIE_ID(DIE), .ST(ST)) u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .j(jcmd), .jd(jd), .q({1'b0, 1'b1, q_d, q_v}), .hw(hw), .hc(hc), .fault(rflt),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(2'b01), .pv_v(pv_v[gs]), .pv_d(pv_d[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]));
        end else begin : g_n
            dsdv_svc_rs #(.MUT(`MUT), .DIE_ID(DIE), .ST(ST)) u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(2'b01), .pv_v(pv_v[gs]), .pv_d(pv_d[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]));
        end
    end endgenerate
    // per-slice local faults (diagnostic probes; the root fault / jd carry them)
    wire [15:0] sflt; wire [31:0] afc [0:15];
    wire [15:0] se_v; wire [511:0] se_d [0:15];
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_p
        if (gs == 9) begin : g_r
            assign sflt[gs] = g_s[gs].g_r.u.u.lf; assign afc[gs] = g_s[gs].g_r.u.u.a_fc;
            assign se_v[gs] = g_s[gs].g_r.u.u.se_v; assign se_d[gs] = g_s[gs].g_r.u.u.se_d;
        end else begin : g_n
            assign sflt[gs] = g_s[gs].g_n.u.u.lf; assign afc[gs] = g_s[gs].g_n.u.u.a_fc;
            assign se_v[gs] = g_s[gs].g_n.u.u.se_v; assign se_d[gs] = g_s[gs].g_n.u.u.se_d;
        end
    end endgenerate

    // ---------------- q frames ----------------
    localparam integer QMAX = 8192;
    reg [511:0] qw [0:QMAX-1];
    integer nq = 0, nq_go = 0, nq_pv = 0, nframes = 0, last_hdr = 0, npair_in = 0;
    integer order [0:4095];
    function automatic [511:0] hdr(input [3:0] typ, input [11:0] len, input [448:0] spec);
        hdr = {typ, 1'b0, 4'b0001, 8'h5a, 3'd0, len, 21'd777, 10'd3, spec};
        nframes = nframes + 1; last_hdr = nq;
    endfunction
    task automatic build_frames();
        reg [448:0] sp; integer r, t, n, b, pr, cnt, base, sz; reg [2303:0] row;
        sp = 0; sp[29:0] = WB;
        qw[nq] = hdr(4'd12, 0, sp); nq = nq + 1;
        for (r = 0; r < wcount; r = r + 1) begin
            qw[nq] = hdr(4'd3, 12'd16, 449'd0); qw[nq][479:459] = WFIRST + r; qw[nq][458:449] = WUSER; nq = nq + 1;
            for (b = 0; b < 16; b = b + 1) begin
                qw[nq] = 0; qw[nq][255:0] = winm[r][256*b +: 256]; qw[nq][263:256] = winm[r][4096 + 8*b +: 8]; nq = nq + 1;
            end
        end
        sp = 0; sp[29:0] = SB; sp[88:81] = wcount; sp[98:89] = nsel; sp[119:99] = WFIRST;
        qw[nq] = hdr(4'd2, 0, sp); qw[nq][458:449] = WUSER; nq = nq + 1;
        n = (nsel + 15) / 16;
        sp = 0; sp[19:10] = nsel;
        if (nsel > 0) begin
            qw[nq] = hdr(4'd7, 12'(n), sp); nq = nq + 1;
            for (b = 0; b < n; b = b + 1) begin
                qw[nq] = 0;
                for (r = 0; r < 16; r = r + 1) if (16 * b + r < nsel) qw[nq][32*r +: 32] = selm[16 * b + r];
                nq = nq + 1;
            end
        end
        for (b = 0; b < 2; b = b + 1) begin
            sp = 0; sp[448] = b[0];
            qw[nq] = hdr(4'd1, 12'd128, sp); nq = nq + 1;
            for (r = 0; r < 128; r = r + 1) begin qw[nq] = qm[8 * b + r / 16][512 * (r % 16) +: 512]; nq = nq + 1; end
        end
        // SM head: SE job (kind 4), parameter rows 0 (fields) and 1 (sinks)
        sp = 0; sp[0] = 1'b1; sp[4:1] = 4'd4; sp[12:5] = 8'h21;
        qw[nq] = hdr(4'd9, 12'd2, sp); nq = nq + 1;
        qw[nq] = 0; qw[nq][13:0] = 14'd0; qw[nq][64 +: 7] = 7'((T + 15) / 16); qw[nq][96 +: 32] = 32'h3dc00000;
        qw[nq][128 +: 3] = 3'($clog2((T + 15) / 16)); nq = nq + 1;
        qw[nq] = 0; for (h = 0; h < 16; h = h + 1) qw[nq][32*h +: 32] = 32'hc0000000 | (h << 18); nq = nq + 1;
        cnt = 0;
        for (r = 0; r < nsel; r = r + 1) if (!own_sel(r))
            for (pr = 0; pr < 8; pr = pr + 1) if (held_sel(r) || pr / 2 == ST) begin order[cnt] = r * 8 + pr; cnt = cnt + 1; end
        for (r = cnt - 1; r > 0; r = r - 1) begin t = $urandom % (r + 1); b = order[r]; order[r] = order[t]; order[t] = b; end
        npair_in = cnt; base = 0;
        while (base < cnt) begin
            sz = (cnt - base > 200) ? 200 : cnt - base;
            qw[nq] = hdr(4'd6, 12'(sz), 449'd0); nq = nq + 1;
            for (b = 0; b < sz; b = b + 1) begin
                r = order[base + b] / 8; pr = order[base + b] % 8; row = imgrow(selm[r]);
                qw[nq] = 0; qw[nq][9:0] = r; qw[nq][30:10] = selm[r]; qw[nq][33:31] = pr;
                qw[nq][289:34] = row[256*pr +: 256]; qw[nq][321:290] = row[2048 + 32*pr +: 32];
                nq = nq + 1;
            end
            base = base + sz;
        end
        nq_go = nq;
        qw[nq] = hdr(4'd13, 0, 449'd0); nq = nq + 1;
        nq_pv = nq;
        n = (T + 1) / 2; base = 0;
        while (base < n) begin
            sz = (n - base > 250) ? 250 : n - base;
            qw[nq] = hdr(4'd5, 12'(sz), 449'd0); nq = nq + 1;
            for (b = 0; b < sz; b = b + 1) begin qw[nq] = pm[base + b]; nq = nq + 1; end
            base = base + sz;
        end
        qw[last_hdr][507] = 1'b1;      // protocol v1.1: END on the job's last q frame
    endtask

    // ---------------- host writes (dsfd_host_sd hw / hc: 8 credits, cr per word taken, ack per completed sector) ----
    localparam integer NHW = 96;
    integer h_cred = 8, h_sent = 0, h_ack = 0, h_err = 0, h_mark = 0;
    reg [255:0] h_dat [0:NHW-1]; reg [31:0] h_adr [0:NHW-1];
    integer cyc = 0;
    initial for (i = 0; i < NHW; i = i + 1) begin
        h_adr[i] = (i < NHW / 2) ? 32'h0300_0000 + 32'(i * 5) : 32'h8300_0000 + 32'(i * 7);
        for (k = 0; k < 8; k = k + 1) h_dat[i][32*k +: 32] = 32'h1234_5678 * (i + 1) + k;
    end
    function automatic [4:0] pcmap(input [29:0] a); reg [29:0] x; x = (a >> 2) ^ (a >> 7) ^ (a >> 12); pcmap = x[4:0]; endfunction
    always @(posedge ck) begin
        hw <= 0;
        h_cred = h_cred + hc[0]; h_ack = h_ack + hc[8:1];
        if (rst && cyc > 30 && h_cred > 0 && ($urandom % 4) == 0) begin
            if (h_sent < NHW) begin
                hw <= {(h_adr[h_sent][31] ? 2'd1 : 2'd0), 1'b1, h_adr[h_sent], h_dat[h_sent], 1'b1}; h_sent = h_sent + 1; h_cred = h_cred - 1;
            end else if (h_mark == 0) begin
                hw <= {2'd0, 1'b1, 32'hffffffff, 256'h0b007_e2d, 1'b1}; h_mark = 1; h_cred = h_cred - 1;
            end
        end
    end
    task automatic host_check();
        integer ii; longint kk; reg [4:0] pc;
        for (ii = 0; ii < NHW; ii = ii + 1) begin
            pc = pcmap(h_adr[ii][29:0]);
            kk = (longint'(pc) << 32) | longint'(h_adr[ii][29:0]);
            if (!hbm.exists(kk) || hbm[kk] !== h_dat[ii]) h_err = h_err + 1;
        end
        if (h_ack != NHW || h_cred != 8) h_err = h_err + 1;
    endtask

    // ---------------- HBM: 32 PCs (slice s, pc p = index 2 s + p) ----------------
    localparam integer PQ = 64;
    integer pq_t [0:31][0:PQ-1]; reg [340:0] pq_w [0:31][0:PQ-1]; integer pq_h [0:31], pq_n [0:31], pq_b [0:31];
    integer cred_err = 0;
    initial for (i = 0; i < 32; i = i + 1) begin pq_h[i] = 0; pq_n[i] = 0; pq_b[i] = 0; end
    always @(posedge ck) begin
        reg [340:0] w341; reg [255:0] old; longint key; integer pc, sd, pp, jj;
        for (sd = 0; sd < 16; sd = sd + 1) begin rk[sd] <= 0; wd[sd] <= 0; rv[sd] <= 0; end
        for (pc = 0; pc < 32; pc = pc + 1) begin
            sd = pc / 2; pp = pc % 2;
            if (rq[sd][341*pp]) begin
                pq_t[pc][(pq_h[pc] + pq_n[pc]) % PQ] = cyc + lat + ($urandom % 16);
                pq_w[pc][(pq_h[pc] + pq_n[pc]) % PQ] = rq[sd][341*pp +: 341];
                pq_n[pc] = pq_n[pc] + 1;
                if (pq_n[pc] > 8) cred_err = cred_err + 1;
            end
            if (pq_n[pc] > 0 && pq_t[pc][pq_h[pc]] <= cyc) begin
                w341 = pq_w[pc][pq_h[pc]];
                key = (longint'(pc) << 32) | longint'(w341[31:2] + (w341[1] ? 0 : pq_b[pc]));
                if (w341[1]) begin
                    old = hbm.exists(key) ? hbm[key] : 256'd0;
                    for (jj = 0; jj < 32; jj = jj + 1) if (w341[53 + jj]) old[8*jj +: 8] = w341[85 + 8*jj +: 8];
                    hbm[key] = old; wd[sd][pp] <= 1'b1; rk[sd][pp] <= 1'b1;
                    pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1;
                end else begin
                    rv[sd][pp] <= 1'b1; r_tag[sd][17*pp +: 17] <= w341[52:36]; r_beat[sd][4*pp +: 4] <= 4'(pq_b[pc]);
                    r_data[sd][256*pp +: 256] <= hbm.exists(key) ? hbm[key] : 256'd0;
                    if (pq_b[pc] + 1 == w341[35:32]) begin
                        pq_b[pc] = 0; pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1; rk[sd][pp] <= 1'b1;
                    end else pq_b[pc] = pq_b[pc] + 1;
                end
            end
        end
    end

    // ---------------- run + checks ----------------
    integer qi = 0, t_pre = -1, n_done = 0;
    integer rt_beats = 0, sc_err = 0, sc_chk = 0, ord_err = 0;
    integer se_rows [0:15], se_err = 0, se_chk = 0, wrows [0:15];
    integer pv_words [0:15], pv_err = 0, pv_chk = 0;
    reg [7:0] pvc [0:15]; reg [63:0] pvf [0:15];
    integer go_cyc = -1, first_rt = -1, last_rt = -1, end_cyc = -1;
    initial for (i = 0; i < 16; i = i + 1) begin se_rows[i] = 0; pv_words[i] = 0; wrows[i] = 0; end
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst <= 1;
        jcmd <= 0;
        if (cyc == 1) build_frames();
        if (cyc == 8) jcmd <= {1'b1, 9'd0, 8'(nframes), 2'b00, 5'b00001, 8'h5a};
        if (jd[0]) begin n_done <= n_done + 1; end_cyc = cyc; end
        // q stream: pre-GO frames back to back with random gaps; GO GODLY cycles after the last; PV after the last score
        q_v <= 0;
        if (rst && cyc > 40 && qi < nq) begin
            if (qi < nq_go) begin
                if (($urandom % 8) != 0) begin q_v <= 1; q_d <= qw[qi]; qi = qi + 1; if (qi == nq_go) t_pre = cyc; end
            end else if (qi == nq_go) begin
                if (cyc >= t_pre + GODLY) begin q_v <= 1; q_d <= qw[qi]; qi = qi + 1; go_cyc = cyc; end
            end else if (rt_beats >= (T + 3) / 4) begin q_v <= 1; q_d <= qw[qi]; qi = qi + 1; end
        end
        // root complete scores
        if (g_s[9].g_r.u.u.rt_v) begin
            reg [2131:0] b; integer r0, rr;
            b = g_s[9].g_r.u.u.rt_d;
            r0 = b[2131:2116];
            if (first_rt < 0) first_rt = cyc; last_rt = cyc;
            if (r0 != 4 * rt_beats) ord_err = ord_err + 1;
            for (rr = 0; rr < 4; rr = rr + 1) if (b[2115 - 3 + rr] && held_row(r0 + rr)) begin
                for (h = 0; h < H; h = h + 1) begin
                    sc_chk = sc_chk + 1;
                    if ((b[64 + (rr*16 + h)*32 +: 32] !== scm[r0 + rr][h*33 +: 32] && !scm[r0 + rr][h*33 + 32]) ||
                        b[rr*16 + h] !== scm[r0 + rr][h*33 + 32]) begin
                        sc_err = sc_err + 1;
                        if (sc_err < 8) $display("SC MISMATCH row %0d head %0d got %08x f%0d exp %08x f%0d", r0 + rr, h,
                            b[64 + (rr*16 + h)*32 +: 32], b[rr*16 + h], scm[r0 + rr][h*33 +: 32], scm[r0 + rr][h*33 + 32]);
                    end
                end
            end
            rt_beats = rt_beats + 1;
        end
        for (s = 0; s < 16; s = s + 1) begin
            // SE rows of the slice's head
            if (se_v[s]) begin
                integer rr, t; t = tile_of(s);
                for (rr = 0; rr < 16; rr = rr + 1) if (16 * se_rows[s] + rr < T && held_row(16 * se_rows[s] + rr)) begin
                    se_chk = se_chk + 1;
                    if (se_d[s][32*rr +: 32] !== scm[16 * se_rows[s] + rr][t*33 +: 32] && !scm[16 * se_rows[s] + rr][t*33 + 32]) begin
                        se_err = se_err + 1;
                        if (se_err < 8) $display("SE MISMATCH slice %0d row %0d got %08x exp %08x", s, 16 * se_rows[s] + rr,
                            se_d[s][32*rr +: 32], scm[16 * se_rows[s] + rr][t*33 +: 32]);
                    end
                end
                se_rows[s] = se_rows[s] + 1;
            end
            if (w_v[s]) wrows[s] = wrows[s] + 1;
            // P.V words
            if (pv_v[s]) begin
                integer wi, t, dm;
                t = tile_of(s); wi = pv_words[s] % 5;
                if (t / 4 != ST) pv_err = pv_err + 1;
                if (wi == 0) begin
                    if (!pv_d[s][512]) pv_err = pv_err + 1;
                    pvc[s] = pv_d[s][71:64]; pvf[s] = pv_d[s][63:0];
                end else begin
                    if (pv_d[s][512]) pv_err = pv_err + 1;
                    dm = 32 * t + 8 * (wi - 1) + pvc[s];
                    for (h = 0; h < H; h = h + 1) begin
                        pv_chk = pv_chk + 1;
                        if ((pv_d[s][32*h +: 32] !== pvm[dm][h*33 +: 32] && !pvm[dm][h*33 + 32]) ||
                            pvf[s][16 * (wi - 1) + h] !== pvm[dm][h*33 + 32]) begin
                            pv_err = pv_err + 1;
                            if (pv_err < 8) $display("PV MISMATCH slice %0d dim %0d head %0d got %08x f%0d exp %08x f%0d", s, dm, h,
                                pv_d[s][32*h +: 32], pvf[s][16 * (wi - 1) + h], pvm[dm][h*33 +: 32], pvm[dm][h*33 + 32]);
                        end
                    end
                end
                pv_words[s] = pv_words[s] + 1;
            end
        end
        if ((end_cyc > 0 && cyc > end_cyc + 300) || cyc >= MAXCYC) begin
            integer bad_se, bad_pv, bad_w, nown; reg [15:0] fl; reg [31:0] fc0;
            bad_se = 0; bad_pv = 0; bad_w = 0; nown = 0; fl = 0; fc0 = 0;
            for (s = 0; s < 16; s = s + 1) begin
                if (se_rows[s] != (T + 15) / 16) bad_se = bad_se + 1;
                if (wrows[s] != se_rows[s]) bad_w = bad_w + 1;
                if (tile_of(s) / 4 == ST) begin nown = nown + 1; if (pv_words[s] != 40) bad_pv = bad_pv + 1; end
                fl[s] = sflt[s]; if (sflt[s] && fc0 == 0) fc0 = afc[s];
            end
            host_check();
            $display("SVCRS_HOST sent=%0d acks=%0d credits=%0d errors=%0d", h_sent, h_ack, h_cred, h_err);
            $display("SVCRS die=%0d st=%0d T=%0d window=%0d nsel=%0d pairs_in=%0d go=%0d first_score=%0d last_score=%0d end=%0d root_beats=%0d sc_checked=%0d sc_errors=%0d order_errors=%0d se_checked=%0d se_errors=%0d se_bad_slices=%0d sm_rows_bad=%0d pv_owner_slices=%0d pv_checked=%0d pv_errors=%0d pv_bad_slices=%0d done=%0d jd_fault=%0d root_fault=%0d slice_faults=%04x first_fault_code=%08x cred_err=%0d cycles=%0d verdict=%s",
                DIE, ST, T, wcount, nsel, npair_in, go_cyc, first_rt, last_rt, end_cyc, rt_beats, sc_chk, sc_err, ord_err,
                se_chk, se_err, bad_se, bad_w, nown, pv_chk, pv_err, bad_pv, n_done, jd[1], rflt, fl, fc0, cred_err, cyc,
                (sc_err == 0 && ord_err == 0 && rt_beats == (T + 3) / 4 && sc_chk > 0 && se_err == 0 && se_chk > 0 &&
                 bad_se == 0 && bad_w == 0 && pv_err == 0 && pv_chk == 4 * 8 * 4 * 16 && bad_pv == 0 && n_done == 1 &&
                 !jd[1] && !rflt && fl == 0 && h_err == 0 && cred_err == 0 && cyc < MAXCYC) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
