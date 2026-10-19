// HBM-SMB-KITS opt-in SRAM-response-FIFO composition. Original master byte-identical.
// Storage-only causal equivalence candidate; native registered boundaries/region clock integration still open.
`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx: C + C2 + P2 + 2,048-word store): the SM service group svg_<q><k>
// with the token-resident relative issuer (ot_hbm_svc_sm_issuer_rel: layer-stride + indexed-expert descriptors, go
// context) and the relocating 2,048-word programme feed (ot_hbm_svc_sm_feed_programmed_rel_id).  Strap identity as
// ot_hbm_svc_sm_group_id; FIXED_GO always (static schedule).  New ports vs ot_hbm_svc_sm_group_id: run_layer (with the run
// launch, from the host collar), ids_v / ids_layer / ids (router top-k broadcast), PAW-bit programme address, DD-row
// descriptor table (DD 256: 8-bit descriptor address / run base, 9-bit run count).
module ot_hbm_svc_sm_group_rel_sram_id #(parameter integer FIFOMUT=0,LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer NID=6,parameter integer IDW=9,parameter integer PAW=11,parameter integer PREL=1,parameter integer DD=256,parameter integer IMUT=0,
 parameter integer DAW=(DD>128)?8:7)(
 // strap identity: id_stack = HBM stack / quadrant (SW0 SE1 NW2 NE3), id_sm = SM index k (PCs 4k..4k+3)
 input wire[1:0]id_stack,input wire[2:0]id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 output wire running,run_done,program_active,fault,
 output wire[1098:0]sm_packet,output wire[82:0]sm_command,
 output wire[42:0]expected_request,output wire[1081:0]lt0,lt1,output wire[569:0]lb0,lb1,output wire[11:0]fm,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 wire reserve_v,reserve_ready,start_v,program_start_v,program_done,feed_fault,issuer_fault;
 wire[31:0]reserve_base;wire[14:0]reserve_row_base;wire[11:0]reserve_total;wire[LB-1:0]reserve_bank,start_bank;
 wire[15:0]reserve_epoch,start_epoch,program_start_loops;wire[6:0]reserve_rows;wire[9:0]reserve_tag_base;
 wire[PAW-1:0]program_start_base;wire[PAW:0]program_start_limit;wire[45:0]program_start_ctx;wire[LBANKS-1:0]block_ready;wire[1:0]cache_ready,cache_owned;
 assign fault=feed_fault||issuer_fault;
 ot_hbm_svc_sm_issuer_rel #(.LBANKS(LBANKS),.NID(NID),.IDW(IDW),.PAW(PAW),.DD(DD),.MUT(IMUT)) issuer(
  .clk(stream_clk),.rst_n(stream_rst_n),.desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data),
  .run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_layer),
  .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.running(running),.run_done(run_done),.fault(issuer_fault),
  .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),
  .reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_rows(reserve_rows),
  .reserve_tag_base(reserve_tag_base),.block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned),
  .start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),.program_start_v(program_start_v),
  .program_start_base(program_start_base),.program_start_limit(program_start_limit),.program_start_loops(program_start_loops),
  .program_start_ctx(program_start_ctx),.program_done(program_done));
 ot_hbm_svc_sm_feed_programmed_rel_sram_id #(.FIFOMUT(FIFOMUT),.LBANKS(LBANKS),.PAW(PAW),.PREL(PREL)) feed(
  .id_stack(id_stack),.id_sm(id_sm),
  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .stream_bank_clk(stream_bank_clk),.hbm_fifo_clk(hbm_fifo_clk),.hbm_pc_clk(hbm_pc_clk),
  .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),
  .reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_rows(reserve_rows),
  .reserve_tag_base(reserve_tag_base),.block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned),
  .start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .program_cfg_we(program_cfg_we),.program_cfg_addr(program_cfg_addr),.program_cfg_data(program_cfg_data),
  .program_start_v(program_start_v),.program_start_base(program_start_base),.program_start_limit(program_start_limit),
  .program_start_loops(program_start_loops),.program_start_ctx(program_start_ctx),.program_active(program_active),.program_done(program_done),.fault(feed_fault),
  .expected_request(expected_request),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm),
  .packet_observe(sm_packet),.programme_observe(),.programme_v(),.sm_command(sm_command),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
  .k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
endmodule
`default_nettype wire
