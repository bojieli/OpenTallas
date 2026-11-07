`timescale 1ns/1ps
// HBM-FORM-SPLIT-14-OPSB opsb_output WP lock-step: old (main part 41 text ddb087e49d, OT_OPSB_N32, no RREG) vs new
// (-DOT_OPSB_N32 -DOT_OPSB_WP=W).  sr_d (all 512 bits, X must match X) and sr_rv: new(t) == old(t - DS) EVERY cycle;
// flt: new(t) == old(t - FS) every cycle (DS = 2 + W, FS = W).  Reset every 400 cycles; traffic of results/die_hbm_1106/
// opsb_rreg/tb_rr.sv plus a collision-only mode (mode 3: every lane legal, lane 0 lands on a random bank 1 cycle in 10, so lane pairs (0, k)
// collide on one bank with different rows; no sector conflicts).
module tb;
  logic clk=0, rst_n=0; logic [1:0] sr_v=0; logic [29:0] sr_addr=0; logic [15:0] lw=0; logic [383:0] lwa=0; logic [511:0] lwd=0;
  wire [511:0] da, db; wire [1:0] va, vb; wire fa, fb;
  old_hgi_sfu_opsb_output a(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(da),.sr_rv(va),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fa));
  ot_hgi_sfu_opsb_output  b(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(db),.sr_rv(vb),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fb));
  always #1 clk=~clk;
  localparam integer DS = 2 + `WPV, FS = `WPV;
  logic [511:0] dq [0:7]; logic [1:0] vq [0:7]; logic fq [0:7];
  always @(posedge clk) begin dq[0]<=da; vq[0]<=va; fq[0]<=fa; for (int i=1;i<8;i++) begin dq[i]<=dq[i-1]; vq[i]<=vq[i-1]; fq[i]<=fq[i-1]; end end
  wire [511:0] de = dq[DS-1]; wire [1:0] ve = vq[DS-1]; wire fe = fq[FS-1];
  integer cyc=0, errs=0, derr=0, ferr=0, rv=0, fl=0, mode=0, kn=0, wr=0; logic [23:0] base;
  always @(negedge clk) begin
    cyc<=cyc+1; rst_n <= (cyc%400)>=6;
    if (cyc%200==0) mode=$urandom%4; base=24'($urandom%4096);
    for (int i=0;i<16;i++) begin lw[i]=($urandom%(mode==2?2:4))==0; lwa[i*24+:24]={4'd0,base[15:0]+16'($urandom%(mode==0?4:64)),4'(i)};
      if (i==0 && mode!=0 && mode!=3) lwa[3:0]=4'($urandom); end
    if (mode==1) for (int i=1;i<16;i++) lwa[i*24+:4]=4'($urandom);
    if (mode==3) begin lw=16'($urandom) & 16'($urandom) | 16'($urandom); for (int i=0;i<16;i++) lwa[i*24+4+:11]=base[10:0]+11'(i); lwa[3:0]=($urandom%10==0)?4'($urandom):4'd0; end
    for (int k=0;k<16;k++) lwd[k*32+:32]=$urandom;
    for (int s=0;s<2;s++) begin sr_v[s]=($urandom%3)==0; sr_addr[s*15+:15]=15'({base[10:0],4'd0}+15'($urandom%(mode==0?64:1024))); end
    if (mode==0 || mode==3) sr_v[1]=1'b0;
    if (sr_v!=0 && $urandom%2==0) lw=0;
    if ((cyc%400)<12) begin lw=0; sr_v=0; end
    if ((cyc%400)>=20) begin
      if (vb!==ve) begin errs++; if (errs<6) $display("CTL MISMATCH cyc=%0d v %b %b", cyc, ve, vb); end
      if (fb!==fe) begin errs++; ferr++; if (errs<6) $display("FLT MISMATCH cyc=%0d f %b %b", cyc, fe, fb); end
      if (db!==de) begin errs++; derr++; if (errs<6) $display("SR_D MISMATCH cyc=%0d valid %b", cyc, ve); end
      if (ve!=0) rv++; if (fe) fl++; if (ve!=0 && ^de!==1'bx) kn++; if (lw!=0) wr++;
    end
    if (cyc==`CYC) begin $display("WP%0d LOCKSTEP %s errs=%0d (sr_d %0d flt %0d) sr_rv=%0d known_valid_reads=%0d flt_cycles=%0d write_cycles=%0d of %0d", `WPV, errs?"FAIL":"PASS", errs, derr, ferr, rv, kn, fl, wr, `CYC); $finish; end
  end
endmodule
