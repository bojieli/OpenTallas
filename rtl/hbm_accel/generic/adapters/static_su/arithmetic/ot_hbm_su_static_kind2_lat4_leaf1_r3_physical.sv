// REGIONAL-ROOT KIND2 lane leaf (H-SU 10-17, after the r1 gate: one lane root of 32,978 sinks failed the >15k measured
// insertion/spread rule): clk_pin = pin registers; clk = stages 0-3 and 5-7 (~13.1k); clk_sfu = stage-4 SFU pipeline (~10.8k);
// clk_ins = the parallel insertion line (~9.4k); clk_side = the SIDE pipe. Roots meet only at the registered seams
// stage-3 registers -> SFU / insertion / side inputs and their output registers -> stage-5 merge.
// TWO-ROOT (pin / lane) KIND2 lane leaf (H-ELEM / coordinator decision 10-16, option (a)): the same pin-registered LAT4/LEAF1 lane
// with ONE regional clock root driving every pipeline stage and insertion register, so no internal stage hop crosses
// clock entries (no cross-root hold reserve). KIND2: the SIDE pipe is inside (no side pins). Roots of different leaves meet only at the registered pins.
// Physical KIND2 FULL lane leaf (global lane 0, SIDE pipe port) (LAT4 / LEAF1; H-SU pgslice 2026-10-16: the KIND0 r2 leaf with KIND 2, same pins): pin-registered lane
// (ot_hbm_su_static_lane_pinreg: every input and output registered at the pin, +2 edges at the parent, absorbed by
// su_top_compile --pin-reg). No arithmetic change. rst_n registered at its pin (PIN_RST=1).
module ot_hbm_su_static_kind2_lat4_leaf1_r3_physical(
 input wire clk_pin,  // regional root of the pin registers (every input, rst_n, every output)
 input wire clk,      // lane root: pipeline stages 0-3 and 5-7
 input wire clk_sfu,  // stage-4 SFU pipeline (exp / den / div) root
 input wire clk_ins,  // insertion (ins line) root, parallel to the SFU
 input wire clk_side, // FULL lane SIDE pipe root (rsqrt / softplus / exp)
 input wire rst_n,
 input wire [10:0] lane_id,
 input wire ld,
 input wire ld_bank,
 input wire [839:0] ld_c,
 input wire emit,
 input wire bank,
 input wire [23:0] o_v,
 input wire [23:0] i_v,
 input wire [23:0] no,
 input wire [23:0] ni,
 input wire [3:0] ls,
 input wire [3:0] lvw,
 input wire [119:0] vb,
 input wire [23:0] krow,
 input wire [23:0] obase,
 input wire [23:0] aibase,
 input wire [1:0] aind,
 input wire [4:0] gsh,
 input wire cpair,
 input wire [1:0] dst,
 input wire [7:0] srcs,
 output wire vi_re,
 output wire [23:0] vi_addr,
 input wire [31:0] vi_q,
 output wire [95:0] rd_addr,
 output wire [3:0] rd_re,
 output wire [7:0] rd_src,
 input wire [127:0] rd_q,
 input wire [7:0] cx_srcs,
 input wire cx_arnd,
 input wire cx_arelu,
 input wire cx_amin,
 input wire cx_cclip,
 input wire [31:0] cx_imm3,
 input wire [2:0] cp_m1,
 input wire [31:0] cp_imm1,
 input wire [2:0] cm_m1,
 input wire [1:0] cm_m2,
 input wire [2:0] cm_qm,
 input wire [31:0] cm_imm1,
 input wire [2:0] ca_ad,
 input wire [31:0] ca_imm2,
 input wire [2:0] ci_sfu,
 input wire [2:0] cs_sfu,
 input wire [2:0] cs_e1,
 input wire [31:0] cs_imm2,
 input wire [1:0] ce_e2,
 input wire [31:0] ce_imm1,
 input wire co_rnd,
 input wire [1:0] co_dst,
 output wire vm_we,
 output wire [23:0] vm_waddr,
 output wire [31:0] vm_wdata,
 output wire kv_we,
 output wire [23:0] kv_waddr,
 output wire [31:0] kv_wdata,
 output wire ro_v,
 output wire [31:0] ro_x,
 output wire fault,
 output wire coll
);
 wire l_side_v, l_fault; wire [31:0] l_side_x, l_side_y; wire side_fault;
 reg side_rst_q;  // rst_n registered at its pin for the SIDE pipe (as the lane's PIN_RST)
 always @(posedge clk_pin) side_rst_q <= rst_n;
 ot_hbm_su_static_lane_pinreg #(.LN(7),.LEAF(1),.KIND(2),.FETCH_EXTRA_EDGES(2),.MLAT(4),.ALAT(3),.PIN_RST(1),.PIN_ROOT(1)) u_native(
 .clk_pin(clk_pin),
 .clk_stage({clk,clk,clk,clk_sfu,clk,clk,clk,clk}),
 .clk_insert({4{clk_ins}}),
 .rst_n(rst_n),
 .lane_id(lane_id),
 .ld(ld),
 .ld_bank(ld_bank),
 .ld_c(ld_c),
 .emit(emit),
 .bank(bank),
 .o_v(o_v),
 .i_v(i_v),
 .no(no),
 .ni(ni),
 .ls(ls),
 .lvw(lvw),
 .vb(vb),
 .krow(krow),
 .obase(obase),
 .aibase(aibase),
 .aind(aind),
 .gsh(gsh),
 .cpair(cpair),
 .dst(dst),
 .srcs(srcs),
 .vi_re(vi_re),
 .vi_addr(vi_addr),
 .vi_q(vi_q),
 .rd_addr(rd_addr),
 .rd_re(rd_re),
 .rd_src(rd_src),
 .rd_q(rd_q),
 .cx_srcs(cx_srcs),
 .cx_arnd(cx_arnd),
 .cx_arelu(cx_arelu),
 .cx_amin(cx_amin),
 .cx_cclip(cx_cclip),
 .cx_imm3(cx_imm3),
 .cp_m1(cp_m1),
 .cp_imm1(cp_imm1),
 .cm_m1(cm_m1),
 .cm_m2(cm_m2),
 .cm_qm(cm_qm),
 .cm_imm1(cm_imm1),
 .ca_ad(ca_ad),
 .ca_imm2(ca_imm2),
 .ci_sfu(ci_sfu),
 .cs_sfu(cs_sfu),
 .cs_e1(cs_e1),
 .cs_imm2(cs_imm2),
 .ce_e2(ce_e2),
 .ce_imm1(ce_imm1),
 .co_rnd(co_rnd),
 .co_dst(co_dst),
 .side_v(l_side_v),
 .side_x(l_side_x),
 .side_y(l_side_y),
 .vm_we(vm_we),
 .vm_waddr(vm_waddr),
 .vm_wdata(vm_wdata),
 .kv_we(kv_we),
 .kv_waddr(kv_waddr),
 .kv_wdata(kv_wdata),
 .ro_v(ro_v),
 .ro_x(ro_x),
 .fault(l_fault),
 .coll(coll)
 );

 // The FULL lane's scalar SIDE pipe lives INSIDE this leaf (H-SU 10-16, owner rule "register every tile pin"): the
 // fixed-depth side loop (side_x -> side pipe -> side_y) has no lane-side slack, so instead of exposing it as
 // combinational pins it closes on the leaf's one root. The S codes take the same one-edge pin register the
 // pgslice applied (PIN_REG g_fn_pin), so the loop timing is unchanged (0 edges). The side fault joins the leaf fault.
 reg [2:0] fn_q, fn_out_q;
 always @(posedge clk_pin) begin fn_q <= ci_sfu; fn_out_q <= cs_sfu; end
 ot_hbm_su_static_side u_side(.clk({6{clk_side}}), .rst_n(side_rst_q), .v(l_side_v), .fn(fn_q), .x(l_side_x), .fn_out(fn_out_q),
  .y(l_side_y), .fault(side_fault));
 reg fault_q;  // the leaf fault leaves through a pin register (lane fault | side fault; sticky at the parent)
 always @(posedge clk_pin) fault_q <= l_fault | side_fault;
 assign fault = fault_q;
endmodule
