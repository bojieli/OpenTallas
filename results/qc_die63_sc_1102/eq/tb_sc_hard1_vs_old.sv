// DIE-QC-63/SC 11-02: lock-step simulation of the old d90 SC leaf (qfd_dv_s5_sc2_leaf, no HARD_PINREG, renamed *_old)
// against the event source qfd_dv_s5_sc2_leaf #(.HARD_PINREG(1)).  Same random stimulus every cycle, reset pulses,
// every output compared with 4-state === each cycle after the first CMP_FROM cycles.  Pipeline delay: the event adds
// no architectural cycle (capture sharing only), so the compare offset is 0 (DELAY parameter, checked).
`timescale 1ns/1ps
module tb;
  parameter integer CYCLES = 3000, CMP_FROM = 4, SEED = 1;
  integer DELAY;  // compare offset (cycles the new source lags the old); +DELAY=1 is the negative control
  reg ck = 0, rst_n = 0;
  reg [100:0] sc_cfg; reg [47:0] dn_i, up_i; reg red_we; reg [23:0] red_addr; reg [31:0] red_data;
  reg [7:0] vm_we; reg [1:0] vm_win0; reg [31:0] vm_wdata0; reg am_v; reg [23:0] am_idx; reg [31:0] am_val; reg [1:0] am_u;
  wire [47:0] dn_o_a, up_o_a, dn_o_b, up_o_b;
  wire w1_we_a, w1_we_b, tok_v_a, tok_v_b, tok_own_a, tok_own_b, busy_a, busy_b, fault_a, fault_b;
  wire [23:0] w1_addr_a, w1_addr_b, tok_idx_a, tok_idx_b; wire [31:0] w1_data_a, w1_data_b, tok_val_a, tok_val_b;
  wire [1:0] tok_user_a, tok_user_b;
  qfd_dv_s5_sc2_leaf_old A (.ck(ck), .rst_n(rst_n), .sc_cfg(sc_cfg), .dn_i(dn_i), .dn_o(dn_o_a), .up_i(up_i), .up_o(up_o_a),
    .red_we(red_we), .red_addr(red_addr), .red_data(red_data), .vm_we(vm_we), .vm_win0(vm_win0), .vm_wdata0(vm_wdata0),
    .am_v(am_v), .am_idx(am_idx), .am_val(am_val), .am_u(am_u), .w1_we(w1_we_a), .w1_addr(w1_addr_a), .w1_data(w1_data_a),
    .tok_v(tok_v_a), .tok_idx(tok_idx_a), .tok_own(tok_own_a), .tok_val(tok_val_a), .tok_user(tok_user_a), .busy(busy_a), .fault(fault_a));
  qfd_dv_s5_sc2_leaf #(.HARD_PINREG(1)) B (.ck(ck), .rst_n(rst_n), .sc_cfg(sc_cfg), .dn_i(dn_i), .dn_o(dn_o_b), .up_i(up_i), .up_o(up_o_b),
    .red_we(red_we), .red_addr(red_addr), .red_data(red_data), .vm_we(vm_we), .vm_win0(vm_win0), .vm_wdata0(vm_wdata0),
    .am_v(am_v), .am_idx(am_idx), .am_val(am_val), .am_u(am_u), .w1_we(w1_we_b), .w1_addr(w1_addr_b), .w1_data(w1_data_b),
    .tok_v(tok_v_b), .tok_idx(tok_idx_b), .tok_own(tok_own_b), .tok_val(tok_val_b), .tok_user(tok_user_b), .busy(busy_b), .fault(fault_b));
  wire [340:0] oa = {dn_o_a, up_o_a, w1_we_a, w1_addr_a, w1_data_a, tok_v_a, tok_idx_a, tok_own_a, tok_val_a, tok_user_a, busy_a, fault_a};
  wire [340:0] ob = {dn_o_b, up_o_b, w1_we_b, w1_addr_b, w1_data_b, tok_v_b, tok_idx_b, tok_own_b, tok_val_b, tok_user_b, busy_b, fault_b};
  reg [340:0] hist [0:15];
  integer cyc, mism, cmp, xa, s, k, toggles; reg [340:0] prev;
  function [31:0] r32; input integer dummy; r32 = $random(s); endfunction
  task drive; begin
    // mostly sparse valid traffic + a fixed-ish config (changes rarely), so the datapath actually runs
    if (cyc % 500 == 0) sc_cfg = {r32(0), r32(0), r32(0), r32(0)};
    dn_i = {r32(0), r32(0)}; up_i = {r32(0), r32(0)};
    red_we = (r32(0) % 4) == 0; red_addr = r32(0); red_data = r32(0);
    vm_we = (r32(0) % 3 == 0) ? r32(0) : 8'h0; vm_win0 = r32(0); vm_wdata0 = r32(0);
    am_v = (r32(0) % 2) == 0; am_idx = r32(0); am_val = r32(0); am_u = r32(0);
  end endtask
  always #0.5 ck = ~ck;
  initial begin
    s = SEED; if ($value$plusargs("SEED=%d", k)) s = k; DELAY = 0; if ($value$plusargs("DELAY=%d", toggles)) DELAY = toggles; mism = 0; cmp = 0; xa = 0; toggles = 0; prev = 0;
    for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
      @(negedge ck);
      rst_n = !((cyc < 3) || (cyc % 1000 >= 700 && cyc % 1000 < 703));
      drive;
      @(posedge ck); #0.1;
      hist[cyc % 16] = oa;
      if (cyc >= CMP_FROM + DELAY) begin
        cmp = cmp + 1;
        if (^ob === 1'bx || ^oa === 1'bx) xa = xa + 1;
        if (ob !== hist[(cyc - DELAY) % 16]) begin
          mism = mism + 1;
          if (mism <= 10) $display("MISMATCH cyc %0d rst_n %b\n  old %h\n  new %h", cyc, rst_n, hist[(cyc - DELAY) % 16], ob);
        end
        if (oa !== prev) toggles = toggles + 1;
      end
      prev = oa;
    end
    $display("SC_EQ_SIM seed %0d cycles %0d compared %0d mismatches %0d cycles_with_X %0d output_changes %0d delay %0d",
             k, CYCLES, cmp, mism, xa, toggles, DELAY);
    $display(mism == 0 ? "SC_EQ_SIM PASS" : "SC_EQ_SIM FAIL");
    $finish;
  end
endmodule
