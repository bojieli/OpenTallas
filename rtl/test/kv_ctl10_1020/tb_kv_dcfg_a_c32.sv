`timescale 1ns/1ps
// KV-CTL10 10-20: lockstep qkd_kv_die_cfg_a (AGES 1, the boot-ages tile's u_dcfg) vs qkd_kv_die_cfg_a_c32 (native census
// form), every output on every edge.  Episodes: POR, then a boot image (32 ECTL + 43 reset-region + capability + 19 age
// words + seal) written in order with random gaps; 1 in 4 episodes injects one error (out of order / repeat / bad padding /
// bad seal / post-seal write / unknown address); 1 in 3 episodes re-POR mid-image.  CMUT = the c32 MUT (bench negatives:
// 6 age words one word off, 7 age outputs ungated) -> must FAIL.  PASS KV_DCFG_A_C32 ... / FAIL ... mismatches<n>
module tb_kv_dcfg_a_c32;
`ifndef CMUT
 `define CMUT 0
`endif
 localparam integer NRST = 43, A0 = 32 + NRST + 1, NW = A0 + 19;
 reg ck = 0; always #5 ck = ~ck;
 reg por_n = 0, we = 0; reg [7:0] addr = 0; reg [63:0] data = 0;
 wire [159:0] ea0, eb0, ec0, ea1, eb1, ec1; wire [NRST*8-1:0] rd0, rd1;
 wire cap0, cap1, s0, s1, f0, f1; wire [31:0] at0, at1; wire [15:0] pv0, pv1; wire [255:0] vp0, vp1;
 qkd_kv_die_cfg_a #(.NRST(NRST), .CAP(1), .AGES(1), .MUT(0)) ref0 (.ck(ck), .por_n(por_n), .cfg_we(we), .cfg_addr(addr), .cfg_data(data),
     .ectl_a_cfg(ea0), .ectl_b_cfg(eb0), .ectl_c_cfg(ec0), .rst_dly(rd0), .fused_program_capability(cap0), .age_attn(at0),
     .age_pv(pv0), .age_vport(vp0), .sealed(s0), .fault(f0));
 qkd_kv_die_cfg_a_c32 #(.NRST(NRST), .CAP(1), .AGES(1), .MUT(`CMUT)) dut (.ck(ck), .por_n(por_n), .cfg_we(we), .cfg_addr(addr), .cfg_data(data),
     .ectl_a_cfg(ea1), .ectl_b_cfg(eb1), .ectl_c_cfg(ec1), .rst_dly(rd1), .fused_program_capability(cap1), .age_attn(at1),
     .age_pv(pv1), .age_vport(vp1), .sealed(s1), .fault(f1));
 wire [1335:0] va = {ea0, eb0, ec0, rd0, cap0, at0, pv0, vp0, s0, f0};
 wire [1335:0] vb = {ea1, eb1, ec1, rd1, cap1, at1, pv1, vp1, s1, f1};
 integer seed = 11, cyc = 0, mism = 0, cmp = 0, seals = 0, faults = 0, ep, w, err, errw, gap, por_at;
 reg armed = 0;
 always @(posedge ck) begin
  #1; cyc = cyc + 1;
  if (armed) begin
   if (va !== vb) begin mism = mism + 1; if (mism <= 8) $display("MISMATCH cyc %0d first diff bit %0d", cyc, $clog2(((va ^ vb) & -(va ^ vb)) + 1) - 1); end
   else cmp = cmp + 1;
  end
 end
 function automatic [63:0] word(input integer i);
  reg [63:0] r; begin
   r = {$random(seed), $random(seed)};
   if (i < 32) word = {49'd0, r[14:0]};
   else if (i < 32 + NRST) word = {56'd0, r[7:0]};
   else if (i == 32 + NRST) word = {63'd0, r[0]};
   else if (i == A0) word = {32'd0, r[31:0]};
   else if (i == A0 + 1 || i == A0 + 2) word = {56'd0, r[7:0]};
   else if (i < NW) word = {48'd0, r[15:0]};
   else word = 64'h514b5644_43464731;
  end
 endfunction
 task automatic wr(input [7:0] a, input [63:0] d);
  begin @(negedge ck); we = 1; addr = a; data = d; @(negedge ck); we = 0; addr = $random(seed); data = {$random(seed), $random(seed)};
   repeat ($unsigned($random(seed)) % 3) @(negedge ck); end
 endtask
 initial begin
  for (ep = 0; ep < 400; ep = ep + 1) begin
   armed = 0; por_n = 0; we = 0; repeat (3) @(negedge ck); por_n = 1; repeat (3) @(negedge ck); armed = 1;
   err = ($unsigned($random(seed)) % 4 == 0) ? 1 + $unsigned($random(seed)) % 6 : 0;
   errw = $unsigned($random(seed)) % (NW + 1);
   por_at = ($unsigned($random(seed)) % 3 == 0) ? $unsigned($random(seed)) % (NW + 1) : -1;
   for (w = 0; w <= NW; w = w + 1) begin
    if (w == por_at) begin armed = 0; por_n = 0; @(negedge ck); por_n = 1; repeat (3) @(negedge ck); armed = 1; end
    if (err != 0 && w == errw) begin
     case (err)
      1: wr(w + 1, word(w + 1));                                  // out of order
      2: begin wr(w, word(w)); wr(w, word(w)); end                 // repeated
      3: wr(w, word(w) | (64'd1 << 40));                            // padding bit
      4: wr(NW, 64'hdead_beef);                                     // bad seal
      5: wr(8'd250, 64'd0);                                         // unknown address
      default: wr(w, word(w));
     endcase
    end else wr(w, word(w));
   end
   if (err == 6) wr(8'd3, word(3));                                 // post-seal write
   repeat (8) @(negedge ck);
   if (s0) seals = seals + 1; if (f0) faults = faults + 1;
  end
  if (mism == 0) $display("PASS KV_DCFG_A_C32 mismatches0 cycles%0d compared%0d episodes400 sealed%0d faulted%0d", cyc, cmp, seals, faults);
  else $display("FAIL KV_DCFG_A_C32 mismatches%0d cycles%0d", mism, cyc);
  $finish;
 end
endmodule
