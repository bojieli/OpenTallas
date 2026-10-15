`timescale 1ns/1ps
`ifndef OT_BANK_DUT
`define OT_BANK_DUT dsfd_vm_static_bank128
`endif
`ifndef OT_BANK_LEAF
`define OT_BANK_LEAF u
`endif
module tb_dsfd_vm_static_bank128;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg rv=0,wv=0;reg [8:0] ra=0,wa=0;reg [7:0] rt=0,wt=0;
 reg [127:0] wd=0;reg [3:0] wm=0;
 wire orv,cv;wire [127:0] rd;wire [7:0] ort,ct;wire [8:0] ca;wire [3:0] cm;
 `OT_BANK_DUT u(.ck(ck),.rst_n(rn),.i_rv(rv),.i_ra(ra),.i_rt(rt),.i_wv(wv),.i_wa(wa),
 .i_wd(wd),.i_wm(wm),.i_wt(wt),.o_rv(orv),.o_rd(rd),.o_rt(ort),.o_commit(cv),.o_ca(ca),.o_cm(cm),.o_ct(ct));
 reg [127:0] gold[0:511];
 reg [127:0] expected[0:2];reg [7:0] tags[0:2];reg [2:0] vq=0;
 reg [8:0] expected_wa;reg [7:0] expected_wt;reg [3:0] expected_wm;reg expected_wv=0;
 integer cyc=0,bad=0,reads=0,writes=0;
 // Reference advances at the actual macro edge, proving read-before-write.
 always @(posedge ck)begin
  cyc=cyc+1;
  if(`OT_BANK_LEAF.rvq)begin expected[1]=gold[`OT_BANK_LEAF.raq];tags[1]=`OT_BANK_LEAF.rtq;end
  if(`OT_BANK_LEAF.wvq)for(integer w=0;w<4;w=w+1)if(`OT_BANK_LEAF.wmq[w])gold[`OT_BANK_LEAF.waq][32*w+:32]=`OT_BANK_LEAF.wdq[32*w+:32];
  expected_wv=`OT_BANK_LEAF.wvq;expected_wa=`OT_BANK_LEAF.waq;expected_wt=`OT_BANK_LEAF.wtq;expected_wm=`OT_BANK_LEAF.wmq;
  #0.1;
  if(orv!=vq[0])bad=bad+1;
  if(orv)begin if(rd!==expected[0] || ort!==tags[0])bad=bad+1;reads=reads+1;end
  if(cv!=expected_wv)bad=bad+1;
  if(cv)begin if(ca!==expected_wa || ct!==expected_wt || cm!==expected_wm)bad=bad+1;writes=writes+1;end
  vq[0]=`OT_BANK_LEAF.rdue;expected[0]=expected[1];tags[0]=tags[1];
 end
 initial begin
  for(integer a=0;a<512;a=a+1)gold[a]=0;
  #9;rn=1;repeat(4)@(negedge ck);
  for(integer a=0;a<512;a=a+1)begin @(negedge ck);wv=1;wa=a;wm=15;wd=0;wt=a;end
  // Every edge has both a read and a masked write; includes same-address cases.
  for(integer n=0;n<20000;n=n+1)begin
   @(negedge ck);rv=1;wv=1;ra=(n*37)%512;wa=(n%3==0)?ra:(n*101)%512;
   rt=n;wt=n*7;wm=n%16;wd={32'(n),32'(n*3),32'(n*7),32'(n*11)};
  end
  @(negedge ck);rv=0;wv=0;repeat(5)@(negedge ck);
  $display("RESULT reads%0d writes%0d bad%0d",reads,writes,bad);
  if(bad==0 && reads==20000 && writes==20512)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
