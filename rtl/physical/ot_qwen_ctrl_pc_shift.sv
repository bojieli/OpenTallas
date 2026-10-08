`timescale 1ns/1ps
// One full Qwen JEDEC pseudo-channel scheduler (WR_EN1, WQ4, PULLIN0),
// behind an 8-entry command-credit boundary. Does NOT include payload storage,
// stream mapping, all-PC descriptor fence or the PHY. Functional clock remains
// 976.5625MHz because original DRAM timing counters are unchanged.
// cmd[31:30]: 0 descriptor {n[10:0],row[18:0]}, 1 go, 2 write
// {20'b0,column[4:0],bank[4:0]}, 3 invalid. Eight initial command credits;
// one returned on each consumed command. Read credits are separate [2:0].
module ot_qwen_ctrl_pc_shift #(parameter integer ENABLE=0,PC=0,PHASE=0)(
 input wire clk,rst_n,
 input wire cmd_v,input wire [31:0] cmd,
 input wire [2:0] read_credit,
 output reg cmd_credit,
 output reg row_v,output reg [2:0] row_op,output reg [4:0] row_bank,
 output reg [18:0] row_row,
 output reg col_v,output reg [4:0] col_bank,col_col,output reg col_we,
 output reg busy,fault
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
 wire rv,cv,cwe;wire [2:0] rop;wire [4:0] rb,cb,cc;wire [18:0] rr;
 wire malformed=(head[31:30]==3) ||
    (head[31:30]==0 && (head[29:19]==0 || head[29:19]>1024));
 wire pop=live && (malformed || (head[31:30]==0 ? desc_ready : head[31:30]==2 ? wr_ready : 1'b1));
 wire push=(ENABLE!=0) && cmd_v_q && count<8;
 ot_hbm_r14_stream_pc_shift #(.SHIFT_WQ(1),.READY_CUT(1),.ENABLE(ENABLE),.REF_MODE(1),.PC(PC),
  .CRED(32),.REF_PHASE((PHASE+(PC*118)/32)%118),.WR_EN(1),.WQ(4),.PULLIN(0),.AQ_RD(0)) core(
  .clk(clk),.rst_n(rst_n),.desc_v(live && !malformed && head[31:30]==0),
  .desc_r(desc_ready),.desc_row(head[18:0]),.desc_n(head[29:19]),
  .go(live && head[31:30]==1),.next_posted(1'b0),
  .row_v(rv),.row_prio(),.row_gnt(1'b1),.row_op(rop),.row_bank(rb),.row_row(rr),
  .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(read_credit_q),
  .busy(core_busy),.ref_fault(core_fault),
  .wr_v(live && head[31:30]==2),.wr_bank(head[4:0]),.wr_col(head[9:5]),
  .wr_r(wr_ready),.col_we(cwe),.wr_rd(1'b0),.col_aq());
 always @(posedge clk) begin
  cmd_q<=cmd;read_credit_q<=read_credit;
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
   cmd_v_q<=0;cmd_credit<=0;wp<=0;rp<=0;count<=0;
   row_v<=0;col_v<=0;col_we<=0;busy<=0;fault_q<=0;fault<=0;
  end else begin
   cmd_v_q<=cmd_v;
   cmd_credit<=pop;
   if(push) wp<=wp+1'b1;
   if(pop) rp<=rp+1'b1;
   case({push,pop})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:count<=count;
   endcase
   if(ENABLE!=0 && ((cmd_v_q && !push) || (pop && malformed))) fault_q<=1;
   row_v<=rv;col_v<=cv;col_we<=cwe;busy<=core_busy;
   fault<=fault_q || core_fault;
  end
 end
endmodule
