`timescale 1ns/1ps
module tb_v41_shared_weight_bursts;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,wv=0;wire wrdy;reg[29:0] wa=0;reg[5:0] wl=17;reg[9:0] wt=0;
wire[31:0] wvr;reg[31:0] wrr=0;wire[8191:0] wd;wire[319:0] wtags;wire[159:0] beats;wire fault;
reg[31:0] kv=0,kwe=0;wire[31:0] krdy,kdone,krv;
reg[959:0] ka=0;reg[127:0] kl=0;reg[8191:0] kd=0;wire[8191:0] krdata;
integer sent=0,got=0,expected=0,cycles=0,kstate=0,badledger=0;
reg[31:0] seen[0:255];integer j;
ot_chip_v41x_shared_hbm_model dut(
.clk(clk),.rst_n(rst_n),.kbase(30'd0),.kcount(30'd32768),.wbase(badledger?30'd0:30'd32768),.wcount(30'd32768),
.k_v(kv),.k_rdy(krdy),.k_addr(ka),.k_len(kl),.k_tag(544'b0),.k_we(kwe),.k_data(kd),.k_strb({1024{1'b1}}),.k_done(kdone),
.kr_v(krv),.kr_rdy(32'hffffffff),.kr_data(krdata),
.w_v(wv),.w_rdy(wrdy),.w_addr(wa),.w_len(wl),.w_tag(wt),.wr_v(wvr),.wr_rdy(wrr),.wr_data(wd),.wr_tag(wtags),.wr_beat(beats),.fault(fault));
initial begin
if(!$value$plusargs("BADLEDGER=%d",badledger)) badledger=0;
for(j=0;j<65536;j=j+1) dut.u_mem.mem[j]=256'(j)^256'h123456789abcdef;
for(j=0;j<256;j=j+1) seen[j]=0;
repeat(3) @(negedge clk);rst_n=1;
end
always @(negedge clk) if(rst_n) begin
cycles=cycles+1;
wv=sent<256;wa=30'(32768+sent*32);wt=10'(sent);wl=(sent&1)?9:17;
wrr=((cycles%17)<5)?0:32'hffffffff;
kv=0;kwe=0;kl=0;
if(kstate==0) begin kv[0]=1;kwe[0]=1;kl[3:0]=1;kd[255:0]=256'hfeed1234;end
if(kstate==2) begin kv[0]=1;kl[3:0]=1;end
if(badledger&&cycles==10) begin
if(!fault||wrdy||(|dut.mv)) $fatal(1,"overlap ledger escaped");
$display("SHARED_BURST_BAD_LEDGER_PASS");$finish;end
if(!badledger&&fault) $fatal(1,"shared fault");
if(sent==256&&got==expected&&kstate==4) begin
if(dut.u_mem.st_ref[0]==0) $fatal(1,"no refresh");
$display("SHARED_BURST_PASS bursts=%0d sectors=%0d cycles=%0d Kwrite_read_exact=1",sent,got,cycles);$finish;end
if(cycles>30000) $fatal(1,"timeout sent%0d got%0d expected%0d Kstate%0d",sent,got,expected,kstate);
end
always @(posedge clk) if(rst_n) begin
if(wv&&wrdy) begin sent=sent+1;expected=expected+wl;end
if(kstate==0&&kv[0]&&krdy[0]) kstate=1;
else if(kstate==1&&kdone[0]) kstate=2;
else if(kstate==2&&kv[0]&&krdy[0]) kstate=3;
else if(kstate==3&&krv[0]) begin
if(krdata[255:0]!==256'hfeed1234) $fatal(1,"K read before write visible");kstate=4;end
for(integer p=0;p<32;p=p+1) if(wvr[p]&&wrr[p]) begin
integer tag,beat,sec;reg[255:0] wanted;
tag=int'(wtags[p*10+:10]);beat=int'(beats[p*5+:5]);sec=32768+tag*32+beat;wanted=256'(sec)^256'h123456789abcdef;
if(tag>=256||beat>=((tag&1)?9:17)||seen[tag][beat]||wd[p*256+:256]!==wanted) $fatal(1,"word/sector mismatch %0d %0d",tag,beat);
seen[tag][beat]=1;got=got+1;
end
end
endmodule
