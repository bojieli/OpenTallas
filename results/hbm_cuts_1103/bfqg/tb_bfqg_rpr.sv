`timescale 1ns/1ps
// DIE-HBM-61/CUTS 11-03: lockstep bench, ot_hgi_sm_xload_cl2_bfqg RPR 16 (kept rp_sel copies) == gold (pin d34578d6f
// module, prefixed gold_), 0 edge shift on rwq every edge; all clock pins on one clock (the one-root RF1 build).
// Random writes/masks/reads incl. multi-tile r_ce and periodic resets. RPMUT != 0 must FAIL.
module tb_bfqg_rpr;
  parameter integer CYC=40000, RPR=16, RPMUT=0;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0, wce=0; reg [1023:0] c_d=0; reg [7:0] mhi=0, mlo=0, r_ce=0; reg [6:0] wa=0, r_a=0;
  wire [255:0] a_q, b_q;
  gold_ot_hgi_sm_xload_cl2_bfqg g(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_ctrl(clk),
    .clk_m0(clk),.clk_m1(clk),.clk_m2(clk),.clk_m3(clk),.clk_m4(clk),.clk_m5(clk),.clk_m6(clk),.clk_m7(clk),
    .clk_l0(clk),.clk_l1(clk),.clk_l2(clk),.clk_l3(clk),.clk_l4(clk),.clk_l5(clk),.clk_l6(clk),.clk_l7(clk),
    .rst_n(rst_n),.c_d(c_d),.wce(wce),.mhi0(mhi[0]),.mhi1(mhi[1]),.mhi2(mhi[2]),.mhi3(mhi[3]),.mhi4(mhi[4]),.mhi5(mhi[5]),
    .mhi6(mhi[6]),.mhi7(mhi[7]),.mlo0(mlo[0]),.mlo1(mlo[1]),.mlo2(mlo[2]),.mlo3(mlo[3]),.mlo4(mlo[4]),.mlo5(mlo[5]),
    .mlo6(mlo[6]),.mlo7(mlo[7]),.wa(wa),.r_ce(r_ce),.r_a(r_a),.rwq(a_q));
  ot_hgi_sm_xload_cl2_bfqg #(.RPR(RPR),.RPMUT(RPMUT)) d(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_ctrl(clk),
    .clk_m0(clk),.clk_m1(clk),.clk_m2(clk),.clk_m3(clk),.clk_m4(clk),.clk_m5(clk),.clk_m6(clk),.clk_m7(clk),
    .clk_l0(clk),.clk_l1(clk),.clk_l2(clk),.clk_l3(clk),.clk_l4(clk),.clk_l5(clk),.clk_l6(clk),.clk_l7(clk),
    .rst_n(rst_n),.c_d(c_d),.wce(wce),.mhi0(mhi[0]),.mhi1(mhi[1]),.mhi2(mhi[2]),.mhi3(mhi[3]),.mhi4(mhi[4]),.mhi5(mhi[5]),
    .mhi6(mhi[6]),.mhi7(mhi[7]),.mlo0(mlo[0]),.mlo1(mlo[1]),.mlo2(mlo[2]),.mlo3(mlo[3]),.mlo4(mlo[4]),.mlo5(mlo[5]),
    .mlo6(mlo[6]),.mlo7(mlo[7]),.wa(wa),.r_ce(r_ce),.r_a(r_a),.rwq(b_q));
  integer cyc, ph, bad=0, nc=0, nnz=0, i;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      ph=cyc%4000; rst_n=(ph>=6);
      wce=($urandom%3)==0; wa=$urandom; r_a=$urandom; mhi=$urandom; mlo=$urandom;
      r_ce=(($urandom%4)==0)?8'($urandom):(8'd1<<($urandom%8));
      for(i=0;i<32;i=i+1) c_d[i*32+:32]=$urandom;
      if(cyc>12) begin nc=nc+1; nnz=nnz+(a_q!=0);
        if(a_q!==b_q) begin bad=bad+1; if(bad<=5) $display("RPR_EQ_MISMATCH cyc=%0d",cyc); end end
    end
    if(bad==0) $display("RPR_EQ PASS RPR=%0d compared=%0d nonzero_rwq=%0d",RPR,nc,nnz);
    else $display("RPR_EQ FAIL RPR=%0d RPMUT=%0d mismatches=%0d of %0d",RPR,RPMUT,bad,nc);
    $finish;
  end
endmodule
