`timescale 1ps/1fs
// ONE source-selected tile0 / two physical columns. Full array, allocator,
// publication/reader leases and source issuer remain enclosing hardware hooks.
// ENABLE=0 routes the original tile to its original external ROM pins.
module ot_qwen_hbm_code_tile_pair_parent #(
 parameter integer ENABLE=0,NSEG=8,CW=32,MEM_EXTRA=1,KV_LOCAL=0
)(
 input wire service_clk,core_clk,por_n,
 input wire service_v,output wire service_r,input ot_hbm_r14_pkg::owned_t service_owned,
 input wire installed,published,source_span_retained,
 input wire[1:0] span_stack,input wire[33:0] first_sector,
 input wire[13:0] span_rows,input wire[12:0] first_row,
 input wire[63:0] operation,input wire[31:0] phase,input wire[6:0] rank,
 input wire hardware_owner_valid,input ot_hbm_r14_pkg::identity_t expected_identity,
 input wire[NSEG*24-1:0] seg_base,seg_len,input wire[NSEG*CW-1:0] seg_sidx,
 input wire[NSEG*2-1:0] seg_kind,input wire[2:0] installed_segment,
 input wire[23:0] installed_base,installed_length,input wire[CW-1:0] installed_sidx,
 input wire[1:0] installed_kind,
 input wire ib_go,input wire[378:0] ib,input wire[127:0] xl,
 input wire[511:0] n_a,n_b,input wire n_va,
 output wire[511:0] t_out,n_y,output wire t_vout,n_vy,
 output wire[4:0] rom_ce,output wire[11:0] rom_addr,input wire[2659:0] legacy_rom_rd,
 output wire kvs_r_ce,output wire[6:0] kvs_r_addr,input wire[511:0] kvs_rd,
 output wire kv_re,output wire[95:0] kv_addr,input wire[2047:0] kv_q,
 output wire fault,output wire crossing_empty,output wire read_pipe_empty
);
 wire request,ready,jfault,tfault;wire[23:0] virtual_address;
 wire[1:0] accepted,raw_valid,response;wire[2659:0] protected_rom;
 // A complete retained span is an explicit hardware admission condition.
 // The child's issuer-vs-accepted guard detects a late revoke/refusal.
 wire admitted=installed&&published&&source_span_retained;
 ot_hbm_qwen_code_pair_join #(.ENABLE(ENABLE),.NSEG(NSEG),.CW(CW),.READ_ALIGN(2)) storage(
 .service_clk(service_clk),.core_clk(core_clk),.por_n(por_n),.service_v(service_v),.service_r(service_r),
 .service_owned(service_owned),.installed(installed),.span_stack(span_stack),.first_sector(first_sector),
 .span_rows(span_rows),.first_row(first_row),.operation(operation),.phase(phase),.rank(rank),
 .hardware_owner_valid(hardware_owner_valid),.expected_identity(expected_identity),
 .seg_base(seg_base),.seg_len(seg_len),.seg_sidx(seg_sidx),.seg_kind(seg_kind),.installed_segment(installed_segment),
 .installed_base(installed_base),.installed_length(installed_length),.installed_sidx(installed_sidx),
 .installed_kind(installed_kind),.published(published),.read_v(request),.virtual_address(virtual_address),
 .read_accepted(accepted),.read_ready(ready),.read_response_valid(raw_valid),.read_data(),.read_bank(),
 .consumer_enable(1'b1),.response_ready(2'b11),.rom_rd(protected_rom),.tile_response_valid(response),
 .fault(jfault),.crossing_empty(crossing_empty));
 ot_qwen_hbm_code_tile_logic_w12 #(.ENABLE(ENABLE),.GT(6144),.TG(4),.SMIN(7),.CODE_BANKS(5),
 .MEM_EXTRA(MEM_EXTRA),.KV_LOCAL(KV_LOCAL)) tile(
 .clk(core_clk),.rst_n(por_n),.tile_id(16'd0),.ib_go(ib_go),.ib(ib),.xl(xl),
 .t_out(t_out),.t_vout(t_vout),.n_a(n_a),.n_b(n_b),.n_va(n_va),.n_y(n_y),.n_vy(n_vy),.fault(tfault),
 .rom_ce(rom_ce),.rom_addr(rom_addr),.rom_rd(ENABLE?protected_rom:legacy_rom_rd),
 .kvs_r_ce(kvs_r_ce),.kvs_r_addr(kvs_r_addr),.kvs_rd(kvs_rd),.kv_re(kv_re),.kv_addr(kv_addr),.kv_q(kv_q),
 .code_span_retained(admitted),.code_storage_fault(jfault),.code_read_accepted(accepted),
 .code_response_valid(response),.code_read_request(request),.code_virtual_address(virtual_address));
 // Drain every issued read, including the fixed response tail. This is only
 // read-pipeline emptiness: never destination lease release or fabric fence.
 reg[1:0] read_tail;
 always @(posedge core_clk or negedge por_n)
  if(!por_n)read_tail<=0;else read_tail<={read_tail[0],request};
 assign read_pipe_empty=!request&&read_tail==0&&raw_valid==0&&response==0;
 assign fault=jfault||tfault;
endmodule
