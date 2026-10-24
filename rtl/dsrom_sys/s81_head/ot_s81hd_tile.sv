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
//   * fanout: the 50-bit chain-best hold is enabled by 3 kept rv copies; the output select by 3 kept copies.
// Latency: own result at go_tile + 1 + BUNDLE_LAT; fire = 2 edges after both are present (select register, output
// register).  A position's chain best and own result must both arrive before the next go reaches the tile (static
// schedule: positions >= 8,357 cycles apart at CUT 0x17b, >= 8,411 at the default CUT 0x1ff / SPLIT9 1; no backpressure).
// 10-24 (S81-HEAD): defaults CUT 0x1ff / SPLIT9 1 = the CLOSED element views' parameters (physical/dsrom_fh_safe/closed/
// elem{A,B}); ot_s81hd_elem at these parameters == the closed RTL (tools/s81_head/hd_elem_eq.sh); +54 cycles vs 0x17b
// (mini array 8,375 -> 8,429, token 21946 exact).  The ROM images follow SK = 11 (tools/s81_head/hd_reskew_images.py).
// The bundle's head_v / head_d / head_row pre-argmax outputs stay internal (unused).
// ---------------------------------------------------------------------------
module ot_s81hd_tile #(
    parameter INSTANCE = "h",                // ROM image prefix (simulation only)
    parameter integer IOREG = 1,             // ot_s81hd_elem pin-registered inputs
    parameter [8:0] CUT = 9'b1_1111_1111,      // 10-24: closed element views (was 0x17b)
    parameter integer SPLIT9 = 1,              // 10-24: closed element views (was 0)
    parameter integer CV = 0                   // 10-24: 1 = elements are the closed-view macros (ot_s81hd_bundle CV)
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
    (* keep *) reg [2:0] rv_q;               // kept copies: [0] row + flt hold, [1] bits[15:0], [2] bits[31:16] + state
    reg [16:0]  row_q;
    reg [31:0]  bits_q;
    reg         flt_q;
    reg [16:0]  row0_q;                      // straps (static)
    reg         ten_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin go_q <= 1'b0; xv_q <= 1'b0; rv_q <= 3'd0; end
        else begin go_q <= i[512]; xv_q <= i[513]; rv_q <= {3{i[514]}}; end
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
    ot_s81hd_bundle #(.INSTANCE(INSTANCE), .IOREG(IOREG), .SAFE(1), .CUT(CUT), .SPLIT9(SPLIT9), .CV(CV)) u_b (
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
        if (rv_q[0]) begin ch_row <= row_q; ch_flt <= flt_q; end
        if (rv_q[1]) ch_bits[15:0] <= bits_q[15:0];
        if (rv_q[2]) ch_bits[31:16] <= bits_q[31:16];
    end

    // ---------------- capture state, fire once per position ---------------------------------------------------------
    // own result: the rising edge of the bundle's res_v (a level until the bundle's next go) after this position's go
    reg res_v_d, ch_have, own_have, fired, sel_v, o_rv;
    wire res_rise = res_v & ~res_v_d;
    wire ready = ch_have & (own_have | ~b_en) & ~fired & ~go_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin res_v_d <= 1'b0; ch_have <= 1'b0; own_have <= 1'b0; fired <= 1'b0; sel_v <= 1'b0; o_rv <= 1'b0; end
        else begin
            res_v_d  <= res_v;
            ch_have  <= rv_q[2] | (ch_have & ~go_q);
            own_have <= (res_rise & b_en) | (own_have & ~go_q);
            fired    <= ready | (fired & ~go_q);
            sel_v    <= ready;
            o_rv     <= sel_v;
        end

    // ---------------- max under the ot_rom_argmax_rows key ----------------------------------------------------------
    function automatic [31:0] okey(input [31:0] x);        // order-preserving key; -0 as +0
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'd0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    wire [31:0] k_own = okey(res_bits), k_ch = okey(ch_bits);
`ifdef OT_S81HD_MUT_TIE_FLIP
    wire own_better = b_en && (k_own > k_ch || (k_own == k_ch && res_row > ch_row));   // MUTANT: highest id on ties
`else
    wire own_better = b_en && (k_own > k_ch || (k_own == k_ch && res_row < ch_row));
`endif
    (* keep *) reg [2:0] sel_q;              // kept copies: [0] row, [1] bits[15:0], [2] bits[31:16]
    reg        bflt_q;
    always @(posedge ck) begin
        sel_q  <= {3{own_better}};
`ifdef OT_S81HD_MUT_FLT_DROP
        bflt_q <= 1'b0;                      // MUTANT: bundle fault dropped
`else
        bflt_q <= b_en & b_fault;
`endif
    end
    reg [16:0] o_row;
    reg [31:0] o_bits;
    reg        o_flt;
    always @(posedge ck) begin
        o_row          <= sel_q[0] ? res_row : ch_row;
        o_bits[15:0]   <= sel_q[1] ? res_bits[15:0] : ch_bits[15:0];
        o_bits[31:16]  <= sel_q[2] ? res_bits[31:16] : ch_bits[31:16];
        o_flt          <= ch_flt | bflt_q;
    end

    assign o = {o_flt, o_bits, o_row, o_rv, xvo_q, goo_q, xo_q};
endmodule
