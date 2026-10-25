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
// CV element parameters: simulation models take the ROM image prefix; the synthesis black boxes take none.
`ifdef SYNTHESIS
`define OT_S81HD_CVP(X)
`else
`define OT_S81HD_CVP(X) #(.INSTANCE(X))
`endif
module ot_s81hd_bundle #(
    parameter integer BST = 2,
    parameter [8:0] CUT = 9'b1_1111_1111,  // 10-24: the closed element views' CUT (was 0x17b)
    parameter integer SPLIT9 = 1,          // ot_v41_fadd SPLIT9 (+1 adder latency, the skew follows); 10-24: 1 (was 0)
    parameter integer SK = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8] + SPLIT9,
    parameter INSTANCE = "h",
    parameter integer IOREG = 0,           // ot_dsrom_head_elem IOREG (pin-registered elements)
    parameter integer SAFE = 1,            // ot_s81hd_elem SAFE (registered argmax compare; required)
    parameter integer A_INPUT_STAGES = 0,  // opt-in aligned A transport; model prices every added cycle
    // MERGE_HOP (S81-HEAD 10-24 hd_tile preview review: c1 -144 / res -288 ps at placement, the four A results meet
    // from cores 350-700 um apart): 1 = a hop register before each compare level (pk_q -> pk_h -> c1 -> c1_h -> res),
    // so a stage does EITHER the ~350-um hop OR the 81-b pick.  +2 cycles on the result; 0 = unchanged.
    parameter integer MERGE_HOP = 0,
    // CV (S81-HEAD 10-24): 1 = the elements are the CLOSED views (physical/dsrom_fh_safe/closed/elem{A,B}) as the hard
    // macros ot_s81hd_elemA_cv (u_eA0..3) / ot_s81hd_elemB_cv (u_eB) in the labelled block g_cv (no generate index in
    // their paths); they are the closed parameter point (CUT 0x1ff, SPLIT9 1, IOREG 1, SAFE 1), checked below.
    // head_v / head_d / head_row are not view pins: 0 under CV (the tile leaves them unused).
    parameter integer CV = 0
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
    generate if (CV) begin : g_cvb
        ot_s81hd_elemB_cv `OT_S81HD_CVP($sformatf("%sb", INSTANCE)) u_eB (
            .clk(clk), .rst_n(rst_n), .go(go_d), .row0(17'd0), .x(xsb), .b_v(1'b0), .b_d(32'd0), .o_v(bo_v), .o_d(bo_d),
            .l_v(nc_lv), .l_d(nc_ld), .done(nc_done), .best_row(nc_row), .best_bits(nc_bits), .best_key(nc_key),
            .fault(b_fault));
    end else begin : g_rtlb
        ot_s81hd_elem #(.LV(6), .PAD(2), .JOIN(0), .ROWS(128), .CUT(CUT), .INSTANCE($sformatf("%sb", INSTANCE)), .IOREG(IOREG), .SAFE(SAFE), .SPLIT9(SPLIT9)) u_b (
            .clk(clk), .rst_n(rst_n), .go(go_d), .row0(17'd0), .x(xsb), .b_v(1'b0), .b_d(32'd0), .o_v(bo_v), .o_d(bo_d),
            .l_v(nc_lv), .l_d(nc_ld), .done(nc_done), .best_row(nc_row), .best_bits(nc_bits), .best_key(nc_key),
            .fault(b_fault));
    end endgenerate
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
    wire [16:0]  row_a [0:3];
    wire [255:0] x_a [0:3];
    wire [3:0]   bv_a;
    wire [31:0]  bd_a [0:3];
    generate for (q = 0; q < 4; q = q + 1) begin : g_a
        wire ov, lv;
        wire [31:0] od, ld;
        wire [16:0] row_in = row0 + 17'd32 * q;
        // All 307 bits use the same depth. Validity alone resets; payload
        // travels continuously, retaining the original systolic and B join alignment.
        // Physical implementation must land these groups at the actual A faces.
        ot_hdc_delay #(.W(2), .D(A_INPUT_STAGES), .RESET(1)) u_av (
            .clk(clk), .rst_n(rst_n), .d({go_d, bv_r[q]}), .q({a_go[q], bv_a[q]}));
        ot_hdc_delay #(.W(305), .D(A_INPUT_STAGES)) u_ad (
            .clk(clk), .rst_n(rst_n), .d({row_in, xsa, bd_r}), .q({row_a[q], x_a[q], bd_a[q]}));
        if (!CV) begin : g_rtl
        ot_s81hd_elem #(.LV(8), .PAD(0), .JOIN(1), .ROWS(32), .CUT(CUT), .INSTANCE($sformatf("%sa%0d", INSTANCE, q)), .IOREG(IOREG), .SAFE(SAFE), .SPLIT9(SPLIT9)) u_e (
            .clk(clk), .rst_n(rst_n), .go(a_go[q]), .row0(row_a[q]), .x(x_a[q]), .b_v(bv_a[q]), .b_d(bd_a[q]),
            .o_v(ov), .o_d(od), .l_v(lv), .l_d(ld),
            .head_v(head_v[q]), .head_d(head_d[32*q+:32]), .head_row(head_row[17*q+:17]), .done(a_done[q]), .best_row(a_row[q]), .best_bits(a_bits[q]),
            .best_key(a_key[q]), .fault(a_fault[q]));
        end
    end endgenerate
    generate if (CV) begin : g_cv
        // closed-view parameter point (ot_dsrom_head_elem IOREG 1 SAFE 1 CUT 0x1ff SPLIT9 1): refuse anything else
        // A_INPUT_STAGES is tile-side transport (all 307 A input bits + go/bv at equal depth): allowed with the views
        if (CUT != 9'h1ff || SPLIT9 != 1 || IOREG != 1 || SAFE != 1) begin : g_bad
            ot_s81hd_cv_params_differ_from_the_closed_views u_refuse ();   // elaboration error by design
        end
        wire [3:0] ov, lv;
        wire [31:0] od [0:3];
        wire [31:0] ld [0:3];
        assign head_v = 4'd0;
        assign head_d = 128'd0;
        assign head_row = 68'd0;
`define OT_S81HD_EA(Q) \
        ot_s81hd_elemA_cv `OT_S81HD_CVP($sformatf("%sa%0d", INSTANCE, Q)) u_eA``Q ( \
            .clk(clk), .rst_n(rst_n), .go(a_go[Q]), .row0(row_a[Q]), .x(x_a[Q]), .b_v(bv_a[Q]), .b_d(bd_a[Q]), \
            .o_v(ov[Q]), .o_d(od[Q]), .l_v(lv[Q]), .l_d(ld[Q]), .done(a_done[Q]), .best_row(a_row[Q]), \
            .best_bits(a_bits[Q]), .best_key(a_key[Q]), .fault(a_fault[Q]));
        `OT_S81HD_EA(0)
        `OT_S81HD_EA(1)
        `OT_S81HD_EA(2)
        `OT_S81HD_EA(3)
`undef OT_S81HD_EA
    end endgenerate
    // 2-level compare tree (lowest-id first max): level 1 (0,1) (2,3), level 2
    function automatic [80:0] pick(input [80:0] u, input [80:0] v);   // {key, row, bits}
        pick = (v[80:49] > u[80:49] || (v[80:49] == u[80:49] && v[48:32] < u[48:32])) ? v : u;
    endfunction
    reg [80:0] c1 [0:1];
    reg        c1_v;
    // S81-HEAD 10-24 (GEOM-REVIEW tile batch 2: u_eA0/best_key -> c1 was a 14-level path across the tile, TT -627 ps):
    // the four A results are registered at the tile side first (pk_q, next to each element's E face), the level-1
    // compare starts from local flops.  +1 cycle on the result; the go block window grows by one (gsh 4).
    reg [80:0] pk_q [0:3];
    reg [3:0]  pk_done;
    // HD-TILE 10-21: the elements clear `done` IOREG (+1) edges after a_go, so with IOREG = 1 the original
    // `&a_done && !a_go[0]` re-raised res_v for one cycle with the PREVIOUS position's result after every later go
    // (measured: 2nd position fired 20 cycles after go).  The block window covers a_go + 3 cycles.
    // MERGE_HOP: the block window grows with the two hop stages (the stale done of the previous position travels them)
    localparam integer GW = 4 + 2 * MERGE_HOP;
    reg [GW-1:0] gsh;
    wire       gblk = a_go[0] | (|gsh);
    reg [3:0]  pk_done_h;
    reg        c1_vh;
    wire [3:0] pk_done_m = MERGE_HOP ? pk_done_h : pk_done;
    wire       c1_v_m = MERGE_HOP ? c1_vh : c1_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c1_v <= 1'b0; res_v <= 1'b0; gsh <= {GW{1'b0}}; pk_done <= 4'd0; pk_done_h <= 4'd0; c1_vh <= 1'b0; end
        else begin
            gsh <= {gsh[GW-2:0], a_go[0]};
            pk_done <= a_done;
            pk_done_h <= pk_done;
            c1_v <= &pk_done_m && !gblk;
            c1_vh <= c1_v;
            res_v <= c1_v_m && !gblk;
        end
    reg [80:0] pk_h [0:3];
    reg [80:0] c1_h [0:1];
    always @(posedge clk) begin
        for (int pq = 0; pq < 4; pq++) begin
            pk_q[pq] <= {a_key[pq], a_row[pq], a_bits[pq]};
            pk_h[pq] <= pk_q[pq];
        end
        c1_h[0] <= c1[0];
        c1_h[1] <= c1[1];
        if (MERGE_HOP) begin
            c1[0] <= pick(pk_h[0], pk_h[1]);
            c1[1] <= pick(pk_h[2], pk_h[3]);
            {res_row, res_bits} <= pick(c1_h[0], c1_h[1]);
        end else begin
            c1[0] <= pick(pk_q[0], pk_q[1]);
            c1[1] <= pick(pk_q[2], pk_q[3]);
            {res_row, res_bits} <= pick(c1[0], c1[1]);
        end
    end
    assign fault = b_fault | (|a_fault);
endmodule
