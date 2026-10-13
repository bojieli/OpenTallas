`define OT_SMH_CG
`define OT_SMH_FC_HIER
`define SYNTHESIS
module ot_hbm_accel_smh #(
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer TCK  = 1,
    parameter integer PIO  = 2,
    parameter integer HAZ  = 1,
    parameter integer NOUT = 4,
    parameter integer RPT  = 2,         // leaves (rows) per hardened tile
    parameter integer ENABLE_INT8 = 0,
    parameter integer PIPE_INT8 = 0, // opt-in second elastic conversion stage
    parameter integer REQCR = 1         // 1 (production): request port with ready latency 2 (req_ready captured raw;
                                        // see front_s); 0: the m3b same-cycle port (bench comparison only)
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    output wire                    start_ready,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    input  wire [$clog2(XD)-1:0]   op_xb,
    output wire                    busy,
    input  wire                    d_valid,
    output wire                    d_ready,
    input  wire [31:0]             d_base,
    input  wire [23:0]             d_lines,
    output wire                    req_v,
    input  wire                    req_ready,
    output wire [31:0]             req_addr,
    output wire [9:0]              req_tag,
    input  wire                    rsp_v,
    input  wire [9:0]              rsp_tag,
    input  wire [1087:0]           rsp_data,
    input  wire                    xw_en,
    input  wire [$clog2(XD)-1:0]   xw_addr,
    input  wire [6:0]              xw_grp,
    input  wire [8*256-1:0]        xw_data,
    output wire                    rv,
    output wire [$clog2(RMAX)-1:0] rrow,
    output wire [NC*32-1:0]        rdata,
    output wire                    fault,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
`ifdef OT_SMH_CG
    ,
    // redesign-hbm 2026-10-09: per-SM coarse clock-gating WAKE (level; from the SM record adapter's per-SM busy, legacy 1):
    // tiles and back ends run on their own ICG (ot_cg_tile), the wake daisy-chained from the hop-1 tiles outward and
    // from each column's bottom tile to its back end; the front strips stay on the raw clock (they own the SM pins)
    input  wire                    cg_en
`endif
);
    localparam integer LB    = SUB * LBS;
    localparam integer LF    = SUB * LSB;
    localparam integer XC    = LB * 266 + LF * 16;
    localparam integer FRAGW = NC * XC;
    localparam integer NBEAT = (FRAGW + 2047) / 2048;
    localparam integer SW    = $clog2(IL);
    localparam integer RW    = $clog2(RMAX);
    localparam integer XW    = $clog2(XD);
    localparam integer TAGW  = RW + 1 + SW;
    localparam integer WSW   = LBS * 256 + LBS * 10 + LSB * 16;
    localparam integer CW    = 6 + TAGW;
    localparam integer RBW   = CW + WSW + 1 + XW;          // row bundle
    localparam integer BBW   = 1 + XW + NBEAT + 2048;      // x-write bundle
    localparam integer GLW   = 2 + 32 + TAGW;              // gather lane
    localparam integer QLW   = 2 + 32 + RW;                // result lane
    localparam integer NL    = NC / 2;
    localparam integer NR    = NC - NL;
    localparam integer NH    = (NL > NR) ? NL : NR;        // lanes per side = the farthest hop
    // log2 of the largest power of two dividing every x-write field offset: the straps carry only the bits above
    function automatic integer lg2g(input integer a, input integer b, input integer cc);
        integer k;
        begin
            k = 0;
            while (k < 11 && (a % (2 << k)) == 0 && (b % (2 << k)) == 0 && (cc % (2 << k)) == 0) k = k + 1;
            lg2g = k;
        end
    endfunction
    localparam integer A1B   = 11 - lg2g(LBS * 266, XC, XC);
    localparam integer A2B   = 11 - lg2g(LSB * 16, LB * 266, XC);
    initial if (NC < 4 || SUB != 4 || RPT != 2) $fatal(1, "ot_hbm_accel_smh (m3 three-strip front): NC >= 4, SUB 4, RPT 2");

    localparam integer NP    = SUB / RPT;                  // tiles per column
    // the production configuration instantiates the hardened pieces without parameter overrides (their defaults),
    // so synthesis keeps their module names as the macro masters; any other configuration passes its parameters
    localparam integer DEF   = (SUB == 4 && LBS == 2 && LSB == 16 && NC == 8 && IL == 8 && RMAX == 4096 && LEV == 4
                                && XD == 128 && MAX_OUT == 512 && TCK == 1 && PIO == 2 && HAZ == 1 && NOUT == 4
                                && RPT == 2 && REQCR == 1 && ENABLE_INT8 == 0) ? 1 : 0;
    initial if (SUB % RPT != 0) $fatal(1, "ot_hbm_accel_smh: SUB must be a multiple of RPT");
    wire [SUB*RBW-1:0] f_rl, f_rr;
    wire [NP*BBW-1:0]  f_bl, f_br;
    wire [NH*QLW-1:0]  f_ql, f_qr;
    // (margin m3) the front as three hardened strips, north to south, wired face to face
    localparam integer OPXW = (RW + 1) + 16 + 8 + 1 + 2 + XW;
    wire            n_sv, n_sret, n_rl, s_dv, s_dret, s_qv, s_qret, s_pv, s_sv;
    wire [OPXW-1:0] n_sd;
    wire [BBW-1:0]  n_xb;
    wire [RBW-1:0]  n_row0, s_row3;
    wire [2:0]      n_pbz;
    wire [55:0]     s_dd;
    wire [41:0]     s_qd;
    wire [1097:0]   s_pd;
    generate if (DEF != 0) begin : g_fd
        ot_hbm_accel_smh_front_n u_fn (
            .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .op_rows(op_rows), .op_c(op_c),
            .op_g(op_g), .op_gs(op_gs), .op_fmt(op_fmt), .op_xb(op_xb), .busy(busy), .xw_en(xw_en),
            .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .arrive(arrive), .release_in(release_in),
            .released(released), .rout_l0(f_rl[0 +: RBW]), .rout_r0(f_rr[0 +: RBW]), .bout_l0(f_bl[0 +: BBW]),
            .bout_r0(f_br[0 +: BBW]), .fs_v(n_sv), .fs_d(n_sd), .fs_ret(n_sret), .fx_b(n_xb), .fr_rl(n_rl),
            .fi_row0(n_row0), .fi_pbz(n_pbz));
        ot_hbm_accel_smh_front_c u_fc (
            .clk(clk), .rst_n(rst_n), .rout_l1(f_rl[RBW +: RBW]), .rout_r1(f_rr[RBW +: RBW]),
            .rout_l2(f_rl[2*RBW +: RBW]), .rout_r2(f_rr[2*RBW +: RBW]), .bout_l1(f_bl[BBW +: BBW]),
            .bout_r1(f_br[BBW +: BBW]), .fs_v(n_sv), .fs_d(n_sd), .fs_ret(n_sret), .fx_b(n_xb), .fr_rl(n_rl),
            .fo_row0(n_row0), .fo_pbz(n_pbz), .fd_v(s_dv), .fd_d(s_dd), .fd_ret(s_dret), .fq_v(s_qv), .fq_d(s_qd),
            .fq_ret(s_qret), .fp_v(s_pv), .fp_d(s_pd), .fsv(s_sv), .fo_row3(s_row3));
        ot_hbm_accel_smh_front_s u_fs (
            .clk(clk), .rst_n(rst_n), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines),
            .req_v(req_v), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v),
            .rsp_tag(rsp_tag), .rsp_data(rsp_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault),
            .rout_l3(f_rl[3*RBW +: RBW]), .rout_r3(f_rr[3*RBW +: RBW]), .qin_l(f_ql), .qin_r(f_qr),
            .fd_v(s_dv), .fd_d(s_dd), .fd_ret(s_dret), .fq_v(s_qv), .fq_d(s_qd), .fq_ret(s_qret), .fp_v(s_pv),
            .fp_d(s_pd), .fsv(s_sv), .fi_row3(s_row3));
    end else begin : g_fp
        ot_hbm_accel_smh_front_n #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .RMAX(RMAX), .XD(XD),
                                   .MAX_OUT(MAX_OUT), .PIO(PIO), .HAZ(HAZ), .NOUT(NOUT), .RPT(RPT)) u_fn (
            .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .op_rows(op_rows), .op_c(op_c),
            .op_g(op_g), .op_gs(op_gs), .op_fmt(op_fmt), .op_xb(op_xb), .busy(busy), .xw_en(xw_en),
            .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .arrive(arrive), .release_in(release_in),
            .released(released), .rout_l0(f_rl[0 +: RBW]), .rout_r0(f_rr[0 +: RBW]), .bout_l0(f_bl[0 +: BBW]),
            .bout_r0(f_br[0 +: BBW]), .fs_v(n_sv), .fs_d(n_sd), .fs_ret(n_sret), .fx_b(n_xb), .fr_rl(n_rl),
            .fi_row0(n_row0), .fi_pbz(n_pbz));
        ot_hbm_accel_smh_front_c #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .RMAX(RMAX), .XD(XD),
                                   .MAX_OUT(MAX_OUT), .PIO(PIO), .HAZ(HAZ), .NOUT(NOUT), .RPT(RPT), .ENABLE_INT8(ENABLE_INT8), .PIPE_INT8(PIPE_INT8)) u_fc (
            .clk(clk), .rst_n(rst_n), .rout_l1(f_rl[RBW +: RBW]), .rout_r1(f_rr[RBW +: RBW]),
            .rout_l2(f_rl[2*RBW +: RBW]), .rout_r2(f_rr[2*RBW +: RBW]), .bout_l1(f_bl[BBW +: BBW]),
            .bout_r1(f_br[BBW +: BBW]), .fs_v(n_sv), .fs_d(n_sd), .fs_ret(n_sret), .fx_b(n_xb), .fr_rl(n_rl),
            .fo_row0(n_row0), .fo_pbz(n_pbz), .fd_v(s_dv), .fd_d(s_dd), .fd_ret(s_dret), .fq_v(s_qv), .fq_d(s_qd),
            .fq_ret(s_qret), .fp_v(s_pv), .fp_d(s_pd), .fsv(s_sv), .fo_row3(s_row3));
        ot_hbm_accel_smh_front_s #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .RMAX(RMAX), .XD(XD),
                                   .MAX_OUT(MAX_OUT), .PIO(PIO), .HAZ(HAZ), .NOUT(NOUT), .RPT(RPT),
                                   .REQCR(REQCR)) u_fs (
            .clk(clk), .rst_n(rst_n), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines),
            .req_v(req_v), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v),
            .rsp_tag(rsp_tag), .rsp_data(rsp_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault),
            .rout_l3(f_rl[3*RBW +: RBW]), .rout_r3(f_rr[3*RBW +: RBW]), .qin_l(f_ql), .qin_r(f_qr),
            .fd_v(s_dv), .fd_d(s_dd), .fd_ret(s_dret), .fq_v(s_qv), .fq_d(s_qd), .fq_ret(s_qret), .fp_v(s_pv),
            .fp_d(s_pd), .fsv(s_sv), .fi_row3(s_row3));
    end endgenerate

    // tile (c, p) = rows p*RPT .. p*RPT+RPT-1 of column c: row bundles, x-write bundle, gather lanes; BE lanes
    localparam integer TRW = RPT * RBW;
    localparam integer TGI = (SUB - RPT) * GLW;
    wire [NC*NP*TRW-1:0]  t_ri, t_ro;
    wire [NC*NP*BBW-1:0]  t_bi, t_bo;
    wire [NC*NP*TGI-1:0]  t_gi;
    wire [NC*NP*SUB*GLW-1:0] t_go;
`ifdef OT_SMH_CG
    wire [NC*NP-1:0] t_cgi, t_cgo;
    wire [NC-1:0]    e_cgo;
`endif
    wire [NC*(NH-1)*QLW-1:0] e_qi;
    wire [NC*NH*QLW-1:0]     e_qo;
    genvar c, p, j;
    generate
    for (c = 0; c < NC; c = c + 1) begin : g_c
        for (p = 0; p < NP; p = p + 1) begin : g_p
            localparam integer T = c * NP + p;
            // row bundles and the x-write bundle: from the front (hop 1) or from the neighbour nearer the front
            if (c == NL - 1) begin : g_fl
                assign t_ri[T*TRW +: TRW] = f_rl[p*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = f_bl[p*BBW +: BBW];
            end else if (c < NL - 1) begin : g_wl
                assign t_ri[T*TRW +: TRW] = t_ro[((c+1)*NP+p)*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = t_bo[((c+1)*NP+p)*BBW +: BBW];
            end else if (c == NL) begin : g_fr
                assign t_ri[T*TRW +: TRW] = f_rr[p*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = f_br[p*BBW +: BBW];
            end else begin : g_er
                assign t_ri[T*TRW +: TRW] = t_ro[((c-1)*NP+p)*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = t_bo[((c-1)*NP+p)*BBW +: BBW];
            end
            // gather lanes from the tile above (the top tile: none)
            if (TGI > 0) begin : g_gi
                if (p == 0) begin : g_g0
                    assign t_gi[T*TGI +: TGI] = {TGI{1'b0}};
                end else begin : g_gn
                    assign t_gi[T*TGI +: TGI] = t_go[(T-1)*SUB*GLW +: TGI];
                end
            end
            // x-write slice straps of the tile's leaves: fragment offsets of the block-dot / BF16 fields (tie cells)
            wire [RPT*A1B-1:0] sa1; wire [RPT*5-1:0] sg1; wire [RPT*A2B-1:0] sa2; wire [RPT*5-1:0] sg2;
            for (j = 0; j < RPT; j = j + 1) begin : g_s
                localparam integer R  = p * RPT + j;
                localparam integer FA = c * XC + R * LBS * 266;
                localparam integer FB = c * XC + LB * 266 + R * LSB * 16;
                localparam [10:0] SA1 = FA % 2048;
                localparam [10:0] SA2 = FB % 2048;
                localparam [4:0]  SG1 = FA / 2048;
                localparam [4:0]  SG2 = FB / 2048;
                assign sa1[j*A1B +: A1B] = SA1[10 -: A1B];
                assign sa2[j*A2B +: A2B] = SA2[10 -: A2B];
                assign sg1[j*5 +: 5] = SG1;
                assign sg2[j*5 +: 5] = SG2;
            end
`ifdef OT_SMH_CG
            // the wake: hop-1 tiles from the SM's cg_en, every other tile from its row neighbour nearer the front
            if (c == NL - 1 || c == NL) begin : g_cw1
                assign t_cgi[T] = cg_en;
            end else if (c < NL - 1) begin : g_cwl
                assign t_cgi[T] = t_cgo[(c+1)*NP+p];
            end else begin : g_cwr
                assign t_cgi[T] = t_cgo[(c-1)*NP+p];
            end
            if (DEF != 0 && c < NL) begin : g_tw
                ot_hbm_accel_smh_tile_wg u_t (
                .clk(clk), .rst_n(rst_n), .cgi(t_cgi[T]), .cgo(t_cgo[T]), .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: (TGI > 0 ? TGI : 1)]),
                .gout(t_go[T*SUB*GLW +: SUB*GLW]));
            end else if (DEF != 0) begin : g_te
                ot_hbm_accel_smh_tile_eg u_t (
                .clk(clk), .rst_n(rst_n), .cgi(t_cgi[T]), .cgo(t_cgo[T]), .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: (TGI > 0 ? TGI : 1)]),
                .gout(t_go[T*SUB*GLW +: SUB*GLW]));
            end else begin : g_tp
                ot_hbm_accel_smh_tile_g #(.SUB(SUB), .RPT(RPT), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW),
                                        .XD(XD), .NBEAT(NBEAT), .TCK(TCK), .A1B(A1B), .A2B(A2B)) u_t (
                .clk(clk), .rst_n(rst_n), .cgi(t_cgi[T]), .cgo(t_cgo[T]), .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: (TGI > 0 ? TGI : 1)]),
                .gout(t_go[T*SUB*GLW +: SUB*GLW]));
            end
        end
`else
            if (DEF != 0 && c < NL) begin : g_tw
                ot_hbm_accel_smh_tile_w u_t (
                .clk(clk), .rst_n(rst_n), .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: (TGI > 0 ? TGI : 1)]),
                .gout(t_go[T*SUB*GLW +: SUB*GLW]));
            end else if (DEF != 0) begin : g_te
                ot_hbm_accel_smh_tile_e u_t (
                .clk(clk), .rst_n(rst_n), .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: (TGI > 0 ? TGI : 1)]),
                .gout(t_go[T*SUB*GLW +: SUB*GLW]));
            end else begin : g_tp
                ot_hbm_accel_smh_tile #(.SUB(SUB), .RPT(RPT), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW),
                                        .XD(XD), .NBEAT(NBEAT), .TCK(TCK), .A1B(A1B), .A2B(A2B)) u_t (
                .clk(clk), .rst_n(rst_n), .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: (TGI > 0 ? TGI : 1)]),
                .gout(t_go[T*SUB*GLW +: SUB*GLW]));
            end
        end
`endif
        // column back end: lanes from the bottom tile; result lanes from the neighbour farther from the front
        if (c < NL) begin : g_ql
            if (c == 0) begin : g_q0
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = {(NH-1)*QLW{1'b0}};
            end else begin : g_qn
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = e_qo[(c-1)*NH*QLW +: (NH-1)*QLW];
            end
        end else begin : g_qr
            if (c == NC - 1) begin : g_q0
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = {(NH-1)*QLW{1'b0}};
            end else begin : g_qn
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = e_qo[(c+1)*NH*QLW +: (NH-1)*QLW];
            end
        end
`ifdef OT_SMH_CG
        if (DEF != 0 && c < NL) begin : g_be_e
            ot_hbm_accel_smh_be_eg u_be (
                .clk(clk), .rst_n(rst_n), .cgi(t_cgo[c*NP+NP-1]), .cgo(e_cgo[c]), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
                .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
        end else if (DEF != 0) begin : g_be_w
            ot_hbm_accel_smh_be_wg u_be (
                .clk(clk), .rst_n(rst_n), .cgi(t_cgo[c*NP+NP-1]), .cgo(e_cgo[c]), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
                .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
        end else begin : g_bp
            ot_hbm_accel_smh_be_g #(.SUB(SUB), .RPT(RPT), .IL(IL), .RMAX(RMAX), .LEV(LEV), .TAGW(TAGW), .NH(NH)) u_be (
                .clk(clk), .rst_n(rst_n), .cgi(t_cgo[c*NP+NP-1]), .cgo(e_cgo[c]), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
                .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
        end
`else
        if (DEF != 0 && c < NL) begin : g_be_e
            ot_hbm_accel_smh_be_e u_be (
                .clk(clk), .rst_n(rst_n), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
                .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
        end else if (DEF != 0) begin : g_be_w
            ot_hbm_accel_smh_be_w u_be (
                .clk(clk), .rst_n(rst_n), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
                .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
        end else begin : g_bp
            ot_hbm_accel_smh_be #(.SUB(SUB), .RPT(RPT), .IL(IL), .RMAX(RMAX), .LEV(LEV), .TAGW(TAGW), .NH(NH)) u_be (
                .clk(clk), .rst_n(rst_n), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
                .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
        end
`endif
    end
    endgenerate
    // the front's result lanes: lane k = the column k hops + 1 away
    generate if (NL > 0) begin : g_fql
        assign f_ql = e_qo[(NL-1)*NH*QLW +: NH*QLW];      // lanes >= NL carry zeros (column 0's empty lanes)
    end else begin : g_fqz
        assign f_ql = {NH*QLW{1'b0}};
    end endgenerate
    assign f_qr = e_qo[NL*NH*QLW +: NH*QLW];
endmodule
module ot_hbm_accel_smh_front_c #(
    parameter integer ENABLE_INT8 = 0,
    parameter integer PIPE_INT8 = 0,
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer PIO  = 2,
    parameter integer HAZ  = 1,
    parameter integer NOUT = 4,
    parameter integer RPT  = 2,
    parameter integer NFMT = SUB * LBS * 8 + SUB
) (
    input  wire                    clk,
    input  wire                    rst_n,
    // rows 1 (tile row 0, leaf 1) and 2 (tile row 1, leaf 0); tile row 1's x-write bundle
    output wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] rout_l1, rout_r1, rout_l2, rout_r2,
    output wire [1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048-1:0] bout_l1, bout_r1,
    // north face (front_n)
    input  wire                    fs_v,
    input  wire [$clog2(RMAX)+1+16+8+1+2+$clog2(XD)-1:0] fs_d,
    output wire                    fs_ret,
    input  wire [1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048-1:0] fx_b,
    input  wire                    fr_rl,
    output wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] fo_row0,
    output wire [2:0]              fo_pbz,
    // south face (front_s)
    input  wire                    fd_v,
    input  wire [55:0]             fd_d,
    output wire                    fd_ret,
    output wire                    fq_v,
    output wire [41:0]             fq_d,
    input  wire                    fq_ret,
    input  wire                    fp_v,
    input  wire [1097:0]           fp_d,
    input  wire                    fsv,
    output wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] fo_row3
);
`ifdef OT_SMH_FC_HIER
    // ======== hbm-smh/fc OT_SMH_FC_HIER (2026-10-11): front_c as hardened sub-elements (physical spec: el1011-hbm-smh.log
    // "[hbm-smh/fc] PHYSICAL SPEC"): fc_bc (ring + bulk copy + south-face channels), fc_is (line skid, INT8, issue, s1,
    // hop H), fc_xl (x-write landing + relay 1 per side, row-0 face register), per side fc_t (rows 0 / 1), fc_xr (x-write
    // relay 2 + one line relay), fc_b (rows 2 / 3, x-write M / O).  The top is wiring only.  Cycles: tile row 1's x write
    // +2, every row bundle +2 (format select +2 with it); everything else unchanged.
    localparam integer XW_ = $clog2(XD);
    localparam integer TAGW_ = $clog2(RMAX) + 1 + $clog2(IL);
    localparam integer RBW_ = 6 + TAGW_ + LBS * 266 + LSB * 16 + 1 + XW_;
    localparam integer BBW_ = 1 + XW_ + (NC * (SUB * LBS * 266 + SUB * LSB * 16) + 2047) / 2048 + 2048;
    localparam integer S1W_ = 3 + TAGW_ + XW_;
    localparam integer LT_ = S1W_ + 1056, LBW_ = S1W_ + 544;
    localparam integer NSL_ = 34;
    initial if (SUB != 4 || RPT != 2 || LBS != 2 || LSB != 16 || NC != 8 || XW_ != 7 || BBW_ != 2069)
        $fatal(1, "OT_SMH_FC_HIER: built for SUB 4 RPT 2 LBS 2 LSB 16 NC 8 XW 7 (TAGW free: the bench runs RMAX 256)");
`ifdef SYNTHESIS
 `define OT_FC_ISP
 `define OT_FC_BCP
 `define OT_FC_RWP
 `define OT_FC_TP
`else
 `define OT_FC_ISP #(.ENABLE_INT8(ENABLE_INT8), .PIPE_INT8(PIPE_INT8), .IL(IL), .RMAX(RMAX), .XD(XD), .PIO(PIO), .HAZ(HAZ), .NOUT(NOUT))
 `define OT_FC_BCP #(.MAX_OUT(MAX_OUT), .PIO(PIO), .TAGW(TAGW_))
 `define OT_FC_RWP #(.ENABLE_INT8(ENABLE_INT8), .TAGW(TAGW_))
 `define OT_FC_TP #(.TAGW(TAGW_))
`endif
    wire [NSL_+1:0] k0_mv, k1_sr;
    wire [1087:0]   k0_d;
    wire            sv2;
    wire [RBW_-1:0] r0a, r3a, r0a_e, r3a_e;
    wire [LT_-1:0]  lt0, lt1;
    wire [LBW_-1:0] lb0, lb1, lbr0, lbr1;
    wire [11:0]     fm;
    wire [2:0]      fmr0, fmr1;
    wire [BBW_-1:0] xw_w, xw_e, xr_w, xr_e;
    ot_hbm_accel_smh_fc_bc `OT_FC_BCP u_bc (.clk(clk), .rst_a(rst_n), .fd_v(fd_v), .fd_d(fd_d), .fd_ret(fd_ret),
        .fq_v(fq_v), .fq_d(fq_d), .fq_ret(fq_ret), .fp_v(fp_v), .fp_d(fp_d), .fsv(fsv), .sv_o(sv2),
        .k0_mv(k0_mv), .k0_d(k0_d), .k1_sr(k1_sr), .r3a(r3a), .fo_row3(fo_row3));
    ot_hbm_accel_smh_fc_is `OT_FC_ISP u_is (.clk(clk), .rst_a(rst_n), .k0_mv(k0_mv), .k0_d(k0_d), .k1_sr(k1_sr),
        .fs_v(fs_v), .fs_d(fs_d), .fs_ret(fs_ret), .fr_rl(fr_rl), .fo_pbz(fo_pbz), .sv_i(sv2),
        .lt0(lt0), .lt1(lt1), .lb0(lb0), .lb1(lb1), .fm(fm));
    ot_hbm_accel_smh_fc_xl `OT_FC_TP u_xl (.clk(clk), .rst_a(rst_n), .fx_b(fx_b), .xw_w(xw_w), .xw_e(xw_e), .r0a(r0a),
        .fo_row0(fo_row0));
    ot_hbm_accel_smh_fc_t `OT_FC_RWP u_tw (.clk(clk), .rst_a(rst_n), .li(lt0), .fi(fm[2:0]), .rout(rout_l1), .r0a(r0a));
    ot_hbm_accel_smh_fc_t `OT_FC_RWP u_te (.clk(clk), .rst_a(rst_n), .li(lt1), .fi(fm[8:6]), .rout(rout_r1), .r0a(r0a_e));
    ot_hbm_accel_smh_fc_xr `OT_FC_TP u_rw (.clk(clk), .rst_a(rst_n), .xi(xw_w), .xo(xr_w), .li(lb0), .lo(lbr0), .fi(fm[5:3]), .fo(fmr0));
    ot_hbm_accel_smh_fc_xr `OT_FC_TP u_re (.clk(clk), .rst_a(rst_n), .xi(xw_e), .xo(xr_e), .li(lb1), .lo(lbr1), .fi(fm[11:9]), .fo(fmr1));
    ot_hbm_accel_smh_fc_b `OT_FC_RWP u_bw (.clk(clk), .rst_a(rst_n), .li(lbr0), .fi(fmr0), .xi(xr_w), .bout(bout_l1),
        .rout(rout_l2), .r3a(r3a));
    ot_hbm_accel_smh_fc_b `OT_FC_RWP u_be (.clk(clk), .rst_a(rst_n), .li(lbr1), .fi(fmr1), .xi(xr_e), .bout(bout_r1),
        .rout(rout_r2), .r3a(r3a_e));
`undef OT_FC_ISP
`undef OT_FC_BCP
`undef OT_FC_RWP
`undef OT_FC_TP
`else
    localparam integer LB    = SUB * LBS;
    localparam integer LF    = SUB * LSB;
    localparam integer XC    = LB * 266 + LF * 16;
    localparam integer FRAGW = NC * XC;
    localparam integer NBEAT = (FRAGW + 2047) / 2048;
    localparam integer SW    = $clog2(IL);
    localparam integer RW    = $clog2(RMAX);
    localparam integer XW    = $clog2(XD);
    localparam integer TAGW  = RW + 1 + SW;
    localparam integer WSW   = LBS * 256 + LBS * 10 + LSB * 16;
    localparam integer CW    = 6 + TAGW;
    localparam integer RBW   = CW + WSW + 1 + XW;
    localparam integer BBW   = 1 + XW + NBEAT + 2048;
    localparam integer OPW   = (RW + 1) + 16 + 8 + 1 + 2;
    localparam integer PIH   = PIO + 1;
    localparam integer CHD   = 2 * PIH + 3;
    localparam integer OPX   = OPW + XW;
    localparam integer NSL   = (1088 + 31) / 32;
    initial if (SUB != 4 || RPT != 2) $fatal(1, "ot_hbm_accel_smh_front_c: the three-strip front assumes SUB 4, RPT 2");

    initial if (ENABLE_INT8 && LSB != 16)
        $fatal(1, "fmt3 adapter requires the production 64 BF16 lanes");
    // ---------------- face halves of the channels and chains ----------------
    wire          h_start, h_pop;
    wire [OPX-1:0] h_opx;
    ot_hbm_accel_smh_csnk #(.W(OPX), .PK(1), .PRK(1), .DEPTH(CHD + 1)) u_sch (.clk(clk), .rst_n(rst_n),
        .i_v(fs_v), .i_d(fs_d), .o_ret(fs_ret), .m_valid(h_start), .m_ready(h_pop), .m_data(h_opx));
    wire [OPW-1:0] h_op = h_opx[XW +: OPW];
    wire [XW-1:0]  h_xb = h_opx[XW-1:0];
    wire [RW:0] h_rows = h_op[OPW-1 -: RW+1];
    wire [15:0] h_c    = h_op[11 +: 16];
    wire [7:0]  h_g    = h_op[3 +: 8];
    wire        h_gs   = h_op[2];
    wire [1:0]  h_fmt  = h_op[1:0];
`ifndef SYNTHESIS
    // The packed image contains pairs of real issue beats; padding slots do
    // not consume data. Reject an incomplete pair rather than leak a half into
    // the next operation. Production Qwen op_c is always even.
    always @(posedge clk)
        if (rst_n && ENABLE_INT8 && h_pop && h_fmt == 2'd3 &&
            h_rows[0] && h_c[0] && h_g[0])
            $fatal(1, "fmt3 needs an even count of real issue beats");
`endif
    wire h_rsp_v; wire [9:0] h_rsp_tag; wire [1087:0] h_rsp_data;
    // response: stages 3 and 4 of m2's four (the north-face landing, then beside the ring)
    ot_hbm_accel_smv_chain #(.W(1), .D(2), .RST(1)) u_prv (.clk(clk), .rst_n(rst_n), .d(fp_v), .q(h_rsp_v));
    ot_hbm_accel_smv_chain #(.W(1098), .D(2), .RST(0)) u_prd (.clk(clk), .rst_n(rst_n), .d(fp_d),
        .q({h_rsp_tag, h_rsp_data}));
    wire h_release;
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_prl (.clk(clk), .rst_n(rst_n), .d(fr_rl), .q(h_release));
    wire h_d_valid, h_d_ready; wire [55:0] h_d;
    ot_hbm_accel_smh_csnk #(.W(56), .PK(1), .PRK(1), .DEPTH(CHD + 1)) u_dch (.clk(clk), .rst_n(rst_n),
        .i_v(fd_v), .i_d(fd_d), .o_ret(fd_ret), .m_valid(h_d_valid), .m_ready(h_d_ready), .m_data(h_d));
    wire h_req_v, h_req_ready; wire [31:0] h_req_addr; wire [9:0] h_req_tag;
    ot_hbm_accel_smh_csrc #(.W(42), .PS(PIH - 1), .PR(1), .DEPTH(CHD)) u_rch (.clk(clk), .rst_n(rst_n),
        .s_valid(h_req_v), .s_ready(h_req_ready), .s_data({h_req_addr, h_req_tag}),
        .o_v(fq_v), .o_d(fq_d), .i_ret(fq_ret));
    // ---------------- bulk copy and the line stream ----------------
    wire          b_valid, b_ready;
    wire [1087:0] b_data;
    wire [NSL-1:0] b_valid_v, b_ready_v;
    ot_hbm_accel_bulk_copy_oq5 #(.ENABLE(1), .LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1),
                             .RING_MACRO(1)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(h_d_valid), .d_ready(h_d_ready), .d_base(h_d[55:24]), .d_lines(h_d[23:0]),
        .req_v(h_req_v), .req_ready(h_req_ready), .req_addr(h_req_addr), .req_tag(h_req_tag),
        .rsp_v(h_rsp_v), .rsp_tag(h_rsp_tag), .rsp_data(h_rsp_data),
        .s_valid(b_valid), .s_ready(b_ready), .s_data(b_data), .s_valid_v(b_valid_v), .s_ready_v(b_ready_v),
        .outstanding(), .idle());
    // (margin m3) the line leaves the ring through a per-slice skid beside the output queue (u_sk0, +1 cycle), then
    // the per-slice skid beside the issue (u_sk, m2's line skid): slice copy i talks only to slice copy i, so no
    // valid / ready fans out across the 1088-bit line (front_m2d -699 ps: oq_n -> 36 copies -> 2176 enables)
    wire [NSL+1:0] k0_sr, k0_mv, k1_sr, k1_mv;
    wire [1087:0]  k0_d;
    wire          w_valid, w_ready;
    wire [1087:0] w_data;
    ot_hbm_accel_smh_skid3v #(.W(1088)) u_sk0 (.clk(clk), .rst_n(rst_n), .s_valid_v({b_valid, b_valid, b_valid_v}),
        .s_ready_v(k0_sr), .s_data(b_data), .m_valid_v(k0_mv), .m_ready_v(k1_sr), .m_data(k0_d));
    assign b_ready = k0_sr[NSL];
    assign b_ready_v = k0_sr[NSL-1:0];
    ot_hbm_accel_smh_skid3v #(.W(1088)) u_sk (.clk(clk), .rst_n(rst_n), .s_valid_v(k0_mv), .s_ready_v(k1_sr),
        .s_data(k0_d), .m_valid_v(k1_mv), .m_ready_v({(NSL+2){w_ready}}), .m_data(w_data));
    assign w_valid = k1_mv[NSL+1];
    reg  [XW-1:0] xb_q;
    wire        sv, h_busy, h_arrive, h_released;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) xb_q <= {XW{1'b0}};
        else if (h_pop) xb_q <= h_xb;
    wire issue_w_valid, issue_w_ready, issue_line_end;
    wire [1087:0] issue_w_data;
    generate if (ENABLE_INT8) begin : g_int8
        wire unpack_ready;
        reg input_open;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) input_open <= 1'b0;
            else if (h_pop) input_open <= 1'b1;
            else if (issue_line_end) input_open <= 1'b0;
        wire intake_credit;
        if (PIPE_INT8) begin : g_credit
            ot_hbm_accel_int8_credit #(.RW(RW)) u_credit (
                .clk(clk),.rst_n(rst_n),.launch(h_pop),.take(w_valid && w_ready),
                .int8_mode(fmt_q==2'd3),.op_rows(h_rows),.op_g(h_g),.op_c(h_c),
                .intake_credit(intake_credit));
        end else begin : g_credit_legacy
            assign intake_credit=1'b1;
        end
        wire demand = input_open && !issue_line_end && intake_credit;
        // hbm-forks 2026-10-09 (HGI-1 CF-SM / CF-1): formats 0-2 BYPASS the adapter (zero added cycles: the DS formats
        // are cycle-identical to ENABLE_INT8 = 0); fmt3 lines go through it.  A DS op behind a fmt3 op waits for the
        // adapter to drain (order kept).
        wire a_busy, a_v; wire [1087:0] a_d;
        wire fmt3 = (fmt_q == 2'd3);
`ifdef OT_SMH_MUT_NOBYP
        wire byp = 1'b0;                                      // NEGATIVE CONTROL: every format through the adapter
`else
        wire byp = !fmt3 && !a_busy;
`endif
        assign w_ready = byp ? issue_w_ready : (unpack_ready && demand && fmt3);
        if (PIPE_INT8 >= 2) begin : g_ob
            // [cg] PIPE_INT8 = 2: registered-ready output queue (ot_hbm_accel_int8_line_ob): the issue's ready no
            // longer reaches the adapter's ~2.7k data enables
            ot_hbm_accel_int8_line_ob u_unpack (.clk(clk), .rst_n(rst_n), .busy(a_busy),
                .int8_mode(fmt3), .s_valid(w_valid && demand && !byp), .s_ready(unpack_ready), .s_data(w_data),
                .m_valid(a_v), .m_ready(issue_w_ready && !byp), .m_data(a_d));
        end else begin : g_ln
        ot_hbm_accel_int8_line #(.PIPE(PIPE_INT8)) u_unpack (.clk(clk), .rst_n(rst_n), .busy(a_busy),
            .int8_mode(fmt3), .s_valid(w_valid && demand && !byp), .s_ready(unpack_ready), .s_data(w_data),
            .m_valid(a_v), .m_ready(issue_w_ready && !byp), .m_data(a_d));
        end
        assign issue_w_valid = byp ? w_valid : a_v;
        assign issue_w_data  = byp ? w_data : a_d;
    end else begin : g_no_int8
        assign issue_w_valid = w_valid;
        assign w_ready = issue_w_ready;
        assign issue_w_data = w_data;
    end endgenerate
    // the unpack's format select (m2, unchanged): launch register, 4 copies, NFC copies, 2 x NFMT replicas
    localparam integer NFR = 2 * NFMT;
    localparam integer NFC = (NFR + 7) / 8;
    reg              pop_r;
    reg  [1:0]       fmt_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pop_r <= 1'b0; fmt_q <= 2'd0; end
        else begin pop_r <= h_pop; if (h_pop) fmt_q <= h_fmt; end
    wire [3:0]       pd1;
    wire [7:0]       fq1;
    wire [NFC-1:0]   pd_c;
    wire [2*NFC-1:0] fq_c;
    wire [2*NFR-1:0] fmt_r;
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_f1
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_pd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(pop_r), .q(pd1[k]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_fq (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(fmt_q),
            .q(fq1[2*k +: 2]));
    end endgenerate
    generate for (k = 0; k < NFC; k = k + 1) begin : g_fc
        localparam integer R0 = 8 * k;
        localparam integer SD = R0 / NFMT;
        localparam integer JR = R0 % NFMT;
        localparam integer SPR = (JR < SUB * LBS * 8) ? JR / (LBS * 8) : JR - SUB * LBS * 8;
        localparam integer G1 = SD * 2 + ((SPR / RPT) % 2);
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_pd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(pd1[G1]), .q(pd_c[k]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_fq (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(fq1[2*G1 +: 2]),
            .q(fq_c[2*k +: 2]));
    end endgenerate
    generate for (k = 0; k < NFR; k = k + 1) begin : g_fmt
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1), .EN(1)) u (.clk(clk), .rst_n(rst_n), .en(pd_c[k / 8]),
            .d(fq_c[2*(k / 8) +: 2]), .q(fmt_r[2*k +: 2]));
    end endgenerate
`ifdef OT_SMH_MUT_BFDLY
    localparam integer DBFX = 11 + 64;
`else
    localparam integer DBFX = 11;
`endif
    ot_hbm_accel_issue_pq #(.IL(IL), .RMAX(RMAX), .XDEPTH(XD), .NOUT(NOUT), .HAZ(HAZ), .DBF(DBFX)) u_issue (
        .clk(clk), .rst_n(rst_n), .start_v(h_start), .launch(h_pop), .op_rows(h_rows), .op_c(h_c), .op_g(h_g),
        .op_gs(h_gs), .op_bf(h_fmt == 2'd0 || (ENABLE_INT8 && h_fmt == 2'd3)),
        .w_valid(issue_w_valid), .x_rdy(1'b1), .w_ready(issue_w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_line_end(issue_line_end), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release),
        .released(h_released), .hz_wait());
    // barrier outputs: launched at the north face (front_n lands them and launches them at its pins)
    ot_hbm_accel_smv_chain #(.W(3), .D(1), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n),
        .d({h_busy, h_arrive, h_released}), .q(fo_pbz));
    // retire: m2's three-stage chain; stage 1 sits at front_s's north face, stages 2 (landing) and 3 here
    ot_hbm_accel_smv_chain #(.W(1), .D(2), .RST(1)) u_sv (.clk(clk), .rst_n(rst_n), .d(fsv), .q(sv));
    // ---------------- s1, hop H, hop H2 (m2, unchanged) ----------------
    localparam integer NSC = 2 * (SUB / RPT);
    localparam integer S1W = 3 + TAGW + XW;
    reg [1087:0]     s1_w;
    reg [2:0]        s1_cv;
    reg [TAGW+XW-1:0] s1_ct;
    wire [S1W-1:0]   s1_c = {s1_cv, s1_ct};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s1_cv <= 3'd0;
        else s1_cv <= {adv && row_ok, i_first, i_last};
    always @(posedge clk) begin
`ifdef OT_SMH_MUT_S1W
        s1_w <= issue_w_data ^ 1088'd8;               // negative-control mutant only (bench: --mut-s1w); never defined in a build
`else
        s1_w <= issue_w_data;
`endif
        s1_ct <= {row_now[RW-1:0], i_glast, si, xa + xb_q};
    end
    wire [NSC*S1W-1:0]  s1c;
    wire [NSC*1088-1:0] hw;
    generate for (k = 0; k < NSC; k = k + 1) begin : g_h
        localparam integer PR = k % (SUB / RPT);
        ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(s1_c[S1W-1 -: 3]), .q(s1c[k*S1W + TAGW + XW +: 3]));
        ot_hbm_accel_smh_kreg #(.W(TAGW + XW)) u_t (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(s1_c[TAGW + XW - 1:0]), .q(s1c[k*S1W +: TAGW + XW]));
        if (LBS == 2 && LSB == 16) begin : g_rows
            if (PR == 0) begin : g_r0
                ot_hbm_accel_smh_kreg #(.W(1056)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(s1_w[1055:0]),
                    .q(hw[k*1088 +: 1056]));
                assign hw[k*1088 + 1056 +: 32] = 32'd0;
            end else begin : g_r1
                ot_hbm_accel_smh_kreg #(.W(512)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(s1_w[1023:512]),
                    .q(hw[k*1088 + 512 +: 512]));
                ot_hbm_accel_smh_kreg #(.W(32)) u_e (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(s1_w[1087:1056]),
                    .q(hw[k*1088 + 1056 +: 32]));
                assign hw[k*1088 +: 512] = 512'd0;
                assign hw[k*1088 + 1024 +: 32] = 32'd0;
            end
        end else begin : g_full
            ot_hbm_accel_smh_kreg #(.W(1088)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(s1_w),
                .q(hw[k*1088 +: 1088]));
        end
    end endgenerate
    wire [NSC*S1W-1:0]  s1c2;
    wire [NSC*1088-1:0] hw2;
    generate for (k = 0; k < NSC; k = k + 1) begin : g_h2
        ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(s1c[k*S1W + TAGW + XW +: 3]), .q(s1c2[k*S1W + TAGW + XW +: 3]));
        ot_hbm_accel_smh_kreg #(.W(TAGW + XW)) u_t (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(s1c[k*S1W +: TAGW + XW]), .q(s1c2[k*S1W +: TAGW + XW]));
        localparam integer PR2 = k % (SUB / RPT);
        if (LBS == 2 && LSB == 16) begin : g_rows
            if (PR2 == 0) begin : g_r0
                ot_hbm_accel_smh_kreg #(.W(1056)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(hw[k*1088 +: 1056]), .q(hw2[k*1088 +: 1056]));
                assign hw2[k*1088 + 1056 +: 32] = 32'd0;
            end else begin : g_r1
                ot_hbm_accel_smh_kreg #(.W(512)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(hw[k*1088 + 512 +: 512]), .q(hw2[k*1088 + 512 +: 512]));
                ot_hbm_accel_smh_kreg #(.W(32)) u_e (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(hw[k*1088 + 1056 +: 32]), .q(hw2[k*1088 + 1056 +: 32]));
                assign hw2[k*1088 +: 512] = 512'd0;
                assign hw2[k*1088 + 1024 +: 32] = 32'd0;
            end
        end else begin : g_full
            ot_hbm_accel_smh_kreg #(.W(1088)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1),
                .d(hw[k*1088 +: 1088]), .q(hw2[k*1088 +: 1088]));
        end
    end endgenerate
    // ---------------- stage A: unpack per (side, sub) (m2, unchanged) ----------------
    genvar sp, q, bb, sd;
    wire [2*SUB*RBW-1:0] a_in;
    generate for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
        for (sd = 0; sd < 2; sd = sd + 1) begin : g_sd
            localparam integer CI = sd * (SUB / RPT) + sp / RPT;
            wire [1087:0] lw = hw2[CI*1088 +: 1088];
            wire [WSW-1:0] un;
            for (q = 0; q < LBS; q = q + 1) begin : g_q
                localparam integer J = sp * LBS + q;
                wire [255:0] fp4w, fp8w;
                for (bb = 0; bb < 32; bb = bb + 1) begin : g_b
                    localparam integer RI = sd * NFMT + ((sp * LBS + q) * 8 + bb / 4) % NFMT;
                    assign fp4w[8*bb +: 8] = {4'd0, lw[128*J + 4*bb +: 4]};
                    assign fp8w[8*bb +: 8] = (J < LB / 2) ? lw[256*J + 8*bb +: 8] : 8'd0;
                    assign un[256*q + 8*bb +: 8] = (fmt_r[2*RI +: 2] == 2'd2) ? fp4w[8*bb +: 8] : fp8w[8*bb +: 8];
                end
                assign un[LBS*256 + 10*q +: 10] = {2'b00, lw[1024 + 8*J +: 8]} - 10'sd127;
            end
            assign un[LBS*266 +: LSB*16] = lw[sp*LSB*16 +: LSB*16];
            localparam integer RC = sd * NFMT + (SUB * LBS * 8 + sp) % NFMT;
            wire bf_op = (fmt_r[2*RC +: 2] == 2'd0) || (ENABLE_INT8 && fmt_r[2*RC +: 2] == 2'd3);
            wire fp4_op = (fmt_r[2*RC +: 2] == 2'd2);
            wire [S1W-1:0] c1 = s1c2[CI*S1W +: S1W];
            wire s1_v = c1[S1W-1], s1_first = c1[S1W-2], s1_last = c1[S1W-3];
            wire [TAGW-1:0] s1_tag = c1[XW +: TAGW];
            wire [XW-1:0] s1_xa = c1[XW-1:0];
            wire [CW-1:0] c_in = {s1_v && !bf_op, s1_v && bf_op, s1_first, s1_last, fp4_op, bf_op, s1_tag};
            assign a_in[(sd*SUB+sp)*RBW +: RBW] = {c_in, un, s1_v, s1_xa};
        end
    end endgenerate
    // ---------------- row bundles: A -> M -> (rows 1, 2: P -> O at the pins; rows 0, 3: M at the face) ----------------
    wire [2*SUB*RBW-1:0] o_r;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_side
        for (sp = 0; sp < SUB; sp = sp + 1) begin : g_rs
            if (sp != 0 && sp != SUB - 1) begin : g_in
                wire [RBW-1:0] a_r, m_r, p_r;
                ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_a (.clk(clk), .rst_n(rst_n),
                    .d(a_in[(sd*SUB+sp)*RBW +: RBW]), .q(a_r));
                ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_m (.clk(clk), .rst_n(rst_n),
                    .d(a_r), .q(m_r));
                ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_p (.clk(clk), .rst_n(rst_n),
                    .d(m_r), .q(p_r));
                ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_o (.clk(clk), .rst_n(rst_n),
                    .d(p_r), .q(o_r[(sd*SUB+sp)*RBW +: RBW]));
            end else if (sd == 0) begin : g_x
                // rows 0 and 3 leave through a face: one copy (both sides' A inputs are bit-identical)
                wire [RBW-1:0] a_r;
                ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_a (.clk(clk), .rst_n(rst_n),
                    .d(a_in[(sd*SUB+sp)*RBW +: RBW]), .q(a_r));
                ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_m (.clk(clk), .rst_n(rst_n),
                    .d(a_r), .q(o_r[(sd*SUB+sp)*RBW +: RBW]));
            end else begin : g_z
                assign o_r[(sd*SUB+sp)*RBW +: RBW] = {RBW{1'b0}};
            end
        end
    end endgenerate
    assign fo_row0 = o_r[0 +: RBW];
    assign fo_row3 = o_r[(SUB-1)*RBW +: RBW];
    assign rout_l1 = o_r[1*RBW +: RBW];
    assign rout_l2 = o_r[2*RBW +: RBW];
    assign rout_r1 = o_r[(SUB+1)*RBW +: RBW];
    assign rout_r2 = o_r[(SUB+2)*RBW +: RBW];
    // ---------------- tile row 1's x-write bundle: landed at the north face, M per side, O at the pins ----------------
    wire [BBW-1:0] xl;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_xlv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(fx_b[BBW-1]),
        .q(xl[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_xld (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(fx_b[BBW-2:0]),
        .q(xl[BBW-2:0]));
    wire [2*BBW-1:0] o_b;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_bs
        wire [BBW-1:0] m_b;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bmv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(xl[BBW-1]),
            .q(m_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bmd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(xl[BBW-2:0]),
            .q(m_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bov (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-1]),
            .q(o_b[sd*BBW + BBW - 1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bod (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-2:0]),
            .q(o_b[sd*BBW +: BBW-1]));
    end endgenerate
    assign bout_l1 = o_b[0 +: BBW];
    assign bout_r1 = o_b[BBW +: BBW];
`endif
endmodule
(* blackbox *) module ot_hbm_accel_smh_front_n #(
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer PIO  = 2,
    parameter integer HAZ  = 1,
    parameter integer NOUT = 4,
    parameter integer RPT  = 2,
    parameter integer NFMT = SUB * LBS * 8 + SUB
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    output wire                    start_ready,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    input  wire [$clog2(XD)-1:0]   op_xb,
    output wire                    busy,
    input  wire                    xw_en,
    input  wire [$clog2(XD)-1:0]   xw_addr,
    input  wire [6:0]              xw_grp,
    input  wire [8*256-1:0]        xw_data,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released,
    
    output wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] rout_l0, rout_r0,
    output wire [1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048-1:0] bout_l0, bout_r0,
    
    output wire                    fs_v,
    output wire [$clog2(RMAX)+1+16+8+1+2+$clog2(XD)-1:0] fs_d,
    input  wire                    fs_ret,
    output wire [1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048-1:0] fx_b,
    output wire                    fr_rl,
    input  wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] fi_row0,
    input  wire [2:0]              fi_pbz
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_front_s #(
    parameter integer RESULT_VALID = `ifdef OT_SMH_RESULT_VALID 1 `else 0 `endif,
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer PIO  = 2,
    parameter integer HAZ  = 1,
    parameter integer NOUT = 4,
    parameter integer RPT  = 2,
    parameter integer NFMT = SUB * LBS * 8 + SUB,
    parameter integer REQCR = 1,
    parameter integer PT4 = 1           
                                        
                                        
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    d_valid,
    output wire                    d_ready,
    input  wire [31:0]             d_base,
    input  wire [23:0]             d_lines,
    output wire                    req_v,
    input  wire                    req_ready,
    output wire [31:0]             req_addr,
    output wire [9:0]              req_tag,
    input  wire                    rsp_v,
    input  wire [9:0]              rsp_tag,
    input  wire [1087:0]           rsp_data,
    output wire                    rv,
    output wire [$clog2(RMAX)-1:0] rrow,
    output wire [NC*32-1:0]        rdata,
    output wire                    fault,
    output wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] rout_l3, rout_r3,
    input  wire [((NC-NC/2 > NC/2) ? NC-NC/2 : NC/2)*(2+32+$clog2(RMAX))-1:0] qin_l, qin_r,
    
    output wire                    fd_v,
    output wire [55:0]             fd_d,
    input  wire                    fd_ret,
    input  wire                    fq_v,
    input  wire [41:0]             fq_d,
    output wire                    fq_ret,
    output wire                    fp_v,
    output wire [1097:0]           fp_d,
    output wire                    fsv,
    input  wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] fi_row3
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_tile_eg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo,
    input  wire [17:0] xs_a1, input wire [9:0] xs_g1, input wire [13:0] xs_a2, input wire [9:0] xs_g2,
    input  wire [1635:0] rin, input wire [2068:0] bin, output wire [1635:0] rout, output wire [2068:0] bout,
    input  wire [99:0] gin, output wire [199:0] gout
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_tile_wg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo,
    input  wire [17:0] xs_a1, input wire [9:0] xs_g1, input wire [13:0] xs_a2, input wire [9:0] xs_g2,
    input  wire [1635:0] rin, input wire [2068:0] bin, output wire [1635:0] rout, output wire [2068:0] bout,
    input  wire [99:0] gin, output wire [199:0] gout
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_be_eg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo, input wire [199:0] gin, input wire [137:0] qin,
    output wire [183:0] qout
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_be_wg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo, input wire [199:0] gin, input wire [137:0] qin,
    output wire [183:0] qout
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_bc #(parameter integer MAX_OUT = 512, parameter integer PIO = 2, parameter integer TAGW = 16) (
    input  wire          clk, rst_a,
    input  wire          fd_v,  input wire [55:0] fd_d, output wire fd_ret,
    output wire          fq_v,  output wire [41:0] fq_d, input wire fq_ret,
    input  wire          fp_v,  input wire [1097:0] fp_d,
    input  wire          fsv,   output wire sv_o,
    output wire [35:0]   k0_mv, output wire [1087:0] k0_d, input wire [35:0] k1_sr,
    input  wire [802+TAGW-1:0] r3a, output wire [802+TAGW-1:0] fo_row3
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_is #(
    parameter integer ENABLE_INT8 = 1, parameter integer PIPE_INT8 = 2, parameter integer IL = 8,
    parameter integer RMAX = 4096, parameter integer XD = 128, parameter integer PIO = 2, parameter integer HAZ = 1,
    parameter integer NOUT = 4
) (
    input  wire          clk, rst_a,
    input  wire [35:0]   k0_mv, input wire [1087:0] k0_d, output wire [35:0] k1_sr,
    input  wire          fs_v,  input wire [$clog2(RMAX)+1+16+8+1+2+$clog2(XD)-1:0] fs_d, output wire fs_ret,
    input  wire          fr_rl, output wire [2:0] fo_pbz,
    input  wire          sv_i,
    output wire [3+$clog2(RMAX)+1+$clog2(IL)+$clog2(XD)+1056-1:0] lt0, lt1,
    output wire [3+$clog2(RMAX)+1+$clog2(IL)+$clog2(XD)+544-1:0]  lb0, lb1,
    output wire [11:0]   fm
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_xl #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] fx_b, output wire [2068:0] xw_w, xw_e,
    input  wire [802+TAGW-1:0] r0a, output wire [802+TAGW-1:0] fo_row0
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_t #(parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [1066+TAGW-1:0] li, input wire [2:0] fi,
    output wire [802+TAGW-1:0] rout, output wire [802+TAGW-1:0] r0a
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_xr #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] xi, output wire [2068:0] xo,
    input  wire [554+TAGW-1:0] li, output wire [554+TAGW-1:0] lo,
    input  wire [2:0]    fi, output wire [2:0]    fo
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_b #(parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [554+TAGW-1:0] li, input wire [2:0] fi, input wire [2068:0] xi,
    output wire [2068:0] bout, output wire [802+TAGW-1:0] rout, output wire [802+TAGW-1:0] r3a
);
endmodule
