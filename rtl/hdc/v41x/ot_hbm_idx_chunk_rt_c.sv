`timescale 1ns/1ps
`default_nettype none
// IDX-SCORE leaf core, COLUMN SPLIT + native32 (HBM-IDX6 2026-10-20): structural successor of ot_hbm_idx_chunk_rt_l
// (same ports minus clk_pair, cycle-exact vs ot_hbm_idx_chunk_owned_native through tb_idx_chunk_rt_equiv -DOT_CHUNK_RT_C).
// Why: leaf_c1 (one root, chunk_rt_l) died in CTS (rc137, 189,723 flops on one root > the 110k refuse line) and its
// actual-Liberty native32 census FAILs 13,574 drivers (max 1,120): query store qc 41 loads (FP4 product table),
// key_p 360, ring-buffer wptr 1,030 / 411, q_we 1,120, region reset copies 432, adder internals u_ca/u_cd 167/72,
// bmul cuts 40, glue valid-line relay copies 40.
// Structure (top-down hierarchy contract: replicated elements hardened once):
//   ot_hbm_idx_chunk_rt_c = wires-only: ot_hidx_chunk_glue + 4 x ot_hidx_score_col (non-parameterised, one key column,
//   8 heads = 4 head-pair regions, ~47k flops: under the 110k refuse line, its own CTS root as a hard child).
//   The only glue <-> column nets: query broadcast {qv_b, q_b} (569 b), the column's key slice (544 b), head ids (64 b),
//   the column reset (1 b) in; running sum (32 b) + fault (1 b) + 4 region online bits out.  Columns never talk to each
//   other.  The glue's SUM_PAD / ONL_PAD / VL_EXTRA parameters (default 0 = this file's cycle-exact timing) are the
//   reference-schedule knobs for a LANDED leaf (tools/landed_parent/lp.py schedule "reference": +E+1 = 3 edges per
//   landed crossing -> VL_EXTRA 6 / SUM_PAD 0 in the landed leaf, VL_EXTRA 6 / SUM_PAD 6 / ONL_PAD 3 in its flat reference).
// native32 changes (each cycle-neutral):
//   * delays >= 3 deep: ot_hdc_delay_rf32 (one-hot self-correcting ring, kept write/read select copies per 16 data bits,
//     kept input copies per 24 rows) instead of the binary-pointer ot_hdc_delay_rf;
//   * query store write enable: 40 kept q_we copies, one per 14-bit slice (was one flop -> 560 enables);
//   * FP4 x FP4 dot: ot_hdc_v41x_q4dot_n (same value; product from 2-bit mantissas and a shift, not a 7-input table);
//   * head weight product: ot_hdc_v41x_bmul_n (same value; kept copies of the shift / select registers);
//   * binary32 adds: ot_hdc_fp32_add_lat_fan32 LAT 7 / DRST 0 (main 520dbea3a: SAFE_DIST 1 native graph in synthesis,
//     its proved-equivalent DRST 0 RTL in simulation); data stages unreset (only the valid chain resets, unused here);
//   * glue valid line in segments of 4 stages per relay copy (<= 20 clears), online / rdy clears on separate copies.
`ifndef OT_IDX_FAN32_SAFE
`ifdef SYNTHESIS
`define OT_IDX_FAN32_SAFE 1
`else
`define OT_IDX_FAN32_SAFE 0
`endif
`endif

// q = d delayed by exactly D edges (cycle-exact vs ot_hdc_delay #(W, D, RESET 0)); no reset.  D >= 3: input register
// copies -> N = D - 2 rows written through a one-hot select -> AND-OR read -> output register.  The master one-hot ring is
// self-correcting (bit 0 <- NOR of bits 0..N-2): any power-up state converges to one-hot within N edges, before the line
// has filled (as ot_hdc_delay_rf's binary pointer); every select copy is registered from the master's next state, so all
// copies equal the master from the first edge on.  Each select-copy bit drives <= 10 data bits (~2.2 mapped loads a bit), each input copy <= 24 rows.
module ot_hdc_delay_rf32 #(
    parameter integer W = 32,
    parameter integer D = 3
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D < 3) begin : g_sh
            ot_hdc_delay #(.W(W), .D(D)) u (.clk(clk), .rst_n(1'b1), .d(d), .q(q));
        end else begin : g_ring
            localparam integer N = D - 2;
            localparam integer GW = 10;                       // data bits per select copy
            localparam integer NG = (W + GW - 1) / GW;
            localparam integer RW = 24;                       // rows per input copy
            localparam integer NC = (N + RW - 1) / RW;
            reg [N-1:0] m;
            wire [N-1:0] mn;
            if (N == 1) begin : g_n1
                assign mn = 1'b1;
            end else begin : g_nn
                assign mn = {m[N-2:0], ~|m[N-2:0]};
            end
            always @(posedge clk) m <= mn;
            reg [W-1:0] dout;
            wire [W-1:0] rd;
            genvar c, k, r;
            wire [W-1:0] din [0:NC-1];
            for (c = 0; c < NC; c = c + 1) begin : g_in
                (* keep *) reg [W-1:0] di;
                always @(posedge clk) di <= d;
                assign din[c] = di;
            end
            for (k = 0; k < NG; k = k + 1) begin : g_grp
                localparam integer LO = k * GW;
                localparam integer HI = (LO + GW > W) ? W : LO + GW;
                (* keep *) reg [N-1:0] ws;
                (* keep *) reg [N-1:0] rs;
                always @(posedge clk) begin ws <= mn; rs <= mn; end
                wire [HI-LO-1:0] orv [0:N];
                assign orv[0] = {(HI-LO){1'b0}};
                for (r = 0; r < N; r = r + 1) begin : g_row
                    reg [HI-LO-1:0] row;
                    always @(posedge clk) if (ws[r]) row <= din[r / RW][HI-1:LO];
                    assign orv[r + 1] = orv[r] | (row & {(HI-LO){rs[r]}});
                end
                assign rd[HI-1:LO] = orv[N];
            end
            always @(posedge clk) dout <= rd;
            assign q = dout;
        end
    endgenerate
endmodule

// Registered shifter with KEPT copies (native32): NS data copies of the d register, each with NH copies of the sh register;
// copy pair (k, h) produces output sub-slice (k, h) of ({d, PAD zeros} >> sh) (LEFT 0) or (d << sh) (LEFT 1), OW bits.
// A barrel-shifter select bit fans out ~8-9x per output bit, so a sh copy steers <= 2 outputs.  Same value as one register
// + one shifter (every copy registers the same d / sh on the same edge).
module ot_hidx_ksh #(
    parameter integer W = 13, parameter integer SHW = 4, parameter integer OW = 27, parameter integer PAD = 14,
    parameter integer LEFT = 0, parameter integer NS = 4, parameter integer NH = 2
) (
    input  wire           clk,
    input  wire [W-1:0]   d,
    input  wire [SHW-1:0] sh,
    output wire [OW-1:0]  q
);
    localparam integer NT = NS * NH;
    localparam integer SL = (OW + NT - 1) / NT;
    genvar k, h;
    for (k = 0; k < NS; k = k + 1) begin : g_c
        (* keep *) reg [W-1:0] dk;
        always @(posedge clk) dk <= d;
        for (h = 0; h < NH; h = h + 1) begin : g_h
            localparam integer LO = (k * NH + h) * SL;
            localparam integer HI = (LO + SL > OW) ? OW : LO + SL;
            (* keep *) reg [SHW-1:0] sk;
            always @(posedge clk) sk <= sh;
            wire [OW-1:0] y;
            if (LEFT != 0) begin : g_l
                assign y = {{(OW > W ? OW - W : 1){1'b0}}, dk} << sk;
            end else begin : g_r
                assign y = {dk, {PAD{1'b0}}} >> sk;
            end
            if (LO < OW) begin : g_o
                assign q[HI-1:LO] = y[HI-1:LO];
            end
        end
    end
endmodule

// Exact FP4 x FP4 block dot (ot_hdc_v41x_q4dot_l, same value at every QL).  Only stage A's signed product changes form:
// dmag(m) = m < 2 ? m : (2 + m[0]) << (m[2:1] - 1), so dmag(a) * dmag(b) = (ma' * mb') << (sa + sb) with 2-bit mantissas
// ma' = {m[2:1] != 0, m[0]} and shifts s = max(m[2:1] - 1, 0); the same 9-bit two's-complement product, offset by 2^8.
module ot_hdc_v41x_q4dot_n #(
    parameter integer QL = 3
) (
    input  wire         clk,
    input  wire [127:0] a,
    input  wire [127:0] b,
    input  wire [7:0]   ua,
    input  wire [7:0]   ub,
    output reg  [31:0]  y,
    output reg          ovf
);
    function automatic [8:0] sprod_n(input sg, input [2:0] x, input [2:0] z);
        reg [1:0] mx, mz; reg [1:0] sx, sz; reg [3:0] mm; reg [7:0] pm;
        begin
            mx = {x[2:1] != 2'd0, x[0]}; mz = {z[2:1] != 2'd0, z[0]};
            sx = (x[2:1] == 2'd0) ? 2'd0 : x[2:1] - 2'd1; sz = (z[2:1] == 2'd0) ? 2'd0 : z[2:1] - 2'd1;
            mm = mx * mz;
            pm = {4'd0, mm} << ({1'b0, sx} + {1'b0, sz});
            sprod_n = (sg ? (9'd0 - {1'b0, pm}) : {1'b0, pm}) ^ 9'h100;
        end
    endfunction
    reg  [32*14-1:0] opa;
    integer i;
    always @* begin
        for (i = 0; i < 32; i = i + 1)
            opa[14*i +: 14] = {5'd0, sprod_n(a[4*i + 3] ^ b[4*i + 3], a[4*i +: 3], b[4*i +: 3])};
    end
    wire [7*14-1:0]  qa;
    ot_hdc_v41x_csa #(.N(32), .M(7), .W(14)) u_ca (.d(opa), .q(qa));
    wire signed [9:0] ea = $signed({2'b00, ua}) + $signed({2'b00, ub}) - 10'sd256;
    wire refa = (ua >= 8'd253) || (ub >= 8'd253);
    reg [7*14-1:0] ra;
    reg signed [9:0] rea;
    reg rrefa;
    always @(posedge clk) begin
        ra <= qa;
        rea <= ea;
        rrefa <= refa;
    end
    wire [2*14-1:0] qb0, qb;
    ot_hdc_v41x_csa #(.N(7), .M(2), .W(14)) u_cb (.d(ra), .q(qb0));
    wire signed [9:0] rea_b;
    wire rrefa_b;
    ot_hdc_delay #(.W(28 + 10 + 1), .D((QL >= 5) ? 1 : 0)) u_cutb (.clk(clk), .rst_n(1'b1),
        .d({qb0, rea, rrefa}), .q({qb, rea_b, rrefa_b}));
    wire [13:0] sb = (qb[13:0] + qb[27:14]) ^ 14'h2000;
    wire [12:0] mb = sb[13] ? (~sb[12:0] + 13'd1) : sb[12:0];
    wire signed [11:0] kb = $signed({{2{rea_b[9]}}, rea_b}) + 12'sd149;
    wire [11:0] nkb = -kb;
    reg         rsg, rkneg;
    reg  [12:0] rm;
    reg  [4:0]  rkl;
    reg  [3:0]  rkr;
    reg signed [11:0] rnl, rov;
    reg signed [9:0] reb;
    reg rrefb;
    // kept copies of the shift amounts / select (each steers one half of the shifted significand; native32)
    (* keep *) reg rkneg_b, rkneg_c;
    always @(posedge clk) begin
        rsg <= sb[13];
        rm <= mb;
        rkneg <= kb[11];
        rkl <= kb[4:0];
        rkr <= (nkb > 12'd14) ? 4'd14 : nkb[3:0];
        rkneg_b <= kb[11]; rkneg_c <= kb[11];
        rnl <= $signed({{2{rea_b[9]}}, rea_b}) + 12'sd138;
        rov <= $signed({{2{rea_b[9]}}, rea_b}) - 12'sd116;
        reb <= rea_b;
        rrefb <= rrefa_b;
    end
    reg  [3:0]  lz0;
    integer kq;
    always @* begin
        lz0 = 4'd13;
        for (kq = 0; kq < 13; kq = kq + 1) if (rm[kq]) lz0 = 4'd12 - kq[3:0];
    end
    wire [26:0]       xr;
    ot_hidx_ksh #(.W(13), .SHW(4), .OW(27), .PAD(14), .LEFT(0), .NS(4), .NH(4)) u_xr (.clk(clk), .d(mb),
        .sh((nkb > 12'd14) ? 4'd14 : nkb[3:0]), .q(xr));
    wire [12:0]       qt = xr[26:14];
    wire              g = xr[13], st = |xr[12:0];
    wire [23:0]       fr = {11'd0, qt} + ((g && (st || qt[0])) ? 24'd1 : 24'd0);
    wire [23:0]       fl;
    ot_hidx_ksh #(.W(13), .SHW(5), .OW(24), .PAD(1), .LEFT(1), .NS(3), .NH(4)) u_fl (.clk(clk), .d(mb), .sh(kb[4:0]), .q(fl));
    wire [23:0]       f0 = {rkneg_c ? fr[23:16] : fl[23:16], rkneg_b ? fr[15:8] : fl[15:8], rkneg ? fr[7:0] : fl[7:0]};
    wire [3:0]        lz;
    wire [12:0]       cm;
    wire [23:0]       f;
    wire signed [9:0] ceb;
    wire signed [11:0] cnl, cov;
    wire              csg, cref;
    ot_hdc_delay #(.W(4 + 13 + 24 + 10 + 12 + 12 + 2), .D((QL >= 4) ? 1 : 0)) u_cutc (.clk(clk), .rst_n(1'b1),
        .d({lz0, rm, f0, reb, rnl, rov, rsg, rrefb}), .q({lz, cm, f, ceb, cnl, cov, csg, cref}));
    wire [12:0]       mn = cm << lz;
    wire [7:0]        bef = ceb[7:0] + 8'd139 - {4'd0, lz};
    wire              nrm = $signed({8'd0, lz}) <= cnl;
    wire              ovc = (cm != 13'd0) && ($signed({8'd0, lz}) <= cov);
    reg  [31:0] yc;
    reg         oc;
    always @* begin
        oc = cref || ovc;
        if (cm == 13'd0 || oc) yc = 32'd0;
        else if (nrm) yc = {csg, bef, mn[11:0], 11'd0};
        else if (f == 24'd0) yc = 32'd0;
        else yc = {csg, 7'd0, f};
    end
    always @(posedge clk) begin
        y <= yc;
        ovf <= oc;
    end
endmodule

// term = to_bf16(mul(max(a, 0), w)) (ot_hdc_v41x_bmul_l, same value, ML 5 only).  The shift amounts and selects that
// fan out over the 16 / 24 / 33-bit significands are registered two or three times (kept copies), each copy steering
// one slice of the bits.
module ot_hdc_v41x_bmul_n (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] w,
    output reg  [15:0] y,
    output reg         ovf
);
    wire        az = a[15] || (a[14:0] == 15'd0);
    wire        wz = (w[14:0] == 15'd0);
    wire [7:0]  ma = {a[14:7] != 8'd0, a[6:0]};
    wire [7:0]  mw = {w[14:7] != 8'd0, w[6:0]};
    wire [8:0]  ea = (a[14:7] == 8'd0) ? 9'd1 : {1'b0, a[14:7]};
    wire [8:0]  ew = (w[14:7] == 8'd0) ? 9'd1 : {1'b0, w[14:7]};
    wire signed [11:0] e1 = $signed({3'b000, ea}) + $signed({3'b000, ew}) - 12'sd268;
    wire signed [11:0] k1 = e1 + 12'sd149;
    wire [11:0] nk1 = -k1;
    reg  [15:0] rp;
    reg  signed [11:0] re;
    reg         rs, rz, rkneg;
    reg  [4:0]  rkl, rkr;
    always @(posedge clk) begin
        rp <= ma * mw;
        re <= e1;
        rs <= w[15];
        rz <= az || wz;
        rkneg <= k1[11];
        rkl <= k1[4:0];
        rkr <= (nk1 > 12'd17) ? 5'd17 : nk1[4:0];
    end
    reg  [4:0]  lz0;
    integer kq;
    always @* begin
        lz0 = 5'd16;
        for (kq = 0; kq < 16; kq = kq + 1) if (rp[kq]) lz0 = 5'd15 - kq[4:0];
    end
    // cut 2 (ML 5): the bundle once, plus kept copies of the shift amounts for the upper halves
    reg  [4:0]  lz;  reg [15:0] p2; reg signed [11:0] e2; reg s2s, s2z, s2kneg; reg [4:0] s2kl, s2kr;
    
    always @(posedge clk) begin
        {lz, p2, e2, s2s, s2z, s2kneg, s2kl, s2kr} <= {lz0, rp, re, rs, rz, rkneg, rkl, rkr};
    end
    wire [15:0]        pn;
    ot_hidx_ksh #(.W(16), .SHW(5), .OW(16), .PAD(1), .LEFT(1), .NS(2), .NH(4)) u_pn (.clk(clk), .d(rp), .sh(lz0), .q(pn));
    wire signed [11:0] be = e2 + 12'sd142 - $signed({7'd0, lz});
    wire [32:0]        xr;
    ot_hidx_ksh #(.W(16), .SHW(5), .OW(33), .PAD(17), .LEFT(0), .NS(5), .NH(4)) u_xr (.clk(clk), .d(rp), .sh(rkr), .q(xr));
    wire [23:0]        fl;
    ot_hidx_ksh #(.W(16), .SHW(5), .OW(24), .PAD(1), .LEFT(1), .NS(3), .NH(4)) u_fl (.clk(clk), .d(rp), .sh(rkl), .q(fl));
    reg  [15:0] s_pn;
    reg  [7:0]  s_be;
    reg         s_nrm, s_o32, s_zero, s_sign, s_kneg;
    (* keep *) reg s_kneg_b, s_kneg_c;
    reg  [16:0] s_q;
    reg         s_g, s_st;
    reg  [23:0] s_fl;
    always @(posedge clk) begin
        s_pn <= pn;
        s_be <= be[7:0];
        s_nrm <= (be >= 12'sd1);
        s_o32 <= !s2z && (p2 != 16'd0) && (be >= 12'sd255);
        s_zero <= s2z || (p2 == 16'd0);
        s_sign <= s2s;
        s_kneg <= s2kneg;
        s_kneg_b <= s2kneg; s_kneg_c <= s2kneg;
        s_q <= xr[32:17];
        s_g <= xr[16];
        s_st <= |xr[15:0];
        s_fl <= fl;
    end
    wire [8:0]  nr = {1'b0, s_pn[15:8]} + ((s_pn[7] && ((|s_pn[6:0]) || s_pn[8])) ? 9'd1 : 9'd0);
    wire [8:0]  nbe = {1'b0, s_be} + {8'd0, nr[8]};
    wire [15:0] ynorm0 = {s_sign, nbe[7:0], nr[8] ? 7'd0 : nr[6:0]};
    wire        onorm0 = (nbe >= 9'd255);
    wire [23:0] fr = {7'd0, s_q} + ((s_g && (s_st || s_q[0])) ? 24'd1 : 24'd0);
    wire [23:0] f0 = {s_kneg_c ? fr[23:16] : s_fl[23:16], s_kneg_b ? fr[15:8] : s_fl[15:8], s_kneg ? fr[7:0] : s_fl[7:0]};
    // cut 3 (ML >= 4): the bundle, plus kept copies of the output selects
    reg [15:0] ynorm; reg onorm; reg [23:0] f; reg t_sign, t_zero, t_o32, t_nrm;
    (* keep *) reg t_zero_b; (* keep *) reg t_o32_b; (* keep *) reg t_nrm_b; (* keep *) reg onorm_b;
    always @(posedge clk) begin
        {ynorm, onorm, f, t_sign, t_zero, t_o32, t_nrm} <= {ynorm0, onorm0, f0, s_sign, s_zero, s_o32, s_nrm};
        t_zero_b <= s_zero; t_o32_b <= s_o32; t_nrm_b <= s_nrm; onorm_b <= onorm0;
    end
    wire [32:0] fb = {9'd0, f} + 33'h7FFF + {32'd0, f[16]};
    wire [15:0] ysub = (f == 24'd0) ? 16'd0 : {t_sign, fb[30:16]};
    wire        kill_a = t_zero || t_o32 || (t_nrm && onorm);
    wire        kill_b = t_zero_b || t_o32_b || (t_nrm_b && onorm_b);
    always @(posedge clk) begin
        ovf <= t_o32 || (!t_zero && t_nrm && onorm);
        y[7:0]  <= kill_a ? 8'd0 : (t_nrm ? ynorm[7:0] : ysub[7:0]);
        y[15:8] <= kill_b ? 8'd0 : (t_nrm_b ? ynorm[15:8] : ysub[15:8]);
    end
endmodule

// One KEY COLUMN of the leaf core (heads 0..7 of the chunk on one 544-bit key tile; ot_hbm_idx_chunk_rt_l g_col[g] with
// g as a port slice).  Non-parameterised: the hard child the leaf replicates 4x.  Inputs land in each head-pair region's
// pin registers (qv_p / q_p / key_p / hid_p), outputs launch from the head-7 sum register cs_o and the region online flops.
module ot_hidx_score_col (
    input  wire          clk,
    input  wire          rst_n,          // the glue's column relay copy (landed: reaches only the region synchronisers)
    input  wire          qv_b,
    input  wire [567:0]  q_b,
    input  wire [543:0]  key,
    input  wire [63:0]   hid,            // head ids, head h at [8h +: 8]
    output wire [31:0]   cs_out,
    output wire          cf_out,
    output wire [3:0]    prdy
);
    localparam integer NB = 4, FPL = 7, FML = 5, QL = 5, HC = 8;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    localparam integer SW = QW - 8;                     // stored query word (codes, scales, weight) = 560
    localparam integer QG = 14, NQG = SW / QG;          // 40 write-enable copies of 14 bits (~2 mapped loads a bit)
    wire [31:0] cs [0:HC]; wire cf [0:HC];
    genvar r, hh, bb, k;
    for (r = 0; r < 4; r = r + 1) begin : g_rgn
        localparam integer NRS = 1 + 2 * NB;
        wire [NRS-1:0] srr; wire rs = srr[0];
        ot_rst_relay_l #(.REGIONS(NRS), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(srr));
        reg rn_p, onl;
        always @(posedge clk) rn_p <= rs;
        always @(posedge clk or negedge rs) if (!rs) onl <= 1'b0; else onl <= rs && rn_p;
        assign prdy[r] = onl;
        // region pin registers, kept per region (equal D across the 4 regions: opt_merge would fold them into one)
        (* keep *) reg qv_p; (* keep *) reg [QW-1:0] q_p; (* keep *) reg [KW-1:0] key_p;
        always @(posedge clk) begin qv_p <= qv_b && rn_p; q_p <= q_b; key_p <= key; end
        wire [7:0] qh_p = q_p[QW-1 -: 8];
        for (hh = 0; hh < 2; hh = hh + 1) begin : g_h
            localparam integer H = 2 * r + hh;
            // two kept head-id copies: each compare feeds 20 of the 40 enable copies (one compare -> 40 loads otherwise)
            (* keep *) reg [7:0] hid_pa; (* keep *) reg [7:0] hid_pb;
            always @(posedge clk) begin hid_pa <= hid[8*H +: 8]; hid_pb <= hid[8*H +: 8]; end
            // ---- (a) query store: own head written one edge after the compare; 40 kept enable copies
            wire q_eqa = qv_p && rn_p && (qh_p == hid_pa);
            wire q_eqb = qv_p && rn_p && (qh_p == hid_pb);
            reg [SW-1:0] q2; reg [SW-1:0] qst;
            always @(posedge clk) q2 <= q_p[QW-9:0];
            for (k = 0; k < NQG; k = k + 1) begin : g_we
                (* keep *) reg we;
                always @(posedge clk) we <= (k < NQG / 2) ? q_eqa : q_eqb;
                always @(posedge clk) if (we) qst[k*QG +: QG] <= q2[k*QG +: QG];
            end
            wire [NB*128-1:0] qc = qst[SW-1 -: NB*128];
            wire [NB*8-1:0]   qs = qst[47:16];
            wire [15:0]       qw = qst[15:0];
            // ---- (c) block dots now, partials delayed FPL*(bb-1)
            wire [NB*32-1:0] acc; wire [NB-1:0] afault;
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
                localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
                wire [31:0] bv0; wire bo0; wire [31:0] bv; wire bo;
                (* keep_hierarchy *) ot_hdc_v41x_q4dot_n #(.QL(QL)) u_d (.clk(clk), .a(qc[bb*128 +: 128]), .b(key_p[128*bb +: 128]),
                    .ua(qs[bb*8 +: 8]), .ub(key_p[NB*128 + 8*bb +: 8]), .y(bv0), .ovf(bo0));
                ot_hdc_delay_rf32 #(.W(33), .D(DS)) u_bd (.clk(clk), .d({bo0, bv0}), .q({bo, bv}));
                if (bb == 0) begin : g_first
                    assign acc[31:0] = bv; assign afault[0] = bo;
                end else begin : g_add
                    wire [1:0] err; wire vo_unused; wire pf, bo_d;
                    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(afault[bb-1]), .q(pf));
                    (* keep_hierarchy *) ot_hdc_fp32_add_lat_fan32 #(.LAT(FPL), .DRST(0), .SAFE_DIST(`OT_IDX_FAN32_SAFE)) u_a (
                        .clk(clk), .rst_n(srr[1 + hh * NB + bb]), .valid_in(1'b1),
                        .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
                    ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(clk), .rst_n(1'b1), .d(bo), .q(bo_d));
                    assign afault[bb] = pf || bo_d || (err != 2'd0);
                end
            end
            wire [15:0] sc16; wire sco;
            ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
            reg [15:0] rsc; reg rscf;
            always @(posedge clk) begin rsc <= sc16; rscf <= afault[NB-1] || sco; end
            wire [15:0] tm0; wire tmo, rscf_d;
            (* keep_hierarchy *) ot_hdc_v41x_bmul_n u_m (.clk(clk), .a(rsc), .w(qw), .y(tm0), .ovf(tmo));
            ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(clk), .rst_n(1'b1), .d(rscf), .q(rscf_d));
            // ---- (b) the head term waits 9h edges
            wire [15:0] tm; wire tf;
            ot_hdc_delay_rf32 #(.W(17), .D((FPL + 2) * H)) u_td (.clk(clk), .d({rscf_d || tmo, tm0}), .q({tf, tm}));
            reg [31:0] csi_p; reg cfi_p; reg [31:0] cs_o; reg cf_o;
`ifdef OT_IDX_RT_MUT_SEAM
            if (H == 2) begin : g_mseam          // mutant: the region seam between regions 0 and 1 one edge late
                reg [31:0] cs_x; reg cf_x;
                always @(posedge clk) begin cs_x <= cs[H]; cf_x <= cf[H]; csi_p <= cs_x; cfi_p <= cf_x; end
            end else begin : g_nseam
                always @(posedge clk) begin csi_p <= cs[H]; cfi_p <= cf[H]; end
            end
`else
            always @(posedge clk) begin csi_p <= cs[H]; cfi_p <= cf[H]; end
`endif
            if (H == 0) begin : g_seed
                wire [32:0] seed_d;
                ot_hdc_delay_rf32 #(.W(33), .D(FPL)) u_sd (.clk(clk),
                    .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
                always @(posedge clk) begin cs_o <= seed_d[31:0]; cf_o <= seed_d[32]; end
            end else begin : g_sum
                wire [1:0] err; wire vo_unused; wire [31:0] sum; wire pf;
                (* keep_hierarchy *) ot_hdc_fp32_add_lat_fan32 #(.LAT(FPL), .DRST(0), .SAFE_DIST(`OT_IDX_FAN32_SAFE)) u_a (
                    .clk(clk), .rst_n(srr[1 + hh * NB]), .valid_in(1'b1),
                    .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
                ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
                always @(posedge clk) begin cs_o <= sum; cf_o <= pf || (err != 2'd0); end
            end
            assign cs[H + 1] = cs_o; assign cf[H + 1] = cf_o;
        end
    end
    assign cs[0] = 32'd0; assign cf[0] = 1'b0;
    assign cs_out = cs[HC]; assign cf_out = cf[HC];
endmodule

// Chunk glue (ot_hbm_idx_chunk_rt_l minus the columns): reset relays, input registers, head ids, valid line, online,
// output registers.  Every column-bound output launches from a glue flop; every column input lands in a glue flop
// (c_sum / c_fault / rdy1) or a SUM_PAD / ONL_PAD pad stage.
module ot_hidx_chunk_glue #(
    parameter integer QLATE    = 0,      // bench mutant: the query broadcast reaches the heads QLATE edges late
    parameter integer VL_EXTRA = 0,      // landed-leaf schedule: valid line + VL_EXTRA edges
    parameter integer SUM_PAD  = 0,      // flat reference of a landed leaf: column sums padded SUM_PAD edges
    parameter integer ONL_PAD  = 0       // flat reference of a landed leaf: region online bits padded ONL_PAD edges
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [511:0]          ql_codes,
    input  wire [31:0]           ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [3:0]            k_kv,
    input  wire [2175:0]         k_key,
    output reg                   c_v,
    output reg  [3:0]            c_kv,
    output reg  [127:0]          c_sum,
    output reg  [3:0]            c_fault,
    output reg                   online,
    output wire                  n_v,
    output wire [3:0]            n_kv,
    output wire [127:0]          n_sum,
    output wire [3:0]            n_fault,
    // to / from the 4 columns
    output wire [3:0]            col_rst_n,
    output wire                  col_qv,
    output wire [567:0]          col_q,
    output wire [2175:0]         col_key,
    output wire [63:0]           col_hid,
    input  wire [127:0]          col_cs,
    input  wire [3:0]            col_cf,
    input  wire [15:0]           col_prdy
);
    localparam integer NB = 4, NKT = 4, FPL = 7, FML = 5, QL = 5, HC = 8;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer XLAT   = FPL + 16;
    localparam integer LATE   = LAT_T + FPL * (HC - 1) + XLAT + VL_EXTRA;
    localparam integer SEG    = 4;                                   // valid-line stages per relay copy (5 bits each)
    localparam integer NVS    = (LATE + SEG - 1) / SEG;
    wire [15:0] prdy; reg [15:0] rdy1, rdy2;
    wire [NKT+1+NVS:0] rr;
    ot_rst_relay_l #(.REGIONS(NKT + 2 + NVS), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[NKT];          // rdy1 / rdy2 clears (32)
    wire rn2 = rr[NKT + 1];     // online clear + the input / valid qualifiers
    assign col_rst_n = rr[NKT-1:0];
    ot_hdc_delay #(.W(16), .D(ONL_PAD)) u_onp (.clk(clk), .rst_n(1'b1), .d(col_prdy), .q(prdy));
    always @(posedge clk or negedge rn)
      if (!rn) begin rdy1 <= 0; rdy2 <= 0; end
      else begin rdy1 <= prdy; rdy2 <= rdy1; end
    always @(posedge clk or negedge rn2)
      if (!rn2) online <= 0; else online <= (&rdy2);
    reg rql_v; reg [QW-1:0] rq; reg rv; reg [NKT-1:0] rkv; reg [NKT*KW-1:0] rkey; reg [7:0] hb_p; reg [7:0] hid [0:HC-1];
    integer i;
    always @(posedge clk) begin
        rql_v <= ql_v && rn2; rq <= {ql_head, ql_codes, ql_sc, ql_w};
        rv <= k_v && rn2; rkv <= k_kv; rkey <= k_key; hb_p <= hb;
`ifdef OT_IDX_RT_MUT_SWAP
        for (i = 0; i < HC; i = i + 1) hid[i] <= (hb_p ^ 8'd8) + 8'(i);   // mutant: this leaf computes its neighbour's heads
`else
        for (i = 0; i < HC; i = i + 1) hid[i] <= hb_p + 8'(i);
`endif
    end
    genvar vs, hx;
    for (hx = 0; hx < HC; hx = hx + 1) begin : g_hid
        assign col_hid[8*hx +: 8] = hid[hx];
    end
    wire [NKT:0] vseg [0:NVS];
    assign vseg[0] = {rkv, rv};
    for (vs = 0; vs < NVS; vs = vs + 1) begin : g_vl
        localparam integer DL = (vs == NVS - 1) ? LATE - SEG * (NVS - 1) : SEG;
        ot_hdc_delay #(.W(NKT + 1), .D(DL), .RESET(1)) u_vl (.clk(clk), .rst_n(rr[NKT + 2 + vs]), .d(vseg[vs]), .q(vseg[vs + 1]));
    end
    wire [NKT:0] vl = vseg[NVS];
    ot_hdc_delay #(.W(1 + QW), .D(QLATE)) u_qlate (.clk(clk), .rst_n(1'b1), .d({rql_v, rq}), .q({col_qv, col_q}));
    assign col_key = rkey;
    wire [127:0] cs_p; wire [3:0] cf_p;
    ot_hdc_delay_rf32 #(.W(132), .D(SUM_PAD)) u_sp (.clk(clk), .d({col_cf, col_cs}), .q({cf_p, cs_p}));
    assign n_sum = cs_p; assign n_fault = cf_p;
    assign n_v = vl[0] && rn2; assign n_kv = vl[NKT:1];
    always @(posedge clk) begin c_v <= n_v; c_kv <= n_kv; c_sum <= cs_p; c_fault <= cf_p; end
endmodule

// The leaf core: wires only (glue + 4 identical columns).  Same ports and cycles as ot_hbm_idx_chunk_rt_l (no clk_pair).
module ot_hbm_idx_chunk_rt_c #(
    parameter integer QLATE = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    hb,
    input  wire          ql_v,
    input  wire [7:0]    ql_head,
    input  wire [511:0]  ql_codes,
    input  wire [31:0]   ql_sc,
    input  wire [15:0]   ql_w,
    input  wire          k_v,
    input  wire [3:0]    k_kv,
    input  wire [2175:0] k_key,
    output wire          c_v,
    output wire [3:0]    c_kv,
    output wire [127:0]  c_sum,
    output wire [3:0]    c_fault,
    output wire          online,
    output wire          n_v,
    output wire [3:0]    n_kv,
    output wire [127:0]  n_sum,
    output wire [3:0]    n_fault
);
    wire [3:0] crst; wire cqv; wire [567:0] cq; wire [2175:0] ckey; wire [63:0] chid;
    wire [127:0] ccs; wire [3:0] ccf; wire [15:0] cprdy;
    ot_hidx_chunk_glue #(.QLATE(QLATE)) u_glue (.clk(clk), .rst_n(rst_n), .hb(hb), .ql_v(ql_v), .ql_head(ql_head),
        .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w), .k_v(k_v), .k_kv(k_kv), .k_key(k_key),
        .c_v(c_v), .c_kv(c_kv), .c_sum(c_sum), .c_fault(c_fault), .online(online),
        .n_v(n_v), .n_kv(n_kv), .n_sum(n_sum), .n_fault(n_fault),
        .col_rst_n(crst), .col_qv(cqv), .col_q(cq), .col_key(ckey), .col_hid(chid),
        .col_cs(ccs), .col_cf(ccf), .col_prdy(cprdy));
    genvar g;
    for (g = 0; g < 4; g = g + 1) begin : g_col
        ot_hidx_score_col u_col (.clk(clk), .rst_n(crst[g]), .qv_b(cqv), .q_b(cq), .key(ckey[g*544 +: 544]), .hid(chid),
            .cs_out(ccs[32*g +: 32]), .cf_out(ccf[g]), .prdy(cprdy[4*g +: 4]));
    end
endmodule
`default_nettype wire
