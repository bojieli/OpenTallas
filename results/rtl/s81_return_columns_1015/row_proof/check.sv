module check;
  reg clk=0; reg [31:0] rng=32'h2545F491; integer cycle,j,k;
  reg rst; reg [7:0] tid1,tid2; reg last1,last2; reg [6:0] fv1,fv2; reg [103:0] fdx1,fdx2;
  reg [7:0] rv_x; reg [2155:0] rd_x; reg [7:0] rv_xd; reg [2155:0] rd_xd;
  reg [4095:0] hrq1,hrq2,hrq1d,hrq2d; reg [255:0] yb1,yb2; reg [127:0] cs1,cs2; reg [15:0] nf1,nf2; reg hov1,hov2; reg [7:0] hz1,hz2,pf1,pf2;
  wire [7:0] r1_rv, r2_rv; wire [2155:0] r1_rd, r2_rd;
  wire [15:0] r1q0,r1q1,r1q2,r1q3,r2q0,r2q1,r2q2,r2q3,r1h0,r1h1,r1h2,r1h3,r2h0,r2h1,r2h2,r2h3; wire [3:0] r1hr,r2hr;
  ref_row ref1(.clk(clk),.rst_c(rst),.tid(tid1),.last(last1),.fv_local(fv1),.fdx_local(fdx1),.rv_in(rv_x),.rd_in(rd_x),.rv_out(r1_rv),.rd_out(r1_rd),
    .rq0(r1q0),.rq1(r1q1),.rq2(r1q2),.rq3(r1q3),.hs_run_c(r1hr),.hs0(r1h0),.hs1(r1h1),.hs2(r1h2),.hs3(r1h3),.hrq(hrq1),.yb(yb1),.cs(cs1),.nflt(nf1),.hov0(hov1),.hnz_d(hz1),.pflt_d(pf1));
  ref_row ref2(.clk(clk),.rst_c(rst),.tid(tid2),.last(last2),.fv_local(fv2),.fdx_local(fdx2),.rv_in(r1_rv),.rd_in(r1_rd),.rv_out(r2_rv),.rd_out(r2_rd),
    .rq0(r2q0),.rq1(r2q1),.rq2(r2q2),.rq3(r2q3),.hs_run_c(r2hr),.hs0(r2h0),.hs1(r2h1),.hs2(r2h2),.hs3(r2h3),.hrq(hrq2),.yb(yb2),.cs(cs2),.nflt(nf2),.hov0(hov2),.hnz_d(hz2),.pflt_d(pf2));
  localparam integer RBW=1140;
  wire [4*RBW-1:0] b0, b1, b2; wire [7:0] d_rv; wire [2155:0] d_rd;
  wire [15:0] d1q0,d1q1,d1q2,d1q3,d2q0,d2q1,d2q2,d2q3,d1h0,d1h1,d1h2,d1h3,d2h0,d2h1,d2h2,d2h3; wire [3:0] d1hr,d2hr;
  ot_s81_hc_rb_flat2cols #(.S_RT(4)) f2c(.rv(rv_xd),.rd(rd_xd),.rb(b0));
  ot_s81_hc_retrow #(.CHAIN_STEP(6),.READ_STAGE(1)) dut1(.clk(clk),.rst_in(rst),.tid(tid1),.last(last1),.fv(fv1),.fdx(fdx1),.rb_in(b0),.rb_out(b1),
    .rq_q0(d1q0),.rq_q1(d1q1),.rq_q2(d1q2),.rq_q3(d1q3),.hs_run_c(d1hr),.hs_c0(d1h0),.hs_c1(d1h1),.hs_c2(d1h2),.hs_c3(d1h3),
    .hrq(hrq1d),.yb(yb1),.cs(cs1),.nflt(nf1),.hov_d(hov1),.hnz_d(hz1),.pflt_d(pf1));
  ot_s81_hc_retrow #(.CHAIN_STEP(6),.READ_STAGE(1)) dut2(.clk(clk),.rst_in(rst),.tid(tid2),.last(last2),.fv(fv2),.fdx(fdx2),.rb_in(b1),.rb_out(b2),
    .rq_q0(d2q0),.rq_q1(d2q1),.rq_q2(d2q2),.rq_q3(d2q3),.hs_run_c(d2hr),.hs_c0(d2h0),.hs_c1(d2h1),.hs_c2(d2h2),.hs_c3(d2h3),
    .hrq(hrq2d),.yb(yb2),.cs(cs2),.nflt(nf2),.hov_d(hov2),.hnz_d(hz2),.pflt_d(pf2));
  ot_s81_hc_rb_cols2flat #(.S_RT(4)) c2f(.rb(b2),.rv(d_rv),.rd(d_rd));
  reg [7:0] p_rv; reg [2155:0] p_rd; reg [15:0] p1q0,p1q1,p1q2,p1q3,p2q0,p2q1,p2q2,p2q3,p1h0,p1h1,p1h2,p1h3,p2h0,p2h1,p2h2,p2h3; reg [3:0] p1hr,p2hr;
  task automatic rnd(inout reg [31:0] s); begin s=s^(s<<13); s=s^(s>>17); s=s^(s<<5); end endtask
  `define RB(v) for(j=0;j<$bits(v);j=j+1) begin rnd(rng); v[j]=rng[0]; end
  initial begin
    rst=0; rv_x=0; rd_x=0; rv_xd=0; rd_xd=0; hrq1d=0; hrq2d=0;
    for(cycle=0;cycle<3000;cycle=cycle+1) begin
      clk=0; #1;
      rst=(cycle>=6 && !(cycle>=1500 && cycle<1504));
      tid1=8'd3; tid2=8'd5; last1=(cycle<1000); last2=1'b0;
      `RB(fdx1) `RB(fdx2) `RB(hrq1) `RB(hrq2) `RB(yb1) `RB(yb2) `RB(cs1) `RB(cs2) `RB(rd_x)
      nf1=(cycle%211==0)?16'h0100:16'd0; nf2=(cycle%223==0)?16'h0002:16'd0; hz1=(cycle%97==0)?8'h10:8'd0; hz2=0; pf1=0; pf2=(cycle%151==0)?8'h04:8'd0;
      hov1=(cycle%61==0); hov2=(cycle%67==0);
      fv1='0; fv1[3]=(cycle%97==0); fv1[6]=(cycle%83==0); fv1[4]=(cycle%7==0); fv1[5]=(cycle%41==0); fdx1[63 +:8]=cycle%5;
      fv2='0; fv2[3]=(cycle%101==1); fv2[6]=(cycle%89==3); fv2[4]=(cycle%7==2); fv2[5]=(cycle%43==5); fdx2[63 +:8]=(cycle+1)%5;
      rv_x=0; rv_x[4]=(cycle%13==0); rv_x[5]=(cycle%17==0);
      for(j=0;j<4;j=j+1) begin rd_x[4+8*j +:8]=(cycle+j)%5; rd_x[4+32+16*j +:16]=(cycle+j)%640; end
      rd_x[4+96 +:8]=cycle%5;
      p_rv=r2_rv; p_rd=r2_rd;
      p1q0=r1q0;p1q1=r1q1;p1q2=r1q2;p1q3=r1q3;p2q0=r2q0;p2q1=r2q1;p2q2=r2q2;p2q3=r2q3;p1hr=r1hr;p2hr=r2hr;
      p1h0=r1h0;p1h1=r1h1;p1h2=r1h2;p1h3=r1h3;p2h0=r2h0;p2h1=r2h1;p2h2=r2h2;p2h3=r2h3;
      #1; clk=1;
      rv_xd<=rv_x; rd_xd<=rd_x; hrq1d<=hrq1; hrq2d<=hrq2;
      #1;
      if(cycle>16 && !(cycle>=1500 && cycle<1516)) begin
        if(d_rv!==p_rv) $fatal(1,"rv mismatch cycle=%0d",cycle);
        if(d_rd!==p_rd) $fatal(1,"rd mismatch cycle=%0d",cycle);
        if({d1q0,d1q1,d1q2,d1q3,d2q0,d2q1,d2q2,d2q3}!=={p1q0,p1q1,p1q2,p1q3,p2q0,p2q1,p2q2,p2q3}) $fatal(1,"request mismatch cycle=%0d",cycle);
        if({d1hr,d2hr,d1h0,d1h1,d1h2,d1h3,d2h0,d2h1,d2h2,d2h3}!=={p1hr,p2hr,p1h0,p1h1,p1h2,p1h3,p2h0,p2h1,p2h2,p2h3}) $fatal(1,"hs mismatch cycle=%0d",cycle);
      end
    end
    $display("PASS row 3000 cycles two-row chain output and all per-column requests exact one cycle later");
    $finish;
  end
endmodule
