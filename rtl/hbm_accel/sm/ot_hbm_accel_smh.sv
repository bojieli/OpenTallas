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
    parameter integer RPT  = 2          // leaves (rows) per hardened tile
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
    initial if (NC < 4 || SUB <= RPT) $fatal(1, "ot_hbm_accel_smh: NC >= 4 and SUB > RPT");

    localparam integer NP    = SUB / RPT;                  // tiles per column
    // the production configuration instantiates the hardened pieces without parameter overrides (their defaults),
    // so synthesis keeps their module names as the macro masters; any other configuration passes its parameters
    localparam integer DEF   = (SUB == 4 && LBS == 2 && LSB == 16 && NC == 8 && IL == 8 && RMAX == 4096 && LEV == 4
                                && XD == 128 && MAX_OUT == 512 && TCK == 1 && PIO == 2 && HAZ == 1 && NOUT == 4
                                && RPT == 2) ? 1 : 0;
    initial if (SUB % RPT != 0) $fatal(1, "ot_hbm_accel_smh: SUB must be a multiple of RPT");
    wire [SUB*RBW-1:0] f_rl, f_rr;
    wire [NP*BBW-1:0]  f_bl, f_br;
    wire [NH*QLW-1:0]  f_ql, f_qr;
    generate if (DEF != 0) begin : g_fd
        ot_hbm_accel_smh_front u_front (
            .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .op_rows(op_rows), .op_c(op_c),
            .op_g(op_g), .op_gs(op_gs), .op_fmt(op_fmt), .op_xb(op_xb), .busy(busy), .d_valid(d_valid),
            .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines), .req_v(req_v), .req_ready(req_ready),
            .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
            .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .rv(rv), .rrow(rrow),
            .rdata(rdata), .fault(fault), .arrive(arrive), .release_in(release_in), .released(released),
            .rout_l(f_rl), .bout_l(f_bl), .rout_r(f_rr), .bout_r(f_br), .qin_l(f_ql), .qin_r(f_qr));
    end else begin : g_fp
        ot_hbm_accel_smh_front #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .RMAX(RMAX), .XD(XD),
                                 .MAX_OUT(MAX_OUT), .PIO(PIO), .HAZ(HAZ), .NOUT(NOUT), .RPT(RPT)) u_front (
            .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .op_rows(op_rows), .op_c(op_c),
            .op_g(op_g), .op_gs(op_gs), .op_fmt(op_fmt), .op_xb(op_xb), .busy(busy), .d_valid(d_valid),
            .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines), .req_v(req_v), .req_ready(req_ready),
            .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
            .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .rv(rv), .rrow(rrow),
            .rdata(rdata), .fault(fault), .arrive(arrive), .release_in(release_in), .released(released),
            .rout_l(f_rl), .bout_l(f_bl), .rout_r(f_rr), .bout_r(f_br), .qin_l(f_ql), .qin_r(f_qr));
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
// The front: ot_hbm_accel_sm_pq's pins, channels, bulk copy, pipelined issue and s1 verbatim; then
//   A   the unpacked row bundles and the x-write beat registered (the format select from 64 kept fmt replicas,
//       <= 32 loads each), one copy per side;
//   O   the output registers, one per (side, row) for the row bundle and the x-write bundle (the tiles' first hop);
// results: lane landing per side, deskew to the farthest column (a column at hop h arrives 2h - 2 cycles after its
// stack output and waits 2(NH - h)), then the pin chains.  rdone (sv) is column 0's aligned valid.
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_front #(
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
    parameter integer RPT  = 2,             // rows (leaves) per tile: one x-write bundle per tile
    parameter integer NFMT = SUB * LBS * 8 + SUB   // fmt replicas: 32 select loads each (unpack), one per sub (c)
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
    output wire                    released,
    output wire [SUB*(6+$clog2(RMAX)+1+$clog2(IL)+LBS*266+LSB*16+1+$clog2(XD))-1:0] rout_l, rout_r,
    output wire [(SUB/RPT)*(1+$clog2(XD)+(NC*(SUB*LBS*266+SUB*LSB*16)+2047)/2048+2048)-1:0] bout_l, bout_r,
    input  wire [((NC-NC/2 > NC/2) ? NC-NC/2 : NC/2)*(2+32+$clog2(RMAX))-1:0] qin_l, qin_r
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
    localparam integer QLW   = 2 + 32 + RW;
    localparam integer NL    = NC / 2;
    localparam integer NR    = NC - NL;
    localparam integer NH    = (NL > NR) ? NL : NR;
    localparam integer OPW   = (RW + 1) + 16 + 8 + 1 + 2;
    localparam integer PIH   = PIO + 1;      // long-haul element-input / channel stages (pins -> mid-front hub)
    localparam integer CHD   = 2 * PIH + 3;
    localparam integer OPX   = OPW + XW;

    // ---------------- boundary, channels, bulk copy, issue, s1: ot_hbm_accel_sm_pq verbatim ----------------
    wire          h_start, h_pop;
    wire [OPX-1:0] h_opx;
    ot_hbm_accel_smh_chan #(.W(OPX), .P(PIH), .DEPTH(CHD)) u_sch (.clk(clk), .rst_n(rst_n),
        .s_valid(start), .s_ready(start_ready), .s_data({op_rows, op_c, op_g, op_gs, op_fmt, op_xb}),
        .m_valid(h_start), .m_ready(h_pop), .m_data(h_opx));
    wire [OPW-1:0] h_op = h_opx[XW +: OPW];
    wire [XW-1:0]  h_xb = h_opx[XW-1:0];
    wire [RW:0] h_rows = h_op[OPW-1 -: RW+1];
    wire [15:0] h_c    = h_op[11 +: 16];
    wire [7:0]  h_g    = h_op[3 +: 8];
    wire        h_gs   = h_op[2];
    wire [1:0]  h_fmt  = h_op[1:0];
    wire h_rsp_v; wire [9:0] h_rsp_tag; wire [1087:0] h_rsp_data;
    // (round 6) the 1088-bit response crosses ~560 um to the ring block: PIO + 2 stages
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO + 2), .RST(1)) u_prv (.clk(clk), .rst_n(rst_n), .d(rsp_v), .q(h_rsp_v));
    ot_hbm_accel_smv_chain #(.W(1098), .D(PIO + 2), .RST(0)) u_prd (.clk(clk), .rst_n(rst_n), .d({rsp_tag, rsp_data}),
        .q({h_rsp_tag, h_rsp_data}));
    wire h_release;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prl (.clk(clk), .rst_n(rst_n), .d(release_in), .q(h_release));
    wire h_d_valid, h_d_ready; wire [55:0] h_d;
    ot_hbm_accel_smh_chan #(.W(56), .P(PIH), .DEPTH(CHD)) u_dch (.clk(clk), .rst_n(rst_n),
        .s_valid(d_valid), .s_ready(d_ready), .s_data({d_base, d_lines}),
        .m_valid(h_d_valid), .m_ready(h_d_ready), .m_data(h_d));
    wire h_req_v, h_req_ready; wire [31:0] h_req_addr; wire [9:0] h_req_tag;
    wire o_req_v, o_req_ready; wire [41:0] o_req_d;
    ot_hbm_accel_smh_chan #(.W(42), .P(PIH), .DEPTH(CHD)) u_rch (.clk(clk), .rst_n(rst_n),
        .s_valid(h_req_v), .s_ready(h_req_ready), .s_data({h_req_addr, h_req_tag}),
        .m_valid(o_req_v), .m_ready(o_req_ready), .m_data(o_req_d));
    // (round 6) the request leaves through a registered 2-entry skid beside the pins: req_ready drives only the
    // skid's own count and head select (+1 cycle on requests)
    ot_hbm_accel_smh_skid #(.W(42)) u_rsk (.clk(clk), .rst_n(rst_n), .s_valid(o_req_v), .s_ready(o_req_ready),
        .s_data(o_req_d), .m_valid(req_v), .m_ready(req_ready), .m_data({req_addr, req_tag}));
    wire          w_valid, w_ready, b_valid, b_ready;
    wire [1087:0] w_data, b_data;
    ot_hbm_accel_bulk_copy_oq4 #(.ENABLE(1), .LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1),
                             .RING_MACRO(1)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(h_d_valid), .d_ready(h_d_ready), .d_base(h_d[55:24]), .d_lines(h_d[23:0]),
        .req_v(h_req_v), .req_ready(h_req_ready), .req_addr(h_req_addr), .req_tag(h_req_tag),
        .rsp_v(h_rsp_v), .rsp_tag(h_rsp_tag), .rsp_data(h_rsp_data),
        .s_valid(b_valid), .s_ready(b_ready), .s_data(b_data), .outstanding(), .idle());
    // the line stream to the issue through a 2-entry skid with a registered ready and a registered head: the bulk
    // copy's pop sees only its own queue and this register (+1 cycle on the stream; order and data unchanged)
    ot_hbm_accel_smh_skid3 #(.W(1088)) u_sk (.clk(clk), .rst_n(rst_n), .s_valid(b_valid), .s_ready(b_ready),
        .s_data(b_data), .m_valid(w_valid), .m_ready(w_ready), .m_data(w_data));
    reg  [XW-1:0] xb_q;
    wire        sv, h_busy, h_arrive, h_released;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) xb_q <= {XW{1'b0}};
        else if (h_pop) xb_q <= h_xb;
    // the unpack's format select: NFMT kept replicas (<= 32 select loads each), loaded one edge after the launch
    // from NFC registered copies of {launch, format} (<= 16 replicas each): the launch no longer fans out to every
    // replica.  Exact: the first line of a launched op reaches the unpack >= 3 cycles after the launch (setup
    // cycle, then issue, then s1), the last line of the previous op unpacks no later than the launch cycle.
    // (round 4) the launch is registered once beside the issue (pop_r, fmt_q), then copied, then the 2 NFMT
    // replicas (one set per side) load.
    localparam integer NFR = 2 * NFMT;
    localparam integer NFC = (NFR + 7) / 8;
    reg              pop_r;
    reg  [1:0]       fmt_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pop_r <= 1'b0; fmt_q <= 2'd0; end
        else begin pop_r <= h_pop; if (h_pop) fmt_q <= h_fmt; end
    // (round 7) one more copy layer (pd1 / fq1: 4 copies, one per (side, sub pair)) between the launch register and
    // the NFC copies: replicas visible 4 cycles after the launch; the first line of the new op reaches the unpack
    // in cycle t + 4 at the earliest (launch t, setup t + 1, first issue t + 2, s1, hop H)
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
        // copy k serves replicas 8k .. 8k + 7: side (8k) / NFMT, sub pair by the replica's sub
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
    // DBF = BF16 column latency - block-dot column latency: 14 for sm_pq's columns; the tile's block-dot column is
    // 7 cycles deeper (bterm3) and its BF16 column 3 deeper (ot_hbm_accel_smh_tc_col): 14 - 7 + 3 = 10
    ot_hbm_accel_issue_pq #(.IL(IL), .RMAX(RMAX), .XDEPTH(XD), .NOUT(NOUT), .HAZ(HAZ), .DBF(10)) u_issue (
        .clk(clk), .rst_n(rst_n), .start_v(h_start), .launch(h_pop), .op_rows(h_rows), .op_c(h_c), .op_g(h_g),
        .op_gs(h_gs), .op_bf(h_fmt == 2'd0),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release),
        .released(h_released), .hz_wait());
    ot_hbm_accel_smv_chain #(.W(3), .D(PIO), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n),
        .d({h_busy, h_arrive, h_released}), .q({busy, arrive, released}));
    // s1 (beside the issue): the line, the control / tag / x address; then the hop H, one kept copy per
    // (side, tile row) carrying only that row's line bits (row 0: [0, 1056), row 1: [512, 1024) and [1056, 1088)):
    // the row bundles leave the hub one register later (+1 cycle on every row read; the x-write beat gets the same
    // +1 at its landing, so the write-before-read margin is unchanged)
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
        s1_w <= w_data ^ 1088'd8;               // negative-control mutant only (bench: --mut-s1w); never defined in a build
`else
        s1_w <= w_data;
`endif
        s1_ct <= {row_now[RW-1:0], i_glast, si, xa + xb_q};
    end
    wire [NSC*S1W-1:0]  s1c;                   // hop H control, per (side, row)
    wire [NSC*1088-1:0] hw;                    // hop H line, per (side, row); bits a row does not use are 0
    generate for (k = 0; k < NSC; k = k + 1) begin : g_h
        localparam integer PR = k % (SUB / RPT);
        ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(s1_c[S1W-1 -: 3]), .q(s1c[k*S1W + TAGW + XW +: 3]));
        ot_hbm_accel_smh_kreg #(.W(TAGW + XW)) u_t (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(s1_c[TAGW + XW - 1:0]), .q(s1c[k*S1W +: TAGW + XW]));
        if (SUB == 4 && RPT == 2 && LBS == 2 && LSB == 16) begin : g_rows
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
        end else begin : g_full                // other geometries: the whole line per copy
            ot_hbm_accel_smh_kreg #(.W(1088)) u_w (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(s1_w),
                .q(hw[k*1088 +: 1088]));
        end
    end endgenerate
    // ---------------- x-write beat at the pins (sm_pq's w0) ----------------
    reg              w0_en;
    reg [XW-1:0]     w0_addr;
    reg [NBEAT-1:0]  w0_oh;
    reg [2047:0]     w0_data;
    integer gq;
    // (round 4) landed at the pins first (wl), decoded one edge later (w0): +1 cycle on every x write, matched by
    // the row bundles' hop H
    reg              wl_en;
    reg [XW-1:0]     wl_addr;
    reg [6:0]        wl_grp;
    reg [2047:0]     wl_data;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wl_en <= 1'b0; w0_en <= 1'b0; end
        else begin wl_en <= xw_en; w0_en <= wl_en; end
    always @(posedge clk) begin
        wl_addr <= xw_addr; wl_grp <= xw_grp; wl_data <= xw_data;
        w0_addr <= wl_addr; w0_data <= wl_data;
        for (gq = 0; gq < NBEAT; gq = gq + 1) w0_oh[gq] <= (wl_grp == gq);
    end

    // ---------------- stage A: unpack per sub (sm_pq's g_sub, format from the replicas), per side ----------------
    genvar sp, q, bb, sd;
    wire [2*SUB*RBW-1:0] a_in;               // per (side, sub): the control from that side / row's s1 copy
    generate for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
        for (sd = 0; sd < 2; sd = sd + 1) begin : g_sd
            localparam integer CI = sd * (SUB / RPT) + sp / RPT;
            wire [1087:0] lw = hw[CI*1088 +: 1088];
            wire [WSW-1:0] un;
            for (q = 0; q < LBS; q = q + 1) begin : g_q
                localparam integer J = sp * LBS + q;
                wire [255:0] fp4w, fp8w;
                for (bb = 0; bb < 32; bb = bb + 1) begin : g_b
                    // replica (side, sp, q, bb / 4): 32 select loads
                    localparam integer RI = sd * NFMT + ((sp * LBS + q) * 8 + bb / 4) % NFMT;
                    assign fp4w[8*bb +: 8] = {4'd0, lw[128*J + 4*bb +: 4]};
                    assign fp8w[8*bb +: 8] = (J < LB / 2) ? lw[256*J + 8*bb +: 8] : 8'd0;
                    assign un[256*q + 8*bb +: 8] = (fmt_r[2*RI +: 2] == 2'd2) ? fp4w[8*bb +: 8] : fp8w[8*bb +: 8];
                end
                assign un[LBS*256 + 10*q +: 10] = {2'b00, lw[1024 + 8*J +: 8]} - 10'sd127;
            end
            assign un[LBS*266 +: LSB*16] = lw[sp*LSB*16 +: LSB*16];
            localparam integer RC = sd * NFMT + (SUB * LBS * 8 + sp) % NFMT;
            wire bf_op = (fmt_r[2*RC +: 2] == 2'd0);
            wire fp4_op = (fmt_r[2*RC +: 2] == 2'd2);
            wire [S1W-1:0] c1 = s1c[CI*S1W +: S1W];
            wire s1_v = c1[S1W-1], s1_first = c1[S1W-2], s1_last = c1[S1W-3];
            wire [TAGW-1:0] s1_tag = c1[XW +: TAGW];
            wire [XW-1:0] s1_xa = c1[XW-1:0];
            wire [CW-1:0] c_in = {s1_v && !bf_op, s1_v && bf_op, s1_first, s1_last, fp4_op, bf_op, s1_tag};
            // bundle layout (MSB first): {c (valids at the top), w, x_ce, x_addr}
            assign a_in[(sd*SUB+sp)*RBW +: RBW] = {c_in, un, s1_v, s1_xa};
        end
    end endgenerate
    // stage A and the output registers: valid bits reset, data not; one copy per side
    wire [2*SUB*RBW-1:0] a_r, m_r, o_r;            // (round 6) A -> M -> O: one more hop to the pins (+1 on reads)
    wire [2*(SUB/RPT)*BBW-1:0] a_b, m_b;        // x-write A and M stages, per (side, row) (+1 on writes)
    wire [2*(SUB/RPT)*BBW-1:0] o_b;
    wire [BBW-1:0]       w0_b = {w0_en, w0_addr, w0_oh, w0_data};
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_side
        for (sp = 0; sp < SUB; sp = sp + 1) begin : g_rs
            ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_a (.clk(clk), .rst_n(rst_n),
                .d(a_in[(sd*SUB+sp)*RBW +: RBW]), .q(a_r[(sd*SUB+sp)*RBW +: RBW]));
            ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_m (.clk(clk), .rst_n(rst_n),
                .d(a_r[(sd*SUB+sp)*RBW +: RBW]), .q(m_r[(sd*SUB+sp)*RBW +: RBW]));
            ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_o (.clk(clk), .rst_n(rst_n),
                .d(m_r[(sd*SUB+sp)*RBW +: RBW]), .q(o_r[(sd*SUB+sp)*RBW +: RBW]));
            if (sp % RPT == 0) begin : g_bo     // one x-write bundle per tile (RPT rows)
                localparam integer PI = sd * (SUB / RPT) + sp / RPT;
                ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bav (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(w0_b[BBW-1]), .q(a_b[PI*BBW + BBW - 1]));
                ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bad (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
                    .q(a_b[PI*BBW +: BBW-1]));
                ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bmv (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(a_b[PI*BBW + BBW - 1]), .q(m_b[PI*BBW + BBW - 1]));
                ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bmd (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(a_b[PI*BBW +: BBW-1]), .q(m_b[PI*BBW +: BBW-1]));
                ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bov (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(m_b[PI*BBW + BBW - 1]), .q(o_b[PI*BBW + BBW - 1]));
                ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bod (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(m_b[PI*BBW +: BBW-1]), .q(o_b[PI*BBW +: BBW-1]));
            end
        end
    end endgenerate
    assign rout_l = o_r[0 +: SUB*RBW];
    assign rout_r = o_r[SUB*RBW +: SUB*RBW];
    assign bout_l = o_b[0 +: (SUB/RPT)*BBW];
    assign bout_r = o_b[(SUB/RPT)*BBW +: (SUB/RPT)*BBW];

    // ---------------- results: lane landing, deskew, pins ----------------
    // lane k of a side = the column k + 1 hops away; it arrives 2k cycles after the nearest; wait 2(NH-1-k)
    wire [NC*QLW-1:0] al;                      // aligned per column
    genvar ln;
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
                ot_hbm_accel_smv_chain #(.W(2), .D(2*(NH-1-ln)), .RST(1)) u_dv (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-1 -: 2]), .q(al[COLN*QLW + QLW - 2 +: 2]));
                ot_hbm_accel_smv_chain #(.W(QLW-2), .D(2*(NH-1-ln)), .RST(0)) u_dd (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-3:0]), .q(al[COLN*QLW +: QLW-2]));
            end
        end
    end endgenerate
    // lane layout: {v, f, y[31:0], row[RW-1:0]}
    wire [NC-1:0]    cf_a;
    wire [NC*32-1:0] cy_a;
    genvar cc;
    generate for (cc = 0; cc < NC; cc = cc + 1) begin : g_al
        assign cf_a[cc] = al[cc*QLW + QLW - 2];
        assign cy_a[32*cc +: 32] = al[cc*QLW + RW +: 32];
    end endgenerate
    // the issue's row retire: column 0's aligned valid, registered once more beside the issue (the landing flop
    // sits at the back-end edge, the issue mid-front; +1 cycle on the retire count only)
    // (round 4) two hop registers (the landing is at the back-end edge, the issue mid-front): +2 on the retire
    ot_hbm_accel_smv_chain #(.W(1), .D(3), .RST(1)) u_sv (.clk(clk), .rst_n(rst_n), .d(al[QLW - 1]), .q(sv));   // (round 6) 3
    reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0;
        else fault_q <= fault_q | (|cf_a);
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
    parameter integer X = 7         // x_ce sits at bit X (above the X-bit x address)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    ot_hbm_accel_smh_kreg #(.W(NV), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[W-1 -: NV]),
        .q(q[W-1 -: NV]));
    ot_hbm_accel_smh_kreg #(.W(W-NV-X-1)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[W-NV-1:X+1]),
        .q(q[W-NV-1:X+1]));
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_x (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[X]), .q(q[X]));
    ot_hbm_accel_smh_kreg #(.W(X)) u_a (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(d[X-1:0]), .q(q[X-1:0]));
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
    parameter integer A2B = 7               // strap bits of the BF16 field offset
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
    assign bout = bl;
    genvar j, ln;
    generate for (j = 0; j < RPT; j = j + 1) begin : g_lf
        // the row bundle of row j (landed, driven on)
        // the row bundle lands in a pass-through copy (rout) and the leaf's own copy (kept, bit-identical)
        wire [RBW-1:0] rl, rp;
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rp (.clk(clk), .rst_n(rst_n),
            .d(rin[j*RBW +: RBW]), .q(rp));
        assign rout[j*RBW +: RBW] = rp;
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_rl (.clk(clk), .rst_n(rst_n),
            .d(rin[j*RBW +: RBW]), .q(rl));
        wire [BBW-1:0] bk;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bkv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[BBW-1]),
            .q(bk[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bkd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[BBW-2:0]),
            .q(bk[BBW-2:0]));
        // one-hot beat group replicas for this leaf's masks (landed straight from the pins, NG copies)
        // (round 5) the beat one-hot lands once per leaf (kept, beside the pins), its NG replicas load one edge later,
        // in step with the leaf's two-stage rotation
        wire [NG*NBEAT-1:0] ohr;
        wire [NBEAT-1:0] ohl;
        ot_hbm_accel_smh_kreg #(.W(NBEAT)) u_ohl (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(bin[2048 +: NBEAT]),
            .q(ohl));
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
        // own rows on lanes 0..RPT-1 (lane RPT-1-j = row j), straight from the G1 flops
        assign gout[(RPT-1-j)*GLW +: GLW] = {gv, gf, gy, gt};
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
    generate for (m = 0; m < NXL; m = m + 1) begin : g_xm
        ot_sram_1r1w_128x256_m1_r2c2 u_x (
            .clk(clk), .r_ce_in(r0x), .r_addr_in(r0a), .rd_out(xrd[256*m +: 256]),
            .w_ce_in(wce_q[m]), .w_addr_in(wa_q), .wd_in(wd_m[256*m +: 256]), .w_mask_in(wm_m[256*m +: 256]),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---- E4 ----
    reg              iv_b, iv_f, ifirst, ilast, ifp4;
    reg [TAGW-1:0]   itag;
    reg [WSW-1:0]    iw;
    reg [SLW-1:0]    ix;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv_b <= 1'b0; iv_f <= 1'b0; end
        else begin iv_b <= c3v[1]; iv_f <= c3v[0]; end
    end
    always @(posedge clk) begin
        ifirst <= c3d[CW-3]; ilast <= c3d[CW-4]; ifp4 <= c3d[CW-5]; itag <= c3d[TAGW-1:0];
        iw <= w3;
        ix <= xrd[SLW-1:0];
    end
    // ---- the column logic (flat in the tile: the modules of the sm_pq leaf's macros) ----
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
    wire [LBS*256-1:0] xq_s;
    wire [LBS*10-1:0]  xe_s;
    genvar qq;
    generate for (qq = 0; qq < LBS; qq = qq + 1) begin : g_bx
        assign xq_s[256*qq +: 256] = ix[qq*266 +: 256];
        assign xe_s[10*qq +: 10]   = ix[qq*266 + 256 +: 10];
    end endgenerate
    generate
        if (TCK != 0) begin : g_k
            ot_hbm_accel_smh_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (   // bterm3: +7 cycles
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
            ot_hbm_accel_smh_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (   // +3 cycles (tile context)
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else begin : g_o
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
            ot_gpu_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end
    endgenerate
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
    assign qout[0 +: QLW] = {kv, cf_q, ky, krow};
    genvar ln;
    generate for (ln = 1; ln < NH; ln = ln + 1) begin : g_q
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(qin[(ln-1)*QLW + QLW - 2 +: 2]), .q(qout[ln*QLW + QLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1),
            .d(qin[(ln-1)*QLW +: QLW-2]), .q(qout[ln*QLW +: QLW-2]));
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
