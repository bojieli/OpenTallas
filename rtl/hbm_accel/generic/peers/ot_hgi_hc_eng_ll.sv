`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 hyper-connection engine, LANE-LOCAL build (ot_hgi_hc_eng LL = 1; hbm-hcvm [ll], 2026-10-11).
// Owner textbook audit 10-11 of the central engine (ot_hgi_hc_ctl over 32 lane slices in the 4,601 x 1,566 um slot):
// class 4 (lane flags -> 32-way AND -> lane commands in one cycle over ~4.4 mm), class 2 (popq / e_v / a_rdy broadcast),
// class 5 (8,192-b beat assembly in one stage), class 1 (one tree over the slot).  This build moves the arithmetic into
// the 32 hardened lanes and leaves the top a relayed broadcast + a reduction tree + a scalar tail:
//
//   lane L (ot_hgi_hc_lane_ll, replicated): reads ONLY VM bank L, writes ONLY bank L, sequences itself.
//     HC_POST      for each of its 20 sectors i: y[i], res[0..3][i] (5 reads); 8 x ot_dsrom_su_hcpost_lane produce row
//                  k = 0..3 of sector i on 4 consecutive cycles -> the lane's write FIFO -> bank L.
//                  out[k][e] = BF16(y*post[k] + (((r0 c0k + r1 c1k) + r2 c2k) + r3 c3k)) (Model.hc_post), unchanged units.
//     HC_PRE_NORM  phase A: h[0..3][i] (4 reads) -> 8 x ot_dsrom_su_norm_mix: x = bf16(seqsum pre_j h_j), kept in the
//                  lane's x buffer; the sector's 8 squares summed sequentially (ot_dsrom_su_norm's chunk chain) = the
//                  golden csum LEAF of chunk i -> up to the top.  Phase B (after g_rdy): the FP32 gain sectors -> the
//                  lane's gain buffer.  Phase C (after the broadcast r): y = bf16(w * (x * r)) (ot_dsrom_su_norm's scale)
//                  -> bank L.
//   top (ot_hgi_hc_ctl_ll): job decode, scalar fetch through the owning lanes, a relayed command bus (RL flops a lane),
//     relayed lane status (RL flops), per-lane chunk FIFOs, the golden csum tree (32-chunk blocks by a 5-level
//     pipelined pairwise tree, the 20 blocks by the padded heap of ot_dsrom_su_norm: a node whose right subtree is all
//     padding passes its left value), ss / D (ot_dsrom_divc), + eps, rsqrt (ot_dsrom_rsqrt), r broadcast; retires when
//     every output write's VM done has come back (relayed done pulses, pipelined popcount) and every lane has reported
//     its read credits home and its FIFO drained.  No lane flag is used in the cycle it is produced.
//
// COMPILER ALLOCATION RULE (LL = 1): the vector operands and the output sit at the SAME VM bank phase (sector index
//   mod 32): HC_POST y (A), res (B), out (O); HC_PRE_NORM h (A), gain (B, FP32: GPK = 0), y (O).  The packed BF16 gain
//   (GPK = 1) spans two lanes a sector and is refused.  A refused job faults with no lane activity (the record falls
//   back to its lowering).  C (the scalars) may sit anywhere.
// MUT (bench negatives, must FAIL): 2 lane 0 swaps res rows 0 / 1 (HC_POST) / h rows 0 / 1 (PRE); 4 retire before the
//   write dones (the top ignores its done count, the lanes their write credits); 5 (PRE) the gain read does not wait for g_rdy.
// ---------------------------------------------------------------------------------------------------------------------

// relay: N register stages (valid with reset, data without)
module ot_hgi_hc_rly #(parameter integer W = 8, parameter integer N = 4) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [W-1:0] d,
    output wire         vq,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_0
        assign vq = v; assign q = d;
    end else begin : g_n
        wire [N:0] vd;
        ot_hdc_vline #(.D(N)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
        ot_hdc_delay #(.W(W), .D(N)) u_d (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
        assign vq = vd[N];
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// one lane: the hardened, replicated element of the LL engine.  Every input lands in a flop; every output is a flop.
// Down command (from the top, relayed): {op 3, x 8, d 128}
//   op 0 JOB  d = {gpk 1, post 1, o_s 15, b_s 15, a_s 15} (sector bases), clears the lane
//   op 1 WGT  beat x of the scalar words: x 0..4 = words 4x .. 4x+3 (HC_POST post[0..3] | comb[j][k] at 4 + 4j + k;
//             HC_PRE_NORM pre[0..3] in beat 0)
//   op 2 SCRD d[14:0] = a scalar sector, x = its slot: the owning lane (sector mod 32 == lid) reads it and returns it up
//   op 3 GO   op 4 GRDY (the gain is in VM)   op 5 RSTD d[31:0] = r
// Up: {v, t (0 scalar sector, 1 chunk sum), x 10 (slot / chunk index), d 256}; wdone (a write landed), fin (level:
//   the run is over: every read answered, every credit home, every output written to VM), flt (sticky).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_lane_ll #(
    parameter integer D   = 5120,
    parameter integer LQ  = 32,
    parameter integer FD  = 64,
    parameter integer HSL = 1,               // 1: the FP datapath as 8 hard element slices (ot_hgi_hc_lane_sl, own clock
                                             //    tree, registered in/out => +2 cycles); 0: flat (one 114k-flop clock root)
    parameter integer KX  = 2,               // H-MTP2: x-buffer row slots of a P-row HC_PRE_NORM (power of two)
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4:0]    lid,
    // VM bank lane
    output reg  [15:0]   wrq,
    input  wire          wrq_cr,
    input  wire [256:0]  wrr,
    output reg  [279:0]  wwq,
    input  wire          wwq_cr,
    input  wire          wwq_done,
    // top
    input  wire          dn_v,
    input  wire [2:0]    dn_op,
    input  wire [7:0]    dn_x,
    input  wire [127:0]  dn_d,
    output reg           up_v,
    output reg           up_t,
    output reg  [9:0]    up_x,
    output reg  [255:0]  up_d,
    output reg           wdone,
    output reg           fin,
    output reg           flt
);
    localparam integer SD = D / 8;           // sectors a row
    localparam integer NM = D / 256;         // sectors a lane (a row)
    localparam integer MB = $clog2(NM + 1);
    localparam integer QB = $clog2(LQ + 1);
    localparam integer FB = $clog2(FD + 1);
    localparam integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
    // ---- local reset relay
    // two reset regions: rl (pin flops, sequencer, FIFO) and rp (the FP pipelines' valid lines); control flops only
    wire [1:0] rlr; wire rl = rlr[0], rp = rlr[1];
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rlr));
    // ---- pin flops
    reg wrq_cr_q, wwq_cr_q, wwq_done_q, rv_q, dv_q; reg [255:0] rd_q; reg [2:0] dop_q; reg [7:0] dx_q; reg [127:0] dd_q;
    reg [4:0] lid_q;
    always @(posedge clk or negedge rl)
        if (!rl) begin wrq_cr_q <= 1'b0; wwq_cr_q <= 1'b0; wwq_done_q <= 1'b0; rv_q <= 1'b0; dv_q <= 1'b0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; rv_q <= wrr[256]; dv_q <= dn_v; end
    always @(posedge clk) begin rd_q <= wrr[255:0]; dop_q <= dn_op; dx_q <= dn_x; dd_q <= dn_d; lid_q <= lid; end

    // ---- job registers
    reg post, run, g_ok, r_ok; reg [14:0] a_s, b_s, o_s; reg [9:0] u;      // u = this lane's first sector of a row
    reg [1023:0] wt;                         // scalar words 0..19 (HC_POST) | H-MTP2 P-row PRE: pre of row p = beat p
    reg [31:0] rh;                           // rstd (the row being scaled)
    // H-MTP2 P-ROW HC_PRE_NORM (2026-10-15): JOB d[49:47] = nr = rows - 1 (0: the single-row job).  Row p reads h at
    //   a_s + p 4 SD, writes y at o_s + p SD (compiler rule: rows contiguous), its pre is WGT beat p, its r is RSTD
    //   x = p.  Read order: row 0 h, the gain (once), rows 1..nr h; row p's h issues only when row p - KX has been
    //   scaled (KX x-buffer slots); the scale of row p follows its r.  Fixed per-row cost, no new handshake off-lane.
    localparam integer KB = (KX > 1) ? $clog2(KX) : 1;
    reg [2:0] nr, rrow, yr;                  // rows-1 | response / y-write row
    reg [3:0] irow, xr, sr;                  // issue / x-write / scale row (0..nr + 1)
    reg [14:0] a_r, o_r;                     // h base of the issuing row, y base of the writing row
    reg g_in;                                // every gain sector landed
    reg [31:0] rha [0:7]; reg [7:0] rok;     // r of each row, landed
    reg [127:0] pre_q;                       // pre of the row being mixed (rides with mx_v)
    reg scp; reg [7:0] scx;                  // a scalar read pending
    // el1011-hbm-fused GPK: HC_PRE_NORM gain PACKED lane-local (BF16, compiler layout): packed sector u + 32 k of this
    // lane holds the gains of its data sectors u + 32 (2k) (words 0..3) and u + 32 (2k + 1) (words 4..7), so the gain
    // is D / 2 words (half the mover traffic) and still bank-local; NG = gain sectors this lane reads
    reg pk; wire [MB-1:0] NG = pk ? MB'(NM / 2) : MB'(NM);
    // el1011-hbm-fused READ PREFETCH (HC_POST): the lane starts its row reads on the JOB command (pf), not on GO, so the
    // top's scalar fetch / weight broadcast / GO relay (~2 RL + the scalar round trip) overlaps the reads.  Responses land
    // in a ring of RG sector groups {y, r0..r3} (the PRE x / gain buffers, idle on HC_POST); the k sweep consumes a whole
    // group a 4-cycle sweep (1.25 reads a cycle, faster than the 1-a-cycle read lane) once GO has delivered the weights.
    // Scalar reads now interleave with data reads on the bank lane: an in-order 1-bit tag FIFO (depth LQ = the lane's
    // credits) tells a scalar response from a data one.
    localparam integer RG = (2 * NM) / 5;    // ring groups (8 at D 5120)
    localparam integer RGB = (RG > 1) ? $clog2(RG) : 1;
    localparam integer TB = (LQ > 1) ? $clog2(LQ) : 1;
    reg pf;                                  // HC_POST: reads may issue (from JOB)
    reg [RGB-1:0] rgp, cgp; reg [MB:0] cg;   // ring write / consume group pointers, groups consumed
    function automatic [255:0] bf2f(input [127:0] h);
        integer e; begin bf2f = '0; for (e = 0; e < 8; e = e + 1) bf2f[32*e +: 32] = {h[16*e +: 16], 16'd0}; end
    endfunction
    wire c_job = dv_q && dop_q == 3'd0, c_wgt = dv_q && dop_q == 3'd1, c_scr = dv_q && dop_q == 3'd2;
    wire c_go = dv_q && dop_q == 3'd3, c_grdy = dv_q && dop_q == 3'd4, c_rstd = dv_q && dop_q == 3'd5;
    wire scr_mine = c_scr && dd_q[4:0] == lid_q;
    always @(posedge clk) begin
        if (c_job) begin post <= dd_q[45]; pk <= dd_q[46] && !dd_q[45]; a_s <= dd_q[14:0]; b_s <= dd_q[29:15]; o_s <= dd_q[44:30];
                         u <= {5'd0, 5'(lid_q - dd_q[4:0])}; nr <= dd_q[45] ? 3'd0 : dd_q[49:47]; end
        if (c_wgt) wt[128*dx_q[2:0] +: 128] <= dd_q;
        if (c_rstd) rha[dx_q[2:0]] <= dd_q[31:0];
    end

    // ---- read issue: scalar | HC_POST 5 a sector | PRE phase A 4 a sector, phase B 1 a sector (the gain)
    reg [QB-1:0] cr;
    reg [MB-1:0] im; reg [2:0] it;           // issue: sector m (0..NM-1), read t of it
    reg ph_b;                                // PRE: issuing the gain (phase B)
    reg [MB:0] gs, gp;                       // HC_POST: sectors started / fully pushed (FIFO admission)
    reg [FB-1:0] occ;
    wire [9:0] i_s = u + {im, 5'd0};         // the row sector of m
    reg rd_all;                              // PRE: every read of the job issued
    wire rd_done = post ? (im == MB'(NM)) : rd_all;
    wire xslot_ok = (irow - sr) < 4'(KX);     // PRE row irow's x slot is free (row irow - KX scaled)
    reg  iss; reg [14:0] isec;
    always @* begin
        iss = 1'b0; isec = '0;
        if (scr_mine) begin iss = 1'b1; isec = dd_q[14:0]; end
        else if ((run || pf) && cr != '0 && !rd_done) begin
            if (post) begin
                if (it != 3'd0 || (({1'b0, occ} + 8'(4 * (gs - gp)) + 8'd4 <= 8'(FD)) && ((gs - cg) < (MB+1)'(RG)))) begin
                    iss = 1'b1;
                    isec = (it == 3'd0) ? (a_s + 15'(i_s)) : (b_s + 15'(it - 3'd1) * 15'(SD) + 15'(i_s));
                end
            end else if (!ph_b) begin
                if (xslot_ok) begin iss = 1'b1; isec = a_r + 15'(it[1:0]) * 15'(SD) + 15'(i_s); end
            end else if (g_ok || MUT == 5) begin
                iss = 1'b1; isec = b_s + 15'(i_s);
            end
        end
    end
    always @(posedge clk or negedge rl)
        if (!rl) wrq[15] <= 1'b0; else wrq[15] <= iss;
    always @(posedge clk) wrq[14:0] <= isec;

    // ---- responses (in order on the bank lane)
    reg [MB-1:0] rm; reg [2:0] rt; reg rph_b;
    reg [255:0] asb [0:4];                    // sector assembly
    reg [255:0] op [0:4];                    // HC_POST operands of the sector in the k sweep (y, r0..r3)
    reg [255:0] xb [0:KX*NM-1], gb [0:NM-1]; // PRE: x (KX row slots) and gain of the lane's sectors
    reg sw; reg [1:0] kk;                    // HC_POST k sweep
    reg mx_v;                                // PRE: a sector's h quad to the mix
    reg [LQ-1:0] tgq; reg [TB-1:0] tgw, tgr;  // tag FIFO: 1 = a scalar read
    wire tg_h = tgq[tgr];
    always @(posedge clk) if (iss) tgq[tgw] <= scr_mine;
    always @(posedge clk or negedge rl)
        if (!rl) begin tgw <= '0; tgr <= '0; end
        else begin if (iss) tgw <= tgw + 1'b1; if (rv_q) tgr <= tgr + 1'b1; end
    wire rsp = rv_q && !tg_h;                // a data response
    wire srsp = rv_q && tg_h;                // a scalar response
    // HC_POST ring: write slot 5 rgp + rt, consume group cgp
    wire [7:0] rs_w = 8'(5 * rgp) + 8'(rt);
    wire cs_go = post && run && ({1'b0, rm} > cg) && (!sw || kk == 2'd3);
    function automatic [255:0] ring(input [7:0] i);
        ring = (i < 8'(NM)) ? xb[i] : gb[i - 8'(NM)];
    endfunction
    wire last_h = rsp && !rph_b && !post && rt == 3'd3;
    always @(posedge clk) begin
        if (rsp && !rph_b && !post) asb[rt] <= rd_q;
        if (cs_go) begin
            op[0] <= ring(8'(5 * cgp)); op[1] <= ring(8'(5 * cgp) + 8'd1); op[2] <= ring(8'(5 * cgp) + 8'd2);
            op[3] <= ring(8'(5 * cgp) + 8'd3); op[4] <= ring(8'(5 * cgp) + 8'd4);
            if (MUT == 2 && lid_q == 5'd0) begin op[1] <= ring(8'(5 * cgp) + 8'd2); op[2] <= ring(8'(5 * cgp) + 8'd1); end
        end
        if (rsp && post && rs_w >= 8'(NM)) gb[rs_w - 8'(NM)] <= rd_q;
        if (last_h) begin
            pre_q <= (MUT == 6) ? wt[127:0] : wt[128*rrow +: 128];     // MUT 6 (must FAIL): every row mixes with row 0's pre
            op[0] <= asb[0]; op[1] <= asb[1]; op[2] <= asb[2]; op[3] <= rd_q;
            if (MUT == 2 && lid_q == 5'd0) begin op[0] <= asb[1]; op[1] <= asb[0]; end
        end
        if (rsp && rph_b && !pk) gb[rm] <= rd_q;
        if (rsp && rph_b && pk) begin gb[{rm, 1'b0}] <= bf2f(rd_q[127:0]); gb[{rm, 1'b1}] <= bf2f(rd_q[255:128]); end
    end

    // ---- datapath: HC_POST 8 element pipelines (row k of the sector a cycle); HC_PRE_NORM mix / x / squares / chunk
    //      chain; phase C scale y = bf16(w * (x * r)).  HSL = 1: each element's pipelines are one hard slice
    //      (ot_hgi_hc_lane_sl) with pin flops in and registered outputs, so every slice output lands SX = 2 cycles later
    //      and the shell's x / chunk / y valid lines are SX longer.
    localparam integer SX = (HSL != 0) ? 2 : 0;
    wire [7:0] hv; wire [255:0] ho; wire [7:0] hf;
    wire [255:0] xl; wire [7:0] mf, sf; wire [255:0] sq;
    wire [255:0] pp, qq; wire [7:0] f1, f2;
    localparam integer DM = LM + 3 * LA + 1;
    wire [DM+SX:0] vm;
    ot_hdc_vline #(.D(DM + SX)) u_vm (.clk(clk), .rst_n(rl), .v(mx_v), .vd(vm));
    wire x_v = vm[DM + SX];
    reg sc_run; reg [MB-1:0] sm;             // scale sector issue
    reg [255:0] xo; reg xo_v; reg [MB-1:0] xo_m;
    wire [KB-1:0] ss_sl = KB'(sr);            // x slot of the row being scaled
    always @(posedge clk) begin xo <= xb[32'(ss_sl) * NM + 32'(sm)]; xo_m <= sm; end
    always @(posedge clk or negedge rl) if (!rl) xo_v <= 1'b0; else xo_v <= sc_run;
    wire [MB-1:0] wm_d;                      // the gain read LMS - 1 cycles after x's (the multiplier's operand register)
    ot_hdc_delay #(.W(MB), .D(LMS - 1)) u_wm (.clk(clk), .rst_n(rl), .d(xo_m), .q(wm_d));
    reg [255:0] wo;
    always @(posedge clk) wo <= gb[wm_d];
    wire [LMS:0] vx;
    ot_hdc_vline #(.D(LMS)) u_vx (.clk(clk), .rst_n(rl), .v(xo_v), .vd(vx));
    genvar e;
    generate if (HSL != 0) begin : g_hsl
        // HC_POST coefficients of row kk (shared by the 8 slices; the slices pin-flop them with sw)
        wire [159:0] cf5 = {wt[32*kk +: 32], wt[32*(4 + 12 + kk) +: 32], wt[32*(4 + 8 + kk) +: 32],
                            wt[32*(4 + 4 + kk) +: 32], wt[32*(4 + 0 + kk) +: 32]};
        for (e = 0; e < 8; e = e + 1) begin : g_sl
            // hard child: no parameter overrides (its defaults are this lane's LM / LA / LMS / ML / AL)
            ot_hgi_hc_lane_sl u_sl (.clk(clk), .rst_n(rst_n), .i_sw(sw),
                .i_op({op[4][32*e +: 32], op[3][32*e +: 32], op[2][32*e +: 32], op[1][32*e +: 32], op[0][32*e +: 32]}),
                .i_cf(cf5), .i_mx(mx_v), .i_pre(pre_q), .i_xov(xo_v), .i_xo(xo[32*e +: 32]), .i_rh(rh),
                .i_wov(vx[LMS]), .i_wo(wo[32*e +: 32]),
                .o_hv(hv[e]), .o_ho(ho[32*e +: 32]), .o_hf(hf[e]), .o_xl(xl[32*e +: 32]), .o_mf(mf[e]),
                .o_sq(sq[32*e +: 32]), .o_sf(sf[e]), .o_qq(qq[32*e +: 32]), .o_f1(f1[e]), .o_f2(f2[e]));
        end
        assign pp = '0;
    end else begin : g_flat
        for (e = 0; e < 8; e = e + 1) begin : g_hp
            ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u_h (.clk(clk), .rst_n(rp), .v(sw),
                .r0(op[1][32*e +: 32]), .r1(op[2][32*e +: 32]), .r2(op[3][32*e +: 32]), .r3(op[4][32*e +: 32]),
                .y(op[0][32*e +: 32]), .c0(wt[32*(4 + 0 + kk) +: 32]), .c1(wt[32*(4 + 4 + kk) +: 32]),
                .c2(wt[32*(4 + 8 + kk) +: 32]), .c3(wt[32*(4 + 12 + kk) +: 32]), .p(wt[32*kk +: 32]),
                .vo(hv[e]), .o(ho[32*e +: 32]), .fault(hf[e]));
        end
        for (e = 0; e < 8; e = e + 1) begin : g_mx
            ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rp), .v(mx_v), .h0(op[0][32*e +: 32]),
                .h1(op[1][32*e +: 32]), .h2(op[2][32*e +: 32]), .h3(op[3][32*e +: 32]), .pre(pre_q),
                .x(xl[32*e +: 32]), .fault(mf[e]));
            ot_hdc_qmul_lat #(LM) u_sq (clk, rp, x_v, xl[32*e +: 32], xl[32*e +: 32], sq[32*e +: 32], sf[e]);
        end
        for (e = 0; e < 8; e = e + 1) begin : g_sc
            ot_hdc_qmul_lat #(LMS) u_xr (clk, rp, xo_v, xo[32*e +: 32], rh, pp[32*e +: 32], f1[e]);
            ot_hdc_qmul_lat #(LMS) u_w  (clk, rp, vx[LMS], wo[32*e +: 32], pp[32*e +: 32], qq[32*e +: 32], f2[e]);
        end
    end endgenerate
    // the chunk chain (ot_dsrom_su_norm's, N = 8) over the squares
    localparam integer DS = LM + 7 * LA;
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rl), .v(x_v), .vd(vs));
    wire [31:0] acc [0:7]; wire [7:0] cf;
    assign acc[0] = sq[31:0]; assign cf[0] = 1'b0;
    genvar k;
    generate for (k = 1; k < 8; k = k + 1) begin : g_ch
        wire [31:0] sd;
        ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rp), .d(sq[32*k +: 32]), .q(sd));
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rp, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], cf[k]);
    end endgenerate
    wire cs_v = vs[DS];
    wire [LMS+SX:0] vq;
    ot_hdc_vline #(.D(LMS + SX)) u_vq (.clk(clk), .rst_n(rl), .v(vx[LMS]), .vd(vq));
    reg y_v; reg [255:0] yb;
    integer w;
    always @(posedge clk) for (w = 0; w < 8; w = w + 1) yb[32*w +: 32] <= bf16(qq[32*w +: 32]);
    always @(posedge clk or negedge rl) if (!rl) y_v <= 1'b0; else y_v <= vq[LMS + SX];

    // ---- outputs into the write FIFO (in order): HC_POST rows (om, ok), PRE y (ym)
    reg [MB-1:0] om, ym, xm, cm; reg [1:0] ok;
    wire [9:0] o_i = u + {om, 5'd0}, y_i = u + {ym, 5'd0}, c_i = u + {cm, 5'd0};
    wire push = hv[0] || y_v;
    wire [270:0] pdat = hv[0] ? {o_s + 15'(ok) * 15'(SD) + 15'(o_i), ho} : {o_r + 15'(y_i), yb};
    wire f_hv, ovf, pop; wire [270:0] f_hd;
    reg [QB-1:0] wcr;
    ot_fifo_sram_fwft #(.W(271), .DEPTH(FD), .MACRO(0), .ESL(64)) u_f (.clk(clk), .rst_n(rl), .push(push), .wdata(pdat), .pop(pop),
        .hv(f_hv), .head(f_hd), .ovf(ovf));
    assign pop = run && f_hv && (wcr != '0);
    always @(posedge clk or negedge rl) if (!rl) wwq[279] <= 1'b0; else wwq[279] <= pop;
    always @(posedge clk) wwq[278:0] <= {f_hd[270:256], f_hd[255:0], 8'hFF};   // no enable: wwq[279] qualifies

    // ---- control
    reg [10:0] npush, nexp_l;                // outputs pushed / expected this run (HC_POST 4 NM, PRE (nr + 1) NM)
    reg [10:0] npop;
    always @(posedge clk or negedge rl) begin
        if (!rl) begin
            run <= 1'b0; g_ok <= 1'b0; r_ok <= 1'b0; scp <= 1'b0; scx <= '0; cr <= QB'(LQ); im <= '0; it <= '0; ph_b <= 1'b0;
            pf <= 1'b0; rgp <= '0; cgp <= '0; cg <= '0;
            gs <= '0; gp <= '0; occ <= '0; rm <= '0; rt <= '0; rph_b <= 1'b0; sw <= 1'b0; kk <= '0; mx_v <= 1'b0;
            sc_run <= 1'b0; sm <= '0; om <= '0; ym <= '0; xm <= '0; cm <= '0; ok <= '0; wcr <= QB'(LQ);
            npush <= '0; nexp_l <= '0; npop <= '0;
            rd_all <= 1'b0; irow <= '0; rrow <= '0; xr <= '0; sr <= '0; yr <= '0; a_r <= '0; o_r <= '0; g_in <= 1'b0; rok <= '0;
            up_v <= 1'b0; up_t <= 1'b0; wdone <= 1'b0; fin <= 1'b0; flt <= 1'b0;
        end else begin
            up_v <= 1'b0; wdone <= wwq_done_q; mx_v <= 1'b0;
            if (c_job) begin
                run <= 1'b0; g_ok <= 1'b0; r_ok <= 1'b0; im <= '0; it <= '0; ph_b <= 1'b0; gs <= '0; gp <= '0;
                rm <= '0; rt <= '0; rph_b <= 1'b0; sw <= 1'b0; kk <= '0; sc_run <= 1'b0; sm <= '0;
                om <= '0; ym <= '0; xm <= '0; cm <= '0; ok <= '0; npush <= '0; npop <= '0; fin <= 1'b0; flt <= 1'b0;
                nexp_l <= dd_q[45] ? 11'(4 * NM) : 11'(NM) * (11'(dd_q[49:47]) + 11'd1);
                rd_all <= 1'b0; irow <= '0; rrow <= '0; xr <= '0; sr <= '0; yr <= '0; a_r <= dd_q[14:0]; o_r <= dd_q[44:30];
                g_in <= 1'b0; rok <= '0;
                pf <= dd_q[45]; rgp <= '0; cgp <= '0; cg <= '0;
            end
            if (c_go) run <= 1'b1;
            if (c_grdy) g_ok <= 1'b1;
            if (scr_mine) begin scp <= 1'b1; scx <= dx_q; end
            // credits
            if (iss && !wrq_cr_q) cr <= cr - 1'b1; else if (!iss && wrq_cr_q) cr <= cr + 1'b1;
            if (pop && !wwq_cr_q) wcr <= wcr - 1'b1; else if (!pop && wwq_cr_q) wcr <= wcr + 1'b1;
            if (push && !pop) occ <= occ + 1'b1; else if (!push && pop) occ <= occ - 1'b1;
            // issue counters
            if (iss && !scr_mine) begin
                if (post) begin
                    if (it == 3'd0) gs <= gs + 1'b1;
                    if (it == 3'd4) begin it <= '0; im <= im + 1'b1; end else it <= it + 1'b1;
                end else if (!ph_b) begin
                    if (it == 3'd3) begin
                        it <= '0;
                        if (im == MB'(NM - 1)) begin
                            im <= '0;
                            if (irow == 3'd0) ph_b <= 1'b1;                       // row 0: the gain next
                            else if (irow == {1'b0, nr}) rd_all <= 1'b1;
                            else begin irow <= irow + 4'd1; a_r <= a_r + 15'(4 * SD); end
                        end else im <= im + 1'b1;
                    end else it <= it + 1'b1;
                end else begin
                    if (im == NG - MB'(1)) begin                              // the gain issued: rows 1..nr, or done
                        if (nr == 3'd0) rd_all <= 1'b1;
                        else begin ph_b <= 1'b0; im <= '0; irow <= 4'd1; a_r <= a_r + 15'(4 * SD); end
                    end else im <= im + 1'b1;
                end
            end
            // responses
            if (srsp) begin
                scp <= 1'b0; up_v <= 1'b1; up_t <= 1'b0;
            end else if (rsp) begin
                if (rph_b) begin
                    if (rm == NG - MB'(1)) begin g_in <= 1'b1; rm <= '0; rph_b <= 1'b0; rrow <= 3'd1; end
                    else rm <= rm + 1'b1;
                end
                else if (post) begin
                    if (rt == 3'd4) begin rt <= '0; rm <= rm + 1'b1; end else rt <= rt + 1'b1;
                end else begin
                    if (rt == 3'd3) begin
                        rt <= '0;
                        if (rm == MB'(NM - 1)) begin
                            rm <= '0;
                            if (rrow == 3'd0) rph_b <= 1'b1; else rrow <= rrow + 3'd1;
                        end else rm <= rm + 1'b1;
                    end else rt <= rt + 1'b1;
                end
            end
            if (rsp && post && rt == 3'd4) rgp <= (rgp == RGB'(RG - 1)) ? '0 : rgp + 1'b1;
            if (cs_go) begin
                sw <= 1'b1; kk <= '0; cg <= cg + 1'b1; cgp <= (cgp == RGB'(RG - 1)) ? '0 : cgp + 1'b1;
            end
            else if (sw) begin if (kk == 2'd3) sw <= 1'b0; kk <= kk + 2'd1; end
            if (last_h) mx_v <= 1'b1;
            // PRE: x into its buffer, the chunk sum up
            if (x_v) begin if (xm == MB'(NM - 1)) begin xm <= '0; xr <= xr + 4'd1; end else xm <= xm + 1'b1; end
            if (cs_v) begin up_v <= 1'b1; up_t <= 1'b1; cm <= (cm == MB'(NM - 1)) ? '0 : cm + 1'b1; end
            // PRE phase C: the scale starts when r has landed and every gain sector is in
            if (c_rstd) begin r_ok <= 1'b1; rok[dx_q[2:0]] <= 1'b1; end
            // the scale of row sr: its r landed, every gain sector in, its x written; one bubble between rows (rh)
            if (!post && run && rok[sr[2:0]] && g_in && xr > sr && !sc_run && !xo_v && sr <= {1'b0, nr}) begin
                sc_run <= 1'b1; rh <= rha[sr[2:0]];
            end
            if (sc_run) begin
                if (sm == MB'(NM - 1)) begin sc_run <= 1'b0; sm <= '0; sr <= sr + 4'd1; end else sm <= sm + 1'b1;
            end
            // outputs
            if (hv[0]) begin if (ok == 2'd3) begin om <= om + 1'b1; gp <= gp + 1'b1; end ok <= ok + 2'd1; end
            if (y_v) begin
                if (ym == MB'(NM - 1)) begin ym <= '0; yr <= yr + 3'd1; o_r <= o_r + 15'(SD); end else ym <= ym + 1'b1;
            end
            if (push) npush <= npush + 1'b1;
            if (pop) npop <= npop + 1'b1;
            if (run && npush == nexp_l && npop == nexp_l && !f_hv && cr == QB'(LQ) && (MUT == 4 || wcr == QB'(LQ))) fin <= 1'b1;
            if ((|hf) || (|mf) || (|sf) || (|cf) || (|f1) || (|f2) || ovf) flt <= 1'b1;
        end
    end
    wire [KB-1:0] xw_sl = KB'(xr);            // x slot of the row being written
    always @(posedge clk) if (x_v) xb[32'(xw_sl) * NM + 32'(xm)] <= xl; else if (rsp && post && rs_w < 8'(NM)) xb[rs_w] <= rd_q;
    // up data: a scalar sector (rd_q) or a chunk sum in the low word; 32-bit select, no enable on the 224 upper bits
    always @(posedge clk) begin
        up_d[255:32] <= rd_q[255:32];
        up_d[31:0]   <= cs_v ? acc[7] : rd_q[31:0];
        up_x         <= cs_v ? c_i : {2'd0, scx};
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_hc_lane_sl: one element slice of ot_hgi_hc_lane_ll (HSL = 1), the hardened sub-element (own clock tree, ~12k
// flops; the flat lane was one 114k-flop clock root).  Every input is pin-flopped, every output registered: the slice's
// outputs are the flat lane's element e signals 2 cycles later.  Element e: HC_POST pipeline (ot_dsrom_su_hcpost_lane),
// PRE mix + square (x_v = its own valid line), phase C scale (x * r, then w * (x r)).
// ---------------------------------------------------------------------------------------------------------------------
`ifndef OT_HC_LANE_SL_HARD
module ot_hgi_hc_lane_sl #(
    parameter integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_sw,
    input  wire [159:0]  i_op,               // {r3, r2, r1, r0, y} = op[4..0] of element e
    input  wire [159:0]  i_cf,               // {p, c3, c2, c1, c0} of row kk
    input  wire          i_mx,
    input  wire [127:0]  i_pre,
    input  wire          i_xov,
    input  wire [31:0]   i_xo,
    input  wire [31:0]   i_rh,
    input  wire          i_wov,
    input  wire [31:0]   i_wo,
    output reg           o_hv,
    output reg  [31:0]   o_ho,
    output reg           o_hf,
    output reg  [31:0]   o_xl,
    output reg           o_mf,
    output reg  [31:0]   o_sq,
    output reg           o_sf,
    output reg  [31:0]   o_qq,
    output reg           o_f1,
    output reg           o_f2
);
    wire [0:0] rr; wire rp = rr[0];
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    // pin flops (valids reset, data not)
    reg sw, mx, xov, wov; reg [159:0] op, cf; reg [127:0] pre; reg [31:0] xo, rh, wo;
    always @(posedge clk or negedge rp)
        if (!rp) begin sw <= 1'b0; mx <= 1'b0; xov <= 1'b0; wov <= 1'b0; end
        else begin sw <= i_sw; mx <= i_mx; xov <= i_xov; wov <= i_wov; end
    always @(posedge clk) begin op <= i_op; cf <= i_cf; pre <= i_pre; xo <= i_xo; rh <= i_rh; wo <= i_wo; end
    wire hv; wire [31:0] ho, xl, sq, pp, qq; wire hf, mf, sf, f1, f2;
    ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u_h (.clk(clk), .rst_n(rp), .v(sw),
        .r0(op[63:32]), .r1(op[95:64]), .r2(op[127:96]), .r3(op[159:128]), .y(op[31:0]),
        .c0(cf[31:0]), .c1(cf[63:32]), .c2(cf[95:64]), .c3(cf[127:96]), .p(cf[159:128]),
        .vo(hv), .o(ho), .fault(hf));
    localparam integer DM = LM + 3 * LA + 1;
    wire [DM:0] vm;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rp), .v(mx), .vd(vm));
    ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rp), .v(mx), .h0(op[31:0]), .h1(op[63:32]),
        .h2(op[95:64]), .h3(op[127:96]), .pre(pre), .x(xl), .fault(mf));
    ot_hdc_qmul_lat #(LM) u_sq (clk, rp, vm[DM], xl, xl, sq, sf);
    ot_hdc_qmul_lat #(LMS) u_xr (clk, rp, xov, xo, rh, pp, f1);
    ot_hdc_qmul_lat #(LMS) u_w  (clk, rp, wov, wo, pp, qq, f2);
    // registered outputs
    always @(posedge clk or negedge rp)
        if (!rp) begin o_hv <= 1'b0; o_hf <= 1'b0; o_mf <= 1'b0; o_sf <= 1'b0; o_f1 <= 1'b0; o_f2 <= 1'b0; end
        else begin o_hv <= hv; o_hf <= hf; o_mf <= mf; o_sf <= sf; o_f1 <= f1; o_f2 <= f2; end
    always @(posedge clk) begin o_ho <= ho; o_xl <= xl; o_sq <= sq; o_qq <= qq; end
endmodule
`endif

// ---------------------------------------------------------------------------------------------------------------------
// the top: job decode, scalar fetch, relayed command broadcast / lane status, the csum tree, the scalar tail
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_ctl_ll #(
    parameter integer D   = 5120,
    parameter integer LQ  = 32,
    parameter integer FD  = 64,
    parameter integer RL  = 10,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              job_v_i,
    output wire              job_rdy,
    input  wire [148:0]      job_i,
    input  wire              g_rdy_i,
    output reg               done,
    output reg               fault,
    output wire              idle,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer SD = D / 8, NM = D / 256, NB = NM;          // NB: 32-chunk blocks (one sector of every lane)
    localparam integer NBP = (NB <= 1) ? 1 : (1 << $clog2(NB));
    localparam integer LM = 5, LA = 6;
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D), DF = D >> DK;
    generate if (D % 256 != 0 || NM > 63 || RL < 1) begin : g_bad
        ot_hgi_hc_eng_ll_D_must_be_a_multiple_of_256_RL_ge_1 u_trap ();
    end endgenerate

    // ---- pin flops
    reg job_v, g_rdy; reg [148:0] job; reg rg_q, wg_q;
    localparam [2:0] S_IDLE = 0, S_GRP = 1, S_SC = 2, S_SCW = 3, S_WG = 4, S_RUN = 5, S_FIN = 6;
    reg [2:0] st;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin job_v <= 1'b0; g_rdy <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; end
        else begin job_v <= job_v_i && (st == S_IDLE) && !job_v; g_rdy <= g_rdy_i; rg_q <= rg_gnt && rg_req;
                   wg_q <= wg_gnt && wg_req; end
    always @(posedge clk) job <= job_i;
    assign job_rdy = (st == S_IDLE);
    assign idle = (st == S_IDLE);
    wire j_post = (job[148:147] == 2'd1);
    wire [14:0] ja = job[17:3], jb = job[35:21], jo = job[93:79];
    // H-MTP2 P-row HC_PRE_NORM: job[39:37] = rows - 1 (B base bits above the scratch gain, else zero); rows at the
    // contiguous strides (h 4 D, y D, pre one sector a row: C sector-aligned)
    wire [2:0] jr = job[39:37];
    wire job_ok = (job[114:94] == 21'(D)) && (job[2:0] == 3'd0) && (job[20:18] == 3'd0) && (job[78:76] == 3'd0) &&
                  (ja[4:0] == jb[4:0]) && (ja[4:0] == jo[4:0]) && !(job[148:147] == 2'd0 && job[36] && (NM % 2 != 0))   /* packed gain: lane-local GPK layout, NM even */ &&
                  (job[148:147] <= 2'd1) && (jr == 3'd0 || (job[148:147] == 2'd0 && job[60:58] == 3'd0));

    // ---- command bus (the top's registers -> RL relay flops per lane)
    reg cv; reg [2:0] cop; reg [7:0] cx; reg [127:0] cd;
    // ---- lane status (RL relay flops per lane -> here)
    wire [31:0] l_upv, l_upt, l_wd, l_fin, l_flt; wire [32*10-1:0] l_upx; wire [32*256-1:0] l_upd;
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_ln
        wire dv; wire [138:0] dd;
        ot_hgi_hc_rly #(.W(139), .N(RL)) u_dn (.clk(clk), .rst_n(rst_n), .v(cv), .d({cop, cx, cd}), .vq(dv), .q(dd));
        wire uv, ut, wd, fn, fl; wire [9:0] ux; wire [255:0] ud;
        ot_hgi_hc_lane_ll #(.D(D), .LQ(LQ), .FD(FD), .MUT(MUT == 2 || MUT == 4 || MUT == 5 || MUT == 6 ? MUT : 0)) u_l (.clk(clk), .rst_n(rst_n),
            .lid(5'(gl)), .wrq(wrq[gl*16 +: 16]), .wrq_cr(wrq_cr[gl]), .wrr(wrr[gl*257 +: 257]), .wwq(wwq[gl*280 +: 280]),
            .wwq_cr(wwq_cr[gl]), .wwq_done(wwq_done[gl]), .dn_v(dv), .dn_op(dd[138:136]), .dn_x(dd[135:128]),
            .dn_d(dd[127:0]), .up_v(uv), .up_t(ut), .up_x(ux), .up_d(ud), .wdone(wd), .fin(fn), .flt(fl));
        wire [3:0] sq;                         // the status pulses / levels: one relay chain (valid-less, reset)
        ot_hdc_delay #(.W(4), .D(RL), .RESET(1)) u_st (.clk(clk), .rst_n(rst_n), .d({wd, fn, fl, 1'b0}), .q(sq));
        wire uq; wire [266:0] uqd;
        ot_hgi_hc_rly #(.W(267), .N(RL)) u_up (.clk(clk), .rst_n(rst_n), .v(uv), .d({ut, ux, ud}), .vq(uq), .q(uqd));
        assign l_upv[gl] = uq; assign l_upt[gl] = uqd[266]; assign l_upx[gl*10 +: 10] = uqd[265:256];
        assign l_upd[gl*256 +: 256] = uqd[255:0];
        assign l_wd[gl] = sq[3]; assign l_fin[gl] = sq[2]; assign l_flt[gl] = sq[1];
    end endgenerate

    // ---- scalars
    reg [3:0] nsc, scs, scl; reg [255:0] scb [0:7]; reg [17:0] c_b; reg [2:0] nrt, hr, rsent;
    wire [1023:0] scw = {scb[3], scb[2], scb[1], scb[0]};
    wire [639:0] scx = scw[{c_b[2:0], 5'd0} +: 640];
    integer w;
    always @(posedge clk)
        for (w = 0; w < 32; w = w + 1) if (l_upv[w] && !l_upt[w]) scb[l_upx[w*10 +: 3]] <= l_upd[w*256 +: 256];

    // ---- done count (pipelined popcount of the relayed done pulses)
    reg [3:0] pc1 [0:3]; reg [5:0] pc2; reg [12:0] ndone, nexp;
    integer q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin for (q = 0; q < 4; q = q + 1) pc1[q] <= '0; pc2 <= '0; end
        else begin
            for (q = 0; q < 4; q = q + 1) begin : g_pc
                integer b; reg [3:0] s; s = '0;
                for (b = 0; b < 8; b = b + 1) s = s + 4'(l_wd[8*q + b]);
                pc1[q] <= s;
            end
            pc2 <= 6'(pc1[0]) + 6'(pc1[1]) + 6'(pc1[2]) + 6'(pc1[3]);
        end
    reg fin_all, flt_any;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fin_all <= 1'b0; flt_any <= 1'b0; end
        else begin fin_all <= &l_fin; flt_any <= |l_flt; end

    // ---- the csum tree: per-lane chunk FIFOs (in each lane's sector order), a block = one entry of every lane
    reg [4:0] ph;                            // the operands' bank phase: chunk u + 32 m is lane (u + ph) mod 32
    reg [31:0] cfq [0:31][0:31]; reg [5:0] cwp [0:31]; reg [5:0] crp;   // all lanes pop together
    integer L;
    always @(posedge clk)
        for (L = 0; L < 32; L = L + 1) if (l_upv[L] && l_upt[L]) cfq[L][cwp[L][4:0]] <= l_upd[L*256 +: 32];
    reg blk_rdy;
    always @* begin
        blk_rdy = 1'b1;
        for (L = 0; L < 32; L = L + 1) if (cwp[L] == crp) blk_rdy = 1'b0;
    end
    reg go_r;                                // a new row (clears the heap)
    reg b0_v; reg [1023:0] b0; reg [5:0] b0_i; reg [5:0] bi;
    always @(posedge clk) begin
        if (blk_rdy && st == S_RUN && bi < 6'(NB)) for (L = 0; L < 32; L = L + 1) b0[32*L +: 32] <= cfq[5'(L + ph)][crp[4:0]];
        if (blk_rdy && st == S_RUN && bi < 6'(NB)) b0_i <= bi;
    end
    // block tree: 5 pairwise levels in the golden order (left = even chunk)
    wire [31:0] tv [0:5][0:31]; wire [5:0] tf;
    localparam integer DTB = 5 * LA;
    wire [DTB:0] tvl;
    ot_hdc_vline #(.D(DTB)) u_tvl (.clk(clk), .rst_n(rst_n), .v(b0_v), .vd(tvl));
    wire [5:0] tbi;
    ot_hdc_delay #(.W(6), .D(DTB)) u_tbi (.clk(clk), .rst_n(rst_n), .d(b0_i), .q(tbi));
    genvar c, kt, n;
    generate
        for (c = 0; c < 32; c = c + 1) begin : g_t0 assign tv[0][c] = b0[32*c +: 32]; end
        assign tf[0] = 1'b0;
        for (kt = 1; kt <= 5; kt = kt + 1) begin : g_tl
            wire [(32 >> kt)-1:0] f;
            for (c = 0; c < (32 >> kt); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, tvl[LA * (kt - 1)], tv[kt - 1][2 * c], tv[kt - 1][2 * c + 1],
                                               tv[kt][c], f[c]);
            end
            for (c = (32 >> kt); c < 32; c = c + 1) begin : g_tz assign tv[kt][c] = 32'd0; end
            assign tf[kt] = |f;
        end
    endgenerate
    wire vsum_v = tvl[DTB]; wire [31:0] vsum = tv[5][0];
    // block heap (ot_dsrom_su_norm's vector levels): leaves NBP + b, padding right subtrees pass their left value
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    wire [31:0] nv [1:2*NBP-1]; wire nd [1:2*NBP-1]; wire np [1:2*NBP-1]; wire [NBP:0] nf;
    assign nf[0] = 1'b0; assign nf[NBP] = 1'b0;
    generate
        for (n = NBP; n < 2 * NBP; n = n + 1) begin : g_leaf
            reg [31:0] val; reg vld;
            wire hit = vsum_v && tbi == 6'(n - NBP);
            always @(posedge clk or negedge rst_n)
                if (!rst_n) vld <= 1'b0; else if (go_r) vld <= 1'b0; else if (hit) vld <= 1'b1;
            always @(posedge clk) if (hit) val <= vsum;
            assign np[n] = hit; assign nd[n] = vld || hit; assign nv[n] = vld ? val : vsum;
        end
        for (n = 1; n < NBP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NBP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NBP) < NB) begin : g_add
                reg stt, vld; reg [31:0] val; wire [LAV:0] av; wire [31:0] s;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !stt && !go_r;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rst_n), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rst_n, fire, nv[2 * n], nv[2 * n + 1], s, nf[n]);
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin stt <= 1'b0; vld <= 1'b0; end
                    else if (go_r) begin stt <= 1'b0; vld <= 1'b0; end
                    else begin if (fire) stt <= 1'b1; if (av[LAV]) vld <= 1'b1; end
                always @(posedge clk) if (av[LAV]) val <= s;
                assign np[n] = av[LAV]; assign nd[n] = vld || av[LAV]; assign nv[n] = vld ? val : s;
            end else begin : g_pass
                assign nv[n] = nv[2 * n]; assign nd[n] = nd[2 * n]; assign np[n] = np[2 * n]; assign nf[n] = 1'b0;
            end
        end
    endgenerate
    wire ss_v = np[1] && !go_r; wire [31:0] ss = nv[1];
    // scalar tail: / D, + eps, rsqrt
    reg [31:0] eps_r;
    reg ssv_q; reg [31:0] ss_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) ssv_q <= 1'b0; else ssv_q <= ss_v;
    always @(posedge clk) ss_q <= ss;
    wire [31:0] mq, me, rr; wire mq_v, rr_v, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssv_q), .x(ss_q), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps_r, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(ve[LA]), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    reg r_pend; reg [31:0] r_hold;

    // ---- sequencer
    reg post; reg gsent, gpend; reg [2:0] wb; reg sfault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; cv <= 1'b0; cop <= '0; cx <= '0;
            cd <= '0; nsc <= '0; scs <= '0; scl <= '0; c_b <= '0; ndone <= '0; nexp <= '0; ph <= '0; crp <= '0; bi <= '0;
            b0_v <= 1'b0; go_r <= 1'b0; eps_r <= '0; r_pend <= 1'b0; r_hold <= '0; post <= 1'b0; gsent <= 1'b0;
            gpend <= 1'b0; wb <= '0; sfault <= 1'b0;
            for (L = 0; L < 32; L = L + 1) cwp[L] <= '0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cv <= 1'b0; b0_v <= 1'b0; go_r <= 1'b0;
            ndone <= ndone + 13'(pc2);
            for (L = 0; L < 32; L = L + 1) if (l_upv[L] && l_upt[L]) cwp[L] <= cwp[L] + 1'b1;
            begin : b_scl
                reg [3:0] ns; ns = '0;
                for (L = 0; L < 32; L = L + 1) if (l_upv[L] && !l_upt[L]) ns = ns + 4'd1;
                scl <= scl + ns;
            end
            if (blk_rdy && st == S_RUN && bi < 6'(NB)) begin crp <= crp + 1'b1; bi <= bi + 1'b1; b0_v <= 1'b1; end
            // H-MTP2: a P-row job's next row enters the tree only after this row's sum left the heap (heap reset)
            if (ss_v && hr != nrt) begin hr <= hr + 3'd1; bi <= '0; go_r <= 1'b1; end
            if (g_rdy && st != S_IDLE) gpend <= 1'b1;
            // el1011-hbm-fused: HC_PRE_NORM takes the lane WRITE group only once the gain has landed (g_rdy): on the die
            // the FUSED mover streams that gain through the lgE write group, so an engine holding it from the job start
            // would wait on a move that waits on it.  No PRE lane writes before the gain command (y needs w); r follows g.
            if (!post && gpend && st == S_RUN) wg_req <= 1'b1;
            if (rr_v) begin r_pend <= 1'b1; r_hold <= rr; end
            if (rr_v && r_pend) sfault <= 1'b1;                    // a row's r overtook the previous one's send
            for (L = 0; L < 32; L = L + 1) if (l_upv[L] && l_upt[L] && (cwp[L] - crp) == 6'd32) sfault <= 1'b1;   // chunk FIFO full
            if (f_div || f_eps || f_rsq || (|tf) || (|nf)) sfault <= 1'b1;
            case (st)
                S_IDLE: if (job_v) begin
                    if (!job_ok) fault <= 1'b1;
                    else begin
                        st <= S_GRP; rg_req <= 1'b1; wg_req <= j_post; post <= j_post; c_b <= job[75:58];
                        eps_r <= job[146:115]; ph <= ja[4:0]; nexp <= j_post ? 13'(4 * SD) : 13'(SD) * (13'(jr) + 13'd1);
                        nrt <= j_post ? 3'd0 : jr; hr <= '0; rsent <= '0;
                        gsent <= 1'b0; gpend <= 1'b0; r_pend <= 1'b0; sfault <= 1'b0; go_r <= 1'b1;
                    end
                end
                S_GRP: if (rg_q && (wg_q || !post)) begin
                    st <= S_SC; scs <= '0; scl <= '0; ndone <= '0; crp <= '0; bi <= '0;
                    for (L = 0; L < 32; L = L + 1) cwp[L] <= '0;
                    nsc <= (nrt != 3'd0) ? 4'(nrt) + 4'd1 : 4'(({3'd0, c_b[2:0]} + (post ? 6'd20 : 6'd4) + 6'd7) >> 3);
                    cv <= 1'b1; cop <= 3'd0; cx <= '0; cd <= {78'd0, nrt, job[36] && !post, post, jo, jb, ja};       // JOB
                end
                S_SC: begin                                                    // one scalar read a cycle
                    cv <= 1'b1; cop <= 3'd2; cx <= 8'(scs); cd <= {113'd0, c_b[17:3] + 15'(scs)};
                    if (scs + 4'd1 == nsc) st <= S_SCW;
                    scs <= scs + 4'd1;
                end
                S_SCW: if (scl == nsc) begin st <= S_WG; wb <= '0; end
                S_WG: begin
                    cv <= 1'b1; cop <= 3'd1; cx <= 8'(wb); cd <= (nrt != 3'd0) ? scb[wb][127:0] : scx[128*wb +: 128];
                    if (wb == (post ? 3'd4 : nrt)) st <= S_RUN; else wb <= wb + 3'd1;
                end
                S_RUN: begin
                    if (!cv && cop == 3'd1) begin cv <= 1'b1; cop <= 3'd3; end                   // GO after the weights
                    else if (!post && gpend && !gsent && wg_q && cop != 3'd1) begin cv <= 1'b1; cop <= 3'd4; gsent <= 1'b1; end
                    else if (!post && r_pend && gsent && cop != 3'd1) begin
                        cv <= 1'b1; cop <= 3'd5; cx <= 8'(rsent); cd <= {96'd0, r_hold}; r_pend <= 1'b0; rsent <= rsent + 3'd1;
                    end
                    if (ndone == nexp && fin_all && cop != 3'd1) st <= S_FIN;
                    // MUT 4 (must FAIL): retire as soon as the last command (GO / r) leaves the top, before any output
                    // write has landed (the relay latency hides a lane-side-only mutant, so it is cut at the top)
                    if (MUT == 4 && cv && (post ? cop == 3'd3 : (cop == 3'd5 && rsent == nrt + 3'd1))) st <= S_FIN;
                end
                S_FIN: begin
                    rg_req <= 1'b0; wg_req <= 1'b0; st <= S_IDLE;
                    if (sfault || flt_any) fault <= 1'b1; else done <= 1'b1;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule

// the LL engine (ot_hgi_hc_eng LL = 1)
module ot_hgi_hc_eng_ll #(
    parameter integer D   = 5120,
    parameter integer LQ  = 32,
    parameter integer FD  = 64,
    parameter integer RL  = 10,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              job_v,
    output wire              job_rdy,
    input  wire [148:0]      job,
    input  wire              g_rdy,
    output wire              done,
    output wire              fault,
    output wire              idle,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    ot_hgi_hc_ctl_ll #(.D(D), .LQ(LQ), .FD(FD), .RL(RL), .MUT(MUT)) u_ctl (.clk(clk), .rst_n(rst_n), .job_v_i(job_v),
        .job_rdy(job_rdy), .job_i(job), .g_rdy_i(g_rdy), .done(done), .fault(fault), .idle(idle), .wrq(wrq),
        .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .rg_req(rg_req), .rg_gnt(rg_gnt),
        .wg_req(wg_req), .wg_gnt(wg_gnt));
endmodule
`default_nettype wire
