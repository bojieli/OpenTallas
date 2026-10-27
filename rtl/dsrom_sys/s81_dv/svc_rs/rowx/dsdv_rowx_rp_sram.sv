`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-ROWX3 (2026-10-26): RE-PAIR of one die half's rank-order (RO = 1) export into PK2 transport slots.
//
// Input: the half's export words as they leave the svc entry P.V lane (dsdv_svc_att RO export, 513 b = {P.V word-0
// marker, half 1, half 0}), the ROWX-2 die config NP 7 x NXW 40, XP 320: in every pass the 8 tiles of the half arrive
// in 8 disjoint 40-cycle windows, back to back (window k of a pass = tile WMAP[k]; word i of pass p carries ranks
// 2 (40 p + i) and + 1 of that tile).  NS = NP x 320 = 2,240 words, one per cycle from cycle XOFF after GO.  The
// arrival cycle is static; a word outside its booked cycle (or a missing one) is the sticky fault f_mis.
// Output: one PK2 slot per cycle, NS slots, the input delayed by 42 cycles.  Pair window w = (windows 2 j, 2 j + 1 of
// a pass): slot n (0..79) = {B half h, A half h} of export word i = n mod 40, h = n div 40 -- the two halves of a slot
// belong to two different tiles (lo = window 2 j, hi = window 2 j + 1) and to the same rank 80 p + 2 i + h, which is
// what the PK2 ingress (type 6, spec [0] = 1) needs (one landing write port per slice).
// SRAM successor: 3 real 64x512 macros, 40 used rows each; zero added data cycles.
// Storage: A windows double-banked (2 x 40 words), B single (40 words): A[w][i] is read up to cycle 80 w + 81 + i,
// next written at 80 (w + 2) + i; B[w][i] is read up to 80 w + 81 + i, next written at 80 (w + 1) + 40 + i.
// Every input lands in a flop; every output leaves a flop.  Fixed schedule: no data-dependent timing anywhere.
// Mutant (bench only): MUT 3 = A read from the wrong bank (pairs window 2 j with the previous pair's window).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_rowx_rp_sram #(parameter integer MUT = 0, parameter integer MUT_BYPASS = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,             // frame start (static die schedule)
    input  wire [15:0]   xoff,           // first export word at GO + XOFF (>= 2)
    input  wire [11:0]   ns,             // slots = NP x 320 (a multiple of 80)
    input  wire          x_v,
    input  wire [512:0]  x_d,
    output reg           o_v,
    output reg  [511:0]  o_d,
    output reg           f_mis
);
    reg go_r, xv; reg [511:0] xd;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin go_r <= 1'b0; xv <= 1'b0; end else begin go_r <= go; xv <= x_v; end
    always @(posedge clk) xd <= x_d[511:0];
    reg arm, in_act, out_act; reg [15:0] dly; reg [11:0] ci, cu; reg [5:0] ii; reg [2:0] kk; reg apar, opar; reg [6:0] n;
    wire [5:0] oi = (n < 7'd40) ? n[5:0] : 6'(n - 7'd40);
    wire oh = n >= 7'd40;
    wire rsel = (MUT == 3) ? ~opar : opar;
    // Read the NEXT output word at this edge. Macro read data is available
    // throughout the following cycle, exactly when the original combinational
    // array would feed the unchanged output register. First read0 is ci40.
    wire first_read = in_act && ci == 12'd40;
    wire [6:0] next_n = out_act ? (n == 7'd79 ? 7'd0 : n + 7'd1) : 7'd0;
    wire [5:0] pre_addr = (next_n < 7'd40) ? next_n[5:0] : 6'(next_n - 7'd40);
    wire rd_en = first_read || out_act;
    wire wa0 = in_act && !kk[0] && !apar;
    wire wa1 = in_act && !kk[0] && apar;
    wire wb = in_act && kk[0];
    wire [511:0] ma0, ma1, mb;
    ot_sram_1r1w_64x512_m1_r2c2 u_a0 (
        .clk(clk), .r_ce_in(rd_en), .r_addr_in(pre_addr), .rd_out(ma0),
        .w_ce_in(wa0), .w_addr_in(ii), .wd_in(xd), .w_mask_in({512{1'b1}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_a1 (
        .clk(clk), .r_ce_in(rd_en), .r_addr_in(pre_addr), .rd_out(ma1),
        .w_ce_in(wa1), .w_addr_in(ii), .wd_in(xd), .w_mask_in({512{1'b1}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_b (
        .clk(clk), .r_ce_in(rd_en), .r_addr_in(pre_addr), .rd_out(mb),
        .w_ce_in(wb), .w_addr_in(ii), .wd_in(xd), .w_mask_in({512{1'b1}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    // Macros are read-before-write. The next-cycle original array view includes
    // this edge's write, so forward collisions (notably first B[0] at ci40).
    reg [2:0] bypass;
    reg [511:0] bypass_d;
    always @(posedge clk) begin
        bypass <= {wb,wa1,wa0} & {3{rd_en && ii == pre_addr && MUT_BYPASS == 0}};
        bypass_d <= xd;
    end
    wire [511:0] qa0 = bypass[0] ? bypass_d : ma0;
    wire [511:0] qa1 = bypass[1] ? bypass_d : ma1;
    wire [511:0] ra = rsel ? qa1 : qa0;
    wire [511:0] rb = bypass[2] ? bypass_d : mb;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            arm <= 0; in_act <= 0; out_act <= 0; dly <= 0; ci <= 0; cu <= 0; ii <= 0; kk <= 0; apar <= 0; opar <= 0; n <= 0;
            o_v <= 0; o_d <= 0; f_mis <= 0;
        end else begin
            if (go_r) begin arm <= 1'b1; dly <= xoff - 16'd2; if (xoff < 16'd2) f_mis <= 1'b1; end
            else if (arm) begin
                if (dly == 0) begin arm <= 1'b0; in_act <= 1'b1; ci <= 0; ii <= 0; kk <= 0; apar <= 0; end
                else dly <= dly - 1'b1;
            end
            if (in_act) begin
                if (!xv) f_mis <= 1'b1;
                if (ii == 6'd39) begin ii <= 0; kk <= kk + 1'b1; if (kk[0]) apar <= ~apar; end else ii <= ii + 1'b1;
                ci <= ci + 1'b1;
                if (ci == ns - 12'd1) in_act <= 1'b0;
                if (ci == 12'd40) begin out_act <= 1'b1; cu <= 0; n <= 0; opar <= 0; end
            end else if (xv) f_mis <= 1'b1;
            o_v <= out_act;
            if (out_act) begin
                o_d <= {rb[256*oh +: 256], ra[256*oh +: 256]};
                if (n == 7'd79) begin n <= 0; opar <= ~opar; end else n <= n + 1'b1;
                cu <= cu + 1'b1;
                if (cu == ns - 12'd1) out_act <= 1'b0;
            end
        end
endmodule
