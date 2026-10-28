`timescale 1ns/1ps
// KV-KITS-9 10-28 (COORD 07:12 condition 2 on the hid2 reset-sample ruling): head bench for the KV head strap leaves.
// Composes one full head the way ot_qkh_head_native_r4 does (4 fronts x 4 stations, 16 lane8, ktree, score4) twice:
//   u_old  = the signed leaves (frontq STRAP_SAMPLE=0 / PORT_REGS=0, lane8 STRAP_DIRECT=0 / S3_COPY=0 / LT_COPY=0);
//   u_new  = the kit leaves (frontq STRAP_SAMPLE=1 / PORT_REGS=1, lane8 STRAP_DIRECT=1, LT_COPY=1, S3_COPY=1 on the
//            even eighths = lanes t with (t/2)%2==0, exactly as kv3_head_eighth_e0/e2/e4/e6 instantiate them).
// Claim under test: hid2 differs from the old copy only while the front reset relay rp is low (hid2[0] + the 4 relay
// hid bits of the RSTFREE probe), and that window is NOT observable at the head outputs after reset release.
// Stimulus: Q beats stream continuously (qv=1) THROUGH reset and from the first edge after release, every hid strap,
// random row/c/lt/e bursts, 4 resets.  Check: {sc_d,sc_f,g_f,nb_d} of u_new === u_old on EVERY edge from time 0
// (in reset, in the window, after), and u_new === reference ot_qwen_nearhbm_head_hs once the reference pipeline is
// settled (100 edges after each release, as tb_qkh_head_native).  KK9_MUT=1 (bench script) delays the hid2 sample by 3
// edges past rp: beats in the window then carry hid 0 -> must FAIL.
module kk9_head #(parameter integer NEW=0, parameter integer MUT=0)
 (input wire clk, rst_n, input wire [3:0] c_in, input wire [1023:0] row_in, input wire [15:0] e_in,
  input wire [11:0] lt_in, input wire [1:0] hid, input wire q_valid_in, input wire [5:0] q_beat_in,
  input wire [511:0] q_data_in, output wire [31:0] sc_d, output wire sc_f, g_f, output wire [1023:0] nb_d);
  wire [232:0] f_t [0:15]; wire [3:0] pack_fault;
  genvar g, t;
  generate for (g = 0; g < 4; g = g + 1) begin : g_front
    ot_qkh_head_frontq_native #(.Q_FP32(1), .MUT(MUT), .PORT_REGS(NEW), .STRAP_SAMPLE(NEW)) u_front
      (.clk(clk), .rst_n(rst_n), .c_in(c_in), .row_in(row_in[256*g +: 256]), .e_in(e_in), .lt_in(lt_in),
       .hid(hid), .q_valid_in(q_valid_in), .q_beat_in(q_beat_in), .q_data_in(q_data_in),
       .f_t0(f_t[4*g]), .f_t1(f_t[4*g+1]), .f_t2(f_t[4*g+2]), .f_t3(f_t[4*g+3]), .pack_fault(pack_fault[g]));
  end endgenerate
  wire [511:0] kp_t, kp_k; wire [15:0] kpv_t, kpv_k, gf_t, gf_k; wire [1023:0] nb_t; wire [15:0] lane_rst_n;
  generate for (t = 0; t < 16; t = t + 1) begin : g_t
    wire [15:0] cr_o; wire [216:0] dr_o; wire [63:0] nb_mid;
    ot_qkh_head_stin_native #(.MUT(MUT)) u_stin (.clk(clk), .rst_n(rst_n), .cr_i(f_t[t][232:217]), .dr_i(f_t[t][216:0]),
       .cr_o(cr_o), .dr_o(dr_o), .lane_rst_n(lane_rst_n[t]));
    ot_qkh_head_stk_native #(.MUT(MUT)) u_stk (.clk(clk), .rst_n(rst_n), .kp_i(kp_t[32*t +: 32]), .kpv_i(kpv_t[t]),
       .gf_i(gf_t[t]), .kp_o(kp_k[32*t +: 32]), .kpv_o(kpv_k[t]), .gf_o(gf_k[t]));
    ot_qkh_head_nb_native #(.MUT(MUT)) u_nb1 (.clk(clk), .nb_i(nb_t[64*t +: 64]), .nb_o(nb_mid));
    ot_qkh_head_nb_native u_nb2 (.clk(clk), .nb_i(nb_mid), .nb_o(nb_d[64*t +: 64]));
    ot_qkh_lane8 #(.STRAP_DIRECT(NEW), .S3_COPY((NEW != 0 && ((t/2) % 2) == 0) ? 1 : 0), .LT_COPY(NEW)) u_l8
      (.clk(clk), .rst_n(lane_rst_n[t]), .c_in({cr_o[15:13], dr_o[216]}), .row_in(dr_o[215:152]), .e_in(dr_o[151:136]),
       .lt_in(cr_o[12:1]), .hid(dr_o[1:0]), .bsel(2'(t/4)), .q_valid_in(cr_o[0]), .q_beat_in(dr_o[135:130]),
       .q_data_in(dr_o[129:2]), .kp(kp_t[32*t +: 32]), .kpv(kpv_t[t]), .nb(nb_t[64*t +: 64]), .gf(gf_t[t]));
  end endgenerate
  wire [31:0] sc_k; wire sf_k, gf_kt, kt_rst_n;
  ot_qkh_ktree u_kt (.clk(clk), .rst_n(kt_rst_n), .kp_in(kp_k), .kpv_in(kpv_k[0]), .gf_in(gf_k), .sc_d(sc_k), .sc_f(sf_k), .g_f(gf_kt));
  ot_qkh_head_score4_native #(.MUT(MUT)) u_score (.clk(clk), .rst_n(rst_n), .sc_i(sc_k), .sf_i(sf_k), .gf_i(gf_kt),
     .pack_fault(pack_fault), .sc_o(sc_d), .sf_o(sc_f), .gf_o(g_f), .kt_rst_n(kt_rst_n));
endmodule

module tb_head_strap_window;
  reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
  reg [3:0] c = 0; reg [1023:0] row = 0; reg [15:0] e = 0; reg [11:0] lt = 0; reg [1:0] hid = 0;
  reg qv = 0; reg [5:0] qb = 0; reg [511:0] qd = 0;
  wire [31:0] rsc, osc, nsc; wire rsf, rgf, osf, ogf, nsf, ngf; wire [1023:0] rnb, onb, nnb;
  ot_qwen_nearhbm_head_hs u_ref (.clk(clk), .rst_n(rst_n), .c_in(c), .row_in(row), .e_in(e), .lt_in(lt), .hid(hid),
    .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .sc_d(rsc), .sc_f(rsf), .g_f(rgf), .nb_d(rnb));
  kk9_head #(.NEW(0)) u_old (.clk(clk), .rst_n(rst_n), .c_in(c), .row_in(row), .e_in(e), .lt_in(lt), .hid(hid),
    .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .sc_d(osc), .sc_f(osf), .g_f(ogf), .nb_d(onb));
  kk9_head #(.NEW(1)) u_new (.clk(clk), .rst_n(rst_n), .c_in(c), .row_in(row), .e_in(e), .lt_in(lt), .hid(hid),
    .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .sc_d(nsc), .sc_f(nsf), .g_f(ngf), .nb_d(nnb));
  integer edges = 0, on_err = 0, ref_err = 0, ref_chk = 0, win_edges = 0, resets = 0, sc_chg = 0, rp_rise = 0;
  integer since_rel = 0; reg ref_on = 0; reg [31:0] last_sc = 0;
  // the old/new hid2 really differ in the window (coverage that the window is exercised, not vacuous)
  wire hid2_diff = u_old.g_front[0].u_front.hid2 !== u_new.g_front[0].u_front.hid2;
  integer hid2_diff_edges = 0;
  always @(posedge clk) begin
    #0.05; edges = edges + 1;
    if (hid2_diff) hid2_diff_edges = hid2_diff_edges + 1;
    if ({osc, osf, ogf, onb} !== {nsc, nsf, ngf, nnb}) begin
      if (on_err < 8) $display("OLD_NEW_MISMATCH edge=%0d rst_n=%b since_rel=%0d sc %h/%h sf %b/%b gf %b/%b nb_eq %b",
                               edges, rst_n, since_rel, osc, nsc, osf, nsf, ogf, ngf, onb === nnb);
      on_err = on_err + 1;
    end
    if (rst_n && since_rel < 24) win_edges = win_edges + 1;
    if (ref_on) begin
      ref_chk = ref_chk + 1;
      if ({rsc, rsf, rgf, rnb} !== {nsc, nsf, ngf, nnb}) begin
        if (ref_err < 8) $display("REF_NEW_MISMATCH edge=%0d sc %h/%h", edges, rsc, nsc);
        ref_err = ref_err + 1;
      end
      if (rsc != last_sc) sc_chg = sc_chg + 1; last_sc = rsc;
    end
    if (rst_n) since_rel = since_rel + 1;
  end
  integer h, r, b, k, j, l, beat = 0;
  task q_beat_rand; begin
    qv = 1; qb = 6'(beat); beat = beat + 1;
    for (l = 0; l < 16; l = l + 1) qd[32*l +: 32] = 32'h3f000000 + 32'($urandom % 32'h00800000) | (($urandom & 1) ? 32'h80000000 : 0);
  end endtask
  task head_reset; begin
    @(negedge clk); rst_n = 0; ref_on = 0; resets = resets + 1;
    // traffic keeps running through reset (random row / c / lt, Q beats) -- worst case for the window
    repeat (6 + ($urandom % 5)) begin @(negedge clk); q_beat_rand(); c = $urandom; lt = $urandom; e = $urandom;
      for (l = 0; l < 32; l = l + 1) row[32*l +: 32] = $urandom; end
    c = 0; lt = 0; beat = 0;
    rst_n = 1; since_rel = 0;
  end endtask
  initial begin
    for (r = 0; r < 4; r = r + 1) begin
      hid = 2'(r ^ 2'b01);             // hid 1,0,3,2: hid != 0 at the first releases (0 would mask the window)
      head_reset();
      // Q rows from the FIRST edge after release: the beats that ride the window (rp still low for the relay stages)
      for (b = 0; b < 64; b = b + 1) begin @(negedge clk); q_beat_rand(); end
      @(negedge clk); qv = 0;
      repeat (100) @(negedge clk);
      ref_on = 1;
      for (k = 0; k < 8; k = k + 1) for (j = 0; j < 80; j = j + 1) begin
        @(negedge clk);
        for (l = 0; l < 128; l = l + 1) row[8*l +: 8] = 8'h28 + 8'((l + k + r + $urandom % 3) % 24);
        e = 16'h3f80 + 16'(k * 13); c = 0; lt = 0;
        if (j < 32 && j % 8 == 0) c = {1'b1, 1'b0, j == 0, 1'(k & 1)};
        if (j >= 32 && j < 64 && j % 8 == 0) c = {1'b0, 1'b1, j == 32, 1'(k & 1)};
        if (j == 48) lt[4] = 1; if (j == 56) lt[0] = 1; if (j == 64) begin lt[5] = 1; lt[7:6] = 0; end
        if (j == 72) lt[8] = 1; if (j >= 76) begin lt[9] = 1; lt[11:10] = 2'(j - 76); end
      end
      @(negedge clk); c = 0; lt = 0;
      repeat (128) @(negedge clk);
    end
    if (resets != 4 || hid2_diff_edges == 0 || win_edges < 4 * 24 || ref_chk < 3000 || sc_chg == 0) begin
      $display("HEAD_STRAP_WINDOW_COVERAGE_FAIL resets=%0d hid2_diff_edges=%0d win_edges=%0d ref_checks=%0d score_changes=%0d",
               resets, hid2_diff_edges, win_edges, ref_chk, sc_chg);
      $fatal(1);
    end
    if (on_err != 0 || ref_err != 0) begin
      $display("FAIL head_strap_window edges=%0d old_new_mismatch=%0d ref_mismatch=%0d hid2_diff_edges=%0d", edges, on_err, ref_err, hid2_diff_edges);
      $fatal(1);
    end
    $display("PASS head_strap_window edges=%0d old_new_mismatch=0 (every edge incl. reset + window) ref_checks=%0d ref_mismatch=0 hid2_diff_edges=%0d window_edges=%0d resets=%0d score_changes=%0d",
             edges, ref_chk, hid2_diff_edges, win_edges, resets, sc_chg);
    $finish;
  end
endmodule
