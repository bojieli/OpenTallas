`timescale 1ns/1ps
module tb_dsfd_vm_static512wide;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [31:0] rv=0,wv=0;reg [447:0] rr=0,wr=0;reg [255:0] rt=0,wt=0;
 reg [511:0] wm=0;reg [16383:0] wd=0;
 wire [127:0] cv;wire [511:0] cm;wire [1151:0] ca;wire [1023:0] ct;
 reg [511:0] gold[0:16383];
 reg [31:0] prv[0:2],pwv[0:2];reg [447:0] pr[0:2],pw[0:2];
 reg [255:0] prt[0:2],pwt[0:2];reg [511:0] pm[0:2];reg [16383:0] pd[0:2];
 reg [31:0] ecv;
 reg [255:0] ect;reg [287:0] eca;reg [511:0] ecm;
 reg [5:0] relv=0;reg [2:0] relg[0:5];
 wire [127:0] gv;wire [16383:0] gd;wire [11:0] gg;wire [11:0] gf;
 dsfd_vm_static512 #(.NROW(32)) u(.ck_rscatter({4{ck}}),.ck_wscatter({4{ck}}),.ck_return({4{ck}}),
 .ck_bank({128{ck}}),.rst_n(rn),.rq_v(rv),.rq_row(rr),.rq_tag(rt),
 .wq_v(wv),.wq_row(wr),.wq_mask(wm),.wq_data(wd),.wq_tag(wt),
 .release_v(relv[5]),.release_group(relg[5]),.release_mask(32'hffffffff),
 .group_v(gv),.group_data(gd),.group_id(gg),.commit_v(cv),.commit_addr(ca),.commit_mask(cm),.commit_tag(ct),.fault(gf));
 reg [16383:0] gexpect[0:2],ngd;reg [2:0] gev=0;reg [2:0] geg[0:2];reg [2:0] ngg;
 integer groups=0;
 integer bad=0,reads=0,writes=0;integer row,b;integer cycles=0;
 always @(posedge ck)begin
  cycles=cycles+1;ngd=0;ngg=0;ecv=0;ect=0;eca=0;ecm=0;
  for(integer q=0;q<32;q=q+1)if(prv[2][q])begin
   row=pr[2][14*q+:14];b=(row%32)^(((row/32)%8)*4);
   ngd[512*prt[2][8*q+:5]+:512]=gold[row];ngg=prt[2][8*q+5+:3];
   reads=reads+1;
  end
  for(integer q=0;q<32;q=q+1)if(pwv[2][q])begin
   row=pw[2][14*q+:14];b=(row%32)^(((row/32)%8)*4);
   ecv[b]=1;ect[8*b+:8]=pwt[2][8*q+:8];eca[9*b+:9]=row/32;ecm[16*b+:16]=pm[2][16*q+:16];writes=writes+1;
   for(integer w=0;w<16;w=w+1)if(pm[2][16*q+w])gold[row][32*w+:32]=pd[2][512*q+32*w+:32];
  end
  #0.1;
  if(gf!=0 ||cv!=={4{ecv}})bad=bad+1;
  for(integer a=0;a<4;a=a+1)for(integer z=0;z<32;z=z+1)if(cv[32*a+z])begin
   if(ca[288*a+9*z+:9]!==eca[9*z+:9] ||ct[256*a+8*z+:8]!==ect[8*z+:8]||cm[128*a+4*z+:4]!==ecm[16*z+4*a+:4])bad=bad+1;
  end
  if(gv !== (gev[2]?128'hffffffffffffffffffffffffffffffff:128'd0))bad=bad+1;
  if(gv)begin groups=groups+1;if(gd!==gexpect[2]||gg!=={4{geg[2]}})bad=bad+1;end
  for(integer x=2;x>0;x=x-1)begin gexpect[x]=gexpect[x-1];geg[x]=geg[x-1];end
  gexpect[0]=ngd;geg[0]=ngg;gev={gev[1:0],|prv[2]};
  for(integer x=5;x>0;x=x-1)relg[x]=relg[x-1];
  relg[0]=rt[7:5];relv={relv[4:0],|rv};
  for(integer p=2;p>0;p=p-1)begin prv[p]=prv[p-1];pwv[p]=pwv[p-1];pr[p]=pr[p-1];pw[p]=pw[p-1];prt[p]=prt[p-1];pwt[p]=pwt[p-1];pm[p]=pm[p-1];pd[p]=pd[p-1];end
  prv[0]=rv;pwv[0]=wv;pr[0]=rr;pw[0]=wr;prt[0]=rt;pwt[0]=wt;pm[0]=wm;pd[0]=wd;
 end
 task frame(input integer n,input integer do_read);
 integer l,j,rrow,wrow;
 begin
  @(negedge ck);rv=do_read?32'hffffffff:0;wv='1;
  for(integer k=0;k<32;k=k+1)begin
   l=k%4;j=l*8+k/4;wrow=32*(n%512)+k;rrow=32*((n-7)&511)+k;
   rr[14*j+:14]=rrow;wr[14*j+:14]=wrow;rt[8*j+:8]={3'(n%8),5'(k)};wt[8*j+:8]=n*37+k;
   wm[16*j+:16]=do_read?16'((n*997+k*613)%65536):16'hffff;
   for(integer z=0;z<16;z=z+1)wd[512*j+32*z+:32]=do_read?32'(n*771+k*39+z*437):32'd0;
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
  if(bad==0&&groups==1024&&reads==32768&&writes==49152)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
