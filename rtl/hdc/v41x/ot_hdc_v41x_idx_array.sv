`timescale 1ns/1ps
// V4.1 indexer scoring array: NS replicas of one element, the full-geometry
// score slice ot_hdc_v41x_idx_score_slice (NK keys x 32 heads x 128 FP4 dims
// per cycle), behind one beat handshake.
//
// Spec instance (results/rtl/w11_idx_array.json): NS=16, NK=4 -> 64 keys/cycle, beat
// aligned with the index reader's 64-key x 544-bit output beat
// (ot_hdc_v41x_idx_shard_quarter_collect: slot 16q+l of a beat is quarter q's
// key l).  Key j of a beat goes to slice j/NK.  Every slice holds its own copy
// of the query registers (the slice's tiles hold them), loaded by one
// broadcast q-load port.
//
// Metadata is per key: global index, candidate keep, reader refusal, slot
// valid; the last tag is per slice (the reader's last tag is per quarter).
// The slice stores the first index of its NK keys and regenerates the others
// as first+g, so the valid keys of one slice group must hold consecutive
// indices -- true of the reader beat, whose 16-key quarter groups are
// consecutive and aligned (NK divides 16).  A violation is a protocol fault.
//
// Handshake: a beat is accepted by all slices in the same cycle (i_ready is
// the AND of the slice readies, every slice sees the accept); a score beat is
// presented when all slices have one and consumed by all together (atomic),
// so the NS*NK scores leave in the beat's slot order.  The slices are
// identical and see identical accept/consume streams, so they stay in step;
// `protocol_fault` flags any divergence (valid or last tags disagreeing).
module ot_hdc_v41x_idx_array #(
    parameter integer NS = 16,         // slice replicas
    parameter integer NK = 4,          // keys per slice per cycle
    parameter integer NB = 4,          // 32-blocks per head (index_head_dim/32)
    parameter integer IH = 32,         // index heads
    parameter integer IW = 30,         // global key index width
    parameter integer MD = 64,         // per-slice score/metadata FIFO depth (deepened to cover the latency)
    parameter integer FPL = 3,         // binary32 add latency (7: 1.2 GHz streaming domain)
    parameter integer FML = 3,         // head-weight product latency
    parameter integer QL = 3           // block-dot latency
) (
    input  wire                     clk,
    input  wire                     rst_n,
    // q load, broadcast: one head per cycle
    input  wire                     ql_v,
    output wire                     ql_ready,
    input  wire [7:0]               ql_head,
    input  wire [NB*128-1:0]        ql_codes,
    input  wire [NB*8-1:0]          ql_sc,
    input  wire [15:0]              ql_w,
    // key beat: NS*NK slots
    input  wire                     i_valid,
    output wire                     i_ready,
    input  wire [NS-1:0]            i_last,
    input  wire [NS*NK-1:0]         i_kv,
    input  wire [NS*NK-1:0]         i_ref,
    input  wire [NS*NK-1:0]         i_keep,
    input  wire [NS*NK*IW-1:0]      i_index,
    input  wire [NS*NK*NB*136-1:0]  i_key,
    // score beat to the selector port: NS*NK slots in beat order
    output wire                     o_valid,
    input  wire                     o_ready,
    output wire [NS-1:0]            o_last,
    output wire [NS*NK-1:0]         o_kv,
    output wire [NS*NK-1:0]         o_fault,
    output wire [NS*NK*16-1:0]      o_score,
    output wire [NS*NK*IW-1:0]      o_index,
    output wire                     protocol_fault
);
    localparam integer KW = NB * 136;
    wire [NS-1:0] sr, sv, qr;
    wire take = i_valid && i_ready;
    wire consume = o_valid && o_ready;
    assign i_ready = &sr;
    assign ql_ready = &qr;
    assign o_valid = &sv;
    assign protocol_fault = (|sv && !(&sv)) || ((&sv) && o_last != {NS{o_last[0]}});

    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_slice
        ot_hdc_v41x_idx_score_slice #(.NK(NK), .NB(NB), .IH(IH), .IW(IW), .MD(MD), .FPL(FPL), .FML(FML), .QL(QL)) u (
            .clk(clk), .rst_n(rst_n),
            .ql_v(ql_v), .ql_ready(qr[s]), .ql_head(ql_head),
            .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
            .i_valid(take), .i_ready(sr[s]), .i_last(i_last[s]),
            .i_first_index(i_index[s*NK*IW +: IW]),
            .i_kv(i_kv[s*NK +: NK]), .i_ref(i_ref[s*NK +: NK]), .i_keep(i_keep[s*NK +: NK]),
            .i_key(i_key[s*NK*KW +: NK*KW]),
            .o_valid(sv[s]), .o_ready(consume), .o_last(o_last[s]),
            .o_kv(o_kv[s*NK +: NK]), .o_fault(o_fault[s*NK +: NK]),
            .o_score(o_score[s*NK*16 +: NK*16]),
            .o_index(o_index[s*NK*IW +: NK*IW]));
    end endgenerate

`ifndef SYNTHESIS
    // consecutive indices inside each slice group (valid slots only)
    integer cs, cg;
    always @(posedge clk) if (rst_n && take)
        for (cs = 0; cs < NS; cs = cs + 1)
            for (cg = 1; cg < NK; cg = cg + 1)
                if (i_kv[cs*NK + cg] &&
                    i_index[(cs*NK + cg)*IW +: IW] != i_index[cs*NK*IW +: IW] + cg)
                    $fatal(1, "idx array: slice %0d slot %0d index not consecutive", cs, cg);
    always @(posedge clk) if (rst_n && protocol_fault)
        $fatal(1, "idx array: slices out of step");
`endif
endmodule
