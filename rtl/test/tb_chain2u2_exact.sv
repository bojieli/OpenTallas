`timescale 1ns/1ps
// tb_chain2u2_exact (BF unroll-by-2, 2026-10-07): ot_v41_chain2u2 against ot_v41_chain2 on a dense random term stream
// that obeys the issue side's rule (a slot revisited >= LAT cycles later, at exactly LAT and LAT + 1 often, so both
// same-adder and cross-adder forwarding and the accumulator path are exercised), random first / last, random FP32
// terms incl. specials, idle gaps.  Every chain output (sum, flag, tag) must match in order; fault must stay low.
module tb_chain2u2_exact;
    localparam integer NCH = 8, TW = 6, LAT = 8, N = 400000;
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg v = 0, first = 0, last = 0, tf = 0; reg [2:0] slot = 0; reg [31:0] term = 0; reg [TW-1:0] tag = 0;
    wire rv, uv, rf, uf, rfa, ufa; wire [31:0] rs, us; wire [TW-1:0] rt, ut;
    ot_v41_chain2 #(.NCH(NCH), .TW(TW)) u_r (.clk(clk), .rst_n(rst_n), .v(v), .slot(slot), .first(first), .last(last),
        .term(term), .term_f(tf), .tag(tag), .ov(rv), .osum(rs), .of(rf), .otag(rt), .fault(rfa));
    ot_v41_chain2u2 #(.NCH(NCH), .TW(TW)) u_u (.clk(clk), .rst_n(rst_n), .v(v), .slot(slot), .first(first), .last(last),
        .term(term), .term_f(tf), .tag(tag), .ov(uv), .osum(us), .of(uf), .otag(ut), .fault(ufa));
    reg [38:0] qr [0:N-1]; integer nr = 0, nu = 0, nc = 0;
    always @(posedge clk) if (rst_n) begin
        if (rv) begin qr[nr] = {rs, rf, rt}; nr = nr + 1; end
        if (uv) begin
            if (nu >= nr) $fatal(1, "U2 DIFF: candidate ahead n=%0d", nu);
            if (qr[nu] !== {us, uf, ut}) $fatal(1, "U2 DIFF n=%0d ref=%h cand=%h", nu, qr[nu], {us, uf, ut});
            nu = nu + 1; nc = nc + 1;
        end
    end
    integer last_t [0:NCH-1]; reg open_ [0:NCH-1]; integer t, s, i, tries;
    function automatic [31:0] rterm(input integer r);
        case (r % 16)
            0: rterm = 32'h0; 1: rterm = 32'h8000_0000; 2: rterm = 32'h7f80_0000; 3: rterm = {$random} | 32'h7f80_0001;
            4: rterm = {1'b0, 8'd1, 23'($random)}; 5: rterm = {1'b1, 8'd254, 23'($random)};
            default: rterm = {$random} & 32'hbfff_ffff;
        endcase
    endfunction
    initial begin
        for (i = 0; i < NCH; i = i + 1) begin last_t[i] = -100; open_[i] = 0; end
        repeat (3) @(negedge clk); rst_n = 1;
        for (t = 0; t < N / 3; t = t + 1) begin
            @(negedge clk);
            v = 0;
            if (($random & 7) != 0) begin
                // prefer a slot that became eligible exactly now or one cycle ago (forwarding), else any eligible
                s = -1;
                for (i = 0; i < NCH; i = i + 1) if (s < 0 && (t - last_t[i] == LAT || t - last_t[i] == LAT + 1) && ($random & 1)) s = i;
                for (tries = 0; tries < 8 && s < 0; tries = tries + 1) begin i = {$random} % NCH; if (t - last_t[i] >= LAT) s = i; end
                if (s >= 0) begin
                    v = 1; slot = s; first = !open_[s] || (($random & 15) == 0); last = ($random & 3) == 0;
                    term = rterm({$random}); tf = ($random & 63) == 0; tag = $random;
                    open_[s] = !last; last_t[s] = t;
                end
            end
        end
        @(negedge clk); v = 0; repeat (64) @(negedge clk);
        $display("U2 compared=%0d ref=%0d cand=%0d fault=%b/%b same_fwd=%0d cross_fwd=%0d", nc, nr, nu, rfa, ufa, u_u.n_same, u_u.n_cross);
        if (nc != nr || nc < 1000 || rfa || ufa || u_u.n_same == 0 || u_u.n_cross == 0) $fatal(1, "U2 DIFF FINAL");
        $display("U2 PASS");
        $finish;
    end
endmodule
