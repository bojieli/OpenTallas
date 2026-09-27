`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ME WEIGHT-OP ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x, ME slot engine 1):
// keeps the as-built matrix engine's contract for WEIGHT ops (me_wsrc = 0; ot_hdc_v41_matvec: go /
// ready / idle, the me_* fields, mx_m / mx_xps (elements) / mx_ops (WORDS), the VM x read ports, the
// G-word masked write ports, ov for the logit capture, the per-lane argmax am_*) and runs the op on the
// re-specified BF16/FP32 weight engine ot_hdc_v41x_wgt_tile KIND 1 (MG chunk units = 8*MG MAC lanes,
// R-ARITH chunk8 csum of mul(w, bf16(x)), M = MP positions per weight read).
//
// Semantics (tools/hdc_program_v41.Machine.me_lane under R-ARITH "me"): output row n = (t*IL + j)*W + l
// (n < nout) is csum_i w[n, i] * bf16(x[xbase + p*xps + j*xjs + i]) over K = 2^split * me_k terms,
// written to lane l of word obase + t*ots + j*ojs + p*ops (me_oen), and / or taken into lane p's argmax
// (me_amax: the first maximum in row order).  The weights are in the tile's own banked layout
// (tools/hdc_images_v41x.py mbank_image / me_geometry -- this adapter derives the same geometry):
//   * an op with xjs != 0 (grouped wo_a) runs as IL sub-ops, sub-op j over rows rho = t*W + l
//     (T = tiles * (G >> split) tiles); any other op is one sub-op over rows rho = n;
//   * segment plg = clamp(ceil(log2(ceil(K/8))), PMIN_LG, log2 MG), nbeat = ceil(K / 8P) beats,
//     rpg = MG >> plg rows per group, nrg = ceil(nrows / rpg) groups;
//   * sub-op j's weights at bank word (wbase << cfg_xs) + j * nrg * nbeat.
// Per sub-op: LOAD copies x of each served position (K elements from xbase + j*xjs + p*xps, BF16-rounded
// RNE as the as-built engine's me_round) through the G read ports of copy 0, one position after another,
// into the local activation buffer; then one tile descriptor; the tile's rows come back rpg a cycle in
// row order and are written one row per word port (slot s -> port s of position p's copy).  The next
// sub-op starts when every row group of this one has returned.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_me_adapt #(
    parameter integer W    = 16,           // lanes per as-built VM word
    parameter integer G    = 4,            // as-built lane groups (word ports per copy)
    parameter integer IL   = 8,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer MP   = 1,
    parameter integer MG   = 8,            // weight-tile chunk units (8*MG lanes)
    parameter integer PMIN_LG = 1,
    parameter integer LB   = 7,
    parameter integer BAW  = 17,           // weight bank word address
    parameter integer KMAX = 512,          // largest K
    parameter integer RL   = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xjs,
    input  wire [1:0]        i_split,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps,
    input  wire [AW-1:0]     i_ops,
    input  wire [3:0]        cfg_xs,          // weight base shift (tools/hdc_images_v41x.py me_xs)
    // weight banks: 8 request buses (one per chain position), bank b = 8u + c answers RL cycles later
    output wire [7:0]        wb_re,
    output wire [8*BAW-1:0]  wb_addr,
    input  wire [8*MG*32-1:0] wb_q,
    // vector memory
    output reg  [MP*G-1:0]   x_re,
    output reg  [MP*G*AW-1:0] x_addr,
    input  wire [MP*G*32-1:0] x_q,
    output reg               ov,
    output reg  [MP*G-1:0]   o_we,
    output reg  [MP*G*AW-1:0] o_addr,
    output reg  [MP*G*W-1:0] o_mask,
    output reg  [MP*G*W*32-1:0] o_data,
    output reg  [MP*NW-1:0]  am_idx,
    output reg  [MP*32-1:0]  am_val,
    output reg  [MP-1:0]     am_any,
    output reg               fault
);
    localparam integer L    = 8 * MG;
    localparam integer LMG  = $clog2(MG);
    localparam integer NC   = MG >> PMIN_LG;          // result slots per cycle (<= G)
    localparam integer KAW  = $clog2(KMAX);
    localparam integer NBW  = 14, RWW = 16;
    localparam [2:0] A_IDLE = 0, A_SUB = 1, A_LOAD = 2, A_DESC = 3, A_WAIT = 4;

    function automatic [3:0] clog2v(input [NW:0] x);   // ceil(log2 x), x >= 1
        integer b;
        begin
            clog2v = 0;
            for (b = 0; b < 16; b = b + 1) if ((17'd1 << b) < x) clog2v = b + 1;
        end
    endfunction

    reg  [2:0]    st;
    reg  [NW-1:0] nout, tiles, kc;
    reg  [AW-1:0] wbase, xbase, xjs, obase, ots, ojs, xps, ops;
    reg  [1:0]    split;
    reg           oen, amax;
    reg  [2:0]    m;
    reg  [3:0]    xs;
    // op geometry
    reg  [NW:0]   K;
    reg  [3:0]    plg;
    reg  [NBW-1:0] nbeat;
    reg  [RWW-1:0] nrows, nrg;
    reg           splitj;
    reg  [3:0]    sj;                                // sub-op
    reg  [AW-1:0] sbase;                             // sub-op weight base
    reg  [RWW-1:0] got;                              // row groups returned
    assign ready = (st == A_IDLE);

    wire [NW:0]  Kc = {1'b0, i_k} << i_split;
    wire [NW:0]  nch = (Kc + 7) >> 3;
    wire [3:0]   plg_c0 = clog2v(nch);
    wire [3:0]   plg_c = (plg_c0 < PMIN_LG) ? PMIN_LG : (plg_c0 > LMG) ? LMG : plg_c0;
    wire         splitj_c = (i_xjs != 0);
    wire [RWW-1:0] nrows_c = splitj_c ? ((i_tiles * (G >> i_split)) * W) : i_nout;
    wire [NW:0]  nbeat_c = (Kc + (8 << plg_c) - 1) >> (3 + plg_c);
    wire [RWW:0] nrg_c = ({1'b0, nrows_c} + (MG >> plg_c) - 1) >> (LMG - plg_c);

    // ---- LOAD: G elements a cycle per position through copy 0's ports; written 2 cycles later
    reg  [2:0]    lp;
    reg  [NW:0]   le;                                // element (of K) being read
    reg           l_v, l2_v;
    reg  [2:0]    l_p, l2_p;
    reg  [NW:0]   l_e, l2_e;
    wire          l_lastp = (le + G >= K);
    reg           d_v;
    wire          d_rdy;
    wire          t_ov;                              // a row group of the tile's results
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= A_IDLE; l_v <= 1'b0; l2_v <= 1'b0; x_re <= 0; d_v <= 1'b0;
        end else begin
            x_re <= 0;
            l_v <= 1'b0;
            l2_v <= l_v;
            d_v <= 1'b0;
            case (st)
                A_IDLE: if (go) begin st <= A_SUB; sj <= 0; end
                A_SUB: begin st <= A_LOAD; lp <= 0; le <= 0; got <= 0; end
                A_LOAD: begin
                    x_re[G-1:0] <= {G{1'b1}};
                    l_v <= 1'b1;
                    le <= le + G;
                    if (l_lastp) begin
                        le <= 0; lp <= lp + 1'b1;
                        if (lp + 1 == m) st <= A_DESC;
                    end
                end
                A_DESC: if (!l_v && !l2_v && !d_v) begin d_v <= 1'b1; st <= A_WAIT; end
                A_WAIT: if (got == nrg) begin
                    if (sj + 1 == (splitj ? IL : 1)) st <= A_IDLE;
                    else begin sj <= sj + 1'b1; st <= A_SUB; end
                end
                default: st <= A_IDLE;
            endcase
            if (t_ov) got <= got + 1'b1;
        end
    end
    integer c;
    always @(posedge clk) begin
        if (st == A_IDLE && go) begin
            nout <= i_nout; tiles <= i_tiles; kc <= i_k; wbase <= i_wbase; xbase <= i_xbase; xjs <= i_xjs;
            obase <= i_obase; ots <= i_ots; ojs <= i_ojs; xps <= i_xps; ops <= i_ops; split <= i_split;
            oen <= i_oen; amax <= i_amax; m <= (i_m == 3'd0) ? 3'd1 : i_m; xs <= cfg_xs;
            K <= Kc; plg <= plg_c; nbeat <= nbeat_c; nrows <= nrows_c; nrg <= nrg_c; splitj <= splitj_c;
        end
        if (st == A_SUB) sbase <= (wbase << xs) + sj * (nrg * nbeat);
        for (c = 0; c < G; c = c + 1)
            x_addr[c*AW +: AW] <= xbase + (splitj ? sj * xjs : {AW{1'b0}}) + lp * xps + le + c;
        l_p <= lp; l_e <= le; l2_p <= l_p; l2_e <= l_e;
    end

    // ---- activation buffer (BF16, RNE of the element as the as-built me_round), per position
    reg  [15:0] xb [0:MP*KMAX-1];
    reg  [32:0] rb;
    integer b;
    always @(posedge clk)
        if (l2_v)
            for (b = 0; b < G; b = b + 1)
                if (l2_e + b < K) begin
                    rb = {1'b0, x_q[32*b +: 32]} + 33'h7FFF + {32'd0, x_q[32*b + 16]};
                    xb[l2_p * KMAX + l2_e + b] <= rb[31:16];
                end

    // ---- the tile
    wire [7:0]        rq_v;
    wire [8*BAW-1:0]  rq_a;
    wire [8*NBW-1:0]  rq_q;
    wire [8*4-1:0]    rq_plg;
    wire              t_idle;
    wire [RWW-1:0]    t_rg;
    wire [NC-1:0]     t_mask;
    wire [NC*MP*32-1:0] t_y;
    wire [NC*MP*16-1:0] t_bf;
    wire [NC*MP-1:0]  t_f;
    // The KIND 1 tile carries a two-bit format with each weight word. The
    // core's existing ROM contains FP32 words, so tag each lane separately;
    // widening the packed bus as a whole would shift all but lane zero.
    wire [8*MG*34-1:0] wb_fmt;
    genvar wi;
    generate for (wi = 0; wi < 8*MG; wi = wi + 1) begin : g_wfmt
        assign wb_fmt[34*wi +: 34] = {2'b00, wb_q[32*wi +: 32]};
    end endgenerate
    // activation broadcast: lane b = 8u + c takes term q*8P + (b mod 8P) of each position, RL cycles later
    reg  [8*MG*MP*16-1:0] xr [0:RL-1];
    integer u, cc, pp, rr;
    reg  [NBW+8:0] term;
    always @(posedge clk) begin
        for (u = 0; u < MG; u = u + 1)
            for (cc = 0; cc < 8; cc = cc + 1) begin
                term = ({9'd0, rq_q[cc*NBW +: NBW]} << (3 + rq_plg[cc*4 +: 4])) +
                       ((8 * u + cc) & ((8 << rq_plg[cc*4 +: 4]) - 1));
                for (pp = 0; pp < MP; pp = pp + 1)
                    xr[0][((8*u + cc)*MP + pp)*16 +: 16] <= xb[pp * KMAX + term[KAW-1:0]];
            end
        for (rr = 1; rr < RL; rr = rr + 1) xr[rr] <= xr[rr-1];
    end
    assign wb_re = rq_v;
    assign wb_addr = rq_a;
    ot_hdc_v41x_wgt_tile #(.KIND(1), .G(MG), .M(MP), .LB(LB), .PMIN_LG(PMIN_LG), .AW(BAW), .NBW(NBW), .RWW(RWW),
                           .EIW(9), .TGW(4), .RL(RL), .OCRED(128)) u_t (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(plg), .d_nb(K[NBW-1:0]),
        .d_nrows(nrows), .d_wbase(sbase[BAW-1:0]), .d_ind(1'b0), .d_eid(9'd0), .d_estride({BAW{1'b0}}),
        .d_fp4(1'b0), .d_tag(4'd0), .d_src(1'b0), .d_split(1'b0),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(),
        .rq_src(), .rq_split(), .rq_rg(),
        .rd_w(wb_fmt), .rd_k('0), .rd_x(xr[RL-1]),
        .o_cr(t_ov), .o_v(t_ov), .o_rg(t_rg), .o_tag(), .o_mask(t_mask), .o_y(t_y), .o_bf(t_bf), .o_f(t_f),
        .o_smask(), .o_ys(), .o_bfs(), .o_fs(),
        .o_cnt_rom(), .o_cnt_stream(), .o_cnt_split(),
        .idle(t_idle));

    // ---- results: slot s of a row group is row rho = rg*rpg + s -> (t, j, l) -> word port s of position p
    reg  [MP*G-1:0]     n_we;
    reg  [MP*G*AW-1:0]  n_addr;
    reg  [MP*G*W-1:0]   n_mask;
    reg  [MP*G*W*32-1:0] n_data;
    reg  [RWW+4:0]      rho;
    reg  [NW-1:0]       tt, jj, ll, nidx;
    reg                 keep;
    reg  [31:0]         y, key, bkey;
    reg  [MP*32-1:0]    am_key;
    reg  [MP*NW-1:0]    b_idx;
    reg  [MP*32-1:0]    b_val, b_key;
    reg  [MP-1:0]       b_any, b_upd;
    reg                 fl;
    integer s, p;
    always @(*) begin
        n_we = 0; n_addr = 0; n_mask = 0; n_data = 0; fl = 1'b0;
        b_idx = am_idx; b_val = am_val; b_key = am_key; b_any = am_any;
        for (s = 0; s < NC; s = s + 1) begin
            rho = ({5'd0, t_rg} << (LMG - plg)) + s;
            if (splitj) begin
                tt = rho >> 4; ll = rho & 15; jj = sj;
            end else begin
                tt = rho >> 7; jj = (rho >> 4) & 7; ll = rho & 15;
            end
            nidx = ((tt * IL + jj) * W) + ll;
            keep = t_ov && t_mask[s] && (nidx < nout);
            for (p = 0; p < MP; p = p + 1) begin
                y = t_y[(s*MP + p)*32 +: 32];
                if (keep && p < m) begin
                    if (t_f[s*MP + p]) fl = 1'b1;
                    n_we[p*G + s] = oen;
                    n_addr[(p*G + s)*AW +: AW] = obase + tt * ots + jj * ojs + p * ops;
                    n_mask[(p*G + s)*W + ll] = 1'b1;
                    n_data[((p*G + s)*W + ll)*32 +: 32] = y;
                    key = y[31] ? ~y : {1'b1, y[30:0]};
                    if (amax && (!b_any[p] || key > b_key[p*32 +: 32])) begin
                        b_any[p] = 1'b1; b_key[p*32 +: 32] = key; b_idx[p*NW +: NW] = nidx;
                        b_val[p*32 +: 32] = y;
                    end
                end
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov <= 1'b0; o_we <= 0; am_any <= 0; am_idx <= 0; am_val <= 0; am_key <= 0; fault <= 1'b0;
        end else begin
            ov <= t_ov && (oen || amax);
            o_we <= n_we;
            if (go && ready && i_amax) am_any <= 0;
            else if (amax && t_ov) begin am_any <= b_any; am_idx <= b_idx; am_val <= b_val; am_key <= b_key; end
            if (go && ready) fault <= 1'b0;
            else if (fl) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        o_addr <= n_addr; o_mask <= n_mask; o_data <= n_data;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= (st == A_IDLE) && !go && t_idle && !t_ov && !ov && !(|o_we);
    end
    // ---- activation counters (bench only, read hierarchically by rtl/test/tb_hdc_core_v41x.sv): ops this
    // engine ran and the elements it processed -- the campaign fails a selected unit whose counters stay 0
    reg [31:0] dbg_ops, dbg_elems;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin dbg_ops <= 0; dbg_elems <= 0; end
        else begin
            if (st == A_IDLE && go) dbg_ops <= dbg_ops + 1;
            dbg_elems <= dbg_elems + (rq_v[0] ? L * MP : 0);        // MACs issued (a beat of L lanes)
        end
    end
endmodule
