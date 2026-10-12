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
// receiver (OUTPUT_PIPE 1: the compare reads a registered head, not the queue mux).
// Boundary (rev 2, fixlat-p2lnk-ffbec0c86-tc TT -280: c_in_v = valid AND a 74-b compare (13 levels to the pin), c_in_r
// -> 604-b output-pipe enables + SEL state (15 levels, 1,208 loads from one input pin), head / row flops 100+ um from
// their pins): no core port touches logic.  Per lane: receiver (lrx_rtt OUTPUT_PIPE, registered head) -> GATE stage
// (a_d / a_v, a REGISTERED match flag a_m: the compare reads flops and lands in one flop, recomputed every cycle for
// the next head / next identity) -> core-side ot_sc_pfifo PINREG S 3 (pin flop capture, registered in_ready /
// out_valid, out_data = 3:1 select by replicated pointer flops, c_in_r only steers the late-select copies).  Start:
// receiver -> ot_sc_pfifo PINREG S 3.  Accepted-start identity: the accept is registered (acc_r) together with a
// free-running copy of c_start_d (sd_r), so c_start_r reaches 1 flop, never the 74-b cur_id enables; the gate opens
// one cycle after the core accepts the start (correct: later is safe, earlier is the fault).  Result row: core ->
// ot_sc_pfifo PINREG S 3 (c_out_r = its registered in_ready, pin flops at the core pins) -> ot_dsrom_mtp_ltx_rc
// (grant from one flop, row flops at the die pins).  Cost: +3 cycles per lane word / +2 per start / +2 per result row,
// pipelined (full rate kept: S 3 with PINREG; receiver depths unchanged).
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
 // ---- start: receiver -> core-side pin FIFO
 wire sv, sr; wire [100:0] sd;
 ot_dsrom_mtp_lrx_rtt #(.W(101),.D(D_C),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(CF),.RETURN_HOPS(CR)) u_st(.clk(clk),.rst_n(rst_n),
  .l_valid(f_sv),.l_ready(t_sg),.l_data(f_sd),.c_valid(sv),.c_ready(sr),.c_data(sd));
 ot_sc_pfifo #(.W(101),.S(3),.G(32),.PINREG(1)) u_sp(.clk(clk),.rst_n(rst_n),.in_valid(sv),.in_ready(sr),.in_data(sd),
  .out_valid(c_start_v[0]),.out_ready(c_start_r[0]),.out_data(c_start_d));
 // ---- accepted-start identity (registered accept + free-running data copy; cur_id loads from flops only)
 reg acc_r; reg [73:0] sd_r, cur_id; reg cur_ok;
 always @(posedge clk) sd_r <= c_start_d[100:27];
 always @(posedge clk)
  if(!rst_n) begin acc_r<=1'b0; cur_ok<=1'b0; cur_id<='0; end
  else begin
   acc_r <= c_start_v[0] && c_start_r[0];
   if(acc_r) begin cur_ok<=1'b1; cur_id<=sd_r; end
  end
 wire [73:0] cur_id_n = acc_r ? sd_r : cur_id;   // identity in force next cycle (from flops)
 wire cur_ok_n = cur_ok || acc_r;
 // ---- lanes: receiver -> gate stage -> core-side pin FIFO
 genvar l;
 generate for (l = 0; l < 2; l = l + 1) begin: g_lane
  wire rv, rr; wire [603:0] rd;
  if (l == 0) begin: g_r
   ot_dsrom_mtp_lrx_rtt #(.W(604),.D(D_V),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(VF),.RETURN_HOPS(VR)) u_rx(.clk(clk),.rst_n(rst_n),
    .l_valid(f_l0v),.l_ready(t_l0g),.l_data(f_l0d),.c_valid(rv),.c_ready(rr),.c_data(rd));
  end else begin: g_r
   ot_dsrom_mtp_lrx_rtt #(.W(604),.D(D_C),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(CF),.RETURN_HOPS(CR)) u_rx(.clk(clk),.rst_n(rst_n),
    .l_valid(f_l1v),.l_ready(t_l1g),.l_data(f_l1d),.c_valid(rv),.c_ready(rr),.c_data(rd));
  end
  // gate stage: a_m = (identity of the word held next cycle == identity in force next cycle), registered
  reg a_v, a_m; reg [603:0] a_d;
  wire pr;                                  // pin FIFO in_ready (a flop)
`ifdef OT_FIXLAT_MUT_NOGATE
  wire pass = a_v;
`else
  wire pass = a_v && a_m;
`endif
  wire adv = !a_v || (pass && pr);          // the stage takes the receiver head (flops only)
  assign rr = adv;
  wire [73:0] id_n = adv ? rd[603:530] : a_d[603:530];
  always @(posedge clk) begin
   if(!rst_n) begin a_v<=1'b0; a_m<=1'b0; end
   else begin
    if(adv) a_v<=rv;
    a_m <= cur_ok_n && (id_n == cur_id_n);
   end
   if(adv && rv) a_d<=rd;
  end
  ot_sc_pfifo #(.W(604),.S(3),.G(32),.PINREG(1)) u_pf(.clk(clk),.rst_n(rst_n),.in_valid(pass),.in_ready(pr),.in_data(a_d),
   .out_valid(c_in_v[l]),.out_ready(c_in_r[l]),.out_data(c_in_d[604*l+:604]));
 end endgenerate
 // ---- result row: core -> pin FIFO -> grant-protocol sender (grant from one flop)
 wire ov, orr; wire [593:0] od;
 ot_sc_pfifo #(.W(594),.S(3),.G(32),.PINREG(1)) u_op(.clk(clk),.rst_n(rst_n),.in_valid(c_out_v[0]),.in_ready(c_out_r[0]),.in_data(c_out_d),
  .out_valid(ov),.out_ready(orr),.out_data(od));
 ot_dsrom_mtp_ltx_rc #(.W(594)) u_o(.clk(clk),.rst_n(rst_n),.c_valid(ov),.c_ready(orr),.c_data(od),
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
// BE S-face contract v3 (el1011-ds-vm b235ed401, s81die-1011 2026-10-11): the VM back end's P2 port is READY-LATENCY
// RL = 4: the BE asserts c_l0v in cycle t only if c_l0r was high in cycle t - RL, and every c_l0v beat is a transfer
// (no same-cycle ready).  This end therefore lands every beat: c_l0v / c_l0d -> pin flops -> a D-entry landing queue
// -> the grant-protocol sender.  c_l0r is a flop: it is raised for cycle t + 1 only if the queue has room for every beat
// that can still arrive, counting the queue, the pin flop and the last RL + 1 issued readies (pops ignored, so the
// bound is safe):  cnt + pv + popcount(rh[RL:0]) + 1 <= D.  The issue -> queue round trip is RL + 2 cycles, so D = RL + 6
// keeps a full-rate stream (one beat a cycle) with no ready bubble.  Mutant OT_S81PH_MUT_P2EP_NOSLACK: ready ignores
// the in-flight beats (room for one) -> the queue overflows under a stalled grant and lane-0 words are lost.
module dsfd_vm_p2_ep #(parameter integer RL = 4, parameter integer D = RL + 6) (
 input wire [0:0] ck, rst,
 input wire [0:0] c_l0v, output wire [0:0] c_l0r, input wire [603:0] c_l0d,
 output wire [0:0] t_l0v, output wire [603:0] t_l0d, input wire [0:0] f_l0g
);
 localparam integer AW = $clog2(D), CW = $clog2(D + 1), HW = RL + 1;
 wire rn;
 ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
 // pin flops (data without reset)
 reg pv; reg [603:0] pd;
 always @(posedge ck[0]) pd <= c_l0d;
 always @(posedge ck[0] or negedge rn) if (!rn) pv <= 1'b0; else pv <= c_l0v[0];
 // landing queue: payload slots without reset, pointers / count with reset
 reg [603:0] q [0:D-1];
 reg [AW-1:0] wp, rp; reg [CW-1:0] cnt;
 wire qv = cnt != 0;
 wire tr;                                   // sender takes the head
 wire pop = qv && tr;
 always @(posedge ck[0]) if (pv) q[wp] <= pd;
 always @(posedge ck[0] or negedge rn)
  if (!rn) begin wp <= 0; rp <= 0; cnt <= 0; end
  else begin
   if (pv)  wp <= (wp == D - 1) ? {AW{1'b0}} : wp + 1'b1;
   if (pop) rp <= (rp == D - 1) ? {AW{1'b0}} : rp + 1'b1;
   cnt <= cnt + pv - pop;
  end
 // credit-style ready: one flop, from flops only
 reg r; reg [HW-1:0] rh;                    // rh[0] = r one cycle ago ... rh[RL] = r RL + 1 cycles ago
 integer k; reg [CW+2:0] infl;
 always @* begin infl = cnt + pv + r; for (k = 0; k < RL; k = k + 1) infl = infl + rh[k]; end
 always @(posedge ck[0] or negedge rn)
  if (!rn) begin r <= 1'b0; rh <= {HW{1'b0}}; end
  else begin
   rh <= {rh[HW-2:0], r};
`ifdef OT_S81PH_MUT_P2EP_NOSLACK
   r <= cnt + pv < D;
`else
   r <= infl + 1 <= D;
`endif
  end
 assign c_l0r = r;
 ot_dsrom_mtp_ltx #(.W(604)) u_l0(.clk(ck[0]),.rst_n(rn),.c_valid(qv),.c_ready(tr),.c_data(q[rp]),
  .l_valid(t_l0v),.l_ready(f_l0g),.l_data(t_l0d));
 // overflow is a contract breach (BE or this bound): visible in simulation
 // synthesis translate_off
 always @(posedge ck[0]) if (rn && pv && !pop && cnt == D) $fatal(1, "dsfd_vm_p2_ep: landing queue overflow (RL %0d D %0d)", RL, D);
 // synthesis translate_on
endmodule
`default_nettype wire
