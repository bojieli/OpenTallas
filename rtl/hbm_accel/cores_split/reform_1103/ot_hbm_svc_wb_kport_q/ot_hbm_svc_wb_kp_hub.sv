`default_nettype none
// DIE-HBM-62/KPORT 2026-11-03: RE-FORM of ot_hbm_svc_wb_kport_q.  Hub of the quadrant write-back block: every stream pin
// rule, reservation, window command and watermark of ot_hbm_svc_wb_kport_q + ot_hbm_svc_wb_cutthrough_cdc (NPC=16, QFOLD=1,
// same stream edges), the payload moved out to 4 x ot_hbm_svc_wb_kp_root.  K side: 16 port FIFOs (root r, port j), per PC p a
// 4:1 pick over (r, p[1:0]) and the K pin skids.  All added edges are inside the variable-wait K path (the DMA-side schedule
// sees wa only, posted on true completion), so nothing changes for the compiler.
// wd_ctl: per wd lane s {valid, sector[31:0]} = wd[289*s+288:289*s+256].  MUT as ot_hbm_svc_wb_kport_q (1,2,3) and
// 4 (bench only) = port FIFO overwrites its head when full is ignored at the pick (K address of a stale head).
module ot_hbm_svc_wb_kp_hub #(parameter integer WOPEN=0, parameter integer MUT=0, parameter integer DEPTH=4,
                              parameter [29:0] STACK_SECTORS=30'd703125000)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stk,
 input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[263:0]wd_ctl,
 output reg wb_ready,output reg[11:0]wa,
 output reg wbw_v,output reg[29:0]wbw_base,output reg[11:0]wbw_total,
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output reg fault,
 // copy frame to the roots (stream_clk)
 output wire c_active,c_bank,c_fault,output wire[29:0]c_base,output wire[11:0]c_committed,
 input wire[3:0]root_ready,
 // ports from the roots (hbm_clk): index 4*r+j
 input wire[15:0]port_v,input wire[31:0]port_pc,input wire[479:0]port_addr,input wire[4095:0]port_data,
 output wire[15:0]port_credit
);
 function automatic [29:0] fold(input [28:0] o,input q);
  fold={o[28:6],q^o[10]^o[15],o[5:0]};
 endfunction
 // ---------------------------------------------------------------- stream pins (ot_hbm_svc_wb_kport_q)
 reg rv_q,rb_q,fb_q,fs_q;reg[15:0]re_q,fe_q;reg[11:0]rt_q;reg[31:0]rbase_q;reg[263:0]wd_q;reg[1:0]stk_q;reg q_s;
 always @(posedge stream_clk)begin
  rb_q<=wb_reserve_bank;fb_q<=wb_fill_bank;re_q<=wb_reserve_epoch;fe_q<=wb_fill_epoch;rt_q<=wb_reserve_sectors;
  rbase_q<=wb_reserve_base;wd_q<=wd_ctl;stk_q<=stk;q_s<=(MUT==2)?1'b0:quad;
 end
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin rv_q<=0;fs_q<=0;end else begin rv_q<=wb_reserve_v;fs_q<=wb_fill_start;end
 reg wd_stk_bad;reg[7:0]wd_vq;reg[31:0]wd_sec[0:7];integer s0;
 always @*begin
  wd_stk_bad=0;
  for(s0=0;s0<8;s0=s0+1)begin
   wd_vq[s0]=wd_q[33*s0+32];
   if(wd_q[33*s0+32]&&wd_q[33*s0+30+:2]!=stk_q)wd_stk_bad=1;
   wd_sec[s0]={2'b00,wd_q[33*s0+:30]};
  end
 end
 wire rbase_stk_bad=rv_q&&rbase_q[31:30]!=stk_q;
 // ---------------------------------------------------------------- block control (ot_hbm_svc_wb_cutthrough_cdc, stream side)
 localparam [32:0] SPACE_END=33'h020000000;
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;wire roots_ready=&root_ready;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 reg [1:0] allocated,started,staged;reg [15:0] epoch[0:1];
 reg [31:0] base[0:1];reg [11:0] total[0:1];reg [11:0] committed[0:1];
 reg filling,fill_bank,copy_active,copy_bank;reg [11:0] ordinal;
 reg stream_sticky,hbm_sticky;(* async_reg = "true" *) reg hf1,hf2,sf1,sf2;
 wire [28:0] meta_data,ack_data;wire meta_full,meta_empty,ack_full,ack_empty;
 wire meta_we,meta_re,ack_we,ack_re;
 reg meta_active,ack_pending;reg [28:0] meta_q;reg [11:0] ack_count;
 wire hbm_fault=hbm_sticky||sf2||!hrst;
 wire blk_fault=stream_sticky||hf2;
 wire [31:0] reserve_base_i={2'b00,rbase_q[29:0]};
 wire [32:0] reserve_end={3'b0,reserve_base_i[29:0]}+rt_q;
 wire reserve_ready=srst&&roots_ready&&!allocated[rb_q]&&!blk_fault&&rt_q!=0&&rt_q<=2048&&
  reserve_base_i[31:30]==2'd0&&reserve_end<=SPACE_END;
 wire [1:0] copy_eligible={staged[1]&&committed[1]!=0,staged[0]&&committed[0]!=0};
 wire start_copy=srst&&roots_ready&&!copy_active&&(|copy_eligible)&&!meta_full&&!blk_fault;
 wire choose_bank=!copy_eligible[0];
 assign meta_we=start_copy;
 ot_hbm_accel_cdc_fifo #(.W(29),.AW(2)) u_meta(
 .wclk(stream_clk),.wrst_n(srst),.we(meta_we),.wdata({choose_bank,epoch[choose_bank],total[choose_bank]}),.full(meta_full),.rd_freed(),
 .rclk(hbm_clk),.rrst_n(hrst),.re(meta_re),.rdata(meta_data),.empty(meta_empty));
 assign meta_re=!meta_active&&!meta_empty&&!hbm_fault;
 assign ack_we=ack_pending&&!ack_full&&!hbm_fault;
 assign ack_re=srst&&!ack_empty&&!blk_fault;
 ot_hbm_accel_cdc_fifo #(.W(29),.AW(2)) u_ack(
 .wclk(hbm_clk),.wrst_n(hrst),.we(ack_we),.wdata(meta_q),.full(ack_full),.rd_freed(),
 .rclk(stream_clk),.rrst_n(srst),.re(ack_re),.rdata(ack_data),.empty(ack_empty));
 assign c_active=copy_active;assign c_bank=copy_bank;assign c_fault=blk_fault;
 assign c_base=base[copy_bank][29:0];assign c_committed=committed[copy_bank];
 reg fill_done,done_v,done_bank;reg [15:0] done_epoch;reg [11:0] done_sectors;
 integer s;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;started<=0;staged<=0;filling<=0;fill_bank<=0;ordinal<=0;copy_active<=0;copy_bank<=0;
   stream_sticky<=0;hf1<=0;hf2<=0;fill_done<=0;done_v<=0;done_bank<=0;done_epoch<=0;done_sectors<=0;
   for(s=0;s<2;s=s+1)begin epoch[s]<=0;base[s]<=0;total[s]<=0;committed[s]<=0;end
  end else begin
   hf1<=hbm_sticky;hf2<=hf1;fill_done<=0;done_v<=0;
   if(rv_q)begin
    if(!reserve_ready)stream_sticky<=1;
    else begin allocated[rb_q]<=1;started[rb_q]<=0;staged[rb_q]<=0;
     epoch[rb_q]<=re_q;base[rb_q]<=reserve_base_i;total[rb_q]<=rt_q;committed[rb_q]<=0;end
   end
   if(fs_q)begin
    if(!roots_ready||filling||!allocated[fb_q]||started[fb_q]||epoch[fb_q]!=fe_q)stream_sticky<=1;
    else begin filling<=1;fill_bank<=fb_q;ordinal<=0;started[fb_q]<=1;staged[fb_q]<=1;end
   end
   if(filling&&!blk_fault)begin
    for(s=0;s<8;s=s+1)begin
     if(ordinal+s<total[fill_bank])begin
      if(!wd_vq[s]||wd_sec[s]!=(base[fill_bank]+ordinal+s))stream_sticky<=1;
     end else if(wd_vq[s])stream_sticky<=1;
    end
    if(ordinal+8>=total[fill_bank])begin filling<=0;committed[fill_bank]<=total[fill_bank];fill_done<=1;end
    else begin ordinal<=ordinal+8;committed[fill_bank]<=((ordinal+12'd8)>>5)<<5;end
   end else if(!blk_fault&&|wd_vq)stream_sticky<=1;
   if(start_copy)begin copy_active<=1;copy_bank<=choose_bank;staged[choose_bank]<=0;end
   if(ack_re)begin
    if(!copy_active||ack_data[28]!=copy_bank||ack_data[27:12]!=epoch[copy_bank]||ack_data[11:0]!=total[copy_bank])stream_sticky<=1;
    else begin allocated[copy_bank]<=0;copy_active<=0;done_v<=1;done_bank<=copy_bank;done_epoch<=epoch[copy_bank];done_sectors<=ack_data[11:0];end
   end
  end
 end
 // ---------------------------------------------------------------- real window of a reservation (ot_hbm_svc_wb_kport_q)
 reg rv1,rb1,rv2,rb2;reg[28:0]ob1,oe1;reg[29:0]sb2,se2;reg rq1;
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin rv1<=0;rv2<=0;end else begin rv1<=rv_q&&reserve_ready;rv2<=rv1;end
 always @(posedge stream_clk)begin
  rb1<=rb_q;ob1<=rbase_q[28:0];oe1<=rbase_q[28:0]+29'(rt_q)-29'd1;rq1<=q_s;
  rb2<=rb1;sb2<=fold(ob1,rq1);se2<=fold(oe1,rq1);
 end
 wire[30:0]span2={1'b0,se2}-{1'b0,sb2}+31'd1;
 wire span_bad=rv2&&(span2>31'd4095||{1'b0,se2}>={1'b0,STACK_SECTORS});
 reg[1:0]accepted;reg[15:0]aepoch[0:1];reg[11:0]atotal[0:1];reg[29:0]wbase[0:1];reg[11:0]wspan[0:1];reg rfault;
 reg fsb_q;
 wire[1:0]owned=allocated;
 wire block_ready=accepted[fb_q]&&aepoch[fb_q]==fe_q&&owned[fb_q];
 wire win_go=(WOPEN==0)?fs_q:fill_done;
 wire win_bank=(WOPEN==0)?fb_q:fsb_q;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
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
 // ---------------------------------------------------------------- port FIFOs (hbm_clk), index 4*r+j; a sender holds DEPTH credits
 localparam integer AW=$clog2(DEPTH);
 reg[287:0]pf_mem[0:15][0:DEPTH-1];reg[AW:0]pf_wp[0:15],pf_rp[0:15];
 wire[15:0]pf_ne;wire[287:0]pf_head[0:15];reg[15:0]pf_pop;
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:g_pf
  assign pf_ne[g]=pf_wp[g]!=pf_rp[g];
  assign pf_head[g]=pf_mem[g][pf_rp[g][AW-1:0]];
 end endgenerate
 integer f;
 always @(posedge hbm_clk or negedge hrst)
  if(!hrst)for(f=0;f<16;f=f+1)begin pf_wp[f]<=0;pf_rp[f]<=0;end
  else for(f=0;f<16;f=f+1)begin
   if(port_v[f])pf_wp[f]<=pf_wp[f]+1'b1;
   if(pf_pop[f])pf_rp[f]<=pf_rp[f]+1'b1;
  end
 always @(posedge hbm_clk) for(f=0;f<16;f=f+1)
  if(port_v[f])pf_mem[f][pf_wp[f][AW-1:0]]<={port_pc[2*f+:2],port_addr[30*f+:30],port_data[256*f+:256]};
 assign port_credit=pf_pop;
 // ---------------------------------------------------------------- per-PC pick, K requests, completions
 reg[15:0]k_v;reg[479:0]k_addr;reg[4095:0]k_wdata;wire[15:0]k_rdy;reg[15:0]k_wr_done_q;
 reg[15:0]req_valid;reg[1:0]req_root[0:15];reg[6:0]outstanding[0:15];
 reg[15:0]pick_v;reg[1:0]pick_root[0:15];reg[1:0]sel_root[0:15];
 integer pc,r,acks;reg[3:0]src;
 always @*begin
  pick_v=0;pf_pop=0;k_v=0;k_addr=0;k_wdata=0;acks=0;
  for(pc=0;pc<16;pc=pc+1)begin
   pick_root[pc]=0;
   for(r=3;r>=0;r=r-1)if(pf_ne[4*r+pc%4]&&pf_head[4*r+pc%4][287:286]==2'(pc/4))begin pick_v[pc]=1;pick_root[pc]=2'(r);end
   sel_root[pc]=req_valid[pc]?req_root[pc]:pick_root[pc];
   src=4'(4*sel_root[pc]+pc%4);
   if(meta_active&&(req_valid[pc]||pick_v[pc])&&!ack_pending&&(outstanding[pc]<64||k_wr_done_q[pc])&&!hbm_fault)begin
    k_v[pc]=1;k_addr[30*pc+:30]=pf_head[src][285:256];k_wdata[256*pc+:256]=pf_head[src][255:0];
    if(k_rdy[pc])pf_pop[src]=1;
   end
   if(k_wr_done_q[pc]&&(outstanding[pc]!=0||(k_v[pc]&&k_rdy[pc])))acks=acks+1;
  end
 end
 integer h;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   sf1<=0;sf2<=0;hbm_sticky<=0;meta_active<=0;meta_q<=0;ack_pending<=0;ack_count<=0;req_valid<=0;
   for(h=0;h<16;h=h+1)begin req_root[h]<=0;outstanding[h]<=0;end
  end else begin
   sf1<=stream_sticky;sf2<=sf1;
   if(meta_re)begin meta_active<=1;meta_q<=meta_data;ack_count<=0;ack_pending<=0;end
   if(meta_active&&!hbm_fault)begin
    for(h=0;h<16;h=h+1)begin
     if(k_v[h]&&!k_rdy[h])begin req_valid[h]<=1;req_root[h]<=sel_root[h];end
     if(k_v[h]&&k_rdy[h])req_valid[h]<=0;
     case ({k_v[h]&&k_rdy[h],k_wr_done_q[h]})
      2'b10:outstanding[h]<=outstanding[h]+1'b1;
      2'b01:if(outstanding[h]!=0)outstanding[h]<=outstanding[h]-1'b1;
      default:begin end
     endcase
     if(k_wr_done_q[h]&&!(outstanding[h]!=0||(k_v[h]&&k_rdy[h])))hbm_sticky<=1;
    end
    if(acks!=0)begin
     ack_count<=ack_count+acks;
     if(ack_count+acks>meta_q[11:0])hbm_sticky<=1;
     if(ack_count+acks==meta_q[11:0])ack_pending<=1;
    end
   end else if(|k_wr_done_q)hbm_sticky<=1;
   if(ack_we)begin ack_pending<=0;meta_active<=0;end
  end
 end
 // ---------------------------------------------------------------- K write pins
 reg q_h;
 always @(posedge hbm_clk)q_h<=(MUT==2)?1'b0:quad;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)k_wr_done_q<=0;else k_wr_done_q<=w_k_wr_done;
 genvar p;
 generate for(p=0;p<16;p=p+1)begin:pc_k
  // One output register per PC (same w_k_v/w_k_rdy contract as the skid2 of the source; the ready path is combinational
  // inside the 1024-ps hbm_clk period, between the pin face register and the FIFO pointers).
  reg o_v;reg[285:0]o_d;
  assign k_rdy[p]=!o_v||w_k_rdy[p];assign w_k_v[p]=o_v;assign {w_k_addr[30*p+:30],w_k_wdata[256*p+:256]}=o_d;
  always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)o_v<=0;else if(k_rdy[p])o_v<=k_v[p];
  always @(posedge hbm_clk)if(k_v[p]&&k_rdy[p])o_d<={fold(k_addr[30*p+:29],q_h),k_wdata[256*p+:256]};
 end endgenerate
endmodule
`default_nettype wire
