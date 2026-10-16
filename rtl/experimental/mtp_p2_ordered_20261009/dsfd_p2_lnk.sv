`timescale 1ns/1ps
`default_nettype none
// MD-2 P2 draft-die links over the die's relay stations (mtp-fixlat-1011, 2026-10-10).
//
// The P2 selected-path core ot_mtp_p2_prefix_path (rb4: REGB 1, ROOTPIPE 1) speaks plain valid / ready on every
// boundary (lane pin FIFOs ot_sc_pfifo S 2, registered start_r, single-flight output station).  On draft die A its
// buses cross registered relay stations (generator P2_BUSES: collective <-> p2, vm <-> p2), so a sender sees ready
// R stages late and the receiver sees valid F stages late: a ready that drops while F + R flits are in flight loses
// flits (lane / start) and an output handshake judged on a stale out_r drops or duplicates the result row
// (ds-1010 lat-audit: "P2 in_r ready over stages: AT RISK, draft die").
//
// Fix: every P2 die-bus channel runs the MTP grant protocol (rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_{pair,rtt}.sv).
// The receiving end is ot_dsrom_mtp_lrx_rtt sized to the stationed round trip (history F + R + 3, depth F + R + 4:
// full rate), the sending end ot_dsrom_mtp_ltx (one flit per grant seen: correct over any relay count).  The core is
// unchanged; dsfd_p2_lnk sits at its pins (same slab, abutting, no stations) and the partner ends are
// dsfd_coll_p2_ep (collective slab) / dsfd_vm_p2_ep (VM slab).  Die-bus widths are unchanged: each former ready bit
// is now the grant bit on the same reverse bus.
//   channel   data direction        F (data stages)   R (grant stages)
//   lane 0    vm -> p2              FWD_V             RET_V
//   lane 1    collective -> p2      FWD_C             RET_C
//   start     collective -> p2      FWD_C             RET_C
//   out row   p2 -> collective      RET_C             FWD_C      (receiver in dsfd_coll_p2_ep)
//   abort / done / fault / corrected: unhandshaked level / pulse wires, a relay only delays them.
// Defaults = draft A's pin-to-pin stages (tools/s81/hub_stage_count.py on s81_dies_recipe draftA, main e707ff5b3):
//   vm -> p2 12, p2 -> vm 14, collective -> p2 8, p2 -> collective 9.
// Lane flit {identity74, expert9, shared1, last1, word7, data512} = 604; start {identity74, ids27} = 101;
// out row {data512, identity74, word7, last1} = 594 (the core's own pin-FIFO packing).
// Transaction gate: the core latches the start identity and FAULTS on a lane word of another identity (transport
// identity check), so a word of transaction t+1 must not reach it before start t+1 fires.  Over stations no sender can
// know when that is (the VM's lane 0 never sees the start at all), so the lane ends present a word to the core only
// while its identity equals the identity of the last start the core accepted; later words wait in the credited
// receiver; the gate lives in each lane's ot_dsrom_mtp_pp2 port stage as a registered per-slot match flag.
// Boundary timing: stationed receivers SEL 1 + OUTPUT_PIPE 1, then ot_dsrom_mtp_pp2 at every core input port (port
// valid / data from flops via one 2:1 mux, the core's ready steers 3 flops); the result row leaves via ltx_rc.
// Core boundary (idle-sweep-1010, fixlat-p2lnk-ffbec0c86-tc TT -280 / SS -594: c_in_v[1] = lv & open_ was a 74-bit
// identity compare + OR tree straight to the port (-248), and c_in_r / c_start_r reached the 604 / 101-b OUTPUT_PIPE
// data enables of the receivers (-246, 1,613 D pins)): every core-facing channel now crosses an abutting grant pair
// ot_dsrom_mtp_ltx_rc -> ot_dsrom_mtp_lrx (D 4, SEL 1, no stations: the closed 3-cycle history is exact, full rate),
// as dsfd_coll_p2_ep does since 5b059065b.  c_*_v is an OR of flops, c_*_d a 4-slot one-hot read of registered slots,
// and c_*_r only selects the pair's dozen state flops, never a data register.  The gate now sits between the stationed
// receiver and the pair (internal reg -> reg), and cur_id follows the core's accepted start one cycle late through a
// registered take (c_start_v & c_start_r -> 1 flop; the identity is held in the pair's head slot until popped, so it
// is captured unconditionally the same cycle): opening a cycle later is always safe.  The result row leaves through
// ot_dsrom_mtp_ltx_rc (c_out_r from one flop, same function as ltx).  Cost: +2 cycles per lane word / start
// (pipelined, full rate), +1 cycle on the gate opening per transaction.
// OT_FIXLAT_MUT_LAT1 (negative control): every receiver here assumes a latency-1 link (0 hops, the legacy
// 3-cycle grant history) at the same depth -> must overflow on the stationed bench.
// OT_FIXLAT_MUT_NOGATE (negative control): no transaction gate -> back-to-back transactions fault the core.
module dsfd_p2_lnk #(parameter integer FWD_V = 12, parameter integer RET_V = 14,
                     parameter integer FWD_C = 8, parameter integer RET_C = 9,
                     parameter integer D_V = FWD_V + RET_V + 4, parameter integer D_C = FWD_C + RET_C + 4) (
 input wire [0:0] ck, rst,                                               // die stream clock, async active-low reset
 // die side
 input wire [0:0] f_l0v, input wire [603:0] f_l0d, output wire [0:0] t_l0g,          // vm -> p2 lane 0
 input wire [0:0] f_l1v, input wire [603:0] f_l1d, output wire [0:0] t_l1g,          // collective -> p2 lane 1
 input wire [0:0] f_sv,  input wire [100:0] f_sd,  output wire [0:0] t_sg,           // collective -> p2 start
 output wire [0:0] t_ov, output wire [593:0] t_od, input wire [0:0] f_og,            // p2 -> collective result row
 // core side (ot_mtp_p2_prefix_path pins)
 output wire [1:0] c_in_v, input wire [1:0] c_in_r, output wire [1207:0] c_in_d,   // {lane1 604, lane0 604}
 output wire [0:0] c_start_v, input wire [0:0] c_start_r, output wire [100:0] c_start_d,
 input wire [0:0] c_out_v, output wire [0:0] c_out_r, input wire [593:0] c_out_d
);
`ifdef OT_FIXLAT_MUT_LAT1
 localparam integer VF = 0, VR = 0, CF = 0, CR = 0;
`else
 localparam integer VF = FWD_V, VR = RET_V, CF = FWD_C, CR = RET_C;
`endif
 wire clk = ck[0];
 wire rst_n;
 ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rst_n));
 wire [1:0] lv, lr;
 wire [1207:0] ld;                                                       // stationed receivers' registered heads
 ot_dsrom_mtp_lrx_rtt #(.W(604),.D(D_V),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(VF),.RETURN_HOPS(VR)) u_l0(.clk(clk),.rst_n(rst_n),
  .l_valid(f_l0v),.l_ready(t_l0g),.l_data(f_l0d),.c_valid(lv[0]),.c_ready(lr[0]),.c_data(ld[603:0]));
 ot_dsrom_mtp_lrx_rtt #(.W(604),.D(D_C),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(CF),.RETURN_HOPS(CR)) u_l1(.clk(clk),.rst_n(rst_n),
  .l_valid(f_l1v),.l_ready(t_l1g),.l_data(f_l1d),.c_valid(lv[1]),.c_ready(lr[1]),.c_data(ld[1207:604]));
 wire sv, sr; wire [100:0] sd;
 ot_dsrom_mtp_lrx_rtt #(.W(101),.D(D_C),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(CF),.RETURN_HOPS(CR)) u_st(.clk(clk),.rst_n(rst_n),
  .l_valid(f_sv),.l_ready(t_sg),.l_data(f_sd),.c_valid(sv),.c_ready(sr),.c_data(sd));
 // core ports: ot_dsrom_mtp_pp2 2-entry ping-pong stages (port valid / data from flops via one 2:1 mux; the core's
 // ready steers 3 flops).  fixlat-p2lnk-ffbec0c86-tc TT -280 (74-b compare to c_in_v; ready -> 604/101-b enables); the
 // ltx_rc -> lrx D4 pairs of 3d7201bc4 put the D4 queue mux on the port (same class measured on collp2 5b059065b).
 ot_dsrom_mtp_pp2 #(.W(101)) u_sc(.clk(clk),.rst_n(rst_n),.i_valid(sv),.i_ready(sr),.i_data(sd),
  .o_valid(c_start_v),.o_ready(c_start_r),.o_data(c_start_d),.g_id(1'b0),.g_ok(1'b0),.g_chg(1'b0));
 // transaction gate: identity of the start the core accepted (registered take), held in each lane stage's slot flags
 reg [73:0] cur_id, acc_id; reg cur_ok, acc, chg;
 always @(posedge clk) acc_id <= c_start_d[100:27];
 always @(posedge clk)
  if(!rst_n) begin acc<=1'b0; cur_ok<=1'b0; cur_id<='0; chg<=1'b0; end
  else begin
   acc <= c_start_v && c_start_r;
   chg <= acc;
   if(acc) begin cur_ok<=1'b1; cur_id<=acc_id; end
  end
`ifdef OT_FIXLAT_MUT_NOGATE
 localparam integer GATE = 0;
`else
 localparam integer GATE = 74;
`endif
 genvar k;
 generate for (k=0; k<2; k=k+1) begin: g_lane
  ot_dsrom_mtp_pp2 #(.W(604),.IDG(GATE),.IDL(530)) u_pp(.clk(clk),.rst_n(rst_n),.i_valid(lv[k]),.i_ready(lr[k]),
   .i_data(ld[604*k +: 604]),.o_valid(c_in_v[k]),.o_ready(c_in_r[k]),.o_data(c_in_d[604*k +: 604]),
   .g_id(cur_id[(GATE>0?GATE:1)-1:0]),.g_ok(cur_ok),.g_chg(chg));
 end endgenerate
 ot_dsrom_mtp_ltx_rc #(.W(594)) u_o(.clk(clk),.rst_n(rst_n),.c_valid(c_out_v),.c_ready(c_out_r),.c_data(c_out_d),
  .l_valid(t_ov),.l_ready(f_og),.l_data(t_od));
endmodule

// Collective-slab end: sends the start, receives the result row (F = p2 -> collective, R = collective -> p2).
// Lane 1 (die B's expert words) is NOT here: dsfd_coll_p2_lane_ba (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_p2_lane.sv,
// OGRANT) is its grant-protocol sender onto the die bus (mtp-colllane-1011 8aa62270c), so this end has no lane-1 port.
// Core side (the abutting dsfd_coll_p2_lane_pa): start in on valid / ready from one flop (ltx_rc); result row out on
// valid / ready through an abutting grant pair (ltx_rc -> ot_dsrom_mtp_lrx D 4 SEL 1, no stations: the closed 3-cycle
// history is exact there), so the core's ready only steers a dozen state flops, never the 594-b row registers
// (fixlat-collp2-ffbec0c86-tc TT -64.76: c_or -> 594-b c_data / wp enables, 13 levels).
module dsfd_coll_p2_ep #(parameter integer FWD_C = 8, parameter integer RET_C = 9,
                         parameter integer D_O = FWD_C + RET_C + 4) (
 input wire [0:0] ck, rst,
 input wire [0:0] c_sv, output wire [0:0] c_sr, input wire [100:0] c_sd,
 output wire [0:0] t_sv, output wire [100:0] t_sd, input wire [0:0] f_sg,
 input wire [0:0] f_ov, input wire [593:0] f_od, output wire [0:0] t_og,
 output wire [0:0] c_ov, input wire [0:0] c_or, output wire [593:0] c_od
);
`ifdef OT_FIXLAT_MUT_LAT1
 localparam integer OF = 0, OR = 0;
`else
 localparam integer OF = RET_C, OR = FWD_C;
`endif
 wire rn;
 ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
 ot_dsrom_mtp_ltx_rc #(.W(101)) u_st(.clk(ck[0]),.rst_n(rn),.c_valid(c_sv),.c_ready(c_sr),.c_data(c_sd),
  .l_valid(t_sv),.l_ready(f_sg),.l_data(t_sd));
 wire ov, orr, gv, gr; wire [593:0] od, gd;
 ot_dsrom_mtp_lrx_rtt #(.W(594),.D(D_O),.SEL(1),.ENABLE_RTT(1),.FORWARD_HOPS(OF),.RETURN_HOPS(OR)) u_o(.clk(ck[0]),.rst_n(rn),
  .l_valid(f_ov),.l_ready(t_og),.l_data(f_od),.c_valid(ov),.c_ready(orr),.c_data(od));
 ot_dsrom_mtp_ltx_rc #(.W(594)) u_og(.clk(ck[0]),.rst_n(rn),.c_valid(ov),.c_ready(orr),.c_data(od),
  .l_valid(gv),.l_ready(gr),.l_data(gd));
 wire cv, cr; wire [593:0] cd;
 ot_dsrom_mtp_lrx #(.W(594),.D(4),.SEL(1)) u_oc(.clk(ck[0]),.rst_n(rn),.l_valid(gv),.l_ready(gr),.l_data(gd),
  .c_valid(cv),.c_ready(cr),.c_data(cd));
 // Core-facing output register (idle-sweep-1011): fixlat-collp2-5b059065b-tc NEEDS_RTL TT -52.31 at the routed insertion =
 // u_oc.rp -> D4 read mux (OA22 / AND3 / AOI21) -> c_od[*] under the 0.62 T output budget. ot_sc_pfifo S 2: c_od is one
 // AND-OR of flop copies (rs x slot), c_ov / c_or-side state are flops, c_or touches only pointer state. +1 cycle per row.
 ot_sc_pfifo #(.W(594),.S(2),.G(32)) u_op(.clk(ck[0]),.rst_n(rn),.in_valid(cv),.in_ready(cr),.in_data(cd),
  .out_valid(c_ov),.out_ready(c_or),.out_data(c_od));
endmodule

// VM-slab end: sends lane 0.
module dsfd_vm_p2_ep (
 input wire [0:0] ck, rst,
 input wire [0:0] c_l0v, output wire [0:0] c_l0r, input wire [603:0] c_l0d,
 output wire [0:0] t_l0v, output wire [603:0] t_l0d, input wire [0:0] f_l0g
);
 wire rn;
 ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
 ot_dsrom_mtp_ltx #(.W(604)) u_l0(.clk(ck[0]),.rst_n(rn),.c_valid(c_l0v),.c_ready(c_l0r),.c_data(c_l0d),
  .l_valid(t_l0v),.l_ready(f_l0g),.l_data(t_l0d));
endmodule
`default_nettype wire
