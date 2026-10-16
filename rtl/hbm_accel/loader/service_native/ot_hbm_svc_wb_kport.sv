`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/dmawb 2026-10-16: DMA write-back -> HBM K-port partner of ONE quadrant DMA (hb_dbk_<q>,
// ot_hgi_dma_back_static_vp4_banks).  Closes G-DMA-WB: the die leaf that the v16 netlist lacked between the DMA's
// write-back outputs (wb_reserve_* / wb_fill_* / wd[2312]) and the quadrant's 32 HBM controller K ports, and the
// producer of the DMA's wb_ready / wa[12] inputs.
//
// CONTENTS (one master for all four quadrants; the stack is the declared identity strap stk, not a parameter):
//  * the real write-back block ot_hbm_svc_wb_cutthrough_cdc (two-buffer 32 x 128x256 SRAM, complete-row watermark,
//    32 Gray CDC payload FIFOs, per-PC XOR-hash pick, 64 posted writes per PC, posted count on TRUE k_wr_done), used
//    unchanged with STACK=0: this leaf checks the stack bits [31:30] of reserve_base and of every valid wd sector against
//    stk and hands the block stack-local sectors (bits [31:30] cleared), so the block's own range/sector checks hold;
//  * the reservation receipt join that ot_hgi_b2_swap_wb_grp_static carried as parent glue (accepted/epoch/total per
//    buffer; wb_ready = accepted & epoch match & block owns the buffer; wa = posted sectors of the returned block;
//    receipt mismatch = fault);
//  * the WB WINDOW command to the quadrant's eight ot_hbm_svc_vm_kshare leaves (wbw_v/base/total).  The DMA's fill start
//    is a compiled absolute edge (drain_at+1), so the window is issued on a compiler-fixed edge: WOPEN=0 at the fill
//    start, WOPEN=1 at the block's last fixed fill edge (fill_done).  The kshare leaves turn it into exact per-PC write
//    counts and share the controller K ports (decision 23:21: no dedicated write PCs).
// FLOW CONTROL: none on the on-die DMA side (the DMA's schedule is static; wb_ready is sampled once at its first drain
// and wa is a posted count).  The only ready signals are on the K side (w_k_rdy, inside the HBM boundary).
// PIN REGISTERS: every DMA-side input is captured by a pin flop; wb_ready, wa, the window command and fault leave from
// flops; each K write port leaves through a 2-entry pin skid (ot_hbm_svc_pin_skid2, the head register drives the pins);
// w_k_wr_done is captured by a pin flop.  Fixed added latency vs the unwrapped composition: DMA -> block +1 stream edge
// (reserve, fill start, wd), block -> wb_ready/wa +1 stream edge, block K request -> pins +1 hbm edge, true completion
// -> block +1 hbm edge.  wb_ready is valid 3 stream edges after the DMA's wb_reserve_v (the DMA samples it at its first
// drain, >= 10 edges later by its own c_lag_ok rule).
// MUT (bench only): 1 = wa reports the fill (not the true completion) -- premature posted count.
module ot_hbm_svc_wb_kport #(parameter integer WOPEN=0, parameter integer MUT=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,                 // four stream-frequency clock-tree roots of the WB payload groups
 input wire[1:0]stk,                             // stack identity strap (declared die constant)
 // DMA write-back side (stream_clk)
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output reg wb_ready,output reg[11:0]wa,
 // WB window command to the quadrant's eight kshare leaves (stream_clk)
 output reg wbw_v,output reg[29:0]wbw_base,output reg[11:0]wbw_total,
 // K write ports of PCs 0..31 (hbm_clk): single-beat full-strobe writes, sector address
 output wire[31:0]w_k_v,input wire[31:0]w_k_rdy,output wire[959:0]w_k_addr,output wire[8191:0]w_k_wdata,
 input wire[31:0]w_k_wr_done,
 output reg fault
);
 // ---------------------------------------------------------------- stream pins
 reg rv_q,rb_q,fb_q,fs_q;reg[15:0]re_q,fe_q;reg[11:0]rt_q;reg[31:0]rbase_q;reg[2311:0]wd_q;reg[1:0]stk_q;
 always @(posedge stream_clk)begin
  rb_q<=wb_reserve_bank;fb_q<=wb_fill_bank;re_q<=wb_reserve_epoch;fe_q<=wb_fill_epoch;rt_q<=wb_reserve_sectors;
  rbase_q<=wb_reserve_base;wd_q<=wd;stk_q<=stk;
 end
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin rv_q<=0;fs_q<=0;end else begin rv_q<=wb_reserve_v;fs_q<=wb_fill_start;end
 // stack check + stack-local sectors
 reg[2311:0]wd_l;reg wd_stk_bad;integer s;
 always @*begin
  wd_l=wd_q;wd_stk_bad=0;
  for(s=0;s<8;s=s+1)begin
   if(wd_q[289*s+288]&&wd_q[289*s+286+:2]!=stk_q)wd_stk_bad=1;
   wd_l[289*s+286+:2]=2'b00;
  end
 end
 wire rbase_stk_bad=rv_q&&rbase_q[31:30]!=stk_q;
 // ---------------------------------------------------------------- write-back block
 wire reserve_ready,fill_done,done_v,done_bank,blk_fault;wire[15:0]done_epoch;wire[11:0]done_sectors;wire[1:0]owned;
 wire[31:0]k_v,k_rdy,k_we,k_wr_done_q;wire[959:0]k_addr;wire[8191:0]k_wdata;wire[127:0]k_len;wire[543:0]k_tag;wire[1023:0]k_wstrb;
 ot_hbm_svc_wb_cutthrough_cdc #(.STACK(2'd0)) u_wb(
  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stream_fifo_clk(stream_fifo_clk),
  .reserve_v(rv_q),.reserve_ready(reserve_ready),.reserve_bank(rb_q),.reserve_epoch(re_q),.reserve_base({2'b00,rbase_q[29:0]}),
  .reserve_total(rt_q),.fill_start(fs_q),.fill_start_bank(fb_q),.fill_start_epoch(fe_q),.wd(wd_l),
  .fill_done(fill_done),.done_v(done_v),.done_bank(done_bank),.done_epoch(done_epoch),.done_sectors(done_sectors),
  .bank_owned(owned),.fault(blk_fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
  .k_wr_done(k_wr_done_q));
 // ---------------------------------------------------------------- reservation receipts, wb_ready, wa, window command
 reg[1:0]accepted;reg[15:0]aepoch[0:1];reg[11:0]atotal[0:1];reg[29:0]abase[0:1];reg rfault;
 reg fsb_q;   // buffer whose fill is in progress (for the WOPEN=1 window)
 wire block_ready=accepted[fb_q]&&aepoch[fb_q]==fe_q&&owned[fb_q];
 wire win_go=(WOPEN==0)?fs_q:fill_done;
 wire win_bank=(WOPEN==0)?fb_q:fsb_q;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   accepted<=0;rfault<=0;wb_ready<=0;wa<=0;wbw_v<=0;wbw_base<=0;wbw_total<=0;fault<=0;fsb_q<=0;
   aepoch[0]<=0;aepoch[1]<=0;atotal[0]<=0;atotal[1]<=0;abase[0]<=0;abase[1]<=0;
  end else begin
   if(rv_q)begin
    if(!reserve_ready)rfault<=1;
    else begin accepted[rb_q]<=1;aepoch[rb_q]<=re_q;atotal[rb_q]<=rt_q;abase[rb_q]<=rbase_q[29:0];end
   end
   if(done_v)begin
    if(!accepted[done_bank]||aepoch[done_bank]!=done_epoch||atotal[done_bank]!=done_sectors)rfault<=1;
    accepted[done_bank]<=0;
   end
   if(fs_q)fsb_q<=fb_q;
   if(rbase_stk_bad||wd_stk_bad)rfault<=1;
   wb_ready<=block_ready;
   wa<=(MUT==1)?(fill_done?atotal[fsb_q]:12'd0):(done_v?done_sectors:12'd0);
   wbw_v<=win_go;wbw_base<=abase[win_bank];wbw_total<=atotal[win_bank];
   fault<=rfault||blk_fault;
  end
 end
 // ---------------------------------------------------------------- K write pins (hbm_clk)
 reg[31:0]wr_done_q;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)wr_done_q<=0;else wr_done_q<=w_k_wr_done;
 assign k_wr_done_q=wr_done_q;
 genvar p;
 generate for(p=0;p<32;p=p+1)begin:pc
  ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_k(.clk(hbm_clk),.rst_n(hbm_rst_n),.in_v(k_v[p]),.in_r(k_rdy[p]),
   .in_data({k_addr[30*p+:30],k_wdata[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
   .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
 end endgenerate
endmodule
`default_nettype wire
