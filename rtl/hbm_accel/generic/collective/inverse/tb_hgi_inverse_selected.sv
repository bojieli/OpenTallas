`timescale 1ns/1ps
module tb_hgi_inverse_selected;
 parameter MUT=0,ENABLETEST=1; reg clk=0;always #1 clk=~clk;reg rst_n=0,go=0;
 reg[11:0]k;reg[7:0]group;reg span=1;reg[31:0]ver=32'h1234,nowver=32'h1234;
 wire rq,rr;wire[10:0]ri;reg[10:0]rspidx;reg rsp=0;reg[31:0]rdata;reg rf=0;wire done,fault,ready;
 reg[3:0]lv=0;wire[3:0]lr;reg[27:0]lo;reg[47:0]ls;reg[63:0]lt;
 wire[3:0]rv,filtered,err;wire[43:0]ridx;wire[63:0]rt;
 ot_hgi_inverse_selected #(.ENABLE(ENABLETEST),.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.go(go),.retire(1'b0),.k(k),.group(group),
  .span_valid(span),.source_version(ver),.source_version_now(nowver),.r_req_v(rq),.r_req_rdy(1'b1),.r_req_index(ri),
  .r_rsp_v(rsp),.r_rsp_index(rspidx),.r_rsp_data(rdata),.r_rsp_fault(rf),.r_rsp_rdy(rr),.build_done(done),.fault(fault),.ready(ready),
  .look_v(lv),.look_rdy(lr),.look_owner(lo),.look_slot(ls),.look_tag(lt),.ret_v(rv),.ret_filtered(filtered),.ret_fault(err),.ret_index(ridx),.ret_tag(rt));
 integer sent[0:16383];integer cycle=0;always @(posedge clk)cycle=cycle+1;integer eo[0:16383],es[0:16383];integer R[0:2047],cnt[0:95],gold[0:95][0:2047];integer ticks=0,requested=0,retired=0,bad=0;
 reg bad_rsp=0;reg expect_error=0;reg pending=0;reg[10:0]reqidx;integer waitn;
 always @(negedge clk)begin
  ticks=ticks+1;rsp=0;
  if(pending)begin if(waitn==0)begin rsp=1;rspidx=bad_rsp?(reqidx^1):reqidx;rdata=R[reqidx];pending=0;end else waitn=waitn-1;end
  if(rq)begin if(pending)$fatal(1,"more than one R request");pending=1;reqidx=ri;waitn=(ri%3);end
  for(integer l=0;l<4;l=l+1)if(rv[l])begin
   integer tag,owner,slot;tag=rt[16*l+:16];owner=eo[tag];slot=es[tag];
   if(expect_error ? !err[l] : (err[l]||filtered[l]!=(slot>=cnt[owner])||(!filtered[l]&&ridx[11*l+:11]!=gold[owner][slot])))begin
    if(bad<8)$display("BAD lane%0d tag%0d owner%0d slot%0d idx%0d filt%0d err%0d want%0d",l,tag,owner,slot,ridx[11*l+:11],filtered[l],err[l],gold[owner][slot]);bad=bad+1;
   end
   if(cycle-sent[tag]+1!=14)$fatal(1,"lookup latency %0d expected14",cycle-sent[tag]+1);retired=retired+1;
  end
 end
 genvar il;generate for(il=0;il<4;il=il+1)begin:maskcheck
 initial for(integer w=0;w<128;w=w+1)begin
  dut.lanes[il].owners.m[0].ram.mem[w]={32{8'ha5}};
  dut.lanes[il].map.m[0].ram.mem[w]={32{8'ha5}};
  dut.lanes[il].map.m[1].ram.mem[w]={32{8'ha5}};
  dut.lanes[il].map.m[2].ram.mem[w]={32{8'ha5}};
 end
 always @(negedge clk)if(done)for(integer w=0;w<128;w=w+1)begin
  if(dut.lanes[il].owners.m[0].ram.mem[w][255:234]!==22'h296969||
     dut.lanes[il].map.m[0].ram.mem[w][255:234]!==22'h296969||
     dut.lanes[il].map.m[1].ram.mem[w][255:234]!==22'h296969||
     dut.lanes[il].map.m[2].ram.mem[w][255:234]!==22'h296969)$fatal(1,"packed SRAM clobbered unmasked bits");
 end
 end endgenerate
 task reset;begin @(negedge clk);rst_n=0;lv=0;go=0;pending=0;repeat(3)@(negedge clk);rst_n=1;repeat(2)@(negedge clk);end endtask
 task build(input integer K,G,shape,malformed);integer owner,start;begin
  reset();bad_rsp=malformed==3;rf=malformed==5;k=K;group=G;requested=0;retired=0;
  for(integer o=0;o<96;o=o+1)cnt[o]=0;
  for(integer i=0;i<K;i=i+1)begin
   owner=(shape==2)?G-1:(shape==1)?3%G:((i*17+i/7)%G);
   R[i]=cnt[owner]*G+owner;gold[owner][cnt[owner]]=i;cnt[owner]=cnt[owner]+1;
  end
  if(malformed==1)R[K/2]=32'hffffffff;
  if(malformed==2)R[K/2]=R[K/2-1];
  @(negedge clk);go=1;@(negedge clk);go=0;start=ticks;
  if(malformed==4)fork begin wait(dut.lanes[0].owners.wpin);@(negedge clk);dut.lanes[0].owners.wmaskbar=dut.lanes[0].owners.wmaskbar^1;end join_none
  while(!done&&!fault&&ticks-start<150000)@(negedge clk);
  if(malformed)begin if(!fault)$fatal(1,"malformed not rejected");$display("FAULT malformed%0d PASS",malformed);end
  else begin if(!ready)$fatal(1,"build failed K%0d G%0d st%0d idx%0d owner%0d slot%0d fault%0d",K,G,dut.st,dut.idx,dut.owner,dut.slot,fault);$display("BUILD K%0d G%0d shape%0d cycles%0d",K,G,shape,ticks-start);end
  bad_rsp=0;rf=0;
 end endtask
 task lookup;integer o,j;begin
  o=0;j=0;
  while(o<group)begin
   @(posedge clk);#0.2;lv=0;
   for(integer lane=0;lane<4;lane=lane+1)if(o<group)begin
    lv[lane]=1;lo[7*lane+:7]=o;ls[12*lane+:12]=j;lt[16*lane+:16]=requested;
    sent[requested]=cycle+1;eo[requested]=o;es[requested]=j;requested=requested+1;
    j=j+1;if(j>cnt[o])begin j=0;o=o+1;end
   end
  end
  @(posedge clk);#0.2;lv=0;repeat(30)@(negedge clk);
  if(retired!=requested)$fatal(1,"retired%0d requested%0d",retired,requested);
 end endtask
 task one_lookup(input integer error_expected);begin
  expect_error=(error_expected!=0);requested=0;retired=0;
  @(posedge clk);#0.2;lv=15;lo=(error_expected==2)?{4{7'd127}}:28'd0;ls=0;
  for(integer lane=0;lane<4;lane=lane+1)begin lt[16*lane+:16]=lane;sent[lane]=cycle+1;eo[lane]=0;es[lane]=0;end
  requested=4;@(posedge clk);#0.2;lv=0;repeat(30)@(negedge clk);
  if(retired!=4)$fatal(1,"fault test missing responses");
  if(error_expected&&!fault)$fatal(1,"uncorrectable did not fault");expect_error=0;
 end endtask
 task badshape(input integer K,G);begin
  reset();k=K;group=G;@(negedge clk);go=1;@(negedge clk);go=0;repeat(4)@(negedge clk);
  if(!fault||ready||rq)$fatal(1,"bad shape accepted");$display("PASS BAD_SHAPE K%0d G%0d",K,G);
 end endtask
 initial begin
  if(!ENABLETEST)begin reset();k=512;group=96;go=1;repeat(20)@(negedge clk);
   if(rq||ready||done||fault)$fatal(1,"default-off activated");$display("PASS DEFAULT_OFF");$finish;end
  build(512,8,0,0);lookup();
  build(2048,96,1,0);lookup();
  build(2048,96,0,0);lookup();
  build(2048,1,0,0);lookup();
  build(17,4,0,0);lookup();
  build(7,2,0,0);lookup();build(1,96,2,0);lookup();
  build(512,96,0,1);build(17,4,0,2);build(17,4,0,3);build(17,4,0,4);build(17,4,0,5);
  build(17,4,0,0);
  dut.lanes[0].owners.m[0].ram.mem[0][0]=~dut.lanes[0].owners.m[0].ram.mem[0][0];
  dut.lanes[1].owners.m[0].ram.mem[0][0]=~dut.lanes[1].owners.m[0].ram.mem[0][0];
  dut.lanes[2].map.m[0].ram.mem[0][0]=~dut.lanes[2].map.m[0].ram.mem[0][0];
  dut.lanes[3].map.m[0].ram.mem[0][0]=~dut.lanes[3].map.m[0].ram.mem[0][0];
  one_lookup(0);$display("PASS SINGLE_BIT_CORRECTION");
  build(17,4,0,0);
  dut.lanes[0].owners.m[0].ram.mem[0][1:0]=dut.lanes[0].owners.m[0].ram.mem[0][1:0]^2'b11;
  dut.lanes[1].owners.m[0].ram.mem[0][1:0]=dut.lanes[1].owners.m[0].ram.mem[0][1:0]^2'b11;
  dut.lanes[2].map.m[0].ram.mem[0][1:0]=dut.lanes[2].map.m[0].ram.mem[0][1:0]^2'b11;
  dut.lanes[3].map.m[0].ram.mem[0][1:0]=dut.lanes[3].map.m[0].ram.mem[0][1:0]^2'b11;
  one_lookup(1);$display("PASS DOUBLE_BIT_POISON");
  build(17,4,0,0);
  dut.lanes[0].owners.m[0].ram.mem[0][38:0]=dut.lanes[0].owners.m[0].ram.mem[0][77:39];
  dut.lanes[1].owners.m[0].ram.mem[0][38:0]=dut.lanes[1].owners.m[0].ram.mem[0][77:39];
  dut.lanes[2].map.m[0].ram.mem[0][38:0]=dut.lanes[2].map.m[0].ram.mem[0][77:39];
  dut.lanes[3].map.m[0].ram.mem[0][38:0]=dut.lanes[3].map.m[0].ram.mem[0][77:39];
  one_lookup(1);$display("PASS WRONG_RECORD_IDENTITY");
  build(17,4,0,0);one_lookup(2);$display("PASS OWNER_RANGE_FAULT");
  build(17,4,0,0);dut.kbar=dut.kbar^1;@(negedge clk);@(negedge clk);
  if(!fault||ready)$fatal(1,"control complement did not fault");$display("PASS CONTROL_COMPLEMENT");
  build(17,4,0,0);nowver=nowver+1;@(negedge clk);@(negedge clk);
  if(!fault||ready)$fatal(1,"source version did not fault");nowver=ver;$display("PASS SOURCE_VERSION");
  badshape(0,96);badshape(2049,96);badshape(16,3);
  if(bad)$fatal(1,"%0d mismatches",bad);$display("PASS INVERSE_SELECTED");$finish;
 end
endmodule
