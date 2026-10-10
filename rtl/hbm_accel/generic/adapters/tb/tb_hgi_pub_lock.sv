`timescale 1ns/1ps
module tb_pub_lock;  // hgi-adapters: the restructured SM publication (ot_hgi_sm_pub) checked against the expected O words; ot_hgi_sm_pub_old = git show 962d7d8d1:rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv (renamed) rides along: random MATVEC results from 32 SMs, VM images compared
    localparam integer NSM = 32;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer seed = 11, errors = 0;
    reg pub_v = 0; reg [39:0] pb = 0; reg [31:0] pst = 0; reg [19:0] pm = 0; reg [12:0] pq = 0; reg [3:0] pp = 0;
    reg [NSM-1:0] rv = 0; reg [NSM*12-1:0] rr = 0; reg [NSM*256-1:0] rd = 0;
    wire ra, rb, da, db, fa, fb; wire [4*338-1:0] qa, qb; wire [4*274-1:0] xa, xb; wire [273:0] ta, tb2; reg [337:0] tq = 0;
    ot_hgi_sm_pub_old ua (.clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(ra), .pub_base(pb), .pub_stride(pst),
        .pub_space(2'd1), .pub_m(pm), .pub_q(pq), .pub_p(pp), .pub_done(da), .pub_fault(fa), .sm_rv(rv), .sm_rrow(rr),
        .sm_rdata(rd), .vmq(qa), .vmr(xa), .s0_v(), .s0_idx(), .s0_data());
    ot_hgi_sm_pub ub (.clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(rb), .pub_base(pb), .pub_stride(pst),
        .pub_space(2'd1), .pub_m(pm), .pub_q(pq), .pub_p(pp), .pub_done(db), .pub_fault(fb), .sm_rv(rv), .sm_rrow(rr),
        .sm_rdata(rd), .vmq(qb), .vmr(xb), .s0_v(), .s0_idx(), .s0_data());
    ot_hgi_vm_unit #(.NC(5)) va (.clk(clk), .rst_n(rst_n), .cq({tq, qa}), .cr({ta, xa}), .status());
    ot_hgi_vm_unit #(.NC(5)) vb (.clk(clk), .rst_n(rst_n), .cq({tq, qb}), .cr({tb2, xb}), .status());
    reg [337:0] tq2 = 0;
    task automatic rd2(input [31:0] word, output [31:0] a, output [31:0] b);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, 1'b0, word[29:3], 5'd0, 256'd0, 32'd0, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!(ta[273] && tb2[273]) && tw < 100) begin @(negedge clk); tw = tw + 1; end
            a = ta[32 * word[2:0] +: 32]; b = tb2[32 * word[2:0] +: 32];
        end
    endtask
    reg [31:0] expv [int];
    integer c, s, i, nda, ndb, t, sr [0:NSM-1], rows, left, w; reg [31:0] va2, vb2;
    always @(posedge clk) begin if (da) nda = nda + 1; if (db) ndb = ndb + 1; end
    initial begin
        repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (c = 0; c < 8; c = c + 1) begin
            pp = 1 + ($unsigned($random(seed)) % 8); pm = 1 + ($unsigned($random(seed)) % 400); pq = (pm + NSM - 1) / NSM;
            pb = 100 * c + ($unsigned($random(seed)) % 50); pst = pm + ($unsigned($random(seed)) % 20); nda = 0; ndb = 0;
            @(negedge clk); pub_v = 1; @(negedge clk); pub_v = 0;
            for (s = 0; s < NSM; s = s + 1) sr[s] = 0;
            left = pm;
            while (left > 0) begin
                @(negedge clk); rv = 0;
                for (s = 0; s < NSM; s = s + 1) begin
                    rows = (pm > s * pq) ? ((pm - s * pq > pq) ? pq : pm - s * pq) : 0;
                    if (sr[s] < rows && ($unsigned($random(seed)) % 48) == 0) begin
                        rv[s] = 1; rr[s*12 +: 12] = sr[s]; for (i = 0; i < 8; i = i + 1) begin rd[s*256 + 32*i +: 32] = $random(seed);
                            if (i < pp) expv[pb + i * pst + s * pq + sr[s]] = rd[s*256 + 32*i +: 32]; end
                        sr[s] = sr[s] + 1; left = left - 1;
                    end
                end
            end
            @(negedge clk); rv = 0;
            t = 0; while ((nda == 0 || ndb == 0) && t < 100000) begin @(posedge clk); t = t + 1; end
            if (fb || ndb != 1) begin $display("ERR cmd %0d done %0d %0d fault %b %b", c, nda, ndb, fa, fb); errors = errors + 1; end
            for (w = pb; w < pb + pp * pst + 8; w = w + 1) begin
                rd2(w, va2, vb2);
                if (expv.exists(w) && vb2 !== expv[w]) begin if (errors < 6) $display("ERR cmd %0d VM[%0d] %h expected %h (old %h)", c, w, vb2, expv[w], va2); errors = errors + 1; end
            end
            $display("cmd %0d P %0d M %0d checked", c, pp, pm);
        end
        if (errors == 0) $display("PUB_LOCK PASS"); else $display("PUB_LOCK FAIL %0d", errors);
        $finish;
    end
endmodule
