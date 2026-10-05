`timescale 1ps/1fs
// ONE opt-in native TP4 K tile landing. Original merge/2 SRAM macros reused.
// Context/identity must be held by enclosing issuer through matched reverse.
// Private committed-write receipt is NOT global VM/KV/HBM publication.
module ot_hbm_qwen_kv_tile_landing #(parameter integer ENABLE=0)(
 input wire service_clk,core_clk,por_n,
 input wire service_v,output wire service_r,input ot_hbm_r14_pkg::owned_t service_owned,
 input wire retained_prior_owner,input ot_hbm_r14_pkg::identity_t expected_identity,
 input wire rd_v,input wire[6:0] rd_row,output wire[511:0] rd_data,
 output wire private_committed,output wire crossing_empty,output wire fault
);
 import ot_hbm_r14_pkg::*;
 owned_t delivered;wire ov,ore,xf;wire[11:0] grant;
 wire[33:0] sec=delivered.id.sector;
 wire[17:0] word_addr={sec[16:0],1'b0};
 wire[1:0] head=word_addr[17:16];wire[8:0] tk=word_addr[15:7];
 wire[6:0] dim=word_addr[6:0];
 wire[6:0] loc=7'((tk/48)*2+head);
 wire legal=ENABLE&&retained_prior_owner&&delivered.id==expected_identity&&
 sec<34'd65536&&head<2&&tk%48==0&&dim<4&&!dim[0]&&loc<22&&
 delivered.id.stack==sec[1:0];
 reg sticky;reg[3:0] pending;
 wire land_fire=ov&&legal&&pending==0&&!sticky&&!xf&&grant[0];
 wire wce;wire[6:0] wa;wire[511:0] wd,wm;
 reg wce_q;reg[6:0] wa_q;reg[511:0] wd_q,wm_q;
 ot_hbm_accel_owned_crossing crossing(.service_clk(service_clk),.stream_clk(core_clk),.por_n(por_n),
 .iv(service_v&&ENABLE),.ir(service_r),.id(service_owned),.ov(ov),.ore(ore),.od(delivered),.fault(xf),.empty(crossing_empty));
 ot_qwen_kv_land_merge #(.NSRC(12)) merge(.clk(core_clk),.rst_n(por_n),.rr_n(7'd0),
 .s_v({11'b0,ov&&legal&&pending==0&&!sticky&&!xf}),
 .s_port(84'(7'({sec[1:0],sec[15],sec[5:2]}))),.s_loc({77'b0,loc}),
 .s_isk(12'd1),.s_ktail(12'd0),.s_sel({22'b0,dim[1:0]}),
 .s_beat({2816'b0,delivered.data}),.tail_lm(128'b0),.s_grant(grant),
 .tok_v(1'b0),.tok_loc(7'b0),.tok_data(512'b0),.tok_mask(512'b0),
 .kvw_ce(wce),.kvw_addr(wa),.kvw_data(wd),.kvw_mask(wm));
 // EXACT original tile source input registration before actual macro w_ce.
 always @(posedge core_clk or negedge por_n)if(!por_n)begin wce_q<=0;pending<=0;sticky<=0;end
 else begin
  wce_q<=ENABLE&&wce;
  if(ov&&!legal)sticky<=1;
  if(land_fire)pending<=4'b0001;
  else if(pending!=0&&!pending[3])pending<=pending<<1;
  if(ore)pending<=0;
 end
 always @(posedge core_clk)begin wa_q<=wa;wd_q<=wd;wm_q<=wm;end
 for(genvar p=0;p<2;p=p+1)begin:column
 ot_sram_1r1w_128x256_m1_r2c2 ram(.clk(core_clk),.r_ce_in(rd_v&&ENABLE),.r_addr_in(rd_row),
 .rd_out(rd_data[p*256+:256]),.w_ce_in(wce_q),.w_addr_in(wa_q),.wd_in(wd_q[p*256+:256]),
 .w_mask_in(wm_q[p*256+:256]),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 // land E0 -> merge outputE1 -> writerregE2 -> SRAM writeE3;
 // pending[3] only after E3; source remains held through crossing reverse.
 assign private_committed=ov&&pending[3]&&legal&&!sticky&&!xf;
 assign ore=private_committed;
 assign fault=sticky||xf;
endmodule
