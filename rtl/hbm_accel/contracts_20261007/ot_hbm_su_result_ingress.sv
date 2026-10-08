`timescale 1ns/1ps
// SU result ingress: one SM lane of the native SM -> SU result edge
// (contract: tools/hbm_sm_su_result_contract.py, results/rtl/hbm_sm_su_result_contract_20261007, 8c8bb2af2).
//
// The SM result face (rv / rrow / rdata / fault, 270 b) is one-way: no ready crosses the die.  Flow control is a
// CREDIT RESERVATION held here: the SU's command path presents an op's row count (op_v, op_rows held until op_ack);
// the lane acknowledges (op_ack, registered, one pulse) once op_rows fit in its free slots and deducts them; every
// drained row returns one slot.  The SU starts the SM op only after op_ack, so rows can never overflow the lane,
// whatever the die path latency.
//
// Ordering comes from the protocol, not timing slack: rows are held until the op's row count is complete
// (arrived == op_rows); only then does the consumer see them (out_v), and op_done pulses once per op.
// Each op's rows are checked: row index < op_rows, each index exactly once (64-bit seen map).
//
// Pipeline (every decision from registered state; registered boundary):
//   A  (arrival check, at the pin register): row range / duplicate / reservation checks, seen + arrived update,
//      `last` = this row completes the head op;  registered into
//   B  (commit): SRAM write, unread / releasable / op-queue updates, op_done.
// Storage: one 64 x 512 1R1W macro (268 b used: row 12 + data 256); 64 slots >= 43 rows per SM per op on the
// DS AR walk.  Read side = the II=1 refill head used by the packet SRAM (macro read latch R + head H).
// Faults (sticky): SM fault, a row with no reserved op, row index out of range or repeated, op_rows 0 or > 64.
module ot_hbm_su_result_ingress #(parameter integer OPQ=4, RW=12, DW=256)(
 input wire clk,rst_n,
 // reservation (SU command path): hold op_v / op_rows until op_ack
 input wire op_v,input wire [6:0] op_rows,output reg op_ack,
 // result face after the die stations (one-way)
 input wire in_v,input wire [RW-1:0] in_row,input wire [DW-1:0] in_data,input wire in_fault,
 // consumer: rows of completed ops only, in arrival order
 output wire out_v,input wire out_r,output wire [RW-1:0] out_row,output wire [DW-1:0] out_data,
 output reg op_done,output reg [6:0] op_done_rows,
 output wire fault,output wire [6:0] free_o);
 localparam integer QW=$clog2(OPQ);
 reg fault_q;
 // ---------------- reservation: registered request, registered acknowledge
 reg [6:0] free_q;                          // free slots (credits)
 reg [6:0] opq[0:OPQ-1];reg [QW:0] oq_n;reg [QW-1:0] oq_w,oq_r;
 reg [6:0] hq_rows_q;reg hq_v_q;            // registered head op (rows expected), A-stage view
 reg req_q;reg [6:0] req_rows_q;
 wire req_ok=req_q&&!op_ack&&oq_n!=OPQ&&req_rows_q<=free_q;
 // ---------------- stage A: arrival checks against the head op
 reg [6:0] arrived;reg [63:0] seen;
 wire [5:0] ri=in_row[5:0];
 wire bad_row=in_v&&(!hq_v_q||in_row>={{(RW-7){1'b0}},hq_rows_q}||seen[ri]);
 wire ok_row=in_v&&!bad_row&&!fault_q;
 wire last=ok_row&&arrived+7'd1==hq_rows_q;
 // ---------------- stage B registers
 reg put_q,last_q;reg [6:0] last_rows_q;reg [RW+DW-1:0] wdata_q;
 // ---------------- storage + refill head
 reg [5:0] wp,rp;reg [6:0] unread;reg pending,held;
 reg [6:0] releasable;               // rows of completed ops still in the lane (unread + R + H)
 wire [511:0] ram_q;
 reg [RW+DW-1:0] head;
 reg rel_nz_q;                       // registered releasable != 0 (no counter -> out_v path)
 assign out_v=held&&rel_nz_q&&!fault_q;
 wire take=out_v&&out_r;
 wire xfer=pending&&(!held||take);
 wire fetch=unread!=0&&(!pending||xfer);
 assign out_row=head[RW+DW-1:DW];assign out_data=head[DW-1:0];
 ot_sram_1r1w_64x512_m1_r2c2 u_store(.clk(clk),.r_ce_in(fetch),.r_addr_in(rp),.rd_out(ram_q),
  .w_ce_in(put_q),.w_addr_in(wp),.wd_in({{(512-RW-DW){1'b0}},wdata_q}),.w_mask_in({512{1'b1}}),
  .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 // op queue head after this edge (pop on stage-A completion of the head op, push on grant)
 wire [QW-1:0] oq_r_n=last?oq_r+1'b1:oq_r;
 wire [QW:0] oq_n_n=oq_n+{{QW{1'b0}},req_ok}-{{QW{1'b0}},last};
 integer k;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   free_q<=7'd64;oq_n<=0;oq_w<=0;oq_r<=0;hq_rows_q<=0;hq_v_q<=0;req_q<=0;req_rows_q<=0;op_ack<=0;
   arrived<=0;seen<=0;fault_q<=0;put_q<=0;last_q<=0;last_rows_q<=0;wdata_q<=0;
   wp<=0;rp<=0;unread<=0;pending<=0;held<=0;releasable<=0;rel_nz_q<=0;head<=0;op_done<=0;op_done_rows<=0;
   for(k=0;k<OPQ;k=k+1)opq[k]<=0;
  end else begin
   op_done<=1'b0;op_ack<=1'b0;
   if(in_fault||bad_row||(op_v&&(op_rows==0||op_rows>7'd64)))fault_q<=1'b1;
   if(!fault_q)begin
    // reservation
    if(!req_q&&!op_ack&&op_v)begin req_q<=1'b1;req_rows_q<=op_rows;end
    if(req_ok)begin req_q<=1'b0;op_ack<=1'b1;opq[oq_w]<=req_rows_q;oq_w<=oq_w+1'b1;end
    free_q<=free_q-(req_ok?req_rows_q:7'd0)+{6'b0,take};
    oq_n<=oq_n_n;oq_r<=oq_r_n;
    // head op view for stage A: the op at oq_r_n (a just-granted op becomes head when the queue was empty)
    hq_v_q<=oq_n_n!=0;
    hq_rows_q<=(oq_n==0||(oq_n==1&&last))?req_rows_q:opq[oq_r_n];
    // stage A
    if(last)begin arrived<=0;seen<=0;end
    else if(ok_row)begin arrived<=arrived+1'b1;seen[ri]<=1'b1;end
    put_q<=ok_row;last_q<=last;last_rows_q<=hq_rows_q;wdata_q<={in_row,in_data};
    // stage B
    if(put_q)wp<=wp+1'b1;
    unread<=unread+{6'b0,put_q}-{6'b0,fetch};
    if(last_q)begin op_done<=1'b1;op_done_rows<=last_rows_q;end
    releasable<=releasable+(last_q?last_rows_q:7'd0)-{6'b0,take};
    rel_nz_q<=(releasable+(last_q?last_rows_q:7'd0)-{6'b0,take})!=7'd0;
    if(fetch)rp<=rp+1'b1;
    pending<=fetch?1'b1:(xfer?1'b0:pending);
    held<=xfer?1'b1:(take?1'b0:held);
    if(xfer)head<=ram_q[RW+DW-1:0];
   end
  end
 assign fault=fault_q;assign free_o=free_q;
endmodule
