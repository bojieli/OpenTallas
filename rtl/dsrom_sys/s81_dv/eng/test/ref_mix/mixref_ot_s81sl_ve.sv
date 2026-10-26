`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-MIX (2026-10-17): ve = the Engram-mix sub-leaf of one BEAT of a DV vector slice (planned x5 per slice, own clock
// root).  It replaces the hub-era dsfd_engram_mix4_c / the p4j void units mix4_w / mix4_e (dsfd_engram_mix4_half, never
// built): every Engram operand is beat-resident in DV (h in vn's h store; K = 4 x 5120 and V = 5120 FP32 = the
// engram.wkv field rows, captured into vp's leaf store; W = q_weight * k_weight, a per-element FP32 constant row in the
// leaf store), so the mix runs where the data is, and only 12 scalars per beat (3 sums x 4 copies) leave the leaf.
//
// Golden (tools/hdc_golden_v41.py engram_layer, chunk8 su class), copy j, D = 5120:
//   hh = csum(h*h), kk = csum(k*k), dd = csum((h*w)*k)       -> this leaf: the beat's aligned 64-element subtree sums
//   rstd = rsqrt(hh/D + eps) * rsqrt(kk/D + eps); dot = (dd*rstd)*scale; gate = sigmoid(signed sqrt(max(|dot|,1e-6)))
//                                                             -> slice finish (xfin exchange + ot_s81_engram_norm/_gate)
//   out = bf16(h + gate*v)                                    -> this leaf (add phase), written back into vn's h store
// A beat (64 elements) is 8 golden chunks = an aligned subtree of the padded pairwise tree, so the beat partial here is
// bit-identical to the flat engine's node, exactly as vn's norm beat partial.
//
// Arithmetic leaves are the gated hub-era Engram leaves, UNCHANGED (rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv):
//   ot_s81_engram_mul4   (4 lanes: h*h, k*k, h*w, (h*w)*k)      x1
//   ot_s81_engram_chunk8 (golden chunk of 8, sequential from +0) x3 (hh, kk, dd)
//   ot_s81_engram_add8   (8 lanes: bf16(h + gate*v))             x1
// plus the beat tree here (3 golden pairwise levels over the 8 chunk sums, one ot_dsrom_qadd per sum, dataflow issue
// with fixed operands per node: exact by construction, as vn's beat tree).
//
// Streams (static schedule, no ready / credit; the feeder -- the beat's vs over vp's extension port -- issues on the
// compiler's fixed timeline):
//   reduce  r_v: 4 elements a cycle {h (BF16 in an FP32 word), k, w}, copy-major, element order (16 cycles a copy,
//           64 a beat); r_c = the copy (checked against the leaf's own count: out of order = sticky fault).
//           -> p_v / p_c / p_hh / p_kk / p_dd: one beat partial triple per copy.
//   add     a_v: 8 elements a cycle {h, v} + the copy's gate; -> o_v / o_c / o_y (BF16 in the upper half of each word).
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 1 key -> 1.0 inside mul4; 2 beat tree
// level-1 pairs (s0 + s2), (s1 + s3) (golden association broken, same operands).
// ---------------------------------------------------------------------------------------------------------------------
module mixref_ot_s81sl_ve #(parameter integer LM = 5, LA = 4, MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    // reduce stream
    input  wire         r_v,
    input  wire [1:0]   r_c,
    input  wire [127:0] r_h, r_k, r_w,
    // beat partials
    output reg          p_v,
    output reg  [1:0]   p_c,
    output reg  [31:0]  p_hh, p_kk, p_dd,
    // add stream
    input  wire         a_v,
    input  wire [1:0]   a_c,
    input  wire [255:0] a_h, a_val,
    input  wire [31:0]  a_g,
    output reg          o_v,
    output reg  [1:0]   o_c,
    output reg  [255:0] o_y,
    output reg          fault
);
    wire rn;
    ot_s81_engram_reset reset_leaf (clk, rst_n, rn);

    // ---------------------------------------------------------------- input pin flops
    reg         rv_q, av_q;
    reg [1:0]   rc_q, ac_q;
    reg [127:0] rh_q, rk_q, rw_q;
    reg [255:0] ah_q, aval_q;
    reg [31:0]  ag_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin rv_q <= 1'b0; av_q <= 1'b0; end
        else begin rv_q <= r_v; av_q <= a_v; end
    always @(posedge clk) begin
        rc_q <= r_c; rh_q <= r_h; rk_q <= r_k; rw_q <= r_w;
        ac_q <= a_c; ah_q <= a_h; aval_q <= a_val; ag_q <= a_g;
    end

    // input order check: element quad counter (16 a copy), copy must match
    reg [5:0] icnt;
    reg       f_order;
    always @(posedge clk or negedge rn)
        if (!rn) begin icnt <= 6'd0; f_order <= 1'b0; end
        else if (rv_q) begin
            icnt <= icnt + 6'd1;
            if (rc_q != icnt[5:4]) f_order <= 1'b1;
        end

    // ---------------------------------------------------------------- products (h*h, k*k, (h*w)*k), 4 lanes
    wire         mv;
    wire [127:0] mhh, mkk, mdd;
    wire         mf;
    ot_s81_engram_mul4 #(.LM(LM), .MUT(MUT == 1 ? 1 : 0)) mul (clk, rst_n, rv_q, 1'b0, rh_q, rk_q, rw_q,
                                                              mv, mhh, mkk, mdd, mf);

    // ---------------------------------------------------------------- pack two quads into one golden chunk of 8
    reg         half;
    reg [127:0] shh, skk, sdd;
    reg         cv;
    reg [255:0] chh, ckk, cdd;
    always @(posedge clk or negedge rn)
        if (!rn) begin half <= 1'b0; cv <= 1'b0; end
        else begin
            cv <= mv && half;
            if (mv) half <= ~half;
        end
    always @(posedge clk) begin
        if (mv && !half) begin shh <= mhh; skk <= mkk; sdd <= mdd; end
        if (mv && half) begin chh <= {mhh, shh}; ckk <= {mkk, skk}; cdd <= {mdd, sdd}; end
    end

    wire [2:0]  sv, sf;
    wire [31:0] shh_s, skk_s, sdd_s;
    ot_s81_engram_chunk8 #(.LA(LA)) chunk_hh (clk, rst_n, cv, chh, sv[0], shh_s, sf[0]);
    ot_s81_engram_chunk8 #(.LA(LA)) chunk_kk (clk, rst_n, cv, ckk, sv[1], skk_s, sf[1]);
    ot_s81_engram_chunk8 #(.LA(LA)) chunk_dd (clk, rst_n, cv, cdd, sv[2], sdd_s, sf[2]);

    // ---------------------------------------------------------------- beat trees (lockstep)
    wire [2:0]  tv, tf;
    wire [1:0]  tc0, tc1, tc2;
    wire [31:0] thh, tkk, tdd;
    mixref_ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_hh (clk, rst_n, sv[0], shh_s, tv[0], tc0, thh, tf[0]);
    mixref_ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_kk (clk, rst_n, sv[1], skk_s, tv[1], tc1, tkk, tf[1]);
    mixref_ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_dd (clk, rst_n, sv[2], sdd_s, tv[2], tc2, tdd, tf[2]);

    always @(posedge clk or negedge rn)
        if (!rn) p_v <= 1'b0;
        else p_v <= tv[0];
    always @(posedge clk) begin p_c <= tc0; p_hh <= thh; p_kk <= tkk; p_dd <= tdd; end
    wire f_lock = (tv[0] != tv[1]) || (tv[0] != tv[2]) || (sv[0] != sv[1]) || (sv[0] != sv[2]) ||
                  (tv[0] && ((tc0 != tc1) || (tc0 != tc2)));

    // ---------------------------------------------------------------- add phase: bf16(h + gate*v), 8 lanes
    wire         yv;
    wire [255:0] yd;
    wire         yf;
    wire [1:0]   yc;
    ot_s81_engram_add8 #(.LM(LM), .LA(LA)) add (clk, rst_n, av_q, 1'b1, ah_q, aval_q, ag_q, ac_q, yv, yd, yf, yc);
    always @(posedge clk or negedge rn)
        if (!rn) o_v <= 1'b0;
        else o_v <= yv;
    always @(posedge clk) begin o_c <= yc; o_y <= yd; end

    always @(posedge clk or negedge rn)
        if (!rn) fault <= 1'b0;
        else if (f_order || mf || (|sf) || (|tf) || f_lock || yf) fault <= 1'b1;
endmodule

// Beat tree: 8 chunk sums of one copy arrive in order (at most one a cycle) -> the golden pairwise node
// ((s0+s1)+(s2+s3))+((s4+s5)+(s6+s7)).  One pipelined adder; node n issues when both operands are present (fixed
// operands per node, so the order of issue cannot change a result).  4 copy slots (copy = slot), cleared at output.
module mixref_ot_s81sl_ve_tree #(parameter integer LA = 4, MUT = 0) (
    input  wire        clk, rst_n, v,
    input  wire [31:0] s,
    output reg         vo,
    output reg  [1:0]  co,
    output reg  [31:0] y,
    output reg         fault
);
    wire rn;
    ot_s81_engram_reset reset_leaf (clk, rst_n, rn);
    // value index: 0..7 leaves, 8..14 nodes n0..n6
    reg [31:0] val  [0:3][0:14];
    reg [14:0] have [0:3];
    reg [6:0]  iss  [0:3];
    reg [4:0]  lcnt;                       // {copy, leaf}
    function automatic [3:0] opa(input integer n);
        opa = (n < 4) ? ((MUT == 2 && n < 2) ? n : 2 * n) : 8 + 2 * (n - 4);
    endfunction
    function automatic [3:0] opb(input integer n);
        opb = (n < 4) ? ((MUT == 2 && n < 2) ? n + 2 : 2 * n + 1) : 9 + 2 * (n - 4);
    endfunction
    // issue select: highest node, lowest slot
    reg        isv;
    reg [1:0]  isl;
    reg [2:0]  isn;
    integer q, n;
    always @* begin
        isv = 1'b0; isl = 2'd0; isn = 3'd0;
        for (q = 3; q >= 0; q = q - 1)
            for (n = 0; n < 7; n = n + 1)
                if (have[q][opa(n)] && have[q][opb(n)] && !iss[q][n]) begin
                    isv = 1'b1; isl = q[1:0]; isn = n[2:0];
                end
    end
    wire [31:0] sum;
    wire        af;
    wire [LA:0] rvl;
    wire [4:0]  rtag;
    ot_dsrom_qadd #(.LAT(LA)) adder (clk, rn, isv, val[isl][opa(isn)], val[isl][opb(isn)], sum, af);
    ot_hdc_vline #(.D(LA)) rv_line (clk, rn, isv, rvl);
    ot_hdc_delay #(.W(5), .D(LA)) tag_line (clk, rn, {isl, isn}, rtag);
    wire        rv = rvl[LA];
    wire [1:0]  rsl = rtag[4:3];
    wire [2:0]  rnd = rtag[2:0];
    integer k;
    always @(posedge clk or negedge rn)
        if (!rn) begin
            lcnt <= 5'd0; vo <= 1'b0; fault <= 1'b0;
            for (k = 0; k < 4; k = k + 1) begin have[k] <= 15'd0; iss[k] <= 7'd0; end
        end else begin
            vo <= 1'b0;
            if (v) begin
                if (have[lcnt[4:3]][lcnt[2:0]]) fault <= 1'b1;          // slot not yet free: schedule violation
                have[lcnt[4:3]][lcnt[2:0]] <= 1'b1;
                lcnt <= lcnt + 5'd1;
            end
            if (isv) iss[isl][isn] <= 1'b1;
            if (rv) begin
                if (rnd == 3'd6) begin
                    vo <= 1'b1; co <= rsl;
                    have[rsl] <= 15'd0; iss[rsl] <= 7'd0;
                end else have[rsl][8 + rnd] <= 1'b1;
            end
            if (af) fault <= 1'b1;
        end
    always @(posedge clk) begin
        if (v) val[lcnt[4:3]][lcnt[2:0]] <= s;
        if (rv) begin
            val[rsl][8 + rnd] <= sum;
            if (rnd == 3'd6) y <= sum;
        end
    end
endmodule
