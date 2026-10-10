`timescale 1ns/1ps
`default_nettype none
// HGI-1 COLL.ARGMAX_MERGE fold (hgi-takeover 2026-10-09, review 10:45 decision 1 continued).
//
// The record runs an exact gather BYPASS of one flit per rank: word 0 = the rank's ARGMAX.LOCAL value (FP32), word 1 its
// global id (U32).  This block sits on the endpoint's delivery lanes: with en = 1 the delivered flits are folded here and
// NOT passed to the SU quarters; when the endpoint reports done, the merged token leaves as ONE delivery flit
// {1, FF, src, gi 0, data = {0..., token}} on lane 0 (the SU writes O word 0; words past O.n are masked by the writer),
// and only then is done passed to the record.  With en = 0 every lane passes through unchanged (zero cycles).
//
// Order (tools/hgi_sim/machine.py u_coll_argmax_merge: lexsort(ids, -float64(value))): larger value first, -0 == +0,
// NaN after every number; equal values (and NaN vs NaN) -> the LOWER id.  The fold is associative and commutative under
// this total order, so the arrival order of the flits does not matter.  Pipeline: lane capture, two pairwise levels,
// the accumulator: 4 edges after the last delivery, then the result flit (+5 cycles per ARGMAX_MERGE, priced).
module ot_hgi_coll_amerge #(
    parameter integer DEL = 4,
    parameter integer FW  = 512,
    parameter integer PWT = FW + 33,
    parameter integer MUT_TIE = 0          // bench mutant: ties resolve to the HIGHER id
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               en,          // ARGMAX_MERGE run (static from the record's go to its completion)
    input  wire               start,       // the run's go: clears the accumulator
    input  wire [7:0]         rank,
    input  wire [DEL-1:0]     d_v,
    input  wire [DEL*PWT-1:0] d_f,
    input  wire               ep_done,     // the endpoint's done_valid (all group flits delivered)
    output reg  [DEL-1:0]     o_v,
    output reg  [DEL*PWT-1:0] o_f,
    output wire               done_out
);
    function automatic [31:0] okey(input [31:0] v);     // monotone integer key of a non-NaN FP32 (-0 -> +0)
        begin
            if (v[30:0] == 31'd0) okey = 32'h8000_0000;
            else okey = v[31] ? ~v : (v | 32'h8000_0000);
        end
    endfunction
    function automatic is_nan(input [31:0] v);
        is_nan = (v[30:23] == 8'hFF) && (v[22:0] != 23'd0);
    endfunction
    // a better than b: {valid, value, id}
    function automatic better(input av, input [31:0] a, input [31:0] ai, input bv, input [31:0] b, input [31:0] bi);
        reg an, bn, lo;
        begin
            an = is_nan(a); bn = is_nan(b);
            lo = (MUT_TIE != 0) ? (ai > bi) : (ai < bi);
            if (!bv) better = av;
            else if (!av) better = 1'b0;
            else if (an != bn) better = bn;
            else if (an) better = lo;
            else if (okey(a) != okey(b)) better = okey(a) > okey(b);
            else better = lo;
        end
    endfunction
    // stage 1: lane capture
    reg [DEL-1:0] s1v; reg [31:0] s1a [0:DEL-1]; reg [31:0] s1i [0:DEL-1];
    // stage 2 / 3: pairwise levels (DEL = 4)
    reg s2v0, s2v1; reg [31:0] s2a0, s2i0, s2a1, s2i1;
    reg s3v; reg [31:0] s3a, s3i;
    reg accv; reg [31:0] acca, acci;
    reg [2:0] flush; reg res_sent, res_pend;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1v <= '0; s2v0 <= 1'b0; s2v1 <= 1'b0; s3v <= 1'b0; accv <= 1'b0; flush <= 3'd0; res_sent <= 1'b0; res_pend <= 1'b0;
        end else begin
            for (integer l = 0; l < DEL; l = l + 1) begin
                s1v[l] <= en && d_v[l]; s1a[l] <= d_f[l*PWT +: 32]; s1i[l] <= d_f[l*PWT + 32 +: 32];
            end
            s2v0 <= s1v[0] | s1v[1]; s2v1 <= s1v[2] | s1v[3];
            if (better(s1v[0], s1a[0], s1i[0], s1v[1], s1a[1], s1i[1]) || !s1v[1]) begin s2a0 <= s1a[0]; s2i0 <= s1i[0]; end
            else begin s2a0 <= s1a[1]; s2i0 <= s1i[1]; end
            if (better(s1v[2], s1a[2], s1i[2], s1v[3], s1a[3], s1i[3]) || !s1v[3]) begin s2a1 <= s1a[2]; s2i1 <= s1i[2]; end
            else begin s2a1 <= s1a[3]; s2i1 <= s1i[3]; end
            s3v <= s2v0 | s2v1;
            if (better(s2v0, s2a0, s2i0, s2v1, s2a1, s2i1) || !s2v1) begin s3a <= s2a0; s3i <= s2i0; end
            else begin s3a <= s2a1; s3i <= s2i1; end
            if (start) begin accv <= 1'b0; res_sent <= 1'b0; res_pend <= 1'b0; flush <= 3'd0; end
            else begin
                if (better(s3v, s3a, s3i, accv, acca, acci)) begin accv <= 1'b1; acca <= s3a; acci <= s3i; end
                // the endpoint's done: every flit is in the lanes; 4 edges flush the pipeline, then the result flit
                if (en && ep_done && !res_sent && !res_pend) begin res_pend <= 1'b1; flush <= 3'd5; end
                else if (res_pend) begin
                    if (flush != 3'd0) flush <= flush - 3'd1;
                    else begin res_pend <= 1'b0; res_sent <= 1'b1; end
                end
                if (!ep_done) res_sent <= 1'b0;   // retired: ready for the next run
            end
        end
    end
    wire emit = res_pend && flush == 3'd0;
    always @* begin
        if (!en) begin o_v = d_v; o_f = d_f; end
        else begin
            o_v = '0; o_f = '0;
            o_v[0] = emit;
            o_f[0 +: PWT] = {1'b1, 8'hFF, rank, 16'd0, {(FW-32){1'b0}}, acci};
        end
    end
    assign done_out = ep_done && (!en || res_sent);
endmodule
`default_nettype wire
