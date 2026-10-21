// Generated source-local HEAD tile successor; old masters retained.
`timescale 1ns/1ps
// Source-local successor of the failed two-stage kit reset landing.
// Three synchronous sampling stages: 2 first copies -> 64 middle -> 1536 final.
// Every family is identical BEFORE the standard ot_rst_split load redistribution.
// This changes reset assertion and release age by +1 edge versus kit landing2.
// Traffic data/valid stages and arithmetic remain unchanged after startup.
module ot_s81hd_tile_r3 #(
 parameter INSTANCE="h", parameter integer IOREG=1,
 parameter [8:0] CUT=9'b1_0111_1011, parameter integer SPLIT9=0
)(input wire ck,rst_n,input wire [564:0] i,output wire [564:0] o,
 input wire [16:0] row0,input wire ten);
 (* keep, ot_rst_split=1 *) reg [1:0] tile_r0;
 (* keep, ot_rst_split=1 *) reg [63:0] tile_r1;
 (* keep, ot_rst_split=1 *) reg [1535:0] tile_r2;
 always @(posedge ck) begin
   tile_r0 <= {2{rst_n}};
   tile_r1 <= {64{tile_r0[0]}};
   tile_r2 <= {1536{tile_r1[0]}};
 end
 ot_s81hd_tile_r3_core #(.INSTANCE(INSTANCE),.IOREG(IOREG),.CUT(CUT),.SPLIT9(SPLIT9)) u_core
 (.ck(ck),.rst_n(tile_r2[0]),.i(i),.o(o),.row0(row0),.ten(ten));
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_elem (S81-HEAD HD-TILE 10-21): census-safe copy of rtl/v41rom/ot_dsrom_head_elem.sv for the S81 release head
// die tile ot_s81hd_tile.  Same arithmetic, same cycle timing (go -> o_v / l_v / done), same ports.  Changes (all exact,
// mapped load count <= 32 per driver, pre-gate native census):
//   * bank capture enables / select: RP 8 -> 10 kept copies (274 / 8 = 35 loads -> <= 28);
//   * IOREG go: two kept pin copies (issue + argmax control | nrow);
//   * join operands j_a / j_b and the argmax key registers k_* load every cycle (no 64 / 82-bit enable): they are read
//     only under their valid (j_v -> u_join valid_in, k_v -> SAFE stage);
//   * root FIFO read pointers: kept copies per 16 / 8 bit group;
//   * SAFE argmax apply: the staged valid / take / bad are 3 kept copies, one per best register group.
// SAFE = 1 is required (the SAFE = 0 compare path is not census-safe and is refused at elaboration).
// NC = 1 (default; HD-TILE census round 2, a mapped select / enable costs 2 load pins a bit):
//   * arithmetic: adders ot_hdc_fp32_add_lat_fan32 (LAT 7, DRST 0, SAFE_DIST 1: the bounded native fp32_add_rne
//     netlist, rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v), so SK = 7; products ot_hdc_fp32_mul_lat_ncr (LAT 6, the
//     native-32 FP32 multiply) on the BF16 operands: exact for every product the S81 head forms (16-bit significand),
//     the same latency as ot_dsrom_bmul3; zero products may carry a sign (the adder returns +0 for every zero sum, and
//     x + (+-0) = x, so sums are unchanged); a product below the FP32 subnormal range is rounded instead of faulted;
//   * every wide enable / select is a kept register copy per <= 16 bits: bank capture RP 18, tree hold `have` x3 a
//     level, root FIFO write pointers x4 (8-bit groups), read pointers x4 / x8, SAFE apply x10, go x4;
//   * the argmax key comes from ot_s81hd_key (2 registered stages; +1 cycle on the key / logit-to-best path);
//   * the issue counter and the row counter are enable-free (AND-clear / carry-in increments).
// Original header follows.
// ---------------------------------------------------------------------------
// ot_dsrom_head_elem: DS-ROM lm_head element at the ROM read rate (recovery lever "head", 2026-10-04).
// Successor of the head use of ot_v41_rom_elem_w10 FAST PP BP=2 (2 BF16 multipliers a macro, a word held 8 cycles,
// phase/config driven).  This element is dedicated to the head GEMV (AGENTS rule 2: irregular/dedicated where it
// wins): one logical macro = 2 x ot_rom_4096x274_m8 read ping-pong (1 word a cycle), 16 BF16 multipliers (one per
// weight of the word), so the MAC rate equals the ROM read width.  No configuration, no clock gate: `go` streams the
// whole macro once (8,192 words + the systolic skew), every word a cycle.
//
// Arithmetic (golden R-ARITH chunk8, tools/hdc_golden_v41.py csum): a word holds 16 consecutive K of one row =
// golden chunks 2m (lanes 0..7) and 2m+1 (lanes 8..15).  Each chunk is summed sequentially from +0 by a systolic
// chain of 8 ot_v41_fadd (stage s adds lane s / 8+s); the products reach stage s exactly when its left operand does
// because the ROM image is SKEWED: lane j of physical word p holds lane j of logical word (p - SK*(j mod 8)) mod 8192
// (SK = the adder latency), and the x broadcast is skewed the same way (ot_dsrom_head_bundle).  The two chunk sums
// meet in the level-1 pair add; a streaming pairwise tree of LV levels (one adder a level, a held left sibling)
// finishes the row's golden node: LV = 8 -> 256 words = the 512-chunk root4096 (part A, K 0..4095), LV = 6 -> 64
// words = the 128-chunk root1024 (part B, K 4096..5119).  PAD (B) adds the two golden padding levels (+0, +0).
// JOIN (A): logit = root4096 + padded root1024 (received from the bundle's B element, in this element's row order),
// then the lowest-id first-max argmax of S81's native terminal (-0 canonical, sign-magnitude key, lower row wins a
// tie) over this element's rows.  Every add is ot_v41_fadd (bit-identical to fp32_add_rne), every product
// ot_v41_bmul2 (exact BF16 x BF16); any adder err or product fault is a sticky fault (fail closed).
//
// Timing: `go` at cycle G -> physical word a issued at G+2+a; the x pins must carry the (skewed) slice of physical
// word a at cycle G+5+a (unchanged by the r3 transport stage: x is delayed with the word).  Products of word a
// at G+13+a; chain stage s of logical word g at G+13+g+SK*s.
// ---------------------------------------------------------------------------
module ot_s81hd_elem_r3 #(
    parameter integer LV = 8,              // tree levels above the word node (row = 2^LV words)
    parameter integer PAD = 0,             // golden +0 padding levels after the root (B: 2)
    parameter integer JOIN = 1,            // 1: logit join + argmax (A element)
    parameter integer ROWS = 32,           // rows the element holds (8192 >> LV)
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SPLIT9 = 0,          // ot_v41_fadd SPLIT9 (+1 adder latency, the skew follows)
    parameter integer NC = 1,              // native-census arithmetic + copies (see header)
    parameter integer SK = NC ? 7 : 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8] + SPLIT9,
    parameter INSTANCE = "",
    // IOREG (default 0; redesign pass 2026-10-06): every input captured in a flop at its pin (+1 cycle, uniform);
    // outputs already leave flops (adder output stages, argmax/fault registers): register-to-register boundary
    parameter integer IOREG = 0,
    // SAFE (default 0; redesign SAFE variant 2026-10-06): the argmax compare is registered (take decided in one
    // cycle, applied in the next; logits arrive >= 64 cycles apart, a back-to-back key fails closed)
    parameter integer SAFE = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         go,
    input  wire [16:0]  row0,              // JOIN: the global id of the element's first row
    input  wire [255:0] x,                 // skewed x slice, lane l at [16l +: 16]
    input  wire         b_v,               // JOIN: padded root1024 of this element's next row
    input  wire [31:0]  b_d,
    output wire         o_v,               // root stream (A: root4096; B: ((root1024 + 0) + 0))
    output wire [31:0]  o_d,
    output wire         l_v,               // JOIN: logit stream
    output wire [31:0]  l_d,
    // Existing registered pre-argmax payload: physical downstream consumer ABI.
    // Exactly one edge after l_v/l_d; no added state or arithmetic.
    output wire         head_v,
    output wire [31:0]  head_d,
    output wire [16:0]  head_row,
    output reg          done,              // JOIN: argmax over the element's rows is final
    output reg  [16:0]  best_row,
    output reg  [31:0]  best_bits,
    output reg  [31:0]  best_key,
    output reg          fault
);
    // IOREG: inputs captured at the pins (+1, uniform: go and x move together, the x contract is unchanged)
    wire [3:0] b_v_wr;
    wire go_e, go_e2, go_e3, go_e4, b_v_e;      // go copies: [0] issue / fault / SAFE stage, [1] nrow[8:0], [2] nrow[16:9], [3] argmax control
    wire [16:0] row0_e;
    wire [255:0] x_e;
    wire [31:0] b_d_e;
    generate if (IOREG) begin : g_pin
        (* keep *) reg [3:0] go_q;
        (* keep *) reg [4:0] b_v_q;
        reg [16:0] row0_q;
        reg [255:0] x_q;
        reg [31:0] b_d_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin go_q <= 4'd0; b_v_q <= 5'd0; end
            else begin go_q <= {4{go}}; b_v_q <= {5{b_v}}; end
        always @(posedge clk) begin row0_q <= row0; x_q <= x; b_d_q <= b_d; end
        assign go_e = go_q[0]; assign go_e2 = go_q[1]; assign go_e3 = go_q[2]; assign go_e4 = go_q[3]; assign b_v_e = b_v_q[0]; assign b_v_wr = b_v_q[4:1]; assign row0_e = row0_q; assign x_e = x_q; assign b_d_e = b_d_q;
    end else begin : g_direct
        assign go_e = go; assign go_e2 = go; assign go_e3 = go; assign go_e4 = go; assign b_v_e = b_v; assign b_v_wr = {4{b_v}}; assign row0_e = row0; assign x_e = x; assign b_d_e = b_d;
    end endgenerate
    localparam integer XLEAD = 5;
    localparam integer NW = 8192;
    localparam integer NPHYS = NW + 7 * SK;
    // ---------------- issue: the whole macro, one word a cycle, ping-pong banks ----------------------------------
    reg go_r, run;
    reg [13:0] a;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin go_r <= 1'b0; run <= 1'b0; a <= 14'd0; end
        else begin
            go_r <= go_e;
            // a <= go_r ? 0 : a + run (AND-clear, carry-in increment: no 14-bit go_r / run select)
            a <= (a + {13'd0, run}) & {14{~go_r}};
            if (go_r) run <= 1'b1;
            else if (run && a == NPHYS - 1) run <= 1'b0;
        end
    wire issue = run;
    wire lane0_live = run && a < NW;       // logical word a exists (lane 0 is unskewed)
    // issue -> word register: i1 (t+1), i2 (t+2, bank capture), i3 (t+3, bank select) -> w_r (t+4)
    reg [3:0] iv, il;
    reg [3:0] ib;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv <= 4'd0; il <= 4'd0; end
        else begin iv <= {iv[2:0], issue}; il <= {il[2:0], lane0_live}; end
    always @(posedge clk) ib <= {ib[2:0], a[0]};
    wire [273:0] rd0, rd1;
    reg  [273:0] cap0, cap1;
    // physical closure (route r1): the bank chip enables come straight from flops (ce of word a registered in the
    // cycle before its issue), and the 274-bit capture enables / 256-bit bank select are registered and replicated
    // (RP copies, kept) instead of decoded from iv/ib in front of their loads.  Cycle-identical to issue && a[0].
    localparam integer RP = 18;
    wire last = a == NPHYS - 1;
    reg ce0_q, ce1_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ce0_q <= 1'b0; ce1_q <= 1'b0; end
        else begin
            ce0_q <= go_r || (run && !last && a[0]);
            ce1_q <= !go_r && run && !last && !a[0];
        end
    ot_rom_4096x274_m8
`ifndef SYNTHESIS
        #(.INSTANCE($sformatf("%s_0", INSTANCE)))
`endif
        u_rom0 (.clk(clk), .ce_in(ce0_q), .addr_in(a[12:1]), .rd_out(rd0));
    ot_rom_4096x274_m8
`ifndef SYNTHESIS
        #(.INSTANCE($sformatf("%s_1", INSTANCE)))
`endif
        u_rom1 (.clk(clk), .ce_in(ce1_q), .addr_in(a[12:1]), .rd_out(rd1));
    // a bank's word is captured two edges after its read (2-cycle path, physical/abi3/v41_w10_elem_pp_multicycle.sdc)
    (* keep *) reg [RP-1:0] en0_q, en1_q, sel_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin en0_q <= '0; en1_q <= '0; end
        else begin en0_q <= {RP{iv[0] && !ib[0]}}; en1_q <= {RP{iv[0] && ib[0]}}; end
    always @(posedge clk) sel_q <= {RP{ib[1]}};
    integer bi;
    always @(posedge clk)
        for (bi = 0; bi < 274; bi = bi + 1) begin
            if (en0_q[bi * RP / 274]) cap0[bi] <= rd0[bi];
            if (en1_q[bi * RP / 274]) cap1[bi] <= rd1[bi];
        end
    // word transport: the bank capture flops sit at the macro pins, the word register at the lanes; one register
    // stage between them (route r2: x1 capture flops driving the cross-element wire violated max slew)
    reg [255:0] t_r, w_r, x_t, x_r;
    reg t_v, t_l, w_v, w_l;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin t_v <= 1'b0; t_l <= 1'b0; w_v <= 1'b0; w_l <= 1'b0; end
        else begin t_v <= iv[2]; t_l <= il[2]; w_v <= t_v; w_l <= t_l; end
    integer wi;
    always @(posedge clk) begin
        for (wi = 0; wi < 256; wi = wi + 1) t_r[wi] <= sel_q[wi * RP / 256] ? cap1[wi] : cap0[wi];
        w_r <= t_r;
        x_t <= x_e; x_r <= x_t;
    end

    // ---------------- 16 multipliers, two systolic chunk chains --------------------------------------------------
    wire [31:0] p [0:15];
    wire [15:0] pf;
    genvar l, s;
    generate for (l = 0; l < 16; l = l + 1) begin : g_m
        if (NC) begin : g_nc
            wire [1:0] me;
            wire       mv;
            ot_hdc_fp32_mul_lat_ncr #(.LAT(6)) u_m (.clk(clk), .rst_v({21{rst_n}}), .valid_in(w_v),
                .a({w_r[16*l +: 16], 16'd0}), .a_nrm({2{w_r[16*l +: 16], 16'd0}}), .b({x_r[16*l +: 16], 16'd0}),
                .y(p[l]), .err(me), .valid_out(mv));
            assign pf[l] = me != 2'd0;          // qualified by the chain valid (cerr), as bmul3's fault
        end else begin : g_b3
            ot_dsrom_bmul3 u_m (.clk(clk), .rst_n(rst_n), .v(w_v), .a({w_r[16*l +: 16], 16'd0}), .b({x_r[16*l +: 16], 16'd0}),
                             .y(p[l]), .fault(pf[l]));
        end
    end endgenerate
    reg [5:0] pl;                          // lane-0 live, aligned with the products (bmul3 latency 6)
    always @(posedge clk or negedge rst_n) if (!rst_n) pl <= 6'd0; else pl <= {pl[4:0], w_l};
    wire [31:0] cs [0:1][0:8];
    wire        cv [0:1][0:8];
    wire [1:0]  ce [0:1][0:7];
    reg  [15:0] cerr;
    generate for (l = 0; l < 2; l = l + 1) begin : g_ch
        assign cs[l][0] = 32'd0;
        assign cv[l][0] = pl[5];
        for (s = 0; s < 8; s = s + 1) begin : g_s
            ot_s81hd_fadd #(.NC(NC), .CUT(CUT), .SPLIT9(SPLIT9)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(cv[l][s]), .a(cs[l][s]), .b(p[8*l + s]),
                                          .y(cs[l][s+1]), .err(ce[l][s]), .valid_out(cv[l][s+1]));
            always @(posedge clk or negedge rst_n)
                if (!rst_n) cerr[8*l + s] <= 1'b0;
                else cerr[8*l + s] <= (cv[l][s] && pf[8*l + s]) || (cv[l][s+1] && ce[l][s] != 2'd0);
        end
    end endgenerate
    // level-1 pair add (golden chunk-pair node = one word)
    wire        n1_v;
    wire [31:0] n1_d;
    wire [1:0]  n1_e;
    ot_s81hd_fadd #(.NC(NC), .CUT(CUT), .SPLIT9(SPLIT9)) u_pair (.clk(clk), .rst_n(rst_n), .valid_in(cv[0][8]), .a(cs[0][8]), .b(cs[1][8]),
                                     .y(n1_d), .err(n1_e), .valid_out(n1_v));

    // ---------------- streaming pairwise tree: LV levels, then PAD (+0) levels -----------------------------------
    wire        tv [0:LV+PAD];
    wire [31:0] td [0:LV+PAD];
    wire [1:0]  te [0:LV+PAD];
    assign tv[0] = n1_v; assign td[0] = n1_d; assign te[0] = n1_e;
    reg [LV+PAD:0] terr;
    genvar k;
    generate for (k = 0; k < LV + PAD; k = k + 1) begin : g_t
        if (k < LV) begin : g_pair
            (* keep *) reg [2:0] have;     // kept copies: [0] held[10:0], [1] held[21:11], [2] held[31:22] + valid
            reg [31:0] held;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) have <= 3'd0;
                else if (tv[k]) have <= {3{!have[2]}};
            always @(posedge clk) begin
                if (tv[k] && !have[0]) held[10:0]  <= td[k][10:0];
                if (tv[k] && !have[1]) held[21:11] <= td[k][21:11];
                if (tv[k] && !have[2]) held[31:22] <= td[k][31:22];
            end
            ot_s81hd_fadd #(.NC(NC), .CUT(CUT), .SPLIT9(SPLIT9)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(tv[k] && have[2]), .a(held), .b(td[k]),
                                          .y(td[k+1]), .err(te[k+1]), .valid_out(tv[k+1]));
        end else begin : g_pad
            ot_s81hd_fadd #(.NC(NC), .CUT(CUT), .SPLIT9(SPLIT9)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(tv[k]), .a(td[k]), .b(32'd0),
                                          .y(td[k+1]), .err(te[k+1]), .valid_out(tv[k+1]));
        end
    end endgenerate
    integer q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) terr <= '0;
        else for (q = 0; q <= LV + PAD; q = q + 1) terr[q] <= tv[q] && te[q] != 2'd0;
    assign o_v = tv[LV+PAD];
    assign o_d = td[LV+PAD];

    // ---------------- JOIN: logit = root4096 + padded root1024, then the lowest-id first-max argmax --------------
    reg jerr;
    if (JOIN != 0) begin : g_join
        // root FIFOs (A: own roots; B: the bundle's padded root1024 for this element's rows, in row order)
        reg [31:0] fa [0:1];
        reg [31:0] fb [0:3];
        (* keep *) reg [3:0] fa_w;         // kept copies: fa_w[c] writes bits 8c +: 8
        (* keep *) reg [7:0] fb_w;         // kept copies: fb_w[2c +: 2] writes bits 8c +: 8
        (* keep *) reg [3:0] fa_r;         // kept copies: fa_r[c] reads bits 8c +: 8
        (* keep *) reg [15:0] fb_r;        // kept copies: fb_r[2c +: 2] reads bits 4c +: 4
        reg [1:0] fa_n;
        reg [2:0] fb_n;
        wire pop = fa_n != 2'd0 && fb_n != 3'd0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin fa_w <= 4'd0; fa_r <= 4'd0; fb_w <= 8'd0; fb_r <= 16'd0; fa_n <= 2'd0; fb_n <= 3'd0; jerr <= 1'b0; end
            else begin
                if (o_v) fa_w <= {4{!fa_w[0]}};
                if (b_v_e) fb_w <= {4{fb_w[1:0] + 2'd1}};
                if (pop) begin fa_r <= {4{!fa_r[0]}}; fb_r <= {8{fb_r[1:0] + 2'd1}}; end
                fa_n <= fa_n + {1'b0, o_v} - {1'b0, pop};
                fb_n <= fb_n + {2'd0, b_v_e} - {2'd0, pop};
                jerr <= (o_v && !pop && fa_n == 2'd2) || (b_v_e && !pop && fb_n == 3'd4);   // overflow: fail closed
            end
        integer wc;
        always @(posedge clk)
            for (wc = 0; wc < 4; wc = wc + 1) begin
                if (o_v) fa[fa_w[wc]][8*wc +: 8] <= o_d[8*wc +: 8];
                if (b_v_wr[wc]) fb[fb_w[2*wc +: 2]][8*wc +: 8] <= b_d_e[8*wc +: 8];
            end
        reg        j_v;
        reg [31:0] j_a, j_b;
        always @(posedge clk or negedge rst_n) if (!rst_n) j_v <= 1'b0; else j_v <= pop;
        // read every cycle (consumed only under j_v): no 64-bit pop enable
        integer jc;
        always @(posedge clk) begin
            for (jc = 0; jc < 4; jc = jc + 1) j_a[8*jc +: 8] <= fa[fa_r[jc]][8*jc +: 8];
            for (jc = 0; jc < 8; jc = jc + 1) j_b[4*jc +: 4] <= fb[fb_r[2*jc +: 2]][4*jc +: 4];
        end
        wire [1:0] le;
        ot_s81hd_fadd #(.NC(NC), .CUT(CUT), .SPLIT9(SPLIT9)) u_join (.clk(clk), .rst_n(rst_n), .valid_in(j_v), .a(j_a), .b(j_b),
                                         .y(l_d), .err(le), .valid_out(l_v));
        // argmax: registered key, then compare (rows arrive in increasing id)
        reg        k_v, k_bad;
        reg [31:0] k_bits;
        wire [31:0] k_key;
        reg [16:0] k_row, nrow;
        reg [6:0]  cnt;
        assign head_v = k_v;
        assign head_d = k_bits;
        assign head_row = k_row;
        // stage K1 registers the logit / row / bad with its valid; the key unit (2 stages) runs beside it, so the key
        // register k_key and the K2 copies of K1 meet one edge later than the original single key stage
        reg        k1_v, k1_bad;
        reg [31:0] k1_bits;
        reg [16:0] k1_row;
        wire [31:0] kk;
        ot_s81hd_key u_lkey (.ck(clk), .x(l_d), .key(kk));    // registered: valid with k_v (2 edges after l_v)
        assign k_key = kk;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin k1_v <= 1'b0; k_v <= 1'b0; end
            else begin k1_v <= l_v; k_v <= k1_v; end
        // row counter: nrow counts the logits already keyed (increment at K1, so it holds this logit's id at l_v)
        always @(posedge clk) begin
            nrow[8:0]  <= go_e2 ? row0_e[8:0]  : nrow[8:0] + {8'd0, k1_v};
            nrow[16:9] <= go_e3 ? row0_e[16:9] : nrow[16:9] + {7'd0, k1_v & (&nrow[8:0])};
        end
        always @(posedge clk) begin               // every cycle (consumed only under k1_v / k_v): no wide enable
            k1_bits <= l_d; k1_row <= nrow; k1_bad <= le != 2'd0 || l_d[30:23] == 8'hff;
            k_bits <= k1_bits; k_row <= k1_row; k_bad <= k1_bad;
        end
        reg have;
        wire take = !have || k_key > best_key || (k_key == best_key && k_row < best_row);
        // SAFE: stage the key and its decision (u_v/u_take), apply one cycle later
        wire        u_v, u_take, u_bad;
        wire [31:0] u_key, u_bits;
        wire [16:0] u_row;
        reg         b2b;
        // SAFE (required): stage the key and its decision, apply one cycle later; the staged valid / take / bad are three
        // kept copies, one per best register group (key | bits | row + control)
        // copies: [3:0] best_key bytes, [7:4] best_bits bytes, [8] best_row[8:0], [9] best_row[16:9] + control
        (* keep *) reg [9:0] sv, st, sb;
        reg [31:0] skey, sbits;
        reg [16:0] srow;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sv <= 10'd0; b2b <= 1'b0; end
            else begin sv <= {10{k_v && !go_e}}; b2b <= k_v && sv[9]; end
        always @(posedge clk) begin st <= {10{take}}; sb <= {10{k_bad}}; skey <= k_key; sbits <= k_bits; srow <= k_row; end
        assign u_v = sv[9]; assign u_take = st[9]; assign u_bad = sb[9]; assign u_key = skey; assign u_bits = sbits; assign u_row = srow;
`ifndef SYNTHESIS
        initial if (SAFE == 0) $fatal(1, "ot_s81hd_elem: SAFE = 1 required (census-safe registered argmax apply)");
`endif
        // best registers: datapath (no reset; `have` gates the first take), one enable copy per byte / row half
        integer bc;
        always @(posedge clk)
            for (bc = 0; bc < 4; bc = bc + 1) begin
                if (!go_e4 && sv[bc] && !sb[bc] && st[bc]) best_key[8*bc +: 8] <= skey[8*bc +: 8];
                if (!go_e4 && sv[4 + bc] && !sb[4 + bc] && st[4 + bc]) best_bits[8*bc +: 8] <= sbits[8*bc +: 8];
            end
        always @(posedge clk) if (!go_e4 && sv[8] && !sb[8] && st[8]) best_row[8:0] <= srow[8:0];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin have <= 1'b0; cnt <= 7'd0; done <= 1'b0; end
            else if (go_e4) begin have <= 1'b0; cnt <= 7'd0; done <= 1'b0; end
            else if (u_v) begin
                cnt <= cnt + 7'd1;
                if (cnt == ROWS - 1) done <= 1'b1;
                if (!u_bad && u_take) have <= 1'b1;
            end
        always @(posedge clk) if (!go_e4 && sv[9] && !sb[9] && st[9]) best_row[16:9] <= srow[16:9];
        reg kerr;
        always @(posedge clk or negedge rst_n) if (!rst_n) kerr <= 1'b0; else kerr <= (u_v && u_bad) || b2b;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) fault <= 1'b0;
            else if (go_e) fault <= 1'b0;
            else if ((|cerr) || (|terr) || jerr || kerr) fault <= 1'b1;
    end else begin : g_nojoin
        assign l_v = 1'b0;
        assign l_d = 32'd0;
        assign head_v = 1'b0;
        assign head_d = 32'd0;
        assign head_row = 17'd0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin fault <= 1'b0; done <= 1'b0; best_row <= 17'd0; best_bits <= 32'd0; best_key <= 32'd0; jerr <= 1'b0; end
            else if (go_e) fault <= 1'b0;
            else if ((|cerr) || (|terr)) fault <= 1'b1;
    end
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_bundle (S81-HEAD HD-TILE 10-21): copy of rtl/v41rom/ot_dsrom_head_bundle.sv on the census-safe element
// ot_s81hd_elem (SAFE = 1 required); the B root register bd_r loads every cycle (read only one edge after bo_v through
// bv_r, so no 32-bit bo_v enable); res_v is blocked for a_go + 3 cycles (stale re-raise fix, below).  Same ports,
// arithmetic and go -> result timing.  Original header follows.
// ---------------------------------------------------------------------------
// ot_dsrom_head_bundle: the replicated unit of the DS-ROM lm_head at the ROM read rate (recovery lever "head").
// 5 logical macros = 10 x ot_rom_4096x274_m8 hold 128 vocabulary rows exactly (zero spare words, as S81's 2,525
// ROM4096 a rank = 252.5 bundles):
//   A elements q = 0..3  (ot_dsrom_head_elem LV 8, JOIN): rows row0 + 32q + k (k = 0..31), K 0..4095, 256 words a row
//   B element            (ot_dsrom_head_elem LV 6, PAD 2): K 4096..5119 of all 128 rows, 64 words a row, row order
//                        n = 4k + q, so A element q's next padded root1024 is ready when (or before) its root4096 is
// x: two unskewed slice streams (xa: K 0..4095, xb: K 4096..5119; slice m = 16 BF16 of word m mod 256 / 64), BST
// registered broadcast stages, then the systolic lane skew (lane j delayed SK x (j mod 8)) shared by the bundle.
// Argmax: the 4 elements' lowest-id first-max results meet in a 2-level registered compare tree (same key / tie rule),
// the rank continues the same tree over its bundles.
// Timing: `go` at G; xa/xb must carry slice m at cycle G + 5 + m (m = 0 .. 8192 + 7 SK - 1).
// ---------------------------------------------------------------------------
module ot_s81hd_bundle_r3 #(
    parameter integer BST = 2,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SPLIT9 = 0,          // ot_v41_fadd SPLIT9 (+1 adder latency, the skew follows)
    parameter integer NC = 1,              // ot_s81hd_elem NC: native-census arithmetic (adder LAT 7 -> SK 7)
    parameter integer SK = NC ? 7 : 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8] + SPLIT9,
    parameter INSTANCE = "h",
    parameter integer IOREG = 0,           // ot_dsrom_head_elem IOREG (pin-registered elements)
    parameter integer SAFE = 1,            // ot_s81hd_elem SAFE (registered argmax compare; required)
    parameter integer A_INPUT_STAGES = 0   // opt-in aligned A transport; model prices every added cycle
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         go,
    input  wire [16:0]  row0,
    input  wire [255:0] xa,
    input  wire [255:0] xb,
    output reg          res_v,
    output reg  [16:0]  res_row,
    output reg  [31:0]  res_bits,
    output wire         fault,
    output wire [3:0]   head_v,
    output wire [127:0] head_d,
    output wire [67:0]  head_row
);
    // registered broadcast
    wire        go_d;
    wire [511:0] x_d;
    ot_hdc_delay #(.W(1), .D(BST), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go), .q(go_d));
    ot_hdc_delay #(.W(512), .D(BST)) u_x (.clk(clk), .rst_n(rst_n), .d({xa, xb}), .q(x_d));
    // systolic lane skew
    wire [255:0] xsa, xsb;
    genvar j, q;
    generate for (j = 0; j < 16; j = j + 1) begin : g_sk
        ot_hdc_delay #(.W(16), .D(SK * (j % 8))) u_a (.clk(clk), .rst_n(rst_n), .d(x_d[256 + 16*j +: 16]), .q(xsa[16*j +: 16]));
        ot_hdc_delay #(.W(16), .D(SK * (j % 8))) u_b (.clk(clk), .rst_n(rst_n), .d(x_d[16*j +: 16]), .q(xsb[16*j +: 16]));
    end endgenerate
    // B element and its root demux (row order n = 4k + q)
    wire        bo_v;
    wire [31:0] bo_d;
    wire        b_fault;
    wire        nc_lv, nc_done;
    wire [31:0] nc_ld, nc_bits, nc_key;
    wire [16:0] nc_row;
    ot_s81hd_elem_r3 #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(CUT), .INSTANCE($sformatf("%sb", INSTANCE)), .IOREG(IOREG), .SAFE(SAFE), .SPLIT9(SPLIT9), .NC(NC), .SK(SK)) u_b (
        .clk(clk), .rst_n(rst_n), .go(go_d), .row0(17'd0), .x(xsb), .b_v(1'b0), .b_d(32'd0), .o_v(bo_v), .o_d(bo_d),
        .l_v(nc_lv), .l_d(nc_ld), .done(nc_done), .best_row(nc_row), .best_bits(nc_bits), .best_key(nc_key),
        .fault(b_fault));
    reg [1:0]  bq;
    reg [3:0]  bv_r;
    reg [31:0] bd_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin bq <= 2'd0; bv_r <= 4'd0; end
        else begin
            if (go_d) bq <= 2'd0; else if (bo_v) bq <= bq + 2'd1;
            bv_r <= bo_v ? (4'd1 << bq) : 4'd0;
        end
    always @(posedge clk) bd_r <= bo_d;                  // consumed one edge after bo_v (bv_r)
    // A elements
    wire [3:0]  a_done, a_fault;
    wire [16:0] a_row [0:3];
    wire [31:0] a_bits [0:3];
    wire [31:0] a_key [0:3];
    wire [3:0] a_go;
    generate for (q = 0; q < 4; q = q + 1) begin : g_a
        wire ov, lv;
        wire [31:0] od, ld;
        wire [16:0] row_a;
        wire [16:0] row_in = row0 + 17'd32 * q;
        wire [255:0] x_a;
        wire bv_a;
        wire [31:0] bd_a;
        // All 307 bits use the same depth. Validity alone resets; payload
        // travels continuously, retaining the original systolic and B join alignment.
        // Physical implementation must land these groups at the actual A faces.
        ot_hdc_delay #(.W(2), .D(A_INPUT_STAGES), .RESET(1)) u_av (
            .clk(clk), .rst_n(rst_n), .d({go_d, bv_r[q]}), .q({a_go[q], bv_a}));
        ot_hdc_delay #(.W(305), .D(A_INPUT_STAGES)) u_ad (
            .clk(clk), .rst_n(rst_n), .d({row_in, xsa, bd_r}), .q({row_a, x_a, bd_a}));
        ot_s81hd_elem_r3 #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(CUT), .INSTANCE($sformatf("%sa%0d", INSTANCE, q)), .IOREG(IOREG), .SAFE(SAFE), .SPLIT9(SPLIT9), .NC(NC), .SK(SK)) u_e (
            .clk(clk), .rst_n(rst_n), .go(a_go[q]), .row0(row_a), .x(x_a), .b_v(bv_a), .b_d(bd_a),
            .o_v(ov), .o_d(od), .l_v(lv), .l_d(ld),
            .head_v(head_v[q]), .head_d(head_d[32*q+:32]), .head_row(head_row[17*q+:17]), .done(a_done[q]), .best_row(a_row[q]), .best_bits(a_bits[q]),
            .best_key(a_key[q]), .fault(a_fault[q]));
    end endgenerate
    // 2-level compare tree (lowest-id first max), census-safe (HD-TILE): each level registers its decision as 11 kept
    // copies (one per <= 8 of the 81 {key, row, bits} bits; a mapped select costs 2 load pins a bit), then selects in
    // the next cycle.  The element bests are stable from done until the next go, so the decisions recompute every
    // cycle; valid runs 4 stages (+2 against the original tree) and is blocked for a_go + 3 cycles: the elements
    // clear `done` IOREG (+1) edges after a_go (the original re-raised res_v with the PREVIOUS result after a later go).
    function automatic vbetter(input [80:0] u, input [80:0] v);   // {key, row, bits}: v replaces u
        vbetter = v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32]);
    endfunction
    wire [80:0] e0 = {a_key[0], a_row[0], a_bits[0]}, e1 = {a_key[1], a_row[1], a_bits[1]};
    wire [80:0] e2 = {a_key[2], a_row[2], a_bits[2]}, e3 = {a_key[3], a_row[3], a_bits[3]};
    (* keep *) reg [10:0] s01, s23, sf;
    reg [80:0] c1a, c1b;
    reg [2:0]  gsh;
    reg        v1, v2, v3;
    wire       gblk = a_go[0] | (|gsh);
    integer bb;
    always @(posedge clk) begin
        s01 <= {11{vbetter(e0, e1)}};
        s23 <= {11{vbetter(e2, e3)}};
        for (bb = 0; bb < 81; bb = bb + 1) begin
            c1a[bb] <= s01[bb / 8] ? e1[bb] : e0[bb];
            c1b[bb] <= s23[bb / 8] ? e3[bb] : e2[bb];
        end
        sf <= {11{vbetter(c1a, c1b)}};
        for (bb = 0; bb < 32; bb = bb + 1) res_bits[bb] <= sf[bb / 8] ? c1b[bb] : c1a[bb];
        for (bb = 32; bb < 49; bb = bb + 1) res_row[bb - 32] <= sf[bb / 8] ? c1b[bb] : c1a[bb];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; res_v <= 1'b0; gsh <= 3'd0; end
        else begin
            gsh <= {gsh[1:0], a_go[0]};
            v1 <= &a_done && !gblk;
            v2 <= v1 && !gblk;
            v3 <= v2 && !gblk;
            res_v <= v3 && !gblk;
        end
    assign fault = b_fault | (|a_fault);
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_tile (S81-HEAD HD-TILE 10-21; spec results/arch/s81_head_1021/SPEC.md sections 1, 2, 6): the LM-head array
// tile of the S81 release head die.  One ot_s81hd_bundle (census-safe copy of ot_dsrom_head_bundle: 5 elements,
// 10 x ot_rom_4096x274_m8, 128 vocabulary rows row0 .. row0 + 127) on the array bus B (565 b):
//   [511:0] x (xa = [255:0] K 0..4095 slice stream, xb = [511:256] K 4096..5119), [512] go, [513] xv,
//   [514] rv, [531:515] row, [563:532] bits (FP32 logit), [564] flt (OR-accumulated).
// Per tile:
//   * x / go / xv: two registered cycles (W-face pin register -> E-face output register): the tile pitch (~648 um)
//     exceeds the 405 um single-cycle planning reach, so a pass-through register sits at each face (+1 cycle a tile
//     against SPEC v1's one cycle; <= 10 cycles a 10-tile chain, handed to the calendar).  The bundle sees the pin
//     register's x / go, so its contract "go at G, slice m at G + 5 + m" holds at every tile (go travels with x).
//   * best: the chain best (i.rv pulse with row / bits / flt) and the tile's own bundle result (when ten = 1) are
//     captured in either order; when both are present the tile fires ONCE per position (cleared by go) with
//     max(chain, own) under the ot_rom_argmax_rows key (FP32 order, -0 = +0, lowest row id on ties).  ten = 0
//     (strap) excludes the bundle (its go is gated, its fault masked): the tile forwards the chain best.
//   * flt: chain flt OR (ten & bundle fault) (the bundle fault is sticky until the bundle's next go).
//   * pins: every input lands in a flop (W face), every output leaves a flop (E face); no combinational in -> out.
//   * reset: control / valid bits only (go, xv, rv copies, capture / fire state); the 2-stage landing at the face and
//     the kept reset copies are the kit's (reset_landing + reset_relay_split, mapped <= 32 loads per copy).
//   * fanout (census: <= 32 load pins a driver; a mapped select / enable costs 2 pins a bit): the 50-bit chain-best
//     hold is enabled by 5 kept rv copies (<= 11 bits each), the output select by 7 kept copies (<= 8 bits each); the
//     FP32 order keys come from ot_s81hd_key (2 registered stages, kept sign / -0 copies per byte).
// Latency: own result at go_tile + 1 + BUNDLE_LAT; fire = 4 edges after both are present (2 key stages, select
// register, output register).  A position's chain best and own result must both arrive before the next go reaches the tile (static
// schedule: positions >= 8,357 cycles apart; no backpressure).
// The bundle's head_v / head_d / head_row pre-argmax outputs stay internal (unused).
// ---------------------------------------------------------------------------
module ot_s81hd_tile_r3_core #(
    parameter INSTANCE = "h",                // ROM image prefix (simulation only)
    parameter integer IOREG = 1,             // ot_s81hd_elem pin-registered inputs
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SPLIT9 = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [564:0] i,
    output wire [564:0] o,
    input  wire [16:0]  row0,
    input  wire         ten
);
    // ---------------- pin registers --------------------------------------------------------------------------------
    reg [511:0] x_q;
    reg         go_q, xv_q;
    (* keep *) reg [4:0] rv_q;               // kept copies: [0] row[8:0] [1] row[16:9] + flt [2] bits[10:0] [3] bits[21:11] [4] bits[31:22] + state
    reg [16:0]  row_q;
    reg [31:0]  bits_q;
    reg         flt_q;
    reg [16:0]  row0_q;                      // straps (static)
    reg         ten_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin go_q <= 1'b0; xv_q <= 1'b0; rv_q <= 5'd0; end
        else begin go_q <= i[512]; xv_q <= i[513]; rv_q <= {5{i[514]}}; end
    always @(posedge ck) begin
        x_q <= i[511:0]; row_q <= i[531:515]; bits_q <= i[563:532]; flt_q <= i[564];
        row0_q <= row0; ten_q <= ten;
    end
    // E-face output register of the x stream (second pass-through stage)
    reg [511:0] xo_q;
    reg         goo_q, xvo_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin goo_q <= 1'b0; xvo_q <= 1'b0; end
`ifdef OT_S81HD_MUT_GO_DROP
        else begin goo_q <= 1'b0; xvo_q <= xv_q; end                  // MUTANT: go not forwarded
`else
        else begin goo_q <= go_q; xvo_q <= xv_q; end
`endif
    always @(posedge ck) xo_q <= x_q;

    // ---------------- bundle -----------------------------------------------------------------------------------------
    wire        b_go = go_q & ten_q;
`ifdef OT_S81HD_MUT_TEN_IGNORED
    wire        b_en = 1'b1;                 // MUTANT: ten ignored (bundle always runs and merges)
`else
    wire        b_en = ten_q;
`endif
    wire        res_v, b_fault;
    wire [16:0] res_row;
    wire [31:0] res_bits;
    wire [3:0]   nc_hv;
    wire [127:0] nc_hd;
    wire [67:0]  nc_hr;
    ot_s81hd_bundle_r3 #(.INSTANCE(INSTANCE), .IOREG(IOREG), .SAFE(1), .CUT(CUT), .SPLIT9(SPLIT9)) u_b (
        .clk(ck), .rst_n(rst_n),
`ifdef OT_S81HD_MUT_TEN_IGNORED
        .go(go_q),
`else
        .go(b_go),
`endif
        .row0(row0_q), .xa(x_q[255:0]), .xb(x_q[511:256]),
        .res_v(res_v), .res_row(res_row), .res_bits(res_bits), .fault(b_fault),
        .head_v(nc_hv), .head_d(nc_hd), .head_row(nc_hr));

    // ---------------- chain best hold (enabled by kept rv copies) -----------------------------------------------------
    reg [16:0] ch_row;
    reg [31:0] ch_bits;
    reg        ch_flt;
    always @(posedge ck) begin
        if (rv_q[0]) ch_row[8:0] <= row_q[8:0];
        if (rv_q[1]) begin ch_row[16:9] <= row_q[16:9]; ch_flt <= flt_q; end
        if (rv_q[2]) ch_bits[10:0] <= bits_q[10:0];
        if (rv_q[3]) ch_bits[21:11] <= bits_q[21:11];
        if (rv_q[4]) ch_bits[31:22] <= bits_q[31:22];
    end
    // order keys (2 registered stages): chain best (held) and own result (stable from res_v until the bundle's next go)
    wire [31:0] k_own, k_ch;
    ot_s81hd_key u_kc (.ck(ck), .x(ch_bits), .key(k_ch));
    ot_s81hd_key u_ko (.ck(ck), .x(res_bits), .key(k_own));

    // ---------------- capture state, fire once per position ---------------------------------------------------------
    // own result: the rising edge of the bundle's res_v (a level until the bundle's next go) after this position's go
    // the keys trail their values by 2 edges: ready waits on the have flags delayed by 2
    reg res_v_d, ch_have, ch_d1, ch_d2, own_have, own_d1, own_d2, fired, sel_v, o_rv;
    wire res_rise = res_v & ~res_v_d;
    wire ready = ch_d2 & (own_d2 | ~b_en) & ~fired & ~go_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin res_v_d <= 1'b0; ch_have <= 1'b0; ch_d1 <= 1'b0; ch_d2 <= 1'b0; own_have <= 1'b0; own_d1 <= 1'b0;
                          own_d2 <= 1'b0; fired <= 1'b0; sel_v <= 1'b0; o_rv <= 1'b0; end
        else begin
            res_v_d  <= res_v;
            ch_have  <= rv_q[4] | (ch_have & ~go_q);
            ch_d1    <= ch_have & ~go_q;
            ch_d2    <= ch_d1 & ~go_q;
            own_have <= (res_rise & b_en) | (own_have & ~go_q);
            own_d1   <= own_have & ~go_q;
            own_d2   <= own_d1 & ~go_q;
            fired    <= ready | (fired & ~go_q);
            sel_v    <= ready;
            o_rv     <= sel_v;
        end

    // ---------------- max under the ot_rom_argmax_rows key ----------------------------------------------------------
`ifdef OT_S81HD_MUT_TIE_FLIP
    wire own_better = b_en && (k_own > k_ch || (k_own == k_ch && res_row > ch_row));   // MUTANT: highest id on ties
`else
    wire own_better = b_en && (k_own > k_ch || (k_own == k_ch && res_row < ch_row));
`endif
    (* keep *) reg [6:0] sel_q;              // kept copies: [2:0] row [5:0] [11:6] [16:12], [6:3] bits bytes
    reg        bflt_q;
    always @(posedge ck) begin
        sel_q  <= {7{own_better}};
`ifdef OT_S81HD_MUT_FLT_DROP
        bflt_q <= 1'b0;                      // MUTANT: bundle fault dropped
`else
        bflt_q <= b_en & b_fault;
`endif
    end
    reg [16:0] o_row;
    reg [31:0] o_bits;
    reg        o_flt;
    integer b;
    always @(posedge ck) begin
        for (b = 0; b < 17; b = b + 1) o_row[b] <= sel_q[b < 6 ? 0 : (b < 12 ? 1 : 2)] ? res_row[b] : ch_row[b];
        for (b = 0; b < 32; b = b + 1) o_bits[b] <= sel_q[3 + b / 8] ? res_bits[b] : ch_bits[b];
        o_flt <= ch_flt | bflt_q;
    end

    assign o = {o_flt, o_bits, o_row, o_rv, xvo_q, goo_q, xo_q};
endmodule
