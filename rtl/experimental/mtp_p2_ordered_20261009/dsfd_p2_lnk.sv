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
// Boundary timing: every receiver facing a core port runs SEL 1 (c_ready selects precomputed next states) and
// OUTPUT_PIPE 1 (registered c_valid / c_data): +1 cycle per lane word / start / result row, pipelined.
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
 wire [1:0] lv, lr, open_;
 ot_dsrom_mtp_lrx_rtt #(.W(604),.D(D_V),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(VF),.RETURN_HOPS(VR)) u_l0(.clk(clk),.rst_n(rst_n),
  .l_valid(f_l0v),.l_ready(t_l0g),.l_data(f_l0d),.c_valid(lv[0]),.c_ready(lr[0]),.c_data(c_in_d[603:0]));
 ot_dsrom_mtp_lrx_rtt #(.W(604),.D(D_C),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(CF),.RETURN_HOPS(CR)) u_l1(.clk(clk),.rst_n(rst_n),
  .l_valid(f_l1v),.l_ready(t_l1g),.l_data(f_l1d),.c_valid(lv[1]),.c_ready(lr[1]),.c_data(c_in_d[1207:604]));
 ot_dsrom_mtp_lrx_rtt #(.W(101),.D(D_C),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(CF),.RETURN_HOPS(CR)) u_st(.clk(clk),.rst_n(rst_n),
  .l_valid(f_sv),.l_ready(t_sg),.l_data(f_sd),.c_valid(c_start_v),.c_ready(c_start_r),.c_data(c_start_d));
 // transaction gate: identity of the start the core last accepted (registered compare against the registered heads)
 reg [73:0] cur_id; reg cur_ok;
 always @(posedge clk)
  if(!rst_n) begin cur_ok<=1'b0; cur_id<='0; end
  else if(c_start_v&&c_start_r) begin cur_ok<=1'b1; cur_id<=c_start_d[100:27]; end
`ifdef OT_FIXLAT_MUT_NOGATE
 assign open_=2'b11;
`else
 assign open_[0]=cur_ok&&(c_in_d[603:530]==cur_id);
 assign open_[1]=cur_ok&&(c_in_d[1207:1134]==cur_id);
`endif
 assign c_in_v=lv&open_;
 assign lr=c_in_r&open_;
 ot_dsrom_mtp_ltx #(.W(594)) u_o(.clk(clk),.rst_n(rst_n),.c_valid(c_out_v),.c_ready(c_out_r),.c_data(c_out_d),
  .l_valid(t_ov),.l_ready(f_og),.l_data(t_od));
endmodule

// Collective-slab end: sends lane 1 and start, receives the result row (F = p2 -> collective, R = collective -> p2).
module dsfd_coll_p2_ep #(parameter integer FWD_C = 8, parameter integer RET_C = 9,
                         parameter integer D_O = FWD_C + RET_C + 4) (
 input wire [0:0] ck, rst,
 input wire [0:0] c_l1v, output wire [0:0] c_l1r, input wire [603:0] c_l1d,
 output wire [0:0] t_l1v, output wire [603:0] t_l1d, input wire [0:0] f_l1g,
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
 ot_dsrom_mtp_ltx #(.W(604)) u_l1(.clk(ck[0]),.rst_n(rn),.c_valid(c_l1v),.c_ready(c_l1r),.c_data(c_l1d),
  .l_valid(t_l1v),.l_ready(f_l1g),.l_data(t_l1d));
 ot_dsrom_mtp_ltx #(.W(101)) u_st(.clk(ck[0]),.rst_n(rn),.c_valid(c_sv),.c_ready(c_sr),.c_data(c_sd),
  .l_valid(t_sv),.l_ready(f_sg),.l_data(t_sd));
 ot_dsrom_mtp_lrx_rtt #(.W(594),.D(D_O),.SEL(1),.ENABLE_RTT(1),.OUTPUT_PIPE(1),.FORWARD_HOPS(OF),.RETURN_HOPS(OR)) u_o(.clk(ck[0]),.rst_n(rn),
  .l_valid(f_ov),.l_ready(t_og),.l_data(f_od),.c_valid(c_ov),.c_ready(c_or),.c_data(c_od));
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
