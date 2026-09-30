`timescale 1ns/1ps
// W15b: ot_coll_topk_merge against tools/hdc_golden_v41.topk_lowest_index (tools/w15_topk_merge.py builds the
// cases and checks the output).  +VEC=<dir>: cases.hex (per case: n, k, stride), score.hex / id.hex (per case
// N*n/16 words, rank-major).  Prints one TOPK line per case and the ids to <dir>/out.hex.
module tb_w15_topk_merge #(parameter integer N = 4, NMAX = 512, P = 64, DIG = 4, NCASE = 8);
    localparam integer RB = (N > 1) ? $clog2(N) : 1, CAP = N * NMAX, CB = $clog2(CAP + 1), WB = $clog2(CAP / 16);
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg [95:0] cs [0:NCASE-1];
    reg [511:0] sc [0:NCASE*CAP/16-1];
    reg [511:0] idw [0:NCASE*CAP/16-1];
    string vec;
    integer fo;
    reg ld_valid = 0, ld_id = 0, go = 0;
    reg [RB-1:0] ld_rank = 0;
    reg [WB-1:0] ld_word = 0;
    reg [511:0] ld_data = 0;
    reg [CB-1:0] n = 16, k = 1;
    reg [31:0] stride = 0;
    wire busy, done, fault, ov, ol;
    wire [512*(P/16)-1:0] od;
    wire [$clog2(P/16+1)-1:0] onw;
    wire [31:0] cyc;
    ot_coll_topk_merge #(.N(N), .NMAX(NMAX), .P(P), .DIG(DIG)) dut (
        .clk(clk), .rst_n(rst_n), .ld_valid(ld_valid), .ld_id(ld_id), .ld_rank(ld_rank), .ld_word(ld_word),
        .ld_data(ld_data), .go(go), .n(n), .k(k), .stride(stride), .busy(busy), .done(done), .fault(fault),
        .out_valid(ov), .out_nw(onw), .out_data(od), .out_last(ol), .stat_cycles(cyc));
    integer nw;
    always @(posedge clk) if (ov) begin
        for (integer l = 0; l < 16 * onw; l = l + 1) $fwrite(fo, "%08x\n", od[32*l +: 32]);
        nw = nw + onw;
    end
    initial begin
        if (!$value$plusargs("VEC=%s", vec)) $fatal(1, "VEC");
        $readmemh({vec, "/cases.hex"}, cs);
        $readmemh({vec, "/score.hex"}, sc);
        $readmemh({vec, "/id.hex"}, idw);
        fo = $fopen({vec, "/out.hex"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        for (integer c = 0; c < NCASE; c = c + 1) begin
            n = cs[c][95:64]; k = cs[c][63:32]; stride = cs[c][31:0];
            @(posedge clk);
            for (integer r = 0; r < N; r = r + 1)
                for (integer w = 0; w < n / 16; w = w + 1)
                    for (integer t = 0; t < 2; t = t + 1) begin
                        ld_valid <= 1; ld_id <= t; ld_rank <= r; ld_word <= w;
                        ld_data <= t ? idw[c*CAP/16 + r*(n/16) + w] : sc[c*CAP/16 + r*(n/16) + w];
                        @(posedge clk);
                    end
            ld_valid <= 0;
            @(posedge clk);
            nw = 0;
            go <= 1; @(posedge clk); go <= 0;
            wait (done || fault);
            @(posedge clk);
            $display("TOPK case=%0d n=%0d k=%0d words=%0d cycles=%0d fault=%0d", c, n, k, nw, cyc, fault);
            if (fault) $finish;
        end
        $fclose(fo);
        $display("TOPKDONE");
        $finish;
    end
    initial begin #50000000; $display("TOPKTIMEOUT"); $finish; end
endmodule
