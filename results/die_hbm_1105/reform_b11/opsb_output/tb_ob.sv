`timescale 1ns/1ps
// HBM-REFORM-B11 opsb_output lock-step: old (git, lgroup2 NLW16) vs new (IREG + lgroup2_lf + BREG + FREG); new sr_d / sr_rv / flt = old two edges earlier.
module tb;
  logic clk=0, rst_n=0; logic [1:0] sr_v=0; logic [29:0] sr_addr=0; logic [15:0] lw=0; logic [383:0] lwa=0; logic [511:0] lwd=0;
  wire [511:0] da, db; wire [1:0] va, vb; wire fa, fb;
  old_hgi_sfu_opsb_output a(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(da),.sr_rv(va),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fa));
  ot_hgi_sfu_opsb_output b(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(db),.sr_rv(vb),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fb));
  always #1 clk=~clk;
  logic [511:0] d1,d2; logic [1:0] v1,v2; logic f1,f2;
  always @(posedge clk) begin d1<=da; d2<=d1; v1<=va; v2<=v1; f1<=fa; f2<=f1; end
  integer cyc=0, errs=0, rv=0, fl=0, mode=0; logic [23:0] base;
  always @(negedge clk) begin
    cyc<=cyc+1; rst_n <= (cyc%400)>=6;   // reset every 400 cycles (sticky flt re-arms)
    if (cyc%200==0) mode=$urandom%3; base=24'($urandom%4096);
    // legal-ish traffic: lane i writes its own bank (lane 0 any), sector reads over a small address window so reads hit written rows
    for (int i=0;i<16;i++) begin lw[i]=($urandom%(mode==2?2:4))==0; lwa[i*24+:24]={4'd0,base[15:0]+16'($urandom%(mode==0?4:64)),4'(i)};
      if (i==0 && mode!=0) lwa[3:0]=4'($urandom); end
    if (mode==1) for (int i=1;i<16;i++) lwa[i*24+:4]=4'($urandom);   // off-candidate lanes: wcoll / flt
    for (int k=0;k<16;k++) lwd[k*32+:32]=$urandom;
    for (int s=0;s<2;s++) begin sr_v[s]=($urandom%3)==0; sr_addr[s*15+:15]=15'({base[10:0],4'd0}+15'($urandom%(mode==0?64:1024))); end
    if (mode==0) sr_v[1]=1'b0;            // legal window: one sector lane, so no sector-lane bank conflict
    if (sr_v!=0 && $urandom%2==0) lw=0;
    if ((cyc%400)<12) begin lw=0; sr_v=0; end   // no ops while reset is held (the compiler issues none)
    if ((cyc%400)>=16) begin
      if (vb!==v2 || fb!==f2) begin errs++; if (errs<6) $display("CTL MISMATCH cyc=%0d v %b %b f %b %b", cyc, v2, vb, f2, fb); end
      for (int s=0;s<2;s++) if (v2[s] && db[256*s+:256]!==d2[256*s+:256]) begin errs++; if (errs<6) $display("SR_D MISMATCH cyc=%0d lane %0d", cyc, s); end
      if (v2!=0) rv++; if (f2) fl++;
    end
    if (cyc==`CYC) begin $display("OB LOCKSTEP %s errs=%0d sr_rv=%0d flt_cycles=%0d of %0d", errs?"FAIL":"PASS", errs, rv, fl, `CYC); $finish; end
  end
endmodule
