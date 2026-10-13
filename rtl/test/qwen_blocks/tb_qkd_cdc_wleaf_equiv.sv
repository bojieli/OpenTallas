`timescale 1ns/1ps
// q13-cdcw 2026-10-13: the hardened die cell qkd_cdc_wleaf (rtl/hdc/kv/qkd_cdc_wleaf.sv: ot_qwen_stream4_cdc_pc at
// the routed parameters MARGIN 1 / LCRED 6 / SYNC 2 / RSEL 1 / RNG 10) against the independently configured
// ot_qwen_stream4_cdc_pc MARGIN 2 reference (tb_stream4_cdc_m2_equiv's stimulus: random traffic on both clocks,
// unrelated periods, stimulus after both domains released): every output of both domains must match on every edge.
// r2: the cell has LD 32 (reference 64: the stimulus holds the controller's credit rule, at most CRED = 32 landing
// words outstanding, counted exactly as the controller does: -1 a push, + h_cred) and WPIPE 1 (h_wcon pin flop: the
// reference sees h_wcon one HCLK edge later; h_hand is same-edge in both).
// NEG = 1: the reference uses SYNC 3 (a different crossing) -> must FAIL.
// NEG = 2: the reference sees h_wcon undelayed (the cell's pin stage is not transparent) -> must FAIL.
// NEG = 3: the stimulus ignores the credit rule with a slow reader (LD 32 overflows where LD 64 does not) -> must FAIL.
module tb_qkd_cdc_wleaf_equiv;
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
        .h_cred(OH[2:0]), .h_wv(OH[3]), .h_wsec(OH[27:4]), .h_hand(h_hand), .h_wcon(NEG == 2 ? h_wcon : h_wcon_d), .h_cv(OH[28]), \
        .h_csec(OH[52:29]), .h_cdata(OH[308:53]), .h_ctag(OH[317:309]), .h_av(h_av), .h_atag(h_atag), .h_fault(OH[318]));
    reg h_wcon_d = 0; always @(posedge hclk) h_wcon_d <= h_wcon;
    integer cred = 32, maxout = 0; reg lvn;
    qkd_cdc_wleaf u_a (
        .clk(clk), .c_arst_n(rst_n), .l_v(oc_a[0]), .l_sec(oc_a[17:1]), .l_row(oc_a[25:18]), .l_data(oc_a[281:26]), .l_pop(l_pop),
        .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(oc_a[282]), .wd_v(oc_a[283]), .wd_tag(oc_a[292:284]),
        .c_fault(oc_a[293]), .hclk(hclk), .h_arst_n(rst_n), .h_lv(h_lv), .h_lsec(h_lsec), .h_lrow(h_lrow), .h_ldata(h_ldata),
        .h_cred(oh_a[2:0]), .h_wv(oh_a[3]), .h_wsec(oh_a[27:4]), .h_hand(h_hand), .h_wcon(h_wcon), .h_cv(oh_a[28]),
        .h_csec(oh_a[52:29]), .h_cdata(oh_a[308:53]), .h_ctag(oh_a[317:309]), .h_av(h_av), .h_atag(h_atag), .h_fault(oh_a[318]));
    `CDC_INST(u_b, 2, (NEG ? 3 : 2), oc_b, oh_b)
    assign oc_a[600:294] = 0; assign oc_b[600:294] = 0; assign oh_a[600:319] = 0; assign oh_b[600:319] = 0;
    integer seed = 11, bad = 0, nc = 0, nh = 0, lv_seen = 0, wd_seen = 0, cv_seen = 0, k;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 11; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
    reg go = 0;
    always @(negedge clk) if (go) begin
        if (oc_a !== oc_b) bad = bad + 1;
        nc = nc + 1; lv_seen = lv_seen + oc_a[0]; wd_seen = wd_seen + oc_a[283];
    end
    always @(negedge hclk) if (go) begin if (oh_a !== oh_b) bad = bad + 1; nh = nh + 1; cv_seen = cv_seen + oh_a[28]; end
    always @(posedge clk) if (go) begin
        l_pop <= (NEG == 3) ? (($random(seed) & 63) == 0) : (($random(seed) & 3) == 0); w_v <= ($random(seed) & 3) == 1;
        w_sec <= $random(seed); w_tag <= $random(seed);
        for (k = 0; k < 256; k = k + 32) w_data[k +: 32] <= $random(seed);
    end
    always @(posedge hclk) if (go) begin
        lvn = (($random(seed) & 1) == 0) && (cred > 0 || NEG == 3);
        h_lv <= lvn; cred = cred - lvn + oh_a[2:0]; if (32 - cred > maxout) maxout = 32 - cred;
        h_hand <= ($random(seed) & 7) == 0; h_wcon <= ($random(seed) & 7) == 1;
        h_av <= ($random(seed) & 7) == 2; h_lsec <= $random(seed); h_lrow <= $random(seed); h_atag <= $random(seed);
        for (k = 0; k < 256; k = k + 32) h_ldata[k +: 32] <= $random(seed);
    end
    initial begin
        repeat (5) @(posedge clk); rst_n = 1; repeat (12) @(posedge clk); go = 1;
        repeat (N) @(posedge clk);
        if (bad == 0 && lv_seen > 100 && wd_seen > 50 && maxout >= 30 && cv_seen > 50) $display("PASS qkd_cdc_wleaf clk_checks=%0d hclk_checks=%0d landings=%0d wdone=%0d completions=%0d max_outstanding=%0d", nc, nh, lv_seen, wd_seen, cv_seen, maxout);
        else begin $display("FAIL qkd_cdc_wleaf NEG=%0d: %0d mismatching edges (landings %0d wdone %0d completions %0d max_outstanding %0d h_fault %b)", NEG, bad, lv_seen, wd_seen, cv_seen, maxout, oh_a[318]); $fatal(1); end
        $finish;
    end
endmodule
