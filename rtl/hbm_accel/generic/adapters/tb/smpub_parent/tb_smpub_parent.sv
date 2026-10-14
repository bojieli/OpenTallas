`timescale 1ns/1ps
module tb_smpub_parent;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,pub_v=0;reg [39:0] pub_base=0;reg [31:0] pub_stride=0;
reg [1:0] pub_space=1;reg [19:0] pub_m=128;reg [12:0] pub_q=4;reg [3:0] pub_p=8;reg pub_bf16=0;
reg [31:0] sm_rv=0;reg [383:0] sm_rrow=0;reg [8191:0] sm_rdata=0;reg [1095:0] vmr=0;
wire ar,br,ad,bd,af,bf,av,bv;wire [1351:0] aq,bq;wire [19:0] ai,bi;wire [31:0] ax,bx,ac,bc;
smpub_parent_reference a(.clk(clk),.rst_n(rst_n),.pub_v(pub_v),.pub_rdy(ar),.pub_base(pub_base),.pub_stride(pub_stride),.pub_space(pub_space),.pub_m(pub_m),.pub_q(pub_q),.pub_p(pub_p),.pub_bf16(pub_bf16),.pub_done(ad),.pub_fault(af),.sm_rv(sm_rv),.sm_rrow(sm_rrow),.sm_rdata(sm_rdata),.vmq(aq),.vmr(vmr),.s0_v(av),.s0_idx(ai),.s0_data(ax),.sm_cr(ac));
`ifdef MUTANT
localparam MUT=1;
`else
localparam MUT=0;
`endif
ot_hgi_sm_pub_hier #(.MUT_ROW(MUT)) b(.clk(clk),.rst_n(rst_n),.pub_v(pub_v),.pub_rdy(br),.pub_base(pub_base),.pub_stride(pub_stride),.pub_space(pub_space),.pub_m(pub_m),.pub_q(pub_q),.pub_p(pub_p),.pub_bf16(pub_bf16),.pub_done(bd),.pub_fault(bf),.sm_rv(sm_rv),.sm_rrow(sm_rrow),.sm_rdata(sm_rdata),.vmq(bq),.vmr(vmr),.s0_v(bv),.s0_idx(bi),.s0_data(bx),.sm_cr(bc));
integer cycle=0,packets=0,words=0;
always @(negedge clk) if(rst_n) begin
cycle=cycle+1;
if({ar,ad,af,av,ac} !== {br,bd,bf,bv,bc}) $fatal(1,"control mismatch cycle %0d",cycle);
if(av && {ai,ax} !== {bi,bx}) $fatal(1,"stream mismatch cycle %0d",cycle);
for(integer c=0;c<4;c=c+1) begin
if(aq[c*338+337] !== bq[c*338+337]) $fatal(1,"VM valid mismatch");
if(aq[c*338+337]) begin packets=packets+1;if(aq[c*338 +:338] !== bq[c*338 +:338]) $fatal(1,"VM packet mismatch");end
end
if(av) words=words+1;
end
integer rows[32];integer left,seed=77,t,cmd_start,start_words,start_packets,reset_phase;
initial begin
repeat(3) @(negedge clk);rst_n=1;
for(reset_phase=1;reset_phase<=8;reset_phase=reset_phase+1) begin
 @(negedge clk);
 for(integer col=0;col<4;col=col+1) begin
  if(b.u_parent.rn_mid[col] !== (reset_phase>=3+col)) $fatal(1,"middle reset release col=%0d phase=%0d",col,reset_phase);
  if(b.u_parent.rn_n[col] !== (reset_phase>=4+col) || b.u_parent.rn_s[col] !== (reset_phase>=4+col)) $fatal(1,"credit reset release col=%0d phase=%0d",col,reset_phase);
 end
end
if(!ar || !br || !(&b.u_parent.rn_mid) || !(&b.u_parent.rn_n) || !(&b.u_parent.rn_s)) $fatal(1,"reset ready barrier");
$display("RESET_PROOF baseline3 middle3/4/5/6 credit4/5/6/7 maxaddedcold4 hotadded0 bothready=1");
for(integer cmd=0;cmd<4;cmd=cmd+1) begin
wait(ar);@(posedge clk);cmd_start=cycle;start_words=words;start_packets=packets;pub_space=(cmd%2)?2:1;pub_base=cmd*4096;pub_stride=128;pub_bf16=(cmd>=2);pub_v=1;
@(posedge clk);pub_v=0;repeat(12) @(posedge clk);
for(integer sm=0;sm<32;sm=sm+1) rows[sm]=0;
left=128;
while(left>0) begin
@(posedge clk);sm_rv=0;
for(integer sm=0;sm<32;sm=sm+1) if(rows[sm]<4 && ($unsigned($random(seed))%8)==0) begin
sm_rv[sm]=1;sm_rrow[sm*12 +:12]=rows[sm];rows[sm]=rows[sm]+1;left=left-1;
for(integer w=0;w<8;w=w+1) sm_rdata[sm*256+w*32 +:32]=$random(seed);
end
for(integer c=0;c<4;c=c+1) begin vmr[c*274+273]=($unsigned($random(seed))%3)!=0;vmr[c*274+256]=1;end
end
@(posedge clk);sm_rv=0;vmr='1;t=0;
while(!ad && t<10000) begin @(posedge clk);t=t+1;end
if(t>=10000 || af) $fatal(1,"timeout/fault cmd %0d",cmd);
$display("PRODUCTION cmd=%0d space=%0d bf16=%0d cycles=%0d words=%0d packets=%0d",cmd,pub_space,pub_bf16,cycle-cmd_start,words-start_words,packets-start_packets);
if(pub_space==2 && (words-start_words!=1024 || cycle-cmd_start>1126)) $fatal(1,"STREAM production budget: 1024words at 1word/cycle within10percent");
repeat(12) @(posedge clk);
end
$display("PASS cycle exact production NSM32 NC8 NPC4 MEM/STREAM BF16 cycles=%0d packets=%0d words=%0d",cycle,packets,words);$finish;
end
endmodule
