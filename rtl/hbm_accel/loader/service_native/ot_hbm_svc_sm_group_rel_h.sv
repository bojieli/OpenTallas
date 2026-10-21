`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARD VIEW master of the SM service group svg_<q><k> (16 per die) = ot_hbm_svc_sm_group_rel_id
// at the GEN2e4 r11 die parameters #(LBANKS 4, NID 6, IDW 9, PAW 11, PREL 1, DD 256, ID_COHORT 1) with the HBM-QINT8
// INT8 S1 view (main 1cf52fbac / ea77ab477, the d98271674 evidence) and XSLOT 0 / OPEN_IL 0 (rate options deferred).
// ot_hbm_svc_sm_group_rel_id stays byte-identical (r11 is bound to it).  Port changes vs rel_id (die GEN, HBM-DIE12):
//   removed  stream_bank_clk[1:0], hbm_fifo_clk[1:0], hbm_pc_clk[3:0]: the die ties them to the same PLL nets as
//            stream_clk / hbm_clk; the tile is one local tree per family (crossings = the reviewed Gray FIFOs only);
//   removed  expected_request, lt0, lt1, lb0, lb1, fm: OPEN outputs in the r11 die (contract_pre open_outputs);
//   removed  k_we, k_wdata, k_wstrb (constant 0: the service is read-only) and k_wr_done (fault input only): no tied
//            functional ports.  The die's vmks g_k_we / g_k_wdata / g_k_wstrb inputs lose their svg driver (vmks
//            element: tie-free removal of its g write path, or a die-level 0 -- HBM-DIE12 / vmks owner decision).
// Everything else is cycle-identical at the SM ports (sm_packet, sm_command, running, run_done, program_active, fault
// up to the HBM-side latencies listed in the kit README: +1 hbm edge per K direction (pin skids), +1 hbm edge
// descriptor -> first command, +1 stream edge landing -> resident; reset release +4 stream / hbm edges).
// Reset: each port lands in an ot_rst_relay (2 sync + 1 KEPT relay stage); the producer families take the AND of both
// ports (as the original's reset_both), the issuer / programme / feed / cache take stream_rst_n only (as the original).
module ot_hbm_svc_sm_group_rel_h #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer NID=6,parameter integer IDW=9,parameter integer PAW=11,parameter integer PREL=1,parameter integer DD=256,parameter integer IMUT=0,
 parameter integer DAW=(DD>128)?8:7,parameter integer ID_COHORT=0)(
 input wire[1:0]id_stack,input wire[2:0]id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output wire running,run_done,program_active,fault,
 output wire[1098:0]sm_packet,output wire[82:0]sm_command,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 initial if(LBANKS!=4||PREL!=1||PAW!=11||DD!=256)$fatal(1,"sm_group_rel_h: the r11 hard view parameters only");
 // ---------------- reset landing (port loads: stream_rst_n 2+9+1, hbm_rst_n 1; AND output 2+12 + 2+15)
 wire[8:0]st;wire[11:0]sr;wire[14:0]hr;
 ot_rst_relay #(.REGIONS(9),.SYNC_STAGES(2),.TREE_STAGES(1)) u_st(.clk(stream_clk),.rst_n_in(stream_rst_n),.rst_n(st));
 wire both_rst_n=stream_rst_n&&hbm_rst_n;
 ot_rst_relay #(.REGIONS(12),.SYNC_STAGES(2),.TREE_STAGES(1)) u_sr(.clk(stream_clk),.rst_n_in(both_rst_n),.rst_n(sr));
 ot_rst_relay #(.REGIONS(15),.SYNC_STAGES(2),.TREE_STAGES(1)) u_hr(.clk(hbm_clk),.rst_n_in(both_rst_n),.rst_n(hr));
 // st[0..4] issuer, st[5] feed control, st[6..7] programme leaf, st[8] cache
 wire reserve_v,reserve_ready,start_v,program_start_v,program_done,feed_fault,issuer_fault;
 wire[31:0]reserve_base;wire[14:0]reserve_row_base;wire[11:0]reserve_total;wire[LB-1:0]reserve_bank,start_bank;
 wire[15:0]reserve_epoch,start_epoch,program_start_loops;wire[6:0]reserve_rows;wire[9:0]reserve_tag_base;
 wire[PAW-1:0]program_start_base;wire[PAW:0]program_start_limit;wire[45:0]program_start_ctx;wire[LBANKS-1:0]block_ready;wire[1:0]cache_ready,cache_owned;
 assign fault=feed_fault||issuer_fault;
 ot_hbm_svc_sm_issuer_rel_h #(.LBANKS(LBANKS),.NID(NID),.IDW(IDW),.PAW(PAW),.DD(DD),.MUT(IMUT),.ID_COHORT(ID_COHORT)) issuer(
  .clk(stream_clk),.rst_n(st[4:0]),.desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data),
  .run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_layer),
  .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort),.running(running),.run_done(run_done),.fault(issuer_fault),
  .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),
  .reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_rows(reserve_rows),
  .reserve_tag_base(reserve_tag_base),.block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned),
  .start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),.program_start_v(program_start_v),
  .program_start_base(program_start_base),.program_start_limit(program_start_limit),.program_start_loops(program_start_loops),
  .program_start_ctx(program_start_ctx),.program_done(program_done));
 ot_hbm_svc_sm_feed_rel_h #(.LBANKS(LBANKS),.PAW(PAW)) feed(
  .id_stack(id_stack),.id_sm(id_sm),.stream_clk(stream_clk),.hbm_clk(hbm_clk),
  .st_rst(st[8:5]),.s_rst(sr),.h_rst(hr),
  .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),
  .reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_rows(reserve_rows),
  .reserve_tag_base(reserve_tag_base),.block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned),
  .start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .program_cfg_we(program_cfg_we),.program_cfg_addr(program_cfg_addr),.program_cfg_data(program_cfg_data),
  .program_start_v(program_start_v),.program_start_base(program_start_base),.program_start_limit(program_start_limit),
  .program_start_loops(program_start_loops),.program_start_ctx(program_start_ctx),.program_active(program_active),.program_done(program_done),.fault(feed_fault),
  .packet_observe(sm_packet),.sm_command(sm_command),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),
  .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
endmodule
`default_nettype wire
