// Same-phase clock source is test stimulus only. Production wrappers expose six separate roots.
`timescale 1ns/1ps
module tb_bank_stage6_allowners;
parameter integer MUT=0;
parameter RG=7, WG=3;
localparam RB=$clog2(RG+1), WB=$clog2(WG+5);
reg clk=0; always #5 clk=~clk;
wire clk_pin=clk,clk_s1=clk,clk_mem=clk,clk_capture=clk,clk_return=clk,clk_status=clk;
reg rst_n=0; reg [2:0] bid=3; reg [1:0] sid=2;
reg rslot_v=0,wslot_v=0; reg [RB-1:0] rslot=0; reg [WB-1:0] wslot=0;
reg [RG*17-1:0] rq=0; wire [RG*257-1:0] rr;
reg [WG*281-1:0] wq=0; wire [WG-1:0] wq_done;
reg [280:0] dq=0,kq=0; wire dq_done,kq_done;
reg [275:0] xq=0,xq2=0; wire xq_done,xq2_done; wire [275:0] eg;
reg [284:0] pq=0; wire [265:0] pr; wire [17:0] status;
ot_vms_bank_static_wdecode_ft_stageclocks #(.RG(RG),.WG(WG),.MUT(MUT)) dut(.*);
reg [255:0] mem[0:2047];
reg [256:0] exp_rr[0:1023][0:RG-1];
reg [265:0] exp_pr[0:1023]; reg [275:0] exp_eg[0:1023];
reg [WG+3:0] exp_done[0:1023];
integer cycle=0,reads=0,writes=0,egresses=0;
integer i,g,row,owner; reg rv,wv,bad; reg [255:0] wd,rd; reg [7:0] mask; reg [15:0] sec;
function automatic [15:0] sector(input integer r,input bit mir);
sector={mir,mir?2'd0:sid,10'(r),bid};
endfunction
function automatic [255:0] pattern(input integer n);
for(integer k=0;k<8;k=k+1) pattern[k*32+:32]=32'h9e3779b9*(n*8+k+1);
endfunction
task automatic clear;
begin rq=0;wq=0;dq=0;kq=0;xq=0;xq2=0;pq=0;rslot_v=0;wslot_v=0;rslot=0;wslot=0;end
endtask
task automatic wr(input integer o,input integer r,input bit mir,input [255:0] d,input [7:0] m);
reg [280:0] payload;
begin
wslot_v=1;wslot=WB'(o);payload={1'b1,sector(r,mir),d,m};
if(o<WG) wq[o*281+:281]=payload;
else case(o-WG)
0:kq=payload;
1:xq={1'b1,mir,10'(r),d,m};
2:pq={1'b1,1'b1,mir,10'(r),d,m,8'h79};
3:xq2={1'b1,mir,10'(r),d,m};
4:dq=payload;
endcase
end
endtask
task automatic rrq(input integer o,input integer r,input bit mir);
begin rslot_v=1;rslot=RB'(o);
if(o==RG) pq={1'b1,1'b0,mir,10'(r),256'd0,8'd0,8'h2a};
else rq[o*17+:17]={1'b1,sector(r,mir)};
end
endtask
task automatic tick;
begin
// Independent sequential memory oracle. Read-before-write applies at every reserved slot.
rv=0;row=0;
if(rslot_v) begin
if(rslot<RG) begin rv=rq[rslot*17+16];sec=rq[rslot*17+:16];row={sec[15],sec[12:3]};end
else if(rslot==RG) begin rv=pq[284]&&!pq[283];row=pq[282:272];end
if(rv) begin
rd=mem[row];reads=reads+1;
if(rslot==RG) exp_pr[cycle+6]={1'b1,1'b0,pq[7:0],rd};
else exp_rr[cycle+6][rslot]={1'b1,rd};
end
end
wv=0;wd=0;mask=0;row=0;bad=0;
if(wslot_v) begin
owner=wslot;
if(owner<WG) begin wv=wq[owner*281+280];sec=wq[owner*281+264+:16];wd=wq[owner*281+8+:256];mask=wq[owner*281+:8];row={sec[15],sec[12:3]};bad=sec[2:0]!=bid||(sec[15]?sec[14:13]!=0:sec[14:13]!=sid);end
else case(owner-WG)
0:begin wv=kq[280];sec=kq[279:264];wd=kq[263:8];mask=kq[7:0];row={sec[15],sec[12:3]};bad=sec[2:0]!=bid||(sec[15]?sec[14:13]!=0:sec[14:13]!=sid);end
1:begin wv=xq[275];row=xq[274:264];wd=xq[263:8];mask=xq[7:0];end
2:begin wv=pq[284]&&pq[283];row=pq[282:272];wd=pq[271:16];mask=pq[15:8];end
3:begin wv=xq2[275];row=xq2[274:264];wd=xq2[263:8];mask=xq2[7:0];end
4:begin wv=dq[280];sec=dq[279:264];wd=dq[263:8];mask=dq[7:0];row={sec[15],sec[12:3]};bad=sec[2:0]!=bid||(sec[15]?sec[14:13]!=0:sec[14:13]!=sid);end
endcase
if(wv) begin
writes=writes+1;
if(!bad) for(integer k=0;k<8;k=k+1) if(mask[k]) mem[row][k*32+:32]=wd[k*32+:32];
if(owner<WG) exp_done[cycle+3][owner]=1;
else case(owner-WG)
0:exp_done[cycle+3][WG]=1;
1:exp_done[cycle+3][WG+1]=1;
2:exp_pr[cycle+6]={1'b1,1'b1,pq[7:0],256'd0};
3:exp_done[cycle+3][WG+2]=1;
4:exp_done[cycle+3][WG+3]=1;
endcase
if(owner<WG&&row>=1024&&!bad) begin exp_eg[cycle+1]={1'b1,11'(row),wd,mask};egresses=egresses+1;end
end
end
@(posedge clk); #1;
for(integer k=0;k<RG;k=k+1) begin
if(rr[k*257+256]!==exp_rr[cycle][k][256]) $fatal(1,"read valid timing cycle %0d lane %0d got %b expected %b",cycle,k,rr[k*257+256],exp_rr[cycle][k][256]);
if(exp_rr[cycle][k][256]&&rr[k*257+:256]!==exp_rr[cycle][k][255:0]) $fatal(1,"read payload cycle %0d lane %0d",cycle,k);
end
if(pr[265]!==exp_pr[cycle][265] || (exp_pr[cycle][265]&&pr!==exp_pr[cycle])) $fatal(1,"packet response cycle %0d got %h expected %h",cycle,pr,exp_pr[cycle]);
if(eg[275]!==exp_eg[cycle][275] || (exp_eg[cycle][275]&&eg!==exp_eg[cycle])) $fatal(1,"mirror egress cycle %0d",cycle);
if({dq_done,xq2_done,xq_done,kq_done,wq_done}!==exp_done[cycle]) $fatal(1,"write commit timing cycle %0d got %b expected %b",cycle,{dq_done,xq2_done,xq_done,kq_done,wq_done},exp_done[cycle]);
cycle=cycle+1;@(negedge clk);
end
endtask
task automatic drain;
begin clear(); repeat(9) tick();end
endtask
initial begin
for(i=0;i<2048;i=i+1) mem[i]=0;
for(i=0;i<1024;i=i+1) begin exp_pr[i]=0;exp_eg[i]=0;exp_done[i]=0;for(g=0;g<RG;g=g+1) exp_rr[i][g]=0;end
repeat(3) @(negedge clk);rst_n=1;repeat(3) @(negedge clk); /* ot_rst_relay release: initialization mode, 3 edges */
// Every source, both spaces; preserve opposite main/mirror parity halves and word masks.
for(i=0;i<2*(WG+5);i=i+1) begin clear();wr(i%(WG+5),17,i>=WG+5,pattern(i),8'hff);tick();end
for(i=0;i<2*(WG+5);i=i+1) begin clear();wr(i%(WG+5),17,i>=WG+5,pattern(i+50),8'h55);tick();end
for(i=0;i<2*(RG+1);i=i+1) begin clear();rrq(i%(RG+1),17,i>=RG+1);tick();end
drain();if(status!==0) $fatal(1,"unexpected ECC/fault status %h",status);
// II=1 with simultaneous same-row read/write exercises actual SRAM read-before-write.
for(i=0;i<210;i=i+1) begin
clear();wr(i%(WG+5),i%16,i[0],pattern(i+100),8'(i));
// Packet cannot be a reader and writer in the same slot.
rrq((i%(WG+5)==WG+2)?i%RG:i%(RG+1),i%16,i[0]);tick();
end
drain();if(status!==0) $fatal(1,"sustained stream status %h",status);
// Real physical macro ECC bit upset, then two-bit upset in same code word.
clear();wr(WG+4,0,0,pattern(900),8'hff);tick();drain();
dut.u_a.arr[0][0]=~dut.u_a.arr[0][0];
clear();rrq(0,0,0);tick();drain();
if(status[15:0]!=1||status[16]) $fatal(1,"single-bit correction status %h",status);
dut.u_a.arr[0][0]=~dut.u_a.arr[0][0]; // restore
// A distinct highest-word correctable fault exercises the population tree.
// The actual MUX2 macro bit-interleaves columns: logical bit224 is physical448.
dut.u_a.arr[0][448]=~dut.u_a.arr[0][448];
clear();rrq(0,0,0);tick();drain();
if(status[15:0]!=2||status[16]) $fatal(1,"last-word CE population mismatch status=%h",status);
dut.u_a.arr[0][448]=~dut.u_a.arr[0][448];
// Double fault: expected response retains corrupt word; UE must latch.
dut.u_a.arr[0][0]=~dut.u_a.arr[0][0];dut.u_a.arr[0][2]=~dut.u_a.arr[0][2];mem[0][1:0]=mem[0][1:0]^2'b11;
clear();rrq(1,0,0);tick();drain();if(!status[16]) $fatal(1,"double-bit error not detected");
// Address errors clear write mask, still drain completion, sticky FAULT.
clear();wr(0,17,0,pattern(999),8'hff);wq[0+:281]={1'b1,16'h4002,pattern(999),8'hff};tick();drain();
if(!status[17]) $fatal(1,"bad bank address not faulted");
clear();rrq(0,17,0);tick();drain();
// Reset controls/status with memory preserved. Unselected active request must fault,
// must not be queued for later replay, and must not overwrite memory.
rst_n=0;repeat(2) @(negedge clk);rst_n=1;repeat(3) @(negedge clk); /* ot_rst_relay release: initialization mode, 3 edges */
clear();wr(1,17,0,pattern(1001),8'hff);wslot=0;
// Oracle sees selected owner 0 (empty), so this is a deliberately dropped invalid schedule.
tick();drain();if(!status[17]) $fatal(1,"unselected active write not faulted");
clear();rrq(1,17,0);tick();drain();
rst_n=0;repeat(2) @(negedge clk);rst_n=1;repeat(3) @(negedge clk); /* ot_rst_relay release: initialization mode, 3 edges */
clear();rrq(1,17,0);rslot=0;tick();drain();if(!status[17]) $fatal(1,"unselected active read not faulted");
// Explicit out-of-range slot faults even with no request.
rst_n=0;repeat(2) @(negedge clk);rst_n=1;repeat(3) @(negedge clk); /* ot_rst_relay release: initialization mode, 3 edges */
if((1<<WB)>WG+5) begin clear();wslot_v=1;wslot=WB'(WG+5);tick();drain();if(!status[17]) $fatal(1,"invalid slot not faulted");end
$display("PASS static bank exact memory masks main/mirror ECC owner timing: reads=%0d writes=%0d egress=%0d cycles=%0d read=n+6 commit=n+3 egress=n+1 II=1",reads,writes,egresses,cycle);$finish;
end
endmodule
