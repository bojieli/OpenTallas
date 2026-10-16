`timescale 1ns/1ps
module tb_host_program_target;
 parameter integer MUT=0,NEG=0;
 integer negative=NEG;initial begin if($value$plusargs("negative=%d",negative))begin end end
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,rv=0;reg[527:0]rd=0;wire rcr,nv,beg,wv,wd,seal,av,rxf;
 wire[527:0]nd;wire[15:0]ep,aep;wire[3:0]target,atarget,dwc;wire[10:0]pwc;wire[9:0]wa;wire[63:0]data,adigest;
 wire[142:0]pr;wire ready,fault,fv;wire[63:0]digest,footer;wire[15:0]pe;wire[3:0]rt;
 qkd_host_program_rx_target rx(.ck(ck),.rst_n(rst_n),.rx_v(rv),.rx_d(rd),.rx_cr(rcr),.normal_v(nv),.normal_d(nd),.normal_cr(1'b0),.begin_image(beg),.image_epoch(ep),.image_target(target),.auth_target(atarget),.pw_count(pwc),.dw_count(dwc),.word_v(wv),.word_desc(wd),.word_addr(wa),.word_data(data),.seal(seal),.auth_v(av),.auth_epoch(aep),.auth_digest(adigest),.fault(rxf));
 qkd_host_program_loader_target #(.MUT(MUT))loader(.ck(ck),.rst_n(rst_n),.begin_image(beg),.image_epoch(ep),.image_target(target),.auth_target(atarget),.replay_target(rt),.pw_count(pwc),.dw_count(dwc),.word_v(wv),.word_desc(wd),.word_addr(wa),.word_data(data),.seal(seal),.auth_v(av),.auth_epoch(aep),.auth_digest(adigest),.execution_active(1'b0),.pr(pr),.program_ready(ready),.fault(fault),.digest(digest),.program_epoch(pe),.authorized_footer_valid(fv),.authorized_footer(footer));
 integer expected_target=0,expected_words=0,seen=0,seen_desc=0,images=0;reg[63:0]gold_digest;
 function automatic[63:0]word_value(input integer t,input integer a);word_value=64'h8123456700000000^(64'(t)<<40)^64'(a*17+3);endfunction
 always @(posedge ck)if(rst_n)begin
  if(pr[74])begin
   if(negative!=0)$fatal(1,"NEGATIVE_REPLAY");
   if(rt!=4'(expected_target)||pr[73:64]!=10'(seen)||pr[63:0]!=word_value(expected_target,seen))$fatal(1,"REPLAY_EXACT t%0d addr%0d seen%0d data%h",rt,pr[73:64],seen,pr[63:0]);
   seen=seen+1;
  end
  if(pr[142])begin
   if(expected_target!=0||pr[141:139]!=0||pr[138:75]!=64'h1234)$fatal(1,"DESC_LEAK");seen_desc=seen_desc+1;
  end
  if(fv&&rt!=0)$fatal(1,"CONFIG_ISA_FOOTER");
 end
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task frame(input reg[511:0]d);begin rv=1;rd={4'd8,12'd0,d};tick(1);rv=0;tick(2);end endtask
 task image(input integer t,input integer n,input integer d);reg[511:0]f;begin
  expected_target=t;expected_words=n;seen=0;seen_desc=0;gold_digest=64'h51484f5354505247^64'(t);
  f=0;f[7:0]=1;f[23:8]=16'(100+t);f[34:24]=11'(n);f[38:35]=4'(d);f[42:39]=4'(t);frame(f);tick(3);
  if(negative==2||negative==3)begin tick(8);if(!(fault||rxf))$fatal(1,"EXPECTED_LENGTH_OR_TARGET_FAULT");$display("PASS rejected actual invalid target/count");$finish;end
  for(integer a=0;a<n;a++)begin
   f=0;f[7:0]=2;f[18:9]=10'(a);f[82:19]=word_value(t,a);frame(f);
   gold_digest={gold_digest[56:0],gold_digest[63:57]}^word_value(t,a)^64'(a);
  end
  if(d!=0)begin f=0;f[7:0]=2;f[8]=1;f[82:19]=64'h1234;frame(f);gold_digest={gold_digest[56:0],gold_digest[63:57]}^64'h1234^64'd1024;end
  f=3;frame(f);tick(3);f=0;f[7:0]=4;f[23:8]=16'(100+t);f[87:24]=gold_digest;f[91:88]=4'(negative==1?t+1:t);frame(f);
  if(negative==1)begin tick(20);if(!fault)$fatal(1,"EXPECTED_AUTH_TARGET_FAULT");$display("PASS rejected cross-target auth");$finish;end
  tick(n+d+20);if(!ready||fault||rxf||seen!=n||seen_desc!=d||digest!=gold_digest||pe!=16'(100+t))$fatal(1,"IMAGE_NOT_EXACT t%0d seen%0d want%0d f%0d rx%0d",t,seen,n,fault,rxf);
  if(t==0&&(!fv||footer!=word_value(0,1023)))$fatal(1,"ISA_FOOTER");images=images+1;
 end endtask
 initial begin
  tick(3);rst_n=1;tick(10);
  if(negative==1)image(3,4,0);else if(negative==2)image(3,5,0);else if(negative==3)image(10,4,0);
  else begin image(1,327,0);image(2,181,0);image(3,4,0);image(4,192,0);image(5,192,0);for(integer t=6;t<=9;t++)image(t,1024,0);image(0,1024,1);end
  $display("PASS actual_HOST_target images%0d all10targets real4SRAM exactreplay targetboundauth footerISAonly",images);$finish;
 end
 initial begin #1000000;$fatal(1,"TIMEOUT");end
endmodule
