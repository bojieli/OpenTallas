`timescale 1ns/1ps
// Structural full four-quarter binding. Arithmetic wrapper source822ca7b65;
// control sourcec17b6a4b0. No SM/VM/HBM endpoint is replaced by a zero response.
module ot_qwen_r25_su_four_quarter #(
 parameter integer ENABLE=0,CAPACITY=8224,OWNER_W=74
)(
 input wire clk,rst_n,warm_abort,
 input wire launch_v,output wire launch_rdy,input wire [1:0] launch_checked,
 input wire [OWNER_W-1:0] launch_owner,input wire [11:0] launch_pc,
 input wire [12:0] launch_count,input wire [19:0] launch_position,input wire [2:0] launch_queries,
 output wire rom_v,input wire rom_rdy,output wire [11:0] rom_pc,
 input wire rom_out_v,output wire rom_out_rdy,input wire [11:0] rom_out_pc,
 input wire [2759:0] rom_words,input wire [3:0] rom_quarters,
 input wire rom_valid,rom_window,input wire [19:0] rom_row0,input wire [15:0] rom_rows,
 output wire [3:0] req_v,input wire [3:0] req_rdy,output wire [1347:0] req,
 input wire [3:0] rsp_v,output wire [3:0] rsp_rdy,input wire [1091:0] rsp,
 output wire query_finished_v,input wire query_finished_rdy,
 input wire [1:0] query_release_checked,input wire [OWNER_W-1:0] query_release_owner,
 input wire [1:0] query_release_query,
 output wire [OWNER_W-1:0] query_finished_owner,output wire [1:0] query_finished_query,
 output wire finished_v,input wire finished_rdy,output wire fault,
 output wire [127:0] virtual_edges,reads,writes,visibility_reads
);
 wire [3:0] cmd_v,cmd_rdy,done_v,qfault;
 wire [2759:0] cmd_words;wire [OWNER_W-1:0] cmd_owner;wire [11:0] cmd_pc;
 wire [1:0] cmd_query;wire [19:0] cmd_position;wire [20:0] cmd_valid_length;
 wire [4*OWNER_W-1:0] done_owner;wire [47:0] done_pc;wire [7:0] done_query;
 wire dispatcher_fault,dispatcher_rdy,dispatcher_finished,dispatcher_query_finished;
 assign query_finished_v=dispatcher_query_finished&&!fault&&!warm_abort;
 assign fault=dispatcher_fault||(|qfault);
 assign launch_rdy=dispatcher_rdy&&!fault&&!warm_abort;
 assign finished_v=dispatcher_finished&&!fault&&!warm_abort;
 ot_qwen_r25_su_dispatch #(.ENABLE(ENABLE),.CAPACITY(CAPACITY),.OWNER_W(OWNER_W),.QUERY_RELEASE(1)) u_dispatch(
  .clk(clk),.rst_n(rst_n),.launch_v(launch_v&&!fault&&!warm_abort),.launch_rdy(dispatcher_rdy),
  .launch_checked(launch_checked),.launch_owner(launch_owner),.launch_pc(launch_pc),
  .launch_count(launch_count),.launch_position(launch_position),.launch_queries(launch_queries),
  .rom_v(rom_v),.rom_rdy(rom_rdy),.rom_pc(rom_pc),.rom_out_v(rom_out_v),
  .rom_out_rdy(rom_out_rdy),.rom_out_pc(rom_out_pc),.rom_words(rom_words),
  .rom_quarters(rom_quarters),.rom_valid(rom_valid),.rom_window(rom_window),
  .rom_row0(rom_row0),.rom_rows(rom_rows),.cmd_v(cmd_v),.cmd_rdy(cmd_rdy),
  .cmd_words(cmd_words),.cmd_owner(cmd_owner),.cmd_pc(cmd_pc),.cmd_query(cmd_query),
  .cmd_position(cmd_position),.cmd_valid_length(cmd_valid_length),
  .done_v(done_v),.done_owner(done_owner),.done_pc(done_pc),.done_query(done_query),
  .query_finished_v(dispatcher_query_finished),.query_finished_rdy(query_finished_rdy&&!fault&&!warm_abort),
  .query_release_checked(query_release_checked),.query_release_owner(query_release_owner),
  .query_release_query(query_release_query),
  .query_finished_owner(query_finished_owner),.query_finished_query(query_finished_query),
  .finished_v(dispatcher_finished),.finished_rdy(finished_rdy&&!fault&&!warm_abort),.fault(dispatcher_fault));
 for(genvar q=0;q<4;q=q+1)begin:quarters
  ot_qwen_r25_su_quarter #(.ENABLE(ENABLE),.N(256),.M(64),.QID(q),.OWNER_W(OWNER_W)) u_quarter(
   .clk(clk),.rst_n(rst_n),.warm_abort(warm_abort||fault),
   .cmd_v(cmd_v[q]&&!fault),.cmd_rdy(cmd_rdy[q]),.cmd_word(cmd_words[q*690+:690]),
   .cmd_owner(cmd_owner),.cmd_pc(cmd_pc),.cmd_query(cmd_query),
   .done_v(done_v[q]),.done_owner(done_owner[q*OWNER_W+:OWNER_W]),
   .done_pc(done_pc[q*12+:12]),.done_query(done_query[q*2+:2]),
   .req_v(req_v[q]),.req_rdy(req_rdy[q]),.req(req[q*337+:337]),
   .rsp_v(rsp_v[q]),.rsp_rdy(rsp_rdy[q]),.rsp(rsp[q*273+:273]),.fault(qfault[q]),
   .virtual_edges(virtual_edges[q*32+:32]),.reads(reads[q*32+:32]),
   .writes(writes[q*32+:32]),.visibility_reads(visibility_reads[q*32+:32]));
 end
endmodule
