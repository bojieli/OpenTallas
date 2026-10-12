`timescale 1ns/1ps
// Cycle-exact equivalence: ot_hgi_qw_dec3 (three tiles, track B) vs ot_hgi_qw_dec (one tile), random back-to-back beats
// over ops 4 (FP8 actquant), 5 (FP4 actquant), 6 (E4M3/FP4 qdq) and illegal headers; every output compared every edge.
// MUT=1 (dec3 actquant fp4 flipped) must FAIL.  +N=<beats> (default 20000).
module tb_hgi_qw_dec3_equiv #(parameter integer MUT = 0);
    reg clk = 0, rst_n = 0, v = 0;
    reg [127:0] header = 0; reg [1023:0] x = 0;
    wire r_vo, r_f, r_df, d_vo, d_f, d_df; wire [511:0] r_y, d_y;
    ot_hgi_qw_dec  ref_u (.clk(clk), .rst_n(rst_n), .v(v), .header(header), .x(x), .vo(r_vo), .y(r_y), .fault(r_f), .decode_fault(r_df));
    ot_hgi_qw_dec3 #(.MUTANT(MUT)) dut (.clk(clk), .rst_n(rst_n), .v(v), .header(header), .x(x), .vo(d_vo), .y(d_y), .fault(d_f), .decode_fault(d_df));
    always #1 clk = ~clk;
    integer n, cyc, errs, nv, nf, ndf, i, op_sel, N;
    reg [31:0] e;
    function automatic [31:0] rnd_f32(input integer sc);
        reg [31:0] r; integer k;
        begin
            r = $urandom; k = $urandom % 100;
            if (k < 2) rnd_f32 = {r[31], 31'd0};                         // +-0
            else if (k < 3 && sc) rnd_f32 = {r[31], 8'hFF, r[22:0]};     // inf / nan (fault)
            else if (k < 6) rnd_f32 = {r[31], 8'd0, r[22:0]};            // subnormal
            else rnd_f32 = {r[31], 8'(100 + ($urandom % 50)), r[22:0]};
        end
    endfunction
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 20000;
        errs = 0; nv = 0; nf = 0; ndf = 0;
        repeat (8) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        for (n = 0; n < N + 64; n = n + 1) begin
            @(negedge clk);
            v = (n < N) && (($urandom % 8) != 0);
            op_sel = $urandom % 16;
            header = {$urandom, $urandom, $urandom, $urandom};
            header[127:124] = (op_sel == 15) ? 4'd3 : 4'd4;
            header[123:118] = (op_sel < 5) ? 6'd4 : (op_sel < 10) ? 6'd5 : (op_sel == 14) ? 6'd7 : 6'd6;
            header[71:64] = (op_sel == 13) ? 8'd8 : 8'd16;
            for (i = 0; i < 32; i = i + 1) x[32*i +: 32] = rnd_f32(($urandom % 64) == 0);
        end
        $display("%s HGI_QW_DEC3_EQUIV beats %0d valid-out %0d fault %0d decode_fault %0d errors %0d",
                 (errs == 0 && nv > N / 2) ? "PASS" : "FAIL", N, nv, nf, ndf, errs);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        if (r_vo) nv <= nv + 1; if (r_vo && r_f) nf <= nf + 1; if (r_df) ndf <= ndf + 1;
        if (r_vo !== d_vo || r_f !== d_f || r_df !== d_df || (r_vo && r_y !== d_y)) begin
            errs <= errs + 1;
            if (errs < 5) $display("MISMATCH t=%0t vo %b/%b f %b/%b df %b/%b y_eq %b", $time, r_vo, d_vo, r_f, d_f, r_df, d_df, r_y === d_y);
        end
    end
endmodule
