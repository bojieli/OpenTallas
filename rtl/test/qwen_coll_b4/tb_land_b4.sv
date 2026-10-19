`timescale 1ns/1ps
// The expected prologue is the fixed four-write/two-ready release contract
// independently derived in the reference lane bench, not an observed ready.
module b4_land_case #(parameter integer W=150, ORDER=0, PH=0)(
 input wire cs,input wire[31:0] es,output integer errors,checks,output wire flt);
 localparam integer G=16,R0=ORDER?9:25,HREG=2,RREG=2,L=3,RPIPE=1;
 localparam integer K=((L-1-((R0+RREG)-(G+HREG)))%8+8)%8;
 reg cd=0;reg[31:0]ed=0;reg en=0,rs=0;reg[W-1:0]src=0;
 generate if(PH==0)begin:g_phase0
  initial forever #5 cd=~cd;
 end else begin:g_phase
  initial begin #(PH);forever #5 cd=~cd;end
 end endgenerate
 always @(posedge cd)ed<=ed+1;
 function automatic[W-1:0]word_of(input integer e);
  integer b;
  for(b=0;b<W;b=b+1)word_of[b]=((e*40503+b*7321)>>(b%23))&1;
  word_of[31:0]=e;
 endfunction
 always @(posedge cs)begin
  src<=word_of(es);en<=(es>=G&&es<300)||(es>=G+320);
 end
 always @(posedge cd)rs<=(ed>=R0&&ed<300)||(ed>=R0+320);
 wire[W-1:0]o;
 ot_coll_b4_land_gated #(.W(W),.FIRST(1)) u_l(.ckf(cs),.ea(en),.i(src),.ck(cd),.rs(rs),.k(3'(K)),.o(o),.fault(flt));
 integer epoch_add,first_ready,ready_set,warm_set,first_output,te;
 integer first0=-1,first1=-1;real full_time;reg[W-1:0]expected;
 initial begin errors=0;checks=0;end
 always @(negedge cd)begin
  te=ed-1-L-RPIPE;expected=(te>=G+HREG)?word_of(te):{W{1'b0}};
  epoch_add=(ed-1>300)?320:0;
  full_time=(G+HREG+epoch_add)*10.0+10.0+30.0;
  first_ready=$rtoi($floor((full_time-PH)/10.0))+1;
  if(first_ready<R0+epoch_add+RREG+1)first_ready=R0+epoch_add+RREG+1;
  ready_set=first_ready+1;warm_set=R0+epoch_add+RREG+((K==0)?8:K);
  first_output=((ready_set>warm_set)?ready_set:warm_set)+2;
  if((ed-1>300&&ed-1<R0+320)||ed-1<first_output)expected=0;
  if(ed>0)begin
   checks=checks+1;
   if(o!==expected || flt)begin
    errors=errors+1;
    if(errors<4)$display("B4_LAND_MISMATCH %m W%0d ORDER%0d PH%0d K%0d ed%0d first%0d actualID%0d expectedID%0d flt%b",W,ORDER,PH,K,ed,first_output,o[31:0],expected[31:0],flt);
   end
   if(expected!=0)begin
    if(epoch_add==0&&first0<0)first0=ed-1;
    if(epoch_add!=0&&first1<0)first1=ed-1;
   end
  end
 end
 final $display("B4_LAND_AGE W%0d ORDER%0d PH%0d K%0d totalreceiverage4 addedovercapture3 first0%0d first1%0d checks%0d errors%0d",W,ORDER,PH,K,first0,first1,checks,errors);
endmodule
module tb_land_b4;
 reg cs=0;reg[31:0]es=0;always #5 cs=~cs;always @(posedge cs)es<=es+1;
 integer e[0:15],n[0:15];wire[15:0]f;
 for(genvar i=0;i<16;i=i+1)begin:g
  localparam integer W=(i%4==0)?150:(i%4==1)?152:(i%4==2)?154:139;
  b4_land_case #(.W(W),.ORDER((i/4)%2),.PH(2*(i/8))) u(cs,es,e[i],n[i],f[i]);
 end
 initial begin
  #5999;
  begin integer err,chk;err=0;chk=0;
   for(integer j=0;j<16;j=j+1)begin err+=e[j];chk+=n[j];end
   if(err || |f || chk<9000)$fatal(1,"B4_LAND FAIL errors%0d checks%0d faults%h",err,chk,f);
   $display("B4_LAND PASS cases16 twoBootOrders repeatReset widths150/152/154/139 phases0/0.2T totalreceiverage4 addedcapture3 checks%0d",chk);
  end
  $finish;
 end
endmodule
