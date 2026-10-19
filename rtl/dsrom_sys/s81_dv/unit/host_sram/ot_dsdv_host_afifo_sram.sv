`timescale 1ns/1ps
// SH storage successor for ot_link_afifo, same ports and write/Gray/credit law.
// Registered SRAM head requires one additional empty-to-nonempty read edge;
// every nonempty pop still advances one word per read clock. Gray stage2 alone
// authorizes reads. No first-stage synchronizer output enters functional logic.
module ot_dsdv_host_afifo_sram #(parameter integer W=514, AW=4, SYNC=2, EC=1) (
 input wire wclk,wrst_n,wr,input wire [W-1:0] wdata,
 output wire wfull,output reg [AW:0] wfreed,output reg ovf,
 input wire rclk,rrst_n,rd,output wire rempty,
 output wire [W-1:0] rdata,output wire [AW:0] rcount,
 // S81-SHLK s10b: EC kept copies of the empty flag (same D, same edge) for wide consumer enables
 output wire [EC-1:0] rempty_c
);
 localparam integer D=1<<AW;
 initial if(W>546||AW>4||AW<2||SYNC<2) $fatal(1,"SH SRAM FIFO unsupported shape");
 function automatic [AW:0] g2b(input [AW:0] g);
  integer k;begin g2b[AW]=g[AW];for(k=AW-1;k>=0;k=k-1)g2b[k]=g2b[k+1]^g[k];end
 endfunction
 reg [AW:0] wbin,wgray,rbin_seen,rbin,rgray;
 (* async_reg="true" *) reg [AW:0] rgray_s[0:SYNC-1],wgray_s[0:SYNC-1];
 wire [AW:0] rgray_w=rgray_s[SYNC-1],wgray_r=wgray_s[SYNC-1];
 wire [AW:0] wbin_n=wbin+1'b1,wgray_n=wbin_n^(wbin_n>>1),rbin_w=g2b(rgray_w);
 assign wfull=(wgray=={~rgray_w[AW:AW-1],rgray_w[AW-2:0]});
 wire push=wr&&!wfull;
 integer i;
 always @(posedge wclk or negedge wrst_n)
  if(!wrst_n) begin
   wbin<=0;wgray<=0;ovf<=0;rbin_seen<=0;wfreed<=0;
   for(i=0;i<SYNC;i=i+1)rgray_s[i]<=0;
  end else begin
   rgray_s[0]<=rgray;for(i=1;i<SYNC;i=i+1)rgray_s[i]<=rgray_s[i-1];
   wfreed<=rbin_w-rbin_seen;rbin_seen<=rbin_w;
   if(wr&&wfull)ovf<=1;
   if(push)begin wbin<=wbin_n;wgray<=wgray_n;end
  end
 reg empty;
 wire pop=rd&&!empty;
 wire [AW:0] rbin_n=rbin+{{AW{1'b0}},pop};
 wire [AW:0] rgray_n=rbin_n^(rbin_n>>1);
 wire have_next=(rgray_n!=wgray_r);
 always @(posedge rclk or negedge rrst_n)
  if(!rrst_n)begin
   rbin<=0;rgray<=0;empty<=1;
   for(i=0;i<SYNC;i=i+1)wgray_s[i]<=0;
  end else begin
   wgray_s[0]<=wgray;for(i=1;i<SYNC;i=i+1)wgray_s[i]<=wgray_s[i-1];
   rbin<=rbin_n;rgray<=rgray_n;empty<=!have_next;
  end
 assign rempty=empty;
 (* keep *) reg [EC-1:0] empty_c;
 always @(posedge rclk or negedge rrst_n)
  if(!rrst_n) empty_c<={EC{1'b1}}; else empty_c<={EC{!have_next}};
 assign rempty_c=empty_c;
 assign rcount=g2b(wgray_r)-rbin;
`ifdef S81SH_SRAM_MUT_CURRENT
 wire [3:0] ra={{(4-AW){1'b0}},rbin[AW-1:0]};
`else
 wire [3:0] ra={{(4-AW){1'b0}},rbin_n[AW-1:0]};
`endif
`ifdef S81SH_SRAM_MUT_EMPTYREAD
 wire re=rrst_n;
`else
 wire re=rrst_n&&have_next;
`endif
 wire we=wrst_n&&push;
 wire [3:0] wa={{(4-AW){1'b0}},wbin[AW-1:0]};
`ifdef OT_S81_SH_RSZ
 // S81-SHLK s10: right-sized dual-clock masters (tools/mem_compiler/build_sh_rsz_1019.py): W 514 = two 16x257
 // (89.4 x 39.4 um), W 289 = one 16x289 (99.1 x 44.0 um), instead of one pin-limited 16x546 (176.9 x 81 um, 825
 // contacts a face, write data split over both faces).  Same addresses, enables, Gray/credit law and edges.
 if(W==514) begin:g_rsz2
`ifdef S81SH_RSZ_MUT_SWAP
  ot_sram_1r1w2c_16x257_m1 u_mem0(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rdata[256:0]),
   .w_ce_in(we),.w_addr_in(wa),.wd_in({wdata[256:1],wdata[0]^wdata[300]}),.w_mask_in({257{1'b1}}));   // mutant: one bit of the low half corrupted by the high half
`else
  ot_sram_1r1w2c_16x257_m1 u_mem0(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rdata[256:0]),
   .w_ce_in(we),.w_addr_in(wa),.wd_in(wdata[256:0]),.w_mask_in({257{1'b1}}));
`endif
  ot_sram_1r1w2c_16x257_m1 u_mem1(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rdata[513:257]),
   .w_ce_in(we),.w_addr_in(wa),.wd_in(wdata[513:257]),.w_mask_in({257{1'b1}}));
 end else if(W==289) begin:g_rsz1
  ot_sram_1r1w2c_16x289_m1 u_mem(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rdata),
   .w_ce_in(we),.w_addr_in(wa),.wd_in(wdata),.w_mask_in({289{1'b1}}));
 end else begin:g_rsz_bad
  initial $fatal(1,"OT_S81_SH_RSZ: no right-sized master for W=%0d",W);
 end
`elsif OT_S81_SH_BANK64
 // S81-SHLK s10 (sr9 gate: the 176.9 x 81 um 16x546 macro is pin-limited, 825 contacts a face = 10.2/um, its write
 // data split over both faces, 2% array efficiency): ceil(W/64) native 32x64 dual-clock banks (31.99 x 17.30 um,
 // 103 contacts a face <= 6/um), rows 16..31 unused, address zero-extended.  Same Gray/credit law, same edges.
 // The W mod 64 tail bits (hx 2, ox 33) sit in a D x TB flop array with the SAME synchronous read (captured on re
 // at ra, held otherwise), so no bank carries < 64 used bits; D x TB <= 528 bits (well under the 2 kb SRAM rule).
 localparam integer NB=W/64, TB=W-NB*64;
 wire [NB*64-1:0] bq;
 genvar mb;
 for(mb=0;mb<NB;mb=mb+1) begin:g_bank
  ot_sram_1r1w2c_32x64_m1 u_mem(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in({1'b0,ra}),.rd_out(bq[mb*64+:64]),
   .w_ce_in(we),.w_addr_in({1'b0,wa}),.wd_in(wdata[mb*64+:64]),.w_mask_in({64{1'b1}}));
 end
 if(TB>0) begin:g_tail
  reg [TB-1:0] tmem[0:D-1];
  reg [TB-1:0] tq;
`ifdef S81SH_BANK_MUT_TAIL
  always @(posedge wclk) if(we) tmem[wa[AW-1:0]+1'b1]<=wdata[W-1-:TB];   // mutant: tail written one slot ahead
`else
  always @(posedge wclk) if(we) tmem[wa[AW-1:0]]<=wdata[W-1-:TB];
`endif
  always @(posedge rclk) if(re) tq<=tmem[ra[AW-1:0]];
  assign rdata={tq,bq};
 end else begin:g_notail
  assign rdata=bq;
 end
`else
 wire [545:0] q;
 ot_sram_1r1w2c_16x546_m1 u_mem(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(q),
  .w_ce_in(we),.w_addr_in(wa),.wd_in({{(546-W){1'b0}},wdata}),.w_mask_in({546{1'b1}}));
 assign rdata=q[W-1:0];
`endif
`ifndef SYNTHESIS
 always @(posedge wclk or posedge rclk)
  if(wrst_n&&rrst_n&&we&&re&&wa==ra)$fatal(1,"SH_SRAM_FIFO_COLLISION addr%0d",ra);
`endif
endmodule
