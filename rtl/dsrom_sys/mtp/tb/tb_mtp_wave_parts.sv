`timescale 1ns/1ps
// tb_mtp_wave building blocks that are bench models (not under test), el1011-ds-mtp wave bench 2026-10-11.
//
// wv_lane    one board / UCIe lane between two MTP lane adapters: the adapter's credit tx lands in an ot_link_credit_rx
//            (DEPTH 8 = the lane tile's landing), crosses LL registered cycles, queues in the link layer (its 512 link
//            credits: an unbounded bench FIFO, overflow is a fault) and is delivered by an ot_link_credit_tx (CRED 8) into
//            the far adapter's landing.  Adapter cycles are measured at the adapter pins, so LL only shifts arrivals.
// wv_cstub   the collective hop between two stage WFCs (not under test): lands the upstream die's credit link (LAND
//            entries, a credit pulse per pop), checks every received word of the INW-word HIDDEN message against
//            wv_word(SIN, ...), and forwards the header (length OUTW) and the first OUTW words re-encoded as
//            wv_word(SOUT, ...) on the downstream die's credit link (CRED credits); 2 cycles input -> output.
module wv_lane #(parameter integer LL = 17) (
    input  wire clk, rst_n,
    input  wire a_v, input wire [552:0] a_d, output wire a_c,
    output wire b_v, output wire [552:0] b_d, input wire b_c,
    output reg  fault
);
    wire rv, rflt; wire [552:0] rd;
    ot_link_credit_rx #(.W(553), .DEPTH(8)) u_rx (.clk(clk), .rst_n(rst_n), .l_valid(a_v), .l_data(a_d), .l_credit(a_c),
        .o_valid(rv), .o_ready(1'b1), .o_data(rd), .fault(rflt));
    wire pv; wire [552:0] pd;
    wv_relay #(.W(554), .N(LL)) u_d (.clk(clk), .rst_n(rst_n), .d({rv, rd}), .q({pv, pd}));
    reg [552:0] q [0:1023]; reg [10:0] wp, rp;
    wire tv = wp != rp; wire tr; wire [552:0] td = q[rp[9:0]];
    always @(posedge clk)
        if (!rst_n) begin wp <= 0; rp <= 0; fault <= 1'b0; end
        else begin
            if (pv) begin q[wp[9:0]] <= pd; wp <= wp + 1'b1; end
            if (tv && tr) rp <= rp + 1'b1;
            if (rflt || (wp - rp) > 11'd1000) fault <= 1'b1;
        end
    ot_link_credit_tx #(.W(553), .CRED(8)) u_tx (.clk(clk), .rst_n(rst_n), .i_valid(tv), .i_ready(tr), .i_data(td),
        .l_valid(b_v), .l_data(b_d), .l_credit(b_c));
endmodule

module wv_cstub #(parameter integer SIN = 1, parameter integer SOUT = 1, parameter integer INW = 41,
                  parameter integer OUTW = 41, parameter integer CRED = 24, parameter integer LAND = 64) (
    input  wire clk, rst_n,
    input  wire i_v, input wire [512:0] i_d, output reg i_c,         // upstream die link (credit protocol)
    output reg  n_v, output reg [512:0] n_d, input wire n_c,         // downstream die link
    output reg  bad
);
    `include "tb_mtp_wave_fn.svh"
    localparam integer HDR_TYPE = 16, HDR_LEN = 24, HDR_POS = 40, HDR_TOK = 114, NW = 21;
    reg [512:0] q [0:255]; integer wp = 0, rp = 0, cr = CRED, mk = -1, mp = 0, mt = 0, msgs = 0;
    reg [512:0] h;
    always @(posedge clk) begin
        n_v <= 1'b0; i_c <= 1'b0;
        if (!rst_n) begin wp = 0; rp = 0; cr = CRED; mk = -1; bad <= 1'b0; end
        else begin
            if (n_c) cr = cr + 1;
            if (rp < wp) begin
                h = q[rp % 256];
                if (mk < 0) begin
                    if (cr > 0) begin
                        if (h[HDR_TYPE +: 4] != 4'd1 || h[HDR_LEN +: 8] != INW || h[512]) begin
                            $display("WAVE FAIL: stub %0d->%0d header type %0d len %0d", SIN, SOUT, h[HDR_TYPE +: 4], h[HDR_LEN +: 8]);
                            bad <= 1'b1;
                        end
                        mp = h[HDR_POS +: NW]; mt = h[HDR_TOK +: NW];
                        h[HDR_LEN +: 8] = OUTW;
                        n_v <= 1'b1; n_d <= h; cr = cr - 1; mk = 0; rp = rp + 1; i_c <= 1'b1;
                    end
                end else if (mk >= OUTW || cr > 0) begin
                    if (h[511:0] !== wv_word(SIN, mp, mt, mk) || h[512] != (mk == INW - 1)) begin
                        $display("WAVE FAIL: stub %0d->%0d word %0d of (p%0d, t%0d) last %0d", SIN, SOUT, mk, mp, mt, h[512]);
                        bad <= 1'b1;
                    end
                    if (mk < OUTW) begin n_v <= 1'b1; n_d <= {mk == OUTW - 1, wv_word(SOUT, mp, mt, mk)}; cr = cr - 1; end
                    mk = mk + 1; rp = rp + 1; i_c <= 1'b1;
                    if (mk == INW) begin mk = -1; msgs = msgs + 1; end
                end
            end
            if (i_v) begin q[wp % 256] = i_d; wp = wp + 1; end
            if (wp - rp > LAND) begin $display("WAVE FAIL: stub %0d->%0d landing overflow", SIN, SOUT); bad <= 1'b1; end
        end
    end
endmodule
