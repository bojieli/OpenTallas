`timescale 1ns/1ps
`default_nettype none
// RTL-BUILD-HBM/stk 2026-10-18 (d4g plan (b), plan item 10): QUADRANT DMA write-back -> HBM K-port partner.
// Successor of ot_hbm_svc_wb_kport (unchanged, the per-stack master of GEN0) for the d4g per-quadrant services: one
// instance per quadrant <q> (wbk_SW / wbk_SE / wbk_NW / wbk_NE), partner of that quadrant's hb_dbk_<q>
// (ot_hgi_dma_back_static_vp4_banks_cp, unchanged master, reads only the quadrant's 8 VM banks vmb_<q>0..7) and of the
// quadrant's FOUR ot_hbm_svc_vm_kshare leaves (unchanged master; W: vmks_<S>0..3 = PCs 0..15, E: vmks_<S>4..7 = PCs
// 16..31).  GEN0 served all 32 PCs of a stack from one wbk per stack, so half its K ports and the window command crossed
// the die centre line (rule R1/R3 FAIL).
//
// ADDRESS CONTRACT (the only compiler-visible change).  The PHY maps a stack-local HBM sector s to PC
// s[6:2]^s[11:7]^s[16:12]; any contiguous run of >= 64 sectors therefore alternates between the W half (hash bit 4 = 0)
// and the E half.  A quadrant DMA write-back block is instead a contiguous run of QUADRANT ORDINALS o (29 b: the DMA's
// wb_reserve_base / wd sector field, stack bits [31:30] as before, bit 29 = 0).  The HBM sector of ordinal o is
//     s = fold_q(o) = {o[28:6], q ^ o[10] ^ o[15], o[5:0]}         (q = 0 W, 1 E: the quad strap)
// a bijection from [0, 2^29) onto the stack sectors whose PC is in the quadrant's half, PC = 16q + (o[5:2]^o[9:6]^o[14:11]),
// 4 consecutive ordinals per PC exactly as the stack map (every aligned 64-ordinal run covers the 16 PCs 4 times).
// Readers of the written data (attention / IDX / gather / loader, any quadrant) address the real sector s.
// The ordinal must also stay inside the stack: fold_q(o_end) < STACK_SECTORS (22.5e9 B / 32), checked here.
// WINDOW COMMAND to the unchanged kshare leaves: real base fold_q(base) and real span fold_q(base+total-1)-fold_q(base)+1;
// the span holds exactly the block's sectors plus the other half's sectors, which no lane of this quadrant counts (their
// hash bit 4 is !q), so the leaves' exact per-PC counts are the block's.  The span must fit the 12-bit window total:
// span <= 4095, always true for total <= 1984 (any alignment); a reservation whose span exceeds it is refused (fault).
//
// TIMING (vs ot_hbm_svc_wb_kport, same pin rules): stream pins +1, wb_ready 3 stream edges after wb_reserve_v (DMA samples
// it >= 10 edges later), wa = posted count of TRUE completions, window command on the fill-start edge (WOPEN=0) or
// fill_done (WOPEN=1) exactly as the master: wbw_v at the same stream edge.  The real window base/span are computed in
// two registered stages after the reservation pin flop (ready >= 8 edges before any fill start).  K side: the fold is two
// XORs on bit 6 in front of each K pin skid (no added edge).  No ready/credit on the on-die DMA side.
// RESET LANDING (L2H-WBK 2026-10-19, SAFE-DESIGN item 1, ROOT-RST): each reset input lands at its face in TWO plain
// registered stages ON ITS OWN CLOCK -- stream_rst_n on stream_clk (srst_l0 -> srst_l1), hbm_rst_n on hbm_clk (hrst_l0 ->
// hrst_l1) -- so each port net has one sink in its declared domain (the kit landing lands every reset on one clock and
// put hbm_rst_n on stream_clk: OT_MULTI_ROOT).  The landed resets replace the ports everywhere below; the cross-domain
// reset combination stays inside u_wb (reset_both -> per-domain ot_reset_sync: assert async, release through 2 stages).
// Reset assertion and release are 2 edges later in each domain: a scheduled constant, no data-latency change.
// MUT (bench only): 1 = premature wa (as the master), 2 = fold ignores the quad strap (E writes land on W-hash sectors),
//                   3 = window total = ordinal total (not the real span: per-PC counts short).
module ot_hbm_svc_wb_kport_q #(parameter integer WOPEN=0, parameter integer MUT=0,
                               parameter [29:0] STACK_SECTORS=30'd703125000)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,                 // four stream-frequency clock-tree roots of the WB payload groups
 input wire[1:0]stk,                             // stack identity strap (declared die constant)
 input wire quad,                                // quadrant identity strap: 0 = W half (PCs 0..15), 1 = E half (16..31)
 // DMA write-back side (stream_clk)
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output reg wb_ready,output reg[11:0]wa,
 // WB window command to the quadrant's four kshare leaves (stream_clk; real stack-local sector base / span)
 output reg wbw_v,output reg[29:0]wbw_base,output reg[11:0]wbw_total,
 // K write ports of the quadrant's PCs 16q+0..16q+15 (hbm_clk): single-beat full-strobe writes, real sector address
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output reg fault
);
 // ---------------------------------------------------------------- reset landing (2 plain stages per domain)
 reg srst_l0,srst_l1,hrst_l0,hrst_l1;
 always @(posedge stream_clk)begin srst_l0<=stream_rst_n;srst_l1<=srst_l0;end
 always @(posedge hbm_clk)begin hrst_l0<=hbm_rst_n;hrst_l1<=hrst_l0;end
 wire srst_n=srst_l1,hrst_n=hrst_l1;
 function automatic [29:0] fold(input [28:0] o,input q);
  fold={o[28:6],q^o[10]^o[15],o[5:0]};
 endfunction
 // ---------------------------------------------------------------- stream pins
 reg rv_q,rb_q,fb_q,fs_q;reg[15:0]re_q,fe_q;reg[11:0]rt_q;reg[31:0]rbase_q;reg[2311:0]wd_q;reg[1:0]stk_q;reg q_s;
 always @(posedge stream_clk)begin
  rb_q<=wb_reserve_bank;fb_q<=wb_fill_bank;re_q<=wb_reserve_epoch;fe_q<=wb_fill_epoch;rt_q<=wb_reserve_sectors;
  rbase_q<=wb_reserve_base;wd_q<=wd;stk_q<=stk;q_s<=(MUT==2)?1'b0:quad;
 end
 always @(posedge stream_clk or negedge srst_n)
  if(!srst_n)begin rv_q<=0;fs_q<=0;end else begin rv_q<=wb_reserve_v;fs_q<=wb_fill_start;end
 // stack check + stack-local ordinals
 reg[2311:0]wd_l;reg wd_stk_bad;integer s;
 always @*begin
  wd_l=wd_q;wd_stk_bad=0;
  for(s=0;s<8;s=s+1)begin
   if(wd_q[289*s+288]&&wd_q[289*s+286+:2]!=stk_q)wd_stk_bad=1;
   wd_l[289*s+286+:2]=2'b00;
  end
 end
 wire rbase_stk_bad=rv_q&&rbase_q[31:30]!=stk_q;
 // ---------------------------------------------------------------- write-back block (quadrant mode)
 wire reserve_ready,fill_done,done_v,done_bank,blk_fault;wire[15:0]done_epoch;wire[11:0]done_sectors;wire[1:0]owned;
 wire[15:0]k_v,k_rdy,k_we,k_wr_done_q;wire[479:0]k_addr;wire[4095:0]k_wdata;wire[63:0]k_len;wire[271:0]k_tag;wire[511:0]k_wstrb;
 ot_hbm_svc_wb_cutthrough_cdc #(.STACK(2'd0),.NPC(16),.QFOLD(1)) u_wb(
  .stream_clk(stream_clk),.stream_rst_n(srst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hrst_n),.stream_fifo_clk(stream_fifo_clk),
  .reserve_v(rv_q),.reserve_ready(reserve_ready),.reserve_bank(rb_q),.reserve_epoch(re_q),.reserve_base({2'b00,rbase_q[29:0]}),
  .reserve_total(rt_q),.fill_start(fs_q),.fill_start_bank(fb_q),.fill_start_epoch(fe_q),.wd(wd_l),
  .fill_done(fill_done),.done_v(done_v),.done_bank(done_bank),.done_epoch(done_epoch),.done_sectors(done_sectors),
  .bank_owned(owned),.fault(blk_fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
  .k_wr_done(k_wr_done_q));
 // ---------------------------------------------------------------- real window of a reservation (2 registered stages)
 reg rv1,rb1,rv2,rb2;reg[28:0]ob1,oe1;reg[29:0]sb2,se2;reg rq1;
 always @(posedge stream_clk or negedge srst_n)
  if(!srst_n)begin rv1<=0;rv2<=0;end else begin rv1<=rv_q&&reserve_ready;rv2<=rv1;end
 always @(posedge stream_clk)begin
  rb1<=rb_q;ob1<=rbase_q[28:0];oe1<=rbase_q[28:0]+29'(rt_q)-29'd1;rq1<=q_s;
  rb2<=rb1;sb2<=fold(ob1,rq1);se2<=fold(oe1,rq1);
 end
 wire[30:0]span2={1'b0,se2}-{1'b0,sb2}+31'd1;
 wire span_bad=rv2&&(span2>31'd4095||{1'b0,se2}>={1'b0,STACK_SECTORS});
 // ---------------------------------------------------------------- reservation receipts, wb_ready, wa, window command
 reg[1:0]accepted;reg[15:0]aepoch[0:1];reg[11:0]atotal[0:1];reg[29:0]wbase[0:1];reg[11:0]wspan[0:1];reg rfault;
 reg fsb_q;   // buffer whose fill is in progress (for the WOPEN=1 window)
 wire block_ready=accepted[fb_q]&&aepoch[fb_q]==fe_q&&owned[fb_q];
 wire win_go=(WOPEN==0)?fs_q:fill_done;
 wire win_bank=(WOPEN==0)?fb_q:fsb_q;
 always @(posedge stream_clk or negedge srst_n)begin
  if(!srst_n)begin
   accepted<=0;rfault<=0;wb_ready<=0;wa<=0;wbw_v<=0;wbw_base<=0;wbw_total<=0;fault<=0;fsb_q<=0;
   aepoch[0]<=0;aepoch[1]<=0;atotal[0]<=0;atotal[1]<=0;wbase[0]<=0;wbase[1]<=0;wspan[0]<=0;wspan[1]<=0;
  end else begin
   if(rv_q)begin
    if(!reserve_ready)rfault<=1;
    else begin accepted[rb_q]<=1;aepoch[rb_q]<=re_q;atotal[rb_q]<=rt_q;end
   end
   if(rv2)begin wbase[rb2]<=sb2;wspan[rb2]<=(MUT==3)?atotal[rb2]:span2[11:0];end
   if(done_v)begin
    if(!accepted[done_bank]||aepoch[done_bank]!=done_epoch||atotal[done_bank]!=done_sectors)rfault<=1;
    accepted[done_bank]<=0;
   end
   if(fs_q)fsb_q<=fb_q;
   if(rbase_stk_bad||wd_stk_bad||span_bad)rfault<=1;
   wb_ready<=block_ready;
   wa<=(MUT==1)?(fill_done?atotal[fsb_q]:12'd0):(done_v?done_sectors:12'd0);
   wbw_v<=win_go;wbw_base<=wbase[win_bank];wbw_total<=wspan[win_bank];
   fault<=rfault||blk_fault;
  end
 end
 // ---------------------------------------------------------------- K write pins (hbm_clk)
 reg[15:0]wr_done_q;reg q_h;
 always @(posedge hbm_clk)q_h<=(MUT==2)?1'b0:quad;
 always @(posedge hbm_clk or negedge hrst_n)if(!hrst_n)wr_done_q<=0;else wr_done_q<=w_k_wr_done;
 assign k_wr_done_q=wr_done_q;
 genvar p;
 generate for(p=0;p<16;p=p+1)begin:pc
  ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_k(.clk(hbm_clk),.rst_n(hrst_n),.in_v(k_v[p]),.in_r(k_rdy[p]),
   .in_data({fold(k_addr[30*p+:29],q_h),k_wdata[256*p+:256]}),.out_v(w_k_v[p]),.out_r(w_k_rdy[p]),
   .out_data({w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}));
 end endgenerate
endmodule
`default_nettype wire
