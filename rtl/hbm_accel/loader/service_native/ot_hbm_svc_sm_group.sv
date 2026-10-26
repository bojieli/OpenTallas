`timescale 1ns/1ps
`default_nettype none
// H-DIE 2026-10-15: one SM's HBM service group = the die master svg_<q><k>: the actual SM-specific four-PC service
// feed (ot_hbm_svc_sm_feed_programmed: four-PC producer, eight landing + five cache SRAMs, programme calendar) driven by
// the actual issuer (ot_hbm_svc_sm_issuer).  Its only non-clock inputs are initialization (programme + descriptor
// tables, from the host loader), one run launch, and the four K ports of its own controllers.  It drives the SM's
// packet and command.  The observation outputs of the feed's S1 consumer copy are kept for benches.
// FIXED_GO=1: programme go on the descriptor's compiler slot (ot_hbm_svc_sm_issuer), so sm_packet is on the die calendar
// (required when the packet also feeds hb_idx.key_lines: the eight groups of a stack must be cycle-aligned).
module ot_hbm_svc_sm_group #(parameter[1:0]STACK=0,parameter integer SM=0,LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer FIXED_GO=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire program_cfg_we,input wire[9:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[6:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[6:0]run_base,input wire[7:0]run_count,
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
 wire[15:0]reserve_epoch,start_epoch,program_start_loops;wire[6:0]reserve_rows;wire[9:0]reserve_tag_base,program_start_base;
 wire[10:0]program_start_limit;wire[LBANKS-1:0]block_ready;wire[1:0]cache_ready,cache_owned;
 assign fault=feed_fault||issuer_fault;
 ot_hbm_svc_sm_issuer #(.LBANKS(LBANKS),.FIXED_GO(FIXED_GO)) issuer(
  .clk(stream_clk),.rst_n(stream_rst_n),.desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data),
  .run_v(run_v),.run_base(run_base),.run_count(run_count),.running(running),.run_done(run_done),.fault(issuer_fault),
  .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),
  .reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_rows(reserve_rows),
  .reserve_tag_base(reserve_tag_base),.block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned),
  .start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),.program_start_v(program_start_v),
  .program_start_base(program_start_base),.program_start_limit(program_start_limit),.program_start_loops(program_start_loops),
  .program_done(program_done));
 ot_hbm_svc_sm_feed_programmed #(.STACK(STACK),.SM(SM),.LBANKS(LBANKS)) feed(
  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .stream_bank_clk(stream_bank_clk),.hbm_fifo_clk(hbm_fifo_clk),.hbm_pc_clk(hbm_pc_clk),
  .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),
  .reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_rows(reserve_rows),
  .reserve_tag_base(reserve_tag_base),.block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned),
  .start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .program_cfg_we(program_cfg_we),.program_cfg_addr(program_cfg_addr),.program_cfg_data(program_cfg_data),
  .program_start_v(program_start_v),.program_start_base(program_start_base),.program_start_limit(program_start_limit),
  .program_start_loops(program_start_loops),.program_active(program_active),.program_done(program_done),.fault(feed_fault),
  .expected_request(expected_request),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm),
  .packet_observe(sm_packet),.programme_observe(),.programme_v(),.sm_command(sm_command),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
  .k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
endmodule
`default_nettype wire
