`timescale 1ns/1ps
module tb_pv_so_ingress_hden #(parameter integer HEADER_DEN=1);
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0;
 reg cv=0,pv=0,pp=0,dv=0,launch=0;reg[19:0]owner=20'h92345,po,do_;reg[7:0]se=8'h31,so=8'h67,dj;
 reg[1:0]quarter;reg[512:0]pd;reg[511:0]par;reg[2:0]pr;reg[15:0]dm;
 wire qv,ready,done,fault;wire[511:0]qd;wire[11:0]fc;
 dsdv_pv_so_ingress_hden #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_owner(owner),.cfg_position(21'd777),.cfg_se_jid(se),.cfg_so_jid(so),
 .pv_v(pv),.pv_quarter(quarter),.pv_d(pd),.param_v(pp),.param_row(pr),.param_owner(po),.param_position((mut==6)?21'd778:21'd777),.param_d(par),
 .launch(launch),.q_v(qv),.q_d(qd),.ready(ready),.done(done),.fault(fault),.fault_code(fc));
 wire gqv,gr,gd,gf;wire[511:0]gqd;wire[11:0]gfc;
 dsdv_pv_so_ingress #(.ENABLE(1),.HEADER_DEN(HEADER_DEN)) gold(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_owner(owner),.cfg_position(21'd777),.cfg_se_jid(se),.cfg_so_jid(so),
 .pv_v(pv),.pv_quarter(quarter),.pv_d(pd),.param_v(pp),.param_row(pr),.param_owner(po),.param_position((mut==6)?21'd778:21'd777),.param_d(par),
 .den_v(1'b0),.den_mask(16'd0),.den_owner(20'd0),.den_jid(8'd0),.launch(launch),.q_v(gqv),.q_d(gqd),.ready(gr),.done(gd),.fault(gf),.fault_code(gfc));
 integer miter_checks=0;always @(negedge clk)if(rst_n)begin miter_checks=miter_checks+1;if({qv,ready,done,fault,fc}!={gqv,gr,gd,gf,gfc} || (qv&&qd!==gqd))$fatal(1,"HEADER_DEN_MITER");end

 function automatic[31:0]val(input integer h,d);val=32'h3f000000^(32'(h)<<17)^32'(d*101);endfunction
 function automatic[511:0]param(input integer r);for(integer l=0;l<16;l=l+1)param[32*l+:32]=32'h40000000^32'(r*1000+l);endfunction
 function automatic[511:0]hdr(input bit op,input integer h);
 reg[511:0]x;begin x=0;x[511:508]=9;x[503]=1;x[502:495]=owner[7:0];x[479:459]=777;x[491:480]=op?32:5;x[458:449]=owner[17:8];x[0]=!op;x[4:1]=5;x[12:5]=so;x[13]=op;if(op)x[29:14]=16'd1<<h;hdr=x;end endfunction
 reg[32:0]jcmd=0;wire[1:0]jdn;wire[514:0]core_q;
 ot_s81_svc_job u_real_job_gate(.ck(clk),.rs_n(rst_n),.j_cmd(jcmd),.j_dn(jdn),.q({2'd0,qd,qv}),.core_q(core_q),.ad(1026'd0),.xd(514'd0),.od(514'd0));
 integer n=0,checks=0,job=0,mut=0,cyc=0,first=-1,last=-1;
 integer edge_n=0,launch_edge=-1;
 always @(posedge clk)begin edge_n=edge_n+1;if(launch)launch_edge=edge_n;end
 reg[511:0]expect_;integer h,r,dim;
 always @(negedge clk)begin
  cyc=cyc+1;
  if(qv)begin
   if(core_q!=={2'd0,qd,1'b1} || jdn[1])$fatal(1,"PVSO_REAL_JOB_GATE_REJECTED");
   if(first<0)begin first=cyc;if(edge_n-launch_edge!=2)$fatal(1,"PVSO_LAUNCH_AGE %0d",edge_n-launch_edge);end last=cyc;
   if(n==0)expect_=hdr(0,0);
   else if(n<=5)expect_=param(n-1);
   else begin h=(n-6)/33;r=(n-6)%33;
    if(r==0)expect_=hdr(1,h);
    else for(integer l=0;l<16;l=l+1)expect_[32*l+:32]=val(h,16*(r-1)+l);
   end
   if(qd!==expect_)$fatal(1,"PVSO_MISMATCH word%0d got%h exp%h",n,qd,expect_);
   n=n+1;checks=checks+1;
  end
 end
 task tick;@(negedge clk);endtask
 task fill;
 integer t,b,w,l;begin
  for(t=0;t<16;t=t+1)for(b=0;b<8;b=b+1)begin
   tick();pv=1;quarter=2'(t/4);pd=0;pd[512]=1;pd[98]=1;pd[97:94]=4'(t);pd[93:92]=2'(t/4);pd[91:72]=owner;pd[119:99]=777;pd[71:64]=8'(b);pd[120]=1;pd[128:121]=(HEADER_DEN!=0 && mut==3)?se+1:se;
   if(HEADER_DEN!=0 && mut==8 && t==9)pd[120]=0;
   if(mut==1 && t==12 && b==0)pd[91:72]=owner^20'h40000;
   if(mut==5 && t==12 && b==0)pd[119:99]=778;
   if(mut==7 && t==12 && b==0)pd[0]=1;
   for(w=1;w<=4;w=w+1)begin
    tick();pv=1;pd=0;
    for(l=0;l<16;l=l+1)pd[32*l+:32]=val(l,32*t+8*(w-1)+b);
   end
  end
  tick();pv=0;
 end endtask
 initial begin
  if($value$plusargs("mut=%d",mut));
  repeat(4)tick();rst_n=1;repeat(5)tick();
  for(job=0;job<2;job=job+1)begin
   tick();cv=1;jcmd={1'b1,24'((17<<7)|1),owner[7:0]};tick();cv=0;jcmd=0;
   for(integer p=0;p<5;p=p+1)begin tick();pp=1;pr=3'(p);po=owner;par=param(p);if(mut==2 && p==4)po=owner^1;end
   tick();pp=0;dv=1;dm=16'hffff;do_=owner;dj=(mut==3)?se+1:se;
   tick();dv=0;
   if(mut==4)begin tick();launch=1;tick();launch=0;end
   fill();repeat(4)tick();
   if(mut!=0)begin if(!fault)$fatal(1,"PVSO_NEGATIVE_NOT_CAUGHT %0d",mut);$display("PVSO_CAUGHT mut=%0d code=%h",mut,fc);$finish;end
   if(!ready || fault)$fatal(1,"PVSO_NOT_READY %h",fc);
   n=0;first=-1;tick();launch=1;tick();launch=0;
   wait(done);repeat(3)tick();
   if(n!=534 || last-first!=533 || fault)$fatal(1,"PVSO_COUNT n%0d span%0d fc%h",n,last-first,fc);
   $display("PVSO_JOB %0d words%0d span%0d exact8192FP32",job,n,last-first);
   owner=owner+20'h40001;se=se+1;so=so+1;repeat(3)tick();
  end
  $display("PVSO_PASS jobs2 checks%0d miter%0d",checks,miter_checks);$finish;
 end
 initial begin #20000;$fatal(1,"PVSO_TIMEOUT");end
endmodule
