`timescale 1ns/1ps
// hgi-1010/g2 2026-10-10: the indexer's HARDENED ELEMENT = one 8-head chunk (ot_hdc_v41x_idx_chunk_l, generated, unchanged)
// with its head base as an input strap instead of a parameter, so ONE view serves all 4 chunks of a score engine (the
// L4 column tap = 4 chunk macros + ot_hdc_v41x_idx_tail_l + the line/beat front end; the flat 512-adder tap is not
// synthesizable: lane12 yosys OOM in `share`, lane8 11.5 h in synth -flatten).
// The chunk decodes a q-load head h as its local head h - HB (HB = 0 here): the element presents ql_head - hb, which lies in
// 0..7 exactly for heads hb..hb+7 (8-bit wrap; hb + 7 < 256), so every q-load, key beat and chunk sum is the chunk's own.
// hb is a die-level constant (0, 8, 16, 24); it reaches only the q-load head compare (a registered input of the chunk).
module ot_hdc_v41x_idx_chunk_el #(
    parameter integer NB  = 4,
    parameter integer NKT = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    output wire                  c_v,
    output wire [NKT-1:0]        c_kv,
    output wire [NKT*32-1:0]     c_sum,
    output wire [NKT-1:0]        c_fault
);
    // el1011-ds-misc/idx 2026-10-11: HIERARCHICAL.  The flat chunk (146,738 sinks in one 760 x 760 block, 52k async-clear
    // adder flops on rst_n) did not close (hgi-idx-chunk-{a,b}-9473077de: CTS spread 518..833 ps, hold stuck at -70).  The
    // element is now NKT hardened key-lane sub-tiles (ot_hdc_v41x_idx_ksub_el, one view, placed as macros): the q-load
    // and hb broadcast to every lane, key lane g and its outputs are lane g's own; each sub-tile registers every input
    // pin and every output, so this level is wiring only (0 added cycles; c_v is lane 0's, all lanes' c_v are equal).
    wire [NKT-1:0] lv;
    genvar g;
    generate
        for (g = 0; g < NKT; g = g + 1) begin : g_k
            ot_hdc_v41x_idx_ksub_el #(.NB(NB), .FPL(FPL), .FML(FML), .QL(QL)) u_k (.clk(clk), .rst_n(rst_n), .hb(hb),
                .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w), .k_v(k_v), .k_kv(k_kv[g]),
                .k_key(k_key[g*NB*136 +: NB*136]), .c_v(lv[g]), .c_kv(c_kv[g]), .c_sum(c_sum[32*g +: 32]),
                .c_fault(c_fault[g]));
        end
    endgenerate
    assign c_v = lv[0];
endmodule
