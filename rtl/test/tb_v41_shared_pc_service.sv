`timescale 1ns/1ps
module tb_v41_shared_pc_service;
parameter WNUM=3,DEN=5;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;
reg[31:0] v=0,rr=0;wire[31:0] ready,rv;
reg[32*30-1:0] addr=0;
reg[32*17-1:0] tag=0;
wire[32*17-1:0] rt;
wire[8191:0] data;
reg[127:0] lengths=0;
integer next[0:31];integer accepted[0:31];integer received[0:31];
integer mode=0,cycles=0,errors=0,total=0,refsum=0,p,a,owner;
reg[255:0] expected;
ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.MEM_WORDS(8),.MEM_MODE(1),.REFPB(3),
.SHARE_W_NUM(WNUM),.SHARE_DEN(DEN)) dut(
.clk(clk),.rst_n(rst_n),.req_v(v),.req_rdy(ready),.req_addr(addr),.req_len(lengths),.req_tag(tag),
.req_we(32'b0),.req_wdata(8192'b0),.req_wstrb(1024'b0),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_data(data));
function automatic integer pc(input integer s);pc=((s>>2)^(s>>7)^(s>>12))&31;endfunction
initial begin
if (!$value$plusargs("MODE=%d",mode)) mode=0;
for(p=0;p<32;p=p+1) begin next[p]=0;accepted[p]=0;received[p]=0;end
repeat(3) @(negedge clk);rst_n=1;
end
always @(negedge clk) if(rst_n) begin
cycles=cycles+1;
for(p=0;p<32;p=p+1) begin
// Distinct explicit half-regions. Alternating rows cause bank/row conflict.
owner=(mode==1)?0:((mode==2)?1:(next[p]&1));a=owner*32768 + ((next[p]>>1)%16)*128;
while(pc(a)!=p) a=a+1;
addr[p*30+:30]=30'(a);tag[p*17+:17]={1'(owner),16'(a)};lengths[p*4+:4]=1;
v[p]=(cycles<9000);
rr[p]=!((cycles%97)<11); // bounded return backpressure
end
if(cycles==10000) begin
for(p=0;p<32;p=p+1) begin
if(accepted[p]!=received[p]) $fatal(1,"undrained PC %0d accepted%0d received%0d",p,accepted[p],received[p]);
if(WNUM!=0 && mode==0 && (dut.share_w_services[p]==0 || dut.share_k_services[p]==0 || dut.share_both_services[p]==0)) $fatal(1,"missing contention");
refsum=refsum+dut.st_ref[p];total=total+received[p];
end
if(errors || refsum==0) $fatal(1,"errors or no refresh");
$display("SHARED_PC_PASS MODE=%0d W=%0d DEN=%0d sectors=%0d refreshes=%0d pc0W=%0d pc0K=%0d both=%0d",mode,WNUM,DEN,total,refsum,dut.share_w_services[0],dut.share_k_services[0],dut.share_both_services[0]);$finish;
end
end
always @(posedge clk) if(rst_n) begin
for(integer c=0;c<32;c=c+1) begin
if(v[c]&&ready[c]) begin next[c]=next[c]+1;accepted[c]=accepted[c]+1;end
if(rv[c]&&rr[c]) begin
expected=dut.pat(30'(rt[c*17+:16]));
if(data[c*256+:256]!==expected) $fatal(1,"wrongdata PC%0d",c);
received[c]=received[c]+1;
end
end
end
initial begin #200000; $fatal(1,"timeout"); end
endmodule
