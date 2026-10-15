`timescale 1ns/1ps
module tb_qfd_kv_static;
 parameter integer MUT_MASK=0,EARLY=0;
 localparam HEADS=1;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,epoch_begin=0,issue_v=0,slot=0;reg[1:0]slot_index=0;
 reg[17:0]epoch_pos=0,issue_nout=1,issue_nin=128;reg[1:0]issue_kind=0;
 reg[63:0]kv_we=0;reg[1535:0]kv_waddr=0;reg[2047:0]kv_wdata=0;
 wire idle,drained,wv,ff;wire[10:0]wt;wire[511:0]wd;wire[7:0]fc;
 integer ep=0,errors=0,total=0,nkv=0,k,h,di,j,n;reg[3:0]seen;reg[511:0]expected;
 ot_qfd_su_kv_static_posted #(.ENABLE(1),.HEADS(1),.MUT_MASK(MUT_MASK))dut(
 .clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch_pos(epoch_pos),
 .issue_v(issue_v),.issue_kind(issue_kind),.issue_nout(issue_nout),.issue_nin(issue_nin),
 .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.epoch_idle(idle),.drained(drained),
 .word_v(wv),.word_tag(wt),.word_data(wd),.word_slot(slot),.word_index(slot_index),.fault(ff),.fault_code(fc));
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

 always @(posedge clk)if(rst_n&&wv)begin
  k=wt[2];h=wt[1];di=wt[0]*64;expected=0;
  for(j=0;j<64;j=j+1)expected[8*j+:8]=code(k,h,di+j);
  if(wt[10:3]!=8'h40||h!=0||seen[{wt[2],wt[0]}]||wd!==expected)errors=errors+1;
  seen[{wt[2],wt[0]}]=1;nkv=nkv+1;total=total+1;
 end
 initial begin
 repeat(3)step();rst_n=1;
 for(ep=0;ep<40;ep=ep+1)begin
  if(!idle)$fatal(1,"formatter not idle at compiled epoch boundary");
  seen=0;nkv=0;epoch_pos=ep%4==0?0:ep%4==1?15:ep%4==2?16:8191;
  epoch_begin=1;step();epoch_begin=0;
  if(EARLY!=0)begin slot=1;slot_index=0;step();slot=0;repeat(4)step();
   if(!ff||total!=0)$fatal(1,"early slot not rejected");
   $display("PASS static formatter early unavailable word faults without deferral");$finish;
  end
  send_issue(0,128);writes(1,0,128);
  send_issue(1,64);writes(0,0,64);
  send_issue(2,64);writes(0,64,64);
  repeat(3)step();
  for(n=0;n<4;n=n+1)begin slot=1;slot_index=n;step();end
  slot=0;repeat(6)step();
  if(nkv!=4||seen!=15||ff||!drained)begin $display("frame%0d words%0d seen%h ff%0d fc%h drained%0d",ep,nkv,seen,ff,fc,drained);errors=errors+1;end
 end
 if(errors)$fatal(1,"FAIL static formatter errors%0d",errors);
 $display("PASS static formatter40epochs actualFP8byteencode10240bytes160scheduledwords no credits");$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
