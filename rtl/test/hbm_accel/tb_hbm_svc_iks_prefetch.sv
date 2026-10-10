`timescale 1ps/1ps
// Timed full-shape actual IKS service with REFpb; pattern exactness and final-credit drain.
module tb_hbm_svc_iks_prefetch #(parameter REF_MODE=3,PULL=0,BATCH=0,KEY_DEPTH=64,MAXREAD=15,STREAM_PS=1024,KEYLEG=24,CODE_MUT=0);
reg clk=0,sclk=0,efck=0,rst_n=0;always #512 clk=~clk;
always begin #416 efck=1;#417 efck=0;end
integer score_phase_ps=0;
initial begin if($value$plusargs("score_phase_ps=%d",score_phase_ps))begin end #(score_phase_ps);forever begin #416 sclk=1;#417 sclk=0;end end
reg[127:0] ed=0;wire[31:0]kv,krdy,kwe,rv,rrdy;wire[959:0]addr;wire[127:0]len,beat;wire[543:0]tag,rtag;
wire[8191:0]data_;wire[8791:0]lines;wire done,fault;wire[7:0]credit;
wire phy_clk,phy_rst_n;wire[8191:0]rawdata;wire[8191:0]wdata;wire[1023:0]wstrb;wire[31:0]wdone;
assign data_=rawdata ^ ((mut==1 && rv[5]) ? (8192'd1 << (5*256)) : 8192'd0);
ot_hbm_svc_core #(.IKS(1),.IK_DEPTH(KEY_DEPTH),.KNO(MAXREAD),.E_ST(11),.XST(2))dut(.ck(clk),.rst(rst_n),.q_d(336'd0),.q_v(8'd0),.q_fclk(8'd0),.q_rdy(),.line(),.fclk(),
.e_d(ed),.e_fclk(efck),.kv(),.ik(),.phy_clk(phy_clk),.phy_rst_n(phy_rst_n),.k_v(kv),.k_rdy(krdy),.k_addr(addr),.k_len(len),.k_tag(tag),.k_we(kwe),.k_wdata(wdata),.k_wstrb(wstrb),
.kr_v(rv),.kr_rdy(rrdy),.kr_tag(rtag),.kr_beat(beat),.kr_data(data_),.w_v(),.w_rdy(1'b0),.w_addr(),.w_len(),.w_tag(),.w_room(8'd0),.wr_v(8'd0),.wr_rdy(),.wr_tag(80'd0),.wr_beat(40'd0),.wr_data(2048'd0),
.wq_d(292'd0),.wq_fclk(1'b0),.wq_g(),.k_wr_done(wdone),.kvs(),.kvs_done(),.ik_credit(credit),.ik_lines(lines),.ik_done(done),.ik_fault(fault));
ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.DW(256),.MEM_WORDS(1024),.TAGW(17),.LENW(4),.BEATW(4),.QD(64),.REFPB(REF_MODE),.PULLIN(PULL),.PULLIN_BATCH(BATCH),.MEM_MODE(1),.CLK_PS(STREAM_PS)) mem(
.clk(phy_clk),.rst_n(phy_rst_n),.req_v(kv),.req_rdy(krdy),.req_addr(addr),.req_len(len),.req_tag(tag),.req_we(kwe),.req_wdata(wdata),.req_wstrb(wstrb),.wr_done(wdone),.rsp_v(rv),.rsp_rdy(rrdy),.rsp_tag(rtag),.rsp_beat(beat),.rsp_data(rawdata));
integer row0=4006;
function automatic[29:0] kaddr(input integer pc,j);
 integer row,bank,col,bhi,blo,hi5;
 begin row=row0+(j>>10);bank=(((j>>7)&7)<<2)|(j&3);col=(j>>2)&31;bhi=(bank>>2)^((row>>2)&7);blo=(bank&3)^(row&3);hi5=((row&3)<<3)|bhi;
 kaddr=30'((row<<15)|(bhi<<12)|(col<<7)|(((pc^col^hi5)&31)<<2)|blo);end
endfunction
function automatic[255:0]pat(input[29:0]a);integer i;begin for(i=0;i<8;i=i+1)pat[i*32+:32]=(a*8+i)*32'h9E3779B1^32'h5bd1e995;end endfunction
integer got=0,l,i,g,pc,j,off,mut=0,t=0,phase=0,delay_=1,rep_=0,query_ns=0,max_fifo=0;
reg[255:0]ex;reg fin=0;time launch,lastline,drained;
wire[8:0] slots[0:31];wire[11:0] request_j[0:31];
for(genvar rp=0;rp<32;rp=rp+1)begin:monitor
 assign slots[rp]=dut.gkvs.gs[rp].slots;
 assign request_j[rp]=dut.gkvs.gs[rp].jn;
end
integer mp,mb;integer req_beats=0,rsp_beats=0,req_stall=0,slot_stall=0,queued=0,max_queued=0,ref_head=0,scheduled_wait=0,return_wait=0,return_full=0; 
always @(posedge clk)if(rst_n&&launch>0&&got<1368)begin
 for(mp=0;mp<32;mp=mp+1)begin
  if(kv[mp]&&krdy[mp])req_beats=req_beats+len[mp*4+:4];
  if(kv[mp]&&!krdy[mp])req_stall=req_stall+1;
  if(rv[mp])rsp_beats=rsp_beats+1;
  if(request_j[mp]<182&&slots[mp]<4)slot_stall=slot_stall+1;
  queued=queued+mem.q_n[mp];
  if(mem.h_sched[mp] && mem.h_tcol[mp]>mem.cyc*STREAM_PS)scheduled_wait=scheduled_wait+1;
  if(mem.r_n[mp]>0 && mem.r_t[mp][mem.r_rp[mp]]>mem.cyc*STREAM_PS)return_wait=return_wait+1;
  if(mem.r_n[mp]>=32)return_full=return_full+1;
  if(mem.q_n[mp]>max_queued)max_queued=mem.q_n[mp];
  if(mem.q_n[mp]>0)begin
   mb=mem.bank_of(mem.q_addr[mp][mem.q_rp[mp]]);
   if(mem.b_refend[mp][mb]>mem.cyc*STREAM_PS)ref_head=ref_head+1;
  end
 end
end
wire[8791:0] delayed_lines;
wire[7:0] fifo_ne;wire[8783:0] fifo_data;wire[55:0] fifo_count;
reg query_ready=0;reg[7:0] popped_credit=0;
wire pop=query_ready&&(&fifo_ne)&&got<1368;
wire link_fault,link_corrected;reg correction_seen=0;
ot_hbm_index_line_cdc #(.KEYLEG(KEYLEG),.MUT(CODE_MUT)) real_line_path(
 .hclk(clk),.sclk(sclk),.rst_n(rst_n),.lines(lines),.landing_lines(delayed_lines),
 .landing_credit(popped_credit),.source_credit(credit),.fault(link_fault),.corrected(link_corrected));
for(genvar fp=0;fp<8;fp=fp+1)begin:landing
 reg captured_valid=0;reg[1097:0]captured_data;
 always@(posedge sclk or negedge rst_n)if(!rst_n)captured_valid<=0;else captured_valid<=delayed_lines[fp*1099];
 always@(posedge sclk)captured_data<=delayed_lines[fp*1099+1+:1098];
 hfd_idx_fifo #(.W(1098),.AW(6)) actual_score_fifo(.ck(sclk),.rst_n(rst_n),.we(captured_valid),.wd(captured_data),.re(pop),.rd(fifo_data[fp*1098+:1098]),.ne(fifo_ne[fp]),.cnt(fifo_count[fp*7+:7]));
end
always@(posedge sclk)begin
 if(link_corrected)correction_seen=1;
 popped_credit<={8{pop}};
 for(integer cp=0;cp<8;cp=cp+1)begin
  if(fifo_count[cp*7+:7]>max_fifo)max_fifo=fifo_count[cp*7+:7];
  if(fifo_count[cp*7+:7]>64)$fatal(1,"FIFO overfull");
 end
 if(rst_n&&pop)begin
  for(integer lp=0;lp<8;lp=lp+1)begin
   if(fifo_data[lp*1098+:10]!==10'(got+lp))$fatal(1,"tag consumed=%0d",got+lp);
   for(integer bp=0;bp<136;bp=bp+1)begin
    g=(got+lp)*136+bp;pc=(g/32)%32;j=g/1024;off=g%32;ex=pat(kaddr(pc,j));
    if(fifo_data[lp*1098+10+bp*8+:8]!==ex[off*8+:8])$fatal(1,"data line=%0d byte=%0d",got+lp,bp);
   end
  end
  got=got+8;lastline=$time;
 end
end
initial begin
if($value$plusargs("mut=%d",mut))begin end
if($value$plusargs("phase_ns=%d",phase))begin end
if($value$plusargs("query_ns=%d",query_ns))begin end
repeat(10)@(negedge clk);rst_n=1;
#(phase*1000+3000);
for(rep_=0;rep_<2;rep_=rep_+1)begin
 got=0;t=0;fin=0;query_ready=0;max_fifo=0;correction_seen=0;row0=4006+rep_*8;
 req_beats=0;rsp_beats=0;req_stall=0;slot_stall=0;queued=0;max_queued=0;ref_head=0;scheduled_wait=0;return_wait=0;return_full=0;
 @(negedge efck);ed=0;ed[0]=1;ed[2:1]=2;ed[17:3]=15'(row0);ed[70:62]=342;launch=$time;
 @(negedge efck);ed[0]=0;
 while(got<1368)begin
  @(negedge sclk);
  if($time-launch>=query_ns*1000)query_ready=1;
  if(link_fault)$fatal(1,"coded crossing poisoned got=%0d",got);
  if(fault)$fatal(1,"svc fault got=%0d",got);
  t=t+1;if(t>2000000)$fatal(1,"protocol timeout got=%0d",got);
 end
 query_ready=0;
 repeat(200)@(negedge clk);
 if(fifo_ne!=0)$fatal(1,"residual FIFO lines");
 if(link_fault)$fatal(1,"coded crossing poisoned during drain");
 if((CODE_MUT==1||CODE_MUT==2)&&!correction_seen)$fatal(1,"missing correction witness");
 if(fault)$fatal(1,"fault during final credit drain");
 $display("IKS_PREFETCH rep=%0d phase_ns=%0d query_hold_ns=%0d keyleg=%0d code_mut=%0d correction_seen=%0d score_phase_ps=%0d lines=%0d max_fifo=%0d last_line_ns=%0.3f exposed_after_query_ns=%0.3f",rep_,phase,query_ns,KEYLEG,CODE_MUT,correction_seen,score_phase_ps,got,max_fifo,(lastline-launch)/1000.0,(lastline-launch-query_ns*1000)/1000.0);
end
$display("PASS_HBM_SVC_IKS_PREFETCH");$finish;
end
endmodule
