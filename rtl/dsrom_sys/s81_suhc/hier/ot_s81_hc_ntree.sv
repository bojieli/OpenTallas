`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_ntree (el1014-s81-norm-tree, 2026-10-14): the NORM TREE variant of the hierarchical S81 HC slab
// (dsfd_sp_hc NTREE = 1; default 0 = the closed serial-chain slab, bit-identical, none of its files touched).
//
// Measured basis (results/rtl/s81_layer_tput_1013/norm_trace_7eb398556): NORM 727 cycles = accept -> sum_return 339 +
// rsqrt 74 + rsqrt -> first row 238 + rows 39 + writer 37.  Four traversals of the 22-half-tile column chain (~16.3 mm,
// 4-5 registers a 740.88-um hop) dominate: the norm go/vector beats forward, the partial packet back, the r beat
// forward, the y rows back.  A tree cannot beat distance (every hop <= 500 um, register at both pins: the far tile is
// >= 33 registers from either end), so the variant does not shorten a traversal: it removes two of them.
//
//   * the scalar end of the norm (sum tree, / D, + eps, rsqrt) moves to the FAR end of the three column chains
//     (ot_s81_hc_cnbot, a bottom region beside the chains' far tiles), where the forward wave of the norm beats ends;
//   * each far half-tile injects its octet's 4-bank partial into a narrow registered lane that runs SOUTH with the
//     wave (ot_s81_hc_ctfx_nt centre strip + ot_s81_hc_ctfs_nt S strip: 2 registers a 740.88-um hop, both <= 393 um,
//     registered at every pin).  The lane is time-multiplexed: octet s of vector v reaches the bottom at
//     base + 2 p_s + v (p_s = its half-tile), two slots by octet parity, so no two partials ever meet (a meeting sets
//     the lane's sticky fault bit);
//   * the bottom collectors (one a chain, two bank-half leaves ot_s81_hc_cncla / _cnclb with their own clock roots) hold the leaves and fire the chain's own subtree of the
//     golden pairwise tree (ot_s81_hc_stree OWN = c, unchanged) at a FIXED offset NT_K after the vector beat passes the
//     far tile; the closed final-rung tile ot_s81_hc_cntree (h2 tuple, unchanged master) takes the three chains'
//     exports, and ot_s81_hc_cnrsq runs the scalar tail of ot_s81_hc_cseq (ot_dsrom_divc, + eps, ot_dsrom_rsqrt:
//     the same modules, the same order: bit-exact by construction);
//   * r leaves the bottom on a narrow registered lane NORTH (33 b: ot_s81_hc_ctfs_nt S strip + ot_s81_hc_ctfx_nt (r2),
//     2 registers a hop) that REPLACES the bus r beat at every half-tile's broadcast source (ctfx_nt; the bus r of
//     the old root path is masked).  The y rows still originate at the far tile and return on the closed row path;
//     the r lane (2 a hop) outruns the row return (5 a hop), so every tile's y is in ybuf before its row passes.
//
// Unchanged and still used: every ctnl / ctpl / ctra / ctrb / ctfn tile of the half-octets, the forward / return buses,
// the column roots, the comb (cseq keeps its own norm tail: its sum and r are computed and discarded, the closed
// tiles stand).  Changed masters (NEW names): ot_s81_hc_cth_nt (region wrapper, no route), ot_s81_hc_ctfx_nt,
// ot_s81_hc_ctfs_nt (strips; r2: ctfx_nt 25.92 tall, ctfs_nt = the closed ctfs outline; the closed ctrn is reused), new: ot_s81_hc_cncla / ot_s81_hc_cnclb (C = 0 / 1 / 2),
// ot_s81_hc_cnrsq; reused at a new slot: ot_s81_hc_cntree (h2 tuple).
// Faults (lane collision, missing / duplicate leaf at fire, tree / div / eps / rsqrt) are sticky in the bottom and
// enter chain 0's far tile on the return valid word (bit S_RT + 2): crx x_f1 -> cseq fault code 1.
// ---------------------------------------------------------------------------------------------------------------------

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_ctfx_nt (centre strip, the closed ctfx outline 576.72 x 12.96): ctfx's fv / fdx pin flops (the slot-wide
// broadcast source) + the two NORM-tree lanes.
//   ul (north, 33 b {v, r}): pin flop ul_out <= ul_in; the NEXT cycle it is this half-tile's r beat: fv[S_RD+3] /
//      fdx[O_R] (the bus r bit is masked: the old root path's r never reaches a consumer).
//   dl (south, DLW b = 2 slots {data 128, vector 3, octet 5, v} + sticky fault): pin flop dl_out <= dl_in, and the far
//      half (tid[0]) of an octet merges its 4-bank chunk sum cs into slot (octet & 1) in the cycle ctra latches it
//      (vs[DS] of a ctq replica on the same local epoch).  A slot already full sets the fault bit.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_ctfx_nt #(
    parameter integer NG = 256, D = 5120, S_RD = 2, ML = 5, AL = 4, CHAIN_STEP = AL, LOCAL_EPOCH = 1
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FXW-1:0]     fd_in,
    output reg  [S_RD+4:0]    fv,
    output reg  [FXW-1:0]     fdx,
    output wire [S_RD+4:0]    fv_local,
    output wire [FXW-1:0]     fdx_local,
    input  wire [7:0]         tid,
    input  wire [63:0]        cs_n,          // chunk sums of banks 0 / 1 (ctnl rows above the band: lanes 3, 7)
    input  wire [63:0]        cs_s,          // banks 2 / 3 (rows below: lanes 11, 15)
    input  wire [DLW-1:0]     dl_in,
    output reg  [DLW-1:0]     dl_out,
    input  wire [32:0]        ul_in,
    output reg  [32:0]        ul_out
);
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer SW = 137, DLW = 2 * SW + 1, DS = ML + 7 * CHAIN_STEP;
    reg rr;
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; ul_out <= 0; end
        else begin fv <= {fv_in[S_RD+4], ul_out[32], fv_in[S_RD+2:0]}; ul_out <= ul_in; end
    always @(posedge clk) begin
        fdx <= fd_in;
        if (ul_out[32]) fdx[O_R +: 32] <= ul_out[31:0];
    end
    // Own the local broadcast capture physically; the cth region wrapper must contain no state.
    // Its reset is the incoming rst_c epoch, exactly the former region register's reset (not rr).
    generate if (LOCAL_EPOCH) begin : g_local_capture
        reg [S_RD+4:0] v;
        reg [FXW-1:0] d;
        always @(posedge clk or negedge rst_in)
            if (!rst_in) v <= 0; else v <= fv;
        always @(posedge clk) d <= fdx;
        assign fv_local = v;
        assign fdx_local = d;
    end else begin : g_no_local_capture
        assign fv_local = fv;
        assign fdx_local = fdx;
    end endgenerate
    // ctq replica on ctra's epoch (cth CNL_PIN: one local register after the broadcast flops)
    wire [S_RD+4:0] fvl;
    wire [O_D-1:0]  fcl;
    generate if (LOCAL_EPOCH) begin : g_le
        reg [S_RD+4:0] v;
        reg [O_D-1:0]  c;
        always @(posedge clk or negedge rst_n) if (!rst_n) v <= 0; else v <= fv;
        always @(posedge clk) c <= fdx[O_D-1:0];
        assign fvl = v; assign fcl = c;
    end else begin : g_nle
        assign fvl = fv; assign fcl = fdx[O_D-1:0];
    end endgenerate
    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [2*ML+1:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP)) u_q (.clk(clk), .rst_n(rst_n),
        .fv(fvl), .fdx({{(FXW - O_D){1'b0}}, fcl}), .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v),
        .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i), .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    wire [127:0] cs = {cs_s, cs_n};
    reg       farq;
    reg [4:0] oct;
    always @(posedge clk) begin farq <= tid[0]; oct <= tid[5:1]; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) dl_out <= 0;
        else begin : mrg
            reg [DLW-1:0] o;
            o = dl_in;
            if (vs[DS] && farq) begin
                if (o[SW * oct[0]]) o[DLW-1] = 1'b1;
                o[SW * oct[0] +: SW] = {cs, si[2:0], oct, 1'b1};
            end
            dl_out <= o;
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Bottom collector of chain C, split by BANK HALF into two hardened leaves with their own clock roots
// (el1014-s81-norm-tree r2, 2026-10-14): the single-root collector ot_s81_hc_cnclt measured 19,155 / 16,082 / 19,155
// sinks (C 0 / 1 / 2) with TT insertion 407.0 / 365.0 / 362.7 ps > 300 (clock rule REFUSE).  Every node the chain owns
// covers leaves of ONE bank (sz <= NS, NS a power of two, leaf j NS + s), so the chain's subtree is four independent
// per-bank subtrees: banks 0 / 1 -> ot_s81_hc_cncla, banks 2 / 3 -> ot_s81_hc_cnclb, each with half the leaf buffer
// (NV x LC x 64 b) and half the adders (~9.6k sinks a leaf).  Same ot_dsrom_qadd nodes, same pairing, same fire offset
// NT_K: the exports are the golden tree's, bit for bit, and leave on output flops in the same cycle as before; the
// bottom wrapper (wires) interleaves the two halves' exports back into the closed ot_s81_hc_cntree's heap order.
// Leaf pins (both halves): N f_fv / f_nv / dl (the half's 64 data bits of each lane slot + the slot's tags, from the far
// tile above); S ex (A: + rvt / pi / flt, to cntree / cnrsq); the halves abut on A's E / B's W face: B's sticky fault
// enters A on a pin flop (A's flt one cycle later for a B-side fault; faults are sticky, the code is unchanged).
// Also from the r1 gate: the leaf write is decoded per (vector, octet) (no runtime part-select) and the leaf read is a
// one-hot select registered per octet (was one 3-bit index with 5,654 loads).
// Sticky fault: lane fault bit (A), a leaf outside the chain / a vector >= NV / a duplicate, a leaf missing at fire, tree.
// NT_K 67 = measured (hc_gate NG 256 hier3, 0c402af5a NT_DBG): the far octet's leaf of vector j is captured 66 cycles
// after j's beat (all three chains in the same cycle); zero slack, the missing-leaf fault guards it (NT_K 66 must FAIL).
// ---------------------------------------------------------------------------------------------------------------------

// one bank half of the chain's subtree of the golden pairwise tree (ot_s81_hc_stree OWN = C restricted to banks 2H, 2H+1)
module ot_s81_hc_streeh #(
    parameter integer NS = 32, NP = 11, LA = 4, OWN = 0, H = 0
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   v,
    input  wire [NP*64-1:0]       pk,             // slot p, bank 2H + j at 64 p + 32 j
    output wire [NEX*32-1:0]      ex,             // this half's exported nodes, increasing heap order
    output wire                   fault
);
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
    function automatic integer half(input integer n);
        half = (((n << lev(n)) - NL) / NS) / 2;
    endfunction
    function automatic integer mine(input integer n);
        mine = (owner(n) == OWN) && (half(n) == H);
    endfunction
    function automatic integer expd(input integer n);
        expd = mine(n) && (n == 1 || owner(n / 2) != OWN);
    endfunction
    function automatic integer exidx(input integer n);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m); exidx = t; end
    endfunction
    localparam integer NEX_ = exidx(2 * NL);
    localparam integer NEX  = (NEX_ > 0) ? NEX_ : 1;
    localparam integer B = (OWN == 0) ? B0 : (OWN == 1) ? B1 : B2;

    wire [LT*LA:0] vl;
    ot_hdc_vline #(.D(LT * LA)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    wire [31:0]     val [1:2*NL-1];
    wire [2*NL-1:0] f;
    assign f[0] = 1'b0;
    genvar n;
    generate
        for (n = 1; n < 2 * NL; n = n + 1) begin : g_n
            localparam integer K = lev(n);
            if (mine(n)) begin : g_own
                if (n >= NL) begin : g_leaf                       // bank J (2H or 2H + 1), sub-tile S = slot S - B
                    localparam integer J = (n - NL) / NS, S = (n - NL) % NS;
                    assign val[n] = pk[64 * (S - B) + 32 * (J - 2 * H) +: 32];
                    assign f[n] = 1'b0;
                end else begin : g_add
                    ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vl[LA * (K - 1)], val[2 * n], val[2 * n + 1], val[n], f[n]);
                end
                if (expd(n)) begin : g_ex
                    assign ex[32 * exidx(n) +: 32] = val[n];
                end
            end else begin : g_none
                assign val[n] = 32'd0;
                assign f[n] = 1'b0;
            end
        end
        if (NEX_ == 0) begin : g_nex
            assign ex = 32'd0;
        end
    endgenerate
    assign fault = |f;
endmodule

// the bank-half collector datapath shared by ot_s81_hc_cncla / ot_s81_hc_cnclb (not a tile by itself)
module ot_s81_hc_cncl_core #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, AL = 4, C = 0, H = 0, NT_K = 67
) (
    input  wire                 sk,
    input  wire                 rs_n,
    input  wire [S_RD+4:0]      f_fv,
    input  wire [7:0]           f_nv,
    input  wire [DLH-1:0]       dl,            // 2 slots {data 64, vector 3, octet 5, v} (+ lane fault, H 0)
    output reg                  v_q,
    output reg  [2:0]           i_q,
    output wire [NEX*32-1:0]    ex_w,
    output wire                 e_any          // this cycle's lane / leaf / missing / tree fault
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, NL = 4 * NS, LT = $clog2(NL);
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2, BC = (C == 0) ? B0 : (C == 1) ? B1 : B2;
    localparam integer N = 4 * NG, NV = D / N;
    localparam integer SH = 73, DLH = 2 * SH + ((H == 0) ? 1 : 0);
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
    function automatic integer expd(input integer n);
        expd = (owner(n) == C) && ((((n << lev(n)) - NL) / NS) / 2 == H) && (n == 1 || owner(n / 2) != C);
    endfunction
    function automatic integer exidx(input integer n);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m); exidx = t; end
    endfunction
    localparam integer NEX_ = exidx(2 * NL);
    localparam integer NEX = (NEX_ > 0) ? NEX_ : 1;
`ifndef SYNTHESIS
    initial if (NV > 8 || LC < 1 || NT_K < 3 || H > 1) $fatal(1, "ot_s81_hc_cncl_core: NV <= 8 vectors, a live chain, NT_K >= 3, H 0 / 1");
`endif
    // pin flops
    reg [S_RD+4:0] fvq;
    reg [7:0]      nvq;
    reg [DLH-1:0]  dlq;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin fvq <= 0; dlq <= 0; end
        else begin fvq <= f_fv; dlq <= dl; end
    always @(posedge sk) nvq <= f_nv;
    wire ng_v = fvq[S_RD+1], nv_v = fvq[S_RD+2];
    // leaf buffer: decoded per (vector, octet), no runtime part-select
    reg [63:0]   lb [0:NV*LC-1];          // vector j, octet p at j LC + p
    reg [LC-1:0] hv [0:NV-1];
    reg          e_lane;
    integer q, j, p;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin
            for (j = 0; j < NV; j = j + 1) hv[j] <= 0;
            e_lane <= 1'b0;
        end else begin
            e_lane <= 1'b0;
            if (H == 0 && dlq[DLH-1]) e_lane <= 1'b1;
            if (ng_v) for (j = 0; j < NV; j = j + 1) hv[j] <= 0;
            else
                for (q = 0; q < 2; q = q + 1)
                    if (dlq[SH * q]) begin : lf
                        reg [4:0] o;
                        reg [2:0] vi;
                        o = dlq[SH * q + 1 +: 5]; vi = dlq[SH * q + 6 +: 3];
                        if (o < BC || o >= BC + LC || vi >= NV || hv[vi][o - BC]) e_lane <= 1'b1;
                        else hv[vi][o - BC] <= 1'b1;
                    end
        end
    always @(posedge sk)
        for (q = 0; q < 2; q = q + 1)
            for (j = 0; j < NV; j = j + 1)
                for (p = 0; p < LC; p = p + 1)
                    if (dlq[SH * q] && dlq[SH * q + 1 +: 5] == BC + p && dlq[SH * q + 6 +: 3] == j)
                        lb[j * LC + p] <= dlq[SH * q + 9 +: 64];
    // fire schedule: vector beat at the far tile + NT_K; the read select is decoded one cycle early and registered
    // once per octet (one-hot, <= 64 loads a bit)
    wire [NT_K:0] fl;
    wire [2:0]    fi1;
    reg  [2:0]    fi;
    (* keep = "true" *) reg [NV-1:0] sel [0:LC-1];
    ot_hdc_vline #(.D(NT_K)) u_fl (.clk(sk), .rst_n(rs_n), .v(nv_v), .vd(fl));
    ot_hdc_delay #(.W(3), .D(NT_K - 1)) u_fi (.clk(sk), .rst_n(rs_n), .d(nvq[2:0]), .q(fi1));
    always @(posedge sk) begin
        fi <= fi1;
        for (p = 0; p < LC; p = p + 1)
            for (j = 0; j < NV; j = j + 1) sel[p][j] <= (fi1 == j);
    end
    reg              e_miss;
    reg [LC*64-1:0]  pk_q;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin v_q <= 1'b0; e_miss <= 1'b0; end
        else begin v_q <= fl[NT_K]; e_miss <= fl[NT_K] && (hv[fi] != {LC{1'b1}}); end
    always @(posedge sk) begin
        i_q <= fi;
        for (p = 0; p < LC; p = p + 1) begin : rd
            reg [63:0] a;
            a = 64'd0;
            for (j = 0; j < NV; j = j + 1) a = a | (lb[j * LC + p] & {64{sel[p][j]}});
            pk_q[64 * p +: 64] <= a;
        end
    end
    wire tf;
    ot_s81_hc_streeh #(.NS(NS), .NP(NP), .LA(AL), .OWN(C), .H(H)) u_tree (.clk(sk), .rst_n(rs_n), .v(v_q),
        .pk({{((NP - LC) * 64){1'b0}}, pk_q}), .ex(ex_w), .fault(tf));
    assign e_any = e_lane | e_miss | tf;
endmodule

// ot_s81_hc_cncla: banks 0 / 1 of chain C's collector + the chain's rvt / pi to cntree + the collector's sticky fault
// (B's fault enters on the E-face pin flop flt_b)
module ot_s81_hc_cncla #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, AL = 4, C = 0, NT_K = 67
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [S_RD+4:0]      f_fv,          // far tile fv_out
    input  wire [7:0]           f_nv,          // far tile fd_out[O_NV +: 8]
    input  wire [2*73:0]        dl,            // far tile partial lane: banks 0 / 1 of both slots + tags + lane fault
    input  wire                 flt_b,         // ot_s81_hc_cnclb's sticky fault
    output reg                  rvt,
    output reg  [7:0]           pi,
    output reg  [NEX*32-1:0]    ex,
    output reg                  flt
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, NL = 4 * NS, LT = $clog2(NL);
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
    function automatic integer expd(input integer n);
        expd = (owner(n) == C) && ((((n << lev(n)) - NL) / NS) / 2 == 0) && (n == 1 || owner(n / 2) != C);
    endfunction
    function automatic integer exidx(input integer n);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m); exidx = t; end
    endfunction
    localparam integer NEX_ = exidx(2 * NL);
    localparam integer NEX = (NEX_ > 0) ? NEX_ : 1;
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg fbq;
    always @(posedge sk or negedge rs_n) if (!rs_n) fbq <= 1'b0; else fbq <= flt_b;
    wire              v_q, e_any;
    wire [2:0]        i_q;
    wire [NEX*32-1:0] ex_w;
    ot_s81_hc_cncl_core #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .AL(AL), .C(C), .H(0), .NT_K(NT_K)) u_c (
        .sk(sk), .rs_n(rs_n), .f_fv(f_fv), .f_nv(f_nv), .dl(dl), .v_q(v_q), .i_q(i_q), .ex_w(ex_w), .e_any(e_any));
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin rvt <= 1'b0; flt <= 1'b0; end
        else begin rvt <= v_q; flt <= flt | e_any | fbq; end
    always @(posedge sk) begin pi <= {5'd0, i_q}; ex <= ex_w; end
endmodule

// ot_s81_hc_cnclb: banks 2 / 3 of chain C's collector; its sticky fault leaves on the W face to ot_s81_hc_cncla
module ot_s81_hc_cnclb #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, AL = 4, C = 0, NT_K = 67
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [S_RD+4:0]      f_fv,          // far tile fv_out
    input  wire [7:0]           f_nv,          // far tile fd_out[O_NV +: 8]
    input  wire [2*73-1:0]      dl,            // far tile partial lane: banks 2 / 3 of both slots + tags
    output reg  [NEX*32-1:0]    ex,
    output reg                  flt
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, NL = 4 * NS, LT = $clog2(NL);
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
    function automatic integer expd(input integer n);
        expd = (owner(n) == C) && ((((n << lev(n)) - NL) / NS) / 2 == 1) && (n == 1 || owner(n / 2) != C);
    endfunction
    function automatic integer exidx(input integer n);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m); exidx = t; end
    endfunction
    localparam integer NEX_ = exidx(2 * NL);
    localparam integer NEX = (NEX_ > 0) ? NEX_ : 1;
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    wire              v_q, e_any;
    wire [2:0]        i_q;
    wire [NEX*32-1:0] ex_w;
    ot_s81_hc_cncl_core #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .AL(AL), .C(C), .H(1), .NT_K(NT_K)) u_c (
        .sk(sk), .rs_n(rs_n), .f_fv(f_fv), .f_nv(f_nv), .dl(dl), .v_q(v_q), .i_q(i_q), .ex_w(ex_w), .e_any(e_any));
    always @(posedge sk or negedge rs_n)
        if (!rs_n) flt <= 1'b0;
        else flt <= flt | e_any;
    always @(posedge sk) ex <= ex_w;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cnrsq (bottom scalar tail): ot_s81_hc_cseq's norm tail at the far end.  eps: COEF row 1 of each slot as it
// leaves chain 0's far tile (rd kind 2, row counter 1: bits 256 .. 287 of the read slot), selected by the norm go's slot
// bit.  ss (ot_s81_hc_cntree output flops) -> capture -> / D (ot_dsrom_divc) -> + eps -> rsqrt -> r on three equal
// lane registers (one a chain).  Sticky fault: tree / div / eps / rsqrt / the collectors'.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cnrsq #(
    parameter integer NG = 256, D = 5120, S_RD = 2, ML = 5, AL = 4
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [S_RD+4:0]      f_fv,          // chain 0 far tile fv_out
    input  wire [O_D-1:0]       f_fc,          // its fd_out control word
    input  wire [S_RD*32-1:0]   f_eps,         // its fd_out[O_D + 512 s + 256 +: 32], s < S_RD
    input  wire                 ss_v,
    input  wire [31:0]          ss,
    input  wire                 tflt,
    input  wire [2:0]           cflt,
    output reg  [3*33-1:0]      ul,
    output reg                  flt,
    output reg                  ngo             // physical owner of the cntree norm-go launch flop
);
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1;
    localparam integer LA = AL, LM = ML;
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    always @(posedge sk or negedge rs_n)
        if (!rs_n) ngo <= 1'b0; else ngo <= f_fv[S_RD + 1];
    reg [S_RD+4:0]     fvq;
    reg [O_D-1:0]      fcq;
    reg [S_RD*32-1:0]  epq;
    reg                ssq_v, tfq;
    reg [31:0]         ssq;
    reg [2:0]          cfq;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin fvq <= 0; ssq_v <= 1'b0; tfq <= 1'b0; cfq <= 0; end
        else begin fvq <= f_fv; ssq_v <= ss_v; tfq <= tflt; cfq <= cflt; end
    always @(posedge sk) begin fcq <= f_fc; epq <= f_eps; ssq <= ss; end
    reg [31:0] cf_eps [0:1];
    reg [31:0] n_eps;
    integer s;
    always @(posedge sk) begin
        for (s = 0; s < S_RD; s = s + 1)
            if (fvq[s] && fcq[O_RK +: 2] == 2'd2 && fcq[O_RC + 16 * s +: 16] == 16'd1) cf_eps[fcq[O_RS]] <= epq[32 * s +: 32];
        if (fvq[S_RD+1]) n_eps <= cf_eps[fcq[O_NG + 1]];
    end
    wire [31:0] mq, me, rr_;
    wire        mq_v, rr_v, f_div, f_ep, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(sk), .rst_n(rs_n), .v(ssq_v), .x(ssq), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(sk), .rst_n(rs_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (sk, rs_n, mq_v, mq, n_eps, me, f_ep);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(sk), .rst_n(rs_n), .v(ve[LA]), .x(me), .y(rr_), .vo(rr_v), .fault(f_rsq));
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin ul <= 0; flt <= 1'b0; end
        else begin ul <= {3{rr_v, rr_}}; flt <= flt | tfq | (|cfq) | f_div | f_ep | f_rsq; end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cnbot (bottom region wrapper, wires only, never hardened): the three collectors (each two bank-half leaves
// ot_s81_hc_cncla / ot_s81_hc_cnclb, exports interleaved back into heap order), the closed final-rung
// tile ot_s81_hc_cntree at its h2 tuple (ngo = the norm go as it leaves chain 0's far tile), the scalar tail.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cnbot #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, NT_K = 67
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [3*FVW-1:0]     f_fv,          // per chain: far tile fv_out
    input  wire [3*8-1:0]       f_nv,          // per chain: far tile fd_out[O_NV +: 8]
    input  wire [O_D-1:0]       f_fc0,         // chain 0: far tile fd_out control word
    input  wire [S_RD*32-1:0]   f_eps0,        // chain 0: eps bits of the read slots
    input  wire [3*DLW-1:0]     dl,            // per chain: partial lane
    output wire [3*33-1:0]      ul,            // per chain: scale lane
    output wire                 flt
);
    localparam integer FVW = S_RD + 5, SW = 137, DLW = 2 * SW + 1;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, O_NG = 5 + S_RD * 16 + 20;
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, NL = 4 * NS, LT = $clog2(NL);
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
    localparam integer NE0_ = exidx(2 * NL, 0), NE1_ = exidx(2 * NL, 1), NE2_ = exidx(2 * NL, 2);
    localparam integer NE0 = (NE0_ > 0) ? NE0_ : 1, NE1 = (NE1_ > 0) ? NE1_ : 1, NE2 = (NE2_ > 0) ? NE2_ : 1;
    localparam integer NEM = (NE0 > NE1) ? ((NE0 > NE2) ? NE0 : NE2) : ((NE1 > NE2) ? NE1 : NE2);
    function automatic integer hlf(input integer n);
        hlf = (((n << lev(n)) - NL) / NS) / 2;
    endfunction
    function automatic integer exh(input integer n, input integer c, input integer h);   // index among half h's exports
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + (expd(m, c) && hlf(m) == h); exh = t; end
    endfunction
    function automatic integer neh(input integer c, input integer h);
        neh = (exh(2 * NL, c, h) > 0) ? exh(2 * NL, c, h) : 1;
    endfunction
    wire [2:0] rv, cf, fb;
    wire [7:0] pc [0:2];
    wire [NEM*32-1:0] xf [0:2];                          // per chain: the full export vector in heap order
    wire [NEM*32-1:0] xa [0:2], xb [0:2];                // per chain: bank-half exports
    genvar c, n;
    generate
        for (c = 0; c < 3; c = c + 1) begin : g_c
            localparam integer NA = neh(c, 0), NB = neh(c, 1);
            wire [DLW-1:0] dlc = dl[c * DLW +: DLW];
            // the lane split by bank half: slot q = {data 128, vector 3, octet 5, v} -> {data 64 of the half, tags 9}
            wire [2*73:0]   dla = {dlc[DLW-1], dlc[SW + 9 +: 64], dlc[SW +: 9], dlc[9 +: 64], dlc[0 +: 9]};
            wire [2*73-1:0] dlb = {dlc[SW + 73 +: 64], dlc[SW +: 9], dlc[73 +: 64], dlc[0 +: 9]};
            ot_s81_hc_cncla #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .AL(AL), .C(c), .NT_K(NT_K)) u_a (.sk(sk),
                .srs(srs), .f_fv(f_fv[c * FVW +: FVW]), .f_nv(f_nv[c * 8 +: 8]), .dl(dla), .flt_b(fb[c]), .rvt(rv[c]), .pi(pc[c]),
                .ex(xa[c][NA*32-1:0]), .flt(cf[c]));
            ot_s81_hc_cnclb #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .AL(AL), .C(c), .NT_K(NT_K)) u_b (.sk(sk),
                .srs(srs), .f_fv(f_fv[c * FVW +: FVW]), .f_nv(f_nv[c * 8 +: 8]), .dl(dlb), .ex(xb[c][NB*32-1:0]), .flt(fb[c]));
            if (NA < NEM) begin : g_pa
                assign xa[c][NEM*32-1:NA*32] = {((NEM - NA) * 32){1'b0}};
            end
            if (NB < NEM) begin : g_pb
                assign xb[c][NEM*32-1:NB*32] = {((NEM - NB) * 32){1'b0}};
            end
            for (n = 1; n < 2 * NL; n = n + 1) begin : g_x
                if (expd(n, c)) begin : g_e
                    if (hlf(n) == 0) begin : g_ha
                        assign xf[c][32 * exidx(n, c) +: 32] = xa[c][32 * exh(n, c, 0) +: 32];
                    end else begin : g_hb
                        assign xf[c][32 * exidx(n, c) +: 32] = xb[c][32 * exh(n, c, 1) +: 32];
                    end
                end
            end
            if (exidx(2 * NL, c) < NEM) begin : g_pf
                assign xf[c][NEM*32-1:exidx(2 * NL, c)*32] = {((NEM - exidx(2 * NL, c)) * 32){1'b0}};
            end
        end
    endgenerate
    wire [NE0*32-1:0] x0 = xf[0][NE0*32-1:0];
    wire [NE1*32-1:0] x1 = xf[1][NE1*32-1:0];
    wire [NE2*32-1:0] x2 = xf[2][NE2*32-1:0];
    wire [7:0] p0 = pc[0], p1 = pc[1], p2 = pc[2];
    wire ngo; // cnrsq owns this registered launch; the region wrapper contains no state.
    wire        ss_v, tflt;
    wire [31:0] ss;
    ot_s81_hc_cntree #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL),
                       .HALF(1), .RLY(2), .RF(4), .DW(6)) u_tr (
        .sk(sk), .srs(srs), .w_rvt(rv[0]), .e_rvt(rv[2]), .w_pi(p0), .e_pi(p2), .w_ex(x0), .e_ex(x2),
        .c_rvt(rv[1]), .c_pi(p1), .c_ex(x1), .ngo_i(ngo), .ss_v(ss_v), .ss(ss), .tflt(tflt));
    ot_s81_hc_cnrsq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL)) u_rsq (.sk(sk), .srs(srs), .f_fv(f_fv[0 +: FVW]),
        .f_fc(f_fc0), .f_eps(f_eps0), .ss_v(ss_v), .ss(ss), .tflt(tflt), .cflt(cf), .ul(ul), .flt(flt), .ngo(ngo));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cth_nt: ot_s81_hc_cth (region wrapper, no route) with ctfx / ctfs / ctrn replaced by their _nt masters and the
// two lane port pairs; every other line is the closed wrapper's.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cth_nt #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer RLY = 2, CNL_PIN = 0, CHAIN_STEP = AL, LANE_SPECIALIZE = 0
) (
    input  wire                       clk,
    input  wire                       rst_in,
    output wire                       rst_out,
    input  wire [7:0]                 tid,
    input  wire                       last,
    input  wire [S_RD+4:0]            fv_in,
    input  wire [FDW-1:0]             fd_in,
    output wire [S_RD+4:0]            fv_out,
    output wire [FDW-1:0]             fd_out,
    input  wire [S_RT+3:0]            rv_in,
    input  wire [RDW-1:0]             rd_in,
    output wire [S_RT+3:0]            rv_out,
    output wire [RDW-1:0]             rd_out,
    output wire [127:0]               cy_out,
    input  wire [127:0]               cy_in,
    // NORM tree lanes (ot_s81_hc_ctfx_nt): partial-sum lane south (dl), scale lane north (ul)
    input  wire [DLW-1:0]             dl_in,
    output wire [DLW-1:0]             dl_out,
    input  wire [32:0]                ul_in,
    output wire [32:0]                ul_out
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    localparam integer RDW = S_RT + 8 * S_RT + 16 * S_RT + 8 + 512 * S_RT;
    localparam integer DLW = 2 * 137 + 1;
`ifndef SYNTHESIS
    initial if (LANE_SPECIALIZE && !CNL_PIN) $fatal(1,"cth LANE_SPECIALIZE requires CNL_PIN");
    initial if (RLY < 2 || GS != 8) $fatal(1, "ot_s81_hc_cth: RLY >= 2 (the return merge takes a relay stage), GS 8");
`endif

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [S_RD+4:0] fv;
    wire [FXW-1:0]  fdx;
    wire [S_RD+4:0] fv_local;
    wire [FXW-1:0] fdx_local;
    wire [S_RD+4:0] fvm;
    wire [4*32-1:0] cs;
    wire [16*32-1:0] acc;
    wire [FDW-1:0]  fdm;
    wire            rst_c;                     // ctfn's first reset stage -> one relay flop in every tile
    ot_s81_hc_ctfn #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD)) u_fn (
        .clk(clk), .rst_in(rst_in), .rst_c(rst_c), .fv_in(fv_in), .fd_in(fd_in), .fvm(fvm), .fdm(fdm));
    wire [DLW-1:0] dl_m;
    wire [32:0]    ul_m;
    ot_s81_hc_ctfx_nt #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .LOCAL_EPOCH(CNL_PIN)) u_fx (
        .clk(clk), .rst_in(rst_c), .fv_in(fv_in), .fd_in(fd_in[FXW-1:0]), .fv(fv), .fdx(fdx), .fv_local(fv_local), .fdx_local(fdx_local),
        .tid(tid), .cs_n(cs[63:0]), .cs_s(cs[127:64]), .dl_in(dl_in), .dl_out(dl_m), .ul_in(ul_m), .ul_out(ul_out));
    ot_s81_hc_ctfs_nt #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .RLY(RLY)) u_fs (
        .clk(clk), .rst_in(rst_c), .rst_out(rst_out), .fvm(fvm), .fdm(fdm), .fv_out(fv_out), .fd_out(fd_out),
        .dl_in(dl_m), .dl_out(dl_out), .ul_in(ul_in), .ul_out(ul_m));
    wire [16*S_RT-1:0]  rq_q;
    wire                hs_run;
    wire [15:0]         hs_c;
    // One physical source per horizontal CTNL column, same registered epoch.
    wire [16*S_RT-1:0] rq_col [0:3];
    wire [3:0] hs_run_col;
    wire [15:0] hs_c_col [0:3];
    assign rq_col[0] = rq_q;
    assign hs_run_col[0] = hs_run;
    assign hs_c_col[0] = hs_c;
    wire [16*64-1:0]    hpr;                       // lane tile n = 4 bank + group
    wire [16*64*S_RT-1:0] hrq;
    wire [16*16-1:0]    yb;
    wire [16*32-1:0]    sq, cyo;
    wire [15:0]         nflt;
    wire [7:0]          hov, pwb, phs, hnz_d, pflt_d, hov_d;
    wire [8*16-1:0]     pob;
    wire [8*32-1:0]     hpo;                       // lane-pair tile m = 2 group + half
    genvar j, l, m;
    generate for (j = 0; j < 4; j = j + 1) begin : g_b
        for (l = 0; l < 4; l = l + 1) begin : g_l
            localparam integer n = 4 * j + l;
            if (!LANE_SPECIALIZE) begin : g_dynamic_lane
            ot_s81_hc_ctnl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fdx),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
            end else begin : g_fixed_lane
                localparam integer P_BITS=lane_payload_width(l);
                wire [O_D+S_RD*P_BITS-1:0] fd_lane;
                assign fd_lane[O_D-1:0]=fdx[O_D-1:0];
                for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
                    for(genvar pb=0;pb<P_BITS;pb=pb+1) begin : g_payload
                        localparam integer RAW_BIT=lane_payload_index(l,pb);
                        assign fd_lane[O_D+rp*P_BITS+pb]=fdx[O_D+rp*512+RAW_BIT];
                    end
                end
                if (l==0) begin : g_l0
            ot_s81_hc_ctnl_l0 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==1) begin : g_l1
            ot_s81_hc_ctnl_l1 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==2) begin : g_l2
            ot_s81_hc_ctnl_l2 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==3) begin : g_l3
            ot_s81_hc_ctnl_l3 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
            end
        end
        assign cy_out[32 * j +: 32] = cyo[32 * (4 * j + 2) +: 32];
    end endgenerate
    generate for (m = 0; m < 8; m = m + 1) begin : g_p
        ot_s81_hc_ctpl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL), .PIN_STAGE(1)) u_p (
            .clk(clk), .rst_in(rst_c), .grp(m[2:1]), .half(m[0]), .fv(fv_local), .fdx(fdx_local),
            .hpr({hpr[64 * (12 + m / 2) +: 64], hpr[64 * (8 + m / 2) +: 64], hpr[64 * (4 + m / 2) +: 64], hpr[64 * (m / 2) +: 64]}),
            .hov(hov[m]), .pwb(pwb[m]), .phs(phs[m]), .pob(pob[16 * m +: 16]), .hpo(hpo[32 * m +: 32]),
            .hov_d(hov_d[m]), .hnz_d(hnz_d[m]), .pflt_d(pflt_d[m]));
    end endgenerate
    assign cs = {acc[32 * 15 +: 32], acc[32 * 11 +: 32], acc[32 * 7 +: 32], acc[32 * 3 +: 32]};
    wire [S_RT+3:0] rvm;
    wire [RDW-1:0]  rdm;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, WA = P_D + 512 * SH;
    wire [8*64*SH-1:0] hqa_n, hqa_s, hqb_n, hqb_s;
    genvar q;
    generate for (j = 0; j < 8; j = j + 1) begin : g_hq
        for (q = 0; q < SH; q = q + 1) begin : g_s
            assign hqa_n[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * j + 64 * q +: 64];
            assign hqa_s[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * (j + 8) + 64 * q +: 64];
            assign hqb_n[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * j + 64 * (q + SH) +: 64];
            assign hqb_s[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * (j + 8) + 64 * (q + SH) +: 64];
        end
    end endgenerate
    ot_s81_hc_ctra #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(CNL_PIN)) u_ra (
        .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local[O_D-1:0]), .rv_in(rv_in),
        .rd_in(rd_in[WA-1:0]), .rvm(rvm), .rdm(rdm[WA-1:0]), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c),
        .rq_q_c1(rq_col[1]), .rq_q_c2(rq_col[2]), .rq_q_c3(rq_col[3]),
        .hs_run_c1(hs_run_col[1]), .hs_run_c2(hs_run_col[2]), .hs_run_c3(hs_run_col[3]),
        .hs_c_c1(hs_c_col[1]), .hs_c_c2(hs_c_col[2]), .hs_c_c3(hs_c_col[3]),
        .hrq_n(hqa_n), .hrq_s(hqa_s), .yb_n(yb[0 +: 128]), .yb_s(yb[128 +: 128]), .cs(cs),
        .nflt_n(nflt[7:0]), .nflt_s(nflt[15:8]), .hov_d(hov_d[0]),
        .hnz_n({hnz_d[6], hnz_d[4], hnz_d[2], hnz_d[0]}), .hnz_s({hnz_d[7], hnz_d[5], hnz_d[3], hnz_d[1]}),
        .pflt_n({pflt_d[6], pflt_d[4], pflt_d[2], pflt_d[0]}), .pflt_s({pflt_d[7], pflt_d[5], pflt_d[3], pflt_d[1]}));
    ot_s81_hc_ctrb #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(CNL_PIN)) u_rb (
        .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local[O_D-1:0]), .rv_in(rv_in),
        .rdh_in(rd_in[P_D-1:0]), .rdd_in(rd_in[RDW-1 -: 512 * SH + 128]), .rdm(rdm[RDW-1 -: 512 * SH]),
        .hrq_n(hqb_n), .hrq_s(hqb_s), .yb_n(yb[0 +: 128]), .yb_s(yb[128 +: 128]));
    ot_s81_hc_ctrn #(.S_RT(S_RT), .RDW(RDW), .RLY(RLY)) u_rn (                   // the CLOSED return strip, unchanged
        .clk(clk), .rst_in(rst_c), .rvm(rvm), .rdm(rdm), .rv_out(rv_out), .rd_out(rd_out));
endmodule

// ot_s81_hc_ctfs_nt: the closed ot_s81_hc_ctfs + one relay register of the partial lane (dl, N -> S) + one relay register
// of the scale lane (ul, S -> N; r2: moved here from ctrn_nt so the closed ctrn stands and its thin strip does not grow:
// hops ctfx_nt -> N face -> the tile above's ctfs_nt ~380 um, ctfs_nt -> its ctfx_nt ~335 um, both <= 500 um).
module ot_s81_hc_ctfs_nt #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, RLY = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    output wire               rst_out,
    input  wire [S_RD+4:0]    fvm,
    input  wire [FDW-1:0]     fdm,
    output reg  [S_RD+4:0]    fv_out,
    output reg  [FDW-1:0]     fd_out,
    input  wire [DLW-1:0]     dl_in,                 // NORM tree partial lane: relay south (pins N / S)
    output reg  [DLW-1:0]     dl_out,
    input  wire [32:0]        ul_in,                 // NORM tree scale lane: relay north (pins S / N)
    output reg  [32:0]        ul_out
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD;
    localparam integer DLW = 2 * 137 + 1;
    reg rr;                                              // regional reset relay: rst_in = ctfn's first stage
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    assign rst_out = rr;
    wire [S_RD+4:0] fvm_d;
    wire [FDW-1:0]  fdm_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fv_out <= 0;
        else fv_out <= fvm_d;
    always @(posedge clk) fd_out <= fdm_d;
    ot_hdc_delay #(.W(S_RD + 5), .D(RLY - 1), .RESET(1)) u_fvr (.clk(clk), .rst_n(rst_n), .d(fvm), .q(fvm_d));
    ot_hdc_delay #(.W(FDW), .D(RLY - 1)) u_fdr (.clk(clk), .rst_n(rst_n), .d(fdm), .q(fdm_d));
    always @(posedge clk or negedge rst_n) if (!rst_n) dl_out <= 0; else dl_out <= dl_in;
    always @(posedge clk or negedge rst_n) if (!rst_n) ul_out <= 0; else ul_out <= ul_in;
endmodule
