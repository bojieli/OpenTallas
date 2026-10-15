`timescale 1ns/1ps
// q15 port-tiles (2026-10-15): one level-6 -> level-7 FP32 pair adder of a slab word half, as its own hardened leaf
// (clock entry ck_pair<p>: 9,778 sinks; previously an inline generate block of qfd_slab_word_half).  Logic, reset
// and latency are byte-for-byte the former g_pair body: 16 x ot_hdc_fp32_add_lat (LAT ADD_LAT, DRST 0), a local
// reset capture, the sticky alignment/fault register.  No ready/credit: every edge is sampled (static schedule).
module qfd_slab_pair_add #(
    parameter integer ADD_LAT = 7
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [513:0] wa,
    input  wire [513:0] wb,
    output wire [511:0] y,
    output wire         pv,
    output wire         pf
);
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
