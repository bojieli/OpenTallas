`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_hc (stream s81-suhc-1011, 2026-10-11): die master of the S81 HC slab.  The dsfd_sp_ctrl engine adapter
// (ot_s81_engine_adapter QD 8, engine port hc = 2) sits at the slab boundary (physical/s81_ctrl/ADAPTER_CONTRACT_1011
// .json): the die nets c_cmd_v / c_cmd_d (85 b) and c_done_v / c_done_tag (9 b) are the controller-clock pulses;
// the engine (ot_s81_hc_core) runs on the slab clock sk.  `inp` is the die dependency net (s81-ctl): the operands of
// the head descriptor are present (VM rows written by their producer); the y operand of a POST is flow-controlled on
// its own bus (y_v / y_rdy).  Every die input lands in a pin flop and every output leaves a flop (VM, y, status);
// the command / done pulses are flopped inside the adapter's CDC FIFOs.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_hc #(
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, LVM = 10, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer OQ = 512, MUT = 0, AMUT = 0,
    parameter integer HIER = 0,                          // 0: flat engine ot_s81_hc_core; 1: hierarchical slab = pin tile
    parameter integer NCOL = 3, GS = 8, S_RT = 4,        //    ot_s81_hc_cpin + combine ot_s81_hc_comb + column roots
                                                         //    ot_s81_hc_croot (chains 0 / 2) + 3 chains of ot_s81_hc_ctile
    parameter integer HALF = 0,                          // HIER structural variant: half-octet sub-tiles (2 an octet)
    parameter integer CSPLIT = 0,                        // HIER structural variant: column roots split N-S (ot_s81_hc_crooty
                                                         //    pins / y FIFO + ot_s81_hc_crootr chain root)
    // 0: existing chain; 1: expose upper seam to die stations + dsfd_sp_hc_t;
    // 2: compose upper/stations/tail for transaction-level exactness (never harden this wrapper).
    parameter integer TAIL_SPLIT = 0, HEAD_ROWS = 10, CNL_PIN = 0, CHAIN_STEP = AL, LANE_SPECIALIZE = 0,
    parameter integer RLY = HALF ? 2 : 1,                // sub-tile relays a hop
    parameter integer PIPE = 1, PIPE_PD = 40,            // HIER: POST issue-order done (ot_s81_hc_cseq PIPE / PD)
    // NORM tree variant (el1014-s81-norm-tree; hier/ot_s81_hc_ntree.sv): 0 = the closed serial-chain slab (default,
    // unchanged); 1 = half-octets ot_s81_hc_cth_nt + the bottom region ot_s81_hc_cnbot (HIER, HALF, TAIL_SPLIT 0 / 2).
    // NT_K: the bottom collectors' fire offset after the vector beat leaves the far tile (cycles).
    parameter integer NTREE = 0, NT_K = 67
) (
    output wire [TFW-1:0] t_tf0, t_tf1, t_tf2,
    input  wire [TRW-1:0] f_tr0, f_tr1, f_tr2,
    input  wire                cck, crs,                 // controller clock / reset (dsfd_sp_ctrl domain)
    input  wire                sk, srs,                  // slab clock / reset
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    input  wire                y_v,
    output wire                y_rdy,
    input  wire [NG*32-1:0]    y_d,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode
);
    // hierarchical slab layout (HIER=1)
    localparam integer TFW = (72+16*S_RD) + ((S_RD*512 > ((NG/GS+NCOL-1)/NCOL)*GS*32) ? S_RD*512 : ((NG/GS+NCOL-1)/NCOL)*GS*32) + S_RD+5+1+128;
    localparam integer TRW = S_RT+4 + S_RT+24*S_RT+8+512*S_RT;
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    localparam integer NL_ = 4 * NS, LT_ = $clog2(NL_);
    // the sum-tree node ownership (as ot_s81_hc_stree): exported subtrees of chains 0 / 2
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT_ - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL_) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL_, c);
    endfunction
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction
`ifndef SYNTHESIS
    initial if (TAIL_SPLIT && (!HIER || !HALF || NCOL != 3 || HEAD_ROWS < 1))
        $fatal(1,"HC tail split requires hierarchical half-octets, three columns and positive head rows");
    initial if (NTREE && (!HIER || !HALF || NCOL != 3 || TAIL_SPLIT == 1))
        $fatal(1,"HC NTREE requires hierarchical half-octets, three columns and TAIL_SPLIT 0 or 2 (the die seam has no lane ports yet)");
`endif
    wire e_v, e_r;
    wire [83:0] e_d;
    generate if (HIER) begin : g_hier
    // hierarchical slab: centre pin tile + combine tile + outer column roots (chains 0 / 2) + 3 column chains
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer RDW = S_RT + 24 * S_RT + 8 + 512 * S_RT;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4, WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    wire        n_cmd_v, n_done_v, n_inp, n_flt, n_online, n_yacc, n_ypop, yacc_w, yacc_e;
    wire [83:0] n_cmd_d;
    wire [7:0]  n_done_tag;
    wire [3:0]  n_fcode;
    wire [S_RD-1:0]     n_rq_v, n_rs_v;
    wire [S_RD*14-1:0]  n_rq_row;
    wire [S_RD*512-1:0] n_rs_d;
    wire [YS1-1:0]      n_y;
    wire [YS1-1:0]      y_s1;
    if (L1 > 0) begin : g_y1
        assign y_s1 = y_d[B1 * GS * 32 +: YS1];
    end else begin : g_ny1
        assign y_s1 = 1'b0;
    end
    ot_s81_hc_cpin #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD)) u_cp (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d), .flt(flt),
        .online(online), .fcode(fcode), .y_v(y_v), .y_rdy(y_rdy), .y_s(y_s1), .yacc_w(yacc_w), .yacc_e(yacc_e),
        .n_cmd_v(n_cmd_v), .n_cmd_d(n_cmd_d), .n_done_v(n_done_v), .n_done_tag(n_done_tag), .n_inp(n_inp),
        .n_rq_v(n_rq_v), .n_rq_row(n_rq_row), .n_rs_v(n_rs_v), .n_rs_d(n_rs_d), .n_flt(n_flt), .n_online(n_online),
        .n_fcode(n_fcode), .n_yacc(n_yacc), .n_y(n_y), .n_ypop(n_ypop));
    wire [FVW-1:0]   w_fv, e_fv;
    wire [FSW-1:0]   w_fd, e_fd;
    wire [4*WSL-1:0] w_w, e_w;
    wire [RVW-1:0]   w_rv, e_rv;
    wire [RDW-1:0]   w_rd, e_rd;
    wire             w_flt, e_flt;
    wire [NCOL-1:0]     ch_rst;
    wire [NCOL*FVW-1:0] ch_fv;
    wire [NCOL*FDW-1:0] ch_fd;
    wire [NCOL*RVW-1:0] ch_rv;
    wire [NCOL*RDW-1:0] ch_rd;
    localparam integer NE0 = (necnt(0) > 0) ? necnt(0) : 1, NE2 = (necnt(2) > 0) ? necnt(2) : 1;
    wire [NE0*32-1:0] w_ex;
    wire [NE2*32-1:0] e_ex;
    ot_s81_hc_comb #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
                     .MUT(MUT), .AMUT(AMUT), .HALF(HALF), .RLY(RLY), .RF(CSPLIT ? 5 : 1),
                     .DW(CSPLIT ? 6 : 5), .RET_EXTRA(CNL_PIN), .PIPE(PIPE), .PIPE_PD(PIPE_PD)) u_cb (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .n_cmd_v(n_cmd_v), .n_cmd_d(n_cmd_d), .n_done_v(n_done_v),
        .n_done_tag(n_done_tag), .n_inp(n_inp), .n_rq_v(n_rq_v), .n_rq_row(n_rq_row), .n_rs_v(n_rs_v), .n_rs_d(n_rs_d),
        .n_flt(n_flt), .n_online(n_online), .n_fcode(n_fcode), .n_yacc(n_yacc), .n_y(n_y), .n_ypop(n_ypop),
        .w_fv(w_fv), .w_fd(w_fd), .w_w(w_w), .w_rv(w_rv), .w_rd(w_rd), .w_ex(w_ex), .w_flt(w_flt),
        .e_fv(e_fv), .e_fd(e_fd), .e_w(e_w), .e_rv(e_rv), .e_rd(e_rd), .e_ex(e_ex), .e_flt(e_flt),
        .ch_rst(ch_rst[1]), .ch_fv(ch_fv[FVW +: FVW]), .ch_fd(ch_fd[FDW +: FDW]), .ch_rv(ch_rv[RVW +: RVW]),
        .ch_rd(ch_rd[RDW +: RDW]));
    genvar c, p;
    if (!CSPLIT) begin : g_r1
    ot_s81_hc_croot #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(0)) u_rw (
        .sk(sk), .srs(srs), .y_s(y_d[B0 * GS * 32 +: L0 * GS * 32]), .wq_v(wq_v[3:0]), .wq_row(wq_row[0 +: 56]),
        .wq_mask(wq_mask[0 +: 64]), .wq_d(wq_d[0 +: 2048]), .yacc(yacc_w), .s_fv(w_fv), .s_fd(w_fd), .s_w(w_w),
        .s_rv(w_rv), .s_rd(w_rd), .s_ex(w_ex), .s_flt(w_flt), .ch_rst(ch_rst[0]), .ch_fv(ch_fv[0 +: FVW]),
        .ch_fd(ch_fd[0 +: FDW]), .ch_rv(ch_rv[0 +: RVW]), .ch_rd(ch_rd[0 +: RDW]));
    ot_s81_hc_croot #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(2)) u_re (
        .sk(sk), .srs(srs), .y_s(y_d[B2 * GS * 32 +: L2 * GS * 32]), .wq_v(wq_v[7:4]), .wq_row(wq_row[56 +: 56]),
        .wq_mask(wq_mask[64 +: 64]), .wq_d(wq_d[2048 +: 2048]), .yacc(yacc_e), .s_fv(e_fv), .s_fd(e_fd), .s_w(e_w),
        .s_rv(e_rv), .s_rd(e_rd), .s_ex(e_ex), .s_flt(e_flt), .ch_rst(ch_rst[2]), .ch_fv(ch_fv[2 * FVW +: FVW]),
        .ch_fd(ch_fd[2 * FDW +: FDW]), .ch_rv(ch_rv[2 * RVW +: RVW]), .ch_rd(ch_rd[2 * RDW +: RDW]));
    end else begin : g_r2
    begin : g_s0
        localparam integer CC = 0;
        localparam integer LCC = (CC == 0) ? L0 : L2;
        localparam integer BCC = (CC == 0) ? B0 : B2;
        wire [LCC-1:0]   p_req;
        wire             p_flt;
        wire [LCC*GS*32-1:0] p_y;
        wire [4*WSL-1:0] p_w;
        ot_s81_hc_crooty #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .C(CC)) u_y (
            .sk(sk), .srs(srs), .y_s(y_d[BCC * GS * 32 +: LCC * GS * 32]), .wq_v(wq_v[0 +: 4]),
            .wq_row(wq_row[0 +: 56]), .wq_mask(wq_mask[0 +: 64]), .wq_d(wq_d[0 +: 2048]),
            .yacc(yacc_w), .p_req(p_req), .p_w(p_w), .p_y(p_y), .p_flt(p_flt));
        ot_s81_hc_crootr #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(CC)) u_r (
            .sk(sk), .srs(srs), .p_req(p_req), .p_y(p_y), .p_w(p_w), .p_flt(p_flt),
            .s_fv(w_fv), .s_fd(w_fd), .s_w(w_w),
            .s_rv(w_rv), .s_rd(w_rd), .s_ex(w_ex),
            .s_flt(w_flt), .ch_rst(ch_rst[CC]), .ch_fv(ch_fv[CC * FVW +: FVW]),
            .ch_fd(ch_fd[CC * FDW +: FDW]), .ch_rv(ch_rv[CC * RVW +: RVW]), .ch_rd(ch_rd[CC * RDW +: RDW]));
    end
    begin : g_s1
        localparam integer CC = 2;
        localparam integer LCC = (CC == 0) ? L0 : L2;
        localparam integer BCC = (CC == 0) ? B0 : B2;
        wire [LCC-1:0]   p_req;
        wire             p_flt;
        wire [LCC*GS*32-1:0] p_y;
        wire [4*WSL-1:0] p_w;
        ot_s81_hc_crooty #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .C(CC)) u_y (
            .sk(sk), .srs(srs), .y_s(y_d[BCC * GS * 32 +: LCC * GS * 32]), .wq_v(wq_v[4 +: 4]),
            .wq_row(wq_row[56 +: 56]), .wq_mask(wq_mask[64 +: 64]), .wq_d(wq_d[2048 +: 2048]),
            .yacc(yacc_e), .p_req(p_req), .p_w(p_w), .p_y(p_y), .p_flt(p_flt));
        ot_s81_hc_crootr #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(CC)) u_r (
            .sk(sk), .srs(srs), .p_req(p_req), .p_y(p_y), .p_w(p_w), .p_flt(p_flt),
            .s_fv(e_fv), .s_fd(e_fd), .s_w(e_w),
            .s_rv(e_rv), .s_rd(e_rd), .s_ex(e_ex),
            .s_flt(e_flt), .ch_rst(ch_rst[CC]), .ch_fv(ch_fv[CC * FVW +: FVW]),
            .ch_fd(ch_fd[CC * FDW +: FDW]), .ch_rv(ch_rv[CC * RVW +: RVW]), .ch_rd(ch_rd[CC * RDW +: RDW]));
    end
    end
    localparam integer NTW = 2 * 137 + 1, O_NVX = 5 + S_RD * 16 + 20 + 6;
    if (TAIL_SPLIT == 0) begin : g_unsplit
    assign {t_tf2,t_tf1,t_tf0} = 0;
    wire [3*FVW-1:0]   nt_fv;
    wire [3*8-1:0]     nt_nv;
    wire [O_D-1:0]     nt_fc0;
    wire [S_RD*32-1:0] nt_eps0;
    wire [3*NTW-1:0]   nt_dl;
    wire [3*33-1:0]    nt_ul;
    wire               nt_flt;
    for (c = 0; c < NCOL; c = c + 1) begin : g_c
        localparam integer LC = ((c == 0) ? L0 : (c == 1) ? L1 : L2) * (HALF ? 2 : 1);   // sub-tiles of the chain
        localparam integer BC = ((c == 0) ? B0 : (c == 1) ? B1 : B2) * (HALF ? 2 : 1);
        if (LC > 0) begin : g_live
            wire [FVW-1:0] fvo [0:LC-1];
            wire [FDW-1:0] fdo [0:LC-1];
            wire [RVW-1:0] rvo [0:LC-1];
            wire [RDW-1:0] rdo [0:LC-1];
            wire           rso [0:LC-1];
            wire [127:0]   cyo [0:LC-1];
            wire [NTW-1:0] dlo [0:LC-1];
            wire [32:0]    ulo [0:LC-1];
            if (NTREE) begin : g_ntend
                assign nt_fv[c * FVW +: FVW] = fvo[LC - 1];
                assign nt_nv[c * 8 +: 8] = fdo[LC - 1][O_NVX +: 8];
                assign nt_dl[c * NTW +: NTW] = dlo[LC - 1];
                if (c == 0) begin : g_c0
                    assign nt_fc0 = fdo[LC - 1][O_D - 1:0];
                    for (genvar s_ = 0; s_ < S_RD; s_ = s_ + 1) begin : g_e
                        assign nt_eps0[32 * s_ +: 32] = fdo[LC - 1][O_D + 512 * s_ + 256 +: 32];
                    end
                end
            end
            for (p = 0; p < LC; p = p + 1) begin : g_p
                localparam [7:0] TID = BC + p;
                if (HALF && NTREE) begin : g_hn   // NORM tree variant (ot_s81_hc_ntree.sv)
                ot_s81_hc_cth_nt #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                .ML(ML), .AL(AL), .RLY(RLY), .CNL_PIN(CNL_PIN), .CHAIN_STEP(CHAIN_STEP), .LANE_SPECIALIZE(LANE_SPECIALIZE)) u_t (
                    .clk(sk), .rst_in(p == 0 ? ch_rst[c] : rso[p > 0 ? p - 1 : 0]), .rst_out(rso[p]), .tid(TID),
                    .last(p == LC - 1),
                    .fv_in(p == 0 ? ch_fv[c * FVW +: FVW] : fvo[p > 0 ? p - 1 : 0]),
                    .fd_in(p == 0 ? ch_fd[c * FDW +: FDW] : fdo[p > 0 ? p - 1 : 0]),
                    .fv_out(fvo[p]), .fd_out(fdo[p]),
                    .rv_in(p == LC - 1 ? ((c == 0) ? {nt_flt, {(S_RT + 2){1'b0}}} : {RVW{1'b0}}) : rvo[p < LC - 1 ? p + 1 : 0]),
                    .rd_in(p == LC - 1 ? {RDW{1'b0}} : rdo[p < LC - 1 ? p + 1 : 0]),
                    .rv_out(rvo[p]), .rd_out(rdo[p]),
                    .cy_out(cyo[p]), .cy_in(p == 0 ? 128'd0 : cyo[p > 0 ? p - 1 : 0]),
                    .dl_in(p == 0 ? {NTW{1'b0}} : dlo[p > 0 ? p - 1 : 0]), .dl_out(dlo[p]),
                    .ul_in(p == LC - 1 ? nt_ul[c * 33 +: 33] : ulo[p < LC - 1 ? p + 1 : 0]), .ul_out(ulo[p]));
                end else if (HALF) begin : g_h   // el1011-s81hc-ctile: HALF sub-tile split into <=15k-sink hard tiles
                ot_s81_hc_cth #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                .ML(ML), .AL(AL), .RLY(RLY), .CNL_PIN(CNL_PIN), .CHAIN_STEP(CHAIN_STEP), .LANE_SPECIALIZE(LANE_SPECIALIZE)) u_t (
                    .clk(sk), .rst_in(p == 0 ? ch_rst[c] : rso[p > 0 ? p - 1 : 0]), .rst_out(rso[p]), .tid(TID),
                    .last(p == LC - 1),
                    .fv_in(p == 0 ? ch_fv[c * FVW +: FVW] : fvo[p > 0 ? p - 1 : 0]),
                    .fd_in(p == 0 ? ch_fd[c * FDW +: FDW] : fdo[p > 0 ? p - 1 : 0]),
                    .fv_out(fvo[p]), .fd_out(fdo[p]),
                    .rv_in(p == LC - 1 ? {RVW{1'b0}} : rvo[p < LC - 1 ? p + 1 : 0]),
                    .rd_in(p == LC - 1 ? {RDW{1'b0}} : rdo[p < LC - 1 ? p + 1 : 0]),
                    .rv_out(rvo[p]), .rd_out(rdo[p]),
                    .cy_out(cyo[p]), .cy_in(p == 0 ? 128'd0 : cyo[p > 0 ? p - 1 : 0]));
                end else begin : g_f
                ot_s81_hc_ctile #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                  .ML(ML), .AL(AL), .HALF(HALF), .RLY(RLY)) u_t (
                    .clk(sk), .rst_in(p == 0 ? ch_rst[c] : rso[p > 0 ? p - 1 : 0]), .rst_out(rso[p]), .tid(TID),
                    .last(p == LC - 1),
                    .fv_in(p == 0 ? ch_fv[c * FVW +: FVW] : fvo[p > 0 ? p - 1 : 0]),
                    .fd_in(p == 0 ? ch_fd[c * FDW +: FDW] : fdo[p > 0 ? p - 1 : 0]),
                    .fv_out(fvo[p]), .fd_out(fdo[p]),
                    .rv_in(p == LC - 1 ? {RVW{1'b0}} : rvo[p < LC - 1 ? p + 1 : 0]),
                    .rd_in(p == LC - 1 ? {RDW{1'b0}} : rdo[p < LC - 1 ? p + 1 : 0]),
                    .rv_out(rvo[p]), .rd_out(rdo[p]),
                    .cy_out(cyo[p]), .cy_in(p == 0 ? 128'd0 : cyo[p > 0 ? p - 1 : 0]));
                end
            end
            assign ch_rv[c * RVW +: RVW] = rvo[0];
            assign ch_rd[c * RDW +: RDW] = rdo[0];
        end else begin : g_none
            assign ch_rv[c * RVW +: RVW] = 0;
            assign ch_rd[c * RDW +: RDW] = 0;
        end
    end
    if (NTREE) begin : g_ntb
        ot_s81_hc_cnbot #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .NT_K(NT_K)) u_bot (
            .sk(sk), .srs(srs), .f_fv(nt_fv), .f_nv(nt_nv), .f_fc0(nt_fc0), .f_eps0(nt_eps0), .dl(nt_dl), .ul(nt_ul),
            .flt(nt_flt));
    end
    end else begin : g_split
        wire [3*NTW-1:0] hdl;                            // NORM tree lanes at the seam (NTREE only)
        wire [3*33-1:0]  hul;
        wire [NCOL*TFW-1:0] sf;
        wire [NCOL*TRW-1:0] sr;
        assign {t_tf2,t_tf1,t_tf0} = sf;
        if (TAIL_SPLIT == 1) begin : g_external
            assign sr = {f_tr2,f_tr1,f_tr0};
            assign hul = 0;
        end else begin : g_composed
            wire [NCOL*TFW-1:0] tf;
            wire [NCOL*TRW-1:0] tr;
            wire [3*NTW-1:0] tdl;
            wire [3*33-1:0]  tul;
            dsfd_sp_hc_t_nt #(.NG(NG),.D(D),.S_RD(S_RD),.S_RT(S_RT),.WIN(WIN),.WOUT(WOUT),.ML(ML),.AL(AL),
                          .NCOL(NCOL),.GS(GS),.RLY(RLY),.HEAD_ROWS(HEAD_ROWS),.CNL_PIN(CNL_PIN),.CHAIN_STEP(CHAIN_STEP), .LANE_SPECIALIZE(LANE_SPECIALIZE),
                          .NTREE(NTREE),.NT_K(NT_K)) u_tail (
                .ck(sk),.f_sf0(tf[0+:TFW]),.f_sf1(tf[TFW+:TFW]),.f_sf2(tf[2*TFW+:TFW]),
                .t_sr0(tr[0+:TRW]),.t_sr1(tr[TRW+:TRW]),.t_sr2(tr[2*TRW+:TRW]),
                .srs(srs),.f_dl(tdl),.t_ul(tul));
            // Models the die's existing seven common-clock stations; reset is an in-band forward bit.
            ot_hdc_delay #(.W(NCOL*TFW),.D(7),.RESET(0)) u_fwd (.clk(sk),.rst_n(srs),.d(sf),.q(tf));
            ot_hdc_delay #(.W(NCOL*TRW),.D(7),.RESET(0)) u_ret (.clk(sk),.rst_n(srs),.d(tr),.q(sr));
            if (NTREE) begin : g_ntst
                // the NORM tree lanes take the same seven stations (registered, reset: they carry valids)
                ot_hdc_delay #(.W(3*NTW),.D(7),.RESET(1)) u_dl (.clk(sk),.rst_n(srs),.d(hdl),.q(tdl));
                ot_hdc_delay #(.W(3*33),.D(7),.RESET(1)) u_ul (.clk(sk),.rst_n(srs),.d(tul),.q(hul));
            end else begin : g_nnt
                assign tdl = 0; assign hul = 0;
            end
        end
        for (c=0;c<NCOL;c=c+1) begin : g_c
            localparam integer LC=((c==0)?L0:(c==1)?L1:L2)*2;
            localparam integer BC=((c==0)?B0:(c==1)?B1:B2)*2;
            localparam integer NH=(LC<HEAD_ROWS)?LC:HEAD_ROWS;
            wire [127:0] cy;
            ot_s81_hc_chain_segment #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
                .WIN(WIN),.WOUT(WOUT),.ML(ML),.AL(AL),.RLY(RLY),.CNL_PIN(CNL_PIN),.CHAIN_STEP(CHAIN_STEP),.LANE_SPECIALIZE(LANE_SPECIALIZE),.BC(BC),.LC(LC),.START(0),.COUNT(NH),.NTREE(NTREE)) u_head (
                .sk(sk),.rst_in(ch_rst[c]),.fv_in(ch_fv[c*FVW+:FVW]),.fd_in(ch_fd[c*FDW+:FDW]),.cy_in(128'd0),
                .rv_in(sr[c*TRW+RDW+:RVW]),.rd_in(sr[c*TRW+:RDW]),
                .rst_out(sf[c*TFW+128+FDW+FVW]),.fv_out(sf[c*TFW+128+FDW+:FVW]),
                .fd_out(sf[c*TFW+128+:FDW]),.cy_out(sf[c*TFW+:128]),
                .rv_out(ch_rv[c*RVW+:RVW]),.rd_out(ch_rd[c*RDW+:RDW]),
                .dl_in({NTW{1'b0}}),.dl_out(hdl[c*NTW+:NTW]),.ul_in(hul[c*33+:33]),.ul_out());
        end
    end
`ifndef SYNTHESIS
    // bench observability (tb job start cycles)
    assign e_v = u_cb.e_v; assign e_r = u_cb.e_r; assign e_d = u_cb.e_d;
`endif
    end else begin : g_flat
    assign {t_tf2,t_tf1,t_tf0}=0;
    wire d_v, a_flt, c_flt;
    wire [7:0]  d_t;
    reg inp_q;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    wire [31:0] jobs;
    wire        bsy;
    // pin flops: VM responses (fixed latency + 1, the core counts responses), y through a registered-ready skid
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    always @(posedge sk) rs_d_q <= rs_d;
    always @(posedge sk or negedge srs) if (!srs) rs_v_q <= 0; else rs_v_q <= rs_v;
    wire yq_v, yq_r, y_ov, y_un;
    wire [NG*32-1:0] yq_d;
    ot_skid_buffer #(.WIDTH(NG*32), .DEPTH(2)) u_ysk (.clk(sk), .rst_n(srs), .in_valid(y_v), .in_ready(y_rdy),
        .in_data(y_d), .out_valid(yq_v), .out_ready(yq_r), .out_data(yq_d), .overflow(y_ov), .underflow(y_un));
    ot_s81_hc_core #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .LVM(LVM), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL),
                     .OQ(OQ), .MUT(MUT)) u_core (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .y_v(yq_v), .y_rdy(yq_r), .y_d(yq_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs));
    assign flt = a_flt | c_flt | y_ov | y_un;
    end endgenerate
endmodule

// Wire-only chain assembly; each cth instance retains its existing hardened local roots.
module ot_s81_hc_chain_segment #(
    parameter integer NG=256,D=5120,NCOL=3,GS=8,S_RD=2,S_RT=4,WIN=2,WOUT=2,ML=5,AL=4,RLY=2,
    parameter integer BC=0,LC=22,START=0,COUNT=10,CNL_PIN=0,CHAIN_STEP=AL,LANE_SPECIALIZE=0,NTREE=0,
    parameter integer FVW=S_RD+5, RVW=S_RT+4, NTW=2*137+1,
    parameter integer FDW=(72+16*S_RD)+((S_RD*512>((NG/GS+NCOL-1)/NCOL)*GS*32)?S_RD*512:((NG/GS+NCOL-1)/NCOL)*GS*32),
    parameter integer RDW=S_RT+24*S_RT+8+512*S_RT
)( input wire sk,rst_in, input wire [FVW-1:0] fv_in,input wire [FDW-1:0] fd_in,
   input wire [127:0] cy_in,input wire [RVW-1:0] rv_in,input wire [RDW-1:0] rd_in,
   output wire rst_out,output wire [FVW-1:0] fv_out,output wire [FDW-1:0] fd_out,
   output wire [127:0] cy_out,output wire [RVW-1:0] rv_out,output wire [RDW-1:0] rd_out,
   // NORM tree lanes (NTREE only): partial lane in at the N end / out at the S end, scale lane in S / out N
   input wire [NTW-1:0] dl_in,output wire [NTW-1:0] dl_out,input wire [32:0] ul_in,output wire [32:0] ul_out);
    genvar p;
    generate if(COUNT>0) begin : g_live
            wire [FVW-1:0] fvo [0:COUNT-1];
            wire [FDW-1:0] fdo [0:COUNT-1];
            wire [RVW-1:0] rvo [0:COUNT-1];
            wire [RDW-1:0] rdo [0:COUNT-1];
            wire           rso [0:COUNT-1];
            wire [127:0]   cyo [0:COUNT-1];
            wire [NTW-1:0] dlo [0:COUNT-1];
            wire [32:0]    ulo [0:COUNT-1];
            for (p = 0; p < COUNT; p = p + 1) begin : g_p
                localparam [7:0] TID = BC + START + p;
                if (NTREE) begin : g_hn   // NORM tree variant (ot_s81_hc_ntree.sv)
                ot_s81_hc_cth_nt #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                .ML(ML), .AL(AL), .RLY(RLY), .CNL_PIN(CNL_PIN), .CHAIN_STEP(CHAIN_STEP), .LANE_SPECIALIZE(LANE_SPECIALIZE)) u_t (
                    .clk(sk), .rst_in(p == 0 ? rst_in : rso[p > 0 ? p - 1 : 0]), .rst_out(rso[p]), .tid(TID),
                    .last(START + p == LC - 1),
                    .fv_in(p == 0 ? fv_in : fvo[p > 0 ? p - 1 : 0]),
                    .fd_in(p == 0 ? fd_in : fdo[p > 0 ? p - 1 : 0]),
                    .fv_out(fvo[p]), .fd_out(fdo[p]),
                    .rv_in(p == COUNT - 1 ? rv_in : rvo[p < COUNT-1 ? p+1 : 0]),
                    .rd_in(p == COUNT - 1 ? rd_in : rdo[p < COUNT-1 ? p+1 : 0]),
                    .rv_out(rvo[p]), .rd_out(rdo[p]),
                    .cy_out(cyo[p]), .cy_in(p == 0 ? cy_in : cyo[p > 0 ? p - 1 : 0]),
                    .dl_in(p == 0 ? dl_in : dlo[p > 0 ? p - 1 : 0]), .dl_out(dlo[p]),
                    .ul_in(p == COUNT - 1 ? ul_in : ulo[p < COUNT-1 ? p+1 : 0]), .ul_out(ulo[p]));
                end else begin : g_h   // el1011-s81hc-ctile: HALF sub-tile split into <=15k-sink hard tiles
                ot_s81_hc_cth #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                .ML(ML), .AL(AL), .RLY(RLY), .CNL_PIN(CNL_PIN), .CHAIN_STEP(CHAIN_STEP), .LANE_SPECIALIZE(LANE_SPECIALIZE)) u_t (
                    .clk(sk), .rst_in(p == 0 ? rst_in : rso[p > 0 ? p - 1 : 0]), .rst_out(rso[p]), .tid(TID),
                    .last(START + p == LC - 1),
                    .fv_in(p == 0 ? fv_in : fvo[p > 0 ? p - 1 : 0]),
                    .fd_in(p == 0 ? fd_in : fdo[p > 0 ? p - 1 : 0]),
                    .fv_out(fvo[p]), .fd_out(fdo[p]),
                    .rv_in(p == COUNT - 1 ? rv_in : rvo[p < COUNT-1 ? p+1 : 0]),
                    .rd_in(p == COUNT - 1 ? rd_in : rdo[p < COUNT-1 ? p+1 : 0]),
                    .rv_out(rvo[p]), .rd_out(rdo[p]),
                    .cy_out(cyo[p]), .cy_in(p == 0 ? cy_in : cyo[p > 0 ? p - 1 : 0]));
                end
            end
            assign rv_out=rvo[0]; assign rd_out=rdo[0];
                assign rst_out=rso[COUNT-1];
            assign fv_out=fvo[COUNT-1]; assign fd_out=fdo[COUNT-1]; assign cy_out=cyo[COUNT-1];
            if (NTREE) begin : g_nl
                assign dl_out=dlo[COUNT-1]; assign ul_out=ulo[0];
            end else begin : g_nnl
                assign dl_out=0; assign ul_out=0;
            end
    end else begin : g_empty
        assign {rst_out,fv_out,fd_out,cy_out}={rst_in,fv_in,fd_in,cy_in};
        assign rv_out=rv_in; assign rd_out=rd_in;
        assign dl_out=dl_in; assign ul_out=ul_in;
    end endgenerate
endmodule

// dsfd_sp_hc_t (S-BIND 2026-10-15): the die name of the HC chain tails across the TAIL_SPLIT 1 seam (hc_s t_tf / f_tr).
// The NORM-tree lanes and bottom reset exist only in the composed TAIL_SPLIT 2 form (dsfd_sp_hc_t_nt): dsfd_sp_hc rejects
// NTREE with TAIL_SPLIT 1 (no lane ports at the die seam), so the die tail has none -- they were unconnected die inputs
// (port-bind INPUT_UNCONNECTED f_dl / srs).  With NTREE 0 the core never reads its lane inputs (chain segments g_h,
// bottom absent); a die NORM tree needs seam lane ports on dsfd_sp_hc_c first (S-NORM swap proposal).
module dsfd_sp_hc_t #(
    parameter integer NG=256,D=5120,S_RD=2,S_RT=4,WIN=2,WOUT=2,ML=5,AL=4,NCOL=3,GS=8,RLY=2,HEAD_ROWS=10,CNL_PIN=0,CHAIN_STEP=AL,LANE_SPECIALIZE=0,
    parameter integer NTREE=0,NT_K=67,
    parameter integer FDW=(72+16*S_RD)+((S_RD*512>((NG/GS+NCOL-1)/NCOL)*GS*32)?S_RD*512:((NG/GS+NCOL-1)/NCOL)*GS*32),
    parameter integer FVW=S_RD+5,RVW=S_RT+4,RDW=S_RT+24*S_RT+8+512*S_RT,TFW=FDW+FVW+129,TRW=RDW+RVW,NTW=2*137+1
 )(input wire ck,input wire [TFW-1:0] f_sf0,f_sf1,f_sf2,output wire [TRW-1:0] t_sr0,t_sr1,t_sr2);
    initial if (NTREE) $fatal(1,"dsfd_sp_hc_t: the die seam has no NORM-tree lane ports (use the composed TAIL_SPLIT 2 form)");
    wire [3*33-1:0] ul_nc;
    dsfd_sp_hc_t_nt #(.NG(NG),.D(D),.S_RD(S_RD),.S_RT(S_RT),.WIN(WIN),.WOUT(WOUT),.ML(ML),.AL(AL),.NCOL(NCOL),.GS(GS),.RLY(RLY),
        .HEAD_ROWS(HEAD_ROWS),.CNL_PIN(CNL_PIN),.CHAIN_STEP(CHAIN_STEP),.LANE_SPECIALIZE(LANE_SPECIALIZE),.NTREE(0),.NT_K(NT_K)) u_t (
        .ck(ck),.f_sf0(f_sf0),.f_sf1(f_sf1),.f_sf2(f_sf2),.t_sr0(t_sr0),.t_sr1(t_sr1),.t_sr2(t_sr2),
        .srs(1'b1),.f_dl({3*NTW{1'b0}}),.t_ul(ul_nc));
endmodule

module dsfd_sp_hc_t_nt #(
    parameter integer NG=256,D=5120,S_RD=2,S_RT=4,WIN=2,WOUT=2,ML=5,AL=4,NCOL=3,GS=8,RLY=2,HEAD_ROWS=10,CNL_PIN=0,CHAIN_STEP=AL,LANE_SPECIALIZE=0,
    parameter integer NTREE=0,NT_K=67,
    parameter integer FDW=(72+16*S_RD)+((S_RD*512>((NG/GS+NCOL-1)/NCOL)*GS*32)?S_RD*512:((NG/GS+NCOL-1)/NCOL)*GS*32),
    parameter integer FVW=S_RD+5,RVW=S_RT+4,RDW=S_RT+24*S_RT+8+512*S_RT,TFW=FDW+FVW+129,TRW=RDW+RVW,NTW=2*137+1
 )(input wire ck,input wire [TFW-1:0] f_sf0,f_sf1,f_sf2,output wire [TRW-1:0] t_sr0,t_sr1,t_sr2,
   // NORM tree (NTREE only): bottom reset, the partial lanes from the head segments, the scale lanes to them
   input wire srs,input wire [3*NTW-1:0] f_dl,output wire [3*33-1:0] t_ul);
    localparam integer NS=NG/GS,NP=(NS+NCOL-1)/NCOL,L1=(NS-2*NP>0)?NS-2*NP:0;
    wire [NCOL*TFW-1:0] sf={f_sf2,f_sf1,f_sf0};
    wire [NCOL*TRW-1:0] sr;
    assign {t_sr2,t_sr1,t_sr0}=sr;
    localparam integer O_D=5+S_RD*16+20+6+8+32+1, O_NVX=5+S_RD*16+20+6;
    wire [3*FVW-1:0]   nt_fv;
    wire [3*8-1:0]     nt_nv;
    wire [3*NTW-1:0]   nt_dl;
    wire [3*33-1:0]    nt_ul;
    wire [O_D-1:0]     nt_fc0;
    wire [S_RD*32-1:0] nt_eps0;
    wire               nt_flt;
    genvar c;
    generate for(c=0;c<NCOL;c=c+1) begin:g_c
        localparam integer LC=((c==1)?L1:NP)*2,BC=((c==0)?0:(c==1)?NP:NP+L1)*2;
        localparam integer NH=(LC<HEAD_ROWS)?LC:HEAD_ROWS;
        wire [FVW-1:0] fvf;
        wire [FDW-1:0] fdf;
        ot_s81_hc_chain_segment #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
            .WIN(WIN),.WOUT(WOUT),.ML(ML),.AL(AL),.RLY(RLY),.CNL_PIN(CNL_PIN),.CHAIN_STEP(CHAIN_STEP),.LANE_SPECIALIZE(LANE_SPECIALIZE),.BC(BC),.LC(LC),.START(NH),.COUNT(LC-NH),.NTREE(NTREE)) u_tail (
            .sk(ck),.rst_in(sf[c*TFW+128+FDW+FVW]),.fv_in(sf[c*TFW+128+FDW+:FVW]),
            .fd_in(sf[c*TFW+128+:FDW]),.cy_in(sf[c*TFW+:128]),
            .rv_in((NTREE && c==0) ? {nt_flt,{(S_RT+2){1'b0}}} : {RVW{1'b0}}),.rd_in({RDW{1'b0}}),
            .rst_out(),.fv_out(fvf),.fd_out(fdf),.cy_out(),.rv_out(sr[c*TRW+RDW+:RVW]),.rd_out(sr[c*TRW+:RDW]),
            .dl_in(f_dl[c*NTW+:NTW]),.dl_out(nt_dl[c*NTW+:NTW]),.ul_in(nt_ul[c*33+:33]),.ul_out(t_ul[c*33+:33]));
        assign nt_fv[c*FVW+:FVW]=fvf; assign nt_nv[c*8+:8]=fdf[O_NVX+:8];
        if (c==0) begin : g_c0
            assign nt_fc0=fdf[O_D-1:0];
            for (genvar s_=0;s_<S_RD;s_=s_+1) begin : g_e
                assign nt_eps0[32*s_+:32]=fdf[O_D+512*s_+256+:32];
            end
        end
    end
    if (NTREE) begin : g_nt
        ot_s81_hc_cnbot #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),.ML(ML),.AL(AL),.NT_K(NT_K)) u_bot (
            .sk(ck),.srs(srs),.f_fv(nt_fv),.f_nv(nt_nv),.f_fc0(nt_fc0),.f_eps0(nt_eps0),.dl(nt_dl),.ul(nt_ul),.flt(nt_flt));
    end else begin : g_nnt
        assign nt_ul=0; assign nt_flt=1'b0;
    end endgenerate
endmodule
