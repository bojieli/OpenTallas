`timescale 1ns/1ps
// KV-CORES 10-25 ECTLK face-port miter: original core (qkd_ectlk_o) vs transformed core, all outputs every edge, on the
// static K stimulus of rtl/test/qwen_static_kv/tb_qkd_ectl3_kiss_st.sv (4 contexts, K responses from a fixed-latency
// row model at the core's RESPONSE_LAT 12) with random q words / exp_done / e words / head score returns.
module tb;
  parameter integer RL = 12;
  reg clk = 0; always #0.5 clk = ~clk;
  reg rst_n = 0; reg [632:0] si = 0; wire [4:0] cfg = 5'(3*4+1); reg [5:0] layer_cur = 0;
  reg rsp_valid = 0; reg [1023:0] rsp_data = 0; reg [13:0] rsp_t = 0; reg rsp_v = 0; reg [15:0] rsp_epoch = 0; reg [5:0] rsp_layer = 0;
  reg [33:0] s0 = 0, s1 = 0, s2 = 0, s3 = 0;
  wire [412:0] so_o, so_n; wire [1558:0] t0_o, t0_n, t1_o, t1_n; wire [15:0] e0_o,e0_n,e1_o,e1_n,e2_o,e2_n,e3_o,e3_n;
  wire f_o, f_n; wire [15:0] re_o, re_n; wire [5:0] rl_o, rl_n; wire [13:0] rt_o, rt_n; wire rv_o, rv_n, rq_o, rq_n;
`define P(sfx, Aso, At0, At1, Ae0, Ae1, Ae2, Ae3, Af, Are, Arl, Art, Arv, Arq) \
  qkd_ectlk``sfx u``sfx (.rsp_epoch(rsp_epoch), .rsp_layer(rsp_layer), .rsp_t(rsp_t), .rsp_v(rsp_v), .rsp_valid(rsp_valid), \
    .s0(s0), .s1(s1), .s2(s2), .s3(s3), .so(Aso), .t0(At0), .t1(At1), .ck({clk,clk,clk}), .e0(Ae0), .e1(Ae1), .e2(Ae2), .e3(Ae3), \
    .rst_n(rst_n), .si(si), .cfg(cfg), .epoch(16'h1234), .fault(Af), .kgo(si[0]), .layer(layer_cur), .req_epoch(Are), .req_layer(Arl), \
    .req_t(Art), .req_v(Arv), .req_valid(Arq), .rsp_data(rsp_data));
  `P(_o, so_o, t0_o, t1_o, e0_o, e1_o, e2_o, e3_o, f_o, re_o, rl_o, rt_o, rv_o, rq_o)
  `P(, so_n, t0_n, t1_n, e0_n, e1_n, e2_n, e3_n, f_n, re_n, rl_n, rt_n, rv_n, rq_n)
  wire [5000:0] vo = {so_o, t0_o, t1_o, e0_o, e1_o, e2_o, e3_o, f_o, re_o, rl_o, rt_o, rv_o, rq_o};
  wire [5000:0] vn = {so_n, t0_n, t1_n, e0_n, e1_n, e2_n, e3_n, f_n, re_n, rl_n, rt_n, rv_n, rq_n};
  function automatic [1023:0] rowf(input integer n);
    for (integer j = 0; j < 32; j = j + 1) rowf[j*32 +: 32] = 32'h42000000 ^ (n*32'h10203) ^ j;
  endfunction
  reg [1023:0] response[0:1023]; reg rv[0:1023]; reg [13:0] tags[0:1023];
  integer cyc, nbridge, mism = 0, edges = 0, kreq = 0, scv = 0, lmc = 0, fl = 0, sof = 0, seed = 5, ci; reg [255:0] lm_prev = 0;
  always @(negedge clk) if (rst_n) begin
    edges = edges + 1;
    if (vo !== vn) begin mism = mism + 1; if (mism < 6) $display("MISMATCH edge=%0d so=%0d t=%0d f=%0d req=%0d", edges, so_o !== so_n,
        {t0_o,t1_o} !== {t0_n,t1_n}, f_o !== f_n, {re_o,rl_o,rt_o,rv_o,rq_o} !== {re_n,rl_n,rt_n,rv_n,rq_n}); end
    scv = scv + so_o[13]; fl = fl + f_o; sof = sof + so_o[412];
    if (so_o[281:154] !== lm_prev[127:0]) lmc = lmc + 1; lm_prev[127:0] = so_o[281:154];
  end
  initial begin
    repeat (6) @(negedge clk); rst_n = 1;
    repeat (80) @(negedge clk);
    for (ci = 0; ci < 4; ci = ci + 1) begin
      for (integer layer_idx = 0; layer_idx < ((ci == 0) ? 8 : 3); layer_idx = layer_idx + 1) begin
        integer ctx; ctx = (ci == 0) ? 8192 : ((ci == 1) ? 1000 : ((ci == 2) ? 300 : 5000));
        layer_cur = 6'(layer_idx + ci); nbridge = 0;
        for (integer j = 0; j < 1024; j = j + 1) begin rv[j] = 0; response[j] = 0; tags[j] = 0; end
        for (cyc = 0; cyc < 500; cyc = cyc + 1) begin
          si = 0; si[14:1] = 14'(ctx); si[17:15] = cyc % 8;
          if (cyc == 0) si[0] = 1;
          if (cyc >= 1 && cyc <= 32) begin si[18] = 1; si[24:19] = cyc - 1; end
          for (integer w = 0; w < 16; w = w + 1) si[25+32*w +: 32] = $random(seed);
          si[537 +: 32] = $random(seed); si[569 +: 32] = $random(seed); si[601 +: 32] = $random(seed);
          s0 = {$random(seed)} % (1 << 30); s1 = $random(seed); s2 = $random(seed); s3 = {2'b00, 32'($random(seed))};
          rsp_valid = rv[cyc]; rsp_data = response[cyc]; rsp_t = tags[cyc]; rsp_epoch = 16'h1234; rsp_layer = layer_cur; rsp_v = 0;
          @(posedge clk);
          if (rq_o) begin rv[cyc+RL] = 1; response[cyc+RL] = rowf(nbridge) ^ {32{32'($random(seed))}}; tags[cyc+RL] = rt_o;
            nbridge = nbridge + 1; kreq = kreq + 1; end
          @(negedge clk);
        end
      end
    end
    $display("ECTLK MITER %s mismatches=%0d edges=%0d kreq=%0d sc_valid=%0d lmax_changes=%0d fault_edges=%0d so_fault_edges=%0d",
             (mism == 0 && kreq > 0 && scv > 0 && lmc > 0) ? "PASS" : "FAIL", mism, edges, kreq, scv, lmc, fl, sof);
    $finish;
  end
endmodule
