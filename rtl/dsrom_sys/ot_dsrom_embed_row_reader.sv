`timescale 1ns/1ps
// ot_dsrom_embed_row_reader -- the DS-ROM embedding row read (S81 home: results/quality/
// w16_dsrom_embedding_head_home_20261001/contract.json): the token's owner rank (token_id / 32,320) holds its vocab
// quarter as BF16 rows of 320 274-bit ROM words (16 BF16 lanes a word, word h*8+b, lane l = element
// h*128 + l*8 + b; tools/rtl_v41_rom_array.py bf16_word), one row inside one 4,096-word bank.  On `start` the reader
// issues the row's WORDS consecutive word reads to the bank macro at one a cycle and returns each word as 16 FP32
// lanes (BF16 << 16) with its word index, one word a cycle, through one output register.
//   cycle 0: start registered (addr / count); 1..WORDS: macro reads (ce each cycle); +1 macro clk->q register;
//   +1 unpack / output register.
// Default-off: ENABLE = 0 elaborates to tied-off outputs (no macro).
module ot_dsrom_embed_row_reader #(
    parameter int    WORDS  = 320,
    parameter int    AW     = 13,
    parameter string VIAMAP = "",
    parameter bit    ENABLE = 0
) (
    input  logic          clk,
    input  logic          rst_n,
    input  logic          start,
    input  logic [AW-1:0] base,
    output logic          o_v,
    output logic [8:0]    o_idx,
    output logic [511:0]  o_d,
    output logic          busy
);
    generate if (!ENABLE) begin : g_off
        assign o_v = 1'b0; assign o_idx = '0; assign o_d = '0; assign busy = 1'b0;
    end else begin : g_on
        logic [AW-1:0] addr;
        logic [8:0]    left, idx_a, idx_q;
        logic          rd, v_q;
        logic [273:0]  q;
        ot_rom_8192x274_m8 #(.VIAMAP(VIAMAP)) u_bank (.clk(clk), .ce_in(rd), .addr_in(addr), .rd_out(q));
        always_ff @(posedge clk) begin
            if (!rst_n) begin
                left <= '0; rd <= 1'b0; v_q <= 1'b0; o_v <= 1'b0;
            end else begin
                if (start && left == 0 && !rd) begin
                    addr <= base; left <= 9'(WORDS); rd <= 1'b1; idx_a <= '0;
                end else if (rd) begin
                    if (left == 1) rd <= 1'b0; else begin addr <= addr + 1'b1; idx_a <= idx_a + 1'b1; end
                    left <= left - 1'b1;
                end
                v_q <= rd; idx_q <= idx_a;                     // macro clk->q register stage
                o_v <= v_q; o_idx <= idx_q;
                for (int l = 0; l < 16; l++) o_d[32 * l +: 32] <= {q[16 * l +: 16], 16'h0000};
            end
        end
        assign busy = rd | v_q | o_v;
    end endgenerate
endmodule
