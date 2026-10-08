`timescale 1ns/1ps
// qwen-blocks 2026-10-07: ot_qwen_stream4_cdc_pc MARGIN 2 (kept reset-release pre-stage per tree) against MARGIN 1,
// same random stimulus on both clocks (unrelated periods), stimulus starting after both have released: every output
// of both domains must match on every edge.  NEG = 1: the reference uses SYNC 3 (a different crossing) -> must FAIL.
module tb_stream4_cdc_m2_equiv;
    parameter integer NEG = 0, N = 20000;
    reg clk = 0, hclk = 0, rst_n = 0;
    always #1.0 clk = ~clk;
    always #1.17 hclk = ~hclk;
    reg l_pop = 0, w_v = 0, h_lv = 0, h_hand = 0, h_wcon = 0, h_av = 0;
    reg [23:0] w_sec = 0; reg [255:0] w_data = 0, h_ldata = 0; reg [8:0] w_tag = 0, h_atag = 0;
    reg [16:0] h_lsec = 0; reg [7:0] h_lrow = 0;
    wire [600:0] oc_a, oc_b; wire [600:0] oh_a, oh_b;
`define CDC_INST(NM, MG, SY, OC, OH) \
    ot_qwen_stream4_cdc_pc #(.MARGIN(MG), .LCRED(6), .SYNC(SY), .RSEL(1), .RNG(10)) NM ( \
        .clk(clk), .c_arst_n(rst_n), .l_v(OC[0]), .l_sec(OC[17:1]), .l_row(OC[25:18]), .l_data(OC[281:26]), .l_pop(l_pop), \
        .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(OC[282]), .wd_v(OC[283]), .wd_tag(OC[292:284]), \
        .c_fault(OC[293]), .hclk(hclk), .h_arst_n(rst_n), .h_lv(h_lv), .h_lsec(h_lsec), .h_lrow(h_lrow), .h_ldata(h_ldata), \
        .h_cred(OH[2:0]), .h_wv(OH[3]), .h_wsec(OH[27:4]), .h_hand(h_hand), .h_wcon(h_wcon), .h_cv(OH[28]), \
        .h_csec(OH[52:29]), .h_cdata(OH[308:53]), .h_ctag(OH[317:309]), .h_av(h_av), .h_atag(h_atag), .h_fault(OH[318]));
    `CDC_INST(u_a, 2, 2, oc_a, oh_a)
    `CDC_INST(u_b, 1, (NEG ? 3 : 2), oc_b, oh_b)
    assign oc_a[600:294] = 0; assign oc_b[600:294] = 0; assign oh_a[600:319] = 0; assign oh_b[600:319] = 0;
    integer seed = 11, bad = 0, nc = 0, nh = 0, lv_seen = 0, wd_seen = 0, k;
    reg go = 0;
    always @(negedge clk) if (go) begin
        if (oc_a !== oc_b) bad = bad + 1;
        nc = nc + 1; lv_seen = lv_seen + oc_a[0]; wd_seen = wd_seen + oc_a[283];
    end
    always @(negedge hclk) if (go) begin if (oh_a !== oh_b) bad = bad + 1; nh = nh + 1; end
    always @(posedge clk) if (go) begin
        l_pop <= ($random(seed) & 3) == 0; w_v <= ($random(seed) & 3) == 1;
        w_sec <= $random(seed); w_tag <= $random(seed);
        for (k = 0; k < 256; k = k + 32) w_data[k +: 32] <= $random(seed);
    end
    always @(posedge hclk) if (go) begin
        h_lv <= ($random(seed) & 3) == 0; h_hand <= ($random(seed) & 7) == 0; h_wcon <= ($random(seed) & 7) == 1;
        h_av <= ($random(seed) & 7) == 2; h_lsec <= $random(seed); h_lrow <= $random(seed); h_atag <= $random(seed);
        for (k = 0; k < 256; k = k + 32) h_ldata[k +: 32] <= $random(seed);
    end
    initial begin
        repeat (5) @(posedge clk); rst_n = 1; repeat (12) @(posedge clk); go = 1;
        repeat (N) @(posedge clk);
        if (bad == 0 && lv_seen > 100 && wd_seen > 50) $display("PASS cdc_m2 clk_checks=%0d hclk_checks=%0d landings=%0d wdone=%0d", nc, nh, lv_seen, wd_seen);
        else $display("FAIL cdc_m2 NEG=%0d: %0d mismatching edges (landings %0d wdone %0d)", NEG, bad, lv_seen, wd_seen);
        $finish;
    end
endmodule
