`timescale 1ps/1ps
// Timed full-shape actual IKS service with REFpb; pattern exactness and final-credit drain.
module tb_hbm_svc_iks_prefetch #(parameter REF_MODE=3,PULL=0,BATCH=0,KEY_DEPTH=64,MAXREAD=15,STREAM_PS=1024,KEYLEG=24,CODE_MUT=0,PORTAL=0,CONTROL=0,EARLY=0);
reg clk=0,sclk=0,efck=0,rst_n=0;always #512 clk=~clk;
always begin #416 efck=1;#417 efck=0;end
integer score_phase_ps=0;
initial begin if($value$plusargs("score_phase_ps=%d",score_phase_ps))begin end #(score_phase_ps);forever begin #416 sclk=1;#417 sclk=0;end end
reg[127:0] ed=0;wire[31:0]kv,krdy,kwe,rv,rrdy;wire[959:0]addr;wire[127:0]len,beat;wire[543:0]tag,rtag;
wire[8191:0]data_;wire[8791:0]lines;wire done,fault;wire[7:0]credit;
wire phy_clk,phy_rst_n;wire[8191:0]rawdata;wire[8191:0]wdata;wire[1023:0]wstrb;wire[31:0]wdone;
assign data_=rawdata ^ ((mut==1 && rv[5]) ? (8192'd1 << (5*256)) : 8192'd0);
ot_hbm_svc_core #(.IKS(1),.IK_PREFETCH(PORTAL),.IK_DEPTH(KEY_DEPTH),.KNO(MAXREAD),.E_ST(11),.XST(2))dut(.ck(clk),.rst(rst_n),.q_d(336'd0),.q_v(8'd0),.q_fclk(8'd0),.q_rdy(),.line(),.fclk(),
.e_d(ed),.e_fclk(efck),.kv(),.ik(),.phy_clk(phy_clk),.phy_rst_n(phy_rst_n),.k_v(kv),.k_rdy(krdy),.k_addr(addr),.k_len(len),.k_tag(tag),.k_we(kwe),.k_wdata(wdata),.k_wstrb(wstrb),
.kr_v(rv),.kr_rdy(rrdy),.kr_tag(rtag),.kr_beat(beat),.kr_data(data_),.w_v(),.w_rdy(1'b0),.w_addr(),.w_len(),.w_tag(),.w_room(8'd0),.wr_v(8'd0),.wr_rdy(),.wr_tag(80'd0),.wr_beat(40'd0),.wr_data(2048'd0),
.wq_d(292'd0),.wq_fclk(1'b0),.wq_g(),.k_wr_done(wdone),.kvs(),.kvs_done(),.ik_credit(credit),.ik_lines(lines),.ik_done(done),.ik_fault(fault),.ip_v(portal_v),.ip_d(portal_d),.ip_fault(PORTAL?sink_fault:1'b0),.ip_take(portal_take));
ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.DW(256),.MEM_WORDS(1024),.TAGW(17),.LENW(4),.BEATW(4),.QD(64),.REFPB(REF_MODE),.PULLIN(PULL),.PULLIN_BATCH(BATCH),.MEM_MODE(1),.CLK_PS(STREAM_PS)) mem(
.clk(phy_clk),.rst_n(phy_rst_n),.req_v(kv),.req_rdy(krdy),.req_addr(addr),.req_len(len),.req_tag(tag),.req_we(kwe),.req_wdata(wdata),.req_wstrb(wstrb),.wr_done(wdone),.rsp_v(rv),.rsp_rdy(rrdy),.rsp_tag(rtag),.rsp_beat(beat),.rsp_data(rawdata));
reg portal_req_v=0,portal_receipt_r=0;
reg[98:0]portal_req_d=0;
wire portal_req_r,portal_receipt_v,source_fault,sink_fault,portal_v,portal_take;
wire[98:0]portal_d;wire[72:0]portal_receipt_frame;
wire[106:0]portal_rq_code;wire[80:0]portal_rc_code;
wire[1:0]portal_rq_epoch,portal_rc_epoch,portal_release;
reg command_v=0,key_visible=0,producer_published=0,producer_drained=0;
reg[72:0]command_frame=0;reg[14:0]command_row=0;
wire command_r,control_prefetch_v,control_start_v,control_done,control_fault,control_retained;
wire[72:0]control_frame;wire[14:0]control_row;wire[5:0]control_layer;wire[13:0]control_ndie;
wire[89:0]control_fs;wire[344:0]control_kin;wire[6:0]control_rank;
reg control_done_seen=0;integer held_credit_witness=0;
wire request_v=CONTROL?control_prefetch_v:portal_req_v;
wire[98:0]request_d=CONTROL?{control_frame,control_row,9'd342,2'd2}:portal_req_d;
wire receipt_r=CONTROL?control_prefetch_v:portal_receipt_r;
ot_hbm_native_index_control #(.ENABLE(CONTROL),.PREFETCH(1)) actual_control(
 .clk(efck),.por_n(rst_n),.owner_valid(1'b1),.owner_fault(1'b0),.allocation_granted(1'b1),
 .owner_frame(command_frame),.allocation_frame(command_frame),.producer_published(producer_published),
 .producer_drained(producer_drained),.selector_idle(1'b1),.command_v(command_v),.command_r(command_r),
 .command_frame(command_frame),.command_rank(7'd17),.command_ndie(14'd2736),.command_k(10'd512),
 .command_cand(1'b0),.command_keep(1'b0),.command_layer(6'(rep_)),.command_key_row0(command_row),
 .key_visible(key_visible),.key_visibility_frame(command_frame),.prefetch_v(control_prefetch_v),
 .prefetch_accepted(portal_receipt_v&&receipt_r),.prefetch_accepted_frame(portal_receipt_frame),
 .held_layer(control_layer),.held_key_row0(control_row),.held_ndie(control_ndie),
 .keep_v(1'b0),.keep_r(),.keep_frame(73'd0),.keep_quarter(2'd0),.keep_bitmap(342'd0),
 .fs(control_fs),.kin(control_kin),.source_start_v(control_start_v),.source_start_r(1'b1),
 .held_frame(control_frame),.held_rank(control_rank),.source_done(got==1368),
 .index_event(got==1368?2'b01:2'b00),.returns_drained(!dut.gkvs.idx_busy),
 .source_idle(got==1368&&fifo_ne==0),.retained(control_retained),.done(control_done),.fault(control_fault));
always@(posedge efck)if(rst_n&&CONTROL)begin
 if(control_fault)$fatal(1,"actual dynamic controller fault");
 if(control_done)control_done_seen=1;
 if(control_start_v)query_ready=1;
 if(!key_visible&&actual_accepts!=rep_)$fatal(1,"service admission before actual key visibility fence");
end
always@(posedge clk)if(rst_n&&EARLY&&rep_==1&&portal_v&&dut.gkvs.idx_busy)begin
 held_credit_witness=held_credit_witness+1;
 if(portal_take)$fatal(1,"next frame admitted before old line credits retired");
end
reg receipt_seen=0;time receipt_time;
integer actual_accepts=0;
ot_hbm_index_prefetch_source source_mailbox(.clk(efck),.rst_n(rst_n),.req_v(request_v),.req_d(request_d),.req_r(portal_req_r),
 .receipt_v(portal_receipt_v),.receipt_r(receipt_r),.receipt_frame(portal_receipt_frame),.fault(source_fault),
 .rq_w(portal_rq_code),.rq_epoch(portal_rq_epoch),.rc_w(portal_rc_code),.rc_epoch(portal_rc_epoch),.rc_fault(sink_fault),.rc_release(portal_release));
ot_hbm_index_prefetch_sink sink_mailbox(.clk(clk),.rst_n(rst_n),.rq_w(portal_rq_code),.rq_epoch(portal_rq_epoch),
 .ip_v(portal_v),.ip_d(portal_d),.ip_take(portal_take),.fault(sink_fault),.rc_w(portal_rc_code),.rc_epoch(portal_rc_epoch),.rc_release(portal_release));
always@(posedge clk)if(portal_take)begin
 actual_accepts=actual_accepts+1;
 if(portal_d!==request_d)$fatal(1,"portal admitted wrong descriptor");
 $display("IKS_PORTAL actual_accepts=%0d frame73=%h at_ps=%0t",actual_accepts,portal_d[98:26],$time);
end
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
 got=0;t=0;fin=0;query_ready=0;max_fifo=0;correction_seen=0;receipt_seen=0;portal_receipt_r=0;row0=4006+rep_*8;
 req_beats=0;rsp_beats=0;req_stall=0;slot_stall=0;queued=0;max_queued=0;ref_head=0;scheduled_wait=0;return_wait=0;return_full=0;
 @(negedge efck);ed=0;
 if(PORTAL)begin portal_req_d={73'(73'h12ab34001200345678+rep_),15'(row0),9'd342,2'd2};portal_req_v=1;end
 else begin ed[0]=1;ed[2:1]=2;ed[17:3]=15'(row0);ed[70:62]=342;end
 launch=$time;
 if(CONTROL)begin
  command_frame=portal_req_d[98:26];command_row=row0;
  key_visible=0;producer_published=0;producer_drained=0;control_done_seen=0;
  while(!command_r)@(negedge efck);command_v=1;
  @(negedge efck);command_v=0;
  repeat(70)@(negedge efck);
  if(actual_accepts!=rep_)$fatal(1,"core accepted before visibility fence");
  key_visible=1;
 end
 @(negedge efck);ed[0]=0;
 while(got<1368)begin
  @(negedge sclk);
  if(PORTAL)begin
   if(source_fault||sink_fault)$fatal(1,"prefetch mailbox fault");
   if(portal_receipt_v&&!receipt_seen)begin
    if(portal_receipt_frame!==request_d[98:26])$fatal(1,"prefetch receipt identity");
    if(actual_accepts!=rep_+1)$fatal(1,"receipt before actual core admission");
    receipt_seen=1;receipt_time=$time;portal_receipt_r=1;portal_req_v=0;
   end
   if(receipt_seen&&!portal_receipt_v)portal_receipt_r=0;
   if(receipt_seen&&$time-receipt_time>=query_ns*1000)begin
    if(CONTROL)begin producer_published=1;producer_drained=1;end
    else query_ready=1;
   end
  end else if($time-launch>=query_ns*1000)query_ready=1;
  if(link_fault)$fatal(1,"coded crossing poisoned got=%0d",got);
  if(fault)$fatal(1,"svc fault got=%0d",got);
  t=t+1;if(t>2000000)$fatal(1,"protocol timeout got=%0d",got);
 end
 query_ready=0;
 if(!EARLY)repeat(200)@(negedge clk);
 if(CONTROL)begin
  t=0;while(!control_done_seen)begin @(negedge efck);t=t+1;if(t>1000)$fatal(1,"controller retirement debt");end
  if(dut.gkvs.idx_busy||fifo_ne!=0)$fatal(1,"controller retired before transport drained");
  $display("IKS_CONTROL full73=%h row15=%0d layer=%0d accepted=%0d retired=1",command_frame,command_row,rep_,actual_accepts);
  @(negedge efck);key_visible=0;
 end
 if(fifo_ne!=0)$fatal(1,"residual FIFO lines");
 if(PORTAL&&(!receipt_seen||actual_accepts!=rep_+1))$fatal(1,"portal frame admission count");
 if(link_fault)$fatal(1,"coded crossing poisoned during drain");
 if((CODE_MUT==1||CODE_MUT==2)&&!correction_seen)$fatal(1,"missing correction witness");
 if(fault)$fatal(1,"fault during final credit drain");
 $display("IKS_PREFETCH rep=%0d phase_ns=%0d query_hold_ns=%0d keyleg=%0d code_mut=%0d correction_seen=%0d score_phase_ps=%0d lines=%0d max_fifo=%0d last_line_ns=%0.3f exposed_after_query_ns=%0.3f",rep_,phase,query_ns,KEYLEG,CODE_MUT,correction_seen,score_phase_ps,got,max_fifo,(lastline-launch)/1000.0,(lastline-(PORTAL?receipt_time:launch)-query_ns*1000)/1000.0);
end
if(EARLY&&held_credit_witness==0)$fatal(1,"missing early next-frame held-credit witness");
$display("IKS_RETENTION early=%0d held_credit_cycles=%0d",EARLY,held_credit_witness);
$display("PASS_HBM_SVC_IKS_PREFETCH");$finish;
end
endmodule
