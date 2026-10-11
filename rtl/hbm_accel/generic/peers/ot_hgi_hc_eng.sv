`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 hyper-connection engine (hgi-unitrate / hgi-1010 b, b-hc, 2026-10-10): FUSED HC_POST and HC_PRE_NORM as ONE
// pass over the wide VM lanes, replacing the record's micro-op lowering (HC_POST: 8 dependent whole-array SU records
// that read the residual 4 times and round-trip each mix through VM scratch; HC_PRE_NORM: mix -> x scratch -> sum of
// squares -> rsqrt -> scale, 4 dependent stage / compute / drain records).  Root cause of the 20.1x / 6.5x unit ratios
// (tput-gate 73bdd2cad): the data movement of the lowering alone exceeds the budget at any SU width.
//
// Arithmetic: the existing exact fused pipelines, unchanged:
//   HC_POST      ot_dsrom_su_hcpost (NG = 64 element groups, 256 outputs a beat):
//                out[k][e] = BF16(y[e]*post[k] + (((r0[e]*c[0][k] + r1[e]*c[1][k]) + r2[e]*c[2][k]) + r3[e]*c[3][k]))
//                = hdc_golden_v41 Model.hc_post.
//   HC_PRE_NORM  ot_dsrom_su_norm (N = 64, HC = 1, MEM = 1, GH = 1): x = bf16(seqsum_j pre[j] h[j]); ss = csum(x x)
//                (chunk8); r = rsqrt(ss / D + eps); y = bf16(w (x r)) = Model.hc_pre + rmsnorm_bf16 under R-ARITH chunk8.
//                GH = 1: the scale waits for the gain ROM (the gain streams in from HBM while the sum is formed).
//
// Job (the record's ne_job, 149 b): {op 2 (1 HC_POST, 0 HC_PRE_NORM), eps 32, n 21, O 18, C 18, 0 21, GPK 1, B 18, A 18}
// (VM word bases).  HC_POST: A = y [D], B = res [4][D], C = post[4] | comb[4][4] (comb[j][k] at C + 4 + 4j + k),
// O = out [4][D].  HC_PRE_NORM: A = h [4][D], B = the gain in VM: GPK = 0 FP32 [D]; GPK = 1 the HBM BF16 row as loaded
// raw by the record's mover (U32 words [D/2], element 2i in the low half of word i); C = pre[4], O = y [D].
// g_rdy (HC_PRE_NORM): the gain is in VM (the mover's done, held by the record); the h pass does not wait for it.
// Refused (fault, no lane activity): n != D, A / B / O not sector aligned.
//
// Lanes (ot_hgi_su_ctlw's wide-lane protocol): read lane b {v, sector 15} -> bank b, LQ credits, sectors back in order;
// write lane b {v, sector 15, data 256, mask 8}, LQ credits, a done a landed write.  Both groups are held (rg / wg
// burst ownership) from the job to its retire.
// Schedule (D a multiple of 256 words (512 for a packed gain), so the 4 rows of an operand sit at the same bank phase):
//   SC  the 1-3 scalar sectors of C (one event; the passes below issue behind it, the engine starts when they land).
//   P1  the single-row vector (HC_POST y, HC_PRE_NORM gain): event e lane L reads row sector 32e + (L - a0) mod 32:
//       every lane every event; into a lane-local buffer, row e.
//   P2  the 4-row operand (res / h) beat b = 64 words (8 sectors) of each row j: event e reads row j of beat e - j, so the
//       4 rows of 4 consecutive beats occupy 4 disjoint 8-lane sets: every lane every event.  A lane's responses are
//       complete quads (j = 0..3 of one beat), collected into a lane quad FIFO (QD deep, reserved at the j = 0 issue).
//   HC_POST: SC, P1, P2 (a beat needs its y).  HC_PRE_NORM: SC, P2, then P1 once g_rdy; the gain is loaded into the norm
//   engine's ROM (one vector a cycle) after P1 and releases its scale phase.
//   A beat is assembled when its 8 lanes hold a quad (HC_POST: and P1 landed).
//   HC_POST output: output event o writes row k of beat o - k (k = 0..3, a 3-beat skew line): again 4 disjoint 8-lane
//   sets, one sector a lane an event, into a lane write FIFO (ot_fifo_sram_fwft, FD deep).  Input beats are admitted
//   only while every lane FIFO has room for everything in flight (no back pressure into the fixed-latency pipeline).
//   HC_PRE_NORM output: y vector i (8 sectors, one a lane) into the same FIFOs; FD >= D / 256 + 1 holds a whole row,
//   so the pipeline's burst never needs back pressure.
// MUT (bench negatives, must FAIL): 1 no output skew (the 4 rows of a beat collide: rows 1..3 lost), 2 P2 quad rows
//   j and j+1 swapped on lane 0, 3 the gain vector of beat b is beat b+1's (PRE) / y of the next beat (POST),
//   4 retire before the last write lands, 5 (PRE) the gain read does not wait for g_rdy.
// ---------------------------------------------------------------------------------------------------------------------
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_hc_lane: one of the controller's 32 lane slices (hbm-phys 2026-10-11: the hardened, replicated element of
// hfd_hc_eng).  Lane L owns VM bank L's read and write lanes: its read credits, the response router (scalar sector ->
// the top; P1 row -> the lane-local P1 buffer; P2 -> the quad collector and the QD-deep quad FIFO, reserved at the
// j = 0 issue), its write FIFO (ot_fifo_sram_fwft FD x 271) with write credits / pending dones / occupancy.  Every VM-side
// input is a pin flop; the VM-side outputs are flops.  The top issues (iss / sc_set), pops (popq) and pushes (push);
// the lane reports flags from its registers.  Cycle- and bit-identical to the flat controller it was cut from.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_lane #(
    parameter integer LQ = 32,
    parameter integer QD = 4,
    parameter integer FD = 64,
    parameter integer NR = 20,               // P1 rows (the FP32 row's D / 256)
    parameter integer NB = 80                // P2 beats (D / 64): a lane's P2 sectors
) (
    input  wire          clk,
    input  wire          rst_n,
    // VM bank lane
    output reg  [15:0]   wrq,
    input  wire          wrq_cr,
    input  wire [256:0]  wrr,
    output reg  [279:0]  wwq,
    input  wire          wwq_cr,
    input  wire          wwq_done,
    // control (the top's registers)
    input  wire          clr,                // S_SC: a new job's P1 / P2 counts start
    input  wire          post,
    input  wire [$clog2(NR):0] p1n,
    input  wire          wg_q,
    input  wire          iss,                // a read this edge
    input  wire [14:0]   iss_sec,
    input  wire          iss_j0,             // a P2 j = 0 read (reserves a quad slot)
    input  wire          sc_set,             // the scalar read of sector sc_ix
    input  wire [1:0]    sc_ix,
    input  wire          popq,
    input  wire          pb_re,
    input  wire [((NR <= 1) ? 1 : $clog2(NR))-1:0] pb_ra,
    output reg  [255:0]  pb_q,
    output wire [1023:0] q_head,
    output wire          q_nz,
    output wire          q_full,             // qres >= QD
    output wire          cr_nz,
    output wire          p1_full,
    output wire          sc_pend,
    output wire          sc_v,               // a scalar sector landed: {sc_vix, sc_d}
    output wire [1:0]    sc_vix,
    output wire [255:0]  sc_d,
    input  wire          push,
    input  wire [270:0]  pdat,
    output wire          pop,
    output wire [$clog2(FD+1)-1:0] occ_o,
    output wire          quiet,
    output wire          ovf
);
    localparam integer QB = $clog2(LQ + 1), RB = (NR <= 1) ? 1 : $clog2(NR), FB = $clog2(FD + 1);
    localparam integer QDB = (QD <= 1) ? 1 : $clog2(QD);
    reg wrq_cr_q, wwq_cr_q, wwq_done_q; reg [256:0] wrr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wrq_cr_q <= 1'b0; wwq_cr_q <= 1'b0; wwq_done_q <= 1'b0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg [QB-1:0] cr; reg scp; reg [1:0] scx; reg [RB:0] p1c; reg [7:0] p2c; reg [1:0] qn; reg [767:0] qsh;
    reg [1023:0] qf [0:QD-1]; reg [QDB-1:0] qwp, qrp; reg [$clog2(QD+1)-1:0] qcnt, qres;
    reg [255:0] pb [0:NR-1];
    reg [FB-1:0] occ; reg [QB-1:0] wcr; reg [7:0] wpend;
    // a response that is not a scalar: HC_POST P1 first (then P2); HC_PRE_NORM P2 first (then P1)
    wire is_p1x = post ? (p1c != p1n) : (p2c == 8'(NB));
    assign q_head = qf[qrp]; assign q_nz = qcnt != '0; assign q_full = qres >= QD; assign cr_nz = cr != '0;
    assign p1_full = p1c == p1n; assign sc_pend = scp;
    wire rv = wrr_q[256];
    assign sc_v = rv && scp; assign sc_vix = scx; assign sc_d = wrr_q[255:0];
    wire f_hv; wire [270:0] f_hd;
    ot_fifo_sram_fwft #(.W(271), .DEPTH(FD), .MACRO(0)) u_f (.clk(clk), .rst_n(rst_n), .push(push), .wdata(pdat), .pop(pop),
        .hv(f_hv), .head(f_hd), .ovf(ovf));
    assign pop = wg_q && f_hv && (wcr != '0);
    assign occ_o = occ;
    assign quiet = !f_hv && occ == '0 && wpend == 8'd0 && wcr == QB'(LQ) && cr == QB'(LQ);
    always @(posedge clk) begin
        if (rv && !scp && is_p1x) pb[p1c[RB-1:0]] <= wrr_q[255:0];
        if (rv && !scp && !is_p1x && qn == 2'd3) qf[qwp] <= {wrr_q[255:0], qsh};
        if (rv && !scp && !is_p1x && qn != 2'd3) qsh[256*qn +: 256] <= wrr_q[255:0];
        if (pb_re) pb_q <= pb[pb_ra];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            wrq <= '0; wwq <= '0; cr <= QB'(LQ); scp <= 1'b0; scx <= '0; p1c <= '0; p2c <= '0; qn <= '0; qwp <= '0; qrp <= '0;
            qcnt <= '0; qres <= '0; occ <= '0; wcr <= QB'(LQ); wpend <= '0;
        end else begin : seq
            reg pu;
            wrq <= {iss, iss_sec};
            wwq <= pop ? {1'b1, f_hd[270:256], f_hd[255:0], 8'hFF} : {1'b0, wwq[278:0]};
            cr <= cr - QB'(iss) + QB'(wrq_cr_q);
            qres <= qres + iss_j0 - popq;
            if (sc_set) begin scp <= 1'b1; scx <= sc_ix; end
            pu = 1'b0;
            if (rv) begin
                if (scp) scp <= 1'b0;
                else if (is_p1x) p1c <= p1c + 1'b1;
                else begin
                    if (qn == 2'd3) begin qwp <= qwp + 1'b1; pu = 1'b1; end
                    qn <= qn + 2'd1; p2c <= p2c + 8'd1;
                end
            end
            qcnt <= qcnt + pu - popq;
            if (popq) qrp <= qrp + 1'b1;
            if (clr) begin p1c <= '0; p2c <= '0; end
            wcr <= wcr - QB'(pop) + QB'(wwq_cr_q);
            wpend <= wpend + 8'(pop) - 8'(wwq_done_q);
            occ <= occ + FB'(push) - FB'(pop);
        end
endmodule

module ot_hgi_hc_ctl #(
    parameter integer D   = 5120,        // the row length (a multiple of 256)
    parameter integer LQ  = 32,          // credits a wide lane holds (= the VM lane queue depth)
    parameter integer QD  = 4,           // lane quad FIFO depth
    parameter integer FD  = 64,          // lane write FIFO depth (power of two <= 64)
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
    output wire [32*16-1:0]  wrq,           // driven by the lane slices
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt,
    // the compute engines (ot_hgi_hc_eng instantiates them; the hardened element is this controller): HC_POST
    // ot_dsrom_su_hcpost NG 64 / HC_PRE_NORM ot_dsrom_su_norm N 64 HC 1 MEM 1 GH 1.  Every output is a flop.
    output reg               e_go,           // a row starts (both engines see it; e_post selects)
    output reg               e_post,
    output reg               e_v,            // a beat: HC_POST {r0..r3 of 64 elements, y}; HC_PRE_NORM h[0..3] of 64 lanes
    output reg  [64*4*32-1:0] e_r,
    output reg  [64*32-1:0]  e_y,
    output reg  [511:0]      comb_w,
    output reg  [127:0]      post_w,
    output reg  [127:0]      pre_w,
    output reg  [31:0]       eps_r,
    output reg               wl_v,           // gain ROM load
    output reg  [7:0]        wl_i,
    output reg  [64*32-1:0]  wl_d,
    output reg               g_loaded,       // the gain ROM holds the whole row (releases the norm's scale)
    input  wire              h_ov_i,           // HC_POST output beat: out[k][e] at [32*(4e + k)]
    input  wire [64*4*32-1:0] h_od_i,
    input  wire              h_f_i,
    input  wire              n_yv_i,           // HC_PRE_NORM y vector
    input  wire [7:0]        n_yi_i,
    input  wire [64*32-1:0]  n_y_i,
    input  wire              n_f_i
);
    localparam integer NB = D / 64;          // beats
    localparam integer NR = D / 256;         // P1 rows a lane (FP32 row)
    localparam integer NRP = D / 512;        // P1 rows a lane (packed BF16 gain)
    localparam integer SD = D / 8;           // sectors a row
    localparam integer QB = $clog2(LQ + 1);
    localparam integer RB = (NR <= 1) ? 1 : $clog2(NR);
    localparam integer FB = $clog2(FD + 1);
    localparam integer QDB = (QD <= 1) ? 1 : $clog2(QD);
    generate if (D % 256 != 0 || NB > 255 || FD < NR + 1 || FD > 64 || (FD & (FD - 1)) != 0 || (QD & (QD - 1)) != 0)
    begin : g_bad
        ot_hgi_hc_eng_D_must_be_a_multiple_of_256_FD_a_power_of_two_in_NR1_64 u_trap ();
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
    // (the lane inputs are pin-flopped in the lane slices)
    reg rg_q, wg_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rg_q <= 1'b0; wg_q <= 1'b0; end
        else begin rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req; end

    // ---- job
    localparam [2:0] S_IDLE = 0, S_GRP = 1, S_SC = 2, S_RUN = 4, S_FIN = 5;
    reg [2:0] st;
    reg       post;                          // 1 HC_POST, 0 HC_PRE_NORM
    reg       gpk;                           // HC_PRE_NORM: the gain is packed BF16
    reg [17:0] a_b, b_b, c_b, o_b;
    wire [17:0] p1_b = post ? a_b : b_b;     // the single-row vector
    wire [17:0] p2_b = post ? b_b : a_b;     // the 4-row operand
    wire [14:0] p1_s = p1_b[17:3], p2_s = p2_b[17:3], o_s = o_b[17:3];
    wire [4:0]  v0 = p1_s[4:0], s0 = p2_s[4:0], o0 = o_s[4:0];
    assign job_rdy = (st == S_IDLE);
    // ---- pin flops: every input is captured by a flop (the engines' outputs, the job, g_rdy, the lanes below)
    reg job_v, g_rdy, h_ov, h_f, n_yv, n_f; reg [148:0] job; reg [64*4*32-1:0] h_od; reg [7:0] n_yi; reg [64*32-1:0] n_y;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin job_v <= 1'b0; g_rdy <= 1'b0; h_ov <= 1'b0; h_f <= 1'b0; n_yv <= 1'b0; n_f <= 1'b0; end
        else begin job_v <= job_v_i && (st == S_IDLE) && !job_v; g_rdy <= g_rdy_i; h_ov <= h_ov_i; h_f <= h_f_i;
                   n_yv <= n_yv_i; n_f <= n_f_i; end
    always @(posedge clk) begin job <= job_i; h_od <= h_od_i; n_yi <= n_yi_i; n_y <= n_y_i; end
    wire job_ok = (job[114:94] == 21'(D)) && (job[2:0] == 3'd0) && (job[20:18] == 3'd0) && (job[78:76] == 3'd0) &&
                  !(job[148:147] == 2'd0 && job[36] && (D % 512 != 0));
    reg  [RB:0] p1n;                         // P1 events (= rows a lane)
    reg  g_ok;                               // g_rdy seen (HC_PRE_NORM)

    // ---- read side
    reg [2:0]  nsc;                          // scalar sectors (1..3)
    reg        sc_ok;                        // the scalars landed and went to the engine
    reg [255:0] scb [0:3];
    reg [RB:0] p1e; reg [8:0] p2e;           // events issued
    // ---- the 32 lane slices (their flags, from their registers)
    wire [31:0] l_cr_nz, l_q_nz, l_q_full, l_p1_full, l_scp, l_sc_v, l_pop, l_quiet, l_ovf;
    wire [32*2-1:0] l_sc_vix; wire [32*256-1:0] l_sc_d, l_pb_q; wire [32*1024-1:0] l_qh; wire [32*FB-1:0] l_occ;
    // this edge's lane commands (combinational, below)
    reg [31:0] c_iss, c_j0, c_scs, c_pbre; reg [14:0] c_sec [0:31]; reg [1:0] c_scix [0:31]; reg [RB-1:0] c_pbra [0:31];
    wire [1023:0] scw = {scb[3], scb[2], scb[1], scb[0]};
    wire [639:0] scx = scw[{c_b[2:0], 5'd0} +: 640];   // C words 0..19 from the scalar sectors
    wire p2_all = (p2e == 9'(NB + 3));
    wire p1_all = (p1e == p1n);
    // the pass issued this cycle (HC_POST: P1 then P2; HC_PRE_NORM: P2 then P1 once the gain is in VM)
    wire ph1 = (st == S_RUN) && !p1_all && (post || (p2_all && (g_ok || MUT == 5)));
    wire ph2 = (st == S_RUN) && !p2_all && (!post || p1_all);

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
            if (p2v[L] && (!l_cr_nz[L] || (p2j0[L] && l_q_full[L]))) ev_ok = 1'b0;
    end
    reg p1_all_cr;
    always @* p1_all_cr = &l_cr_nz;
    reg p1_done;
    always @* p1_done = &l_p1_full;

    // ---- beat assembly: stage A pops the 8 quads of beat ab (HC_POST: and reads the y row ab / 4); stage B forms it
    reg [7:0] ab, bo;                        // beats into the engine / beats out of it (HC_POST)
    reg [7:0] oe;                            // output events (HC_POST, incl. the 3 flush events)
    reg room;
    always @* begin
        room = 1'b1;
        for (L = 0; L < 32; L = L + 1)
            if ({1'b0, l_occ[L*FB +: FB]} + 8'(ab - bo) + 8'd5 > 8'(FD)) room = 1'b0;
    end
    reg [4:0] qlane [0:7]; reg a_rdy;
    always @* begin
        a_rdy = (st == S_RUN) && sc_ok && (ab < 8'(NB)) && (!post || (p1_done && room));
        for (L = 0; L < 8; L = L + 1) begin
            qlane[L] = s0 + {ab[1:0], 3'd0} + 5'(L);
            if (!l_q_nz[qlane[L]]) a_rdy = 1'b0;
        end
    end
    reg [31:0] popq;
    always @* begin popq = '0; if (a_rdy) for (L = 0; L < 8; L = L + 1) popq[qlane[L]] = 1'b1; end
    reg a_v; reg [7:0] a_b8; reg [1023:0] a_q [0:7];
    // ---- HC_PRE_NORM gain load: vector gi of w from the P1 buffer (G1 gather, G2 unpack -> the norm's ROM)
    reg [7:0] gi; reg g1_v; reg [7:0] g1_i; reg [4:0] g1_ln [0:7];
    wire g1_go = !post && st == S_RUN && p1_all && p1_done && gi < 8'(NB);
    // ---- output: HC_POST skew line (row k of beat o - k at output event o), HC_PRE_NORM y vectors
    reg [2047:0] d11, d21, d22, d31, d32, d33;
    reg v11, v21, v22, v31, v32, v33;         // validity along the lines
    wire [2047:0] hr [0:3];                   // row k of the engine's output beat
    genvar gk, gg;
    generate for (gk = 0; gk < 4; gk = gk + 1) begin : g_hr
        for (gg = 0; gg < 64; gg = gg + 1) begin : g_e
            assign hr[gk][32*gg +: 32] = h_od[32*(4*gg + gk) +: 32];
        end
    end endgenerate
    wire ev = post && (h_ov || (bo == 8'(NB) && oe < 8'(NB + 3)));
    reg [3:0] rv; reg [2047:0] rd [0:3]; reg [7:0] rbt [0:3];
    always @* begin
        rv[0] = h_ov;         rd[0] = hr[0];         rbt[0] = oe;
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
                        reg [4:0] ln; ln = o0 + {oe[1:0], 3'd0} + 5'(t);
                        push[ln] = 1'b1;
                        pdat[ln] = {15'(o_s + 15'(k) * 15'(SD) + {oe, 3'd0} + 15'(t)), hr[k][256*t +: 256]};
                    end
        end else if (post && ev) begin
            for (k = 0; k < 4; k = k + 1)
                if (rv[k])
                    for (t = 0; t < 8; t = t + 1) begin : g_pp
                        reg [4:0] ln; ln = o0 + {rbt[k][1:0], 3'd0} + 5'(t);
                        push[ln] = 1'b1;
                        pdat[ln] = {15'(o_s + 15'(k) * 15'(SD) + {rbt[k], 3'd0} + 15'(t)), rd[k][256*t +: 256]};
                    end
        end
        if (!post && n_yv)
            for (t = 0; t < 8; t = t + 1) begin : g_py
                reg [4:0] ln; ln = o0 + {n_yi[1:0], 3'd0} + 5'(t);
                push[ln] = 1'b1;
                pdat[ln] = {15'(o_s + {n_yi, 3'd0} + 15'(t)), n_y[256*t +: 256]};
            end
    end
    // ---- the lane slices
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_ln
        wire [15:0] lq; wire [279:0] lw;
        assign wrq[gl*16 +: 16] = lq; assign wwq[gl*280 +: 280] = lw;
        ot_hgi_hc_lane #(.LQ(LQ), .QD(QD), .FD(FD), .NR(NR), .NB(NB)) u_l (.clk(clk), .rst_n(rst_n), .wrq(lq),
            .wrq_cr(wrq_cr[gl]), .wrr(wrr[gl*257 +: 257]), .wwq(lw), .wwq_cr(wwq_cr[gl]), .wwq_done(wwq_done[gl]),
            .clr(st == S_SC), .post(post), .p1n(p1n), .wg_q(wg_q), .iss(c_iss[gl]), .iss_sec(c_sec[gl]), .iss_j0(c_j0[gl]),
            .sc_set(c_scs[gl]), .sc_ix(c_scix[gl]), .popq(popq[gl]), .pb_re(c_pbre[gl]), .pb_ra(c_pbra[gl]),
            .pb_q(l_pb_q[gl*256 +: 256]), .q_head(l_qh[gl*1024 +: 1024]), .q_nz(l_q_nz[gl]), .q_full(l_q_full[gl]),
            .cr_nz(l_cr_nz[gl]), .p1_full(l_p1_full[gl]), .sc_pend(l_scp[gl]), .sc_v(l_sc_v[gl]),
            .sc_vix(l_sc_vix[gl*2 +: 2]), .sc_d(l_sc_d[gl*256 +: 256]), .push(push[gl]), .pdat(pdat[gl]), .pop(l_pop[gl]),
            .occ_o(l_occ[gl*FB +: FB]), .quiet(l_quiet[gl]), .ovf(l_ovf[gl]));
    end endgenerate
    // the lane commands of this edge: reads (scalar / P1 / P2 event), quad pops, P1-buffer reads
    always @* begin
        c_iss = '0; c_j0 = '0; c_scs = '0; c_pbre = '0;
        for (L = 0; L < 32; L = L + 1) begin c_sec[L] = '0; c_scix[L] = '0; c_pbra[L] = '0; end
        if (st == S_SC)
            for (L = 0; L < 4; L = L + 1) if (L < nsc) begin : g_sc
                reg [14:0] sx; sx = c_b[17:3] + 15'(L);
                c_iss[sx[4:0]] = 1'b1; c_sec[sx[4:0]] = sx; c_scs[sx[4:0]] = 1'b1; c_scix[sx[4:0]] = 2'(L);
            end
        if (st == S_RUN) begin
            if (ph1) begin
                if (p1_all_cr)
                    for (L = 0; L < 32; L = L + 1) begin : g_p1
                        reg [4:0] u; u = 5'(L) - v0;
                        c_iss[L] = 1'b1; c_sec[L] = 15'(p1_s + {p1e, 5'd0} + {10'd0, u});
                    end
            end else if (ph2 && ev_ok)
                for (L = 0; L < 32; L = L + 1) if (p2v[L]) begin c_iss[L] = 1'b1; c_sec[L] = p2sec[L]; c_j0[L] = p2j0[L]; end
        end
        if (a_rdy && post)
            for (L = 0; L < 32; L = L + 1) begin
                c_pbre[L] = 1'b1; c_pbra[L] = RB'((MUT == 3 ? ((ab + 8'd1 < 8'(NB)) ? ab + 8'd1 : ab) : ab) >> 2);
            end
        if (g1_go) begin : g_g1r
            reg [7:0] gs; reg [9:0] q0; reg [4:0] ln;
            gs = (MUT == 3 && gi + 8'd1 < 8'(NB)) ? gi + 8'd1 : gi;
            for (L = 0; L < 8; L = L + 1) begin
                q0 = gpk ? ({2'b0, gs, 2'b00} + 10'(L & 3)) : ({1'b0, gs, 3'b000} + 10'(L));
                ln = v0 + q0[4:0];
                c_pbre[ln] = 1'b1; c_pbra[ln] = RB'(q0 >> 5);
            end
        end
    end

    reg [12:0] nwr, nexp;                    // sectors written / expected
    reg sfault;
    reg quiet;
    always @* begin
        quiet = 1'b1;
        for (L = 0; L < 32; L = L + 1)
            if (!l_quiet[L]) quiet = 1'b0;
    end
    assign idle = (st == S_IDLE);

    integer w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0;
            post <= 1'b0; e_post <= 1'b0; gpk <= 1'b0; e_r <= '0; e_y <= '0; wl_d <= '0; eps_r <= '0; a_b <= '0; b_b <= '0; c_b <= '0; o_b <= '0; nsc <= '0;
            sc_ok <= 1'b0; p1n <= '0; g_ok <= 1'b0;
            p1e <= '0; p2e <= '0; ab <= '0; bo <= '0; oe <= '0; a_v <= 1'b0; e_go <= 1'b0; e_v <= 1'b0;
            v11 <= 1'b0; v21 <= 1'b0; v22 <= 1'b0; v31 <= 1'b0; v32 <= 1'b0; v33 <= 1'b0; nwr <= '0; nexp <= '0; sfault <= 1'b0;
            post_w <= '0; pre_w <= '0; comb_w <= '0; a_b8 <= '0;
            gi <= '0; g1_v <= 1'b0; g1_i <= '0; wl_v <= 1'b0; wl_i <= '0; g_loaded <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; e_go <= 1'b0; e_v <= 1'b0; a_v <= 1'b0; g1_v <= 1'b0; wl_v <= 1'b0;
            if (h_f || n_f || (|l_ovf)) sfault <= 1'b1;
            if (g_rdy) g_ok <= 1'b1;
            // ---------------- read issue
            begin : b_iss
                case (st)
                    S_IDLE: if (job_v) begin
                        post <= (job[148:147] == 2'd1); e_post <= (job[148:147] == 2'd1); gpk <= job[36]; eps_r <= job[146:115]; o_b <= job[93:76];
                        c_b <= job[75:58]; b_b <= job[35:18]; a_b <= job[17:0]; g_ok <= 1'b0; g_loaded <= 1'b0;
                        p1n <= (job[148:147] == 2'd0 && job[36]) ? (RB+1)'(NRP) : (RB+1)'(NR);
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
                        st <= S_RUN; sc_ok <= 1'b0;
                        p1e <= '0; p2e <= '0; ab <= '0; bo <= '0; oe <= '0; nwr <= '0; gi <= '0;
                    end
                    S_RUN: begin
                        if (l_scp == '0 && !sc_ok) begin            // the scalars landed: weights to the engine, go
                            post_w <= scx[127:0]; pre_w <= scx[127:0]; comb_w <= scx[639:128];
                            e_go <= 1'b1; sc_ok <= 1'b1;
                        end
                        if (ph1) begin
                            if (p1_all_cr) p1e <= p1e + 1'b1;
                        end else if (ph2 && ev_ok) p2e <= p2e + 1'b1;
                        if (p2_all && p1_all && ab == 8'(NB) && nwr == nexp && quiet && !a_v && !e_v) st <= S_FIN;
                    end
                    S_FIN: begin
                        rg_req <= 1'b0; wg_req <= 1'b0; st <= S_IDLE; sc_ok <= 1'b0;
                        if (sfault) fault <= 1'b1; else done <= 1'b1;
                        sfault <= 1'b0;
                    end
                    default: st <= S_IDLE;
                endcase
            end
            // ---------------- read responses: the lanes route them; the scalar sectors come here
            for (w = 0; w < 32; w = w + 1) if (l_sc_v[w]) scb[l_sc_vix[w*2 +: 2]] <= l_sc_d[w*256 +: 256];
            // ---------------- stage A / B
            if (a_rdy) begin
                for (w = 0; w < 8; w = w + 1) a_q[w] <= l_qh[qlane[w]*1024 +: 1024];
                a_v <= 1'b1; a_b8 <= (MUT == 3 && post && ab + 8'd1 < 8'(NB)) ? ab + 8'd1 : ab; ab <= ab + 8'd1;
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
                    if (post) e_y[256*w +: 256] <= l_pb_q[yl*256 +: 256];
                end
                e_v <= 1'b1;
            end
            // ---------------- HC_PRE_NORM gain load (after P1): G1 gathers vector gi's sectors, G2 writes the ROM
            if (g1_go) begin : g_g1
                reg [7:0] gs; reg [9:0] q0;
                gs = (MUT == 3 && gi + 8'd1 < 8'(NB)) ? gi + 8'd1 : gi;
                for (w = 0; w < 8; w = w + 1) begin
                    // packed: sector 4 gs + w (w < 4); FP32: sector 8 gs + w (the lane reads it: l_pb_q next edge)
                    q0 = gpk ? ({2'b0, gs, 2'b00} + 10'(w & 3)) : ({1'b0, gs, 3'b000} + 10'(w));
                    g1_ln[w] <= v0 + q0[4:0];
                end
                g1_v <= 1'b1; g1_i <= gi; gi <= gi + 8'd1;
            end
            if (g1_v) begin
                for (w = 0; w < 64; w = w + 1)
                    if (gpk) wl_d[32*w +: 32] <= {l_pb_q[g1_ln[w >> 4]*256 + 32*((w >> 1) & 7) + 16*(w & 1) +: 16], 16'd0};
                    else     wl_d[32*w +: 32] <= l_pb_q[g1_ln[w >> 3]*256 + 32*(w & 7) +: 32];
                wl_v <= 1'b1; wl_i <= g1_i;
            end
            if (wl_v && wl_i == 8'(NB - 1)) g_loaded <= 1'b1;
            // ---------------- output skew line (HC_POST)
            if (ev) begin
                d11 <= hr[1]; d21 <= hr[2]; d22 <= d21; d31 <= hr[3]; d32 <= d31; d33 <= d32;
                v11 <= h_ov; v21 <= h_ov; v22 <= v21; v31 <= h_ov; v32 <= v31; v33 <= v32;
                oe <= oe + 8'd1;
                if (h_ov) bo <= bo + 8'd1;
            end
            // ---------------- drain
            begin : b_dr
                integer np;
                np = 0;
                for (w = 0; w < 32; w = w + 1) if (l_pop[w]) np = np + 1;
                nwr <= nwr + 13'(np);
                if (MUT == 4 && st == S_RUN && p2_all && p1_all && ab == 8'(NB) && nwr + 13'(np) == nexp) st <= S_FIN;
            end
        end
    end
endmodule

// the engine = the controller (the hardened element) + the existing exact compute pipelines
module ot_hgi_hc_eng #(
    parameter integer D   = 5120,
    parameter integer LQ  = 32,
    parameter integer QD  = 4,
    parameter integer FD  = 64,
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
    function automatic [31:0] f32i(input integer x);     // binary32 of a positive integer < 2^24 (exact)
        integer e; reg [31:0] r;
        begin
            e = 0; while ((x >> (e + 1)) != 0) e = e + 1;
            r = {1'b0, 8'(127 + e), 23'((x << (23 - e)) & 32'h7FFFFF)};
            f32i = r;
        end
    endfunction
    localparam [31:0] NF = f32i(D);
    wire e_go, post, e_v, wl_v, g_loaded; wire [64*4*32-1:0] e_r; wire [64*32-1:0] e_y, wl_d; wire [511:0] comb_w;
    wire [127:0] post_w, pre_w; wire [31:0] eps_r; wire [7:0] wl_i;
    wire h_ov, h_f, n_yv, n_f;
    wire [64*4*32-1:0] h_od; wire [7:0] n_yi; wire [64*32-1:0] n_y;
    ot_hgi_hc_ctl #(.D(D), .LQ(LQ), .QD(QD), .FD(FD), .MUT(MUT)) u_ctl (.clk(clk), .rst_n(rst_n), .job_v_i(job_v),
        .job_rdy(job_rdy), .job_i(job), .g_rdy_i(g_rdy), .done(done), .fault(fault), .idle(idle), .wrq(wrq), .wrq_cr(wrq_cr),
        .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req),
        .wg_gnt(wg_gnt), .e_go(e_go), .e_post(post), .e_v(e_v), .e_r(e_r), .e_y(e_y), .comb_w(comb_w), .post_w(post_w),
        .pre_w(pre_w), .eps_r(eps_r), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .g_loaded(g_loaded), .h_ov_i(h_ov),
        .h_od_i(h_od), .h_f_i(h_f), .n_yv_i(n_yv), .n_yi_i(n_yi), .n_y_i(n_y), .n_f_i(n_f));
    // ---- engines
    ot_dsrom_su_hcpost #(.NG(64), .WIN(2), .WOUT(2), .ML(7), .AL(6)) u_post (.clk(clk), .rst_n(rst_n), .go(e_go && post),
        .comb(comb_w), .post(post_w), .in_v(e_v && post), .in_r(e_r), .in_y(e_y), .out_v(h_ov), .out_d(h_od), .fault(h_f));
    ot_dsrom_su_norm #(.N(64), .D(D), .HC(1), .RD(0), .QUANT(0), .MEM(1), .GH(1), .RW(9), .BW(9), .LM(5), .LA(6), .RXS(1), .SXC(1), .FREG(1)) u_norm (
        .clk(clk), .rst_n(rst_n), .go(e_go && !post), .in_v(e_v && !post), .in_x(e_r), .pre(pre_w), .n_f(NF), .eps(eps_r),
        .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t({31'd0, g_loaded}), .sin_t(32'd0), .y_v(n_yv), .y_i(n_yi), .y(n_y),
        .r_v(), .r(), .q_v(), .q_i(), .q_codes(), .q_e(), .q_y(), .ro_v(), .ro(), .fault(n_f));

endmodule
`default_nettype wire
