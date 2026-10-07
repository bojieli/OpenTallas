`timescale 1ns/1ps
// Default-off diagnostic protection for the retained row_v/col_v stream
// contract. All command fields and credits become zero on mismatch or halt.
// Physical CA encoding, pending-write drain and refresh handoff are parent
// obligations. A single sequential-state upset is covered, not common-mode
// faults in both copies, clock/reset, input wires or combinational cells.
module ot_qwen_ctrl_pc_protected #(parameter integer ENABLE=0,PC=0,PHASE=0)(
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
 assign cmd_credit=allow && cr[0];
 assign row_v=allow && rv[0];
 assign row_op=row_v?ro[0]:3'b0;
 assign row_bank=row_v?rb[0]:5'b0;
 assign row_row=row_v?rr[0]:19'b0;
 assign col_v=allow && cv[0];
 assign col_bank=col_v?cb[0]:5'b0;
 assign col_col=col_v?cc[0]:5'b0;
 assign col_we=col_v && cwe[0];
 assign busy=allow && bs[0];
 // Expose registered sticky state, not clock-edge comparator settling.
 // Commands are inhibited immediately by halt; the fault notification follows
 // at the next sample edge. Both downstream interfaces are synchronous.
 assign fault=(ENABLE!=0) && rst_n && (trip_seen || !permit_state);
endmodule
