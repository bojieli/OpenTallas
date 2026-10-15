`timescale 1ns/1ps
module tb_dsfd_vm_static_group128;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [31:0] rv=0,wv=0;reg [447:0] rr=0,wr=0;reg [255:0] rt=0,wt=0;
 reg [127:0] wm=0;reg [4095:0] wd=0;
 wire [31:0] ov,cv;wire [4095:0] od;wire [255:0] ot,ct;wire [287:0] ca;wire [127:0] cm;wire [1:0] fault;
 dsfd_vm_static_slice128 u(.ck_rscatter(ck),.ck_wscatter(ck),.ck_bank({32{ck}}),.rst_n(rn),
 .rq_v(rv),.rq_row(rr),.rq_tag(rt),.wq_v(wv),.wq_row(wr),.wq_mask(wm),.wq_data(wd),.wq_tag(wt),
 .rs_v(ov),.rs_data(od),.rs_tag(ot),.commit_v(cv),.commit_addr(ca),.commit_mask(cm),.commit_tag(ct),.fault(fault));
 reg [127:0] gold[0:16383];
 reg [31:0] prv[0:2],pwv[0:2];reg [447:0] pr[0:2],pw[0:2];
 reg [255:0] prt[0:2],pwt[0:2];reg [127:0] pm[0:2];reg [4095:0] pd[0:2];
 reg [31:0] expected_v=0,next_v,ecv;reg [4095:0] expected_d,next_d;
 reg [255:0] expected_t,next_t,ect;reg [287:0] eca;reg [127:0] ecm;
 reg [5:0] relv=0;reg [3:0] relg[0:5];
 wire [15:0] gv;wire [2047:0] gd;wire [3:0] gg;wire gf;
 `ifdef OT_VM_GROUP_MUT_EARLY_RELEASE
 wire release_v=relv[4];wire [3:0] release_group=relg[4];
`else
 wire release_v=relv[5];wire [3:0] release_group=relg[5];
`endif
 dsfd_vm_static_return u_return(.ck(ck),.rst_n(rn),.i_v(ov),.i_tag(ot),.i_data(od),
 .release_v(release_v),.release_group(release_group),.release_mask(16'hffff),.o_v(gv),.o_data(gd),.o_group(gg),.fault(gf));
 reg [2047:0] gexpect[0:2],ngd;reg [2:0] gev=0;reg [3:0] geg[0:2];reg [3:0] ngg;
 integer groups=0;
 integer bad=0,reads=0,writes=0;integer row,b;integer cycles=0;
 always @(posedge ck)begin
  cycles=cycles+1;ngd=0;ngg=0;next_v=0;next_d=0;next_t=0;ecv=0;ect=0;eca=0;ecm=0;
  for(integer q=0;q<32;q=q+1)if(prv[2][q])begin
   row=pr[2][14*q+:14];b=(row%32)^(((row/32)%8)*4);
   ngd[128*prt[2][8*q+:4]+:128]=gold[row];ngg=prt[2][8*q+4+:4];
   next_v[b]=1;next_d[128*b+:128]=gold[row];next_t[8*b+:8]=prt[2][8*q+:8];
  end
  for(integer q=0;q<32;q=q+1)if(pwv[2][q])begin
   row=pw[2][14*q+:14];b=(row%32)^(((row/32)%8)*4);
   ecv[b]=1;ect[8*b+:8]=pwt[2][8*q+:8];eca[9*b+:9]=row/32;ecm[4*b+:4]=pm[2][4*q+:4];
   for(integer w=0;w<4;w=w+1)if(pm[2][4*q+w])gold[row][32*w+:32]=pd[2][128*q+32*w+:32];
  end
  #0.1;
  if(ov!==expected_v || cv!==ecv || fault!=0 || gf!=0)bad=bad+1;
  for(integer q=0;q<32;q=q+1)begin
   if(ov[q])begin reads=reads+1;if(od[128*q+:128]!==expected_d[128*q+:128] ||ot[8*q+:8]!==expected_t[8*q+:8])bad=bad+1;end
   if(cv[q])begin writes=writes+1;if(ct[8*q+:8]!==ect[8*q+:8]||ca[9*q+:9]!==eca[9*q+:9]||cm[4*q+:4]!==ecm[4*q+:4])bad=bad+1;end
  end
  if(gv !== (gev[2]?16'hffff:16'h0000))bad=bad+1;
  if(gv)begin groups=groups+1;if(gd!==gexpect[2]||gg!==geg[2])bad=bad+1;end
  for(integer x=2;x>0;x=x-1)begin gexpect[x]=gexpect[x-1];geg[x]=geg[x-1];end
  gexpect[0]=ngd;geg[0]=ngg;gev={gev[1:0],|prv[2]};
  for(integer x=5;x>0;x=x-1)relg[x]=relg[x-1];
  relg[0]=rt[7:4];relv={relv[4:0],|rv};
  expected_v=next_v;expected_d=next_d;expected_t=next_t;
  for(integer p=2;p>0;p=p-1)begin prv[p]=prv[p-1];pwv[p]=pwv[p-1];pr[p]=pr[p-1];pw[p]=pw[p-1];prt[p]=prt[p-1];pwt[p]=pwt[p-1];pm[p]=pm[p-1];pd[p]=pd[p-1];end
  prv[0]=rv;pwv[0]=wv;pr[0]=rr;pw[0]=wr;prt[0]=rt;pwt[0]=wt;pm[0]=wm;pd[0]=wd;
 end
 task frame(input integer n,input integer do_read);
 integer l,j,rrow,wrow;
 begin
  @(negedge ck);rv=do_read?32'h0f0f0f0f:0;wv='1;
  for(integer k=0;k<32;k=k+1)begin
   l=k%4;j=l*8+k/4;wrow=32*(n%512)+k;rrow=32*((n-7)&511)+k;
   rr[14*j+:14]=rrow;wr[14*j+:14]=wrow;rt[8*j+:8]={4'(n%16),4'(k%16)};wt[8*j+:8]=n*37+k;
   wm[4*j+:4]=do_read?(n+k)%16:15;
   wd[128*j+:128]=do_read?{32'(n),32'(k),32'(n*127+k),32'(n*771+k)}:128'd0;
  end
 end endtask
 initial begin
  for(integer p=0;p<3;p=p+1)begin prv[p]=0;pwv[p]=0;end
  for(integer a=0;a<16384;a=a+1)gold[a]=0;
  #9;rn=1;repeat(5)@(negedge ck);
  for(integer n=0;n<512;n=n+1)frame(n,0);
  for(integer n=512;n<1536;n=n+1)frame(n,1);
  @(negedge ck);rv=0;wv=0;repeat(10)@(negedge ck);
  $display("RESULT reads%0d writes%0d bad%0d cycles%0d",reads,writes,bad,cycles);$display("GROUPS %0d",groups);
  if(bad==0&&reads==16384&&writes==49152&&groups==1024)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
