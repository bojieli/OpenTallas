// Random lockstep: ot_hbm_rf_visibility_fence_live LATE_CHECK=0 (reference) vs LATE_CHECK=1,
// identical inputs every cycle, every output compared every cycle (fault-free: must be equal).
// Stimulus follows the protocol (phase-matched channels, correct identity) with mutants:
// wrong identity, wrong-phase valids, wrong drain fields, partial alldrain, runtime resets, POR.
// +seed=<n> +cycles=<n> +mut=<per mille>
// +inj=<per 10k>: injection mode (lockstep compare off; stimulus follows the LATE_CHECK=1 copy):
// random upsets in lat1 (single witness bit, single live-copy bit, two witness bits in one SECDED
// half, one bit in two live copies, one bit of the duplicate witness). Checked: no handshake on
// the corrupted cycle for every kind (a single live-copy upset also holds the row, then scrubs);
// the RTL $fatal obligations (no handshake on a dirty row; candidate encode == encode(next_raw);
// select decision == released handshakes on a clean row) every cycle; an uncorrectable upset
// raises fault and quarantine on the next edge and the row stays frozen; a correctable upset
// never changes the retained identity.
`timescale 1ns/1ps
module tb_fence_late_lockstep;
  reg clk=0, por_n=0, rst_n=0;
  reg req_valid=0, req_internal_SIMD=0; reg [54:0] req_identity=0;
  reg host_ack_valid=0, simd_ack_retire_valid=0, visible_ready=0, consumer_valid=0;
  reg child_reverse_valid=0, parent_reverse_valid=0, reverse_CDC_valid=0, drain_req_ready=0;
  reg drain_rsp_valid=0, drain_rsp_has_owner=0, drain_rsp_reset_scope=0, retire_ready=0;
  reg [54:0] host_ack_identity=0, simd_ack_retire_identity=0, consumer_identity=0,
             child_reverse_identity=0, parent_reverse_identity=0, reverse_CDC_identity=0, drain_rsp_identity=0;
  reg [8:0] alldrain_live=0;
  wire [127:0] o0, o1;
`define FENCE(name, LC, o) \
  wire name``_rr, name``_har, name``_sar, name``_vv, name``_cr, name``_chr, name``_pr, name``_cdr, name``_dqv, name``_dqo, name``_dqs, name``_dsr, name``_rv, name``_f, name``_q; \
  wire [54:0] name``_vid, name``_did, name``_rid; \
  ot_hbm_rf_visibility_fence_live #(.ENABLE(1),.LATE_CHECK(LC)) name( \
    .clk(clk),.por_n(por_n),.rst_n(rst_n),.req_valid(req_valid),.req_identity(req_identity), \
    .req_internal_SIMD(req_internal_SIMD),.req_ready(name``_rr),.host_ack_valid(host_ack_valid), \
    .host_ack_identity(host_ack_identity),.host_ack_ready(name``_har),.simd_ack_retire_valid(simd_ack_retire_valid), \
    .simd_ack_retire_identity(simd_ack_retire_identity),.simd_ack_retire_ready(name``_sar), \
    .visible_valid(name``_vv),.visible_identity(name``_vid),.visible_ready(visible_ready), \
    .consumer_valid(consumer_valid),.consumer_identity(consumer_identity),.consumer_ready(name``_cr), \
    .child_reverse_valid(child_reverse_valid),.child_reverse_identity(child_reverse_identity),.child_reverse_ready(name``_chr), \
    .parent_reverse_valid(parent_reverse_valid),.parent_reverse_identity(parent_reverse_identity),.parent_reverse_ready(name``_pr), \
    .reverse_CDC_valid(reverse_CDC_valid),.reverse_CDC_identity(reverse_CDC_identity),.reverse_CDC_ready(name``_cdr), \
    .drain_req_valid(name``_dqv),.drain_req_identity(name``_did),.drain_req_has_owner(name``_dqo), \
    .drain_req_reset_scope(name``_dqs),.drain_req_ready(drain_req_ready),.drain_rsp_valid(drain_rsp_valid), \
    .drain_rsp_identity(drain_rsp_identity),.drain_rsp_has_owner(drain_rsp_has_owner), \
    .drain_rsp_reset_scope(drain_rsp_reset_scope),.alldrain_live(alldrain_live),.drain_rsp_ready(name``_dsr), \
    .retire_valid(name``_rv),.retire_identity(name``_rid),.retire_ready(retire_ready),.fault(name``_f),.quarantine(name``_q)); \
  assign o = {name``_rr,name``_har,name``_sar,name``_vv,name``_cr,name``_chr,name``_pr,name``_cdr,name``_dqv,name``_dqo, \
              name``_dqs,name``_dsr,name``_rv,name``_f,name``_q,name``_vid[54:0],name``_did[54:0],name``_rid[2:0]};
  `FENCE(ref0, 1'b0, o0)
  `FENCE(lat1, 1'b1, o1)
  wire [54:0] rid_full0=ref0_rid, rid_full1=lat1_rid;
  integer seed, cycles, cyc, mism=0, hs=0, nrst=0, npor=0, nfault=0, nretire=0;
  reg [3:0] ph; integer inj, kind, b1, b2, ninj=0, nue=0, inj_bad=0; reg [54:0] id_before; reg fault_before;
  wire lat_hs = (req_valid&&lat1_rr) || (host_ack_valid&&lat1_har) || (simd_ack_retire_valid&&lat1_sar) || (lat1_vv&&visible_ready)
     || (consumer_valid&&lat1_cr) || (child_reverse_valid&&lat1_chr) || (parent_reverse_valid&&lat1_pr) || (reverse_CDC_valid&&lat1_cdr)
     || (lat1_dqv&&drain_req_ready) || (drain_rsp_valid&&lat1_dsr) || (lat1_rv&&retire_ready);
  reg [63:0] xs;
  function [31:0] rnd(input integer dummy); begin   // xorshift64
    xs = xs ^ (xs << 13); xs = xs ^ (xs >> 7); xs = xs ^ (xs << 17); rnd = xs[31:0]; end endfunction
  function [54:0] maybe_bad(input [54:0] id); begin
    maybe_bad = (rnd(0)%1000 < mut) ? id ^ (55'd1 << (rnd(0)%55)) : id; end endfunction
  function bit pr(input integer pct); begin pr = (rnd(0)%100) < pct; end endfunction
  integer mut;   // wrong-phase / foreign-field mutant rate per mille per channel (+mut=)
  function bit pm(input integer pml); begin pm = (rnd(0)%1000) < pml; end endfunction
  always #1 clk=~clk;
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed=1;
    if (!$value$plusargs("cycles=%d", cycles)) cycles=200000;
    if (!$value$plusargs("mut=%d", mut)) mut=2;
    if (!$value$plusargs("inj=%d", inj)) inj=0;
    xs = 64'h9E3779B97F4A7C15 ^ seed;
    repeat(3) @(negedge clk); por_n=1; rst_n=1;
    for (cyc=0; cyc<cycles; cyc=cyc+1) begin
      @(negedge clk);
      ph = inj ? lat1.enabled.phase : ref0.enabled.phase;
      // runtime reset pulses and rare cold POR
      if (pm(2)) begin rst_n=0; nrst=nrst+1; end else if (!rst_n && pr(50)) rst_n=1;
      if (por_n && rnd(0)%(inj ? 500 : 5000)==0) begin por_n=0; npor=npor+1; end else if (!por_n) por_n=1;
      req_valid = (ph==0) ? pr(60) : pm(mut);
      req_identity = {rnd(0),rnd(0)}; if (pr(97)) req_identity[47:45] = rnd(0)%6;
      req_internal_SIMD = pr(50);
      host_ack_valid = (ph==1 && !(inj ? lat1.enabled.raw[61] : ref0.enabled.raw[61])) ? pr(60) : pm(mut);
      simd_ack_retire_valid = (ph==1 && (inj ? lat1.enabled.raw[61] : ref0.enabled.raw[61])) ? pr(60) : pm(mut);
      host_ack_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      simd_ack_retire_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      visible_ready = pr(60);
      consumer_valid = (ph==3) ? pr(60) : pm(mut);       consumer_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      child_reverse_valid = (ph==4) ? pr(60) : pm(mut);  child_reverse_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      parent_reverse_valid = (ph==5) ? pr(60) : pm(mut); parent_reverse_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      reverse_CDC_valid = (ph==6) ? pr(60) : pm(mut);    reverse_CDC_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      drain_req_ready = pr(60);
      drain_rsp_valid = (ph==8 || ph==11) ? pr(60) : pm(mut);
      drain_rsp_identity = maybe_bad((inj ? lat1.enabled.identity : ref0.enabled.identity));
      drain_rsp_has_owner = !pm(mut) ? (inj ? lat1_dqo : ref0_dqo) : !(inj ? lat1_dqo : ref0_dqo);
      drain_rsp_reset_scope = !pm(mut) ? (inj ? lat1_dqs : ref0_dqs) : !(inj ? lat1_dqs : ref0_dqs);
      alldrain_live = pr(80) ? 9'h1ff : rnd(0);
      retire_ready = pr(60);
      // injection (lat1 only), applied after the inputs, before the compare point
      if (inj && por_n && rst_n && !lat1.enabled.bad_q && !lat1.enabled.dirty && (rnd(0)%10000) < inj) begin
        kind = rnd(0)%5; b1 = rnd(0)%144; b2 = (b1/72)*72 + (b1%72 + 1 + rnd(0)%71) % 72; ninj=ninj+1;  // b2: same SECDED half
        id_before = lat1.enabled.identity; fault_before = lat1_f;
        case (kind)
          0: lat1.enabled.protected_state[b1] = ~lat1.enabled.protected_state[b1];
          1: begin b1=b1%71; lat1.enabled.live_b[b1] = ~lat1.enabled.live_b[b1]; end
          2: begin lat1.enabled.protected_state[b1] = ~lat1.enabled.protected_state[b1];
                   lat1.enabled.protected_state[b2] = ~lat1.enabled.protected_state[b2]; end
          3: begin b1=b1%71; lat1.enabled.live_a[b1] = ~lat1.enabled.live_a[b1];
                   lat1.enabled.live_c[b1] = ~lat1.enabled.live_c[b1]; end
          4: lat1.enabled.ps_dup[b1] = ~lat1.enabled.ps_dup[b1];
        endcase
        #0.25;
        if (lat_hs) begin inj_bad=inj_bad+1; $display("INJ_FAIL handshake on corrupted row kind=%0d", kind); end
        if ((kind<=1 || kind==4) && lat1.enabled.identity!==id_before) begin inj_bad=inj_bad+1; $display("INJ_FAIL correctable changed identity"); end
        if (kind==2 || kind==3) begin
          nue=nue+1;
          @(posedge clk); #0.1;
          if (!lat1_f || !lat1_q) begin inj_bad=inj_bad+1; $display("INJ_FAIL no fault one edge after UE kind=%0d", kind); end
        end
      end
      #0.5;
      if (!inj && (o0 !== o1 || rid_full0 !== rid_full1)) begin
        mism=mism+1;
        if (mism<10) $display("MISMATCH cyc=%0d ph=%0d o0=%h o1=%h", cyc, ph, o0, o1);
      end
      if (ref0_f) nfault=nfault+1;
      hs = hs + (req_valid&&ref0_rr) + (host_ack_valid&&ref0_har) + (simd_ack_retire_valid&&ref0_sar) + (ref0_vv&&visible_ready)
         + (consumer_valid&&ref0_cr) + (child_reverse_valid&&ref0_chr) + (parent_reverse_valid&&ref0_pr) + (reverse_CDC_valid&&ref0_cdr)
         + (ref0_dqv&&drain_req_ready) + (drain_rsp_valid&&ref0_dsr) + (ref0_rv&&retire_ready);
      nretire = nretire + (ref0_rv&&retire_ready);
    end
    if (inj) begin
      $display("INJECT mut=%0d seed=%0d cycles=%0d injections=%0d uncorrectable=%0d failures=%0d handshakes_ref=%0d", mut, seed, cycles, ninj, nue, inj_bad, hs);
      if (inj_bad==0) $display("INJECT_PASS"); else $display("INJECT_FAIL");
    end else begin
    $display("LOCKSTEP mut=%0d seed=%0d cycles=%0d handshakes=%0d retires=%0d fault_cycles=%0d rst=%0d por=%0d mismatches=%0d",
             mut, seed, cycles, hs, nretire, nfault, nrst, npor, mism);
    if (mism==0) $display("LOCKSTEP_PASS"); else $display("LOCKSTEP_FAIL");
    end
    $finish;
  end
endmodule
