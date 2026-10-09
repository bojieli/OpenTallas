`timescale 1ps/1fs
`default_nettype none
// Dynamic metadata controller. The enclosing CP owns the full73 lease; this
// block neither allocates VM storage nor substitutes issued writes for ACKs.
// Native query credit and VM/router output joins are separate actual children.
// strip-protect 2026-10-09 (REVIEW_20261009 S4/X3): PROTECT=0 (default) removes the rejected flop-level protection;
// PROTECT=1 is the original, bit for bit.  Fault-free behaviour is identical (physical/strip_protect/bench.py).
module ot_hbm_native_index_control #(parameter integer ENABLE=0,PREFETCH=0,PROTECT=0)(
 input wire clk,por_n,
 input wire owner_valid,owner_fault,allocation_granted,
 input wire [72:0] owner_frame,allocation_frame,
 input wire producer_published,producer_drained,selector_idle,
 input wire command_v,output wire command_r,
 input wire [72:0] command_frame,input wire [6:0] command_rank,
 input wire [13:0] command_ndie,input wire [9:0] command_k,
 input wire command_cand,command_keep,
 input wire [5:0] command_layer,input wire [14:0] command_key_row0,
 // Actual paired append completion/fence receipt, independent of query values.
 input wire key_visible,input wire [72:0] key_visibility_frame,
 output wire prefetch_v,input wire prefetch_accepted,
 input wire [72:0] prefetch_accepted_frame,
 output wire [5:0] held_layer,output wire [14:0] held_key_row0,
 output wire [13:0] held_ndie,
 input wire keep_v,output wire keep_r,input wire [72:0] keep_frame,
 input wire [1:0] keep_quarter,input wire [341:0] keep_bitmap,
 output wire [89:0] fs,output wire [344:0] kin,
 output wire source_start_v,input wire source_start_r,
 output wire [72:0] held_frame,output wire [6:0] held_rank,
 input wire source_done,input wire [1:0] index_event,
 input wire returns_drained,source_idle,
 output wire retained,output wire done,output wire fault
);
 localparam integer DW=127;
 localparam [3:0] IDLE=0,WAITPUB=1,KEEP=2,EMITKEEP=3,GAP=4,
                  FRAME=5,STARTGAP=6,START=7,RUN=8,RETIRE=9,FAULT=10;
 reg [DW-1:0] desc,desc_n;
 reg [343:0] mask,mask_n;
 // {prefetch_accepted,source_done_seen,index_done_seen,gap2,seen4,state4}
 reg [12:0] ctl,ctl_n;
 reg [DW-1:0] next_desc;
 reg [343:0] next_mask;
 reg [12:0] next_ctl;
 wire [3:0] state=ctl[3:0];
 wire [3:0] seen=ctl[7:4];
 wire [1:0] gap=ctl[9:8];
 wire index_seen=ctl[10],source_seen=ctl[11];
 wire coded_ok=(PROTECT==0)||((desc_n==~desc)&&(mask_n==~mask)&&(ctl_n==~ctl));
 wire active=state!=IDLE;
 wire lease_ok=owner_valid&&!owner_fault&&allocation_granted&&
               owner_frame==allocation_frame&&(!active||owner_frame==desc[72:0]);
 wire enabled=ENABLE&&coded_ok&&state!=FAULT;
 assign command_r=enabled&&state==IDLE&&lease_ok&&selector_idle;
 assign keep_r=enabled&&state==KEEP&&lease_ok&&keep_frame==desc[72:0]&&!seen[keep_quarter];
 assign held_frame=desc[72:0];assign held_rank=desc[79:73];
 assign held_layer=desc[126:121];assign held_key_row0=desc[120:106];
 assign held_ndie=desc[93:80];
 assign prefetch_v=enabled&&PREFETCH&&lease_ok&&active&&state!=RETIRE&&
                   !ctl[12]&&key_visible&&key_visibility_frame==desc[72:0];
 assign fs=(enabled&&lease_ok&&state==FRAME)?
   {desc[105],desc[104],desc[103:94],desc[93:80],desc[79:73],
    desc[72:53],desc[35:32],desc[31:0],1'b1}:90'd0;
 assign kin=(enabled&&lease_ok&&state==EMITKEEP)?{mask,1'b1}:345'd0;
 assign source_start_v=enabled&&state==START&&lease_ok;
 assign retained=ENABLE&&active;
 assign done=enabled&&lease_ok&&state==RETIRE;
 assign fault=ENABLE&&(!coded_ok||state==FAULT);
 always @* begin
  next_desc=desc;next_mask=mask;next_ctl=ctl;
  if(ENABLE)begin
   if(!coded_ok||(active&&!lease_ok)||index_event[1]||
      (PREFETCH&&active&&key_visible&&key_visibility_frame!=desc[72:0])||
      (PREFETCH&&prefetch_accepted&&(!prefetch_v||prefetch_accepted_frame!=desc[72:0]))) next_ctl[3:0]=FAULT;
   else case(state)
    IDLE:if(command_v&&command_r)begin
     if(command_frame!=owner_frame||command_rank>=96||command_ndie>10944||
        command_k==0||command_k>512||(PREFETCH&&(command_layer>=40||command_key_row0>32085)))next_ctl[3:0]=FAULT;
     else begin next_desc={command_layer,command_key_row0,command_keep,command_cand,command_k,command_ndie,
                          command_rank,command_frame};next_ctl=WAITPUB;end
    end
    WAITPUB:if(producer_published&&producer_drained&&(!PREFETCH||ctl[12]))
     next_ctl[3:0]=desc[105]?KEEP:FRAME;
    KEEP:if(keep_v)begin
     if(keep_frame!=desc[72:0]||seen[keep_quarter])next_ctl[3:0]=FAULT;
     else if(keep_r)begin next_mask={keep_bitmap,keep_quarter};
      next_ctl[4+keep_quarter]=1'b1;next_ctl[3:0]=EMITKEEP;end
    end
    EMITKEEP:begin next_ctl[3:0]=GAP;next_ctl[9:8]=2;end
    GAP:if(gap!=0)next_ctl[9:8]=gap-1'b1;
        else next_ctl[3:0]=(&seen)?FRAME:KEEP;
    FRAME:begin next_ctl[3:0]=STARTGAP;next_ctl[9:8]=2;end
    STARTGAP:if(gap!=0)next_ctl[9:8]=gap-1'b1;else next_ctl[3:0]=START;
    START:if(source_start_v&&source_start_r)next_ctl[3:0]=RUN;
    RUN:begin
     if(source_done)next_ctl[11]=1'b1;
     if(index_event[0])next_ctl[10]=1'b1;
     if((source_seen||source_done)&&(index_seen||index_event[0])&&
        returns_drained&&source_idle&&selector_idle)next_ctl[3:0]=RETIRE;
    end
    RETIRE:next_ctl=0;
    FAULT:next_ctl[3:0]=FAULT;
    default:next_ctl[3:0]=FAULT;
   endcase
   if(PREFETCH&&prefetch_v&&prefetch_accepted&&prefetch_accepted_frame==desc[72:0])next_ctl[12]=1;
  end
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin desc<=0;desc_n<={DW{1'b1}};mask<=0;mask_n<={344{1'b1}};
   ctl<=0;ctl_n<=13'h1fff;end
  else begin desc<=next_desc;desc_n<=~next_desc;mask<=next_mask;mask_n<=~next_mask;
   ctl<=next_ctl;ctl_n<=~next_ctl;end
 end
endmodule
`default_nettype wire
