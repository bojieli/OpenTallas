`timescale 1ns/1ps
// q15 port-tiles (2026-10-15): one level-6 -> level-7 FP32 pair of a slab word half as its own hardened leaf, WITH its
// two root capture banks: the 514-b words of roots a and b are captured at the leaf's input pins on their own clock
// entries (ck_a / ck_b = the die's ck_bw<2p> / ck_bw<2p+1>, 515 sinks each), then 16 x ot_hdc_fp32_add_lat (LAT
// ADD_LAT, DRST 0) on ck (= ck_pair<p>, ~9.5k sinks).  Logic, resets and latency are exactly the former
// qfd_slab_word_half g_root[2p], g_root[2p+1] and g_pair[p] bodies (gate 80ceb739c: a capture-free leaf had 8-level
// input cones at its pins; the captures now are the pin registers).  Static schedule: every edge is sampled.
module qfd_slab_pair_add #(
    parameter integer ADD_LAT = 7
) (
    input  wire         ck_a,
    input  wire         ck_b,
    input  wire         ck,
    input  wire         rst_n_a,    // the die reset, one copy per clock entry domain (each captured on its own entry)
    input  wire         rst_n_b,
    input  wire         rst_n,
    input  wire [513:0] bw_a,
    input  wire [513:0] bw_b,
    output wire [511:0] y,
    output wire         pv,
    output wire         pf
);
    (* keep *) reg [513:0] wa, wb;
    (* keep *) reg reset_a, reset_b;
    always @(posedge ck_a) reset_a <= rst_n_a;
    always @(posedge ck_a) begin
        wa[511:0] <= bw_a[511:0];
        wa[513:512] <= reset_a ? bw_a[513:512] : 2'b0;
    end
    always @(posedge ck_b) reset_b <= rst_n_b;
    always @(posedge ck_b) begin
        wb[511:0] <= bw_b[511:0];
        wb[513:512] <= reset_b ? bw_b[513:512] : 2'b0;
    end
    (* keep *) reg reset_q;
    always @(posedge ck) reset_q <= rst_n;
    wire valid_in = wa[512] & wb[512];
    wire [15:0] lv;
    wire [31:0] le;
    genvar l;
    generate for(l=0;l<16;l=l+1) begin:g_lane
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT),.DRST(0)) u_add (
            .clk(ck), .rst_n(reset_q), .valid_in(valid_in),
            .a(wa[32*l +: 32]), .b(wb[32*l +: 32]),
            .y(y[32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
    end endgenerate
    reg mismatch;
    always @(posedge ck)
        if(!reset_q) mismatch <= 1'b0;
        else mismatch <= mismatch | (wa[512] ^ wb[512]) | wa[513] | wb[513];
    assign pv = lv[0];
    assign pf = mismatch | (lv[0] & (|le)) | (|(lv ^ {16{lv[0]}}));
endmodule
