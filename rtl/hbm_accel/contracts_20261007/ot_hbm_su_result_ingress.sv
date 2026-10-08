`timescale 1ns/1ps
// SU result ingress: one SM lane of the native SM -> SU result edge
// (contract: tools/hbm_sm_su_result_contract.py, results/rtl/hbm_sm_su_result_contract_20261007, 8c8bb2af2).
//
// The SM result face (rv / rrow / rdata / fault, 270 b) is one-way: no ready crosses the die.  Flow control is a
// CREDIT RESERVATION held here: the SU's command path may start an SM op only after this lane accepts the op's
// row count (op_v && op_r), which deducts op_rows from the free-slot credits; every drained row returns one
// credit.  Rows therefore can never overflow the lane, whatever the die path latency.
//
// Ordering comes from the protocol, not timing slack: rows are held until the op's row count is complete
// (arrived == op_rows); only then does the consumer see them (out_v), and op_done pulses once per op.
// Each op's rows are checked: row index < op_rows, each index exactly once (64-bit seen map).
//
// Storage: one 64 x 512 1R1W macro (268 b used: row 12 + data 256); 64 slots >= 43 rows per SM per op on the
// DS AR walk.  Read side = the II=1 refill head used by the packet SRAM (macro read latch R + head H).
// Faults (sticky): SM fault, a row with no reserved op, row index out of range or repeated, op_rows 0 or > 64.
module ot_hbm_su_result_ingress #(parameter integer OPQ=4, RW=12, DW=256)(
 input wire clk,rst_n,
 // reservation (SU command path): accept an op of op_rows rows before starting the SM
 input wire op_v,input wire [6:0] op_rows,output wire op_r,
 // result face after the die stations (one-way)
 input wire in_v,input wire [RW-1:0] in_row,input wire [DW-1:0] in_data,input wire in_fault,
 // consumer: rows of completed ops only, in arrival order
 output wire out_v,input wire out_r,output wire [RW-1:0] out_row,output wire [DW-1:0] out_data,
 output reg op_done,output reg [6:0] op_done_rows,
 output wire fault,output wire [6:0] free_o);
 localparam integer QW=$clog2(OPQ);
 // ---------------- credits and op queue
 reg [6:0] free_q,free_n;
 reg [6:0] opq[0:OPQ-1];reg [QW:0] oq_n;reg [QW-1:0] oq_w,oq_r;
 wire [6:0] hq_rows=opq[oq_r];wire hq_v=oq_n!=0;
 reg [6:0] arrived;reg [63:0] seen;
 reg fault_q;
 assign op_r=!fault_q&&oq_n!=OPQ&&op_rows!=0&&op_rows<=7'd64&&op_rows<=free_q;
 wire grant=op_v&&op_r;
 // ---------------- arrival checks
 wire [5:0] ri=in_row[5:0];
 wire bad_row=in_v&&(!hq_v||in_row>={{(RW-7){1'b0}},hq_rows}||seen[ri]);
 wire last=in_v&&!bad_row&&arrived+7'd1==hq_rows;
 // ---------------- storage + refill head
 reg [5:0] wp,rp;reg [6:0] unread;reg pending,held;
 reg [6:0] releasable;               // rows of completed ops still in the lane (unread + R + H)
 wire [511:0] ram_q;
 reg [RW+DW-1:0] head;
 assign out_v=held&&releasable!=0&&!fault_q;
 wire take=out_v&&out_r;
 wire xfer=pending&&(!held||take);
 wire fetch=unread!=0&&(!pending||xfer);
 wire put=in_v&&!bad_row&&!fault_q;
 assign out_row=head[RW+DW-1:DW];assign out_data=head[DW-1:0];
 ot_sram_1r1w_64x512_m1_r2c2 u_store(.clk(clk),.r_ce_in(fetch),.r_addr_in(rp),.rd_out(ram_q),
  .w_ce_in(put),.w_addr_in(wp),.wd_in({{(512-RW-DW){1'b0}},in_row,in_data}),.w_mask_in({512{1'b1}}),
  .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 always @*begin
  free_n=free_q;
  if(grant)free_n=free_n-op_rows;
  if(take)free_n=free_n+1'b1;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   free_q<=7'd64;oq_n<=0;oq_w<=0;oq_r<=0;arrived<=0;seen<=0;fault_q<=0;
   wp<=0;rp<=0;unread<=0;pending<=0;held<=0;releasable<=0;head<=0;op_done<=0;op_done_rows<=0;
  end else begin
   op_done<=1'b0;
   if(in_fault||bad_row||(op_v&&(op_rows==0||op_rows>7'd64)))fault_q<=1'b1;
   if(!fault_q)begin
    free_q<=free_n;
    if(grant)begin opq[oq_w]<=op_rows;oq_w<=oq_w+1'b1;end
    oq_n<=oq_n+{{QW{1'b0}},grant}-{{QW{1'b0}},last};
    if(put)begin wp<=wp+1'b1;end
    unread<=unread+{6'b0,put}-{6'b0,fetch};
    if(last)begin
     oq_r<=oq_r+1'b1;arrived<=0;seen<=0;op_done<=1'b1;op_done_rows<=hq_rows;
    end else if(put)begin arrived<=arrived+1'b1;seen[ri]<=1'b1;end
    releasable<=releasable+(last?hq_rows:7'd0)-{6'b0,take};
    if(fetch)rp<=rp+1'b1;
    pending<=fetch?1'b1:(xfer?1'b0:pending);
    held<=xfer?1'b1:(take?1'b0:held);
    if(xfer)head<=ram_q[RW+DW-1:0];
   end
  end
 assign fault=fault_q;assign free_o=free_q;
endmodule
