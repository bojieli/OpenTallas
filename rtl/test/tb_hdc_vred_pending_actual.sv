`timescale 1ns/1ps
module tb_hdc_vred_pending_actual #(parameter integer DUTQLA=4,DUTQLM=5);
 localparam integer DELTA=3+(DUTQLM-3)+17*(DUTQLA-3);
 reg clk=0,rst=0,v=0,mx=0,sq=0,last=0;reg[23:0]addr=0;reg[2047:0]x=0;
 always #5 clk=~clk;
 wire aw,bw,ab,bb,af,bf;wire[23:0]aa,ba;wire[31:0]ad,bd;
 ot_hdc_vreduce #(.SW(64),.LV(7)) baseline(clk,rst,v,mx,sq,last,addr,x,aw,aa,ad,ab,af);
 qfd_su_vred_entries64 #(.QLA(DUTQLA),.QLM(DUTQLM)) split(
 .ck_region0(clk),.ck_region1(clk),.ck_region2(clk),.ck_region3(clk),.ck_region4(clk),.ck_region5(clk),.ck_region6(clk),.ck_region7(clk),.ck_tail(clk),.rst_n(rst),
 .v_in(v),.mx_in(mx),.sq_in(sq),.last_in(last),.addr_in(addr),.x_in(x),.o_we(bw),.o_addr(ba),.o_data(bd),.busy(bb),.fault(bf));
 reg[31:0] dataq[0:255];reg[23:0] addrq[0:255];integer cycleq[0:255];integer wi=0,ri=0,cy=0,err=0;
 integer seg,j,l,seed=73,n,words=0,sums=0,maxes=0,squares=0;
 wire fenced,guard_fault;
 wire guard_last = `ifdef OT_VRED_PENDING_MUT 1'b0 `else last `endif;
 ot_hdc_vred_pending_guard #(.CW(19)) guard(clk,rst,v,guard_last,bw,bb,fenced,guard_fault);
 integer pending_test=0,early_hole=0,max_pending=0;
 always @(posedge clk) if(rst) begin
  case({v&&last,bw})
   2'b10:pending_test=pending_test+1;
   2'b01:pending_test=pending_test-1;
  endcase
  if(pending_test>max_pending)max_pending=pending_test;
 end
 always @(negedge clk) if(rst)begin
  if(pending_test>0&&!fenced)$fatal(1,"FALSE_IDLE_PENDING_OUTPUTS %0d",pending_test);
  if(pending_test>0&&!bb)early_hole=early_hole+1;
  if(guard_fault)$fatal(1,"GUARD_ACCOUNTING_FAULT");
 end
 always @(negedge clk) if(rst)begin
  cy=cy+1;
  if(aw)begin dataq[wi]=ad;addrq[wi]=aa;cycleq[wi]=cy;wi=wi+1;end
  if(bw)begin
   if(!bb)begin $display("BUSY_RELEASE_EARLY");err=err+1;end
   if(ri>=wi || bd!==dataq[ri] || ba!==addrq[ri] || cy-cycleq[ri]!=DELTA)begin
    if(err<10)$display("MISMATCH idx=%0d got=%h exp=%h addr=%h/%h delta=%0d",ri,bd,dataq[ri],ba,addrq[ri],cy-cycleq[ri]);err=err+1;
   end
   ri=ri+1;
  end
  if(af||bf)begin $display("UNEXPECTED_FAULT");err=err+1;end
 end
 initial begin
  repeat(4)@(negedge clk);rst=1;
  for(seg=0;seg<120;seg=seg+1)begin
   n=(seg%7)+1;mx=seg%3==1;sq=seg%3==2;
   if(mx)maxes=maxes+1;else sums=sums+1;if(sq)squares=squares+1;
   for(j=0;j<n;j=j+1)begin
    @(negedge clk);v=1;last=j==n-1;addr=24'h18000+seg;
    for(l=0;l<64;l=l+1)begin
     x[l*32+31]=0;x[l*32+23+:8]=124+((l+j)%5);x[l*32+:23]=$random(seed);
    end
    words=words+64;
    if(j%3==1)begin @(negedge clk);v=0;end
   end
   @(negedge clk);v=0;last=0;repeat(2)@(negedge clk);
  end
  repeat(400)@(negedge clk);
  if(wi!=120||ri!=wi||sums!=80||maxes!=40||squares!=40)begin $display("COUNT_FAIL baseline=%0d split=%0d",wi,ri);err=err+1;end
  if(early_hole<1||max_pending<3||pending_test!=0)begin
   $display("GUARD_VACUITY holes=%0d maxpending=%0d remaining=%0d",early_hole,max_pending,pending_test);err=err+1;
  end
  if(err)begin $display("FAIL VRED errors=%0d",err);$fatal(1);end
  $display("PASS pending guard holes=%0d maxpending=%0d",early_hole,max_pending);
  $display("PASS VRED segments=%0d words=%0d sum=%0d max=%0d square=%0d delta=%0d",ri,words,sums,maxes,squares,DELTA);$finish;
 end
endmodule
