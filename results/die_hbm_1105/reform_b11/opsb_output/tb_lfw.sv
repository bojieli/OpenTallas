`timescale 1ns/1ps
// HBM-REFORM-B11: lgroup2_lf lane-write + sector-read log selects vs ot_hgi_su_lgroup2 (opsb_output params NLW16 NS2), banks = lbank_fake
// (registers every bank input onto rd, so sr_d observes the read select and the write select). Random with address locality.
module tb;
  logic clk=0, rst_n=0; logic [1:0] sr_v; logic [29:0] sr_addr; logic [15:0] lw; logic [383:0] lwa; logic [511:0] lwd;
  wire [511:0] da, db; wire [1:0] va, vb; wire fa, fb;
  gold_top a(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(da),.sr_rv(va),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fa));
  gate_top b(.clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(db),.sr_rv(vb),.lw(lw),.lwa(lwa),.lwd(lwd),.flt(fb));
  always #1 clk=~clk;
  integer cyc=0, errs=0, hits=0, wc=0, mode; logic [23:0] base;
  always @(negedge clk) begin
    cyc<=cyc+1; rst_n <= (cyc%64)>=3;
    if (cyc%64==0) mode=$urandom%6; base=24'($urandom);
    // modes 4,5: legal lane writes (lane i -> its bank i; lane 0 -> any bank, same or another row), so wcoll is rare
    if (mode>=4) begin for (int i=0;i<16;i++) begin lw[i]=($urandom%3)==0; lwa[i*24+:24]={base[23:5]+19'($urandom%(mode==4?1:2)),i[4:0]};
      if (i==0) lwa[4:0]=5'($urandom%16) | 5'(lwa[4:0] & 5'h10); end
      lwa[4]=1'b0; for (int i=1;i<16;i++) lwa[i*24+4]=1'b0; end
    else
    for (int i=0;i<16;i++) begin lw[i] = ($urandom%(mode==3?2:5))==0;
      lwa[i*24+:24] = (mode==0) ? 24'($urandom) : (mode==1) ? (24'(i) + {base[23:4],4'd0} + 24'(16*($urandom%2)))
                     : (base + 24'($urandom%(mode==2?40:600))); end
    for (int s=0;s<2;s++) begin sr_v[s]=(mode>=4)?1'b0:(($urandom%(mode==3?2:6))==0); sr_addr[s*15+:15]=(mode==0)?15'($urandom):15'(base[14:0]+15'($urandom%(mode==1?8:64))); end
    for (int k=0;k<16;k++) lwd[k*32+:32]=$urandom;
    if (cyc>6) begin
      if (da!==db || va!==vb) begin errs++; if (errs<6) $display("SR MISMATCH cyc=%0d", cyc); end
      if (fa!==fb) begin errs++; if (errs<6) $display("FLT MISMATCH cyc=%0d %b %b", cyc, fa, fb); end
      if (fa && (cyc%64)==40) hits++;
      if (a.u_g.wcoll) wc++;
    end
    if (cyc==200000) begin $display("LFW LOCKSTEP %s errs=%0d flt_cycles=%0d wcoll=%0d", errs?"FAIL":"PASS", errs, hits, wc); $finish; end
  end
endmodule
