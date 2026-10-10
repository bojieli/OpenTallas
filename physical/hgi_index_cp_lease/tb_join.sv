`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,owner_valid=1,owner_fault=0;reg[72:0]owner_frame;
 reg cmd_v=0;wire cmd_r;reg[1818:0]cmd_rec;
 reg grant_v=0;wire grant_r;reg[72:0]grant_frame;reg[5:0]grant_layer;
 reg[6:0]grant_rank;reg[19:0]grant_pos;reg[59:0]grant_key_rows;
 reg[63:0]grant_row_ends;reg[35:0]grant_block_counts;
 reg key_visible=0,query_ACK=0,prefetch_accepted=0;
 reg[72:0]key_visible_frame,query_ACK_frame,prefetch_frame;
 wire prefetch_v,native_v,native_r;wire[1:0]prefetch_quarter;reg[1:0]prefetch_accepted_quarter;
 wire[1818:0]native_rec;wire[75:0]lease_event;reg stale_native_receipt=0;
 wire[72:0]native_accepted_frame=lease_event[75:3]^(stale_native_receipt?73'd1:73'd0);
 assign native_r=lease_event[0];
 wire[72:0]held_frame;wire[5:0]held_layer;wire[6:0]held_rank;
 wire[14:0]held_key_row0;wire[8:0]held_blocks;wire[59:0]held_key_rows;wire[35:0]held_block_counts;
 reg reads_drained=0,consumer_done=0,VM_ACKs_drained=0;reg[72:0]drain_frame;
 reg source_idle=1,selector_idle=1,release_r=0;wire release_v,retained,fault;
 ot_hgi_index_cp_lease #(.ENABLE(1)) dut(.*);
 wire[89:0]fs;wire[1047:0]qb;wire[337:0]vmq;wire[2:0]ret;
 reg[273:0]vmr=0;
 hfd_hgi_idx_lease native(.ck(clk),.rst(!por_n),.f_hgi_cmdproc(native_rec),
  .f_index_lease({held_frame,native_v}),.t_index_lease(lease_event),
  .f_hgi_vmr(vmr),.t_hgi_vmq(vmq),.t_hgi_cmdproc(ret),.t_sel_fs(fs),.t_sel_qb(qb),
  .f_sel_co(72'd0),.f_sel_ev(2'd0),.f_sel_qbr(1'b0),.f_sel_to(612'd0));
 integer accepted=0,frames=0,requests=0,mode=0,i,waits=0;
 // Transactional minimum VM responder echoes real request tags; no writes,
 // publication/service grants or selector-completion receipts are fabricated.
 always@(negedge clk)begin
  vmr=0;
  if(vmq[337])begin
   vmr[273]=1;vmr[272:257]=vmq[15:0];vmr[255:0]={8{32'h3f800000}};
   requests=requests+1;
  end
 end
 always@(posedge clk)begin #1;
  if(lease_event[0])begin
   accepted=accepted+1;
   if(lease_event[75:3]!==owner_frame)$fatal(1,"actual accepted frame mismatch");
  end
  if(lease_event[2])$fatal(1,"unexpected native unit fault");
  if(fs[0])begin
   frames=frames+1;
   if(fs[32:1]!=42||fs[36:33]!=5||fs[56:37]!=7)$fatal(1,"actual fs job/gen/pos alias");
  end
 end
 task tick;begin @(posedge clk);#2;@(negedge clk);#1;end endtask
 task check(input bit ok,input[255:0]msg);begin if(!ok)begin $display("CP_INDEX_JOIN FAIL MODE%0d %0s",mode,msg);$fatal(1);end end endtask
 initial begin
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  owner_frame=(73'd7<<53)|(73'd5<<32)|73'd42;cmd_rec=0;
  cmd_rec[0]=1;cmd_rec[32:1]=20;cmd_rec[64:33]=40;cmd_rec[76:65]=1;cmd_rec[100:94]=7'b0010011;
  cmd_rec[1810:1791]=7;cmd_rec[1818:1811]=103;
  cmd_rec[129+:2]=1;cmd_rec[177+:20]=4096;cmd_rec[197+:20]=1;
  cmd_rec[385+:2]=1;cmd_rec[1153+:2]=1;cmd_rec[1155+:3]=5;
  grant_frame=owner_frame;grant_layer=20;grant_rank=7;grant_pos=7;
  grant_key_rows={15'd1300,15'd900,15'd500,15'd100};grant_row_ends={16'd1700,16'd1300,16'd900,16'd500};grant_block_counts=5;
  key_visible_frame=owner_frame;query_ACK_frame=owner_frame;prefetch_frame=owner_frame;drain_frame=owner_frame;prefetch_accepted_quarter=0;
  repeat(12)tick;por_n=1;repeat(12)tick;
  check(cmd_r,"real actor dispatch ready");cmd_v=1;tick;cmd_v=0;
  // Upstream rec may change after actual capture. The actor keeps the exact
  // record and metadata through both actual three-stage wrapper crossings.
  cmd_rec=0;
  repeat(16)begin tick;check(retained&&!native_v&&accepted==0&&requests==0,"missing grant emits nothing");end
  if(mode==1)begin
   grant_frame=owner_frame^1;grant_v=1;tick;grant_v=0;
   repeat(16)tick;check(fault&&retained&&!release_v&&accepted==0&&requests==0,"stale grant blocked before unit");
  end else begin
   grant_v=1;tick;grant_v=0;
   repeat(8)begin tick;check(!native_v&&accepted==0&&requests==0,"missing visibility emits nothing");end
   key_visible=1;query_ACK=1;tick;key_visible=0;query_ACK=0;
   for(i=0;i<4;i=i+1)begin
    if(held_blocks!=0)begin prefetch_accepted=1;prefetch_accepted_quarter=i;end
    tick;prefetch_accepted=0;
   end
   check(native_v,"native command released after real prerequisites");
   if(mode==2)stale_native_receipt=1;
   waits=0;while(accepted==0&&waits<30)begin tick;waits=waits+1;end
   check(accepted==1,"actual source acceptance event");tick;
   if(mode==2)begin repeat(8)tick;check(fault&&retained&&!release_v,"stale launched receipt retains");end
   else begin
    check(!native_v&&!fault,"framed acceptance captured");
    waits=0;while(frames==0&&waits<300)begin tick;waits=waits+1;end
    check(frames==1&&requests>=4,"actual native frame after actual weight reads");
    repeat(24)begin tick;check(accepted==1&&retained&&!release_v,"done/read/VM drains remain OPEN");end
    if(mode==3)begin drain_frame=owner_frame^1;reads_drained=1;tick;reads_drained=0;check(fault&&retained&&!release_v,"stale real drain boundary");end
   end
  end
  $display("CP_INDEX_JOIN PASS MODE%0d actual_accepts=%0d actual_frames=%0d VM_reads=%0d capture3_launch3=1 retirement_OPEN=1",mode,accepted,frames,requests);$finish;
 end
endmodule
