`timescale 1ns/1ps
module tb;
  reg clk = 0; always #0.5 clk = ~clk;
  integer seed = 11, edges = 0, mism = 0, hq = 0, nk = 0, nfi = 0, nfo = 0, nles = 0;
  reg [779:0] i_next = 0;
  reg [0:0] hrst_n = 0;
  reg [127:0] i_grp = 0;
  reg [1:0] pc__cfg_stack = 0;
  reg [287:0] pc__hes = 0;
  reg [260:0] pc__land_er = 0;
  reg [4:0] pc__pc = 0;
  reg [288:0] pc__pi = 0;
  reg [0:0] rst_n = 0;
  reg [298:0] i_prev = 0;
  reg [0:0] pc__fi = 0;
  reg [32:0] pc__ki = 0;
  reg [0:0] x__est__0_1 = 0;
  wire [327:0] pc__po_o, pc__po_n;
  wire [304:0] o_grp_o, o_grp_n;
  wire [0:0] pc__hcompletion_v_o, pc__hcompletion_v_n;
  wire [0:0] pc__hcompletion_we_o, pc__hcompletion_we_n;
  wire [260:0] pc__her_o, pc__her_n;
  wire [287:0] pc__land_es_o, pc__land_es_n;
  wire [298:0] o_next_o, o_next_n;
  wire [779:0] o_prev_o, o_prev_n;
  wire [0:0] pc__fo_o, pc__fo_n;
  wire [32:0] pc__ko_o, pc__ko_n;
  reg fi_d = 0; always @(posedge clk) fi_d <= pc__fi[0];
  qkd_kvs_pc_o u_o (.i_next(i_next), .hrst_n(hrst_n), .i_grp(i_grp), .pc__cfg_stack(pc__cfg_stack), .pc__hes(pc__hes), .pc__land_er(pc__land_er), .pc__pc(pc__pc), .pc__pi(pc__pi), .rst_n(rst_n), .i_prev(i_prev), .pc__ki(pc__ki), .x__est__0_1(x__est__0_1),   .pc__fi(fi_d), .ck(clk), .hck(clk), .pc__front_hbm_data({4{clk}}), .pc__return_hbm_data({4{clk}}), .pc__po(pc__po_o), .o_grp(o_grp_o), .pc__hcompletion_v(pc__hcompletion_v_o), .pc__hcompletion_we(pc__hcompletion_we_o), .pc__her(pc__her_o), .pc__land_es(pc__land_es_o), .o_next(o_next_o), .o_prev(o_prev_o), .pc__fo(pc__fo_o), .pc__ko(pc__ko_o));
  qkd_kvs_pc u_n (.i_next(i_next[779:0]), .pc__po(pc__po_n), .ck(clk), .hrst_n(hrst_n[0:0]), .i_grp(i_grp[127:0]), .o_grp(o_grp_n), .pc__cfg_stack(pc__cfg_stack[1:0]), .pc__hcompletion_v(pc__hcompletion_v_n), .pc__hcompletion_we(pc__hcompletion_we_n), .pc__her(pc__her_n), .pc__hes(pc__hes[287:0]), .pc__land_er(pc__land_er[0:0]), .pc__land_er_259(pc__land_er[260:259]), .pc__land_es(pc__land_es_n), .pc__pc(pc__pc[4:0]), .pc__pi(pc__pi[288:0]), .rst_n(rst_n[0:0]), .i_prev(i_prev[298:0]), .o_next(o_next_n), .o_prev(o_prev_n), .pc__fi(pc__fi[0:0]), .pc__fo(pc__fo_n), .pc__ki(pc__ki[32:0]), .pc__ko(pc__ko_n), .x__est__0_1(x__est__0_1[0:0]));
  wire [9999:0] vo = {pc__po_o, o_grp_o, pc__hcompletion_v_o, pc__hcompletion_we_o, pc__her_o, pc__land_es_o, o_next_o, o_prev_o, pc__fo_o};
  wire [9999:0] vn = {pc__po_n, o_grp_n, pc__hcompletion_v_n, pc__hcompletion_we_n, pc__her_n, pc__land_es_n, o_next_n, o_prev_n, pc__fo_n};
  reg [32:0] ko_ref = 0; always @(posedge clk) ko_ref <= pc__ko_o;
  always @(posedge clk) hq <= hrst_n[0] ? (hq > 0 ? hq - 1 : 0) : 4;
  always @(negedge clk) if (rst_n[0] && hrst_n[0] && hq == 0) begin edges = edges + 1;
    if (vo !== vn) begin mism = mism + 1; if (mism < 8) begin
      if (pc__po_o !== pc__po_n) $display("MISMATCH edge=%0d pc__po", edges);
      if (o_grp_o !== o_grp_n) $display("MISMATCH edge=%0d o_grp", edges);
      if (pc__hcompletion_v_o !== pc__hcompletion_v_n) $display("MISMATCH edge=%0d pc__hcompletion_v", edges);
      if (pc__hcompletion_we_o !== pc__hcompletion_we_n) $display("MISMATCH edge=%0d pc__hcompletion_we", edges);
      if (pc__her_o !== pc__her_n) $display("MISMATCH edge=%0d pc__her", edges);
      if (pc__land_es_o !== pc__land_es_n) $display("MISMATCH edge=%0d pc__land_es", edges);
      if (o_next_o !== o_next_n) $display("MISMATCH edge=%0d o_next", edges);
      if (o_prev_o !== o_prev_n) $display("MISMATCH edge=%0d o_prev", edges);
      if (pc__fo_o !== pc__fo_n) $display("MISMATCH edge=%0d pc__fo", edges);
    end end
    if (pc__ko_n !== ko_ref) begin mism = mism + 1; if (mism < 8) $display("MISMATCH edge=%0d ko", edges); end
    nk = nk + (pc__ko_n[0] ? 1 : 0); nfi = nfi + pc__fi[0];
    nfo = nfo + pc__fo_o[0];
    nles = nles + pc__land_es_o[0];
  end
  integer c = 0, r; reg [31:0] rr;
  initial begin rst_n = 0; hrst_n = 0; pc__cfg_stack = 2'd1; pc__pc = 5'd5; end
  always @(negedge clk) begin
    c = c + 1;
    rst_n[0] = !(c < 8 || (c % 2000 >= 1999 || c % 2000 < 5)); hrst_n[0] = rst_n[0];
    r = $random(seed); for (integer w = 0; w < 25; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; i_next[w*32 +: 32] = rr; end
    r = $random(seed); for (integer w = 0; w < 4; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; i_grp[w*32 +: 32] = rr; end
    r = $random(seed); for (integer w = 0; w < 9; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; pc__hes[w*32 +: 32] = rr; end
    r = $random(seed); for (integer w = 0; w < 9; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; pc__land_er[w*32 +: 32] = rr; end
    r = $random(seed); for (integer w = 0; w < 10; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; pc__pi[w*32 +: 32] = rr; end
    r = $random(seed); for (integer w = 0; w < 10; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; i_prev[w*32 +: 32] = rr; end
    pc__fi[0] = ((c % 2000) >= 10 && (c % 2000) < 14) || (c >= 3000 && ($random(seed) & 255) == 0);
    r = $random(seed); for (integer w = 0; w < 2; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; pc__ki[w*32 +: 32] = rr; end
    r = $random(seed); x__est__0_1 = ((r & 15) == 0) ? 1'($random(seed)) : 0;
    if (c % 700 == 0) $display("DBG c=%0d fo=%b les0=%b ki0=%b", c, pc__fo_o[0], pc__land_es_o[0], pc__ki[0]);
  end
  initial begin
    #6008;
    $display("KVSPC MITER %s mismatches=%0d edges=%0d ko_v=%0d fi=%0d fo_edges=%0d land_es_v=%0d", (mism == 0 && edges > 1000) ? "PASS" : "FAIL", mism, edges, nk, nfi, nfo, nles);
    $finish; end
endmodule
