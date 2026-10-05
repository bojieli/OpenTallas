`timescale 1ns/1ps
// SECDED decoder check: +VEC=<file> lines "codeword_hex data_hex status" with
// status 0 ok, 1 corrected, 2 uncorrectable (from tools/mem_compiler/ecc.py);
// every line is decoded by rtl/dft/ot_rom_secded_dec.sv and compared.
module tb_secded #(parameter integer K = 64) (input wire clk);
    localparam integer R = ecc_r(K);
    localparam integer N = K + R + 1;
    function automatic integer ecc_r(input integer k);
        integer r;
        begin
            r = 1;
            while ((1 << r) < k + r + 1) r = r + 1;
            ecc_r = r;
        end
    endfunction
    reg [N-1:0] cw;
    reg [K-1:0] exp_d;
    integer st, fd, n, lines = 0, errs = 0;
    wire [K-1:0] d;
    wire c, u;
    ot_rom_secded_dec #(.K(K)) dut (.cw(cw), .data(d), .corrected(c), .uncorrectable(u));
    reg [8*512-1:0] fname;
    initial begin
        if (!$value$plusargs("VEC=%s", fname)) $finish;
        fd = $fopen(fname, "r");
    end
    reg have = 1'b0;
    always @(posedge clk) begin
        if (fd == 0 || $feof(fd)) begin
            $display("SECDED K=%0d vectors=%0d errors=%0d", K, lines, errs);
            $finish;
        end else begin
            n = $fscanf(fd, "%h %h %d\n", cw, exp_d, st);
            have <= (n == 3);
        end
    end
    always @(negedge clk) if (have) begin
        lines = lines + 1;
        if ((st == 0 && (d !== exp_d || c || u)) || (st == 1 && (d !== exp_d || !c || u))
            || (st == 2 && (!u || c))) begin
            if (errs < 5) $display("MISMATCH cw=%h d=%h exp=%h c=%b u=%b st=%0d", cw, d, exp_d, c, u, st);
            errs = errs + 1;
        end
    end
endmodule
