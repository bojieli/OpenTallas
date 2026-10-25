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
// S81-VE r2 (10-19, route b571a8c2c NEEDS_RTL TT -338 / FF -25): static streaming pairwise beat tree (one adder per golden
// level, same association and issue cycle, 129 cyc GAP 0) and D>=3 delay lines as rings instead of shift registers.
// S81-VE r3 (10-19, SAFE-DESIGN checklist after the failed route; r2 gate: ONE merged reset sync drove 2,320 flops,
// 1,230 non-clock roots > 32 loads, ring write pointers 760-870 loads, pack enables 379, operand decodes merged across
// lanes 264):
//   reset   one ot_rst_relay (2 sync + 1 kept relay stage, 18 region copies) behind the kit's 2-stage reset landing;
//           every region copy resets <= 32 flops and ONLY valid / control state: the per-leaf ot_s81_engram_reset
//           syncs are gone (identical, so synthesis merged them into one 2,320-load flop), the FP units are the ve-local
//           valid-only-reset copies (ot_s81sl_ve_fp.sv: 4 / 5 reset flops a unit, r2 38 / 39), and the separate reset
//           valid delay lines are gone (each unit's valid is the previous unit's exported valid_out: same cycle).
//   copies  reset-free KEPT copies: ring row selects are one-hot registers replicated per 8-bit slice (each bit: 8
//           write enables + 8 read gates), the pack's low-quad hold enable is 24 kept copies (16 bits each), every
//           multiplier operand that fed two decodes has its own kept operand register (mh a / b, mk a / b, mw a, key
//           line), the add phase's gate word is one kept copy per lane (r2: one decode for 8 lanes, 264 loads).
//   tree    level operands: the held even operand feeds the adder directly, the odd one through one free register;
//           data registers carry no enable (consumers are valid-qualified), so no wide enable net remains.
// Calendars unchanged (reduce first-in -> last partial 129 cyc at GAP 0, add 44 cyc); reset release +1 edge (relay
// stage), a one-time cost after reset, nothing on the token path.  MUT (bench only): 1 key -> 1.0 inside mul4; 2 beat
// tree level-1 pairs (s0 + s2), (s1 + s3); 3 the chunk operand rings' slice-1 READ select one row late.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_ve #(parameter integer LM = 5, LA = 4, MUT = 0) (
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
    output reg  [127:0] o_y,             // packed BF16: o_y[16 k +: 16] = lane k (low halves were constant 0; OWNER DECISION 8 (2026-10-24, S81-KITS-RTLA):)
    (* keep *) output reg          fault
);
    // ---------------------------------------------------------------- reset regions (<= 32 reset loads each)
    //  0 top control | 1..4 mul4 lanes | 5,6 chunk_hh | 7,8 chunk_kk | 9,10 chunk_dd | 11..13 trees | 14..17 add8 lane pairs
    localparam integer NR = 18;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    wire rn = rq[0];

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
    wire         mv, mvpre;
    wire [127:0] mhh, mkk, mdd;
    wire         mf;
    ot_s81sl_ve_mul4 #(.LM(LM), .MUT(MUT == 1 ? 1 : 0)) mul (clk, rq[4:1], rv_q, 1'b0, rh_q, rk_q, rw_q,
                                                              mv, mvpre, mhh, mkk, mdd, mf);

    // ---------------------------------------------------------------- pack two quads into one golden chunk of 8
    // half / cv: control (reset).  The low quad is held by 24 kept enable copies (16 bits each): e_lo(t) = mv(t) &&
    // !half(t), registered one edge early from mul4's pre-pin valid (mv(t) = mvpre(t-1), half(t) = half ^ mv).  The
    // chunk word register carries no enable (chunk8 qualifies it with cv).
    reg         half;
    reg         cv;
    always @(posedge clk or negedge rn)
        if (!rn) begin half <= 1'b0; cv <= 1'b0; end
        else begin
            cv <= mv && half;
            if (mv) half <= ~half;
        end
    wire e_lo_d = mvpre && !(half ^ mv);
    (* keep = "true" *) reg [23:0] e_lo;
    always @(posedge clk) e_lo <= {24{e_lo_d}};
    reg  [383:0] sbus;                                   // {sdd, skk, shh}
    wire [383:0] mbus = {mdd, mkk, mhh};
    genvar g;
    generate for (g = 0; g < 24; g = g + 1) begin : g_lo
        always @(posedge clk) if (e_lo[g]) sbus[16*g +: 16] <= mbus[16*g +: 16];
    end endgenerate
    reg [255:0] chh, ckk, cdd;
    always @(posedge clk) begin
        chh <= {mhh, sbus[127:0]}; ckk <= {mkk, sbus[255:128]}; cdd <= {mdd, sbus[383:256]};
    end

    wire [2:0]  sv, sf;
    wire [31:0] shh_s, skk_s, sdd_s;
    ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_hh (clk, rq[6:5],  cv, chh, sv[0], shh_s, sf[0]);
    ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_kk (clk, rq[8:7],  cv, ckk, sv[1], skk_s, sf[1]);
    ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_dd (clk, rq[10:9], cv, cdd, sv[2], sdd_s, sf[2]);

    // ---------------------------------------------------------------- beat trees (lockstep)
    wire [2:0]  tv, tf;
    wire [1:0]  tc0, tc1, tc2;
    wire [31:0] thh, tkk, tdd;
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_hh (clk, rq[11], sv[0], shh_s, tv[0], tc0, thh, tf[0]);
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_kk (clk, rq[12], sv[1], skk_s, tv[1], tc1, tkk, tf[1]);
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_dd (clk, rq[13], sv[2], sdd_s, tv[2], tc2, tdd, tf[2]);

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
    ot_s81sl_ve_add8 #(.LM(LM), .LA(LA)) add (clk, rq[17:14], av_q, 1'b1, ah_q, aval_q, ag_q, ac_q, yv, yd, yf, yc);
    always @(posedge clk or negedge rn)
        if (!rn) o_v <= 1'b0;
        else o_v <= yv;
    always @(posedge clk) begin o_c <= yc; o_y <= {yd[255:240], yd[223:208], yd[191:176], yd[159:144], yd[127:112], yd[95:80], yd[63:48], yd[31:16]}; end

    // S81-KITS-RTLA 10-24 (face_guard: register on every pin): sticky state in fault_s, the pin flop fault is an
    // output-only copy of the same next value (was: fault fed back into its own D).  0 cycles, bit / cycle identical.
    (* keep *) reg fault_s;
    wire fault_n = fault_s | f_order | mf | (|sf) | (|tf) | f_lock | yf;
    always @(posedge clk or negedge rn)
        if (!rn) begin fault <= 1'b0; fault_s <= 1'b0; end
        else begin fault <= fault_n; fault_s <= fault_n; end
endmodule

// Beat tree: 8 chunk sums of one copy arrive in order (at most one a cycle) -> the golden pairwise node
// ((s0+s1)+(s2+s3))+((s4+s5)+(s6+s7)).  Static streaming form: three pipelined adders, one per level.  Each level sees
// its operands in order, holds the even one (enabled 32-bit register) and issues the pair the cycle after the odd one
// lands: the odd operand goes through one free-running register, the held even operand feeds the adder directly (it is
// rewritten at the earliest on the edge the adder captures it).  Level valids are the adders' own valid_out.
// MUT 2 (bench only): level-1 pairs (s0 + s2), (s1 + s3).
module ot_s81sl_ve_tree #(parameter integer LA = 4, MUT = 0) (
    input  wire        clk, rn, v,
    input  wire [31:0] s,
    output reg         vo,
    output reg  [1:0]  co,
    output reg  [31:0] y,
    output reg         fault
);
    // ---- level 1: leaf pairs
    reg  [2:0]  li;                        // leaf index within the copy
    (* keep *) reg [31:0] h1, a1, b1;      // r4b: both copies kept (a non-kept twin folds into the kept one)
    reg  [31:0] m1;
    (* keep *) reg [31:0] h1c, a1c, b1c;      // VE4: kept second operand copies (the adder's alignment operands)
    reg         i1;
    wire hold1  = (MUT == 2) ? (li == 3'd0 || li == 3'd4 || li == 3'd6) : !li[0];
    wire stash1 = (MUT == 2) && (li == 3'd1);
    wire [31:0] pa1 = (MUT == 2 && li == 3'd3) ? m1 : h1;
    always @(posedge clk or negedge rn)
        if (!rn) begin li <= 3'd0; i1 <= 1'b0; end
        else begin
            i1 <= v && !hold1 && !stash1;
            if (v) li <= li + 3'd1;
        end
    // r4b: the hold enable is 4 kept AND copies, one per 16 bits of h1 / h1c (r4a one enable net: 64 loads)
    wire [3:0] e1;
    genvar ge;
    generate for (ge = 0; ge < 4; ge = ge + 1) begin : g_e1
        ot_s81sl_ve_kand u (.a(v), .b(hold1), .y(e1[ge]));
    end endgenerate
    always @(posedge clk) begin
        if (e1[0]) h1[15:0] <= s[15:0];
        if (e1[1]) h1[31:16] <= s[31:16];
        if (e1[2]) h1c[15:0] <= s[15:0];
        if (e1[3]) h1c[31:16] <= s[31:16];
        if (v && stash1) m1 <= s;
        a1 <= pa1;                         // MUT 2 only (the MUT 0 build drops it)
        a1c <= pa1;
        b1 <= s;
        b1c <= s;
    end
    wire [31:0] s1, s1c;
    wire        f1, r1;
    ot_s81sl_ve_qadd #(.LAT(LA)) add1 (clk, rn, i1, (MUT == 2) ? a1 : h1, (MUT == 2) ? a1c : h1c, b1, b1c, s1, s1c, r1, f1);
    // ---- level 2: pairs of level-1 sums (n0,n1) -> n4, (n2,n3) -> n5
    reg         p2, i2;
    (* keep *) reg [31:0] h2, b2;
    (* keep *) reg [31:0] h2c, b2c;
    always @(posedge clk or negedge rn)
        if (!rn) begin p2 <= 1'b0; i2 <= 1'b0; end
        else begin
            i2 <= r1 && p2;
            if (r1) p2 <= ~p2;
        end
    wire [3:0] e2;
    generate for (ge = 0; ge < 4; ge = ge + 1) begin : g_e2
        ot_s81sl_ve_kand u (.a(r1), .b(!p2), .y(e2[ge]));
    end endgenerate
    always @(posedge clk) begin
        if (e2[0]) h2[15:0] <= s1[15:0];
        if (e2[1]) h2[31:16] <= s1[31:16];
        if (e2[2]) h2c[15:0] <= s1c[15:0];
        if (e2[3]) h2c[31:16] <= s1c[31:16];
        b2 <= s1;
        b2c <= s1c;
    end
    wire [31:0] s2, s2c;
    wire        f2, r2;
    ot_s81sl_ve_qadd #(.LAT(LA)) add2 (clk, rn, i2, h2, h2c, b2, b2c, s2, s2c, r2, f2);
    // ---- level 3: (n4, n5) -> n6 = the beat partial
    reg         p3, i3;
    (* keep *) reg [31:0] h3, b3;
    (* keep *) reg [31:0] h3c, b3c;
    always @(posedge clk or negedge rn)
        if (!rn) begin p3 <= 1'b0; i3 <= 1'b0; end
        else begin
            i3 <= r2 && p3;
            if (r2) p3 <= ~p3;
        end
    wire [3:0] e3;
    generate for (ge = 0; ge < 4; ge = ge + 1) begin : g_e3
        ot_s81sl_ve_kand u (.a(r2), .b(!p3), .y(e3[ge]));
    end endgenerate
    always @(posedge clk) begin
        if (e3[0]) h3[15:0] <= s2[15:0];
        if (e3[1]) h3[31:16] <= s2[31:16];
        if (e3[2]) h3c[15:0] <= s2c[15:0];
        if (e3[3]) h3c[31:16] <= s2c[31:16];
        b3 <= s2;
        b3c <= s2c;
    end
    wire [31:0] s3, s3c;
    wire        f3, r3;
    ot_s81sl_ve_qadd #(.LAT(LA)) add3 (clk, rn, i3, h3, h3c, b3, b3c, s3, s3c, r3, f3);
    // ---- output: copy = arrival order
    reg [1:0] oc;
    always @(posedge clk or negedge rn)
        if (!rn) begin vo <= 1'b0; oc <= 2'd0; fault <= 1'b0; end
        else begin
            vo <= r3;
            if (r3) oc <= oc + 2'd1;
            if (f1 || f2 || f3) fault <= 1'b1;
        end
    always @(posedge clk) begin y <= s3; co <= oc; end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Ring delay line (r3): q is d delayed by exactly D edges, cycle-exact as ot_hdc_delay / ot_hdc_delay_rf for D >= 3:
// input register -> N = D - 2 rows (one row written per edge) -> output register.  The row select is a ONE-HOT
// register replicated per 8-bit slice (* keep *), each bit driving 8 write enables + 8 read AND gates; all copies are
// registered from one decode of the next write pointer (self-correcting: wptr leaves any out-of-range power-up value on
// its first edge, the one-hot copies follow one edge later -- before the line has filled, as the rf form).  No reset
// (data and pointer), no runtime-indexed array (rows are plain registers, the read is an AND-OR of the selected row).
// D < 3: ot_hdc_delay (wire / one or two registers).  MUT 3 (bench only): slice 1's read select one row late.
// ---------------------------------------------------------------------------------------------------------------------
// VE4: q2 = a kept copy of q (the ring's output register duplicated; D = 0: q2 = d2, the caller's own copy; D = 1, 2:
// a kept register chain from d2).  Consumers that need no copy leave q2 open (synthesis drops it).
module ot_s81sl_ve_dly #(parameter integer W = 32, D = 1, MUT = 0) (
    input wire clk, input wire [W-1:0] d, input wire [W-1:0] d2, output wire [W-1:0] q, output wire [W-1:0] q2);
    generate if (D >= 3) begin : g_ring
        ot_s81sl_ve_ring #(.W(W), .D(D), .MUT(MUT)) u (clk, d, q, q2);
    end else if (D == 0) begin : g_w
        assign q = d;
        assign q2 = d2;
    end else begin : g_sh
        // r4b: both chains are kept registers (ot_hdc_delay's unkept flops folded into the kept copy chain)
        (* keep *) reg [W-1:0] p [0:D-1];
        (* keep *) reg [W-1:0] c [0:D-1];
        integer i;
        always @(posedge clk) begin
            p[0] <= d;
            c[0] <= d2;
            for (i = 1; i < D; i = i + 1) begin p[i] <= p[i - 1]; c[i] <= c[i - 1]; end
        end
        assign q = p[D - 1];
        assign q2 = c[D - 1];
    end endgenerate
endmodule

module ot_s81sl_ve_ring #(parameter integer W = 32, D = 3, MUT = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q, output wire [W-1:0] q2);
    localparam integer N = D - 2;
    localparam integer K = (N <= 2) ? 1 : $clog2(N);
    localparam [K-1:0] LAST = N - 1;
    localparam integer S = (W + 7) / 8;
    reg [W-1:0] din;
    (* keep *) reg [W-1:0] dout;                 // r4b: kept like dout2
    (* keep *) reg [W-1:0] dout2;                // VE4: kept copy of the output register (same D)
    reg [K-1:0] wptr;
    wire [K-1:0] wnext = (wptr >= LAST) ? {K{1'b0}} : wptr + 1'b1;
    reg  [N-1:0] oh_d, oh_late;
    integer r;
    always @* for (r = 0; r < N; r = r + 1) begin
        oh_d[r] = (wnext == r[K-1:0]);
        oh_late[r] = (wptr == r[K-1:0]);
    end
    always @(posedge clk) begin din <= d; wptr <= wnext; end
    genvar sl, i;
    generate for (sl = 0; sl < S; sl = sl + 1) begin : g_s
        localparam integer LO = 8 * sl;
        localparam integer SW = (W - LO) < 8 ? (W - LO) : 8;
        (* keep = "true" *) reg [N-1:0] oh;          // this slice's row select copy
        always @(posedge clk) oh <= oh_d;
        // MUT 3 (bench only): slice 1 READS one row late (a uniformly rotated select would still be exact)
        reg [N-1:0] ohr;
        always @(posedge clk) ohr <= (MUT == 3 && sl == 1) ? oh_late : oh_d;
        wire [N-1:0] rsel = (MUT == 3) ? ohr : oh;
        wire [SW*N-1:0] sel;
        for (i = 0; i < N; i = i + 1) begin : g_r
            reg [SW-1:0] row;
            always @(posedge clk) if (oh[i]) row <= din[LO +: SW];
            assign sel[SW*i +: SW] = row & {SW{rsel[i]}};
        end
        reg [SW-1:0] rd;
        integer j;
        always @* begin rd = {SW{1'b0}}; for (j = 0; j < N; j = j + 1) rd = rd | sel[SW*j +: SW]; end
        always @(posedge clk) dout[LO +: SW] <= rd;
        always @(posedge clk) dout2[LO +: SW] <= rd;
    end endgenerate
    assign q = dout;
    assign q2 = dout2;
`ifndef SYNTHESIS
    initial wptr = {K{1'b0}};
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ve-local arithmetic leaves: the gated hub Engram leaves of rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv (mul4,
// chunk8, add8), identical arithmetic and latency; r3: regional resets from the top relay (rq), valid-only-reset FP
// units (ot_s81sl_ve_qmul / _qadd), unit valids chained from the unit before, kept operand copies, ring delay lines.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_ve_mul4 #(parameter integer LM=5,MUT=0)(
 input wire clk,input wire [3:0] rq,input wire v,phase,input wire [127:0] h,k,w,
 output wire vo,output wire vpre,output wire [127:0] hh,kk,dot,output reg fault);
 wire rn=rq[0];
 reg [127:0] hp,kp,wp;reg vp_in,phase_in;
 always @(posedge clk or negedge rn)if(!rn)begin vp_in<=0;phase_in<=0;end else begin vp_in<=v;phase_in<=phase;end
 always @(posedge clk)begin hp<=h;kp<=k;wp<=w;end
 reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=vp_in&&!phase_in;
 wire [127:0] hs,ks,hw,dot_mid;wire [15:0] f;wire [3:0] dv;
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  // one kept operand register per decode (r2: hr fed mh a, mh b and mw a; kr fed mk a, mk b and the key line);
  // VE4: plus a kept second copy of every multiplier operand (the unit's normalise operand: ot_s81sl_ve_fp.sv)
  (* keep = "true" *) reg [31:0] ha,hb,hwa,ka,kb,kl,wl,ha2,hb2,hwa2,ka2,kb2,wl2;
  always @(posedge clk)begin ha<=hp[32*l+:32];hb<=hp[32*l+:32];hwa<=hp[32*l+:32];
   ka<=kp[32*l+:32];kb<=kp[32*l+:32];kl<=kp[32*l+:32];wl<=wp[32*l+:32];
   ha2<=hp[32*l+:32];hb2<=hp[32*l+:32];hwa2<=hp[32*l+:32];ka2<=kp[32*l+:32];kb2<=kp[32*l+:32];wl2<=wp[32*l+:32];end
  wire [31:0] kd,kd2,dr,hw2,nc0,nc1,nc2;wire vh,vk,vw;
  ot_s81sl_ve_qmul #(LM) mh(clk,rq[l],vr,ha,ha2,hb,hb2,hs[32*l+:32],nc0,vh,f[4*l]);
  ot_s81sl_ve_qmul #(LM) mk(clk,rq[l],vr,ka,ka2,kb,kb2,ks[32*l+:32],nc1,vk,f[4*l+1]);
  ot_s81sl_ve_qmul #(LM) mw(clk,rq[l],vr,hwa,hwa2,wl,wl2,hw[32*l+:32],hw2,vw,f[4*l+2]);
  ot_s81sl_ve_dly #(.W(32),.D(LM)) key_line(clk,kl,kl,kd,kd2);
  ot_s81sl_ve_qmul #(LM) md(clk,rq[l],vw,hw[32*l+:32],hw2,(MUT==1)?32'h3f800000:kd,(MUT==1)?32'h3f800000:kd2,dr,nc2,dv[l],f[4*l+3]);
  reg [31:0] dout;always @(posedge clk)dout<=dr;assign dot_mid[32*l+:32]=dout;
 end endgenerate
 wire [127:0] hmid,kmid;
 ot_s81sl_ve_dly #(.W(128),.D(LM+1)) hline(clk,hs,hs,hmid,);
 ot_s81sl_ve_dly #(.W(128),.D(LM+1)) kline(clk,ks,ks,kmid,);
 reg [127:0] hh_pin,kk_pin,dot_pin;
 always @(posedge clk)begin hh_pin<=hmid;kk_pin<=kmid;dot_pin<=dot_mid;end
 assign hh=hh_pin;assign kk=kk_pin;assign dot=dot_pin;
 reg valid;always @(posedge clk or negedge rn)if(!rn)valid<=0;else valid<=dv[0];
 reg valid_pin;always @(posedge clk or negedge rn)if(!rn)valid_pin<=0;else valid_pin<=valid;
 assign vo=valid_pin;assign vpre=valid;wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81sl_ve_chunk8 #(parameter integer LA=4,MUT=0)(
 input wire clk,input wire [1:0] rq,input wire v,input wire [255:0] x,
 output wire vo,output wire [31:0] sum,output reg fault);
 wire rn=rq[0];
 (* keep = "true" *) reg [255:0] xr;reg vr;   // r4b: kept (xr[31:0] folded into xr0c)
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)xr<=x;
 // VE4: acc2 = the kept second copy of each adder's output (the next adder's alignment operand); xr0c a kept copy
 // of the term-0 word (term 0 has no delay line)
 wire [31:0] acc[0:8];wire [31:0] acc2[0:8];wire [7:0] f;wire [8:0] tv;assign acc[0]=0;assign acc2[0]=0;assign tv[0]=vr;
 (* keep = "true" *) reg [31:0] xr0c;
 always @(posedge clk)xr0c<=x[31:0];
 genvar t;
 generate for(t=0;t<8;t=t+1)begin:term
  wire [31:0] xd,xd2;
  ot_s81sl_ve_dly #(.W(32),.D(LA*t),.MUT(MUT)) operand_line(clk,xr[32*t+:32],(t==0)?xr0c:xr[32*t+:32],xd,xd2);
  ot_s81sl_ve_qadd #(.LAT(LA)) add(clk,rq[t/4],tv[t],acc[t],acc2[t],xd,xd2,acc[t+1],acc2[t+1],tv[t+1],f[t]);
 end endgenerate
 assign vo=tv[8];assign sum=acc[8];wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81sl_ve_add8 #(parameter integer LM=5,LA=4)(
 input wire clk,input wire [3:0] rq,input wire v,phase,input wire [255:0] h,value,input wire [31:0] gate,input wire [1:0] copy,
 output reg vo,output reg [255:0] y,output reg fault,output wire [1:0] copy_out);
 wire rn=rq[0];
 reg vr;reg [255:0] hr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v&&phase;
 always @(posedge clk)hr<=h;
 wire [15:0] f;wire [7:0] av;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:lane
  // one kept gate copy per lane (r2: one gr register -> 8 lane multipliers -> their b decodes merged, 264 loads);
  // VE4: kept second copies of the multiplier operands, the h line's output and the product (alignment operands)
  (* keep = "true" *) reg [31:0] gl,gl2,vl1,vl2;   // r4b: vl1 (was the non-kept valr slice) kept too
  always @(posedge clk)begin gl<=gate;gl2<=gate;vl1<=value[32*l+:32];vl2<=value[32*l+:32];end
  wire [31:0] prod,prod2,hd,hd2,ys,nc;wire mvo;
  ot_s81sl_ve_qmul #(LM) mul(clk,rq[l/2],vr,vl1,vl2,gl,gl2,prod,prod2,mvo,f[2*l]);
  ot_s81sl_ve_dly #(.W(32),.D(LM)) hline(clk,hr[32*l+:32],hr[32*l+:32],hd,hd2);
  ot_s81sl_ve_qadd #(.LAT(LA)) add(clk,rq[l/2],mvo,hd,hd2,prod,prod2,ys,nc,av[l],f[2*l+1]);
  wire [31:0] rounded=ys+32'h7fff+ys[16];
  always @(posedge clk)y[32*l+:32]<={rounded[31:16],16'd0};
 end endgenerate
 always @(posedge clk or negedge rn)if(!rn)vo<=0;else vo<=av[0];
 wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
 ot_s81sl_ve_dly #(.W(2),.D(LM+LA+2)) copy_line(clk,copy,copy,copy_out,);
endmodule
