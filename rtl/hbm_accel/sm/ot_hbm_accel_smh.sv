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

// ======== hbm-smh/fc OT_SMH_FC_HIER: front_c's hardened sub-elements (2026-10-11; physical spec in el1011-hbm-smh.log) ====
// Every child: own ot_rst_relay (2 + 1 release) on the raw port reset, pin flops on inputs, registered outputs.
// Liberty blackboxes carry no parameters: the defaults are the production / candidate (ENABLE_INT8 1, PIPE_INT8 2) build;
// front_c passes parameters in simulation only.
`ifdef OT_SMH_FC_HIER
// [hbm-smh/fc] round 6: fc_bc's first line skid with a REGISTERED N boundary.  Same 2-entry handshake as
// ot_hbm_accel_smh_skid3v per 32-bit slice (s_ready = not full, m_valid = not empty, +1 cycle s -> m, one transfer a
// cycle), but stored as head H + tail T so m_data, m_valid_v and s_ready_v all leave flops (cal3: k0_d = rp ? e1 : e0
// behind the N-face pins, 397 ps of wire, TT -205).  Cycle-identical to skid3v at every port when valid.
module ot_hbm_accel_smh_skid3r #(
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
        wire [3:0] st;                         // {cnt[1:0], m_valid, full} (reset: empty, ready)
        wire [1:0] c = st[3:2];
        wire mv = st[1], sr = !st[0];
        wire pu = s_valid_v[i] && sr;
        wire po = mv && m_ready_v[i];
        wire [1:0] cn = c + {1'b0, pu} - {1'b0, po};
        assign s_ready_v[i] = sr;
        assign m_valid_v[i] = mv;
        ot_hbm_accel_smh_kregk #(.W(4), .RST(1)) u (.clk(clk), .rst_n(rst_n),
            .d({cn, cn != 2'd0, cn == 2'd2}), .q(st));
        if (i < NS) begin : g_d
            localparam integer LO = 32 * i;
            localparam integer WB = (W - LO < 32) ? W - LO : 32;
            reg [WB-1:0] h, t;
            // head: loads when it empties (pop) or the queue was empty; from T when two were held
            wire h_en = (c == 2'd0) ? pu : (po && (c == 2'd2 || pu));
            wire t_en = pu && ((c == 2'd1 && !po) || (c == 2'd2));
            always @(posedge clk) begin
                if (h_en) h <= c[1] ? t : s_data[LO +: WB];
                if (t_en) t <= s_data[LO +: WB];
            end
            assign m_data[LO +: WB] = h;
        end
    end endgenerate
endmodule

// [hbm-smh/fc] round 6: fc_is's INT8 adapter + output queue + format bypass, cut into 34 slices of 32 bits
// (32 x two lanes + two tail slices of bits 1024-1087), each with its own kept control state and its own fmt3 copy, so
// no select / enable net spans the line (cal3 TT -227: pending -> 512-bit codes mux -> classify -> 1088 a_data mux,
// a_capacity / int8_mode on ~1-2k loads).  Both halves are classified at the input; the high half is held classified,
// so the pending select is a registered 2:1 mux.  Behaviour = ot_hbm_accel_int8_line_ob (u_core PIPE 1) + fc_is's
// byp mux, cycle for cycle; data registers load from slice control alone (contents while invalid never reach e0 / e1).
module ot_hbm_accel_smh_fc_i8s (
    input  wire          clk, rst_n,
    input  wire [33:0]   f3_v,                 // fmt3 copies (one per slice), loaded with the op
    input  wire          s_valid,
    output wire          s_ready,
    input  wire [1087:0] s_data,
    output wire          busy, byp,
    output wire          m_valid,
    input  wire          m_ready,
    output wire [1087:0] o_data                // byp ? s_data : queue head
);
    function automatic [15:0] classify(input [7:0] code_in);
        reg [7:0] code, mag;
        reg [2:0] top;
        integer b;
        begin
`ifdef OT_INT8_MUT_SIGN
            code = code_in & 8'h7f;
`else
            code = code_in;
`endif
            mag = code[7] ? (~code + 8'd1) : code;
            top = 0;
            for (b = 0; b < 8; b = b + 1) if (mag[b]) top = b;
            classify = {4'd0, top, code[7], mag};
        end
    endfunction
    function automatic [15:0] encode(input [15:0] field);
        reg [7:0] shifted, exponent;
        begin
            exponent = 8'd127 + field[11:9];
            shifted = field[7:0] << (7 - field[11:9]);
            encode = (field[7:0] == 0) ? 16'd0 : {field[8], exponent, shifted[6:0]};
        end
    endfunction
    genvar g, l;
    generate for (g = 0; g < 34; g = g + 1) begin : g_s
        localparam integer LO = 32 * g;
        wire [7:0] st;                          // {pending, a_valid, a_int8, m_valid, cnt[1:0], wp, rp}
        wire pend = st[7], av = st[6], ai = st[5], mv = st[4], wp = st[1], rp = st[0];
        wire [1:0] cnt = st[3:2];
        wire f3 = f3_v[g];
`ifdef OT_INT8_MUT_OBDROP
        wire c_rdy = 1'b1;                      // NEGATIVE CONTROL: the queue ignores its fill (overrun drops a beat)
`else
        wire c_rdy = (cnt != 2'd2);
`endif
        wire cap = !mv || c_rdy;
        wire a_cap = !av || cap;
        wire push = mv && c_rdy;
        wire pop = (cnt != 2'd0) && m_ready;
        wire bz = mv || av || pend || (cnt != 2'd0);
`ifdef OT_SMH_MUT_NOBYP
        wire bp = 1'b0;
`else
        wire bp = !f3 && !bz;
`endif
        wire n_mv = cap ? av : mv;
        wire n_av = a_cap ? (pend || s_valid) : av;
        wire n_ai = a_cap ? (pend ? 1'b1 : (s_valid ? f3 : ai)) : ai;
        wire n_pd = a_cap ? (pend ? 1'b0 : (s_valid && f3)) : pend;
        ot_hbm_accel_smh_kregk #(.W(8), .RST(1)) u_c (.clk(clk), .rst_n(rst_n),
            .d({n_pd, n_av, n_ai, n_mv, cnt + {1'b0, push} - {1'b0, pop}, push ? ~wp : wp, pop ? ~rp : rp}), .q(st));
        if (g == 0) begin : g_o
            assign s_ready = a_cap && !pend;
            assign busy = bz;
            assign byp = bp;
            assign m_valid = (cnt != 2'd0);
        end
        reg [31:0] ad, md, e0, e1;
        wire [31:0] lo_c, hi_c, nx, wd;
        if (g < 32) begin : g_l
            reg [31:0] hc;
            for (l = 0; l < 2; l = l + 1) begin : g_ln
                assign lo_c[16*l +: 16] = classify(s_data[8*(2*g+l) +: 8]);
                assign hi_c[16*l +: 16] = classify(s_data[512 + 8*(2*g+l) +: 8]);
                assign wd[16*l +: 16] = encode(ad[16*l +: 16]);
            end
            always @(posedge clk) if (a_cap && !pend) hc <= hi_c;
            assign nx = pend ? hc : (f3 ? lo_c : s_data[LO +: 32]);
        end else begin : g_t
            assign lo_c = 32'd0; assign hi_c = 32'd0;
            assign wd = 32'd0;
            assign nx = (pend || f3) ? 32'd0 : s_data[LO +: 32];
        end
        always @(posedge clk) begin
            if (a_cap) ad <= nx;
            if (cap) md <= ai ? wd : ad;
            if (push && !wp) e0 <= md;
            if (push &&  wp) e1 <= md;
        end
        assign o_data[LO +: 32] = bp ? s_data[LO +: 32] : (rp ? e1 : e0);
    end endgenerate
endmodule

// fc_bc: ring SRAMs + bulk copy, the south-face channels (descriptor sink, request source, response chain both stages),
// retire landing (stage 2), the first line skid (u_sk0, outputs registered), row 3's face register.
module ot_hbm_accel_smh_fc_bc #(parameter integer MAX_OUT = 512, parameter integer PIO = 2, parameter integer TAGW = 16) (
    input  wire          clk, rst_a,
    input  wire          fd_v,  input wire [55:0] fd_d, output wire fd_ret,
    output wire          fq_v,  output wire [41:0] fq_d, input wire fq_ret,
    input  wire          fp_v,  input wire [1097:0] fp_d,
    input  wire          fsv,   output wire sv_o,
    output wire [35:0]   k0_mv, output wire [1087:0] k0_d, input wire [35:0] k1_sr,
    input  wire [802+TAGW-1:0] r3a, output wire [802+TAGW-1:0] fo_row3
);
    localparam integer PIH = PIO + 1, CHD = 2 * PIH + 3, NSL = 34;
    // reset: one relay flop per consumer (class 2: the single relay flop's async-clear net failed recovery by
    // -720 ps across fc_is; same structure here): 0 channels, 1 response / retire chains, 2 bulk copy, 3 skid, 4 row-3 reg
    wire [4:0] rr;
    ot_rst_relay #(.REGIONS(5)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rr));
    wire rn = rr[1];
    wire h_rsp_v; wire [9:0] h_rsp_tag; wire [1087:0] h_rsp_data;
    ot_hbm_accel_smv_chain #(.W(1), .D(2), .RST(1)) u_prv (.clk(clk), .rst_n(rn), .d(fp_v), .q(h_rsp_v));
    ot_hbm_accel_smv_chain #(.W(1098), .D(2), .RST(0)) u_prd (.clk(clk), .rst_n(rn), .d(fp_d), .q({h_rsp_tag, h_rsp_data}));
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_sv (.clk(clk), .rst_n(rn), .d(fsv), .q(sv_o));
    wire h_d_valid, h_d_ready; wire [55:0] h_d;
    ot_hbm_accel_smh_csnk #(.W(56), .PK(1), .PRK(1), .DEPTH(CHD + 1)) u_dch (.clk(clk), .rst_n(rr[0]),
        .i_v(fd_v), .i_d(fd_d), .o_ret(fd_ret), .m_valid(h_d_valid), .m_ready(h_d_ready), .m_data(h_d));
    wire h_req_v, h_req_ready; wire [31:0] h_req_addr; wire [9:0] h_req_tag;
    ot_hbm_accel_smh_csrc #(.W(42), .PS(PIH - 1), .PR(1), .DEPTH(CHD)) u_rch (.clk(clk), .rst_n(rr[0]),
        .s_valid(h_req_v), .s_ready(h_req_ready), .s_data({h_req_addr, h_req_tag}),
        .o_v(fq_v), .o_d(fq_d), .i_ret(fq_ret));
    wire b_valid, b_ready; wire [1087:0] b_data; wire [NSL-1:0] b_valid_v, b_ready_v;
    ot_hbm_accel_bulk_copy_oq5 #(.ENABLE(1), .LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1),
                             .RING_MACRO(1)) u_bc (
        .clk(clk), .rst_n(rr[2]), .d_valid(h_d_valid), .d_ready(h_d_ready), .d_base(h_d[55:24]), .d_lines(h_d[23:0]),
        .req_v(h_req_v), .req_ready(h_req_ready), .req_addr(h_req_addr), .req_tag(h_req_tag),
        .rsp_v(h_rsp_v), .rsp_tag(h_rsp_tag), .rsp_data(h_rsp_data),
        .s_valid(b_valid), .s_ready(b_ready), .s_data(b_data), .s_valid_v(b_valid_v), .s_ready_v(b_ready_v),
        .outstanding(), .idle());
    wire [NSL+1:0] k0_sr;
    ot_hbm_accel_smh_skid3r #(.W(1088)) u_sk0 (.clk(clk), .rst_n(rr[3]), .s_valid_v({b_valid, b_valid, b_valid_v}),
        .s_ready_v(k0_sr), .s_data(b_data), .m_valid_v(k0_mv), .m_ready_v(k1_sr), .m_data(k0_d));
    assign b_ready = k0_sr[NSL];
    assign b_ready_v = k0_sr[NSL-1:0];
    ot_hbm_accel_smh_bundle_reg #(.W(802+TAGW), .V(4+TAGW), .NV(2), .X(7)) u_m3 (.clk(clk), .rst_n(rr[4]), .d(r3a), .q(fo_row3));
endmodule

// fc_is: second line skid, INT8 adapter, issue, op channel sink, release / retire landings, barrier outputs, s1, hop H
// (two PR0 copies to the rows-0/1 children, two PR1 copies to the rows-2/3 side), format launch copies.
module ot_hbm_accel_smh_fc_is #(
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
    localparam integer SW = $clog2(IL), RW = $clog2(RMAX), XW = $clog2(XD), TAGW = RW + 1 + SW;
    localparam integer OPW = (RW + 1) + 16 + 8 + 1 + 2, OPX = OPW + XW, PIH = PIO + 1, CHD = 2 * PIH + 3, NSL = 34;
    localparam integer S1W = 3 + TAGW + XW;
    // reset: one relay flop per consumer group (class 2: route 5b228c4a2-cal TT -657 ps = the single relay flop's
    // async-clear net, recovery to 2,841 flops): 0 op channel, 1 skid, 2 INT8, 3 issue, 4 misc / launch copies
    wire [4:0] rr;
    ot_rst_relay #(.REGIONS(5)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rr));
    wire rn = rr[4];
    wire h_start, h_pop; wire [OPX-1:0] h_opx;
    ot_hbm_accel_smh_csnk #(.W(OPX), .PK(1), .PRK(1), .DEPTH(CHD + 1)) u_sch (.clk(clk), .rst_n(rr[0]),
        .i_v(fs_v), .i_d(fs_d), .o_ret(fs_ret), .m_valid(h_start), .m_ready(h_pop), .m_data(h_opx));
    wire [OPW-1:0] h_op = h_opx[XW +: OPW];
    wire [XW-1:0]  h_xb = h_opx[XW-1:0];
    wire [RW:0] h_rows = h_op[OPW-1 -: RW+1];
    wire [15:0] h_c    = h_op[11 +: 16];
    wire [7:0]  h_g    = h_op[3 +: 8];
    wire        h_gs   = h_op[2];
    wire [1:0]  h_fmt  = h_op[1:0];
`ifndef SYNTHESIS
    always @(posedge clk)
        if (rn && ENABLE_INT8 && h_pop && h_fmt == 2'd3 && h_rows[0] && h_c[0] && h_g[0])
            $fatal(1, "fmt3 needs an even count of real issue beats");
`endif
    wire h_release;
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_prl (.clk(clk), .rst_n(rn), .d(fr_rl), .q(h_release));
    wire w_valid, w_ready; wire [1087:0] w_data; wire [NSL+1:0] k1_mv;
    ot_hbm_accel_smh_skid3v #(.W(1088)) u_sk (.clk(clk), .rst_n(rr[1]), .s_valid_v(k0_mv), .s_ready_v(k1_sr),
        .s_data(k0_d), .m_valid_v(k1_mv), .m_ready_v({(NSL+2){w_ready}}), .m_data(w_data));
    assign w_valid = k1_mv[NSL+1];
    reg  [XW-1:0] xb_q;
    wire        sv, h_busy, h_arrive, h_released;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rn)
        if (!rn) xb_q <= {XW{1'b0}};
        else if (h_pop) xb_q <= h_xb;
    wire issue_w_valid, issue_w_ready, issue_line_end;
    wire [1087:0] issue_w_data;
    reg              pop_r;
    reg  [1:0]       fmt_q;
    generate if (ENABLE_INT8) begin : g_int8
        wire unpack_ready;
        reg input_open;
        always @(posedge clk or negedge rr[2])
            if (!rr[2]) input_open <= 1'b0;
            else if (h_pop) input_open <= 1'b1;
            else if (issue_line_end) input_open <= 1'b0;
        wire intake_credit;
        if (PIPE_INT8) begin : g_credit
            ot_hbm_accel_int8_credit #(.RW(RW)) u_credit (
                .clk(clk),.rst_n(rr[2]),.launch(h_pop),.take(w_valid && w_ready),
                .int8_mode(fmt_q==2'd3),.op_rows(h_rows),.op_g(h_g),.op_c(h_c),
                .intake_credit(intake_credit));
        end else begin : g_credit_legacy
            assign intake_credit=1'b1;
        end
        // r7 (fcis-r6 TT -138.89: u_issue.si -> iss_line_end compare, ~600 ps, fanned to the 34 slice-control copies):
        // with the exact producer-beat credit (PIPE_INT8 >= 1) the adapter has always taken the op's last beat before the
        // issue consumes it, so !iss_line_end is implied there; the PIPE_INT8 >= 2 intake uses registered terms only.
        wire demand = input_open && intake_credit && ((PIPE_INT8 >= 2) || !issue_line_end);
        wire a_busy, a_v; wire [1087:0] a_d;
        wire fmt3 = (fmt_q == 2'd3);
        wire byp;
        if (PIPE_INT8 >= 2) begin : g_ob
            // round 6 (class 2 + 5): the adapter, its output queue and the bypass mux cut into 34 slices x 32 bits
            // (ot_hbm_accel_smh_fc_i8s), each with kept control state and its own fmt3 copy; slice 0 drives the
            // control outputs (byp / busy / ready / valid).  Cycle-identical to ot_hbm_accel_int8_line_ob + the mux.
            (* keep *) reg [33:0] f3_v;
            always @(posedge clk or negedge rn)
                if (!rn) f3_v <= 34'd0;
                else if (h_pop) f3_v <= {34{h_fmt == 2'd3}};
            wire s_byp;
            ot_hbm_accel_smh_fc_i8s u_unpack (.clk(clk), .rst_n(rr[2]), .f3_v(f3_v),
                .s_valid(w_valid && demand && !s_byp), .s_ready(unpack_ready), .s_data(w_data),
                .busy(a_busy), .byp(s_byp), .m_valid(a_v), .m_ready(issue_w_ready && !s_byp), .o_data(a_d));
            assign byp = s_byp;
            assign issue_w_data = a_d;
        end else begin : g_ln
`ifdef OT_SMH_MUT_NOBYP
            assign byp = 1'b0;
`else
            assign byp = !fmt3 && !a_busy;
`endif
            ot_hbm_accel_int8_line #(.PIPE(PIPE_INT8)) u_unpack (.clk(clk), .rst_n(rr[2]), .busy(a_busy),
                .int8_mode(fmt3), .s_valid(w_valid && demand && !byp), .s_ready(unpack_ready), .s_data(w_data),
                .m_valid(a_v), .m_ready(issue_w_ready && !byp), .m_data(a_d));
            assign issue_w_data = byp ? w_data : a_d;
        end
        assign w_ready = byp ? issue_w_ready : (unpack_ready && demand && fmt3);
        assign issue_w_valid = byp ? w_valid : a_v;
    end else begin : g_no_int8
        assign issue_w_valid = w_valid;
        assign w_ready = issue_w_ready;
        assign issue_w_data = w_data;
    end endgenerate
    always @(posedge clk or negedge rn)
        if (!rn) begin pop_r <= 1'b0; fmt_q <= 2'd0; end
        else begin pop_r <= h_pop; if (h_pop) fmt_q <= h_fmt; end
    // format launch copies (m2's g_f1): copy G = side * 2 + (bottom pair): 0 W rows 0/1, 1 W rows 2/3, 2 E 0/1, 3 E 2/3
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_f1
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_pd (.clk(clk), .rst_n(rn), .en(1'b1), .d(pop_r), .q(fm[3*k+2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_fq (.clk(clk), .rst_n(rn), .en(1'b1), .d(fmt_q), .q(fm[3*k +: 2]));
    end endgenerate
`ifdef OT_SMH_MUT_BFDLY
    localparam integer DBFX = 11 + 64;
`else
    localparam integer DBFX = 11;
`endif
    ot_hbm_accel_issue_pq #(.IL(IL), .RMAX(RMAX), .XDEPTH(XD), .NOUT(NOUT), .HAZ(HAZ), .DBF(DBFX)) u_issue (
        .clk(clk), .rst_n(rr[3]), .start_v(h_start), .launch(h_pop), .op_rows(h_rows), .op_c(h_c), .op_g(h_g),
        .op_gs(h_gs), .op_bf(h_fmt == 2'd0 || (ENABLE_INT8 && h_fmt == 2'd3)),
        .w_valid(issue_w_valid), .x_rdy(1'b1), .w_ready(issue_w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_line_end(issue_line_end), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release),
        .released(h_released), .hz_wait());
    ot_hbm_accel_smv_chain #(.W(3), .D(1), .RST(1)) u_pbz (.clk(clk), .rst_n(rn),
        .d({h_busy, h_arrive, h_released}), .q(fo_pbz));
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_sv (.clk(clk), .rst_n(rn), .d(sv_i), .q(sv));
    reg [1087:0]     s1_w;
    reg [2:0]        s1_cv;
    reg [TAGW+XW-1:0] s1_ct;
    always @(posedge clk or negedge rn)
        if (!rn) s1_cv <= 3'd0;
        else s1_cv <= {adv && row_ok, i_first, i_last};
    always @(posedge clk) begin
`ifdef OT_SMH_MUT_S1W
        s1_w <= issue_w_data ^ 1088'd8;
`else
        s1_w <= issue_w_data;
`endif
        s1_ct <= {row_now[RW-1:0], i_glast, si, xa + xb_q};
    end
    // hop H (m2's g_h): the four line copies, each {valid 3, tag + x, line part}
    wire [4*S1W-1:0] hc;
    generate for (k = 0; k < 4; k = k + 1) begin : g_h
        ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_v (.clk(clk), .rst_n(rn), .en(1'b1), .d(s1_cv), .q(hc[k*S1W + TAGW + XW +: 3]));
        ot_hbm_accel_smh_kreg #(.W(TAGW + XW)) u_t (.clk(clk), .rst_n(rn), .en(1'b1), .d(s1_ct), .q(hc[k*S1W +: TAGW + XW]));
    end endgenerate
    wire [1055:0] hw0, hw2; wire [543:0] hw1, hw3;
    ot_hbm_accel_smh_kreg #(.W(1056)) u_w0 (.clk(clk), .rst_n(rn), .en(1'b1), .d(s1_w[1055:0]), .q(hw0));
    ot_hbm_accel_smh_kreg #(.W(1056)) u_w2 (.clk(clk), .rst_n(rn), .en(1'b1), .d(s1_w[1055:0]), .q(hw2));
    ot_hbm_accel_smh_kreg #(.W(544)) u_w1 (.clk(clk), .rst_n(rn), .en(1'b1), .d({s1_w[1087:1056], s1_w[1023:512]}), .q(hw1));
    ot_hbm_accel_smh_kreg #(.W(544)) u_w3 (.clk(clk), .rst_n(rn), .en(1'b1), .d({s1_w[1087:1056], s1_w[1023:512]}), .q(hw3));
    assign lt0 = {hc[0*S1W +: S1W], hw0};
    assign lb0 = {hc[1*S1W +: S1W], hw1};
    assign lt1 = {hc[2*S1W +: S1W], hw2};
    assign lb1 = {hc[3*S1W +: S1W], hw3};
endmodule

// fc_xl: tile row 1's x-write landing at the north face, relay 1 per side (W / E edges), row 0's face register.
module ot_hbm_accel_smh_fc_xl #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] fx_b, output wire [2068:0] xw_w, xw_e,
    input  wire [802+TAGW-1:0] r0a, output wire [802+TAGW-1:0] fo_row0
);
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rn));
    wire [2068:0] xl;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_xlv (.clk(clk), .rst_n(rn), .en(1'b1), .d(fx_b[2068]), .q(xl[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_xld (.clk(clk), .rst_n(rn), .en(1'b1), .d(fx_b[2067:0]), .q(xl[2067:0]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_r1wv (.clk(clk), .rst_n(rn), .en(1'b1), .d(xl[2068]), .q(xw_w[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_r1wd (.clk(clk), .rst_n(rn), .en(1'b1), .d(xl[2067:0]), .q(xw_w[2067:0]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_r1ev (.clk(clk), .rst_n(rn), .en(1'b1), .d(xl[2068]), .q(xw_e[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_r1ed (.clk(clk), .rst_n(rn), .en(1'b1), .d(xl[2067:0]), .q(xw_e[2067:0]));
    ot_hbm_accel_smh_bundle_reg #(.W(802+TAGW), .V(4+TAGW), .NV(2), .X(7)) u_m0 (.clk(clk), .rst_n(rn), .d(r0a), .q(fo_row0));
endmodule

// fc_xr: x-write relay 2 (one side) and one relay on that side's PR1 line copy and format bits.
module ot_hbm_accel_smh_fc_xr #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] xi, output wire [2068:0] xo,
    input  wire [554+TAGW-1:0] li, output wire [554+TAGW-1:0] lo,
    input  wire [2:0]    fi, output wire [2:0]    fo
);
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rn));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_xv (.clk(clk), .rst_n(rn), .en(1'b1), .d(xi[2068]), .q(xo[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_xd (.clk(clk), .rst_n(rn), .en(1'b1), .d(xi[2067:0]), .q(xo[2067:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_lv (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[554+TAGW-1 -: 3]), .q(lo[554+TAGW-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(551+TAGW)) u_ld (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[551+TAGW-1:0]), .q(lo[551+TAGW-1:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_f (.clk(clk), .rst_n(rn), .en(1'b1), .d(fi), .q(fo));
endmodule

// row unpack + format replicas of one row bundle (m2's stage-A input), shared by fc_t / fc_b.  lw: the line (zeros where
// the copy carries none), fr: 17 format replicas {16 byte groups, 1 row control}.
module ot_hbm_accel_smh_fc_unpack #(parameter integer SP = 0, parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire [1087:0] lw, input wire [33:0] fr, input wire [10+TAGW-1:0] c1, output wire [802+TAGW-1:0] a_in
);
    wire [787:0] un;
    genvar q, bb;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
        localparam integer J = SP * 2 + q;
        for (bb = 0; bb < 32; bb = bb + 1) begin : g_b
            localparam integer RI = q * 8 + bb / 4;
            wire [7:0] fp4w = {4'd0, lw[128*J + 4*bb +: 4]};
            wire [7:0] fp8w = (J < 4) ? lw[256*J + 8*bb +: 8] : 8'd0;
            assign un[256*q + 8*bb +: 8] = (fr[2*RI +: 2] == 2'd2) ? fp4w : fp8w;
        end
        assign un[512 + 10*q +: 10] = {2'b00, lw[1024 + 8*J +: 8]} - 10'sd127;
    end endgenerate
    assign un[532 +: 256] = lw[SP*256 +: 256];
    wire bf_op = (fr[33:32] == 2'd0) || (ENABLE_INT8 && fr[33:32] == 2'd3);
    wire fp4_op = (fr[33:32] == 2'd2);
    wire s1_v = c1[9+TAGW], s1_first = c1[8+TAGW], s1_last = c1[7+TAGW];
    wire [TAGW-1:0] s1_tag = c1[7 +: TAGW];
    wire [6:0]  s1_xa  = c1[6:0];
    assign a_in = {s1_v && !bf_op, s1_v && bf_op, s1_first, s1_last, fp4_op, bf_op, s1_tag, un, s1_v, s1_xa};
endmodule

// per-row format replicas: one enable / value copy per 8 replicas (m2's g_fc), 17 replicas (m2's g_fmt).
module ot_hbm_accel_smh_fc_fmt (
    input wire clk, rn, input wire pd, input wire [1:0] fq, output wire [33:0] fr
);
    wire [2:0] pc; wire [5:0] qc;
    genvar k;
    generate for (k = 0; k < 3; k = k + 1) begin : g_c
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_pd (.clk(clk), .rst_n(rn), .en(1'b1), .d(pd), .q(pc[k]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_fq (.clk(clk), .rst_n(rn), .en(1'b1), .d(fq), .q(qc[2*k +: 2]));
    end
    for (k = 0; k < 17; k = k + 1) begin : g_r
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1), .EN(1)) u (.clk(clk), .rst_n(rn), .en(pc[k / 8]), .d(qc[2*(k / 8) +: 2]),
            .q(fr[2*k +: 2]));
    end endgenerate
endmodule

// fc_t: one side's tile-row-0 rows: H2 (pin flops) + 2 pads on the PR0 line, row sp0 A (to the row-0 face register in
// fc_xl), row sp1 A-M-P-O (rout_*1 pins).
module ot_hbm_accel_smh_fc_t #(parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [1066+TAGW-1:0] li, input wire [2:0] fi,
    output wire [802+TAGW-1:0] rout, output wire [802+TAGW-1:0] r0a
);
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rn));
    localparam integer LT = 1066 + TAGW, RB = 802 + TAGW;
    wire [LT-1:0] l2, l3, l4;
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_h2v (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[LT-1 -: 3]), .q(l2[LT-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LT-3)) u_h2d (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[LT-4:0]), .q(l2[LT-4:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_p1v (.clk(clk), .rst_n(rn), .en(1'b1), .d(l2[LT-1 -: 3]), .q(l3[LT-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LT-3)) u_p1d (.clk(clk), .rst_n(rn), .en(1'b1), .d(l2[LT-4:0]), .q(l3[LT-4:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_p2v (.clk(clk), .rst_n(rn), .en(1'b1), .d(l3[LT-1 -: 3]), .q(l4[LT-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LT-3)) u_p2d (.clk(clk), .rst_n(rn), .en(1'b1), .d(l3[LT-4:0]), .q(l4[LT-4:0]));
    // format: +2 with the line (pin flop, pad), then the per-row copies and replicas
    wire [2:0] f1, f2;
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_f1 (.clk(clk), .rst_n(rn), .en(1'b1), .d(fi), .q(f1));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_f2 (.clk(clk), .rst_n(rn), .en(1'b1), .d(f1), .q(f2));
    wire [1087:0] lw = {32'd0, l4[1055:0]};
    wire [33:0] fr0, fr1;
    ot_hbm_accel_smh_fc_fmt u_fm0 (.clk(clk), .rn(rn), .pd(f2[2]), .fq(f2[1:0]), .fr(fr0));
    ot_hbm_accel_smh_fc_fmt u_fm1 (.clk(clk), .rn(rn), .pd(f2[2]), .fq(f2[1:0]), .fr(fr1));
    wire [RB-1:0] a0, a1, ar1, mr1, pr1;
    ot_hbm_accel_smh_fc_unpack #(.SP(0), .ENABLE_INT8(ENABLE_INT8), .TAGW(TAGW)) u_u0 (.lw(lw), .fr(fr0), .c1(l4[LT-1:1056]), .a_in(a0));
    ot_hbm_accel_smh_fc_unpack #(.SP(1), .ENABLE_INT8(ENABLE_INT8), .TAGW(TAGW)) u_u1 (.lw(lw), .fr(fr1), .c1(l4[LT-1:1056]), .a_in(a1));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_a0 (.clk(clk), .rst_n(rn), .d(a0), .q(r0a));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_a1 (.clk(clk), .rst_n(rn), .d(a1), .q(ar1));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_m1 (.clk(clk), .rst_n(rn), .d(ar1), .q(mr1));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_p1 (.clk(clk), .rst_n(rn), .d(mr1), .q(pr1));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_o1 (.clk(clk), .rst_n(rn), .d(pr1), .q(rout));
endmodule

// fc_b: one side's tile-row-1 rows and x write: H2 (pin flops) + 1 pad on the PR1 line (fc_xr holds the other relay),
// row sp2 A-M-P-O (rout_*2), row sp3 A (to the row-3 face register in fc_bc), x-write M (pin flops) + O (bout_*1).
module ot_hbm_accel_smh_fc_b #(parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [554+TAGW-1:0] li, input wire [2:0] fi, input wire [2068:0] xi,
    output wire [2068:0] bout, output wire [802+TAGW-1:0] rout, output wire [802+TAGW-1:0] r3a
);
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rn));
    localparam integer LB = 554 + TAGW, RB = 802 + TAGW;
    wire [LB-1:0] l2, l3;
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_h2v (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[LB-1 -: 3]), .q(l2[LB-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LB-3)) u_h2d (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[LB-4:0]), .q(l2[LB-4:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_p2v (.clk(clk), .rst_n(rn), .en(1'b1), .d(l2[LB-1 -: 3]), .q(l3[LB-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LB-3)) u_p2d (.clk(clk), .rst_n(rn), .en(1'b1), .d(l2[LB-4:0]), .q(l3[LB-4:0]));
    wire [2:0] f2;
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_f2 (.clk(clk), .rst_n(rn), .en(1'b1), .d(fi), .q(f2));
    // l3 = {c 10+TAGW, line[1087:1056], line[1023:512]}
    wire [1087:0] lw = {l3[543:512], 32'd0, l3[511:0], 512'd0};
    wire [33:0] fr2, fr3;
    ot_hbm_accel_smh_fc_fmt u_fm2 (.clk(clk), .rn(rn), .pd(f2[2]), .fq(f2[1:0]), .fr(fr2));
    ot_hbm_accel_smh_fc_fmt u_fm3 (.clk(clk), .rn(rn), .pd(f2[2]), .fq(f2[1:0]), .fr(fr3));
    wire [RB-1:0] a2, a3, ar2, mr2, pr2;
    ot_hbm_accel_smh_fc_unpack #(.SP(2), .ENABLE_INT8(ENABLE_INT8), .TAGW(TAGW)) u_u2 (.lw(lw), .fr(fr2), .c1(l3[LB-1:544]), .a_in(a2));
    ot_hbm_accel_smh_fc_unpack #(.SP(3), .ENABLE_INT8(ENABLE_INT8), .TAGW(TAGW)) u_u3 (.lw(lw), .fr(fr3), .c1(l3[LB-1:544]), .a_in(a3));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_a3 (.clk(clk), .rst_n(rn), .d(a3), .q(r3a));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_a2 (.clk(clk), .rst_n(rn), .d(a2), .q(ar2));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_m2 (.clk(clk), .rst_n(rn), .d(ar2), .q(mr2));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_p2 (.clk(clk), .rst_n(rn), .d(mr2), .q(pr2));
    ot_hbm_accel_smh_bundle_reg #(.W(RB), .V(4+TAGW), .NV(2), .X(7)) u_o2 (.clk(clk), .rst_n(rn), .d(pr2), .q(rout));
    wire [2068:0] xm;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bmv (.clk(clk), .rst_n(rn), .en(1'b1), .d(xi[2068]), .q(xm[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_bmd (.clk(clk), .rst_n(rn), .en(1'b1), .d(xi[2067:0]), .q(xm[2067:0]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bov (.clk(clk), .rst_n(rn), .en(1'b1), .d(xm[2068]), .q(bout[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_bod (.clk(clk), .rst_n(rn), .en(1'b1), .d(xm[2067:0]), .q(bout[2067:0]));
endmodule
`endif


module ot_hbm_accel_smh_front_s #(
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
    parameter integer PT4 = 1           // hbm-forks 2026-10-09: = ot_hbm_accel_smh_tile PT4 (m3h: a 4th row-bundle register per
                                        //   tile hop, so a column's results arrive 1 more cycle per hop: the result deskew is
                                        //   (5 + PT4) a hop; m3h left it at 5 and columns at hop >= 2 merged a wrong row)
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
    // el1013-smh-r14 OT_SMH_PINREG: the gated tile lands rin / bin in its own pin registers (+1 row-bundle register per
    // tile hop), so a column's results arrive 1 more cycle per hop: the deskew is (5 + PT4 + PINR) a hop
    // OT_SMH_MUT_PINR_DESKEW (bench mutant only): the front keeps the 5 + PT4 deskew against pin-registered tiles
    localparam integer PINR =
`ifdef OT_SMH_MUT_PINR_DESKEW
        0;
`elsif OT_SMH_PINREG
        1;
`else
        0;
`endif
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
                ot_hbm_accel_smv_chain #(.W(2), .D((5+PT4+PINR)*(NH-1-ln)), .RST(1)) u_dv (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-1 -: 2]), .q(al[COLN*QLW + QLW - 2 +: 2]));
                ot_hbm_accel_smv_chain #(.W(QLW-2), .D((5+PT4+PINR)*(NH-1-ln)), .RST(0)) u_dd (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-3:0]), .q(al[COLN*QLW +: QLW-2]));
            end
        end
    end endgenerate
    wire [NC-1:0]    cf_a;
    wire [NC-1:0]    cv_a;
    wire result_v, result_fault;
    wire [NC*32-1:0] cy_a;
    genvar cc;
    generate for (cc = 0; cc < NC; cc = cc + 1) begin : g_al
        assign cf_a[cc] = al[cc*QLW + QLW - 2];
        assign cv_a[cc] = al[cc*QLW + QLW - 1];
        assign cy_a[32*cc +: 32] = al[cc*QLW + RW +: 32];
    end endgenerate
    ot_hbm_accel_smh_result_valid #(.NC(NC), .ENABLE(RESULT_VALID)) u_result_valid (
        .valids(cv_a), .faults(cf_a), .row_valid(result_v), .fault_event(result_fault));
    // retire: stage 1 of m2's three, at the north face (front_c lands it and adds the third beside the issue)
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_sv (.clk(clk), .rst_n(rst_n), .d(result_v), .q(fsv));
    reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0;
        else fault_q <= fault_q | result_fault
`ifdef OT_SMH_RCH_NONEMPTY
            | rch_state_fault
`endif
            ;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d(result_v), .q(rv));
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
`ifdef OT_SMH_HIER
    // el1011-hbm-smh OT_SMH_HIER: the tile as hardened sub-elements (pt_w, pt_e, and per leaf xs + bdc + tcc = 2 tcl + tct);
    // the top keeps the gather launch (u_gov / u_god), the pass-through G1 lanes and the leaf G1 select (leafh).
`ifndef SYNTHESIS
    initial if (RPT != 2 || SUB != 4) $error("OT_SMH_HIER: built for RPT 2, SUB 4");
`endif
    // per-consumer resets: g1 / g2 / go = leaf j's own-row gather relays (at the leaf, mid-tile, at the S-edge gout pins),
    // p1 / p2 / p3 = the pass-through G1 lanes (N edge, mid-tile, S edge), ptw / pte / lh = the hard children
    wire [RPT-1:0] r_g1, r_g2, r_go, r_lh;
    wire r_p1, r_p2, r_p3, r_ptw, r_pte;
`ifdef OT_SMH_RSTPIN
    // el1013-smh-r11 OT_SMH_RSTPIN (SM tile cluster r10 CTS diagnosis B1): the rst_n PORT lands in ONE pin flop on the tile
    // clock and nothing else; a registered tree (ot_hbm_accel_smh_rst_tree, <= ~350 um a stage, uniform depth 5) carries it
    // to the north leaf, the pass-through band and the south leaf, and each band's final copies reset only that band.
    // Leaf 0 is the north leaf, leaf 1 the south leaf (floorplan); the gather relays take the copy of the band they sit in.
    wire rt_gn, rt_lhn, rt_gm, rt_ptw, rt_pte, rt_gs, rt_lhs;
    ot_hbm_accel_smh_rst_tree u_rt (.clk(clk), .rst_n(rst_n), .gn(rt_gn), .lhn(rt_lhn), .gm(rt_gm), .ptw(rt_ptw),
                                    .pte(rt_pte), .gs(rt_gs), .lhs(rt_lhs));
    assign r_g1 = {rt_gs, rt_gn}; assign r_g2 = {rt_gs, rt_gm}; assign r_go = {rt_gs, rt_gs};
    assign r_lh = {rt_lhs, rt_lhn};
    assign r_p1 = rt_gn; assign r_p2 = rt_gm; assign r_p3 = rt_gs; assign r_ptw = rt_ptw; assign r_pte = rt_pte;
`else
    wire [RPT+1:0] rr;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(RPT + 2)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
`else
    assign rr = {(RPT + 2){rst_n}};
`endif
    assign r_g1 = rr[RPT-1:0]; assign r_g2 = rr[RPT-1:0]; assign r_go = rr[RPT-1:0]; assign r_lh = {RPT{rst_n}};
    assign r_p1 = rr[RPT+1]; assign r_p2 = rr[RPT+1]; assign r_p3 = rr[RPT+1]; assign r_ptw = rst_n; assign r_pte = rst_n;
`endif
    wire [BBW-1:0] bk1_n, bk1_s, bm;
    wire [NBEAT-1:0] ohl1_n, ohl1_s;
    wire [RPT*RBW-1:0] rpm;
    wire [RBW-1:0] rl1_n, rl1_s;
    // el1013-smh-r14 OT_SMH_PINREG (SM tile cluster r13 post-CTS diagnosis, el1011-hbm-smh.log 10-13): the cluster had no
    // boundary register of its own on the row bundles and the x-write beat: rin / bin ports fed pt_w's pins, and pt_w
    // spends 240-530 ps from a pin to its landing flops (every bin bit lands in 3-5 flops: the pass copy and the N / S
    // leaf copies; ETM setup arc -345..+5 ps against a 526 ps insertion), more than the 223 ps receiver share of the
    // die link on all 3,705 bits (post-CTS TT -419 worst / -157 mean at 770 ps).  One register per bit at the tile's
    // own rin / bin pins: port -> flop is the tile's receiver share, flop -> pt_w a full internal cycle.  +1 cycle per
    // tile hop on the row bundles AND the x-write beat (in step: the x-write margin is unchanged); a column's results
    // arrive 1 more cycle per hop, taken by the front's result deskew (ot_hbm_accel_smh_front_s: 5 + PT4 + 1 a hop).
    wire [RPT*RBW-1:0] rin_l;
    wire [BBW-1:0]     bin_l;
`ifdef OT_SMH_PINREG
    genvar pj;
    generate for (pj = 0; pj < RPT; pj = pj + 1) begin : g_pin
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_r (.clk(clk), .rst_n(r_ptw),
            .d(rin[pj*RBW +: RBW]), .q(rin_l[pj*RBW +: RBW]));
    end endgenerate
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_pbv (.clk(clk), .rst_n(r_ptw), .en(1'b1), .d(bin[BBW-1]), .q(bin_l[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_pbd (.clk(clk), .rst_n(r_ptw), .en(1'b1), .d(bin[BBW-2:0]), .q(bin_l[BBW-2:0]));
`else
    assign rin_l = rin;
    assign bin_l = bin;
`endif
`ifdef OT_SMH_COMPACT_PT
    ot_hbm_smh_compact_pt_w
`else
    ot_hbm_accel_smh_pt_w
`endif
`ifndef SYNTHESIS
        #(.TAGW(TAGW), .NBEAT(NBEAT))
`endif
        u_ptw (.clk(clk), .rst_a(r_ptw), .rin(rin_l), .bin(bin_l), .rpm(rpm), .bm(bm), .rl1_n(rl1_n),
        .bk1_n(bk1_n), .ohl1_n(ohl1_n), .rl1_s(rl1_s), .bk1_s(bk1_s), .ohl1_s(ohl1_s));
`ifdef OT_SMH_COMPACT_PT
    ot_hbm_smh_compact_pt_e
`else
    ot_hbm_accel_smh_pt_e
`endif
`ifndef SYNTHESIS
        #(.TAGW(TAGW), .NBEAT(NBEAT))
`endif
        u_pte (.clk(clk), .rst_a(r_pte), .rpm(rpm), .bm(bm), .rout(rout), .bout(bout));
    genvar j, ln;
    generate for (j = 0; j < RPT; j = j + 1) begin : g_lf
        wire gv, gf; wire [31:0] gy; wire [TAGW-1:0] gt;
        ot_hbm_accel_smh_leafh #(.LBS(LBS), .LSB(LSB), .IL(IL), .TAGW(TAGW), .XD(XD), .NBEAT(NBEAT), .TCK(TCK),
                                 .NMG(NMG), .A1B(A1B), .A2B(A2B)) u_lh (
            .clk(clk), .rst_n(r_lh[j]), .xs_a1(xs_a1[j*A1B +: A1B]), .xs_g1(xs_g1[j*5 +: 5]),
            .xs_a2(xs_a2[j*A2B +: A2B]), .xs_g2(xs_g2[j*5 +: 5]), .rl1(j == 0 ? rl1_n : rl1_s),
            .bk1(j == 0 ? bk1_n : bk1_s), .ohl1(j == 0 ? ohl1_n : ohl1_s), .gv(gv), .gf(gf), .gy(gy), .gt(gt));
        // (physical spec round 3) the hierarchical tile is 1,080 um tall: leaf 0's result travels ~1,000 um to the
        // S-edge gout pins -> two relay registers on EVERY own-row lane of every tile (uniform: the back end's deskew
        // is unchanged; +2 cycles on every result), <= ~360 um of wire per stage
        wire [GLW-1:0] g1, g2;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_grv1 (.clk(clk), .rst_n(r_g1[j]), .en(1'b1), .d({gv, gf}), .q(g1[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_grd1 (.clk(clk), .rst_n(r_g1[j]), .en(1'b1), .d({gy, gt}), .q(g1[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_grv2 (.clk(clk), .rst_n(r_g2[j]), .en(1'b1), .d(g1[GLW-2 +: 2]), .q(g2[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_grd2 (.clk(clk), .rst_n(r_g2[j]), .en(1'b1), .d(g1[0 +: GLW-2]), .q(g2[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_gov (.clk(clk), .rst_n(r_go[j]), .en(1'b1), .d(g2[GLW-2 +: 2]),
            .q(gout[(RPT-1-j)*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_god (.clk(clk), .rst_n(r_go[j]), .en(1'b1), .d(g2[0 +: GLW-2]),
            .q(gout[(RPT-1-j)*GLW +: GLW-2]));
    end
    for (ln = RPT; ln < SUB; ln = ln + 1) begin : g_gl
        wire [GLW-1:0] gm;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(r_p1), .en(1'b1),
            .d(gin[(ln-RPT)*GLW + GLW - 2 +: 2]), .q(gm[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d (.clk(clk), .rst_n(r_p1), .en(1'b1),
            .d(gin[(ln-RPT)*GLW +: GLW-2]), .q(gm[0 +: GLW-2]));
        wire [GLW-1:0] gn;                    // (round 5) a third register: 510 um is more than two spans
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v2 (.clk(clk), .rst_n(r_p2), .en(1'b1),
            .d(gm[GLW-2 +: 2]), .q(gn[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d2 (.clk(clk), .rst_n(r_p2), .en(1'b1),
            .d(gm[0 +: GLW-2]), .q(gn[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v3 (.clk(clk), .rst_n(r_p3), .en(1'b1),
            .d(gn[GLW-2 +: 2]), .q(gout[ln*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d3 (.clk(clk), .rst_n(r_p3), .en(1'b1),
            .d(gn[0 +: GLW-2]), .q(gout[ln*GLW +: GLW-2]));
    end endgenerate
`else
`ifdef OT_SMH_PINREG
`ifndef SYNTHESIS
    initial $fatal(1, "OT_SMH_PINREG is built for the hierarchical tile (OT_SMH_HIER): the flat tile has no pin landing stage");
`endif
`endif
    // fe-push-hphys-1010 OT_SMH_RSTRELAY: the rst_n port drives only ot_rst_relay (async assert, synchronous release
    // RELEASE = 3 tile edges; the cg tile keeps its gate open HOLD edges after reset).  Region j < RPT = leaf j (its
    // landing copies, rotator replicas, leaf, gather launch); RPT = the b / r pass-through; RPT + 1 = the G1 lanes.
    wire [RPT+1:0] rr;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(RPT + 2)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
`else
    assign rr = {(RPT + 2){rst_n}};
`endif
    // ---- landing: the x-write bundle (driven on to the next tile from these flops) ----
    // the x-write bundle lands in a pass-through copy (driven on to the next tile) and one copy per leaf (the leaf's
    // rotator), so neither spans the tile; the copies are bit-identical kept registers
    wire [BBW-1:0] bl;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blv (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bin[BBW-1]),
        .q(bl[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bld (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bin[BBW-2:0]), .q(bl[BBW-2:0]));
    // (margin m2) the pass-through copy lands at the input pins and launches from a second register at the output
    // pins (+1 per tile hop on the x-write beat, matched by the row bundles' +1 per hop: the margin is unchanged)
    // (margin m3e) a third pass-through register mid-tile (tile_e c2: u_bld -> u_bld2 -10.6 ps across the tile): +1 per
    // tile hop on the x-write beat, matched by the row bundles' third register (rpm), so the margin is unchanged
    wire [BBW-1:0] bm, bm4;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blvm (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bl[BBW-1]), .q(bm[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bldm (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bl[BBW-2:0]), .q(bm[BBW-2:0]));
    generate if (PT4 != 0) begin : g_pt4b
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blvn (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bm[BBW-1]), .q(bm4[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bldn (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bm[BBW-2:0]), .q(bm4[BBW-2:0]));
    end else begin : g_pt3b
        assign bm4 = bm;
    end endgenerate
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blv2 (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bm4[BBW-1]),
        .q(bout[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bld2 (.clk(clk), .rst_n(rr[RPT]), .en(1'b1), .d(bm4[BBW-2:0]), .q(bout[BBW-2:0]));
    genvar j, ln;
    generate for (j = 0; j < RPT; j = j + 1) begin : g_lf
        // the row bundle of row j (landed, driven on)
        // the row bundle lands in a pass-through copy (rout) and the leaf's own copy (kept, bit-identical)
        wire [RBW-1:0] rl, rl1, rp, rpm, rpm4;
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp (.clk(clk), .rst_n(rr[RPT]),
            .d(rin[j*RBW +: RBW]), .q(rp));
        // (margin m2) landing at the input pins (u_rp), launch from a register at the output pins; (m3e) a third
        // register mid-tile (u_rpm, rp -> rp2 was +0.8 ps): 3 per hop, in step with the x-write beat
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rpm (.clk(clk), .rst_n(rr[RPT]),
            .d(rp), .q(rpm));
        if (PT4 != 0) begin : g_pt4r
            ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rpn (.clk(clk), .rst_n(rr[RPT]),
                .d(rpm), .q(rpm4));
        end else begin : g_pt3r
            assign rpm4 = rpm;
        end
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp2 (.clk(clk), .rst_n(rr[RPT]),
            .d(rpm4), .q(rout[j*RBW +: RBW]));
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl (.clk(clk), .rst_n(rr[j]),
            .d(rin[j*RBW +: RBW]), .q(rl1));
        wire [BBW-1:0] bk, bk1;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkv (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(bin[BBW-1]),
            .q(bk1[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkd (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(bin[BBW-2:0]),
            .q(bk1[BBW-2:0]));
        // one-hot beat group replicas for this leaf's masks (landed straight from the pins, NG copies)
        // (round 5) the beat one-hot lands once per leaf (kept, beside the pins), its NG replicas load one edge later,
        // in step with the leaf's two-stage rotation
        wire [NG*NBEAT-1:0] ohr;
        wire [NBEAT-1:0] ohl, ohl1;
        ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohl (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(bin[2048 +: NBEAT]),
            .q(ohl1));
`ifdef OT_SMH_HIER
        // el1011-hbm-smh OT_SMH_HIER: the leaf is a HARDENED sub-element (ot_hbm_accel_smh_leafh: its own clock tree,
        // reset relay and pin-flop boundary).  The tile keeps the pin landings (rl1 / bk1 / ohl1) and the gather
        // launch; the second landing (rl2 / bk2 / ohl2 + the one-hot replicas) moves into the leaf as its input pin
        // flops.  0 cycles: the same registers, a different physical owner.
        wire gv, gf; wire [31:0] gy; wire [TAGW-1:0] gt;
        ot_hbm_accel_smh_leafh #(.LBS(LBS), .LSB(LSB), .IL(IL), .TAGW(TAGW), .XD(XD), .NBEAT(NBEAT), .TCK(TCK),
                                 .NMG(NMG), .A1B(A1B), .A2B(A2B)) u_lh (
            .clk(clk), .rst_n(rst_n), .xs_a1(xs_a1[j*A1B +: A1B]), .xs_g1(xs_g1[j*5 +: 5]),
            .xs_a2(xs_a2[j*A2B +: A2B]), .xs_g2(xs_g2[j*5 +: 5]), .rl1(rl1), .bk1(bk1), .ohl1(ohl1),
            .gv(gv), .gf(gf), .gy(gy), .gt(gt));
`else
        // (m3e) the leaf's row copy one register deeper (+1 on every read), matching the x-write copy's bk2 below
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl2 (.clk(clk), .rst_n(rr[j]),
            .d(rl1), .q(rl));
        // (m3e) the leaf's x-write copy registered again inside the leaf before the strap rotation (tile_e c2: the
        // pin landing u_bkd -> 8:1 rotation -> bf0 / blk0 -92 / -84 ps, 10-12 levels): +1 on the write, matched above
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkv2 (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(bk1[BBW-1]),
            .q(bk[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkd2 (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(bk1[BBW-2:0]),
            .q(bk[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohl2 (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(ohl1), .q(ohl));   // (m3e) +1 with bk2
        genvar gi;
        for (gi = 0; gi < NG; gi = gi + 1) begin : g_ohr
            ot_hbm_accel_smh_kreg #(.W(NBEAT)) u (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d(ohl),
                .q(ohr[gi*NBEAT +: NBEAT]));
        end
        wire gv, gf; wire [31:0] gy; wire [TAGW-1:0] gt;
        ot_hbm_accel_smh_leaf #(.LBS(LBS), .LSB(LSB), .IL(IL), .TAGW(TAGW), .XD(XD), .NBEAT(NBEAT), .TCK(TCK),
                                .NMG(NMG), .A1B(A1B), .A2B(A2B)) u_leaf (
            .clk(clk), .rst_n(rr[j]), .xs_a1(xs_a1[j*A1B +: A1B]), .xs_g1(xs_g1[j*5 +: 5]),
            .xs_a2(xs_a2[j*A2B +: A2B]), .xs_g2(xs_g2[j*5 +: 5]),
            .c_l(rl[RBW-1 -: CW]), .w_l(rl[XW+1 +: WSW]), .x_ce(rl[XW]), .x_a(rl[XW-1:0]),
            .b_en(bk[BBW-1]), .b_a(bk[BBW-2 -: XW]), .b_d(bk[2047:0]), .ohr(ohr),
            .gv(gv), .gf(gf), .gy(gy), .gt(gt));
`endif
        // own rows on lanes 0..RPT-1 (lane RPT-1-j = row j): (margin m2) G1 then a launch register at the gout pins
        // (+1 on every gather lane alike: the back end's deskew is unchanged)
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_gov (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d({gv, gf}),
            .q(gout[(RPT-1-j)*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_god (.clk(clk), .rst_n(rr[j]), .en(1'b1), .d({gy, gt}),
            .q(gout[(RPT-1-j)*GLW +: GLW-2]));
    end
    // lanes from the tile above moved down one
    // pass-through G1 lanes: two registers across the 510 um tile (landing, then launch), the back end's
    // deskew accounts for 2 per tile hop
    for (ln = RPT; ln < SUB; ln = ln + 1) begin : g_gl
        wire [GLW-1:0] gm;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(rr[RPT+1]), .en(1'b1),
            .d(gin[(ln-RPT)*GLW + GLW - 2 +: 2]), .q(gm[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d (.clk(clk), .rst_n(rr[RPT+1]), .en(1'b1),
            .d(gin[(ln-RPT)*GLW +: GLW-2]), .q(gm[0 +: GLW-2]));
        wire [GLW-1:0] gn;                    // (round 5) a third register: 510 um is more than two spans
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v2 (.clk(clk), .rst_n(rr[RPT+1]), .en(1'b1),
            .d(gm[GLW-2 +: 2]), .q(gn[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d2 (.clk(clk), .rst_n(rr[RPT+1]), .en(1'b1),
            .d(gm[0 +: GLW-2]), .q(gn[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v3 (.clk(clk), .rst_n(rr[RPT+1]), .en(1'b1),
            .d(gn[GLW-2 +: 2]), .q(gout[ln*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d3 (.clk(clk), .rst_n(rr[RPT+1]), .en(1'b1),
            .d(gn[0 +: GLW-2]), .q(gout[ln*GLW +: GLW-2]));
    end endgenerate
`endif
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
`ifdef OT_SMH_HIER
    input  wire                     rst_a,          // raw port reset: the leaf and each column relay it locally
`else
    input  wire                     rst_n,
`endif
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
`ifdef OT_SMH_HIER
    // el1011-hbm-smh: the hierarchical leaf FRONT (hardened inside ot_hbm_accel_smh_xs) ends at the operand (i) stage
    output wire                     o_iv_b,
    output wire                     o_iv_f,
    output wire                     o_ifirst,
    output wire                     o_ilast,
    output wire                     o_ifp4,
    output wire [TAGW-1:0]          o_itag,
    output wire [LBS*266+LSB*16-1:0] o_iw,
    output wire [LBS*266+LSB*16-1:0] o_ix
`else
    output wire                     gv,
    output wire                     gf,
    output wire [31:0]              gy,
    output wire [TAGW-1:0]          gt
`endif
);
`ifdef OT_SMH_HIER
    wire rst_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rst_n));
`else
    assign rst_n = rst_a;
`endif
`endif
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
    // STRAP FAN-OUT TREE (el1011-hbm-smmv-b 2026-10-12; smh_xs ref_tile FLOORPLAN_MARGIN refusal: port xs_a1[6] drove
    // 3,567 loads, xs_a2[5] 3,139 -- every rotation shifter of the beat hung on the raw strap pins).  The offsets are
    // STATIC straps, so they are pin-flopped (a?p) and fanned out through a registered tree: pin flop -> 8 kept mid
    // copies -> one kept copy per 64-bit output chunk of each rotation stage (stage 0, h, l, carry mask) => <= ~64 mux
    // loads a copy, <= 8 / <= 7 flop loads on the tree levels.  The data path latency is UNCHANGED (no beat stage
    // added); the straps settle 3 edges after power-up, long before reset releases the first beat.
    localparam integer CK  = 64;
    localparam integer N0K = (NBK + 255 + CK - 1) / CK, N0F = (NBF + 255 + CK - 1) / CK;
    localparam integer NHK = (NBK + 63 + CK - 1) / CK,  NHF = (NBF + 63 + CK - 1) / CK;
    localparam integer NLK = (NBK + CK - 1) / CK,       NLF = (NBF + CK - 1) / CK;
    localparam integer NA1 = N0K + NHK + 2 * NLK, NA2 = N0F + NHF + 2 * NLF;
    (* keep *) reg [10:0] a1p;
    (* keep *) reg [10:0] a2p;
    (* keep *) reg [4:0] g1p;
    (* keep *) reg [4:0] g2p;
    always @(posedge clk) begin a1p <= {xs_a1, {G1S{1'b0}}}; a2p <= {xs_a2, {G2S{1'b0}}}; g1p <= xs_g1; g2p <= xs_g2; end
    wire [8*11-1:0] a1m, a2m;
    wire [NA1*11-1:0] a1c;
    wire [NA2*11-1:0] a2c;
    genvar sk;
    generate for (sk = 0; sk < 8; sk = sk + 1) begin : g_sm
        (* keep *) reg [10:0] q1;
        (* keep *) reg [10:0] q2;
        always @(posedge clk) begin q1 <= a1p; q2 <= a2p; end
        assign a1m[sk*11 +: 11] = q1; assign a2m[sk*11 +: 11] = q2;
    end endgenerate
    generate for (sk = 0; sk < NA1; sk = sk + 1) begin : g_s1
        (* keep *) reg [10:0] q;
`ifdef OT_SMH_MUT_SFAN
        // negative control: stage-0 chunk 0's copy rotates by one 256-b step too far
        always @(posedge clk) q <= a1m[(sk % 8)*11 +: 11] + ((sk == 0) ? 11'd256 : 11'd0);
`else
        always @(posedge clk) q <= a1m[(sk % 8)*11 +: 11];
`endif
        assign a1c[sk*11 +: 11] = q;
    end endgenerate
    generate for (sk = 0; sk < NA2; sk = sk + 1) begin : g_s2
        (* keep *) reg [10:0] q;
        always @(posedge clk) q <= a2m[(sk % 8)*11 +: 11];
        assign a2c[sk*11 +: 11] = q;
    end endgenerate
    wire [4095:0] dd = {b_d, b_d};
    // (round 5) W0: rotate by a[10:8]; W1: by a[7:6]; W2: by a[5:0] (each stage <= 8:1 / 4:1 / 64:1 muxes)
    localparam integer RM = 8;
    // stage 0 (a[10:8]): chunk c of the output from its own strap copy (dd is 4,096 b: every index stays in range)
    wire [N0K*CK-1:0] blk_0;
    wire [N0F*CK-1:0] bf_0;
    generate for (sk = 0; sk < N0K; sk = sk + 1) begin : g_r0k
        wire [10:0] a = a1c[sk*11 +: 11];
        assign blk_0[sk*CK +: CK] = dd[sk*CK + {a[10:RM], {RM{1'b0}}} +: CK];
    end endgenerate
    generate for (sk = 0; sk < N0F; sk = sk + 1) begin : g_r0f
        wire [10:0] a = a2c[sk*11 +: 11];
        assign bf_0[sk*CK +: CK] = dd[sk*CK + {a[10:RM], {RM{1'b0}}} +: CK];
    end endgenerate
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
    // stage h (a[7:6]) on zero-padded sources (the shift's zero fill), chunked as stage 0
    wire [NHK*CK+255:0] blk0x = {{(NHK*CK+256-(NBK+255)){1'b0}}, blk0};
    wire [NHF*CK+255:0] bf0x  = {{(NHF*CK+256-(NBF+255)){1'b0}}, bf0};
    wire [NHK*CK-1:0] blk_h;
    wire [NHF*CK-1:0] bf_h;
    generate for (sk = 0; sk < NHK; sk = sk + 1) begin : g_rhk
        wire [10:0] a = a1c[(N0K + sk)*11 +: 11];
        assign blk_h[sk*CK +: CK] = blk0x[sk*CK + {a[RM-1:RH], {RH{1'b0}}} +: CK];
    end endgenerate
    generate for (sk = 0; sk < NHF; sk = sk + 1) begin : g_rhf
        wire [10:0] a = a2c[(N0F + sk)*11 +: 11];
        assign bf_h[sk*CK +: CK] = bf0x[sk*CK + {a[RM-1:RH], {RH{1'b0}}} +: CK];
    end endgenerate
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
        (* keep *) reg [4:0] g0;                                // per-group kept copy of the static strap (fan-out)
        always @(posedge clk) g0 <= (b < NG1) ? g1p : g2p;
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
    // stage l (a[5:0]) and the carry mask (1 where the field bit is in beat g + 1), chunked as stage 0
    wire [NLK*CK+63:0] blk1x = {{(NLK*CK+64-(NBK+63)){1'b0}}, blk1};
    wire [NLF*CK+63:0] bf1x  = {{(NLF*CK+64-(NBF+63)){1'b0}}, bf1};
    wire [NLK*CK-1:0] blk_l, blk_c;
    wire [NLF*CK-1:0] bf_l, bf_c;
    generate for (sk = 0; sk < NLK; sk = sk + 1) begin : g_rlk
        wire [10:0] a = a1c[(N0K + NHK + sk)*11 +: 11];
        wire [10:0] ac = a1c[(N0K + NHK + NLK + sk)*11 +: 11];
        assign blk_l[sk*CK +: CK] = blk1x[sk*CK + a[RH-1:0] +: CK];
        for (genvar ci = 0; ci < CK; ci = ci + 1) begin : g_c
            assign blk_c[sk*CK + ci] = ({21'd0, ac} + 32'(sk*CK + ci)) >= 32'd2048;
        end
    end endgenerate
    generate for (sk = 0; sk < NLF; sk = sk + 1) begin : g_rlf
        wire [10:0] a = a2c[(N0F + NHF + sk)*11 +: 11];
        wire [10:0] ac = a2c[(N0F + NHF + NLF + sk)*11 +: 11];
        assign bf_l[sk*CK +: CK] = bf1x[sk*CK + a[RH-1:0] +: CK];
        for (genvar ci = 0; ci < CK; ci = ci + 1) begin : g_c
            assign bf_c[sk*CK + ci] = ({21'd0, ac} + 32'(sk*CK + ci)) >= 32'd2048;
        end
    end endgenerate
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
        // [cg-smt] 2026-10-10 OT_SMH_XLK: a NEGEDGE lockup stage between the kept pin registers and the macro (same values,
        // same edge at the macro: posedge kreg at t -> negedge at t+0.5 -> macro at t+1; 0 cycles).  Root cause
        // (hbm_smh_tile_wg_cg-a6d34a72e smtc cal, FF): the macro clock pin sits 59 ps after its pin registers
        // (shared macro leaf net, 281 ps slew) + 47 ps library hold -> r_addr_in / w_mask_in hold -55..-84 ps that
        // repair could not buffer; the negedge launch gives the macro inputs a half-cycle hold window (setup slack
        // at these pins was +668 ps TT, so half a cycle is free).
        wire          rce3, wce3;
        wire [XW-1:0] ra3, wa3;
        wire [255:0]  wd3, wm3;
`ifdef OT_SMH_XLK
        reg           rce_n, wce_n;
        reg  [XW-1:0] ra_n, wa_n;
        reg  [255:0]  wd_n3, wm_n3;
        always @(negedge clk or negedge rst_n)
            if (!rst_n) begin rce_n <= 1'b0; wce_n <= 1'b0; end
            else begin rce_n <= rce2; wce_n <= wce2; end
        always @(negedge clk) begin ra_n <= ra2; wa_n <= wa2; wd_n3 <= wd2; wm_n3 <= wm2; end
        assign rce3 = rce_n; assign wce3 = wce_n; assign ra3 = ra_n; assign wa3 = wa_n; assign wd3 = wd_n3; assign wm3 = wm_n3;
`else
        assign rce3 = rce2; assign wce3 = wce2; assign ra3 = ra2; assign wa3 = wa2; assign wd3 = wd2; assign wm3 = wm2;
`endif
        ot_sram_1r1w_128x256_m1_r2c2 u_x (
            .clk(clk), .r_ce_in(rce3), .r_addr_in(ra3), .rd_out(xrd[256*m +: 256]),
            .w_ce_in(wce3), .w_addr_in(wa3), .wd_in(wd3), .w_mask_in(wm3),
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

`ifdef OT_SMH_HIER
    // el1011-hbm-smh OT_SMH_HIER: the columns and the G1 stage live in ot_hbm_accel_smh_leafh; the i stage is the
    // front's registered output (its j stage became the column input pin flops: 0 cycles)
    assign o_iv_b = iv_b; assign o_iv_f = iv_f; assign o_ifirst = ifirst; assign o_ilast = ilast; assign o_ifp4 = ifp4;
    assign o_itag = itag; assign o_iw = iw; assign o_ix = ix;
`else
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
`endif
`ifdef OT_SMH_MUT_BFDLY
    // negative-control mutant only (bench --mut-bfdly; never defined in a build): the BF16 column's output 64 cycles
    // late, so a BF16 -> block-dot op pair can collide at G1 / the stack (with c = 8 lines a row the real pipeline's
    // D difference, <= DBF + 4 SLAT = 39, is below the 57-cycle row span and the retire-order hazard is unreachable)
    wire [1+1+32+TAGW-1:0] mbf;
    ot_hdc_delay #(.W(2+32+TAGW), .D(64), .RESET(1)) u_mbf (.clk(clk), .rst_n(rst_n), .d({fov_r, ffault_r, fy_r, ftag_r}),
        .q(mbf));
    assign {fov, ffault, fy, ftag} = mbf;
`endif
`ifndef OT_SMH_HIER
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
`endif
endmodule

`ifdef OT_SMH_HIER
// a hardened master is a liberty cell (no parameters): synthesis instantiates it at its defaults (= the production
// configuration); simulation passes TAGW so the reduced bench configuration (RMAX 256: TAGW 12) elaborates the same RTL
`ifdef SYNTHESIS
`define OT_SMH_HP
`else
`define OT_SMH_HP #(.TAGW(TAGW))
`endif
// xs also takes NBEAT (x-write one-hot width: 13 at NC 8, 7 at the reduced bench's NC 4); default = production
`ifdef SYNTHESIS
`define OT_SMH_HPN
`else
`define OT_SMH_HPN #(.TAGW(TAGW), .NBEAT(NBEAT))
`endif
// ======== el1011-hbm-smh OT_SMH_HIER: the SM tile as a hierarchy of hardened sub-elements (2026-10-11) ========
// Textbook audit class 1: the flat tile was ONE clock root over 129.6k sinks (363 x 510 um, 82.8k hold endpoints,
// 134k hold buffers).  Every hardened sub-element below has its own clock tree (<= ~15k sinks), its own reset relay
// on the raw port reset (2 + 1: every register releases on the same edge as before), pin flops on every input and
// register-driven outputs.  Hardened masters (a liberty blackbox has no parameters: instantiated at their defaults =
// the production configuration): pt_w / pt_e (the pass-through band and every leaf landing), xs (leaf front: landing
// pin flops, strap rotation, 4 x-store SRAMs, operand registers), bdc (2 block-dot lanes), tcl (8 BF16 lanes), tct
// (the 16-lane BF16 tree).  The tile top keeps the ICG, the gather lanes
// and the G1 select.  0 cycles anywhere: registers change physical owner only.

// ---- the leaf (flattened in the tile top): xs -> {bdc, tcc} -> G1 ----
module ot_hbm_accel_smh_leafh #(
    parameter integer LBS = 2, parameter integer LSB = 16, parameter integer IL = 8, parameter integer TAGW = 16,
    parameter integer XD = 128, parameter integer NBEAT = 13, parameter integer TCK = 1, parameter integer NMG = 32,
    parameter integer A1B = 9, parameter integer A2B = 7
) (
    input  wire clk, input wire rst_n,
    input  wire [A1B-1:0] xs_a1, input wire [4:0] xs_g1, input wire [A2B-1:0] xs_a2, input wire [4:0] xs_g2,
    input  wire [6+TAGW+LBS*266+LSB*16+1+$clog2(XD)-1:0] rl1,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]            bk1,
    input  wire [NBEAT-1:0]                              ohl1,
    output wire gv, output wire gf, output wire [31:0] gy, output wire [TAGW-1:0] gt
);
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    wire [LBS*266+LSB*16-1:0] iw, ix;
`ifdef OT_SMH_RSTPIN
    // el1013-smh-r11: the leaf band's reset copy lands in one kept register per consumer (x store, block-dot column, the
    // three BF16 column tiles, the G1 select), each beside its consumer's rst_a pin
    (* keep *) reg [4:0] rq;
    always @(posedge clk) rq <= {5{rst_n}};
    wire r_xs = rq[0], r_bdc = rq[1], r_tcc = rq[2], r_g = rq[3], r_x = rq[4];
`else
    wire r_xs = rst_n, r_bdc = rst_n, r_tcc = rst_n, r_g = rst_n, r_x = rst_n;
`endif
    ot_hbm_accel_smh_xs `OT_SMH_HPN u_xs (.clk(clk), .rst_a(r_xs), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rl1(rl1), .bk1(bk1), .ohl1(ohl1), .o_iv_b(iv_b), .o_iv_f(iv_f), .o_ifirst(ifirst), .o_ilast(ilast),
        .o_ifp4(ifp4), .o_itag(itag), .o_iw(iw), .o_ix(ix), .o_ifirst_e(ifirst_e), .o_ilast_e(ilast_e), .o_itag_e(itag_e));
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
`ifdef OT_SMH_XREL
    // el1013-smh-r15 OT_SMH_XREL (r14 --cts gate, sign-off reference: xs o_ix / o_iw -> tcl h1 i_x / i_w is 630-1,023 um of
    // wire between two hard children, -65 / -103 ps on 112 / 176 endpoints before repair, -95 after repair in r13; xs ->
    // bdc 693 um on 8): one leaf-owned register on EVERY operand / control bit between the x store and BOTH columns, at
    // fixed stations midway (xb_*: in the xs | bdc gap; xf_*: in the centre channel on the way to the BF16 columns).
    // +1 cycle on both columns alike, so the G1 select sees the same order; every leaf of every tile alike, so the
    // gather lanes and the front's result deskew are unchanged.
    reg xb_v, xf_v, xb_first, xb_last, xb_fp4, xf_first, xf_last;
    reg [TAGW-1:0] xb_tag, xf_tag;
    reg [LBS*266-1:0] xb_w, xb_x;
    reg [LSB*16-1:0] xf_w, xf_x;
    always @(posedge clk or negedge r_x)
        if (!r_x) begin xb_v <= 1'b0; xf_v <= 1'b0; end
        else begin xb_v <= iv_b; xf_v <= iv_f; end
    always @(posedge clk) begin
        xb_first <= ifirst; xb_last <= ilast; xb_fp4 <= ifp4; xb_tag <= itag;
        xb_w <= iw[0 +: LBS*266]; xb_x <= ix[0 +: LBS*266];
        xf_first <= ifirst_e; xf_last <= ilast_e; xf_tag <= itag_e;
        xf_w <= iw[LBS*266 +: LSB*16]; xf_x <= ix[LBS*266 +: LSB*16];
    end
    ot_hbm_accel_smh_bdc `OT_SMH_HP u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(xb_v), .i_first(xb_first), .i_last(xb_last), .i_fp4(xb_fp4),
        .i_tag(xb_tag), .i_w(xb_w), .i_x(xb_x), .ov(bov), .y(by), .otag(btag), .fault(bfault));
    ot_hbm_accel_smh_tcc `OT_SMH_HP u_tcc (.clk(clk), .rst_a(r_tcc), .i_v(xf_v), .i_first(xf_first), .i_last(xf_last), .i_tag(xf_tag),
        .i_w(xf_w), .i_x(xf_x), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
`else
    ot_hbm_accel_smh_bdc `OT_SMH_HP u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(iv_b), .i_first(ifirst), .i_last(ilast), .i_fp4(ifp4),
        .i_tag(itag), .i_w(iw[0 +: LBS*266]), .i_x(ix[0 +: LBS*266]), .ov(bov), .y(by), .otag(btag), .fault(bfault));
    ot_hbm_accel_smh_tcc `OT_SMH_HP u_tcc (.clk(clk), .rst_a(r_tcc), .i_v(iv_f), .i_first(ifirst_e), .i_last(ilast_e), .i_tag(itag_e),
        .i_w(iw[LBS*266 +: LSB*16]), .i_x(ix[LBS*266 +: LSB*16]), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
`endif
    // G1: select by the producing column, registered (was the leaf's last stage)
    wire g_n;
`ifdef OT_SMH_RSTPIN
    assign g_n = r_g;
`elsif OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(g_n));
`else
    assign g_n = rst_n;
`endif
    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(posedge clk or negedge g_n)
        if (!g_n) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= bov | fov; gf_q <= bfault | ffault | (bov & fov); end
    always @(posedge clk) begin gy_q <= bov ? by : fy; gt_q <= bov ? btag : ftag; end
    assign gv = gv_q; assign gf = gf_q; assign gy = gy_q; assign gt = gt_q;
endmodule

// ---- xs: the leaf front (HARDENED): landing pin flops, strap rotation, x store, operand registers ----
module ot_hbm_accel_smh_xs #(parameter integer TAGW = 16, parameter integer NBEAT = 13) (
    input  wire clk, input wire rst_a,
    input  wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input  wire [6+TAGW+788+1+7-1:0] rl1, input wire [7+NBEAT+2048:0] bk1, input wire [NBEAT-1:0] ohl1,
    output wire o_iv_b, output wire o_iv_f, output wire o_ifirst, output wire o_ilast, output wire o_ifp4,
    output wire [TAGW-1:0] o_itag, output wire [787:0] o_iw, output wire [787:0] o_ix,
    // the BF16 column's copies of the shared control (E face; the block-dot column takes the W-face copies)
    output wire o_ifirst_e, output wire o_ilast_e, output wire [TAGW-1:0] o_itag_e
);
    localparam integer XW = 7, CW = 6 + TAGW, WSW = 788, RBW = CW + WSW + 1 + XW, BBW = 1 + XW + NBEAT + 2048, NG = 25;
    assign o_ifirst_e = o_ifirst; assign o_ilast_e = o_ilast; assign o_itag_e = o_itag;
    wire rl_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rl_n));
`else
    assign rl_n = rst_a;
`endif
    // input lockups (el1011-hbm-smh, xs -cal route: -72 ps hold at the u_bkd2 landing, TNS -54 ns): the 2,900 landing bits
    // hop 21.6 um from pt_w's posedge launch flops on a DIFFERENT clock tree; a NEGEDGE stage at the pins gives every bit a
    // half-cycle hold window whatever the tree skew (posedge t -> negedge t + 0.5 -> posedge t + 1: 0 cycles; setup has
    // ~385 ps for the 22 um hop).  Data-only registers (the posedge stage behind them keeps the valid resets).
    // (round 4, xs ilk route b911713a2: TT -104.8 ps) the negedge lockups cost half a cycle and their 2,900-sink branch
    // clocked ~170 ps after the capture flops -> replaced by a deterministic hold-delay stage on each landing bit
    // (ot_hdly, 2 x HB4xp67 ~76 ps FF, dont_touch'ed by physical/qwen_die_masters/hdly_dont_touch.tcl at PRE_FLOORPLAN):
    // full-cycle setup, hold window independent of the neighbour's tree; a wire in simulation (0 cycles)
    wire [RBW-1:0] rl1_n; wire [BBW-1:0] bk1_n; wire [NBEAT-1:0] ohl1_n;
    ot_hdly #(.W(RBW), .N(2)) u_hdly_rl (.a(rl1), .y(rl1_n));
    ot_hdly #(.W(BBW), .N(2)) u_hdly_bk (.a(bk1), .y(bk1_n));
    ot_hdly #(.W(NBEAT), .N(2)) u_hdly_oh (.a(ohl1), .y(ohl1_n));
    // the input pin flops (the tile's second landing: u_rl2 / u_bkv2 / u_bkd2 / u_ohl2 + the one-hot replicas)
    wire [RBW-1:0] rl;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl2 (.clk(clk), .rst_n(rl_n), .d(rl1_n), .q(rl));
    wire [BBW-1:0] bk;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkv2 (.clk(clk), .rst_n(rl_n), .en(1'b1), .d(bk1_n[BBW-1]), .q(bk[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkd2 (.clk(clk), .rst_n(rl_n), .en(1'b1), .d(bk1_n[BBW-2:0]), .q(bk[BBW-2:0]));
    wire [NBEAT-1:0] ohl;
    wire [NG*NBEAT-1:0] ohr;
    ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohl2 (.clk(clk), .rst_n(rl_n), .en(1'b1), .d(ohl1_n), .q(ohl));
    genvar gi;
    generate for (gi = 0; gi < NG; gi = gi + 1) begin : g_ohr
        ot_hbm_accel_smh_kreg #(.W(NBEAT)) u (.clk(clk), .rst_n(rl_n), .en(1'b1), .d(ohl), .q(ohr[gi*NBEAT +: NBEAT]));
    end endgenerate
    ot_hbm_accel_smh_leaf #(.TAGW(TAGW), .NBEAT(NBEAT)) u_leaf (
        .clk(clk), .rst_a(rst_a), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .c_l(rl[RBW-1 -: CW]), .w_l(rl[XW+1 +: WSW]), .x_ce(rl[XW]), .x_a(rl[XW-1:0]),
        .b_en(bk[BBW-1]), .b_a(bk[BBW-2 -: XW]), .b_d(bk[2047:0]), .ohr(ohr),
        .o_iv_b(o_iv_b), .o_iv_f(o_iv_f), .o_ifirst(o_ifirst), .o_ilast(o_ilast), .o_ifp4(o_ifp4), .o_itag(o_itag),
        .o_iw(o_iw), .o_ix(o_ix));
endmodule

// the block-dot column: the leaf's j stage as input pin flops, then ot_hbm_accel_smh_bd_col (unchanged)
module ot_hbm_accel_smh_bdc #(parameter integer LBS = 2, parameter integer IL = 8, parameter integer TAGW = 16) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_first, input wire i_last, input wire i_fp4, input wire [TAGW-1:0] i_tag,
    input  wire [LBS*266-1:0] i_w, input wire [LBS*266-1:0] i_x,
    output wire ov, output wire [31:0] y, output wire [TAGW-1:0] otag, output wire fault
);
    wire rst_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rst_n));
`else
    assign rst_n = rst_a;
`endif
    reg jv, jfirst, jlast, jfp4;
    reg [TAGW-1:0] jtag;
    reg [LBS*266-1:0] jw, jx;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) jv <= 1'b0;
        else jv <= i_v;
    always @(posedge clk) begin jfirst <= i_first; jlast <= i_last; jfp4 <= i_fp4; jtag <= i_tag; jw <= i_w; jx <= i_x; end
    wire [LBS*256-1:0] xq_s;
    wire [LBS*10-1:0]  xe_s;
    genvar qq;
    generate for (qq = 0; qq < LBS; qq = qq + 1) begin : g_bx
        assign xq_s[256*qq +: 256] = jx[qq*266 +: 256];
        assign xe_s[10*qq +: 10]   = jx[qq*266 + 256 +: 10];
    end endgenerate
    ot_hbm_accel_smh_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
        .clk(clk), .rst_n(rst_n), .v(jv), .first(jfirst), .last(jlast), .fp4(jfp4), .tag(jtag),
        .wq(jw[0 +: LBS*256]), .we(jw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
        .ov(ov), .y(y), .otag(otag), .fault(fault));
endmodule

// the BF16 column (flattened wrapper): two hardened 8-lane halves (tcl) and the hardened 16-lane tree (tct).  The
// lane sums launch from sum_q in tcl and land in sum_q2 as tct's input pin flops (the two registers of tc_col);
// every half keeps its own copy of the control pipeline (bit-identical kept copies).
module ot_hbm_accel_smh_tcc #(parameter integer TAGW = 16) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_first, input wire i_last, input wire [TAGW-1:0] i_tag,
    input  wire [255:0] i_w, input wire [255:0] i_x,
    output wire ov, output wire [31:0] y, output wire [TAGW-1:0] otag, output wire fault
);
    wire [255:0] s0, s1;
    wire lf0, lf1;
    ot_hbm_accel_smh_tcl u_h0 (.clk(clk), .rst_a(rst_a), .i_v(i_v), .i_first(i_first), .i_w(i_w[0 +: 128]),
        .i_x(i_x[0 +: 128]), .sum_o(s0), .lfault(lf0));
    ot_hbm_accel_smh_tcl u_h1 (.clk(clk), .rst_a(rst_a), .i_v(i_v), .i_first(i_first), .i_w(i_w[128 +: 128]),
        .i_x(i_x[128 +: 128]), .sum_o(s1), .lfault(lf1));
    ot_hbm_accel_smh_tct `OT_SMH_HP u_tr (.clk(clk), .rst_a(rst_a), .i_v(i_v), .i_last(i_last), .i_tag(i_tag), .sum_i({s1, s0}),
        .lf_a(lf0), .lf_b(lf1), .ov(ov), .y(y), .otag(otag), .fault(fault));
endmodule

// tcl: 8 BF16 lanes of ot_hbm_accel_smh_tc_col (HARDENED), its j stage as the input pin flops
module ot_hbm_accel_smh_tcl #(parameter integer L = 8, parameter integer IL = 8, parameter integer ALAT = 7) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_first, input wire [L*16-1:0] i_w, input wire [L*16-1:0] i_x,
    output wire [L*32-1:0] sum_o, output wire lfault
);
    localparam integer FB = IL - ALAT;
    localparam integer ML = 7;
    wire rst_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rst_n));
`else
    assign rst_n = rst_a;
`endif
    reg jv, jfirst;
    reg [L*16-1:0] jw, jx;
    always @(posedge clk or negedge rst_n) if (!rst_n) jv <= 1'b0; else jv <= i_v;
    always @(posedge clk) begin jfirst <= i_first; jw <= i_w; jx <= i_x; end
    reg v_q, first_q, v_q2, first_q2;
    reg [L-1:0] v_ql;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v_q <= 1'b0; first_q <= 1'b0; v_q2 <= 1'b0; first_q2 <= 1'b0; v_ql <= {L{1'b0}}; end
        else begin v_q <= jv; first_q <= jv && jfirst; v_q2 <= v_q; first_q2 <= first_q; v_ql <= {L{v_q}}; end
    end
    always @(posedge clk) begin w_q <= jw; x_q <= jx; end
    wire [ML:0] fl, vl;
    ot_hdc_vline #(.D(ML)) u_f (.clk(clk), .rst_n(rst_n), .v(first_q2), .vd(fl));
    ot_hdc_vline #(.D(ML)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q2), .vd(vl));
    wire [L*32-1:0] sum;
    reg  [L*32-1:0] sum_q;
    wire [L-1:0] lf;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        reg  [15:0] w_l, x_l;
        wire f0, f1;
        always @(posedge clk) begin w_l <= w_q[16*l +: 16]; x_l <= x_q[16*l +: 16]; end
        ot_hbm_accel_smh_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q2), .kill(!v_ql[l]), .a({w_l, 16'd0}),
                                     .b({x_l, 16'd0}), .y(prod), .fault(f0));
        reg flc;
        always @(posedge clk or negedge rst_n) if (!rst_n) flc <= 1'b0; else flc <= fl[ML-2];
        always @(posedge clk) acc_q <= flc ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(vl[ML]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        always @(posedge clk) sum_q[32*l +: 32] <= sum[32*l +: 32];
        assign lf[l] = f0 | f1;
    end endgenerate
`ifdef OT_SMH_FACE_CLONE
    // PATH-HBM-SM 10-25 (face_guard R2): the sticky fault flop fed both its own hold path and the lfault pin (shared).
    // The pin gets its own kept copy with the same D and reset (lane_fault | |lf): cycle-exact, lane_fault keeps the
    // feedback.  Both are kept so synthesis cannot fold them back into one flop.
    (* keep *) reg lane_fault;
    (* keep *) reg lfault_k;
    always @(posedge clk or negedge rst_n) if (!rst_n) lane_fault <= 1'b0; else lane_fault <= lane_fault | (|lf);
    always @(posedge clk or negedge rst_n) if (!rst_n) lfault_k <= 1'b0; else lfault_k <= lane_fault | (|lf);
    assign sum_o = sum_q;
    assign lfault = lfault_k;
`else
    reg lane_fault;
    always @(posedge clk or negedge rst_n) if (!rst_n) lane_fault <= 1'b0; else lane_fault <= lane_fault | (|lf);
    assign sum_o = sum_q;
    assign lfault = lane_fault;
`endif
endmodule

// tct: the 16-lane tree of ot_hbm_accel_smh_tc_col (HARDENED); sum_q2 is its input pin register.  The sticky lane
// faults land on pin flops too (+1 edge on the sticky bit only: it is set >= ALAT + LL edges before any ov it affects).
module ot_hbm_accel_smh_tct #(parameter integer L = 16, parameter integer TAGW = 16, parameter integer ALAT = 7) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_last, input wire [TAGW-1:0] i_tag, input wire [L*32-1:0] sum_i,
    input  wire lf_a, input wire lf_b,
    output wire ov, output wire [31:0] y, output wire [TAGW-1:0] otag, output wire fault
);
    localparam integer ML = 7;
    localparam integer LL = ML + ALAT + 2;
    wire rst_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rst_n));
`else
    assign rst_n = rst_a;
`endif
    reg jv, jlast, lfa_q, lfb_q;
    reg [TAGW-1:0] jtag;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin jv <= 1'b0; lfa_q <= 1'b0; lfb_q <= 1'b0; end
        else begin jv <= i_v; lfa_q <= lf_a; lfb_q <= lf_b; end
    always @(posedge clk) begin jlast <= i_last; jtag <= i_tag; end
    reg v_q, last_q, last_q2;
    reg [TAGW-1:0] tag_q, tag_q2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; last_q <= 1'b0; last_q2 <= 1'b0; end
        else begin v_q <= jv; last_q <= jv && jlast; last_q2 <= last_q; end
    always @(posedge clk) begin tag_q <= jtag; tag_q2 <= tag_q; end
    wire [LL:0] ll;
    ot_hdc_vline #(.D(LL)) u_l (.clk(clk), .rst_n(rst_n), .v(last_q2), .vd(ll));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LL)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_q2), .q(tag_d));
    reg [L*32-1:0] sum_q2;
    always @(posedge clk) sum_q2 <= sum_i;
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(L), .TAGW(TAGW), .ALAT(ALAT)) u_tree (.clk(clk), .rst_n(rst_n), .v(ll[LL]), .d(sum_q2), .tag(tag_d),
                                             .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    reg ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin ov_q <= t_ov; fault_q <= lfa_q | lfb_q | tf; end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q; assign y = y_q; assign otag = otag_q; assign fault = fault_q;
endmodule

// ---- the pass-through band (HARDENED, two masters split across x so each spans the tile's full pin face) ----
// pt_w: landing (u_rp / u_bl) + the second register (u_rpm / u_blm) of both rows and the x-write beat, and every leaf
// landing (u_rl, u_bk, u_ohl): leaf 0's copies leave on the N face, leaf 1's on the S face
module ot_hbm_accel_smh_pt_w #(parameter integer TAGW = 16, parameter integer NBEAT = 13) (
    input wire clk, input wire rst_a, input wire [2*(6+TAGW+788+1+7)-1:0] rin, input wire [7+NBEAT+2048:0] bin,
    output wire [2*(6+TAGW+788+1+7)-1:0] rpm, output wire [7+NBEAT+2048:0] bm,
    output wire [6+TAGW+788+1+7-1:0] rl1_n, output wire [7+NBEAT+2048:0] bk1_n, output wire [NBEAT-1:0] ohl1_n,
    output wire [6+TAGW+788+1+7-1:0] rl1_s, output wire [7+NBEAT+2048:0] bk1_s, output wire [NBEAT-1:0] ohl1_s
);
    // output hold-delay stage (el1012-hbm T5, smh_pt_w_ref_p45-lf NEEDS_RTL FF -13.53 -> -4.53 after a 12,470-cell hold ECO):
    // every output is flop Q -> output buffer -> port (~75-85 ps FF), and the die-context output-min contract asks for
    // clk->port >= (L_min - L_launch) + 50 hold skew + 25 uncertainty; launch flops on the early leaves (287-295 ps vs the
    // 299 ps reference) miss by 3-14 ps on ~6,000 bits, a residue the post-route ECO cannot place in the above-only pin band.
    // One dont_touch'ed HB4xp67 per output bit (ot_hdly N=1, ~38 ps FF, spec route.hold_delay) is sender-owned hold by
    // construction inside this tile's own 0.2 T output budget (TT output setup +79.6 ps before it); a wire in simulation.
    localparam integer RBW_O = 6 + TAGW + 788 + 1 + 7, BBW_O = 7 + NBEAT + 2048 + 1;
    wire [2*RBW_O-1:0] rpm_q; wire [BBW_O-1:0] bm_q, bk1_n_q, bk1_s_q; wire [RBW_O-1:0] rl1_n_q, rl1_s_q;
    wire [NBEAT-1:0] ohl1_n_q, ohl1_s_q;
`ifdef OT_SMH_PTW_OHDLY
    localparam integer OHN = 1;
`else
    localparam integer OHN = 0;
`endif
    ot_hdly #(.W(2*RBW_O), .N(OHN)) u_hdly_orpm (.a(rpm_q), .y(rpm));
    ot_hdly #(.W(BBW_O), .N(OHN)) u_hdly_obm (.a(bm_q), .y(bm));
    ot_hdly #(.W(RBW_O), .N(OHN)) u_hdly_orln (.a(rl1_n_q), .y(rl1_n));
    ot_hdly #(.W(RBW_O), .N(OHN)) u_hdly_orls (.a(rl1_s_q), .y(rl1_s));
    ot_hdly #(.W(BBW_O), .N(OHN)) u_hdly_obkn (.a(bk1_n_q), .y(bk1_n));
    ot_hdly #(.W(BBW_O), .N(OHN)) u_hdly_obks (.a(bk1_s_q), .y(bk1_s));
    ot_hdly #(.W(NBEAT), .N(OHN)) u_hdly_oohn (.a(ohl1_n_q), .y(ohl1_n));
    ot_hdly #(.W(NBEAT), .N(OHN)) u_hdly_oohs (.a(ohl1_s_q), .y(ohl1_s));
    localparam integer CW = 6 + TAGW, XW = 7, RBW = CW + 788 + 1 + XW, BBW = 1 + XW + NBEAT + 2048;
    wire rw_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rw_n));
`else
    assign rw_n = rst_a;
`endif
    genvar j;
    generate for (j = 0; j < 2; j = j + 1) begin : g_r
        wire [RBW-1:0] rp;
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp (.clk(clk), .rst_n(rw_n), .d(rin[j*RBW +: RBW]), .q(rp));
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rpm (.clk(clk), .rst_n(rw_n), .d(rp), .q(rpm_q[j*RBW +: RBW]));
    end endgenerate
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rln (.clk(clk), .rst_n(rw_n), .d(rin[0 +: RBW]), .q(rl1_n_q));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rls (.clk(clk), .rst_n(rw_n), .d(rin[RBW +: RBW]), .q(rl1_s_q));
    wire [BBW-1:0] bl;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blv (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[BBW-1]), .q(bl[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bld (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[BBW-2:0]), .q(bl[BBW-2:0]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blvm (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bl[BBW-1]), .q(bm_q[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bldm (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bl[BBW-2:0]), .q(bm_q[BBW-2:0]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkvn (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[BBW-1]), .q(bk1_n_q[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkdn (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[BBW-2:0]), .q(bk1_n_q[BBW-2:0]));
    ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohln (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[2048 +: NBEAT]), .q(ohl1_n_q));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkvs (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[BBW-1]), .q(bk1_s_q[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkds (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[BBW-2:0]), .q(bk1_s_q[BBW-2:0]));
    ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohls (.clk(clk), .rst_n(rw_n), .en(1'b1), .d(bin[2048 +: NBEAT]), .q(ohl1_s_q));
endmodule
// pt_e: the third (u_rpn / u_bln) and launch (u_rp2 / u_bl2) registers
module ot_hbm_accel_smh_pt_e #(parameter integer TAGW = 16, parameter integer NBEAT = 13) (
    input wire clk, input wire rst_a, input wire [2*(6+TAGW+788+1+7)-1:0] rpm, input wire [7+NBEAT+2048:0] bm,
    output wire [2*(6+TAGW+788+1+7)-1:0] rout, output wire [7+NBEAT+2048:0] bout
);
    localparam integer CW = 6 + TAGW, XW = 7, RBW = CW + 788 + 1 + XW, BBW = 1 + XW + NBEAT + 2048;
    wire re_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(re_n));
`else
    assign re_n = rst_a;
`endif
    genvar j;
    generate for (j = 0; j < 2; j = j + 1) begin : g_r
        wire [RBW-1:0] rpn;
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rpn (.clk(clk), .rst_n(re_n), .d(rpm[j*RBW +: RBW]), .q(rpn));
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp2 (.clk(clk), .rst_n(re_n), .d(rpn), .q(rout[j*RBW +: RBW]));
    end endgenerate
    wire [BBW-1:0] bm4;
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blvn (.clk(clk), .rst_n(re_n), .en(1'b1), .d(bm[BBW-1]), .q(bm4[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bldn (.clk(clk), .rst_n(re_n), .en(1'b1), .d(bm[BBW-2:0]), .q(bm4[BBW-2:0]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_blv2 (.clk(clk), .rst_n(re_n), .en(1'b1), .d(bm4[BBW-1]), .q(bout[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bld2 (.clk(clk), .rst_n(re_n), .en(1'b1), .d(bm4[BBW-2:0]), .q(bout[BBW-2:0]));
endmodule
`undef OT_SMH_HP
`endif  // OT_SMH_HIER

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

// ---------------------------------------------------------------------------
// redesign-hbm 2026-10-09: COARSE CLOCK-GATED pieces (one ICG per hardened tile / back end, ot_cg_tile).  The piece
// netlist is unchanged (ot_hbm_accel_smh_tile / _be on the gated clock, x-store macros included); cgi lands in the
// gate's ungated pin flop, cgo forwards it.  _wg / _eg are the production masters (pin sides as _w / _e).
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_tile_g #(
    parameter integer SUB = 4, parameter integer RPT = 2, parameter integer LBS = 2, parameter integer LSB = 16,
    parameter integer NC = 8, parameter integer IL = 8, parameter integer TAGW = 16, parameter integer XD = 128,
    parameter integer NBEAT = 13, parameter integer TCK = 1, parameter integer NMG = 32, parameter integer A1B = 9,
    parameter integer A2B = 7, parameter integer PT4 = 1, parameter integer HOLD = `ifdef OT_SMH_CG_MUT_HOLD0 0 `else 64 `endif,
    parameter integer MUT_LATE = `ifdef OT_SMH_CG_MUT_LATE 32 `else 0 `endif,
    // [cg-smt] 2026-10-10 OT_SMH_CG_ENREG: the tile ICG's ENA from one register beside the gate (ot_cg_tile ENREG, 0 cycles).
    // Root cause (tile_wg cg a6d34a72e smtc cal): ENA from cnt / wq at leaf insertion 670 ps -> ICG CK at 217 ps over
    // 160 ps of wire (507 ps slew): TT setup -198 / -352 ps.
    parameter integer ENREG = `ifdef OT_SMH_CG_ENREG 1 `else 0 `endif
) (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo,
    input  wire [RPT*A1B-1:0] xs_a1, input wire [RPT*5-1:0] xs_g1, input wire [RPT*A2B-1:0] xs_a2, input wire [RPT*5-1:0] xs_g2,
    input  wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rin,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bin,
    output wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rout,
    output wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bout,
    input  wire [(SUB-RPT)*(2+32+TAGW)-1:0]                    gin,
    output wire [SUB*(2+32+TAGW)-1:0]                          gout
);
    wire gclk;
    // el1013-smh-r14 OT_SMH_PINREG: receiver-owned hold on the wake pin.  cgi lands in the two raw-clock registers beside
    // the clk pin (wq, en_r; clock arrival ~4 ps) through one input buffer: FF hold -37.5 ps against the class-0 boundary
    // reference (input min = the raw registers' own arrival), and the spine keeps those port-net cells fixed and
    // dont_touch, so hold repair stalled (r11 / r13 OT_HOLD_STALL I2R = 2).  Two kept HB4xp67 (ot_hdly, ~38 ps each at
    // FF) in front of both registers; identity in simulation.  TT setup: the wake has the full receiver share.
    wire cgi_h;
    ot_hdly #(.W(1), .N(
`ifdef OT_SMH_PINREG
        2
`else
        0
`endif
        )) u_hdly_cgi (.a(cgi), .y(cgi_h));
    // el1013-smh-r11 OT_SMH_RSTPIN: no reset on the raw clock (RSTEN 0, RAWRST 0); the wake holds the gate open in reset
    // (cg_en is high in reset: ot_hgi_sm_leaf resets it to 1 and each tile forwards it one raw register a hop), and the
    // reset itself enters the gated tile through its pin flop (ot_hbm_accel_smh_rst_tree).
    // RESET CONTRACT of the gated tile: rst_n low for >= 32 clk edges with cgi high (hops + pin flop + tree + child relays);
    // the tile's state leaves reset 9 edges after the port (tree 5/6 + child relay 3), inside the HOLD = 64 open window.
    ot_cg_tile #(.HOLD(HOLD), .MUT_LATE(MUT_LATE), .ENREG(ENREG)
`ifdef OT_SMH_RSTPIN
                 , .RSTEN(0), .RAWRST(0)
`endif
                 ) u_cgt (.clk(clk), .rst_n(rst_n), .cgi(cgi_h), .cgo(cgo), .gclk(gclk));
    // Static slice positions settle while reset holds the tile gate open.
    // Five regional stations avoid a raw north-face wire crossing the cluster.
    localparam integer STRAPW = A1B + 5 + A2B + 5;
    wire [RPT*A1B-1:0] sx_a1;
    wire [RPT*5-1:0] sx_g1, sx_g2;
    wire [RPT*A2B-1:0] sx_a2;
    genvar sr;
    generate for (sr = 0; sr < RPT; sr = sr + 1) begin : g_strap
        wire [STRAPW-1:0] d = {xs_g2[sr*5 +: 5], xs_a2[sr*A2B +: A2B],
                                  xs_g1[sr*5 +: 5], xs_a1[sr*A1B +: A1B]};
        wire [STRAPW-1:0] q;
        ot_hbm_accel_smh_strap_region #(.W(STRAPW),
            .MUT(`ifdef OT_SMH_MUT_STRAP_REGION (sr == 1) `else 0 `endif)) u_sr (.clk(gclk), .d(d), .q(q));
        assign {sx_g2[sr*5 +: 5], sx_a2[sr*A2B +: A2B],
                sx_g1[sr*5 +: 5], sx_a1[sr*A1B +: A1B]} = q;
    end endgenerate
    ot_hbm_accel_smh_tile #(.SUB(SUB), .RPT(RPT), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW), .XD(XD),
                            .NBEAT(NBEAT), .TCK(TCK), .NMG(NMG), .A1B(A1B), .A2B(A2B), .PT4(PT4)) u (
        .clk(gclk), .rst_n(rst_n), .xs_a1(sx_a1), .xs_g1(sx_g1), .xs_a2(sx_a2), .xs_g2(sx_g2), .rin(rin), .bin(bin),
        .rout(rout), .bout(bout), .gin(gin), .gout(gout));
endmodule
module ot_hbm_accel_smh_be_g #(
    parameter integer SUB = 4, parameter integer RPT = 2, parameter integer IL = 8, parameter integer RMAX = 4096,
    parameter integer LEV = 4, parameter integer TAGW = 16, parameter integer NH = 4, parameter integer HOLD = `ifdef OT_SMH_CG_MUT_HOLD0 0 `else 64 `endif,
    parameter integer MUT_LATE = `ifdef OT_SMH_CG_MUT_LATE 32 `else 0 `endif
) (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo,
    input  wire [SUB*(2+32+TAGW)-1:0]          gin,
    input  wire [(NH-1)*(2+32+$clog2(RMAX))-1:0] qin,
    output wire [NH*(2+32+$clog2(RMAX))-1:0]     qout
);
    wire gclk;
    ot_cg_tile #(.HOLD(HOLD), .MUT_LATE(MUT_LATE)) u_cgt (.clk(clk), .rst_n(rst_n), .cgi(cgi), .cgo(cgo), .gclk(gclk));
    ot_hbm_accel_smh_be #(.SUB(SUB), .RPT(RPT), .IL(IL), .RMAX(RMAX), .LEV(LEV), .TAGW(TAGW), .NH(NH)) u (
        .clk(gclk), .rst_n(rst_n), .gin(gin), .qin(qin), .qout(qout));
endmodule
module ot_hbm_accel_smh_tile_eg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo,
    input  wire [17:0] xs_a1, input wire [9:0] xs_g1, input wire [13:0] xs_a2, input wire [9:0] xs_g2,
    input  wire [1635:0] rin, input wire [2068:0] bin, output wire [1635:0] rout, output wire [2068:0] bout,
    input  wire [99:0] gin, output wire [199:0] gout
);
    ot_hbm_accel_smh_tile_g u (.*);
endmodule
module ot_hbm_accel_smh_tile_wg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo,
    input  wire [17:0] xs_a1, input wire [9:0] xs_g1, input wire [13:0] xs_a2, input wire [9:0] xs_g2,
    input  wire [1635:0] rin, input wire [2068:0] bin, output wire [1635:0] rout, output wire [2068:0] bout,
    input  wire [99:0] gin, output wire [199:0] gout
);
    ot_hbm_accel_smh_tile_g u (.*);
endmodule
module ot_hbm_accel_smh_be_eg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo, input wire [199:0] gin, input wire [137:0] qin,
    output wire [183:0] qout
);
    ot_hbm_accel_smh_be_g u (.*);
endmodule
module ot_hbm_accel_smh_be_wg (
    input  wire clk, input wire rst_n, input wire cgi, output wire cgo, input wire [199:0] gin, input wire [137:0] qin,
    output wire [183:0] qout
);
    ot_hbm_accel_smh_be_g u (.*);
endmodule

// Optional gated-result consumer qualification, sized before RTL in
// results/uarch/smh_result_valid_20261010/model.json. No arithmetic or latency changes.
// ENABLE=0 preserves the released south-front valid/fault contract exactly.
module ot_hbm_accel_smh_result_valid #(
    parameter integer NC = 8,
    parameter integer ENABLE = 0
) (
    input wire [NC-1:0] valids,
    input wire [NC-1:0] faults,
    output wire row_valid,
    output wire fault_event
);
    wire all_valid = &valids;
    wire partial_valid = (|valids) && !all_valid;
    assign row_valid = ENABLE ? all_valid : valids[0];
    assign fault_event = ENABLE ? ((|(faults & valids)) | partial_valid) : (|faults);
endmodule

// Static configuration only: reset keeps the cluster gate open for startup; no data-path cycle added.
// ---------------------------------------------------------------------------
// el1013-smh-r11 (2026-10-13) ot_hbm_accel_smh_rst_tree: the hierarchical SM tile's registered reset distribution.
// Why (r10 CTS diagnosis B1): one rst_n pin on the N face fanned combinationally over a 630 x 1,253 um tile in one cycle
// (-> the ICG ENA -2,360 ps over ~1,200 um and 897 ps of buffers; -> u_rr / the children's rst_a 400-800 ps).
// What: p0 = the pin flop (the port's ONLY load); a trunk of plain registers on the tile clock runs N -> S, one station a
// band (physical spec: stations fixed in the landing channels, <= ~350 um a stage); every output is a kept register at
// depth 5 from the port, so all bands assert and release on the same edge:
//   north (leaf 0):  p0 -> n1 -> n2 -> n3 -> {gn, lhn}
//   mid (pt_w/pt_e): p0 -> t1 -> m2 -> m3 -> {gm, ptw, pte}
//   south (leaf 1):  p0 -> t1 -> t2 -> s3 -> {gs, lhs}
// No reset on these registers (they ARE the reset); assertion and release are both synchronous, the children keep their
// own asynchronous-assert / 3-edge-release relay behind rst_a.  Active low throughout.
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_rst_tree (
    input  wire clk, input wire rst_n,
    output wire gn, output wire lhn, output wire gm, output wire ptw, output wire pte, output wire gs, output wire lhs
);
    (* keep *) reg p0, n1, n2, n3, t1, t2, m2, m3, s3;
    (* keep *) reg f_gn, f_lhn, f_gm, f_ptw, f_pte, f_gs, f_lhs;
    always @(posedge clk) begin
        p0 <= rst_n;
        n1 <= p0; n2 <= n1; n3 <= n2;
        t1 <= p0; t2 <= t1;
        m2 <= t1; m3 <= m2;
        s3 <= t2;
        f_gn <= n3; f_lhn <= n3;
        f_gm <= m3; f_ptw <= m3; f_pte <= m3;
        f_gs <= s3; f_lhs <= s3;
    end
    assign gn = f_gn; assign lhn = f_lhn; assign gm = f_gm; assign ptw = f_ptw; assign pte = f_pte;
    assign gs = f_gs; assign lhs = f_lhs;
endmodule

module ot_hbm_accel_smh_strap_region #(parameter integer W = 26, parameter integer MUT = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q
);
    (* keep *) reg [W-1:0] s0, s1, s2, s3, s4;
    always @(posedge clk) begin
        s0 <= d; s1 <= s0; s2 <= s1; s3 <= s2; s4 <= s3;
    end
    // Negative control corrupts one offset bit at the final regional station.
    assign q = s4 ^ {{(W-1){1'b0}}, (MUT != 0)};
endmodule
