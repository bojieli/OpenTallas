`timescale 1ns/1ps
// emb-hbm 2026-10-08: ot_qwen_ctrl_pc_head (left byte-identical) + the STATIC-ROW port of the embedding region
// (ot_hbm_r14_stream_pc_srow SROW = 1).  Die master qfd_ctrl_emb_<pc> (successor of qfd_ctrl_ready_hbm_<pc>).
//   static port: s_v / s_we / s_bank / s_col / s_row captured at the pin (no logic before the flop), pushed into the
//     scheduler's SQD-entry static queue; s_cr = registered credit pulse, one per static entry issued (the sender
//     starts with SQD credits).  A push without room latches fault (sender ignored credits).
//   col_sr: the column command is a static one (registered with col_v / col_we, the same output delay).
// Everything else (cmd / read_credit / row / col / busy / fault) is ot_qwen_ctrl_pc_head unchanged.
// One full Qwen JEDEC pseudo-channel scheduler (WR_EN1, WQ4, PULLIN0),
// behind an 8-entry command-credit boundary. Does NOT include payload storage,
// stream mapping, all-PC descriptor fence or the PHY. Functional clock remains
// 976.5625MHz because original DRAM timing counters are unchanged.
// cmd[31:30]: 0 descriptor {n[10:0],row[18:0]}, 1 go, 2 write
// {20'b0,column[4:0],bank[4:0]}, 3 invalid. Eight initial command credits;
// one returned on each consumed command. Read credits are separate [2:0].
module ot_qwen_ctrl_pc_emb #(parameter integer ENABLE=0,PC=0,PHASE=0,SQD=4,S_STARVE=8,TWIN=0,TWIN_ROFF=0)(
 input wire clk,rst_n,
 input wire cmd_v,input wire [31:0] cmd,
 input wire [2:0] read_credit,
 output reg cmd_credit,
 output reg row_v,output reg [2:0] row_op,output reg [4:0] row_bank,
 output reg [18:0] row_row,
 output reg col_v,output reg [4:0] col_bank,col_col,output reg col_we,
 output reg busy,fault,
 input wire s_v,s_we,input wire [4:0] s_bank,s_col,input wire [18:0] s_row,
 output reg s_cr,output reg col_sr
);
 (* keep *) reg cmd_v_q;
 (* keep *) reg [31:0] cmd_q;
 (* keep *) reg [2:0] read_credit_q;
 reg [31:0] fifo[0:7];
 reg [2:0] wp,rp;
 reg [3:0] count;
 reg fault_q;
 // Lookahead head: same visible consume cycle and eight-credit capacity.
 // Data need not reset: count gates all consumers until the first push.
 (* keep *) reg [31:0] head;
 wire [2:0] rp_next=rp+3'd1;
 wire live=(ENABLE!=0) && count!=0;
 wire desc_ready,wr_ready,core_fault,core_busy;
 wire rv,cv,cwe,csr,sr_r,spop;wire [2:0] rop;wire [4:0] rb,cb,cc;wire [18:0] rr;
 (* keep *) reg s_v_q,s_we_q;(* keep *) reg [4:0] s_bank_q,s_col_q;(* keep *) reg [18:0] s_row_q;
 wire malformed=(head[31:30]==3) ||
    (head[31:30]==0 && (head[29:19]==0 || head[29:19]>1024));
 wire pop=live && (malformed || (head[31:30]==0 ? desc_ready : head[31:30]==2 ? wr_ready : 1'b1));
 wire push=(ENABLE!=0) && cmd_v_q && count<8;
 ot_hbm_r14_stream_pc_srow #(.SROW(1),.SQD(SQD),.S_STARVE(S_STARVE),.TWIN(TWIN),.TWIN_ROFF(TWIN_ROFF),.READY_CUT(1),.ENABLE(ENABLE),.REF_MODE(1),.PC(PC),
  .CRED(32),.REF_PHASE((PHASE+(PC*118)/32)%118),.WR_EN(1),.WQ(4),.PULLIN(0),.AQ_RD(0)) core(
  .clk(clk),.rst_n(rst_n),.desc_v(live && !malformed && head[31:30]==0),
  .desc_r(desc_ready),.desc_row(head[18:0]),.desc_n(head[29:19]),
  .go(live && head[31:30]==1),.next_posted(1'b0),
  .row_v(rv),.row_prio(),.row_gnt(1'b1),.row_op(rop),.row_bank(rb),.row_row(rr),
  .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(read_credit_q),
  .busy(core_busy),.ref_fault(core_fault),
  .wr_v(live && head[31:30]==2),.wr_bank(head[4:0]),.wr_col(head[9:5]),
  .wr_r(wr_ready),.col_we(cwe),.wr_rd(1'b0),.col_aq(),
  .s_v(ENABLE!=0 && s_v_q),.s_we(s_we_q),.s_bank(s_bank_q),.s_col(s_col_q),.s_row(s_row_q),
  .s_r(sr_r),.col_sr(csr),.s_pop(spop));
 always @(posedge clk) begin
  cmd_q<=cmd;read_credit_q<=read_credit;
  s_we_q<=s_we;s_bank_q<=s_bank;s_col_q<=s_col;s_row_q<=s_row;
  if(push) fifo[wp]<=cmd_q;
  if(count==0 && push) head<=cmd_q;
  else if(pop) begin
   if(count>1) head<=fifo[rp_next];
   else if(push) head<=cmd_q;
  end
  // Equal output delay on every row/column preserves all JEDEC spacings.
  row_op<=rop;row_bank<=rb;row_row<=rr;col_bank<=cb;col_col<=cc;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   cmd_v_q<=0;cmd_credit<=0;wp<=0;rp<=0;count<=0;s_v_q<=0;s_cr<=0;col_sr<=0;
   row_v<=0;col_v<=0;col_we<=0;busy<=0;fault_q<=0;fault<=0;
  end else begin
   cmd_v_q<=cmd_v;
   s_v_q<=s_v;s_cr<=spop;col_sr<=csr;
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
   fault<=fault_q || core_fault;
  end
 end
endmodule
