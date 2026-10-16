`timescale 1ns/1ps
// qwen-split/kvsys die lead r7 2026-10-15 (die v1.4): the die-placed HOST PC slice = the formally proven
// qkd_host_pc_slice (UNCHANGED, instantiated as u_slice) + the two die-wiring chains a 12-mm stack column needs so the
// root core does not take 128 x 4 single-bit status wires and a 128-load boot_go broadcast across the die:
//   status chain: sk/sd/so/sf [31:0] (all_ack / boot_done / boot_ok / boot_fault by LOGICAL PC bit lpc), slot 31 -> slot 0
//                 -> root (slice_ack / slice_boot_done / slice_boot_ok / slice_boot_fault [st*32 +: 32]); one register a
//                 slot: a slot-k PC's bit reaches the chain head k + 1 cycles after the slice raised it (fixed, compiler
//                 stage; distinct bit positions, so OR-merging never loses a pulse: the a/c vectors of the station chain
//                 use the same rule)
//   boot chain:   bgi -> slice boot_go, bgo = bgi registered (slot 0 -> slot 31): slot k starts boot k cycles after
//                 slot 0 (boot completion is reported per PC on the status chain, so the skew is observable, not assumed)
// Static schedule (owner 10-14): no ready / credit / backpressure added; both chains are fixed-latency pipelines.
module qkd_host_pc_slice_die #(parameter integer MUT=0)(
 input wire ck_station,ck_static,ck_boot,ck_boot_test,
 input wire host_rst_n,hbm_rst_n,
 input wire[4:0]lpc,
 input wire bgi,output reg bgo,
 input wire[290:0]fi,output wire[290:0]fo,
 input wire[31:0]ci,output wire[31:0]co,
 input wire[31:0]ai,output wire[31:0]ao,
 input wire fault_i,output wire fault_o,
 input wire[287:0]land_es,output wire[260:0]land_er,
 output wire[287:0]ctrl_es,input wire[260:0]ctrl_er,
 input wire ctrl_completion_v,ctrl_completion_we,
 input wire[31:0]ski,sdi,soi,sfi,
 output reg[31:0]sko,sdo,soo,sfo
);
 // One physical capture before the boot and related boot-test consumers.
 // Existing bgo chain stays one edge; each PC's boot starts one edge later.
 (* keep = "true" *) reg bgi_q;
 always @(posedge ck_boot or negedge hbm_rst_n)
  if(!hbm_rst_n)bgi_q<=0;else bgi_q<=bgi;
 wire all_ack,boot_done,boot_ok,boot_fault;
 qkd_host_pc_slice u_slice(.ck_station(ck_station),.ck_static(ck_static),.ck_boot(ck_boot),.ck_boot_test(ck_boot_test),
  .host_rst_n(host_rst_n),.hbm_rst_n(hbm_rst_n),.boot_go((MUT==2)?bgi:bgi_q),.lpc(lpc),.fi(fi),.fo(fo),.ci(ci),.co(co),.ai(ai),.ao(ao),
  .fault_i(fault_i),.fault_o(fault_o),.land_es(land_es),.land_er(land_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),
  .ctrl_completion_v(ctrl_completion_v),.ctrl_completion_we(ctrl_completion_we),
  .all_ack(all_ack),.boot_done(boot_done),.boot_ok(boot_ok),.boot_fault(boot_fault));
 // The physical strap belongs to ck_station at the input face. Capture it
 // before its related-clock boot status consumers; lpc is constant per PC.
 // Boot must allow one station edge for this strap capture before bgi.
 (* keep = "true" *) reg [4:0] lpc_status;
 always @(posedge ck_station) lpc_status <= lpc;
 wire[4:0]pos=(MUT==1)?lpc_status^5'd1:lpc_status;
 wire[31:0]one=32'd1<<pos;
 always @(posedge ck_station or negedge host_rst_n)
  if(!host_rst_n)sko<=0;else sko<=ski|(all_ack?one:32'd0);
 always @(posedge ck_boot or negedge hbm_rst_n)
  if(!hbm_rst_n)begin bgo<=0;sdo<=0;soo<=0;sfo<=0;end
  else begin
   bgo<=bgi;
   sdo<=sdi|(boot_done?one:32'd0);soo<=soi|(boot_ok?one:32'd0);sfo<=sfi|(boot_fault?one:32'd0);
  end
endmodule
