`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17; helper S81-SLICE-SU): vs = the SU lane engine of one BEAT leaf of a DV vector slice
// (x5 per slice, own clock root).  It runs the central S81 SU's element ops on the beat leaf's rows: the leaf store
// lives in vp; vs reads and writes it through vp's extension port (one row-pair read and one row-pair write a cycle at
// most, in compiler slots that never meet a vp op) and streams act-quant inputs to vq's second input (u / um).
// Sub-leaves it drives (each its own master and clock root, registered pins both sides; measured flops in the header of
// tools/s81_slice/vs_bench.sh):
//   ot_s81sl_vsw               one hub SwiGLU lane (ot_s81_su_swl, unchanged: ~14k flops, so it cannot share vs's root)
//   ot_s81_su_rxsf -> _rxsb    the closed hub RA lane pair (sqrt(softplus); front / back leaves dsfd_su_t_rxsf / _rxsb)
//
// Commands: vp forwards ops 8..15 unchanged (s_v / s_d, one edge).  s_d = {imm 128, n 8, a1 10, a0 10, op 4};
//   imm[9:0] ob (result row base)   imm[10] wb (write results)   imm[11] uq (stream to vq)   imm[12] / [13] um_q / um_b
//   imm[21:14] um_i (the vector's global beat index for vq)  imm[24:22] j0 (first vq sub-beat)
//   imm[63:32] lim   imm[95:64] w0 (groups 0..7)   imm[127:96] w1 (groups 8..15)            (SW only)
//   imm[25] wr, imm[28:26] wsel (SW only; TOK-S81-GAPS 10-18): w0 = w1 = FP32 word wsel of the leaf-store row pair a1
//           (the gunit router's weights rows R+1 / R+2, CTL target 5).  The weight row pair is read at step 0, the groups
//           follow 4 edges later on the same SW cadence (fixed timeline, +4 edges; no handshake).  wr = 0: imm w0 / w1.
// ONE op runs at a time, from its command to its last result: a command while busy, op 14 / 15, or a malformed count is
// a sticky fault (the compiler schedules every op on its measured fixed timeline; nothing waits or arbitrates).
// Operand layouts are compiler-fixed: a read is the row pair (a0 + 2 s, a0 + 2 s + 1) = x_qd[127:0], x_qd[255:128].
//   8  SW   n groups (<= 16, 4 elements each), one read every 4 cycles: row a0 + 2 s = g[4 s ..], a0 + 2 s + 1 = u[4 s ..]
//           -> vsw: a = BF16(w * (silu(min(g, lim)) * clip(u, -lim, lim))), the hub lane's units and order.  w = w0 for
//           groups 0..7, w1 for 8..15 (one 32-element act-quant block each; the shared expert: w = 1.0, exact).
//           wb: row ob + s (FP32 words holding BF16);  uq: groups 2 i, 2 i + 1 -> vq sub-beat j0 + i; um at the command.
//   9  QB   n sub-beats (j0 + n <= 8): row pair a0 + 2 s -> vq sub-beat j0 + s unchanged (z_quant: vq's ot_dsrom_aq12
//           is the golden act-quant; su_gate qb() has no other step).  um at the command.
//   10 RA   n elements: rows a0 .. (8 a read, one read every 8 cycles) -> r = sqrt(softplus(x)) one a cycle on the RA
//           lane pair (ra_* pins) -> rows ob + i / 4 (FP32; the last row word-masked).
//   11 RB   n rows: row a0 + 2 s = scores, a0 + 2 s + 1 = bias -> scores + bias (ot_dsrom_qadd, 4 lanes) -> row ob + s.
//   12 QR   n rows, one read every 2 cycles: row a0 + 2 s = q[4 s .. 4 s + 3] (2 adjacent pairs), a0 + 2 s + 1 =
//           {c, s, c', s'} of the two pairs -> rope_tail (re = a c - b s, im = b c + a s: 2 ot_hdc_qmul_lat + 1
//           ot_dsrom_qadd a lane, the hub ot_s81_su_rxqr lane; one pair a cycle on 2 lanes), BF16 -> row ob + s.
//   13 MOE  n = 8 chunks: expert e (0..6, routed in id order then shared) chunk c at rows a0 + 16 e + 2 c, + 1 (8
//           elements) -> (((((e0 + e1) + e2) + e3) + e4) + e5) + e6, every partial binary32 RNE (ot_dsrom_qadd LAT 6 =
//           the hub moe leaf's ot_dsrom_fp32_add_f12_l6), BF16 at the end -> row pair ob + 2 c.  8 lanes, expert-major
//           reads one a cycle: the adder loop is 8 cycles (operand register, LAT 6, acc register), so chunk c's partial
//           meets its next expert exactly; phase 0 passes e0 through the adder as e0 + (-0), an exact identity in RNE
//           for every e0 (a NaN / Inf operand raises the adder fault, as it would in e0 + e1).
//   14 ENG  (RTL-BUILD-S81 2026-10-18) the Engram mix feeder of the beat's ve sub-leaf (ot_s81sl_ve, the 4 HC copies x 64
//           elements of this beat; golden tools/hdc_golden_v41.py engram_layer).  imm[30] = phase.  The beat's h is first
//           copied into the leaf store by vp HSTORE (32 rows at Hb, vn's half-row layout: half row i = rows Hb + 2 i,
//           Hb + 2 i + 1 = elements 4 i .. 4 i + 3 of all 4 copies, copy j element 4 i + e at bits (4 j + e) * 16).
//           K / W / V region (compiler row map results/arch/s81_dv_1016/eng/kv_rowmap.json, A0 per Engram layer): K_j at
//           A0 + 16 j (element 4 r + w at row A0 + 16 j + r, word w), W_j at A0 + 64 + 16 j, V at A0 + 128 (144 rows).
//           phase 0 REDUCE  n = 64, a0 = Hb, a1 = A0: 16 h row-pair reads (one a cycle) into the h stash (4 kb), then
//                   64 reads alternating K_j and W_j row pairs (8 elements = 2 quads each; copy-major) -> ve quads, one a
//                   cycle after the first pair (GAP 0); the 4 ve beat partial triples (hh, kk, dd)
//                   leave the leaf on e_v / e_c / e_d (pin flops, toward xr -> xfin ENG).  Done = 4th triple out.
//                   The gate latch is cleared at the command.
//           gates   g_v / g_c / g_d (eg -> centre -> this leaf): gate of copy g_c latched; a second gate of one copy
//                   before the next REDUCE is a sticky fault.
//           phase 1 ADD  n = 32, a0 = A0, a1 = Hb' (write-back base): all 4 gates must be latched (else fault, command
//                   refused).  32 reads of the V row pairs (A0 + 128 + 2 s = V[8 s .. 8 s + 7], re-read per copy) -> one ve add
//                   beat a cycle (8 elements of copy j = read >> 3, h from the stash, gate j) -> the 32 BF16 results land
//                   in the stash in place (copy j's slots only) -> 16 row-pair writes Hb' + 2 i (the h layout) -> vp HLOAD
//                   moves them back into vn's h store.  Done = last write.
// Pins: every input lands in a flop; every output leaves a flop.  Reset: ot_rst_relay (regional synchronous release).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vs #(
    parameter integer XL = 6,          // qmul / qadd latency (ot_hdc_qmul_lat 6 as rxqr, ot_dsrom_qadd 6 = f12_l6)
    parameter integer MUT = 0          // bench negative controls: 1 SW drops w, 2 RB drops bias, 3 QR inverse rotation,
                                       // 4 MOE rounds every partial to BF16, 5 QB swaps the sub-beat halves, 6 RA returns rows shifted,
                                       // 9 SW wr takes w1 from word wsel ^ 1 of the weight row
                                       // 7 ENG ADD takes the gate of copy j ^ 1, 8 ENG REDUCE feeds K as W
) (
    input  wire          clk,
    input  wire          rst_n,
    // command (from vp)
    input  wire          s_v,
    input  wire [159:0]  s_d,
    // vp leaf-store extension port: row-pair read (data on x_qv / x_qd a fixed number of edges later) and write
    output reg           x_rv,
    output reg  [9:0]    x_ra,
    input  wire          x_qv,
    input  wire [255:0]  x_qd,
    output reg           x_wv,
    output reg  [9:0]    x_wa,
    output reg  [7:0]    x_wm,
    output reg  [255:0]  x_wd,
    // vq second input: 8-lane sub-beats + gather mode
    output reg           u_v,
    output reg  [2:0]    u_i,
    output reg  [255:0]  u,
    output reg           um_v,
    output reg           um_q,
    output reg           um_b,
    output reg  [7:0]    um_i,
    // SW lane sub-leaf (ot_s81sl_vsw): a group {u3..u0, g3..g0} with its weight / limit; 4 BF16 results back
    output reg           sw_v,
    output reg  [255:0]  sw_d,
    output reg  [31:0]   sw_w,
    output reg  [31:0]   sw_lim,
    input  wire          sw_vi,
    input  wire [63:0]   sw_ri,
    input  wire          sw_fi,
    // RA lane pair (closed hub leaves): to ot_s81_su_rxsf, from ot_s81_su_rxsb
    output reg           ra_v,
    output reg  [31:0]   ra_x,
    input  wire          ra_vi,
    input  wire [31:0]   ra_ri,
    input  wire          ra_fi,
    // ve sub-leaf (Engram mix of this beat): reduce quads / add beats out, beat partials / results / fault back
    output reg           ve_rv,
    output reg  [1:0]    ve_rc,
    output reg  [127:0]  ve_rh,
    output reg  [127:0]  ve_rk,
    output reg  [127:0]  ve_rw,
    input  wire          ve_pv,
    input  wire [1:0]    ve_pc,
    input  wire [31:0]   ve_phh,
    input  wire [31:0]   ve_pkk,
    input  wire [31:0]   ve_pdd,
    output reg           ve_av,
    output reg  [1:0]    ve_ac,
    output reg  [255:0]  ve_ah,
    output reg  [255:0]  ve_aval,
    output reg  [31:0]   ve_ag,
    input  wire          ve_ov,
    input  wire [1:0]    ve_oc,
    input  wire [255:0]  ve_oy,
    input  wire          ve_fi,
    // Engram beat partials to the slice centre ({dd, kk, hh}) and gates from it
    output reg           e_v,
    output reg  [1:0]    e_c,
    output reg  [95:0]   e_d,
    input  wire          g_v,
    input  wire [1:0]    g_c,
    input  wire [31:0]   g_d,
    output reg           fault
);
    localparam [3:0] OP_SW = 4'd8, OP_QB = 4'd9, OP_RA = 4'd10, OP_RB = 4'd11, OP_QR = 4'd12, OP_MOE = 4'd13, OP_ENG = 4'd14;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_r = rsv[1], rs_x = rsv[2], rs_o = rsv[3];
    integer i, k, e2;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction

    // ---------------------------------------------------------------- input pin flops
    reg sv_c, xqv_c, rav_c, raf_c, swv_c, swf_c; reg [159:0] sd_c; reg [255:0] xq_c; reg [31:0] rar_c; reg [63:0] swr_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin sv_c <= 1'b0; xqv_c <= 1'b0; rav_c <= 1'b0; raf_c <= 1'b0; swv_c <= 1'b0; swf_c <= 1'b0; end
        else begin sv_c <= s_v; xqv_c <= x_qv; rav_c <= ra_vi; raf_c <= ra_fi; swv_c <= sw_vi; swf_c <= sw_fi; end
    always @(posedge clk) begin sd_c <= s_d; xq_c <= x_qd; rar_c <= ra_ri; swr_c <= sw_ri; end
    reg vpv_c, vov_c, vef_c, gv_c; reg [1:0] vpc_c, voc_c, gc_c; reg [95:0] vpd_c; reg [255:0] voy_c; reg [31:0] gd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin vpv_c <= 1'b0; vov_c <= 1'b0; vef_c <= 1'b0; gv_c <= 1'b0; end
        else begin vpv_c <= ve_pv; vov_c <= ve_ov; vef_c <= ve_fi; gv_c <= g_v; end
    always @(posedge clk) begin
        vpc_c <= ve_pc; vpd_c <= {ve_pdd, ve_pkk, ve_phh}; voc_c <= ve_oc; voy_c <= ve_oy; gc_c <= g_c; gd_c <= g_d;
    end

    // ---------------------------------------------------------------- command register and checks
    wire [3:0] c_op = sd_c[3:0]; wire [9:0] c_a0 = sd_c[13:4]; wire [7:0] c_n = sd_c[31:24]; wire [127:0] c_imm = sd_c[159:32];
    wire [2:0] c_j0 = c_imm[24:22];
    wire [9:0] c_a1 = sd_c[23:14]; wire c_ph = c_imm[30];
    reg  [3:0] gmask;                                                     // ENG gates latched (copy mask)
    wire [7:0] c_nsb = (c_op == OP_QB) ? c_n : {1'b0, c_n[7:1]};          // vq sub-beats of a streaming op
    wire c_uq = c_imm[11] || c_op == OP_QB;
    wire c_bad = (c_op != OP_SW && c_op != OP_QB && c_op != OP_RA && c_op != OP_RB && c_op != OP_QR && c_op != OP_MOE &&
                  c_op != OP_ENG) ||
                 (c_op == OP_ENG && (c_ph ? (c_n != 8'd32 || gmask != 4'hF) : c_n != 8'd64)) ||
                 (c_n == 8'd0) || (c_op == OP_SW && c_n > 8'd16) || (c_op == OP_MOE && c_n != 8'd8) ||
                 (c_uq && (c_op == OP_SW || c_op == OP_QB) && ((c_op == OP_SW && c_n[0]) || ({5'd0, c_j0} + c_nsb) > 8'd8));
    reg busy, done; reg [3:0] op; reg [9:0] a0, a1, ob; reg [7:0] n; reg wb, uq, ph, wr; reg [2:0] j0, wsel; reg [31:0] lim, w0, w1;
    wire c_wr = c_op == OP_SW && c_imm[25];
    wire acc_cmd = sv_c && !busy && !c_bad;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin busy <= 1'b0; op <= 4'd0; end
        else if (acc_cmd) begin busy <= 1'b1; op <= c_op; end
        else if (done) busy <= 1'b0;
    always @(posedge clk)
        if (acc_cmd) begin
            a0 <= c_a0; a1 <= c_a1; ph <= c_ph; n <= c_n; ob <= c_imm[9:0]; wb <= c_imm[10]; uq <= c_uq; j0 <= c_j0;
            lim <= c_imm[63:32]; wr <= c_wr; wsel <= c_imm[28:26];
        end
    // SW weights: from the immediate, or (wr) from word wsel of the row pair a1 = the op's first arrival
    wire w_arr;
    always @(posedge clk)
        if (acc_cmd) begin w0 <= c_imm[95:64]; w1 <= c_imm[127:96]; end
        else if (w_arr) begin
            w0 <= xq_c[32 * wsel +: 32]; w1 <= (MUT == 9) ? xq_c[32 * (wsel ^ 3'd1) +: 32] : xq_c[32 * wsel +: 32];
        end

    // ---------------------------------------------------------------- read issue (fixed cadence per op)
    //   QB / RB: one pair a cycle;  QR: every 2 cycles;  SW: every 4 cycles (the lane takes a group in 4);
    //   RA: every 8 cycles (8 elements);  MOE: 56 pairs, one a cycle, step 8 e + c at a0 + 16 e + 2 c
    reg rrun; reg [8:0] rs, rn; reg [2:0] cad;       // read step, last step, cadence mask (step & cad == 0 issues)
    wire [8:0] c_nr = (c_op == OP_RA) ? {4'd0, c_n[7:3]} + {8'd0, |c_n[2:0]} : {1'b0, c_n};   // reads
    always @(posedge clk or negedge rs_r)
        if (!rs_r) begin rrun <= 1'b0; rs <= 9'd0; rn <= 9'd0; cad <= 3'd0; x_rv <= 1'b0; end
        else begin
            x_rv <= 1'b0;
            if (acc_cmd) begin
                rrun <= 1'b1; rs <= 9'd0;
                cad <= (c_op == OP_RA) ? 3'd7 : (c_op == OP_SW) ? 3'd3 : (c_op == OP_QR) ? 3'd1 : 3'd0;
                rn  <= (c_op == OP_ENG) ? (c_ph ? 9'd31 : 9'd79) : (c_op == OP_MOE) ? 9'd55 : (c_op == OP_RA) ? {c_nr[5:0], 3'd0} - 9'd8 :
                       (c_op == OP_SW) ? {c_nr[6:0], 2'd0} - (c_wr ? 9'd0 : 9'd4) : (c_op == OP_QR) ? {c_nr[7:0], 1'b0} - 9'd2 : c_nr - 9'd1;
            end else if (rrun) begin
                rs <= rs + 9'd1;
                if (rs == rn) rrun <= 1'b0;
                x_rv <= (rs[2:0] & cad) == 3'd0;
            end
        end
    wire [8:0] rs_e = rs - 9'd16;                    // ENG REDUCE K / W read r: copy r[6:4], pair r[3:1], W when r[0]
    always @(posedge clk)
        case (op)
            OP_MOE: x_ra <= a0 + {3'd0, rs[5:3], 4'd0} + {6'd0, rs[2:0], 1'b0};
            OP_RA:  x_ra <= a0 + {2'd0, rs[8:3], 1'b0};
            OP_SW:  x_ra <= (wr && rs == 9'd0) ? a1 : a0 + {1'b0, rs[8:2] - {6'd0, wr}, 1'b0};
            OP_QR:  x_ra <= a0 + {rs[8:1], 1'b0};
            OP_ENG: x_ra <= ph ? a0 + 10'd128 + {6'd0, rs[2:0], 1'b0} :
                           (rs < 9'd16) ? a0 + {rs[8:0], 1'b0} :
                           a1 + {3'd0, rs_e[0], 6'd0} + {3'd0, rs_e[6:4], 4'd0} + {6'd0, rs_e[3:1], 1'b0};
            default: x_ra <= a0 + {rs[8:0], 1'b0};
        endcase

    // arrivals: the k-th read's row pair is at xq_c in arrival k (x_qv marks it, a fixed number of edges after x_rv)
    wire arr = xqv_c && busy;
    wire [31:0] xw [0:7];
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_xw
        assign xw[gl] = xq_c[32 * gl +: 32];
    end endgenerate
    reg [7:0] ka;                                    // arrivals of the running op
    always @(posedge clk or negedge rs_c)
        if (!rs_c) ka <= 8'd0;
        else if (acc_cmd) ka <= 8'd0;
        else if (arr) ka <= ka + 8'd1;
    // ENG stash-read index replicas (gate high_fanout: one 16 x 256-b stash read select drove 4,100 loads): 4 identical
    // copies of the arrival and flush counters, one per 64-b column group of the stash (keep: not merged by synthesis)
    (* keep = "true" *) reg [7:0] ka_q [0:3];
    (* keep = "true" *) reg [3:0] fl_q [0:3];
    (* keep = "true" *) reg [3:0] eqp_q [0:3];
    (* keep = "true" *) reg       ep_q [0:3];
    integer rq;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) for (rq = 0; rq < 4; rq = rq + 1) ka_q[rq] <= 8'd0;
        else for (rq = 0; rq < 4; rq = rq + 1)
            if (acc_cmd) ka_q[rq] <= 8'd0; else if (arr) ka_q[rq] <= ka_q[rq] + 8'd1;

    // ================================================================ SW: groups to the lane sub-leaf
    assign w_arr = arr && op == OP_SW && wr && ka == 8'd0;
    wire [7:0] kg = ka - {7'd0, wr};                 // SW group index of this arrival (wr: arrival 0 = the weight row)
    always @(posedge clk or negedge rs_r) if (!rs_r) sw_v <= 1'b0; else sw_v <= arr && op == OP_SW && !w_arr;
    always @(posedge clk) begin
        sw_d <= xq_c; sw_lim <= lim;
        sw_w <= (MUT == 1) ? 32'h3F800000 : (kg >= 8'd8 ? w1 : w0);
    end

    // ================================================================ X lanes: 8 x ot_dsrom_qadd, 4 x ot_hdc_qmul_lat
    // QR: a read carries 2 rotation pairs; pair 0 (q0, q1; c, s at words 4, 5) issues on arrival, pair 1 (q2, q3; c', s'
    // at words 6, 7) one cycle later from a stash.  QR lane l (0, 1): mine = q[l], pair = q[l ^ 1]; muls 2 l (mine * c),
    // 2 l + 1 (pair * (l ? s : -s)); its adder sums them (the hub rxqr lane: ODD lanes add b c + a s).
    wire qr_a = arr && op == OP_QR;
    reg  qr_b; reg [127:0] qr_st;                  // pair 1 stash {s', c', q3, q2}
    always @(posedge clk or negedge rs_x) if (!rs_x) qr_b <= 1'b0; else qr_b <= qr_a;
    always @(posedge clk) if (qr_a) qr_st <= {xw[7], xw[6], xw[3], xw[2]};
    wire [31:0] qm0 = qr_b ? qr_st[31:0] : xw[0], qm1 = qr_b ? qr_st[63:32] : xw[1];
    wire [31:0] qc  = qr_b ? qr_st[95:64] : xw[4], qs = qr_b ? qr_st[127:96] : xw[5];
    wire qr_in = qr_a || qr_b;
    wire [31:0] mp [0:3]; wire [3:0] mf; wire [XL:0] vmq;
    ot_hdc_vline #(.D(XL)) u_vmq (.clk(clk), .rst_n(rs_x), .v(qr_in), .vd(vmq));
    generate for (gl = 0; gl < 2; gl = gl + 1) begin : g_qm
        wire [31:0] mine = gl ? qm1 : qm0, pair = gl ? qm0 : qm1;
        wire [31:0] sg = ((gl != 0) ^ (MUT == 3)) ? qs : {~qs[31], qs[30:0]};
        ot_hdc_qmul_lat #(XL) u_p (clk, rs_x, qr_in, mine, qc, mp[2 * gl], mf[2 * gl]);
        ot_hdc_qmul_lat #(XL) u_q (clk, rs_x, qr_in, pair, sg, mp[2 * gl + 1], mf[2 * gl + 1]);
    end endgenerate
    // adder operand registers (one stage after the source mux): RB lanes 0..3, QR lanes 0..1, MOE lanes 0..7
    wire moe_in = arr && op == OP_MOE;
    wire [2:0] moe_e = ka[5:3];                      // expert of this arrival (8 e + c)
    reg  [31:0] xa [0:7], xb [0:7]; reg x_iv;
    wire [31:0] ay [0:7]; wire [7:0] af; wire [XL:0] vx;
    reg  [31:0] acc1 [0:7];
    // (MUT 4 rounds every partial to BF16, the hub moe leaf's EARLY_BF16 control; an expert-order reversal is NOT
    // visible on the 1M token's moe_sum rows: its FP32 differences vanish under the final BF16 rounding)
    always @(posedge clk or negedge rs_x)
        if (!rs_x) x_iv <= 1'b0;
        else x_iv <= (arr && op == OP_RB) || vmq[XL] || moe_in;
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1)
            if (op == OP_RB) begin
                xa[i] <= xw[i & 3]; xb[i] <= (MUT == 2) ? 32'd0 : xw[4 + (i & 3)];
            end else if (op == OP_QR) begin
                xa[i] <= mp[2 * (i & 1)]; xb[i] <= mp[2 * (i & 1) + 1];
            end else begin
                xa[i] <= (moe_e == 3'd0) ? xw[i] : (MUT == 4) ? bf16(acc1[i]) : acc1[i];
                xb[i] <= (moe_e == 3'd0) ? 32'h80000000 : xw[i];
            end
    ot_hdc_vline #(.D(XL)) u_vx (.clk(clk), .rst_n(rs_x), .v(x_iv), .vd(vx));
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_xa
        ot_dsrom_qadd #(.LAT(XL)) u_a (clk, rs_x, x_iv, xa[gl], xb[gl], ay[gl], af[gl]);
    end endgenerate
    // adder results: MOE phases 0..5 loop back (acc1 -> operand register: 8 cycles a turn), phase 6 / RB / QR leave
    reg [7:0] k_xo;
    always @(posedge clk or negedge rs_x)
        if (!rs_x) k_xo <= 8'd0;
        else if (acc_cmd) k_xo <= 8'd0;
        else if (vx[XL]) k_xo <= k_xo + 8'd1;
    always @(posedge clk) for (i = 0; i < 8; i = i + 1) acc1[i] <= ay[i];
    reg xo_v; reg [255:0] xo_d; reg [127:0] qr_h;  // QR: pair 0's two results wait for pair 1's
    always @(posedge clk or negedge rs_x)
        if (!rs_x) xo_v <= 1'b0;
        else xo_v <= vx[XL] && (op == OP_RB || (op == OP_QR && k_xo[0]) || (op == OP_MOE && k_xo >= 8'd48));
    always @(posedge clk) begin
        if (vx[XL] && op == OP_QR && !k_xo[0]) qr_h <= {64'd0, bf16(ay[1]), bf16(ay[0])};
        for (i = 0; i < 8; i = i + 1) xo_d[32 * i +: 32] <= (op == OP_RB) ? ay[i] : bf16(ay[i]);
        if (op == OP_QR) xo_d[127:0] <= {bf16(ay[1]), bf16(ay[0]), qr_h[63:0]};
    end

    // ================================================================ RA: serialise to the lane pair, collect rows
    reg [223:0] ras; reg [3:0] rasn; reg [7:0] ra_left;
    wire ra_ld = arr && op == OP_RA;
    wire ra_go = (rasn != 4'd0 || ra_ld) && ra_left != 8'd0;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin ra_v <= 1'b0; rasn <= 4'd0; ra_left <= 8'd0; end
        else begin
            if (acc_cmd) ra_left <= (c_op == OP_RA) ? c_n : 8'd0;
            else if (ra_go) ra_left <= ra_left - 8'd1;
            rasn <= ra_ld ? 4'd7 : (rasn != 4'd0) ? rasn - 4'd1 : 4'd0;
            ra_v <= ra_go;
        end
    always @(posedge clk) begin
        if (ra_ld) begin ras <= xq_c[255:32]; ra_x <= xq_c[31:0]; end
        else begin ras <= {32'd0, ras[223:32]}; ra_x <= ras[31:0]; end
    end
    reg [7:0] k_ra; reg [95:0] rad;                // results returned; the row being assembled (words 0..2)
    always @(posedge clk or negedge rs_o)
        if (!rs_o) k_ra <= 8'd0;
        else if (acc_cmd) k_ra <= 8'd0;
        else if (rav_c) k_ra <= k_ra + 8'd1;
    always @(posedge clk) if (rav_c) for (i = 0; i < 3; i = i + 1) if (k_ra[1:0] == i) rad[32 * i +: 32] <= rar_c;
    wire ra_row = rav_c && op == OP_RA && (k_ra[1:0] == 2'd3 || k_ra + 8'd1 == n);

    // ================================================================ ENG: h stash, ve feeder, gate latch, write-back
    reg [255:0] hst [0:15];                          // the beat's h half rows (vn layout), updated in place by ADD
    reg [2:0] kp_e; reg [5:0] ko_e; reg [4:0] fl_e; reg fl_on;
    reg [31:0]  gate [0:3];
    wire eng_r = arr && op == OP_ENG && !ph, eng_a = arr && op == OP_ENG && ph;
    wire [7:0] er = ka - 8'd16;                      // REDUCE K / W arrival r (16 .. 79): K pair even r, W pair odd r
    reg  [255:0] kst; reg [127:0] wst; reg epend;    // K pair stash, W upper half, second quad pending
    wire [5:0] eq0 = {er[6:4], er[3:1], 1'b0}; reg [5:0] eqp;
    wire [5:0] eq = epend ? eqp : eq0;              // quad 16 j + i (W arrival: even quad; next cycle: odd)
    reg [255:0] hrow, hra, hrb, xwsel; reg [31:0] gsel;
    always @(*) begin
        for (rq = 0; rq < 4; rq = rq + 1) begin
            hrow[64 * rq +: 64] = hst[ep_q[rq] ? eqp_q[rq] : {ka_q[rq][3:1], 1'b0}][64 * rq +: 64];
            hra[64 * rq +: 64] = hst[{ka_q[rq][2:0], 1'b0}][64 * rq +: 64];
            hrb[64 * rq +: 64] = hst[{ka_q[rq][2:0], 1'b1}][64 * rq +: 64];
            xwsel[64 * rq +: 64] = hst[fl_q[rq]][64 * rq +: 64];
        end
        gsel = gate[(MUT == 7) ? ka[4:3] ^ 2'd1 : ka[4:3]];
    end
    function automatic [31:0] hw32(input [255:0] r, input [1:0] j, input [1:0] e);
        hw32 = {r[(4 * j + e) * 16 +: 16], 16'd0};
    endfunction
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin ve_rv <= 1'b0; ve_av <= 1'b0; gmask <= 4'd0; epend <= 1'b0;
                         for (rq = 0; rq < 4; rq = rq + 1) ep_q[rq] <= 1'b0; end
        else begin
            ve_rv <= (eng_r && ka >= 8'd16 && er[0]) || epend;
            epend <= eng_r && ka >= 8'd16 && er[0];
            for (rq = 0; rq < 4; rq = rq + 1) ep_q[rq] <= eng_r && ka >= 8'd16 && er[0];
            ve_av <= eng_a;
            if (acc_cmd && c_op == OP_ENG && !c_ph) gmask <= 4'd0;
            else if (gv_c) gmask <= gmask | (4'd1 << gc_c);
        end
    always @(posedge clk) begin
        if (gv_c) gate[gc_c] <= gd_c;
        // REDUCE: arrivals 0..15 = h half rows into the stash; 16..79 = K / W of quad q -> ve
        if (eng_r && ka < 8'd16) hst[ka[3:0]] <= xq_c;
        ve_rc <= eq[5:4];
        for (i = 0; i < 4; i = i + 1) ve_rh[32 * i +: 32] <= hw32(hrow, eq[5:4], i[1:0]);
        if (eng_r && ka >= 8'd16 && !er[0]) kst <= xq_c;
        if (eng_r && ka >= 8'd16 && er[0]) wst <= xq_c[255:128];
        eqp <= eq0 | 6'd1;
        for (rq = 0; rq < 4; rq = rq + 1) eqp_q[rq] <= {ka_q[rq][3:1], 1'b1};
        ve_rk <= epend ? kst[255:128] : kst[127:0];
        ve_rw <= (MUT == 8) ? (epend ? kst[255:128] : kst[127:0]) : (epend ? wst : xq_c[127:0]);
        // ADD: arrival s (copy j = ka[4:3], elements 8 s' .. 8 s' + 7, s' = ka[2:0]) = V row pair; h from half rows 2 s', 2 s' + 1
        ve_ac <= ka[4:3];
        for (i = 0; i < 4; i = i + 1) begin
            ve_ah[32 * i +: 32] <= hw32(hra, ka[4:3], i[1:0]); ve_ah[32 * (i + 4) +: 32] <= hw32(hrb, ka[4:3], i[1:0]);
        end
        ve_aval <= xq_c;
        ve_ag <= gsel;
        // ADD results: copy j's slots of half rows 2 s, 2 s + 1
        // (decoded constant-index slices: one-hot row pair x copy, no runtime part-select)
        if (vov_c && op == OP_ENG && ph)
            for (i = 0; i < 16; i = i + 1)
                for (k = 0; k < 4; k = k + 1)
                    if ((i >> 1) == ko_e[2:0] && k == voc_c)
                        for (e2 = 0; e2 < 4; e2 = e2 + 1)
                            hst[i][(4 * k + e2) * 16 +: 16] <= voy_c[32 * (4 * (i & 1) + e2) + 16 +: 16];
    end
    // partial triples out; result / flush counters
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin e_v <= 1'b0; kp_e <= 3'd0; ko_e <= 6'd0; fl_e <= 5'd0; fl_on <= 1'b0;
                         for (rq = 0; rq < 4; rq = rq + 1) fl_q[rq] <= 4'd0; end
        else begin
            e_v <= vpv_c;
            if (acc_cmd) begin kp_e <= 3'd0; ko_e <= 6'd0; fl_e <= 5'd0; fl_on <= 1'b0;
                               for (rq = 0; rq < 4; rq = rq + 1) fl_q[rq] <= 4'd0; end
            else begin
                if (vpv_c) kp_e <= kp_e + 3'd1;
                if (vov_c) begin ko_e <= ko_e + 6'd1; if (ko_e == 6'd31) fl_on <= 1'b1; end
                if (fl_on) begin fl_e <= fl_e + 5'd1; if (fl_e == 5'd15) fl_on <= 1'b0; end
                if (fl_on) for (rq = 0; rq < 4; rq = rq + 1) fl_q[rq] <= fl_q[rq] + 4'd1;
            end
        end
    always @(posedge clk) begin e_c <= vpc_c; e_d <= vpd_c; end

    // ================================================================ results: leaf-store write port, vq stream, done
    reg [7:0] k_out; reg [127:0] sw_prev;
    wire [127:0] sw_w32 = {swr_c[63:48], 16'd0, swr_c[47:32], 16'd0, swr_c[31:16], 16'd0, swr_c[15:0], 16'd0};
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin x_wv <= 1'b0; u_v <= 1'b0; um_v <= 1'b0; k_out <= 8'd0; done <= 1'b0; end
        else begin
            x_wv <= 1'b0; u_v <= 1'b0; done <= 1'b0;
            um_v <= acc_cmd && c_uq && (c_op == OP_SW || c_op == OP_QB);
            if (acc_cmd) k_out <= 8'd0;
            else if (busy && !done) case (op)
                OP_SW: if (swv_c) begin
                    x_wv <= wb; u_v <= uq && k_out[0]; k_out <= k_out + 8'd1;
                    if (k_out + 8'd1 == n) done <= 1'b1;
                end
                OP_QB: if (arr) begin
                    u_v <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_out + 8'd1 == n) done <= 1'b1;
                end
                OP_RA: if (ra_row) begin
                    x_wv <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_ra + 8'd1 == n) done <= 1'b1;
                end
                OP_RB, OP_QR: if (xo_v) begin
                    x_wv <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_out + 8'd1 == n) done <= 1'b1;
                end
                OP_MOE: if (xo_v) begin
                    x_wv <= 1'b1; k_out <= k_out + 8'd1;
                    if (k_out == 8'd7) done <= 1'b1;
                end
                OP_ENG: if (!ph) begin
                    if (vpv_c && kp_e == 3'd3) done <= 1'b1;
                end else if (fl_on) begin
                    x_wv <= 1'b1;
                    if (fl_e == 5'd15) done <= 1'b1;
                end
                default: ;
            endcase
        end
    always @(posedge clk) begin
        if (acc_cmd) begin um_q <= c_imm[12]; um_b <= c_imm[13]; um_i <= c_imm[21:14]; end
        if (swv_c) sw_prev <= sw_w32;
        case (op)
            OP_SW: begin
                x_wa <= ob + {2'd0, k_out[7:0]}; x_wm <= 8'h0F; x_wd <= {128'd0, sw_w32};
                u <= {sw_w32, sw_prev}; u_i <= j0 + k_out[3:1];
            end
            OP_QB: begin
                u <= (MUT == 5) ? {xq_c[127:0], xq_c[255:128]} : xq_c; u_i <= j0 + k_out[2:0];
            end
            OP_RA: begin
                x_wa <= ob + {4'd0, k_ra[7:2]} + ((MUT == 6) ? 10'd1 : 10'd0);
                x_wm <= (k_ra[1:0] == 2'd3) ? 8'h0F : (k_ra[1:0] == 2'd2) ? 8'h07 : (k_ra[1:0] == 2'd1) ? 8'h03 : 8'h01;
                x_wd <= {128'd0, rar_c, rad};
                for (i = 0; i < 3; i = i + 1) if (k_ra[1:0] == i) x_wd[32 * i +: 32] <= rar_c;
            end
            OP_RB, OP_QR: begin x_wa <= ob + {2'd0, k_out[7:0]}; x_wm <= 8'h0F; x_wd <= {128'd0, xo_d[127:0]}; end
            OP_ENG: begin x_wa <= a1 + {4'd0, fl_e[4:0], 1'b0}; x_wm <= 8'hFF; x_wd <= xwsel; end
            default: begin x_wa <= ob + {1'b0, k_out[7:0], 1'b0}; x_wm <= 8'hFF; x_wd <= xo_d; end   // MOE
        endcase
    end

    // ---------------------------------------------------------------- faults (sticky)
    reg f_cmd, f_unit;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin fault <= 1'b0; f_cmd <= 1'b0; f_unit <= 1'b0; end
        else begin
            f_cmd <= (sv_c && (busy || c_bad)) || (xqv_c && !busy) || (swv_c && op != OP_SW) || (rav_c && op != OP_RA) ||
                     (vpv_c && !(busy && op == OP_ENG && !ph)) || (vov_c && !(busy && op == OP_ENG && ph)) ||
                     (vov_c && voc_c != ko_e[4:3]) || (gv_c && gmask[gc_c]);
            f_unit <= (|mf) | (|af) | raf_c | swf_c | vef_c;
            fault <= fault | f_cmd | f_unit;
        end
endmodule

