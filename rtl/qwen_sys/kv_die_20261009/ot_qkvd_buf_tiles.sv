`timescale 1ns/1ps
// el1011-q-kvd 2026-10-11: hardened link-buffer sub-tiles for ot_qkvd_d2d (HT=1).  Textbook audit of the KV / ROM ends:
// one clock root over ~100k sinks (class 1), binary FIFO pointers driving every bit of a 528-bit mux / decode (class 2),
// 48:1 x 528 b read mux in one cycle (class 5), 16-17 % utilisation without macros (class 6).  Each buffer becomes its
// own hardened tile (own clock tree, reset relay, pin flops on push / din, registered dout / empty), so the d2d parent
// keeps only the link logic.  Contract (both tiles): order / data exact; empty = "no word at the head"; occupancy
// (count / full) is kept by the parent from push / pop; one extra cycle push -> head (the pin flop).
//
// ot_qkvd_sbuf: depth <= 64, W 528 = 512 in one ot_sram_1r1w_64x512 macro + 16 tag bits in flops; registered write
// stage, capture flops on rd_out inside each head-queue slice, 8-deep head queue as 8 x 66-bit slices each with its own
// control copy.
module ot_qkvd_sbuf #(
    parameter integer PIQ = 0      // 1: pop registered once per head-queue slice (pin register; pop acts one cycle later)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [527:0] din,
    input  wire         pop,
    output wire [527:0] dout,
    output wire         empty
);
    localparam integer W = 528, SW = 66, NS = 8;
`ifdef KVD_SBP
    localparam integer P = `KVD_SBP;
`else
    localparam integer P = 8;
`endif
    localparam integer CW = $clog2(P + 1);
    wire [NS:0] rr;
    ot_rst_relay #(.REGIONS(NS + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    // pin flops
    reg          push_q;
    reg  [W-1:0] din_q;
    always @(posedge clk or negedge rr[NS]) if (!rr[NS]) push_q <= 1'b0; else push_q <= push;
    always @(posedge clk) din_q <= din;
    // SRAM path control (region NS)
    reg  [5:0]   wp_s, rp_s, ra, sw_a;
    reg  [6:0]   ns;
    reg  [CW:0]  f;
    reg          sw_v, rq, rd_v, cap_vc;
    reg  [511:0] sw_d;
    reg  [15:0]  sw_t, tag_rd;
    reg  [15:0]  tagm [0:63];
    wire [511:0] rd_out;
    wire [CW-1:0] oc;
`ifdef KVD_FSBMUT
    wire direct = push_q && (oc < P[CW-1:0]);
`else
    wire direct = push_q && (ns == 0) && (f == 0) && (oc < P[CW-1:0]);
`endif
    wire tos = push_q && !direct;
    wire req = (ns != 0) && ({1'b0, oc} + f < P);
    always @(posedge clk or negedge rr[NS])
        if (!rr[NS]) begin wp_s <= 0; rp_s <= 0; ns <= 0; f <= 0; sw_v <= 1'b0; rq <= 1'b0; rd_v <= 1'b0; cap_vc <= 1'b0; end
        else begin
            sw_v <= tos; rq <= req; rd_v <= rq; cap_vc <= rd_v;
            if (tos) wp_s <= wp_s + 1'b1;
            if (req) rp_s <= rp_s + 1'b1;
            ns <= ns + (tos ? 1'b1 : 1'b0) - (req ? 1'b1 : 1'b0);
            f  <= f + (req ? 1'b1 : 1'b0) - (cap_vc ? 1'b1 : 1'b0);
        end
    always @(posedge clk) begin
        if (tos) begin sw_a <= wp_s; sw_d <= din_q[511:0]; sw_t <= din_q[527:512]; end
        if (sw_v) tagm[sw_a] <= sw_t;
        if (req) ra <= rp_s;
        if (rq) tag_rd <= tagm[ra];
    end
    ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(rq), .r_addr_in(ra), .rd_out(rd_out),
        .w_ce_in(sw_v), .w_addr_in(sw_a), .wd_in(sw_d), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    wire [W-1:0] mq = {tag_rd, rd_out};
    wire [NS-1:0] e;
    wire [CW-1:0] c [0:NS-1];
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_s
        (* keep_hierarchy *) ot_qkvd_sbq_sl #(.SW(SW), .D(P), .PIQ(PIQ)) u_sl (.clk(clk), .rst_n(rr[s]), .direct(direct),
            .din(din_q[SW*s +: SW]), .rd_v(rd_v), .mq(mq[SW*s +: SW]), .pop(pop), .dout(dout[SW*s +: SW]),
            .empty(e[s]), .count(c[s]));
    end endgenerate
    assign empty = e[0];
    assign oc    = c[0];
endmodule

// one 66-bit slice of the sbuf head queue: capture flops for its share of the macro word, its own capture-valid copy,
// and its own registered-head FIFO control (RH=1 behaviour).
module ot_qkvd_sbq_sl #(
    parameter integer SW = 66,
    parameter integer D  = 8,
    parameter integer PIQ = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          direct,
    input  wire [SW-1:0] din,
    input  wire          rd_v,
    input  wire [SW-1:0] mq,
    input  wire          pop,
    output wire [SW-1:0] dout,
    output wire          empty,
    output wire [$clog2(D+1)-1:0] count
);
    reg [SW-1:0] cap;
    reg          capv;
    always @(posedge clk) cap <= mq;
    always @(posedge clk or negedge rst_n) if (!rst_n) capv <= 1'b0; else capv <= rd_v;
    wire pop_e;
    generate if (PIQ != 0) begin : g_piq
        (* keep *) reg pop_q;
        always @(posedge clk or negedge rst_n) if (!rst_n) pop_q <= 1'b0; else pop_q <= pop;
`ifdef KVD_PIQMUT
        assign pop_e = pop;            // mutant: pop pin not registered (acts a cycle early)
`else
        assign pop_e = pop_q;
`endif
    end else begin : g_npiq
        assign pop_e = pop;
    end endgenerate
    ot_qkvd_fifo_sl #(.SW(SW), .D(D)) u_q (.clk(clk), .rst_n(rst_n), .push(direct || capv), .din(capv ? cap : din),
        .pop(pop_e), .dout(dout), .empty(empty), .count(count));
endmodule

// ot_qkvd_fbuf8: depth <= 8 flop buffer as 8 x 66-bit slices (own control copy each) behind pin flops.
module ot_qkvd_fbuf8 #(
    parameter integer PIQ = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [527:0] din,
    input  wire         pop,
    output wire [527:0] dout,
    output wire         empty
);
    wire [8:0] rr;
    ot_rst_relay #(.REGIONS(9), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg          push_q;
    reg  [527:0] din_q;
    always @(posedge clk or negedge rr[8]) if (!rr[8]) push_q <= 1'b0; else push_q <= push;
    always @(posedge clk) din_q <= din;
    wire [3:0] cnt_unused;
    ot_qkvd_fifo_sliced #(.W(528), .SW(66), .D(8), .PIQ(PIQ)) u_f (.clk(clk), .rst_n(rr[7:0]), .push(push_q), .din(din_q),
        .pop(pop), .dout(dout), .empty(empty), .count(cnt_unused));
endmodule

// q13b-kvend 2026-10-13: the same two tiles with EVERY face pin registered (pin-register rule: register at the pin ->
// wire -> register at the pin).  push / din already had pin flops and dout / empty are registered; pop was the one face
// pin that entered a combinational cone (8 slice controls; ~660 ps in the old sbuf view, which left the parent's pop pin
// flop ~110 ps).  Here pop is registered once per slice (8 kept copies, each beside its slice control), so the pop pin
// is a plain flop D and a pop takes effect ONE CYCLE AFTER the pin (ot_qkvd_d2d PQ=2 issues it one cycle earlier from
// the shadow occupancy; order / data / credits unchanged).  Fixed-name tops for the hard views.
module ot_qkvd_sbufp (input wire clk, input wire rst_n, input wire push, input wire [527:0] din, input wire pop,
    output wire [527:0] dout, output wire empty);
    ot_qkvd_sbuf #(.PIQ(1)) u (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop), .dout(dout), .empty(empty));
endmodule
module ot_qkvd_fbuf8p (input wire clk, input wire rst_n, input wire push, input wire [527:0] din, input wire pop,
    output wire [527:0] dout, output wire empty);
    ot_qkvd_fbuf8 #(.PIQ(1)) u (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop), .dout(dout), .empty(empty));
endmodule
