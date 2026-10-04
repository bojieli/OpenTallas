`timescale 1ns/1ps
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
module ot_dsrom_head_elem #(
    parameter integer LV = 8,              // tree levels above the word node (row = 2^LV words)
    parameter integer PAD = 0,             // golden +0 padding levels after the root (B: 2)
    parameter integer JOIN = 1,            // 1: logit join + argmax (A element)
    parameter integer ROWS = 32,           // rows the element holds (8192 >> LV)
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SK = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    parameter INSTANCE = ""
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
    output reg          done,              // JOIN: argmax over the element's rows is final
    output reg  [16:0]  best_row,
    output reg  [31:0]  best_bits,
    output reg  [31:0]  best_key,
    output reg          fault
);
    localparam integer XLEAD = 5;
    localparam integer NW = 8192;
    localparam integer NPHYS = NW + 7 * SK;
    // ---------------- issue: the whole macro, one word a cycle, ping-pong banks ----------------------------------
    reg go_r, run;
    reg [13:0] a;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin go_r <= 1'b0; run <= 1'b0; a <= 14'd0; end
        else begin
            go_r <= go;
            if (go_r) begin run <= 1'b1; a <= 14'd0; end
            else if (run) begin a <= a + 14'd1; if (a == NPHYS - 1) run <= 1'b0; end
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
    localparam integer RP = 8;
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
        x_t <= x; x_r <= x_t;
    end

    // ---------------- 16 multipliers, two systolic chunk chains --------------------------------------------------
    wire [31:0] p [0:15];
    wire [15:0] pf;
    genvar l, s;
    generate for (l = 0; l < 16; l = l + 1) begin : g_m
        ot_dsrom_bmul3 u_m (.clk(clk), .rst_n(rst_n), .v(w_v), .a({w_r[16*l +: 16], 16'd0}), .b({x_r[16*l +: 16], 16'd0}),
                         .y(p[l]), .fault(pf[l]));
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
            ot_v41_fadd #(.CUT(CUT)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(cv[l][s]), .a(cs[l][s]), .b(p[8*l + s]),
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
    ot_v41_fadd #(.CUT(CUT)) u_pair (.clk(clk), .rst_n(rst_n), .valid_in(cv[0][8]), .a(cs[0][8]), .b(cs[1][8]),
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
            reg have;
            reg [31:0] held;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) have <= 1'b0;
                else if (tv[k]) have <= !have;
            always @(posedge clk) if (tv[k] && !have) held <= td[k];
            ot_v41_fadd #(.CUT(CUT)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(tv[k] && have), .a(held), .b(td[k]),
                                          .y(td[k+1]), .err(te[k+1]), .valid_out(tv[k+1]));
        end else begin : g_pad
            ot_v41_fadd #(.CUT(CUT)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(tv[k]), .a(td[k]), .b(32'd0),
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
        reg fa_w, fa_r;
        reg [1:0] fb_w, fb_r;
        reg [1:0] fa_n;
        reg [2:0] fb_n;
        wire pop = fa_n != 2'd0 && fb_n != 3'd0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin fa_w <= 1'b0; fa_r <= 1'b0; fb_w <= 2'd0; fb_r <= 2'd0; fa_n <= 2'd0; fb_n <= 3'd0; jerr <= 1'b0; end
            else begin
                if (o_v) fa_w <= !fa_w;
                if (b_v) fb_w <= fb_w + 2'd1;
                if (pop) begin fa_r <= !fa_r; fb_r <= fb_r + 2'd1; end
                fa_n <= fa_n + {1'b0, o_v} - {1'b0, pop};
                fb_n <= fb_n + {2'd0, b_v} - {2'd0, pop};
                jerr <= (o_v && !pop && fa_n == 2'd2) || (b_v && !pop && fb_n == 3'd4);   // overflow: fail closed
            end
        always @(posedge clk) begin
            if (o_v) fa[fa_w] <= o_d;
            if (b_v) fb[fb_w] <= b_d;
        end
        reg        j_v;
        reg [31:0] j_a, j_b;
        always @(posedge clk or negedge rst_n) if (!rst_n) j_v <= 1'b0; else j_v <= pop;
        always @(posedge clk) if (pop) begin j_a <= fa[fa_r]; j_b <= fb[fb_r]; end
        wire [1:0] le;
        ot_v41_fadd #(.CUT(CUT)) u_join (.clk(clk), .rst_n(rst_n), .valid_in(j_v), .a(j_a), .b(j_b),
                                         .y(l_d), .err(le), .valid_out(l_v));
        // argmax: registered key, then compare (rows arrive in increasing id)
        reg        k_v, k_bad;
        reg [31:0] k_key, k_bits;
        reg [16:0] k_row, nrow;
        reg [6:0]  cnt;
        wire [31:0] canon = (l_d == 32'h80000000) ? 32'd0 : l_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin k_v <= 1'b0; nrow <= 17'd0; end
            else begin
                k_v <= l_v;
                if (go) nrow <= row0; else if (l_v) nrow <= nrow + 17'd1;
            end
        always @(posedge clk) if (l_v) begin
            k_key <= canon[31] ? ~canon : {1'b1, canon[30:0]};
            k_bits <= l_d; k_row <= nrow;
            k_bad <= le != 2'd0 || l_d[30:23] == 8'hff;
        end
        reg have;
        wire take = !have || k_key > best_key || (k_key == best_key && k_row < best_row);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin have <= 1'b0; cnt <= 7'd0; done <= 1'b0; best_key <= 32'd0; best_row <= 17'd0; best_bits <= 32'd0; end
            else if (go) begin have <= 1'b0; cnt <= 7'd0; done <= 1'b0; end
            else if (k_v) begin
                cnt <= cnt + 7'd1;
                if (cnt == ROWS - 1) done <= 1'b1;
                if (!k_bad && take) begin have <= 1'b1; best_key <= k_key; best_row <= k_row; best_bits <= k_bits; end
            end
        reg kerr;
        always @(posedge clk or negedge rst_n) if (!rst_n) kerr <= 1'b0; else kerr <= k_v && k_bad;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) fault <= 1'b0;
            else if (go) fault <= 1'b0;
            else if ((|cerr) || (|terr) || jerr || kerr) fault <= 1'b1;
    end else begin : g_nojoin
        assign l_v = 1'b0;
        assign l_d = 32'd0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin fault <= 1'b0; done <= 1'b0; best_row <= 17'd0; best_bits <= 32'd0; best_key <= 32'd0; jerr <= 1'b0; end
            else if (go) fault <= 1'b0;
            else if ((|cerr) || (|terr)) fault <= 1'b1;
    end
endmodule
