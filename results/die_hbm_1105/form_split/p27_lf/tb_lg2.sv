`timescale 1ns/1ps
module tb;
  logic clk=0, rst_n=0; logic [15:0] rq; logic [383:0] ra; logic [7:0] sw_v; logic [119:0] sw_addr; logic [63:0] sw_mask; logic [2047:0] sw_d;
  wire [511:0] rd_a, rd_b; wire flt_a, flt_b;
  gold_top a(.clk(clk),.rst_n(rst_n),.rq(rq),.ra(ra),.rd(rd_a),.sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.flt(flt_a));
  gate_top b(.clk(clk),.rst_n(rst_n),.rq(rq),.ra(ra),.rd(rd_b),.sw_v(sw_v),.sw_addr(sw_addr),.sw_mask(sw_mask),.sw_d(sw_d),.flt(flt_b));
  always #1 clk=~clk;
  integer cyc=0, errs=0, hits=0, mode; logic [23:0] base;
  always @(negedge clk) begin
    cyc<=cyc+1; rst_n <= (cyc%64)>=3;
    mode = $urandom%4; base = 24'($urandom);
    for (int i=0;i<16;i++) begin rq[i] = ($urandom%3)!=0; ra[i*24+:24] = (mode==0) ? 24'($urandom) : (base + 24'($urandom%(mode==1?4:(mode==2?40:600)))); end
    for (int s=0;s<8;s++) begin sw_v[s]=($urandom%(mode==0?3:24))==0; sw_addr[s*15+:15]= (mode==0)? 15'($urandom) : 15'(base[14:0]+15'($urandom%(mode==1?8:64))); end
    for (int k=0;k<2;k++) sw_mask[k*32+:32]=$urandom; for (int k=0;k<64;k++) sw_d[k*32+:32]=$urandom;
    if (cyc>6) begin
      if (rd_a!==rd_b) begin errs++; if (errs<6) $display("RD MISMATCH cyc=%0d", cyc); end
      if (flt_a!==flt_b) begin errs++; if (errs<6) $display("FLT MISMATCH cyc=%0d %b %b", cyc, flt_a, flt_b); end
      if (flt_a && (cyc%64)==40) hits++;
    end
    if (cyc==200000) begin $display("LG2 LOCKSTEP %s errs=%0d flt_cycles=%0d", errs?"FAIL":"PASS", errs, hits); $finish; end
  end
endmodule
