`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_comb (s81-suhc-hier-1011, 2026-10-11): the CENTRE combine tile of the hierarchical S81 HC slab
// (dsfd_sp_hc HIER=1): 575.992 um wide, under the centre pin tile, between the two outer column roots, above the
// centre column chain.  It holds the dsfd_sp_ctrl engine adapter (ot_s81_engine_adapter QD 8), the root sequencer /
// VM slots / norm scalar tail / act-quant (ot_s81_hc_hroot), the final rungs of the sum tree, the centre chain's root
// (its y slice FIFO, its subtrees) and the y credit view (beats available = accept notices - beats taken).
// Every seam is registered both sides; the centre chain is padded to the outer chains' register counts so all three
// chains run in lockstep: forward = send + capture + RF + chain output flop, return = capture + RT + send + capture.
// The centre chain is the short one (NS - 2 NP sub-tiles): 3 more registers a missing hop on both buses.
// The done pulse waits for the write path (send + capture + RW + pin flop) before the adapter: the last write of a
// job leaves the slab pins no later than its done.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_comb #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer WIN = 2, WOUT = 2, MUT = 0, AMUT = 0, RF = 1, RT = 1, RW = 2, YD = 16
) (
    input  wire                 cck, crs, sk, srs,
    // centre pin tile seam
    input  wire                 n_cmd_v,
    input  wire [83:0]          n_cmd_d,
    output wire                 n_done_v,
    output wire [7:0]           n_done_tag,
    input  wire                 n_inp,
    output reg  [S_RD-1:0]      n_rq_v,
    output reg  [S_RD*14-1:0]   n_rq_row,
    input  wire [S_RD-1:0]      n_rs_v,
    input  wire [S_RD*512-1:0]  n_rs_d,
    output reg                  n_flt,
    output reg                  n_online,
    output reg  [3:0]           n_fcode,
    input  wire                 n_yacc,
    input  wire [YS1-1:0]       n_y,
    output reg                  n_ypop,
    // west / east column root seams
    output reg  [FVW-1:0]       w_fv,
    output reg  [FSW-1:0]       w_fd,
    output reg  [4*WSL-1:0]     w_w,
    input  wire [RVW-1:0]       w_rv,
    input  wire [RDW-1:0]       w_rd,
    input  wire [NE0*32-1:0]    w_ex,
    input  wire                 w_flt,
    output reg  [FVW-1:0]       e_fv,
    output reg  [FSW-1:0]       e_fd,
    output reg  [4*WSL-1:0]     e_w,
    input  wire [RVW-1:0]       e_rv,
    input  wire [RDW-1:0]       e_rd,
    input  wire [NE2*32-1:0]    e_ex,
    input  wire                 e_flt,
    // centre column chain
    output wire                 ch_rst,
    output reg  [FVW-1:0]       ch_fv,
    output reg  [FDW-1:0]       ch_fd,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL) % NS;
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
        necnt = exidx(2 * NL, c);
    endfunction
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_PI = S_RT + 24 * S_RT, P_D = P_PI + 8, RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer NE0_ = necnt(0), NE1_ = necnt(1), NE2_ = necnt(2);
    localparam integer NE0 = (NE0_ > 0) ? NE0_ : 1, NE1 = (NE1_ > 0) ? NE1_ : 1, NE2 = (NE2_ > 0) ? NE2_ : 1;
    localparam integer NIM_ = NE0_ + NE1_ + NE2_, NIM = (NIM_ > 0) ? NIM_ : 1;
    localparam integer DW = 3 + RW;                               // done waits the write path
    localparam integer YB = $clog2(YD);

    // ---------------------------------------------------------------- adapter
    wire e_v, e_r, d_v, a_flt, c_flt, online;
    wire [83:0] e_d;
    wire [7:0]  d_t;
    wire [3:0]  fcode;
    reg  inp_q;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= n_inp;
    reg        cv_q;
    reg [83:0] cd_q;
    always @(posedge cck or negedge crs) if (!crs) cv_q <= 1'b0; else cv_q <= n_cmd_v;
    always @(posedge cck) cd_q <= n_cmd_d;
    wire [8:0] dd;
    ot_hdc_delay #(.W(9), .D(DW), .RESET(1)) u_dd (.clk(sk), .rst_n(srs), .d({d_v, d_t}), .q(dd));
    wire       cdv;
    wire [7:0] cdt;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(cdv), .c_done_tag(cdt),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(dd[8]), .e_done_tag(dd[7:0]));
    reg       dv_q;
    reg [7:0] dt_q;
    always @(posedge cck or negedge crs) if (!crs) dv_q <= 1'b0; else dv_q <= cdv;
    always @(posedge cck) dt_q <= cdt;
    assign n_done_v = dv_q;
    assign n_done_tag = dt_q;

    // ---------------------------------------------------------------- seam captures
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    reg                 ya;
    reg  [YS1-1:0]      y1;
    reg  [RVW-1:0]      wrv, erv, crv;
    reg  [RDW-1:0]      wrd, erd, crd;
    reg  [NE0*32-1:0]   wex;
    reg  [NE2*32-1:0]   eex;
    reg                 wfl, efl;
    always @(posedge sk or negedge srs)
        if (!srs) begin rs_v_q <= 0; ya <= 1'b0; wrv <= 0; erv <= 0; crv <= 0; wfl <= 1'b0; efl <= 1'b0; end
        else begin rs_v_q <= n_rs_v; ya <= n_yacc; wrv <= w_rv; erv <= e_rv; crv <= ch_rv; wfl <= w_flt; efl <= e_flt; end
    always @(posedge sk) begin rs_d_q <= n_rs_d; y1 <= n_y; wrd <= w_rd; erd <= e_rd; crd <= ch_rd; wex <= w_ex; eex <= e_ex; end

    // ---------------------------------------------------------------- y credit view
    reg  [7:0] avail;
    wire       h_yrdy;
    wire       h_yv = (avail != 0);
    wire       ytake = h_yv && h_yrdy;
    always @(posedge sk or negedge srs) if (!srs) avail <= 0; else avail <= avail + ya - ytake;

    // ---------------------------------------------------------------- the centre chain: return, subtrees, padding
    wire [NE1*32-1:0] ex1;
    wire              tf1;
    ot_s81_hc_stree #(.NS(NS), .NP(NP), .LA(AL), .OWN(1)) u_tree1 (.clk(sk), .rst_n(srs), .v(crv[S_RT]),
        .pk(crd[P_D +: NP * 128]), .im(32'd0), .ex(ex1), .r_v(), .r(), .fault(tf1));
    localparam integer HOP = 3;                                   // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1);                     // the centre chain is short by NP - L1 sub-tiles
    localparam integer RP = RT + 2 + PAD;                         // the outer chains' relay + send + capture + padding
    wire [RVW-1:0]    crv_p;
    wire [RDW-1:0]    crd_p;
    wire [NE1*32-1:0] ex1_p;
    wire [RVW-1:0]    crv_f = {crv[RVW-1], crv[RVW-2] | tf1, crv[RVW-3:0]};
    ot_hdc_delay #(.W(RVW), .D(RP), .RESET(1)) u_prv (.clk(sk), .rst_n(srs), .d(crv_f), .q(crv_p));
    ot_hdc_delay #(.W(RDW), .D(RP)) u_prd (.clk(sk), .rst_n(srs), .d(crd), .q(crd_p));
    ot_hdc_delay #(.W(NE1 * 32), .D(RP)) u_pex (.clk(sk), .rst_n(srs), .d(ex1), .q(ex1_p));
    // merged return (lockstep: valids / metadata identical, row data disjoint per lane) and the imported subtrees
    wire [RVW-1:0] m_rv = wrv | erv | ((L1 > 0) ? crv_p : {RVW{1'b0}});
    wire [RDW-1:0] m_rd = wrd | erd | ((L1 > 0) ? crd_p : {RDW{1'b0}});
    wire [NIM*32-1:0] m_im;
    generate
        if (NIM_ > 0) begin : g_im
            if (NE0_ > 0) begin : g0 assign m_im[0 +: NE0_ * 32] = wex[NE0_ * 32 - 1:0]; end
            if (NE1_ > 0) begin : g1 assign m_im[NE0_ * 32 +: NE1_ * 32] = ex1_p[NE1_ * 32 - 1:0]; end
            if (NE2_ > 0) begin : g2 assign m_im[(NE0_ + NE1_) * 32 +: NE2_ * 32] = eex[NE2_ * 32 - 1:0]; end
        end else begin : g_noim
            assign m_im = 32'd0;
        end
    endgenerate

    // ---------------------------------------------------------------- root
    wire [FVW-1:0] fv;
    wire [FSW-1:0] fd;
    wire [S_RD-1:0]    rq_v;
    wire [S_RD*14-1:0] rq_row;
    wire [S_WR-1:0]     wq_v;
    wire [S_WR*14-1:0]  wq_row;
    wire [S_WR*16-1:0]  wq_mask;
    wire [S_WR*512-1:0] wq_d;
    wire [31:0] jobs;
    wire        bsy;
    ot_s81_hc_hroot #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
                      .MUT(MUT), .NIM(NIM)) u_root (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .y_v(h_yv), .y_rdy(h_yrdy), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs), .fv(fv), .fd(fd), .rv_in(m_rv), .rd_in(m_rd), .im(m_im));

    // ---------------------------------------------------------------- sends
    reg [YB:0] yn1;
    reg        yfl;
    integer s;
    always @(posedge sk or negedge srs)
        if (!srs) begin
            n_rq_v <= 0; n_flt <= 1'b0; n_online <= 1'b0; n_fcode <= 0; n_ypop <= 1'b0; w_fv <= 0; e_fv <= 0;
        end else begin
            n_rq_v <= rq_v; n_flt <= a_flt | c_flt | wfl | efl | yfl; n_online <= online; n_fcode <= fcode;
            n_ypop <= fv[S_RD];
            w_fv <= fv; e_fv <= fv;
        end
    always @(posedge sk) begin
        n_rq_row <= rq_row; w_fd <= fd; e_fd <= fd;
        for (s = 0; s < 4; s = s + 1) begin
            w_w[WSL * s +: WSL] <= {wq_d[512 * s +: 512], wq_mask[16 * s +: 16], wq_row[14 * s +: 14], wq_v[s]};
            e_w[WSL * s +: WSL] <= {wq_d[512 * (s + 4) +: 512], wq_mask[16 * (s + 4) +: 16], wq_row[14 * (s + 4) +: 14], wq_v[s + 4]};
        end
    end
    // write valids on reset flops (the slot words above carry them too: the outer roots take the valid from its own flop)
    // ---------------------------------------------------------------- the centre chain: forward (padded) + y FIFO
    reg [1:0] rr;
    always @(posedge sk) rr <= {rr[0], srs};
    assign ch_rst = rr[1];
    localparam integer FP = 2 + RF + PAD;                         // send + capture + RF + padding
    wire [FVW-1:0] fv_p;
    wire [FSW-1:0] fd_p;
    ot_hdc_delay #(.W(FVW), .D(FP), .RESET(1)) u_pfv (.clk(sk), .rst_n(srs), .d(fv), .q(fv_p));
    ot_hdc_delay #(.W(FSW), .D(FP)) u_pfd (.clk(sk), .rst_n(srs), .d(fd), .q(fd_p));
    reg  [YS1-1:0] yf [0:YD-1];
    reg  [YB-1:0]  yw, yr;
    wire pop = fv_p[S_RD];
    always @(posedge sk or negedge srs)
        if (!srs) begin ch_fv <= 0; yn1 <= 0; yw <= 0; yr <= 0; yfl <= 1'b0; end
        else begin
            ch_fv <= (L1 > 0) ? fv_p : {FVW{1'b0}};
            if (ya) yw <= yw + 1'b1;
            if (pop) yr <= yr + 1'b1;
            yn1 <= yn1 + ya - pop;
            if (L1 > 0 && ((ya && !pop && yn1 == YD) || (pop && yn1 == 0))) yfl <= 1'b1;
        end
    always @(posedge sk) begin
        if (ya) yf[yw] <= y1;
        ch_fd[O_D-1:0] <= fd_p[O_D-1:0];
        begin : dfield
            reg [FDD-1:0] t;
            t = {FDD{1'b0}};
            if (pop) t[YS1-1:0] = yf[yr];
            else t[S_RD*512-1:0] = fd_p[O_D +: S_RD * 512];
            ch_fd[O_D +: FDD] <= t;
        end
    end
`ifndef SYNTHESIS
    wire unused_ok = &{1'b0, jobs, bsy, ex1_p};
`endif
endmodule
