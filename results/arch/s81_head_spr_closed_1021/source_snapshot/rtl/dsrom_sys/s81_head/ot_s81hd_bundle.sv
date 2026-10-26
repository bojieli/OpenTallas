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
module ot_s81hd_bundle #(
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
    ot_s81hd_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(CUT), .INSTANCE($sformatf("%sb", INSTANCE)), .IOREG(IOREG), .SAFE(SAFE), .SPLIT9(SPLIT9), .NC(NC), .SK(SK)) u_b (
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
        ot_s81hd_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(CUT), .INSTANCE($sformatf("%sa%0d", INSTANCE, q)), .IOREG(IOREG), .SAFE(SAFE), .SPLIT9(SPLIT9), .NC(NC), .SK(SK)) u_e (
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
