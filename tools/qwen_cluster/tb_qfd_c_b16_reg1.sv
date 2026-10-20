`timescale 1ns/1ps
// Region bench of the CB16 representative landed region c1r1 (rtl/physical/qcluster/qfd_c_b16_reg1.sv, two tops):
//   qfd_c_b16_reg1  (leg-a alignment = same-clock hard landing ring pair, K2)  vs
//   qfd_c_b16_reg1b (leg-a alignment = three stn514 relays).
// (a) EQUIVALENCE: both tops on the same 5 region clocks (one period, per-root phase offsets) and the same random
//     input words; every output bus (bco, lt_o, ly_o, lf_o) must be cycle-exact, bit-exact equal, AND equal to an
//     untimed reference built from the plan.json priced path latencies (-G L_*), so both cannot be wrong together.
// (b) RESET EPOCHS: every region root reset is released on calendar edge R; own leaves are inside the DUT (RDL 6),
//     neighbour leaves are modelled here as the neighbour's pin + 5 stages (RDL 6).  Bound probes check that every
//     landing slice (writer and reader of all 8 crossings + the reg1 ring pair, both halves, both tops) leaves reset
//     on the SAME edge EXP_REL and that each reader's first valid word is read at EXP_REL+K from the slot written at
//     EXP_REL (sel 0001; vld 0011, or 0111 when the writer root's edge EXP_REL+K precedes the reader's).
// Driven by tools/qwen_cluster/bench_reg1.sh (MUT selects tb-side mutants; source mutants are sed copies there).
package reg1_tb_pkg;
  parameter int R = 24;              // first calendar edge at which every region root reset input is sampled high
  parameter int RDL = 6;             // parent reset-leaf depth contract (pin register + 5 kept stages)
  parameter int K = 2;               // landing read epoch (D4/K2 contract)
  parameter int EXP_REL = R + RDL + 2;   // landing halves add rst_l0 + r2: first edge a slice acts out of reset
  parameter int EXP_SLICES = 374;        // (36 reg1 + 32 reg1b landing halves) / 2 sides * 11 slices of <=24 bits
  int n_w = 0, n_r = 0, n_rf = 0, ep_err = 0;
endpackage

module ep_probe_w (input wire ck, input wire r2, input wire [3:0] sel, input wire [3:0] vld);
  import reg1_tb_pkg::*;
  int n = 0;
  bit done = 0;
  always @(posedge ck) begin
    if (!done && r2) begin
      done = 1;
      n_w++;
      if (n != EXP_REL || sel != 4'b0001 || vld != 4'b0000) begin
        ep_err++;
        if (ep_err < 60) $display("REG1_EPOCH_FAIL side=w edge=%0d exp=%0d sel=%b vld=%b %m", n, EXP_REL, sel, vld);
      end else if (is_s0($sformatf("%m"))) $display("REG1_EPOCH side=w edge=%0d %m", n);
    end
    n++;
  end
  function automatic bit is_s0(string s);
    for (int i = 0; i + 10 <= s.len(); i++) if (s.substr(i, i + 9) == "g_slice[0]") return 1;
    return 0;
  endfunction
endmodule

module ep_probe_r (input wire ck, input wire r2, input wire warm, input wire [3:0] sel, input wire [3:0] vld);
  import reg1_tb_pkg::*;
  int n = 0;
  bit done = 0, fdone = 0;
  always @(posedge ck) begin
    if (!done && r2) begin
      done = 1;
      n_r++;
      if (n != EXP_REL || sel != (4'b0001 << ((4 - K) % 4))) begin
        ep_err++;
        if (ep_err < 60) $display("REG1_EPOCH_FAIL side=r edge=%0d exp=%0d sel=%b %m", n, EXP_REL, sel);
      end else if (is_s0($sformatf("%m"))) $display("REG1_EPOCH side=r edge=%0d %m", n);
    end
    if (!fdone && warm) begin
      fdone = 1;
      n_rf++;
      if (n != EXP_REL + K || sel != 4'b0001 || !(vld inside {4'b0011, 4'b0111})) begin
        ep_err++;
        if (ep_err < 60)
          $display("REG1_EPOCH_FAIL side=first_word edge=%0d exp=%0d sel=%b vld=%b %m", n, EXP_REL + K, sel, vld);
      end else if (is_s0($sformatf("%m"))) $display("REG1_FIRST_WORD edge=%0d slot_vld=%b %m", n, vld);
    end
    n++;
  end
  function automatic bit is_s0(string s);
    for (int i = 0; i + 10 <= s.len(); i++) if (s.substr(i, i + 9) == "g_slice[0]") return 1;
    return 0;
  endfunction
endmodule

bind qfd_c_land_safe_w_slice ep_probe_w u_ep (.ck(ck), .r2(r2), .sel(sel), .vld(vld_q));
bind qfd_c_land_safe_r_slice ep_probe_r u_ep (.ck(ck), .r2(r2), .warm(warm), .sel(sel), .vld(vld));

module tb_clk #(parameter real PH = 0.0, parameter real T = 1.0) (output reg ck);
  initial begin
    ck = 0;
    #(T + PH);
    forever begin ck = 1; #(T / 2); ck = 0; #(T / 2); end
  end
endmodule

module tb;
  import reg1_tb_pkg::*;
  import a0_model_pkg::*;
  parameter int MUT = 0;      // tb-side: 3 = neighbour leaf lrst_leg_3_0a_4_r released one edge late
  parameter int PHS = 0;      // 0: neighbour phases within the ~80 ps landing contract; 1: wide (+-0.45 T) stress
  parameter int NCYC = 24000;
  parameter int L_BC = 0, L_TAP = 0, L_NA = 0, L_NB = 0, L_TO = 0, L_NY = 0, L_LF = 0;
  localparam int HN = R + RDL + NCYC + 64;
  localparam real T = 1.0;
  localparam [11:0] CID = 12'hA5C;
  localparam [15:0] TID = {CID, 4'b0011};   // {cid, tl, tl, th, th}

  // roots: c1r1 (own), c1r0, c1r2, c0r1, c2r1
  wire ck_c1r1, ck_c1r0, ck_c1r2, ck_c0r1, ck_c2r1;
  tb_clk #(.PH(0.0), .T(T))                   g0 (ck_c1r1);
  tb_clk #(.PH(PHS ? 0.40 : 0.07), .T(T))     g1 (ck_c1r0);
  tb_clk #(.PH(PHS ? -0.35 : -0.08), .T(T))   g2 (ck_c1r2);
  tb_clk #(.PH(PHS ? 0.25 : 0.05), .T(T))     g3 (ck_c0r1);
  tb_clk #(.PH(PHS ? -0.45 : -0.06), .T(T))   g4 (ck_c2r1);

  // per-root calendar edge counters (edge index of the NEXT posedge)
  int c11 = 0, c10 = 0, c12 = 0, c01 = 0, c21 = 0;
  always @(posedge ck_c1r1) c11++;
  always @(posedge ck_c1r0) c10++;
  always @(posedge ck_c1r2) c12++;
  always @(posedge ck_c0r1) c01++;
  always @(posedge ck_c2r1) c21++;

  // root resets (each driven in its own root, first sampled high on edge R) and neighbour reset leaves (RDL 6)
  reg rst11 = 0, rst10 = 0, rst12 = 0, rst01 = 0, rst21 = 0;
  always @(negedge ck_c1r1) rst11 <= (c11 >= R);
  always @(negedge ck_c1r0) rst10 <= (c10 >= R);
  always @(negedge ck_c1r2) rst12 <= (c12 >= R);
  always @(negedge ck_c0r1) rst01 <= (c01 >= R);
  always @(negedge ck_c2r1) rst21 <= (c21 >= R);
  reg [RDL-1:0] lr10 = 0, lr12 = 0, lr01 = 0;
  reg [RDL:0] lr21 = 0;
  always @(posedge ck_c1r0) lr10 <= {lr10[RDL-2:0], rst10};
  always @(posedge ck_c1r2) lr12 <= {lr12[RDL-2:0], rst12};
  always @(posedge ck_c0r1) lr01 <= {lr01[RDL-2:0], rst01};
  always @(posedge ck_c2r1) lr21 <= {lr21[RDL-1:0], rst21};
  wire leaf10 = lr10[RDL-1], leaf12 = lr12[RDL-1], leaf01 = lr01[RDL-1];
  wire leaf21 = (MUT == 3) ? lr21[RDL] : lr21[RDL-1];   // M3: one neighbour leaf one edge late

  // stimulus: each input bus is driven in its writer's root, word for edge n stored in h_*[n]
  reg [515:0] bc = 0;
  reg [513:0] la = 0, lb = 0, lf = 0;
  logic [515:0] h_bc [0:HN-1];
  logic [513:0] h_la [0:HN-1], h_lb [0:HN-1], h_lf [0:HN-1];
  initial begin
    for (int i = 0; i < HN; i++) begin h_bc[i] = 0; h_la[i] = 0; h_lb[i] = 0; h_lf[i] = 0; end
  end
  function automatic logic [515:0] rnd516();
    logic [515:0] v;
    for (int i = 0; i < 17; i++) v[i*32 +: 32] = $urandom;
    v[515:512] = $urandom;
    return v;
  endfunction
  always @(negedge ck_c1r0) if (c10 < HN) begin
    logic [515:0] w;
    logic [515:0] v;
    w = rnd516(); v = rnd516();
    bc <= w; h_bc[c10] = w; la <= v[513:0]; h_la[c10] = v[513:0];
  end
  always @(negedge ck_c0r1) if (c01 < HN) begin
    logic [515:0] w;
    w = rnd516(); lb <= w[513:0]; h_lb[c01] = w[513:0];
  end
  always @(negedge ck_c1r2) if (c12 < HN) begin
    logic [515:0] w;
    w = rnd516(); lf <= w[513:0]; h_lf[c12] = w[513:0];
  end

  wire [515:0] bco1, bco2;
  wire [513:0] lt1, lt2, ly1, ly2, lfo1, lfo2;
  qfd_c_b16_reg1 u1 (.bc(bc), .bco(bco1), .la_i(la), .lb_i(lb), .lt_o(lt1), .ly_o(ly1), .lf_i(lf), .lf_o(lfo1),
      .lrst_dn1_rly3_w(leaf10), .lrst_dn1_rly6_r(leaf12), .lrst_leg_2_0a_3_w(leaf10), .lrst_leg_2_0b_y_w(leaf01),
      .lrst_leg_1_1b_y_r(leaf01), .lrst_leg_3_0a_4_r(leaf21), .lrst_leg_4_0b_1_w(leaf12), .lrst_leg_4_0b_5_r(leaf10),
      .ck_c1r1(ck_c1r1), .ck_c1r0(ck_c1r0), .ck_c1r2(ck_c1r2), .ck_c0r1(ck_c0r1), .ck_c2r1(ck_c2r1),
      .rst_c1r1(rst11), .far(1'b0), .cid(CID));
  qfd_c_b16_reg1b u2 (.bc(bc), .bco(bco2), .la_i(la), .lb_i(lb), .lt_o(lt2), .ly_o(ly2), .lf_i(lf), .lf_o(lfo2),
      .lrst_dn1_rly3_w(leaf10), .lrst_dn1_rly6_r(leaf12), .lrst_leg_2_0a_3_w(leaf10), .lrst_leg_2_0b_y_w(leaf01),
      .lrst_leg_1_1b_y_r(leaf01), .lrst_leg_3_0a_4_r(leaf21), .lrst_leg_4_0b_1_w(leaf12), .lrst_leg_4_0b_5_r(leaf10),
      .ck_c1r1(ck_c1r1), .ck_c1r0(ck_c1r0), .ck_c1r2(ck_c1r2), .ck_c0r1(ck_c0r1), .ck_c2r1(ck_c2r1),
      .rst_c1r1(rst11), .far(1'b0), .cid(CID));

  // untimed reference: A0 output registered on edge m, and each bus at the edge q its last register updates
  function automatic logic [513:0] a0_t(int m);
    return f_t(h_la[m - L_NA], h_lb[m - L_NB], h_bc[m - L_TAP][507:0]);
  endfunction
  function automatic logic [513:0] a0_y(int m);
    return f_y(h_la[m - L_NA], h_lb[m - L_NB], h_bc[m - L_TAP][379:0], TID);
  endfunction
  localparam int A0_FULL = EXP_REL + ((L_NA > L_NB ? L_NA : L_NB) > L_TAP ? (L_NA > L_NB ? L_NA : L_NB) : L_TAP);
  localparam logic [513:0] LT_MASK = ~({6'b0, 128'hffffffff_ffffffff_ffffffff_ffffffff, 380'b0});

  int eq_err = 0, ref_err = 0, eq_chk = 0, ref_chk = 0;
  int eqn[4] = '{0, 0, 0, 0};
  task automatic eq(int k, string nm, int q, logic [515:0] a, logic [515:0] b);
    eq_chk++;
    if (a !== b) begin
      eq_err++; eqn[k]++;
      if (eqn[k] <= 3) begin
        int bit0 = -1;
        for (int i = 0; i < 516; i++) if (bit0 < 0 && a[i] !== b[i]) bit0 = i;
        $display("REG1_EQ_MISMATCH out=%s edge=%0d first_bit=%0d reg1=%h reg1b=%h", nm, q, bit0, a[63:0], b[63:0]);
      end
    end
  endtask
  task automatic rf(string nm, int q, logic [515:0] got, logic [515:0] exp, logic [515:0] mask, string top);
    ref_chk++;
    if ((got & mask) !== (exp & mask)) begin
      ref_err++;
      if (ref_err <= 8) $display("REG1_REF_MISMATCH out=%s top=%s edge=%0d got=%h exp=%h", nm, top, q, got[63:0], exp[63:0]);
    end
  endtask
  // compare at each output root's negedge after its edge q = counter - 1
  always @(negedge ck_c1r2) begin : chk_bco
    int q; q = c12 - 1;
    if (q >= R && q < HN) begin
      eq(0, "bco", q, bco1, bco2);
      rf("bco", q, bco1, (q - (L_BC - 1) >= EXP_REL) ? h_bc[q - (L_BC - 1)] : 516'b0, {516{1'b1}}, "reg1");
      rf("bco", q, bco2, (q - (L_BC - 1) >= EXP_REL) ? h_bc[q - (L_BC - 1)] : 516'b0, {516{1'b1}}, "reg1b");
    end
  end
  always @(negedge ck_c1r0) begin : chk_lf
    int q; q = c10 - 1;
    if (q >= R && q < HN) begin
      eq(1, "lf_o", q, {2'b0, lfo1}, {2'b0, lfo2});
      rf("lf_o", q, {2'b0, lfo1}, (q - (L_LF - 1) >= EXP_REL) ? {2'b0, h_lf[q - (L_LF - 1)]} : 516'b0, {516{1'b1}}, "reg1");
      rf("lf_o", q, {2'b0, lfo2}, (q - (L_LF - 1) >= EXP_REL) ? {2'b0, h_lf[q - (L_LF - 1)]} : 516'b0, {516{1'b1}}, "reg1b");
    end
  end
  always @(negedge ck_c0r1) begin : chk_lt
    int q; q = c01 - 1;
    if (q >= R && q < HN) begin
      eq(2, "lt_o", q, {2'b0, lt1}, {2'b0, lt2});
      if (q - L_TO >= A0_FULL) begin
        rf("lt_o", q, {2'b0, lt1}, {2'b0, a0_t(q - L_TO)}, {2'b0, LT_MASK}, "reg1");
        rf("lt_o", q, {2'b0, lt2}, {2'b0, a0_t(q - L_TO)}, {2'b0, LT_MASK}, "reg1b");
      end
    end
  end
  always @(negedge ck_c2r1) begin : chk_ly
    int q; q = c21 - 1;
    if (q >= R && q < HN) begin
      eq(3, "ly_o", q, {2'b0, ly1}, {2'b0, ly2});
      if (q - L_NY >= A0_FULL) begin
        rf("ly_o", q, {2'b0, ly1}, {2'b0, a0_y(q - L_NY)}, {516{1'b1}}, "reg1");
        rf("ly_o", q, {2'b0, ly2}, {2'b0, a0_y(q - L_NY)}, {516{1'b1}}, "reg1b");
      end
    end
  end

  initial begin
    if (L_BC == 0 || L_NA == 0 || L_NY == 0 || L_LF == 0) $fatal(1, "REG1_FAIL no plan latencies (-G L_*)");
    $display("REG1_CFG MUT=%0d PHS=%0d R=%0d RDL=%0d EXP_REL=%0d K=%0d NCYC=%0d L_BC=%0d L_TAP=%0d L_NA=%0d L_NB=%0d L_TO=%0d L_NY=%0d L_LF=%0d",
             MUT, PHS, R, RDL, EXP_REL, K, NCYC, L_BC, L_TAP, L_NA, L_NB, L_TO, L_NY, L_LF);
    wait (c11 >= R + RDL + NCYC + 32);
    #(T / 4);
    if (n_w != EXP_SLICES || n_r != EXP_SLICES || n_rf != EXP_SLICES) begin
      ep_err++;
      $display("REG1_EPOCH_FAIL count w=%0d r=%0d first_word=%0d exp=%0d", n_w, n_r, n_rf, EXP_SLICES);
    end
    $display("REG1_SUMMARY MUT%0d PHS=%0d eq_checks=%0d eq_err=%0d (bco %0d lf_o %0d lt_o %0d ly_o %0d) ref_checks=%0d ref_err=%0d epoch_slices w=%0d r=%0d first_word=%0d epoch_err=%0d",
             MUT, PHS, eq_chk, eq_err, eqn[0], eqn[1], eqn[2], eqn[3], ref_chk, ref_err, n_w, n_r, n_rf, ep_err);
    if (eq_err || ref_err || ep_err) $fatal(1, "REG1_FAIL MUT%0d eq_err=%0d ref_err=%0d epoch_err=%0d", MUT, eq_err, ref_err, ep_err);
    $display("REG1_PASS MUT%0d PHS=%0d", MUT, PHS);
    $finish;
  end
endmodule
