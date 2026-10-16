`timescale 1ns/1ps
// dsfd_vm_static_wfc (wires-only parent over dsfd_vm_static_wfc_ctl) vs the r9 parent body (dsfd_vm_static_wfc_ref,
// extracted from git by wfc_ctl_equiv_gate.sh): same random f_wfc / e_v / e_d / vm_fault at related 3:4 clocks; every
// output compared on every stream edge; the registered fault compared one stream edge later.
module tb_wfc_ctl_equiv;
 parameter integer RLAT = 17, PAD = 0;
 reg ckt=0, cks=0; always #6 ckt=~ckt; always #8 cks=~cks;
 reg rt=0, rs=0;
 reg [559:0] f_wfc=0; reg [3:0] e_v=0; reg [2047:0] e_d=0; reg vmf=0;
 wire [1028:0] ta, tb; wire wva, wvb; wire [13:0] wra, wrb; wire [511:0] wda, wdb; wire [3:0] ava, avb; wire [55:0] ara, arb;
 wire fa, fb;
 dsfd_vm_static_wfc_ref #(.RLAT(RLAT), .RESPONSE_PAD(PAD)) ref_(cks, ckt, cks, ckt, cks, ckt, rs, rt, rs, rt, rs, rt,
   f_wfc, ta, wva, wra, wda, ava, ara, e_v, e_d, vmf, fa);
 dsfd_vm_static_wfc #(.RLAT(RLAT), .RESPONSE_PAD(PAD)) dut(cks, ckt, cks, ckt, cks, ckt, rs, rt, rs, rt, rs, rt,
   f_wfc, tb, wvb, wrb, wdb, avb, arb, e_v, e_d, vmf, fb);
 integer seed=1, seed0, n=0, k, faults=0, writes=0; reg fa_d=0;
 initial begin
  if($value$plusargs("seed=%d",seed))begin end seed0=seed;
  #190.5; rt=1; rs=1;   // release before epoch 4 (tb_ot_s81_vm_x34 convention, 3,336 ps epoch scaled to 48 ns)
  repeat(4000) begin
   @(negedge ckt);
   // the core's aux returns exactly as the decode expects them (ref internals); one stray return late in the run
   e_v = (ref_.e0 ? (4'd1 << ref_.l0) : 4'd0) | (ref_.e1 ? (4'd1 << ref_.l1) : 4'd0);
   if (n == 3500) e_v = e_v ^ 4'd8;
   for(k=0;k<64;k=k+1) e_d[32*k+:32]=$random(seed);
   vmf = (n>3800) && ($random(seed)%50==0);
   @(posedge ckt); #1;
   if(ta!==tb) $fatal(1,"MISMATCH t_wfc edge%0d",n);
   if({wva,wra,wda}!=={wvb,wrb,wdb}) $fatal(1,"MISMATCH w edge%0d",n);
   if({ava,ara}!=={avb,arb}) $fatal(1,"MISMATCH a edge%0d",n);
   if(fb!==fa_d) $fatal(1,"MISMATCH fault(+1) edge%0d ref%b dut%b",n,fa_d,fb);
   if (fa && !fa_d) $display("first fault edge%0d err%b rbad%b x34f%b x43f%b", n, ref_.err, ref_.r_bad, ref_.x34f, ref_.x43f);
   fa_d=fa; faults=faults+fa; writes=writes+wva; n=n+1;
  end
  $display("WFC_CTL_EQUIV PASS seed%0d edges%0d writes%0d fault_edges%0d",seed0,n,writes,faults); $finish;
 end
 always @(negedge cks) if(rs) begin
  f_wfc = 0;
  if($random(seed)%3==0) begin f_wfc[0]=1; f_wfc[527:513]=(n>3700 && $random(seed)%20==0)?15'h4abc:$unsigned($random(seed))%16384; for(k=0;k<16;k=k+1) f_wfc[1+32*k+:32]=$random(seed); end
  if($random(seed)%3==0) begin f_wfc[528]=1; f_wfc[543:529]=$unsigned($random(seed))%16384; f_wfc[558:544]=$unsigned($random(seed))%16384; f_wfc[559]=$random(seed); if (f_wfc[545:544]==f_wfc[530:529]) f_wfc[545:544]=f_wfc[530:529]+2'd1; end
 end
endmodule
