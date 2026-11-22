// S81-VPW-XRB equivalence bench: ot_s81sl_vpw XR=1 SLR=1, XRB 0 vs XRB 1, random writers, every output every cycle.
`timescale 1ns/1ps
module tb_vpw_xrb;
    reg clk = 0, rst_n = 0;
    reg sw_v; reg [9:0] sw_a; reg [7:0] sw_m; reg [255:0] sw_d;
    reg [1:0] cw_v; reg [23:0] cw_a; reg [63:0] cw_d;
    reg x_wv; reg [9:0] x_wa; reg [7:0] x_wm; reg [255:0] xwd;
    reg hs_v; reg [9:0] hs_a; reg [255:0] hs_d;
    wire [1:0] wv0, wv1; wire [8:0] a00, a01, a10, a11; wire [127:0] d00, d01, d10, d11, m00, m01, m10, m11; wire c0, c1;
    ot_s81sl_vpw #(.XR(1), .SLR(1), .XRB(0)) u0 (.clk(clk), .rst_n(rst_n), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .xwd(xwd), .hs_v(hs_v), .hs_a(hs_a),
        .hs_d(hs_d), .wv(wv0), .wa0(a00), .wa1(a01), .wd0(d00), .wd1(d01), .wm0(m00), .wm1(m01), .wcol(c0));
    ot_s81sl_vpw #(.XR(1), .SLR(1), .XRB(1)) u1 (.clk(clk), .rst_n(rst_n), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .xwd(xwd), .hs_v(hs_v), .hs_a(hs_a),
        .hs_d(hs_d), .wv(wv1), .wa0(a10), .wa1(a11), .wd0(d10), .wd1(d11), .wm0(m10), .wm1(m11), .wcol(c1));
    always #1 clk = ~clk;
    integer i, bad = 0, checked = 0, active = 0;
    task rnd; begin
        sw_v = $random; sw_a = $random; sw_m = $random; sw_d = {8{$random}};
        cw_v = $random; cw_a = $random; cw_d = {$random, $random};
        x_wv = $random; x_wa = $random; x_wm = $random; xwd = {8{$random}};
        hs_v = ($random % 4) == 0; hs_a = $random; hs_d = {8{$random}};
    end endtask
    initial begin
        rnd; #5 rst_n = 1;
        for (i = 0; i < 20000; i = i + 1) begin
            @(negedge clk);
            if (i > 3) begin
                checked = checked + 1;
                if (wv0 !== wv1 || a00 !== a10 || a01 !== a11 || d00 !== d10 || d01 !== d11 || m00 !== m10 || m01 !== m11 || c0 !== c1) begin
                    bad = bad + 1;
                    if (bad < 5) $display("MISMATCH cycle %0d wv %b/%b wd0 %h/%h", i, wv0, wv1, d00, d10);
                end
                if (|wv0) active = active + 1;
            end
            rnd;
        end
        $display("XRB_EQ checked %0d cycles, %0d with a write, mismatches %0d", checked, active, bad);
        if (bad == 0 && active > 1000) $display("XRB_EQ PASS"); else $display("XRB_EQ FAIL");
        $finish;
    end
endmodule
