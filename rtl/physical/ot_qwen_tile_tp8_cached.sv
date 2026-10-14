`timescale 1ns/1ps
// Candidate composition only. All 26 core/cache roots must pause coherently
// across the full field on any miss; load_clk remains active. Clocks supplied
// here already carry the die phi-minus-insertion schedule. No local clock gate
// or combinational clock enable is implemented by this wires-only parent.
// load_epoch/load_x must belong to the current instruction context and actual
// requested address. clear/drain and registered global admission remain external
// obligations, not properties established by the local cache/core seam proof.
module ot_qwen_tile_tp8_cached (
 input wire clk_ctl,input wire [4:0] clk_rp,input wire [7:0] clk_sl,
 input wire clk_node,input wire [7:0] clk_tx,input wire [1:0] clk_rqr,
 input wire clk_cache,input wire load_clk,input wire rst_n,
 input wire [15:0] tile_id,input wire ib_go,input wire [378:0] ib,
 input wire clear,input wire j_repeat,input wire load_v,
 input wire [20:0] load_epoch,input wire [127:0] load_x,
 input wire [511:0] n_a,input wire [511:0] n_b,input wire n_va,
 output wire [511:0] n_y,output wire n_vy,
 output wire [511:0] t_out,output wire t_vout,
 output wire core_fault,output wire cache_fault,output wire cache_hit,
 output wire [3:0] x_re,output wire [95:0] x_addr,output wire [20:0] x_epoch
);
 wire [127:0] x_response;
 ot_qwen_rom_tile_nkt_tp8_core u_core (
  .clk_ctl(clk_ctl),.clk_rp(clk_rp),.clk_sl(clk_sl),.clk_node(clk_node),
  .clk_tx(clk_tx),.clk_rqr(clk_rqr),.rst_n(rst_n),.tile_id(tile_id),
  .ib_go(ib_go),.ib(ib),.x_response(x_response),
  .n_a(n_a),.n_b(n_b),.n_va(n_va),.n_y(n_y),.n_vy(n_vy),
  .t_out(t_out),.t_vout(t_vout),.fault(core_fault),
  .cx_xre(x_re),.cx_xaddr(x_addr),.cx_xepoch(x_epoch));
 ot_qwen_xcache_indexed u_cache (
  .load_clk(load_clk),.core_clk(clk_cache),.rst_n(rst_n),.clear(clear),
  .j_repeat(j_repeat),.load_v(load_v),.load_epoch(load_epoch),.load_x(load_x),
  .read_v(x_re),.read_epoch(x_epoch),.hit(cache_hit),.q_x(x_response),
  .fault(cache_fault));
endmodule
