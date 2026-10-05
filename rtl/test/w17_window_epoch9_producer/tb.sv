`timescale 1ns/1ps
// PREPARED, NOT COMPILED. Synthetic QE-capture output -> actual blocks+guard ->
// qualified source -> actual owner mux/KARB/idx_hbm -> actual descriptor lifecycle.
// No engine/QE arithmetic, full-wrapper overlay, checkpoint data, or fault recovery.
module tb #(parameter integer RETAIN=0);
 localparam integer BASE=262144,POS=1048575,FIRST=POS-127;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,step_v=0,cap_v=0,producer_issue=0,prime_v=0,desc_v=0,pv_mode=0;
 reg [9:0] step_user=0;reg [20:0] step_pos=0,prime_row=0;
 reg [29:0] cap_addr=0;reg [255:0] cap_codes=0;reg [7:0] cap_scale=0;
 wire cap_ready,producer_idle,producer_ready,blk_v,blk_ready,bad;
 wire [29:0] cap_base,blk_base,blk_first;wire [20:0] blk_row,blk_local;
 wire [3:0] blk_idx;wire [255:0] blk_codes;wire [7:0] blk_scale;wire producer_fault;
 wire prime_ready,start_ready,staged_v,busy,done,fault,kv_v;
 wire [4:0] fault_code;wire [31:0] refill_cycles,sectors_read,rows_fetched,blocks_written,sectors_written;
 wire [7:0] rows_refilled;wire [3:0] kv_m;wire [16959:0] kv_w;
 wire [3:0] wv,wrdy,wwe,wsv,wsrdy,wwdone,mv,mrdy,mwe,msv,msrdy,mwdone;
 wire [119:0] wa,ma;wire [15:0] wl,ml,wb,mb;
 wire [63:0] wt,mt,wst,mst;wire [1023:0] wd,md,wsd,msd;wire [127:0] wm,mm;
 wire mux_fault;
 wire [31:0] hv,hrdy,hwe,hwdone,rv,rrdy;wire [959:0] ha;wire [127:0] hl,rb;
 wire [543:0] ht,rt;wire [8191:0] hd,rd;wire [1023:0] hm;
 wire desc_accept,issue_ok,life_done,life_fault;wire [3:0] life_code;
 wire [15:0] desc_gen;wire [10:0] desc_rows,life_beats;
 reg [15:0] service_gen=0;reg engine_idle=1;
 wire issue=issue_ok&&engine_idle;
 integer primed=0,desc_count=0,life_done_count=0,source_done_count=0;
 integer writes=0,acks=0,reads=0,replies=0,beats=0,op_beats=0;
 integer last_ack=-1,logical_publish=-1,op_start[0:1],op_stage[0:1],op_done[0:1];
 integer pending_read=0,total_pending,columns=0,wr_columns=0,rd_columns=0;
 reg [4351:0] got_reply=0;
 // Column inputs sampled at negedge from stable actual backend head state.
 reg [31:0] column_valid=0,column_we=0;
 reg [29:0] column_addr[0:31];reg [16:0] column_tag[0:31];
 reg [255:0] column_data[0:31];reg [31:0] column_strb[0:31];
 longint column_ps[0:31];
 // Shadow delayed-visible storage is only the17sectors actually written.
 reg [255:0] visible[0:16];longint latest_visible_ps[0:16];
 longint visible_due[0:31];reg [255:0] visible_data[0:31];reg [31:0] visible_strb[0:31];
 integer visible_sec[0:31];reg [31:0] visibility_committed=0;
 integer lastcode_rd=0,lastscale_rd=0,reply_index,epoch,slot,sec;
 reg [255:0] expected_data;reg [264:0] expected_group;
 function automatic [255:0] pattern(input integer addr);
  reg [255:0] p;
  for(integer n=0;n<32;n=n+1) p[n*8+:8]=((addr-BASE)%17==16)?8'(120+n%5):8'(1+((addr-BASE)*3+n)%100);
  return p;
 endfunction
 function automatic [255:0] expected_sector(input integer addr);
  reg [255:0] p;p=pattern(addr);
  if(addr==BASE+127*17+16) p[255:128]={16{8'h55}};
  return p;
 endfunction
 ot_hdc_v41x_window_kv_blocks #(.AW(30),.POS_W(21),.KVT_SH(13),.SEPARATE_ROWS(1)) producer (
  .clk(clk),.rst_n(rst_n),.cap_v(cap_v),.cap_src_addr(cap_addr),.cap_codes(cap_codes),.cap_scale(cap_scale),
  .cap_ready(cap_ready),.cap_src_base(cap_base),.idle(producer_idle),.issue(producer_issue),
  .issue_src_base(30'd55232),.issue_kvt_base(30'b0),.issue_row(21'd127),.issue_abs_row(21'(POS)),
  .issue_ready(producer_ready),.blk_v(blk_v),.blk_ready(blk_ready),.blk_kvt_base(blk_base),
  .blk_row(blk_row),.blk_kvt_row(blk_local),.blk_idx(blk_idx),.blk_first_elem(blk_first),
  .blk_codes(blk_codes),.blk_scale(blk_scale),.fault(producer_fault));
 ot_chip_v41x_window_block_guard #(.AW(30),.POS_W(21)) guard (
  .step_pos(step_pos),.blk_abs_row(blk_row),.blk_kvt_row(blk_local),.blk_idx(blk_idx),
  .kvt_base(blk_base),.first_elem(blk_first),.hbm_slot(),.expected_first(),.bad(bad));
 // Tile's unchanged assign win_blk_user=window_user is represented by step_user.
 ot_chip_v41x_window_attn_source #(.WIN_STACK(2),.STREAM_II1(0),.REFILL_CREDITS(8),.RETAIN_L0(RETAIN)) win (
  .clk(clk),.rst_n(rst_n),.retain_qk(!pv_mode),.retain_pv(pv_mode),
  .retain_complete(life_done&&engine_idle),.retain_invalidate(step_v),.retain_generation(desc_gen),
  .region_base_sector(30'(BASE)),.region_sector_count(30'd2176),
  .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(step_user),.prime_row(prime_row),
  .blk_v(blk_v&&!bad),.blk_ready(blk_ready),.blk_user(step_user),.blk_row(blk_row),
  .blk_idx(blk_idx),.blk_codes(blk_codes),.blk_scale(blk_scale),
  .start_v(desc_accept),.start_ready(start_ready),.start_user(step_user),.start_first(21'(FIRST)),.start_count(8'd128),
  .staged_v(staged_v),.stream_go(issue),.busy(busy),.done(done),.fault(fault),.fault_code(fault_code),
  .refill_cycles(refill_cycles),.sectors_read(sectors_read),.rows_fetched(rows_fetched),
  .blocks_written(blocks_written),.sectors_written(sectors_written),.rows_refilled(rows_refilled),
  .kv_v(kv_v),.kv_ready(!engine_idle),.kv_m(kv_m),.kv_w(kv_w),
  .m_v(wv),.m_rdy(wrdy),.m_addr(wa),.m_len(wl),.m_tag(wt),.m_we(wwe),.m_wdata(wd),.m_wstrb(wm),
  .m_wr_done(wwdone),.s_v(wsv),.s_rdy(wsrdy),.s_tag(wst),.s_beat(wb),.s_data(wsd));
 ot_chip_v41x_attn_desc_lifecycle #(.AW(30),.NW(21),.L0_ONLY(1)) life (
  .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_user(step_user),.desc_pos(21'(POS)),
  .desc_tiles(pv_mode?21'd16:21'd4),.desc_k(pv_mode?21'd128:21'd512),
  .desc_nout(pv_mode?21'd512:21'd128),.desc_wbase(30'b0),.desc_ts(pv_mode?30'd1:30'd512),
  .desc_ks(pv_mode?30'd32:30'd1),.desc_js(30'b0),.desc_hg(2'd1),.desc_mmode(1'b1),
  .desc_accept(desc_accept),.desc_gen(desc_gen),.desc_rows(desc_rows),
  .stage_v(staged_v),.stage_gen(service_gen),.stage_rows(11'd128),
  .beat_v(kv_v),.beat_ready(!engine_idle),.beat_gen(service_gen),.beat_mask(kv_m),
  .issue_v(issue),.engine_idle(engine_idle),.service_fault(fault||mux_fault||producer_fault),
  .wrap_drained(!busy&&prime_ready&&!blk_v),.issue_ok(issue_ok),.done(life_done),.fault(life_fault),
  .fault_code(life_code),.beats_accepted(life_beats));
`include "transport_body.svh"
 initial begin
  for(integer n=0;n<2176;n=n+1) mem.mem[BASE+n]=(n/17==127)?{32{8'h55}}:pattern(BASE+n);
  for(integer n=0;n<17;n=n+1) begin visible[n]={32{8'h55}};latest_visible_ps[n]=0;end
  for(integer n=0;n<2;n=n+1)begin op_start[n]=-1;op_stage[n]=-1;op_done[n]=-1;end
  #1.1;rst_n=1;
 end
 always @(negedge clk) if(rst_n) begin
  step_v=mem.cyc==299;
  prime_v=primed<127;prime_row=21'(FIRST+primed);
  cap_v=mem.cyc>=300&&mem.cyc<316;
  cap_addr=30'(55232+(mem.cyc-300)*32);
  cap_codes=pattern(BASE+127*17+integer'(mem.cyc-300));cap_scale=8'(120+(mem.cyc-300)%5);
  producer_issue=mem.cyc==316;
  desc_v=0;
  if(desc_count==0&&acks==32) begin pv_mode=0;desc_v=1;end
  else if(desc_count==1&&life_done_count==1&&source_done_count==1) begin pv_mode=1;desc_v=1;end
  for(integer p=0;p<32;p=p+1)begin
   column_valid[p]=mem.h_sched[p]&&mem.q_n[p]>0&&mem.h_tcol[p]<=mem.cyc*1000;
   column_ps[p]=mem.h_tcol[p];
   column_addr[p]=mem.q_addr[p][mem.q_rp[p]];column_tag[p]=mem.q_tag[p][mem.q_rp[p]];
   column_we[p]=mem.q_we[p][mem.q_rp[p]];column_data[p]=mem.q_data[p][mem.q_rp[p]];
   column_strb[p]=mem.q_strb[p][mem.q_rp[p]];
  end
 end
 always @(posedge clk) if(rst_n) begin
  if(step_v)begin step_user<=0;step_pos<=21'(POS);end
  if(prime_v&&prime_ready)primed=primed+1;
  if(cap_v&&!cap_ready)$fatal(1,"capture refused");
  if(producer_issue&&!producer_ready)$fatal(1,"producer issue before FULL");
  if(blk_v&&blk_ready)begin
   if(bad||blk_idx!==4'(blocks_written)||blk_row!=POS||blk_local!=127||step_user!=0)
    $fatal(1,"producer provenance/order");
   $display("BLOCK cycle=%0d block=%0d",mem.cyc,blk_idx);
  end
  if(producer_fault||fault||mux_fault||life_fault)$fatal(1,"producer/source/lifecycle fault %0d/%0d",fault_code,life_code);
  if(desc_accept)begin
   if(desc_count>=2||!start_ready||acks!=32||!producer_idle||desc_rows!=128||desc_gen!=desc_count+1)
    $fatal(1,"descriptor admission/user/generation/drain");
   service_gen<=desc_gen;op_start[desc_count]=mem.cyc;desc_count=desc_count+1;op_beats=0;
   $display("DESCRIPTOR cycle=%0d op=%0d generation=%0d user=0 rows=128",mem.cyc,desc_count-1,desc_gen);
  end
  if(issue)engine_idle<=0;
  if(wwdone[2])begin
   acks=acks+1;last_ack=mem.cyc;
   $display("WRITE_ACK cycle=%0d count=%0d",mem.cyc,acks);
  end
  if(wv[2]&&wrdy[2])begin
   if(wa[60+:30]<BASE||wa[60+:30]>=BASE+2176||wl[8+:4]!=1)$fatal(1,"address capacity/length");
   if(wwe[2])begin
    sec=(writes%2==0)?writes/2:16;
    if(writes>=32||wa[60+:30]!=BASE+127*17+sec||wt[32+:16]!=sec||
      wm[64+:32]!==((writes%2==0)?32'hffffffff:(32'b1<<(writes/2))))$fatal(1,"write address/tag/strobe");
    writes=writes+1;
   end else begin reads=reads+1;pending_read=pending_read+1;end
   $display("REQUEST cycle=%0d pc=%0d address=%0d tag=%0d we=%0d strobe=%0d",mem.cyc,arb.kpc,wa[60+:30],{1'b1,wt[32+:16]},wwe[2],wm[64+:32]);
  end
  if(wsv[2]&&wsrdy[2])begin
   epoch=wst[32+:16]>>5;slot=(epoch-1)%128;sec=wst[32+:5];reply_index=(epoch-1)*17+sec;
   if(epoch<1||epoch>256||sec>16||got_reply[reply_index]||wb[8+:4]!=0||
     wsd[512+:256]!==expected_sector(BASE+slot*17+sec))$fatal(1,"reply epoch/data/order");
   got_reply[reply_index]=1;replies=replies+1;pending_read=pending_read-1;
   $display("REPLY cycle=%0d pc=%0d address=%0d tag=%0d op=%0d",mem.cyc,arb.ksel,BASE+slot*17+sec,{1'b1,wst[32+:16]},desc_count-1);
  end
  // Observe source logical publication separately from physical visibility.
  if(acks==32&&logical_publish<0)begin logical_publish=mem.cyc;$display("LOGICAL_PUBLISH cycle=%0d",mem.cyc);end
  for(integer n=0;n<wr_columns;n=n+1) if(!visibility_committed[n]&&visible_due[n]<=mem.cyc*1000)begin
   for(integer byteidx=0;byteidx<32;byteidx=byteidx+1)if(visible_strb[n][byteidx])visible[visible_sec[n]][byteidx*8+:8]=visible_data[n][byteidx*8+:8];
   visibility_committed[n]=1;
  end
  for(integer p=0;p<32;p=p+1)if(column_valid[p])begin
   columns=columns+1;sec=(column_addr[p]-BASE)%17;
   $display("COLUMN cycle=%0d pc=%0d tcol_ps=%0d address=%0d tag=%0d we=%0d",mem.cyc,p,column_ps[p],column_addr[p],column_tag[p],column_we[p]);
   if(column_we[p])begin
    if(wr_columns>=32)$fatal(1,"write column count");
    visible_due[wr_columns]=column_ps[p]+7274;visible_sec[wr_columns]=sec;
    visible_data[wr_columns]=column_data[p];visible_strb[wr_columns]=column_strb[p];
    latest_visible_ps[sec]=visible_due[wr_columns];wr_columns=wr_columns+1;
   end else begin
    rd_columns=rd_columns+1;
    if((column_addr[p]-BASE)/17==127)begin
     if(wr_columns!=32||column_ps[p]<latest_visible_ps[sec]||visible[sec]!==expected_sector(column_addr[p]))
      $fatal(1,"READcapture before visibility or incorrect masked data");
     if(sec==15)lastcode_rd=column_ps[p];if(sec==16)lastscale_rd=column_ps[p];
    end
   end
  end
  if(staged_v)begin
   if(op_stage[desc_count-1]>=0||pending_read||rows_refilled!=128)$fatal(1,"stage before row drain");
   op_stage[desc_count-1]=mem.cyc;
   $display("STAGE cycle=%0d op=%0d generation=%0d refill=%0d",mem.cyc,desc_count-1,service_gen,refill_cycles);
  end
  if(kv_v&&!engine_idle)begin
   if(kv_m!=15||service_gen!=desc_count||op_beats>=32)$fatal(1,"beat generation/mask/count");
   for(integer l=0;l<4;l=l+1)for(integer g=0;g<16;g=g+1)begin
    expected_data=pattern(BASE+(op_beats*4+l)*17+16);
    expected_group={1'b0,expected_data[g*8+:8],pattern(BASE+(op_beats*4+l)*17+g)};
    if(kv_w[(l*16+g)*265+:265]!==expected_group)$fatal(1,"packed producer row data mismatch");
   end
   op_beats=op_beats+1;beats=beats+1;if(op_beats==32)engine_idle<=1;
  end
  if(done)source_done_count=source_done_count+1;
  if(life_done)begin
   if(!engine_idle||op_beats!=32||busy||pending_read||writes!=32||acks!=32)$fatal(1,"lifecycle done before drain");
   op_done[desc_count-1]=mem.cyc;life_done_count=life_done_count+1;
   $display("LIFECYCLE_DONE cycle=%0d op=%0d generation=%0d",mem.cyc,desc_count-1,service_gen);
  end
  #0.001;
  if(logical_publish>=0&&!win.u_window.row_valid[127])$fatal(1,"logical row validity lost");
  total_pending=0;for(integer p=0;p<32;p=p+1)total_pending+=mem.q_n[p]+mem.r_n[p];
  if(acks==32&&(total_pending!=pending_read||total_pending!=win.u_window.refill_pending))$fatal(1,"read conservation");
  if(life_done_count==2&&source_done_count==2)begin
   if(beats!=64||blocks_written!=16||sectors_written!=32||reads!=(RETAIN?2176:4352)||replies!=reads||
      win.u_window.refill_epoch!=(RETAIN?128:256)||visibility_committed!=32'hffffffff||wr_columns!=32||rd_columns!=reads)
    $fatal(1,"final totals/visibility/no-force epochs");
   for(integer p=0;p<32;p=p+1)begin
    if(mem.q_n[p]||mem.r_n[p]||arb.kw_out[p]||arb.bw_out[p])$fatal(1,"final backend/arbiter drain");
    $display("PC_DRAIN pc=%0d reads=%0d writes=%0d refreshes=%0d activations=%0d q=%0d r=%0d",p,mem.st_rd[p],mem.st_wr[p],mem.st_ref[p],mem.st_act[p],mem.q_n[p],mem.r_n[p]);
   end
   $display("PRODUCER_LIFECYCLE_PASS retain=%0d writes=%0d acks=%0d reads=%0d replies=%0d beats=%0d epoch=%0d",RETAIN,writes,acks,reads,replies,beats,win.u_window.refill_epoch);$finish;
  end
  if(mem.cyc>200000)$fatal(1,"cycle cap");
 end
endmodule
