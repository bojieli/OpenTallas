`timescale 1ns/1ps
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
module ot_dsrom_head_bundle #(
    parameter integer BST = 2,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SK = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    parameter INSTANCE = "h"
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
    output wire         fault
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
    ot_dsrom_head_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(CUT), .INSTANCE($sformatf("%sb", INSTANCE))) u_b (
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
    always @(posedge clk) if (bo_v) bd_r <= bo_d;
    // A elements
    wire [3:0]  a_done, a_fault;
    wire [16:0] a_row [0:3];
    wire [31:0] a_bits [0:3];
    wire [31:0] a_key [0:3];
    generate for (q = 0; q < 4; q = q + 1) begin : g_a
        wire ov, lv;
        wire [31:0] od, ld;
        ot_dsrom_head_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(CUT), .INSTANCE($sformatf("%sa%0d", INSTANCE, q))) u_e (
            .clk(clk), .rst_n(rst_n), .go(go_d), .row0(row0 + 17'd32 * q), .x(xsa), .b_v(bv_r[q]), .b_d(bd_r),
            .o_v(ov), .o_d(od), .l_v(lv), .l_d(ld), .done(a_done[q]), .best_row(a_row[q]), .best_bits(a_bits[q]),
            .best_key(a_key[q]), .fault(a_fault[q]));
    end endgenerate
    // 2-level compare tree (lowest-id first max): level 1 (0,1) (2,3), level 2
    function automatic [80:0] pick(input [80:0] u, input [80:0] v);   // {key, row, bits}
        pick = (v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32])) ? v : u;
    endfunction
    reg [80:0] c1 [0:1];
    reg        c1_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c1_v <= 1'b0; res_v <= 1'b0; end
        else begin
            c1_v <= &a_done && !go_d;
            res_v <= c1_v && !go_d;
        end
    always @(posedge clk) begin
        c1[0] <= pick({a_key[0], a_row[0], a_bits[0]}, {a_key[1], a_row[1], a_bits[1]});
        c1[1] <= pick({a_key[2], a_row[2], a_bits[2]}, {a_key[3], a_row[3], a_bits[3]});
        {res_row, res_bits} <= pick(c1[0], c1[1]);
    end
    assign fault = b_fault | (|a_fault);
endmodule
