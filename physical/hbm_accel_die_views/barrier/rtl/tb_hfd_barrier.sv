`timescale 1ns/1ps
// hfd_barrier wrapper bench: two 32-way sense-reversing barriers behind the die ports. One seed; exits nonzero on any
// mismatch. Checks: release only when ALL 32 arrive senses of a node toggled (31 of 32 must not release), both senses,
// node independence, release latency.
module tb_hfd_barrier;
    reg [0:0] ck = 0, rst = 1; reg [63:0] f = 0; wire [63:0] t;
    hfd_barrier dut(.ck(ck), .f_cmdproc(f), .rst(rst), .t_cmdproc(t));
    always #0.4165 ck = ~ck;
    integer err = 0, checks = 0, lat;
    task automatic expect_t(input [63:0] e, input integer cyc);
        integer k; begin
            for (k = 0; k < cyc; k = k + 1) @(posedge ck);
            #0.1 checks = checks + 1;
            if (t !== e) begin err = err + 1; $display("MISMATCH t=%h exp=%h at %0t", t, e, $time); end
        end endtask
    task automatic measure(input integer lo, input e);
        integer k; begin
            lat = -1;
            for (k = 0; k < 20 && lat < 0; k = k + 1) begin @(posedge ck); #0.1 if (t[lo] === e) lat = k + 1; end
        end endtask
    integer s, seed = 20261006;
    initial begin
        repeat (6) @(posedge ck); rst = 0; repeat (6) @(posedge ck);
        expect_t(64'h0, 1);
        for (s = 0; s < 8; s = s + 1) begin
            // node 0: raise 31 of 32 (random hole) -> no release
            begin : blk
                integer hole; reg sense;
                sense = ~f[0];
                hole = $urandom(seed) % 32; seed = seed + 1;
                f[31:0] = {32{sense}}; f[hole] = ~sense;
                expect_t({t[63:32], {32{~sense}}}, 10);
                f[hole] = sense;
                measure(0, sense);
                checks = checks + 1;
                if (lat != 4) begin err = err + 1; $display("LATENCY node0 %0d != 4", lat); end
                expect_t({t[63:32], {32{sense}}}, 1);
                // node 1 independent: full toggle
                f[63:32] = {32{~f[32]}};
                expect_t({{32{f[32]}}, {32{sense}}}, 8);
            end
        end
        $display("BARRIER_TB checks=%0d mismatches=%0d", checks, err);
        if (err != 0 || checks < 20) $fatal(1, "FAIL");
        $finish;
    end
endmodule
