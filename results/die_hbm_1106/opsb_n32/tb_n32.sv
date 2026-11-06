`timescale 1ns/1ps
// HBM-FORM-SPLIT-13-OPSB opsb_output lock-step: old (main text, 16 x ot_sram_1r1w_256x256_m2_r2c2 row banks) vs new
// (-DOT_OPSB_N32, 16 x ot_sram_1r1w_2048x32_m8_r0c0).  Same latency: EVERY output (sr_d all 512 bits, sr_rv, flt) is
// compared EVERY cycle with !== (X must match X), reset pulses every 400 cycles; traffic of results/die_hbm_1105/reform_b11.
module tb;
  logic clk=0, rst_n=0; logic [1:0] sr_v=0; logic [29:0] sr_addr=0; logic [15:0] lw=0; logic [383:0] lwa=0; logic [511:0] lwd=0;
  wire [511:0] da, db; wire [1:0] va, vb; wire fa, fb;
  old_hgi_sfu_opsb_output a(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(da),.sr_rv(va),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fa));
  ot_hgi_sfu_opsb_output  b(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(db),.sr_rv(vb),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fb));
  always #1 clk=~clk;
  integer cyc=0, errs=0, derr=0, rv=0, fl=0, mode=0, kn=0; logic [23:0] base;
  always @(negedge clk) begin
    cyc<=cyc+1; rst_n <= (cyc%400)>=6;
    if (cyc%200==0) mode=$urandom%3; base=24'($urandom%4096);
    for (int i=0;i<16;i++) begin lw[i]=($urandom%(mode==2?2:4))==0; lwa[i*24+:24]={4'd0,base[15:0]+16'($urandom%(mode==0?4:64)),4'(i)};
      if (i==0 && mode!=0) lwa[3:0]=4'($urandom); end
    if (mode==1) for (int i=1;i<16;i++) lwa[i*24+:4]=4'($urandom);
    for (int k=0;k<16;k++) lwd[k*32+:32]=$urandom;
    for (int s=0;s<2;s++) begin sr_v[s]=($urandom%3)==0; sr_addr[s*15+:15]=15'({base[10:0],4'd0}+15'($urandom%(mode==0?64:1024))); end
    if (mode==0) sr_v[1]=1'b0;
    if (sr_v!=0 && $urandom%2==0) lw=0;
    if ((cyc%400)<12) begin lw=0; sr_v=0; end
    if (vb!==va || fb!==fa) begin errs++; if (errs<6) $display("CTL MISMATCH cyc=%0d v %b %b f %b %b", cyc, va, vb, fa, fb); end
    if (db!==da) begin errs++; derr++; if (errs<6) $display("SR_D MISMATCH cyc=%0d valid %b", cyc, va); end
    if (va!=0) rv++; if (fa) fl++; if (va!=0 && ^da!==1'bx) kn++;
    if (cyc==`CYC) begin $display("N32 LOCKSTEP %s errs=%0d (sr_d %0d) sr_rv=%0d known_valid_reads=%0d flt_cycles=%0d of %0d", errs?"FAIL":"PASS", errs, derr, rv, kn, fl, `CYC); $finish; end
  end
endmodule
