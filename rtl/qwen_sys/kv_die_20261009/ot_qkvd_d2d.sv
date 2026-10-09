`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09 (OWNER DECISION ~04:00 PT, option 1a): one die's end of the ROM die <-> KV die link.  Our logic
// between the die buses and the UCIe PHY + D2D adapter hard macro (ot_qkvd_ucie_x64_phy: licensed IP, FDI side only;
// the UCIe D2D adapter inside the macro owns CRC / retry per the UCIe spec, so a flit that reaches this block is good
// or the macro has failed -- the sequence check below catches a lost / repeated flit and fails closed).
// Contract: results/arch/qwen_kv_die_20261009/CONTRACT.md (classes, word formats, credits, latency).
//
//   die TX face   per class i < NT: t_v / t_d captured at the pin flops (no logic before them), an IBD[i]-word buffer,
//                 t_cr = one registered credit pulse per word that leaves it (the die-bus sender starts with IBD[i]).
//   link TX       one flit a 1.2 GHz FDI cycle while the macro reports tx_up (idle flits carry credits only):
//                 {seq 8, credit return 4 x 2 b, dv, class 3, word W}.  A word is sent only with a link credit for its
//                 class in hand (FCR[i] = the far receive buffer); round-robin over the classes that have both.
//   link RX       the FDI flit is captured at the macro pins; sequence checked; credit fields add to the TX link
//                 credits; a word goes to its class's RBD[j]-word receive buffer (class - RXB = j).
//   die RX face   r_v / r_d launched from flops, one word per die credit (OCR[j] initial, r_cr returns one, captured at
//                 the pin).  A receive-buffer word's link credit is owed back to the far side when it leaves the buffer.
//   faults        sticky, registered: die-face overrun, receive-buffer overrun, sequence error, credit overflow,
//                 class out of range.
// Order and values are preserved exactly per class; latency is not cycle-fixed (credit flow control end to end).
// Same 1.2 GHz clock on both dies (KV-die PLL, forwarded): the FDI runs on the local core clock; the macro retimes.
// MUT (bench only): 1 = one extra link credit on TX class 0 (overruns the far buffer under back-pressure),
//                   2 = link credit owed at receive-buffer PUSH instead of pop (early credit).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_d2d #(
    parameter integer NT  = 4,                      // TX classes (this die -> far die)
    parameter integer NR  = 3,                      // RX classes (far die -> this die)
    parameter integer TXB = 0,                      // class number of TX class 0
    parameter integer RXB = 4,                      // class number of RX class 0
    parameter integer W   = 528,                    // die word: {tag 16, data 512}
    parameter [31:0]  IBD = {8'd8, 8'd8, 8'd8, 8'd8},   // die-face TX buffer per TX class (byte i = class i)
    parameter [31:0]  FCR = {8'd8, 8'd8, 8'd8, 8'd8},   // far receive buffer per TX class (initial link credits)
    parameter [31:0]  RBD = {8'd8, 8'd8, 8'd8, 8'd8},   // receive buffer per RX class
    parameter [31:0]  OCR = {8'd8, 8'd8, 8'd8, 8'd8},   // die-face RX credits per RX class
    parameter integer MUT = 0,
    parameter integer FW  = 8 + 8 + 1 + 3 + W
) (
    input  wire            clk,
    input  wire            rst_n,
    // die TX face
    input  wire [NT-1:0]   t_v,
    input  wire [NT*W-1:0] t_d,
    output reg  [NT-1:0]   t_cr,
    // die RX face
    output reg  [NR-1:0]   r_v,
    output reg  [NR*W-1:0] r_d,
    input  wire [NR-1:0]   r_cr,
    // PHY FDI (hard macro)
    input  wire            tx_up,
    output reg             tx_v,
    output reg  [FW-1:0]   tx_flit,
    input  wire            rx_v,
    input  wire [FW-1:0]   rx_flit,
    output reg             fault,
    output reg  [4:0]      fault_cause
);
    // ---- reset copy ----
    reg rs0, rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    // ---- pin capture ----
    reg [NT-1:0]   ci_v;
    reg [NT*W-1:0] ci_d;
    reg [NR-1:0]   cr_q;
    reg            up_q;
    always @(posedge clk) ci_d <= t_d;
    always @(posedge clk or negedge rs)
        if (!rs) begin ci_v <= 0; cr_q <= 0; up_q <= 1'b0; end
        else begin ci_v <= t_v; cr_q <= r_cr; up_q <= tx_up; end
    reg          rq_v;
    reg [FW-1:0] rq_f;
    always @(posedge clk) rq_f <= rx_flit;
    always @(posedge clk or negedge rs) if (!rs) rq_v <= 1'b0; else rq_v <= rx_v;
    wire [7:0]   rx_seq_f = rq_f[W + 12 +: 8];
    wire [7:0]   rx_crs   = rq_f[W + 4 +: 8];
    wire         rx_dv    = rq_v && rq_f[W + 3];
    wire [2:0]   rx_cls   = rq_f[W +: 3];
    wire [W-1:0] rx_word  = rq_f[W-1:0];

    reg f_die, f_rb, f_seq, f_cred, f_cls;
    // ---- TX side ----
    wire [NT-1:0]   ib_empty, ib_full;
    wire [NT*W-1:0] ib_head;
    reg  [NT-1:0]   lc_nz;             // a link credit in hand, per TX class
    reg  [7:0]      lcred [0:NT-1];
    reg  [$clog2(NT+1)-1:0] rr;        // round-robin pointer: class searched first
    // grant: first class at or after rr that has a word and a link credit
    reg  [NT-1:0] gnt;
    reg           any;
    integer k, c;
    always @* begin
        gnt = 0; any = 1'b0;
        for (k = 0; k < NT; k = k + 1) begin
            c = (rr + k) % NT;
            if (!any && up_q && !ib_empty[c] && lc_nz[c]) begin gnt[c] = 1'b1; any = 1'b1; end
        end
    end
    genvar i, j;
    generate for (i = 0; i < NT; i = i + 1) begin : g_tx
        wire [$clog2(IBD[8*i +: 8]+1)-1:0] cnt;
        ot_qkvd_fifo #(.W(W), .D(IBD[8*i +: 8])) u_ib (.clk(clk), .rst_n(rs), .push(ci_v[i]), .din(ci_d[W*i +: W]),
            .pop(gnt[i]), .dout(ib_head[W*i +: W]), .empty(ib_empty[i]), .full(ib_full[i]), .count(cnt));
    end endgenerate
    reg [W-1:0] sel_word;
    reg [2:0]   sel_cls;
    always @* begin
        sel_word = {W{1'b0}}; sel_cls = 3'd0;
        for (k = 0; k < NT; k = k + 1) if (gnt[k]) begin sel_word = ib_head[W*k +: W]; sel_cls = 3'(TXB + k); end
    end
    // ---- RX side ----
    wire [NR-1:0]   rb_empty, rb_full;
    wire [NR*W-1:0] rb_head;
    reg  [7:0]      ocred [0:NR-1];
    reg  [7:0]      owed  [0:NR-1];
    wire [NR-1:0]   rb_push, rb_pop;
    generate for (j = 0; j < NR; j = j + 1) begin : g_rx
        wire [$clog2(RBD[8*j +: 8]+1)-1:0] cnt;
        assign rb_push[j] = rx_dv && (rx_cls == 3'(RXB + j));
        assign rb_pop[j]  = !rb_empty[j] && (ocred[j] != 0);
        ot_qkvd_fifo #(.W(W), .D(RBD[8*j +: 8])) u_rb (.clk(clk), .rst_n(rs), .push(rb_push[j]), .din(rx_word),
            .pop(rb_pop[j]), .dout(rb_head[W*j +: W]), .empty(rb_empty[j]), .full(rb_full[j]), .count(cnt));
    end endgenerate
    // credit return fields (2 b each, 4 fields; field j = this die's RX class j)
    reg [7:0] cr_ret;
    reg [1:0] ret [0:3];
    always @* begin
        cr_ret = 8'd0;
        for (k = 0; k < 4; k = k + 1) begin
            ret[k] = 2'd0;
            if (k < NR) ret[k] = (owed[k] > 8'd3) ? 2'd3 : owed[k][1:0];
            if (!up_q) ret[k] = 2'd0;
            cr_ret[2*k +: 2] = ret[k];
        end
    end
    reg [7:0] tx_seq, rx_seq;
    always @(posedge clk or negedge rs) begin
        if (!rs) begin
            tx_v <= 1'b0; tx_flit <= {FW{1'b0}}; tx_seq <= 8'd0; rx_seq <= 8'd0; rr <= 0;
            t_cr <= 0; r_v <= 0;
            f_die <= 1'b0; f_rb <= 1'b0; f_seq <= 1'b0; f_cred <= 1'b0; f_cls <= 1'b0;
            fault <= 1'b0; fault_cause <= 5'd0;
            for (k = 0; k < NT; k = k + 1) begin
                lcred[k] <= FCR[8*k +: 8] + ((MUT == 1 && k == 0) ? 8'd1 : 8'd0);
                lc_nz[k] <= (FCR[8*k +: 8] != 0);
            end
            for (k = 0; k < NR; k = k + 1) begin ocred[k] <= OCR[8*k +: 8]; owed[k] <= 8'd0; end
        end else begin
            // die TX face
            for (k = 0; k < NT; k = k + 1) if (ci_v[k] && ib_full[k] && !gnt[k]) f_die <= 1'b1;
            t_cr <= gnt;
            // link TX
            tx_v <= up_q;
            if (up_q) tx_seq <= tx_seq + 1'b1;
            tx_flit <= {tx_seq, cr_ret, any, sel_cls, sel_word};
            if (any) rr <= ((rr + 1) % NT);
            for (k = 0; k < NT; k = k + 1) begin : upd_lc
                reg [8:0] nxt;
                nxt = {1'b0, lcred[k]} - (gnt[k] ? 9'd1 : 9'd0) + ((rq_v && k < 4) ? {7'd0, rx_crs[2*k +: 2]} : 9'd0);
                lcred[k] <= nxt[7:0];
                lc_nz[k] <= (nxt != 0);
                if (nxt > {1'b0, FCR[8*k +: 8]} + ((MUT == 1 && k == 0) ? 9'd1 : 9'd0)) f_cred <= 1'b1;
            end
            // link RX
            if (rq_v) begin
                rx_seq <= rx_seq + 1'b1;
                if (rx_seq_f != rx_seq) f_seq <= 1'b1;
            end
            if (rx_dv && (rx_cls < 3'(RXB) || rx_cls >= 3'(RXB + NR))) f_cls <= 1'b1;
            for (k = 0; k < NR; k = k + 1) begin
                if (rb_push[k] && rb_full[k] && !rb_pop[k]) f_rb <= 1'b1;
                owed[k] <= owed[k] - (up_q ? {6'd0, ret[k]} : 8'd0) + ((MUT == 2 ? rb_push[k] : rb_pop[k]) ? 8'd1 : 8'd0);
                ocred[k] <= ocred[k] - (rb_pop[k] ? 8'd1 : 8'd0) + (cr_q[k] ? 8'd1 : 8'd0);
            end
            // die RX face
            r_v <= rb_pop;
            fault_cause <= {f_cls, f_cred, f_seq, f_rb, f_die};
            fault <= f_die | f_rb | f_seq | f_cred | f_cls;
        end
    end
    always @(posedge clk) for (k = 0; k < NR; k = k + 1) if (rb_pop[k]) r_d[W*k +: W] <= rb_head[W*k +: W];
endmodule
