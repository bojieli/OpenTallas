`timescale 1ns/1ps
module tb_provider_top;
 parameter MUT_ROW=0,MUT_QBEAT=0,MUT_ACK=0,MUT_COMMIT=0,MUT_RSP=0,MUT_QRESTART=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg start=0;reg [15:0] epoch=16'h1234;reg [17:0] pos=18'd15;
 wire qrstart,qreq,qready,qv,qdone,qfault;wire [15:0] re,qe;wire [2:0] rc;wire [23:0] a0,a1;wire [5:0] qb;wire [511:0] qd;
 reg reqready=0,rspv=0;reg [15:0] rspe=0;reg [2:0] rspc=0;reg [2047:0] rspd=0;reg outready=0;
 reg [31:0] vm [0:511];integer cycles=0,errors=0,qwords=0;
 reg iv=0;reg [1:0] ik=0;reg [17:0] nin=128;reg [63:0] we=0;reg [1535:0] wa=0;reg [2047:0] wd=0;
 wire fs,fd,fv,fr,ff;wire [10:0] ft;wire [511:0] data;wire [7:0] fc;
 wire bs,rv,rkind,commit,pfault;wire [15:0] rowe;wire [5:0] rowl;wire [17:0] rowp;wire [1023:0] rowd;wire [3:0] acr;
 reg rr=0;reg [3:0] ackv=0,ackk=0;reg [63:0] acke=0;reg [23:0] ackl=0;reg [71:0] ackp=0;
 reg qs=0;wire admit,allfault;
 ot_qfd_native_qkv_provider #(.ENABLE(1)) u_top(
 .clk(clk),.rst_n(rst_n),.epoch_begin(start),.epoch(epoch),.layer(6'd0),.pos(pos),.epoch_ready(fs),
 .kv_issue_accepted(iv),.kv_issue_kind(ik),.kv_issue_nout(18'd1),.kv_issue_nin(nin),.kv_admit_ready(admit),.kv_we(we),.kv_waddr(wa),.kv_wdata(wd),.formatter_emitted(fd),
 .row_v(rv),.row_ready(rr),.row_kind(rkind),.row_epoch(rowe),.row_layer(rowl),.row_pos(rowp),.row_data(rowd),
 .store_ack_v(ackv),.store_ack_kind(ackk),.store_ack_epoch(acke),.store_ack_layer(ackl),.store_ack_pos(ackp),.store_ack_credit(acr),.kv_committed(commit),
 .q_start(qs),.qr_vm_committed(1'b1),.q_base(24'd13696),.q_start_ready(qrstart),
 .vm_req_v(qreq),.vm_req_ready(reqready),.vm_req_epoch(re),.vm_req_chunk(rc),.vm_req_a0(a0),.vm_req_a1(a1),
 .vm_rsp_v(rspv),.vm_rsp_epoch(rspe),.vm_rsp_chunk(rspc),.vm_rsp_data(rspd),.q_v(qv),.q_ready(outready),.q_beat(qb),.q_data(qd),.q_epoch(qe),.q_emitted_done(qdone),.fault(allfault));
 assign ff=allfault;assign pfault=allfault;assign qfault=allfault;
 reg [7:0] landing [0:3][0:255];integer due[0:3][0:1];integer rowcount=0,ackcount=0,early=0;
 integer reqdue=-1;reg [15:0] reqepoch;reg [2:0] reqchunk;integer reqaddr=0;
 function automatic [7:0] bytecode(input integer k,input integer d);integer v;begin v=(k*91+d)%254;if(v>=127)v=v+1;bytecode=v;end endfunction
 function automatic [31:0] f32(input [7:0] b);reg [3:0] e;reg [2:0] m;begin e=b[6:3];m=b[2:0];if(e!=0)f32={b[7],8'(e+120),m,20'd0};else if(m[2])f32={b[7],8'd120,m[1:0],21'd0};else if(m[1])f32={b[7],8'd119,m[0],22'd0};else if(m[0])f32={b[7],8'd118,23'd0};else f32={b[7],31'd0};end endfunction
 integer j,q,k,d,l;
 always @(negedge clk)if(rst_n)begin
  reqready=cycles%4!=0;outready=cycles%7!=0;rr=cycles%5!=0;rspv=0;ackv=0;
  if(reqdue==cycles)begin
   rspv=1;rspe=reqepoch^(MUT_RSP!=0?16'd1:16'd0);rspc=reqchunk;
   for(j=0;j<64;j=j+1)rspd[32*j+:32]=vm[reqaddr-13696+j];reqdue=-1;
  end
  for(q=0;q<4;q=q+1)for(k=0;k<2;k=k+1)if(due[q][k]==cycles)begin
   ackv[q]=1;ackk[q]=k;acke[16*q+:16]=epoch^(MUT_ACK!=0&&q==3?16'd1:16'd0);ackl[6*q+:6]=0;ackp[18*q+:18]=pos;due[q][k]=-1;
  end
 end
 always @(posedge clk)if(rst_n)begin
  cycles=cycles+1;
  if(qreq&&reqready)begin
   if(a1!=a0+1||re!=epoch||a0!=13696+rc*64||reqdue!=-1)errors=errors+1;
   reqaddr=a0;reqepoch=re;reqchunk=rc;reqdue=cycles+9;
  end
  if(qv&&outready)begin
   if(qb!=qwords||qe!=epoch)errors=errors+1;
   for(j=0;j<16;j=j+1)if(qd[32*j+:32]!==vm[qwords*16+j])errors=errors+1;qwords=qwords+1;
  end
  if(rv&&rr)begin
   if(rowe!=epoch||rowl!=0||rowp!=pos||rkind!=rowcount)errors=errors+1;
   for(q=0;q<4;q=q+1)begin
    // These are actual backing-state writes, using provider row data only.
    for(j=0;j<128;j=j+1)landing[q][rkind*128+j]=rowd[8*j+:8];
    due[q][rkind]=cycles+11+q*7+(q==3?59:0);
   end
   rowcount=rowcount+1;
  end
  if(|ackv)ackcount=ackcount+$countones(ackv);
  if(commit&&ackcount<8)early=early+1;
  if(cycles>1000)begin $display("PROVIDER_FAIL bounded protocol did not complete");$finish;end
 end
 task step;begin @(negedge clk);end endtask
 task issue(input integer op,input integer n);begin ik=op;nin=n;wait(admit);step();iv=1;step();iv=0;end endtask
 task write64(input integer kind,input integer base);begin
  we=64'hffffffffffffffff;
  for(l=0;l<64;l=l+1)begin
   d=base+l;wa[24*l+:24]=(kind==0)?((pos/16)*128+d)*16+pos%16:1048576+pos*128+d;wd[32*l+:32]=f32(bytecode(kind,d));
  end
  step();we=0;
 end endtask
 initial begin
  for(j=0;j<512;j=j+1)vm[j]=32'h3f000000+j*12345;
  for(q=0;q<4;q=q+1)begin for(j=0;j<256;j=j+1)landing[q][j]=8'haa;for(k=0;k<2;k=k+1)due[q][k]=-1;end
  repeat(3)step();rst_n=1;step();start=1;step();start=0;repeat(3)step();wait(qrstart);qs=1;step();qs=0;
  issue(0,128);write64(1,0);write64(1,64);issue(1,64);write64(0,0);issue(2,64);write64(0,64);
  if(MUT_RSP!=0)begin wait(qfault);repeat(4)step();if(qwords==0)$display("PROVIDER_Q_REJECT_PASS stale response no output");else $display("PROVIDER_Q_REJECT_FAIL");$finish;end
  wait(qwords==32);wait(ackcount==8);repeat(6)step();
  for(q=0;q<4;q=q+1)for(k=0;k<2;k=k+1)for(j=0;j<128;j=j+1)if(landing[q][k*128+j]!==bytecode(k,j))errors=errors+1;
  if(MUT_QRESTART!=0)begin qs=1;step();qs=0;repeat(2)step();if(allfault)$display("PROVIDER_Q_RESTART_REJECT_PASS duplicate epoch");else $display("PROVIDER_Q_RESTART_REJECT_FAIL");$finish;end
  if(MUT_ACK!=0)begin if(pfault&&!commit)$display("PROVIDER_ACK_REJECT_PASS stale epoch no release");else $display("PROVIDER_ACK_REJECT_FAIL");end
  else if(errors==0&&commit&&!ff&&!pfault&&!qfault&&early==0)$display("PROVIDER_PASS Q32 KV2 four-quadrant backing writes1024bytes ACK8 cycles%0d",cycles);
  else $display("PROVIDER_FAIL data_errors%0d early%0d commit%0d ff%0d pf%0d qf%0d",errors,early,commit,ff,pfault,qfault);
  $finish;
 end
endmodule
