`timescale 1ns/1ps
module tb_native;
 parameter HEADS=1,MUT_LANE=0,MUT_TAG=0,MUT_MASK=0,FAULTCASE=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,epoch_begin=0,issue_v=0;reg [17:0] epoch_pos=0;
 reg [1:0] issue_kind=0;reg [17:0] issue_nout=HEADS,issue_nin=128;
 reg [63:0] kv_we=0;reg [1535:0] kv_waddr=0;reg [2047:0] kv_wdata=0;
 wire ready,drained,wv,wr,ff;wire [10:0] wt;wire [511:0] wd;wire [7:0] fc;
 reg qv=0;reg [5:0] qb=0;reg [511:0] qd=0;wire qr,xv,cf;wire [10:0] xt;wire [511:0] xd;
 reg cr=0;reg [127:0] returns=0;
 ot_qfd_su_kv_native_posted #(.ENABLE(1),.HEADS(HEADS),.MUT_LANE(MUT_LANE),.MUT_TAG(MUT_TAG),.MUT_MASK(MUT_MASK)) u(
 .clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch_pos(epoch_pos),.issue_v(issue_v),.issue_kind(issue_kind),.issue_nout(issue_nout),.issue_nin(issue_nin),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.epoch_ready(ready),.drained(drained),.word_v(wv),.word_ready(wr),.word_tag(wt),.word_data(wd),.fault(ff),.fault_code(fc));
 ot_qfd_su_kv_native_credit #(.ENABLE(1)) c(.clk(clk),.rst_n(rst_n),.kv_v(wv),.kv_tag(wt),.kv_data(wd),.kv_ready(wr),.q_v(qv),.q_beat(qb),.q_data(qd),.q_ready(qr),.credit_return(cr),.x_v(xv),.x_tag(xt),.x_data(xd),.fault(cf));
 integer errors=0,total=0,nkv=0,nq=0,ep=0,cyc=0;
 reg [7:0] tags=0;reg [31:0] qtags=0;
 function automatic [7:0] code(input integer k,input integer h,input integer d);
  integer x;begin x=(k*91+h*37+d+ep*17)%254;if(x>=127)x=x+1;code=x;end
 endfunction
 function automatic [31:0] decode(input [7:0] b);
  reg [3:0] e;reg [2:0] m;begin e=b[6:3];m=b[2:0];
   if(e!=0)decode={b[7],8'(e+120),m,20'd0};
   else if(m[2])decode={b[7],8'd120,m[1:0],21'd0};
   else if(m[1])decode={b[7],8'd119,m[0],22'd0};
   else if(m[0])decode={b[7],8'd118,23'd0};
   else decode={b[7],31'd0};
  end
 endfunction
 function automatic [23:0] address(input integer k,input integer h,input integer d);
  begin if(k==0)address=((h*512+epoch_pos/16)*128+d)*16+epoch_pos%16;
   else address=HEADS*1048576+(h*8192+epoch_pos)*128+d;end
 endfunction
 integer j,t,k,h,di,l,perm,qsent;reg [511:0] expected;
 always @(negedge clk)begin cr=returns[0];end
 always @(posedge clk)if(rst_n)begin
  cyc=cyc+1;returns=returns>>1;
  if(cyc%1000==0)$display("PROGRESS cycles%0d ep%0d ready%0d active%0d sent%h issued%h seen%0d ff%0d fc%h nq%0d nkv%0d credits%0d",cyc,ep,ready,u.active,u.sent,u.issued,$countones(u.seen),ff,fc,nq,nkv,c.credits);
  if(cyc>20000)begin $display("NATIVE_KV_FAIL no retirement within 40 epochs * (40 words + 80 credit latency + 16 producer stages) * 3 slack");$finish;end
  if(xv)begin
   // A consumed wire word returns exactly one credit after arbitrary latency.
   returns[79]=1;
   total=total+1;
   if(xt[10:8]==2)begin
    k=xt[2];h=xt[1];di=xt[0]*64;expected=0;
    for(j=0;j<64;j=j+1)expected[8*j+:8]=code(k,h,di+j);
    if(h>=HEADS||tags[xt[2:0]]||xd!==expected)errors=errors+1;
    tags[xt[2:0]]=1;nkv=nkv+1;
   end else if(xt[10:8]==1)begin
    if(xt[5:0]>=32||qtags[xt[5:0]]||xd!=={16{32'(ep*1000+xt[5:0])}})errors=errors+1;
    qtags[xt[5:0]]=1;nq=nq+1;
   end else errors=errors+1;
  end
 end
 task step;begin @(negedge clk);end endtask
 task send_issue(input integer op,input integer n);begin
  issue_kind=op;issue_nin=n;issue_v=1;step();issue_v=0;
 end endtask
 task writes(input integer kind_,input integer base_,input integer length_);integer hh,dd,ll,pp;begin
  for(hh=0;hh<HEADS;hh=hh+1)for(dd=base_;dd<base_+length_;dd=dd+64)begin
   kv_we=64'hffffffffffffffff;kv_waddr=0;kv_wdata=0;
   for(ll=0;ll<64;ll=ll+1)begin
    pp=(ll*17)%64;
    kv_waddr[24*ll+:24]=address(kind_,hh,dd+pp);
    kv_wdata[32*ll+:32]=decode(code(kind_,hh,dd+pp));
   end
   step();kv_we=0;
  end
 end endtask
 initial begin
  repeat(3)step();rst_n=1;
  if(FAULTCASE!=0)begin
   epoch_begin=1;step();epoch_begin=0;send_issue(0,128);
   kv_we=1;kv_waddr[23:0]=address(1,0,0);kv_wdata[31:0]=decode(8'h38);
   case(FAULTCASE)1:kv_waddr[23:0]=kv_waddr[23:0]+128;2:kv_wdata[31:0]=32'h3f812345;3:begin step();end
    4:begin kv_we=0;issue_v=1;issue_nout=HEADS+1;end endcase
   step();kv_we=0;issue_v=0;repeat(6)step();
   if(ff&&total==0)$display("NATIVE_KV_REJECT_PASS case=%0d code=%h",FAULTCASE,fc);
   else $display("NATIVE_KV_REJECT_FAIL case=%0d ff=%0d words=%0d",FAULTCASE,ff,total);
   $finish;
  end
  for(ep=0;ep<40;ep=ep+1)begin
   wait(ready);step();tags=0;qtags=0;nkv=0;nq=0;
   case(ep%4)0:epoch_pos=0;1:epoch_pos=15;2:epoch_pos=16;3:epoch_pos=8191;endcase
   epoch_begin=1;step();epoch_begin=0;
   send_issue(0,128);writes(1,0,128);
   send_issue(1,64);writes(0,0,64);
   send_issue(2,64);writes(0,64,64);
   qsent=0;
   while(qsent<32)begin
    qv=(cyc%5!=0);qb=qsent;qd={16{32'(ep*1000+qsent)}};
    @(posedge clk);if(qv&&qr)qsent=qsent+1;step();
   end
   qv=0;
   wait(drained);repeat(4)step();
   if(nkv!=4*HEADS||nq!=32||ff||cf)begin errors=errors+1;$display("epoch%0d nkv%0d nq%0d ff%0d fc%h cf%0d",ep,nkv,nq,ff,fc,cf);end
   repeat(2)step();
  end
  if(errors==0)$display("NATIVE_KV_PASS heads=%0d epochs=40 uniqueKVbytes=%0d words=%0d cycles=%0d",HEADS,40*256*HEADS,total,cyc);
  else $display("NATIVE_KV_FAIL data_errors=%0d",errors);
  $finish;
 end
endmodule
