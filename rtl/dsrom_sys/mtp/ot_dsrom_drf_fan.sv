`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_drf_fan: the draft-die link fan-out / fan-in node (stream mtp-rom, 2026-10-08; MTP_AUDIT gap G5).
//
// DP1-EP5 places each DSpark block's routed experts on 5 replica TP4 groups; replica r computes block row r.
// The recovery record priced a STAR: every primary rank die drives 15 board links (3 blocks x 5 replicas).
// This node turns it into a 2-level tree: the primary rank die keeps one link per block (to the block's
// replica 0, 3 links instead of 15), and replica 0's die forwards to replicas 1..4 (4 links) -- one extra link
// hop each way for 4 of the 5 rows, priced by the composition (mtp-die owns the topology).
//
// Function (messages are header + payload flits, `last` on the final flit; the header's DEST byte is a source
// route: its low nibble is this node's output, 0 = this die (local), 1..N = child port nibble-1; a message sent
// to a child carries DEST >> 4, i.e. the child's own route):
//   down  up_in -> local_out or child_out[k]: routed whole messages, in order (one input, so no interleave);
//   up    local_in and child_in[k] -> up_out: whole messages merged round-robin (a message, once started,
//         holds the output until its last flit; a row's return is one message, so rows never interleave).
// Rows are independent (row r's expert sum is computed entirely on replica r), so the merge order does not
// change any value; the primary places each returned row by its row id.
// Every port is a 2-entry skid (registered ready / valid); +2 cycles each way through the node.
// Mutants: OT_DRFFAN_MUT_INTERLEAVE (the merge may switch inputs mid-message),
//          OT_DRFFAN_MUT_DEST (DEST is not rewritten for the child).
// ---------------------------------------------------------------------------
module ot_dsrom_drf_fan #(
    parameter integer FLIT = 512,
    parameter integer N    = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              up_in_valid,  output wire up_in_ready,  input  wire [FLIT:0] up_in_data,
    output wire              up_out_valid, input  wire up_out_ready, output wire [FLIT:0] up_out_data,
    output wire              lo_out_valid, input  wire lo_out_ready, output wire [FLIT:0] lo_out_data,
    input  wire              lo_in_valid,  output wire lo_in_ready,  input  wire [FLIT:0] lo_in_data,
    output wire [N-1:0]      ch_out_valid, input  wire [N-1:0] ch_out_ready, output wire [N*(FLIT+1)-1:0] ch_out_data,
    input  wire [N-1:0]      ch_in_valid,  output wire [N-1:0] ch_in_ready,  input  wire [N*(FLIT+1)-1:0] ch_in_data,
    output reg               fault
);
    localparam integer W = FLIT + 1, M = N + 1;           // merge inputs: 0 = local, 1..N = children
    localparam integer MB = $clog2(M);
    reg live; always @(posedge clk) live <= rst_n;

    // ------------------------------------------------ down: route by DEST
    wire dv; wire [W-1:0] dd; wire dr;
    ot_dsrom_mtp_skid #(.W(W)) u_di (.clk(clk), .rst_n(live), .in_valid(up_in_valid), .in_ready(up_in_ready),
        .in_data(up_in_data), .out_valid(dv), .out_ready(dr), .out_data(dd));
    reg hdr; reg [MB-1:0] cur;                             // message in progress: target
    wire [7:0] dest = dd[7:0];
    wire [MB-1:0] tgt = hdr ? ((dest[3:0] <= N) ? dest[MB-1:0] : {MB{1'b0}}) : cur;
    wire [M-1:0] o_rdy;
    wire [M-1:0] o_v;
    wire [W-1:0] o_d = (hdr && tgt != 0)
`ifndef OT_DRFFAN_MUT_DEST
                       ? {dd[W-1:8], 4'd0, dest[7:4]}
`else
                       ? dd
`endif
                       : dd;
    genvar g;
    generate for (g = 0; g < M; g = g + 1) begin : g_o
        assign o_v[g] = dv && tgt == g;
        if (g == 0) begin : g_l
            ot_dsrom_mtp_skid #(.W(W)) u_o (.clk(clk), .rst_n(live), .in_valid(o_v[g]), .in_ready(o_rdy[g]),
                .in_data(o_d), .out_valid(lo_out_valid), .out_ready(lo_out_ready), .out_data(lo_out_data));
        end else begin : g_c
            ot_dsrom_mtp_skid #(.W(W)) u_o (.clk(clk), .rst_n(live), .in_valid(o_v[g]), .in_ready(o_rdy[g]),
                .in_data(o_d), .out_valid(ch_out_valid[g-1]), .out_ready(ch_out_ready[g-1]),
                .out_data(ch_out_data[(g-1)*W +: W]));
        end
    end endgenerate
    assign dr = o_rdy[tgt];
    always @(posedge clk) begin
        if (!live) begin hdr <= 1'b1; cur <= 0; fault <= 1'b0; end
        else if (dv && dr) begin
            hdr <= dd[W-1]; cur <= tgt;
            if (hdr && dest[3:0] > N) fault <= 1'b1;
        end
    end

    // ------------------------------------------------ up: whole-message round-robin merge
    wire [M-1:0] iv; wire [M*W-1:0] id; wire [M-1:0] ir;
    generate for (g = 0; g < M; g = g + 1) begin : g_i
        if (g == 0) begin : g_l
            ot_dsrom_mtp_skid #(.W(W)) u_i (.clk(clk), .rst_n(live), .in_valid(lo_in_valid), .in_ready(lo_in_ready),
                .in_data(lo_in_data), .out_valid(iv[g]), .out_ready(ir[g]), .out_data(id[g*W +: W]));
        end else begin : g_c
            ot_dsrom_mtp_skid #(.W(W)) u_i (.clk(clk), .rst_n(live), .in_valid(ch_in_valid[g-1]),
                .in_ready(ch_in_ready[g-1]), .in_data(ch_in_data[(g-1)*W +: W]), .out_valid(iv[g]), .out_ready(ir[g]),
                .out_data(id[g*W +: W]));
        end
    end endgenerate
    reg lock; reg [MB-1:0] sel, rr;
    reg [MB-1:0] pick; reg pick_v;
    integer k;
    always @(*) begin
        pick_v = 1'b0; pick = rr;
        for (k = M - 1; k >= 0; k = k - 1) begin
            if (iv[(rr + k) % M]) begin pick_v = 1'b1; pick = (rr + k) % M; end
        end
    end
`ifdef OT_DRFFAN_MUT_INTERLEAVE
    wire [MB-1:0] s = pick;  wire s_v = pick_v;
`else
    wire [MB-1:0] s = lock ? sel : pick;  wire s_v = lock ? iv[sel] : pick_v;
`endif
    wire u_rdy;
    wire u_fire = s_v && u_rdy;
    generate for (g = 0; g < M; g = g + 1) begin : g_ir
        assign ir[g] = u_fire && s == g;
    end endgenerate
    ot_dsrom_mtp_skid #(.W(W)) u_uo (.clk(clk), .rst_n(live), .in_valid(s_v), .in_ready(u_rdy),
        .in_data(id[s*W +: W]), .out_valid(up_out_valid), .out_ready(up_out_ready), .out_data(up_out_data));
    always @(posedge clk) begin
        if (!live) begin lock <= 1'b0; sel <= 0; rr <= 0; end
        else if (u_fire) begin
            lock <= !id[s*W + W - 1]; sel <= s;
            if (id[s*W + W - 1]) rr <= (s == M - 1) ? 0 : s + 1'b1;
        end
    end
endmodule
