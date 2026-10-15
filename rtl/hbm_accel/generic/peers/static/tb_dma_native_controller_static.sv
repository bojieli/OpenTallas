`timescale 1ps/1fs
module tb_dma_native_controller_static;
parameter integer MUT=0;
parameter integer TRACE=0;
parameter integer WB_PIPELINE=2;
parameter integer HBM_SECTOR_BASE=32'h28800000;
parameter integer PRE_SECTOR_BASE=32'h28800a00;
parameter integer PHY_K_BASE=32'h28800000;
reg clk=0,hbm_clk=0;initial forever begin #416.666 clk=1;#416.667 clk=0;end
initial begin #173;forever #512 hbm_clk=~hbm_clk;end
reg rst_n=0;reg readback_start=0;wire [3:0]readback_done;
reg g_v=0,g_last=0;reg [1:0] g_q=0;reg [226:0] g_mv=0;reg [31:0] g_issue_at=0,g_drain_at=0;
reg g_wb_bank=0;reg [15:0] g_wb_epoch=0;
wire [31:0] cycle;wire fence_quiet,done,fault;wire [3:0] e_src,e_busy;
wire [543:0] rq;wire [8223:0] rr;wire [3:0] reserve,fill;wire [3:0] reserve_bank,fill_bank;wire [63:0] reserve_epoch,fill_epoch;wire [47:0] sectors;wire [127:0] base;wire [9247:0] wd;
wire [47:0] wa;
wire [3:0] wb_done,wb_fill_done,wb_fault;
wire [127:0] wb_k_v,wb_k_rdy,wb_k_we,actual_k_wr_done;
wire [3839:0] wb_k_addr;wire [511:0] wb_k_len;wire [2175:0] wb_k_tag;
wire [32767:0] wb_k_data;wire [4095:0] wb_k_strb;
ot_hgi_b2_swap_wb_grp_static #(.MUT(MUT),.WB_PIPELINE(WB_PIPELINE)) dut(.stream_clk(clk),.stream_rst_n(rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(rst_n),
 .g_v(g_v),.g_last(g_last),.g_q(g_q),.g_mv(g_mv),.g_issue_at(g_issue_at),.g_drain_at(g_drain_at),.g_wb_bank(g_wb_bank),.g_wb_epoch(g_wb_epoch),
 .cycle(cycle),.fence_quiet(fence_quiet),.done(done),.fault(fault),.e_src(e_src),.e_busy(e_busy),.rq(rq),.rr(rr),
 .wb_done_v(wb_done),.wb_fill_done(wb_fill_done),.wb_fault(wb_fault),.actual_posted_sectors(wa),
 .k_v(wb_k_v),.k_rdy(wb_k_rdy),.k_addr(wb_k_addr),.k_len(wb_k_len),.k_tag(wb_k_tag),.k_we(wb_k_we),.k_wdata(wb_k_data),.k_wstrb(wb_k_strb),.k_wr_done(actual_k_wr_done));
assign wd=dut.wd;assign reserve=dut.reserve;assign fill=dut.fill_start;assign sectors=dut.reserve_total;assign base=dut.reserve_base;
assign reserve_bank=dut.reserve_bank;assign fill_bank=dut.fill_bank;assign reserve_epoch=dut.reserve_epoch;assign fill_epoch=dut.fill_epoch;
generate if(TRACE!=0&&WB_PIPELINE!=0)begin:TRACE_BOUNDARY
 for(genvar q=0;q<4;q=q+1)begin:Q
 always @(negedge clk)if(rst_n&&armed)begin
  if(reserve[q]||fill[q]||wb_fill_done[q]||dut.Q[q].PIPELINED_WB.wb.start_copy||wb_done[q])
   $display("TRACE_STAGE mode%0d q%0d stream%0d start%0d reserve%0b fill%0b staged%0b copy%0b done%0b",mode,q,cycle,start_at,reserve[q],fill[q],wb_fill_done[q],dut.Q[q].PIPELINED_WB.wb.start_copy,wb_done[q]);
 end
 end
end endgenerate
integer physical_writes[0:3],physical_acks[0:3],memory_checks[0:3];
integer first_phy[0:3],last_phy[0:3],last_ack[0:3],hbm_edge=0,throughput_bad=0;
reg [640:0] phy_seen[0:3];reg check_memory=0;
always @(posedge hbm_clk)if(rst_n)hbm_edge=hbm_edge+1;
for(genvar stack=0;stack<4;stack=stack+1)begin:PHY
 wire [31:0] k_v,k_rdy,k_we,kr_v;wire [959:0] k_addr;wire [127:0] k_len;wire [543:0] k_tag;
 wire [8191:0] k_data;wire [1023:0] k_strb;wire k_oor,w_oor;
 reg[31:0]rd_v=0;wire[31:0]rd_rdy;reg[959:0]rd_addr=0;reg[543:0]rd_tag=0;wire[543:0]kr_tag;wire[8191:0]kr_data;reg rb_done=0;assign readback_done[stack]=rb_done;
 ot_hbm_svc_phy_mux mux(.hbm_clk(hbm_clk),.hbm_rst_n(rst_n),
  .rd_v(rd_v),.rd_rdy(rd_rdy),.rd_addr(rd_addr),.rd_len({32{4'd1}}),.rd_tag(rd_tag),
  .wb_v(wb_k_v[stack*32+:32]),.wb_rdy(wb_k_rdy[stack*32+:32]),.wb_addr(wb_k_addr[stack*960+:960]),.wb_len(wb_k_len[stack*128+:128]),.wb_tag(wb_k_tag[stack*544+:544]),.wb_data(wb_k_data[stack*8192+:8192]),.wb_strb(wb_k_strb[stack*1024+:1024]),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_data),.k_wstrb(k_strb));
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;
 ot_hbm_svc_native_sector_queued_stack controller(.clk(hbm_clk),.pc_clk({32{hbm_clk}}),.rst_n(rst_n),
 .k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_data),.k_wstrb(k_strb),.k_wr_done(actual_k_wr_done[stack*32+:32]),
 .kr_v(kr_v),.kr_rdy(32'hffffffff),.kr_tag(kr_tag),.kr_beat(),.kr_data(kr_data),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(k_oor));
 assign w_oor=0;
 ot_dma_command_dram_fixture #(.K_BASE(PHY_K_BASE),.K_MEM(65536)) dram(.clk(hbm_clk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 integer emitted[0:31],posted[0:31];
 initial for(integer p=0;p<32;p=p+1)begin emitted[p]=0;posted[p]=0;end
 always @(posedge hbm_clk)if(rst_n)begin
 if(k_oor)$fatal(1,"native controller fault including verification/idle");
 for(integer p=0;p<32;p=p+1)begin
  if(col_v[p]&&col_we[p])emitted[p]=emitted[p]+1;
  if(actual_k_wr_done[stack*32+p])begin if(posted[p]>=emitted[p])$fatal(1,"native enqueue ACK before physical WR");posted[p]=posted[p]+1;end
 end end
 initial forever begin:READBACK
  integer i,pc,guard;reg[29:0]addr;reg[255:0]expected_word;
  wait(readback_start);rb_done=0;
  for(i=0;i<(stack==0?641:640);i=i+1)begin
   addr=i==640?30'(PRE_SECTOR_BASE):30'(HBM_SECTOR_BASE+2*stack+i);pc=(addr[6:2]^addr[11:7]^addr[16:12]);expected_word=i==640?pattern(0,128,0):pattern(stack,i/8,i%8);
   @(negedge hbm_clk);rd_addr=0;rd_tag=0;rd_addr[pc*30+:30]=addr;rd_tag[pc*17+:17]=17'(i);rd_v=32'b1<<pc;guard=0;
   do begin @(posedge hbm_clk);guard=guard+1;if(guard>20000)$fatal(1,"native read admission timeout");end while(!rd_rdy[pc]);
   @(negedge hbm_clk);rd_v=0;guard=0;
   while(!kr_v[pc])begin @(negedge hbm_clk);guard=guard+1;if(guard>20000)$fatal(1,"native read response timeout");end
   if(kr_tag[pc*17+:17]!==17'(i)||kr_data[pc*256+:256]!==expected_word)$fatal(1,"native command readback identity/data stack%0d sector%0d",stack,i);
  end
  if(dram.reads!=(mode+1)*(stack==0?641:640)||dram.writes!=(mode+1)*(stack==0?641:640))$fatal(1,"native physical command totals");
  $display("NATIVE_READBACK PASS stack%0d exactsectors%0d actualRDcommands%0d refreshes%0d",stack,stack==0?641:640,dram.reads,dram.refreshes);rb_done=1;wait(!readback_start);rb_done=0;
 end

 always @(posedge hbm_clk)if(rst_n&&armed)begin:CHECK_PHY
  integer pc,sec,idx;reg [255:0] expected_data;reg [16:0] expected_tag;
  if(k_oor||w_oor)$fatal(1,"actual PHY aperture");
  for(pc=0;pc<32;pc=pc+1)begin
   if(actual_k_wr_done[stack*32+pc])begin physical_acks[stack]=physical_acks[stack]+1;last_ack[stack]=hbm_edge;end
   if(k_v[pc]&&k_rdy[pc])begin
    sec=int'(k_addr[pc*30+:30]);
    if((((sec>>2)^(sec>>7)^(sec>>12))&31)!=pc)$fatal(1,"actual PHY XOR PC map");
    if(stack==0&&sec==PRE_SECTOR_BASE)begin idx=640;expected_data=pattern(0,128,0);expected_tag={1'b1,16'(mode*2+1)};end
    else begin idx=sec-HBM_SECTOR_BASE-2*stack;if(idx<0||idx>=640)$fatal(1,"actual PHY store address");expected_data=pattern(stack,idx/8,idx%8);expected_tag={1'b0,16'(mode*2)};end
    if(!k_we[pc]||k_len[pc*4+:4]!=1||k_strb[pc*32+:32]!==32'hffffffff||k_tag[pc*17+:17]!==expected_tag)$fatal(1,"actual PHY write identity/mask");
    if(phy_seen[stack][idx]||k_data[pc*256+:256]!==expected_data)$fatal(1,"actual WB SRAM/CDC payload or duplicate at stack%0d sector%0d",stack,sec);
    phy_seen[stack][idx]=1;if(physical_writes[stack]==0)first_phy[stack]=hbm_edge;
    physical_writes[stack]=physical_writes[stack]+1;last_phy[stack]=hbm_edge;
   end
  end
 end
 // Off-chip verification only. No preload or hierarchical write is performed.
 always @(posedge clk)begin:CHECK_HBM_ARRAY
  integer i;#2;
  if(check_memory)begin
   for(i=0;i<640;i=i+1)begin
    if(dram.mem[HBM_SECTOR_BASE+2*stack+i-PHY_K_BASE]!==pattern(stack,i/8,i%8))$fatal(1,"actual mutable HBM memory data stack%0d sector%0d",stack,i);
    memory_checks[stack]=memory_checks[stack]+1;
   end
   if(stack==0)begin if(dram.mem[PRE_SECTOR_BASE-PHY_K_BASE]!==pattern(0,128,0))$fatal(1,"actual mutable HBM PRE data");memory_checks[stack]=memory_checks[stack]+1;end
  end
 end
end
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
reg [640:0] seen[0:3];
reg armed=0;reg mir=0;reg [288:0] beat;reg [31:0] address;integer ordinal;reg [255:0] expdata;
function automatic [255:0] pattern(input integer node,input integer row,input integer bank);
for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h3c6ef372*(1+mode*100000+node*5120+row*64+bank*8+k);
endfunction
function automatic [15:0] sector(input integer node,input integer row,input integer bank,input bit mirror);
sector={mirror,mirror?2'd0:2'(node),10'(row),3'(bank)};
endfunction
function automatic [226:0] move(input integer node,input bit pre,input bit mirror);
reg [39:0] vb;reg [36:0] db;
begin
vb=mirror?(40'd65536+(pre?40'd20480:40'(node*5120))):(pre?40'd8192:40'd0);
db=(37'(node)<<35)+(pre?(37'(PRE_SECTOR_BASE)<<5):((37'(HBM_SECTOR_BASE)<<5)+37'(64*node)));
move={pre?21'd8:21'd64,pre?20'd1:20'd80,16'd1,pre?32'd0:32'd256,{3'd0,db},3'd0,2'd0,16'd1,32'd64,vb,3'd0,2'd1};
end
endfunction
task automatic clear;
begin g_v=0;g_last=0;g_q=0;g_mv=0;g_issue_at=0;g_drain_at=0;g_wb_bank=0;g_wb_epoch=0;for(integer i=0;i<4;i=i+1)for(integer j=0;j<8;j=j+1)dq[i][j]=0;end
endtask
task automatic tick;
begin
at=cycle;
if(armed)for(integer i=0;i<4;i=i+1)if(scrub[i]>=0)begin
for(integer j=0;j<8;j=j+1)dq[i][j]={1'b1,sector(i,scrub[i]+(mir?i*80:0),j,mir),256'hdeadbeef,8'hff};scrub[i]=scrub[i]-1;
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
if(i==0&&address[29:0]==30'(PRE_SECTOR_BASE))begin ordinal=640;expdata=pattern(0,128,0);if(at!=pre_drain+2)$fatal(1,"PRE wd timing");end
else begin
ordinal=int'(address[29:0])-HBM_SECTOR_BASE-2*i;
if(ordinal<0||ordinal>=640)$fatal(1,"HBM address outside actual production slot at%0d addr%h",at,address);
expdata=pattern(i,ordinal/8,ordinal%8);
if(at!=drain_at+2+ordinal/8||ordinal%8!=j)$fatal(1,"fixed WB lane/address timeline at%0d",at);
end
if(seen[i][ordinal])$fatal(1,"duplicate HBM sector");seen[i][ordinal]=1;
if(beat[255:0]!==expdata)$fatal(1,"actual landing SRAM payload at%0d q%0d ordinal%0d",at,i,ordinal);
count=count+1;
end
end
end
end
if(armed)begin
for(integer i=0;i<4;i=i+1)acks=acks+int'(wa[i*12+:12]);
if(done)begin done_count=done_count+1;if(physical_acks[0]+physical_acks[1]+physical_acks[2]+physical_acks[3]!=2561)$fatal(1,"fence before actual HBM drain ACK");if(acks!=2561||count!=2561)$fatal(1,"early fence %0d writes %0d ack",count,acks);end
end
@(negedge clk);
end
endtask
initial begin

for(q=0;q<4;q=q+1)begin scrub[q]=-1;src_seen[q]=0;seen[q]=0;end
clear();repeat(3)@(negedge clk);rst_n=1;
for(mode=0;mode<2;mode=mode+1)begin
mir=mode!=0;armed=0;check_memory=0;
for(q=0;q<4;q=q+1)begin physical_writes[q]=0;physical_acks[q]=0;memory_checks[q]=0;phy_seen[q]=0;first_phy[q]=0;last_phy[q]=0;last_ack[q]=0;end
count=0;acks=0;requests=0;done_count=0;
for(q=0;q<4;q=q+1)begin scrub[q]=-1;src_seen[q]=0;seen[q]=0;end
for(n=0;n<(mir?320:80);n=n+1)begin clear();for(q=0;q<4;q=q+1)for(b=0;b<8;b=b+1)dq[q][b]={1'b1,sector(q,n,b,mir),mir?pattern(n/80,n%80,b):pattern(q,n,b),8'hff};tick();end
clear();dq[0][0]={1'b1,sector(0,mir?320:128,0,mir),pattern(0,128,0),8'hff};tick();clear();repeat(8)tick();
start_at=cycle;source_at=start_at+16;drain_at=source_at+10;pre_issue=drain_at+90;pre_drain=pre_issue+11;armed=1;
for(q=0;q<4;q=q+1)begin clear();g_v=1;g_q=2'(q);g_last=q==3;g_mv=move(q,0,mir);g_issue_at=source_at;g_drain_at=drain_at;g_wb_bank=0;g_wb_epoch=16'(mode*2);tick();end
clear();while(cycle<drain_at+84)begin tick();clear();end
g_v=1;g_last=1;g_q=0;g_mv=move(0,1,mir);g_issue_at=pre_issue;g_drain_at=pre_drain;g_wb_bank=1;g_wb_epoch=16'(mode*2+1);tick();clear();
while(done_count==0&&cycle<pre_drain+100000)begin tick();clear();end
if(done_count!=1||!fence_quiet||requests!=2561)$fatal(1,"missing production completion/requests");
for(q=0;q<4;q=q+1)if(src_seen[q]!=(q==0?2:1))$fatal(1,"posted retire counts");
if(cycle-start_at>272)begin throughput_bad=throughput_bad+1;$display("DMA_WB_PHY_THROUGHPUT FAIL actual_full_fence_cycles=%0d limit272 immutable_price248",cycle-start_at);end
check_memory=1;tick();check_memory=0;
for(q=0;q<4;q=q+1)begin
 if(physical_writes[q]!=(q==0?641:640)||physical_acks[q]!=(q==0?641:640)||memory_checks[q]!=(q==0?641:640))$fatal(1,"missing actual HBM memory/ACK coverage");
 $display("DMA_WB_PHY_STACK stack=%0d writes=%0d realACKs=%0d memorychecks=%0d firstHBMedge=%0d lastHBMedge=%0d lastACKedge=%0d",q,physical_writes[q],physical_acks[q],memory_checks[q],first_phy[q],last_phy[q],last_ack[q]);
end
$display("PASS production %s STORE20480words+PRE8: real32VMbanks/96macros+32landingmacros+128WBmacros+128actualr14controllers+commandDRAM;2561exactsectors,postedsourceoverwrite,fenceafter2561acks;firstcommand->fence=%0dcycles",mir?"MIRROR":"MAIN",cycle-start_at-1);
armed=0;readback_start=1;while(readback_done!=4'hf)begin tick();clear();end readback_start=0;repeat(5)tick();clear();
end
$display("DMA_NATIVE_FUNCTIONAL PASS both main/mirror actual mutableHBM no preload;throughput_fail_campaigns=%0d",throughput_bad);$finish;
end
endmodule
