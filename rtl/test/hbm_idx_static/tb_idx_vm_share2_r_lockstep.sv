`timescale 1ns/1ps
// HBM-NSFIX/SHARE2 10-18: LOCKSTEP of the pin-registered two-client share ot_hbm_idx_vm_share2_static_r (REG 1, the
// hardened bank-pair leaf ot_hbm_idx_vm_share2_leaf_r x4) against the proven zero-latency share
// ot_hbm_idx_vm_share2_static (REG 0; face bench run_vm_share2.sh) shifted by the new latency. Two identical 8-bank
// read groups of real ot_vms_bank_static banks (24 SRAM macros each), preloaded with the same rows; the same request
// stream (owner per bank per edge: idle / A / B, and in the second half rare double bookings) drives both shares on the
// same edge. Every edge: dut.vm_rq sampled by the bank == ref.vm_rq one edge earlier (+1), dut.a_rr/b_rr == ref.a_rr/b_rr two edges
// earlier (+2 round trip: each client captures n+10 instead of n+8), dut.fault == ref.fault one edge earlier (+1).
module tb_idx_vm_share2_r_lockstep;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [135:0] a_rq=0,b_rq=0;
 wire [135:0] r_vmrq,d_vmrq;wire [2055:0] r_vmrr,d_vmrr,r_a,r_b,d_a,d_b;wire r_f,d_f;
 reg [8*281-1:0] wr=0;wire [143:0] r_st,d_st;
 ot_hbm_idx_vm_share2_static #(.REG(0)) ref_s(.clk_pair({4{clk}}),.rst_n(rst_n),.a_rq(a_rq),.b_rq(b_rq),.vm_rq(r_vmrq),.vm_rr(r_vmrr),.a_rr(r_a),.b_rr(r_b),.fault(r_f));
 ot_hbm_idx_vm_share2_static_r #(.MUT(MUT)) dut_s(.clk_pair({4{clk}}),.rst_n(rst_n),.a_rq(a_rq),.b_rq(b_rq),.vm_rq(d_vmrq),.vm_rr(d_vmrr),.a_rr(d_a),.b_rr(d_b),.fault(d_f));
 for(genvar g=0;g<2;g=g+1)begin:grp
  wire [135:0] rq=(g==0)?r_vmrq:d_vmrq;wire [2055:0] rr;
  if(g==0)begin:gr assign r_vmrr=rr;end else begin:gd assign d_vmrr=rr;end
  for(genvar b=0;b<8;b=b+1)begin:bank
   wire done,dqd,kqd,xd,x2d;wire [275:0] eg;wire[265:0] pr;wire [17:0] st;
   ot_vms_bank_static #(.RG(1),.WG(1)) mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
    .rslot_v(rq[b*17+16]),.rslot(1'b0),.wslot_v(wr[b*281+280]),.wslot(3'd0),
    .rq(rq[b*17+:17]),.rr(rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(done),
    .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),
    .xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(st));
   if(g==0)begin:sr assign r_st[b*18+:18]=st;end else begin:sd assign d_st[b*18+:18]=st;end
  end
 end
 function automatic [255:0] pattern(input integer row,input integer b);
  for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h9e3779b9*(row*64+b*8+k+1);
 endfunction
 reg [2055:0] h_a[0:3],h_b[0:3];reg h_f[0:3];
 integer e_rq=0,e_rr=0,e_f=0,e_st=0,shown=0;
 integer checked=0,errors=0,na=0,nb=0,dbl=0,first_err=-1,cyc=0;bit checking=0;
 // the bank request is what the bank SAMPLES: compare 1 ns before each edge (a_rq changes at the negedge)
 reg [135:0] p_rq=0;
 always @(negedge clk)begin
  #4;
  // AD3-HBM-SHARE2 10-18: bank request data is don't-care under valid 0 (the bank samples it only under valid); the valid
  // bit of every bank and the data of every VALID request are compared exactly.
  if(checking)begin for(integer g=0;g<8;g=g+1)if(d_vmrq[g*17+16]!==p_rq[g*17+16]||(p_rq[g*17+16]&&d_vmrq[g*17+:16]!==p_rq[g*17+:16]))begin errors++;e_rq++;if(first_err<0)first_err=cyc;end end
  p_rq=r_vmrq;
 end
 always @(posedge clk)begin
  cyc=cyc+1;
  #1;
  if(checking)begin
   checked++;
   if(d_a!==h_a[1]||d_b!==h_b[1])begin errors++;e_rr++;
    if(shown<6)begin shown++;for(integer b=0;b<8;b=b+1)if(d_a[b*257+:257]!==h_a[1][b*257+:257]||d_b[b*257+:257]!==h_b[1][b*257+:257])
     $display("RR_MISMATCH cyc%0d bank%0d dA_v%b refA_v%b dB_v%b refB_v%b dataA_eq%0d dataB_eq%0d",cyc,b,d_a[b*257+256],h_a[1][b*257+256],d_b[b*257+256],h_b[1][b*257+256],
      d_a[b*257+:256]===h_a[1][b*257+:256],d_b[b*257+:256]===h_b[1][b*257+:256]);end end
   if(d_f!==h_f[0])begin errors++;e_f++;end
   if(r_st!==144'd0||d_st!==144'd0)begin errors++;e_st++;end
   if(errors>0&&first_err<0)first_err=cyc;
   for(integer b=0;b<8;b=b+1)begin na+=int'(r_a[b*257+256]);nb+=int'(r_b[b*257+256]);end
  end
  h_a[1]=h_a[0];h_a[0]=r_a;h_b[1]=h_b[0];h_b[0]=r_b;h_f[0]=r_f;
 end
 initial begin
  for(integer i=0;i<4;i=i+1)begin h_a[i]=0;h_b[i]=0;h_f[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<256;row=row+1)begin
   @(negedge clk);
   for(integer b=0;b<8;b=b+1)wr[b*281+:281]={1'b1,1'(row/128),2'd0,10'(row%128),3'(b),pattern(row,b),8'hff};
  end
  @(negedge clk);wr=0;repeat(12)@(negedge clk);checking=1;
  for(integer c=0;c<2048;c=c+1)begin
   a_rq=0;b_rq=0;
   for(integer b=0;b<8;b=b+1)begin
    integer who;who=(c*7+b*3+(c/13)+(c*c)%5)%3; // 0 idle, 1 A, 2 B, changing per bank per edge
    if(c>=1024&&((c*31+b*17)%97)==0)who=3;     // rare double booking (second half only)
    if(who==1||who==3)a_rq[b*17+:17]={1'b1,1'(c/8),2'd0,10'((c+b*13)%128),3'(b)};
    if(who==2||who==3)b_rq[b*17+:17]={1'b1,1'(c/5),2'd0,10'((c*3+b)%128),3'(b)};
    if(who==3)dbl++;
   end
   @(negedge clk);
  end
  a_rq=0;b_rq=0;repeat(14)@(negedge clk);checking=0;
  $display("IDX_VM_SHARE2R MUT%0d checked%0d a_reads%0d b_reads%0d dbl%0d errors%0d (rq%0d rr%0d f%0d st%0d) first_err%0d ref_fault%0d dut_fault%0d leaves4 SRAMs48",
   MUT,checked,na,nb,dbl,errors,e_rq,e_rr,e_f,e_st,first_err,r_f,d_f);
  if(errors||na<3000||nb<3000||dbl<4||!r_f||!d_f)$fatal(1,"registered share2 lockstep");
  $finish;
 end
endmodule
