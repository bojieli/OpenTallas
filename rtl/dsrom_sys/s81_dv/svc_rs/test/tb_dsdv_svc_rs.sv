`timescale 1ns/1ps
// S81U-SVC 2026-10-17: exact bench of the 16 regional service slices dsdv_svc_rs (2 x 8 grid, sid = 2 col + row,
// abutted faces; S81U-SVC4 p4j: entry slices 5 (W) / 11 (E) = dsdv_svc_rs_entry, the q.k fold at slice 9) against the
// dsfd_svc_c GOLDEN (tools/v41_ckv_sel_attn_vectors.py,
// the vectors tb_dsfd_svc_c runs: window rows qdq_fp8 through OWN_ROW frames -> HBM -> the window load, selected rows
// qdq_fp4_e4m3 owned here from HBM / held elsewhere on ROWS frames, q, p; expected scores sc.hex and p.v pv.hex).
// The bench is the VM + host + 16 regional controllers: it arms the job on both entries' j (frame count, END source 0),
// sends the same q frames into both entries' q pins in the same cycle (CFG, OWN_ROW x wcount, WIN_LOAD, SEL_IDS, ATTN_Q
// x 2, SMJ (SE job + 2 parameter rows), ROWS (shuffled), GO at a compiled cycle carrying the compiled p-feed start PO and
// P.V drain base PVO, then PV at the compiled cycle GO + PVS -- checked to be after the last fold score), host sector
// writes on the hw of the half that owns the PC (8-credit hc contract per entry; the end marker to both), and models
// every slice's 2 PCs (request queue, DQ 8 credits, latency lat + rand, in-order
// beats) on the compiler's dim-sliced image (the owned compressed rows pre-written per slice; the window rows only
// through the slices' own OWN_ROW writes).
// MU-S81/SVC (10-18, multi-user per-user HBM bases; TB only, defaults = the single-user bench unchanged):
//   +u0=<user> (default 3) +sb0=<SB> (default 0x1000): the latency user's id and compressed-row region base.
//   +dir2=<case> +u1=<user> +sb1=<SB>: a SECOND job (user u1, its own vectors, its owned rows pre-written at sb1 in the
//   same HBM image before job 0) runs after job 0 is checked; each job is checked vs its own golden (SVCRS job=<n> line;
//   SVCRS_MU = both). +start2 fixes the second launch (default 8192), never completion-driven.
//   +static_io=1 fixes command issue and external HBM response delay for exact shift comparisons.
//   This is a two-job component isolation gate, not full-shape native token qualification.
//   +trace prints every output event (root beats, SE rows, P.V words, PC requests) with its cycle
//   (SVCRS_TR <job> <cyc> ...): job 0 must be cycle-identical to the single-user run.  Mutants (+mumut=, job 1 only):
//   1 = WIN_LOAD SB = sb0 (user 0's compressed rows), 2 = WIN_LOAD user = u0 (user 0's window ring).
// Checks (PASS = all zero):
//   root   every complete score beat (16 heads x 4 rows) of the HELD rows bit-exact (flags as expected; value
//          unless flagged), beats in row order, exactly ceil(T / 4) beats;
//   SM     every slice's SE operand row (16 rows of its head = tile) equals the golden scores of the held rows;
//          SE rows = ceil(T / 16); the SM head writes one e row per SE row, no SM fault;
//   P.V    at the pv pins of the entry of the half that holds quarter ST (none at the other): 4 windows of 40 words
//          (owner k = tile 4 ST + k: 8 beats x 5 words) back to back, every word bit-exact vs pv.hex (dims 32 t + 8 j + c);
//   job    one jd done per entry, no jd fault, no slice fault (att / sx / stream / SM / return tree), host image + acks
//          + credits,
//          HBM credit discipline (<= 8 per PC).
`ifndef RS_OBS
`define RS_OBS
`endif
// S81U-SVC6: RS_PL = the slices are pre-built Verilator protect-libs (rs_bench_pl.sh; MUT / DIE_ID / ST and the RS_MUT_*
// defines are baked into the libs), so the top build sees only the wrappers -- the --hierarchical top re-elaborated the full
// slice hierarchy in V3Param (> 4 h single-thread at 66 GB, never finished)
`ifdef RS_PL
`define RS_ENT_MOD dsdv_svc_rs_entry_pl
`define RS_SL_MOD dsdv_svc_rs_pl
`define RS_PRM
`else
`define RS_ENT_MOD dsdv_svc_rs_entry
`define RS_SL_MOD dsdv_svc_rs
`define RS_PRM #(.MUT(`MUT), .DIE_ID(DIE), .ST(ST), .SRAM_MACRO(SRAM_MACRO))
`endif
module tb_dsdv_svc_rs;
    parameter bit SRAM_MACRO = 0;
    parameter integer DIE = 0;
    parameter integer ST = 0;
    parameter integer MAXCYC = 400000;
    parameter integer GODLY = 400;
    parameter integer PVS0 = 150;          // compiled PV send: GO + ceil(5 T / 4) + PVS0 (the D = 32 share scores
                                           // 1.25 cycles a row: tb_dsdv_svc_pfeed last score 1.25 T + 40; + tree + gd)
    parameter integer KPV = 55;            // compiled P.V drain base: PO + 8 ceil(T / 32) + KPV (SVC-PV 10-18, PV_CRED 8:
                                           // tb_dsdv_svc_pvdrain, all 8 beats in pvq by p0 + 53 + 8 ceil(T / 32); was
                                           // PO + ceil(T / 4) + 112 for the 4-deep pvq, which faulted 15 / 19)
`ifndef MUT
`define MUT 0
`endif
`include "dsdv_svc_rs_roles.svh"
    localparam integer H = 16, D = 512, NHBM = 32768, WB = 30'h100, SB = 30'h1000, WFIRST = 1000, WUSER = 3;
    integer static_io = 0, start2 = 8192; bit j0_checked = 0;
    integer cur_user = WUSER, u1 = 4, cur_sb = SB, sb1 = SB + 30'h9000, cur_job = 0, mumut = 0, trace = 0;
    integer u0 = WUSER, sb0 = SB; reg [7:0] cur_tag = 8'h5a; reg [1023:0] dir2; bit mu = 0;
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
        if ($value$plusargs("u0=%d", u0)) ; if ($value$plusargs("sb0=%h", sb0)) ;
        if ($value$plusargs("u1=%d", u1)) ; if ($value$plusargs("sb1=%h", sb1)) ;
        if ($value$plusargs("mumut=%d", mumut)) ; if ($value$plusargs("trace=%d", trace)) ;
        mu = $value$plusargs("dir2=%s", dir2);
        if ($value$plusargs("static_io=%d", static_io)) ;
        if ($value$plusargs("tag0=%h", cur_tag)) ;
        if ($value$plusargs("start2=%d", start2)) ;
        if (mu && (u0 == u1 || start2 <= 40 || start2 >= MAXCYC - 40))
            $fatal(1, "MU invalid distinct users or fixed start2");
        $display("SVCRS_CONFIG sram_macro=%0d static_io=%0d start2=%0d", SRAM_MACRO, static_io, start2);
        // MU: the second user's owned rows go into the same HBM image first (no $urandom: job 0 sees the same sequence)
        if (mu) begin load_vec(dir2); preload(sb1); img.delete(); end
        load_vec(dir);
        cur_user = u0; cur_sb = sb0;
        void'($urandom(seed));
        preload(sb0);
    end
    task automatic load_vec(input reg [1023:0] dd);
        $readmemh({dd, "/cfg.hex"}, cfg);
        $readmemh({dd, "/sel.hex"}, selm);
        $readmemh({dd, "/win.hex"}, winm);
        $readmemh({dd, "/hkey.hex"}, hkey);
        $readmemh({dd, "/hdat.hex"}, hdat);
        $readmemh({dd, "/q.hex"}, qm);
        $readmemh({dd, "/p.hex"}, pm);
        $readmemh({dd, "/sc.hex"}, scm);
        $readmemh({dd, "/pv.hex"}, pvm);
        wcount = cfg[0]; nsel = cfg[1]; nh = cfg[3]; T = cfg[4];
        for (i = 0; i < nh; i = i + 1) img[hkey[i]] = hdat[i];
    endtask
    task automatic preload(input integer sbase);
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
                    hbm[(longint'(2 * sd + ((g0 >> 8) & 1)) << 32) | longint'(sbase + 9 * (g0 >> 9) + b)] = blk[256*b +: 256];
            end
        end
    endtask

    // ---------------- 16 slices ----------------
    localparam integer W = 2132, SW = 1076, DW = 805, UW = 16;
    wire [3:0] gi_v [0:15], go_v [0:15], si_v [0:15], so_v [0:15];
    wire [4*W-1:0] gi_d [0:15], go_d [0:15]; wire [4*SW-1:0] si_d [0:15], so_d [0:15];
    wire [4*DW-1:0] dn_i [0:15], dn_o [0:15]; wire [4*UW-1:0] up_i [0:15], up_o [0:15];
    wire [2*341-1:0] rq [0:15]; reg [1:0] rk [0:15], wd [0:15], rv [0:15];
    reg [2*256-1:0] r_data [0:15]; reg [2*17-1:0] r_tag [0:15]; reg [2*4-1:0] r_beat [0:15];
    wire [15:0] pv_v, w_v; wire [512:0] pv_d [0:15]; wire [13:0] w_a [0:15]; wire [15:0] w_m [0:15];
    wire [511:0] w_d [0:15]; wire [11:0] w_st [0:15];
    reg [32:0] jcmd = 0; reg q_v = 0; reg [511:0] q_d = 0;
    wire [1:0] jdx [0:1]; reg [291:0] hwx [0:1]; wire [8:0] hcx [0:1]; wire [1:0] rfx;   // [0] W entry 5, [1] E entry 11
    wire [4*514-1:0] ri [0:15], ro [0:15];
    // RTL-BUILD-S81 10-18: region status st_rg at the two entries; +hsdrop=<sid> holds one slice's controller hs at
    // {fault 0, live 0} from reset (never rose: no hs fault) -> its half must report live 0, the other half live 1
    wire [1:0] stx [0:1]; reg [1:0] hsv [0:15]; integer hsdrop;
    initial begin hsdrop = -1; void'($value$plusargs("hsdrop=%d", hsdrop)); for (int k = 0; k < 16; k++) hsv[k] = (k == hsdrop) ? 2'b00 : 2'b01; end
    wire [2678:0] obs [0:15];
    function automatic bit is_entry(input integer sd); is_entry = sd == RS_ENTRY_W || sd == RS_ENTRY_E; endfunction
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
                assign ri[gs][514*gf +: 514] = ro[NBS][514*OF +: 514];
            end else begin : g_e
                assign gi_v[gs][gf] = 1'b0; assign gi_d[gs][W*gf +: W] = '0;
                assign si_v[gs][gf] = 1'b0; assign si_d[gs][SW*gf +: SW] = '0;
                assign dn_i[gs][DW*gf +: DW] = '0; assign up_i[gs][UW*gf +: UW] = '0;
                assign ri[gs][514*gf +: 514] = '0;
            end
        end
        if (gs == RS_ENTRY_W || gs == RS_ENTRY_E) begin : g_r
            localparam integer HX = (gs == RS_ENTRY_E) ? 1 : 0;
            `RS_ENT_MOD `RS_PRM u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .j(jcmd), .jd(jdx[HX]), .q({1'b0, 1'b1, q_d, q_v}), .hw(hwx[HX]), .hc(hcx[HX]), .fault(rfx[HX]), .st_rg(stx[HX]),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .ri(ri[gs]), .ro(ro[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(hsv[gs]), .pv_v(pv_v[gs]), .pv_d(pv_d[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]), .obs(obs[gs]));
        end else begin : g_n
            `RS_SL_MOD `RS_PRM u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .ri(ri[gs]), .ro(ro[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(hsv[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]), .obs(obs[gs]));
            assign pv_v[gs] = 1'b0; assign pv_d[gs] = '0;
        end
    end endgenerate
    // per-slice local faults and probes (observation ports, RS_OBS: {rt_v, rt_d, se_v, se_d, a_fc, lf})
    wire [15:0] sflt; wire [31:0] afc [0:15];
    wire [15:0] se_v; wire [511:0] se_d [0:15]; wire [15:0] rt_vv; wire [2131:0] rt_dd [0:15];
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_p
        assign sflt[gs] = obs[gs][0]; assign afc[gs] = obs[gs][32:1];
        assign se_d[gs] = obs[gs][544:33]; assign se_v[gs] = obs[gs][545];
        assign rt_dd[gs] = obs[gs][2677:546]; assign rt_vv[gs] = obs[gs][2678];
    end endgenerate

    // ---------------- q frames ----------------
    localparam integer QMAX = 8192;
    reg [511:0] qw [0:QMAX-1];
    integer nq = 0, nq_go = 0, nq_pv = 0, nframes = 0, last_hdr = 0, npair_in = 0;
    integer pvs_c = 0, po_c = 0, pvo_c = 0;          // the compiled PV send, p-feed start and P.V drain base
    integer order [0:4095];
    function automatic [511:0] hdr(input [3:0] typ, input [11:0] len, input [448:0] spec);
        hdr = {typ, 1'b0, 4'b0001, cur_tag, 3'd0, len, 21'd777, 10'(cur_user), spec};
        nframes = nframes + 1; last_hdr = nq;
    endfunction
    task automatic build_frames();
        reg [448:0] sp; integer r, t, n, b, pr, cnt, base, sz; reg [2303:0] row;
        // compiler rule (S81U-SVC4 static P.V): PV leaves the host PVS after GO; a slice's p feed starts once its last
        // step's words have landed on the slowest slice (gd >= 6: words 2k, 2k + 1 by step k), the P.V drain base KPV
        // after the last p step (engine pv beats, tb_dsdv_svc_pfeed)
        n = (T + 1) / 2;
        pvs_c = (5 * T + 3) / 4 + PVS0;
        po_c = pvs_c + (n + 1) / 2 + (n + 249) / 250 + 4;
        pvo_c = po_c + 8 * ((T + 31) / 32) + KPV;
        sp = 0; sp[29:0] = WB;
        qw[nq] = hdr(4'd12, 0, sp); nq = nq + 1;
        for (r = 0; r < wcount; r = r + 1) begin
            qw[nq] = hdr(4'd3, 12'd16, 449'd0); qw[nq][479:459] = WFIRST + r; qw[nq][458:449] = 10'(cur_user); nq = nq + 1;
            for (b = 0; b < 16; b = b + 1) begin
                qw[nq] = 0; qw[nq][255:0] = winm[r][256*b +: 256]; qw[nq][263:256] = winm[r][4096 + 8*b +: 8]; nq = nq + 1;
            end
        end
        sp = 0; sp[29:0] = (cur_job == 1 && mumut == 1) ? 30'(sb0) : 30'(cur_sb); sp[88:81] = wcount; sp[98:89] = nsel; sp[119:99] = WFIRST;
        qw[nq] = hdr(4'd2, 0, sp); qw[nq][458:449] = (cur_job == 1 && mumut == 2) ? 10'(u0) : 10'(cur_user); nq = nq + 1;
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
        sp = 0; sp[15:0] = po_c; sp[31:16] = pvo_c;
        qw[nq] = hdr(4'd13, 0, sp); nq = nq + 1;
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
    integer h_cred [0:1], h_sent = 0, h_ack = 0, h_err = 0, h_mark = 0;   // p4j: one 8-credit hw / hc contract per entry
    initial begin h_cred[0] = 8; h_cred[1] = 8; end
    reg [255:0] h_dat [0:NHW-1]; reg [31:0] h_adr [0:NHW-1];
    integer cyc = 0;
    initial for (i = 0; i < NHW; i = i + 1) begin
        h_adr[i] = (i < NHW / 2) ? 32'h0300_0000 + 32'(i * 5) : 32'h8300_0000 + 32'(i * 7);
        for (k = 0; k < 8; k = k + 1) h_dat[i][32*k +: 32] = 32'h1234_5678 * (i + 1) + k;
    end
    function automatic [4:0] pcmap(input [29:0] a); reg [29:0] x; x = (a >> 2) ^ (a >> 7) ^ (a >> 12); pcmap = x[4:0]; endfunction
    // the host sends a sector write to the entry of the half that owns its PC (slices 0..7 W, 8..15 E); the end marker
    // goes to both entries
    always @(posedge ck) begin
        integer hh;
        hwx[0] <= 0; hwx[1] <= 0;
        for (hh = 0; hh < 2; hh = hh + 1) begin h_cred[hh] = h_cred[hh] + hcx[hh][0]; h_ack = h_ack + hcx[hh][8:1]; end
        if (rst && cyc > 30 && (static_io != 0 ? (cyc % 4 == 0) : (($urandom % 4) == 0))) begin
            if (h_sent < NHW) begin
                hh = (pcmap(h_adr[h_sent][29:0]) >= 5'd16) ? 1 : 0;
                if (h_cred[hh] > 0) begin
                    hwx[hh] <= {(h_adr[h_sent][31] ? 2'd1 : 2'd0), 1'b1, h_adr[h_sent], h_dat[h_sent], 1'b1};
                    h_sent = h_sent + 1; h_cred[hh] = h_cred[hh] - 1;
                end
            end else if (h_mark == 0 && h_cred[0] > 0 && h_cred[1] > 0) begin
                hwx[0] <= {2'd0, 1'b1, 32'hffffffff, 256'h0b007_e2d, 1'b1}; hwx[1] <= {2'd0, 1'b1, 32'hffffffff, 256'h0b007_e2d, 1'b1};
                h_mark = 1; h_cred[0] = h_cred[0] - 1; h_cred[1] = h_cred[1] - 1;
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
        if (h_ack != NHW || h_cred[0] != 8 || h_cred[1] != 8) h_err = h_err + 1;
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
                pq_t[pc][(pq_h[pc] + pq_n[pc]) % PQ] = cyc + lat + (static_io != 0 ? 0 : ($urandom % 16));
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
    integer qi = 0, t_pre = -1, j_cyc = 8, q_cyc = 40, j0_pass = 0;
    integer rt_beats = 0, sc_err = 0, sc_chk = 0, ord_err = 0;
    integer se_rows [0:15], se_err = 0, se_chk = 0, wrows [0:15];
    integer pv_words [0:15], pv_err = 0, pv_chk = 0;
    reg [7:0] pvc [0:15]; reg [63:0] pvf [0:15];
    integer go_cyc = -1, first_rt = -1, last_rt = -1, end_cyc = -1, pv_early = 0, pv_sent = -1;
    integer n_done_x [0:1], pv_first = -1, pv_last = -1, pv_gap = 0, pv_other = 0, pv_n = 0;
    initial for (i = 0; i < 16; i = i + 1) begin se_rows[i] = 0; pv_words[i] = 0; wrows[i] = 0; end
    initial begin n_done_x[0] = 0; n_done_x[1] = 0; end
    localparam integer PVH = (ST >= 2) ? 0 : 1;      // the half whose entry carries quarter ST's P.V (tiles 4 ST .. 4 ST + 3)
    always @(posedge ck) begin
        cyc <= cyc + 1;
`ifdef RS_PROG
        if (cyc % 500 == 0) begin $display("SVCRS_PROG cyc=%0d qi=%0d done=%0d/%0d rt_beats=%0d pv_n=%0d rfx=%0h sflt=%04x jd=%0d%0d", cyc, qi, n_done_x[0], n_done_x[1], rt_beats, pv_n, rfx, sflt, jdx[0][1], jdx[1][1]); $fflush; end
`endif
        if (cyc == 3) rst <= 1;
        jcmd <= 0;
        if (cyc == 1) build_frames();
        if (cyc == j_cyc) jcmd <= {1'b1, 9'd0, 8'(nframes), 2'b00, 5'b00001, cur_tag};
        for (k = 0; k < 2; k = k + 1) if (jdx[k][0]) begin n_done_x[k] = n_done_x[k] + 1; if (cyc > end_cyc) end_cyc = cyc; end
        // q stream: pre-GO frames back to back with random gaps; GO GODLY cycles after the last; PV after the last score
        q_v <= 0;
        if (rst && cyc > q_cyc && qi < nq) begin
            if (qi < nq_go) begin
                if (static_io != 0 || ($urandom % 8) != 0) begin q_v <= 1; q_d <= qw[qi]; qi = qi + 1; if (qi == nq_go) t_pre = cyc; end
            end else if (qi == nq_go) begin
                if (cyc >= t_pre + GODLY) begin q_v <= 1; q_d <= qw[qi]; qi = qi + 1; go_cyc = cyc; end
            end else if (cyc >= go_cyc + pvs_c) begin
                if (qi == nq_pv && rt_beats < (T + 3) / 4) pv_early = 1;      // the compiled PV send precedes a fold score
                if (qi == nq_pv) pv_sent = cyc;
                q_v <= 1; q_d <= qw[qi]; qi = qi + 1;
            end
        end
        // root complete scores
        if (rt_vv[RS_FOLD]) begin
            reg [2131:0] b; integer r0, rr;
            b = rt_dd[RS_FOLD];
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
            // P.V words: only at the entry pins; owner k = tile 4 ST + k in window k (40 words), back to back
            if (pv_v[s]) begin
                integer wi, t, dm;
                if (s != ((PVH == 1) ? RS_ENTRY_E : RS_ENTRY_W)) pv_other = pv_other + 1;
                else begin
                    t = 4 * ST + pv_n / 40; wi = pv_n % 5;
                    if (pv_first < 0) pv_first = cyc; else if (cyc != pv_last + 1) pv_gap = pv_gap + 1;
                    pv_last = cyc;
                    if (pv_n >= 160) pv_err = pv_err + 1;
                    else if (wi == 0) begin
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
                                if (pv_err < 8) $display("PV MISMATCH entry %0d tile %0d dim %0d head %0d got %08x f%0d exp %08x f%0d", s, t, dm, h,
                                    pv_d[s][32*h +: 32], pvf[s][16 * (wi - 1) + h], pvm[dm][h*33 +: 32], pvm[dm][h*33 + 32]);
                            end
                        end
                    end
                    pv_n = pv_n + 1;
                end
            end
        end
        if ((!j0_checked && n_done_x[0] > 0 && n_done_x[1] > 0 && cyc > end_cyc + 300) || cyc >= MAXCYC) begin
            integer bad_se, bad_pv, bad_w, nown, st_bad; reg [15:0] fl; reg [31:0] fc0; bit jpass;
            bad_se = 0; bad_pv = 0; bad_w = 0; nown = 0; fl = 0; fc0 = 0;
            for (s = 0; s < 16; s = s + 1) begin
                if (se_rows[s] != (T + 15) / 16) bad_se = bad_se + 1;
                if (wrows[s] != se_rows[s]) bad_w = bad_w + 1;
                if (tile_of(s) / 4 == ST) nown = nown + 1;
                fl[s] = sflt[s]; if (sflt[s] && fc0 == 0) fc0 = afc[s];
            end
            host_check();
            st_bad = (stx[0] !== {1'b0, !(hsdrop >= 0 && hsdrop < 8)}) + (stx[1] !== {1'b0, !(hsdrop >= 8 && hsdrop < 16)});
            $display("SVCRS_ST hsdrop=%0d st_rg W=%b E=%b bad=%0d", hsdrop, stx[0], stx[1], st_bad);
            bad_pv = (pv_n != 160) + (pv_gap != 0) + (pv_other != 0);
            $display("SVCRS_HOST sent=%0d acks=%0d credits=%0d/%0d errors=%0d", h_sent, h_ack, h_cred[0], h_cred[1], h_err);
            $display("SVCRS_SCHED T=%0d pvs=%0d po=%0d pvo=%0d go=%0d last_fold_score=%0d pv_sent=%0d pv_early=%0d pv_words=%0d pv_first=%0d pv_last=%0d pv_gaps=%0d pv_other_entry=%0d done_W=%0d done_E=%0d",
                T, pvs_c, po_c, pvo_c, go_cyc, last_rt, pv_sent, pv_early, pv_n, pv_first, pv_last, pv_gap, pv_other,
                n_done_x[0], n_done_x[1]);
            $display("SVCRS die=%0d st=%0d T=%0d window=%0d nsel=%0d pairs_in=%0d go=%0d first_score=%0d last_score=%0d end=%0d root_beats=%0d sc_checked=%0d sc_errors=%0d order_errors=%0d se_checked=%0d se_errors=%0d se_bad_slices=%0d sm_rows_bad=%0d pv_owner_slices=%0d pv_checked=%0d pv_errors=%0d pv_bad_slices=%0d done=%0d jd_fault=%0d root_fault=%0d slice_faults=%04x first_fault_code=%08x cred_err=%0d cycles=%0d verdict=%s",
                DIE, ST, T, wcount, nsel, npair_in, go_cyc, first_rt, last_rt, end_cyc, rt_beats, sc_chk, sc_err, ord_err,
                se_chk, se_err, bad_se, bad_w, nown, pv_chk, pv_err, bad_pv, n_done_x[0] + n_done_x[1], jdx[0][1] | jdx[1][1],
                rfx != 0, fl, fc0, cred_err, cyc,
                (sc_err == 0 && ord_err == 0 && rt_beats == (T + 3) / 4 && sc_chk > 0 && se_err == 0 && se_chk > 0 &&
                 bad_se == 0 && bad_w == 0 && pv_err == 0 && pv_chk == 4 * 8 * 4 * 16 && bad_pv == 0 &&
                 n_done_x[0] == 1 && n_done_x[1] == 1 && pv_early == 0 &&
                 !jdx[0][1] && !jdx[1][1] && rfx == 0 && fl == 0 && h_err == 0 && cred_err == 0 && st_bad == 0 && cyc < MAXCYC) ? "PASS" : "FAIL");
            jpass = sc_err == 0 && ord_err == 0 && rt_beats == (T + 3) / 4 && sc_chk > 0 && se_err == 0 && se_chk > 0 &&
                    bad_se == 0 && bad_w == 0 && pv_err == 0 && pv_chk == 4 * 8 * 4 * 16 && bad_pv == 0 &&
                    n_done_x[0] == 1 && n_done_x[1] == 1 && pv_early == 0 &&
                    !jdx[0][1] && !jdx[1][1] && rfx == 0 && fl == 0 && h_err == 0 && cred_err == 0 && st_bad == 0 && cyc < MAXCYC;
            if (mu) $display("SVCRS_JOB job=%0d user=%0d sb=%08x wb=%08x mumut=%0d T=%0d sc_checked=%0d sc_errors=%0d se_errors=%0d pv_checked=%0d pv_errors=%0d slice_faults=%04x verdict=%s",
                cur_job, cur_user, cur_sb, WB, mumut, T, sc_chk, sc_err, se_err, pv_chk, pv_err, fl, jpass ? "PASS" : "FAIL");
            if (mu && cur_job == 0 && cyc < MAXCYC) begin j0_pass = jpass; j0_checked = 1; end
            else begin
                if (mu) $display("SVCRS_MU users=%0d,%0d job0=%s job1=%s verdict=%s", u0, u1, j0_pass ? "PASS" : "FAIL",
                    (cur_job == 1 && jpass) ? "PASS" : "FAIL", (j0_pass && cur_job == 1 && jpass) ? "PASS" : "FAIL");
                $finish;
            end
        end
        // Fixed compiled launch: completion is checked but cannot move this boundary.
        if (mu && cur_job == 0 && cyc == start2) begin
            if (!j0_checked || !j0_pass) $fatal(1, "MU job0 missed fixed boundary");
            for (k = 0; k < 32; k = k + 1)
                if (pq_n[k] != 0 || pq_b[k] != 0) $fatal(1, "MU HBM not drained at fixed boundary");
            next_job();
        end
    end
    // MU-S81/SVC: the second job (user u1, vectors dir2, owned rows at sb1): reload the golden, reset the checkers, re-arm
    task automatic next_job();
        img.delete(); load_vec(dir2);
        j0_checked = 0;
        cur_job = 1; cur_user = u1; cur_sb = sb1; cur_tag = 8'h5b;
        qi = 0; nq = 0; nq_go = 0; nq_pv = 0; nframes = 0; last_hdr = 0; t_pre = -1;
        rt_beats = 0; sc_err = 0; sc_chk = 0; ord_err = 0; se_err = 0; se_chk = 0; pv_err = 0; pv_chk = 0;
        go_cyc = -1; first_rt = -1; last_rt = -1; end_cyc = -1; pv_early = 0; pv_sent = -1;
        n_done_x[0] = 0; n_done_x[1] = 0; pv_first = -1; pv_last = -1; pv_gap = 0; pv_other = 0; pv_n = 0;
        for (i = 0; i < 16; i = i + 1) begin se_rows[i] = 0; pv_words[i] = 0; wrows[i] = 0; end
        build_frames();
        j_cyc = start2 + 8; q_cyc = start2 + 40;
    endtask
    // +trace: every output event with its cycle (job 0 of a MU run must equal the single-user run line for line)
    always @(posedge ck) if (trace != 0) begin
        integer ts, tp;
        if (rt_vv[RS_FOLD]) $display("SVCRS_TR %0d %0d RT %h", cur_job, cyc, rt_dd[RS_FOLD]);
        for (ts = 0; ts < 16; ts = ts + 1) begin
            if (se_v[ts]) $display("SVCRS_TR %0d %0d SE %0d %h", cur_job, cyc, ts, se_d[ts]);
            if (pv_v[ts]) $display("SVCRS_TR %0d %0d PV %0d %h", cur_job, cyc, ts, pv_d[ts]);
            if (w_v[ts]) $display("SVCRS_TR %0d %0d W %0d %h %h %h", cur_job, cyc, ts, w_a[ts], w_m[ts], w_d[ts]);
            for (tp = 0; tp < 2; tp = tp + 1)
                if (rq[ts][341*tp]) $display("SVCRS_TR %0d %0d RQ %0d %h", cur_job, cyc, 2 * ts + tp, rq[ts][341*tp +: 341]);
        end
    end
endmodule
