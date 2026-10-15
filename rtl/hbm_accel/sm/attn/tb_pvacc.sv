`timescale 1ns/1ps
module tb_pvacc;
    parameter integer MUT = 0;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg in_v = 0, f = 0, l = 0, g = 0; reg [1:0] k = 0, ci = 0; reg [63:0] code = 0; reg [9:0] e = 0; reg [31:0] p = 0;
    wire ov, flt; wire [1:0] ok; wire [255:0] oy;
    ot_hbm_accel_smh_pvacc #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_k(k), .in_cfirst(f), .in_clast(l),
        .in_ci(ci), .in_glast(g), .in_code(code), .in_e(e), .in_p(p), .out_v(ov), .out_k(ok), .out_y(oy), .fault(flt));
    integer fd, fo, r; integer a0, a1, a2, a3, a4, a5; reg [63:0] tc; reg [9:0] te; reg [31:0] tp;
    always @(posedge clk) if (ov) $fdisplay(fo, "OUT %0d %064x", ok, oy);
    initial begin
        fd = $fopen({`DIR, "/stim.txt"}, "r"); fo = $fopen({`DIR, "/out.txt"}, "w");
        repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
        while (!$feof(fd)) begin
            r = $fscanf(fd, "%d %d %d %d %d %d %h %h %h\n", a0, a1, a2, a3, a4, a5, tc, te, tp);
            @(negedge clk); in_v = a0[0]; k = a1[1:0]; f = a2[0]; l = a3[0]; ci = a4[1:0]; g = a5[0]; code = tc; e = te; p = tp;
        end
        @(negedge clk); in_v = 0; repeat (20) @(posedge clk);
        if (flt) $fdisplay(fo, "FAULT");
        $fclose(fo); $finish;
    end
endmodule
