`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_stop (stream ds-control, 2026-10-08): the STOP CONDITION in the head die's sampler path (gap C14 of the
// T2 coverage ledger: the array stopped on a fixed gen_len count only, with no EOS compare and no maximum-length
// clamp).  It sits between the head root's ordered argmax (the step's greedy token, ot_dsrom S81 native head
// terminal) and the RESULT framer (ot_s81_hop_tx), one register stage:
//     stop = (EOSEN && token == EOS) || (pos + 1 >= MAXL)
// where pos is the position the step computed (its token goes to position pos + 1), EOS the released
// eos_token_id (1, compiler/models/deepseek-v4.1-flash/config.json) and MAXL the run's maximum sequence length
// (positions 0 .. MAXL-1).  The run configuration arrives in every HIDDEN header (ot_s81_hdr.svh), so the head die
// needs no configuration path.  The SOURCE honours STOP only on generated positions (pos + 1 >= prompt length) and
// also bounds every user by gen_len.  Cost: +1 cycle on the head's token output (the register), priced per token.
// ---------------------------------------------------------------------------
module ot_s81_stop #(
    parameter integer NW = 21
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          am_v,          // argmax result of the step
    input  wire [NW-1:0] am_pos,
    input  wire [NW-1:0] am_tok,
    input  wire [31:0]   am_val,
    input  wire          run_eosen,
    input  wire [NW-1:0] run_eos,
    input  wire [NW:0]   run_maxl,
    output reg           res_v,
    output reg  [NW-1:0] res_tok,
    output reg  [31:0]   res_val,
    output reg           res_stop,
    output reg  [31:0]   st_eos,
    output reg  [31:0]   st_maxl
);
    wire eos  = run_eosen && (am_tok == run_eos);
    wire maxl = ({1'b0, am_pos} + 1'b1) >= run_maxl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            res_v <= 1'b0; res_tok <= 0; res_val <= 0; res_stop <= 1'b0; st_eos <= 0; st_maxl <= 0;
        end else begin
            res_v <= am_v;
            if (am_v) begin
                res_tok <= am_tok; res_val <= am_val; res_stop <= eos || maxl;
                if (eos) st_eos <= st_eos + 1;
                if (maxl) st_maxl <= st_maxl + 1;
            end
        end
    end
endmodule
