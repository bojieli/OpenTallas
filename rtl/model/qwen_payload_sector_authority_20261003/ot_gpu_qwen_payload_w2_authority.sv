`timescale 1ns/1ps
// SINGLE authority bound to actual selected NC6 ports. No W2/controller copy.
// The enclosing physical mux must apply req_permit to ALL six c_req_v offers,
// and capture_permit to BOTH c_rsp_rdy and c_wr_done_rdy. raw readiness / valid
// are from W2, caller readiness is from the real destination (before masking).
// bus_PC is the actual physical W2 instance currently selected by its mux.
// Reverse input is a real retained CDC offer, held until reverse_ready.
module ot_gpu_qwen_payload_w2_authority #(parameter ENABLE=0, IDENTW=207)(
 input wire clk, por_n, run_enable, local_reset,
 input wire alloc_valid, output wire alloc_ready,
 input wire [126:0] alloc_source, input wire alloc_rmw,
 input wire map_valid, map_sector_clear, input wire [33:0] map_addr,
 input wire [6:0] map_PC, input wire [2:0] map_client,
 input wire [31:0] map_tag, input wire [3:0] map_gen,
 output wire grant_live, output wire [206:0] grant_identity,
 output wire grant_rmw, output wire [2:0] grant_phase,
 input wire [6:0] bus_PC,
 input wire [5:0] caller_req_v, caller_req_we, raw_req_rdy,
 input wire [203:0] caller_req_addr,
 input wire [191:0] caller_req_tag, input wire [23:0] caller_req_gen,
 output wire [5:0] req_permit,
 input wire [5:0] raw_rsp_v, raw_wr_done_v,
 input wire [191:0] raw_rsp_tag, raw_wr_done_tag,
 input wire [23:0] raw_rsp_gen, raw_wr_done_gen,
 input wire [5:0] caller_rsp_rdy, caller_wr_done_rdy,
 output wire [5:0] capture_permit,
 input wire reverse_valid, output wire reverse_ready,
 input wire [79:0] reverse_route, input wire reverse_write,
 input wire release_valid, output wire release_ready,
 input wire [206:0] release_identity,
 output wire fault, issue_ready
);
 wire [2:0] client=grant_identity[38:36];
 wire client_ok=client<6;
 wire capture_ready;
 wire write_phase=grant_phase==5 || grant_phase==6;
 wire [206:0] issued={grant_identity[206:80],
     caller_req_addr[client*34+:34],bus_PC,client,
     caller_req_tag[client*32+:32],caller_req_gen[client*4+:4]};
 wire [206:0] captured={grant_identity[206:80],grant_identity[79:46],
     bus_PC,client,
     (write_phase ? raw_wr_done_tag[client*32+:32] : raw_rsp_tag[client*32+:32]),
     (write_phase ? raw_wr_done_gen[client*4+:4] : raw_rsp_gen[client*4+:4])};
 wire owned_issue=grant_live && client_ok && caller_req_v[client] && raw_req_rdy[client] && req_permit[client];
 wire owned_capture=grant_live && client_ok &&
     (write_phase ? raw_wr_done_v[client] && caller_wr_done_rdy[client] : raw_rsp_v[client] && caller_rsp_rdy[client]);
 wire [275:0] caller_owners;
 genvar g;
 generate for(g=0;g<6;g=g+1) begin: callers
  assign caller_owners[g*46+:46]={bus_PC,3'(g),caller_req_tag[g*32+:32],caller_req_gen[g*4+:4]};
  // Other clients' captures stay owned by their existing authority; the
  // selected payload root adds its own ready mask, not an always-ready tie.
  assign capture_permit[g]=ENABLE && por_n && run_enable && !local_reset && !fault &&
      (!grant_live || client!=g || capture_ready);
 end endgenerate
 ot_gpu_qwen_payload_sector_authority #(.ENABLE(ENABLE),.IDENTW(IDENTW)) root(
  .clk(clk),.por_n(por_n),.run_enable(run_enable),.local_reset(local_reset),
  .alloc_valid(alloc_valid),.alloc_ready(alloc_ready),.alloc_source(alloc_source),.alloc_rmw(alloc_rmw),
  .map_valid(map_valid),.map_sector_clear(map_sector_clear),.map_addr(map_addr),
  .map_PC(map_PC),.map_client(map_client),.map_tag(map_tag),.map_gen(map_gen),
  .grant_live(grant_live),.grant_identity(grant_identity),.grant_rmw(grant_rmw),.grant_phase(grant_phase),
  .guard_addr(caller_req_addr),.guard_owner(caller_owners),.guard_write(caller_req_we),.guard_permit(req_permit),
  .issue_valid(owned_issue),.issue_ready(issue_ready),.issue_identity(issued),.issue_write(caller_req_we[client]),
  .capture_valid(owned_capture),.capture_ready(capture_ready),.capture_identity(captured),.capture_write(write_phase),
  .reverse_valid(reverse_valid),.reverse_ready(reverse_ready),
  .reverse_identity({grant_identity[206:80],reverse_route}),.reverse_write(reverse_write),
  .release_valid(release_valid),.release_ready(release_ready),.release_identity(release_identity),.fault(fault)
 );
endmodule
