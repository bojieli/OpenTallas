`timescale 1ns/1ps
// Lockstep bench: ot_dshbm_expert_union FAST = 0 (as built) vs FAST = 1, every output compared every cycle on
// NCASE random unions (1..PM columns of K ids, partial add_en, clustered / spread / edge ids, random out_ready).
module tb_union_lockstep;
    parameter integer NE = 384, K = 6, PM = 8, IW = 9, NCASE = 3000, SEED = 1;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg clr = 0, add_v = 0, flush = 0, ordy = 1; reg [2:0] add_col = 0; reg [K*IW-1:0] add_ids = 0; reg [K-1:0] add_en = 0;
    wire v0, v1, l0, l1, b0, b1; wire [IW-1:0] i0, i1; wire [PM-1:0] m0, m1; wire [IW:0] c0, c1;
    ot_dshbm_expert_union #(.NE(NE), .K(K), .PM(PM), .IW(IW), .FAST(0)) d0 (.clk(clk), .rst_n(rst_n), .clr(clr),
        .add_v(add_v), .add_col(add_col), .add_ids(add_ids), .add_en(add_en), .flush(flush), .out_v(v0), .out_ready(ordy),
        .out_id(i0), .out_mask(m0), .out_last(l0), .busy(b0), .count(c0));
    ot_dshbm_expert_union #(.NE(NE), .K(K), .PM(PM), .IW(IW), .FAST(1)) d1 (.clk(clk), .rst_n(rst_n), .clr(clr),
        .add_v(add_v), .add_col(add_col), .add_ids(add_ids), .add_en(add_en), .flush(flush), .out_v(v1), .out_ready(ordy),
        .out_id(i1), .out_mask(m1), .out_last(l1), .busy(b1), .count(c1));
    integer bad = 0, emitted = 0, cyc = 0, seed, c, j, k, np, md;
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (v0 !== v1 || b0 !== b1 || c0 !== c1 || (v0 && (i0 !== i1 || m0 !== m1 || l0 !== l1))) begin
            bad = bad + 1; if (bad < 10) $display("MISMATCH cyc %0d v %b%b id %0d %0d m %h %h l %b%b b %b%b c %0d %0d", cyc, v0, v1, i0, i1, m0, m1, l0, l1, b0, b1, c0, c1);
        end
        if (v0 && ordy) emitted = emitted + 1;
    end
    function integer rid(input integer m);
        integer r;
        begin
            r = $unsigned($random(seed));
            case (m)
                0: rid = r % NE;
                1: rid = (r % 40) + 32 * ((r >> 8) % 3);          // clustered in a few words
                2: rid = (r & 1) ? (NE - 1 - (r >> 4) % 4) : ((r >> 4) % 4);  // edges
                default: rid = 32 * ((r >> 3) % (NE / 32)) + (r & 31);
            endcase
        end
    endfunction
    initial begin
        seed = SEED;
        repeat (3) @(posedge clk); rst_n = 1;
        for (c = 0; c < NCASE; c = c + 1) begin
            md = c % 4;
            @(negedge clk); clr = 1; @(negedge clk); clr = 0;
            np = 1 + $unsigned($random(seed)) % PM;
            for (j = 0; j < np; j = j + 1) begin
                add_v = 1; add_col = j;
                for (k = 0; k < K; k = k + 1) add_ids[k*IW +: IW] = rid(md);
                add_en = (c % 5 == 0) ? ($random(seed) | 1) : {K{1'b1}};
                @(negedge clk);
                if (($random(seed) & 3) == 0) begin add_v = 0; @(negedge clk); end
            end
            add_v = 0;
            if ($random(seed) & 1) @(negedge clk);
            flush = 1; @(negedge clk); flush = 0;
            while (b0 || b1) begin ordy = (c % 3 == 0) ? $random(seed) : 1'b1; @(negedge clk); end
            ordy = 1;
        end
        $display("LOCKSTEP union cases=%0d emitted=%0d mismatches=%0d", NCASE, emitted, bad);
        $finish;
    end
endmodule
