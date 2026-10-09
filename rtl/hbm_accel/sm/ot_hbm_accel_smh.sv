`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_smh: the DS HBM SM element (ot_hbm_accel_sm_pq: pipelined issue + the G1 select by the column that
// produced the result) rebuilt as a PHYSICAL HIERARCHY that closes by construction at 1.2 GHz SS (0.833 ns):
// every hardened piece is small (one clock tree each, ~0.3 mm), every boundary is flop -> pin -> pin -> flop with no
// logic, and the parent holds no standard cells (abutment wires and the macro clock tree only).
//
// Why (results/rtl/hbm_opt1_production_20261005/installed_context_r1 and this record's full STA of the legacy CTS
// database): the flat element (225k top flops, 2.2 x 2.07 mm, tc16 / bd_col as sub-macros) had a 3.4-4.3 ns clock
// insertion with 260-350 ps skew between neighbouring top flops, macro clock pins 366 ps late behind long-wire repair,
// 44k violating endpoints in every class (macro -> G1, G1 -> DG, the distribution chains, the bulk copy, the column
// trees), and a >6 h route.  The cure is structural, not a knob.
//
// Pieces (each hardened once, replicated):
//   ot_hbm_accel_smh_tile  (NC x SUB, one per leaf): the leaf's x-store macros, its E3/E4 registers, the BF16 and the
//       block-dot column logic FLAT (no macro boundary inside), the G1 select by the producing column's valid, and
//       pass-through registers: the row bundle (control, weight slice, x read) and the x-write beat move one tile per
//       cycle along the row, the gather lanes one tile per cycle down the column.  Every input lands in a flop, every
//       output leaves one.  The tile is identical everywhere: its x-write slice position is a static strap (xs_*)
//       driven by tie cells in the parent (a rotator on constants), not a per-instance netlist.
//   ot_hbm_accel_smh_be    (NC, one per column, below the column): lane landing + deskew (lane k waits SUB-1-k), the
//       column's combine tree and streaming stack, and the result lanes moving one column per cycle to the front.
//   ot_hbm_accel_smh_front (one, in the middle of the row): the pins (PIO), descriptor / request / op channels, bulk
//       copy, pipelined issue, s1, unpack, two distribution stages, result landing + deskew, and the pin outputs.
// Columns 0..NL-1 lie west of the front (column NL-1 next to it), NL..NC-1 east (NL = NC/2); a column at hop h
// (1 = next to the front) receives its row bundle h cycles after the front's output register.
//
// Cycles against ot_hbm_accel_sm_pq (DS = 3, DG = 3, PIO = 2), all latency only (one issue a cycle, the issue loop and
// every single-cycle loop unchanged; measured on the 12 PQ sequences, records results/rtl/hbm_sm_structure_20261005):
//   row bundle: a hop-h column lands S+2+h (sm_pq: every column S+4): -1..+2;
//   gather: G1 -> tree input 2 flops (sm_pq 4): -2 (two rows per tile, one pass per tile);
//   stack: ot_hbm_accel_stack (pending lookup registered): +1;
//   results: 2h transport + deskew to the farthest column; the pins' output chain sees a row +3..4 cycles after
//   sm_pq, rdone likewise (measured +3..4 cycles per dependent op in the serial runs);
//   x write: the strap rotation in two registered stages: write edge W+5+h, read edge S+3+h (sm_pq W+7, S+5): the
//   same write-before-read margin, so every load the hub issues for sm_pq is legal here.
// The fault output is a sticky OR, now registered at each hop (a few cycles later).
// Arithmetic, line order, tree order, x addressing: unchanged (leaf, tree, stack pairing and issue are sm_pq's).
// ---------------------------------------------------------------------------
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

// A register that synthesis keeps as its own instance (a replica stays a replica); optional async reset to 0 and
// optional load enable.
(* keep_hierarchy *)
module ot_hbm_accel_smh_kreg #(
    parameter integer W = 1,
    parameter integer RST = 0,
    parameter integer EN = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         en,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    generate if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n)
            if (!rst_n) q <= {W{1'b0}};
            else if (EN == 0 || en) q <= d;
    end else begin : g_n
        always @(posedge clk) if (EN == 0 || en) q <= d;
    end endgenerate
endmodule

// ot_hbm_accel_smh_kreg with its flops kept (a deliberate duplicate copy that synthesis must not merge)
module ot_hbm_accel_smh_kregk #(
    parameter integer W = 1,
    parameter integer RST = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* keep *) reg [W-1:0] r;
    generate if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= {W{1'b0}}; else r <= d;
    end else begin : g_n
        always @(posedge clk) r <= d;
    end endgenerate
    assign q = r;
endmodule

// A 2-entry skid with a registered ready (s_ready = not full, from the count register) and a registered head
// (m_data leaves a flop): one transfer a cycle, order and data unchanged, +1 cycle from s to m.
module ot_hbm_accel_smh_skid #(
    parameter integer W = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    reg [1:0]   cnt;
    reg [W-1:0] head, tail;
    assign s_ready = (cnt != 2'd2);
    assign m_valid = (cnt != 2'd0);
    assign m_data = head;
    wire push = s_valid && s_ready;
    wire pop  = m_valid && m_ready;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cnt <= 2'd0;
        else cnt <= cnt + {1'b0, push} - {1'b0, pop};
    always @(posedge clk) begin
        if (cnt == 2'd2) begin if (pop) head <= tail; end
        else if (push && (cnt == 2'd0 || pop)) head <= s_data;
        if (push && cnt == 2'd1 && !pop) tail <= s_data;
    end
endmodule

// ot_hbm_accel_smh_skid's behaviour with the data kept in place: two entries written by a write pointer, read
// through one-hot read-select copies (one per 32-bit slice, registered), so a pop moves no data and fans out only to
// the select copies' inputs.  Registered ready (not full), one transfer a cycle, +1 cycle, order and data unchanged.
module ot_hbm_accel_smh_skid2 #(
    parameter integer W = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    localparam integer NS = (W + 31) / 32;
    reg [1:0]   cnt;
    reg         wp, rp;
    reg [W-1:0] e0, e1;
    assign s_ready = (cnt != 2'd2);
    assign m_valid = (cnt != 2'd0);
    wire push = s_valid && s_ready;
    wire pop  = m_valid && m_ready;
    wire rp_nx = pop ? ~rp : rp;
    wire [2*NS-1:0] ro;
    ot_hbm_accel_bc_kreg #(.W(2*NS), .RV({NS{2'b01}})) u_ro (.clk(clk), .rst_n(rst_n), .d({NS{rp_nx, ~rp_nx}}),
        .q(ro));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cnt <= 2'd0; wp <= 1'b0; rp <= 1'b0; end
        else begin
            cnt <= cnt + {1'b0, push} - {1'b0, pop};
            if (push) wp <= ~wp;
            rp <= rp_nx;
        end
    always @(posedge clk) begin
        if (push && !wp) e0 <= s_data;
        if (push && wp)  e1 <= s_data;
    end
    genvar i;
    generate for (i = 0; i < NS; i = i + 1) begin : g_s
        localparam integer LO = 32 * i;
        localparam integer WB = (W - LO < 32) ? W - LO : 32;
        assign m_data[LO +: WB] = ({WB{ro[2*i]}} & e0[LO +: WB]) | ({WB{ro[2*i+1]}} & e1[LO +: WB]);
    end endgenerate
endmodule

// ot_hbm_accel_smh_skid2 with the whole control state (count, write and read pointers) held in one kept copy per
// 32-bit slice plus one copy for each port (ready to the source, valid to the sink): a push or pop is applied by
// every copy alike (bit-identical), so no state register fans out across the line.  Same behaviour, +1 cycle.
module ot_hbm_accel_smh_skid3 #(
    parameter integer W = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    localparam integer NS = (W + 31) / 32;
    // copy NS: the source port's (ready), copy NS + 1: the sink port's (valid); copies 0 .. NS-1: the slices
    wire [4*(NS+2)-1:0] st;                    // per copy {cnt[1:0], wp, rp}
    wire [1:0] cs = st[4*NS + 2 +: 2];
    wire [1:0] cm = st[4*(NS+1) + 2 +: 2];
    assign s_ready = (cs != 2'd2);
    assign m_valid = (cm != 2'd0);
    wire push = s_valid && s_ready;
    wire pop  = m_valid && m_ready;
    genvar i;
    generate for (i = 0; i < NS + 2; i = i + 1) begin : g_c
        wire [1:0] c = st[4*i + 2 +: 2];
        wire wp = st[4*i + 1], rp = st[4*i];
        // push / pop recomputed from this copy's own count (all copies hold the same count)
        wire pu = s_valid && (c != 2'd2);
        wire po = (c != 2'd0) && m_ready;
        ot_hbm_accel_bc_kreg #(.W(4), .RV(4'd0)) u (.clk(clk), .rst_n(rst_n),
            .d({c + {1'b0, pu} - {1'b0, po}, pu ? ~wp : wp, po ? ~rp : rp}), .q(st[4*i +: 4]));
        if (i < NS) begin : g_d
            localparam integer LO = 32 * i;
            localparam integer WB = (W - LO < 32) ? W - LO : 32;
            reg [WB-1:0] e0, e1;
            always @(posedge clk) begin
                if (pu && !wp) e0 <= s_data[LO +: WB];
                if (pu && wp)  e1 <= s_data[LO +: WB];
            end
            assign m_data[LO +: WB] = rp ? e1 : e0;
        end
    end endgenerate
endmodule

// ot_hbm_accel_smv_chan with a registered head: the sink FIFO's output is a register holding mem[rp] (refilled
// from mem[rp + 1] on a pop, or from the arriving entry when it lands at the new head), so m_data leaves a flop
// and no read-pointer mux sits between the FIFO and the consumer / pin.  Cycle-identical to ot_hbm_accel_smv_chan:
// same credits, same P-stage transfer and return, m_valid = (cnt != 0), m_data = mem[rp] whenever m_valid.
module ot_hbm_accel_smh_chan #(
    parameter integer W = 8,
    parameter integer P = 2,
    parameter integer DEPTH = 7
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    localparam integer CW = $clog2(DEPTH + 1);
    localparam integer AW = (DEPTH <= 1) ? 1 : $clog2(DEPTH);
    reg  [CW-1:0] cred;
    wire          fire = s_valid && s_ready;
    wire          ret;
    assign s_ready = (cred != 0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cred <= DEPTH[CW-1:0];
        else cred <= cred - fire + ret;
    wire          f_v;
    wire [W-1:0]  f_d;
    ot_hbm_accel_smv_chain #(.W(1), .D(P), .RST(1)) u_fv (.clk(clk), .rst_n(rst_n), .d(fire), .q(f_v));
    ot_hbm_accel_smv_chain #(.W(W), .D(P), .RST(0)) u_fd (.clk(clk), .rst_n(rst_n), .d(s_data), .q(f_d));
    reg  [W-1:0]  mem [0:DEPTH-1];
    reg  [AW-1:0] wp, rp, rp1;
    reg  [CW-1:0] cnt;
    reg  [W-1:0]  head;
    wire          pop = m_valid && m_ready;
    assign m_valid = (cnt != 0);
    assign m_data = head;
    wire [AW-1:0] wp1 = (wp == DEPTH - 1) ? {AW{1'b0}} : wp + 1'b1;
    wire [AW-1:0] rp2 = (rp1 == DEPTH - 1) ? {AW{1'b0}} : rp1 + 1'b1;
    wire          land_head = f_v && (pop ? (wp == rp1) : (wp == rp));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; rp1 <= (DEPTH == 1) ? {AW{1'b0}} : 1; cnt <= 0; end
        else begin
            if (f_v) wp <= wp1;
            if (pop) begin rp <= rp1; rp1 <= rp2; end
            cnt <= cnt + f_v - pop;
        end
    always @(posedge clk) begin
        if (f_v) mem[wp] <= f_d;
        if (land_head) head <= f_d;
        else if (pop) head <= mem[rp1];
    end
    ot_hbm_accel_smv_chain #(.W(1), .D(P), .RST(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(pop), .q(ret));
endmodule

// ---------------------------------------------------------------------------
// Credit-channel halves (margin m3): ot_hbm_accel_smh_chan cut at a hardened-piece face.  csrc holds the credits
// and the first PS forward / last PR return stages, csnk the last PK forward / first PRK return stages and the
// FIFO with its registered head.  With PS + PK = PR + PRK = P the pair is cycle-identical to
// ot_hbm_accel_smh_chan #(.P(P)): every face signal leaves a flop on one side and lands in a flop on the other.
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_csrc #(
    parameter integer W = 8,
    parameter integer PS = 2,
    parameter integer PR = 2,
    parameter integer DEPTH = 9
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         o_v,
    output wire [W-1:0] o_d,
    input  wire         i_ret
);
    localparam integer CW = $clog2(DEPTH + 1);
    reg  [CW-1:0] cred;
    wire          fire = s_valid && s_ready;
    wire          ret;
    assign s_ready = (cred != 0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cred <= DEPTH[CW-1:0];
        else cred <= cred - fire + ret;
    ot_hbm_accel_smv_chain #(.W(1), .D(PS), .RST(1)) u_fv (.clk(clk), .rst_n(rst_n), .d(fire), .q(o_v));
    ot_hbm_accel_smv_chain #(.W(W), .D(PS), .RST(0)) u_fd (.clk(clk), .rst_n(rst_n), .d(s_data), .q(o_d));
    ot_hbm_accel_smv_chain #(.W(1), .D(PR), .RST(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(i_ret), .q(ret));
endmodule

module ot_hbm_accel_smh_csnk #(
    parameter integer W = 8,
    parameter integer PK = 1,
    parameter integer PRK = 1,
    parameter integer DEPTH = 9,
    parameter integer FASTV = 0     // hbm-blocks 2026-10-07: 1 = m_valid (cnt != 0) and the two head-landing pointer
                                    //    compares (wp == rp, wp == rp1) held in flops computed from the next state:
                                    //    front_s m3f u_rch.cnt -> head +7.36 ps / 9 levels; same behaviour, 0 cycles
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         i_v,
    input  wire [W-1:0] i_d,
    output wire         o_ret,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    localparam integer CW = $clog2(DEPTH + 1);
    localparam integer AW = (DEPTH <= 1) ? 1 : $clog2(DEPTH);
    wire          f_v;
    wire [W-1:0]  f_d;
    ot_hbm_accel_smv_chain #(.W(1), .D(PK), .RST(1)) u_fv (.clk(clk), .rst_n(rst_n), .d(i_v), .q(f_v));
    ot_hbm_accel_smv_chain #(.W(W), .D(PK), .RST(0)) u_fd (.clk(clk), .rst_n(rst_n), .d(i_d), .q(f_d));
    reg  [W-1:0]  mem [0:DEPTH-1];
    reg  [AW-1:0] wp, rp, rp1;
    reg  [CW-1:0] cnt;
    reg  [W-1:0]  head;
    wire          pop = m_valid && m_ready;
    assign m_data = head;
    wire [AW-1:0] wp1 = (wp == DEPTH - 1) ? {AW{1'b0}} : wp + 1'b1;
    wire [AW-1:0] rp2 = (rp1 == DEPTH - 1) ? {AW{1'b0}} : rp1 + 1'b1;
    wire          land_head;
    generate if (FASTV >= 2) begin : g_fv2
        // FASTV 2 (m3i): every compare precomputed from registers, f_v / pop only select among them (one mux level
        // after the face-landed f_v: m3g front_s f_v -> e0 +2.13 ps / 5 levels after a long face wire)
        reg mv, e0, e1;
        wire [AW-1:0] rp2_ = rp2;
        wire eq_w_r = (wp == rp), eq_w_r1 = (wp == rp1), eq_w_r2 = (wp == rp2_);
        wire eq_w1_r = (wp1 == rp), eq_w1_r1 = (wp1 == rp1), eq_w1_r2 = (wp1 == rp2_);
        wire ne1 = (cnt != 1);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin mv <= 1'b0; e0 <= 1'b1; e1 <= (DEPTH == 1); end
            else begin
                case ({f_v, pop})
                    2'b00: begin mv <= mv;  e0 <= eq_w_r;   e1 <= eq_w_r1;  end
                    2'b01: begin mv <= ne1; e0 <= eq_w_r1;  e1 <= eq_w_r2;  end
                    2'b10: begin mv <= 1'b1; e0 <= eq_w1_r;  e1 <= eq_w1_r1; end
                    default: begin mv <= mv; e0 <= eq_w1_r1; e1 <= eq_w1_r2; end
                endcase
            end
        assign m_valid = mv;
        assign land_head = f_v && (pop ? e1 : e0);
    end else if (FASTV != 0) begin : g_fv
        reg mv, e0, e1;
        wire [CW-1:0] cnt_n = cnt + f_v - pop;
        wire [AW-1:0] wp_n  = f_v ? wp1 : wp;
        wire [AW-1:0] rp_n  = pop ? rp1 : rp;
        wire [AW-1:0] rp1_n = pop ? rp2 : rp1;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin mv <= 1'b0; e0 <= 1'b1; e1 <= (DEPTH == 1); end
            else begin mv <= (cnt_n != 0); e0 <= (wp_n == rp_n); e1 <= (wp_n == rp1_n); end
        assign m_valid = mv;
        assign land_head = f_v && (pop ? e1 : e0);
    end else begin : g_sv
        assign m_valid = (cnt != 0);
        assign land_head = f_v && (pop ? (wp == rp1) : (wp == rp));
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; rp1 <= (DEPTH == 1) ? {AW{1'b0}} : 1; cnt <= 0; end
        else begin
            if (f_v) wp <= wp1;
            if (pop) begin rp <= rp1; rp1 <= rp2; end
            cnt <= cnt + f_v - pop;
        end
    always @(posedge clk) begin
        if (f_v) mem[wp] <= f_d;
        if (land_head) head <= f_d;
        else if (pop) head <= mem[rp1];
    end
    ot_hbm_accel_smv_chain #(.W(1), .D(PRK), .RST(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(pop), .q(o_ret));
endmodule

// csrc with a REGISTERED element-pin input (margin m3b): the pin's valid and data land in flops with no logic
// (front_s c2 route: d_valid -> fire -> credit adder -113 ps; the element pins keep only ~190 ps after the W13 die
// budget).  The transfer the source saw at the pin (valid AND the ready it presented) is known one edge later, so the
// ready it presents reserves the one unaccounted transfer: s_ready = (cred >= 2), and the channel carries one credit
// more (DEPTH + 1 at both halves) for the same rate.  The landing flops are the first forward stage: the latency to the
// face is unchanged.
module ot_hbm_accel_smh_csrc_r #(
    parameter integer W = 8,
    parameter integer PS = 2,
    parameter integer PR = 2,
    parameter integer DEPTH = 10
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         o_v,
    output wire [W-1:0] o_d,
    input  wire         i_ret
);
    localparam integer CW = $clog2(DEPTH + 1);
    reg  [CW-1:0] cred;
    reg           vq, rq;
    reg  [W-1:0]  dq;
    wire          ret;
    wire          fire_q = vq && rq;
    assign s_ready = (cred >= 2);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cred <= DEPTH[CW-1:0]; vq <= 1'b0; rq <= 1'b0; end
        else begin vq <= s_valid; rq <= s_ready; cred <= cred - fire_q + ret; end
    always @(posedge clk) dq <= s_data;
    ot_hbm_accel_smv_chain #(.W(1), .D(PS - 1), .RST(1)) u_fv (.clk(clk), .rst_n(rst_n), .d(fire_q), .q(o_v));
    ot_hbm_accel_smv_chain #(.W(W), .D(PS - 1), .RST(0)) u_fd (.clk(clk), .rst_n(rst_n), .d(dq), .q(o_d));
    ot_hbm_accel_smv_chain #(.W(1), .D(PR), .RST(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(i_ret), .q(ret));
endmodule

// The request skid at the element pins (margin m3b), replacing ot_hbm_accel_smh_skid there: a 4-entry queue whose
// read pointer is the only state the pin's ready touches (rp <= ready ? rp + 1 : rp, one mux level, 3 flops beside
// the pin); the data leaves through a 4:1 select on rp (output path).  The write side sees the read pointer one edge
// late (rpq), so its room is conservative by at most one entry.  front_s c2: req_ready -> pop -> 84 head / tail
// enables -184 ps.  Same order and data, one transfer a cycle, +1 cycle from s to m as before.
module ot_hbm_accel_smh_oskid #(
    parameter integer W = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    reg [2:0]   wp, rp, rpq;
    reg [W-1:0] mem [0:3];
    wire [2:0]  occ_w = wp - rpq;
    assign s_ready = (occ_w != 3'd4);
    assign m_valid = (wp != rp);
    assign m_data = mem[rp[1:0]];
    wire push = s_valid && s_ready;
    wire [2:0] rp1 = rp + 3'd1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 3'd0; rp <= 3'd0; rpq <= 3'd0; end
        else begin
            if (push) wp <= wp + 3'd1;
            rp <= (m_valid && m_ready) ? rp1 : rp;
            rpq <= rp;
        end
    always @(posedge clk) if (push) mem[wp[1:0]] <= s_data;
endmodule

// The request port with READY LATENCY 2 (REQCR = 1, margin m3d; owner-approved credit-style protocol): req_ready lands
// in a flop with no logic (rq) and req_v / req_addr / req_tag leave flops.  A beat is shown in cycle t + 2 only if the
// receiver showed ready in cycle t, so the receiver must take every beat that arrives up to two cycles after it drops
// ready: a 2-entry headroom in its FIFO (the credits of the round trip).  The die's receiver (station hfd_stn_r2) ties
// req_ready to a register and never stalls, which meets this by construction.  front_s m3 / m3b: any logic between
// req_ready and a flop failed (-184 / -75 ps: the hfd_sm sheet leaves 86 ps inside the element on this pin).
// Mutants (negative controls): OT_SMH_MUT_REQOVF shows beats without the permission (receiver overflow),
// OT_SMH_MUT_REQLEAK pops a request every 64 transfers without showing it (a lost credit / request).
module ot_hbm_accel_smh_reqrl #(
    parameter integer W = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    reg         rq, ov;
    reg [W-1:0] od;
`ifdef OT_SMH_MUT_REQOVF
    wire perm = 1'b1;
`else
    wire perm = rq;
`endif
    wire go = s_valid && perm;
`ifdef OT_SMH_MUT_REQLEAK
    reg [5:0] lk;
    always @(posedge clk or negedge rst_n) if (!rst_n) lk <= 6'd0; else if (go) lk <= lk + 6'd1;
    wire drop = (lk == 6'd63);
`else
    wire drop = 1'b0;
`endif
    assign s_ready = perm;
    assign m_valid = ov;
    assign m_data = od;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rq <= 1'b0; ov <= 1'b0; end
        else begin rq <= m_ready; ov <= go && !drop; end
    always @(posedge clk) if (go) od <= s_data;
endmodule

// ot_hbm_accel_smh_skid3 with every handshake PER COPY (margin m3): copy i (0 .. NS-1: the 32-bit slices; NS: the
// source port; NS + 1: the sink port) takes its own s_valid_v[i] / m_ready_v[i] and drives its own s_ready_v[i] /
// m_valid_v[i].  Chained slice to slice, two of these move a wide line with no signal fanning out across it.  All
// copies hold the same state when their inputs are bit-identical copies.  +1 cycle, one transfer a cycle.
module ot_hbm_accel_smh_skid3v #(
    parameter integer W = 8
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire [(W+31)/32+1:0]         s_valid_v,
    output wire [(W+31)/32+1:0]         s_ready_v,
    input  wire [W-1:0]                 s_data,
    output wire [(W+31)/32+1:0]         m_valid_v,
    input  wire [(W+31)/32+1:0]         m_ready_v,
    output wire [W-1:0]                 m_data
);
    localparam integer NS = (W + 31) / 32;
    genvar i;
    generate for (i = 0; i < NS + 2; i = i + 1) begin : g_c
        wire [3:0] st;                         // {cnt[1:0], wp, rp}
        wire [1:0] c = st[3:2];
        wire wp = st[1], rp = st[0];
        wire pu = s_valid_v[i] && (c != 2'd2);
        wire po = (c != 2'd0) && m_ready_v[i];
        assign s_ready_v[i] = (c != 2'd2);
        assign m_valid_v[i] = (c != 2'd0);
        ot_hbm_accel_bc_kreg #(.W(4), .RV(4'd0)) u (.clk(clk), .rst_n(rst_n),
            .d({c + {1'b0, pu} - {1'b0, po}, pu ? ~wp : wp, po ? ~rp : rp}), .q(st));
        if (i < NS) begin : g_d
            localparam integer LO = 32 * i;
            localparam integer WB = (W - LO < 32) ? W - LO : 32;
            reg [WB-1:0] e0, e1;
            always @(posedge clk) begin
                if (pu && !wp) e0 <= s_data[LO +: WB];
                if (pu && wp)  e1 <= s_data[LO +: WB];
            end
            assign m_data[LO +: WB] = rp ? e1 : e0;
        end
    end endgenerate
endmodule

// ---------------------------------------------------------------------------
// The front (margin m3): ot_hbm_accel_sm_pq's pins, channels, bulk copy, pipelined issue and s1, cut into three
// hardened STRIPS stacked north to south, each <= 0.52 mm tall and 0.432 mm wide, every face register-to-register
// (front_m2d: post-CTS -709 ps, GRT overflow 83 as one 432 x 1115 um piece):
//   front_n (top, 354 um):    the north element pins (op channel source with its credits AT the pins, x-write landing
//                             and decode, barrier), tile row 0's row-0 bundle and x-write bundle outputs;
//   front_c (middle, 518 um): ring + bulk copy, the line stream (two per-slice skids), issue, s1, hops H / H2,
//                             unpack, the row bundles of rows 1 and 2, tile row 1's x-write bundle;
//   front_s (bottom, 242 um): the south element pins (descriptor channel source and request channel sink + skid at
//                             the pins, response chain), the results (lane landing, deskew, pin chains), row 3.
// Faces: credit channels split into source / sink halves (csrc / csnk, the same P stages), push chains split, one
// copy of a crossing row bundle (the two sides' copies are bit-identical).
// Cycles against m2 (latency only; one issue a cycle and every loop unchanged):
//   row bundles +1 on every row (rows 0 / 3: a landing at the far face; rows 1 / 2: one pad register, so the four
//   rows stay aligned for the column back end); tile row 1's x write +1 (its landing at front_c's north face), tile
//   row 0's x write +0: no write is later relative to its reads, so the write-before-read margin is kept (or grows);
//   line stream +1 (u_sk0); release_in -> issue +1, busy / arrive / released -> pins +1; op, descriptor, request,
//   response and retire chains unchanged (their stages sit at the faces).
// The tile adds +1 on both its x-store read and write (macro-input registers).
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_front_n #(
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
    // tile row 0: row 0's bundle and the x-write bundle, west (l) and east (r)
    output wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] rout_l0, rout_r0,
    output wire [1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048-1:0] bout_l0, bout_r0,
    // south face (to front_c)
    output wire                    fs_v,
    output wire [$clog2(RMAX)+1+16+8+1+2+$clog2(XD)-1:0] fs_d,
    input  wire                    fs_ret,
    output wire [1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048-1:0] fx_b,
    output wire                    fr_rl,
    input  wire [6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD)-1:0] fi_row0,
    input  wire [2:0]              fi_pbz
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
    localparam integer RBW   = CW + WSW + 1 + XW;
    localparam integer BBW   = 1 + XW + NBEAT + 2048;
    localparam integer OPW   = (RW + 1) + 16 + 8 + 1 + 2;
    localparam integer PIH   = PIO + 1;
    localparam integer CHD   = 2 * PIH + 3;
    localparam integer OPX   = OPW + XW;
    initial if (SUB != 4 || RPT != 2) $fatal(1, "ot_hbm_accel_smh_front_n: the three-strip front assumes SUB 4, RPT 2");
    // op channel source: credits and the first stage at the pins, the second stage at the south face
    ot_hbm_accel_smh_csrc_r #(.W(OPX), .PS(PIH - 1), .PR(PIH - 1), .DEPTH(CHD + 1)) u_sch (.clk(clk), .rst_n(rst_n),
        .s_valid(start), .s_ready(start_ready), .s_data({op_rows, op_c, op_g, op_gs, op_fmt, op_xb}),
        .o_v(fs_v), .o_d(fs_d), .i_ret(fs_ret));
    // barrier: release_in landed at its pin, launched at the face; busy / arrive / released landed at the face,
    // launched at their pins (+1 each against m2's PIO chains)
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prl (.clk(clk), .rst_n(rst_n), .d(release_in), .q(fr_rl));
    ot_hbm_accel_smv_chain #(.W(3), .D(PIO), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n), .d(fi_pbz),
        .q({busy, arrive, released}));
    // ---------------- x-write beat at the pins (sm_pq's w0): wl, wm, w0 as in m2 ----------------
    reg              w0_en;
    reg [XW-1:0]     w0_addr;
    reg [NBEAT-1:0]  w0_oh;
    reg [2047:0]     w0_data;
    integer gq;
    reg              wl_en, wm_en;
    reg [XW-1:0]     wl_addr, wm_addr;
    reg [6:0]        wl_grp, wm_grp;
    reg [2047:0]     wl_data, wm_data;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wl_en <= 1'b0; wm_en <= 1'b0; w0_en <= 1'b0; end
        else begin wl_en <= xw_en; wm_en <= wl_en; w0_en <= wm_en; end
    always @(posedge clk) begin
        wl_addr <= xw_addr; wl_grp <= xw_grp; wl_data <= xw_data;
        wm_addr <= wl_addr; wm_grp <= wl_grp; wm_data <= wl_data;
        w0_addr <= wm_addr; w0_data <= wm_data;
        for (gq = 0; gq < NBEAT; gq = gq + 1) w0_oh[gq] <= (wm_grp == gq);
    end
    wire [BBW-1:0] w0_b = {w0_en, w0_addr, w0_oh, w0_data};
    // tile row 1's beat: its m2 A stage, launched at the south face
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_fxv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-1]),
        .q(fx_b[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_fxd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
        .q(fx_b[BBW-2:0]));
    // tile row 0's beat: A, M, O per side (m2)
    genvar sd;
    wire [2*BBW-1:0] o_b;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_side
        wire [BBW-1:0] a_b, m_b;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bav (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-1]),
            .q(a_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bad (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
            .q(a_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bmv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(a_b[BBW-1]),
            .q(m_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bmd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(a_b[BBW-2:0]),
            .q(m_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bov (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-1]),
            .q(o_b[sd*BBW + BBW - 1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bod (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-2:0]),
            .q(o_b[sd*BBW +: BBW-1]));
    end endgenerate
    assign bout_l0 = o_b[0 +: BBW];
    assign bout_r0 = o_b[BBW +: BBW];
    // row 0's bundle: landed in one copy PER SIDE (hbm-blocks 2026-10-07: m3f u_rl -> u_ol -108.56 ps / 5 levels, one
    // south-face copy feeding both edge registers; each copy now sits between the face and its side, 0 cycles), then
    // the O register per side at its pins
    wire [RBW-1:0] r0l_l, r0l_r;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW), .K(1)) u_rl (.clk(clk), .rst_n(rst_n),
        .d(fi_row0), .q(r0l_l));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW), .K(1)) u_rr (.clk(clk), .rst_n(rst_n),
        .d(fi_row0), .q(r0l_r));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_ol (.clk(clk), .rst_n(rst_n),
        .d(r0l_l), .q(rout_l0));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_or (.clk(clk), .rst_n(rst_n),
        .d(r0l_r), .q(rout_r0));
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
        ot_hbm_accel_int8_line #(.PIPE(PIPE_INT8)) u_unpack (.clk(clk), .rst_n(rst_n), .busy(a_busy),
            .int8_mode(fmt3), .s_valid(w_valid && demand && !byp), .s_ready(unpack_ready), .s_data(w_data),
            .m_valid(a_v), .m_ready(issue_w_ready && !byp), .m_data(a_d));
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
endmodule

module ot_hbm_accel_smh_front_s #(
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
    parameter integer REQCR = 1
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
    // north face (front_c)
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
    localparam integer SW    = $clog2(IL);
    localparam integer RW    = $clog2(RMAX);
    localparam integer XW    = $clog2(XD);
    localparam integer TAGW  = RW + 1 + SW;
    localparam integer WSW   = LBS * 256 + LBS * 10 + LSB * 16;
    localparam integer CW    = 6 + TAGW;
    localparam integer RBW   = CW + WSW + 1 + XW;
    localparam integer QLW   = 2 + 32 + RW;
    localparam integer NL    = NC / 2;
    localparam integer NR    = NC - NL;
    localparam integer NH    = (NL > NR) ? NL : NR;
    localparam integer PIH   = PIO + 1;
    localparam integer CHD   = 2 * PIH + 3;
    initial if (SUB != 4 || RPT != 2) $fatal(1, "ot_hbm_accel_smh_front_s: the three-strip front assumes SUB 4, RPT 2");
    // descriptor channel source: credits and the first stage at the pins, the second at the north face
    ot_hbm_accel_smh_csrc_r #(.W(56), .PS(PIH - 1), .PR(PIH - 1), .DEPTH(CHD + 1)) u_dch (.clk(clk), .rst_n(rst_n),
        .s_valid(d_valid), .s_ready(d_ready), .s_data({d_base, d_lines}), .o_v(fd_v), .o_d(fd_d), .i_ret(fd_ret));
    // request channel sink (landing at the north face) and m2's registered skid beside the pins
    wire o_req_v, o_req_ready; wire [41:0] o_req_d;
`ifdef OT_SMH_RCH_NONEMPTY
    // Explicit opt-in: protected cached occupancy; physical closure gates pending.
    wire rch_state_fault;
    ot_hbm_accel_smh_csnk_ne #(.W(42), .PK(1), .PRK(PIH - 1), .DEPTH(CHD)) u_rch (.clk(clk), .rst_n(rst_n),
        .state_fault(rch_state_fault),
`else
    ot_hbm_accel_smh_csnk #(.W(42), .PK(1), .PRK(PIH - 1), .DEPTH(CHD), .FASTV(2)) u_rch (.clk(clk), .rst_n(rst_n),
`endif
        .i_v(fq_v), .i_d(fq_d), .o_ret(fq_ret), .m_valid(o_req_v), .m_ready(o_req_ready), .m_data(o_req_d));
    generate if (REQCR != 0) begin : g_rc
        ot_hbm_accel_smh_reqrl #(.W(42)) u_rsk (.clk(clk), .rst_n(rst_n), .s_valid(o_req_v), .s_ready(o_req_ready),
            .s_data(o_req_d), .m_valid(req_v), .m_ready(req_ready), .m_data({req_addr, req_tag}));
    end else begin : g_rs
        ot_hbm_accel_smh_oskid #(.W(42)) u_rsk (.clk(clk), .rst_n(rst_n), .s_valid(o_req_v), .s_ready(o_req_ready),
            .s_data(o_req_d), .m_valid(req_v), .m_ready(req_ready), .m_data({req_addr, req_tag}));
    end endgenerate
    // response: stages 1 (pins) and 2 (north face) of m2's four
    ot_hbm_accel_smv_chain #(.W(1), .D(2), .RST(1)) u_prv (.clk(clk), .rst_n(rst_n), .d(rsp_v), .q(fp_v));
    ot_hbm_accel_smv_chain #(.W(1098), .D(2), .RST(0)) u_prd (.clk(clk), .rst_n(rst_n), .d({rsp_tag, rsp_data}),
        .q(fp_d));
    // row 3's bundle: landed at the north face, O per side at its pins
    wire [RBW-1:0] r3l;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl (.clk(clk), .rst_n(rst_n),
        .d(fi_row3), .q(r3l));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_ol (.clk(clk), .rst_n(rst_n),
        .d(r3l), .q(rout_l3));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_or (.clk(clk), .rst_n(rst_n),
        .d(r3l), .q(rout_r3));
    // ---------------- results: lane landing, deskew, pins (m2, unchanged) ----------------
    wire [NC*QLW-1:0] al;
    genvar ln, sd;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_qs
        for (ln = 0; ln < NH; ln = ln + 1) begin : g_ln
            localparam integer COLN = (sd == 0) ? NL - 1 - ln : NL + ln;
            if (COLN >= 0 && COLN < NC && ((sd == 0 && ln < NL) || (sd == 1 && ln < NR))) begin : g_use
                wire [QLW-1:0] lin = (sd == 0) ? qin_l[ln*QLW +: QLW] : qin_r[ln*QLW +: QLW];
                wire [QLW-1:0] land;
                ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_lv (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(lin[QLW-1 -: 2]), .q(land[QLW-1 -: 2]));
                ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_ld (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(lin[QLW-3:0]), .q(land[QLW-3:0]));
                ot_hbm_accel_smv_chain #(.W(2), .D(5*(NH-1-ln)), .RST(1)) u_dv (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-1 -: 2]), .q(al[COLN*QLW + QLW - 2 +: 2]));
                ot_hbm_accel_smv_chain #(.W(QLW-2), .D(5*(NH-1-ln)), .RST(0)) u_dd (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-3:0]), .q(al[COLN*QLW +: QLW-2]));
            end
        end
    end endgenerate
    wire [NC-1:0]    cf_a;
    wire [NC*32-1:0] cy_a;
    genvar cc;
    generate for (cc = 0; cc < NC; cc = cc + 1) begin : g_al
        assign cf_a[cc] = al[cc*QLW + QLW - 2];
        assign cy_a[32*cc +: 32] = al[cc*QLW + RW +: 32];
    end endgenerate
    // retire: stage 1 of m2's three, at the north face (front_c lands it and adds the third beside the issue)
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_sv (.clk(clk), .rst_n(rst_n), .d(al[QLW - 1]), .q(fsv));
    reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0;
        else fault_q <= fault_q | (|cf_a)
`ifdef OT_SMH_RCH_NONEMPTY
            | rch_state_fault
`endif
            ;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d(al[QLW - 1]), .q(rv));
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_pfo (.clk(clk), .rst_n(rst_n), .d(fault_q), .q(fault));
    ot_hbm_accel_smv_chain #(.W(RW + NC*32), .D(PIO), .RST(0)) u_prd_o (.clk(clk), .rst_n(rst_n),
        .d({al[RW-1:0], cy_a}), .q({rrow, rdata}));
endmodule

// A bundle register {valids (NV, reset), data}: the row bundle's c valids (top NV bits) and x_ce (bit X) reset.
module ot_hbm_accel_smh_bundle_reg #(
    parameter integer W = 8,
    parameter integer V = 4,        // bits below the NV top valids that are data (c's non-valid part, w ...)
    parameter integer NV = 2,
    parameter integer X = 7,        // x_ce sits at bit X (above the X-bit x address)
    parameter integer K = 0         // 1: kept flops (a deliberate duplicate of another bundle register)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (K != 0) begin : g_k
        ot_hbm_accel_smh_kregk #(.W(NV), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .d(d[W-1 -: NV]), .q(q[W-1 -: NV]));
        ot_hbm_accel_smh_kregk #(.W(W-NV-X-1)) u_d (.clk(clk), .rst_n(rst_n), .d(d[W-NV-1:X+1]), .q(q[W-NV-1:X+1]));
        ot_hbm_accel_smh_kregk #(.W(1), .RST(1)) u_x (.clk(clk), .rst_n(rst_n), .d(d[X]), .q(q[X]));
        ot_hbm_accel_smh_kregk #(.W(X)) u_a (.clk(clk), .rst_n(rst_n), .d(d[X-1:0]), .q(q[X-1:0]));
    end else begin : g_p
    ot_hbm_accel_smh_kreg #(.W(NV), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[W-1 -: NV]),
        .q(q[W-1 -: NV]));
    ot_hbm_accel_smh_kreg #(.W(W-NV-X-1)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[W-NV-1:X+1]),
        .q(q[W-NV-1:X+1]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_x (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[X]), .q(q[X]));
    ot_hbm_accel_smh_kreg #(.W(X)) u_a (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[X-1:0]), .q(q[X-1:0]));
    end endgenerate
endmodule

// ---------------------------------------------------------------------------
// One tile (identical everywhere): RPT leaves of one column (rows p*RPT .. p*RPT+RPT-1) sharing the x-write bundle.
// Relative to the landing edge L (the row bundles' flops; = sm_pq's L2):
//   L     rin / bin landed (and driven on to the next tile from these flops); gin landed into gout[RPT..]
//   L+1   E3: c3, w3; x-store read latched (address from L); x-write rotation stage W1
//   L+2   x-write data / masks / enables registered (W2), written at L+3
//   L+2   E4 (the column logic's input registers, ot_gpu_sm_v stage 2)
//   ...   G1 (gout[0..RPT-1], lane k = row p*RPT + RPT-1-k): the column result selected by the producing column's
//         valid (sm_pq fix)
// x-write: a leaf's block-dot field is beat bits [a1, a1 + LBS*266) of beat g1 (wrapping into g1 + 1), its BF16
// field [a2, a2 + LSB*16) of beat g2; a1 / a2 / g1 / g2 are straps (tie cells in the parent).  The data is the beat
// rotated by the strap (a shifter on a constant select), the per-bit mask the beat's one-hot at g1 or g1 + 1 by a
// strap thermometer; both registered (sm_pq's leaf registered the beat and masked combinationally into the macros).
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_tile #(
    parameter integer SUB = 4,
    parameter integer RPT = 2,
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer NC  = 8,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 13,
    parameter integer TCK = 1,
    parameter integer NMG = 32,             // mask bits per one-hot replica
    parameter integer A1B = 9,              // strap bits of the block-dot field offset (its low 11 - A1B bits are 0)
    parameter integer A2B = 7,              // strap bits of the BF16 field offset
    parameter integer PT4 = 1               // hbm-blocks 2026-10-07 (m3h): a FOURTH pass-through register on the x-write beat
                                            //   and on every row bundle (m3f tile_w: u_bldm -> u_bld2 -44.13 / u_bld -> u_bldm
                                            //   -42.11 / u_rpm -> u_rp2 -27.24, 4-5 levels of wire): +1 per tile hop on both
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [RPT*A1B-1:0]       xs_a1,
    input  wire [RPT*5-1:0]         xs_g1,
    input  wire [RPT*A2B-1:0]       xs_a2,
    input  wire [RPT*5-1:0]         xs_g2,
    input  wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rin,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bin,
    output wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rout,
    output wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bout,
    input  wire [(SUB-RPT)*(2+32+TAGW)-1:0]                    gin,
    output wire [SUB*(2+32+TAGW)-1:0]                          gout
);
    localparam integer SLW = LBS * 266 + LSB * 16;
    localparam integer WSW = SLW;
    localparam integer XW  = $clog2(XD);
    localparam integer CW  = 6 + TAGW;
    localparam integer RBW = CW + WSW + 1 + XW;
    localparam integer BBW = 1 + XW + NBEAT + 2048;
    localparam integer GLW = 2 + 32 + TAGW;
    localparam integer NG  = (LBS * 266 + NMG - 1) / NMG + (LSB * 16 + NMG - 1) / NMG;   // mask groups per leaf
    // ---- landing: the x-write bundle (driven on to the next tile from these flops) ----
    // the x-write bundle lands in a pass-through copy (driven on to the next tile) and one copy per leaf (the leaf's
    // rotator), so neither spans the tile; the copies are bit-identical kept registers
    wire [BBW-1:0] bl;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[BBW-1]),
        .q(bl[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bld (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[BBW-2:0]), .q(bl[BBW-2:0]));
    // (margin m2) the pass-through copy lands at the input pins and launches from a second register at the output
    // pins (+1 per tile hop on the x-write beat, matched by the row bundles' +1 per hop: the margin is unchanged)
    // (margin m3e) a third pass-through register mid-tile (tile_e c2: u_bld -> u_bld2 -10.6 ps across the tile): +1 per
    // tile hop on the x-write beat, matched by the row bundles' third register (rpm), so the margin is unchanged
    wire [BBW-1:0] bm, bm4;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blvm (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bl[BBW-1]), .q(bm[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bldm (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bl[BBW-2:0]), .q(bm[BBW-2:0]));
    generate if (PT4 != 0) begin : g_pt4b
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blvn (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bm[BBW-1]), .q(bm4[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bldn (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bm[BBW-2:0]), .q(bm4[BBW-2:0]));
    end else begin : g_pt3b
        assign bm4 = bm;
    end endgenerate
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bm4[BBW-1]),
        .q(bout[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bld2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bm4[BBW-2:0]), .q(bout[BBW-2:0]));
    genvar j, ln;
    generate for (j = 0; j < RPT; j = j + 1) begin : g_lf
        // the row bundle of row j (landed, driven on)
        // the row bundle lands in a pass-through copy (rout) and the leaf's own copy (kept, bit-identical)
        wire [RBW-1:0] rl, rl1, rp, rpm, rpm4;
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp (.clk(clk), .rst_n(rst_n),
            .d(rin[j*RBW +: RBW]), .q(rp));
        // (margin m2) landing at the input pins (u_rp), launch from a register at the output pins; (m3e) a third
        // register mid-tile (u_rpm, rp -> rp2 was +0.8 ps): 3 per hop, in step with the x-write beat
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rpm (.clk(clk), .rst_n(rst_n),
            .d(rp), .q(rpm));
        if (PT4 != 0) begin : g_pt4r
            ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rpn (.clk(clk), .rst_n(rst_n),
                .d(rpm), .q(rpm4));
        end else begin : g_pt3r
            assign rpm4 = rpm;
        end
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp2 (.clk(clk), .rst_n(rst_n),
            .d(rpm4), .q(rout[j*RBW +: RBW]));
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl (.clk(clk), .rst_n(rst_n),
            .d(rin[j*RBW +: RBW]), .q(rl1));
        // (m3e) the leaf's row copy one register deeper (+1 on every read), matching the x-write copy's bk2 below
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl2 (.clk(clk), .rst_n(rst_n),
            .d(rl1), .q(rl));
        wire [BBW-1:0] bk, bk1;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[BBW-1]),
            .q(bk1[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[BBW-2:0]),
            .q(bk1[BBW-2:0]));
        // (m3e) the leaf's x-write copy registered again inside the leaf before the strap rotation (tile_e c2: the
        // pin landing u_bkd -> 8:1 rotation -> bf0 / blk0 -92 / -84 ps, 10-12 levels): +1 on the write, matched above
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bk1[BBW-1]),
            .q(bk[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bk1[BBW-2:0]),
            .q(bk[BBW-2:0]));
        // one-hot beat group replicas for this leaf's masks (landed straight from the pins, NG copies)
        // (round 5) the beat one-hot lands once per leaf (kept, beside the pins), its NG replicas load one edge later,
        // in step with the leaf's two-stage rotation
        wire [NG*NBEAT-1:0] ohr;
        wire [NBEAT-1:0] ohl, ohl1;
        ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohl (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[2048 +: NBEAT]),
            .q(ohl1));
        ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohl2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(ohl1), .q(ohl));   // (m3e) +1 with bk2
        genvar gi;
        for (gi = 0; gi < NG; gi = gi + 1) begin : g_ohr
            ot_hbm_accel_smh_kreg #(.W(NBEAT)) u (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(ohl),
                .q(ohr[gi*NBEAT +: NBEAT]));
        end
        wire gv, gf; wire [31:0] gy; wire [TAGW-1:0] gt;
        ot_hbm_accel_smh_leaf #(.LBS(LBS), .LSB(LSB), .IL(IL), .TAGW(TAGW), .XD(XD), .NBEAT(NBEAT), .TCK(TCK),
                                .NMG(NMG), .A1B(A1B), .A2B(A2B)) u_leaf (
            .clk(clk), .rst_n(rst_n), .xs_a1(xs_a1[j*A1B +: A1B]), .xs_g1(xs_g1[j*5 +: 5]),
            .xs_a2(xs_a2[j*A2B +: A2B]), .xs_g2(xs_g2[j*5 +: 5]),
            .c_l(rl[RBW-1 -: CW]), .w_l(rl[XW+1 +: WSW]), .x_ce(rl[XW]), .x_a(rl[XW-1:0]),
            .b_en(bk[BBW-1]), .b_a(bk[BBW-2 -: XW]), .b_d(bk[2047:0]), .ohr(ohr),
            .gv(gv), .gf(gf), .gy(gy), .gt(gt));
        // own rows on lanes 0..RPT-1 (lane RPT-1-j = row j): (margin m2) G1 then a launch register at the gout pins
        // (+1 on every gather lane alike: the back end's deskew is unchanged)
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_gov (.clk(clk), .rst_n(rst_n), .en(1'b1), .d({gv, gf}),
            .q(gout[(RPT-1-j)*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_god (.clk(clk), .rst_n(rst_n), .en(1'b1), .d({gy, gt}),
            .q(gout[(RPT-1-j)*GLW +: GLW-2]));
    end
    // lanes from the tile above moved down one
    // pass-through G1 lanes: two registers across the 510 um tile (landing, then launch), the back end's
    // deskew accounts for 2 per tile hop
    for (ln = RPT; ln < SUB; ln = ln + 1) begin : g_gl
        wire [GLW-1:0] gm;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(gin[(ln-RPT)*GLW + GLW - 2 +: 2]), .q(gm[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(gin[(ln-RPT)*GLW +: GLW-2]), .q(gm[0 +: GLW-2]));
        wire [GLW-1:0] gn;                    // (round 5) a third register: 510 um is more than two spans
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v2 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(gm[GLW-2 +: 2]), .q(gn[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d2 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(gm[0 +: GLW-2]), .q(gn[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v3 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(gn[GLW-2 +: 2]), .q(gout[ln*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d3 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(gn[0 +: GLW-2]), .q(gout[ln*GLW +: GLW-2]));
    end endgenerate
endmodule

// One leaf inside a tile (not hardened on its own): sm_pq's leaf (E3, x store, E4, the two columns, G1 by the
// producing column) fed from the tile's landing flops, with the strap-mapped, registered x write.
module ot_hbm_accel_smh_leaf #(
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 13,
    parameter integer TCK = 1,
    parameter integer NMG = 32,
    parameter integer A1B = 9,
    parameter integer A2B = 7
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [A1B-1:0]           xs_a1,
    input  wire [4:0]               xs_g1,
    input  wire [A2B-1:0]           xs_a2,
    input  wire [4:0]               xs_g2,
    input  wire [6+TAGW-1:0]        c_l,
    input  wire [LBS*266+LSB*16-1:0] w_l,
    input  wire                     x_ce,
    input  wire [$clog2(XD)-1:0]    x_a,
    input  wire                     b_en,
    input  wire [$clog2(XD)-1:0]    b_a,
    input  wire [2047:0]            b_d,
    input  wire [((LBS*266+NMG-1)/NMG+(LSB*16+NMG-1)/NMG)*NBEAT-1:0] ohr,
    output wire                     gv,
    output wire                     gf,
    output wire [31:0]              gy,
    output wire [TAGW-1:0]          gt
);
    localparam integer SLW = LBS * 266 + LSB * 16;
    localparam integer WSW = SLW;
    localparam integer NXL = (SLW + 255) / 256;
    localparam integer XW  = $clog2(XD);
    localparam integer CW  = 6 + TAGW;
    localparam integer G1S = 11 - A1B;
    localparam integer G2S = 11 - A2B;
    // ---- (round 5) R0: the landed row bundle registered once more inside the leaf (+1 cycle on every read,
    // matched by the x write's split rotation below: the write-before-read margin is unchanged) ----
    reg  [1:0]     r0v;
    reg            r0x;
    reg  [CW-3:0]  r0d;
    reg  [WSW-1:0] r0w;
    reg  [XW-1:0]  r0a;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin r0v <= 2'b00; r0x <= 1'b0; end
        else begin r0v <= c_l[CW-1:CW-2]; r0x <= x_ce; end
    always @(posedge clk) begin r0d <= c_l[CW-3:0]; r0w <= w_l; r0a <= x_a; end
    // ---- E3: line and control (sm_pq leaf) ----
    reg  [1:0]     c3v;
    reg  [CW-3:0]  c3d;
    reg  [WSW-1:0] w3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c3v <= 2'b00;
        else c3v <= r0v;
    always @(posedge clk) begin c3d <= r0d; w3 <= r0w; end
    // (margin m3) E3b: the row pipeline one register deeper, in step with the x-store read address registered once
    // more at the macro pins (r1x / r1a below): +1 cycle on every row read; the x write gets the same +1 at the macro
    // inputs (wce2 / wa2 / wd2 / wm2), so the write-before-read margin is unchanged
    reg  [1:0]     c3bv;
    reg  [CW-3:0]  c3bd;
    reg  [WSW-1:0] w3b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c3bv <= 2'b00;
        else c3bv <= c3v;
    always @(posedge clk) begin c3bd <= c3d; w3b <= w3; end
    // ---- x write: the slice by strap rotation, masks by strap thermometer; two registered stages ----
    // W1: rotate by the offset's high bits (a[10:6]), latch the beat's one-hot at g / g + 1 per mask group;
    // W2 (= E3 level): rotate by the low bits, per-bit masks, per-macro write enables.  The rotation is a shifter
    // on constant selects split in two (9 mux levels across the 2048-bit beat do not fit one cycle with their wires).
    localparam integer RH = 6;                                   // low bits rotated in W2
    localparam integer NBK = LBS * 266, NBF = LSB * 16;
    wire [10:0]   a1 = {xs_a1, {G1S{1'b0}}};
    wire [10:0]   a2 = {xs_a2, {G2S{1'b0}}};
    wire [4095:0] dd = {b_d, b_d};
    // (round 5) W0: rotate by a[10:8]; W1: by a[7:6]; W2: by a[5:0] (each stage <= 8:1 / 4:1 / 64:1 muxes)
    localparam integer RM = 8;
    wire [4095:0] blk_0 = dd >> {a1[10:RM], {RM{1'b0}}};
    wire [4095:0] bf_0  = dd >> {a2[10:RM], {RM{1'b0}}};
    reg  [NBK+(1<<RM)-2:0] blk0;
    reg  [NBF+(1<<RM)-2:0] bf0;
    reg            we0;
    reg  [XW-1:0]  wa0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) we0 <= 1'b0;
        else we0 <= b_en;
    always @(posedge clk) begin
        blk0 <= blk_0[NBK+(1<<RM)-2:0];
        bf0  <= bf_0[NBF+(1<<RM)-2:0];
        wa0  <= b_a;
    end
    wire [NBK+(1<<RM)-2:0] blk_h = blk0 >> {a1[RM-1:RH], {RH{1'b0}}};
    wire [NBF+(1<<RM)-2:0] bf_h  = bf0 >> {a2[RM-1:RH], {RH{1'b0}}};
    reg  [NBK+(1<<RH)-2:0] blk1;
    reg  [NBF+(1<<RH)-2:0] bf1;
    reg            we1;
    reg  [XW-1:0]  wa1;
    localparam integer NG1 = (NBK + NMG - 1) / NMG;              // mask groups of the block-dot field
    localparam integer NGR = NG1 + (NBF + NMG - 1) / NMG;        // + of the BF16 field (a group is in one field)
    reg  [NGR-1:0] ml1, mh1;                                     // per mask group: beat one-hot at g, at g + 1
    genvar b, m;
    generate for (b = 0; b < NGR; b = b + 1) begin : g_mg
        wire [NBEAT-1:0] oh = ohr[b*NBEAT +: NBEAT];
        wire [4:0] g0 = (b < NG1) ? xs_g1 : xs_g2;
        wire [5:0] g1n = {1'b0, g0} + 6'd1;
        always @(posedge clk) begin
            ml1[b] <= (g0 < NBEAT) ? oh[g0] : 1'b0;
            mh1[b] <= (g1n < NBEAT) ? oh[g1n] : 1'b0;
        end
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) we1 <= 1'b0;
        else we1 <= we0;
    always @(posedge clk) begin
        blk1 <= blk_h[NBK+(1<<RH)-2:0];
        bf1  <= bf_h[NBF+(1<<RH)-2:0];
        wa1  <= wa0;
    end
    wire [NBK+(1<<RH)-2:0] blk_l = blk1 >> a1[RH-1:0];
    wire [NBF+(1<<RH)-2:0] bf_l  = bf1 >> a2[RH-1:0];
    wire [4095:0] blk_c = {{2048{1'b1}}, {2048{1'b0}}} >> a1;    // 1 where the field bit is in beat g1 + 1
    wire [4095:0] bf_c  = {{2048{1'b1}}, {2048{1'b0}}} >> a2;
    wire [SLW-1:0] wd_n = {bf_l[NBF-1:0], blk_l[NBK-1:0]};
    wire [SLW-1:0] car  = {bf_c[NBF-1:0], blk_c[NBK-1:0]};
    reg  [SLW-1:0] wd_q, wm_q;
    reg            we_q;
    reg  [XW-1:0]  wa_q;
    reg  [NXL-1:0] wce_q;
    wire [SLW-1:0] wm_n;
    generate for (b = 0; b < SLW; b = b + 1) begin : g_wm
        localparam integer GB = (b < NBK) ? b / NMG : NG1 + (b - NBK) / NMG;
        assign wm_n[b] = car[b] ? mh1[GB] : ml1[GB];
    end endgenerate
    wire [NXL*256-1:0] wm_nm = {{(NXL*256-SLW){1'b0}}, wm_n};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) we_q <= 1'b0;
        else we_q <= we1;
    generate for (m = 0; m < NXL; m = m + 1) begin : g_wce
        always @(posedge clk or negedge rst_n)
            if (!rst_n) wce_q[m] <= 1'b0;
            else wce_q[m] <= we1 && (|wm_nm[256*m +: 256]);
    end endgenerate
    always @(posedge clk) begin wa_q <= wa1; wd_q <= wd_n; wm_q <= wm_n; end
    wire [NXL*256-1:0] wd_m = {{(NXL*256-SLW){1'b0}}, wd_q};
    wire [NXL*256-1:0] wm_m = {{(NXL*256-SLW){1'b0}}, wm_q};
    // ---- x store: NXL macros, read from the landed address ----
    wire [NXL*256-1:0] xrd;
    // (margin m3) every macro input leaves a kept register at that macro's pins, one set per macro: tileW_m2d SS -83
    // was wd_q -> 290 ps of wire -> the macro's wd_in (the write data registers sat with the rotator, not the macro)
    generate for (m = 0; m < NXL; m = m + 1) begin : g_xm
        wire          rce2, wce2;
        wire [XW-1:0] ra2, wa2;
        wire [255:0]  wd2, wm2;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_rce (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(r0x), .q(rce2));
        ot_hbm_accel_smh_kreg #(.W(XW)) u_ra (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(r0a), .q(ra2));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_wce (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(wce_q[m]), .q(wce2));
        ot_hbm_accel_smh_kreg #(.W(XW)) u_wa (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(wa_q), .q(wa2));
        ot_hbm_accel_smh_kreg #(.W(256)) u_wd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(wd_m[256*m +: 256]), .q(wd2));
        ot_hbm_accel_smh_kreg #(.W(256)) u_wm (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(wm_m[256*m +: 256]), .q(wm2));
        ot_sram_1r1w_128x256_m1_r2c2 u_x (
            .clk(clk), .r_ce_in(rce2), .r_addr_in(ra2), .rd_out(xrd[256*m +: 256]),
            .w_ce_in(wce2), .w_addr_in(wa2), .wd_in(wd2), .w_mask_in(wm2),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---- E4 ----
    reg              iv_b, iv_f, ifirst, ilast, ifp4;
    reg [TAGW-1:0]   itag;
    reg [WSW-1:0]    iw;
    reg [SLW-1:0]    ix;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv_b <= 1'b0; iv_f <= 1'b0; end
        else begin iv_b <= c3bv[1]; iv_f <= c3bv[0]; end
    end
    always @(posedge clk) begin
        ifirst <= c3bd[CW-3]; ilast <= c3bd[CW-4]; ifp4 <= c3bd[CW-5]; itag <= c3bd[TAGW-1:0];
        iw <= w3b;
        ix <= xrd[SLW-1:0];
    end
    // ---- E5 (margin m1, +1 on both columns): the macro read lands in E4 at the macro pins, then E5 feeds the
    // columns; the x-store read edge and the write-before-read margin are unchanged ----
    reg              jv_b, jv_f, jfirst, jlast, jfp4;
    reg [TAGW-1:0]   jtag;
    reg [WSW-1:0]    jw;
    reg [SLW-1:0]    jx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin jv_b <= 1'b0; jv_f <= 1'b0; end
        else begin jv_b <= iv_b; jv_f <= iv_f; end
    end
    always @(posedge clk) begin
        jfirst <= ifirst; jlast <= ilast; jfp4 <= ifp4; jtag <= itag; jw <= iw; jx <= ix;
    end
    // ---- the column logic (flat in the tile: the modules of the sm_pq leaf's macros) ----
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
`ifdef OT_SMH_MUT_BFDLY
    wire fov_r, ffault_r; wire [31:0] fy_r; wire [TAGW-1:0] ftag_r;
`endif
    wire [LBS*256-1:0] xq_s;
    wire [LBS*10-1:0]  xe_s;
    genvar qq;
    generate for (qq = 0; qq < LBS; qq = qq + 1) begin : g_bx
        assign xq_s[256*qq +: 256] = jx[qq*266 +: 256];
        assign xe_s[10*qq +: 10]   = jx[qq*266 + 256 +: 10];
    end endgenerate
    generate
        if (TCK != 0) begin : g_k
            ot_hbm_accel_smh_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (   // bterm3: +7 cycles
                .clk(clk), .rst_n(rst_n), .v(jv_b), .first(jfirst), .last(jlast), .fp4(jfp4), .tag(jtag),
                .wq(jw[0 +: LBS*256]), .we(jw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
            ot_hbm_accel_smh_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (   // +3 cycles (tile context)
                .clk(clk), .rst_n(rst_n), .v(jv_f), .first(jfirst), .last(jlast), .tag(jtag),
                .w(jw[LBS*266 +: LSB*16]), .x(jx[LBS*266 +: LSB*16]),
`ifdef OT_SMH_MUT_BFDLY
                .ov(fov_r), .y(fy_r), .otag(ftag_r), .fault(ffault_r));
`else
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
`endif
        end else begin : g_o
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(jv_b), .first(jfirst), .last(jlast), .fp4(jfp4), .tag(jtag),
                .wq(jw[0 +: LBS*256]), .we(jw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
            ot_gpu_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(jv_f), .first(jfirst), .last(jlast), .tag(jtag),
                .w(jw[LBS*266 +: LSB*16]), .x(jx[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end
    endgenerate
`ifdef OT_SMH_MUT_BFDLY
    // negative-control mutant only (bench --mut-bfdly; never defined in a build): the BF16 column's output 64 cycles
    // late, so a BF16 -> block-dot op pair can collide at G1 / the stack (with c = 8 lines a row the real pipeline's
    // D difference, <= DBF + 4 SLAT = 39, is below the 57-cycle row span and the retire-order hazard is unreachable)
    wire [1+1+32+TAGW-1:0] mbf;
    ot_hdc_delay #(.W(2+32+TAGW), .D(64), .RESET(1)) u_mbf (.clk(clk), .rst_n(rst_n), .d({fov_r, ffault_r, fy_r, ftag_r}),
        .q(mbf));
    assign {fov, ffault, fy, ftag} = mbf;
`endif
    // ---- G1: select by the producing column (sm_pq), registered: the tile's lane output flops ----
    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= bov | fov; gf_q <= bfault | ffault | (bov & fov); end
    always @(posedge clk) begin
        gy_q <= bov ? by : fy;
        gt_q <= bov ? btag : ftag;
    end
    assign gv = gv_q; assign gf = gf_q; assign gy = gy_q; assign gt = gt_q;
endmodule

// ---------------------------------------------------------------------------
// One column back end.  gin lane k = row SUB-1-k of this column; it left its G1 P(k) = k / RPT flops ago (one per
// tile it passed below its own).  Every lane is landed and waits PM - P(k) more (PM = (SUB-1) / RPT), so all rows
// reach the tree-input flops (= sm_pq's td_in) together, G1 + PM + 1 (sm_pq: G1 + DG + 1 = G1 + 4).  Then sm_pq's
// g_col: tree (row 0's valid and tag lead, the rows' faults OR-ed one cycle later) and stack.  Result lane
// {v, f, y, row}: the stack's output flops on lane 0 (the fault from its own flop), lanes from the farther column
// moved on one.
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_be #(
    parameter integer SUB  = 4,
    parameter integer RPT  = 2,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer TAGW = 16,
    parameter integer NH   = 4,
    parameter integer STK  = 1              // 1: ot_hbm_accel_stack (pending lookup registered, +1 cycle); 0: ot_gpu_stack
) (
    input  wire                              clk,
    input  wire                              rst_n,
    input  wire [SUB*(2+32+TAGW)-1:0]        gin,
    input  wire [(NH-1)*(2+32+$clog2(RMAX))-1:0] qin,
    output wire [NH*(2+32+$clog2(RMAX))-1:0]     qout
);
    localparam integer GLW = 2 + 32 + TAGW;
    localparam integer RW  = $clog2(RMAX);
    localparam integer SW  = $clog2(IL);
    localparam integer QLW = 2 + 32 + RW;
    localparam integer PM  = (SUB - 1) / RPT;
    wire [SUB*GLW-1:0] tl;                 // per row, at the tree-input stage
    genvar k;
    generate for (k = 0; k < SUB; k = k + 1) begin : g_ln
        localparam integer ROW = SUB - 1 - k;
        // a lane from tile hop t = k / RPT has passed 3t pass-through registers: deskew 1 + 3 (PM - t)
        ot_hbm_accel_smv_chain #(.W(2), .D(1 + 3 * (PM - k / RPT)), .RST(1)) u_v (.clk(clk), .rst_n(rst_n),
            .d(gin[k*GLW + GLW - 2 +: 2]), .q(tl[ROW*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smv_chain #(.W(GLW-2), .D(1 + 3 * (PM - k / RPT)), .RST(0)) u_d (.clk(clk), .rst_n(rst_n),
            .d(gin[k*GLW +: GLW-2]), .q(tl[ROW*GLW +: GLW-2]));
    end endgenerate
    wire              tv_in = tl[GLW - 1];                  // row 0's valid
    wire [TAGW-1:0]   tt_in = tl[TAGW-1:0];                 // row 0's tag
    wire [SUB*32-1:0] td_in;
    wire [SUB-1:0]    tf_in;
    genvar sp;
    generate for (sp = 0; sp < SUB; sp = sp + 1) begin : g_td
        assign td_in[32*sp +: 32] = tl[sp*GLW + TAGW +: 32];
        assign tf_in[sp] = tl[sp*GLW + GLW - 2];
    end endgenerate
    reg gfault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) gfault <= 1'b0;
        else gfault <= |tf_in;
    wire tv, tf;
    wire [31:0] ty;
    wire [TAGW-1:0] tt;
    ot_gpu_tree #(.N(SUB), .TAGW(TAGW), .ALAT(7)) u_comb (.clk(clk), .rst_n(rst_n), .v(tv_in), .d(td_in),
                                                          .tag(tt_in), .ov(tv), .y(ty), .otag(tt), .fault(tf));
    wire kv, kf;
    wire [31:0] ky;
    wire [RW-1:0] krow;
    generate if (STK != 0) begin : g_hs
        ot_hbm_accel_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(kv), .y(ky), .otag(krow), .fault(kf));
    end else begin : g_gs
        ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(kv), .y(ky), .otag(krow), .fault(kf));
    end endgenerate
    reg cf_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cf_q <= 1'b0;
        else cf_q <= gfault | tf | kf;
    // (margin m2) the column's own result lane launches from a register at the qout pins (+1 on every result alike)
    ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_q0v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d({kv, cf_q}),
        .q(qout[QLW - 2 +: 2]));
    ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_q0d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d({ky, krow}),
        .q(qout[0 +: QLW - 2]));
    genvar ln;
    // (margin m2) pass lanes land at the qin pins and launch from a second register at the qout pins (+1 per hop)
    generate for (ln = 1; ln < NH; ln = ln + 1) begin : g_q
        wire [QLW-1:0] ql;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(qin[(ln-1)*QLW + QLW - 2 +: 2]), .q(ql[QLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(qin[(ln-1)*QLW +: QLW-2]), .q(ql[0 +: QLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v2 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(ql[QLW - 2 +: 2]), .q(qout[ln*QLW + QLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_d2 (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(ql[0 +: QLW-2]), .q(qout[ln*QLW +: QLW-2]));
    end endgenerate
endmodule

// ---------------------------------------------------------------------------
// Pin-side variants of the hardened tile and back end (production defaults): the same netlist, routed twice with
// the bundle pins on opposite edges, so each needs its own master name in the parent.  _e: row bundles enter west and
// leave east (tiles right of the front) / results leave east (back ends left of the front); _w: the mirror.
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_tile_e (
    input  wire clk, input wire rst_n,
    input  wire [17:0] xs_a1, input wire [9:0] xs_g1, input wire [13:0] xs_a2, input wire [9:0] xs_g2,
    input  wire [1635:0] rin, input wire [2068:0] bin, output wire [1635:0] rout, output wire [2068:0] bout,
    input  wire [99:0] gin, output wire [199:0] gout
);
    ot_hbm_accel_smh_tile u (.*);
endmodule
module ot_hbm_accel_smh_tile_w (
    input  wire clk, input wire rst_n,
    input  wire [17:0] xs_a1, input wire [9:0] xs_g1, input wire [13:0] xs_a2, input wire [9:0] xs_g2,
    input  wire [1635:0] rin, input wire [2068:0] bin, output wire [1635:0] rout, output wire [2068:0] bout,
    input  wire [99:0] gin, output wire [199:0] gout
);
    ot_hbm_accel_smh_tile u (.*);
endmodule
module ot_hbm_accel_smh_be_e (
    input  wire clk, input wire rst_n, input wire [199:0] gin, input wire [137:0] qin, output wire [183:0] qout
);
    ot_hbm_accel_smh_be u (.*);
endmodule
module ot_hbm_accel_smh_be_w (
    input  wire clk, input wire rst_n, input wire [199:0] gin, input wire [137:0] qin, output wire [183:0] qout
);
    ot_hbm_accel_smh_be u (.*);
endmodule
