`timescale 1ns/1ps
// Persistent unified host/write/KV scheduler successor. Command FIFO includes
// descriptor first-sector metadata. One JEDEC/refresh/bank state machine owns
// PHY commands for every phase; compiled RD reservations replace read credits.
// Host static/write queue issue must be included in the same compiled calendar.
module ot_qkd_static_ctrl_pc_emb #(parameter integer ENABLE=0,PC=0,PHASE=0,SQD=4,S_STARVE=8,TWIN=0,TWIN_ROFF=0,PULLIN=0,PROFILE=0,CONTEXT_DESC=0,STATIC_REFRESH=0)(   // PULLIN: qwen-1010/b
 input wire clk,rst_n,
 input wire cmd_v,input wire [31:0] cmd,
 input wire [9:0] cmd_first, input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
 // KV-TOK B 2026-10-24: boot window (see ot_qkd_static_kv_timing.boot_static_col), captured in a pin flop like the
 // reservations; col_boot marks a static column issued in the window WITHOUT a reservation (registered with col_sr).
 input wire boot_window,output reg col_boot,
 output reg cmd_credit,
 output reg row_v,output reg [2:0] row_op,output reg [4:0] row_bank,
 output reg [18:0] row_row,
 output reg col_v,output reg [4:0] col_bank,col_col,output reg col_we,
 output reg busy,fault,output wire phase_idle,
 input wire [346:0] s_context,output reg [346:0] col_context,
 input wire s_v,s_we,input wire [4:0] s_bank,s_col,input wire [18:0] s_row,
 output reg s_cr,output reg col_sr
);
 (* keep *) reg cmd_v_q;
 (* keep *) reg [31:0] cmd_q;
 (* keep *) reg [9:0] first_q;
 (* keep *) reg rdslot_q,srslot_q,wrslot_q,bootwin_q;
 reg [9:0] first_fifo[0:7];reg [9:0] head_first;
 reg [31:0] fifo[0:7];
 reg [2:0] wp,rp;
 reg [3:0] count;
 reg fault_q;
 // Lookahead head: same visible consume cycle and eight-credit capacity.
 // Data need not reset: count gates all consumers until the first push.
 (* keep *) reg [31:0] head;
 wire [2:0] rp_next=rp+3'd1;
 wire live=(ENABLE!=0) && count!=0;
 wire desc_ready,wr_ready,core_fault,core_busy,schedule_fault,core_idle;
 wire rv,cv,cwe,csr,sr_r,spop;wire [2:0] rop;wire [4:0] rb,cb,cc;wire [18:0] rr;
 (* keep *) reg s_v_q,s_we_q;(* keep *) reg [4:0] s_bank_q,s_col_q;(* keep *) reg [18:0] s_row_q;
 (* keep *) reg [346:0] s_context_q;
 wire [346:0] core_context;
 wire context_head=CONTEXT_DESC!=0 && head[31:30]==3;
 wire descriptor_head=head[31:30]==0 || context_head;
 wire malformed=(head[31:30]==3 && !context_head) || (context_head && (head[27:19]>256 || head_first>128)) ||
    (head[31:30]==0 && (head[29:19]==0 || head[29:19]>1024 || head_first>=head[29:19]));
 wire pop=live && (malformed || (descriptor_head ? desc_ready : head[31:30]==2 ? wr_ready : 1'b1));
 wire push=(ENABLE!=0) && cmd_v_q && count<8;
 assign phase_idle=core_idle && count==0 && !cmd_v_q && !s_v_q;
 ot_qkd_static_kv_timing #(.STATIC_REFRESH(STATIC_REFRESH),.CONTEXT_DESC(CONTEXT_DESC),.PROFILE(PROFILE),.SROW(1),.SQD(SQD),.S_STARVE(S_STARVE),.TWIN(TWIN),.TWIN_ROFF(TWIN_ROFF),.READY_CUT(1),.ENABLE(ENABLE),.REF_MODE(1),.PC(PC),
  .REF_PHASE((PHASE+(PC*118)/32)%118),.WR_EN(1),.WQ(4),.PULLIN(PULLIN),.AQ_RD(0)) core(
  .clk(clk),.rst_n(rst_n),.desc_v(live && !malformed && descriptor_head),
  .desc_r(desc_ready),.desc_row(head[18:0]),.desc_n(context_head?{2'b0,head[27:19]}:head[29:19]),.desc_first(head_first),.desc_context(context_head),.desc_vpass(head[28]),.desc_k_order_b(head[29]),.desc_k_count0(head_first[7:0]),.reserved_rd(rdslot_q),.reserved_static_col(srslot_q),.reserved_write_col(wrslot_q),.boot_static_col(bootwin_q),.schedule_fault(schedule_fault),.phase_idle(core_idle),
  .go(live && head[31:30]==1),.next_posted(1'b0),
  .row_v(rv),.row_prio(),.row_gnt(1'b1),.row_op(rop),.row_bank(rb),.row_row(rr),
  .col_v(cv),.col_bank(cb),.col_col(cc),
  .busy(core_busy),.ref_fault(core_fault),
  .wr_v(live && head[31:30]==2),.wr_bank(head[4:0]),.wr_col(head[9:5]),
  .wr_r(wr_ready),.col_we(cwe),.wr_rd(1'b0),.col_aq(),
  .s_context(s_context_q),.col_context(core_context),.s_v(ENABLE!=0 && s_v_q),.s_we(s_we_q),.s_bank(s_bank_q),.s_col(s_col_q),.s_row(s_row_q),
  .s_r(sr_r),.col_sr(csr),.s_pop(spop));
 always @(posedge clk) begin
  cmd_q<=cmd;first_q<=cmd_first;
  s_context_q<=s_context;col_context<=core_context;
  s_we_q<=s_we;s_bank_q<=s_bank;s_col_q<=s_col;s_row_q<=s_row;
  if(push)begin fifo[wp]<=cmd_q;first_fifo[wp]<=first_q;end
  if(count==0 && push)begin head<=cmd_q;head_first<=first_q;end
  else if(pop) begin
   if(count>1)begin head<=fifo[rp_next];head_first<=first_fifo[rp_next];end
   else if(push)begin head<=cmd_q;head_first<=first_q;end
  end
  // Equal output delay on every row/column preserves all JEDEC spacings.
  row_op<=rop;row_bank<=rb;row_row<=rr;col_bank<=cb;col_col<=cc;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   cmd_v_q<=0;rdslot_q<=0;srslot_q<=0;wrslot_q<=0;bootwin_q<=0;col_boot<=0;cmd_credit<=0;wp<=0;rp<=0;count<=0;s_v_q<=0;s_cr<=0;col_sr<=0;
   row_v<=0;col_v<=0;col_we<=0;busy<=0;fault_q<=0;fault<=0;
  end else begin
   cmd_v_q<=cmd_v;rdslot_q<=reserved_rd;srslot_q<=reserved_static_col;wrslot_q<=reserved_write_col;
   s_v_q<=s_v;s_cr<=spop;col_sr<=csr;bootwin_q<=boot_window;col_boot<=csr&&bootwin_q&&!srslot_q;
   cmd_credit<=pop;
   if(push) wp<=wp+1'b1;
   if(pop) rp<=rp+1'b1;
   case({push,pop})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:count<=count;
   endcase
   if(ENABLE!=0 && ((cmd_v_q && !push) || (pop && malformed) || (s_v_q && !sr_r))) fault_q<=1;
   row_v<=rv;col_v<=cv;col_we<=cwe;busy<=core_busy;
   fault<=fault_q || core_fault || schedule_fault;
  end
 end
endmodule
