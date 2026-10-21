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
// HBM-WBK2 2026-10-20 (H.STA.BLK.5 structural successor, kit hbm_wbk_q2_1020): the write-back block is now
// ot_hbm_svc_wb_kq2_core (ot_hbm_svc_wb_kq2.sv: stream-family copy + registered one-hot lane -> PC select + per-PC
// 32-b-sliced reviewed ot_link_afifo crossing + 32-b-sliced K pin skids; reset relays of <= 32 loads).  This wrapper keeps
// every stream-pin behaviour above unchanged; its control registers reset from core relay leaves (either landed reset
// resets the whole port), and the pins that fan out widely are captured in KEPT pin copies (fill_start x8,
// wb_fill_bank x6, reservation bank x2, window bank selects x2).  FAW = log2 depth of the per-PC crossing FIFOs.
// HBM-WBK8 2026-10-20 (census-safe successor, kits hbm_wbk_q8*_1020): the block is ot_hbm_svc_wb_kq8_core
// (ot_hbm_svc_wb_kq8.sv: 16-b reviewed crossing FIFOs, AW = FAW, PP = 1 ping-pong pairs = 8 entries per PC; lockstep
// registered pops; 3-entry K pin rings).  This wrapper: fill_start x8 / fill_bank x7 core copies; the reservation epoch
// and total are stored ONE edge after the reservation under kept per-entry write enables (read >= 10 edges later); every
// window-register select / write enable is a kept copy serving <= 16 bits.  Stream-pin behaviour unchanged.
module ot_hbm_svc_wb_kport_q #(parameter integer WOPEN=0, parameter integer MUT=0, parameter integer FAW=2,
                               parameter integer PP=1,
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
 wire [1:0] kr;                                  // core stream-family relay leaves for this wrapper's control registers
 function automatic [29:0] fold(input [28:0] o,input q);
  fold={o[28:6],q^o[10]^o[15],o[5:0]};
 endfunction
 // ---------------------------------------------------------------- stream pins
 reg rv_q,rb_q,fb_q,fs_q;reg[15:0]re_q,fe_q;reg[11:0]rt_q;reg[31:0]rbase_q;reg[2311:0]wd_q;reg q_s;
 (* keep="true",dont_touch="true" *) reg[1:0]stk_c[0:2];   // stack strap copies: slots 0..3, 4..7, base check
 (* keep="true",dont_touch="true" *) reg fs_c [0:7];      // fill_start pin copies for the core fill FSM copies
 (* keep="true",dont_touch="true" *) reg fb_c [0:15];     // wb_fill_bank pin copies: core 0..6/14/15, aepoch 7/11, window 8..10/12/13
 (* keep="true",dont_touch="true" *) reg rb_c;            // wb_reserve_bank pin copy for the core
 integer ci;
 always @(posedge stream_clk)begin
  rb_q<=wb_reserve_bank;rb_c<=wb_reserve_bank;fb_q<=wb_fill_bank;for(ci=0;ci<16;ci=ci+1)fb_c[ci]<=wb_fill_bank;
  re_q<=wb_reserve_epoch;fe_q<=wb_fill_epoch;rt_q<=wb_reserve_sectors;
  rbase_q<=wb_reserve_base;wd_q<=wd;for(ci=0;ci<3;ci=ci+1)stk_c[ci]<=stk;q_s<=(MUT==2)?1'b0:quad;
 end
 always @(posedge stream_clk or negedge kr[0])
  if(!kr[0])begin rv_q<=0;fs_q<=0;for(ci=0;ci<8;ci=ci+1)fs_c[ci]<=1'b0;end
  else begin rv_q<=wb_reserve_v;fs_q<=wb_fill_start;for(ci=0;ci<8;ci=ci+1)fs_c[ci]<=wb_fill_start;end
 // stack check + stack-local ordinals
 reg[2311:0]wd_l;reg wd_stk_bad;integer s;
 always @*begin
  wd_l=wd_q;wd_stk_bad=0;
  for(s=0;s<8;s=s+1)begin
   if(wd_q[289*s+288]&&wd_q[289*s+286+:2]!=stk_c[s/4])wd_stk_bad=1;
   wd_l[289*s+286+:2]=2'b00;
  end
 end
 wire rbase_stk_bad=rv_q&&rbase_q[31:30]!=stk_c[2];
 // ---------------------------------------------------------------- write-back block (quadrant mode)
 wire reserve_ready,fill_done,done_v,blk_fault;wire[2:0]done_bank;wire[15:0]done_epoch;wire[11:0]done_sectors;wire[1:0]owned;
 reg q_h;
 always @(posedge hbm_clk)q_h<=(MUT==2)?1'b0:quad;
 ot_hbm_svc_wb_kq8_core #(.FAW(FAW),.PP(PP),.MUT(MUT)) u_wb(
  .stream_clk(stream_clk),.hbm_clk(hbm_clk),.stream_fifo_clk(stream_fifo_clk),.srst_in_n(srst_n),.hrst_in_n(hrst_n),
  .kp_rst_n(kr),
  .reserve_v(rv_q),.reserve_ready(reserve_ready),.reserve_bank(rb_c),.reserve_epoch(re_q),.reserve_base({2'b00,rbase_q[29:0]}),
  .reserve_total(rt_q),.fill_start_c({fs_c[7],fs_c[6],fs_c[5],fs_c[4],fs_c[3],fs_c[2],fs_c[1],fs_c[0]}),
  .fill_bank_c({fb_c[15],fb_c[14],fb_c[6],fb_c[5],fb_c[4],fb_c[3],fb_c[2],fb_c[1],fb_c[0]}),.fill_start_epoch(fe_q),.wd(wd_l),
  .fill_done(fill_done),.done_v(done_v),.done_bank(done_bank),.done_epoch(done_epoch),.done_sectors(done_sectors),
  .bank_owned(owned),.fault(blk_fault),.q_h(q_h),
  .w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata),.w_k_wr_done(w_k_wr_done));
 // ---------------------------------------------------------------- real window of a reservation (2 registered stages)
 reg rv1,rv2,rb1;(* keep="true",dont_touch="true" *) reg rb2c [0:2];reg[28:0]ob1,oe1;reg[29:0]sb2,se2;reg rq1;
 always @(posedge stream_clk or negedge kr[0])
  if(!kr[0])begin rv1<=0;rv2<=0;end else begin rv1<=rv_q&&reserve_ready;rv2<=rv1;end
 always @(posedge stream_clk)begin
  rb1<=rb_q;ob1<=rbase_q[28:0];oe1<=rbase_q[28:0]+29'(rt_q)-29'd1;rq1<=q_s;
  rb2c[0]<=rb1;rb2c[1]<=rb1;rb2c[2]<=rb1;sb2<=fold(ob1,rq1);se2<=fold(oe1,rq1);
 end
 wire[30:0]span2={1'b0,se2}-{1'b0,sb2}+31'd1;
 wire span_bad=rv2&&(span2>31'd4095||{1'b0,se2}>={1'b0,STACK_SECTORS});
 // ---------------------------------------------------------------- reservation receipts, wb_ready, wa, window command
 reg[1:0]accepted;reg[15:0]aepoch[0:1];reg[11:0]atotal[0:1];reg[29:0]wbase[0:1];reg[11:0]wspan[0:1];reg rfault;
 (* keep="true",dont_touch="true" *) reg fsb_c [0:5];   // buffer whose fill is in progress (for the WOPEN=1 window)
 wire block_ready=accepted[fb_q]&&aepoch[fb_c[7]][7:0]==fe_q[7:0]&&aepoch[fb_c[11]][15:8]==fe_q[15:8]&&owned[fb_q];
 wire win_go=(WOPEN==0)?fs_q:fill_done;
 wire wb_b=(WOPEN==0)?fb_c[8]:fsb_c[0];          // window base select (bits 7:0)
 wire wb_b2=(WOPEN==0)?fb_c[12]:fsb_c[4];        // window base select (bits 14:8)
 wire wb_h=(WOPEN==0)?fb_c[9]:fsb_c[2];          // window base select (bits 22:15)
 wire wb_h2=(WOPEN==0)?fb_c[13]:fsb_c[5];        // window base select (bits 29:23)
 wire wb_t=(WOPEN==0)?fb_c[10]:fsb_c[1];         // window total select
 always @(posedge stream_clk or negedge kr[0])begin
  if(!kr[0])begin
   accepted<=0;rfault<=0;wb_ready<=0;wbw_v<=0;fault<=0;
  end else begin
   if(rv_q)begin
    if(!reserve_ready)rfault<=1;
    else accepted[rb_q]<=1;
   end
   if(done_v)begin
    if(!accepted[done_bank[0]]||aepoch[done_bank[1]]!=done_epoch||atotal[done_bank[2]]!=done_sectors)rfault<=1;
    accepted[done_bank[0]]<=0;
   end
   if(rbase_stk_bad||wd_stk_bad||span_bad)rfault<=1;
   wb_ready<=block_ready;
   wbw_v<=win_go;
   fault<=rfault||blk_fault;
  end
 end
 always @(posedge stream_clk or negedge kr[1])
  if(!kr[1])wa<=0;
  else wa<=(MUT==1)?(fill_done?atotal[fsb_c[3]]:12'd0):(done_v?done_sectors:12'd0);
 // reservation receipt data: one edge after the reservation, kept per-entry write enables (epoch / total)
 reg[15:0]re_q1;reg[11:0]rt_q1;(* keep="true",dont_touch="true" *) reg[1:0]awe[0:1];
 integer ai;
 always @(posedge stream_clk)begin
  re_q1<=re_q;rt_q1<=rt_q;
  for(ai=0;ai<2;ai=ai+1)awe[ai]<={rv_q&&reserve_ready&&rb_q,rv_q&&reserve_ready&&!rb_q};
  for(ai=0;ai<2;ai=ai+1)begin
   if(awe[0][ai])aepoch[ai]<=re_q1;
   if(awe[1][ai])atotal[ai]<=rt_q1;
  end
  if(rv2)begin
   wbase[rb2c[0]][14:0]<=sb2[14:0];
   wbase[rb2c[1]][29:15]<=sb2[29:15];
   wspan[rb2c[2]]<=(MUT==3)?atotal[rb2c[2]]:span2[11:0];
  end
  if(fs_q)for(ai=0;ai<6;ai=ai+1)fsb_c[ai]<=fb_q;
  wbw_base<={wbase[wb_h2][29:23],wbase[wb_h][22:15],wbase[wb_b2][14:8],wbase[wb_b][7:0]};wbw_total<=wspan[wb_t];
 end
endmodule
`default_nettype wire
