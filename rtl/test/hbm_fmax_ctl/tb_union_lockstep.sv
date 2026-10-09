`timescale 1ns/1ps
// Stream lockstep: ot_dshbm_expert_union FAST = 0 (as built) vs FAST = 1 on NCASE random unions (1..PM columns of
// K ids, partial add_en, clustered / spread / edge ids, random out_ready back-pressure).  Per case the emitted
// {id, mask, last} streams must be equal and the final counts equal; the flush -> first-id latency of each
// (out_ready high) is recorded.
module tb_union_lockstep;
    parameter integer NE = 384, K = 6, PM = 8, IW = 9, NCASE = 3000, SEED = 1, MAXE = 64;
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
    reg [IW+PM:0] s0 [0:MAXE-1], s1 [0:MAXE-1];
    integer e0, e1, f0, f1, tfl, cyc = 0, bad = 0, emitted = 0, lat0 = 0, lat1 = 0, seed, c, j, k, np, md;
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (v0 && ordy) begin if (e0 == 0) f0 = cyc - tfl; s0[e0] = {i0, m0, l0}; e0 = e0 + 1; end
        if (v1 && ordy) begin if (e1 == 0) f1 = cyc - tfl; s1[e1] = {i1, m1, l1}; e1 = e1 + 1; end
    end
    function integer rid(input integer m);
        integer r;
        begin
            r = $unsigned($random(seed));
            case (m)
                0: rid = r % NE;
                1: rid = (r % 40) + 32 * ((r >> 8) % 3);
                2: rid = (r & 1) ? (NE - 1 - (r >> 4) % 4) : ((r >> 4) % 4);
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
            e0 = 0; e1 = 0; tfl = cyc + 1;
            flush = 1; @(negedge clk); flush = 0;
            while (b0 || b1) begin ordy = (c % 3 == 0) ? $random(seed) : 1'b1; @(negedge clk); end
            ordy = 1;
            if (e0 != e1 || c0 !== c1) begin bad = bad + 1; if (bad < 8) $display("MISMATCH case %0d n %0d %0d count %0d %0d", c, e0, e1, c0, c1); end
            else for (j = 0; j < e0; j = j + 1) if (s0[j] !== s1[j]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH case %0d item %0d", c, j); end
            if (c % 3 != 0) begin lat0 = f0; lat1 = f1; end
            emitted = emitted + e0;
        end
        $display("LOCKSTEP union cases=%0d emitted=%0d mismatches=%0d flush_to_first0=%0d flush_to_first1=%0d", NCASE, emitted, bad, lat0, lat1);
        $finish;
    end
endmodule
