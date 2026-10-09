`timescale 1ns/1ps
// Default-off diagnostic protection for the retained row_v/col_v stream
// contract. All command fields and credits become zero on mismatch or halt.
// Physical CA encoding, pending-write drain and refresh handoff are parent
// obligations. A single sequential-state upset is covered, not common-mode
// faults in both copies, clock/reset, input wires or combinational cells.
module ot_qwen_ctrl_pc_protected #(parameter integer ENABLE=0,PC=0,PHASE=0,
  // OREG=1 (qwen-blocks 2026-10-07; 0 = original): the gated command/credit/busy/fault outputs leave from registers (+1
  // cycle on every output, so JEDEC spacing is unchanged); rst_n and the replica compare no longer reach the pins
  parameter integer OREG=0)(
 input wire clk,rst_n,cmd_v,input wire [31:0] cmd,
 input wire [2:0] read_credit,
 output wire cmd_credit,row_v,output wire [2:0] row_op,
 output wire [4:0] row_bank,output wire [18:0] row_row,
 output wire col_v,output wire [4:0] col_bank,col_col,
 output wire col_we,busy,fault
);
 wire [1:0] cr,rv,cv,cwe,bs,ft;
 wire [2:0] ro[0:1];wire [4:0] rb[0:1],cb[0:1],cc[0:1];
 wire [18:0] rr[0:1];
 wire [42:0] packet[0:1];
 for(genvar g=0;g<2;g=g+1) begin:g_replica
  // Keep both hierarchy roots through flatten/opt/share. A mapped-state
  // inventory is a separate adoption gate; RTL duplication alone is not proof.
  (* keep=1, dont_touch=1, keep_hierarchy=1 *)
  ot_qwen_ctrl_pc_shift #(.ENABLE(ENABLE),.PC(PC),.PHASE(PHASE)) u(
   .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd(cmd),.read_credit(read_credit),
   .cmd_credit(cr[g]),.row_v(rv[g]),.row_op(ro[g]),.row_bank(rb[g]),.row_row(rr[g]),
   .col_v(cv[g]),.col_bank(cb[g]),.col_col(cc[g]),.col_we(cwe[g]),.busy(bs[g]),.fault(ft[g]));
  // Ignore payload only when its own valid is zero; valid disagreement always
  // participates in equality. This also avoids comparing uninitialised data.
  assign packet[g]={cr[g],bs[g],ft[g],rv[g],
    rv[g]?{ro[g],rb[g],rr[g]}:27'b0,
    cv[g],cv[g]?{cb[g],cc[g],cwe[g]}:11'b0};
 end
 wire agree=(packet[0]==packet[1]);
 (* keep=1, dont_touch=1 *) reg trip_seen;
 (* keep=1, dont_touch=1 *) reg permit_state;
 wire halt=trip_seen || !permit_state || !agree || (|ft);
 wire allow=(ENABLE!=0) && rst_n && !halt;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin trip_seen<=0;permit_state<=1;end
  else if(halt) begin trip_seen<=1;permit_state<=0;end
 wire        w_cr=allow && cr[0];
 wire        w_rv=allow && rv[0];
 wire [2:0]  w_ro=w_rv?ro[0]:3'b0;
 wire [4:0]  w_rb=w_rv?rb[0]:5'b0;
 wire [18:0] w_rr=w_rv?rr[0]:19'b0;
 wire        w_cv=allow && cv[0];
 wire [4:0]  w_cb=w_cv?cb[0]:5'b0;
 wire [4:0]  w_cc=w_cv?cc[0]:5'b0;
 wire        w_we=w_cv && cwe[0];
 wire        w_bs=allow && bs[0];
 // Expose registered sticky state, not clock-edge comparator settling.
 // Commands are inhibited immediately by halt; the fault notification follows
 // at the next sample edge. Both downstream interfaces are synchronous.
 wire        w_ft=(ENABLE!=0) && rst_n && (trip_seen || !permit_state);
 generate if (OREG!=0) begin : g_oreg
  (* keep=1 *) reg [44:0] oq;
  always @(posedge clk or negedge rst_n)
   if(!rst_n) oq<=45'b0;
   else oq<={w_cr,w_rv,w_ro,w_rb,w_rr,w_cv,w_cb,w_cc,w_we,w_bs,(ENABLE!=0) && (halt || trip_seen || !permit_state)};
  assign {cmd_credit,row_v,row_op,row_bank,row_row,col_v,col_bank,col_col,col_we,busy,fault}=oq;
 end else begin : g_comb
  assign {cmd_credit,row_v,row_op,row_bank,row_row,col_v,col_bank,col_col,col_we,busy,fault}=
         {w_cr,w_rv,w_ro,w_rb,w_rr,w_cv,w_cb,w_cc,w_we,w_bs,w_ft};
 end endgenerate
endmodule
