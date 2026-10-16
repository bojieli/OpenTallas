`timescale 1ns/1ps
module tb #(parameter integer RLAT=13,parameter integer SEED=0);
 reg ct=0,cs=0,rt=0,rs=0;always #3 ct=~ct;always #4 cs=~cs;
 reg nv=0;reg[83:0]nd=0;reg[14:0]crq=0;reg[2203:0]coll=0;reg[2:0]qstatus=3'b011;
 wire[3:0]av0,av1,wv0,wv1;wire[55:0]ar0,ar1,wr0,wr1;wire[2047:0]wd0,wd1;wire[63:0]wm0,wm1;wire[31:0]wt0,wt1;
 reg[3:0]ev0=0,ev1=0;reg[2047:0]ed0=0,ed1=0;wire[512:0]crs0,crs1,qs0,qs1;wire[511:0]g0,g1;wire f0,f1;
 dsfd_vm_static_xio_ref #(.RLAT(RLAT))refdut(.ck_control_t(ct),.ck_control_s(cs),.ck_x43_t({2{ct}}),.ck_x43_s({2{cs}}),.rss_control_t(rt),.rst_control_s(rs),.rss_x43_t({2{rt}}),.rst_x43_s({2{rs}}),.n_v(nv),.n_d(nd),.a_v(av0),.a_row(ar0),.e_v(ev0),.e_d(ed0),.f_collective(coll),.f_crq(crq),.t_crs(crs0),.w_v(wv0),.w_row(wr0),.w_d(wd0),.w_m(wm0),.w_t(wt0),.t_gather(g0),.f_xgo(11'd0),.qSW(qs0),.qSWs(qstatus),.fault(f0));
 dsfd_vm_static_xio #(.RLAT(RLAT))dut(.ck_control_t(ct),.ck_control_s(cs),.ck_return_t(ct),.rss_return_t(rt),.ck_fault_t(ct),.ck_fault_s(cs),.ck_fault_join_t(ct),.rss_fault_join_t(rt),.rss_fault_t(rt),.rst_fault_s(rs),.ck_x43_t({2{ct}}),.ck_x43_s({2{cs}}),.rss_control_t(rt),.rst_control_s(rs),.rss_x43_t({2{rt}}),.rst_x43_s({2{rs}}),.n_v(nv),.n_d(nd),.a_v(av1),.a_row(ar1),.e_v(ev1),.e_d(ed1),.f_collective(coll),.f_crq(crq),.t_crs(crs1),.w_v(wv1),.w_row(wr1),.w_d(wd1),.w_m(wm1),.w_t(wt1),.t_gather(g1),.f_xgo(11'd0),.qSW(qs1),.qSWs(qstatus),.fault(f1));
 function[511:0]data(input[13:0]row);integer b;begin for(b=0;b<16;b=b+1)data[32*b+:32]=32'h93ab7200^(32'(row)<<2)^32'(b*131);data[1:0]=3;end endfunction
 reg[3:0]pv0[0:RLAT-1],pv1[0:RLAT-1];reg[2047:0]pd0[0:RLAT-1],pd1[0:RLAT-1];
 reg[3:0]avh;reg[55:0]arh;reg[512:0]ch[0:4];reg[512:0]qh[0:3];reg[511:0]gh[0:3];
 integer k,j,cyc=0,scyc=0,requests=0,creads=0,qreads=0,greads=0, faultedge0=-1,faultedge1=-1;reg checking=0,inject=0;
 always @(posedge ct)begin
  pv0[0]<=av0;pv1[0]<=av1;for(k=0;k<4;k=k+1)begin pd0[0][512*k+:512]<=data(ar0[14*k+:14]);pd1[0][512*k+:512]<=data(ar1[14*k+:14]);end
  for(k=1;k<RLAT;k=k+1)begin pv0[k]<=pv0[k-1];pv1[k]<=pv1[k-1];pd0[k]<=pd0[k-1];pd1[k]<=pd1[k-1];end
  ev0<=pv0[RLAT-2];ev1<=pv1[RLAT-2];ed0<=pd0[RLAT-2];ed1<=pd1[RLAT-2];
  #0.1;
  if(checking)begin
   if(pv1[0]!==pv0[2])$fatal(1,"REQUEST DELTA cycle%0d new%h olddelay%h",cyc,pv1[0],pv0[2]);
   for(integer lane=0;lane<4;lane=lane+1)if(pv1[0][lane]&&pd1[0][512*lane+:512]!==pd0[2][512*lane+:512])$fatal(1,"REQUEST ROW DELTA");
   if(crs1[0]!==ch[3][0] || (crs1[0]&&crs1[512:1]!==ch[3][512:1]))$fatal(1,"COLLECTIVE DELTA cycle%0d got%h expected%h",cyc,crs1,ch[3]);
   if({wv1,wr1,wd1,wm1,wt1}!=={wv0,wr0,wd0,wm0,wt0})$fatal(1,"TUPLE tag/row/mask/data mismatch");
   if(inject&&f0&&faultedge0<0)faultedge0=cyc;
   if(inject&&f1&&faultedge1<0)faultedge1=cyc;
   if(!inject&&(f0||f1))$fatal(1,"VALID PROGRAM FAULT cycle%0d old%0b new%0b req%0b ret%0b serial%0b",cyc,f0,f1,dut.req_fault,dut.ret_fault,dut.serial_fault);
   if(av1!=0)requests=requests+1;if(crs1[0])creads=creads+1;
  end
  avh=av0;arh=ar0;for(j=4;j>0;j=j-1)ch[j]=ch[j-1];ch[0]=crs0;cyc=cyc+1;
 end
 always @(posedge cs)begin
  #0.2;
  if(checking)begin
   if(qs1[0]!==qh[2][0]||(qs1[0]&&qs1[512:1]!==qh[2][512:1]))$fatal(1,"QUERY SERIAL DELTA serial%0d got%h expected%h",scyc,qs1,qh[2]);
   // gather valid is carried in the payload ABI; compare only its actual stream-valid event.
   if(dut.go_v!==gh[2][511] || (dut.go_v&&g1[511:1]!==gh[2][510:0]))$fatal(1,"GATHER SERIAL DELTA serial%0d got%h expected%h",scyc,g1,gh[2]);
   if(qs1[0])qreads=qreads+1;if(dut.go_v)greads=greads+1;
  end
  for(j=3;j>0;j=j-1)begin qh[j]=qh[j-1];gh[j]=gh[j-1];end
  qh[0]=qs0;gh[0]={refdut.go_v,g0[511:1]};scyc=scyc+1;
 end
 task waitcore(input integer n);integer x;begin for(x=0;x<n;x=x+1)@(negedge ct);end endtask
 task stream(input bit gather,input[13:0]base,input[4:0]count);begin
  @(negedge ct);nv=1;nd=0;nd[30:28]=4;nd[26]=gather;nd[25:12]=base;nd[11:7]=count;
  @(negedge ct);nv=0;
 end endtask
 initial begin
  avh=0;arh=0;for(k=0;k<RLAT;k=k+1)begin pv0[k]=0;pv1[k]=0;pd0[k]=0;pd1[k]=0;end
  for(k=0;k<5;k=k+1)ch[k]=0;for(k=0;k<4;k=k+1)begin qh[k]=0;gh[k]=0;end
  #95;rt=1;rs=1;waitcore(60);checking=1;
  for(j=0;j<4;j=j+1)coll[551*j+:551]={8'(40+j),512'(100+j),16'(16'h8110+j),14'(777+101*j),1'b1};
  for(integer n=0;n<128;n=n+1)begin @(negedge ct);crq={14'(200+n),1'b1};end
  @(negedge ct);crq=0;waitcore(50+SEED);
  stream(0,14'd1000,5'd31);waitcore(120+SEED);stream(1,14'd2040,5'd31);waitcore(140);
  if(creads!=128||qreads!=32||greads!=32)$fatal(1,"COUNTS C%0d Q%0d G%0d",creads,qreads,greads);
  inject=1;qstatus=0;stream(0,14'd3000,5'd3);waitcore(100);
  if(!f0||!f1)$fatal(1,"FAULT reflection missing old%0b new%0b",f0,f1);
  // Common-epoch warm reset must clear every local root and sticky diagnostic.
  checking=0;nv=0;crq=0;coll=0;qstatus=3'b011;rt=0;rs=0;waitcore(32);
  while(($time%24)!=23)#1;rt=1;rs=1;waitcore(60);inject=0;checking=1;
  for(integer n=0;n<16;n=n+1)begin @(negedge ct);crq={14'(400+n),1'b1};end
  @(negedge ct);crq=0;waitcore(50);
  stream(0,14'd5000,5'd3);waitcore(100);
  if(f0||f1)$fatal(1,"WARM RESET recovery fault old%0b new%0b",f0,f1);
  $display("XIO_PARTITION PASS requests%0d collective%0d query%0d gather%0d deltaRequest2 deltaCollective4 deltaQGcore4 deltaQGserial3 IIunchanged faultreflected oldFaultEdge%0d newFaultEdge%0d",requests,creads,qreads,greads,faultedge0,faultedge1);$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
