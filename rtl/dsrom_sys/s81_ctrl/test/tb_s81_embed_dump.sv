`timescale 1ns/1ps
// tb_s81_embed_dump (s81-functional-token r3, 2026-10-14): the S81 embed stage's row read for the continuous run --
// ot_dsrom_embed_row_reader (ENABLE 1) on the ASAP7 ROM macro model personalised with the real token's BF16 row
// (tools/dsrom_1m_embed.py golden: embed.viamap.hex), every output word dumped as "<idx> <512b>" to embed_words.mem
// (+OUT=<file>) and checked against embed_exp.mem; tools/s81_ftok/embed_hin.py packs the RTL words into L0's HIDDEN
// flits.  Verdict: EMBDUMP PASS|FAIL.
module tb_s81_embed_dump;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0, start = 1'b0; reg [12:0] base; integer b = 0;
    wire o_v, busy; wire [8:0] o_idx; wire [511:0] o_d;
    reg [511:0] exp_ [0:319];
    integer cyc = 0, n = 0, err = 0, fd;
    string of;
    ot_dsrom_embed_row_reader #(.WORDS(320), .VIAMAP("embed.viamap.hex"), .ENABLE(1)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .base(base), .o_v(o_v), .o_idx(o_idx), .o_d(o_d), .busy(busy));
    initial begin
        $readmemh("embed_exp.mem", exp_);
        if (!$value$plusargs("BASE=%d", b)) b = 0;
        if (!$value$plusargs("OUT=%s", of)) of = "embed_words.mem";
        base = b[12:0]; fd = $fopen(of, "w");
    end
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        start <= (cyc == 8);
        if (o_v) begin
            $fdisplay(fd, "%0d %0128h", o_idx, o_d);
            if (o_d !== exp_[o_idx] || o_idx != n[8:0]) err = err + 1;
            n = n + 1;
        end
        if ((cyc > 8 && !busy && n == 320) || cyc > 5000) begin
            $fclose(fd);
            $display("EMBDUMP words=%0d errors=%0d %s", n, err, (n == 320 && err == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
