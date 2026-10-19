`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx: options C + C2 + P2 + 2,048-word programme store) -- the per-SM HBM
// service ISSUER with a TOKEN-RESIDENT descriptor table.  Successor of ot_hbm_svc_sm_issuer (FIXED_GO=1 behaviour kept;
// the old module is untouched).  As built, a token needs ~1,700 descriptors per SM (128-row table, rewritten per layer
// through the host ingress: ~51k ingress edges a layer vs ~14.6k cycles, and run-locked -> the static schedule would
// stall).  Here every descriptor is RELATIVE, so one table install serves every layer of the token:
//   C  (layer stride):  BLOCK = {row_base, slot} + run_layer x layer_stride                  (layer-major placement)
//   C2 (indexed expert): ... + ids[id_sel-1] x expert_stride   (routed-expert id from the router's broadcast, CF-IDXD)
//   where BLOCK is an 18-bit block address = DRAM row index [17:3] + sub-row slot [2:0] (base[9:7], 8 blocks a row index:
//   ot_hbm_svc_sm4pc_cdc_rel_id / prefetch_overlap_owner_rel_id); strides are in blocks.
//   P2 (shape-generic LOOPED programmes): the go carries a CONTEXT {row_off, tag_base, epoch, cache bank, lstep, fl, fmt}
//      that the feed applies to every word (and every loop iteration) of the launched programme, so one 8-word body (one
//      group-slot t step) x loops 8 serves every block of a wave shape; prog_base/limit are 11/12 bits (2,048 words).
//   DD = 256 rows (two 128x256 macros): a DS token's resident set is ~124 layer descriptors (3 layer kinds incl. attention
//      and routed experts) + 54 LM-head blocks + MTP, over 128 (HBM-SMBUDGET finding); DD = 128 keeps one macro.
// run launch: {run_base, run_count} as before plus run_layer (the layer index, carried by the host collar's run launch).
// ids: ids_v pulses {ids_layer, ids[NID x IDW]} once per MoE layer (IDW 9: DS V4.1 has 384 routed experts) (the router's top-k, broadcast to the 16 issuers).  A
// descriptor with id_sel != 0 is held in the RESERVE pipeline (the elastic HBM-prefetch side) until the ids of ITS run's
// layer have arrived; the go stays a compiler slot (FIXED_GO): the compiler proves ids_at + fetch <= go_at, and an id that
// arrives too late is the sticky late-go fault, never a stall of the fixed calendar.
// Descriptor word (256 b, one table row, magic 5d15 [255:240]):
//   [31:0] base (stack [31:30], block slot [9:7], else 0)  [46:32] row_base  [48:47] landing  [64:49] epoch  [71:65] rows (1..64)  [81:72] tag_base
//   [91:82] prog_base[9:0]  [102:92] prog_limit[10:0]  [118:103] loops  [142:119] go_at (edge from the run launch)
//   [157:143] layer_stride  [172:158] expert_stride  [176:173] id_sel (0 none, 1..NID)  [188:177] row_off
//   [189] prog_base[10]  [190] prog_limit[11]  [194:191] lstep (lines per loop iteration; 0 = unlooped)
//   [197:195] SM mode (xc)  [198] mrel (xc takes the mode)  [199] fl (format launch on the programme's first edge)
//   [231:200] zero  [239:232] row identity (8 b; DD 128: [239] zero).
// Reserve pipeline: table read -> A (fields, id wait) -> P (registered 9x15 products) -> S (block = {row_base, slot} +
// products, 18-bit, overflow = fault) -> reserve.  Faults (sticky): bad word, id_sel > NID, row overflow, run while running / count
// 0, issue the feed refuses (queue overflow), late or busy go slot, done without a programme.
// MUT (bench negative controls): 1 layer stride ignored; 2 expert id ignored (id 0); 3 context row_off dropped.
module ot_hbm_svc_sm_issuer_rel #(parameter integer LBANKS=4, parameter integer LB=(LBANKS>2)?2:1, parameter integer QD=4,
 parameter integer NID=6, parameter integer IDW=9, parameter integer PAW=11, parameter integer DD=256, parameter integer MUT=0,
 parameter integer DAW=(DD>128)?8:7, parameter integer ID_COHORT=0)(
 input wire clk,rst_n,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output reg running,run_done,fault,
 output wire reserve_v,input wire reserve_ready,output wire[31:0]reserve_base,output wire[14:0]reserve_row_base,
 output wire[11:0]reserve_total,output wire[LB-1:0]reserve_bank,output wire[15:0]reserve_epoch,output wire[6:0]reserve_rows,
 output wire[9:0]reserve_tag_base,
 input wire[LBANKS-1:0]block_ready,input wire[1:0]cache_ready,cache_owned,
 output wire start_v,output wire[LB-1:0]start_bank,output wire[15:0]start_epoch,
 output wire program_start_v,output wire[PAW-1:0]program_start_base,output wire[PAW:0]program_start_limit,
 output wire[15:0]program_start_loops,
 output wire[45:0]program_start_ctx,   // {row_off12, tag_base10, epoch16, bank1, lstep4, fl1, mode2}
 input wire program_done
);
 initial if(NID<1||NID>15||IDW<1||IDW>9||(PAW!=10&&PAW!=11)||(DD!=128&&DD!=256))$fatal(1,"issuer_rel parameters");
 // descriptor table: DD/128 actual 128x256 SRAMs, registered write port; written at install only (locked while running)
 reg desc_we_q;reg[DAW-1:0]desc_addr_q;reg[255:0]desc_data_q;
 always @(posedge clk)begin desc_addr_q<=desc_addr;desc_data_q<=desc_data;end
 always @(posedge clk or negedge rst_n)if(!rst_n)desc_we_q<=0;else desc_we_q<=desc_we;
 reg rd_q;reg[DAW-1:0]rp,rp_q;wire[255:0]rd;
 wire rd_go;
 generate if(DD==128)begin:g_t1
  ot_sram_1r1w_128x256_m1_r2c2 u_desc(.clk(clk),.r_ce_in(rd_go),.r_addr_in(rp[6:0]),.rd_out(rd),
   .w_ce_in(desc_we_q&&!running),.w_addr_in(desc_addr_q[6:0]),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end else begin:g_t2
  wire[255:0]rd_lo,rd_hi;
  ot_sram_1r1w_128x256_m1_r2c2 u_desc_lo(.clk(clk),.r_ce_in(rd_go&&!rp[7]),.r_addr_in(rp[6:0]),.rd_out(rd_lo),
   .w_ce_in(desc_we_q&&!running&&!desc_addr_q[7]),.w_addr_in(desc_addr_q[6:0]),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  ot_sram_1r1w_128x256_m1_r2c2 u_desc_hi(.clk(clk),.r_ce_in(rd_go&&rp[7]),.r_addr_in(rp[6:0]),.rd_out(rd_hi),
   .w_ce_in(desc_we_q&&!running&&desc_addr_q[7]),.w_addr_in(desc_addr_q[6:0]),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  assign rd=rp_q[7]?rd_hi:rd_lo;
 end endgenerate
 // run / ids registers
 reg[7:0]layer_q,ids_layer_q;reg ids_ok_q;reg[IDW*NID-1:0]ids_q;
 reg[15:0]run_cohort_q;
 // reserve pipeline A -> P -> S
 reg[DAW:0]n_rd,n_go;reg a_v,p_v,st_v;reg[199:0]a,p;reg[142:0]st;reg[23:0]p_lay,p_id;reg[23:0]rc;
 wire[3:0]a_sel=a[176:173];
 wire a_ids=a_sel==0||(ids_ok_q&&ids_layer_q==layer_q);
 wire a_go=a_v&&!p_v&&a_ids;
 wire[IDW-1:0]a_id=(a_sel==0||MUT==2)?{IDW{1'b0}}:ids_q[(a_sel-4'd1)*IDW+:IDW];
 wire[25:0]s_blk={8'd0,p[46:32],p[9:7]}+{2'd0,p_lay}+{2'd0,p_id};
 wire s_go=p_v&&!st_v;
 assign rd_go=running&&n_rd!=0&&!a_v&&!rd_q;
 wire[6:0]st_rows=st[71:65];
 wire[12:0]st_total=(((st_rows*136)+127)>>7)<<2;
 assign reserve_v=st_v&&reserve_ready;
 assign reserve_base=st[31:0];assign reserve_row_base=st[46:32];assign reserve_total=st_total[11:0];
 assign reserve_bank=st[47+:LB];assign reserve_epoch=st[64:49];assign reserve_rows=st_rows;assign reserve_tag_base=st[81:72];
 // start / go queues: {fl1, mode2, lstep4, row_off12, tag10, go_at24, loops16, limit12, base11, epoch16, landing LB}
 localparam integer QW=7+12+10+24+16+12+11+16+LB;
 reg[QW-1:0]sq[0:QD-1],gq[0:QD-1];reg[2:0]sq_n,gq_n;reg[1:0]sq_r,sq_w,gq_r,gq_w;
 reg[QW-1:0]s_ent;
 wire[QW-1:0]sh=sq[sq_r],gh=gq[gq_r];
 wire[LB-1:0]sh_land=sh[LB-1:0];wire[LB-1:0]gh_land=gh[LB-1:0];
 assign start_v=sq_n!=0&&gq_n<QD&&block_ready[sh_land]&&!cache_owned[sh_land[0]];
 assign start_bank=sh_land;assign start_epoch=sh[LB+:16];
 reg go_busy;
 wire[23:0]gh_at=gh[LB+55+:24];
 assign program_start_v=gq_n!=0&&rc==gh_at;
 assign program_start_base=gh[LB+16+:PAW];assign program_start_limit=gh[LB+27+:PAW+1];assign program_start_loops=gh[LB+39+:16];
 wire[11:0]gh_roff=(MUT==3)?12'd0:gh[LB+89+:12];
 assign program_start_ctx={gh_roff,gh[LB+79+:10],gh[LB+:16],gh_land[0],gh[LB+101+:4],gh[LB+107],gh[LB+105+:2]};
 wire push_s=reserve_v,pop_s=start_v,push_g=start_v,pop_g=program_start_v;
 wire[DAW-1:0]rd_id=rd[232+:DAW];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   running<=0;run_done<=0;fault<=0;rd_q<=0;rp<=0;rp_q<=0;n_rd<=0;n_go<=0;a_v<=0;p_v<=0;st_v<=0;st<=0;rc<=0;
   sq_n<=0;gq_n<=0;sq_r<=0;sq_w<=0;gq_r<=0;gq_w<=0;go_busy<=0;layer_q<=0;ids_layer_q<=0;ids_ok_q<=0;run_cohort_q<=0;
  end else begin
   run_done<=0;
   if(run_v)begin
    if(running||run_count==0||{1'b0,run_base}+run_count>(DD))fault<=1;
    else begin
     running<=1;rp<=run_base;n_rd<=run_count;n_go<=run_count;rc<=0;layer_q<=run_layer;
     if(ID_COHORT!=0)begin ids_ok_q<=0;run_cohort_q<=run_cohort_q+16'd1;end
    end
   end
   if(ids_v)begin
    if(ID_COHORT!=0&&(!running||run_v||ids_ok_q||ids_layer!=layer_q||ids_cohort!=run_cohort_q))fault<=1;
    else begin ids_ok_q<=1;ids_layer_q<=ids_layer;ids_q<=ids;end
   end
   rd_q<=rd_go;rp_q<=rp;
   if(running&&!run_v)rc<=rc+24'd1;
   if(rd_go)begin rp<=rp+1'b1;n_rd<=n_rd-1'b1;end
   if(rd_q)begin
    a<=rd[199:0];a_v<=1;
    if(rd[255:240]!=16'h5d15||rd_id!=rp_q||(DAW==7&&rd[239])||rd[231:200]!=0||rd[176:173]>NID)fault<=1;
   end
   if(a_go)begin
    a_v<=0;p_v<=1;p<=a;
    p_lay<=(MUT==1)?24'd0:24'(layer_q)*24'(a[157:143]);
    p_id<=24'(a_id)*24'(a[172:158]);
   end
   // In native mode a missing/stale result cannot silently hold an expert past its fixed slot.
   if(ID_COHORT!=0&&a_v&&a_sel!=0&&!a_ids&&rc>=a[142:119])fault<=1;
   if(s_go)begin
    p_v<=0;st_v<=1;
    st<={p[142:47],s_blk[17:3],p[31:10],s_blk[2:0],p[6:0]};
    s_ent<={p[199],p[196:195],p[194:191],p[188:177],p[81:72],p[142:119],p[118:103],p[190],p[102:92],p[189],p[91:82],p[64:49],p[47+:LB]};
    if(s_blk>=26'd262144)fault<=1;
   end
   if(reserve_v)st_v<=0;
   if(push_s)begin sq[sq_w]<=s_ent;sq_w<=sq_w+2'd1;end
   if(pop_s)sq_r<=sq_r+2'd1;
   sq_n<=sq_n+(push_s?3'd1:3'd0)-(pop_s?3'd1:3'd0);
   if(push_g)begin gq[gq_w]<=sh;gq_w<=gq_w+2'd1;end
   if(pop_g)gq_r<=gq_r+2'd1;
   gq_n<=gq_n+(push_g?3'd1:3'd0)-(pop_g?3'd1:3'd0);
   if(push_s&&sq_n==QD&&!pop_s)fault<=1;
   if(pop_g)go_busy<=1;
   if(gq_n!=0&&(rc==gh_at&&(go_busy||!cache_ready[gh_land[0]])||rc>gh_at))fault<=1;   // missed slot: never waits
   if(program_done)begin
    if(!go_busy)fault<=1;
    go_busy<=0;
    if(running&&n_go==1)begin running<=0;run_done<=1;end
    n_go<=n_go-1'b1;
   end
  end
 end
endmodule
`default_nettype wire
