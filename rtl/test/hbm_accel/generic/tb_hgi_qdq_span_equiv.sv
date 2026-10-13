`timescale 1ns/1ps
// The production records have m=1. Exercise the row/stride product over its full field widths,
// including maximal products and VM-range rejection, and compare every front field at its added latency.
module tb_hgi_qdq_span_equiv;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; reg [682:0] rec = 0;
    ot_hgi_qdq_q #(.SPANPIPE(0)) legacy (.clk(clk), .rst_n(rst_n), .rec(rec),
        .wrq_cr(8'd0), .wrr(2056'd0), .wwq_cr(8'd0), .wwq_done(8'd0), .rg_gnt(1'b0), .wg_gnt(1'b0));
    ot_hgi_qdq_q #(.SPANPIPE(1)) staged (.clk(clk), .rst_n(rst_n), .rec(rec),
        .wrq_cr(8'd0), .wrr(2056'd0), .wwq_cr(8'd0), .wwq_done(8'd0), .rg_gnt(1'b0), .wg_gnt(1'b0));
    reg [334:0] expected [0:5];
    wire [334:0] ref_fields = {legacy.fld2, legacy.fast2, legacy.same2, legacy.aend2, legacy.oend2,
        legacy.ab2, legacy.ob2, legacy.n2, legacy.m2, legacy.ars2, legacy.ors2, legacy.hd2};
    wire [334:0] new_fields = {staged.fld2, staged.fast2, staged.same2, staged.aend2, staged.oend2,
        staged.ab2, staged.ob2, staged.n2, staged.m2, staged.ars2, staged.ors2, staged.hd2};
    integer cycles = 0, checked = 0, k;
    always @(negedge clk) begin
        if (cycles > 20) begin
            if (new_fields !== expected[5]) $fatal(1, "SPAN_EQ mismatch cycle=%0d new=%h expected=%h", cycles, new_fields, expected[5]);
            checked = checked + 1;
        end
        for (k = 5; k > 0; k = k - 1) expected[k] = expected[k-1];
        expected[0] = ref_fields;
        cycles = cycles + 1;
    end
    reg [255:0] a, o; reg [127:0] h; reg [19:0] n, m;
    initial begin
        repeat (8) @(posedge clk); rst_n = 1;
        for (integer i = 0; i < 512; i = i + 1) begin
            @(posedge clk);
            a = 0; o = 0; h = 0; n = 20'($urandom | 32'd1); m = 20'($urandom | 32'd1);
            a[1:0] = 1; o[1:0] = 1; a[47:8] = {$urandom, 8'($urandom)}; o[47:8] = {$urandom, 8'($urandom)};
            a[67:48] = n; o[67:48] = n; a[87:68] = m; o[87:68] = m;
            a[119:88] = $urandom; o[119:88] = $urandom;
            if (i % 8 == 0) begin a[87:68] = 20'hfffff; o[87:68] = 20'hfffff; a[119:88] = 32'hffffffff; o[119:88] = 32'hffffffff; end
            if (i % 8 == 1) begin a[87:68] = 1; o[87:68] = 1; end
            if (i % 8 == 2) begin a[47:8] = 0; o[47:8] = 40'd262143; a[119:88] = 0; o[119:88] = 0; end
            h[127:124] = 4; h[123:118] = 4; h[99:93] = 7'b0010001;
            // No dispatch: the continuously clocked span stages are exercised without launching memory traffic.
            rec = {21'(n), 21'(n), o, a, h, 1'b0};
        end
        repeat (15) @(posedge clk);
        $display("PASS HGI_QDQ_SPAN_EQ checked=%0d latency_added=6", checked); $finish;
    end
endmodule
