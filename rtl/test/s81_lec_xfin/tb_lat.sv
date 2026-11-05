`timescale 1ns/1ps
// LEC-EGN-1 xfin form bench: gold = eng_finish @2c2cb26e06 (0-cycle operand path), new = working tree (log-depth gs +
// registered operand select win_op_q, +1 cycle per issue). Latency-tolerant: the ordered r_v result stream
// {r_hh, r_kk, r_dd} and the per-episode fault flag must match; reports the max r_v latency shift.
module tb;
  localparam P=3,K=5;
  reg clk=0, rst_n=0, go=0; reg [P-1:0] f_v=0; reg [P*2-1:0] f_t=0; reg [P*8-1:0] f_base=0; reg [P*K*32-1:0] f_d=0;
  wire rv0,rv1,f0,f1; wire [31:0] h0,k0,d0,h1,k1,d1;
  gold_eng_finish g(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_t(f_t),.f_base(f_base),.f_d(f_d),.r_v(rv0),.r_hh(h0),.r_kk(k0),.r_dd(d0),.fault(f0));
  ot_s81dv_eng_finish n(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_t(f_t),.f_base(f_base),.f_d(f_d),.r_v(rv1),.r_hh(h1),.r_kk(k1),.r_dd(d1),.fault(f1));
  always #1 clk=~clk;
  integer gocyc=0, lat0=0, lat1=0, cyc=0, mism=0, n0=0, n1=0, ep, i, j, q, cnt, seed, maxsh=0, fe0=0, fe1=0, fmis=0;
  integer ord [0:47];
  reg [95:0] s0 [0:255]; integer c0 [0:255];
  reg ef0=0, ef1=0;
  always @(posedge clk) begin cyc<=cyc+1;
    if (rst_n && rv0) begin s0[n0%256] = {h0,k0,d0}; c0[n0%256] = cyc; n0 = n0 + 1; if (cyc-gocyc > lat0) lat0 = cyc-gocyc; end
    if (rst_n && rv1) begin
      if (n1 >= n0) begin mism=mism+1; if (mism<5) $display("EXTRA new r_v cyc %0d", cyc); end
      else begin
        if (s0[n1%256] !== {h1,k1,d1}) begin mism=mism+1; if (mism<5) $display("MISMATCH #%0d cyc %0d %h/%h", n1, cyc, s0[n1%256], {h1,k1,d1}); end
        if (cyc - c0[n1%256] > maxsh) maxsh = cyc - c0[n1%256];
      end
      n1 = n1 + 1; if (cyc-gocyc > lat1) lat1 = cyc-gocyc; end
    if (f0) ef0 = 1; if (f1) ef1 = 1;
  end
  task rnd32(output [31:0] x); begin x = {1'b0, 8'd100 + ($random(seed) & 8'h1f), 23'h0 | $random(seed)}; if ($random(seed)&1) x[31]=1; end endtask
  reg [31:0] w;
  initial begin
    seed = 0; if ($value$plusargs("seed=%d", seed)) ;
    repeat(5) @(negedge clk); rst_n=1; repeat(3) @(negedge clk);
    for (ep=0; ep<12; ep=ep+1) begin
      ef0=0; ef1=0; gocyc=cyc; go=1; @(negedge clk); go=0; repeat(3) @(negedge clk);
      for (i=0;i<48;i=i+1) ord[i]=i;
      for (i=47;i>0;i=i-1) begin j=$unsigned($random(seed))%(i+1); q=ord[i]; ord[i]=ord[j]; ord[j]=q; end
      i=0;
      while (i<48) begin
        f_v=0; cnt=0;
        for (q=0;q<P;q=q+1) if (i<48 && ($random(seed)&3)!=0) begin
          f_v[q]=1; f_t[q*2+:2]=ord[i]/16; f_base[q*8+:8]=(ord[i]%16)*5;
          for (j=0;j<K;j=j+1) begin rnd32(w); f_d[(q*K+j)*32+:32]=w; end
          if (ep>=10 && ($random(seed)&15)==0) f_base[q*8+:8]=$random(seed);
          i=i+1; end
        @(negedge clk);
      end
      f_v=0; repeat(1500) @(negedge clk);
      if (ef0 !== ef1) begin fmis = fmis + 1; $display("FAULT MISMATCH ep %0d %b/%b", ep, ef0, ef1); end
      if (ef0) fe0 = fe0 + 1; if (ef1) fe1 = fe1 + 1;
    end
    if (n0 != n1) mism = mism + 1;
    $display("XFIN_LAT %s cycles %0d r_v %0d/%0d fault_eps %0d/%0d max_shift %0d go_to_rv_max %0d/%0d mismatches %0d fault_mis %0d seed %0d",
             (mism==0 && fmis==0 && n0>0) ? "PASS" : "FAIL", cyc, n0, n1, fe0, fe1, maxsh, lat0, lat1, mism, fmis, seed);
    $finish;
  end
endmodule
