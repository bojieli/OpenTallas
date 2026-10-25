`timescale 1ns/1ps
// PATH-S81/ENG2 10-25: exact miter of ot_s81eng_xq_n32 (-DOT_S81ENG_XQ_OHSEL) vs the unchanged text (*_ref), driven
// directly at its o_* / vi_* pins so trains run in every window (the core-level miter depends on the lookup producing
// beats).  Reset pulses mid-run, o_v stalls; vo_a, vo_b, fault compared on EVERY cycle.
module tb;
`ifdef OHSEL_MUT
    localparam integer XM = 3;
`else
    localparam integer XM = 0;
`endif
    reg ck = 0, rst_n = 0, o_v = 0;
    reg [4:0] o_col = 0; reg [2:0] o_beat = 0; reg [263:0] o_d = 0;
    reg [275:0] vi_a = 0, vi_b = 0;
    wire [275:0] vo_a, vo_b, vo_a_r, vo_b_r; wire f, f_r;
    ot_s81eng_xq_n32 #(.MUT(XM)) dut (.ck(ck), .rst_n(rst_n), .o_v(o_v), .o_col(o_col), .o_beat(o_beat), .o_d(o_d),
        .vi_a(vi_a), .vo_a(vo_a), .vi_b(vi_b), .vo_b(vo_b), .fault(f));
    ot_s81eng_xq_n32_ref ref0 (.ck(ck), .rst_n(rst_n), .o_v(o_v), .o_col(o_col), .o_beat(o_beat), .o_d(o_d),
        .vi_a(vi_a), .vo_a(vo_a_r), .vi_b(vi_b), .vo_b(vo_b_r), .fault(f_r));
    reg [63:0] s;
    function automatic [63:0] xs(input [63:0] x);
        reg [63:0] t; begin t = x ^ (x << 13); t = t ^ (t >> 7); xs = t ^ (t << 17); end
    endfunction
    integer cyc = 0, ncyc = 40000, seed = 1, mis = 0, n_tx = 0, n_txnz = 0, n_s1 = 0, n_pass = 0, n_rst = 0, k, gap = 0, ph = 0;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 40000;
        s = 64'h9e3779b97f4a7c15 ^ {32'd0, seed[31:0]} ^ ({32'd0, seed[31:0]} << 29);
    end
    always #1 ck = ~ck;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        s = xs(s);
        if (cyc == 8) rst_n <= 1;
        if (cyc == ncyc / 3 || (cyc > 2 * ncyc / 3 && s[12:0] == 13'd77 && n_rst < 3)) begin rst_n <= 0; gap = 3 + s[16:14]; n_rst <= n_rst + 1; end
        else if (!rst_n && cyc > 8) begin if (gap == 0) rst_n <= 1; else gap = gap - 1; end
        // windows of 48 beats (24 cols x 2 beats) with random stalls, then an idle gap for the train + pass-through
        ph = cyc % 400;
        o_v <= (ph < 120) && (s[2:0] != 3'd0);
        if ((ph < 120) && (s[2:0] != 3'd0)) begin o_beat <= o_beat + 3'd1; if (o_beat == 3'd7) o_col <= o_col + 5'd1; end
        if (ph == 399) begin o_beat <= 0; o_col <= 0; end
        for (k = 0; k < 4; k = k + 1) begin s = xs(s); o_d[64*k +: 64] <= s; end
        s = xs(s); o_d[263:256] <= s[7:0];
        s = xs(s); vi_a[63:0] <= s; vi_a[0] <= (s[6:0] == 7'd0); s = xs(s); vi_a[127:64] <= s; s = xs(s); vi_a[191:128] <= s;
        s = xs(s); vi_a[255:192] <= s; vi_a[275:256] <= s[19:0];
        s = xs(s); vi_b[63:0] <= s; vi_b[0] <= (s[6:0] == 7'd1); s = xs(s); vi_b[127:64] <= s; s = xs(s); vi_b[191:128] <= s;
        s = xs(s); vi_b[255:192] <= s; vi_b[275:256] <= s[19:0];
        if (dut.tx) begin n_tx <= n_tx + 1; if (vo_b[275:1] != 0) n_txnz <= n_txnz + 1; if (dut.fc[1:0] == 2'd1) n_s1 <= n_s1 + 1; end
        else if (rst_n && vo_b[275:1] != 0) n_pass <= n_pass + 1;
        if ({vo_a, vo_b, f} !== {vo_a_r, vo_b_r, f_r}) begin
            if (mis < 5) $display("MISMATCH cyc=%0d vo_a %0d vo_b %0d fault %b/%b", cyc, vo_a != vo_a_r, vo_b != vo_b_r, f, f_r);
            mis <= mis + 1;
        end
        if (cyc == ncyc) begin
            $display("ENG2_XQ_MITER %s seed=%0d cycles=%0d mismatches=%0d resets=%0d tx_cycles=%0d tx_nonzero_vo_b=%0d frag1_cycles=%0d pass_nonzero=%0d",
                     (mis == 0 && n_tx > 200 && n_txnz > 100 && n_s1 > 50 && n_pass > 100) ? "PASS" : "FAIL", seed, ncyc, mis, n_rst + 1,
                     n_tx, n_txnz, n_s1, n_pass);
            $finish;
        end
    end
endmodule
