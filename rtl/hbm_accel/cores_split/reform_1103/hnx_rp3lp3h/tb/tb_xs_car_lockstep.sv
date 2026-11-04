// DIE-HBM-63 11-04: hnx_xs_car with AZ against the pinned body (no AZ) over every legal strap, a = {strap, AZ zero bits}.
// run_xs_car_lockstep.sh builds OLD from rtl/hbm_next/sm/hnx_xs3.sv at 4d6f5439dce as hnx_xs_car_old. AZM != AZ = mutant.
`timescale 1ns/1ps
module tb_xs_car_lockstep #(parameter integer NB = 532, parameter integer AZ = 2, parameter integer AZM = AZ);
    reg clk = 0; reg [10:0] a = 0;
    wire [NB-1:0] co, cn;
    hnx_xs_car_old #(.NB(NB)) u_o (.clk(clk), .a(a), .car(co));
    hnx_xs_car #(.NB(NB), .AZ(AZM)) u_n (.clk(clk), .a(a), .car(cn));
    integer s, c, bad = 0, n = 0;
    initial begin
        for (s = 0; s < (1 << (11 - AZ)); s = s + 1) begin
            a = s << AZ;
            for (c = 0; c < 6; c = c + 1) begin #1 clk = 1; #1 clk = 0; end
            n = n + 1;
            if (cn !== co || ^co === 1'bx) begin bad = bad + 1; if (bad < 5) $display("DIFF a=%0d", a); end
        end
        $display("NB=%0d AZ=%0d AZM=%0d straps=%0d mismatches=%0d", NB, AZ, AZM, n, bad);
        $finish;
    end
endmodule
