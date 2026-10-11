`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 hyper-connection engine (hgi-unitrate / hgi-1010 b, 2026-10-10): FUSED HC_POST and HC_PRE_NORM as ONE pass over
// the wide VM lanes, replacing the record's micro-op lowering (HC_POST: 8 dependent whole-array SU records that read
// the residual 4 times and round-trip each mix through VM scratch; HC_PRE_NORM: mix -> x scratch -> sum of squares ->
// rsqrt -> scale, 4 dependent stage / compute / drain records).  Root cause of the 20.1x / 6.5x unit ratios
// (tput-gate 73bdd2cad): the data movement of the lowering alone exceeds the budget at any SU width.
//
// Arithmetic: the existing exact fused pipelines, unchanged:
//   HC_POST      ot_dsrom_su_hcpost (NG = 64 element groups, 256 outputs a beat):
//                out[k][e] = BF16(y[e]*post[k] + (((r0[e]*c[0][k] + r1[e]*c[1][k]) + r2[e]*c[2][k]) + r3[e]*c[3][k]))
//                = hdc_golden_v41 Model.hc_post.
//   HC_PRE_NORM  ot_dsrom_su_norm (N = 64, HC = 1, MEM = 1): x = bf16(seqsum_j pre[j] h[j]); ss = csum(x x) (chunk8);
//                r = rsqrt(ss / D + eps); y = bf16(w (x r)) = Model.hc_pre + rmsnorm_bf16 under R-ARITH chunk8.
//
// Job (the record's ne_job, 149 b): {op 2 (1 HC_POST, 0 HC_PRE_NORM), eps 32, n 21, O 18, C 18, B 40, A 18} (VM word
// bases).  HC_POST: A = y [D], B = res [4][D], C = post[4] | comb[4][4] (comb[j][k] at C + 4 + 4j + k), O = out [4][D].
// HC_PRE_NORM: A = h [4][D], B = the FP32 gain in VM [D] (the record's mover put it there), C = pre[4], O = y [D].
// Refused (fault, no lane activity): n != D, A / B / O not sector aligned.
//
// Lanes (ot_hgi_su_ctlw's wide-lane protocol): read lane b {v, sector 15} -> bank b, LQ credits, sectors back in order;
// write lane b {v, sector 15, data 256, mask 8}, LQ credits, a done a landed write.  Both groups are held (rg / wg
// burst ownership) from the job to its retire.
// Schedule (D a multiple of 256 words, so the 4 rows of an operand sit at the same bank phase):
//   SC  the 1-3 scalar sectors of C (one event).
//   P1  the single-row vector (HC_POST y, HC_PRE_NORM gain): D/8 sectors, event e lane L reads row offset 32e + (L - a0)
//       mod 32: every lane every event; into a lane-local buffer, row e.
//   P2  the 4-row operand (res / h) beat b = 64 words (8 sectors) of each row j: event e reads row j of beat e - j, so the
//       4 rows of 4 consecutive beats occupy 4 disjoint 8-lane sets: every lane every event.  A lane's responses are
//       complete quads (j = 0..3 of one beat), collected into a lane quad FIFO (QD deep, reserved at the j = 0 issue).
//   A beat is assembled when its 8 lanes hold a quad (and P1 landed); the engine takes it with the P1 row (y / gain).
//   HC_POST output: output event o writes row k of beat o - k (k = 0..3, a 3-beat skew line): again 4 disjoint 8-lane
//   sets, one sector a lane an event, into a lane write FIFO (ot_fifo_sram_fwft, FD deep).  Input beats are admitted
//   only while every lane FIFO has room for everything in flight (no back pressure into the fixed-latency pipeline).
//   HC_PRE_NORM output: y vector i (8 sectors, one a lane) into the same FIFOs; FD >= D / 256 + 1 holds a whole row,
//   so the pipeline's burst never needs back pressure.
// MUT (bench negatives, must FAIL): 1 no output skew (the 4 rows of a beat collide: rows 1..3 lost), 2 P2 quad rows
//   j and j+1 swapped on lane 0, 3 the gain vector of beat b is beat b+1's (PRE) / y of the next beat (POST),
//   4 retire before the last write lands.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_eng #(
    parameter integer D   = 5120,        // the row length (a multiple of 256)
    parameter integer LQ  = 32,          // credits a wide lane holds
    parameter integer QD  = 4,           // lane quad FIFO depth
    parameter integer FD  = 64,          // lane write FIFO depth (power of two <= 64)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              job_v,
    output wire              job_rdy,
    input  wire [148:0]      job,
    output reg               done,
    output reg               fault,
    output wire              idle,
    output reg  [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output reg  [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer NB = D / 64;          // beats
    localparam integer NR = D / 256;         // P1 rows a lane
    localparam integer SD = D / 8;           // sectors a row
    localparam integer QB = $clog2(LQ + 1);
    localparam integer RB = (NR <= 1) ? 1 : $clog2(NR);
    localparam integer FB = $clog2(FD + 1);
    generate if (D % 256 != 0 || NB > 255 || FD < NR + 1 || FD > 64 || (FD & (FD - 1)) != 0) begin : g_bad
        initial $fatal(1, "ot_hgi_hc_eng: D must be a multiple of 256 (<= 16,320), FD a power of two in [D/256+1, 64]");
    end endgenerate
    function automatic [31:0] f32i(input integer x);     // binary32 of a positive integer < 2^24 (exact)
        integer e; reg [31:0] r;
        begin
            e = 0; while ((x >> (e + 1)) != 0) e = e + 1;
            r = {1'b0, 8'(127 + e), 23'((x << (23 - e)) & 32'h7FFFFF)};
            f32i = r;
        end
    endfunction
    localparam [31:0] NF = f32i(D);

    // ---- registered lane inputs
    reg [31:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [32*257-1:0] wrr_q; reg rg_q, wg_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; rg_q <= 1'b0; wg_q <= 1'b0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr;
                   rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req; end

    // ---- job
    localparam [2:0] S_IDLE = 0, S_GRP = 1, S_SC = 2, S_SCW = 3, S_RUN = 4, S_FIN = 5;
    reg [2:0] st;
    reg       post;                          // 1 HC_POST, 0 HC_PRE_NORM
    reg [31:0] eps_r;
    reg [17:0] a_b, b_b, c_b, o_b;
    wire [17:0] p1_b = post ? a_b : b_b;     // the single-row vector
    wire [17:0] p2_b = post ? b_b : a_b;     // the 4-row operand
    wire [14:0] p1_s = p1_b[17:3], p2_s = p2_b[17:3], o_s = o_b[17:3];
    wire [4:0]  v0 = p1_s[4:0], s0 = p2_s[4:0], o0 = o_s[4:0];
    assign job_rdy = (st == S_IDLE);
    wire job_ok = (job[114:94] == 21'(D)) && (job[2:0] == 3'd0) && (job[20:18] == 3'd0) && (job[78:76] == 3'd0);

    // ---- read side
    reg [QB-1:0] cr [0:31];
    reg [2:0]  nsc;                          // scalar sectors (1..4)
    reg [31:0] sc_pend; reg [1:0] sc_ix [0:31];
    reg [255:0] scb [0:3];
    reg [RB:0] p1e; reg [8:0] p2e;           // events issued
    reg [RB:0] p1c [0:31];                   // P1 sectors landed a lane
    reg [1:0]  qn [0:31];                    // quad collector position
    reg [767:0] qsh [0:31];
    reg [1023:0] qf [0:31][0:QD-1];
    reg [$clog2(QD)-1:0] qwp [0:31], qrp [0:31];
    reg [$clog2(QD+1)-1:0] qcnt [0:31], qres [0:31];
    reg [255:0] pb [0:31][0:NR-1];            // the P1 row, lane-local (row e of lane L = row offset 32e + (L - v0) mod 32)
    wire [1023:0] scw = {scb[3], scb[2], scb[1], scb[0]};
    wire [639:0] scx = scw[{c_b[2:0], 5'd0} +: 640];   // C words 0..19 from the scalar sectors
    reg [127:0] post_w, pre_w; reg [511:0] comb_w;

    // P2 event e: lane L reads row j = (e - g) mod 4 of beat b = e - j, g = ((L - s0) mod 32) / 8
    reg [31:0] p2v; reg [14:0] p2sec [0:31]; reg [31:0] p2j0;
    integer L;
    always @* begin
        for (L = 0; L < 32; L = L + 1) begin : g_p2
            reg [4:0] u; reg [1:0] g, j; reg [9:0] b;
            u = 5'(L) - s0; g = u[4:3]; j = 2'(p2e[1:0] - {1'b0, g[1:0]}) ; b = 10'(p2e) - {8'd0, j};
            p2v[L] = (p2e >= {7'd0, j}) && (({1'b0, p2e} - {8'd0, j}) < 10'(NB));
            p2j0[L] = (j == 2'd0);
            p2sec[L] = p2_s + 15'(j) * 15'(SD) + {b[9:0], 3'd0} + {12'd0, u[2:0]};
        end
    end
    reg ev_ok;
    always @* begin
        ev_ok = 1'b1;
        for (L = 0; L < 32; L = L + 1)
            if (p2v[L] && (cr[L] == '0 || (p2j0[L] && qres[L] >= QD))) ev_ok = 1'b0;
    end
    reg p1_all_cr;
    always @* begin p1_all_cr = 1'b1; for (L = 0; L < 32; L = L + 1) if (cr[L] == '0) p1_all_cr = 1'b0; end
    reg p1_done;
    always @* begin p1_done = 1'b1; for (L = 0; L < 32; L = L + 1) if (p1c[L] != (RB+1)'(NR)) p1_done = 1'b0; end

    // ---- beat assembly: stage A pops the 8 quads of beat ab and reads the P1 row ab / 4; stage B forms the beat
    reg [7:0] ab, bo;                        // beats into the engine / beats out of it (HC_POST)
    reg [7:0] oe;                            // output events (HC_POST, incl. the 3 flush events)
    reg [FB-1:0] occ [0:31];
    reg room;
    always @* begin
        room = 1'b1;
        for (L = 0; L < 32; L = L + 1)
            if ({1'b0, occ[L]} + 8'(ab - bo) + 8'd5 > 8'(FD)) room = 1'b0;
    end
    reg [4:0] qlane [0:7]; reg a_rdy;
    always @* begin
        a_rdy = (st == S_RUN) && p1_done && (ab < 8'(NB)) && (!post || room);
        for (L = 0; L < 8; L = L + 1) begin
            qlane[L] = s0 + {ab[1:0], 3'd0} + 5'(L);
            if (qcnt[qlane[L]] == '0) a_rdy = 1'b0;
        end
    end
    reg [31:0] popq;
    always @* begin popq = '0; if (a_rdy) for (L = 0; L < 8; L = L + 1) popq[qlane[L]] = 1'b1; end
    reg a_v; reg [7:0] a_b8; reg [1023:0] a_q [0:7]; reg [255:0] pb_rd [0:31];
    reg e_go, e_v; reg [64*4*32-1:0] e_r; reg [64*32-1:0] e_y; reg [7:0] e_i;
    // ---- engines
    wire h_ov, h_f, n_yv, n_f;
    wire [64*4*32-1:0] h_od; wire [7:0] n_yi; wire [64*32-1:0] n_y;
    ot_dsrom_su_hcpost #(.NG(64), .WIN(2), .WOUT(2), .ML(5), .AL(4)) u_post (.clk(clk), .rst_n(rst_n), .go(e_go && post),
        .comb(comb_w), .post(post_w), .in_v(e_v && post), .in_r(e_r), .in_y(e_y), .out_v(h_ov), .out_d(h_od), .fault(h_f));
    ot_dsrom_su_norm #(.N(64), .D(D), .HC(1), .RD(0), .QUANT(0), .MEM(1), .RW(2), .BW(2), .LM(5), .LA(4)) u_norm (
        .clk(clk), .rst_n(rst_n), .go(e_go && !post), .in_v(e_v && !post), .in_x(e_r), .pre(pre_w), .n_f(NF), .eps(eps_r),
        .wl_v(e_v && !post), .wl_i(e_i), .wl_d(e_y), .cos_t(32'd0), .sin_t(32'd0), .y_v(n_yv), .y_i(n_yi), .y(n_y),
        .r_v(), .r(), .q_v(), .q_i(), .q_codes(), .q_e(), .q_y(), .ro_v(), .ro(), .fault(n_f));

    // ---- output: HC_POST skew line (row k of beat o - k at output event o), HC_PRE_NORM y vectors
    reg [2047:0] d11, d21, d22, d31, d32, d33;
    reg v11, v21, v22, v31, v32, v33;         // validity along the lines
    function automatic [2047:0] hrow(input [64*4*32-1:0] od, input integer k);
        integer g; begin for (g = 0; g < 64; g = g + 1) hrow[32*g +: 32] = od[32*(4*g + k) +: 32]; end
    endfunction
    wire ev = post && (h_ov || (bo == 8'(NB) && oe < 8'(NB + 3)));
    reg [3:0] rv; reg [2047:0] rd [0:3]; reg [7:0] rbt [0:3];
    always @* begin
        rv[0] = h_ov;         rd[0] = hrow(h_od, 0); rbt[0] = oe;
        rv[1] = v11;          rd[1] = d11;           rbt[1] = oe - 8'd1;
        rv[2] = v22;          rd[2] = d22;           rbt[2] = oe - 8'd2;
        rv[3] = v33;          rd[3] = d33;           rbt[3] = oe - 8'd3;
    end
    // lane pushes
    reg [31:0] push; reg [270:0] pdat [0:31];
    integer k, t;
    always @* begin
        push = '0;
        for (L = 0; L < 32; L = L + 1) pdat[L] = '0;
        if (post && ev && MUT == 1) begin                     // MUT 1: no skew, the 4 rows of a beat collide
            if (h_ov)
                for (k = 0; k < 4; k = k + 1)
                    for (t = 0; t < 8; t = t + 1) begin : g_pm
                        reg [4:0] ln; reg [2047:0] hr; ln = o0 + {oe[1:0], 3'd0} + 5'(t); hr = hrow(h_od, k);
                        push[ln] = 1'b1;
                        pdat[ln] = {15'(o_s + 15'(k) * 15'(SD) + {oe, 3'd0} + 15'(t)), hr[256*t +: 256]};
                    end
        end else if (post && ev) begin
            for (k = 0; k < 4; k = k + 1)
                if (rv[k])
                    for (t = 0; t < 8; t = t + 1) begin : g_pp
                        reg [4:0] ln; reg [2047:0] hr; ln = o0 + {rbt[k][1:0], 3'd0} + 5'(t); hr = rd[k];
                        push[ln] = 1'b1;
                        pdat[ln] = {15'(o_s + 15'(k) * 15'(SD) + {rbt[k], 3'd0} + 15'(t)), hr[256*t +: 256]};
                    end
        end
        if (!post && n_yv)
            for (t = 0; t < 8; t = t + 1) begin : g_py
                reg [4:0] ln; ln = o0 + {n_yi[1:0], 3'd0} + 5'(t);
                push[ln] = 1'b1;
                pdat[ln] = {15'(o_s + {n_yi, 3'd0} + 15'(t)), n_y[256*t +: 256]};
            end
    end
    // lane write FIFOs + drain
    wire [31:0] f_hv, f_ovf; wire [270:0] f_hd [0:31]; reg [31:0] pop;
    reg [QB-1:0] wcr [0:31]; reg [7:0] wpend [0:31];
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_wf
        ot_fifo_sram_fwft #(.W(271), .DEPTH(FD), .MACRO(0)) u_f (.clk(clk), .rst_n(rst_n), .push(push[gl]),
            .wdata(pdat[gl]), .pop(pop[gl]), .hv(f_hv[gl]), .head(f_hd[gl]), .ovf(f_ovf[gl]));
    end endgenerate
    always @* for (L = 0; L < 32; L = L + 1) pop[L] = wg_q && f_hv[L] && (wcr[L] != '0);

    reg [12:0] nwr, nexp;                    // sectors written / expected
    reg sfault;
    reg quiet;
    always @* begin
        quiet = 1'b1;
        for (L = 0; L < 32; L = L + 1)
            if (f_hv[L] || occ[L] != '0 || wpend[L] != 8'd0 || wcr[L] != QB'(LQ) || cr[L] != QB'(LQ)) quiet = 1'b0;
    end
    assign idle = (st == S_IDLE);

    integer w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; wrq <= '0; wwq <= '0;
            post <= 1'b0; eps_r <= '0; a_b <= '0; b_b <= '0; c_b <= '0; o_b <= '0; nsc <= '0; sc_pend <= '0;
            p1e <= '0; p2e <= '0; ab <= '0; bo <= '0; oe <= '0; a_v <= 1'b0; e_go <= 1'b0; e_v <= 1'b0; e_i <= '0;
            v11 <= 1'b0; v21 <= 1'b0; v22 <= 1'b0; v31 <= 1'b0; v32 <= 1'b0; v33 <= 1'b0; nwr <= '0; nexp <= '0; sfault <= 1'b0;
            post_w <= '0; pre_w <= '0; comb_w <= '0; a_b8 <= '0;
            for (w = 0; w < 32; w = w + 1) begin
                cr[w] <= QB'(LQ); wcr[w] <= QB'(LQ); wpend[w] <= '0; p1c[w] <= '0; qn[w] <= '0; qwp[w] <= '0;
                qrp[w] <= '0; qcnt[w] <= '0; qres[w] <= '0; occ[w] <= '0; sc_ix[w] <= '0;
            end
        end else begin
            done <= 1'b0; fault <= 1'b0; e_go <= 1'b0; e_v <= 1'b0; a_v <= 1'b0;
            for (w = 0; w < 32; w = w + 1) begin wrq[w*16 + 15] <= 1'b0; wwq[w*280 + 279] <= 1'b0; end
            if (h_f || n_f || (|f_ovf)) sfault <= 1'b1;
            // ---------------- read issue
            begin : b_iss
                reg [31:0] iss, j0;
                iss = '0; j0 = '0;
                case (st)
                    S_IDLE: if (job_v) begin
                        post <= (job[148:147] == 2'd1); eps_r <= job[146:115]; o_b <= job[93:76]; c_b <= job[75:58];
                        b_b <= job[35:18]; a_b <= job[17:0];
                        if (!job_ok) fault <= 1'b1;
                        else begin
                            st <= S_GRP; rg_req <= 1'b1; wg_req <= 1'b1;
                            nexp <= (job[148:147] == 2'd1) ? 13'(4 * SD) : 13'(SD);
                        end
                    end
                    S_GRP: if (rg_q && wg_q) begin
                        st <= S_SC; nsc <= 3'(({3'd0, c_b[2:0]} + (post ? 6'd20 : 6'd4) + 6'd7) >> 3);
                    end
                    S_SC: begin
                        for (w = 0; w < 4; w = w + 1) if (w < nsc) begin : g_sc
                            reg [14:0] s; s = c_b[17:3] + 15'(w);
                            wrq[s[4:0]*16 +: 16] <= {1'b1, s}; iss[s[4:0]] = 1'b1; sc_ix[s[4:0]] <= 2'(w);
                        end
                        sc_pend <= iss; st <= S_SCW;
                    end
                    S_SCW: if (sc_pend == '0) begin
                        post_w <= scx[127:0]; pre_w <= scx[127:0]; comb_w <= scx[639:128];
                        e_go <= 1'b1; st <= S_RUN; p1e <= '0; p2e <= '0; ab <= '0; bo <= '0; oe <= '0; nwr <= '0;
                    end
                    S_RUN: begin
                        if (p1e < (RB+1)'(NR)) begin
                            if (p1_all_cr) begin
                                for (w = 0; w < 32; w = w + 1) begin : g_p1
                                    reg [4:0] u; u = 5'(w) - v0;
                                    wrq[w*16 +: 16] <= {1'b1, 15'(p1_s + {p1e, 5'd0} + {10'd0, u})};
                                end
                                iss = '1; p1e <= p1e + 1'b1;
                            end
                        end else if (p2e < 9'(NB + 3) && ev_ok) begin
                            for (w = 0; w < 32; w = w + 1) if (p2v[w]) begin
                                wrq[w*16 +: 16] <= {1'b1, p2sec[w]}; iss[w] = 1'b1; j0[w] = p2j0[w];
                            end
                            p2e <= p2e + 1'b1;
                        end
                        if (p2e == 9'(NB + 3) && ab == 8'(NB) && nwr == nexp && quiet && !a_v && !e_v) st <= S_FIN;
                    end
                    S_FIN: begin
                        rg_req <= 1'b0; wg_req <= 1'b0; st <= S_IDLE;
                        if (sfault) fault <= 1'b1; else done <= 1'b1;
                        sfault <= 1'b0;
                    end
                    default: st <= S_IDLE;
                endcase
                for (w = 0; w < 32; w = w + 1) begin
                    cr[w] <= cr[w] - QB'(iss[w]) + QB'(wrq_cr_q[w]);
                    qres[w] <= qres[w] + j0[w] - popq[w];
                end
            end
            // ---------------- read responses
            for (w = 0; w < 32; w = w + 1) if (wrr_q[w*257 + 256]) begin
                if (sc_pend[w]) begin scb[sc_ix[w]] <= wrr_q[w*257 +: 256]; sc_pend[w] <= 1'b0; end
                else if (p1c[w] != (RB+1)'(NR)) begin pb[w][p1c[w][RB-1:0]] <= wrr_q[w*257 +: 256]; p1c[w] <= p1c[w] + 1'b1; end
                else begin
                    if (qn[w] == 2'd3) begin
                        qf[w][qwp[w]] <= {wrr_q[w*257 +: 256], qsh[w]};
                        qwp[w] <= qwp[w] + 1'b1;
                    end else qsh[w][256*qn[w] +: 256] <= wrr_q[w*257 +: 256];
                    qn[w] <= qn[w] + 2'd1;
                end
            end
            for (w = 0; w < 32; w = w + 1) begin : g_qc
                reg pu;
                pu = wrr_q[w*257 + 256] && !sc_pend[w] && p1c[w] == (RB+1)'(NR) && qn[w] == 2'd3;
                qcnt[w] <= qcnt[w] + pu - popq[w];
                if (popq[w]) qrp[w] <= qrp[w] + 1'b1;
            end
            // ---------------- stage A / B
            if (a_rdy) begin
                for (w = 0; w < 8; w = w + 1) a_q[w] <= qf[qlane[w]][qrp[qlane[w]]];
                for (w = 0; w < 32; w = w + 1) pb_rd[w] <= pb[w][RB'((MUT == 3 ? ((ab + 8'd1 < 8'(NB)) ? ab + 8'd1 : ab) : ab) >> 2)];
                a_v <= 1'b1; a_b8 <= (MUT == 3 && ab + 8'd1 < 8'(NB)) ? ab + 8'd1 : ab; ab <= ab + 8'd1;
            end
            if (a_v) begin
                for (w = 0; w < 8; w = w + 1) begin : g_bb
                    reg [4:0] yl; reg [1023:0] q; integer x;
                    yl = v0 + {a_b8[1:0], 3'd0} + 5'(w);
                    q = a_q[w];
                    if (MUT == 2 && w == 0) q = {q[767:512], q[1023:768], q[511:0]};
                    for (x = 0; x < 8; x = x + 1) begin
                        // element 8w + x: HC_POST r_j at [32*(4g + j)]; HC_PRE_NORM copy j of lane l at [(j*64 + l)*32]
                        if (post) begin
                            e_r[32*(4*(8*w + x) + 0) +: 32] <= q[256*0 + 32*x +: 32];
                            e_r[32*(4*(8*w + x) + 1) +: 32] <= q[256*1 + 32*x +: 32];
                            e_r[32*(4*(8*w + x) + 2) +: 32] <= q[256*2 + 32*x +: 32];
                            e_r[32*(4*(8*w + x) + 3) +: 32] <= q[256*3 + 32*x +: 32];
                        end else begin
                            e_r[32*(0*64 + 8*w + x) +: 32] <= q[256*0 + 32*x +: 32];
                            e_r[32*(1*64 + 8*w + x) +: 32] <= q[256*1 + 32*x +: 32];
                            e_r[32*(2*64 + 8*w + x) +: 32] <= q[256*2 + 32*x +: 32];
                            e_r[32*(3*64 + 8*w + x) +: 32] <= q[256*3 + 32*x +: 32];
                        end
                    end
                    e_y[256*w +: 256] <= pb_rd[yl];
                end
                e_v <= 1'b1; e_i <= a_b8;
            end
            // ---------------- output skew line (HC_POST)
            if (ev) begin
                d11 <= hrow(h_od, 1); d21 <= hrow(h_od, 2); d22 <= d21; d31 <= hrow(h_od, 3); d32 <= d31; d33 <= d32;
                v11 <= h_ov; v21 <= h_ov; v22 <= v21; v31 <= h_ov; v32 <= v31; v33 <= v32;
                oe <= oe + 8'd1;
                if (h_ov) bo <= bo + 8'd1;
            end
            // ---------------- drain
            begin : b_dr
                integer np;
                np = 0;
                for (w = 0; w < 32; w = w + 1) begin
                    if (pop[w]) begin wwq[w*280 +: 280] <= {1'b1, f_hd[w][270:256], f_hd[w][255:0], 8'hFF}; np = np + 1; end
                    wcr[w] <= wcr[w] - QB'(pop[w]) + QB'(wwq_cr_q[w]);
                    wpend[w] <= wpend[w] + 8'(pop[w]) - 8'(wwq_done_q[w]);
                    occ[w] <= occ[w] + FB'(push[w]) - FB'(pop[w]);
                end
                nwr <= nwr + 13'(np);
                if (MUT == 4 && st == S_RUN && p2e == 9'(NB + 3) && ab == 8'(NB) && nwr + 13'(np) == nexp) st <= S_FIN;
            end
        end
    end
endmodule
`default_nettype wire
