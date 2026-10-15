`timescale 1ns/1ps
module tb_qkd_program_commit;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,beg=0,auth=0,active=0;reg[15:0]ep=0,ae=0;
 reg[63:0]ad=0;reg[1:0]ce=0;reg[11:0]row=0;reg[1023:0]data=0,mask=0;
 reg dv=0;reg[2:0]da=0;reg[63:0]dd=0;reg df=1;
 wire pv,pf,cv,ready,fault,cap;reg stores_ready=1;reg image_cap=1;wire[9:0]pa;wire[63:0]pd,cd;wire[15:0]cep;
 reg rce=0;reg[5:0]ra=0;wire[1023:0]rd;
 reg[63:0]desc[0:7];integer commits=0;
 qkd_program_pw_observer obs(ce,row,data,mask,pv,pa,pd,pf);
 qkd_program_commit dut(ck,rst_n,active,stores_ready,beg,ep,11'd1024,4'd8,auth,ae,ad,pv,pa,pd,pf,dv,da,dd,df,cv,ready,fault,cap,cep,cd);
 for(genvar b=0;b<2;b=b+1)begin:g_macro
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(ck),.r_ce_in(rce),.r_addr_in(ra),.rd_out(rd[512*b+:512]),
   .w_ce_in(ce[b]),.w_addr_in(row[6*b+:6]),.wd_in(data[512*b+:512]),.w_mask_in(mask[512*b+:512]),
   .rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(18'd0));
 end
 always @(posedge ck)begin if(dv)desc[da]<=dd;end
 always @(negedge ck)if(cv)commits=commits+1;
 function automatic[63:0]word(input integer n);word=(n==1023)?(64'h5850463100000006|({63'd0,image_cap}<<12)):64'hdf983ca8175620ab^(64'(n)*64'h137f85f05522aa13);endfunction
 function automatic[63:0]gold;
  reg[63:0]h;integer n;begin h=64'h51484f5354505247;
   for(n=0;n<1032;n=n+1)h={h[56:0],h[63:57]}^word(n)^{53'd0,1'(n>=1024),10'(n>=1024?n-1024:n)};
   gold=h;end
 endfunction
 task automatic clear;
 begin @(negedge ck);rst_n=0;beg=0;auth=0;ce=0;dv=0;active=0;stores_ready=1;repeat(3)@(negedge ck);rst_n=1;commits=0;end
 endtask
 task automatic arm(input integer mode);
 begin ep=16'h4281;ae=ep;ad=gold();beg=1;@(negedge ck);beg=0;
  if(mode==5)ae=ep+1;auth=1;@(negedge ck);auth=0;end
 endtask
 task automatic pw(input integer n,input integer mode);
 integer addr,bank,slice;begin
  addr=n;if(mode==3&&n==53)addr=54;
  bank=(addr>>3)&1;slice=addr&7;ce=2'b1<<bank;row={6'(addr>>4),6'(addr>>4)};
  data={16{word(n)}};mask=0;mask[512*bank+64*slice+:64]=64'hffffffffffffffff;
  if(mode==4&&n==53)data[512*bank+64*slice]=~data[512*bank+64*slice];
  if(mode==6&&n==53)mask[512*bank+64*slice]=0;
  if(mode==1&&n==53)ce=0;
  @(negedge ck);ce=0;
  if(mode==2&&n==53)begin ce=2'b1<<bank;@(negedge ck);ce=0;end
 end endtask
 task automatic run(input integer mode);
 integer n,s;begin clear();image_cap=(mode!=10);if(mode==9)stores_ready=0;arm(mode);
  for(n=0;n<1024;n=n+1)pw(n,mode);
  for(n=0;n<8;n=n+1)begin
   dv=!(mode==7&&n==7);da=3'(n);dd=word(1024+n);df=!(mode==8&&n==3);
   @(negedge ck);dv=0;
  end
  repeat(2)@(negedge ck);
  if(mode==9)begin
   if(ready||cap||commits)$fatal(1,"storevalid bypass");
   stores_ready=1;repeat(2)@(negedge ck);
  end
  if(mode==0||mode==9||mode==10)begin
   if(!ready||fault||cap!=image_cap||commits!=1||cep!=ep||cd!=gold())$fatal(1,"normal actual writes not committed");
   // Actual macro readback, separately from the write-pin digest observer.
   rce=1;for(n=0;n<64;n=n+1)begin ra=6'(n);@(negedge ck);@(negedge ck);
    for(s=0;s<16;s=s+1)if(rd[64*s+:64]!==word(16*n+s))$fatal(1,"actual macro readback");end
   rce=0;for(n=0;n<8;n=n+1)if(desc[n]!==word(1024+n))$fatal(1,"descriptor readback");
   // BEGIN revokes a previously valid commitment immediately on its edge.
   beg=1;@(negedge ck);beg=0;if(ready||cap)$fatal(1,"stale commitment survived newBEGIN");
   $display("PASS macro_pin_commit 1024PW8DW actual2SRAM readback and epoch/digest");
  end else begin
   if(ready||commits!=0)$fatal(1,"mutant accepted mode%0d",mode);
   if(mode!=7&&!fault)$fatal(1,"mutant failed to fault mode%0d",mode);
   $display("PASS rejected_mutant mode%0d fault%0d commits%0d",mode,fault,commits);
  end
 end endtask
 reg jb=0,ja=0;reg[1:0]jr=0,jf=0,jc=0;reg[31:0]je=0;reg[127:0]jd=0;
 wire jcv,jready,jfault,jcap;wire[15:0]jepoch;wire[63:0]jdigest;
 qkd_program_commit_join joiner(ck,rst_n,jb,ja,active,stores_ready,16'h4281,64'h0123456789abcdef,
  jr,jf,jc,je,jd,jcv,jready,jfault,jcap,jepoch,jdigest);
 task automatic join_test(input integer mismatch);
 begin
  clear();jb=1;jr=3;@(negedge ck);jb=0;ja=1;@(negedge ck);ja=0;
  repeat(2)@(negedge ck);if(jready)$fatal(1,"join accepted stalecopy");
  jr=0;@(negedge ck);jr=1;je={16'h4281,16'h4281};jd={2{64'h0123456789abcdef}};jc=3;
  @(negedge ck);if(jready)$fatal(1,"join skippedcopy");jr=3;
  if(mismatch)jd[64]=~jd[64];repeat(2)@(negedge ck);
  if(mismatch)begin if(!jfault||jready||jcap)$fatal(1,"join wrongcopy accepted");end
  else if(!jready||!jcap||jepoch!=16'h4281||jdigest!=64'h0123456789abcdef)$fatal(1,"join noactualcopies");
  $display("PASS physical_copy_join mismatch%0d",mismatch);
 end endtask
 initial begin for(integer mode=0;mode<11;mode=mode+1)run(mode);join_test(0);join_test(1);$finish;end
endmodule
