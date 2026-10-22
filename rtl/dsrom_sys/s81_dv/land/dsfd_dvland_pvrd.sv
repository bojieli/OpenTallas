`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-DIE5 (2026-10-18, coordinator 0dt): dsfd_dvland_pvrd -- the P.V lane's LANDING with a static fixed-latency width
// adapter into the C3 slice band port bi (receiving side, no backpressure, no ready).
//
//   lane i[561:0] (one dsfd_dvrlyh_562 chain from the svc entry rsv_05 / rsv_11):
//     [0] pv_v, [513:1] pv_d = {beat head flag 1, word 512}, [561:514] spare (0)
//   ring: ot_s81_land #(562, D 4) on the lane's forwarded clock ck_f, read on the slice root ck at K (LANDING-CONTRACT)
//   adapter (one register, +1 edge): every landed word becomes one slice RD beat (ot_s81sl_xr RD receive format):
//     o[0] v, o[3:1] kind 4 (RD), o[8:4] hops 0, o[12:9] src 0, o[20:13] 0, o[36:21] slice mask 0 (the band port does
//     not check it), o[39:37] leaf, o[49:40] row, o[51:50] pairs - 1 = 1 (one 512-b word = 2 row pairs), o[563:52] word,
//     o[1103:564] 0.
//   static address calendar: word w of the job's P.V drain (the owners' compiled 40-word windows, back to back:
//     dsdv_svc_att, 8 beats x 5 words, word 0 of a beat = the head word) goes to leaf (w mod 5), row rb + 4 (w div 5);
//     a leaf gets one 2-pair RD every 5 words, its unpacker is busy 2 cycles -> no collision at 1 word / cycle.
//     w wraps at the strap nw (words per job, compiler: 4 owner slices x 40 = 160).
//   fault (sticky, assertion only -- never reschedules): the ring's slot epoch check, or a head flag on a word that is
//     not word 0 of a 5-word beat (calendar slip).
// S81-SMWIRE (10-19): SO gather words.  A landed word with i[561] = 1 (the svc entry's pv_x[47] stamp: the word is
//   inside the entry's booked SO gather window) is NOT a P.V word: it bypasses the P.V address calendar (w / lv / row
//   unchanged) and leaves as an SO band word for ot_s81sl_xr's B port: o[0] v, o[3:1] kind 2 (XB), o[4] = word head flag
//   (d bit 512: the gather header word), o[6:5] route (i[558:557]), o[563:52] word, everything else 0.  An SO word while a
//   P.V drain is part-way (w != 0) is a fault (the windows are disjoint by the compiler).
// Straps (identity, die ties): k (ring K), nw, rb.  MUT (bench negative controls only): 1 leaf calendar off by one.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_dvland_pvrd #(parameter integer MUT = 0) (
    input  wire          ck_f,
    input  wire [561:0]  i,
    input  wire          ck,
    input  wire          rs,
    input  wire [2:0]    k,
    input  wire [7:0]    nw,
    input  wire [9:0]    rb,
    output reg  [1103:0] o,
    output wire          fault
);
    wire [561:0] l;
    wire lf;
    ot_s81_land #(.W(562), .D(4)) u_land (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(l), .fault(lf));
    wire so = l[561];
    wire v = l[0] && !so, sv = l[0] && so;
    wire hd = l[513];
    wire [511:0] d = l[512:1];
    reg [7:0] w;
    reg [2:0] lv;
    reg [9:0] row;
    reg ff;
    wire [2:0] lv_o = (MUT == 1) ? ((lv == 3'd4) ? 3'd0 : lv + 3'd1) : lv;
    always @(posedge ck or negedge rs)
        if (!rs) begin w <= 8'd0; lv <= 3'd0; row <= 10'd0; ff <= 1'b0; end
        else if (sv) begin
            if (w != 8'd0) ff <= 1'b1;
        end else if (v) begin
            if (hd != (lv == 3'd0)) ff <= 1'b1;
            if (w == nw - 8'd1) begin w <= 8'd0; lv <= 3'd0; row <= 10'd0; end
            else begin
                w <= w + 8'd1;
                if (lv == 3'd4) begin lv <= 3'd0; row <= row + 10'd4; end
                else lv <= lv + 3'd1;
            end
        end
    always @(posedge ck or negedge rs)
        if (!rs) o[0] <= 1'b0;
        else o[0] <= v || sv;
    always @(posedge ck) begin
        o[3:1] <= so ? 3'd2 : 3'd4; o[4] <= so && hd; o[6:5] <= so ? l[558:557] : 2'd0; o[8:7] <= 2'd0;
        o[12:9] <= 4'd0; o[20:13] <= 8'd0; o[36:21] <= 16'd0;
        o[39:37] <= so ? 3'd0 : lv_o; o[49:40] <= so ? 10'd0 : rb + row; o[51:50] <= so ? 2'd0 : 2'd1; o[563:52] <= d;
        o[1103:564] <= 540'd0;
    end
    assign fault = lf | ff;
endmodule
`default_nettype wire
