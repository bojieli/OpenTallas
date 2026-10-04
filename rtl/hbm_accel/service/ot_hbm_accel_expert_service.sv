`timescale 1ps/1fs
// CK/2 expert service: finite retained requests, real row/column handshakes,
// strict REFpb, saved owner/tag/beat return mapping, actual consumer ACK credits.
// Read-only successor. Other clients/WRITE fences stay on the causal provider.
module ot_hbm_accel_expert_service #(parameter ENABLE=0,STACK=0,DIE=0,PHASE=0)(
 input wire clk,por_n,run_enable,
 input wire req_v,output wire req_r,input ot_hbm_r14_pkg::request_t req,
 output wire[31:0] row_v,input wire[31:0] row_gnt,
 output wire[95:0] row_op,output wire[159:0] row_bank,output wire[607:0] row_row,
 output wire[31:0] col_v,input wire[31:0] col_gnt,
 output ot_hbm_r14_pkg::command_t col_cmd[0:31],
 input wire[31:0] rsp_v,output wire[31:0] rsp_r,
 input wire[511:0] rsp_tag,input wire[159:0] rsp_beat,input wire[8191:0] rsp_data,
 output wire[31:0] owned_v,input wire[31:0] owned_r,
 output ot_hbm_r14_pkg::owned_t owned[0:31],output wire fault,output wire idle);
 import ot_hbm_r14_pkg::*;import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign req_r=0;assign row_v=0;assign row_op=0;assign row_bank=0;assign row_row=0;
  assign col_v=0;assign rsp_r=0;assign owned_v=0;assign fault=0;assign idle=1;
  for(genvar p=0;p<32;p=p+1)begin assign col_cmd[p]='0;assign owned[p]='0;end
 end else begin:on
  typedef struct packed {logic live;logic[5:0] gen;identity_t id;logic[5:0] len;
                         logic[31:0] issued,returned,acked;} context_t;
  typedef struct packed {logic[47:0] slots;logic[2:0] wp,rp;logic[3:0] count;} queue_t;
  typedef struct packed {logic cur_v,next_v;logic[5:0] cur,next;} owner_t;
  context_t contexts[0:63],cn[0:63];reg[359:0] context_seal[0:63];
  queue_t queues[0:31],qn[0:31];reg[71:0] queue_seal[0:31];
  owner_t owners[0:31],onext[0:31];reg[71:0] owner_seal[0:31];
  reg sticky;reg[71:0] sticky_seal;
  function automatic[359:0] seal_context(input context_t c);
   for(integer k=0;k<5;k=k+1)seal_context[k*72+:72]=encode64(64'(320'(c)>>(k*64)));
  endfunction
  wire[63:0] context_bad;wire[31:0] queue_bad,owner_bad,pc_fault,fifo_fault,fifo_empty;
  for(genvar s=0;s<64;s=s+1)assign context_bad[s]=context_seal[s]!=seal_context(contexts[s]);
  for(genvar p=0;p<32;p=p+1)begin
   assign queue_bad[p]=queue_seal[p]!=encode64(64'(queues[p]));
   assign owner_bad[p]=owner_seal[p]!=encode64(64'(owners[p]));
  end
  wire bad=(|context_bad)||(|queue_bad)||(|owner_bad)||(sticky_seal!=encode64(64'(sticky)));
  assign fault=sticky||bad||(|pc_fault)||(|fifo_fault);
  wire legal=!req.we && req.len!=0 && req.len<=32 && req.len[1:0]==0 && req.id.sector[1:0]==0 &&
    req.id.stack==2'(STACK) && req.id.die==1'(DIE) &&
    ({1'b0,req.id.sector}+35'(req.len)<=CAPACITY_SECTORS) &&
    (({1'b0,req.id.sector[6:0]}+8'(req.len))<=128);
  reg free_v,room;reg[5:0] free_slot;reg[31:0] wanted;
  always @*begin
   wanted=0;for(integer b=0;b<32;b=b+1)if(b<req.len)wanted[pc_of(req.id.sector+34'(b))]=1;
   free_v=0;free_slot=0;for(integer s=63;s>=0;s=s-1)if(!contexts[s].live)begin free_v=1;free_slot=6'(s);end
   room=1;for(integer p=0;p<32;p=p+1)if(wanted[p]&&queues[p].count==8)room=0;
  end
  assign req_r=run_enable&&legal&&free_v&&room&&!fault;
  wire admit=req_v&&req_r;
  wire[31:0] desc_v,desc_r,busy,win_end,win_next,return_v,return_r;
  wire[159:0] cb,cc;wire[95:0] cred;
  wire[272:0] return_word[0:31];wire[31:0] return_put_r,return_legal;
  reg[33:0] desc_sector[0:31];reg[4:0] issued_beat[0:31];
  wire[5:0] front[0:31];wire[11:0] physical_tag[0:31];
  for(genvar p=0;p<32;p=p+1)begin:pc
   assign front[p]=queues[p].slots[queues[p].rp*6+:6];
   assign desc_v[p]=run_enable&&queues[p].count!=0&&!fault;
   always @*begin
    desc_sector[p]=contexts[front[p]].id.sector;
    for(integer b=31;b>=0;b=b-1)if(b<contexts[front[p]].len&&pc_of(contexts[front[p]].id.sector+34'(b))==5'(p))
      desc_sector[p]=contexts[front[p]].id.sector+34'(b);
    issued_beat[p]=0;
    for(integer b=31;b>=0;b=b-1)if(b<contexts[owners[p].cur].len&&pc_of(contexts[owners[p].cur].id.sector+34'(b))==5'(p)&&
       bank_of(contexts[owners[p].cur].id.sector+34'(b))==cb[p*5+:5])issued_beat[p]=5'(b);
   end
   wire[4:0] db=bank_of(desc_sector[p]);
   assign physical_tag[p]={contexts[owners[p].cur].gen,owners[p].cur};
   ot_hbm_accel_stream_pc #(.ENABLE(1),.PC(p),.CRED(32),.REF_MODE(1),
    .REF_PHASE((PHASE+p*118/32)%118)) controller(.clk(clk),.rst_n(por_n),
    .desc_v(desc_v[p]),.desc_r(desc_r[p]),.desc_row(19'(desc_sector[p]>>15)),.desc_n(11'd4),
    .desc_first({1'b0,db[4:2],desc_sector[p][11:7],2'b00}),
    .go(run_enable&&!fault),.next_posted(owners[p].next_v),.col_gnt(col_gnt[p]&&run_enable&&!fault),
    .window_end(win_end[p]),.window_next(win_next[p]),
    .row_v(row_v[p]),.row_prio(),.row_gnt(row_gnt[p]),.row_op(row_op[p*3+:3]),
    .row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
    .col_v(col_v[p]),.col_bank(cb[p*5+:5]),.col_col(cc[p*5+:5]),
    .cred_ret(cred[p*3+:3]),.busy(busy[p]),.ref_fault(pc_fault[p]));
   assign col_cmd[p]='{op:RD,pc:5'(p),bank:cb[p*5+:5],row:19'(contexts[owners[p].cur].id.sector>>15),
    sector:contexts[owners[p].cur].id.sector+34'(issued_beat[p]),tag:physical_tag[p],beat:issued_beat[p],data:256'b0};
   wire[11:0] rt=rsp_tag[p*16+:12];wire[5:0] slot=rt[5:0];wire[4:0] beat=rsp_beat[p*5+:5];
   assign return_legal[p]=contexts[slot].live&&contexts[slot].gen==rt[11:6]&&rsp_tag[p*16+12+:4]==0&&
    beat<contexts[slot].len&&pc_of(contexts[slot].id.sector+34'(beat))==5'(p)&&
    contexts[slot].issued[beat]&&!contexts[slot].returned[beat];
   assign rsp_r[p]=return_put_r[p]&&return_legal[p]&&!fault;
   ot_hbm_accel_return_fifo returns(.clk(clk),.por_n(por_n),.iv(rsp_v[p]&&return_legal[p]&&!fault),
    .ir(return_put_r[p]),.id({rt,beat,rsp_data[p*256+:256]}),.ov(return_v[p]),.ore(return_r[p]),
    .od(return_word[p]),.fault(fifo_fault[p]),.empty(fifo_empty[p]));
   wire[11:0] out_tag=return_word[p][272:261];wire[4:0] out_beat=return_word[p][260:256];
   wire[5:0] out_slot=out_tag[5:0];
   wire out_legal=contexts[out_slot].live&&contexts[out_slot].gen==out_tag[11:6]&&
    contexts[out_slot].returned[out_beat]&&!contexts[out_slot].acked[out_beat]&&
    pc_of(contexts[out_slot].id.sector+34'(out_beat))==5'(p);
   assign owned_v[p]=return_v[p]&&out_legal&&!fault;
   assign return_r[p]=owned_r[p]&&owned_v[p];
   identity_t out_id;always @*begin out_id=contexts[out_slot].id;out_id.sector=out_id.sector+34'(out_beat);end
   assign owned[p]='{id:out_id,data:return_word[p][255:0],physical_tag:out_tag,beat:out_beat};
   assign cred[p*3+:3]=3'(owned_v[p]&&owned_r[p]);
  end
  reg next_sticky;reg live_any;
  always @*begin
   next_sticky=sticky;live_any=0;
   for(integer t=0;t<64;t=t+1)begin cn[t]=contexts[t];if(contexts[t].live)live_any=1;end
   for(integer p=0;p<32;p=p+1)begin
    qn[p]=queues[p];onext[p]=owners[p];
    if(desc_v[p]&&desc_r[p])begin
     qn[p].rp=queues[p].rp+1'b1;qn[p].count=qn[p].count-1'b1;
     if(busy[p])begin onext[p].next=front[p];onext[p].next_v=1;end
     else begin onext[p].cur=front[p];onext[p].cur_v=1;end
    end
    if(win_end[p])begin
     if(win_next[p])begin onext[p].cur=owners[p].next_v?owners[p].next:front[p];onext[p].cur_v=1;onext[p].next_v=0;end
     else onext[p].cur_v=0;
    end
    if(col_v[p]&&col_gnt[p])begin
     if(!owners[p].cur_v||!contexts[owners[p].cur].live||contexts[owners[p].cur].issued[issued_beat[p]])next_sticky=1;
     else cn[owners[p].cur].issued[issued_beat[p]]=1;
    end
    if(rsp_v[p]&&!return_legal[p])next_sticky=1;
    if(rsp_v[p]&&rsp_r[p])cn[rsp_tag[p*16+:6]].returned[rsp_beat[p*5+:5]]=1;
    if(owned_v[p]&&owned_r[p])cn[owned[p].physical_tag[5:0]].acked[owned[p].beat]=1;
   end
   for(integer t=0;t<64;t=t+1)if(cn[t].live&&cn[t].acked==beat_mask(cn[t].len))cn[t].live=0;
   if(req_v&&!legal)next_sticky=1;
   if(admit)begin
    cn[free_slot]='{live:1'b1,gen:contexts[free_slot].gen+6'd1,id:req.id,len:req.len,issued:32'b0,returned:32'b0,acked:32'b0};
    for(integer p=0;p<32;p=p+1)if(wanted[p])begin
     qn[p].slots[queues[p].wp*6+:6]=free_slot;qn[p].wp=queues[p].wp+1'b1;qn[p].count=qn[p].count+1'b1;
    end
   end
  end
  assign idle=!live_any&&!(|busy)&&(&fifo_empty);
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin
    sticky<=0;sticky_seal<=0;
    for(integer t=0;t<64;t=t+1)begin contexts[t]<='0;context_seal[t]<=0;end
    for(integer p=0;p<32;p=p+1)begin queues[p]<='0;queue_seal[p]<=0;owners[p]<='0;owner_seal[p]<=0;end
   end else if(!fault)begin
    sticky<=next_sticky;sticky_seal<=encode64(64'(next_sticky));
    for(integer t=0;t<64;t=t+1)begin contexts[t]<=cn[t];context_seal[t]<=seal_context(cn[t]);end
    for(integer p=0;p<32;p=p+1)begin queues[p]<=qn[p];queue_seal[p]<=encode64(64'(qn[p]));
      owners[p]<=onext[p];owner_seal[p]<=encode64(64'(onext[p]));end
   end
  end
 end endgenerate
endmodule
