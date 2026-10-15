`timescale 1ns/1ps
module tb_dsfd_vm_static_read_router;
 reg ck=0,rst=0;always #0.417 ck=~ck;
 wire[63:0] cds={64{ck}};wire[7:0] cvs={8{ck}};
 reg[16383:0] data=0;reg[127:0] valid=0;
 reg[17:0] ne=0;reg[89:0] ns=0;reg[11:0] ae=0;reg[19:0] me=0;reg[99:0] ms=0;
 wire[9215:0] nd;wire[17:0] nv;wire[2047:0]pd;wire pv;wire[4095:0]xd;wire[7:0]xv;wire[10239:0]md;wire[19:0]mv;wire[7:0]fault;
 dsfd_vm_static_read_router dut(.ck_data(cds),.ck_valid(cvs),.rst_n(rst),.slot_data(data),.slot_valid(valid),.n_expected(ne),.n_slot(ns),.aux_expected(ae),.mx_expected(me),.mx_slot(ms),.n_data(nd),.n_valid(nv),.pq_data(pd),.pq_valid(pv),.x_data(xd),.x_valid(xv),.mx_data(md),.mx_valid(mv),.fault(fault));
 integer mode=0,seed=1,bad=0,cy=0,checks=0,native30=0,mix30=0,su1cross=0;
 reg[17:0]en[0:1000];reg[11:0]ea[0:1000];reg[19:0]em[0:1000];reg[9215:0]edn[0:1000];reg[2047:0]edp[0:1000];reg[4095:0]edx[0:1000];reg[10239:0]edm[0:1000];integer i,j,p,s,l,g,b;
 function[511:0]row(input integer cycle,input integer slot);integer w;begin for(w=0;w<16;w=w+1)row[32*w+:32]=32'(cycle*100003+slot*1709+w*131+seed*7919+19);end endfunction
 initial for(i=0;i<=1000;i=i+1)begin en[i]=0;ea[i]=0;em[i]=0;end
 always @(posedge ck)if(rst)begin
 #0.01;
 if(mode==0)begin
  if(nv!==en[cy]||xv!==ea[cy][11:4]||pv!==ea[cy][0]||mv!==em[cy])begin bad=bad+1;if(bad<8)$display("VALID cy%0d native%h/%h mx%h/%h",cy,nv,en[cy],mv,em[cy]);end
  for(integer q=0;q<18;q=q+1)if(en[cy][q])begin checks=checks+1;if(nd[512*q+:512]!==edn[cy][512*q+:512])begin bad=bad+1;if(bad<8)$display("NATIVE DATA cy%0d q%0d",cy,q);end end
  if(ea[cy][0])for(integer q=0;q<4;q=q+1)begin checks=checks+1;if(pd[512*q+:512]!==edp[cy][512*q+:512])bad=bad+1;end
  for(integer q=0;q<8;q=q+1)if(ea[cy][q+4])begin checks=checks+1;if(xd[512*q+:512]!==edx[cy][512*q+:512])bad=bad+1;end
  for(integer q=0;q<20;q=q+1)if(em[cy][q])begin checks=checks+1;if(md[512*q+:512]!==edm[cy][512*q+:512])begin bad=bad+1;if(bad<8)$display("MIX DATA cy%0d q%0d",cy,q);end end
 end
 end
 task step;begin @(negedge ck);cy=cy+1;ne=0;ns=0;ae=0;me=0;ms=0;valid=0;end endtask
 task expect_rows;begin
 en[cy+1]=ne;ea[cy+1]=ae;em[cy+1]=me;
 for(p=0;p<18;p=p+1)edn[cy+1][512*p+:512]=data[512*ns[5*p+:5]+:512];
 for(p=0;p<4;p=p+1)edp[cy+1][512*p+:512]=data[512*(20+p)+:512];
 for(p=0;p<8;p=p+1)edx[cy+1][512*p+:512]=data[512*(24+p)+:512];
 for(p=0;p<20;p=p+1)edm[cy+1][512*p+:512]=data[512*ms[5*p+:5]+:512];
 end endtask
 initial begin
 if(!$value$plusargs("mode=%d",mode))mode=0;if(!$value$plusargs("seed=%d",seed))seed=1;
 repeat(4)@(negedge ck);rst=1;repeat(5)step;
 for(j=0;j<300;j=j+1)begin
  step;
  for(p=0;p<32;p=p+1)data[512*p+:512]=row(j,p);
  if(j%3==0)begin
   ne=18'h3ffff;ae=12'hfff;native30=native30+1;
   for(p=0;p<16;p=p+1)ns[5*p+:5]=5'(p);ns[80+:5]=16;ns[85+:5]=17;
  end else if(j%3==1)begin
   me=20'hfffff;ne[17:16]=2'b11;ae[11:4]=8'hff;mix30=mix30+1;
   ns[80+:5]=5'(16+j%4);ns[85+:5]=5'(16+(j+1)%4);
   for(p=0;p<20;p=p+1)ms[5*p+:5]={3'(p<16?p/4:5),2'((p+j+seed)%4)};
  end else begin
   ne[1:0]=2'b11;ae=12'hfff;su1cross=su1cross+1;
   ns[0+:5]=5'((j+seed)%4);ns[5+:5]=5'(4+(j+seed)%4);
  end
  for(s=0;s<4;s=s+1)begin
   for(p=0;p<18;p=p+1)if(ne[p])valid[32*s+ns[5*p+:5]]=1;
   for(p=0;p<12;p=p+1)if(ae[p])valid[32*s+20+p]=1;
   for(p=0;p<20;p=p+1)if(me[p])valid[32*s+ms[5*p+:5]]=1;
  end
  if(j==12&&mode==1)valid[0]=0;
  if(j==13&&mode==2)ms[5*16+:5]=4;
  if(j==12&&mode==3)valid[32*2+24]=0;
  expect_rows;
 end
 repeat(5)step;
 if(mode==0)begin
  if(fault||checks!=7400||native30!=100||mix30!=100||su1cross!=100)bad=bad+1;
  $display("READ_ROUTER %s mode0 checks%0d fullnative%0d fullmix%0d su1cross%0d fault%h bad%0d",bad==0?"PASS":"FAIL",checks,native30,mix30,su1cross,fault,bad);
 end else begin
  b=(mode==1?0:mode==2?5:6);
  $display("READ_ROUTER %s mode%0d fault%h expected%h",fault==(8'b1<<b)?"PASS":"FAIL",mode,fault,8'b1<<b);
 end
 $finish;
 end
endmodule
