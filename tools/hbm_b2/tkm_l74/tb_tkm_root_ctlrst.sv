// Old (no-reset extract, X/random power-up) vs __ctlrst (reset form): all outputs
// must be identical on every cycle after the first reset release, on random
// stimulus with random mid-run resets. Old core module renamed OLD_*.
`timescale 1ns/1ps
module tb_tkm_root_ctlrst;
  parameter int CYCLES = 200000;
  parameter int SEED = 1;
  parameter int RSTP = 20000;  // mean cycles between random mid-run resets
  reg clk = 0, rst_n = 0, start = 0, arg_mode = 0, cfg_has_r = 0;
  reg [343:0] u_up_0; reg [11:0] cfg_n; reg [12:0] cfg_k, cfg_nout; reg [7:0] cfg_g, cfg_gbase;
  reg [15:0] cfg_pf; reg [39:0] cfg_obase, cfg_rbase; reg [3:0] del_valid, del_slot; reg [2115:0] del_flit;
  wire [39:0] a_w_addr, b_w_addr; wire [343:0] a_eq, b_eq; wire [31:0] a_sc, b_sc;
  wire [511:0] a_wd, b_wd; wire [15:0] a_wm, b_wm;
  wire a_busy, b_busy, a_evq, b_evq, a_cq, b_cq, a_clr, b_clr, a_f, b_f, a_d, b_d, a_wv, b_wv;
`define PORTS(P) .u_up_0(u_up_0), .clk(clk), .rst_n(rst_n), .start(start), .cfg_n(cfg_n), .cfg_k(cfg_k), \
   .cfg_g(cfg_g), .cfg_gbase(cfg_gbase), .cfg_pf(cfg_pf), .cfg_nout(cfg_nout), .cfg_obase(cfg_obase), \
   .cfg_rbase(cfg_rbase), .cfg_has_r(cfg_has_r), .del_valid(del_valid), .del_flit(del_flit), .buffer_clk(clk), \
   .del_slot(del_slot), .arg_mode(arg_mode), .w_addr(P``_w_addr), .u_entry_q(P``_eq), .stat_cycles(P``_sc), \
   .w_data(P``_wd), .w_mask(P``_wm), .busy(P``_busy), .u_entry_vq(P``_evq), .u_conv_q(P``_cq), .u_clr_q(P``_clr), \
   .fault(P``_f), .done(P``_d), .w_v(P``_wv)
  OLD_tkm_tp192_root_core            u_old (`PORTS(a));
  ot_hgi_coll_tkm_tp192_root_core    u_new (`PORTS(b));
  wire [1500:0] oa = {a_w_addr, a_eq, a_sc, a_wd, a_wm, a_busy, a_evq, a_cq, a_clr, a_f, a_d, a_wv};
  wire [1500:0] ob = {b_w_addr, b_eq, b_sc, b_wd, b_wm, b_busy, b_evq, b_cq, b_clr, b_f, b_d, b_wv};
  always #1 clk = ~clk;
  integer cyc = 0, seen = 0, nmis = 0, ndone = 0, nwv = 0, nstart = 0, nfault = 0, nbusy = 0, nrst = 0, nraw = 0;
  integer s, seedv, dvp = 100, stp = 40;
  function automatic [31:0] r32(); r32 = $urandom; endfunction
  task automatic rnd_cfg();
    // small shapes mostly (so jobs finish), sometimes wide random
    if (($urandom % 4) != 0) begin
      cfg_n = $urandom % 64; cfg_k = $urandom % 16; cfg_nout = $urandom % 16; cfg_g = $urandom % 8;
      cfg_gbase = $urandom % 8; cfg_pf = $urandom % 32;
    end else begin
      cfg_n = r32(); cfg_k = r32(); cfg_nout = r32(); cfg_g = r32(); cfg_gbase = r32(); cfg_pf = r32();
    end
    cfg_obase = {r32(), r32()}; cfg_rbase = {r32(), r32()}; cfg_has_r = $urandom; arg_mode = $urandom;
  endtask
  initial begin
    seedv = SEED; void'($value$plusargs("seed=%d", seedv)); s = $urandom(seedv);
    void'($value$plusargs("dvp=%d", dvp)); void'($value$plusargs("stp=%d", stp));
    for (int i = 0; i < 344; i += 32) u_up_0[i +: 32] = r32();
    for (int i = 0; i < 2116; i += 32) del_flit[i +: 32] = r32();
    del_valid = 0; del_slot = 0; rnd_cfg();
  end
  always @(negedge clk) begin
    cyc <= cyc + 1;
    if (cyc == 5) rst_n <= 1;
    else if (cyc > 5 && ($urandom % RSTP) == 0) begin rst_n <= 0; nrst <= nrst + 1; end
    else if (!rst_n && cyc > 5 && ($urandom % 4) == 0) rst_n <= 1;
    start <= (($urandom % stp) == 0);
    if (($urandom % 8) == 0) rnd_cfg();
    del_valid <= (($urandom % 100) < dvp) ? $urandom : 4'd0; del_slot <= $urandom;
    for (int i = 0; i < 2116; i += 32) del_flit[i +: 32] <= r32();
    for (int i = 0; i < 344; i += 32) u_up_0[i +: 32] <= r32();
  end
  always @(posedge clk) begin
    if (rst_n) seen <= 1;
    if (seen) begin
      // control outputs + stat every cycle; payload only where its valid qualifies it
      // (w_addr/w_data/w_mask under w_v, u_entry_q under u_entry_vq); raw payload diffs counted apart
      if ({a_busy, a_evq, a_cq, a_clr, a_f, a_d, a_wv, a_sc} !== {b_busy, b_evq, b_cq, b_clr, b_f, b_d, b_wv, b_sc}
          || (a_wv && {a_w_addr, a_wd, a_wm} !== {b_w_addr, b_wd, b_wm}) || (a_evq && a_eq !== b_eq)) begin
        nmis <= nmis + 1;
        if (nmis < 10) $display("MISMATCH cyc %0d ctl a=%b b=%b sc %h/%h wv %b addr %h/%h evq %b eqdiff %0d",
          cyc, {a_busy, a_evq, a_cq, a_clr, a_f, a_d, a_wv}, {b_busy, b_evq, b_cq, b_clr, b_f, b_d, b_wv}, a_sc, b_sc,
          a_wv, a_w_addr, b_w_addr, a_evq, $countones(a_eq ^ b_eq));
      end
      if (oa !== ob) nraw <= nraw + 1;
      ndone <= ndone + b_d; nwv <= nwv + b_wv; nstart <= nstart + start; nfault <= nfault + b_f; nbusy <= nbusy + b_busy;
    end
    if (cyc % 5000 == 0) $display("progress cyc %0d mism %0d done %0d wv %0d", cyc, nmis, ndone, nwv);
    if (cyc == CYCLES) begin
      $display("SUMMARY seed=%0d cycles=%0d mismatches=%0d raw_unqualified_payload_diff_cycles=%0d resets=%0d start=%0d busy_cyc=%0d done_cyc=%0d wv_cyc=%0d fault_cyc=%0d",
               seedv, cyc, nmis, nraw, nrst, nstart, nbusy, ndone, nwv, nfault);
      if (nmis != 0) $fatal(1, "FAIL"); else $display("PASS");
      $finish;
    end
  end
endmodule
