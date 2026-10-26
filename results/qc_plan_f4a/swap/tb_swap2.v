// QC-PLAN-F4A narrowed swap lockstep: vm8x vmr + qfd_dv_s8_crh_rp1 with the column SRAM view (new) vs origin/main m2 view (old, _o).
// suffixed _o).  Same random stream into both copies of each core; q and fault compared every cycle after reset.
// Rows restricted to 0..15 (+ bank bit, + full lane offsets) so reads hit written words often; row 0 included so the
// repair-row mutant (+define+MUT_RR: new view rr_en untied) is exercised.
`timescale 1ns/1ps
module tb;
  reg ck = 0; always #0.5 ck = ~ck;
  reg rst_n;
  reg [7:0] re, vm_we, cr_re; reg [191:0] addr, vm_waddr, cr_addr; reg [255:0] vm_wdata;
  reg w16_we, w1_we; reg [23:0] w16_addr, w1_addr; reg [511:0] w16_data; reg [31:0] w1_data;
  reg tw_we; reg [1:0] tw_kind; reg [23:0] tw_addr; reg [511:0] tw_d;
  wire [255:0] qv_n, qv_o, qc_n, qc_o; wire fv_n, fv_o, fc_n, fc_o;
  qfd_dv_s8x_vmr   vn (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(qv_n), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
      .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fv_n));
  qfd_dv_s8x_vmr_o vo (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(qv_o), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
      .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fv_o));
  qfd_dv_s8_crh_rp1 cn (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(qc_n), .tw_we(tw_we), .tw_kind(tw_kind),
      .tw_addr(tw_addr), .tw_d(tw_d), .fault(fc_n));
  qfd_dv_s8_crh_rp1_o co (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(qc_o), .tw_we(tw_we), .tw_kind(tw_kind),
      .tw_addr(tw_addr), .tw_d(tw_d), .fault(fc_o));
  integer cyc, j, mv, mc, nzv, nzc, seed, N;
  function [23:0] ra; input dummy; begin ra = $random; ra[13:4] = $random & 15; end endfunction
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    if (!$value$plusargs("n=%d", N)) N = 60000;
    for (j = 0; j < seed * 7919; j = j + 1) cyc = $random;  // advance the global $random stream per seed (plain $random ignores the seed var)
    mv = 0; mc = 0; nzv = 0; nzc = 0; rst_n = 0;
    {re, vm_we, cr_re, w16_we, w1_we, tw_we} = 0; addr = 0; vm_waddr = 0; cr_addr = 0; vm_wdata = 0; w16_addr = 0; w1_addr = 0;
    w16_data = 0; w1_data = 0; tw_kind = 0; tw_addr = 0; tw_d = 0;
    repeat (4) @(negedge ck);
    rst_n = 1;
    for (cyc = 0; cyc < N; cyc = cyc + 1) begin
      @(negedge ck);
      if (cyc > 8) begin
        if (qv_n !== qv_o || fv_n !== fv_o) begin mv = mv + 1; if (mv < 4) $display("VMR MISMATCH cyc %0d", cyc); end
        if (qc_n !== qc_o || fc_n !== fc_o) begin mc = mc + 1; if (mc < 4) $display("RP1 MISMATCH cyc %0d", cyc); end
        if (qv_o != 0) nzv = nzv + 1;
        if (qc_o != 0) nzc = nzc + 1;
      end
      re = $random; cr_re = $random;
      for (j = 0; j < 8; j = j + 1) begin addr[24*j +: 24] = ra(0); vm_waddr[24*j +: 24] = ra(0); cr_addr[24*j +: 24] = ra(0);
        vm_wdata[32*j +: 32] = $random; end
      vm_we = $random; w16_we = ($random & 3) == 0; w16_addr = ra(0); w1_we = ($random & 3) == 0; w1_addr = ra(0); w1_data = $random;
      for (j = 0; j < 16; j = j + 1) begin w16_data[32*j +: 32] = $random; tw_d[32*j +: 32] = $random; end
      tw_we = $random; tw_kind = $random; tw_addr = ra(0); tw_addr[9:0] = $random & 15;
    end
    $display("RESULT seed_in %0d cycles %0d vmr_mismatch %0d rp1_mismatch %0d vmr_nonzero_q %0d rp1_nonzero_q %0d", seed, N, mv, mc, nzv, nzc);
    $finish;
  end
endmodule
