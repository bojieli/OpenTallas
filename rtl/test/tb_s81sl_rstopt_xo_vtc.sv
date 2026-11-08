`timescale 1ns/1ps
// S81-TYPES-7-LEC J3: lock-step bench of ot_s81sl_rstopt_xo (new: train capture enables also 1 in reset) against the
// previous revision (renamed ot_s81sl_rstopt_xo_old).  Random line / V / fragment / NX / ci traffic with frequent ci XB
// trains (vt_go), three warm resets, zero power-up.  ci beats are held off in reset and for 4 edges after rst_n release
// (no transaction is defined across the release edge).  Every output compared on every edge from 4 edges after release.
// Prints RESULT ... errors N.
// Run (verilator 5.032): verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --x-initial 0 --x-assign 0
//   --top-module tb_s81sl_rstopt_xo_vtc tb.sv <old renamed _old> ot_s81sl_rstopt_xo.sv rtl/lib/ot_rst_relay.sv.  1108: new 0 errors
//   (59,872 checks, 5,618 trains); mutants vtc always 1 / vtc on sp / vph slot 2 from slot 0: 9,623 / 9,623 / 10,068 errors.
module tb_s81sl_rstopt_xo_vtc;
  localparam integer W = 1104, V = 276;
  reg clk = 0, rst_n = 0;
  reg [3:0] sid; reg [W-1:0] ri_w, ri_e, ci_b; reg [V-1:0] vi; reg [4:0] xf_v, xf_s; reg [5*V-1:0] xf;
  reg [172:0] nx_eo, nx_wo; reg [2:0] ci_dir;
  wire [W-1:0] roe_a, row_a, roe_b, row_b, dle_a, dlw_a, dle_b, dlw_b; wire [V-1:0] vo_a, vo_b, dlv_a, dlv_b;
  wire [172:0] nwi_a, nei_a, nwi_b, nei_b; wire [2:0] gv_a, gf_a, gv_b, gf_b; wire [20:0] gi_a, gi_b;
  wire [3071:0] gd_a, gd_b; wire dev_a, dwv_a, dvv_a, f_a, dev_b, dwv_b, dvv_b, f_b;
  ot_s81sl_rstopt_xo_old A (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(roe_a), .ro_w(row_a),
    .vi(vi), .vo(vo_a), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(nwi_a), .nx_ei(nei_a), .nx_eo(nx_eo), .nx_wo(nx_wo),
    .g_v(gv_a), .g_fam(gf_a), .g_idx(gi_a), .g_d(gd_a), .dl_ev(dev_a), .dl_e(dle_a), .dl_wv(dwv_a), .dl_w(dlw_a),
    .dl_vv(dvv_a), .dl_vb(dlv_a), .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_a));
  ot_s81sl_rstopt_xo B (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(roe_b), .ro_w(row_b),
    .vi(vi), .vo(vo_b), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(nwi_b), .nx_ei(nei_b), .nx_eo(nx_eo), .nx_wo(nx_wo),
    .g_v(gv_b), .g_fam(gf_b), .g_idx(gi_b), .g_d(gd_b), .dl_ev(dev_b), .dl_e(dle_b), .dl_wv(dwv_b), .dl_w(dlw_b),
    .dl_vv(dvv_b), .dl_vb(dlv_b), .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_b));
  integer cyc = 0, since = 0, nchk = 0, err = 0, ntrain = 0, nvo = 0, j;
  always #1 clk = ~clk;
  function automatic [W-1:0] rw(); integer q; begin for (q = 0; q < W; q = q + 32) rw[q +: 32] = $urandom; end endfunction
  initial begin
    sid = 4'd5; ri_w = 0; ri_e = 0; ci_b = 0; vi = 0; xf_v = 0; xf_s = 0; xf = 0; nx_eo = 0; nx_wo = 0; ci_dir = 0;
    repeat (60000) begin
      @(negedge clk);
      cyc = cyc + 1;
      rst_n = !((cyc < 40) || (cyc >= 15000 && cyc < 15040) || (cyc >= 37000 && cyc < 37040));
      since = rst_n ? since + 1 : 0;
      ri_w = rw(); ri_e = rw(); vi = rw(); xf = {rw(), rw()}; nx_eo = rw(); nx_wo = rw();
      if ($urandom % 2) ri_w[0] = 0; if ($urandom % 2) ri_e[0] = 0; if ($urandom % 2) vi[0] = 0;
      xf_v = ($urandom % 4 == 0) ? $urandom : 5'd0; xf_s = $urandom;
      if ($urandom % 2) nx_eo[172] = 0; if ($urandom % 2) nx_wo[172] = 0;
      ci_b = rw(); ci_dir = $urandom;
      if ($urandom % 2) ci_b[3:1] = 3'd2;                      // K_XB: trains when ci_dir[2]
      if (!rst_n || since < 4 || ($urandom % 3) == 0) ci_b[0] = 0;
      @(posedge clk); #0.1;
      if (A.vt_go) ntrain = ntrain + 1;
      if (vo_a[0]) nvo = nvo + 1;
      if (since >= 4) begin
        nchk = nchk + 1;
        if (roe_a !== roe_b || row_a !== row_b || vo_a !== vo_b || nwi_a !== nwi_b || nei_a !== nei_b || gv_a !== gv_b ||
            gf_a !== gf_b || gi_a !== gi_b || gd_a !== gd_b || dev_a !== dev_b || dle_a !== dle_b || dwv_a !== dwv_b ||
            dlw_a !== dlw_b || dvv_a !== dvv_b || dlv_a !== dlv_b || f_a !== f_b) begin
          err = err + 1; if (err < 5) $display("MISMATCH cyc %0d since %0d vo %0d", cyc, since, vo_a !== vo_b);
        end
      end
    end
    $display("RESULT checks %0d trains %0d vo_valid %0d errors %0d", nchk, ntrain, nvo, err);
    $finish;
  end
endmodule
