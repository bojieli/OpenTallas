`timescale 1ns/1ps
module tb_dma_back_static;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg g_v=0,g_last=0;reg [1:0] g_q=0;reg [226:0] g_mv=0;reg [31:0] g_issue_at=0,g_drain_at=0;
reg g_wb_bank=0;reg [15:0] g_wb_epoch=0;
wire [31:0] cycle;wire fence_quiet,done,fault;wire [3:0] e_src,e_busy;
wire [543:0] rq;wire [8223:0] rr;wire [3:0] reserve,fill;wire [3:0] reserve_bank,fill_bank;wire [63:0] reserve_epoch,fill_epoch;wire [47:0] sectors;wire [127:0] base;wire [9247:0] wd;
reg [47:0] wa=0;
ot_hgi_b2_swap_grp_static #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.g_v(g_v),.g_last(g_last),.g_q(g_q),.g_mv(g_mv),.g_issue_at(g_issue_at),.g_drain_at(g_drain_at),.g_wb_bank(g_wb_bank),.g_wb_epoch(g_wb_epoch),.cycle(cycle),
    .fence_quiet(fence_quiet),.done(done),.fault(fault),.e_src(e_src),.e_busy(e_busy),.rq(rq),.rr(rr),.wb_reserve_v(reserve),.wb_reserve_bank(reserve_bank),.wb_fill_bank(fill_bank),.wb_reserve_epoch(reserve_epoch),.wb_fill_epoch(fill_epoch),.wb_reserve_sectors(sectors),.wb_reserve_base(base),.wb_fill_start(fill),.wb_ready(4'b1111),.wd(wd),.wa(wa));
reg [280:0] dq[0:3][0:7];wire [17:0] status[0:3][0:7];
for(genvar q=0;q<4;q=q+1)begin:Q
for(genvar b=0;b<8;b=b+1)begin:B
    wire [513:0] responses;
    ot_vms_bank_static #(.RG(2),.WG(2)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
    .rslot_v(rq[(q*8+b)*17+16]),.rslot(2'd0),.wslot_v(dq[q][b][280]),.wslot(3'd6),
    .rq({17'd0,rq[(q*8+b)*17+:17]}),.rr(responses),.wq(562'd0),.wq_done(),.dq(dq[q][b]),.dq_done(),.kq(281'd0),.kq_done(),
    .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[q][b]));
    assign rr[(q*8+b)*257+:257]=responses[256:0];
end
end
integer at,n,q,b,w,mode,source_at,drain_at,pre_issue,pre_drain,start_at;
integer scrub[0:3],src_seen[0:3];integer count=0,acks=0,done_count=0,requests=0;
reg [47:0] ack_due[0:4095];reg [640:0] seen[0:3];
reg armed=0;reg mir=0;reg [288:0] beat;reg [31:0] address;integer ordinal;reg [255:0] expdata;
function automatic [255:0] pattern(input integer node,input integer row,input integer bank);
for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h3c6ef372*(1+node*5120+row*64+bank*8+k);
endfunction
function automatic [15:0] sector(input integer node,input integer row,input integer bank,input bit mirror);
sector={mirror,mirror?2'd0:2'(node),10'(row),3'(bank)};
endfunction
function automatic [226:0] move(input integer node,input bit pre,input bit mirror);
reg [39:0] vb;reg [36:0] db;
begin
vb=(mirror?40'd65536:40'd0)+(pre?40'd8192:40'd0);
db=(37'(node)<<35)+(pre?37'h120000:37'h100000+37'(64*node));
move={pre?21'd8:21'd64,pre?20'd1:20'd80,16'd1,pre?32'd0:32'd256,{3'd0,db},3'd0,2'd0,16'd1,32'd64,vb,3'd0,2'd1};
end
endfunction
task automatic clear;
begin g_v=0;g_last=0;g_q=0;g_mv=0;g_issue_at=0;g_drain_at=0;g_wb_bank=0;g_wb_epoch=0;for(integer i=0;i<4;i=i+1)for(integer j=0;j<8;j=j+1)dq[i][j]=0;end
endtask
task automatic tick;
begin
at=cycle;wa=ack_due[at];
if(armed)for(integer i=0;i<4;i=i+1)if(scrub[i]>=0)begin
for(integer j=0;j<8;j=j+1)dq[i][j]={1'b1,sector(i,scrub[i],j,mir),256'hdeadbeef,8'hff};scrub[i]=scrub[i]-1;
end
@(posedge clk);#1;
if(fault) $fatal(1,"dispatcher/engine fault at%0d",at);
for(integer i=0;i<4;i=i+1)begin
for(integer j=0;j<8;j=j+1)if(status[i][j]!==0)$fatal(1,"actual VM bank fault at%0d q%0d b%0d status%h",at,i,j,status[i][j]);
if(armed)begin
if(e_src[i])begin
if(src_seen[i]==0)begin if(at!=source_at+88)$fatal(1,"premature/mistimed posted source at%0d expected%0d",at,source_at+88);scrub[i]=79;end
else if(i!=0||at!=pre_issue+9)$fatal(1,"PRE source timing at%0d",at);
src_seen[i]=src_seen[i]+1;
end
if(reserve[i])begin
if(reserve_bank[i]!==((sectors[i*12+:12]==1)?1'b1:1'b0)||reserve_epoch[i*16+:16]!==16'(mode*2+(sectors[i*12+:12]==1?1:0)))$fatal(1,"compiler WB bank/epoch reservation mismatch");
if(sectors[i*12+:12]!==12'd640&&!(i==0&&sectors[i*12+:12]===12'd1))$fatal(1,"block reservation size");
end
for(integer j=0;j<8;j=j+1)begin
if(rq[(i*8+j)*17+16])begin
if(!((at>=source_at&&at<source_at+80)||(i==0&&j==0&&at==pre_issue)))$fatal(1,"VM issue outside compiler calendar at%0d",at);
requests=requests+1;
end
beat=wd[(i*8+j)*289+:289];
if(beat[288])begin
address=beat[287:256];
if(address[31:30]!==2'(i))$fatal(1,"wrong HBM stack");
if(i==0&&address[29:0]==30'h9000)begin ordinal=640;expdata=pattern(0,128,0);if(at!=pre_drain+2)$fatal(1,"PRE wd timing");end
else begin
ordinal=int'(address[29:0])-32768-2*i;
if(ordinal<0||ordinal>=640)$fatal(1,"HBM address outside actual production slot at%0d addr%h",at,address);
expdata=pattern(i,ordinal/8,ordinal%8);
if(at!=drain_at+2+ordinal/8||ordinal%8!=j)$fatal(1,"fixed WB lane/address timeline at%0d",at);
end
if(seen[i][ordinal])$fatal(1,"duplicate HBM sector");seen[i][ordinal]=1;
if(beat[255:0]!==expdata)$fatal(1,"actual landing SRAM payload at%0d q%0d ordinal%0d",at,i,ordinal);
count=count+1;ack_due[at+40][i*12+:12]=ack_due[at+40][i*12+:12]+1;
end
end
end
end
if(armed)begin
for(integer i=0;i<4;i=i+1)acks=acks+int'(wa[i*12+:12]);
if(done)begin done_count=done_count+1;if(acks!=2561||count!=2561)$fatal(1,"early fence %0d writes %0d ack",count,acks);end
end
@(negedge clk);
end
endtask
initial begin
for(n=0;n<4096;n=n+1)ack_due[n]=0;
for(q=0;q<4;q=q+1)begin scrub[q]=-1;src_seen[q]=0;seen[q]=0;end
clear();repeat(3)@(negedge clk);rst_n=1;
for(mode=0;mode<2;mode=mode+1)begin
mir=mode!=0;armed=0;count=0;acks=0;requests=0;done_count=0;
for(q=0;q<4;q=q+1)begin scrub[q]=-1;src_seen[q]=0;seen[q]=0;end
for(n=0;n<80;n=n+1)begin clear();for(q=0;q<4;q=q+1)for(b=0;b<8;b=b+1)dq[q][b]={1'b1,sector(q,n,b,mir),pattern(q,n,b),8'hff};tick();end
clear();dq[0][0]={1'b1,sector(0,128,0,mir),pattern(0,128,0),8'hff};tick();clear();repeat(8)tick();
start_at=cycle;source_at=start_at+16;drain_at=source_at+10;pre_issue=drain_at+90;pre_drain=pre_issue+11;armed=1;
for(q=0;q<4;q=q+1)begin clear();g_v=1;g_q=2'(q);g_last=q==3;g_mv=move(q,0,mir);g_issue_at=source_at;g_drain_at=drain_at;g_wb_bank=0;g_wb_epoch=16'(mode*2);tick();end
clear();while(cycle<drain_at+84)begin tick();clear();end
g_v=1;g_last=1;g_q=0;g_mv=move(0,1,mir);g_issue_at=pre_issue;g_drain_at=pre_drain;g_wb_bank=1;g_wb_epoch=16'(mode*2+1);tick();clear();
while(done_count==0&&cycle<pre_drain+100)begin tick();clear();end
if(done_count!=1||!fence_quiet||requests!=2561)$fatal(1,"missing production completion/requests");
for(q=0;q<4;q=q+1)if(src_seen[q]!=(q==0?2:1))$fatal(1,"posted retire counts");
if(cycle-start_at>272)$fatal(1,"production throughput %0d >272",cycle-start_at);
$display("PASS production %s STORE20480words+PRE8: real32VMbanks/96macros+32landingmacros;2561exactsectors,postedsourceoverwrite,fenceafter2561acks;firstcommand->fence=%0dcycles",mir?"MIRROR":"MAIN",cycle-start_at);
armed=0;repeat(5)tick();clear();
end
$display("PASS DMA static actual production both main/mirror, no runtime VM credits/ready/group lease or dynamic onchip issue");$finish;
end
endmodule
