`timescale 1ns/1ps
module tb_xload_lock;  // hgi-adapters: banked x-load vs the pre-restructure x-load (ot_hgi_sm_xload_old = git show 6fbdd1c:...), 10 random commands, every x-store write identical
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; integer seed = 3, errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg x_v = 0; reg [39:0] x_base = 0; reg [20:0] x_n = 0; reg [3:0] x_p = 0; reg [31:0] x_stride = 0;
    wire rdy_a, rdy_b, done_a, done_b, f_a, f_b, en_a, en_b; wire [6:0] ad_a, ad_b, gr_a, gr_b; wire [2047:0] d_a, d_b;
    wire [4*338-1:0] qa, qb; wire [4*274-1:0] ra, rb; wire [273:0] tra, trb; reg [337:0] tq = 0;
    ot_hgi_sm_xload_old ua (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(rdy_a), .x_base(x_base), .x_n(x_n), .x_p(x_p),
        .x_stride(x_stride), .x_space(2'd1), .x_fmt(2'd0), .x_done(done_a), .x_fault(f_a), .xw_en(en_a), .xw_addr(ad_a),
        .xw_grp(gr_a), .xw_data(d_a), .vmq(qa), .vmr(ra));
    ot_hgi_sm_xload ub (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(rdy_b), .x_base(x_base), .x_n(x_n), .x_p(x_p),
        .x_stride(x_stride), .x_space(2'd1), .x_fmt(2'd0), .x_done(done_b), .x_fault(f_b), .xw_en(en_b), .xw_addr(ad_b),
        .xw_grp(gr_b), .xw_data(d_b), .vmq(qb), .vmr(rb));
    ot_hgi_vm_unit #(.NC(5)) va (.clk(clk), .rst_n(rst_n), .cq({tq, qa}), .cr({tra, ra}), .status());
    ot_hgi_vm_unit #(.NC(5)) vb (.clk(clk), .rst_n(rst_n), .cq({tq, qb}), .cr({trb, rb}), .status());
    reg [2047:0] ma [0:16383]; reg [2047:0] mb [0:16383]; reg [16383:0] wa, wb;
    always @(posedge clk) begin
        if (en_a) begin ma[{ad_a, gr_a}] <= d_a; wa[{ad_a, gr_a}] <= 1'b1; end
        if (en_b) begin mb[{ad_b, gr_b}] <= d_b; wb[{ad_b, gr_b}] <= 1'b1; end
    end
    task automatic vm_w(input [31:0] word, input [31:0] data);
        begin
            @(negedge clk); tq = {1'b1, 1'b1, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0; repeat (6) @(negedge clk);
        end
    endtask
    integer c, i, k, nda, ndb, t;
    always @(posedge clk) begin if (done_a) nda = nda + 1; if (done_b) ndb = ndb + 1; end
    initial begin
        repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (i = 0; i < 2600; i = i + 1) vm_w(i, $random(seed));
        for (c = 0; c < 10; c = c + 1) begin
            wa = 0; wb = 0; nda = 0; ndb = 0;
            x_p = 1 + ($unsigned($random(seed)) % 8); x_n = 1 + ($unsigned($random(seed)) % 1500);
            x_base = 8 * ($unsigned($random(seed)) % 20); x_stride = 8 * (((x_n + 7) / 8) + ($unsigned($random(seed)) % 3));
            @(negedge clk); x_v = 1; @(negedge clk); x_v = 0;
            t = 0; while ((nda == 0 || ndb == 0) && t < 200000) begin @(posedge clk); t = t + 1; end
            repeat (4) @(posedge clk);
            for (k = 0; k < 16384; k = k + 1) if (wa[k] || wb[k]) if (wa[k] !== wb[k] || ma[k] !== mb[k]) begin
                if (errors < 5) $display("ERR cmd %0d P %0d K %0d write %0d differs (%b %b)", c, x_p, x_n, k, wa[k], wb[k]);
                errors = errors + 1; end
            $display("cmd %0d P %0d K %0d done %0d/%0d", c, x_p, x_n, nda, ndb);
        end
        if (errors == 0) $display("XLOAD_LOCK PASS"); else $display("XLOAD_LOCK FAIL %0d", errors);
        $finish;
    end
endmodule
