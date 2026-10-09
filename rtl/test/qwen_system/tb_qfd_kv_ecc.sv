`timescale 1ns/1ps
// KV sector ECC bench (qwen-system 2026-10-08): ot_qfd_kv_ecc encode -> store -> decode.
//   NS random sectors: clean read (no CE/UE, data exact); EVERY single-bit flip of the 288 stored bits (corrected,
//   data exact, CE, no UE); EVERY double-bit flip inside one SECDED word (72 x 71 / 2 x 4 a sector: UE, never a silent
//   wrong release); random double flips across two words (each corrected).  MUT = 1 must fail.
module tb_qfd_kv_ecc;
    parameter integer NS = 6, MUT = 0;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg s_v = 0, c_v = 0; reg [255:0] s_d = 0; reg [287:0] c_d = 0;
    wire e_v, d_v, d_ce, d_ue, ue_fault; wire [287:0] e_d; wire [255:0] d_d; wire [31:0] ce_count;
    ot_qfd_kv_ecc #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .s_v(s_v), .s_d(s_d), .e_v(e_v), .e_d(e_d), .c_v(c_v),
        .c_d(c_d), .d_v(d_v), .d_d(d_d), .d_ce(d_ce), .d_ue(d_ue), .ue_fault(ue_fault), .ce_count(ce_count));
    integer n, i, j, w, bad = 0, n_clean = 0, n_ce = 0, n_ue = 0, n_x = 0, silent = 0;
    reg [287:0] code;
    task automatic rd(input [287:0] x, input integer kind);   // 0 clean, 1 correctable, 2 uncorrectable
        begin
            @(negedge clk); c_v = 1; c_d = x; @(negedge clk); c_v = 0;
            case (kind)
                0: begin n_clean = n_clean + 1; if (d_ce || d_ue || d_d !== s_d) bad = bad + 1; end
                1: begin n_ce = n_ce + 1; if (!d_ce || d_ue || d_d !== s_d) bad = bad + 1; end
                2: begin n_ue = n_ue + 1; if (!d_ue) begin bad = bad + 1; if (d_d !== s_d) silent = silent + 1; end end
            endcase
        end
    endtask
    initial begin
        repeat (3) @(negedge clk); rst_n = 1;
        for (n = 0; n < NS; n = n + 1) begin
            for (w = 0; w < 8; w = w + 1) s_d[32*w +: 32] = $random;
            if (n == 0) s_d = 0;
            if (n == 1) s_d = {256{1'b1}};
            @(negedge clk); s_v = 1; @(negedge clk); s_v = 0; code = e_d;
            rd(code, 0);
            for (i = 0; i < 288; i = i + 1) rd(code ^ (288'd1 << i), 1);
            for (w = 0; w < 4; w = w + 1)
                for (i = 0; i < 72; i = i + 1)
                    for (j = i + 1; j < 72; j = j + 1) begin : dbl
                        integer bi, bj;
                        bi = (i < 64) ? 64*w + i : 256 + 8*w + (i - 64);
                        bj = (j < 64) ? 64*w + j : 256 + 8*w + (j - 64);
                        rd(code ^ (288'd1 << bi) ^ (288'd1 << bj), 2);
                    end
            for (i = 0; i < 64; i = i + 1) begin : x2
                integer a, b;
                a = $urandom % 64; b = 64 + ($urandom % 64);        // words 0 and 1: one error each
                rd(code ^ (288'd1 << a) ^ (288'd1 << b), 1); n_x = n_x + 1;
            end
        end
        $display("KV_ECC_RESULT pass=%0d sectors=%0d clean=%0d corrected=%0d (single + two-word doubles) double_same_word=%0d double_two_words=%0d bad=%0d silent_wrong=%0d ue_fault=%0d ce_count=%0d mut=%0d",
                 bad == 0 && ue_fault, NS, n_clean, n_ce, n_ue, n_x, bad, silent, ue_fault, ce_count, MUT);
        $finish;
    end
endmodule
