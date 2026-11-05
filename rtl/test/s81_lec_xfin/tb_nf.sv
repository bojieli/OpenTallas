`timescale 1ns/1ps
// FORM-NF bench: gold = norm_finish before FORM-NF, new = ot_s81dv_norm_finish (latency-tolerant).  Ordered r_v result stream and
// per-episode fault flag must match.  Legal flit bases only (sid * K), as ot_s81dv_xfin drives; duplicate flits in the last episodes.
module tb;
  localparam P=3,K=5,NS=16;
  reg clk=0, rst_n=0, go=0; reg [P-1:0] f_v=0; reg [P*8-1:0] f_base=0; reg [P*K*32-1:0] f_d=0; reg [31:0] eps=32'h2b8cbccc;
  wire rv0,rv1,f0,f1; wire [31:0] r0,r1;
  gold_nf g(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_base(f_base),.f_d(f_d),.eps(eps),.r_v(rv0),.r(r0),.fault(f0));
  ot_s81dv_norm_finish n(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_base(f_base),.f_d(f_d),.eps(eps),.r_v(rv1),.r(r1),.fault(f1));
  always #1 clk=~clk;
  integer gocyc=0, lat0=0, lat1=0, cyc=0, mism=0, n0=0, n1=0, ep, i, j, q, seed, maxsh=0, fe0=0, fe1=0, fmis=0;
  integer ord [0:NS-1];
  reg [31:0] s0 [0:255]; integer c0 [0:255];
  reg ef0=0, ef1=0;
  // both sample at the rising edge; new's out face moved at the prior falling edge
  always @(posedge clk) begin cyc<=cyc+1;
    if (rst_n && rv0===1'b1) begin s0[n0%256] = r0; c0[n0%256] = cyc; n0 = n0 + 1; if (cyc-gocyc > lat0) lat0 = cyc-gocyc; end
    if (rst_n && rv1===1'b1) begin
      if (n1 >= n0) begin mism=mism+1; if (mism<5) $display("EXTRA new r_v cyc %0d", cyc); end
      else begin
        if (s0[n1%256] !== r1) begin mism=mism+1; if (mism<5) $display("MISMATCH #%0d cyc %0d %h/%h", n1, cyc, s0[n1%256], r1); end
        if (cyc - c0[n1%256] > maxsh) maxsh = cyc - c0[n1%256];
      end
      n1 = n1 + 1; if (cyc-gocyc > lat1) lat1 = cyc-gocyc; end
    if (f0===1'b1) ef0 = 1; if (f1===1'b1) ef1 = 1;
  end
  task rnd32(output [31:0] x); begin x = {1'b0, 8'd100 + ($random(seed) & 8'h1f), 23'h0 | $random(seed)}; if (($random(seed)&63)==0) x[31]=1; end endtask
  reg [31:0] w;
  initial begin
    seed = 0; if ($value$plusargs("seed=%d", seed)) ;
    repeat(5) @(negedge clk); rst_n=1; repeat(3) @(negedge clk);
    for (ep=0; ep<12; ep=ep+1) begin
      ef0=0; ef1=0; gocyc=cyc; go=1; @(negedge clk); go=0; repeat(3) @(negedge clk);
      for (i=0;i<NS;i=i+1) ord[i]=i;
      for (i=NS-1;i>0;i=i-1) begin j=$unsigned($random(seed))%(i+1); q=ord[i]; ord[i]=ord[j]; ord[j]=q; end
      i=0;
      while (i<NS) begin
        f_v=0;
        for (q=0;q<P;q=q+1) if (i<NS && ($random(seed)&3)!=0) begin
          f_v[q]=1; f_base[q*8+:8]=ord[i]*K;
          for (j=0;j<K;j=j+1) begin rnd32(w); f_d[(q*K+j)*32+:32]=w; end
          if (ep>=10 && ($random(seed)&7)==0) f_base[q*8+:8]=ord[0]*K;   // duplicate flit
          i=i+1; end
        @(negedge clk);
      end
      f_v=0; repeat(1200) @(negedge clk);
      if (ef0 !== ef1) begin fmis = fmis + 1; $display("FAULT MISMATCH ep %0d %b/%b", ep, ef0, ef1); end
      if (ef0) fe0 = fe0 + 1; if (ef1) fe1 = fe1 + 1;
    end
    if (n0 != n1) mism = mism + 1;
    $display("NF_LAT %s cycles %0d r_v %0d/%0d fault_eps %0d/%0d max_shift %0d go_to_rv_max %0d/%0d mismatches %0d fault_mis %0d seed %0d",
             (mism==0 && fmis==0 && n0>0) ? "PASS" : "FAIL", cyc, n0, n1, fe0, fe1, maxsh, lat0, lat1, mism, fmis, seed);
    $finish;
  end
endmodule
