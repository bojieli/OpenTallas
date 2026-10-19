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
// Q-KVFIX 0130 (2026-10-17, owner 10-16 mandatory native audit + regional synchronous resets), PINCAP=1 (default):
// every input pin lands on its own flop at the face (no logic, no second load):
//   host_rst_n / hbm_rst_n: one synchronous capture flop each (ck_station / ck_boot) drives the slice's resets
//     (+1 edge on reset assertion and release; the die's regional reset tree already releases by compiled edge);
//   ctrl_er[260:0], ctrl_completion_v/we: captured on ck_boot (+1 edge on the controller -> landing response / credit
//     return and on the completion observer; both sit on the elastic HBM-controller boundary, owner 10-14);
//   ski / sdi / soi / sfi: captured at the N face (status chain 2 edges a slot: slot k's bit reaches the head 2k + 1
//     edges after the slice raised it, was k + 1; status/boot reporting only);
//   bgi: bgi_q is the only load; bgo = bgi_q registered (boot chain 2 edges a slot: slot k boots 2k + 1 edges after
//     slot-0 bgi, was k + 1).
// ctrl_es[0] / [286] pin flops drive only their pins (in-tile observers use launch_v / launch_we copies, 0 edges).
// KVE-2 es1 (2026-10-17, native launch 241.7 ps on ctrl_es[0], pc1 route classified): synthesis folded the launch_v copy
// into the ctrl_es[0] flop (same D; a keep on the reg does not stop opt_merge), so that pin flop drove 20 in-tile loads
// (BUFx3 fanout 20 -> INV -> wire buffer -> pin, 184 ps flop->pin).  ESPIN=1 (default): a dedicated pin register stage
// on all 288 ctrl_es bits (unique D = the slice's internal ctrl_es register, Q -> pin only): +1 ck_boot edge on the
// command path to the HBM controller (the elastic off-die HBM boundary, owner 10-14; priced as +1 cycle of HBM command
// latency, no throughput change; the completion observer still sees launch_v at the internal edge, the controller's
// response is consequently one edge later on the elastic return).  ESPIN=0 = pc1 (history).  MUT=4 bypasses the stage.
// MUT=3 drops the ctrl_er pin capture (bench mutant).  PINCAP=0 = the pre-0130 wrapper (history; not die-bindable).
// KV-FIX3 es2 (2026-10-17, es1 qkd_hslice / qkd_hslice_dn EARLY_FAIL_HOLD FF -110 ps, repair stalled): ONE clock entry ck.
// The die drives ck_station / ck_static / ck_boot / ck_boot_test from the SAME die net clk_core_<stack> (kv_die.py), but
// as four tile pins = four CTS roots, so every internal cross-root hop (boot->static ctrl_er -> u_static.er, static<->core,
// static->boot, test->boot: 5,695 hold endpoints) paid the 100 ps die-skew hold reserve (pc1 closed only after ~15k hold
// buffers).  One regional root (6,999 sinks < 15k) makes those hops ordinary same-tree paths; the neighbour skew budget
// stays where it belongs, at the registered face pins (PINCAP captures / ESPIN launches) against the die's neighbours.
// Inner modules keep their own clock names, all driven by ck: same cycles, bit-identical (benches already drove one ck).
module qkd_host_pc_slice_die #(parameter integer MUT=0,parameter integer PINCAP=1,parameter integer ESPIN=1)(
 input wire ck,
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
 wire ck_station=ck, ck_static=ck, ck_boot=ck, ck_boot_test=ck;   // one root (KV-FIX3 es2)
 // ---- pin captures (PINCAP) ----
 (* keep = "true" *) reg host_rn,hbm_rn;
 always @(posedge ck_station) host_rn<=host_rst_n;
 always @(posedge ck_boot) hbm_rn<=hbm_rst_n;
 (* keep = "true" *) reg[260:0]ctrl_er_q;
 (* keep = "true" *) reg cmp_v_q,cmp_we_q;
 always @(posedge ck_boot)begin ctrl_er_q<=ctrl_er;cmp_v_q<=ctrl_completion_v;cmp_we_q<=ctrl_completion_we;end
 (* keep = "true" *) reg[31:0]ski_q;
 (* keep = "true" *) reg[31:0]sdi_q,soi_q,sfi_q;
 always @(posedge ck_station) ski_q<=ski;
 always @(posedge ck_boot)begin sdi_q<=sdi;soi_q<=soi;sfi_q<=sfi;end
 wire host_r=PINCAP?host_rn:host_rst_n, hbm_r=PINCAP?hbm_rn:hbm_rst_n;
 wire[260:0]er_s=(PINCAP&&MUT!=3)?ctrl_er_q:ctrl_er;
 wire cv_s=PINCAP?cmp_v_q:ctrl_completion_v, cw_s=PINCAP?cmp_we_q:ctrl_completion_we;
 wire[31:0]ski_s=PINCAP?ski_q:ski, sdi_s=PINCAP?sdi_q:sdi, soi_s=PINCAP?soi_q:soi, sfi_s=PINCAP?sfi_q:sfi;
 // One physical capture before the boot and related boot-test consumers.
 (* keep = "true" *) reg bgi_q;
 always @(posedge ck_boot or negedge hbm_r)
  if(!hbm_r)bgi_q<=0;else bgi_q<=bgi;
 wire all_ack,boot_done,boot_ok,boot_fault;
 wire[287:0]es_i;
 (* keep = "true" *) reg[287:0]es_pin;
 always @(posedge ck_boot or negedge hbm_r)
  if(!hbm_r)es_pin<=288'b0;else es_pin<=es_i;
 assign ctrl_es=(ESPIN&&MUT!=4)?es_pin:es_i;
 qkd_host_pc_slice u_slice(.ck_station(ck_station),.ck_static(ck_static),.ck_boot(ck_boot),.ck_boot_test(ck_boot_test),
  .host_rst_n(host_r),.hbm_rst_n(hbm_r),.boot_go((MUT==2)?bgi:bgi_q),.lpc(lpc),.fi(fi),.fo(fo),.ci(ci),.co(co),.ai(ai),.ao(ao),
  .fault_i(fault_i),.fault_o(fault_o),.land_es(land_es),.land_er(land_er),.ctrl_es(es_i),.ctrl_er(er_s),
  .ctrl_completion_v(cv_s),.ctrl_completion_we(cw_s),
  .all_ack(all_ack),.boot_done(boot_done),.boot_ok(boot_ok),.boot_fault(boot_fault));
 // The physical strap belongs to ck_station at the input face. Capture it
 // before its related-clock boot status consumers; lpc is constant per PC.
 // Boot must allow one station edge for this strap capture before bgi.
 (* keep = "true" *) reg [4:0] lpc_status;
 always @(posedge ck_station) lpc_status <= lpc;
 wire[4:0]pos=(MUT==1)?lpc_status^5'd1:lpc_status;
 wire[31:0]one=32'd1<<pos;
 always @(posedge ck_station or negedge host_r)
  if(!host_r)sko<=0;else sko<=ski_s|(all_ack?one:32'd0);
 always @(posedge ck_boot or negedge hbm_r)
  if(!hbm_r)begin bgo<=0;sdo<=0;soo<=0;sfo<=0;end
  else begin
   bgo<=PINCAP?bgi_q:bgi;
   sdo<=sdi_s|(boot_done?one:32'd0);soo<=soi_s|(boot_ok?one:32'd0);sfo<=sfi_s|(boot_fault?one:32'd0);
  end
endmodule
