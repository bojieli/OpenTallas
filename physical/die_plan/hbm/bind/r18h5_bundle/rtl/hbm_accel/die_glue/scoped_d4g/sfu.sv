// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_arithmetic_grid.sv
`timescale 1ns/1ps
`default_nettype none
// Wires-only native arithmetic-grid candidate. No HGI/control/memory envelope is claimed.
// Each mapper adds4edges; caller must bind exact controller phase and actual cache/ACK lifetime.
module ot_hgi_sfu_arithmetic_grid__d4g_sfu #(
 parameter integer BTREE=0   // 1: registered broadcast tree (4 ot_hgi_sfu_bcast_e0__d4g_sfu nodes + 16 ot_hgi_sfu_lane_map_e123__d4g_sfu), cycle-identical
) (
 input wire [15:0] clk_lane, clk_map, rst_lane_n, rst_map_n,
 input wire [1741:0] control,
 input wire [511:0] vi_q,
 input wire [2047:0] rd_q,
 output wire [15:0] vi_re, vm_we, kv_we, ro_v, fault, coll,
 output wire [383:0] vi_addr, vm_waddr, kv_waddr,
 output wire [1535:0] rd_addr,
 output wire [63:0] rd_re,
 output wire [127:0] rd_src,
 output wire [511:0] vm_wdata, kv_wdata, ro_x
);
 // side_v/side_x/side_y REMOVED (H-NETLIST/suport 2026-10-16, H-SU agreed): ot_su12_sfu__d4g_sfu leaves its lane's side pins
 // open / 0 (rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv:152): its own side_v/side_x outputs are undriven and side_y is
 // ignored, so they are left unconnected here.
 wire [0:0] r_ld;
 wire [0:0] r_ld_bank;
 wire [1199:0] r_ld_c;
 wire [0:0] r_emit;
 wire [0:0] r_bank;
 wire [23:0] r_o_v;
 wire [23:0] r_i_v;
 wire [23:0] r_no;
 wire [23:0] r_ni;
 wire [3:0] r_ls;
 wire [3:0] r_lvw;
 wire [119:0] r_vb;
 wire [23:0] r_krow;
 wire [23:0] r_obase;
 wire [23:0] r_aibase;
 wire [1:0] r_aind;
 wire [4:0] r_gsh;
 wire [0:0] r_cpair;
 wire [1:0] r_dst;
 wire [7:0] r_srcs;
 wire [0:0] r_cx_arnd;
 wire [0:0] r_cx_arelu;
 wire [0:0] r_cx_amin;
 wire [0:0] r_cx_cclip;
 wire [31:0] r_cx_imm3;
 wire [2:0] r_cp_m1;
 wire [31:0] r_cp_imm1;
 wire [2:0] r_cm_m1;
 wire [1:0] r_cm_m2;
 wire [2:0] r_cm_qm;
 wire [31:0] r_cm_imm1;
 wire [2:0] r_ca_ad;
 wire [31:0] r_ca_imm2;
 wire [2:0] r_ci_sfu;
 wire [2:0] r_cs_sfu;
 wire [2:0] r_cs_e1;
 wire [31:0] r_cs_imm2;
 wire [1:0] r_ce_e2;
 wire [31:0] r_ce_imm1;
 wire [0:0] r_co_rnd;
 wire [1:0] r_co_dst;
 assign {r_ld, r_ld_bank, r_ld_c, r_emit, r_bank, r_o_v, r_i_v, r_no, r_ni, r_ls, r_lvw, r_vb, r_krow, r_obase, r_aibase, r_aind, r_gsh, r_cpair, r_dst, r_srcs, r_cx_arnd, r_cx_arelu, r_cx_amin, r_cx_cclip, r_cx_imm3, r_cp_m1, r_cp_imm1, r_cm_m1, r_cm_m2, r_cm_qm, r_cm_imm1, r_ca_ad, r_ca_imm2, r_ci_sfu, r_cs_sfu, r_cs_e1, r_cs_imm2, r_ce_e2, r_ce_imm1, r_co_rnd, r_co_dst}=control;
 wire [479:0] terms;
 for(genvar s=0;s<5;s=s+1)begin:g_terms
  for(genvar k=0;k<4;k=k+1)begin:g_bit
   assign terms[(s*4+k)*24+:24]=r_ld_c[(s*10+k)*24+:24];
  end
 end
 wire [479:0] n_terms[0:3]; wire [23:0] n_ov[0:3],n_iv[0:3],n_row[0:3]; wire [3:0] n_ls[0:3],n_lvw[0:3];
 wire n_emit[0:3],n_ld[0:3]; wire [459:0] n_pass[0:3];
 wire [460:0] c_pass={r_ld, r_ld_bank, r_bank, r_no, r_ni, r_vb, r_obase, r_aibase, r_aind, r_gsh, r_cpair, r_dst, r_srcs, r_cx_arnd, r_cx_arelu, r_cx_amin, r_cx_cclip, r_cx_imm3, r_cp_m1, r_cp_imm1, r_cm_m1, r_cm_m2, r_cm_qm, r_cm_imm1, r_ca_ad, r_ca_imm2, r_ci_sfu, r_cs_sfu, r_cs_e1, r_cs_imm2, r_ce_e2, r_ce_imm1, r_co_rnd, r_co_dst};
 if(BTREE!=0)begin:g_tree
  // one edge-0 node per four lanes, clocked / reset with the first mapper of its group (same domain, own root)
  for(genvar q=0;q<4;q=q+1)begin:g_node
   ot_hgi_sfu_bcast_e0__d4g_sfu u_node(.clk(clk_map[4*q]),.rst_n(rst_map_n[4*q]),.ld_terms(terms),.i_o_v(r_o_v),.i_i_v(r_i_v),
    .i_krow(r_krow),.i_ls(r_ls),.i_lvw(r_lvw),.i_emit(r_emit),.i_pass(c_pass),.e0_terms(n_terms[q]),.e0_ov(n_ov[q]),
    .e0_iv(n_iv[q]),.e0_row(n_row[q]),.e0_ls(n_ls[q]),.e0_lvw(n_lvw[q]),.e0_emit(n_emit[q]),.e0_pass(n_pass[q]),.e0_ld(n_ld[q]));
  end
 end
 for(genvar j=0;j<16;j=j+1)begin:g_lane
  wire [0:0] m_ld;
  wire [0:0] m_ld_bank;
  wire [1199:0] m_ld_c;
  wire [0:0] m_emit;
  wire [0:0] m_bank;
  wire [23:0] m_o_v;
  wire [23:0] m_i_v;
  wire [23:0] m_no;
  wire [23:0] m_ni;
  wire [3:0] m_ls;
  wire [3:0] m_lvw;
  wire [119:0] m_vb;
  wire [23:0] m_krow;
  wire [23:0] m_obase;
  wire [23:0] m_aibase;
  wire [1:0] m_aind;
  wire [4:0] m_gsh;
  wire [0:0] m_cpair;
  wire [1:0] m_dst;
  wire [7:0] m_srcs;
  wire [0:0] m_cx_arnd;
  wire [0:0] m_cx_arelu;
  wire [0:0] m_cx_amin;
  wire [0:0] m_cx_cclip;
  wire [31:0] m_cx_imm3;
  wire [2:0] m_cp_m1;
  wire [31:0] m_cp_imm1;
  wire [2:0] m_cm_m1;
  wire [1:0] m_cm_m2;
  wire [2:0] m_cm_qm;
  wire [31:0] m_cm_imm1;
  wire [2:0] m_ca_ad;
  wire [31:0] m_ca_imm2;
  wire [2:0] m_ci_sfu;
  wire [2:0] m_cs_sfu;
  wire [2:0] m_cs_e1;
  wire [31:0] m_cs_imm2;
  wire [1:0] m_ce_e2;
  wire [31:0] m_ce_imm1;
  wire [0:0] m_co_rnd;
  wire [1:0] m_co_dst;
  wire [460:0] mapped_pass;
  if(BTREE!=0)begin:g_e123
  ot_hgi_sfu_lane_map_e123__d4g_sfu u_map (
.clk(clk_map[j]),.rst_n(rst_map_n[j]),.lane_j(4'(j)),.e0_terms(n_terms[j/4]),.e0_ov(n_ov[j/4]),.e0_iv(n_iv[j/4]),
.e0_row(n_row[j/4]),.e0_ls(n_ls[j/4]),.e0_lvw(n_lvw[j/4]),.e0_emit(n_emit[j/4]),.e0_pass(n_pass[j/4]),.e0_ld(n_ld[j/4]),
.o_ld_c(m_ld_c),.o_o_v(m_o_v),.o_i_v(m_i_v),.o_krow(m_krow),.o_ls(m_ls),.o_lvw(m_lvw),.o_emit(m_emit),.o_pass(mapped_pass));
  end else begin:g_mono
  ot_hgi_sfu_lane_map__d4g_sfu u_map (
.clk(clk_map[j]),.rst_n(rst_map_n[j]),.lane_j(4'(j)),.ld_terms(terms),
.i_o_v(r_o_v),.i_i_v(r_i_v),.i_krow(r_krow),.i_ls(r_ls),.i_lvw(r_lvw),.i_emit(r_emit),
.i_pass(c_pass),
.o_ld_c(m_ld_c),.o_o_v(m_o_v),.o_i_v(m_i_v),.o_krow(m_krow),.o_ls(m_ls),.o_lvw(m_lvw),.o_emit(m_emit),.o_pass(mapped_pass));
  end
  assign {m_ld, m_ld_bank, m_bank, m_no, m_ni, m_vb, m_obase, m_aibase, m_aind, m_gsh, m_cpair, m_dst, m_srcs, m_cx_arnd, m_cx_arelu, m_cx_amin, m_cx_cclip, m_cx_imm3, m_cp_m1, m_cp_imm1, m_cm_m1, m_cm_m2, m_cm_qm, m_cm_imm1, m_ca_ad, m_ca_imm2, m_ci_sfu, m_cs_sfu, m_cs_e1, m_cs_imm2, m_ce_e2, m_ce_imm1, m_co_rnd, m_co_dst}=mapped_pass;
`ifdef OT_HARD_CHILDREN
  ot_su12_sfu__d4g_sfu u_sfu (
`else
  ot_su12_sfu__d4g_sfu #(.GSH(1),.KIMM(1),.DENR(1),.DRING(3)) u_sfu (
`endif
.clk(clk_lane[j]),.rst_n(rst_lane_n[j]),
.ld(m_ld),
.ld_bank(m_ld_bank),
.ld_c(m_ld_c),
.emit(m_emit),
.bank(m_bank),
.o_v(m_o_v),
.i_v(m_i_v),
.no(m_no),
.ni(m_ni),
.ls(m_ls),
.lvw(m_lvw),
.vb(m_vb),
.krow(m_krow),
.obase(m_obase),
.aibase(m_aibase),
.aind(m_aind),
.gsh(m_gsh),
.cpair(m_cpair),
.dst(m_dst),
.srcs(m_srcs),
.cx_arnd(m_cx_arnd),
.cx_arelu(m_cx_arelu),
.cx_amin(m_cx_amin),
.cx_cclip(m_cx_cclip),
.cx_imm3(m_cx_imm3),
.cp_m1(m_cp_m1),
.cp_imm1(m_cp_imm1),
.cm_m1(m_cm_m1),
.cm_m2(m_cm_m2),
.cm_qm(m_cm_qm),
.cm_imm1(m_cm_imm1),
.ca_ad(m_ca_ad),
.ca_imm2(m_ca_imm2),
.ci_sfu(m_ci_sfu),
.cs_sfu(m_cs_sfu),
.cs_e1(m_cs_e1),
.cs_imm2(m_cs_imm2),
.ce_e2(m_ce_e2),
.ce_imm1(m_ce_imm1),
.co_rnd(m_co_rnd),
.co_dst(m_co_dst),
.vi_q(vi_q[j*32+:32]),
.rd_q(rd_q[j*128+:128]),
.side_y(),
.vi_re(vi_re[j]),
.vm_we(vm_we[j]),
.kv_we(kv_we[j]),
.ro_v(ro_v[j]),
.fault(fault[j]),
.coll(coll[j]),
.side_v(),
.vi_addr(vi_addr[j*24+:24]),
.vm_waddr(vm_waddr[j*24+:24]),
.kv_waddr(kv_waddr[j*24+:24]),
.rd_addr(rd_addr[j*96+:96]),
.rd_re(rd_re[j*4+:4]),
.rd_src(rd_src[j*8+:8]),
.vm_wdata(vm_wdata[j*32+:32]),
.kv_wdata(kv_wdata[j*32+:32]),
.ro_x(ro_x[j*32+:32]),
.side_x());
 end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_bcast_tree.sv
`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay__d4g_sfu /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// SFU controller broadcast as a REGISTERED distribution tree (Claude hbm-group-B3, 2026-10-14).
//
// The quarter's controller broadcasts 1,022 dynamic bits (ld terms 480, o/i/row 72, ls/lvw 8, emit 1, pass 461) to 16
// lane mappers spread ~1.7 mm along the arithmetic grid; in the monolithic mapper every lane captured them itself at
// its edge 0 (audit 10-14: no registered broadcast tree, a single 1.7 mm hop).  The mapper's edge 0 is a PURE capture of
// common bits (only lane_j is per lane, and lane_j is captured beside it), so the capture can move to the tree: one
// ot_hgi_sfu_bcast_e0__d4g_sfu node per four lanes holds edge 0 (controller -> node <= 500 um), and ot_hgi_sfu_lane_map_e123__d4g_sfu
// holds edges 1..3 of each lane (node -> mapper <= 500 um).  Same four registered edges from the controller output to
// the frozen body (BCAST1 / mapper4 / RET5 unchanged, nothing re-delayed), 2 x 500 um of registered reach, and 4 x
// 1,022 capture flops instead of 16 x 1,022 (-12,264 flops a quarter).  Cycle-identical to ot_hgi_sfu_lane_map__d4g_sfu.
module ot_hgi_sfu_bcast_e0__d4g_sfu (
 input wire clk, rst_n,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output reg [479:0] e0_terms,
 output reg [23:0] e0_ov, e0_iv, e0_row,
 output reg [3:0] e0_ls, e0_lvw,
 output reg e0_emit,
 output reg [459:0] e0_pass,
 output reg e0_ld
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 always @(posedge clk) begin
  e0_terms<=ld_terms; e0_ov<=i_o_v; e0_iv<=i_i_v; e0_row<=i_krow; e0_ls<=i_ls; e0_lvw<=i_lvw; e0_pass<=i_pass[459:0];
  if(!f_rst) begin e0_emit<=1'b0; e0_ld<=1'b0; end
  else begin e0_emit<=i_emit; e0_ld<=i_pass[460]; end
 end
endmodule

// Lane mapper edges 1..3 behind a broadcast node (ot_hgi_sfu_lane_map__d4g_sfu with its edge-0 capture moved to the node).
module ot_hgi_sfu_lane_map_e123__d4g_sfu #(parameter integer MUT_LANE=0, MUT_PASS=0) (   // MUT_PASS 1: pass one edge short (must FAIL)
 input wire clk, rst_n,
 input wire [3:0] lane_j,
 input wire [479:0] e0_terms,
 input wire [23:0] e0_ov, e0_iv, e0_row,
 input wire [3:0] e0_ls, e0_lvw,
 input wire e0_emit,
 input wire [459:0] e0_pass,
 input wire e0_ld,
 output reg [1199:0] o_ld_c,
 output reg [23:0] o_o_v, o_i_v, o_krow,
 output reg [3:0] o_ls, o_lvw,
 output reg o_emit,
 output wire [460:0] o_pass
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 reg [3:0] j0;                                   // captured on the node's edge 0 (lane_j may be a live input)
 reg emit1,emit2;
 reg [79:0] meta1,meta2;
 reg [3:1] ld_pipe;
 // pass: three more edges as a 2-slot ring + output register (written once, read once; no flop-to-flop data chain)
 reg [459:0] ps [0:1]; reg [1:0] poh; reg [459:0] pq;
 always @(posedge clk `OT_SFU_ARST(rst_n)) if(!rst_n) poh<=2'b01; else poh<={poh[0],poh[1]};
 always @(posedge clk) begin
  if(poh[0]) ps[0]<=e0_pass; if(poh[1]) ps[1]<=e0_pass;
  pq<=MUT_PASS ? e0_pass : (poh[0] ? ps[0] : 460'd0) | (poh[1] ? ps[1] : 460'd0);
 end
 assign o_pass={ld_pipe[3],pq};
 reg [23:0] term1[0:19],pair2[0:9];
 always @(posedge clk) begin
  j0<=lane_j ^ 4'(MUT_LANE);
  meta1<={24'(e0_ov + (24'(j0)>>e0_ls) - (24'd5>>e0_ls)),
          24'(e0_iv + (24'(j0)&((24'd1<<e0_ls)-1)) - (24'd5&((24'd1<<e0_ls)-1))),
          24'(e0_row + (24'(j0)>>e0_ls) - (24'd5>>e0_ls)),
          e0_ls,(e0_lvw<3 ? 4'd3 : e0_lvw)};
  meta2<=meta1;
  {o_o_v,o_i_v,o_krow,o_ls,o_lvw}<=meta2;
  for(integer s=0;s<5;s=s+1) begin
   for(integer k=0;k<4;k=k+1)
    term1[s*4+k]<=j0[k] ? e0_terms[(s*4+k)*24+:24] : 24'd0;
   pair2[s*2]<=term1[s*4]+term1[s*4+1];
   pair2[s*2+1]<=term1[s*4+2]+term1[s*4+3];
   o_ld_c[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
  end
  if(!f_rst) begin emit1<=0;emit2<=0;o_emit<=0;ld_pipe<=0;end
  else begin emit1<=e0_emit && (24'(j0)<(24'd1<<e0_lvw));emit2<=emit1;o_emit<=emit2;ld_pipe<={ld_pipe[2:1],e0_ld};end
 end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_core_split2.sv
`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay__d4g_sfu /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// ot_hgi_sfu_core_split2__d4g_sfu (H-SU 2026-10-16, k7; opt-in successor of ot_hgi_sfu_core_split, which stays unchanged):
// the same SFU core (pin registers, VM bridge, static engine with 16 lanes + 80 operand SRAMs; same latencies) with
//  (1) the lane-direct buses split by die face so every lane's 116 boundary pins sit beside it: lanes 0..7 on the W
//      face (_w = bits of lanes 0..7, i.e. the LOW half of each lane-major bus), lanes 8..15 on the E face (_e = high
//      half). Port mapping: vi_re = {vi_re_e, vi_re_w}, vi_addr = {vi_addr_e, vi_addr_w}, ... (lane j at [j*W +: W]).
//  (2) regional clock roots: clk = bridge + engine (~10.9k flops); clk_pw = W-face pin registers local_rq/local_wq/
//      local_rr/local_w_done (~4.4k); clk_pe = E-face pin registers io/compiler_control/ro_v/ro_x (~2.7k). Same clock
//      from the die (one source, three balanced roots like clk_lane/clk_map), so no cycle changes. k6 had 18,143 sinks
//      on clk (> 15k with no measured tree: textbook REFUSE).
//  (3) rst_n drives only ot_rst_relay__d4g_sfu (4 regions: bridge, engine, W pins, E pins); release +3 clk edges (the static
//      programme starts long after reset; exactness is per transaction). k6 had 13,745 loads on the rst_n port.
// OT_SFU_CORE_MUT_SKIP_REG (bench negative control) as in ot_hgi_sfu_core_split.
module ot_hgi_sfu_core_split2__d4g_sfu #(
 parameter integer LWB=15,
 parameter integer LG_PATH=0,
 // HBM-BANKLAT-SU 10-19: the SFU LG pair tap's READ_RETURN/WRITE_RETURN as bound on the die (ot_hgi_sfu_lg_pair_tap_leaf;
 // 14/11 = zero-lane SU tap + non-pin bank). The bridge expects TAP_RR/TAP_WR + 2*(LG_PATH+1).
 parameter integer TAP_RR=14,
 parameter integer TAP_WR=11
)(
 input wire clk,clk_pw,clk_pe,rst_n,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [470:0] io_word,
 input wire [1741:0] compiler_control,
 output reg [135:0] local_rq,
 input wire [2055:0] local_rr,
 output reg [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [7:0] vi_re_w,vi_re_e,
 output wire [191:0] vi_addr_w,vi_addr_e,
 input wire [255:0] vi_q_w,vi_q_e,
 output reg [7:0] ro_v_w,ro_v_e,
 output wire [7:0] kv_we_w,kv_we_e,
 output reg [255:0] ro_x_w,ro_x_e,
 output wire [255:0] kv_wdata_w,kv_wdata_e,
 output wire [191:0] kv_waddr_w,kv_waddr_e,
 output reg fault
);
 localparam IOW=8+8+128+16+8*LWB+24+96+4+2+2*LWB+32+2+1;
 initial if(LWB!=15 || IOW!=471)$fatal(1,"SFU IO programme ABI requires LWB15");
 wire [3:0] rr;   // 0 bridge, 1 engine, 2 W pins, 3 E pins
 ot_rst_relay__d4g_sfu #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg [470:0] io_r;
 reg [1741:0] ctl_r;
`ifdef OT_SFU_SYNC_RST
 // k8 sync-reset standard: boundary pin registers are pure data stages (no reset; the bridge / engine they feed are
 // held in reset by their own regional relays until these registers carry live values)
 always @(posedge clk_pe) begin io_r<=io_word;ctl_r<=compiler_control;end
`else
 always @(posedge clk_pe `OT_SFU_ARST(rr[3]))
  if(!rr[3])begin io_r<=0;ctl_r<=0;end
  else begin io_r<=io_word;ctl_r<=compiler_control;end
`endif
`ifdef OT_SFU_CORE_MUT_SKIP_REG
 wire [470:0] io=io_word;
 wire [1741:0] control=compiler_control;
`else
 wire [470:0] io=io_r;
 wire [1741:0] control=ctl_r;
`endif
 wire [7:0] prefetch_v,prefetch_scalar;
 wire [127:0] prefetch_sector;
 wire [15:0] prefetch_group;
 wire [119:0] prefetch_local_addr;
 wire [23:0] prefetch_word;
 wire [95:0] scalar_addr;
 wire [3:0] scalar_enable;
 wire [1:0] drain_v,drain_round_bf16;
 wire [29:0] drain_addr;
 wire [31:0] drain_vm_sector;
 wire arithmetic_start_unused;
 assign {arithmetic_start_unused,drain_round_bf16,drain_vm_sector,drain_addr,drain_v,scalar_enable,
         scalar_addr,prefetch_word,prefetch_local_addr,prefetch_group,prefetch_sector,prefetch_scalar,prefetch_v}=io;
 wire [7:0] stage_v;
 wire [15:0] stage_group;
 wire [8*LWB-1:0] stage_addr;
 wire [63:0] stage_mask;
 wire [2047:0] stage_data;
 wire [3:0] scalar_load;
 wire [95:0] scalar_load_addr;
 wire [127:0] scalar_data;
 wire [511:0] drain_data;
 wire [1:0] drain_result_v;
 wire bridge_fault,engine_fault;
 wire [135:0] b_rq;
 wire [2247:0] b_wq;
 reg [2055:0] b_rr;
 reg [7:0] b_wd;
 wire [15:0] e_rov;
 wire [511:0] e_rox;
`ifdef OT_SFU_SYNC_RST
 // k8 sync-reset standard: boundary pin registers are pure data stages (no reset; the bridge / engine they feed are
 // held in reset by their own regional relays until these registers carry live values)
 always @(posedge clk_pw) begin local_rq<=b_rq;local_wq<=b_wq;b_rr<=local_rr;b_wd<=local_w_done;end
`else
 always @(posedge clk_pw `OT_SFU_ARST(rr[2]))
  if(!rr[2])begin local_rq<=0;local_wq<=0;b_rr<=0;b_wd<=0;end
  else begin local_rq<=b_rq;local_wq<=b_wq;b_rr<=local_rr;b_wd<=local_w_done;end
`endif
`ifdef OT_SFU_SYNC_RST
 // k8 sync-reset standard: boundary pin registers are pure data stages (no reset; the bridge / engine they feed are
 // held in reset by their own regional relays until these registers carry live values)
 always @(posedge clk_pe) begin {ro_v_e,ro_v_w}<=e_rov;{ro_x_e,ro_x_w}<=e_rox;end
`else
 always @(posedge clk_pe `OT_SFU_ARST(rr[3]))
  if(!rr[3])begin ro_v_w<=0;ro_v_e<=0;ro_x_w<=0;ro_x_e<=0;end
  else begin {ro_v_e,ro_v_w}<=e_rov;{ro_x_e,ro_x_w}<=e_rox;end
`endif
 localparam integer LGB=LG_PATH+1;
 ot_hgi_sfu_vm_static_bridge__d4g_sfu #(.LWB(LWB),.READ_RETURN(TAP_RR+2*LGB),.WRITE_RETURN(TAP_WR+2*LGB)) u_vm(
 .clk(clk),.rst_n(rr[0]),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),.prefetch_v(prefetch_v),.prefetch_sector(prefetch_sector),.prefetch_group(prefetch_group),
 .prefetch_local_addr(prefetch_local_addr),.prefetch_scalar(prefetch_scalar),.prefetch_word(prefetch_word),.scalar_addr(scalar_addr),
 .local_rq(b_rq),.local_rr(b_rr),.local_wq(b_wq),.local_w_done(b_wd),
 .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
 .scalar_load(scalar_load),.scalar_load_addr(scalar_load_addr),.scalar_data(scalar_data),
 .drain_v(drain_v),.drain_round_bf16(drain_round_bf16),.drain_vm_sector(drain_vm_sector),.drain_result_v(drain_result_v),.drain_data(drain_data),.fault(bridge_fault));
 ot_hgi_sfu_static_engine__d4g_sfu #(.LWB(LWB)) u_engine(
  .clk(clk),.rst_n(rr[1]),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .compiler_control(control),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_load_addr),.scalar_data(scalar_data),
  .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
  .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),
  .vi_re({vi_re_e,vi_re_w}),.vi_addr({vi_addr_e,vi_addr_w}),.vi_q({vi_q_e,vi_q_w}),.ro_v(e_rov),.ro_x(e_rox),
  .kv_we({kv_we_e,kv_we_w}),.kv_waddr({kv_waddr_e,kv_waddr_w}),.kv_wdata({kv_wdata_e,kv_wdata_w}),.fault(engine_fault));
 always @(posedge clk_pe `OT_SFU_ARST(rr[3]))
  if(!rr[3])fault<=0;else if(bridge_fault||engine_fault)fault<=1;
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_core_split3.sv
`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SFU core k9 (H-SU 2026-10-17, coordinator 0co: square-ish ~1,600 x 1,800 cluster, owner rule "no long-thin blocks").
// Pure port re-slicing of ot_hgi_sfu_core_split2__d4g_sfu (no logic, no registers, no edges): the sixteen lane-direct buses are
// split into four face groups so each group of four lane leaves (hard child ot_su12_sfu__d4g_sfu) faces its own block side:
//   _w = lanes 0-3 (W column)   _n = lanes 4-7 (N row)   _e = lanes 8-11 (E column)   _s = lanes 12-15 (S row).
// split2's X_w[k*W +: W] (lane k, k=0..7) -> lanes 0-3 on _w, 4-7 on _n; X_e (lanes 8..15) -> 8-11 on _e, 12-15 on _s.
// Every other port is split2's unchanged (local_* / io_word / compiler_control / clocks / resets / fault).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sfu_core_split3 #(
 parameter integer LWB=15,
 parameter integer LG_PATH=0,
 parameter integer TAP_RR=14,    // HBM-BANKLAT-SU 10-19: = the bound sfu_<q><g> tap READ_RETURN / WRITE_RETURN
 parameter integer TAP_WR=11
)(
 input wire clk,clk_pw,clk_pe,rst_n,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [470:0] io_word,
 input wire [1741:0] compiler_control,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [3:0] vi_re_w,vi_re_n,vi_re_e,vi_re_s,
 output wire [95:0] vi_addr_w,vi_addr_n,vi_addr_e,vi_addr_s,
 input wire [127:0] vi_q_w,vi_q_n,vi_q_e,vi_q_s,
 output wire [3:0] ro_v_w,ro_v_n,ro_v_e,ro_v_s,
 output wire [3:0] kv_we_w,kv_we_n,kv_we_e,kv_we_s,
 output wire [127:0] ro_x_w,ro_x_n,ro_x_e,ro_x_s,
 output wire [127:0] kv_wdata_w,kv_wdata_n,kv_wdata_e,kv_wdata_s,
 output wire [95:0] kv_waddr_w,kv_waddr_n,kv_waddr_e,kv_waddr_s,
 output wire fault
);
 wire [7:0] a_vi_re_w,a_vi_re_e,a_ro_v_w,a_ro_v_e,a_kv_we_w,a_kv_we_e;
 wire [191:0] a_vi_addr_w,a_vi_addr_e,a_kv_waddr_w,a_kv_waddr_e;
 wire [255:0] a_ro_x_w,a_ro_x_e,a_kv_wdata_w,a_kv_wdata_e;
 ot_hgi_sfu_core_split2__d4g_sfu #(.LWB(LWB),.LG_PATH(LG_PATH),.TAP_RR(TAP_RR),.TAP_WR(TAP_WR)) u_core(
  .clk(clk),.clk_pw(clk_pw),.clk_pe(clk_pe),.rst_n(rst_n),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),
  .clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .io_word(io_word),.compiler_control(compiler_control),
  .local_rq(local_rq),.local_rr(local_rr),.local_wq(local_wq),.local_w_done(local_w_done),
  .vi_re_w(a_vi_re_w),.vi_re_e(a_vi_re_e),.vi_addr_w(a_vi_addr_w),.vi_addr_e(a_vi_addr_e),
  .vi_q_w({vi_q_n,vi_q_w}),.vi_q_e({vi_q_s,vi_q_e}),
  .ro_v_w(a_ro_v_w),.ro_v_e(a_ro_v_e),.kv_we_w(a_kv_we_w),.kv_we_e(a_kv_we_e),
  .ro_x_w(a_ro_x_w),.ro_x_e(a_ro_x_e),.kv_wdata_w(a_kv_wdata_w),.kv_wdata_e(a_kv_wdata_e),
  .kv_waddr_w(a_kv_waddr_w),.kv_waddr_e(a_kv_waddr_e),.fault(fault));
 assign {vi_re_n,vi_re_w}=a_vi_re_w;          assign {vi_re_s,vi_re_e}=a_vi_re_e;
 assign {vi_addr_n,vi_addr_w}=a_vi_addr_w;    assign {vi_addr_s,vi_addr_e}=a_vi_addr_e;
 assign {ro_v_n,ro_v_w}=a_ro_v_w;             assign {ro_v_s,ro_v_e}=a_ro_v_e;
 assign {kv_we_n,kv_we_w}=a_kv_we_w;          assign {kv_we_s,kv_we_e}=a_kv_we_e;
 assign {ro_x_n,ro_x_w}=a_ro_x_w;             assign {ro_x_s,ro_x_e}=a_ro_x_e;
 assign {kv_wdata_n,kv_wdata_w}=a_kv_wdata_w; assign {kv_wdata_s,kv_wdata_e}=a_kv_wdata_e;
 assign {kv_waddr_n,kv_waddr_w}=a_kv_waddr_w; assign {kv_waddr_s,kv_waddr_e}=a_kv_waddr_e;
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_lane_map.sv
`timescale 1ns/1ps
`default_nettype none
// Adapter for CLOSED ot_su12_sfu__d4g_sfu, whose lane index is physically fixed at5.
// Four registered edges; native broadcast/retirement must price and bind them.
module ot_hgi_sfu_lane_map__d4g_sfu #(parameter integer MUT_LANE=0) (
 input wire clk, rst_n,
 input wire [3:0] lane_j,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output reg [1199:0] o_ld_c,
 output reg [23:0] o_o_v, o_i_v, o_krow,
 output reg [3:0] o_ls, o_lvw,
 output reg o_emit,
 output wire [460:0] o_pass
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 reg [479:0] terms0;
 reg [23:0] ov0,iv0,row0;
 reg [3:0] ls0,lvw0,j0;
 reg emit0,emit1,emit2;
 reg [79:0] meta1,meta2;
 // ld is control, not retained payload: reset must not replay a ring slot.
 reg [3:0] ld_pipe;
 ot_hdc_delay_ring__d4g_sfu #(.W(460),.D(4),.RING(3)) u_pass (.clk(clk),.rst_n(rst_n),.d(i_pass[459:0]),.q(o_pass[459:0]));
 assign o_pass[460]=ld_pipe[3];
 reg [23:0] term1[0:19],pair2[0:9];
 always @(posedge clk) begin
  terms0<=ld_terms; ov0<=i_o_v; iv0<=i_i_v; row0<=i_krow;
  ls0<=i_ls; lvw0<=i_lvw; j0<=lane_j ^ 4'(MUT_LANE);
  // All integer expressions wrap at24 bits, as the frozen lane's kadd.
  meta1<={24'(ov0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          24'(iv0 + (24'(j0)&((24'd1<<ls0)-1)) - (24'd5&((24'd1<<ls0)-1))),
          24'(row0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          ls0,(lvw0<3 ? 4'd3 : lvw0)};
  meta2<=meta1;
  {o_o_v,o_i_v,o_krow,o_ls,o_lvw}<=meta2;
  for(integer s=0;s<5;s=s+1) begin
   for(integer k=0;k<4;k=k+1)
    term1[s*4+k]<=j0[k] ? terms0[(s*4+k)*24+:24] : 24'd0;
   pair2[s*2]<=term1[s*4]+term1[s*4+1];
   pair2[s*2+1]<=term1[s*4+2]+term1[s*4+3];
   o_ld_c[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
  end
  if(!f_rst) begin emit0<=0;emit1<=0;emit2<=0;o_emit<=0;ld_pipe<=0;end
  else begin emit0<=i_emit;emit1<=emit0 && (24'(j0)<(24'd1<<lvw0));emit2<=emit1;o_emit<=emit2;ld_pipe<={ld_pipe[2:0],i_pass[460]};end
 end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_engine.sv
`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay__d4g_sfu /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Actual sixteen-lane arithmetic joined to its mapped operand/output store.
// VM sector arrivals and drains are compiler slots; preload completes BEFORE
// arithmetic launch. The compiler prices the VM tap's14 edges separately from
// the local SRAM word-read edge. No combinational14-to1 latency substitution.
// Index ports require a separate actual mapped service. The inherited side
// pins are reserved: KIND1 lanes do not implement scalar-side classes; those
// opcodes fault and must dispatch through a real full-lane/side engine.
module ot_hgi_sfu_static_engine__d4g_sfu #(parameter integer LWB=15)(
 input wire clk,rst_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [1741:0] compiler_control,
 input wire [3:0] scalar_load,scalar_enable,
 input wire [95:0] scalar_addr,
 input wire [127:0] scalar_data,
 input wire [7:0] stage_v,
 input wire [15:0] stage_group,
 input wire [8*LWB-1:0] stage_addr,
 input wire [63:0] stage_mask,
 input wire [2047:0] stage_data,
 input wire [1:0] drain_v,
 input wire [2*LWB-1:0] drain_addr,
 output wire [511:0] drain_data,
 output wire [1:0] drain_result_v,
 output wire [15:0] vi_re,
 output wire [383:0] vi_addr,
 input wire [511:0] vi_q,
 output wire [15:0] ro_v,kv_we,
 output wire [511:0] ro_x,kv_wdata,
 output wire [383:0] kv_waddr,
 output reg fault
);
 // side_v/side_x/side_y REMOVED (H-NETLIST/suport 2026-10-16, H-SU agreed): ot_su12_sfu__d4g_sfu binds its lane with .side_v(), .side_x(),
 // .side_y(32'd0) (rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv:152), so these pins were undriven / ignored; KIND1 side
 // opcodes still fault (ot_hgi_sfu_static_engine__d4g_sfu).
 wire [63:0] rd_re;
 wire [1535:0] rd_addr;
 wire [127:0] rd_src;
 wire [2047:0] rd_q;
 wire [15:0] vm_we,lane_fault,lane_coll;
 wire [383:0] vm_addr;
 wire [511:0] vm_data;
 wire store_fault;
 ot_hgi_sfu_static_quarter__d4g_sfu u_arithmetic(
  .clk_control(clk),.rst_control_n(rst_n),.compiler_control(compiler_control),
  .clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .vi_q(vi_q),.rd_q(rd_q),.vi_re(vi_re),.vi_addr(vi_addr),
  .rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),
  .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.ro_v(ro_v),.ro_x(ro_x),
  .fault(lane_fault),.coll(lane_coll));
 ot_hgi_sfu_static_operand_store__d4g_sfu #(.LWB(LWB)) u_memory(
  .clk(clk),.rst_n(rst_n),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(rd_q),
  .vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),
  .scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_addr),.scalar_data(scalar_data),
  .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
  .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),.fault(store_fault));
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)fault<=0;
  else if(store_fault || |lane_fault || |lane_coll ||
   (compiler_control[77:75]!=0 && compiler_control[77:75]!=1 && compiler_control[77:75]!=4 && compiler_control[77:75]!=5) ||
   (compiler_control[74:72]!=0 && compiler_control[74:72]!=1 && compiler_control[74:72]!=4 && compiler_control[74:72]!=5))fault<=1;
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv
`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay__d4g_sfu /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Compiler-prefetched operand store for the actual sixteen-lane SFU.
// Four independent operand groups and one output group, each with sixteen
// interleaved physical banks. No issue/return queues, credits or leases.
// Eight arriving sectors can fill all four operand groups at two sectors per
// group per edge. A conflicting same-bank write is an error, never a retry.
// Index/gather memory and non-VM sources are NOT aliased onto these operands.
// The separate engine index port must receive its own actual mapped service.
module ot_hgi_sfu_static_operand_store__d4g_sfu #(
 parameter integer LWB=15, MUT_XBAR=0
)(
 input wire clk,rst_n,
 input wire [3:0] scalar_load,scalar_enable,
 input wire [95:0] scalar_addr,
 input wire [127:0] scalar_data,
 input wire [63:0] rd_re,
 input wire [1535:0] rd_addr,
 input wire [127:0] rd_src,
 output wire [2047:0] rd_q,
 input wire [15:0] vm_we,
 input wire [383:0] vm_waddr,
 input wire [511:0] vm_wdata,
 input wire [7:0] stage_v,
 input wire [15:0] stage_group,
 input wire [8*LWB-1:0] stage_addr,
 input wire [63:0] stage_mask,
 input wire [2047:0] stage_data,
 input wire [1:0] drain_v,
 input wire [2*LWB-1:0] drain_addr,
 output wire [511:0] drain_data,
 output wire [1:0] drain_result_v,
 output reg fault
);
 generate if(LWB<14 || LWB>17)begin:g_bad_size
  ot_sfu_store_requires_actual_supported_SRAM_geometry u_refuse();
 end endgenerate
 wire [4:0] group_fault;
 reg [23:0] scalar_addr_q[0:3];
 reg [31:0] scalar_data_q[0:3];
 reg [3:0] scalar_valid;
 reg scalar_bad;
 always @(posedge clk)for(integer g=0;g<4;g=g+1)
  if(scalar_load[g])begin scalar_addr_q[g]<=scalar_addr[24*g+:24];scalar_data_q[g]<=scalar_data[32*g+:32];end
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)scalar_valid<=0;else scalar_valid<=scalar_valid|scalar_load;
 always @*begin
  scalar_bad=0;
  for(integer l=0;l<16;l=l+1)for(integer g=0;g<4;g=g+1)
   if(rd_re[4*l+g] && scalar_enable[g] &&
    (!scalar_valid[g] || rd_addr[24*(4*l+g)+:24]!=scalar_addr_q[g]))scalar_bad=1;
 end
 reg bad_source,bad_range;
 always @*begin
  bad_source=0;bad_range=0;
  for(integer l=0;l<16;l=l+1)begin
   if(vm_we[l] && |vm_waddr[24*l+LWB+:24-LWB])bad_range=1;
   for(integer g=0;g<4;g=g+1)
    if(rd_re[4*l+g] && !scalar_enable[g] && |rd_addr[24*(4*l+g)+LWB+:24-LWB])bad_range=1;
  end
  for(integer b=0;b<8;b=b+1)
   if(stage_v[b] && stage_addr[LWB*b+:LWB]>{LWB{1'b1}}-7)bad_range=1;
  for(integer b=0;b<2;b=b+1)
   if(drain_v[b] && drain_addr[LWB*b+:LWB]>{LWB{1'b1}}-7)bad_range=1;
  for(integer l=0;l<16;l=l+1)
   for(integer s=0;s<4;s=s+1)
    if(rd_re[4*l+s] && rd_src[8*l+2*s+:2]!=0)bad_source=1;
 end
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)fault<=0;
  else if(bad_source || bad_range || scalar_bad || |group_fault)fault<=1;
 for(genvar g=0;g<4;g=g+1)begin:g_operand
  wire [15:0] req;
  wire [383:0] addr;
  wire [511:0] data;
  reg [511:0] scalar_read;
  reg scalar_selected;
  always @(posedge clk)begin
   scalar_selected<=scalar_enable[g];
   for(integer l=0;l<16;l=l+1)if(rd_re[4*l+g] && scalar_enable[g])scalar_read[32*l+:32]<=scalar_data_q[g];
  end
  wire [7:0] sw;
  for(genvar l=0;l<16;l=l+1)begin:g_lane
   assign req[l]=rd_re[4*l+g] && rd_src[8*l+2*g+:2]==0 && !scalar_enable[g];
   assign addr[24*l+:24]=rd_addr[(4*l+g)*24+:24];
   assign rd_q[(4*l+g)*32+:32]=scalar_selected?scalar_read[32*l+:32]:data[32*l+:32];
  end
  for(genvar b=0;b<8;b=b+1)begin:g_stage
   assign sw[b]=stage_v[b] && stage_group[2*b+:2]==g;
  end
  ot_hgi_su_lgroup2__d4g_sfu #(.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(0),
   .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(8)) u_group(
   .clk(clk),.rst_n(rst_n),.rq(req),.rr(req),.ra(addr),.rd(data),
   .sr_v(8'd0),.sr_addr({8*LWB{1'b0}}),.sr_d(),.sr_rv(),
   .sw_v(sw),.sw_addr(stage_addr),.sw_mask(stage_mask),.sw_d(stage_data),
   .lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
   .flt(group_fault[g]));
 end
 ot_hgi_su_lgroup2__d4g_sfu #(.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(16),
  .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(2)) u_output(
  .clk(clk),.rst_n(rst_n),.rq(16'd0),.rr(16'd0),.ra(384'd0),.rd(),
  .sr_v(drain_v),.sr_addr(drain_addr),.sr_d(drain_data),.sr_rv(drain_result_v),
  .sw_v(2'd0),.sw_addr({2*LWB{1'b0}}),.sw_mask(16'd0),.sw_d(512'd0),
  .lw(vm_we),.lwa(vm_waddr),.lwd(vm_wdata),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
  .flt(group_fault[4]));
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv
`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay__d4g_sfu /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Compiler-issued SFU arithmetic. The 1742-bit control word is the explicit
// lane-grid ABI (see ot_hgi_sfu_arithmetic_grid__d4g_sfu), not an instruction FIFO.
// Every edge is consumed; there is no ready, credit, lease, or issue retry.
// A zero word is a bubble. The compiler must preload operand memory and price
// the input register (one edge), mapper (four), and selected arithmetic pipes.
// Reduction results are exposed for an external compiler-scheduled reducer;
// this block does not silently implement the old dynamic reduction controller.
module ot_hgi_sfu_static_quarter__d4g_sfu #(
 parameter integer BTREE=0
)(
 input wire clk_control,rst_control_n,
 input wire [1741:0] compiler_control,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [511:0] vi_q,
 input wire [2047:0] rd_q,
 output wire [15:0] vi_re,vm_we,kv_we,ro_v,fault,coll,
 output wire [383:0] vi_addr,vm_waddr,kv_waddr,
 output wire [1535:0] rd_addr,
 output wire [63:0] rd_re,
 output wire [127:0] rd_src,
 output wire [511:0] vm_wdata,kv_wdata,ro_x
);
 reg [1741:0] control;
 always @(posedge clk_control `OT_SFU_ARST(rst_control_n))
  if(!rst_control_n)control<=0;else control<=compiler_control;
`ifdef OT_SFU_STATIC_PHASE_MUTANT
 reg [1741:0] late;
 always @(posedge clk_control `OT_SFU_ARST(rst_control_n))
  if(!rst_control_n)late<=0;else late<=control;
 wire [1741:0] grid_control=late;
`else
 wire [1741:0] grid_control=control;
`endif
 ot_hgi_sfu_arithmetic_grid__d4g_sfu #(.BTREE(BTREE)) u_grid(
 .clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
 .control(grid_control),.vi_q(vi_q),.rd_q(rd_q),
 .vi_re(vi_re),.vm_we(vm_we),.kv_we(kv_we),.ro_v(ro_v),.fault(fault),.coll(coll),
 .vi_addr(vi_addr),.vm_waddr(vm_waddr),.kv_waddr(kv_waddr),.rd_addr(rd_addr),.rd_re(rd_re),
 .rd_src(rd_src),.vm_wdata(vm_wdata),.kv_wdata(kv_wdata),.ro_x(ro_x));
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_sfu_vm_static_bridge.sv
`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay__d4g_sfu /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Fixed-cycle SFU VM prefetch/drain bridge. Requests and selectors come from
// an actual compiler programme. No request FIFO, credits, leases or retries.
// Mid-tap READ_RETURN14 is measured at response pins after edge n+14 for a
// request captured n; SRAM/scalar store consumes the response at n+15.
// The metadata delay crosses exactly those14 response edges alongside data.
module ot_hgi_sfu_vm_static_bridge__d4g_sfu #(
 parameter integer LWB=15, READ_RETURN=14, WRITE_RETURN=11
)(
 input wire clk,rst_n,
 // Four related, same-frequency clock roots, one for each physical bank pair.
 // They are not asynchronous domains: no CDC FIFO or extra service edge.
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [7:0] prefetch_v,
 input wire [127:0] prefetch_sector,
 input wire [15:0] prefetch_group,
 input wire [8*LWB-1:0] prefetch_local_addr,
 input wire [7:0] prefetch_scalar,
 input wire [23:0] prefetch_word,
 input wire [95:0] scalar_addr,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [7:0] stage_v,
 output wire [15:0] stage_group,
 output wire [8*LWB-1:0] stage_addr,
 output wire [2047:0] stage_data,
 output wire [63:0] stage_mask,
 output reg [3:0] scalar_load,
 output wire [95:0] scalar_load_addr,
 output reg [127:0] scalar_data,
 input wire [1:0] drain_v,drain_round_bf16,
 input wire [31:0] drain_vm_sector,
 input wire [1:0] drain_result_v,
 input wire [511:0] drain_data,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output reg fault
);
 localparam META=2+4+2*LWB+2+6;
 wire [7:0] expect_v,scalar;
 wire [23:0] word_sel;
 wire [3:0] group_fault;
 // Scalar addresses belong to the programme, independent of the VM bank.
 reg [95:0] scalar_addr_pipe[0:READ_RETURN];
 assign scalar_load_addr=scalar_addr_pipe[READ_RETURN];
 assign stage_v=expect_v&~scalar;
 assign stage_mask=64'hffffffffffffffff;
 for(genvar b=0;b<8;b=b+1)begin:g_read
  assign local_rq[b*17+:17]={prefetch_v[b],prefetch_sector[b*16+:16]};
  assign stage_data[b*256+:256]=local_rr[b*257+:256];
 end
 reg scalar_collision;
 reg [3:0] used_group;
 always @*begin
  scalar_load=0;scalar_data=0;used_group=0;scalar_collision=0;
  for(integer b=0;b<8;b=b+1)if(expect_v[b]&&scalar[b])begin
   if(used_group[stage_group[2*b+:2]])scalar_collision=1;
   used_group[stage_group[2*b+:2]]=1;
   scalar_load[stage_group[2*b+:2]]=1;
   scalar_data[32*stage_group[2*b+:2]+:32]=local_rr[257*b+32*word_sel[3*b+:3]+:32];
  end
 end
 function automatic [255:0] round_sector(input [255:0] data,input do_round);
  reg [31:0] word,rounded;
  for(integer w=0;w<8;w=w+1)begin
   word=data[32*w+:32];
`ifdef OT_SFU_VM_BF16_MUTANT
   rounded=word+32'h00007fff; // true negative: ties with odd high word round the wrong way
`else
   rounded=word+32'h00007fff+{31'd0,word[16]};
`endif
   round_sector[32*w+:32]=do_round?{rounded[31:16],16'd0}:word;
  end
 endfunction
 // Actual state partition: each root owns only its two banks' metadata,
 // request checks, write output flops and fixed completion observers.
 // The programme and operand store remain on clk. Their related-clock
 // crossings require the die clock/pin plan; this is not a reach waiver.
 for(genvar g=0;g<4;g=g+1)begin:g_lg
  reg [META-1:0] meta[0:READ_RETURN];
  reg [561:0] write_q;
  assign local_wq[562*g+:562]=write_q;
  assign {expect_v[2*g+:2],stage_group[4*g+:4],stage_addr[2*LWB*g+:2*LWB],
          scalar[2*g+:2],word_sel[6*g+:6]}=meta[READ_RETURN];
  reg [1:0] drain_round_q,drain_expected;
  reg [31:0] drain_sector_q;
  reg [1:0] write_expected[0:WRITE_RETURN+1];
  reg [1:0] write_v;
  reg write_collision;
  reg fault_q;
  assign group_fault[g]=fault_q;
  always @*begin
   write_v=0;write_collision=0;
   for(integer s=0;s<2;s=s+1)
    if(drain_expected[s] && drain_sector_q[16*s+1+:2]==g)begin
     if(write_v[drain_sector_q[16*s]])write_collision=1;
     write_v[drain_sector_q[16*s]]=1;
    end
  end
  always @(posedge clk_lg[g])begin
   drain_sector_q<=drain_vm_sector;drain_round_q<=drain_round_bf16;
   write_q<=0;
   for(integer s=0;s<2;s=s+1)
    if(drain_expected[s] && drain_sector_q[16*s+1+:2]==g)
     write_q[281*drain_sector_q[16*s]+:281]<=
      {1'b1,drain_sector_q[16*s+:16],round_sector(drain_data[256*s+:256],drain_round_q[s]),8'hff};
  end
  always @(posedge clk_lg[g] `OT_SFU_ARST(rst_lg_n[g]))begin
   if(!rst_lg_n[g])begin
    fault_q<=0;drain_expected<=0;
    for(integer i=0;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=0;
    for(integer i=0;i<=READ_RETURN;i=i+1)meta[i]<=0;
   end else begin
    meta[0]<={prefetch_v[2*g+:2],prefetch_group[4*g+:4],prefetch_local_addr[2*LWB*g+:2*LWB],
              prefetch_scalar[2*g+:2],prefetch_word[6*g+:6]};
    for(integer i=1;i<=READ_RETURN;i=i+1)meta[i]<=meta[i-1];
    drain_expected<=drain_v;
    write_expected[0]<=write_v;
    for(integer i=1;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=write_expected[i-1];
    for(integer b=0;b<2;b=b+1)begin
     if(prefetch_v[2*g+b]&&prefetch_sector[16*(2*g+b)+:3]!=(2*g+b))fault_q<=1;
     if(expect_v[2*g+b]!=local_rr[(2*g+b)*257+256])fault_q<=1;
     if(write_expected[WRITE_RETURN+1][b]!=local_w_done[2*g+b])fault_q<=1;
    end
    if(drain_result_v!=drain_expected || write_collision)fault_q<=1;
   end
  end
 end
 always @(posedge clk `OT_SFU_ARST(rst_n))begin
  if(!rst_n)begin
   fault<=0;
   for(integer i=0;i<=READ_RETURN;i=i+1)scalar_addr_pipe[i]<=0;
  end else begin
   scalar_addr_pipe[0]<=scalar_addr;
   for(integer i=1;i<=READ_RETURN;i=i+1)scalar_addr_pipe[i]<=scalar_addr_pipe[i-1];
   if(|group_fault || scalar_collision)fault<=1;
  end
 end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
`timescale 1ns/1ps
`default_nettype none
`ifndef OT_SU_C12_RSLICE
`define OT_SU_C12_RSLICE 64
`endif
`ifndef OT_SU_C12_DENR
`define OT_SU_C12_DENR 1
`endif
`ifndef OT_SU_C12_SFUT
`define OT_SU_C12_SFUT 0
`endif
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 stream-unit die body (hgi-adapters, 2026-10-09) on the D1 memory model (spec 2.4 "How engines reach VM",
// main aeac6fa40): record -> ot_hgi_su_record (decode) -> STAGE the op's VM operands into the unit's local fixed-latency
// operand memory -> the unchanged stream unit ot_hdc_v41x_vec runs on local addresses -> DRAIN the words it wrote back to
// VM -> retire.  VM is reached only through ONE hfd_hgi_vm packet client (up to 4 requests outstanding, in-order
// responses: ot_hgi_vm_unit fast path).
//   stage: per operand the op reads (A always; B, C, D by the template; c_pair widens A by its pair word) the span
//     [lo, hi] = [base, base + (no - 1) so + (ni' - 1) si] (ni' = ceil(ni / 2) for b_half B / D) is copied sector by
//     sector into a local region placed at lb (lb = lo mod 8: sector to sector); the op word's bases are relocated
//     (base - lo + lb), strides unchanged, so the unit's address arithmetic is untouched;
//   drain: O (dst VM) and R (red) are local regions too; every word the unit writes (element writes and reducer results)
//     sets a dirty bit, and the drain writes each dirty sector back with its word mask, so words the op did not write are
//     never touched in VM (no read-modify-write of neighbours);
//   ordering: one record at a time in the unit (spec 4.1); the record retires when its last drain write is acknowledged.
//   Copies have exactly the golden's semantics (Machine.su1 reads every operand before it writes any result).
// Refusals (record fault): a gather (a_ind != 0: its span depends on the id table), a stream source / sink (STREAM is the
//   stream-port successor), an operand set larger than one local region set (LW words).
// Local memory: LW words (behavioural here; on the die the unit's r25 operand macros).  Single region set in v1; the
//   double-buffered successor stages record k+1 while record k computes when k+1 reads nothing k writes.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_ctl__d4g_sfu #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,           // log2 local words (the Qwen head: 37,984 B + O + the stream region)
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,            // 1: the SFU die body (SFU.GLU records; ot_hgi_su_record GLU mode)
    parameter integer SLB = 16,           // log2 words of the stream-0 landing region (top of the local memory)
    parameter integer MUT_DIRTY = 0,      // mutant: drain whole sectors (overwrites words the op did not write)
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB,   // local memory group sizes (log2 words; G0 = LWB)
    parameter integer LGO = LWB, RWB = 6,                 // the O group, the reducer-result file
    // FILL-9 (2026-10-10) opt-in timing structure, both default 0 (historical elaboration); -D flips them for benches.
    // RST_RELAY 1: the rst_n port drives only rtl/lib/ot_rst_relay__d4g_sfu (async assert, release 3 edges later; regions 0 record
    // adapter, 1 controller, 2 engine-status / return pins); rec_rdy is held low until region 0 has left reset.
    parameter integer RST_RELAY = `ifdef OT_SU_RST_RELAY 1 `else 0 `endif,
    // PRE_PIPE 1: the op-level layout (pow2ceil slot, row width) and no x ni are computed over 3 registered phases of
    // S_PRE instead of one edge (routed worst path: w -> 16x16 multiply / pow2ceil ripple -> compare; +2 cycles an op)
    parameter integer PRE_PIPE = `ifdef OT_SU_PRE_PIPE 1 `else 0 `endif
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    // STREAM 0 (SM -> SU): element idx of the stream (slot x M + row) and its value; lands in the stream region
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    // STREAM to ARGMAX (the 523-b su_red stream: {bias_en, bias 256, vals 256, mask 8, last, v}); am_rdy = the argmax
    // unit holds a STREAM record (it consumes every beat once busy)
    output reg  [522:0]  am_stream,
    input  wire          am_rdy,
    // the stream unit (ot_hdc_v41x_vec): go / ready / idle / fault, the relocated op word
    output reg           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output reg  [669:0]  wl,
    // the local memory (ot_hgi_su_lmem__d4g_sfu; on the die the r25 operand macros): every port registered here
    output reg           sl_v,                // a STREAM 0 word lands
    output reg  [LWB-1:0] sl_addr,
    output reg  [31:0]   sl_data,
    output reg           sw_v,                // staged words (up to 8 consecutive local words)
    output reg  [255:0]  sw_data,
    output reg  [3:0]    sw_g,                // the groups the staged words land in (A + C for c_pair)
    output reg  [LWB-1:0] sw_addr,            // local word address of word 0 of the 8 (any alignment)
    output reg  [7:0]    sw_mask,             // the words written
    output reg           sr_v,                // read 8 consecutive words of a group (any alignment)
    output reg  [1:0]    sr_g,                // 1 = O, 2 = R
    output reg  [LWB-1:0] sr_addr,
    input  wire [255:0]  sr_data,
    input  wire          sr_rv,               // sr_data valid (the memory's response; reads return in order)
    output reg  [3:0]    use_p,               // the op's read ports in use (A, B, C or c_pair, D)
    input  wire          sl_pend,             // STREAM landing words still queued in the memory
    output wire          a_str,               // the op's A is the STREAM region
    input  wire          cfault               // memory bank conflict / overflow (sticky): fail closed
);
    localparam integer AW = 24, NR = N / 8, LW = 1 << LWB;
    // ---- the record adapter (decode) and the op it issues
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r;
    wire [1:0] strm;
    // ---- reset (RST_RELAY): region 0 the record adapter, 1 the controller, 2 the engine-status / return pin flops
    wire [2:0] rr; wire rec_rdy_rec;
    generate if (RST_RELAY) begin : g_rr
        ot_rst_relay__d4g_sfu #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
        assign rec_rdy = rec_rdy_rec && rr[0];
    end else begin : g_rr_port
        assign rr = {3{rst_n}};
        assign rec_rdy = rec_rdy_rec;
    end endgenerate
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET)) u_rec (.clk(clk), .rst_n(rr[0]), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy_rec),
        .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o),
        .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .drained(), .op_strm(strm), .lg_v(1'b0), .lg_rdy(), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w),
        .su_idle(su_idle_r), .su_fault(su_fault_r));
    // ---- the op word (PFIELDS) fields
    reg [669:0] w;
    wire [15:0] no = w[0 +: 16], ni = w[16 +: 16];
    wire [1:0]  aind = w[136 +: 2], dst = w[380 +: 2], red = w[478 +: 2];
    wire        bhalf = w[210], cpair = w[283], redwhole = w[481], redtree = w[482];
    wire [2:0]  m1 = w[360 +: 3], qm = w[365 +: 3], ad = w[368 +: 3], e1 = w[374 +: 3];
    wire [1:0]  m2 = w[363 +: 2], e2 = w[377 +: 2];
    wire use_b = (m1 == 3'd1) || (m1 == 3'd4) || (m1 == 3'd6) || (ad == 3'd3) || (e2 == 2'd1);
    wire use_c = !cpair && ((m2 == 2'd1) || (qm != 3'd0) || (ad == 3'd1) || (ad == 3'd2) || (e1 == 3'd1) || (e1 == 3'd2));
    wire use_d = (qm != 3'd0) || (ad == 3'd5);
    // region k: 0 A, 1 B, 2 C, 3 D (sources), 4 O, 5 R (sinks); base / so / si offsets in the word
    reg [2:0] rk;                                         // region walk
    reg [23:0] base_k, so_k, si_k; reg [15:0] nr_k, ni_k; reg used_k; reg hf_k;
    always @* begin
        case (rk)
            3'd0: begin base_k = w[40 +: 24];  so_k = w[64 +: 24];  si_k = w[88 +: 24];  used_k = 1'b1; end
            3'd1: begin base_k = w[138 +: 24]; so_k = w[162 +: 24]; si_k = w[186 +: 24]; used_k = use_b; end
            3'd2: begin base_k = w[211 +: 24]; so_k = w[235 +: 24]; si_k = w[259 +: 24]; used_k = use_c; end
            3'd3: begin base_k = w[284 +: 24]; so_k = w[308 +: 24]; si_k = w[332 +: 24]; used_k = use_d; end
            3'd4: begin base_k = w[382 +: 24]; so_k = w[406 +: 24]; si_k = w[430 +: 24]; used_k = (dst == 2'd1); end
            default: begin base_k = w[484 +: 24]; so_k = w[508 +: 24]; si_k = 24'd0; used_k = (red != 2'd0); end
        endcase
        hf_k = bhalf && (rk == 3'd1 || rk == 3'd3);
        nr_k = (rk == 3'd5) ? ((redwhole || redtree) ? 16'd1 : no) : no;
        ni_k = (rk == 3'd5) ? 16'd1 : (hf_k ? ((ni + 16'd1) >> 1) : ni);          // words a row
    end
    // ---- DENSE RELAYOUT (hgi-1010/d, the lane-local memory): every region is copied to an N-aligned base with element
    //      (o, i) at base + o L + i (inner stride 1; broadcast operands replicated), L chosen so the vec's lanes fall on
    //      their own banks (or the few fixed partners the memory's network serves):
    //        an op the vec flattens (no per-row reduction, no gather / KV-T, even width for half / ALT ops): L = the row
    //        width (all rows contiguous: the vec runs one row, vectors at multiples of its width VW);
    //        otherwise L = the vec's slot S (packed rows, ni <= S) or roundup(ni, N) (spanning rows);
    //        S = min(VW, pow2ceil(max(ni, 8 if reducing else 1))), VW = 1 (scalar class) / M (SFU class) / N (ot_hdc_v41x_vec)
    //      the op word's base / row stride / inner stride name the local layout (inner stride 1); STREAM A / O keep the
    //      contiguous stream layout (rows of ni).  R (one word a row) is dense in the result file.
    function automatic [LWB:0] p2c(input [15:0] x);      // pow2ceil(x), x >= 1
        integer b2; p2c = 1;
        for (b2 = 0; b2 < 16; b2 = b2 + 1) if (p2c < x) p2c = p2c << 1;
    endfunction
    wire [2:0] sfu = w[371 +: 3];
    wire scalar_c = (sfu == 3'd2) || (sfu == 3'd3) || (sfu == 3'd6) || (sfu == 3'd7);
    wire sfu_c = (sfu == 3'd1) || (sfu == 3'd4) || (sfu == 3'd5) || (m1 == 3'd4) || (m1 == 3'd5);
    wire [15:0] vw = scalar_c ? 16'd1 : sfu_c ? M : N;
    wire red_on = (red != 2'd0);
    wire flatc = (!red_on || redwhole || redtree) && (aind == 2'd0) && (dst != 2'd3) &&
                 (!ni[0] || !(bhalf || qm == 3'd3 || qm == 3'd4));
    wire [LWB:0] s_el0 = p2c((ni > (red_on ? 16'd8 : 16'd1)) ? ni : (red_on ? 16'd8 : 16'd1));
    wire [LWB:0] s_el = (s_el0 > vw) ? vw : s_el0;
    wire [LWB:0] l_el = flatc ? ni : (ni <= s_el) ? s_el : ((ni + N - 1) & ~(N - 1));
    // (hgi-1010/c timing: the op-level layout is registered once per op in S_PRE; regions then mux registers only)
    reg [LWB:0] l_full_q, l_half_q; reg [31:0] nn_q;
    wire [LWB:0] L_k = (rk == 3'd5) ? 1 : hf_k ? l_half_q : l_full_q;
    // ---- per region state
    reg [23:0] lo [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [LWB:0] Lr [0:5]; reg [23:0] sor [0:5], sir [0:5];
    reg [15:0] nrr [0:5], nir [0:5]; reg [LWB:0] lsz [0:5];
    reg [39:0] macc; reg [4:0] mbit; reg [1:0] mph;        // (nr - 1) L + nw by shift-add
    // ---- VM traffic
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [2:0] outst; reg [26:0] q_sec [0:3]; reg [1:0] q_h, q_t;  // outstanding requests, in order
    // per request: how its response lands: 0 run (the sector's words in [q_lo, q_hi] at word + q_off), 1 rep (word q_w
    // replicated over q_msk at q_la), 2 elem (word q_w at q_la)
    reg [1:0] q_md [0:3]; reg [2:0] q_w [0:3]; reg [7:0] q_msk [0:3]; reg [LWB-1:0] q_la [0:3];
    reg [23:0] q_lo [0:3], q_hi [0:3]; reg [25:0] q_off [0:3];
    // staging cursor: row, VM row base, local row base, element (word) index, the run mode's sector walk
    reg [15:0] s_rows, s_j; reg [23:0] s_rb, s_va; reg [LWB:0] s_lr; reg [26:0] cur_sec, end_sec; reg [1:0] s_md;
    reg [3:0] st;
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_RUN = 6, S_RUNW = 7,
                     S_DRAIN = 8, S_DRW = 9, S_DONE = 10, S_FAULT = 11, S_SOUT = 12, S_PRE = 13, S_NX1 = 14, S_NX2 = 15;
    // registered region operands (hgi-1010/c timing): the multiply's shift registers, the placement, the stage cursor
    reg [15:0] nrm1_s; reg [39:0] lsh_s; reg [15:0] nw_s; reg [2:0] gk_s; reg [LWB:0] lbk_s, gend_s, gsz_s, gsz2_s;
    reg [23:0] c_so, c_si; reg [15:0] c_nw; reg [LWB:0] c_L;
    reg [2:0] dk;                                         // drain region (4 O, 5 R)
    reg [26:0] rsec_d, rsec_d2, rsec_d3; reg so_w;
    reg [3:0] rp;                                         // read pipe
    reg [255:0] sr_data_q; reg sr_rv_q;
    always @(posedge clk) sr_data_q <= sr_data;
    always @(posedge clk or negedge rr[2]) if (!rr[2]) sr_rv_q <= 1'b0; else sr_rv_q <= sr_rv;
    // drain reads in flight: {VM sector, word mask} of each issued read, popped by its response (valid-driven, any
    // memory latency; hgi-1010/d exactness audit: no reader counts edges)
    reg [34:0] df [0:3]; reg [1:0] df_h, df_t; reg [2:0] nf;
    reg cfault_q; always @(posedge clk) cfault_q <= cfault;
    // ---- allocation: G0 A, G1 B, G2 C (+ A's copy for c_pair), G3 D, G4 O, G5 R (the result file)
    reg [LWB:0] galloc [0:5];
    // ---- drain walker: the O / R shape; local and VM cursors
    reg [15:0] d_row, d_rem, d_ni; reg [23:0] d_cur, d_rowb, d_so, d_si; reg d_run, d_live;
    reg [LWB:0] d_lcur, d_lrow, d_L;
    reg [7:0] mk_d, mk_d2, mk_d3;
    // ---- STREAM 0 landing (the GS region, addresses SBASE..) and the op's stream flags
    localparam integer SW = 1 << SLB;
    localparam [LWB:0] SBASE = LW - SW;
    function automatic [LWB:0] gsz(input [2:0] g);
        case (g) 3'd0: gsz = SBASE; 3'd1: gsz = 1 << LG1; 3'd2: gsz = 1 << LG2; 3'd3: gsz = 1 << LG3; 3'd4: gsz = 1 << LGO;
                 default: gsz = 1 << RWB; endcase
    endfunction
    reg [20:0] scount; reg a_s, o_s; reg s_clr;
    assign a_str = a_s;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot; reg [20:0] ebeat; reg [LWB:0] o_lb; reg amr_q;
    always @(posedge clk) amr_q <= am_rdy;
    reg ready_q, idle_q, vfault_q;
    always @(posedge clk or negedge rr[2]) begin
        if (!rr[2]) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; end
    end
    reg vf_seen; reg [1:0] idle_ph;
    // PRE_PIPE: the op layout over 3 phases (pre_ph), every phase register to register
    function automatic [LWB:0] p2c_f(input [LWB:0] x);  // pow2ceil(x), x >= 1: smear(x - 1) + 1 (log depth)
        reg [LWB:0] y; integer b3;
        y = x - 1;
        for (b3 = 1; b3 <= LWB; b3 = b3 << 1) y = y | (y >> b3);
        p2c_f = y + 1;
    endfunction
    reg [1:0] pre_ph; reg [LWB:0] px_q, ps0_q, prnd_q, pvw_q; reg pflat_q; reg [23:0] pml_q, pmh_q;
    integer k2;
    always @(posedge clk or negedge rr[1]) begin
        if (!rr[1]) begin
            st <= S_IDLE; pre_ph <= 2'd0; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; go <= 1'b0; vmq <= 338'd0;
            sl_v <= 1'b0; sw_v <= 1'b0; sr_v <= 1'b0; rp <= 4'd0; use_p <= 4'd0; nf <= 3'd0; df_h <= 2'd0; df_t <= 2'd0;
            outst <= 3'd0; q_h <= 2'd0; q_t <= 2'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            sw_v <= 1'b0; sr_v <= 1'b0;
            if (s0v_q && s0i_q >= SW) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (cfault_q && st != S_FAULT) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            if (vfault_q && st == S_RUNW) vf_seen <= 1'b1;
            case (st)
                S_IDLE: begin
                    s_clr <= 1'b0;
                    if (op_v && op_rdy_r) begin
                        w <= op_w; wl <= op_w; op_rdy_r <= 1'b0; su_idle_r <= 1'b0; rk <= 3'd0; vf_seen <= 1'b0;
                        for (k2 = 0; k2 < 6; k2 = k2 + 1) galloc[k2] <= 0;
                        a_s <= strm[0]; o_s <= strm[1]; st <= S_PRE;
                    end
                end
                S_PRE: if (PRE_PIPE == 0) begin                     // the op's layout (registered once)
                    l_full_q <= l_el; l_half_q <= flatc ? (ni >> 1) : ((l_el >> 1) == 0 ? 1 : (l_el >> 1));
                    nn_q <= {16'd0, no} * {16'd0, ni};
                    st <= S_SPAN;
                end else begin : pre3                               // same values, 3 register-to-register phases
                    reg [LWB:0] se_;
                    case (pre_ph)
                        2'd0: begin                                 // operands: max(ni, 8 | 1), vw, flat, roundup, partials
                            px_q <= (ni > (red_on ? 16'd8 : 16'd1)) ? ni : (red_on ? 16'd8 : 16'd1);
                            pvw_q <= vw; pflat_q <= flatc; prnd_q <= (ni + N - 1) & ~(N - 1);
                            pml_q <= {8'd0, no} * {16'd0, ni[7:0]}; pmh_q <= {8'd0, no} * {16'd0, ni[15:8]};
                            pre_ph <= 2'd1;
                        end
                        2'd1: begin                                 // pow2ceil; the product
                            ps0_q <= p2c_f(px_q);
                            nn_q <= {8'd0, pml_q} + {pmh_q, 8'd0};
                            pre_ph <= 2'd2;
                        end
                        default: begin                              // slot = min(pow2ceil, vw); row width
                            se_ = (ps0_q > pvw_q) ? pvw_q : ps0_q;
                            if (pflat_q) begin l_full_q <= ni; l_half_q <= ni >> 1; end
                            else if (ni <= se_) begin l_full_q <= se_; l_half_q <= ((se_ >> 1) == 0) ? 1 : (se_ >> 1); end
                            else begin l_full_q <= prnd_q; l_half_q <= ((prnd_q >> 1) == 0) ? 1 : (prnd_q >> 1); end
                            pre_ph <= 2'd0; st <= S_SPAN;
                        end
                    endcase
                end
                S_SPAN: begin                                       // region rk: used? its layout
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    lo[rk] <= base_k; sor[rk] <= so_k; sir[rk] <= si_k; nrr[rk] <= nr_k; nir[rk] <= ni_k;
                    Lr[rk] <= L_k; nrm1_s <= nr_k - 16'd1; lsh_s <= {{(39-LWB){1'b0}}, L_k}; nw_s <= ni_k;
                    gk_s <= (rk == 3'd4) ? 3'd4 : (rk == 3'd5) ? 3'd5 : rk;
                    if (rk == 3'd0 && a_s) begin                    // A = STREAM: rows of ni, element o ni + i = idx
                        wl[40 +: 24] <= SBASE; wl[64 +: 24] <= {8'd0, ni}; wl[88 +: 24] <= 24'd1; st <= S_NEXTR;
                    end else if (rk == 3'd4 && o_s) begin           // O = STREAM: contiguous rows of ni in G4, no drain
                        Lr[4] <= ni; nrr[4] <= no; nir[4] <= ni; rv[4] <= 1'b1;
                        nrm1_s <= no - 16'd1; lsh_s <= {24'd0, ni}; nw_s <= ni;
                        macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL;
                    end
                    else if (!used_k) st <= S_NEXTR;
                    else begin macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL; end
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // lsz = (nr - 1) L + nw: shift registers, a bit an edge
                    if (mph == 2'd0) begin
                        if (nrm1_s[0]) macc <= macc + lsh_s;
                        nrm1_s <= nrm1_s >> 1; lsh_s <= lsh_s << 1;
                        if (mbit == 5'd15) mph <= 2'd1; else mbit <= mbit + 5'd1;
                    end else begin
                        lsz[rk] <= macc[LWB:0] + nw_s; st <= S_NEXTR;
                    end
                end
                S_NEXTR: begin                                      // placement: the aligned base (registered)
                    lbk_s <= (galloc[gk_s] + N - 1) & ~(N - 1); gsz_s <= gsz(gk_s); gsz2_s <= gsz(3'd2);
                    st <= rv[rk] ? S_NX1 : S_NX2;
                end
                S_NX1: begin gend_s <= lbk_s + lsz[rk]; st <= S_NX2; end
                S_NX2: begin                                        // place region rk (N-aligned), rewrite its fields
                    if (rv[rk]) begin
                        lb[rk] <= lbk_s;
                        galloc[gk_s] <= gend_s;
                        if (rk == 3'd0 && cpair) galloc[2] <= gend_s;         // A's copy in G2 (C reads A[e ^ 1])
                        if (gend_s > gsz_s || (rk == 3'd0 && cpair && gend_s > gsz2_s)) begin
                            su_fault_r <= 1'b1; st <= S_FAULT; end
                        case (rk)
                            3'd0: begin wl[40 +: 24]  <= lbk_s; wl[64 +: 24]  <= Lr[0]; wl[88 +: 24]  <= 24'd1; end
                            3'd1: begin wl[138 +: 24] <= lbk_s; wl[162 +: 24] <= Lr[1]; wl[186 +: 24] <= 24'd1; end
                            3'd2: begin wl[211 +: 24] <= lbk_s; wl[235 +: 24] <= Lr[2]; wl[259 +: 24] <= 24'd1; end
                            3'd3: begin wl[284 +: 24] <= lbk_s; wl[308 +: 24] <= Lr[3]; wl[332 +: 24] <= 24'd1; end
                            3'd4: begin wl[382 +: 24] <= lbk_s; wl[406 +: 24] <= Lr[4]; wl[430 +: 24] <= 24'd1; end
                            default: begin wl[484 +: 24] <= lbk_s; wl[508 +: 24] <= 24'd1; end
                        endcase
                    end else begin
                        // an unused stream: give it the flat-consistent stride (so = row words, si = 1) so the vec's
                        // flatten test (every stream contiguous across rows) agrees with the dense layout's choice
                        // (flatc).  Without it an absent B / C / D (record so 0, si 1) made the vec run a flatc op
                        // unflattened: a whole-op reduction over rows of ni then issues 2^tz(ni)-element vectors at
                        // row offsets the lane-local banks cannot serve (cfault; DS L0 q_norm.ss, ni 160, at N 64).
                        // Same rule as ot_hgi_su_ctlx__d4g_sfu.
                        case (rk)
                            3'd1: begin wl[162 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; wl[186 +: 24] <= 24'd1; end
                            3'd2: begin wl[235 +: 24] <= {8'd0, ni}; wl[259 +: 24] <= 24'd1; end
                            3'd3: begin wl[308 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; wl[332 +: 24] <= 24'd1; end
                            3'd4: if (!o_s) begin wl[406 +: 24] <= {8'd0, ni}; wl[430 +: 24] <= 24'd1; end
                            default: ;
                        endcase
                    end
                    if (st != S_FAULT) begin
                        if (rk == 3'd5) begin rk <= 3'd0; st <= S_STAGE; end
                        else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_STAGE: begin                                      // sources: gather the rows into the dense layout
                    if (rk == 3'd4) st <= S_RUN;
                    else if (!rv[rk]) rk <= rk + 3'd1;
                    else begin
                        st <= S_STW; q_h <= 0; q_t <= 0; outst <= 0;
                        sw_g <= (rk == 3'd0 && cpair) ? 4'b0101 : (4'b0001 << rk);
                        s_rows <= nrr[rk]; s_rb <= lo[rk]; s_lr <= lb[rk]; s_j <= 16'd0; s_va <= lo[rk];
                        c_so <= sor[rk]; c_si <= sir[rk]; c_nw <= nir[rk]; c_L <= Lr[rk];
                        s_md <= (sir[rk] == 24'd1) ? 2'd0 : (sir[rk] == 24'd0) ? 2'd1 : 2'd2;
                        cur_sec <= lo[rk] >> 3; end_sec <= (lo[rk] + nir[rk] - 24'd1) >> 3;
                    end
                end
                S_STW: begin
                    // issue (up to 4 outstanding, in order): run = the row's sectors; rep = one read per 8 copies;
                    // elem = one read per element
                    begin : iss
                        reg go_; reg [26:0] sc_; reg last_;
                        go_ = outst < 3'd4 && s_rows != 16'd0 && !(vr[273] && outst == 3'd4);
                        sc_ = (s_md == 2'd0) ? cur_sec : {3'd0, s_va[23:3]};
                        if (go_) begin
                            vmq <= {1'b1, 1'b0, sc_, 5'd0, 256'd0, 32'd0, 16'h5355};
                            q_sec[q_t] <= sc_; q_md[q_t] <= s_md; q_w[q_t] <= s_va[2:0];
                            q_lo[q_t] <= s_rb; q_hi[q_t] <= s_rb + c_nw - 24'd1;
                            q_off[q_t] <= {{(25-LWB){1'b0}}, s_lr} - {2'b00, s_rb};
                            q_la[q_t] <= s_lr + s_j;
                            q_msk[q_t] <= (s_md == 2'd1) ? ((c_nw - s_j >= 16'd8) ? 8'hFF :
                                                            ((8'd1 << (c_nw - s_j)) - 8'd1)) : 8'd1;
                            q_t <= q_t + 2'd1;
                            // advance the cursor
                            case (s_md)
                                2'd0: last_ = (cur_sec == end_sec);
                                2'd1: last_ = (c_nw - s_j <= 16'd8);
                                default: last_ = (s_j + 16'd1 == c_nw);
                            endcase
                            if (last_) begin                              // the next row
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + c_so; s_va <= s_rb + c_so;
                                s_lr <= s_lr + c_L; s_j <= 16'd0;
                                cur_sec <= (s_rb + c_so) >> 3; end_sec <= (s_rb + c_so + c_nw - 24'd1) >> 3;
                            end else begin
                                cur_sec <= cur_sec + 27'd1;
                                if (s_md == 2'd1) s_j <= s_j + 16'd8;
                                else if (s_md == 2'd2) begin s_j <= s_j + 16'd1; s_va <= s_va + c_si; end
                            end
                        end
                        outst <= outst + (go_ ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                        if (s_rows == 16'd0 && outst == ((vr[273] && !vr[256]) ? 3'd1 : 3'd0)) begin
                            rk <= rk + 3'd1; st <= S_STAGE;
                        end
                    end
                    if (vr[273] && !vr[256]) begin : land
                        reg [23:0] w0; integer q; reg [31:0] wd_;
                        w0 = {q_sec[q_h][20:0], 3'b000}; wd_ = vr[32*q_w[q_h] +: 32];
                        sw_v <= 1'b1; q_h <= q_h + 2'd1;
                        case (q_md[q_h])
                            2'd0: begin
                                sw_addr <= w0 + q_off[q_h][LWB-1:0]; sw_data <= vr[255:0];
                                for (q = 0; q < 8; q = q + 1) sw_mask[q] <= (w0 + q >= q_lo[q_h]) && (w0 + q <= q_hi[q_h]);
                            end
                            2'd1: begin sw_addr <= q_la[q_h]; sw_data <= {8{wd_}}; sw_mask <= q_msk[q_h]; end
                            default: begin sw_addr <= q_la[q_h]; sw_data <= {224'd0, wd_}; sw_mask <= 8'd1; end
                        endcase
                    end
                end
                S_RUN: if (ready_q && !sl_pend && (!a_s || {11'd0, scount} >= nn_q)) begin
                    go <= 1'b1; st <= S_RUNW; idle_ph <= 2'd0; use_p <= {use_d, use_c || cpair, use_b, 1'b1};
                end
                S_RUNW: begin
                    go <= 1'b0;
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        else begin dk <= 3'd4; st <= S_DRAIN; end
                    end
                end
                S_DRAIN: begin
                    use_p <= 4'd0;
                    if (dk == 3'd6) begin
                        if (o_s) begin etot <= PRE_PIPE ? nn_q[20:0] : {5'd0, no} * {5'd0, ni}; ebeat <= 21'd0; o_lb <= lb[4]; rp <= 4'd0; so_w <= 1'b0;
                                       st <= S_SOUT; end
                        else st <= S_DONE;
                    end
                    else if (!rv[dk] || (dk == 3'd4 && o_s)) dk <= dk + 3'd1;
                    else begin
                        // the shape: O = no rows of ni at (so, si); R = nr rows of one word at r_so
                        d_cur <= lo[dk]; d_rowb <= lo[dk]; d_so <= sor[dk]; d_si <= (dk == 3'd4) ? sir[dk] : 24'd0;
                        d_row <= nrr[dk]; d_ni <= nir[dk]; d_rem <= nir[dk];
                        d_run <= (dk == 3'd4) && (sir[dk] == 24'd1);
                        d_lcur <= lb[dk]; d_lrow <= lb[dk]; d_L <= Lr[dk];
                        d_live <= (nrr[dk] != 16'd0 && nir[dk] != 16'd0);
                        st <= S_DRW; outst <= 0; rp <= 4'd0;
                    end
                end
                S_DRW: begin                                        // the shape's words back to VM, word-masked
                    begin : dw
                        reg issue; reg [3:0] cnt; reg [7:0] mk; reg [2:0] off;
                        off = d_cur[2:0];
                        cnt = d_run ? (({12'd0, 4'd8} - {13'd0, off} < d_rem) ? 4'd8 - {1'b0, off} : d_rem[3:0]) : 4'd1;
                        mk = MUT_DIRTY ? 8'hFF : (((8'd1 << cnt) - 8'd1) << off);
                        issue = d_live && outst + nf < 3'd4;
                        if (issue) begin
                            // 8 consecutive local words whose word 'off' is the element at d_cur
                            sr_v <= 1'b1; sr_g <= (dk == 3'd4) ? 2'd1 : 2'd2; sr_addr <= d_lcur[LWB-1:0] - off;
                            df[df_t] <= {27'({3'd0, d_cur[23:3]}), mk}; df_t <= df_t + 2'd1;
                            if (d_rem == {12'd0, cnt}) begin
                                if (d_row == 16'd1) d_live <= 1'b0;
                                else begin d_row <= d_row - 16'd1; d_rowb <= d_rowb + d_so; d_cur <= d_rowb + d_so;
                                           d_rem <= d_ni; d_lrow <= d_lrow + d_L; d_lcur <= d_lrow + d_L; end
                            end else begin
                                d_cur <= d_cur + (d_run ? {20'd0, cnt} : d_si); d_rem <= d_rem - {12'd0, cnt};
                                d_lcur <= d_lcur + cnt;
                            end
                        end
                        if (sr_rv_q) begin                          // a read's response: its sector to VM, word-masked
                            vmq <= {1'b1, 1'b1, df[df_h][34:8], 5'd0, sr_data_q,
                                    {{4{df[df_h][7]}}, {4{df[df_h][6]}}, {4{df[df_h][5]}}, {4{df[df_h][4]}},
                                     {4{df[df_h][3]}}, {4{df[df_h][2]}}, {4{df[df_h][1]}}, {4{df[df_h][0]}}},
                                    16'h5357};
                            df_h <= df_h + 2'd1;
                        end
                        nf <= nf + (issue ? 3'd1 : 3'd0) - (sr_rv_q ? 3'd1 : 3'd0);
                        outst <= outst + (sr_rv_q ? 3'd1 : 3'd0) - ((vr[273] && vr[256]) ? 3'd1 : 3'd0);
                        if (!d_live && nf == 3'd0 && outst == ((vr[273] && vr[256]) ? 3'd1 : 3'd0)) begin
                            dk <= dk + 3'd1; st <= S_DRAIN; end
                    end
                end
                S_SOUT: if (amr_q && !so_w) begin                  // 8 elements a beat, in element order
                    sr_v <= 1'b1; sr_g <= 2'd1; sr_addr <= o_lb + ebeat; so_w <= 1'b1;
                end else if (so_w && sr_rv_q) begin                 // the memory's response (valid-driven)
                    begin : so
                        reg [7:0] mk; integer q;
                        for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                        am_stream <= {1'b0, 256'd0, sr_data_q, mk, (ebeat + 21'd8 >= etot), 1'b1};
                    end
                    so_w <= 1'b0;
                    if (ebeat + 21'd8 >= etot) st <= S_DONE; else ebeat <= ebeat + 21'd8;
                end
                S_DONE: begin su_idle_r <= 1'b1; op_rdy_r <= 1'b1; st <= S_IDLE; if (a_s) s_clr <= 1'b1; end
                S_FAULT: ;                                           // sticky (the adapter halts)
                default: st <= S_FAULT;
            endcase
        end
    end
`ifdef SU_DBG
    reg sfr_d; always @(posedge clk) sfr_d <= su_fault_r;
    always @(posedge clk) if (su_fault_r && !sfr_d)
        $display("SU_DBG %m fault st %0d rk %0d cfault %0d s0 %0d vf %0d gend %0d gsz %0d gsz2 %0d ni %0d no %0d L %0d lsz %0d",
                 st, rk, cfault_q, s0v_q && s0i_q >= SW, vf_seen, gend_s, gsz_s, gsz2_s, ni, no, Lr[rk], lsz[rk]);
`endif
endmodule

module ot_hgi_su_lbank__d4g_sfu #(
    parameter integer RB = 13,             // log2 words in the bank
    parameter integer MACRO = 1,           // 1: ot_sram_1r1w_1024x256 rows (RB = 13); 0: behavioural
    parameter integer LAT = 0              // bench mutant (behavioural banks): 1 = read latency 2 edges, 2 = 0 edges
) (
    input  wire          clk,
    input  wire          re,
    input  wire [RB-1:0] ra,
    output wire [31:0]   rd,
    input  wire          we,
    input  wire [RB-1:0] wa,
    input  wire [31:0]   wd
);
    reg [2:0] ks;
    always @(posedge clk) if (re) ks <= ra[2:0];
    wire [255:0] wm = {224'd0, 32'hFFFF_FFFF} << {wa[2:0], 5'd0};
    generate if (MACRO && RB == 13) begin : g_m
        wire [255:0] ro;
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00), .rr_addr(18'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 12) begin : g_m12       // 512 rows: the 1,024-row macro, upper half unused
        wire [255:0] ro;
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in({1'b0, ra[RB-1:3]}), .rd_out(ro),
            .w_ce_in(we), .w_addr_in({1'b0, wa[RB-1:3]}), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 11) begin : g_m11
        wire [255:0] ro;
        ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 10) begin : g_m10
        wire [255:0] ro;
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 9) begin : g_m9
        // 512 words occupy the lower 64 rows; the upper 64 physical rows are unused.
        wire [255:0] ro;
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in({1'b0, ra[RB-1:3]}), .rd_out(ro),
            .w_ce_in(we), .w_addr_in({1'b0, wa[RB-1:3]}), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO) begin : g_unsupported_macro
        initial $fatal(1, "ot_hgi_su_lbank__d4g_sfu: unsupported MACRO=1 RB=%0d", RB);
        assign rd = 32'd0;
    end else begin : g_b
        reg [31:0] m [0:(1 << RB) - 1];
        reg [31:0] q, q2;
        always @(posedge clk) begin if (re) q <= m[ra]; q2 <= q; if (we) m[wa] <= wd; end
        assign rd = (LAT == 1) ? q2 : (LAT == 2) ? m[ra] : q;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The unit's local operand memory, LANE-LOCAL (hgi-1010/d, 2026-10-10; scales to N = 512 lanes, Tensix-style).
// Every group is N word-interleaved banks (bank b holds the words whose local address = b mod N), one bank a lane.  The
// controller lays EVERY region out dense (element (o, i) at base + o L + i, base N-aligned, L = the vec's slot / row
// span; broadcast operands replicated; see ot_hgi_su_ctl__d4g_sfu), so a lane reads its own bank or one of a few fixed partners:
//   rot_j    (l + j M) mod N       j < N / M      (SFU-class ops issue M lanes; the vector start is a multiple of M)
//   swp_j    ((l ^ 1) + j M) mod N               (c_pair: C reads A[e ^ 1])
//   half_j   ((l >> 1) + j M / 2) mod N  j < 2N/M  (BF16-pair streams B / D: lanes 2k, 2k + 1 share word k)
//   lane 0   any bank                            (scalar-class ops run on lane 0)
// so the read network is a few-way mux a lane, not an N x N crossbar.  A bank serves one row an edge: the row of the
// first requesting candidate lane mapped to it.  A qualified read (used port, vector memory source) whose bank is not a
// candidate, or whose row differs from its bank's row, raises cfault (fail closed, never a wrong value).
// Groups: G0 A, G1 B, G2 C (+ A's copy for c_pair), G3 D (staged; read by ports A..D), GO (the lanes' element writes),
// GR (the reducer results, a small register file with NR write ports), GS (the STREAM-0 landing region, read by port A
// when A is STREAM).  Staging writes / drain reads move 8 consecutive words (any alignment: 8 distinct banks).
// Read latency: one edge (the address at edge k, the data after edge k + 1), as ot_hdc_v41x_vec expects.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_lgroup2__d4g_sfu #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24,
    parameter integer NLW = 0,             // lane write ports (GO: N)
    parameter integer MACRO = 1,
    parameter integer MUT_XBAR = 0,        // bench mutant: identity lanes take the neighbouring bank's word
    parameter integer LAT = 0,             // bench mutant: bank read latency 1 = +1 edge, 2 = -1 edge (see ot_hgi_su_lbank__d4g_sfu)
    parameter integer NS = 1               // sector lanes: NS independent 8-word stage writes / drain reads an edge
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      rq,                    // qualified lane reads (used port, vector-memory source)
    input  wire [N-1:0]      rr,                    // raw lane read enables
    input  wire [N*AW-1:0]   ra,
    output wire [N*32-1:0]   rd,
    input  wire [NS-1:0]     sr_v,                  // per sector lane: 8 consecutive words (drain / STREAM-out)
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_d,
    output wire [NS-1:0]     sr_rv,                 // sr_d valid: the sector read's response (follows the banks' latency)
    input  wire [NS-1:0]     sw_v,                  // per sector lane: up to 8 consecutive words (stage)
    input  wire [NS*LWB-1:0] sw_addr,
    input  wire [NS*8-1:0]   sw_mask,
    input  wire [NS*256-1:0] sw_d,
    input  wire [(NLW>0?NLW:1)-1:0]    lw,          // lane writes (element writes)
    input  wire [(NLW>0?NLW:1)*AW-1:0] lwa,
    input  wire [(NLW>0?NLW:1)*32-1:0] lwd,
    input  wire              s1_v,                  // one word (STREAM landing)
    input  wire [LWB-1:0]    s1_a,
    input  wire [31:0]       s1_d,
    output reg               flt
);
    localparam integer LN = $clog2(N), RB = LWB - LN, NROT = N / M, NHALF = (2 * N) / M, HM = (M / 2 > 0) ? M / 2 : 1;
    localparam integer NCAND = 2 * NROT + NHALF;
    localparam integer NL = (NLW > 0) ? NLW : 1;
    // candidate bank c of lane l (k < NCAND)
    function automatic [LN-1:0] cbank(input integer l, input integer k);
        integer j;
        if (k < NROT) cbank = (l + k * M) % N;
        else if (k < 2 * NROT) begin j = k - NROT; cbank = ((l ^ 1) + j * M) % N; end
        else begin j = k - 2 * NROT; cbank = ((l >> 1) + j * HM) % N; end
    endfunction
    // ---- read side: per bank, the row of the first requesting candidate lane mapped to it
    reg  [N-1:0]  b_re; reg [RB-1:0] b_ra [0:N-1];
    wire [31:0]   b_rd [0:N-1];
    reg  [N-1:0]  lok;                               // the lane's bank is one of its candidates
    integer b, l, k;
    reg src;                                         // sector-lane read conflict (this edge)
    always @* begin : rsel
        integer rj_, sl_; reg [LWB-1:0] sa; reg [LN-1:0] bl;
        sa = {LWB{1'b0}}; bl = {LN{1'b0}};
        for (b = 0; b < N; b = b + 1) begin b_re[b] = 1'b0; b_ra[b] = {RB{1'b0}}; end
        for (l = 0; l < N; l = l + 1) begin
            bl = ra[l*AW +: LN]; lok[l] = (l == 0);
            for (k = 0; k < NCAND; k = k + 1) if (cbank(l, k) == bl) lok[l] = 1'b1;
        end
        src = 1'b0;
        if (|sr_v) begin
            // sector lanes: 8 words each; two words on one bank must be one row (else a sector-lane conflict, fail closed)
            for (sl_ = 0; sl_ < NS; sl_ = sl_ + 1) if (sr_v[sl_])
                for (rj_ = 0; rj_ < 8; rj_ = rj_ + 1) begin
                    sa = sr_addr[sl_*LWB +: LWB] + rj_;
                    if (b_re[sa[LN-1:0]] && b_ra[sa[LN-1:0]] != sa[LWB-1:LN]) src = 1'b1;
                    b_re[sa[LN-1:0]] = 1'b1; b_ra[sa[LN-1:0]] = sa[LWB-1:LN];
                end
        end else begin
            // lowest-index lane wins a bank (the bank's row); the others must agree (checked below)
            for (l = N - 1; l >= 0; l = l - 1)
                if (rr[l] && lok[l]) begin
                    bl = ra[l*AW +: LN]; b_re[bl] = 1'b1; b_ra[bl] = ra[l*AW + LN +: RB];
                end
        end
    end
    reg [LN-1:0] lb_q [0:N-1]; reg [LN-1:0] sr_lo [0:NS-1];
    reg [LN-1:0] lb_q2 [0:N-1]; reg [LN-1:0] sr_lo2 [0:NS-1]; reg [NS-1:0] srv1, srv2;
    integer s_;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) if (rr[l]) lb_q[l] <= ra[l*AW +: LN];
        for (s_ = 0; s_ < NS; s_ = s_ + 1) begin if (sr_v[s_]) sr_lo[s_] <= sr_addr[s_*LWB +: LN]; sr_lo2[s_] <= sr_lo[s_]; end
        for (l = 0; l < N; l = l + 1) lb_q2[l] <= lb_q[l];
        srv2 <= srv1;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) srv1 <= {NS{1'b0}}; else srv1 <= sr_v;
    // the response valid and the network selects follow the banks' latency (LAT mutants move the data, valid and
    // selects together, so a valid-driven reader stays exact and a fixed-latency one does not)
    assign sr_rv = (LAT == 1) ? srv2 : (LAT == 2) ? sr_v : srv1;
    wire [LN-1:0] lb_s [0:N-1];
    for (genvar gs_ = 0; gs_ < N; gs_ = gs_ + 1) begin : g_ls
        assign lb_s[gs_] = (LAT == 1) ? lb_q2[gs_] : (LAT == 2) ? ra[gs_*AW +: LN] : lb_q[gs_];
    end
    // the data network: a lane takes its bank among its candidates (lane 0: any bank)
    genvar gl, gj, gk;
    for (gl = 0; gl < N; gl = gl + 1) begin : g_rd
        if (gl == 0) begin : g_any
            wire [LN-1:0] bs = lb_s[gl] + MUT_XBAR[LN-1:0];
            assign rd[0 +: 32] = b_rd[bs];
        end else begin : g_c
            reg [31:0] dv;
            always @* begin : mx
                integer kk;
                dv = 32'd0;
                for (kk = NCAND - 1; kk >= 0; kk = kk - 1)
                    if (lb_s[gl] == cbank(gl, kk)) dv = b_rd[(cbank(gl, kk) + MUT_XBAR) % N];
            end
            assign rd[32*gl +: 32] = dv;
        end
    end
    for (gk = 0; gk < NS; gk = gk + 1) begin : g_srl
        wire [LN-1:0] sr_s = (LAT == 1) ? sr_lo2[gk] : (LAT == 2) ? sr_addr[gk*LWB +: LN] : sr_lo[gk];
        for (gj = 0; gj < 8; gj = gj + 1) begin : g_sr
            wire [LN-1:0] bj = sr_s + gj;
            assign sr_d[256*gk + 32*gj +: 32] = b_rd[bj];
        end
    end
    // ---- write side: stage (8 words) > lane writes > the single-word STREAM landing (its own group in practice)
    reg  [N-1:0] b_we; reg [RB-1:0] b_wa [0:N-1]; reg [31:0] b_wd [0:N-1];
    reg  wcoll;
    always @* begin : wsel
        integer wl_, wj_, wk_, ws_; reg [LWB-1:0] sb; reg [LN-1:0] wb_; reg ok_;
        sb = {LWB{1'b0}}; wb_ = {LN{1'b0}}; ok_ = 1'b0;
        for (b = 0; b < N; b = b + 1) begin b_we[b] = 1'b0; b_wa[b] = {RB{1'b0}}; b_wd[b] = 32'd0; end
        wcoll = 1'b0;
        for (ws_ = 0; ws_ < NS; ws_ = ws_ + 1) if (sw_v[ws_])
            for (wj_ = 0; wj_ < 8; wj_ = wj_ + 1) if (sw_mask[ws_*8 + wj_]) begin
                sb = sw_addr[ws_*LWB +: LWB] + wj_;
                if (b_we[sb[LN-1:0]]) wcoll = 1'b1;          // two sector lanes on one bank: fail closed
                b_we[sb[LN-1:0]] = 1'b1; b_wa[sb[LN-1:0]] = sb[LWB-1:LN]; b_wd[sb[LN-1:0]] = sw_d[ws_*256 + 32*wj_ +: 32];
            end
        if (NLW > 0) begin
            if (|sw_v && |lw) wcoll = 1'b1;
            for (wl_ = 0; wl_ < NL; wl_ = wl_ + 1)
                if (lw[wl_]) begin
                    wb_ = lwa[wl_*AW +: LN]; ok_ = (wl_ == 0);
                    for (wk_ = 0; wk_ < NROT; wk_ = wk_ + 1) if (cbank(wl_, wk_) == wb_) ok_ = 1'b1;
                    if (!ok_) wcoll = 1'b1;
                    // two lanes on one bank must write the same row (the later lane wins, as a behavioural memory)
                    if (b_we[wb_] && b_wa[wb_] != lwa[wl_*AW + LN +: RB]) wcoll = 1'b1;
                    if (!(|sw_v)) begin b_we[wb_] = 1'b1; b_wa[wb_] = lwa[wl_*AW + LN +: RB]; b_wd[wb_] = lwd[32*wl_ +: 32]; end
                end
        end
        if (s1_v) begin
            if (b_we[s1_a[LN-1:0]]) wcoll = 1'b1;
            b_we[s1_a[LN-1:0]] = 1'b1; b_wa[s1_a[LN-1:0]] = s1_a[LWB-1:LN]; b_wd[s1_a[LN-1:0]] = s1_d;
        end
    end
    // ---- fail-closed checks (registered)
    reg [N-1:0] rq_q, lok_q; reg [RB-1:0] lr_q [0:N-1]; reg [RB-1:0] br_q [0:N-1]; reg srv_q, wcoll_q;
    always @(posedge clk) begin
        rq_q <= (|sr_v) ? {N{1'b0}} : rq; lok_q <= lok; srv_q <= ((|sr_v) && |rq) || src; wcoll_q <= wcoll;
        for (l = 0; l < N; l = l + 1) lr_q[l] <= ra[l*AW + LN +: RB];
        for (b = 0; b < N; b = b + 1) br_q[b] <= b_ra[b];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else begin
            if (srv_q || wcoll_q) flt <= 1'b1;
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]])) flt <= 1'b1;
`ifdef LMEM_DBG
            if (srv_q) $display("LMEM_DBG %m sr during lane reads / sector-lane conflict");
            if (wcoll_q) $display("LMEM_DBG %m write collision");
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]]))
                    $display("LMEM_DBG %m read lane %0d bank %0d cand %0d row %0d bank-row %0d", l, lb_q[l], lok_q[l],
                             lr_q[l], br_q[lb_q[l]]);
`endif
        end
    end
    genvar gb;
    for (gb = 0; gb < N; gb = gb + 1) begin : g_bank
        ot_hgi_su_lbank__d4g_sfu #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
    end
endmodule

// the reducer results: a small register file, NR write ports (any address), 8-word reads
module ot_hgi_su_rfile__d4g_sfu #(parameter integer NR = 2, RWB = 6, AW = 24, NS = 1) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NR-1:0]     we,
    input  wire [NR*AW-1:0]  wa,
    input  wire [NR*32-1:0]  wd,
    input  wire [NS-1:0]     sr_v,
    input  wire [NS*RWB-1:0] sr_addr,
    output reg  [NS*256-1:0] sr_d,
    output reg  [NS-1:0]     sr_rv,                 // sr_d valid (one edge after sr_v)
    output reg               flt                    // a result outside the file
);
    reg [31:0] m [0:(1 << RWB) - 1];
    integer j, q, s;
    always @(posedge clk) begin
        for (j = 0; j < NR; j = j + 1) if (we[j]) m[wa[j*AW +: RWB]] <= wd[32*j +: 32];
        for (s = 0; s < NS; s = s + 1)
            if (sr_v[s]) for (q = 0; q < 8; q = q + 1) sr_d[256*s + 32*q +: 32] <= m[(sr_addr[s*RWB +: RWB] + q) & ((1 << RWB) - 1)];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else for (j = 0; j < NR; j = j + 1) if (we[j] && |wa[j*AW + RWB +: AW - RWB]) flt <= 1'b1;
    always @(posedge clk or negedge rst_n) if (!rst_n) sr_rv <= {NS{1'b0}}; else sr_rv <= sr_v;
endmodule

module ot_hgi_su_lmem__d4g_sfu #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24, NR = N / 8, MACRO = 1,
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB,   // log2 words of B, C, D, O (G0 = LWB: A)
    parameter integer RWB = 6,                                      // log2 words of the reducer-result file
    parameter integer SLB = 16,
    parameter integer NOSTR = 0,
    parameter integer MUT_XBAR = 0,
    parameter integer MUT_LAT = 0,         // bench mutants: 1 / 2 = every bank's read latency +1 / -1 edge (behavioural
                                           //   banks; the lane ports' 1-edge contract breaks), 3 / 4 = the drain response
                                           //   valid one edge early / late against its data
    parameter integer NS = 1               // sector lanes (stage writes / drain reads an edge; WIDE: 32, lane b = sector b)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [3:0]        use_p,
    input  wire [N-1:0]      vi_re,
    input  wire [N*AW-1:0]   vi_addr,
    output wire [N*32-1:0]   vi_q,
    input  wire [4*N-1:0]    rd_re,
    input  wire [4*N*AW-1:0] rd_addr,
    input  wire [8*N-1:0]    rd_src,
    output wire [4*N*32-1:0] rd_q,
    input  wire [N-1:0]      vm_we,
    input  wire [N*AW-1:0]   vm_waddr,
    input  wire [N*32-1:0]   vm_wdata,
    input  wire [NR-1:0]     res_we,
    input  wire [NR*AW-1:0]  res_addr,
    input  wire [NR*32-1:0]  res_data,
    input  wire              sl_v,
    input  wire [LWB-1:0]    sl_addr,
    input  wire [31:0]       sl_data,
    output wire              sl_pend,
    input  wire              a_str,
    input  wire [NS-1:0]     sw_v,                  // per sector lane: up to 8 consecutive words (any alignment)
    input  wire [3:0]        sw_g,                  // staging groups of this edge's writes (A, B, C, D; A + C for c_pair)
    input  wire [NS*LWB-1:0] sw_addr,
    input  wire [NS*8-1:0]   sw_mask,
    input  wire [NS*256-1:0] sw_data,
    input  wire [NS-1:0]     sr_v,                  // per sector lane: 8 consecutive words (any alignment)
    input  wire [1:0]        sr_g,                  // this edge's drain reads: 1 = O, 2 = R
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_data,
    output wire [NS-1:0]     sr_rv,                 // sr_data valid per lane: drain / STREAM-out readers consume on it
    output reg               cfault
);
    localparam integer LAT = (MUT_LAT == 1 || MUT_LAT == 2) ? MUT_LAT : 0;
    wire [6:0] gf; wire [NS*256-1:0] o_sr, r_sr; wire [NS-1:0] o_rv, r_rv;
    reg [1:0] srg_q; always @(posedge clk) if (|sr_v) srg_q <= sr_g;
    assign sr_data = (srg_q == 2'd2) ? r_sr : o_sr;
    wire [NS-1:0] srv0 = (srg_q == 2'd2) ? r_rv : o_rv;
    reg [NS-1:0] srv_late; always @(posedge clk or negedge rst_n) if (!rst_n) srv_late <= {NS{1'b0}}; else srv_late <= srv0;
    assign sr_rv = (MUT_LAT == 3) ? (sr_v & {NS{sr_g == 2'd1 || sr_g == 2'd2}}) : (MUT_LAT == 4) ? srv_late : srv0;
    assign vi_q = {N*32{1'b0}};
    assign sl_pend = 1'b0;
    reg vi_bad; always @(posedge clk) vi_bad <= |vi_re;
    always @(posedge clk or negedge rst_n) if (!rst_n) cfault <= 1'b0; else if (vi_bad || |gf) cfault <= 1'b1;
`ifdef LMEM_DBG
    always @(posedge clk) if (vi_bad) $display("LMEM_DBG gather read");
`endif
    reg as_q; always @(posedge clk) as_q <= a_str;
    wire [N*32-1:0] gs_rd;
    genvar g, l;
    for (g = 0; g < 4; g = g + 1) begin : g_grp
        wire [N-1:0] rr, rq; wire [N*AW-1:0] ra; wire [N*32-1:0] rd;
        for (l = 0; l < N; l = l + 1) begin : g_l
            assign rr[l] = rd_re[4*l + g] && !(g == 0 && a_str);
            assign rq[l] = rr[l] && use_p[g] && rd_src[8*l + 2*g +: 2] == 2'd0;
            assign ra[l*AW +: AW] = rd_addr[(4*l + g)*AW +: AW];
            if (g == 0) begin : g_a
                assign rd_q[(4*l)*32 +: 32] = as_q ? gs_rd[32*l +: 32] : rd[32*l +: 32];
            end else begin : g_o
                assign rd_q[(4*l + g)*32 +: 32] = rd[32*l +: 32];
            end
        end
        localparam integer GB = (g == 0) ? LWB : (g == 1) ? LG1 : (g == 2) ? LG2 : LG3;
        wire [NS*GB-1:0] sw_ga;
        for (genvar s = 0; s < NS; s = s + 1) begin : g_swa assign sw_ga[s*GB +: GB] = sw_addr[s*LWB +: GB]; end
        ot_hgi_su_lgroup2__d4g_sfu #(.N(N), .M(M), .LWB(GB), .AW(AW), .NLW(0), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT), .NS(NS)) u_g (
            .clk(clk), .rst_n(rst_n), .rq(rq), .rr(rr), .ra(ra), .rd(rd), .sr_v({NS{1'b0}}), .sr_addr({NS*GB{1'b0}}), .sr_d(), .sr_rv(),
            .sw_v(sw_v & {NS{sw_g[g]}}), .sw_addr(sw_ga), .sw_mask(sw_mask), .sw_d(sw_data), .lw(1'b0),
            .lwa({AW{1'b0}}), .lwd(32'd0), .s1_v(1'b0), .s1_a({GB{1'b0}}), .s1_d(32'd0), .flt(gf[g]));
    end
    // GO: the lanes' element writes; drain / STREAM-out reads
    wire [NS*LGO-1:0] sr_oa; wire [NS*RWB-1:0] sr_ra;
    for (genvar s = 0; s < NS; s = s + 1) begin : g_sra
        assign sr_oa[s*LGO +: LGO] = sr_addr[s*LWB +: LGO]; assign sr_ra[s*RWB +: RWB] = sr_addr[s*LWB +: RWB];
    end
    ot_hgi_su_lgroup2__d4g_sfu #(.N(N), .M(M), .LWB(LGO), .AW(AW), .NLW(N), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT), .NS(NS)) u_go (
        .clk(clk), .rst_n(rst_n), .rq({N{1'b0}}), .rr({N{1'b0}}), .ra({N*AW{1'b0}}), .rd(), .sr_v(sr_v & {NS{sr_g == 2'd1}}),
        .sr_addr(sr_oa), .sr_d(o_sr), .sr_rv(o_rv), .sw_v({NS{1'b0}}), .sw_addr({NS*LGO{1'b0}}), .sw_mask({NS*8{1'b0}}), .sw_d({NS*256{1'b0}}),
        .lw(vm_we), .lwa(vm_waddr), .lwd(vm_wdata), .s1_v(1'b0), .s1_a({LGO{1'b0}}), .s1_d(32'd0), .flt(gf[4]));
    // GR: the reducer results
    ot_hgi_su_rfile__d4g_sfu #(.NR(NR), .RWB(RWB), .AW(AW), .NS(NS)) u_gr (.clk(clk), .rst_n(rst_n), .we(res_we), .wa(res_addr),
        .wd(res_data), .sr_v(sr_v & {NS{sr_g == 2'd2}}), .sr_addr(sr_ra), .sr_d(r_sr), .sr_rv(r_rv), .flt(gf[5]));
    // GS: the STREAM-0 landing region (port A reads it when the op's A is STREAM)
    wire [N-1:0] gs_rr, gs_rq; wire [N*AW-1:0] gs_ra;
    for (l = 0; l < N; l = l + 1) begin : g_sa
        assign gs_rr[l] = rd_re[4*l] && a_str;
        assign gs_rq[l] = gs_rr[l] && use_p[0] && rd_src[8*l +: 2] == 2'd0;
        assign gs_ra[l*AW +: AW] = rd_addr[(4*l)*AW +: AW];
    end
    if (NOSTR) begin : g_nostr
        reg bad; always @(posedge clk) bad <= sl_v || |gs_rq;
        assign gs_rd = {N*32{1'b0}}; assign gf[6] = bad;
    end else begin : g_str
        ot_hgi_su_lgroup2__d4g_sfu #(.N(N), .M(M), .LWB(SLB), .AW(AW), .NLW(0), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT)) u_gs (
            .clk(clk), .rst_n(rst_n), .rq(gs_rq), .rr(gs_rr), .ra(gs_ra), .rd(gs_rd), .sr_v(1'b0), .sr_addr({SLB{1'b0}}),
            .sr_d(), .sr_rv(), .sw_v(1'b0), .sw_addr({SLB{1'b0}}), .sw_mask(8'd0), .sw_d(256'd0), .lw(1'b0), .lwa({AW{1'b0}}),
            .lwd(32'd0), .s1_v(sl_v), .s1_a(sl_addr[SLB-1:0]), .s1_d(sl_data), .flt(gf[6]));
    end
`ifdef LMEM_PROF
    final $display("LMEM_GROUPS cfault %0d", cfault);
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The stream-unit die body: the controller (ot_hgi_su_ctl__d4g_sfu: record adapter + stage / drain / STREAM) + the unchanged
// stream unit ot_hdc_v41x_vec + its local memory.  Ports as before the split (2026-10-10).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_unit__d4g_sfu #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer MUT_DIRTY = 0,
    parameter integer WIDE = 0,           // hgi-unitrate: 1 = ot_hgi_su_ctlw__d4g_sfu on the behavioural wide lmem (bench model);
                                          //   2 = ot_hgi_su_ctlx__d4g_sfu on d's lane-local lmem (NS 32): the PRODUCTION engine
    parameter integer MUT_X = 0,          // WIDE = 2 bench mutants (ot_hgi_su_ctlx__d4g_sfu)
    parameter integer DF = 16,            // WIDE = 2: landed-but-unwritten stage sectors a lane
    parameter integer LQ = 8,             // WIDE: credits a lane holds (size to the lane-group round trip incl. relays)
    parameter integer LRLAT = 1,          // WIDE bench: the wide lmem model's read latency (the controller is valid-driven)
    parameter integer MUT_RV = 0,         // WIDE bench: lmem read valid 1 early / 2 late (must FAIL)
    parameter integer MUT_W = 0,          // WIDE bench mutants (ot_hgi_su_ctlw__d4g_sfu)
    // WIDE = 0 (hgi-1010/d): the lane-local banked local memory (ot_hgi_su_lmem__d4g_sfu) and its dense-layout controller
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB, RWB = 6,
    parameter integer MACRO = 1,          // local memory: 1 = banked SRAM macros, 0 = behavioural banks
    parameter integer MUT_LAT = 0         // bench mutants (ot_hgi_su_lmem__d4g_sfu MUT_LAT; 1 / 2 force behavioural banks)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output wire [522:0]  am_stream,
    input  wire          am_rdy,
    // WIDE = 1 only (tie off / leave open otherwise): the VM wide lanes, lane b <-> VM bank b (ot_hgi_su_ctlw__d4g_sfu)
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,           // shared lane groups: request / grant (tie grants 1 for a dedicated group)
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    localparam integer AW = 24, NR = N / 8;
    wire go, ready, idle, vfault, ofault, ro; wire [669:0] wl;
    wire sl_v, sw_v, dc_v, sr_v; wire [LWB-1:0] sl_addr; wire [31:0] sl_data; wire [LWB-4:0] sw_sec, dc_sec, sr_sec;
    wire [255:0] sw_data, sr_data; wire [7:0] sr_dm;
    wire [31:0] lsw_v, ldc_v, ldr_v; wire [32*(LWB-3)-1:0] lsw_sec, ldc_sec, ldr_sec; wire [32*256-1:0] lsw_d, ldr_d;
    wire [32*8-1:0] ldr_dm; wire lm_bank_err; wire [31:0] ldr_rv; wire sr_rv;
    // WIDE = 0: the lane-local memory's controller ports
    wire [LWB-1:0] l_sw_addr, l_sr_addr; wire [7:0] l_sw_mask; wire [3:0] l_sw_g, l_use_p; wire [1:0] l_sr_g;
    wire l_sl_pend, l_cfault, l_a_str, l_sr_rv;
    // WIDE = 2: the production engine's 32 lmem sector lanes
    wire [31:0] x_sw_v, x_sr_v, x_sr_rv; wire [32*256-1:0] x_sw_data, x_sr_data; wire [3:0] x_sw_g, x_use_p; wire [1:0] x_sr_g;
    wire [32*LWB-1:0] x_sw_addr, x_sr_addr; wire [32*8-1:0] x_sw_mask; wire x_a_str, x_cfault, x_sl_pend;
    generate if (WIDE == 2) begin : g_xctl
    ot_hgi_su_ctlx__d4g_sfu #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET),
        .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB), .LQ(LQ), .DF(DF), .MUT_X(MUT_X)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sw_v(x_sw_v), .sw_data(x_sw_data), .sw_g(x_sw_g), .sw_addr(x_sw_addr), .sw_mask(x_sw_mask), .sr_v(x_sr_v), .sr_g(x_sr_g),
        .sr_addr(x_sr_addr), .sr_data(x_sr_data), .sr_rv(x_sr_rv), .use_p(x_use_p), .sl_pend(x_sl_pend), .a_str(x_a_str),
        .cfault(x_cfault), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done),
        .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt));
    end else if (WIDE == 1) begin : g_wctl
`ifndef OT_CTLW_SLICES
`define OT_CTLW_SLICES 0
`endif
    ot_hgi_su_ctlw__d4g_sfu #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET), .MUT_W(MUT_W), .LQ(LQ), .SLICES(`OT_CTLW_SLICES)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_sec(sw_sec), .sw_data(sw_data), .dc_v(dc_v), .dc_sec(dc_sec), .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm),
        .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .rg_req(rg_req), .rg_gnt(rg_gnt),
        .wg_req(wg_req), .wg_gnt(wg_gnt), .ldr_rv(ldr_rv), .sr_rv(sr_rv), .lsw_v(lsw_v), .lsw_sec(lsw_sec),
        .lsw_d(lsw_d), .ldc_v(ldc_v), .ldc_sec(ldc_sec), .ldr_v(ldr_v), .ldr_sec(ldr_sec), .ldr_d(ldr_d), .ldr_dm(ldr_dm));
    end else begin : g_ctl
    ot_hgi_su_ctl__d4g_sfu #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET), .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_addr(l_sw_addr), .sw_mask(l_sw_mask), .sw_data(sw_data), .sw_g(l_sw_g), .sr_v(sr_v), .sr_g(l_sr_g),
        .sr_addr(l_sr_addr), .sr_data(sr_data), .sr_rv(l_sr_rv), .use_p(l_use_p), .sl_pend(l_sl_pend), .a_str(l_a_str),
        .cfault(l_cfault));
        assign wrq = '0; assign wwq = '0; assign rg_req = 1'b0; assign wg_req = 1'b0;
    end endgenerate
    wire [N-1:0] vi_re, vm_we, kv_we; wire [N*AW-1:0] vi_addr, vm_waddr, kv_waddr; wire [N*32-1:0] vi_q;
    wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; wire [4*N*32-1:0] rd_q;
    wire [N*32-1:0] vm_wdata, kv_wdata; wire [NR-1:0] res_we; wire [NR*AW-1:0] res_addr; wire [NR*32-1:0] res_data;
    wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire de, dr, ds; wire [7:0] es, rs, ss;
`ifdef OT_SU_C12
    // tput-fix-1011 (bench only, -DOT_SU_C12 with the *_c12 file set): the stream unit as the die's c12 lane array --
    // ot_su13_ctl64's functional parameter set (rtl/hdc/v41x/phys/ot_hdc_su_ctl_c13_phys.sv less the physical-only CTL13;
    // lanes = ot_su12_sfu__d4g_sfu / ot_su12_light__d4g_sfu: MLAT 6, ALAT 6, OPR 1, DDIV 21, SIDEX 4, CAPR 1)
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21),
                      .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(`OT_SU_C12_RSLICE),
                      .CTL12(1), .DENR(`OT_SU_C12_DENR), .SFUT(`OT_SU_C12_SFUT))
                    u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
`else
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV)) u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
`endif
        .i_nout(wl[0 +: 16]), .i_nin(wl[16 +: 16]), .i_asrc(wl[32 +: 2]), .i_bsrc(wl[34 +: 2]), .i_csrc(wl[36 +: 2]),
        .i_dsrc(wl[38 +: 2]), .i_abase(wl[40 +: 24]), .i_aso(wl[64 +: 24]), .i_asi(wl[88 +: 24]),
        .i_aibase(wl[112 +: 24]), .i_aind(wl[136 +: 2]), .i_bbase(wl[138 +: 24]), .i_bso(wl[162 +: 24]),
        .i_bsi(wl[186 +: 24]), .i_bhalf(wl[210]), .i_cbase(wl[211 +: 24]), .i_cso(wl[235 +: 24]),
        .i_csi(wl[259 +: 24]), .i_cpair(wl[283]), .i_dbase(wl[284 +: 24]), .i_dso(wl[308 +: 24]),
        .i_dsi(wl[332 +: 24]), .i_arnd(wl[356]), .i_arelu(wl[357]), .i_amin(wl[358]), .i_cclip(wl[359]),
        .i_m1(wl[360 +: 3]), .i_m2(wl[363 +: 2]), .i_qm(wl[365 +: 3]), .i_ad(wl[368 +: 3]), .i_sfu(wl[371 +: 3]),
        .i_e1(wl[374 +: 3]), .i_e2(wl[377 +: 2]), .i_rnd(wl[379]), .i_dst(wl[380 +: 2]), .i_obase(wl[382 +: 24]),
        .i_oso(wl[406 +: 24]), .i_osi(wl[430 +: 24]), .i_orow(wl[454 +: 24]), .i_red(wl[478 +: 2]),
        .i_redsq(wl[480]), .i_redwhole(wl[481]), .i_redtree(wl[482]), .i_redrnd(wl[483]), .i_rbase(wl[484 +: 24]),
        .i_rso(wl[508 +: 24]), .i_imm1(wl[532 +: 32]), .i_imm2(wl[564 +: 32]), .i_imm3(wl[596 +: 32]),
        .i_ch_src(wl[628 +: 2]), .i_ch_seq(wl[630 +: 8]), .i_ch_lead(wl[638 +: 16]), .i_ch_mul(wl[654 +: 16]),
        .x_seq(8'd0), .x_dseq(8'hFF), .x_cnt(16'd0), .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq),
        .cr_cnt(cr_cnt), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we),
        .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(vfault), .order_fault(ofault), .emitted(emitted), .retire_o(ro), .dbg_emit(de), .dbg_eseq(es),
        .dbg_ret(dr), .dbg_rseq(rs), .dbg_res(ds), .dbg_sseq(ss));
    generate if (WIDE == 2) begin : g_xmem
    ot_hgi_su_lmem__d4g_sfu #(.N(N), .M(M), .LWB(LWB), .AW(AW), .MACRO(MACRO && (MUT_LAT == 0 || MUT_LAT > 2)), .MUT_LAT(MUT_LAT),
        .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB), .SLB(SLB), .NOSTR(GLU), .NS(32)) u_mem (.clk(clk), .rst_n(rst_n),
        .use_p(x_use_p), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re), .rd_addr(rd_addr), .rd_src(rd_src),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sl_pend(x_sl_pend), .a_str(x_a_str),
        .sw_v(x_sw_v), .sw_g(x_sw_g), .sw_addr(x_sw_addr), .sw_mask(x_sw_mask), .sw_data(x_sw_data), .sr_v(x_sr_v), .sr_g(x_sr_g),
        .sr_addr(x_sr_addr), .sr_data(x_sr_data), .sr_rv(x_sr_rv), .cfault(x_cfault));
    end else if (WIDE == 1) begin : g_wmem
    ot_hgi_su_lmemw__d4g_sfu #(.N(N), .LWB(LWB), .AW(AW), .RLAT(LRLAT), .MUT_RV(MUT_RV)) u_mem (.clk(clk), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .rd_re(rd_re), .rd_addr(rd_addr), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm),
        .lsw_v(lsw_v), .lsw_sec(lsw_sec), .lsw_d(lsw_d), .ldc_v(ldc_v), .ldc_sec(ldc_sec), .ldr_v(ldr_v), .ldr_sec(ldr_sec),
        .ldr_d(ldr_d), .ldr_dm(ldr_dm), .ldr_rv(ldr_rv), .sr_rv(sr_rv), .bank_err(lm_bank_err));
    end else begin : g_mem
    ot_hgi_su_lmem__d4g_sfu #(.N(N), .M(M), .LWB(LWB), .AW(AW), .MACRO(MACRO && (MUT_LAT == 0 || MUT_LAT > 2)), .MUT_LAT(MUT_LAT),
        .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB), .SLB(SLB), .NOSTR(GLU)) u_mem (.clk(clk), .rst_n(rst_n),
        .use_p(l_use_p), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re), .rd_addr(rd_addr), .rd_src(rd_src),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sl_pend(l_sl_pend), .a_str(l_a_str),
        .sw_v(sw_v), .sw_g(l_sw_g), .sw_addr(l_sw_addr), .sw_mask(l_sw_mask), .sw_data(sw_data), .sr_v(sr_v), .sr_g(l_sr_g),
        .sr_addr(l_sr_addr), .sr_data(sr_data), .sr_rv(l_sr_rv), .cfault(l_cfault));
    end endgenerate
endmodule
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 stream-unit / SFU die body controller, WIDE successor (hgi-unitrate 2026-10-10; ot_hgi_su_unit__d4g_sfu WIDE = 1).
// Same record semantics as ot_hgi_su_ctl__d4g_sfu (stage the op's VM operands into the local operand memory, run the unchanged
// ot_hdc_v41x_vec on local addresses, drain the words it wrote, retire on the last drain write), re-architected for
// throughput at the production record shapes (Qwen3-8B P 8,191: 31,276 sectors staged and 19,682 drained a layer):
//   * span: the (no - 1) so + (ni - 1) si extent is a 3-edge pipelined multiply (4 partial products of 8 x 24),
//     not 32 serial shift-add edges a region;
//   * placement: every region is placed with lb == lo (mod 256 words), so a VM sector and its local copy sit in the
//     same bank (sector mod 32): the 32 wide lanes need no crossbar;
//   * stage: 32 lanes, lane b streams bank b's sectors of every source region through the VM wide read lanes (LQ
//     credits a lane, in-order responses landed through a per-lane FIFO of local sector numbers), while the same lane
//     clears its sink sectors' dirty masks: one sector a lane an edge, 1 KB an edge per unit;
//   * drain: 32 lanes read {data, dirty mask} of their local sink sectors (read pipe 3 edges) and write each dirty
//     sector word-masked through the VM wide write lanes (credit at acceptance, retire on the last done).
// The packet client (vmq / vmr) stays idle in this mode.  Order, faults and STREAM paths are those of ot_hgi_su_ctl__d4g_sfu.
// ---------------------------------------------------------------------------------------------------------------------
`ifndef OT_CTLW_NLP
`ifdef OT_CTLW_HEAD_EXT
`define OT_CTLW_NLP 8      // GLUE PLACEMENT (el1011-hbm-sfu 10-11): the ctlw HEAD tile = control + slice 0 (lanes 0-7)
`else
`define OT_CTLW_NLP 32
`endif
`endif
module ot_hgi_su_ctlw__d4g_sfu #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,           // log2 local words (the Qwen head: 37,984 B + O + the stream region)
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,            // 1: the SFU die body (SFU.GLU records; ot_hgi_su_record GLU mode)
    parameter integer SLB = 16,           // log2 words of the stream-0 landing region (top of the local memory)
    parameter integer MUT_DIRTY = 0,      // mutant: drain whole sectors (overwrites words the op did not write)
    parameter integer LQ = 8,             // credits a wide lane holds (= the VM lane queue depth)
    parameter integer MUT_W = 0,          // bench mutants: 1 stage lands every sector at its lane's first slot (no
                                          //   advance), 2 the drain skips the last sector of each lane, 3 the record
                                          //   retires before its drain writes are in VM (no done wait), 4 no source / live-sink hazard check
                                          //   (a record stages an operand an older record has not drained yet)
    parameter integer SLICES = 0,         // el1011-hbm-sfu: 1 = 4 hardened 8-lane slices + 2-stage reduction hub, 2 = and
                                          //   the lanes' landing FIFOs in 64x16 SRAM (default 0: flat)
    parameter integer OVL = 1             // 1: three-slot record pipeline (span + stage | run | drain overlap); 0: one
                                          //   record at a time (each slot waits for the younger ones to empty)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    // STREAM 0 (SM -> SU): element idx of the stream (slot x M + row) and its value; lands in the stream region
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    // STREAM to ARGMAX (the 523-b su_red stream: {bias_en, bias 256, vals 256, mask 8, last, v}); am_rdy = the argmax
    // unit holds a STREAM record (it consumes every beat once busy)
    output reg  [522:0]  am_stream,
    input  wire          am_rdy,
    // the stream unit (ot_hdc_v41x_vec): go / ready / idle / fault, the relocated op word
    output reg           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output reg  [669:0]  wl,
    // the local memory (ot_hgi_su_lmem__d4g_sfu; on the die the r25 operand macros): every port registered here
    output reg           sl_v,                // a STREAM 0 word lands
    output reg  [LWB-1:0] sl_addr,
    output reg  [31:0]   sl_data,
    output reg           sw_v,                // a staged sector (8 words, local sector address)
    output reg  [LWB-4:0] sw_sec,
    output reg  [255:0]  sw_data,
    output reg           dc_v,                // clear a sector's dirty mask
    output reg  [LWB-4:0] dc_sec,
    output reg           sr_v,                // read a sector: words + dirty mask, one edge later
    output reg  [LWB-4:0] sr_sec,
    input  wire [255:0]  sr_data,
    input  wire [7:0]    sr_dm,
    // WIDE STAGE / DRAIN (hgi-unitrate 2026-10-10): 32 lanes, lane b <-> VM bank b <-> local bank b (every region is
    // placed with lb == lo mod 256 words, so a VM sector and its local copy share the bank: no crossbar)
    output wire  [`OT_CTLW_NLP*16-1:0]  wrq,          // VM wide read lane b {v, sector 15}: LQ credits a lane
    input  wire [`OT_CTLW_NLP-1:0]       wrq_cr,       // a credit back (the request reached its bank)
    input  wire [`OT_CTLW_NLP*257-1:0] wrr,          // the sector {v, data 256}, in request order
    output wire  [`OT_CTLW_NLP*280-1:0] wwq,          // VM wide write lane b {v, sector 15, wdata 256, word mask 8}
    input  wire [`OT_CTLW_NLP-1:0]       wwq_cr,       // a credit back (the write reached its bank)
    input  wire [`OT_CTLW_NLP-1:0]       wwq_done,     // a write in the macro (the record retires after the last)
    // shared lane groups (ot_hgi_vm_lanearb): a burst (a record's stage / drain) holds its group from grant to release;
    // tie the grants high for a dedicated group
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt,
    output wire  [`OT_CTLW_NLP-1:0]       lsw_v,        // local stage write lane b (sector, data)
    output wire  [`OT_CTLW_NLP*(LWB-3)-1:0] lsw_sec,
    output wire  [`OT_CTLW_NLP*256-1:0] lsw_d,
    output wire  [`OT_CTLW_NLP-1:0]       ldc_v,        // local dirty clear lane b
    output wire  [`OT_CTLW_NLP*(LWB-3)-1:0] ldc_sec,
    output wire  [`OT_CTLW_NLP-1:0]       ldr_v,        // local drain read lane b: {data, dirty mask} one edge later
    output wire  [`OT_CTLW_NLP*(LWB-3)-1:0] ldr_sec,
    input  wire [`OT_CTLW_NLP*256-1:0] ldr_d,
    input  wire [`OT_CTLW_NLP*8-1:0]   ldr_dm,
    input  wire [`OT_CTLW_NLP-1:0]       ldr_rv,       // the lane's drain read data is valid (any latency, in request order)
    input  wire              sr_rv         // the STREAM-out sector read data is valid
`ifdef OT_CTLW_HEAD_EXT
    // the edge-registered nearest-neighbour link to slice tile 1 (descriptor / go forward from slice 0's pin registers,
    // the done / overflow combine back into slice 0's pin flops)
    , output wire c_wst_go, output wire c_wdr_go, output wire c_d_os,
    output wire [6*24-1:0] c_lo, output wire [6*24-1:0] c_hi, output wire [6*(LWB+1)-1:0] c_lb, output wire [5:0] c_rv,
    output wire [6*21-1:0] c_dsec, output wire [2*24-1:0] c_dlo, output wire [2*24-1:0] c_dhi,
    output wire [2*(LWB+1)-1:0] c_dlb, output wire [1:0] c_drv, output wire [2*21-1:0] c_ddsec,
    input  wire c_wst_dn, input wire c_wdr_dn, input wire c_ovf
`endif
);
    localparam integer AW = 24, NR = N / 8, LW = 1 << LWB;
    // ---- the record adapter (decode) and the op it issues
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r;
    wire [1:0] strm;
    reg su_ret;
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET), .PIPED(1)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o),
        .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .drained(), .op_strm(strm), .lg_v(1'b0), .lg_rdy(), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w),
        .su_idle(su_idle_r), .su_fault(su_fault_r), .su_ret(su_ret));
    // ---- the op word (PFIELDS) fields
    reg [669:0] w;
    wire [15:0] no = w[0 +: 16], ni = w[16 +: 16];
    wire [1:0]  aind = w[136 +: 2], dst = w[380 +: 2], red = w[478 +: 2];
    wire        bhalf = w[210], cpair = w[283], redwhole = w[481], redtree = w[482];
    wire [2:0]  m1 = w[360 +: 3], qm = w[365 +: 3], ad = w[368 +: 3], e1 = w[374 +: 3];
    wire [1:0]  m2 = w[363 +: 2], e2 = w[377 +: 2];
    wire use_b = (m1 == 3'd1) || (m1 == 3'd4) || (m1 == 3'd6) || (ad == 3'd3) || (e2 == 2'd1);
    wire use_c = !cpair && ((m2 == 2'd1) || (qm != 3'd0) || (ad == 3'd1) || (ad == 3'd2) || (e1 == 3'd1) || (e1 == 3'd2));
    wire use_d = (qm != 3'd0) || (ad == 3'd5);
    // region k: 0 A, 1 B, 2 C, 3 D (sources), 4 O, 5 R (sinks); base / so / si offsets in the word
    function automatic [23:0] fb(input integer k);
        case (k) 0: fb = 40; 1: fb = 138; 2: fb = 211; 3: fb = 284; 4: fb = 382; default: fb = 484; endcase
    endfunction
    reg [2:0] rk;                                         // region walk
    reg [23:0] base_k, so_k, si_k; reg [15:0] nr_k, ni_k; reg used_k;
    always @* begin
        case (rk)
            3'd0: begin base_k = w[40 +: 24];  so_k = w[64 +: 24];  si_k = w[88 +: 24];  used_k = 1'b1; end
            3'd1: begin base_k = w[138 +: 24]; so_k = w[162 +: 24]; si_k = w[186 +: 24]; used_k = use_b; end
            3'd2: begin base_k = w[211 +: 24]; so_k = w[235 +: 24]; si_k = w[259 +: 24]; used_k = use_c; end
            3'd3: begin base_k = w[284 +: 24]; so_k = w[308 +: 24]; si_k = w[332 +: 24]; used_k = use_d; end
            3'd4: begin base_k = w[382 +: 24]; so_k = w[406 +: 24]; si_k = w[430 +: 24]; used_k = (dst == 2'd1); end
            default: begin base_k = w[484 +: 24]; so_k = w[508 +: 24]; si_k = 24'd0; used_k = (red != 2'd0); end
        endcase
        nr_k = (rk == 3'd5) ? ((redwhole || redtree) ? 16'd1 : no) : no;
        ni_k = (rk == 3'd5) ? 16'd1 : ((bhalf && (rk == 3'd1 || rk == 3'd3)) ? ((ni + 16'd1) >> 1) : ni);
    end
    // ---- span / relocation per region
    reg [23:0] lo [0:5]; reg [23:0] hi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5];
    reg [LWB:0] alloc;
    reg [39:0] macc; reg [4:0] mbit; reg [1:0] mph;        // (nr - 1) so + (ni - 1) si
    reg [15:0] ma, mc; reg [23:0] mb, md; reg [31:0] pp0, pp1, pp2, pp3;
    reg [23:0] span_hi;
    // ---- VM traffic
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [2:0] outst; reg [26:0] q_sec [0:3]; reg [1:0] q_h, q_t;  // outstanding requests (sectors), in order
    reg [26:0] cur_sec, end_sec;
    reg [3:0] st;
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_RUN = 6, S_RUNW = 7,
                     S_DRAIN = 8, S_DRW = 9, S_DONE = 10, S_FAULT = 11, S_SOUT = 12;
    reg [2:0] dk;                                         // drain region (4 O, 5 R)
    reg [26:0] rsec_d, rsec_d2, rsec_d3; reg so_w;
    reg [3:0] rp;                                         // read pipe: a sector read is in flight
    // Local-memory return pin registers; advance data, mask, valid and sector identity together.
    reg [255:0] sr_data_q; reg [7:0] sr_dm_q;
    reg sr_rv_q;
    always @(posedge clk) begin sr_data_q <= sr_data; sr_dm_q <= sr_dm; end
    always @(posedge clk or negedge rst_n) if (!rst_n) sr_rv_q <= 1'b0; else sr_rv_q <= sr_rv;
    reg [255:0] rd_hold; reg [7:0] rd_dm_hold;
    // ---- STREAM 0 landing (top SW words of the local memory) and the op's stream flags
    localparam integer SW = 1 << SLB;
    localparam [LWB:0] SBASE = LW - SW;
    reg [20:0] scount; reg a_s, o_s; reg s_clr;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot; reg [20:0] ebeat; reg [LWB:0] o_lb; reg amr_q;
    always @(posedge clk) amr_q <= am_rdy;

    // RUN slot
    reg r_v, r_gop, r_cdone, r_as, r_os, r_ser; reg [15:0] r_no, r_ni; reg [LWB:0] r_rs, r_re;
    reg [23:0] r_lo [4:5]; reg [23:0] r_hi [4:5]; reg [LWB:0] r_lb [4:5]; reg r_rv [4:5]; reg [20:0] r_dsec [4:5];
    // DRAIN slot
    reg d_v, d_go, d_as, d_os, d_ser; reg [15:0] d_no, d_ni; reg [LWB:0] d_rs, d_re;
    reg [23:0] d_lo [4:5]; reg [23:0] d_hi [4:5]; reg [LWB:0] d_lb [4:5]; reg d_rv [4:5]; reg [20:0] d_dsec [4:5];
    reg [1:0] d_ph;                                       // 0 start, 1 lanes, 2 STREAM out
    // =================================================================================================================
    // WIDE LANES.  Lane b owns the sectors of bank b (sector mod 32) of every region.  Stage: per source region the
    // lane issues its sectors (LQ credits), the responses land in order into local bank b (a per-lane FIFO of the
    // local sector each request lands at); the same lane clears the dirty masks of its sink sectors.  Drain: per sink
    // region the lane reads its local sectors {data, dirty}, and writes each dirty one (word-masked) to VM.
    // =================================================================================================================
    localparam integer LSW = LWB - 3, QB = $clog2(LQ);
    reg [20:0] dsec [0:5];                                 // local sector - VM sector, per region
    reg wst_go, wdr_go;
    // flat lane outputs (SLICES = 0) / sliced (SLICES != 0)
    reg  [32*16-1:0] wrq_f; reg [32*280-1:0] wwq_f; reg [31:0] lsw_v_f; reg [32*(LWB-3)-1:0] lsw_sec_f;
    reg  [32*256-1:0] lsw_d_f; reg [31:0] ldc_v_f; reg [32*(LWB-3)-1:0] ldc_sec_f; reg [31:0] ldr_v_f;
    reg  [32*(LWB-3)-1:0] ldr_sec_f;
    wire wst_done, wdr_done, lane_ovf;
    reg [273:0] vr_unused;
    reg [31:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [32*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg [32*256-1:0] ldr_d_q; reg [32*8-1:0] ldr_dm_q;
    reg [31:0] ldr_rv_q;
    always @(posedge clk) begin ldr_d_q <= ldr_d; ldr_dm_q <= ldr_dm; end
    always @(posedge clk or negedge rst_n) if (!rst_n) ldr_rv_q <= '0; else ldr_rv_q <= ldr_rv;
    // drain reads are VALID-driven: each lane keeps the VM sector of every read in flight (in order); a returned
    // {data, dirty} (ldr_rv, pin-flopped) pops it, whatever the memory latency
    reg [20:0] dq_s [0:31][0:LQ-1]; reg [QB-1:0] dq_h [0:31], dq_t [0:31]; reg [QB:0] dq_n [0:31];
    // per-lane state
    reg [2:0]  sg_r [0:31]; reg sg_on [0:31]; reg [20:0] sg_nx [0:31]; reg [20:0] sg_end [0:31];
    // landing FIFO: LQ queued at the VM + the accepted-not-landed pipe (VM core + relays): power of two >= 2 LQ + 32
    localparam integer LFB = $clog2(2 * LQ + 32), LFD = 1 << LFB;
    reg [QB:0] cr [0:31]; reg [LSW-1:0] lq [0:31][0:LFD-1]; reg [LFB-1:0] lqh [0:31], lqt [0:31]; reg [LFB:0] lqn [0:31];
    reg [5:0] wpend [0:31]; reg lane_ovf_f;
    reg [2:0]  cl_r [0:31]; reg cl_on [0:31]; reg [LSW-1:0] cl_nx [0:31]; reg [LSW-1:0] cl_end [0:31];
    reg [2:0]  dg_r [0:31]; reg dg_on [0:31]; reg [LSW-1:0] dg_nx [0:31]; reg [LSW-1:0] dg_end [0:31];
    reg [QB:0] wcr [0:31]; reg [31:0] dp1, dp2, dp3; reg [20:0] dp1_s [0:31]; reg [20:0] dp2_s [0:31]; reg [20:0] dp3_s [0:31];
    reg [31:0] wst_ldone, wdr_ldone;
    wire wst_done_f = &wst_ldone, wdr_done_f = &wdr_ldone;
    function automatic [20:0] first_of(input [20:0] lo_s, input integer b);
        first_of = lo_s + 21'((5'(b) - lo_s[4:0]) & 5'd31);
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wrq_f <= '0; wwq_f <= '0; lsw_v_f <= '0; ldc_v_f <= '0; ldr_v_f <= '0; dp1 <= '0; dp2 <= '0; dp3 <= '0;
            for (integer b = 0; b < 32; b = b + 1) begin dq_h[b] <= '0; dq_t[b] <= '0; dq_n[b] <= '0; end
            wst_ldone <= '1; wdr_ldone <= '1; lane_ovf_f <= 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin
                sg_r[b] <= 3'd7; sg_on[b] <= 1'b0; cl_r[b] <= 3'd7; cl_on[b] <= 1'b0; dg_r[b] <= 3'd7; dg_on[b] <= 1'b0;
                cr[b] <= (QB+1)'(LQ); wcr[b] <= (QB+1)'(LQ); lqh[b] <= '0; lqt[b] <= '0; lqn[b] <= '0; wpend[b] <= '0;
            end
        end else begin
            for (integer b = 0; b < 32; b = b + 1) begin : lane
                reg iss, land, dr_iss, wsend, wfree;
                reg [20:0] f;
                iss = 1'b0; land = 1'b0; dr_iss = 1'b0; wsend = 1'b0; wfree = 1'b0;
                wrq_f[b*16 + 15] <= 1'b0; lsw_v_f[b] <= 1'b0; ldc_v_f[b] <= 1'b0; ldr_v_f[b] <= 1'b0; wwq_f[b*280 + 279] <= 1'b0;
                // ---------------- stage: source region walk (regions 0..3)
                if (wst_go) begin sg_r[b] <= 3'd0; sg_on[b] <= 1'b0; cl_r[b] <= 3'd4; cl_on[b] <= 1'b0; wst_ldone[b] <= 1'b0; end
                else if (sg_r[b] < 3'd4) begin
                    if (!sg_on[b]) begin
                        f = first_of(21'(lo[sg_r[b]] >> 3), b);
                        if (rv[sg_r[b]] && f <= 21'(hi[sg_r[b]] >> 3)) begin
                            sg_nx[b] <= f; sg_end[b] <= 21'(hi[sg_r[b]] >> 3); sg_on[b] <= 1'b1;
                        end else sg_r[b] <= sg_r[b] + 3'd1;
                    end else if (cr[b] != 0) begin
                        iss = 1'b1;
                        wrq_f[b*16 +: 16] <= {1'b1, sg_nx[b][14:0]};
                        lq[b][lqt[b]] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        lqt[b] <= lqt[b] + 1'b1;
                        if (sg_nx[b] + 21'd32 > sg_end[b]) begin sg_on[b] <= 1'b0; sg_r[b] <= sg_r[b] + 3'd1; end
                        else sg_nx[b] <= sg_nx[b] + 21'd32;
                    end
                end
                // responses land in request order
                if (wrr_q[b*257 + 256]) begin
                    land = 1'b1;
                    lsw_v_f[b] <= 1'b1; lsw_sec_f[b*LSW +: LSW] <= (MUT_W == 1) ? lq[b][0] : lq[b][lqh[b]];
                    lsw_d_f[b*256 +: 256] <= wrr_q[b*257 +: 256];
                    lqh[b] <= lqh[b] + 1'b1;
                end
                lqn[b] <= lqn[b] + iss - land;
                if (lqn[b] == (LFB+1)'(LFD) && iss && !land) lane_ovf_f <= 1'b1;
                cr[b] <= cr[b] - iss + wrq_cr_q[b];
                // sink dirty-mask clears (regions 4, 5; the local span), one sector a lane an edge
                if (!wst_go && cl_r[b] < 3'd6) begin
                    if (!cl_on[b]) begin
                        f = first_of(21'(lb[cl_r[b]] >> 3), b);
                        if (rv[cl_r[b]] && f <= 21'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3)) begin
                            cl_nx[b] <= LSW'(f); cl_end[b] <= LSW'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3);
                            cl_on[b] <= 1'b1;
                        end else cl_r[b] <= cl_r[b] + 3'd1;
                    end else begin
                        ldc_v_f[b] <= 1'b1; ldc_sec_f[b*LSW +: LSW] <= cl_nx[b];
                        if (21'(cl_nx[b]) + 21'd32 > 21'(cl_end[b])) begin cl_on[b] <= 1'b0; cl_r[b] <= cl_r[b] + 3'd1; end
                        else cl_nx[b] <= cl_nx[b] + LSW'(32);
                    end
                end
                if (!wst_go && sg_r[b] >= 3'd4 && sg_r[b] != 3'd7 && cl_r[b] >= 3'd6 &&
                    ((lqn[b] + iss - land) == 0 && (cr[b] - iss + wrq_cr_q[b]) == (QB+1)'(LQ))) wst_ldone[b] <= 1'b1;
                // ---------------- drain: sink regions 4 (O, unless STREAM) and 5 (R)
                if (wdr_go) begin dg_r[b] <= 3'd4; dg_on[b] <= 1'b0; wdr_ldone[b] <= 1'b0; end
                else if (dg_r[b] < 3'd6) begin
                    if (!dg_on[b]) begin
                        f = first_of(21'(d_lb[dg_r[b]] >> 3), b);
                        if (d_rv[dg_r[b]] && !(dg_r[b] == 3'd4 && d_os) &&
                            f <= 21'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3)) begin
                            dg_nx[b] <= LSW'(f); dg_end[b] <= LSW'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3);
                            dg_on[b] <= 1'b1;
                        end else dg_r[b] <= dg_r[b] + 3'd1;
                    end else if (wcr[b] != 0) begin
                        if (!(MUT_W == 2 && 21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b]))) begin
                            dr_iss = 1'b1;
                            ldr_v_f[b] <= 1'b1; ldr_sec_f[b*LSW +: LSW] <= dg_nx[b];
                            dq_s[b][dq_t[b]] <= 21'(dg_nx[b]) - d_dsec[dg_r[b]]; dq_t[b] <= dq_t[b] + 1'b1;
                        end
                        if (21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b])) begin dg_on[b] <= 1'b0; dg_r[b] <= dg_r[b] + 3'd1; end
                        else dg_nx[b] <= dg_nx[b] + LSW'(32);
                    end
                end
                // read return: valid-driven (ldr_rv pin flop), the sector identity from the lane's in-flight FIFO
                begin : wpub
                    reg [7:0] mk; reg v3; reg [20:0] s3;
                    mk = MUT_DIRTY ? 8'hFF : ldr_dm_q[b*8 +: 8];
                    v3 = ldr_rv_q[b]; s3 = dq_s[b][dq_h[b]];
                    if (v3) dq_h[b] <= dq_h[b] + 1'b1;
                    dq_n[b] <= dq_n[b] + dr_iss - v3;
                    if (v3) begin
                        if (mk != 8'd0) begin
                            wsend = 1'b1;
                            wwq_f[b*280 +: 280] <= {1'b1, s3[14:0], ldr_d_q[b*256 +: 256], mk};
                        end else wfree = 1'b1;
                    end
                end
                wcr[b] <= wcr[b] - dr_iss + wfree + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend - wwq_done_q[b];
                if (!wdr_go && dg_r[b] >= 3'd6 && dg_r[b] != 3'd7 && !dr_iss && (dq_n[b] - ldr_rv_q[b]) == 0 &&
                    (MUT_W == 3 || ((wpend[b] + wsend - wwq_done_q[b]) == 0 && (wcr[b] - dr_iss + wfree + wwq_cr_q[b]) == (QB+1)'(LQ)))) wdr_ldone[b] <= 1'b1;
            end
        end
    end
    // ---- SLICES (el1011-hbm-sfu, default off): four hardened 8-lane slices + a two-stage registered reduction hub
    generate if (SLICES != 0) begin : g_slices
        wire [3:0] s_wst, s_wdr, s_ovf;
        wire [6*24-1:0] lo_v, hi_v; wire [6*(LWB+1)-1:0] lb_v; wire [5:0] rv_v; wire [6*21-1:0] dsec_v;
        wire [2*24-1:0] dlo_v, dhi_v; wire [2*(LWB+1)-1:0] dlb_v; wire [1:0] drv_v; wire [2*21-1:0] ddsec_v;
        for (genvar q = 0; q < 6; q = q + 1) begin : g_rq
            assign lo_v[q*24 +: 24] = lo[q]; assign hi_v[q*24 +: 24] = hi[q]; assign lb_v[q*(LWB+1) +: LWB+1] = lb[q];
            assign rv_v[q] = rv[q]; assign dsec_v[q*21 +: 21] = dsec[q];
        end
        for (genvar q = 4; q < 6; q = q + 1) begin : g_dq
            assign dlo_v[(q-4)*24 +: 24] = d_lo[q]; assign dhi_v[(q-4)*24 +: 24] = d_hi[q];
            assign dlb_v[(q-4)*(LWB+1) +: LWB+1] = d_lb[q]; assign drv_v[q-4] = d_rv[q]; assign ddsec_v[(q-4)*21 +: 21] = d_dsec[q];
        end
        // GLUE PLACEMENT (owner 10-11 ~19:15): no hub.  The slices form a chain of edge-registered nearest-neighbour
        // links: descriptors / go forward (slice g's pin registers drive slice g+1's pin registers, one edge a hop),
        // done / overflow combine backward (slice g pin-flops slice g+1's combined flags, ANDs / ORs its own, registers
        // the result: two edges a hop).  Slice 0's combined flags are the whole unit's.
        localparam integer NSL = 4;
        wire [NSL:0] c_go_s, c_go_d, c_os;
        wire [6*24-1:0] c_lo_v [0:NSL]; wire [6*24-1:0] c_hi_v [0:NSL]; wire [6*(LWB+1)-1:0] c_lb_v [0:NSL];
        wire [5:0] c_rv_v [0:NSL]; wire [6*21-1:0] c_dsec_v [0:NSL]; wire [2*24-1:0] c_dlo_v [0:NSL];
        wire [2*24-1:0] c_dhi_v [0:NSL]; wire [2*(LWB+1)-1:0] c_dlb_v [0:NSL]; wire [1:0] c_drv_v [0:NSL];
        wire [2*21-1:0] c_ddsec_v [0:NSL];
        wire [NSL:0] dn_st, dn_dr, dn_ov;           // dn_*[g]: slice g's combined flags (g .. NSL-1); [NSL] = the chain end
        assign c_go_s[0] = wst_go; assign c_go_d[0] = wdr_go; assign c_os[0] = d_os;
        assign c_lo_v[0] = lo_v; assign c_hi_v[0] = hi_v; assign c_lb_v[0] = lb_v; assign c_rv_v[0] = rv_v;
        assign c_dsec_v[0] = dsec_v; assign c_dlo_v[0] = dlo_v; assign c_dhi_v[0] = dhi_v; assign c_dlb_v[0] = dlb_v;
        assign c_drv_v[0] = drv_v; assign c_ddsec_v[0] = ddsec_v;
`ifdef OT_CTLW_HEAD_EXT
        localparam integer NIN = 1;                 // the head tile holds slice 0; slices 1..3 are die-placed tiles
        assign c_wst_go = c_go_s[1]; assign c_wdr_go = c_go_d[1]; assign c_d_os = c_os[1];
        assign c_lo = c_lo_v[1]; assign c_hi = c_hi_v[1]; assign c_lb = c_lb_v[1]; assign c_rv = c_rv_v[1];
        assign c_dsec = c_dsec_v[1]; assign c_dlo = c_dlo_v[1]; assign c_dhi = c_dhi_v[1]; assign c_dlb = c_dlb_v[1];
        assign c_drv = c_drv_v[1]; assign c_ddsec = c_ddsec_v[1];
        assign dn_st[1] = c_wst_dn; assign dn_dr[1] = c_wdr_dn; assign dn_ov[1] = c_ovf;
`else
        localparam integer NIN = NSL;
        assign dn_st[NSL] = 1'b1; assign dn_dr[NSL] = 1'b1; assign dn_ov[NSL] = 1'b0;
`endif
        for (genvar g = 0; g < NIN; g = g + 1) begin : g_s
`ifdef OT_CTLW_SLICE_H   // el1013-hbm-qdq opt-in (default off): the slice as the physical cluster of four hard 2-lane leaves
            ot_hgi_su_ctlw_slice_h #(.SL(g), .NL(8), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_slice (
`else
            ot_hgi_su_ctlw_slice__d4g_sfu #(.SL(g), .NL(8), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(SLICES >= 2 ? 1 : 0)) u_slice (
`endif
                .clk(clk), .rst_n(rst_n), .sl_i(2'(g)), .wst_go_i(c_go_s[g]), .wdr_go_i(c_go_d[g]),
                .lo_i(c_lo_v[g]), .hi_i(c_hi_v[g]), .lb_i(c_lb_v[g]), .rv_i(c_rv_v[g]), .dsec_i(c_dsec_v[g]),
                .d_lo_i(c_dlo_v[g]), .d_hi_i(c_dhi_v[g]), .d_lb_i(c_dlb_v[g]), .d_rv_i(c_drv_v[g]), .d_dsec_i(c_ddsec_v[g]), .d_os_i(c_os[g]),
                .wst_go_o(c_go_s[g+1]), .wdr_go_o(c_go_d[g+1]), .lo_o(c_lo_v[g+1]), .hi_o(c_hi_v[g+1]), .lb_o(c_lb_v[g+1]),
                .rv_o(c_rv_v[g+1]), .dsec_o(c_dsec_v[g+1]), .d_lo_o(c_dlo_v[g+1]), .d_hi_o(c_dhi_v[g+1]), .d_lb_o(c_dlb_v[g+1]),
                .d_rv_o(c_drv_v[g+1]), .d_dsec_o(c_ddsec_v[g+1]), .d_os_o(c_os[g+1]),
                .wst_dn_i(dn_st[g+1]), .wdr_dn_i(dn_dr[g+1]), .ovf_i(dn_ov[g+1]),
                .wrq(wrq[g*8*16 +: 8*16]), .wrq_cr(wrq_cr[g*8 +: 8]), .wrr(wrr[g*8*257 +: 8*257]),
                .wwq(wwq[g*8*280 +: 8*280]), .wwq_cr(wwq_cr[g*8 +: 8]), .wwq_done(wwq_done[g*8 +: 8]),
                .lsw_v(lsw_v[g*8 +: 8]), .lsw_sec(lsw_sec[g*8*(LWB-3) +: 8*(LWB-3)]), .lsw_d(lsw_d[g*8*256 +: 8*256]),
                .ldc_v(ldc_v[g*8 +: 8]), .ldc_sec(ldc_sec[g*8*(LWB-3) +: 8*(LWB-3)]),
                .ldr_v(ldr_v[g*8 +: 8]), .ldr_sec(ldr_sec[g*8*(LWB-3) +: 8*(LWB-3)]),
                .ldr_d(ldr_d[g*8*256 +: 8*256]), .ldr_dm(ldr_dm[g*8*8 +: 8*8]), .ldr_rv(ldr_rv[g*8 +: 8]),
                .wst_dn(dn_st[g]), .wdr_dn(dn_dr[g]), .ovf(dn_ov[g]));
        end
        // go blanking: a done seen within BL edges of its go belongs to the previous burst.  Worst path, slice 3: go
        // ctlw -> s0 .. s3 pins (4), lane done (1), s3 combine (1), back s2 / s1 / s0 (2 each: 6), the capture here (1)
        // = 13 (the single-slice hub path was 4 with BL 6): BL = 15
`ifdef OT_CTLW_SLICE_H
        // slice_h: 3 forward edges a hop and 4 back (N-face flag flop, leaf pin flop, leaf flag, AND4): go -> s3 f0 (10),
        // fm (11), leaf pin flop (12), lane done (13), leaf flag (14), s3 AND4 (15), back s2 / s1 / s0 (4 each: 27),
        // the capture here (28): BL = 30
        localparam integer BL = 30;
        reg h_wst, h_wdr, h_ovf; reg [4:0] bl_st, bl_dr;
`else
        localparam integer BL = 15;
        reg h_wst, h_wdr, h_ovf; reg [3:0] bl_st, bl_dr;
`endif
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin h_wst <= 1'b1; h_wdr <= 1'b1; h_ovf <= 1'b0; bl_st <= '0; bl_dr <= '0; end
            else begin
                h_wst <= dn_st[0]; h_wdr <= dn_dr[0]; h_ovf <= dn_ov[0];
`ifdef OT_CTLW_SLICE_H
                bl_st <= wst_go ? 5'(BL) : (bl_st != 0 ? bl_st - 5'd1 : 5'd0);
                bl_dr <= wdr_go ? 5'(BL) : (bl_dr != 0 ? bl_dr - 5'd1 : 5'd0);
`else
                bl_st <= wst_go ? 4'(BL) : (bl_st != 0 ? bl_st - 4'd1 : 4'd0);
                bl_dr <= wdr_go ? 4'(BL) : (bl_dr != 0 ? bl_dr - 4'd1 : 4'd0);
`endif
            end
        assign wst_done = h_wst && bl_st == 0 && !wst_go;
        assign wdr_done = h_wdr && bl_dr == 0 && !wdr_go;
        assign lane_ovf = h_ovf;
    end else begin : g_flat
        assign wrq = wrq_f; assign wwq = wwq_f; assign lsw_v = lsw_v_f; assign lsw_sec = lsw_sec_f; assign lsw_d = lsw_d_f;
        assign ldc_v = ldc_v_f; assign ldc_sec = ldc_sec_f; assign ldr_v = ldr_v_f; assign ldr_sec = ldr_sec_f;
        assign wst_done = wst_done_f; assign wdr_done = wdr_done_f; assign lane_ovf = lane_ovf_f;
    end endgenerate
    // =================================================================================================================
    // RECORD PIPELINE (OVL): three slots.  FRONT: decode -> extents (pipelined multiply) -> local allocation (a ring
    // over [0, SBASE): a record's regions sit after the previous record's, wrapping to 0, never over a live record's)
    // -> placement -> wait until no source region overlaps the VM sink span of an older record not yet drained (its
    // results must be read from VM after they land there) -> wide stage.  RUN: the vec (go when ready) on the staged
    // record.  DRAIN: the wide drain (or the STREAM-out to ARGMAX), then the in-order retire pulse (su_ret).  A FRONT
    // record stages while an older one runs or drains; RUN starts while an older one drains (its sinks are other local
    // words; its drain follows the older drain, so VM write order is program order).  STREAM records (A from STREAM 0,
    // O to ARGMAX) run alone (the landing region and its count belong to one record).
    // =================================================================================================================
    reg ready_q, idle_q, vfault_q, rg_q, wg_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req; end
    end
    reg vf_seen; reg [1:0] idle_ph;
    reg [669:0] fw;                                       // FRONT: the relocated op word being built
    reg [LWB:0] f_rs, ap; reg [LWB+1:0] fsize; reg f_ser;
    // census (bench): which slots are busy this edge
    wire a_span = (st == S_SPAN || st == S_MUL || st == S_NEXTR || st == S_STAGE);
    wire a_stage = (st == S_STW);
    wire a_run = r_v && !r_cdone;
    wire a_drain = d_v;
    // live-range / hazard predicates for the FRONT record
    function automatic ovl_r(input [LWB:0] a0, input [LWB:0] a1, input [LWB:0] b0, input [LWB:0] b1);
        ovl_r = (a0 < b1) && (b0 < a1);
    endfunction
    function automatic ovl_v(input [23:0] a0, input [23:0] a1, input [23:0] b0, input [23:0] b1);
        ovl_v = (a0 <= b1) && (b0 <= a1);                 // inclusive word spans
    endfunction
    wire [LWB:0] fb_try = ({1'b0, ap} + fsize <= {2'b0, SBASE}) ? ap : '0;
    wire alloc_ok = !(r_v && ovl_r(fb_try, LWB'(fb_try + fsize), r_rs, r_re)) &&
                    !(d_v && ovl_r(fb_try, LWB'(fb_try + fsize), d_rs, d_re)) &&
                    ({1'b0, fb_try} + fsize <= {2'b0, SBASE}) &&
                    (!f_ser || (!r_v && !d_v)) && !(r_v && r_ser) && !(d_v && d_ser) && (OVL != 0 || (!r_v && !d_v));
    reg haz;
    always @* begin
        haz = 1'b0;
        for (integer q = 0; q < 4; q = q + 1) if (rv[q]) begin
            for (integer k = 4; k < 6; k = k + 1) begin
                if (r_v && r_rv[k] && !(k == 4 && r_os) && ovl_v(lo[q], hi[q], r_lo[k], r_hi[k])) haz = 1'b1;
                if (d_v && d_rv[k] && !(k == 4 && d_os) && ovl_v(lo[q], hi[q], d_lo[k], d_hi[k])) haz = 1'b1;
            end
        end
        if (MUT_W == 4) haz = 1'b0;
    end
    wire [LWB:0] lbk = alloc + (LWB+1)'((lo[rk][7:0] - alloc[7:0]) & 8'hFF);   // lb == lo (mod 256 words): bank-aligned
    localparam [3:0] S_WAITA = 4'd13, S_RDY = 4'd14;
    integer k2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; go <= 1'b0; vmq <= 338'd0; su_ret <= 1'b0;
            sl_v <= 1'b0; sw_v <= 1'b0; dc_v <= 1'b0; sr_v <= 1'b0; rp <= 4'd0; wst_go <= 1'b0; wdr_go <= 1'b0;
            outst <= 3'd0; q_h <= 2'd0; q_t <= 2'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
            r_v <= 1'b0; r_gop <= 1'b0; r_cdone <= 1'b0; d_v <= 1'b0; d_go <= 1'b0; ap <= '0; r_ser <= 1'b0; d_ser <= 1'b0;
            rg_req <= 1'b0; wg_req <= 1'b0;
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0; su_ret <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            sw_v <= 1'b0; dc_v <= 1'b0; sr_v <= 1'b0; wst_go <= 1'b0; wdr_go <= 1'b0; go <= 1'b0;
            if ((s0v_q && s0i_q >= SW) || lane_ovf) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            s_clr <= 1'b0;
            if (vfault_q && r_v && !r_gop) vf_seen <= 1'b1;
            su_idle_r <= (st == S_IDLE) && !r_v && !d_v;
            // ------------------------------------------------------------------ FRONT
            case (st)
                S_IDLE: begin
                    if (op_v && op_rdy_r) begin
                        w <= op_w; fw <= op_w; op_rdy_r <= 1'b0; rk <= 3'd0; fsize <= '0;
                        a_s <= strm[0]; o_s <= strm[1]; f_ser <= strm[0] | strm[1]; st <= S_SPAN;
                        for (k2 = 0; k2 < 6; k2 = k2 + 1) rv[k2] <= 1'b0;
                    end
                end
                S_SPAN: begin                                       // region rk: used? span start
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    if (rk == 3'd0 && a_s) begin                    // A = STREAM: rows of ni, element o ni + i = idx
                        fw[40 +: 24] <= SBASE; fw[64 +: 24] <= {8'd0, ni}; fw[88 +: 24] <= 24'd1; rk <= rk + 3'd1;
                    end else if (rk == 3'd4 && o_s && a_s && red == 2'd0) begin
                        // O = STREAM over A = STREAM, element-wise: O aliases the stream landing region
                        fw[382 +: 24] <= SBASE; fw[406 +: 24] <= {8'd0, ni}; fw[430 +: 24] <= 24'd1;
                        lb[4] <= SBASE; rv[4] <= 1'b0; rk <= rk + 3'd1;
                    end else if (rk == 3'd4 && o_s) begin           // O = STREAM: a contiguous local region, no drain
                        fw[406 +: 24] <= {8'd0, ni}; fw[430 +: 24] <= 24'd1; w[406 +: 24] <= {8'd0, ni}; w[430 +: 24] <= 24'd1;
                        w[382 +: 24] <= 24'd0; fw[382 +: 24] <= 24'd0; lo[4] <= 24'd0; macc <= 40'd0; mbit <= 5'd0;
                        mph <= 2'd0; rv[4] <= 1'b1; st <= S_MUL;
                    end else if (!used_k) begin
                        if (rk == 3'd5) st <= S_WAITA; else rk <= rk + 3'd1;
                    end else begin
                        lo[rk] <= base_k; macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL;
                    end
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // macc = (nr - 1) so + (ni - 1) si, PIPELINED:
                    // edge 0 operand flops, edge 1 four 8 x 24 partial products, edge 2 their sum, edge 3 the extent
                    if (mph == 2'd0) begin
                        ma <= nr_k - 16'd1; mb <= so_k; mc <= ni_k - 16'd1; md <= si_k; mph <= 2'd1; mbit <= 5'd0;
                    end else if (mph == 2'd1) begin
                        if (mbit == 5'd0) begin
                            pp0 <= ma[7:0] * mb; pp1 <= ma[15:8] * mb; pp2 <= mc[7:0] * md; pp3 <= mc[15:8] * md;
                            mbit <= 5'd1;
                        end else begin
                            macc <= {8'd0, pp0} + {pp1, 8'd0} + {8'd0, pp2} + {pp3, 8'd0}; mph <= 2'd2;
                        end
                    end else begin
                        // c_pair reads A[e ^ 1]: widen A to whole pairs
                        if (rk == 3'd0 && cpair) begin
                            lo[0] <= base_k & ~24'd1; hi[0] <= (base_k + macc[23:0]) | 24'd1;
                            fsize <= fsize + (LWB+2)'(((base_k + macc[23:0]) | 24'd1) - (base_k & ~24'd1)) + 265;
                        end else begin
                            hi[rk] <= base_k + macc[23:0];
                            fsize <= fsize + (LWB+2)'(base_k + macc[23:0] - lo[rk]) + 265;   // span + guard 8 + align 256
                        end
                        if (rk == 3'd5) st <= S_WAITA; else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_WAITA: if (alloc_ok) begin                         // a free local range for the whole record
                    alloc <= fb_try; f_rs <= fb_try; rk <= 3'd0; st <= S_NEXTR;
                end
                S_NEXTR: begin                                      // place region rk, relocate its base
                    if (rv[rk]) begin
                        lb[rk] <= lbk;
                        alloc <= lbk + (hi[rk] - lo[rk]) + 1 + 8;
                        if (lbk + (hi[rk] - lo[rk]) + 1 > SBASE) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        case (rk)
                            3'd0: fw[40 +: 24]  <= w[40 +: 24]  - lo[0] + lbk;
                            3'd1: fw[138 +: 24] <= w[138 +: 24] - lo[1] + lbk;
                            3'd2: fw[211 +: 24] <= w[211 +: 24] - lo[2] + lbk;
                            3'd3: fw[284 +: 24] <= w[284 +: 24] - lo[3] + lbk;
                            3'd4: fw[382 +: 24] <= w[382 +: 24] - lo[4] + lbk;
                            default: fw[484 +: 24] <= w[484 +: 24] - lo[5] + lbk;
                        endcase
                    end
                    if (!(rv[rk] && lbk + (hi[rk] - lo[rk]) + 1 > SBASE)) begin
                        if (rk == 3'd5) begin rk <= 3'd0; st <= S_STAGE; end
                        else rk <= rk + 3'd1;
                    end
                end
                S_STAGE: begin                                      // sources clear of every older undrained sink?
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) dsec[k2] <= 21'((lb[k2] >> 3) - (lo[k2] >> 3));
                    if (!haz) rg_req <= 1'b1;                       // the read lane group for the stage burst
                    if (!haz && rg_req && rg_q) begin st <= S_STW; wst_go <= 1'b1; ap <= alloc; end
                end
                S_STW: if (!wst_go && wst_done) begin st <= S_RDY; rg_req <= 1'b0; end
                S_RDY: if (!r_v) begin                              // into RUN
                    r_v <= 1'b1; r_gop <= 1'b1; r_cdone <= 1'b0; wl <= fw; r_as <= a_s; r_os <= o_s; r_ser <= f_ser;
                    r_no <= no; r_ni <= ni; r_rs <= f_rs; r_re <= ap;
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        r_lo[k2] <= lo[k2]; r_hi[k2] <= hi[k2]; r_lb[k2] <= lb[k2]; r_rv[k2] <= rv[k2]; r_dsec[k2] <= dsec[k2];
                    end
                    op_rdy_r <= 1'b1; st <= S_IDLE;
                end
                S_FAULT: ;                                           // sticky (the adapter halts)
                default: st <= S_FAULT;
            endcase
            // ------------------------------------------------------------------ RUN
            if (r_v && st != S_FAULT) begin
                if (r_gop) begin
                    if (ready_q && (!r_as || scount >= {5'd0, r_no} * {5'd0, r_ni})) begin
                        go <= 1'b1; r_gop <= 1'b0; idle_ph <= 2'd0; vf_seen <= 1'b0;
                    end
                end else if (!r_cdone) begin
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        else r_cdone <= 1'b1;
                    end
                end else if (!d_v) begin                            // into DRAIN
                    d_v <= 1'b1; d_ph <= 2'd0; d_as <= r_as; d_os <= r_os; d_ser <= r_ser; d_no <= r_no; d_ni <= r_ni;
                    d_rs <= r_rs; d_re <= r_re;
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        d_lo[k2] <= r_lo[k2]; d_hi[k2] <= r_hi[k2]; d_lb[k2] <= r_lb[k2]; d_rv[k2] <= r_rv[k2]; d_dsec[k2] <= r_dsec[k2];
                    end
                    r_v <= 1'b0; r_ser <= 1'b0;
                end
            end
            // ------------------------------------------------------------------ DRAIN
            if (d_v && st != S_FAULT) begin
                case (d_ph)
                    2'd0: if ((d_rv[4] && !d_os) || d_rv[5]) begin
                              wg_req <= 1'b1;                       // the write lane group for the drain burst
                              if (wg_req && wg_q) begin wdr_go <= 1'b1; d_ph <= 2'd1; end
                          end
                          else if (d_os) begin etot <= {5'd0, d_no} * {5'd0, d_ni}; ebeat <= 21'd0; o_lb <= d_lb[4]; rp <= 4'd0;
                                               so_w <= 1'b0; d_ph <= 2'd2; end
                          else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                    2'd1: if (!wdr_go && wdr_done) begin
                              wg_req <= 1'b0;
                              if (d_os) begin etot <= {5'd0, d_no} * {5'd0, d_ni}; ebeat <= 21'd0; o_lb <= d_lb[4]; rp <= 4'd0;
                                              so_w <= 1'b0; d_ph <= 2'd2; end
                              else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                          end
                    default: begin                                  // STREAM out: 8 elements a beat, in element order
                        // one sector read in flight; its data is taken on the memory's valid (any latency)
                        if (amr_q && !so_w) begin
                            sr_v <= 1'b1; sr_sec <= (o_lb + ebeat) >> 3; so_w <= 1'b1;
                        end else if (so_w && sr_rv_q) begin
                            begin : so
                                reg [7:0] mk; integer q;
                                for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                                am_stream <= {1'b0, 256'd0, sr_data_q, mk, (ebeat + 21'd8 >= etot), 1'b1};
                            end
                            so_w <= 1'b0;
                            if (ebeat + 21'd8 >= etot) begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                            else ebeat <= ebeat + 21'd8;
                        end
                    end
                endcase
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Local operand memory with the 32 wide lanes (behavioural; the banked-macro build is sub-agent d's ot_hgi_su_lmem__d4g_sfu
// successor, requirement in hgi-1010.log "b -> d"): ot_hgi_su_lmem__d4g_sfu's ports plus, per lane b (local bank b): a stage
// sector write, a dirty-mask clear and a drain sector read {data, dirty mask} one edge later.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_lmemw__d4g_sfu #(
    parameter integer N = 16, LWB = 17, AW = 24, NR = N / 8,
    parameter integer RLAT = 1,           // bench: drain / STREAM-out read latency (edges); the controller is valid-driven
    parameter integer MUT_RV = 0          // bench mutants: 1 the read valid one edge EARLY, 2 one edge LATE (vs its data)
) (
    input  wire              clk,
    input  wire [N-1:0]      vi_re,
    input  wire [N*AW-1:0]   vi_addr,
    output reg  [N*32-1:0]   vi_q,
    input  wire [4*N-1:0]    rd_re,
    input  wire [4*N*AW-1:0] rd_addr,
    output reg  [4*N*32-1:0] rd_q,
    input  wire [N-1:0]      vm_we,
    input  wire [N*AW-1:0]   vm_waddr,
    input  wire [N*32-1:0]   vm_wdata,
    input  wire [NR-1:0]     res_we,
    input  wire [NR*AW-1:0]  res_addr,
    input  wire [NR*32-1:0]  res_data,
    input  wire              sl_v,
    input  wire [LWB-1:0]    sl_addr,
    input  wire [31:0]       sl_data,
    input  wire              sr_v,
    input  wire [LWB-4:0]    sr_sec,
    output reg  [255:0]      sr_data,
    output reg  [7:0]        sr_dm,
    input  wire [31:0]       lsw_v,
    input  wire [32*(LWB-3)-1:0] lsw_sec,
    input  wire [32*256-1:0] lsw_d,
    input  wire [31:0]       ldc_v,
    input  wire [32*(LWB-3)-1:0] ldc_sec,
    input  wire [31:0]       ldr_v,
    input  wire [32*(LWB-3)-1:0] ldr_sec,
    output reg  [32*256-1:0] ldr_d,
    output reg  [32*8-1:0]   ldr_dm,
    output wire [31:0]       ldr_rv,
    output wire              sr_rv,
    output reg               bank_err          // a lane addressed another bank (controller bug): sticky
);
    localparam integer LW = 1 << LWB, LS = LWB - 3;
    reg [31:0] lm [0:LW-1];
    // read data leaves after RLAT edges: ldr_d / sr_data are the last stage of a delay line, valids alongside
    reg [32*256-1:0] ld_p [1:4]; reg [32*8-1:0] lm_p [1:4]; reg [31:0] lv_p [0:5]; reg [255:0] sd_p [1:4]; reg [7:0] sm_p [1:4]; reg sv_p [0:5];
    reg [32*256-1:0] ld0; reg [32*8-1:0] lm0; reg [255:0] sd0; reg [7:0] sm0;
    always @* begin lv_p[0] = ldr_v; sv_p[0] = sr_v; end
    always @(posedge clk) begin
        lv_p[1] <= lv_p[0]; sv_p[1] <= sv_p[0];
        for (integer q = 2; q <= 4; q = q + 1) begin ld_p[q] <= ld_p[q-1]; lm_p[q] <= lm_p[q-1]; sd_p[q] <= sd_p[q-1]; sm_p[q] <= sm_p[q-1]; end
        for (integer q = 2; q <= 5; q = q + 1) begin lv_p[q] <= lv_p[q-1]; sv_p[q] <= sv_p[q-1]; end
    end
    always @* begin ldr_d = ld_p[RLAT]; ldr_dm = lm_p[RLAT]; sr_data = sd_p[RLAT]; sr_dm = sm_p[RLAT]; end
    localparam integer VL = (MUT_RV == 1) ? RLAT - 1 : (MUT_RV == 2) ? RLAT + 1 : RLAT;
    assign ldr_rv = lv_p[VL]; assign sr_rv = sv_p[VL];
    reg [7:0]  dm [0:LW/8-1];
    integer l, s2, q;
    initial bank_err = 1'b0;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) vi_q[32*l +: 32] <= lm[vi_addr[l*AW +: AW] & (LW - 1)];
            for (s2 = 0; s2 < 4; s2 = s2 + 1)
                if (rd_re[4*l + s2]) rd_q[(4*l + s2)*32 +: 32] <= lm[rd_addr[(4*l + s2)*AW +: AW] & (LW - 1)];
        end
        if (sr_v) begin for (q = 0; q < 8; q = q + 1) sd0[32*q +: 32] = lm[{sr_sec, 3'b000} + q]; sm0 = dm[sr_sec]; end
        sd_p[1] <= sd0; sm_p[1] <= sm0;
        for (l = 0; l < 32; l = l + 1) begin
            if (ldr_v[l]) begin
                for (q = 0; q < 8; q = q + 1) ld0[l*256 + 32*q +: 32] = lm[{ldr_sec[l*LS +: LS], 3'b000} + q];
                lm0[l*8 +: 8] = dm[ldr_sec[l*LS +: LS]];
            end
            ld_p[1][l*256 +: 256] <= ld0[l*256 +: 256]; lm_p[1][l*8 +: 8] <= lm0[l*8 +: 8];
            if ((lsw_v[l] && lsw_sec[l*LS +: 5] != 5'(l)) || (ldc_v[l] && ldc_sec[l*LS +: 5] != 5'(l)) ||
                (ldr_v[l] && ldr_sec[l*LS +: 5] != 5'(l))) bank_err <= 1'b1;
        end
        if (sl_v) lm[sl_addr] <= sl_data;
        for (l = 0; l < 32; l = l + 1) begin
            if (lsw_v[l]) for (q = 0; q < 8; q = q + 1) lm[{lsw_sec[l*LS +: LS], 3'b000} + q] <= lsw_d[l*256 + 32*q +: 32];
            if (ldc_v[l]) dm[ldc_sec[l*LS +: LS]] <= 8'd0;
        end
        for (l = 0; l < N; l = l + 1)
            if (vm_we[l]) begin
                lm[vm_waddr[l*AW +: AW] & (LW - 1)] <= vm_wdata[32*l +: 32];
                dm[(vm_waddr[l*AW +: AW] & (LW - 1)) >> 3][vm_waddr[l*AW +: 3]] <= 1'b1;
            end
        for (l = 0; l < NR; l = l + 1)
            if (res_we[l]) begin
                lm[res_addr[l*AW +: AW] & (LW - 1)] <= res_data[32*l +: 32];
                dm[(res_addr[l*AW +: AW] & (LW - 1)) >> 3][res_addr[l*AW +: 3]] <= 1'b1;
            end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 stream-unit / SFU / FUSED die-body controller, PRODUCTION form (hgi-unitrate 2026-10-10, lead decision: one
// production SU = the wide engine on sub-agent d's lane-local lmem; ot_hgi_su_unit__d4g_sfu WIDE = 2).
//   * layout: d's dense relayout (ot_hgi_su_ctl__d4g_sfu): every region at an N-aligned base, element (o, i) at base + o L + i,
//     broadcast operands replicated, groups G0 A, G1 B, G2 C (+ A's copy for c_pair), G3 D, GO O, GR R;
//   * span: (nr - 1) L + nw by a 3-edge pipelined multiply (4 partial products), not a bit-serial walk;
//   * stage: the VM wide read lanes (lane b <-> VM bank b, LQ credits) and NS = 32 lmem sector lanes.  A BEAT is the
//     consecutive VM sectors of one row (up to 32: distinct VM banks and, the row being contiguous in the dense layout,
//     256 consecutive local words = distinct lmem banks for N >= 256).  Responses land per lane in order; a landing
//     scheduler writes one beat an edge (oldest first), so an edge's sector writes never collide.  Broadcast (inner
//     stride 0) rows: one VM read, then the replicate engine writes the row's L words, 32 sectors an edge.  Any other
//     inner stride: one element an edge.
//   * drain: the shape walk of O / R (no dirty bits): a beat = up to 32 VM sectors of a contiguous row (one lmem sector
//     read each, word-masked VM write on that sector's lane), valid-driven on the lmem's sr_rv; other shapes one
//     element an edge;
//   * record pipeline: FRONT (decode, span, place, stage) | RUN (the vec) | DRAIN, in-order retire (ot_hgi_su_record
//     PIPED).  A FRONT record allocates per group after the previous record (ring; never over a live RUN / DRAIN
//     record's range), and stages a source only once no older undrained record's sink overlaps it in VM.
//     STREAM records (A = STREAM 0, O = STREAM to ARGMAX) run alone.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_ctlx__d4g_sfu #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer MUT_DIRTY = 0,      // mutant: drain whole sectors (writes words outside the op's shape)
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB, RWB = 6,
    parameter integer LQ = 8,             // VM lane credits (size to the lane-group round trip)
    parameter integer DF = 16,            // per-lane landed-but-unwritten stage sectors
    parameter integer OVL = 1,            // 1: record pipeline; 0: one record at a time
    parameter integer MUT_X = 0           // mutants: 1 a beat's landing ignores its row mask, 2 no source / live-sink
                                          //   hazard, 3 the replicate engine writes one sector short
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output reg  [522:0]  am_stream,
    input  wire          am_rdy,
    output reg           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output reg  [669:0]  wl,
    output reg           sl_v,
    output reg  [LWB-1:0] sl_addr,
    output reg  [31:0]   sl_data,
    // lmem sector lanes (NS = 32)
    output reg  [31:0]       sw_v,
    output reg  [32*256-1:0] sw_data,
    output reg  [3:0]        sw_g,
    output reg  [32*LWB-1:0] sw_addr,
    output reg  [32*8-1:0]   sw_mask,
    output reg  [31:0]       sr_v,
    output reg  [1:0]        sr_g,
    output reg  [32*LWB-1:0] sr_addr,
    input  wire [32*256-1:0] sr_data,
    input  wire [31:0]       sr_rv,
    output reg  [3:0]        use_p,
    input  wire              sl_pend,
    output wire              a_str,
    input  wire              cfault,
    // VM wide lane group ports
    output reg  [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output reg  [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer AW = 24, LW = 1 << LWB, QB = $clog2(LQ), DB = $clog2(DF);
    // sectors a beat: 8 x BL consecutive local words must fall on distinct banks (d's lmem rule) -> BL = min(32, N / 8)
    generate if ((1 << QB) != LQ || (1 << DB) != DF) begin : g_pow2
        ot_hgi_su_ctlx_LQ_and_DF_must_be_powers_of_two u_trap ();
    end endgenerate
    localparam integer BL = (N / 8 < 32) ? ((N / 8 < 1) ? 1 : N / 8) : 32;
    // ---- the record adapter (decode), PIPED: retire on su_ret
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r, su_ret;
    wire [1:0] strm;
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET), .PIPED(1)) u_rec (.clk(clk),
        .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .drained(), .op_strm(strm), .lg_v(1'b0), .lg_rdy(),
        .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w), .su_idle(su_idle_r), .su_fault(su_fault_r), .su_ret(su_ret));
    // ---- FRONT: the op word fields
    reg [669:0] w, fw;
    wire [15:0] no = w[0 +: 16], ni = w[16 +: 16];
    wire [1:0]  aind = w[136 +: 2], dst = w[380 +: 2], red = w[478 +: 2];
    wire        bhalf = w[210], cpair = w[283], redwhole = w[481], redtree = w[482];
    wire [2:0]  m1 = w[360 +: 3], qm = w[365 +: 3], ad = w[368 +: 3], e1 = w[374 +: 3];
    wire [1:0]  m2 = w[363 +: 2], e2 = w[377 +: 2];
    wire use_b = (m1 == 3'd1) || (m1 == 3'd4) || (m1 == 3'd6) || (ad == 3'd3) || (e2 == 2'd1);
    wire use_c = !cpair && ((m2 == 2'd1) || (qm != 3'd0) || (ad == 3'd1) || (ad == 3'd2) || (e1 == 3'd1) || (e1 == 3'd2));
    wire use_d = (qm != 3'd0) || (ad == 3'd5);
    reg [2:0] rk;
    reg [23:0] base_k, so_k, si_k; reg [15:0] nr_k, ni_k; reg used_k; reg hf_k;
    always @* begin
        case (rk)
            3'd0: begin base_k = w[40 +: 24];  so_k = w[64 +: 24];  si_k = w[88 +: 24];  used_k = 1'b1; end
            3'd1: begin base_k = w[138 +: 24]; so_k = w[162 +: 24]; si_k = w[186 +: 24]; used_k = use_b; end
            3'd2: begin base_k = w[211 +: 24]; so_k = w[235 +: 24]; si_k = w[259 +: 24]; used_k = use_c; end
            3'd3: begin base_k = w[284 +: 24]; so_k = w[308 +: 24]; si_k = w[332 +: 24]; used_k = use_d; end
            3'd4: begin base_k = w[382 +: 24]; so_k = w[406 +: 24]; si_k = w[430 +: 24]; used_k = (dst == 2'd1); end
            default: begin base_k = w[484 +: 24]; so_k = w[508 +: 24]; si_k = 24'd0; used_k = (red != 2'd0); end
        endcase
        hf_k = bhalf && (rk == 3'd1 || rk == 3'd3);
        nr_k = (rk == 3'd5) ? ((redwhole || redtree) ? 16'd1 : no) : no;
        ni_k = (rk == 3'd5) ? 16'd1 : (hf_k ? ((ni + 16'd1) >> 1) : ni);
    end
    // ---- the dense layout (d's ot_hgi_su_ctl__d4g_sfu, unchanged rule)
    function automatic [LWB:0] p2c(input [15:0] x);
        integer b2; p2c = 1;
        for (b2 = 0; b2 < 16; b2 = b2 + 1) if (p2c < x) p2c = p2c << 1;
    endfunction
    wire [2:0] sfu = w[371 +: 3];
    wire scalar_c = (sfu == 3'd2) || (sfu == 3'd3) || (sfu == 3'd6) || (sfu == 3'd7);
    wire sfu_c = (sfu == 3'd1) || (sfu == 3'd4) || (sfu == 3'd5) || (m1 == 3'd4) || (m1 == 3'd5);
    wire [15:0] vw = scalar_c ? 16'd1 : sfu_c ? M : N;
    wire red_on = (red != 2'd0);
    wire flatc = (!red_on || redwhole || redtree) && (aind == 2'd0) && (dst != 2'd3) &&
                 (!ni[0] || !(bhalf || qm == 3'd3 || qm == 3'd4));
    wire [LWB:0] s_el0 = p2c((ni > (red_on ? 16'd8 : 16'd1)) ? ni : (red_on ? 16'd8 : 16'd1));
    wire [LWB:0] s_el = (s_el0 > vw) ? vw : s_el0;
    wire [LWB:0] l_el = flatc ? ni : (ni <= s_el) ? s_el : ((ni + N - 1) & ~(N - 1));
    reg [LWB:0] l_full_q, l_half_q; reg [31:0] nn_q;
    wire [LWB:0] L_k = (rk == 3'd5) ? 1 : hf_k ? l_half_q : l_full_q;
    // ---- FRONT per-region state
    reg [23:0] lo [0:5]; reg [23:0] vhi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [LWB:0] Lr [0:5];
    reg [23:0] sor [0:5], sir [0:5]; reg [15:0] nrr [0:5], nir [0:5]; reg [LWB:0] lsz [0:5];
    reg a_s, o_s, f_ser;
    // pipelined multiply: lsz = (nr - 1) L + nw ; VM extent vhi = lo + (nr - 1) so + (nw - 1) si
    reg [15:0] ma; reg [LWB:0] mb; reg [23:0] mc, md; reg [15:0] me;
    reg [39:0] pa0, pa1, pc0, pc1, pe0, pe1; reg [1:0] mph;
    // ---- groups: G0 A, G1 B, G2 C, G3 D, G4 O, G5 R; per group the FRONT record's need, the ring pointer, live ranges
    localparam [LWB:0] SBASE = LW - (1 << SLB);
    function automatic [LWB:0] gsz(input [2:0] g);
        case (g) 3'd0: gsz = SBASE; 3'd1: gsz = 1 << LG1; 3'd2: gsz = 1 << LG2; 3'd3: gsz = 1 << LG3; 3'd4: gsz = 1 << LGO;
                 default: gsz = 1 << RWB; endcase
    endfunction
    function automatic [2:0] grp(input [2:0] r); grp = r; endfunction        // region k lives in group k
    reg [LWB+1:0] need [0:5]; reg [LWB:0] gap [0:5];                         // the FRONT record's need, ring pointers
    reg [LWB:0] gbase [0:5]; reg [LWB:0] galloc [0:5];                       // FRONT placement base / cursor per group
    reg [LWB:0] r_gs [0:5], r_ge [0:5], d_gs [0:5], d_ge [0:5];              // RUN / DRAIN live ranges per group
    // ---- RUN / DRAIN slots
    reg r_v, r_gop, r_cdone, r_as, r_os, r_ser; reg [15:0] r_no, r_ni; reg [31:0] r_nn;
    reg d_v, d_as, d_os, d_ser; reg [15:0] d_no, d_ni; reg [2:0] d_ph; reg [2:0] dk;
    reg [23:0] r_lo [4:5], r_vhi [4:5], r_so [4:5], r_si [4:5]; reg [15:0] r_nr [4:5], r_nw [4:5]; reg [LWB:0] r_lb [4:5], r_L [4:5]; reg r_rv [4:5];
    reg [23:0] d_lo [4:5], d_vhi [4:5], d_so [4:5], d_si [4:5]; reg [15:0] d_nr [4:5], d_nw [4:5]; reg [LWB:0] d_lb [4:5], d_L [4:5]; reg d_rv [4:5];
    // ---- STREAM 0 landing and the stream flags
    localparam integer SW = 1 << SLB;
    reg [20:0] scount; reg s_clr;
    assign a_str = r_v ? r_as : a_s;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot, ebeat; reg [LWB:0] o_lb; reg amr_q, so_w;
    always @(posedge clk) amr_q <= am_rdy;
    reg ready_q, idle_q, vfault_q, rg_q, wg_q, cfault_q;
    reg [255:0] sr0_q; reg [31:0] sr_rv_q; reg [32*256-1:0] sr_d_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; cfault_q <= 1'b0; sr_rv_q <= '0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req;
                   cfault_q <= cfault; sr_rv_q <= sr_rv; end
    end
    always @(posedge clk) sr_d_q <= sr_data;
    reg [31:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [32*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg vf_seen; reg [1:0] idle_ph;
    // =================================================================================================================
    // STAGE engine (FRONT record): issuer -> per-lane in-flight meta FIFO -> landed {meta, data} FIFO -> beat scheduler
    // meta: {beat 8, mode 2 (0 run, 1 rep, 2 elem), group 4, local addr LWB, mask 8, word idx 3, rep count LWB+1}
    // =================================================================================================================
    localparam integer MW = 8 + 2 + 4 + LWB + 8 + 3 + (LWB + 1);
    reg st_go, st_busy, st_done;
    reg [2:0] sk;                                         // region being issued (0..3)
    reg [15:0] s_rows; reg [23:0] s_rb, s_va, s_nw, s_j; reg [LWB:0] s_lr, s_L; reg [23:0] s_so, s_si; reg [1:0] s_md;
    reg [20:0] s_cur, s_end; reg [3:0] s_g; reg [7:0] s_beat;
    reg [QB:0] cr [0:31]; reg [DB:0] slot [0:31];
    // in-flight meta FIFO: a power of two deep (pointers wrap at 2^n; LQ + DF need not be one)
    localparam integer MQB = $clog2(LQ + DF), MQD = 1 << MQB;
    reg [MW-1:0] mq [0:31][0:MQD-1]; reg [MQB:0] mq_n [0:31]; reg [MQB-1:0] mq_h [0:31], mq_t [0:31];
    reg [MW+255:0] lq [0:31][0:DF-1]; reg [DB:0] lq_n [0:31]; reg [DB-1:0] lq_h [0:31], lq_t [0:31];
    // beat queue: {beat id, count of sectors, mode}
    reg [7:0] bq_id [0:63]; reg [5:0] bq_cnt [0:63]; reg [5:0] bq_h, bq_t; reg [6:0] bq_n; reg [5:0] b_left; reg b_act;
    // replicate engine
    reg rp_on; reg [LWB:0] rp_a, rp_end; reg [31:0] rp_w; reg [3:0] rp_g;
    reg lane_ovf;
    function automatic [MW-1:0] meta(input [7:0] bt, input [1:0] mdd, input [3:0] g, input [LWB-1:0] la, input [7:0] mk,
                                     input [2:0] wi, input [LWB:0] rc);
        meta = {bt, mdd, g, la, mk, wi, rc};
    endfunction
    // meta field extraction
    function automatic [7:0] m_bt(input [MW-1:0] x); m_bt = x[MW-1 -: 8]; endfunction
    function automatic [1:0] m_md(input [MW-1:0] x); m_md = x[MW-9 -: 2]; endfunction
    function automatic [3:0] m_g(input [MW-1:0] x); m_g = x[MW-11 -: 4]; endfunction
    function automatic [LWB-1:0] m_la(input [MW-1:0] x); m_la = x[MW-15 -: LWB]; endfunction
    function automatic [7:0] m_mk(input [MW-1:0] x); m_mk = x[(LWB+1) + 3 + 7 -: 8]; endfunction
    function automatic [2:0] m_wi(input [MW-1:0] x); m_wi = x[(LWB+1) + 2 -: 3]; endfunction
    function automatic [LWB:0] m_rc(input [MW-1:0] x); m_rc = x[LWB:0]; endfunction
    // =================================================================================================================
    // DRAIN engine (DRAIN record): beats of VM sectors of the O / R shape, one lmem sector read each, VM write on the
    // sector's lane when the read returns (valid-driven, per-lane in-order sector FIFO)
    // =================================================================================================================
    reg dr_go, dr_done; reg dr_live; reg [2:0] drk;
    reg [15:0] e_rows; reg [23:0] e_rb, e_nw, e_va, e_j; reg [LWB:0] e_lr, e_L; reg [23:0] e_so, e_si; reg e_run;
    reg [20:0] e_cur, e_end; reg [1:0] e_g; reg e_wait;
    reg [QB:0] wcr [0:31]; reg [5:0] wpend [0:31];
    reg [28:0] dq [0:31][0:LQ-1]; reg [QB:0] dq_n [0:31]; reg [QB-1:0] dq_h [0:31], dq_t [0:31];   // {VM sector 21, mask 8}
    reg [31:0] dq_any;
    // ---- hazard / allocation predicates
    function automatic ovl_v(input [23:0] a0, input [23:0] a1, input [23:0] b0, input [23:0] b1);
        ovl_v = (a0 <= b1) && (b0 <= a1);
    endfunction
    function automatic ovl_r(input [LWB:0] a0, input [LWB:0] a1, input [LWB:0] b0, input [LWB:0] b1);
        ovl_r = (a0 < a1) && (b0 < b1) && (a0 < b1) && (b0 < a1);
    endfunction
    reg haz; reg alloc_ok; reg [LWB:0] try_b [0:5];
    always @* begin
        haz = 1'b0;
        for (integer q = 0; q < 4; q = q + 1) if (rv[q])
            for (integer k = 4; k < 6; k = k + 1) begin
                if (r_v && r_rv[k] && !(k == 4 && r_os) && ovl_v(lo[q], vhi[q], r_lo[k], r_vhi[k])) haz = 1'b1;
                if (d_v && d_rv[k] && !(k == 4 && d_os) && ovl_v(lo[q], vhi[q], d_lo[k], d_vhi[k])) haz = 1'b1;
            end
        if (MUT_X == 2) haz = 1'b0;
        alloc_ok = (!f_ser || (!r_v && !d_v)) && !(r_v && r_ser) && !(d_v && d_ser) && (OVL != 0 || (!r_v && !d_v));
        for (integer g = 0; g < 6; g = g + 1) begin
            try_b[g] = ({1'b0, gap[g]} + need[g] <= {1'b0, gsz(g[2:0])}) ? gap[g] : '0;
            if (need[g] != 0) begin
                if ({1'b0, try_b[g]} + need[g] > {1'b0, gsz(g[2:0])}) alloc_ok = 1'b0;
                if (r_v && ovl_r(try_b[g], LWB'(try_b[g] + need[g]), r_gs[g], r_ge[g])) alloc_ok = 1'b0;
                if (d_v && ovl_r(try_b[g], LWB'(try_b[g] + need[g]), d_gs[g], d_ge[g])) alloc_ok = 1'b0;
            end
        end
        if (cpair && need[2] != 0) alloc_ok = 1'b0;      // c_pair puts A's copy in G2: only with C unused (as d)
    end
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_FAULT = 11,
                     S_PRE = 13, S_WAITA = 14, S_RDY = 15;
    reg [3:0] st;
    // census (bench)
    wire a_span = (st == S_SPAN || st == S_MUL || st == S_NEXTR || st == S_WAITA || st == S_PRE || st == S_STAGE);
    wire a_stage = (st == S_STW);
    wire a_run = r_v && !r_cdone;
    wire a_drain = d_v;
    integer k2;
    // =================================================================================================================
    // control
    // =================================================================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; su_ret <= 1'b0; go <= 1'b0; vmq <= 338'd0;
            sl_v <= 1'b0; use_p <= 4'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
            r_v <= 1'b0; r_gop <= 1'b0; r_cdone <= 1'b0; r_ser <= 1'b0; d_v <= 1'b0; d_ser <= 1'b0; d_ph <= 3'd0;
            st_go <= 1'b0; dr_go <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; so_w <= 1'b0; f_ser <= 1'b0;
            for (k2 = 0; k2 < 6; k2 = k2 + 1) begin gap[k2] <= '0; need[k2] <= '0; r_gs[k2] <= '0; r_ge[k2] <= '0; d_gs[k2] <= '0; d_ge[k2] <= '0; end
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; su_ret <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0; go <= 1'b0;
            st_go <= 1'b0; dr_go <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            if ((s0v_q && s0i_q >= SW) || lane_ovf || (cfault_q && st != S_FAULT)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            s_clr <= 1'b0;
            if (vfault_q && r_v && !r_gop) vf_seen <= 1'b1;
            su_idle_r <= (st == S_IDLE) && !r_v && !d_v;
            case (st)
                S_IDLE: if (op_v && op_rdy_r) begin
                    w <= op_w; fw <= op_w; op_rdy_r <= 1'b0; rk <= 3'd0;
                    a_s <= strm[0]; o_s <= strm[1]; f_ser <= strm[0] | strm[1]; st <= S_PRE;
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin rv[k2] <= 1'b0; need[k2] <= '0; end
                end
                S_PRE: begin
                    l_full_q <= l_el; l_half_q <= flatc ? (ni >> 1) : ((l_el >> 1) == 0 ? 1 : (l_el >> 1));
                    nn_q <= {16'd0, no} * {16'd0, ni};
                    st <= S_SPAN;
                end
                S_SPAN: begin
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    lo[rk] <= base_k; sor[rk] <= so_k; sir[rk] <= si_k; nrr[rk] <= nr_k; nir[rk] <= ni_k; Lr[rk] <= L_k;
                    ma <= nr_k - 16'd1; mb <= L_k; mc <= so_k; md <= si_k; me <= ni_k - 16'd1; mph <= 2'd0;
                    if (rk == 3'd0 && a_s) begin
                        fw[40 +: 24] <= SBASE; fw[64 +: 24] <= {8'd0, ni}; fw[88 +: 24] <= 24'd1; rk <= rk + 3'd1;
                    end else if (rk == 3'd4 && o_s) begin             // O = STREAM: contiguous rows of ni in GO, no drain
                        Lr[4] <= ni; nrr[4] <= no; nir[4] <= ni; rv[4] <= 1'b1;
                        ma <= no - 16'd1; mb <= ni; me <= ni - 16'd1; st <= S_MUL;
                    end else if (!used_k) begin
                        if (rk == 3'd5) st <= S_WAITA; else rk <= rk + 3'd1;
                    end else st <= S_MUL;
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // 3 edges: partial products, sums, extent
                    if (mph == 2'd0) begin
                        pa0 <= ma[7:0] * mb; pa1 <= ma[15:8] * mb; pc0 <= ma[7:0] * mc; pc1 <= ma[15:8] * mc;
                        pe0 <= me[7:0] * md; pe1 <= me[15:8] * md; mph <= 2'd1;
                    end else if (mph == 2'd1) begin
                        lsz[rk] <= LWB'(pa0 + (pa1 << 8)) + LWB'(nir[rk]);
                        vhi[rk] <= lo[rk] + 24'(pc0 + (pc1 << 8)) + 24'(pe0 + (pe1 << 8));
                        need[grp(rk)] <= need[grp(rk)] + (LWB+2)'(((pa0 + (pa1 << 8)) + nir[rk] + N - 1) & ~(N - 1));
                        if (rk == 3'd0 && cpair) need[2] <= need[2];
                        mph <= 2'd2;
                    end else begin
                        if (rk == 3'd5) st <= S_WAITA; else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_WAITA: if (alloc_ok) begin                         // ring placement per group, clear of live records
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin gbase[k2] <= try_b[k2]; galloc[k2] <= try_b[k2]; end
                    rk <= 3'd0; st <= S_NEXTR;
                end
                S_NEXTR: begin                                      // place region rk (N-aligned), rewrite its fields
                    if (rv[rk]) begin
                        lb[rk] <= galloc[rk];
                        galloc[rk] <= (galloc[rk] + lsz[rk] + N - 1) & ~(N - 1);
                        case (rk)
                            3'd0: begin fw[40 +: 24]  <= galloc[0]; fw[64 +: 24]  <= Lr[0]; fw[88 +: 24]  <= 24'd1; end
                            3'd1: begin fw[138 +: 24] <= galloc[1]; fw[162 +: 24] <= Lr[1]; fw[186 +: 24] <= 24'd1; end
                            3'd2: begin fw[211 +: 24] <= galloc[2]; fw[235 +: 24] <= Lr[2]; fw[259 +: 24] <= 24'd1; end
                            3'd3: begin fw[284 +: 24] <= galloc[3]; fw[308 +: 24] <= Lr[3]; fw[332 +: 24] <= 24'd1; end
                            3'd4: begin fw[382 +: 24] <= galloc[4]; fw[406 +: 24] <= Lr[4]; fw[430 +: 24] <= 24'd1; end
                            default: begin fw[484 +: 24] <= galloc[5]; fw[508 +: 24] <= 24'd1; end
                        endcase
                    end
                    else begin
                        // an unused stream: give it the flat-consistent stride (so = row words, si = 1) so the vec's
                        // flatten test (every stream contiguous across rows) agrees with the dense layout's choice
                        case (rk)
                            3'd1: begin fw[162 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; fw[186 +: 24] <= 24'd1; end
                            3'd2: begin fw[235 +: 24] <= {8'd0, ni}; fw[259 +: 24] <= 24'd1; end
                            3'd3: begin fw[308 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; fw[332 +: 24] <= 24'd1; end
                            3'd4: if (!o_s) begin fw[406 +: 24] <= {8'd0, ni}; fw[430 +: 24] <= 24'd1; end
                            default: ;
                        endcase
                    end
                    if (rk == 3'd5) st <= S_STAGE; else rk <= rk + 3'd1;
                end
                S_STAGE: begin                                      // sources clear of older undrained sinks?
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) gap[k2] <= galloc[k2];
                    if (!haz) rg_req <= 1'b1;
                    if (!haz && rg_req && rg_q) begin st <= S_STW; st_go <= 1'b1; end
                end
                S_STW: if (!st_go && st_done) begin st <= S_RDY; rg_req <= 1'b0; end
                S_RDY: if (!r_v) begin                              // into RUN
                    r_v <= 1'b1; r_gop <= 1'b1; r_cdone <= 1'b0; wl <= fw; r_as <= a_s; r_os <= o_s; r_ser <= f_ser;
                    r_no <= no; r_ni <= ni; r_nn <= nn_q;
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin r_gs[k2] <= gbase[k2]; r_ge[k2] <= galloc[k2]; end
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        r_lo[k2] <= lo[k2]; r_vhi[k2] <= vhi[k2]; r_so[k2] <= sor[k2]; r_si[k2] <= sir[k2]; r_nr[k2] <= nrr[k2];
                        r_nw[k2] <= nir[k2]; r_lb[k2] <= lb[k2]; r_L[k2] <= Lr[k2]; r_rv[k2] <= rv[k2];
                    end
                    op_rdy_r <= 1'b1; st <= S_IDLE;
                end
                S_FAULT: ;
                default: st <= S_FAULT;
            endcase
            // ---------------------------------------------------------------- RUN
            if (r_v && st != S_FAULT) begin
                if (r_gop) begin
                    if (ready_q && !sl_pend && (!r_as || {11'd0, scount} >= r_nn)) begin
                        go <= 1'b1; r_gop <= 1'b0; idle_ph <= 2'd0; vf_seen <= 1'b0;
                        use_p <= {wl[365 +: 3] != 3'd0 || wl[368 +: 3] == 3'd5,
                                  wl[283] || (wl[363 +: 2] == 2'd1) || (wl[365 +: 3] != 3'd0) || (wl[368 +: 3] == 3'd1) ||
                                  (wl[368 +: 3] == 3'd2) || (wl[374 +: 3] == 3'd1) || (wl[374 +: 3] == 3'd2),
                                  (wl[360 +: 3] == 3'd1) || (wl[360 +: 3] == 3'd4) || (wl[360 +: 3] == 3'd6) ||
                                  (wl[368 +: 3] == 3'd3) || (wl[377 +: 2] == 2'd1), 1'b1};
                    end
                end else if (!r_cdone) begin
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        else begin r_cdone <= 1'b1; use_p <= 4'd0; end
                    end
                end else if (!d_v) begin                            // into DRAIN
                    d_v <= 1'b1; d_ph <= 3'd0; d_as <= r_as; d_os <= r_os; d_ser <= r_ser; d_no <= r_no; d_ni <= r_ni;
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin d_gs[k2] <= r_gs[k2]; d_ge[k2] <= r_ge[k2]; end
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        d_lo[k2] <= r_lo[k2]; d_vhi[k2] <= r_vhi[k2]; d_so[k2] <= r_so[k2]; d_si[k2] <= r_si[k2];
                        d_nr[k2] <= r_nr[k2]; d_nw[k2] <= r_nw[k2]; d_lb[k2] <= r_lb[k2]; d_L[k2] <= r_L[k2]; d_rv[k2] <= r_rv[k2];
                    end
                    r_v <= 1'b0; r_ser <= 1'b0;
                end
            end
            // ---------------------------------------------------------------- DRAIN
            if (d_v && st != S_FAULT) begin
                case (d_ph)
                    3'd0: begin
                        if ((d_rv[4] && !d_os) || d_rv[5]) begin
                            wg_req <= 1'b1;
                            if (wg_req && wg_q) begin dr_go <= 1'b1; d_ph <= 3'd1; end
                        end else if (d_os) d_ph <= 3'd2;
                        else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                    end
                    3'd1: if (!dr_go && dr_done) begin
                        wg_req <= 1'b0;
                        if (d_os) d_ph <= 3'd2;
                        else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                    end
                    3'd2: begin etot <= {5'd0, d_no} * {5'd0, d_ni}; ebeat <= 21'd0; o_lb <= d_lb[4]; so_w <= 1'b0; d_ph <= 3'd3; end
                    default: begin                                  // STREAM out on sector lane 0, valid-driven
                        if (amr_q && !so_w) so_w <= 1'b1;
                        else if (so_w && sr_rv_q[0]) begin
                            begin : so
                                reg [7:0] mk; integer q;
                                for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                                am_stream <= {1'b0, 256'd0, sr_d_q[255:0], mk, (ebeat + 21'd8 >= etot), 1'b1};
                            end
                            so_w <= 1'b0;
                            if (ebeat + 21'd8 >= etot) begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                            else ebeat <= ebeat + 21'd8;
                        end
                    end
                endcase
            end
        end
    end
    // STREAM-out read issue (one sector read when so_w rises)
    reg so_iss;
    // =================================================================================================================
    // the lane engines (stage issue / landing / beat scheduler; drain issue / return / VM write)
    // =================================================================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wrq <= '0; wwq <= '0; sw_v <= '0; sr_v <= '0; st_busy <= 1'b0; st_done <= 1'b1; dr_live <= 1'b0; dr_done <= 1'b1;
            bq_h <= '0; bq_t <= '0; bq_n <= '0; b_act <= 1'b0; rp_on <= 1'b0; lane_ovf <= 1'b0; s_beat <= '0; so_iss <= 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin
                cr[b] <= (QB+1)'(LQ); slot[b] <= (DB+1)'(DF); mq_n[b] <= '0; mq_h[b] <= '0; mq_t[b] <= '0;
                lq_n[b] <= '0; lq_h[b] <= '0; lq_t[b] <= '0; wcr[b] <= (QB+1)'(LQ); wpend[b] <= '0; dq_n[b] <= '0; dq_h[b] <= '0; dq_t[b] <= '0;
            end
        end else begin : eng
            reg [31:0] iss; reg [31:0] land; reg [31:0] wr; reg [31:0] dri; reg [31:0] dret; reg [31:0] wsend;
            reg [MW-1:0] mh; integer n_ok; reg [20:0] sc; reg [4:0] bl; reg stop; reg [23:0] w0; reg [7:0] mk;
            reg bq_push; reg [7:0] bq_pid; reg [5:0] bq_pcnt; reg bq_pop;
            iss = '0; land = '0; wr = '0; dri = '0; dret = '0; wsend = '0; bq_push = 1'b0; bq_pid = '0; bq_pcnt = '0; bq_pop = 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin wrq[b*16 + 15] <= 1'b0; wwq[b*280 + 279] <= 1'b0; end
            sw_v <= '0; sr_v <= '0;
            // ---------------------------------------------------------------- stage: start
            if (st_go) begin
                st_busy <= 1'b1; st_done <= 1'b0; sk <= 3'd0; s_rows <= 16'd0;
            end
            // ---------------------------------------------------------------- stage: issuer (one beat an edge)
            if (st_busy && !st_go) begin
                if (s_rows == 16'd0) begin                      // the next used source region
                    if (sk >= 3'd4) st_busy <= 1'b0;
                    else if (!rv[sk]) sk <= sk + 3'd1;
                    else begin : rsetup
                        reg [1:0] mdd; reg merge;
                        mdd = (sir[sk] == 24'd1) ? 2'd0 : (sir[sk] == 24'd0) ? 2'd1 : 2'd2;
                        merge = (mdd == 2'd0) && (sor[sk] == {8'd0, nir[sk]}) && (Lr[sk] == nir[sk]);
                        s_md <= mdd; s_g <= (sk == 3'd0 && cpair) ? 4'b0101 : (4'b0001 << sk);
                        s_rows <= merge ? 16'd1 : nrr[sk];
                        s_nw <= merge ? 24'({8'd0, nrr[sk]} * {8'd0, nir[sk]}) : {8'd0, nir[sk]};
                        s_rb <= lo[sk]; s_va <= lo[sk]; s_lr <= lb[sk]; s_j <= 24'd0; s_so <= sor[sk]; s_si <= sir[sk];
                        s_L <= Lr[sk]; s_cur <= 21'(lo[sk] >> 3);
                        s_end <= 21'((lo[sk] + (merge ? 24'({8'd0, nrr[sk]} * {8'd0, nir[sk]}) : {8'd0, nir[sk]}) - 24'd1) >> 3);
                        sk <= sk + 3'd1;
                    end
                end else begin
                    // a beat: the run's next sectors (prefix with credits / slots), or one rep / elem request
                    n_ok = 0; stop = 1'b0;
                    if (s_md == 2'd0) begin
                        for (integer k = 0; k < BL; k = k + 1) begin
                            sc = s_cur + 21'(k); bl = sc[4:0];
                            if (!stop && sc <= s_end && cr[bl] != 0 && slot[bl] != 0 && mq_n[bl] < (MQB+1)'(MQD)) begin
                                iss[bl] = 1'b1; n_ok = n_ok + 1;
                                w0 = {sc, 3'b000};
                                for (integer q = 0; q < 8; q = q + 1) mk[q] = MUT_X == 1 ? 1'b1 : ((w0 + q >= s_rb) && (w0 + q < s_rb + s_nw));
                                wrq[bl*16 +: 16] <= {1'b1, sc[14:0]};
                                mq[bl][mq_t[bl]] <= meta(s_beat, 2'd0, s_g, LWB'(w0 - s_rb + s_lr), mk, 3'd0, '0);
                            end else stop = 1'b1;
                        end
                        if (n_ok > 0) begin
                            bq_push = 1'b1; bq_pid = s_beat; bq_pcnt = 6'(n_ok); s_beat <= s_beat + 8'd1;
                            if (s_cur + 21'(n_ok) > s_end) begin       // the row is issued: the next row
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + s_so; s_lr <= s_lr + s_L;
                                s_cur <= 21'((s_rb + s_so) >> 3); s_end <= 21'((s_rb + s_so + s_nw - 24'd1) >> 3);
                            end else s_cur <= s_cur + 21'(n_ok);
                        end
                    end else begin
                        sc = (s_md == 2'd1) ? 21'(s_rb >> 3) : 21'(s_va >> 3); bl = sc[4:0];
                        if (cr[bl] != 0 && slot[bl] != 0 && mq_n[bl] < (MQB+1)'(MQD) && bq_n < 7'd60) begin
                            iss[bl] = 1'b1;
                            wrq[bl*16 +: 16] <= {1'b1, sc[14:0]};
                            if (s_md == 2'd1)                      // broadcast row: one read, the row's L words
                                mq[bl][mq_t[bl]] <= meta(s_beat, 2'd1, s_g, s_lr[LWB-1:0], 8'hFF, s_rb[2:0], LWB'(s_nw));
                            else
                                mq[bl][mq_t[bl]] <= meta(s_beat, 2'd2, s_g, LWB'(s_lr + s_j), 8'h01, s_va[2:0], '0);
                            bq_push = 1'b1; bq_pid = s_beat; bq_pcnt = 6'd1; s_beat <= s_beat + 8'd1;
                            if (s_md == 2'd1 || s_j + 24'd1 == s_nw) begin
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + s_so; s_va <= s_rb + s_so; s_lr <= s_lr + s_L; s_j <= 24'd0;
                            end else begin s_j <= s_j + 24'd1; s_va <= s_va + s_si; end
                        end
                    end
                end
            end
            // ---------------------------------------------------------------- stage: responses land in the lane FIFOs
            for (integer b = 0; b < 32; b = b + 1) begin
                if (wrr_q[b*257 + 256]) begin
                    land[b] = 1'b1;
                    lq[b][lq_t[b]] <= {mq[b][mq_h[b]], wrr_q[b*257 +: 256]};
                    if (lq_n[b] == (DB+1)'(DF)) lane_ovf <= 1'b1;
                end
            end
            // ---------------------------------------------------------------- stage: the beat scheduler (oldest beat)
            if (rp_on) begin                                    // replicate engine: 32 sectors of copies an edge
                sw_g <= rp_g;
                for (integer b = 0; b < 32; b = b + 1) begin : rpl
                    reg [LWB:0] a_;
                    a_ = rp_a + (LWB+1)'(8 * b);
                    if (b < BL && a_ < rp_end && !(MUT_X == 3 && a_ + 8 >= rp_end)) begin
                        sw_v[b] <= 1'b1; sw_addr[b*LWB +: LWB] <= a_[LWB-1:0]; sw_data[b*256 +: 256] <= {8{rp_w}};
                        for (integer q = 0; q < 8; q = q + 1) sw_mask[b*8 + q] <= (a_ + q < rp_end);
                    end
                end
                if (rp_a + 8 * BL >= rp_end) begin rp_on <= 1'b0; bq_pop = 1'b1; end
                else rp_a <= rp_a + 8 * BL;
            end else if (bq_n != 0) begin : sched
                reg [5:0] got_; reg [5:0] need_; reg rep_;
                got_ = '0; need_ = b_act ? b_left : bq_cnt[bq_h]; rep_ = 1'b0;
                for (integer b = 0; b < 32; b = b + 1)
                    if (lq_n[b] != 0 && m_bt(lq[b][lq_h[b]][MW+255 -: MW]) == bq_id[bq_h]) begin : one
                        reg [MW-1:0] mm; reg [255:0] dd;
                        mm = lq[b][lq_h[b]][MW+255 -: MW]; dd = lq[b][lq_h[b]][255:0];
                        wr[b] = 1'b1; got_ = got_ + 6'd1;
                        sw_g <= m_g(mm);
                        case (m_md(mm))
                            2'd0: begin sw_v[b] <= 1'b1; sw_addr[b*LWB +: LWB] <= m_la(mm); sw_data[b*256 +: 256] <= dd;
                                        sw_mask[b*8 +: 8] <= m_mk(mm); end
                            2'd1: begin rep_ = 1'b1; rp_on <= 1'b1; rp_a <= {1'b0, m_la(mm)}; rp_end <= {1'b0, m_la(mm)} + m_rc(mm);
                                        rp_w <= dd[32*m_wi(mm) +: 32]; rp_g <= m_g(mm); end
                            default: begin sw_v[b] <= 1'b1; sw_addr[b*LWB +: LWB] <= m_la(mm); sw_data[b*256 +: 256] <= {224'd0, dd[32*m_wi(mm) +: 32]};
                                           sw_mask[b*8 +: 8] <= 8'h01; end
                        endcase
                    end
                if (got_ != 0 && !rep_) begin
                    if (got_ == need_) begin b_act <= 1'b0; bq_pop = 1'b1; end
                    else begin b_act <= 1'b1; b_left <= need_ - got_; end
                end
            end
            for (integer b = 0; b < 32; b = b + 1) begin
                if (iss[b]) mq_t[b] <= mq_t[b] + 1'b1;
                if (land[b]) begin mq_h[b] <= mq_h[b] + 1'b1; lq_t[b] <= lq_t[b] + 1'b1; end
                if (wr[b]) lq_h[b] <= lq_h[b] + 1'b1;
                mq_n[b] <= mq_n[b] + iss[b] - land[b];
                lq_n[b] <= lq_n[b] + land[b] - wr[b];
                cr[b] <= cr[b] - iss[b] + wrq_cr_q[b];
                slot[b] <= slot[b] - iss[b] + wr[b];
            end
            if (bq_push) begin bq_id[bq_t] <= bq_pid; bq_cnt[bq_t] <= bq_pcnt; bq_t <= bq_t + 6'd1; end
            if (bq_pop) bq_h <= bq_h + 6'd1;
            bq_n <= bq_n + bq_push - bq_pop;
            if (bq_push && bq_n == 7'd64) lane_ovf <= 1'b1;
            begin : sdone
                reg idle_; idle_ = !st_busy && !st_go && (bq_n + bq_push - bq_pop) == 0 && !rp_on;
                for (integer b = 0; b < 32; b = b + 1)
                    if (mq_n[b] + iss[b] - land[b] != 0 || (cr[b] - iss[b] + wrq_cr_q[b]) != (QB+1)'(LQ)) idle_ = 1'b0;
                if (!st_done && idle_ && !st_go) st_done <= 1'b1;
            end
            // ---------------------------------------------------------------- drain: start
            if (dr_go) begin dr_live <= 1'b1; dr_done <= 1'b0; drk <= 3'd4; e_rows <= 16'd0; e_wait <= 1'b0; end
            else if (dr_live) begin
                if (e_rows == 16'd0) begin                      // the next sink region (after the previous one's reads)
                    if (dq_any == 0 && !e_wait) begin
                        if (drk >= 3'd6) dr_live <= 1'b0;
                        else if (!d_rv[drk] || (drk == 3'd4 && d_os)) drk <= drk + 3'd1;
                        else begin : dsetup
                            reg run_; reg merge_; reg [23:0] so_; reg [15:0] nr_, nw_;
                            nr_ = d_nr[drk]; nw_ = d_nw[drk]; so_ = d_so[drk];
                            run_ = (drk == 3'd4) ? (d_si[drk] == 24'd1) : (so_ == 24'd1 || nr_ == 16'd1);
                            if (drk == 3'd5) begin                  // R: one word a row at r_so (stride 0 = 1)
                                merge_ = (so_ == 24'd1 || so_ == 24'd0 || nr_ == 16'd1);
                                e_nw <= merge_ ? {8'd0, nr_} : 24'd1; e_rows <= merge_ ? 16'd1 : nr_;
                                e_so <= (so_ == 24'd0) ? 24'd1 : so_; e_L <= 1; e_run <= 1'b1; e_si <= 24'd0;
                                e_end <= 21'((d_lo[drk] + (merge_ ? {8'd0, nr_} : 24'd1) - 24'd1) >> 3);
                            end else begin
                                merge_ = run_ && (so_ == {8'd0, nw_}) && (d_L[drk] == nw_);
                                e_nw <= merge_ ? 24'({8'd0, nr_} * {8'd0, nw_}) : {8'd0, nw_}; e_rows <= merge_ ? 16'd1 : nr_;
                                e_so <= so_; e_L <= d_L[drk]; e_run <= run_; e_si <= d_si[drk];
                                e_end <= 21'((d_lo[drk] + (merge_ ? 24'({8'd0, nr_} * {8'd0, nw_}) : {8'd0, nw_}) - 24'd1) >> 3);
                            end
                            e_rb <= d_lo[drk]; e_va <= d_lo[drk]; e_lr <= d_lb[drk]; e_j <= 24'd0; e_cur <= 21'(d_lo[drk] >> 3);
                            e_g <= (drk == 3'd4) ? 2'd1 : 2'd2;
                            drk <= drk + 3'd1;
                        end
                    end
                    e_wait <= 1'b0;
                end else begin
                    stop = 1'b0; n_ok = 0;
                    sr_g <= e_g;
                    if (e_run) begin                            // a beat: the row's next sectors, one lmem read each
                        for (integer k = 0; k < BL; k = k + 1) begin
                            sc = e_cur + 21'(k); bl = sc[4:0];
                            if (!stop && sc <= e_end && wcr[bl] != 0 && dq_n[bl] < (QB+1)'(LQ)) begin
                                dri[bl] = 1'b1; n_ok = n_ok + 1;
                                w0 = {sc, 3'b000};
                                for (integer q = 0; q < 8; q = q + 1) mk[q] = MUT_DIRTY ? 1'b1 : ((w0 + q >= e_rb) && (w0 + q < e_rb + e_nw));
                                sr_v[bl] <= 1'b1; sr_addr[bl*LWB +: LWB] <= LWB'(w0 - e_rb + e_lr);
                                dq[bl][dq_t[bl]] <= {sc, mk};
                            end else stop = 1'b1;
                        end
                        if (n_ok > 0) begin
                            if (e_cur + 21'(n_ok) > e_end) begin
                                e_rows <= e_rows - 16'd1; e_rb <= e_rb + e_so; e_lr <= e_lr + e_L;
                                e_cur <= 21'((e_rb + e_so) >> 3); e_end <= 21'((e_rb + e_so + e_nw - 24'd1) >> 3);
                                if (e_rows == 16'd1) e_wait <= 1'b1;
                            end else e_cur <= e_cur + 21'(n_ok);
                        end
                    end else begin                              // one element an edge
                        sc = 21'(e_va >> 3); bl = sc[4:0];
                        if (wcr[bl] != 0 && dq_n[bl] < (QB+1)'(LQ)) begin
                            dri[bl] = 1'b1;
                            sr_v[bl] <= 1'b1; sr_addr[bl*LWB +: LWB] <= LWB'(e_lr + e_j - e_va[2:0]);
                            dq[bl][dq_t[bl]] <= {sc, (MUT_DIRTY ? 8'hFF : (8'd1 << e_va[2:0]))};
                            if (e_j + 24'd1 == e_nw) begin
                                e_rows <= e_rows - 16'd1; e_rb <= e_rb + e_so; e_va <= e_rb + e_so; e_lr <= e_lr + e_L; e_j <= 24'd0;
                                if (e_rows == 16'd1) e_wait <= 1'b1;
                            end else begin e_j <= e_j + 24'd1; e_va <= e_va + e_si; end
                        end
                    end
                end
            end
            // STREAM-out sector read (lane 0) when the DRAIN slot asks
            so_iss <= so_w;
            if (so_w && !so_iss && d_ph == 3'd3) begin sr_v[0] <= 1'b1; sr_g <= 2'd1; sr_addr[0 +: LWB] <= LWB'(o_lb + ebeat); end
            // drain returns -> VM writes
            for (integer b = 0; b < 32; b = b + 1) begin
                if (sr_rv_q[b] && dq_n[b] != 0) begin
                    dret[b] = 1'b1; wsend[b] = 1'b1;
                    wwq[b*280 +: 280] <= {1'b1, dq[b][dq_h[b]][22:8], sr_d_q[b*256 +: 256], dq[b][dq_h[b]][7:0]};
                end
                if (dri[b]) dq_t[b] <= dq_t[b] + 1'b1;
                if (dret[b]) dq_h[b] <= dq_h[b] + 1'b1;
                dq_n[b] <= dq_n[b] + dri[b] - dret[b];
                wcr[b] <= wcr[b] - dri[b] + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend[b] - wwq_done_q[b];
            end
            dq_any <= '0;
            for (integer b = 0; b < 32; b = b + 1) if (dq_n[b] + dri[b] - dret[b] != 0) dq_any[b] <= 1'b1;
            begin : ddone
                reg idle_; idle_ = !dr_live && !dr_go;
                for (integer b = 0; b < 32; b = b + 1)
                    if (dq_n[b] + dri[b] - dret[b] != 0 || wpend[b] + wsend[b] - wwq_done_q[b] != 0 ||
                        (wcr[b] - dri[b] + wwq_cr_q[b]) != (QB+1)'(LQ)) idle_ = 1'b0;
                if (!dr_done && idle_) dr_done <= 1'b1;
            end
        end
    end
endmodule

`default_nettype wire

// el1011-hbm-sfu 2026-10-11 (textbook classes 1 + 6: ot_hgi_su_ctlw__d4g_sfu was one 80,059-flop clock tree in a 1 x 1 mm die at
// 5.7 % utilisation, 40,691 pins): eight of the 32 wide lanes as a hardened slice.  The lane logic is the flat
// ctlw's, verbatim (lane b of slice SL is global lane SL*NL+b: its first sector, its VM / local bank); every slice input
// is a pin register (the shared region descriptors and go pulses arrive one edge later, together), every output a
// register; the slice's all-lanes-done / overflow reductions leave registered (the hub reduces the four again).
module ot_hgi_su_ctlw_slice__d4g_sfu #(
    parameter integer SL = 0, parameter integer NL = 8, parameter integer LWB = 17, parameter integer LQ = 8,
    parameter integer MUT_W = 0, parameter integer MUT_DIRTY = 0,
    parameter integer LQSRAM = 0          // 1: each lane's landing FIFO in a 64x16 1R1W SRAM (FWFT), not 64 x LSW flops
) (
    input  wire clk, input wire rst_n,
    input  wire wst_go_i, input wire wdr_go_i,
    input  wire [6*24-1:0] lo_i, input wire [6*24-1:0] hi_i, input wire [6*(LWB+1)-1:0] lb_i, input wire [5:0] rv_i,
    input  wire [6*21-1:0] dsec_i,
    input  wire [2*24-1:0] d_lo_i, input wire [2*24-1:0] d_hi_i, input wire [2*(LWB+1)-1:0] d_lb_i, input wire [1:0] d_rv_i,
    input  wire [2*21-1:0] d_dsec_i, input wire d_os_i,
    // GLUE PLACEMENT (el1011-hbm-sfu 10-11): slice id strap (one hard tile for every slice), the forward link (this
    // slice's descriptor / go pin registers, to the next slice) and the backward done / overflow combine link
    input  wire [1:0] sl_i,
    output wire wst_go_o, output wire wdr_go_o, output wire d_os_o,
    output wire [6*24-1:0] lo_o, output wire [6*24-1:0] hi_o, output wire [6*(LWB+1)-1:0] lb_o, output wire [5:0] rv_o,
    output wire [6*21-1:0] dsec_o, output wire [2*24-1:0] d_lo_o, output wire [2*24-1:0] d_hi_o,
    output wire [2*(LWB+1)-1:0] d_lb_o, output wire [1:0] d_rv_o, output wire [2*21-1:0] d_dsec_o,
    input  wire wst_dn_i, input wire wdr_dn_i, input wire ovf_i,
    output reg  [NL*16-1:0] wrq, input wire [NL-1:0] wrq_cr, input wire [NL*257-1:0] wrr,
    output reg  [NL*280-1:0] wwq, input wire [NL-1:0] wwq_cr, input wire [NL-1:0] wwq_done,
    output reg  [NL-1:0] lsw_v, output reg [NL*(LWB-3)-1:0] lsw_sec, output reg [NL*256-1:0] lsw_d,
    output reg  [NL-1:0] ldc_v, output reg [NL*(LWB-3)-1:0] ldc_sec,
    output reg  [NL-1:0] ldr_v, output reg [NL*(LWB-3)-1:0] ldr_sec,
    input  wire [NL*256-1:0] ldr_d, input wire [NL*8-1:0] ldr_dm, input wire [NL-1:0] ldr_rv,
    output reg  wst_dn, output reg wdr_dn, output reg ovf
);
    localparam integer LSW = LWB - 3, QB = $clog2(LQ);
    reg rst_l; always @(posedge clk) rst_l <= rst_n;          // the slice's reset pin flop
    reg wst_go, wdr_go;
    always @(posedge clk or negedge rst_l) if (!rst_l) begin wst_go <= 1'b0; wdr_go <= 1'b0; end
                                           else begin wst_go <= wst_go_i; wdr_go <= wdr_go_i; end
    reg [23:0] lo [0:5]; reg [23:0] hi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [20:0] dsec [0:5];
    reg [23:0] d_lo [4:5]; reg [23:0] d_hi [4:5]; reg [LWB:0] d_lb [4:5]; reg d_rv [4:5]; reg [20:0] d_dsec [4:5]; reg d_os;
    always @(posedge clk) begin
        for (integer q = 0; q < 6; q = q + 1) begin
            lo[q] <= lo_i[q*24 +: 24]; hi[q] <= hi_i[q*24 +: 24]; lb[q] <= lb_i[q*(LWB+1) +: LWB+1]; rv[q] <= rv_i[q];
            dsec[q] <= dsec_i[q*21 +: 21];
        end
        for (integer q = 4; q < 6; q = q + 1) begin
            d_lo[q] <= d_lo_i[(q-4)*24 +: 24]; d_hi[q] <= d_hi_i[(q-4)*24 +: 24]; d_lb[q] <= d_lb_i[(q-4)*(LWB+1) +: LWB+1];
            d_rv[q] <= d_rv_i[q-4]; d_dsec[q] <= d_dsec_i[(q-4)*21 +: 21];
        end
        d_os <= d_os_i;
    end
    reg [1:0] sl_q; always @(posedge clk) sl_q <= sl_i;      // strap pin flop
    assign wst_go_o = wst_go; assign wdr_go_o = wdr_go; assign d_os_o = d_os;
    for (genvar q = 0; q < 6; q = q + 1) begin : g_fo
        assign lo_o[q*24 +: 24] = lo[q]; assign hi_o[q*24 +: 24] = hi[q]; assign lb_o[q*(LWB+1) +: LWB+1] = lb[q];
        assign rv_o[q] = rv[q]; assign dsec_o[q*21 +: 21] = dsec[q];
    end
    for (genvar q = 4; q < 6; q = q + 1) begin : g_fd
        assign d_lo_o[(q-4)*24 +: 24] = d_lo[q]; assign d_hi_o[(q-4)*24 +: 24] = d_hi[q];
        assign d_lb_o[(q-4)*(LWB+1) +: LWB+1] = d_lb[q]; assign d_rv_o[q-4] = d_rv[q]; assign d_dsec_o[(q-4)*21 +: 21] = d_dsec[q];
    end
    reg dn_st_q, dn_dr_q, dn_ov_q;                           // the next slice's combined flags, pin-flopped
    always @(posedge clk or negedge rst_l) if (!rst_l) begin dn_st_q <= 1'b1; dn_dr_q <= 1'b1; dn_ov_q <= 1'b0; end
                                           else begin dn_st_q <= wst_dn_i; dn_dr_q <= wdr_dn_i; dn_ov_q <= ovf_i; end
    reg [NL-1:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [NL*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg [NL*256-1:0] ldr_d_q; reg [NL*8-1:0] ldr_dm_q;
    reg [NL-1:0] ldr_rv_q;
    always @(posedge clk) begin ldr_d_q <= ldr_d; ldr_dm_q <= ldr_dm; end
    always @(posedge clk or negedge rst_l) if (!rst_l) ldr_rv_q <= '0; else ldr_rv_q <= ldr_rv;
    // drain reads are VALID-driven: each lane keeps the VM sector of every read in flight (in order); a returned
    // {data, dirty} (ldr_rv, pin-flopped) pops it, whatever the memory latency
    reg [20:0] dq_s [0:NL-1][0:LQ-1]; reg [QB-1:0] dq_h [0:NL-1], dq_t [0:NL-1]; reg [QB:0] dq_n [0:NL-1];
    // per-lane state
    reg [2:0]  sg_r [0:NL-1]; reg sg_on [0:NL-1]; reg [20:0] sg_nx [0:NL-1]; reg [20:0] sg_end [0:NL-1];
    // landing FIFO: LQ queued at the VM + the accepted-not-landed pipe (VM core + relays): power of two >= 2 LQ + 32
    localparam integer LFB = $clog2(2 * LQ + 32), LFD = 1 << LFB;
    reg [QB:0] cr [0:NL-1]; reg [LSW-1:0] lq [0:NL-1][0:LFD-1]; reg [LFB-1:0] lqh [0:NL-1], lqt [0:NL-1]; reg [LFB:0] lqn [0:NL-1];
    reg [5:0] wpend [0:NL-1]; reg lane_ovf;
    reg [2:0]  cl_r [0:NL-1]; reg cl_on [0:NL-1]; reg [LSW-1:0] cl_nx [0:NL-1]; reg [LSW-1:0] cl_end [0:NL-1];
    reg [2:0]  dg_r [0:NL-1]; reg dg_on [0:NL-1]; reg [LSW-1:0] dg_nx [0:NL-1]; reg [LSW-1:0] dg_end [0:NL-1];
    reg [QB:0] wcr [0:NL-1]; reg [NL-1:0] dp1, dp2, dp3; reg [20:0] dp1_s [0:NL-1]; reg [20:0] dp2_s [0:NL-1]; reg [20:0] dp3_s [0:NL-1];
    reg [NL-1:0] wst_ldone, wdr_ldone;
    function automatic [20:0] first_of(input [20:0] lo_s, input integer b);
        first_of = lo_s + 21'((5'(b) - lo_s[4:0]) & 5'd31);
    endfunction
    // landing FIFO head per lane: flops (LQSRAM 0) or an SRAM first-word-fall-through FIFO (LQSRAM 1); lq_first = slot 0
    wire [LSW-1:0] lq_head [0:NL-1]; reg [LSW-1:0] lq_first [0:NL-1];
    generate if (LQSRAM != 0) begin : g_lqm
        initial if (LFD != 64 || LSW > 16) $error("ot_hgi_su_ctlw_slice__d4g_sfu LQSRAM: needs LFD 64 and LSW <= 16");
        for (genvar g = 0; g < NL; g = g + 1) begin : g_l
            wire push = !wst_go && sg_r[g] < 3'd4 && sg_on[g] && cr[g] != 0;
            // MUT_W 4 (bench mutant, el1011-hbm-sfu 10-11): the SRAM FIFO pop one edge late -> a back-to-back landing
            // reads the previous head (wrong sector); the only mutant that exercises this FIFO's read-ahead (MUT_DIRTY is
            // unobservable on the production shapes: every drained sink sector is whole, dirty mask 8'hFF)
            reg pop_d;
            always @(posedge clk or negedge rst_l) if (!rst_l) pop_d <= 1'b0; else pop_d <= wrr_q[g*257 + 256];
            wire pop = (MUT_W == 4) ? pop_d : wrr_q[g*257 + 256];
            wire hv, ovf_l;
            ot_fifo_sram_fwft #(.W(LSW), .DEPTH(64), .MACRO(3)) u_lq (.clk(clk), .rst_n(rst_l), .push(push),
                .wdata(LSW'(sg_nx[g] + dsec[sg_r[g]])), .pop(pop), .hv(hv), .head(lq_head[g]), .ovf(ovf_l));
            // synthesis translate_off
            always @(posedge clk) if (rst_l && pop && !hv)
                $error("ctlw slice %0d lane %0d: a response landed before its FIFO head was readable", SL, g);
            // synthesis translate_on
        end
    end else begin : g_lqf
        for (genvar g = 0; g < NL; g = g + 1) begin : g_l
            assign lq_head[g] = lq[g][lqh[g]];
        end
    end endgenerate
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) begin
            wrq <= '0; wwq <= '0; lsw_v <= '0; ldc_v <= '0; ldr_v <= '0; dp1 <= '0; dp2 <= '0; dp3 <= '0;
            for (integer b = 0; b < NL; b = b + 1) begin dq_h[b] <= '0; dq_t[b] <= '0; dq_n[b] <= '0; end
            wst_ldone <= '1; wdr_ldone <= '1; lane_ovf <= 1'b0;
            for (integer b = 0; b < NL; b = b + 1) begin
                sg_r[b] <= 3'd7; sg_on[b] <= 1'b0; cl_r[b] <= 3'd7; cl_on[b] <= 1'b0; dg_r[b] <= 3'd7; dg_on[b] <= 1'b0;
                cr[b] <= (QB+1)'(LQ); wcr[b] <= (QB+1)'(LQ); lqh[b] <= '0; lqt[b] <= '0; lqn[b] <= '0; wpend[b] <= '0;
            end
        end else begin
            for (integer b = 0; b < NL; b = b + 1) begin : lane
                reg iss, land, dr_iss, wsend, wfree;
                reg [20:0] f;
                iss = 1'b0; land = 1'b0; dr_iss = 1'b0; wsend = 1'b0; wfree = 1'b0;
                wrq[b*16 + 15] <= 1'b0; lsw_v[b] <= 1'b0; ldc_v[b] <= 1'b0; ldr_v[b] <= 1'b0; wwq[b*280 + 279] <= 1'b0;
                // ---------------- stage: source region walk (regions 0..3)
                if (wst_go) begin sg_r[b] <= 3'd0; sg_on[b] <= 1'b0; cl_r[b] <= 3'd4; cl_on[b] <= 1'b0; wst_ldone[b] <= 1'b0; end
                else if (sg_r[b] < 3'd4) begin
                    if (!sg_on[b]) begin
                        f = first_of(21'(lo[sg_r[b]] >> 3), 32'(sl_q) * NL + b);
                        if (rv[sg_r[b]] && f <= 21'(hi[sg_r[b]] >> 3)) begin
                            sg_nx[b] <= f; sg_end[b] <= 21'(hi[sg_r[b]] >> 3); sg_on[b] <= 1'b1;
                        end else sg_r[b] <= sg_r[b] + 3'd1;
                    end else if (cr[b] != 0) begin
                        iss = 1'b1;
                        wrq[b*16 +: 16] <= {1'b1, sg_nx[b][14:0]};
                        if (LQSRAM == 0) lq[b][lqt[b]] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        if (lqt[b] == '0) lq_first[b] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        lqt[b] <= lqt[b] + 1'b1;
                        if (sg_nx[b] + 21'd32 > sg_end[b]) begin sg_on[b] <= 1'b0; sg_r[b] <= sg_r[b] + 3'd1; end
                        else sg_nx[b] <= sg_nx[b] + 21'd32;
                    end
                end
                // responses land in request order
                if (wrr_q[b*257 + 256]) begin
                    land = 1'b1;
                    lsw_v[b] <= 1'b1; lsw_sec[b*LSW +: LSW] <= (MUT_W == 1) ? lq_first[b] : lq_head[b];
                    lsw_d[b*256 +: 256] <= wrr_q[b*257 +: 256];
                    lqh[b] <= lqh[b] + 1'b1;
                end
                lqn[b] <= lqn[b] + iss - land;
                if (lqn[b] == (LFB+1)'(LFD) && iss && !land) lane_ovf <= 1'b1;
                cr[b] <= cr[b] - iss + wrq_cr_q[b];
                // sink dirty-mask clears (regions 4, 5; the local span), one sector a lane an edge
                if (!wst_go && cl_r[b] < 3'd6) begin
                    if (!cl_on[b]) begin
                        f = first_of(21'(lb[cl_r[b]] >> 3), 32'(sl_q) * NL + b);
                        if (rv[cl_r[b]] && f <= 21'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3)) begin
                            cl_nx[b] <= LSW'(f); cl_end[b] <= LSW'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3);
                            cl_on[b] <= 1'b1;
                        end else cl_r[b] <= cl_r[b] + 3'd1;
                    end else begin
                        ldc_v[b] <= 1'b1; ldc_sec[b*LSW +: LSW] <= cl_nx[b];
                        if (21'(cl_nx[b]) + 21'd32 > 21'(cl_end[b])) begin cl_on[b] <= 1'b0; cl_r[b] <= cl_r[b] + 3'd1; end
                        else cl_nx[b] <= cl_nx[b] + LSW'(32);
                    end
                end
                if (!wst_go && sg_r[b] >= 3'd4 && sg_r[b] != 3'd7 && cl_r[b] >= 3'd6 &&
                    ((lqn[b] + iss - land) == 0 && (cr[b] - iss + wrq_cr_q[b]) == (QB+1)'(LQ))) wst_ldone[b] <= 1'b1;
                // ---------------- drain: sink regions 4 (O, unless STREAM) and 5 (R)
                if (wdr_go) begin dg_r[b] <= 3'd4; dg_on[b] <= 1'b0; wdr_ldone[b] <= 1'b0; end
                else if (dg_r[b] < 3'd6) begin
                    if (!dg_on[b]) begin
                        f = first_of(21'(d_lb[dg_r[b]] >> 3), 32'(sl_q) * NL + b);
                        if (d_rv[dg_r[b]] && !(dg_r[b] == 3'd4 && d_os) &&
                            f <= 21'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3)) begin
                            dg_nx[b] <= LSW'(f); dg_end[b] <= LSW'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3);
                            dg_on[b] <= 1'b1;
                        end else dg_r[b] <= dg_r[b] + 3'd1;
                    end else if (wcr[b] != 0) begin
                        if (!(MUT_W == 2 && 21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b]))) begin
                            dr_iss = 1'b1;
                            ldr_v[b] <= 1'b1; ldr_sec[b*LSW +: LSW] <= dg_nx[b];
                            dq_s[b][dq_t[b]] <= 21'(dg_nx[b]) - d_dsec[dg_r[b]]; dq_t[b] <= dq_t[b] + 1'b1;
                        end
                        if (21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b])) begin dg_on[b] <= 1'b0; dg_r[b] <= dg_r[b] + 3'd1; end
                        else dg_nx[b] <= dg_nx[b] + LSW'(32);
                    end
                end
                // read return: valid-driven (ldr_rv pin flop), the sector identity from the lane's in-flight FIFO
                begin : wpub
                    reg [7:0] mk; reg v3; reg [20:0] s3;
                    mk = MUT_DIRTY ? 8'hFF : ldr_dm_q[b*8 +: 8];
                    v3 = ldr_rv_q[b]; s3 = dq_s[b][dq_h[b]];
                    if (v3) dq_h[b] <= dq_h[b] + 1'b1;
                    dq_n[b] <= dq_n[b] + dr_iss - v3;
                    if (v3) begin
                        if (mk != 8'd0) begin
                            wsend = 1'b1;
                            wwq[b*280 +: 280] <= {1'b1, s3[14:0], ldr_d_q[b*256 +: 256], mk};
                        end else wfree = 1'b1;
                    end
                end
                wcr[b] <= wcr[b] - dr_iss + wfree + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend - wwq_done_q[b];
                if (!wdr_go && dg_r[b] >= 3'd6 && dg_r[b] != 3'd7 && !dr_iss && (dq_n[b] - ldr_rv_q[b]) == 0 &&
                    (MUT_W == 3 || ((wpend[b] + wsend - wwq_done_q[b]) == 0 && (wcr[b] - dr_iss + wfree + wwq_cr_q[b]) == (QB+1)'(LQ)))) wdr_ldone[b] <= 1'b1;
            end
        end
    end
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wst_dn <= 1'b1; wdr_dn <= 1'b1; ovf <= 1'b0; end
        else begin wst_dn <= (&wst_ldone) && dn_st_q; wdr_dn <= (&wdr_ldone) && dn_dr_q; ovf <= lane_ovf || dn_ov_q; end
endmodule

// Scoped source: rtl/hdc/ot_hdc_delay.sv
`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay__d4g_sfu #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_delay_ring.sv
`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay_ring__d4g_sfu #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0,
    // RING (CLAUDE HBM-ABSTRACTS views agent, default off): D >= 4 as a ring of D-1 slots plus an output register
    // (slot written at edge e is read into q at edge e + D - 1: the same q as the shift line) -- no flop-to-flop chain
    // for hold repair, every slot written / read through its own one-hot enable
    parameter integer RING = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else if (RING != 0 && D >= 4) begin : g_ring
            localparam integer N = D - 1;
            reg [W-1:0] m [0:N-1];
            reg [N-1:0] oh;                       // one-hot slot of this edge (read, then written)
            reg [W-1:0] qr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            reg [W-1:0] rd;
            integer i;
            always @(*) begin
                rd = {W{1'b0}};
                for (i = 0; i < N; i = i + 1) rd = rd | (m[i] & {W{oh[i]}});
            end
            genvar j;
            for (j = 0; j < N; j = j + 1) begin : g_s
                if (RESET != 0) begin : g_rst
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) m[j] <= {W{1'b0}}; else if (oh[j]) m[j] <= d;
                end else begin : g_nrst
                    always @(posedge clk) if (oh[j]) m[j] <= d;
                end
            end
            if (RESET != 0) begin : g_qrst
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnrst
                always @(posedge clk) qr <= rd;
            end
            assign q = qr;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_fastfp.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Low-latency binary32 add and multiply (ot_hdc_qadd__d4g_sfu / ot_hdc_qmul__d4g_sfu) for the
// decode core's stream unit and special-function pipelines.
//
// Same arithmetic, bit for bit, as the qualified five-stage pipes they stand in
// for -- rtl/proto/ot_fp32_add_rne_pipe.sv and rtl/hdc/ot_hdc_fp32_mul_pipe.sv:
// IEEE RNE with gradual underflow, every zero result canonical +0, a zero
// multiplier operand giving +0, (+-0)+(+-0) = +0, and a nonfinite operand or an
// overflowing result failing closed through `err` with y = 0.  Equivalence is
// checked cycle by cycle against those pipes (rtl/test/tb_hdc_fastfp_equiv.sv).
//
// What is different is depth.  The five-stage pipes are cut around carry
// chains that the synthesis flow maps to ripple logic (a 31-bit magnitude
// compare, 28-bit adds, a 48-bit product sum, the rounding increment); here
// every carry chain is an explicit Kogge-Stone prefix network, the product is a
// carry-save tree, and the leading-zero count is a tree whose exponent-floor
// clamp is a sentinel bit, so each operation is three register stages.
// ---------------------------------------------------------------------------

// W-bit adder with carry-in, Kogge-Stone prefix carries.
module ot_hdc_ksa__d4g_sfu #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    reg [W:0] g, p, gn, pn;
    integer l, i;
    always @* begin
        g = {a & b, cin};
        p = {a ^ b, 1'b0};
        for (l = 1; l <= W; l = l * 2) begin
            gn = g;
            pn = p;
            for (i = l; i <= W; i = i + 1) begin
                gn[i] = g[i] | (p[i] & g[i - l]);
                pn[i] = p[i] & p[i - l];
            end
            g = gn;
            p = pn;
        end
    end
    assign s = (a ^ b) ^ g[W-1:0];
    assign cout = g[W];
endmodule

// Leading-zero count of a 32-bit word as a tree (n = 32 for zero).
module ot_hdc_lzc32__d4g_sfu (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule

// 24 x 24 unsigned product in two halves, so a pipeline register can sit in
// the middle of the tree: 24 AND rows, Wallace reduction by vector 3:2
// compressors 24 -> 16 -> 11 -> 8 (ot_hdc_mul24_rows__d4g_sfu), then 8 -> 6 -> 4 -> 3
// -> 2 and a Kogge-Stone final add (ot_hdc_mul24_sum__d4g_sfu).  Rows are flat vectors,
// row k in bits [48k +: 48]; a compressor writes its sum to row 2i and its
// carry to row 2i+1.
module ot_hdc_mul24_rows__d4g_sfu (
    input  wire [23:0]     a,
    input  wire [23:0]     b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;        // {carry, sum} of three rows
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a & {24{b[i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

module ot_hdc_mul24_sum__d4g_sfu (
    input  wire [48*8-1:0] rows,
    output wire [47:0]     p
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(rows[144*i +: 48], rows[144*i + 48 +: 48], rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire unused_cout;
    ot_hdc_ksa__d4g_sfu #(.W(48)) u_cpa (.a(l7[47:0]), .b(l7[95:48]), .cin(1'b0), .s(p), .cout(unused_cout));
endmodule

// ---------------------------------------------------------------------------
// Binary32 add, LATENCY 3, II 1.  Stage for stage:
//   1  decode; |b| > |a| as one 31-bit prefix compare of the encodings; both
//      exponent differences; the smaller significand aligned with a jam
//   2  the add and the subtract (both prefix adders); the add's one-bit
//      renormalize; the cancellation normalize, its shift the leading-zero
//      count of the difference OR a sentinel at the exponent floor
//   3  round to nearest even (prefix increment), encode, the refusals
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_fast__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    //: Magnitude order is the integer order of the encodings (a subnormal's
    //: exponent 1 and a normal's hidden bit agree with it), so the swap is one
    //: compare: b[30:0] > a[30:0] exactly when a - b borrows.
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksa__d4g_sfu #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire swap = !cmp_c;
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksa__d4g_sfu #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksa__d4g_sfu #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    //: Three guard bits, everything shifted past them OR-ed into the lowest.
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    //: Both alignments, then the pick: when b is the larger b's exponent is
    //: not below a's, so dba is the distance; otherwise dab.
    wire [27:0] small_a = jam28(a_man, dba);
    wire [27:0] small_b = jam28(b_man, dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= bypass;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= bypass_code;
        s1_sub <= a[31] ^ b[31];
        s1_sign <= swap ? b[31] : a[31];
        s1_exp <= swap ? b_exp : a_exp;
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? small_a : small_b;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum, dif;
    wire sum_c, dif_c;
    ot_hdc_ksa__d4g_sfu #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum), .cout(sum_c));
    ot_hdc_ksa__d4g_sfu #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif), .cout(dif_c));
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    //: The authority normalizes one bit at a time while bit 26 is clear and the
    //: exponent is above 1: the shift is min(lzc, exp - 1).  A one at bit
    //: 26 - (exp - 1) makes the count stop there.
    wire [7:0]  room = s1_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz;
    ot_hdc_lzc32__d4g_sfu u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz));
    wire [26:0] sub_val = dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksa__d4g_sfu #(.W(8)) u_esub (.a(s1_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksa__d4g_sfu #(.W(8)) u_eadd (.a(s1_exp), .b(8'd0), .cin(carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_code <= s1_code; s2_sign <= s1_sign;
        s2_zero <= s1_sub && (dif == 28'd0);
        s2_exp <= s1_sub ? exp_sub : exp_add;
        s2_val <= s1_sub ? sub_val : add_val;
    end

    // -- stage 3 ------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_sfu #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd), .cout(rnd_c));
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, s2_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {s2_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (s2_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= s2_code; err <= s2_err; end
            else if (s2_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Binary32 multiply, LATENCY 3, II 1.
//   1  decode; subnormal operands normalized (tree LZC); the exponent sum;
//      the partial products and three carry-save levels (24 -> 8 rows)
//   2  the rest of the tree and the prefix final add; both exponent
//      decisions (leading bit 47 or 46) and the subnormal-result alignment
//      masks, all from the exponent sum alone
//   3  the product's top bit picks the decision; align, round, encode, refuse
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_fast__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_sfu u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_sfu u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    //: The authority's powers: field - 150 for a normal, -149 - shift for a
    //: subnormal (a normal has no leading zero, so the shift is 0 there).
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksa__d4g_sfu #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));

    //: The first three compressor levels ride in stage 1, after the normalize.
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows__d4g_sfu u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= nonfinite || zero;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_sign <= a[31] ^ b[31];
        s1_rows <= rows;
        s1_power <= power;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [47:0] prod;
    ot_hdc_mul24_sum__d4g_sfu u_sum (.rows(s1_rows), .p(prod));
    //: floor = power + msb; a subnormal result when floor < -126, and then the
    //: alignment is -(power + 149) whatever the msb, so only the normal path's
    //: fixed alignment (23 or 24) depends on the product.
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    //: sh_sub >= 24 whenever it is used; clamp at 63 (everything below).
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_sign <= s1_sign;
        s2_prod <= prod;
        s2_sub47 <= fl47 < -12'sd126;
        s2_sub46 <= fl46 < -12'sd126;
        s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_sh <= shc; s2_mr <= m_round; s2_ms <= m_sticky;
    end

    // -- stage 3 ------------------------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_sfu #(.W(24)) u_rnd (.a(main), .b(24'd0), .cin(rb && (st || main[0])), .s(rnd), .cout(rnd_c));
    wire carry = !is_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = fl + {11'd0, carry};
    wire over = !is_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = is_sub && rnd[23];
    wire [31:0] code = is_sub ? (sub_carry ? {s2_sign, 8'h01, 23'd0} : {s2_sign, 8'h00, rnd[22:0]})
                              : {s2_sign, field, man[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= 32'd0; err <= s2_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// Fault-reporting wrappers, as ot_hdc_fadd / ot_hdc_fmul but LATENCY 3.
module ot_hdc_qadd__d4g_sfu #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_add_fast__d4g_sfu (unchanged); L > 3 is ot_hdc_fp32_add_lat__d4g_sfu #(L), bit for bit
    // the same values, with the extra cuts (rtl/hdc/ot_hdc_fp32_add_lat__d4g_sfu.sv) so no stage carries two prefix adders.
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_add_fast__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul__d4g_sfu #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_mul_fast__d4g_sfu (unchanged); L > 3 is ot_hdc_fp32_mul_lat__d4g_sfu #(L), bit for bit
    // the same values; L >= 5 cuts the four carry-save levels from the 48-bit prefix add (fast stage 2, the lane
    // tile's -180 ps TT path s1_rows -> s2_prod).
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_mul_fast__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fastfp_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 serial-domain wrappers over the fast binary32 units (rtl/hdc/ot_hdc_fastfp.sv), kept out of that file so
// the records that pin it stay current.  Needs rtl/hdc/ot_hdc_fastfp.sv (or its DPI stand-ins); the non-default
// branches also need rtl/hdc/ot_hdc_fp32_mul_lat__d4g_sfu.sv, rtl/hdc/ot_hdc_fp32_add_lat__d4g_sfu.sv and rtl/hdc/ot_hdc_prefix.sv.
//   ot_hdc_qmul_lat__d4g_sfu #(LAT)       ot_hdc_qmul__d4g_sfu at LAT 3 (default), ot_hdc_fp32_mul_lat4__d4g_sfu / _lat5i / _lat #(LAT)
//   ot_hdc_qadd_lat__d4g_sfu #(KEEP, LAT) ot_hdc_qadd__d4g_sfu (default), ot_hdc_fp32_add_lat3__d4g_sfu / _lat4i (keep-prefix adders)
//   ot_hdc_kadd__d4g_sfu / _kge / _kinc   integer add / compare / increment: behavioural (K = 0) or keep-prefix (K = 1)
// ---------------------------------------------------------------------------
// ot_hdc_qmul_lat__d4g_sfu #(LAT): ot_hdc_qmul__d4g_sfu with the multiplier's latency as a parameter.  LAT = 3 is ot_hdc_qmul__d4g_sfu
// itself (ot_hdc_fp32_mul_fast__d4g_sfu); LAT = 4..7 is ot_hdc_fp32_mul_lat__d4g_sfu #(LAT) (rtl/hdc/ot_hdc_fp32_mul_lat__d4g_sfu.sv, which
// needs rtl/hdc/ot_hdc_fp32_add_lat__d4g_sfu.sv), bit-identical to it (21d9aab2: 5,000,000 biased pairs).  W11 serial
// domain: the 3-stage multiply misses 1.111 ns at SS; LAT 4 reaches 987 MHz.
module ot_hdc_qmul_lat__d4g_sfu #(
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (LAT == 3) begin : g_l3
        ot_hdc_fp32_mul_fast__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_l4
        // the fixed LAT-4 top: a plain module name, so synthesis can keep it as its own hierarchy
        // (ORFS SYNTH_KEEP_MODULES) and ABC maps it as the standalone unit
        ot_hdc_fp32_mul_lat4__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 5) begin : g_l5
        // LAT 5 is the input-cut variant (C1 + C3; rtl/hdc/ot_hdc_fp32_mul_lat__d4g_sfu.sv): the operand multiplexer ahead of
        // the unit shares a stage with the decode / normalise, not with the partial products (W11 serial domain)
        ot_hdc_fp32_mul_lat5i__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_ln
        ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// ot_hdc_qadd_lat__d4g_sfu #(KEEP, LAT): ot_hdc_qadd__d4g_sfu, or (KEEP = 1) the plain ot_hdc_fp32_add_lat3__d4g_sfu top of
// rtl/hdc/ot_hdc_fp32_add_lat__d4g_sfu.sv (needs rtl/hdc/ot_hdc_prefix.sv): the same binary32 add, bit for bit, with
// (* keep *) Kogge-Stone prefix adders that ABC cannot re-ripple inside a parent block; LAT = 4 (KEEP = 1) is
// the input-cut ot_hdc_fp32_add_lat4i__d4g_sfu (W11 serial domain, 0.9 GHz at SS).
module ot_hdc_qadd_lat__d4g_sfu #(
    parameter integer KEEP = 0,
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (KEEP == 0) begin : g_fast
        ot_hdc_fp32_add_fast__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_keep4
        ot_hdc_fp32_add_lat4i__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_keep
        ot_hdc_fp32_add_lat3__d4g_sfu u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Keep-prefix integer arithmetic for the W11 serial-domain build (K = 1: rtl/hdc/ot_hdc_prefix.sv, whose
// (* keep *) Kogge-Stone levels ABC cannot re-ripple; K = 0: the behavioural operator, the unit as it was).
module ot_hdc_kadd__d4g_sfu #(parameter integer W = 24, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire cin, output wire [W-1:0] s, output wire cout
);
    generate if (K == 0) begin : g_b
        assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
    end else begin : g_k
        ot_hdc_ksadd_k__d4g_sfu #(.W(W)) u (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
    end endgenerate
endmodule

// ge = (a >= b), unsigned
module ot_hdc_kge__d4g_sfu #(parameter integer W = 32, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, output wire ge
);
    generate if (K == 0) begin : g_b
        assign ge = (a >= b);
    end else begin : g_k
        wire [W-1:0] unused_s;
        ot_hdc_ksadd_k__d4g_sfu #(.W(W)) u (.a(a), .b(~b), .cin(1'b1), .s(unused_s), .cout(ge));
    end endgenerate
endmodule

// y = a + inc (mod 2^W)
module ot_hdc_kinc__d4g_sfu #(parameter integer W = 16, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire inc, output wire [W-1:0] y
);
    generate if (K == 0) begin : g_b
        assign y = a + {{(W-1){1'b0}}, inc};
    end else begin : g_k
        wire unused_co;
        ot_hdc_inc_k__d4g_sfu #(.W(W)) u (.a(a), .inc(inc), .y(y), .co(unused_co));
    end endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_add_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_add_lat__d4g_sfu #(LAT): the binary32 adder of ot_hdc_fp32_add_fast__d4g_sfu (rtl/hdc/ot_hdc_fastfp.sv), bit for bit,
// with LAT = 3..6 register stages.  A MEASUREMENT vehicle for the 1.2 GHz @ SS decision (W11, 2026-09-30): the
// same logic is cut at up to three extra boundaries, so the SS fmax against LAT shows the flop overhead.
//   A1  decode, magnitude compare, exponent differences        | cut C_A  (LAT >= 5)
//   A2  both jammed alignments, the swap pick
//   B1  28-bit sum and difference (prefix adders)               | cut C_B  (LAT >= 4)
//   B2  normalise: sentinel LZC, shift, exponent adjust
//   C1  round increment (prefix adder)                          | cut C_C  (LAT >= 6)
//   C2  encode, subnormal, overflow, canonical zero -> y
//   (B2 is cut after the sentinel LZC when LAT >= 7)
// Every prefix adder is ot_hdc_ksadd_k__d4g_sfu (rtl/hdc/ot_hdc_prefix.sv): (* keep *) Kogge-Stone levels, so ABC cannot
// re-ripple the carries inside a parent block (W13: the plain form closed standalone and failed in context).
// LAT 3 has the cuts of ot_hdc_fp32_add_fast__d4g_sfu (after A, after B, after C).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_lat__d4g_sfu #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bits {D, C, B, A} (LAT must be 3 + their count); -1: by LAT.
    // W11 serial domain: CUTS = 4'b0001 (C_A, LAT 4) cuts the INPUT side, so an operand multiplexer in front of
    // the unit shares stage 1 with the decode / compare instead of the alignment
    parameter integer CUTS = -1,
    // DRST 0 (fe-push-hphys-1010, opt-in via OT_FP_DATA_NORST): only the valid bits are reset (cuts VB, valid_out);
    // y / err / data cuts are plain flops (consumers qualify them with valid_out).  1: legacy, every stage bit reset.
    parameter integer DRST = `ifdef OT_FP_DATA_NORST 0 `else 1 `endif
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;     // inside B2: after the sentinel LZC
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k__d4g_sfu #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k__d4g_sfu #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k__d4g_sfu #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 boundary bundle
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    ot_hdc_w11_cut__d4g_sfu #(.W(WA + 1), .CUT(CUT_A), .VB(DRST ? -1 : WA - 1)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    // ---- A2 ----------------------------------------------------------------------------------------
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k__d4g_sfu #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k__d4g_sfu #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    ot_hdc_w11_cut__d4g_sfu #(.W(WB), .CUT(CUT_B), .VB(DRST ? -1 : WB - 1)) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    // ---- B2 ----------------------------------------------------------------------------------------
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32__d4g_sfu u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // B2a -> B2b boundary (LAT >= 7)
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    ot_hdc_w11_cut__d4g_sfu #(.W(WD), .CUT(CUT_D), .VB(DRST ? -1 : WD - 1)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k__d4g_sfu #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k__d4g_sfu #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_sfu #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [WC-1:0] c2_in;
    ot_hdc_w11_cut__d4g_sfu #(.W(WC), .CUT(CUT_C), .VB(DRST ? -1 : WC - 1)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    // ---- C2 ----------------------------------------------------------------------------------------
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate if (DRST != 0) begin : g_yr
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
            else begin
                valid_out <= u_v;
                if (u_byp) begin y <= u_code; err <= u_err; end
                else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
                else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
                else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
            end
        end
    end else begin : g_yn
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= u_v;
        end
        always @(posedge clk) begin
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end endgenerate
endmodule

// a W-bit bundle, registered when CUT = 1 (bit 0... the bundle's MSB is the valid, reset to 0), else passed through
// VB >= 0 (fe-push-hphys-1010, opt-in): only bit VB (the bundle's valid) is reset; the data bits are plain flops (a wide
// datapath costs no reset fan-out; validity travels on the reset bit).  VB < 0 (default): every bit reset, as before.
module ot_hdc_w11_cut__d4g_sfu #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

// fixed tops for the hardening sweep
// the W11 serial-domain LAT-4 adder: the LAT-3 cuts plus C_A (after the decode / compare), bit-identical
module ot_hdc_fp32_add_lat4i__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(4), .CUTS(1)) u (.*);
endmodule
module ot_hdc_fp32_add_lat3__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(3)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat5__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat6__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_add_lat7__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_sfu #(.LAT(7)) u (.*);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_mul_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_mul_lat__d4g_sfu #(LAT): the binary32 multiplier of ot_hdc_fp32_mul_fast__d4g_sfu (rtl/hdc/ot_hdc_fastfp.sv), bit for
// bit, with LAT = 3..9 register stages (W11 measurement vehicle for 1.2 GHz @ SS; see ot_hdc_fp32_add_lat__d4g_sfu).
//   S1  decode, subnormal LZC                             | C5 (LAT >= 8; margin rule 2026-10-06)
//       normalise shift                                   | C1 (LAT >= 6)
//       partial products + three carry-save levels, the exponent sum
//   S2  four carry-save levels                            | C2 (LAT >= 5)
//       the 48-bit prefix add; the subnormal masks
//   S3  select, subnormal shift, sticky/round bits        | C3 (LAT >= 4)
//       round increment (prefix add)                      | C4 (LAT >= 7)
//       encode                                            | C6 (LAT >= 9; margin rule 2026-10-06)
//   C7 (LAT >= 10; margin m3 2026-10-06) sits in front of S1: field / zero / non-finite decode | LZC, power
//       refusals -> y
// Every prefix adder is ot_hdc_ksadd_k__d4g_sfu (rtl/hdc/ot_hdc_prefix.sv, (* keep *) levels).
// Uses ot_hdc_w11_cut__d4g_sfu (rtl/hdc/ot_hdc_fp32_add_lat__d4g_sfu.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_lat__d4g_sfu #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bit k-1 = C<k> (LAT must be 3 + their count); -1: by LAT as above.
    // W11 serial domain: CUTS = 4'b0101 (C1 + C3, LAT 5) cuts the INPUT side, so an operand multiplexer in front
    // of the unit shares stage 1 with the decode / normalise instead of the partial-product rows
    parameter integer CUTS = -1,
    // KCP > 1 (margin m3, 2026-10-06): the C1 operand register is KCP kept copies (ot_hdc_mul_kcp48__d4g_sfu), each driving
    // 24/KCP partial products, so the 24-load operand broadcast to the partial-product rows is a local net.  Values
    // identical (every copy captures the same a_n / b_n); no added cycle.  Needs CUT1.
    parameter integer KCP = 1,
    // Opt-in: reset only valid bits at extra cuts; payload is ignored until valid.
    parameter integer DRST = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    localparam integer CUT7 = (CUTS >= 0) ? (CUTS / 64) % 2 : (LAT >= 10) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + CUT7 + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_mul_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- S1a: decode, normalise --------------------------------------------------------------------
    // C7: field / zero / non-finite decode | LZC, power
    wire [68:0] c7;
    ot_hdc_w11_cut__d4g_sfu #(.W(69), .CUT(CUT7), .VB(DRST ? -1 : 69-1)) u_c7 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a, b, (a[30:23] == 8'd0), (b[30:23] == 8'd0),
            (a[30:23] == 8'hff) || (b[30:23] == 8'hff), (a[30:0] == 31'd0) || (b[30:0] == 31'd0)}), .q(c7));
    wire        x_v, x_afz, x_bfz, nonfinite, zero;
    wire [31:0] x_a, x_b;
    assign {x_v, x_a, x_b, x_afz, x_bfz, nonfinite, zero} = c7;
    wire [7:0]  a_field = x_a[30:23];
    wire [7:0]  b_field = x_b[30:23];
    wire [23:0] a_raw = {!x_afz, x_a[22:0]};
    wire [23:0] b_raw = {!x_bfz, x_b[22:0]};
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_sfu u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_sfu u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = x_afz ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = x_bfz ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut__d4g_sfu #(.W(W5), .CUT(CUT5), .VB(DRST ? -1 : W5-1)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({x_v, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), x_a[31] ^ x_b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = n_ar << n_al;
    wire [23:0] b_n = n_br << n_bl;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut__d4g_sfu #(.W(W1), .CUT(CUT1), .VB(DRST ? -1 : W1-1)) u_c1 (.clk(clk), .rst_n(rst_n),
        .d({n_v, n_bz, n_err, n_sign, a_n, b_n, n_ap, n_bp}),
        .q(c1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = c1;
    // ---- S1b: rows, exponent sum ------------------------------------------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k__d4g_sfu #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    generate if (KCP > 1 && CUT1 != 0) begin : g_kcp
        wire [KCP*24-1:0] ka, kb;
        genvar k;
        for (k = 0; k < KCP; k = k + 1) begin : g_c
            ot_hdc_mul_kcp48__d4g_sfu u_k (.clk(clk), .rst_n(rst_n),
`ifdef NEGK
                .d({a_n ^ ((k == 1) ? 24'd1 : 24'd0), b_n}),   // bench negative control only
`else
                .d({a_n, b_n}),
`endif .q({ka[24*k +: 24], kb[24*k +: 24]}));
        end
        ot_hdc_mul24_rows_k__d4g_sfu #(.K(KCP)) u_rows (.a(ka), .b(kb), .rows(rows));
    end else begin : g_nokcp
        ot_hdc_mul24_rows__d4g_sfu u_rows (.a(p_a), .b(p_b), .rows(rows));
    end endgenerate

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= p_v;
    end
    always @(posedge clk) begin
        s1_byp <= p_byp; s1_err <= p_err; s1_sign <= p_sign; s1_rows <= rows; s1_power <= power;
    end

    // ---- S2a: compress to two rows; masks ----------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut__d4g_sfu #(.W(W2), .CUT(CUT2), .VB(DRST ? -1 : W2-1)) u_c2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = c2;
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k__d4g_sfu #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl47; s2_fl46 <= q_fl46;
        s2_sh <= q_sh; s2_mr <= q_mr; s2_ms <= q_ms;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut__d4g_sfu #(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-1)) u_c3 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_sfu #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut__d4g_sfu #(.W(W4), .CUT(CUT4), .VB(DRST ? -1 : W4-1)) u_c4 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, r_fl, rnd_w, rnd_cw}), .q(c4));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c;
    wire [1:0]  o_err;
    wire signed [11:0] o_fl;
    wire [23:0] rnd;
    assign {o_v, o_byp, o_err, o_sign, o_sub, o_fl, rnd, rnd_c} = c4;
    // ---- S3c: encode --------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = o_fl + {11'd0, carry};
    wire over = !o_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // C6: encode | refusals -> y
    localparam integer W6 = 1 + 1 + 2 + 1 + 32;
    wire [W6-1:0] c6;
    ot_hdc_w11_cut__d4g_sfu #(.W(W6), .CUT(CUT6), .VB(DRST ? -1 : W6-1)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    generate if (DRST != 0) begin : g_output_reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end
    end else begin : g_output_valid_reset
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= e_v;
        end
        always @(posedge clk) begin
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end endgenerate
endmodule

module ot_hdc_fp32_mul_lat4__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat6__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat7__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(7)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat9__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(9)) u (.*);
endmodule

// the W11 serial-domain LAT-5 multiplier: the LAT-4 cuts plus C1 (after the decode / normalise), bit-identical
module ot_hdc_fp32_mul_lat5i__d4g_sfu (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_sfu #(.LAT(5), .CUTS(5)) u (.*);
endmodule

// KCP copy of the C1 operand register: kept (SYNTH_KEEP_MODULES) so equal-D copies are never merged into one driver
module ot_hdc_mul_kcp48__d4g_sfu (input wire clk, input wire rst_n, input wire [47:0] d, output reg [47:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 48'd0; else q <= d;
endmodule

// ot_hdc_mul24_rows__d4g_sfu with the operands supplied as K copies: partial product i reads copy i*K/24 (identical values)
module ot_hdc_mul24_rows_k__d4g_sfu #(parameter integer K = 2) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a[24*(i*K/24) +: 24] & {24{b[24*(i*K/24) + i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_prefix.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Explicit log-depth adders (W10, 72f00b86; shared FP primitive copy owned by W11, rtl/hdc/ot_hdc_prefix.sv).
//
// Written as behavioural `a + b` or `a + inc`, yosys/ABC maps these adders as carry ripples (chains of MAJ or
// OR cells) even with ADDER_MAP_FILE cleared: measured at ORFS WC, 0.833 ns, a 28-bit add inside the element
// took 920 ps and a 24-bit rounding increment a chain of ten OR4/OR5 cells (W10 and W13, 2026-09-30).  Here each
// Kogge-Stone prefix level is a (* keep *) net, so synthesis must keep log2(W) levels.
//
// ot_v41_ksadd: s = a + b + cin (W bits), cout.
// ot_v41_inc:   y = a + inc (W bits), co (the carry out of the top bit).
// ---------------------------------------------------------------------------
module ot_hdc_ksadd_k__d4g_sfu #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule


module ot_hdc_inc_k__d4g_sfu #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    // t[i]: all of positions [0, i] are one, position 0 being the increment
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign t[l + 1][i] = t[l][i] & t[l][i - (1 << l)];
                end else begin : g_p
                    assign t[l + 1][i] = t[l][i];
                end
            end
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule

// Scoped source: rtl/hdc/ot_hdc_sfu.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Special-function pipelines of the hardwired decode core: exp, reciprocal and
// reciprocal square root.  Each is an unrolled chain of the qualified binary32
// multiply/add pipes (LATENCY 5, II 1) plus single-cycle integer steps, so each
// accepts one operand per cycle and returns it a fixed DEPTH later.  No divider,
// no iteration, no combinational IEEE operation.
//
// The algorithms and their operation order are the specification in
// tools/hdc_golden.py (exp, reciprocal, rsqrt); the RTL matches it bit for bit.
// ---------------------------------------------------------------------------

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_vline__d4g_sfu #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule

// exp(x): clamp to [-87, 88]; n = rint(x*log2e) by the 1.5*2^23 trick; two-
// constant Cody-Waite reduction; degree-6 Horner; 2^n added to the exponent.
module ot_hdc_exp__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 92;
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [31:0] K_MAGIC = 32'h4B400000;   //  1.5 * 2^23
    localparam [31:0] K_NMAGIC = 32'hCB400000;
    localparam [31:0] K_HI    = 32'h3F317200;   //  ln2 high part
    localparam [31:0] K_LO    = 32'h35BFBE8E;   //  ln2 low part
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t, u, n, a_hi, a_lo, r1, r, xc_d20, lo_d5;
    wire [6:0] f;
    ot_hdc_fmul m_t  (clk, rst_n, vd[1],  xc, K_LOG2E, t,   f[0]);   // 6
    ot_hdc_fadd a_u  (clk, rst_n, vd[6],  t,  K_MAGIC, u,   f[1]);   // 11
    ot_hdc_fadd a_n  (clk, rst_n, vd[11], u,  K_NMAGIC, n,  f[2]);   // 16
    ot_hdc_fmul m_hi (clk, rst_n, vd[16], n,  K_HI,    a_hi, f[3]);  // 21
    ot_hdc_fmul m_lo (clk, rst_n, vd[16], n,  K_LO,    a_lo, f[4]);  // 21
    ot_hdc_delay__d4g_sfu #(.W(32), .D(20)) d_x (clk, rst_n, xc, xc_d20);
    ot_hdc_fadd a_r1 (clk, rst_n, vd[21], xc_d20, {~a_hi[31], a_hi[30:0]}, r1, f[5]);  // 26
    ot_hdc_delay__d4g_sfu #(.W(32), .D(5)) d_lo (clk, rst_n, a_lo, lo_d5);
    ot_hdc_fadd a_r  (clk, rst_n, vd[26], r1, {~lo_d5[31], lo_d5[30:0]}, r, f[6]);     // 31

    // Horner: p = C0; six times p = p*r + C[k]; r travels in 10-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay__d4g_sfu #(.W(32), .D(10)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_fmul u_m (clk, rst_n, vd[31 + 10*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_fadd u_a (clk, rst_n, vd[36 + 10*(k-1)], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    // n as an integer: u = 1.5*2^23 + n exactly, so n sits in u's fraction.
    reg  [8:0] nint;
    wire [8:0] nint_d;
    always @(posedge clk) nint <= u[8:0];   // low 9 bits of 0x400000 + n are n
    ot_hdc_delay__d4g_sfu #(.W(9), .D(79)) d_n (clk, rst_n, nint, nint_d);   // 12 -> 91
    always @(posedge clk) y <= pa[6] + {{14{nint_d[8]}}, nint_d, 23'd0};   // 92

    assign fault = |{f, hf};
endmodule

// 1/d: seed 0x7ef311c7 - bits(d), three Newton-Raphson steps y*(2 - d*y).
module ot_hdc_recip__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 46;
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0, d1;
    always @(posedge clk) begin
        // The bit seed wraps above this finite positive denominator.
        // Saturate that unsupported range to +0 before Newton iteration.
        y0 <= (!x[31] && x[30:23] != 8'hff && x > 32'h7EF311C7)
            ? 32'h00000000 : 32'h7EF311C7 - x;
        d1 <= x;
    end
    wire [31:0] yi [0:3];
    wire [31:0] dd [0:2];
    wire [31:0] m [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [8:0] f;
    assign yi[0] = y0;
    assign dd[0] = d1;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_d
                ot_hdc_delay__d4g_sfu #(.W(32), .D(15)) d_d (clk, rst_n, dd[k], dd[k+1]);
            end
            ot_hdc_fmul m_m (clk, rst_n, vd[1 + 15*k], dd[k], yi[k], m[k], f[3*k]);
            ot_hdc_fadd a_s (clk, rst_n, vd[6 + 15*k], 32'h40000000, {~m[k][31], m[k][30:0]}, s[k], f[3*k+1]);
            ot_hdc_delay__d4g_sfu #(.W(32), .D(10)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y (clk, rst_n, vd[11 + 15*k], yd[k], s[k], yi[k+1], f[3*k+2]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_rsqrt__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 61;
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    always @(posedge clk) y0 <= 32'h5F3759DF - {1'b0, x[31:1]};
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_fmul m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // 5
    ot_hdc_delay__d4g_sfu #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 6
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay__d4g_sfu #(.W(32), .D(20)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_fmul m_yy (clk, rst_n, vd[1 + 20*k],  yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_fmul m_hm (clk, rst_n, vd[6 + 20*k],  hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_fadd a_s  (clk, rst_n, vd[11 + 20*k], 32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay__d4g_sfu #(.W(32), .D(15)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y  (clk, rst_n, vd[16 + 20*k], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fdiv.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION, fully pipelined: II 1, fixed DEPTH 31.
//
// WHY A NEW DIVIDER.  The repository's qualified correctly rounded divider,
// rtl/abi3/ot_a3_fp32_div_rne_pipe.sv, is a bisection FSM: one operand in
// flight, an in_ready handshake and ~50 cycles per quotient.  The decode core
// streams one operand per cycle, so it needs the same function as a systolic
// pipe.  This is the digit recurrence that rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv
// uses for the square root, applied to division: one quotient bit per stage,
// a 25-bit compare-and-subtract per stage, no multiplier anywhere.
//
// FUNCTION.  y = RN_even(a / b) in binary32 with gradual underflow, and every
// zero result canonical +0 -- the arithmetic of tools/hdc_golden_v41.div and of
// the qualified add/mul pipes.  Operands may be subnormal.  A nonfinite
// operand, a zero divisor or an overflowing quotient FAILS CLOSED: `fault` on
// that result and y = +0 (the pipes' convention; never an infinity).
//
// EXACTNESS.  Both significands are normalised to [2^23, 2^24).  The recurrence
// forms Q = floor(ma * 2^26 / mb), 26 or 27 significant bits, and the final
// remainder; the remainder is nonzero exactly when the quotient is inexact, so
// {Q, remainder != 0} carries the guard and a true sticky bit.  A subnormal
// result shifts {significand, guard} right with the shifted-out bits ORed into
// the sticky, then rounds once.  So the result is rounded exactly once, from
// the exact quotient.
//
// Stages: 1 decode/normalise, 27 recurrence (quotient bits 2^0 .. 2^-26),
// 3 finish (select and exponent, subnormal shift, round and encode).
// ---------------------------------------------------------------------------
module ot_hdc_fdiv__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer DEPTH = 31;
    localparam integer QB = 27;

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- decode: normalise both significands (priority encoder + shift) ------
    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    wire [33:0] na = norm(a[30:23], a[22:0]);
    wire [33:0] nb = norm(b[30:23], b[22:0]);

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_zero <= (a[30:0] == 31'd0);
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // ---- recurrence: stage j forms quotient bit 2^-j -----------------------------
    reg [24:0]        r_rem  [0:QB-1];
    reg [QB-1:0]      r_q    [0:QB-1];
    reg [23:0]        r_mb   [0:QB-1];
    reg               r_sign [0:QB-1];
    reg               r_zero [0:QB-1];
    reg               r_bad  [0:QB-1];
    reg signed [10:0] r_e    [0:QB-1];

    genvar j;
    generate
        for (j = 0; j < QB; j = j + 1) begin : g_rec
            wire [24:0] src_rem = (j == 0) ? {1'b0, d_ma} : {r_rem[j-1][23:0], 1'b0};
            wire [23:0] src_mb  = (j == 0) ? d_mb : r_mb[j-1];
            wire [QB-1:0] src_q = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [25:0] diff = {1'b0, src_rem} - {2'b0, src_mb};
            wire take = !diff[25];
            always @(posedge clk) begin
                r_rem[j]  <= take ? diff[24:0] : src_rem;
                r_q[j]    <= {src_q[QB-2:0], take};
                r_mb[j]   <= src_mb;
                r_sign[j] <= (j == 0) ? d_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? d_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? d_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? d_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[QB-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[QB-1];
        f1_zero <= r_zero[QB-1];
        f1_bad  <= r_bad[QB-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[QB-1]);
            f1_be  <= r_e[QB-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[QB-1]);
            f1_be  <= r_e[QB-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = (25'd1 << sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3: round to nearest even, encode ----------------------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    wire [30:0] code = {f2_field, f2_sig[22:0]} + {30'd0, rup};
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule

// Scoped source: rtl/hdc/v41x/ot_dsrom_su_f12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery su_swiglu (2026-10-04): 1.2 GHz copies of the SU's exact SFU blocks (new files only; the
// originals in rtl/hdc/v41x/ot_hdc_v41x_sfu.sv are unchanged).  Same function bit for bit; only register boundaries
// move and integer adders become keep-prefix (ot_hdc_kadd__d4g_sfu / ot_hdc_kinc__d4g_sfu K 1, rtl/hdc/ot_hdc_prefix.sv), for the
// 1.2 GHz build (rtl/hdc/ot_hdc_fastfp_lat_f12.sv):
//   ot_dsrom_exp_f12__d4g_sfu   ot_hdc_v41x_exp__d4g_sfu with n = rint(x log2e) over two stages (shift | round + sign) and the two
//                      range-reduction adds on the 6-stage f12 adder (ot_dsrom_add_f12_l6__d4g_sfu): DEPTH + 1 + 2 (6 - LA)
//   ot_dsrom_fdiv_f12__d4g_sfu  ot_hdc_v41x_fdiv__d4g_sfu with the operand normalisation over two stages (leading one | shift),
//                      keep-prefix trial subtractions and 3*mb, and the round / encode over two stages: DEPTH 21
// Equivalence to the originals: tools/dsrom_su_swiglu.py runs the fused benches against the golden; the lane bench
// exercises both on the same operands.
// ---------------------------------------------------------------------------
module ot_dsrom_exp_f12__d4g_sfu #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_sfu)
    parameter integer LA = 3,                   // add latency (ot_hdc_qadd_lat__d4g_sfu: 3, or 4 input cut)
    parameter integer ASUM = 0                  // S81-RERUN (default off): the six polynomial adds get the sum | LZC
                                                //   cut (ot_hdc_fp32_add_f12_l5s, LA 4 -> 5): +6 cycles
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer T_N = 1 + LM + 2;        // n registered (1.2 GHz: shift | round + sign, two stages)
    localparam integer T_K = T_N + 1;           // table products registered
    localparam integer LR = 6;                  // r = (x - n ln2_hi) - n ln2_lo: the 6-stage f12 adder (routed: these two
                                                //   adders' compare -> align stage was the lane's only 1.2 GHz miss)
    localparam integer T_R1 = T_K + LR;
    localparam integer T_R = T_R1 + LR;
    localparam integer LP = LA + ASUM;           // the polynomial adds' latency
    localparam integer T_P = T_R + 6 * (LM + LP);
    localparam integer DEPTH = T_P + 1;         // 7 LM + 6 LA + 2 LR + 5: 76 at LM 5 / LA 4
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction
    //: {n*LN2_HI, RN(n*LN2_LO)}: the golden's binary32 products (hdc_golden.mul,
    //: canonical +0 at n = 0), indexed by n's low 8 bits.
    function automatic [63:0] ln2_nk(input [7:0] nk);
        case (nk)
            8'd130: ln2_nk = {32'hC2AEAC38, 32'hB93CBF94};   // n = -126
            8'd131: ln2_nk = {32'hC2AD4954, 32'hB93B4017};   // n = -125
            8'd132: ln2_nk = {32'hC2ABE670, 32'hB939C09A};   // n = -124
            8'd133: ln2_nk = {32'hC2AA838C, 32'hB938411C};   // n = -123
            8'd134: ln2_nk = {32'hC2A920A8, 32'hB936C19F};   // n = -122
            8'd135: ln2_nk = {32'hC2A7BDC4, 32'hB9354222};   // n = -121
            8'd136: ln2_nk = {32'hC2A65AE0, 32'hB933C2A5};   // n = -120
            8'd137: ln2_nk = {32'hC2A4F7FC, 32'hB9324328};   // n = -119
            8'd138: ln2_nk = {32'hC2A39518, 32'hB930C3AB};   // n = -118
            8'd139: ln2_nk = {32'hC2A23234, 32'hB92F442E};   // n = -117
            8'd140: ln2_nk = {32'hC2A0CF50, 32'hB92DC4B1};   // n = -116
            8'd141: ln2_nk = {32'hC29F6C6C, 32'hB92C4534};   // n = -115
            8'd142: ln2_nk = {32'hC29E0988, 32'hB92AC5B6};   // n = -114
            8'd143: ln2_nk = {32'hC29CA6A4, 32'hB9294639};   // n = -113
            8'd144: ln2_nk = {32'hC29B43C0, 32'hB927C6BC};   // n = -112
            8'd145: ln2_nk = {32'hC299E0DC, 32'hB926473F};   // n = -111
            8'd146: ln2_nk = {32'hC2987DF8, 32'hB924C7C2};   // n = -110
            8'd147: ln2_nk = {32'hC2971B14, 32'hB9234845};   // n = -109
            8'd148: ln2_nk = {32'hC295B830, 32'hB921C8C8};   // n = -108
            8'd149: ln2_nk = {32'hC294554C, 32'hB920494B};   // n = -107
            8'd150: ln2_nk = {32'hC292F268, 32'hB91EC9CE};   // n = -106
            8'd151: ln2_nk = {32'hC2918F84, 32'hB91D4A50};   // n = -105
            8'd152: ln2_nk = {32'hC2902CA0, 32'hB91BCAD3};   // n = -104
            8'd153: ln2_nk = {32'hC28EC9BC, 32'hB91A4B56};   // n = -103
            8'd154: ln2_nk = {32'hC28D66D8, 32'hB918CBD9};   // n = -102
            8'd155: ln2_nk = {32'hC28C03F4, 32'hB9174C5C};   // n = -101
            8'd156: ln2_nk = {32'hC28AA110, 32'hB915CCDF};   // n = -100
            8'd157: ln2_nk = {32'hC2893E2C, 32'hB9144D62};   // n = -99
            8'd158: ln2_nk = {32'hC287DB48, 32'hB912CDE5};   // n = -98
            8'd159: ln2_nk = {32'hC2867864, 32'hB9114E68};   // n = -97
            8'd160: ln2_nk = {32'hC2851580, 32'hB90FCEEA};   // n = -96
            8'd161: ln2_nk = {32'hC283B29C, 32'hB90E4F6D};   // n = -95
            8'd162: ln2_nk = {32'hC2824FB8, 32'hB90CCFF0};   // n = -94
            8'd163: ln2_nk = {32'hC280ECD4, 32'hB90B5073};   // n = -93
            8'd164: ln2_nk = {32'hC27F13E0, 32'hB909D0F6};   // n = -92
            8'd165: ln2_nk = {32'hC27C4E18, 32'hB9085179};   // n = -91
            8'd166: ln2_nk = {32'hC2798850, 32'hB906D1FC};   // n = -90
            8'd167: ln2_nk = {32'hC276C288, 32'hB905527F};   // n = -89
            8'd168: ln2_nk = {32'hC273FCC0, 32'hB903D302};   // n = -88
            8'd169: ln2_nk = {32'hC27136F8, 32'hB9025385};   // n = -87
            8'd170: ln2_nk = {32'hC26E7130, 32'hB900D407};   // n = -86
            8'd171: ln2_nk = {32'hC26BAB68, 32'hB8FEA915};   // n = -85
            8'd172: ln2_nk = {32'hC268E5A0, 32'hB8FBAA1A};   // n = -84
            8'd173: ln2_nk = {32'hC2661FD8, 32'hB8F8AB20};   // n = -83
            8'd174: ln2_nk = {32'hC2635A10, 32'hB8F5AC26};   // n = -82
            8'd175: ln2_nk = {32'hC2609448, 32'hB8F2AD2C};   // n = -81
            8'd176: ln2_nk = {32'hC25DCE80, 32'hB8EFAE32};   // n = -80
            8'd177: ln2_nk = {32'hC25B08B8, 32'hB8ECAF37};   // n = -79
            8'd178: ln2_nk = {32'hC25842F0, 32'hB8E9B03D};   // n = -78
            8'd179: ln2_nk = {32'hC2557D28, 32'hB8E6B143};   // n = -77
            8'd180: ln2_nk = {32'hC252B760, 32'hB8E3B249};   // n = -76
            8'd181: ln2_nk = {32'hC24FF198, 32'hB8E0B34E};   // n = -75
            8'd182: ln2_nk = {32'hC24D2BD0, 32'hB8DDB454};   // n = -74
            8'd183: ln2_nk = {32'hC24A6608, 32'hB8DAB55A};   // n = -73
            8'd184: ln2_nk = {32'hC247A040, 32'hB8D7B660};   // n = -72
            8'd185: ln2_nk = {32'hC244DA78, 32'hB8D4B766};   // n = -71
            8'd186: ln2_nk = {32'hC24214B0, 32'hB8D1B86B};   // n = -70
            8'd187: ln2_nk = {32'hC23F4EE8, 32'hB8CEB971};   // n = -69
            8'd188: ln2_nk = {32'hC23C8920, 32'hB8CBBA77};   // n = -68
            8'd189: ln2_nk = {32'hC239C358, 32'hB8C8BB7D};   // n = -67
            8'd190: ln2_nk = {32'hC236FD90, 32'hB8C5BC82};   // n = -66
            8'd191: ln2_nk = {32'hC23437C8, 32'hB8C2BD88};   // n = -65
            8'd192: ln2_nk = {32'hC2317200, 32'hB8BFBE8E};   // n = -64
            8'd193: ln2_nk = {32'hC22EAC38, 32'hB8BCBF94};   // n = -63
            8'd194: ln2_nk = {32'hC22BE670, 32'hB8B9C09A};   // n = -62
            8'd195: ln2_nk = {32'hC22920A8, 32'hB8B6C19F};   // n = -61
            8'd196: ln2_nk = {32'hC2265AE0, 32'hB8B3C2A5};   // n = -60
            8'd197: ln2_nk = {32'hC2239518, 32'hB8B0C3AB};   // n = -59
            8'd198: ln2_nk = {32'hC220CF50, 32'hB8ADC4B1};   // n = -58
            8'd199: ln2_nk = {32'hC21E0988, 32'hB8AAC5B6};   // n = -57
            8'd200: ln2_nk = {32'hC21B43C0, 32'hB8A7C6BC};   // n = -56
            8'd201: ln2_nk = {32'hC2187DF8, 32'hB8A4C7C2};   // n = -55
            8'd202: ln2_nk = {32'hC215B830, 32'hB8A1C8C8};   // n = -54
            8'd203: ln2_nk = {32'hC212F268, 32'hB89EC9CE};   // n = -53
            8'd204: ln2_nk = {32'hC2102CA0, 32'hB89BCAD3};   // n = -52
            8'd205: ln2_nk = {32'hC20D66D8, 32'hB898CBD9};   // n = -51
            8'd206: ln2_nk = {32'hC20AA110, 32'hB895CCDF};   // n = -50
            8'd207: ln2_nk = {32'hC207DB48, 32'hB892CDE5};   // n = -49
            8'd208: ln2_nk = {32'hC2051580, 32'hB88FCEEA};   // n = -48
            8'd209: ln2_nk = {32'hC2024FB8, 32'hB88CCFF0};   // n = -47
            8'd210: ln2_nk = {32'hC1FF13E0, 32'hB889D0F6};   // n = -46
            8'd211: ln2_nk = {32'hC1F98850, 32'hB886D1FC};   // n = -45
            8'd212: ln2_nk = {32'hC1F3FCC0, 32'hB883D302};   // n = -44
            8'd213: ln2_nk = {32'hC1EE7130, 32'hB880D407};   // n = -43
            8'd214: ln2_nk = {32'hC1E8E5A0, 32'hB87BAA1A};   // n = -42
            8'd215: ln2_nk = {32'hC1E35A10, 32'hB875AC26};   // n = -41
            8'd216: ln2_nk = {32'hC1DDCE80, 32'hB86FAE32};   // n = -40
            8'd217: ln2_nk = {32'hC1D842F0, 32'hB869B03D};   // n = -39
            8'd218: ln2_nk = {32'hC1D2B760, 32'hB863B249};   // n = -38
            8'd219: ln2_nk = {32'hC1CD2BD0, 32'hB85DB454};   // n = -37
            8'd220: ln2_nk = {32'hC1C7A040, 32'hB857B660};   // n = -36
            8'd221: ln2_nk = {32'hC1C214B0, 32'hB851B86B};   // n = -35
            8'd222: ln2_nk = {32'hC1BC8920, 32'hB84BBA77};   // n = -34
            8'd223: ln2_nk = {32'hC1B6FD90, 32'hB845BC82};   // n = -33
            8'd224: ln2_nk = {32'hC1B17200, 32'hB83FBE8E};   // n = -32
            8'd225: ln2_nk = {32'hC1ABE670, 32'hB839C09A};   // n = -31
            8'd226: ln2_nk = {32'hC1A65AE0, 32'hB833C2A5};   // n = -30
            8'd227: ln2_nk = {32'hC1A0CF50, 32'hB82DC4B1};   // n = -29
            8'd228: ln2_nk = {32'hC19B43C0, 32'hB827C6BC};   // n = -28
            8'd229: ln2_nk = {32'hC195B830, 32'hB821C8C8};   // n = -27
            8'd230: ln2_nk = {32'hC1902CA0, 32'hB81BCAD3};   // n = -26
            8'd231: ln2_nk = {32'hC18AA110, 32'hB815CCDF};   // n = -25
            8'd232: ln2_nk = {32'hC1851580, 32'hB80FCEEA};   // n = -24
            8'd233: ln2_nk = {32'hC17F13E0, 32'hB809D0F6};   // n = -23
            8'd234: ln2_nk = {32'hC173FCC0, 32'hB803D302};   // n = -22
            8'd235: ln2_nk = {32'hC168E5A0, 32'hB7FBAA1A};   // n = -21
            8'd236: ln2_nk = {32'hC15DCE80, 32'hB7EFAE32};   // n = -20
            8'd237: ln2_nk = {32'hC152B760, 32'hB7E3B249};   // n = -19
            8'd238: ln2_nk = {32'hC147A040, 32'hB7D7B660};   // n = -18
            8'd239: ln2_nk = {32'hC13C8920, 32'hB7CBBA77};   // n = -17
            8'd240: ln2_nk = {32'hC1317200, 32'hB7BFBE8E};   // n = -16
            8'd241: ln2_nk = {32'hC1265AE0, 32'hB7B3C2A5};   // n = -15
            8'd242: ln2_nk = {32'hC11B43C0, 32'hB7A7C6BC};   // n = -14
            8'd243: ln2_nk = {32'hC1102CA0, 32'hB79BCAD3};   // n = -13
            8'd244: ln2_nk = {32'hC1051580, 32'hB78FCEEA};   // n = -12
            8'd245: ln2_nk = {32'hC0F3FCC0, 32'hB783D302};   // n = -11
            8'd246: ln2_nk = {32'hC0DDCE80, 32'hB76FAE32};   // n = -10
            8'd247: ln2_nk = {32'hC0C7A040, 32'hB757B660};   // n = -9
            8'd248: ln2_nk = {32'hC0B17200, 32'hB73FBE8E};   // n = -8
            8'd249: ln2_nk = {32'hC09B43C0, 32'hB727C6BC};   // n = -7
            8'd250: ln2_nk = {32'hC0851580, 32'hB70FCEEA};   // n = -6
            8'd251: ln2_nk = {32'hC05DCE80, 32'hB6EFAE32};   // n = -5
            8'd252: ln2_nk = {32'hC0317200, 32'hB6BFBE8E};   // n = -4
            8'd253: ln2_nk = {32'hC0051580, 32'hB68FCEEA};   // n = -3
            8'd254: ln2_nk = {32'hBFB17200, 32'hB63FBE8E};   // n = -2
            8'd255: ln2_nk = {32'hBF317200, 32'hB5BFBE8E};   // n = -1
            8'd0  : ln2_nk = {32'h00000000, 32'h00000000};   // n = 0
            8'd1  : ln2_nk = {32'h3F317200, 32'h35BFBE8E};   // n = 1
            8'd2  : ln2_nk = {32'h3FB17200, 32'h363FBE8E};   // n = 2
            8'd3  : ln2_nk = {32'h40051580, 32'h368FCEEA};   // n = 3
            8'd4  : ln2_nk = {32'h40317200, 32'h36BFBE8E};   // n = 4
            8'd5  : ln2_nk = {32'h405DCE80, 32'h36EFAE32};   // n = 5
            8'd6  : ln2_nk = {32'h40851580, 32'h370FCEEA};   // n = 6
            8'd7  : ln2_nk = {32'h409B43C0, 32'h3727C6BC};   // n = 7
            8'd8  : ln2_nk = {32'h40B17200, 32'h373FBE8E};   // n = 8
            8'd9  : ln2_nk = {32'h40C7A040, 32'h3757B660};   // n = 9
            8'd10 : ln2_nk = {32'h40DDCE80, 32'h376FAE32};   // n = 10
            8'd11 : ln2_nk = {32'h40F3FCC0, 32'h3783D302};   // n = 11
            8'd12 : ln2_nk = {32'h41051580, 32'h378FCEEA};   // n = 12
            8'd13 : ln2_nk = {32'h41102CA0, 32'h379BCAD3};   // n = 13
            8'd14 : ln2_nk = {32'h411B43C0, 32'h37A7C6BC};   // n = 14
            8'd15 : ln2_nk = {32'h41265AE0, 32'h37B3C2A5};   // n = 15
            8'd16 : ln2_nk = {32'h41317200, 32'h37BFBE8E};   // n = 16
            8'd17 : ln2_nk = {32'h413C8920, 32'h37CBBA77};   // n = 17
            8'd18 : ln2_nk = {32'h4147A040, 32'h37D7B660};   // n = 18
            8'd19 : ln2_nk = {32'h4152B760, 32'h37E3B249};   // n = 19
            8'd20 : ln2_nk = {32'h415DCE80, 32'h37EFAE32};   // n = 20
            8'd21 : ln2_nk = {32'h4168E5A0, 32'h37FBAA1A};   // n = 21
            8'd22 : ln2_nk = {32'h4173FCC0, 32'h3803D302};   // n = 22
            8'd23 : ln2_nk = {32'h417F13E0, 32'h3809D0F6};   // n = 23
            8'd24 : ln2_nk = {32'h41851580, 32'h380FCEEA};   // n = 24
            8'd25 : ln2_nk = {32'h418AA110, 32'h3815CCDF};   // n = 25
            8'd26 : ln2_nk = {32'h41902CA0, 32'h381BCAD3};   // n = 26
            8'd27 : ln2_nk = {32'h4195B830, 32'h3821C8C8};   // n = 27
            8'd28 : ln2_nk = {32'h419B43C0, 32'h3827C6BC};   // n = 28
            8'd29 : ln2_nk = {32'h41A0CF50, 32'h382DC4B1};   // n = 29
            8'd30 : ln2_nk = {32'h41A65AE0, 32'h3833C2A5};   // n = 30
            8'd31 : ln2_nk = {32'h41ABE670, 32'h3839C09A};   // n = 31
            8'd32 : ln2_nk = {32'h41B17200, 32'h383FBE8E};   // n = 32
            8'd33 : ln2_nk = {32'h41B6FD90, 32'h3845BC82};   // n = 33
            8'd34 : ln2_nk = {32'h41BC8920, 32'h384BBA77};   // n = 34
            8'd35 : ln2_nk = {32'h41C214B0, 32'h3851B86B};   // n = 35
            8'd36 : ln2_nk = {32'h41C7A040, 32'h3857B660};   // n = 36
            8'd37 : ln2_nk = {32'h41CD2BD0, 32'h385DB454};   // n = 37
            8'd38 : ln2_nk = {32'h41D2B760, 32'h3863B249};   // n = 38
            8'd39 : ln2_nk = {32'h41D842F0, 32'h3869B03D};   // n = 39
            8'd40 : ln2_nk = {32'h41DDCE80, 32'h386FAE32};   // n = 40
            8'd41 : ln2_nk = {32'h41E35A10, 32'h3875AC26};   // n = 41
            8'd42 : ln2_nk = {32'h41E8E5A0, 32'h387BAA1A};   // n = 42
            8'd43 : ln2_nk = {32'h41EE7130, 32'h3880D407};   // n = 43
            8'd44 : ln2_nk = {32'h41F3FCC0, 32'h3883D302};   // n = 44
            8'd45 : ln2_nk = {32'h41F98850, 32'h3886D1FC};   // n = 45
            8'd46 : ln2_nk = {32'h41FF13E0, 32'h3889D0F6};   // n = 46
            8'd47 : ln2_nk = {32'h42024FB8, 32'h388CCFF0};   // n = 47
            8'd48 : ln2_nk = {32'h42051580, 32'h388FCEEA};   // n = 48
            8'd49 : ln2_nk = {32'h4207DB48, 32'h3892CDE5};   // n = 49
            8'd50 : ln2_nk = {32'h420AA110, 32'h3895CCDF};   // n = 50
            8'd51 : ln2_nk = {32'h420D66D8, 32'h3898CBD9};   // n = 51
            8'd52 : ln2_nk = {32'h42102CA0, 32'h389BCAD3};   // n = 52
            8'd53 : ln2_nk = {32'h4212F268, 32'h389EC9CE};   // n = 53
            8'd54 : ln2_nk = {32'h4215B830, 32'h38A1C8C8};   // n = 54
            8'd55 : ln2_nk = {32'h42187DF8, 32'h38A4C7C2};   // n = 55
            8'd56 : ln2_nk = {32'h421B43C0, 32'h38A7C6BC};   // n = 56
            8'd57 : ln2_nk = {32'h421E0988, 32'h38AAC5B6};   // n = 57
            8'd58 : ln2_nk = {32'h4220CF50, 32'h38ADC4B1};   // n = 58
            8'd59 : ln2_nk = {32'h42239518, 32'h38B0C3AB};   // n = 59
            8'd60 : ln2_nk = {32'h42265AE0, 32'h38B3C2A5};   // n = 60
            8'd61 : ln2_nk = {32'h422920A8, 32'h38B6C19F};   // n = 61
            8'd62 : ln2_nk = {32'h422BE670, 32'h38B9C09A};   // n = 62
            8'd63 : ln2_nk = {32'h422EAC38, 32'h38BCBF94};   // n = 63
            8'd64 : ln2_nk = {32'h42317200, 32'h38BFBE8E};   // n = 64
            8'd65 : ln2_nk = {32'h423437C8, 32'h38C2BD88};   // n = 65
            8'd66 : ln2_nk = {32'h4236FD90, 32'h38C5BC82};   // n = 66
            8'd67 : ln2_nk = {32'h4239C358, 32'h38C8BB7D};   // n = 67
            8'd68 : ln2_nk = {32'h423C8920, 32'h38CBBA77};   // n = 68
            8'd69 : ln2_nk = {32'h423F4EE8, 32'h38CEB971};   // n = 69
            8'd70 : ln2_nk = {32'h424214B0, 32'h38D1B86B};   // n = 70
            8'd71 : ln2_nk = {32'h4244DA78, 32'h38D4B766};   // n = 71
            8'd72 : ln2_nk = {32'h4247A040, 32'h38D7B660};   // n = 72
            8'd73 : ln2_nk = {32'h424A6608, 32'h38DAB55A};   // n = 73
            8'd74 : ln2_nk = {32'h424D2BD0, 32'h38DDB454};   // n = 74
            8'd75 : ln2_nk = {32'h424FF198, 32'h38E0B34E};   // n = 75
            8'd76 : ln2_nk = {32'h4252B760, 32'h38E3B249};   // n = 76
            8'd77 : ln2_nk = {32'h42557D28, 32'h38E6B143};   // n = 77
            8'd78 : ln2_nk = {32'h425842F0, 32'h38E9B03D};   // n = 78
            8'd79 : ln2_nk = {32'h425B08B8, 32'h38ECAF37};   // n = 79
            8'd80 : ln2_nk = {32'h425DCE80, 32'h38EFAE32};   // n = 80
            8'd81 : ln2_nk = {32'h42609448, 32'h38F2AD2C};   // n = 81
            8'd82 : ln2_nk = {32'h42635A10, 32'h38F5AC26};   // n = 82
            8'd83 : ln2_nk = {32'h42661FD8, 32'h38F8AB20};   // n = 83
            8'd84 : ln2_nk = {32'h4268E5A0, 32'h38FBAA1A};   // n = 84
            8'd85 : ln2_nk = {32'h426BAB68, 32'h38FEA915};   // n = 85
            8'd86 : ln2_nk = {32'h426E7130, 32'h3900D407};   // n = 86
            8'd87 : ln2_nk = {32'h427136F8, 32'h39025385};   // n = 87
            8'd88 : ln2_nk = {32'h4273FCC0, 32'h3903D302};   // n = 88
            8'd89 : ln2_nk = {32'h4276C288, 32'h3905527F};   // n = 89
            8'd90 : ln2_nk = {32'h42798850, 32'h3906D1FC};   // n = 90
            8'd91 : ln2_nk = {32'h427C4E18, 32'h39085179};   // n = 91
            8'd92 : ln2_nk = {32'h427F13E0, 32'h3909D0F6};   // n = 92
            8'd93 : ln2_nk = {32'h4280ECD4, 32'h390B5073};   // n = 93
            8'd94 : ln2_nk = {32'h42824FB8, 32'h390CCFF0};   // n = 94
            8'd95 : ln2_nk = {32'h4283B29C, 32'h390E4F6D};   // n = 95
            8'd96 : ln2_nk = {32'h42851580, 32'h390FCEEA};   // n = 96
            8'd97 : ln2_nk = {32'h42867864, 32'h39114E68};   // n = 97
            8'd98 : ln2_nk = {32'h4287DB48, 32'h3912CDE5};   // n = 98
            8'd99 : ln2_nk = {32'h42893E2C, 32'h39144D62};   // n = 99
            8'd100: ln2_nk = {32'h428AA110, 32'h3915CCDF};   // n = 100
            8'd101: ln2_nk = {32'h428C03F4, 32'h39174C5C};   // n = 101
            8'd102: ln2_nk = {32'h428D66D8, 32'h3918CBD9};   // n = 102
            8'd103: ln2_nk = {32'h428EC9BC, 32'h391A4B56};   // n = 103
            8'd104: ln2_nk = {32'h42902CA0, 32'h391BCAD3};   // n = 104
            8'd105: ln2_nk = {32'h42918F84, 32'h391D4A50};   // n = 105
            8'd106: ln2_nk = {32'h4292F268, 32'h391EC9CE};   // n = 106
            8'd107: ln2_nk = {32'h4294554C, 32'h3920494B};   // n = 107
            8'd108: ln2_nk = {32'h4295B830, 32'h3921C8C8};   // n = 108
            8'd109: ln2_nk = {32'h42971B14, 32'h39234845};   // n = 109
            8'd110: ln2_nk = {32'h42987DF8, 32'h3924C7C2};   // n = 110
            8'd111: ln2_nk = {32'h4299E0DC, 32'h3926473F};   // n = 111
            8'd112: ln2_nk = {32'h429B43C0, 32'h3927C6BC};   // n = 112
            8'd113: ln2_nk = {32'h429CA6A4, 32'h39294639};   // n = 113
            8'd114: ln2_nk = {32'h429E0988, 32'h392AC5B6};   // n = 114
            8'd115: ln2_nk = {32'h429F6C6C, 32'h392C4534};   // n = 115
            8'd116: ln2_nk = {32'h42A0CF50, 32'h392DC4B1};   // n = 116
            8'd117: ln2_nk = {32'h42A23234, 32'h392F442E};   // n = 117
            8'd118: ln2_nk = {32'h42A39518, 32'h3930C3AB};   // n = 118
            8'd119: ln2_nk = {32'h42A4F7FC, 32'h39324328};   // n = 119
            8'd120: ln2_nk = {32'h42A65AE0, 32'h3933C2A5};   // n = 120
            8'd121: ln2_nk = {32'h42A7BDC4, 32'h39354222};   // n = 121
            8'd122: ln2_nk = {32'h42A920A8, 32'h3936C19F};   // n = 122
            8'd123: ln2_nk = {32'h42AA838C, 32'h3938411C};   // n = 123
            8'd124: ln2_nk = {32'h42ABE670, 32'h3939C09A};   // n = 124
            8'd125: ln2_nk = {32'h42AD4954, 32'h393B4017};   // n = 125
            8'd126: ln2_nk = {32'h42AEAC38, 32'h393CBF94};   // n = 126
            8'd127: ln2_nk = {32'h42B00F1C, 32'h393E3F11};   // n = 127
            default: ln2_nk = 64'd0;
        endcase
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t;
    wire [2:0] f;
    ot_hdc_qmul_lat__d4g_sfu #(LM) m_t (clk, rst_n, vd[1], xc, K_LOG2E, t, f[0]);   // 1 + LM

    // n = rint-to-even(t), |t| < 127.  With E = field - 127, the integer part
    // is the significand shifted right by 23 - E (E in [-1, 6]); below E = -1,
    // |t| < 1/2 and n = 0.
    wire [23:0] tm = {1'b1, t[22:0]};
    wire [7:0]  te = t[30:23];
    wire [4:0]  tsh = 5'd23 - (te[4:0] - 5'd31);      // 23 - E, as te - 127 = te[4:0] - 31 (mod 32)
    wire [23:0] tip = tm >> tsh;
    wire [4:0]  trb = tsh - 5'd1;
    wire        thalf = tm[trb];
    wire        tstk = |(tm & ~({24{1'b1}} << trb));
    // stage 1: the shifted integer part and the rounding decision
    reg  [7:0]  s_tip;
    reg         s_inc, s_small, s_neg;
    always @(posedge clk) begin
        s_tip <= tip[7:0]; s_inc <= thalf && (tstk || tip[0]); s_small <= (te < 8'd126); s_neg <= t[31];
    end
    // stage 2: round and sign
    wire [7:0]  tmag = s_small ? 8'd0 : (s_tip + {7'd0, s_inc});
    reg  [8:0]  nint;
    always @(posedge clk) nint <= s_neg ? -{1'b0, tmag} : {1'b0, tmag};

    reg [31:0] a_hi, a_lo;
    always @(posedge clk) {a_hi, a_lo} <= ln2_nk(nint[7:0]);

    wire [31:0] r1, r, xc_d, lo_d;
    ot_hdc_delay__d4g_sfu #(.W(32), .D(T_K - 1)) d_x (clk, rst_n, xc, xc_d);
    ot_dsrom_add_f12_l6__d4g_sfu a_r1 (clk, rst_n, vd[T_K], xc_d, {~a_hi[31], a_hi[30:0]}, r1, f[1]);
    ot_hdc_delay__d4g_sfu #(.W(32), .D(LR)) d_lo (clk, rst_n, a_lo, lo_d);
    ot_dsrom_add_f12_l6__d4g_sfu a_r  (clk, rst_n, vd[T_R1], r1, {~lo_d[31], lo_d[30:0]}, r, f[2]);

    // Horner: p = C0; six times p = p*r + C[k]; r travels in (LM+LA)-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay__d4g_sfu #(.W(32), .D(LM + LP)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_qmul_lat__d4g_sfu #(LM) u_m (clk, rst_n, vd[T_R + (LM + LP)*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat__d4g_sfu #(.KEEP(ASUM != 0 ? 2 : ((LM != 3 || LA != 3) ? 1 : 0)), .LAT(LP)) u_a (clk, rst_n, vd[T_R + (LM + LP)*(k-1) + LM], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [8:0] nint_d;
    ot_hdc_delay__d4g_sfu #(.W(9), .D(T_P - T_N)) d_n (clk, rst_n, nint, nint_d);
    // 2^n into the exponent field (a keep-prefix add in the serial-domain build, LM != 3)
    wire [31:0] y_n;
    wire        unused_cy;
    ot_hdc_kadd__d4g_sfu #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_yn (.a(pa[6]), .b({{14{nint_d[8]}}, nint_d, 23'd0}), .cin(1'b0),
                                                      .s(y_n), .cout(unused_cy));
    always @(posedge clk) y <= y_n;

    assign fault = |{f, hf};
endmodule


module ot_dsrom_fdiv_f12__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer QB = 27;
    localparam integer NS = (QB + 1) / 2;      // 14
    localparam integer DEPTH = 3 + NS + 4;     // 21 (1.2 GHz: normalise in two stages, encode in two)

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    // stage C1: the operands' leading-one positions (a subnormal's), decode flags
    function automatic [4:0] lz;      // position of the leading one of f (0 when f = 0)
        input [22:0] f;
        integer i;
        begin
            lz = 5'd0;
            for (i = 0; i < 23; i = i + 1) if (f[i]) lz = i[4:0];
        end
    endfunction
    reg        c_sign, c_zero, c_bad;
    reg [31:0] c_a, c_b;
    reg [4:0]  c_pa, c_pb;
    always @(posedge clk) begin
        c_sign <= a[31] ^ b[31];
        c_zero <= (a[30:0] == 31'd0);
        c_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        c_a <= a; c_b <= b;
        c_pa <= lz(a[22:0]); c_pb <= lz(b[22:0]);
    end
    // stage C2: normalise (= the function norm of ot_hdc_v41x_fdiv__d4g_sfu, with p precomputed)
    function automatic [33:0] normp;
        input [7:0]  e;
        input [22:0] f;
        input [4:0]  p;
        begin
            if (e != 8'd0) normp = {1'b1, f, e - 10'sd127};
            else normp = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
        end
    endfunction
    wire [33:0] na = normp(c_a[30:23], c_a[22:0], c_pa);
    wire [33:0] nb = normp(c_b[30:23], c_b[22:0], c_pb);

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= c_sign;
        d_zero <= c_zero;
        d_bad  <= c_bad;
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // 3 mb, once (keep-prefix add)
    wire [25:0] mb3_n;
    wire        mb3_c;
    ot_hdc_kadd__d4g_sfu #(.W(26), .K(1)) u_mb3 (.a({2'b0, d_mb}), .b({1'b0, d_mb, 1'b0}), .cin(1'b0), .s(mb3_n), .cout(mb3_c));
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= d_sign; e_zero <= d_zero; e_bad <= d_bad; e_e <= d_e;
        e_ma <= d_ma; e_mb <= d_mb; e_mb3 <= mb3_n;
    end

    reg [24:0]        r_rem  [0:NS-1];
    reg [QB-1:0]      r_q    [0:NS-1];
    reg [23:0]        r_mb   [0:NS-1];
    reg [25:0]        r_mb3  [0:NS-1];
    reg               r_sign [0:NS-1];
    reg               r_zero [0:NS-1];
    reg               r_bad  [0:NS-1];
    reg signed [10:0] r_e    [0:NS-1];

    genvar j;
    generate
        for (j = 0; j < NS; j = j + 1) begin : g_rec
            // quotient bits 2j and 2j+1 (bit 2^-k is restoring step k); stage NS-1 forms one bit
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            // the three trial subtractions as keep-prefix adders (x + ~m + 1), so ABC keeps them log-depth
            wire [27:0]   d1, d2, d3;
            wire          c1u, c2u, c3u;
            ot_hdc_kadd__d4g_sfu #(.W(28), .K(1)) u_d1 (.a({1'b0, x}), .b(~{4'b0, mb}), .cin(1'b1), .s(d1), .cout(c1u));
            ot_hdc_kadd__d4g_sfu #(.W(28), .K(1)) u_d2 (.a({1'b0, x}), .b(~{3'b0, mb, 1'b0}), .cin(1'b1), .s(d2), .cout(c2u));
            ot_hdc_kadd__d4g_sfu #(.W(28), .K(1)) u_d3 (.a({1'b0, x}), .b(~{2'b0, mb3}), .cin(1'b1), .s(d3), .cout(c3u));
            wire [1:0]    q  = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
            wire [26:0]   r  = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
            always @(posedge clk) begin
                r_rem[j]  <= r[24:0];
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[NS-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_zero <= r_zero[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = (25'd1 << sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3a: round to nearest even (keep-prefix increment) --------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    wire [30:0] code_n;
    ot_hdc_kinc__d4g_sfu #(.W(31), .K(1)) u_rnd (.a({f2_field, f2_sig[22:0]}), .inc(rup), .y(code_n));
    reg  [30:0] f3_code;
    reg         f3_sign, f3_zero, f3_bad, f3_ovf;
    always @(posedge clk) begin
        f3_code <= code_n; f3_sign <= f2_sign; f3_zero <= f2_zero; f3_bad <= f2_bad; f3_ovf <= f2_ovf;
    end
    // ---- finish 3b: encode ---------------------------------------------------------------
    wire        ovf = f3_ovf || (f3_code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f3_bad || (ovf && !f3_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f3_zero || f3_code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f3_sign, f3_code}; fault <= 1'b0; end
    end
endmodule


// ot_dsrom_add_f12_l6__d4g_sfu: the f12 binary32 adder (rtl/hdc/ot_hdc_fp32_f12.sv ot_hdc_fp32_add_f12) with six cuts: the
// LAT-5 _l5x cut set plus a cut between the magnitude compare and the alignment (CUTS bit 0).  Same function, one
// more register; ot_hdc_qadd_lat__d4g_sfu's port order and fault convention.
module ot_dsrom_add_f12_l6__d4g_sfu (input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
                            output wire [31:0] y, output wire fault);
    wire [1:0] err;
    wire vo;
    ot_hdc_fp32_add_f12_l6x u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

// ---------------------------------------------------------------------------
// ot_dsrom_actquant_f12__d4g_sfu: rtl/hdc/v41/ot_hdc_actquant.sv (FP8 E4M3 / FP4 E2M1 + E8M0 activation quantiser, one
// 32-element block a cycle) for the 1.2 GHz domain, same function bit for bit (the original is unchanged):
//   * the max tree one compare level a stage (keep-prefix compares), the floor with the last level;
//   * the scale product amax * (1/448 | 1/6) on ot_hdc_qmul_lat__d4g_sfu #(5) (the f12 multiplier: binary32 RNE with
//     gradual underflow, as ot_hdc_fmul; amax is finite and positive, the product cannot overflow);
//   * the per-element grid exponent, the rounding and the encode each over two stages.
// Stages: S0 input | M1..M5 32->16->8->4->2->1 (+ floor) | 5 multiply | E e | G1 Ev | G2 grid, shift | R1 shift,
// guard, sticky | R2 count, exponent base | C1 codes, partial exponents | C2 BF16 value.  LATENCY = 13 + MLAT
// (18 or 19; the original: 13).
// ---------------------------------------------------------------------------
module ot_dsrom_actquant_f12__d4g_sfu #(
    parameter integer MLAT = 5,     // scale multiply latency: 5 (ot_hdc_fp32_mul_f12_l5) or 6 (_l6, operand select in front)
    parameter integer XSRAM = 0     // el1011-s81su (opt-in): the elements' S0 -> E wait line in SRAM (ot_sram_dline,
                                    // 2 x 64x512 macros + capture flops) instead of 1,024 x (6 + MLAT) flops; same values
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          fp4,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault
);
    localparam integer LATENCY = 13 + MLAT;
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [30:0] FLOOR_FP4 = 31'h01c00000;   // float32(6 * 2^-126)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    localparam [31:0] INV_6     = 32'h3e2aaaab;   // float32(1/6)
    integer i;
    genvar k, lv;

    // ---- S0: input register
    reg          s0_v, s0_fp4;
    reg [1023:0] s0_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s0_v <= 1'b0; else s0_v <= v;
    end
    always @(posedge clk) begin s0_x <= x; s0_fp4 <= fp4; end
    reg nf0;
    always @(*) begin
        nf0 = 1'b0;
        for (i = 0; i < 32; i = i + 1) nf0 = nf0 | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end

    // ---- M1..M5: the max tree, one level a stage (31-bit magnitudes)
    wire [31*32-1:0] lvl [0:5];
    wire [5:0] lv_v, lv_fp4, lv_nf;
    generate
        for (k = 0; k < 32; k = k + 1) begin : g_m0
            assign lvl[0][31*k +: 31] = s0_x[32*k +: 31];
        end
        assign lv_v[0] = s0_v; assign lv_fp4[0] = s0_fp4; assign lv_nf[0] = nf0;
        for (lv = 1; lv <= 5; lv = lv + 1) begin : g_lv
            localparam integer NO = 32 >> lv;
            reg [31*NO-1:0] r;
            reg rv, rf, rn;
            for (k = 0; k < NO; k = k + 1) begin : g_n
                wire [30:0] a0 = lvl[lv-1][31*(2*k) +: 31], a1 = lvl[lv-1][31*(2*k+1) +: 31];
                wire ge;
                ot_hdc_kge__d4g_sfu #(.W(31), .K(1)) u_ge (.a(a0), .b(a1), .ge(ge));
                wire [30:0] m = ge ? a0 : a1;
                if (lv == 5) begin : g_fl            // the floor with the last level
                    wire [30:0] fl = lv_fp4[lv-1] ? FLOOR_FP4 : FLOOR_FP8;
                    wire gf;
                    ot_hdc_kge__d4g_sfu #(.W(31), .K(1)) u_gf (.a(m), .b(fl), .ge(gf));
                    always @(posedge clk) r[31*k +: 31] <= gf ? m : fl;
                end else begin : g_nf
                    always @(posedge clk) r[31*k +: 31] <= m;
                end
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) rv <= 1'b0; else rv <= lv_v[lv-1];
            end
            always @(posedge clk) begin rf <= lv_fp4[lv-1]; rn <= lv_nf[lv-1]; end
            assign lvl[lv][31*NO-1:0] = r;
            if (NO < 32) begin : g_pad
                assign lvl[lv][31*32-1:31*NO] = 0;
            end
            assign lv_v[lv] = rv; assign lv_fp4[lv] = rf; assign lv_nf[lv] = rn;
        end
    endgenerate
    wire [30:0] amax = lvl[5][30:0];

    // ---- the scale product (5 stages)
    wire [31:0] prod;
    wire        pfault;
    ot_hdc_qmul_lat__d4g_sfu #(MLAT) u_scale (clk, rst_n, lv_v[5], {1'b0, amax}, lv_fp4[5] ? INV_6 : INV_448, prod, pfault);
    wire [MLAT:0] vl;
    ot_hdc_vline__d4g_sfu #(.D(MLAT)) u_vl (.clk(clk), .rst_n(rst_n), .v(lv_v[5]), .vd(vl));
    wire p_fp4, p_nf;
    ot_hdc_delay__d4g_sfu #(.W(2), .D(MLAT)) u_dp (.clk(clk), .rst_n(rst_n), .d({lv_fp4[5], lv_nf[5]}), .q({p_fp4, p_nf}));
    // the elements, S0 -> E (5 tree + MLAT multiply registers, then E itself: aligned at E's input)
    wire [1023:0] xe;
    generate if (XSRAM != 0) begin : g_xs
        ot_sram_dline #(.W(1024), .D(6 + MLAT)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(xe));
    end else begin : g_xf
        ot_hdc_delay__d4g_sfu #(.W(1024), .D(6 + MLAT)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(xe));
    end endgenerate

    // ---- E: e = ceil_log2(prod)
    reg              e_v, e_fp4, e_nf;
    reg signed [9:0] e_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0; else e_v <= vl[MLAT];
    end
    always @(posedge clk) begin
        e_fp4 <= p_fp4; e_nf <= p_nf | pfault;
        e_e <= $signed({2'b00, prod[30:23]}) - 10'sd127 + {9'd0, (prod[22:0] != 23'd0)};
    end

    // ---- G1: Ev = exponent(x) - e, significand, sign
    reg               g1_v, g1_fp4, g1_nf;
    reg signed [9:0]  g1_e;
    reg signed [10:0] g1_ev [0:31];
    reg [23:0]        g1_sig [0:31];
    reg [31:0]        g1_sgn;
    reg [7:0]         fld;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g1_v <= 1'b0; else g1_v <= e_v;
    end
    always @(posedge clk) begin
        g1_fp4 <= e_fp4; g1_nf <= e_nf; g1_e <= e_e;
        for (i = 0; i < 32; i = i + 1) begin
            fld = xe[32*i + 23 +: 8];
            g1_ev[i] <= ((fld == 8'd0) ? -11'sd126 : ($signed({3'b000, fld}) - 11'sd127)) - e_e;
            g1_sig[i] <= {(fld != 8'd0), xe[32*i +: 23]};
            g1_sgn[i] <= xe[32*i + 31] && (xe[32*i +: 31] != 31'd0);
        end
    end

    // ---- G2: grid exponent and shift amount
    reg              g2_v, g2_fp4, g2_nf;
    reg signed [9:0] g2_e;
    reg [23:0]       g2_sig [0:31];
    reg [4:0]        g2_rs [0:31];
    reg signed [4:0] g2_g [0:31];
    reg [31:0]       g2_sgn;
    reg signed [10:0] dd, mine;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g2_v <= 1'b0; else g2_v <= g1_v;
    end
    always @(posedge clk) begin
        g2_fp4 <= g1_fp4; g2_nf <= g1_nf; g2_e <= g1_e; g2_sgn <= g1_sgn;
        mine = g1_fp4 ? 11'sd0 : -11'sd6;
        for (i = 0; i < 32; i = i + 1) begin
            dd = mine - g1_ev[i];
            g2_sig[i] <= g1_sig[i];
            if (dd > 11'sd0) begin
                g2_g[i] <= mine[4:0];
                g2_rs[i] <= (dd > (g1_fp4 ? 11'sd4 : 11'sd6)) ? 5'd26 : ((g1_fp4 ? 5'd22 : 5'd20) + dd[4:0]);
            end else begin
                g2_g[i] <= g1_ev[i][4:0];
                g2_rs[i] <= g1_fp4 ? 5'd22 : 5'd20;
            end
        end
    end

    // ---- R1: shift to the grid: the count's low bits, guard, sticky
    reg              r1_v, r1_fp4, r1_nf;
    reg signed [9:0] r1_e;
    reg [4:0]        r1_t [0:31];
    reg [31:0]       r1_gd, r1_st, r1_sgn;
    reg signed [4:0] r1_g [0:31];
    reg [50:0]       wide;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r1_v <= 1'b0; else r1_v <= g2_v;
    end
    always @(posedge clk) begin
        r1_fp4 <= g2_fp4; r1_nf <= g2_nf; r1_e <= g2_e; r1_sgn <= g2_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            wide = {g2_sig[i], 27'd0} >> g2_rs[i];
            r1_t[i] <= wide[31:27];
            r1_gd[i] <= wide[26];
            r1_st[i] <= (wide[25:0] != 26'd0);
            r1_g[i] <= g2_g[i];
        end
    end

    // ---- R2: round to nearest even
    reg              r2_v, r2_fp4, r2_nf;
    reg signed [9:0] r2_e;
    reg [4:0]        r2_c [0:31];
    reg signed [4:0] r2_g [0:31];
    reg [31:0]       r2_sgn;
    reg signed [11:0] r2_base [0:31];     // g - mant_bits + e (the BF16 exponent's base)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r2_v <= 1'b0; else r2_v <= r1_v;
    end
    always @(posedge clk) begin
        r2_fp4 <= r1_fp4; r2_nf <= r1_nf; r2_e <= r1_e; r2_sgn <= r1_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            r2_c[i] <= r1_t[i] + {4'd0, r1_gd[i] & (r1_st[i] | r1_t[i][0])};
            r2_g[i] <= r1_g[i];
            r2_base[i] <= r1_g[i] - (r1_fp4 ? 12'sd1 : 12'sd3) + r1_e;
        end
    end

    // ---- C1: codes; the BF16 value's pieces (leading position, normalised count, subnormal value, exponent base)
    reg              c1_v, c1_fp4, c1_nf;
    reg signed [9:0] c1_e;
    reg [255:0]      c1_q;
    reg [2:0]        c1_p [0:31];
    reg [7:0]        c1_cn [0:31];
    reg [6:0]        c1_sub [0:31];
    reg signed [11:0] c1_bb [0:31];
    reg [31:0]       c1_z, c1_sgn;
    reg [2:0]        p;
    reg [4:0]        c;
    reg [3:0]        g4;
    reg signed [11:0] shs;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) c1_v <= 1'b0; else c1_v <= r2_v;
    end
    always @(posedge clk) begin
        c1_fp4 <= r2_fp4; c1_nf <= r2_nf; c1_e <= r2_e; c1_sgn <= r2_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            c = r2_c[i];
            g4 = r2_g[i][3:0];
            if (!r2_fp4) begin
                if (c[4])      c1_q[8*i +: 8] <= {r2_sgn[i], g4 + 4'd8, 3'd0};
                else if (c[3]) c1_q[8*i +: 8] <= {r2_sgn[i], g4 + 4'd7, c[2:0]};
                else           c1_q[8*i +: 8] <= {r2_sgn[i], 4'd0, c[2:0]};
            end else begin
                if (c[2])      c1_q[8*i +: 8] <= {4'd0, r2_sgn[i], g4[1:0] + 2'd2, 1'b0};
                else if (c[1]) c1_q[8*i +: 8] <= {4'd0, r2_sgn[i], g4[1:0] + 2'd1, c[0]};
                else           c1_q[8*i +: 8] <= {4'd0, r2_sgn[i], 2'd0, c[0]};
            end
            p = c[4] ? 3'd4 : c[3] ? 3'd3 : c[2] ? 3'd2 : c[1] ? 3'd1 : 3'd0;
            c1_p[i] <= p;
            c1_cn[i] <= {3'd0, c} << (3'd7 - p);
            c1_bb[i] <= r2_base[i] + 12'sd127;
            shs = r2_base[i] + 12'sd133;
            c1_sub[i] <= (shs < 12'sd0) ? 7'd0 : ({2'd0, c} << shs[3:0]);
            c1_z[i] <= (c == 5'd0);
        end
    end

    // ---- C2: the dequantised value c * 2^(g - mant_bits + e) as BF16
    reg signed [11:0] be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= c1_v; fault <= c1_v && c1_nf; end
    end
    always @(posedge clk) begin
        e <= c1_e;
        q <= c1_q;
        for (i = 0; i < 32; i = i + 1) begin
            be = c1_bb[i] + $signed({9'd0, c1_p[i]});
            if (c1_z[i])             y[16*i +: 16] <= {c1_sgn[i], 15'd0};
            else if (be >= 12'sd255) y[16*i +: 16] <= {c1_sgn[i], 8'hFF, 7'd0};
            else if (be >= 12'sd1)   y[16*i +: 16] <= {c1_sgn[i], be[7:0], c1_cn[i][6:0]};
            else                     y[16*i +: 16] <= {c1_sgn[i], 8'd0, c1_sub[i]};
        end
    end
endmodule

// Scoped source: rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv
`timescale 1ns/1ps
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_sfu.sv for the c12
// build, derived from the f12 file (rtl/hbm_accel/su/pinned_native/ot_hdc_v41x_sfu_f12.sv, unchanged).  Only
// ot_hdc_v41x_softplus__d4g_sfu changes, and only through two new parameters whose defaults are the f12 unit:
//   DDIV = 21  its divider u / (t + 2) is the DS ROM kit's ot_dsrom_fdiv_f12__d4g_sfu (rtl/hdc/v41x/ot_dsrom_su_f12.sv; the
//              f12 divider's normalise stage missed 0.833 ns by 29 ps in the routed SFU lane): DEPTH + 2
//   FSQ = 1    its square root is ot_hdc_fsqrt_c12__d4g_sfu (rtl/hdc/v41/ot_hdc_fsqrt_c12__d4g_sfu.sv: keep-prefix digit recurrence,
//              precomputed finish; same DEPTH 31; the routed softplus missed by 113 ps in ot_hdc_fsqrt__d4g_sfu's finish)
// DEPTH = exp + 11 LM + 10 LA + 31 + DDIV.  Bit-identical (the SU campaigns' SFU equivalence).
// hbm-fmax-su (2026-10-04): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_sfu.sv for the 1.2 GHz build: the original
// except ot_hdc_v41x_fdiv__d4g_sfu's timing-only rewrites (marked hbm-fmax-su; bit- and cycle-identical).  A source list names
// this file OR the original; the original (pinned by committed records) is unchanged.  Needs rtl/hdc/ot_hdc_prefix.sv.
// ---------------------------------------------------------------------------
// Special-function pipes of the V4.1 vector stream unit (ot_hdc_v41x_vec), at
// the fast-FP depths and with NO padding:
//
//   ot_hdc_v41x_exp__d4g_sfu       exp(x), DEPTH 49     } verbatim copies of ot_hdc_exp__d4g_sfu and
//   ot_hdc_v41x_rsqrt__d4g_sfu     1/sqrt(x), DEPTH 37  } ot_hdc_rsqrt__d4g_sfu in rtl/hdc/ot_hdc_sfu.sv
//                                                on branch worktree-agent-a516a664e7d53536c
//                                                (acc46e61), renamed only.  The
//                                                main-line file keeps the five-stage
//                                                pipes under the old names.  Their
//                                                algorithms are tools/hdc_golden.py
//                                                exp and rsqrt, checked there on all
//                                                2^32 inputs.
//   ot_hdc_v41x_fdiv__d4g_sfu      IEEE binary32 division, DEPTH 19 (rtl/hdc/v41/ot_hdc_fdiv__d4g_sfu's
//                         digit recurrence, two quotient bits per stage, radix-4 select)
//   ot_hdc_v41x_softplus__d4g_sfu  softplus and sqrt(softplus), DEPTH 162
//   ot_hdc_v41x_ins__d4g_sfu       an insertion delay line: variable depth, in order
//
// They are built from the fast binary32 add and multiply (rtl/hdc/ot_hdc_fastfp.sv:
// LATENCY 3, II 1), which are bit-identical to the qualified five-stage pipes.
// ---------------------------------------------------------------------------

// exp(x): clamp to [-87, 88]; t = x*log2e; n = rint(t); two-constant Cody-Waite
// reduction; degree-6 Horner; 2^n added to the exponent.
//
// The golden forms n by the 1.5*2^23 trick: u = t + 1.5*2^23 is the exact sum
// rounded to an integer, ties to even (|t| < 2^22 puts u in [2^23, 2^24), where
// the ulp is 1, and 1.5*2^23 is even), and n = u - 1.5*2^23 is exact.  That is
// rint-to-even of t, so here it is one integer step on t's encoding.  n*ln2_hi
// (exact) and RN(n*ln2_lo) depend on n alone, n in [-126, 127] after the clamp:
// a 254-entry table holding the golden's own products.
module ot_hdc_v41x_exp__d4g_sfu #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_sfu)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat__d4g_sfu: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer T_N = 1 + LM + 1;        // n registered
    localparam integer T_K = T_N + 1;           // table products registered
    localparam integer T_R1 = T_K + LA;
    localparam integer T_R = T_R1 + LA;
    localparam integer T_P = T_R + 6 * (LM + LA);
    localparam integer DEPTH = T_P + 1;         // 7 LM + 8 LA + 4: 49 (LM 3), 56 (LM 4)
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction
    //: {n*LN2_HI, RN(n*LN2_LO)}: the golden's binary32 products (hdc_golden.mul,
    //: canonical +0 at n = 0), indexed by n's low 8 bits.
    function automatic [63:0] ln2_nk(input [7:0] nk);
        case (nk)
            8'd130: ln2_nk = {32'hC2AEAC38, 32'hB93CBF94};   // n = -126
            8'd131: ln2_nk = {32'hC2AD4954, 32'hB93B4017};   // n = -125
            8'd132: ln2_nk = {32'hC2ABE670, 32'hB939C09A};   // n = -124
            8'd133: ln2_nk = {32'hC2AA838C, 32'hB938411C};   // n = -123
            8'd134: ln2_nk = {32'hC2A920A8, 32'hB936C19F};   // n = -122
            8'd135: ln2_nk = {32'hC2A7BDC4, 32'hB9354222};   // n = -121
            8'd136: ln2_nk = {32'hC2A65AE0, 32'hB933C2A5};   // n = -120
            8'd137: ln2_nk = {32'hC2A4F7FC, 32'hB9324328};   // n = -119
            8'd138: ln2_nk = {32'hC2A39518, 32'hB930C3AB};   // n = -118
            8'd139: ln2_nk = {32'hC2A23234, 32'hB92F442E};   // n = -117
            8'd140: ln2_nk = {32'hC2A0CF50, 32'hB92DC4B1};   // n = -116
            8'd141: ln2_nk = {32'hC29F6C6C, 32'hB92C4534};   // n = -115
            8'd142: ln2_nk = {32'hC29E0988, 32'hB92AC5B6};   // n = -114
            8'd143: ln2_nk = {32'hC29CA6A4, 32'hB9294639};   // n = -113
            8'd144: ln2_nk = {32'hC29B43C0, 32'hB927C6BC};   // n = -112
            8'd145: ln2_nk = {32'hC299E0DC, 32'hB926473F};   // n = -111
            8'd146: ln2_nk = {32'hC2987DF8, 32'hB924C7C2};   // n = -110
            8'd147: ln2_nk = {32'hC2971B14, 32'hB9234845};   // n = -109
            8'd148: ln2_nk = {32'hC295B830, 32'hB921C8C8};   // n = -108
            8'd149: ln2_nk = {32'hC294554C, 32'hB920494B};   // n = -107
            8'd150: ln2_nk = {32'hC292F268, 32'hB91EC9CE};   // n = -106
            8'd151: ln2_nk = {32'hC2918F84, 32'hB91D4A50};   // n = -105
            8'd152: ln2_nk = {32'hC2902CA0, 32'hB91BCAD3};   // n = -104
            8'd153: ln2_nk = {32'hC28EC9BC, 32'hB91A4B56};   // n = -103
            8'd154: ln2_nk = {32'hC28D66D8, 32'hB918CBD9};   // n = -102
            8'd155: ln2_nk = {32'hC28C03F4, 32'hB9174C5C};   // n = -101
            8'd156: ln2_nk = {32'hC28AA110, 32'hB915CCDF};   // n = -100
            8'd157: ln2_nk = {32'hC2893E2C, 32'hB9144D62};   // n = -99
            8'd158: ln2_nk = {32'hC287DB48, 32'hB912CDE5};   // n = -98
            8'd159: ln2_nk = {32'hC2867864, 32'hB9114E68};   // n = -97
            8'd160: ln2_nk = {32'hC2851580, 32'hB90FCEEA};   // n = -96
            8'd161: ln2_nk = {32'hC283B29C, 32'hB90E4F6D};   // n = -95
            8'd162: ln2_nk = {32'hC2824FB8, 32'hB90CCFF0};   // n = -94
            8'd163: ln2_nk = {32'hC280ECD4, 32'hB90B5073};   // n = -93
            8'd164: ln2_nk = {32'hC27F13E0, 32'hB909D0F6};   // n = -92
            8'd165: ln2_nk = {32'hC27C4E18, 32'hB9085179};   // n = -91
            8'd166: ln2_nk = {32'hC2798850, 32'hB906D1FC};   // n = -90
            8'd167: ln2_nk = {32'hC276C288, 32'hB905527F};   // n = -89
            8'd168: ln2_nk = {32'hC273FCC0, 32'hB903D302};   // n = -88
            8'd169: ln2_nk = {32'hC27136F8, 32'hB9025385};   // n = -87
            8'd170: ln2_nk = {32'hC26E7130, 32'hB900D407};   // n = -86
            8'd171: ln2_nk = {32'hC26BAB68, 32'hB8FEA915};   // n = -85
            8'd172: ln2_nk = {32'hC268E5A0, 32'hB8FBAA1A};   // n = -84
            8'd173: ln2_nk = {32'hC2661FD8, 32'hB8F8AB20};   // n = -83
            8'd174: ln2_nk = {32'hC2635A10, 32'hB8F5AC26};   // n = -82
            8'd175: ln2_nk = {32'hC2609448, 32'hB8F2AD2C};   // n = -81
            8'd176: ln2_nk = {32'hC25DCE80, 32'hB8EFAE32};   // n = -80
            8'd177: ln2_nk = {32'hC25B08B8, 32'hB8ECAF37};   // n = -79
            8'd178: ln2_nk = {32'hC25842F0, 32'hB8E9B03D};   // n = -78
            8'd179: ln2_nk = {32'hC2557D28, 32'hB8E6B143};   // n = -77
            8'd180: ln2_nk = {32'hC252B760, 32'hB8E3B249};   // n = -76
            8'd181: ln2_nk = {32'hC24FF198, 32'hB8E0B34E};   // n = -75
            8'd182: ln2_nk = {32'hC24D2BD0, 32'hB8DDB454};   // n = -74
            8'd183: ln2_nk = {32'hC24A6608, 32'hB8DAB55A};   // n = -73
            8'd184: ln2_nk = {32'hC247A040, 32'hB8D7B660};   // n = -72
            8'd185: ln2_nk = {32'hC244DA78, 32'hB8D4B766};   // n = -71
            8'd186: ln2_nk = {32'hC24214B0, 32'hB8D1B86B};   // n = -70
            8'd187: ln2_nk = {32'hC23F4EE8, 32'hB8CEB971};   // n = -69
            8'd188: ln2_nk = {32'hC23C8920, 32'hB8CBBA77};   // n = -68
            8'd189: ln2_nk = {32'hC239C358, 32'hB8C8BB7D};   // n = -67
            8'd190: ln2_nk = {32'hC236FD90, 32'hB8C5BC82};   // n = -66
            8'd191: ln2_nk = {32'hC23437C8, 32'hB8C2BD88};   // n = -65
            8'd192: ln2_nk = {32'hC2317200, 32'hB8BFBE8E};   // n = -64
            8'd193: ln2_nk = {32'hC22EAC38, 32'hB8BCBF94};   // n = -63
            8'd194: ln2_nk = {32'hC22BE670, 32'hB8B9C09A};   // n = -62
            8'd195: ln2_nk = {32'hC22920A8, 32'hB8B6C19F};   // n = -61
            8'd196: ln2_nk = {32'hC2265AE0, 32'hB8B3C2A5};   // n = -60
            8'd197: ln2_nk = {32'hC2239518, 32'hB8B0C3AB};   // n = -59
            8'd198: ln2_nk = {32'hC220CF50, 32'hB8ADC4B1};   // n = -58
            8'd199: ln2_nk = {32'hC21E0988, 32'hB8AAC5B6};   // n = -57
            8'd200: ln2_nk = {32'hC21B43C0, 32'hB8A7C6BC};   // n = -56
            8'd201: ln2_nk = {32'hC2187DF8, 32'hB8A4C7C2};   // n = -55
            8'd202: ln2_nk = {32'hC215B830, 32'hB8A1C8C8};   // n = -54
            8'd203: ln2_nk = {32'hC212F268, 32'hB89EC9CE};   // n = -53
            8'd204: ln2_nk = {32'hC2102CA0, 32'hB89BCAD3};   // n = -52
            8'd205: ln2_nk = {32'hC20D66D8, 32'hB898CBD9};   // n = -51
            8'd206: ln2_nk = {32'hC20AA110, 32'hB895CCDF};   // n = -50
            8'd207: ln2_nk = {32'hC207DB48, 32'hB892CDE5};   // n = -49
            8'd208: ln2_nk = {32'hC2051580, 32'hB88FCEEA};   // n = -48
            8'd209: ln2_nk = {32'hC2024FB8, 32'hB88CCFF0};   // n = -47
            8'd210: ln2_nk = {32'hC1FF13E0, 32'hB889D0F6};   // n = -46
            8'd211: ln2_nk = {32'hC1F98850, 32'hB886D1FC};   // n = -45
            8'd212: ln2_nk = {32'hC1F3FCC0, 32'hB883D302};   // n = -44
            8'd213: ln2_nk = {32'hC1EE7130, 32'hB880D407};   // n = -43
            8'd214: ln2_nk = {32'hC1E8E5A0, 32'hB87BAA1A};   // n = -42
            8'd215: ln2_nk = {32'hC1E35A10, 32'hB875AC26};   // n = -41
            8'd216: ln2_nk = {32'hC1DDCE80, 32'hB86FAE32};   // n = -40
            8'd217: ln2_nk = {32'hC1D842F0, 32'hB869B03D};   // n = -39
            8'd218: ln2_nk = {32'hC1D2B760, 32'hB863B249};   // n = -38
            8'd219: ln2_nk = {32'hC1CD2BD0, 32'hB85DB454};   // n = -37
            8'd220: ln2_nk = {32'hC1C7A040, 32'hB857B660};   // n = -36
            8'd221: ln2_nk = {32'hC1C214B0, 32'hB851B86B};   // n = -35
            8'd222: ln2_nk = {32'hC1BC8920, 32'hB84BBA77};   // n = -34
            8'd223: ln2_nk = {32'hC1B6FD90, 32'hB845BC82};   // n = -33
            8'd224: ln2_nk = {32'hC1B17200, 32'hB83FBE8E};   // n = -32
            8'd225: ln2_nk = {32'hC1ABE670, 32'hB839C09A};   // n = -31
            8'd226: ln2_nk = {32'hC1A65AE0, 32'hB833C2A5};   // n = -30
            8'd227: ln2_nk = {32'hC1A0CF50, 32'hB82DC4B1};   // n = -29
            8'd228: ln2_nk = {32'hC19B43C0, 32'hB827C6BC};   // n = -28
            8'd229: ln2_nk = {32'hC195B830, 32'hB821C8C8};   // n = -27
            8'd230: ln2_nk = {32'hC1902CA0, 32'hB81BCAD3};   // n = -26
            8'd231: ln2_nk = {32'hC18AA110, 32'hB815CCDF};   // n = -25
            8'd232: ln2_nk = {32'hC1851580, 32'hB80FCEEA};   // n = -24
            8'd233: ln2_nk = {32'hC17F13E0, 32'hB809D0F6};   // n = -23
            8'd234: ln2_nk = {32'hC173FCC0, 32'hB803D302};   // n = -22
            8'd235: ln2_nk = {32'hC168E5A0, 32'hB7FBAA1A};   // n = -21
            8'd236: ln2_nk = {32'hC15DCE80, 32'hB7EFAE32};   // n = -20
            8'd237: ln2_nk = {32'hC152B760, 32'hB7E3B249};   // n = -19
            8'd238: ln2_nk = {32'hC147A040, 32'hB7D7B660};   // n = -18
            8'd239: ln2_nk = {32'hC13C8920, 32'hB7CBBA77};   // n = -17
            8'd240: ln2_nk = {32'hC1317200, 32'hB7BFBE8E};   // n = -16
            8'd241: ln2_nk = {32'hC1265AE0, 32'hB7B3C2A5};   // n = -15
            8'd242: ln2_nk = {32'hC11B43C0, 32'hB7A7C6BC};   // n = -14
            8'd243: ln2_nk = {32'hC1102CA0, 32'hB79BCAD3};   // n = -13
            8'd244: ln2_nk = {32'hC1051580, 32'hB78FCEEA};   // n = -12
            8'd245: ln2_nk = {32'hC0F3FCC0, 32'hB783D302};   // n = -11
            8'd246: ln2_nk = {32'hC0DDCE80, 32'hB76FAE32};   // n = -10
            8'd247: ln2_nk = {32'hC0C7A040, 32'hB757B660};   // n = -9
            8'd248: ln2_nk = {32'hC0B17200, 32'hB73FBE8E};   // n = -8
            8'd249: ln2_nk = {32'hC09B43C0, 32'hB727C6BC};   // n = -7
            8'd250: ln2_nk = {32'hC0851580, 32'hB70FCEEA};   // n = -6
            8'd251: ln2_nk = {32'hC05DCE80, 32'hB6EFAE32};   // n = -5
            8'd252: ln2_nk = {32'hC0317200, 32'hB6BFBE8E};   // n = -4
            8'd253: ln2_nk = {32'hC0051580, 32'hB68FCEEA};   // n = -3
            8'd254: ln2_nk = {32'hBFB17200, 32'hB63FBE8E};   // n = -2
            8'd255: ln2_nk = {32'hBF317200, 32'hB5BFBE8E};   // n = -1
            8'd0  : ln2_nk = {32'h00000000, 32'h00000000};   // n = 0
            8'd1  : ln2_nk = {32'h3F317200, 32'h35BFBE8E};   // n = 1
            8'd2  : ln2_nk = {32'h3FB17200, 32'h363FBE8E};   // n = 2
            8'd3  : ln2_nk = {32'h40051580, 32'h368FCEEA};   // n = 3
            8'd4  : ln2_nk = {32'h40317200, 32'h36BFBE8E};   // n = 4
            8'd5  : ln2_nk = {32'h405DCE80, 32'h36EFAE32};   // n = 5
            8'd6  : ln2_nk = {32'h40851580, 32'h370FCEEA};   // n = 6
            8'd7  : ln2_nk = {32'h409B43C0, 32'h3727C6BC};   // n = 7
            8'd8  : ln2_nk = {32'h40B17200, 32'h373FBE8E};   // n = 8
            8'd9  : ln2_nk = {32'h40C7A040, 32'h3757B660};   // n = 9
            8'd10 : ln2_nk = {32'h40DDCE80, 32'h376FAE32};   // n = 10
            8'd11 : ln2_nk = {32'h40F3FCC0, 32'h3783D302};   // n = 11
            8'd12 : ln2_nk = {32'h41051580, 32'h378FCEEA};   // n = 12
            8'd13 : ln2_nk = {32'h41102CA0, 32'h379BCAD3};   // n = 13
            8'd14 : ln2_nk = {32'h411B43C0, 32'h37A7C6BC};   // n = 14
            8'd15 : ln2_nk = {32'h41265AE0, 32'h37B3C2A5};   // n = 15
            8'd16 : ln2_nk = {32'h41317200, 32'h37BFBE8E};   // n = 16
            8'd17 : ln2_nk = {32'h413C8920, 32'h37CBBA77};   // n = 17
            8'd18 : ln2_nk = {32'h4147A040, 32'h37D7B660};   // n = 18
            8'd19 : ln2_nk = {32'h4152B760, 32'h37E3B249};   // n = 19
            8'd20 : ln2_nk = {32'h415DCE80, 32'h37EFAE32};   // n = 20
            8'd21 : ln2_nk = {32'h4168E5A0, 32'h37FBAA1A};   // n = 21
            8'd22 : ln2_nk = {32'h4173FCC0, 32'h3803D302};   // n = 22
            8'd23 : ln2_nk = {32'h417F13E0, 32'h3809D0F6};   // n = 23
            8'd24 : ln2_nk = {32'h41851580, 32'h380FCEEA};   // n = 24
            8'd25 : ln2_nk = {32'h418AA110, 32'h3815CCDF};   // n = 25
            8'd26 : ln2_nk = {32'h41902CA0, 32'h381BCAD3};   // n = 26
            8'd27 : ln2_nk = {32'h4195B830, 32'h3821C8C8};   // n = 27
            8'd28 : ln2_nk = {32'h419B43C0, 32'h3827C6BC};   // n = 28
            8'd29 : ln2_nk = {32'h41A0CF50, 32'h382DC4B1};   // n = 29
            8'd30 : ln2_nk = {32'h41A65AE0, 32'h3833C2A5};   // n = 30
            8'd31 : ln2_nk = {32'h41ABE670, 32'h3839C09A};   // n = 31
            8'd32 : ln2_nk = {32'h41B17200, 32'h383FBE8E};   // n = 32
            8'd33 : ln2_nk = {32'h41B6FD90, 32'h3845BC82};   // n = 33
            8'd34 : ln2_nk = {32'h41BC8920, 32'h384BBA77};   // n = 34
            8'd35 : ln2_nk = {32'h41C214B0, 32'h3851B86B};   // n = 35
            8'd36 : ln2_nk = {32'h41C7A040, 32'h3857B660};   // n = 36
            8'd37 : ln2_nk = {32'h41CD2BD0, 32'h385DB454};   // n = 37
            8'd38 : ln2_nk = {32'h41D2B760, 32'h3863B249};   // n = 38
            8'd39 : ln2_nk = {32'h41D842F0, 32'h3869B03D};   // n = 39
            8'd40 : ln2_nk = {32'h41DDCE80, 32'h386FAE32};   // n = 40
            8'd41 : ln2_nk = {32'h41E35A10, 32'h3875AC26};   // n = 41
            8'd42 : ln2_nk = {32'h41E8E5A0, 32'h387BAA1A};   // n = 42
            8'd43 : ln2_nk = {32'h41EE7130, 32'h3880D407};   // n = 43
            8'd44 : ln2_nk = {32'h41F3FCC0, 32'h3883D302};   // n = 44
            8'd45 : ln2_nk = {32'h41F98850, 32'h3886D1FC};   // n = 45
            8'd46 : ln2_nk = {32'h41FF13E0, 32'h3889D0F6};   // n = 46
            8'd47 : ln2_nk = {32'h42024FB8, 32'h388CCFF0};   // n = 47
            8'd48 : ln2_nk = {32'h42051580, 32'h388FCEEA};   // n = 48
            8'd49 : ln2_nk = {32'h4207DB48, 32'h3892CDE5};   // n = 49
            8'd50 : ln2_nk = {32'h420AA110, 32'h3895CCDF};   // n = 50
            8'd51 : ln2_nk = {32'h420D66D8, 32'h3898CBD9};   // n = 51
            8'd52 : ln2_nk = {32'h42102CA0, 32'h389BCAD3};   // n = 52
            8'd53 : ln2_nk = {32'h4212F268, 32'h389EC9CE};   // n = 53
            8'd54 : ln2_nk = {32'h4215B830, 32'h38A1C8C8};   // n = 54
            8'd55 : ln2_nk = {32'h42187DF8, 32'h38A4C7C2};   // n = 55
            8'd56 : ln2_nk = {32'h421B43C0, 32'h38A7C6BC};   // n = 56
            8'd57 : ln2_nk = {32'h421E0988, 32'h38AAC5B6};   // n = 57
            8'd58 : ln2_nk = {32'h4220CF50, 32'h38ADC4B1};   // n = 58
            8'd59 : ln2_nk = {32'h42239518, 32'h38B0C3AB};   // n = 59
            8'd60 : ln2_nk = {32'h42265AE0, 32'h38B3C2A5};   // n = 60
            8'd61 : ln2_nk = {32'h422920A8, 32'h38B6C19F};   // n = 61
            8'd62 : ln2_nk = {32'h422BE670, 32'h38B9C09A};   // n = 62
            8'd63 : ln2_nk = {32'h422EAC38, 32'h38BCBF94};   // n = 63
            8'd64 : ln2_nk = {32'h42317200, 32'h38BFBE8E};   // n = 64
            8'd65 : ln2_nk = {32'h423437C8, 32'h38C2BD88};   // n = 65
            8'd66 : ln2_nk = {32'h4236FD90, 32'h38C5BC82};   // n = 66
            8'd67 : ln2_nk = {32'h4239C358, 32'h38C8BB7D};   // n = 67
            8'd68 : ln2_nk = {32'h423C8920, 32'h38CBBA77};   // n = 68
            8'd69 : ln2_nk = {32'h423F4EE8, 32'h38CEB971};   // n = 69
            8'd70 : ln2_nk = {32'h424214B0, 32'h38D1B86B};   // n = 70
            8'd71 : ln2_nk = {32'h4244DA78, 32'h38D4B766};   // n = 71
            8'd72 : ln2_nk = {32'h4247A040, 32'h38D7B660};   // n = 72
            8'd73 : ln2_nk = {32'h424A6608, 32'h38DAB55A};   // n = 73
            8'd74 : ln2_nk = {32'h424D2BD0, 32'h38DDB454};   // n = 74
            8'd75 : ln2_nk = {32'h424FF198, 32'h38E0B34E};   // n = 75
            8'd76 : ln2_nk = {32'h4252B760, 32'h38E3B249};   // n = 76
            8'd77 : ln2_nk = {32'h42557D28, 32'h38E6B143};   // n = 77
            8'd78 : ln2_nk = {32'h425842F0, 32'h38E9B03D};   // n = 78
            8'd79 : ln2_nk = {32'h425B08B8, 32'h38ECAF37};   // n = 79
            8'd80 : ln2_nk = {32'h425DCE80, 32'h38EFAE32};   // n = 80
            8'd81 : ln2_nk = {32'h42609448, 32'h38F2AD2C};   // n = 81
            8'd82 : ln2_nk = {32'h42635A10, 32'h38F5AC26};   // n = 82
            8'd83 : ln2_nk = {32'h42661FD8, 32'h38F8AB20};   // n = 83
            8'd84 : ln2_nk = {32'h4268E5A0, 32'h38FBAA1A};   // n = 84
            8'd85 : ln2_nk = {32'h426BAB68, 32'h38FEA915};   // n = 85
            8'd86 : ln2_nk = {32'h426E7130, 32'h3900D407};   // n = 86
            8'd87 : ln2_nk = {32'h427136F8, 32'h39025385};   // n = 87
            8'd88 : ln2_nk = {32'h4273FCC0, 32'h3903D302};   // n = 88
            8'd89 : ln2_nk = {32'h4276C288, 32'h3905527F};   // n = 89
            8'd90 : ln2_nk = {32'h42798850, 32'h3906D1FC};   // n = 90
            8'd91 : ln2_nk = {32'h427C4E18, 32'h39085179};   // n = 91
            8'd92 : ln2_nk = {32'h427F13E0, 32'h3909D0F6};   // n = 92
            8'd93 : ln2_nk = {32'h4280ECD4, 32'h390B5073};   // n = 93
            8'd94 : ln2_nk = {32'h42824FB8, 32'h390CCFF0};   // n = 94
            8'd95 : ln2_nk = {32'h4283B29C, 32'h390E4F6D};   // n = 95
            8'd96 : ln2_nk = {32'h42851580, 32'h390FCEEA};   // n = 96
            8'd97 : ln2_nk = {32'h42867864, 32'h39114E68};   // n = 97
            8'd98 : ln2_nk = {32'h4287DB48, 32'h3912CDE5};   // n = 98
            8'd99 : ln2_nk = {32'h42893E2C, 32'h39144D62};   // n = 99
            8'd100: ln2_nk = {32'h428AA110, 32'h3915CCDF};   // n = 100
            8'd101: ln2_nk = {32'h428C03F4, 32'h39174C5C};   // n = 101
            8'd102: ln2_nk = {32'h428D66D8, 32'h3918CBD9};   // n = 102
            8'd103: ln2_nk = {32'h428EC9BC, 32'h391A4B56};   // n = 103
            8'd104: ln2_nk = {32'h42902CA0, 32'h391BCAD3};   // n = 104
            8'd105: ln2_nk = {32'h42918F84, 32'h391D4A50};   // n = 105
            8'd106: ln2_nk = {32'h4292F268, 32'h391EC9CE};   // n = 106
            8'd107: ln2_nk = {32'h4294554C, 32'h3920494B};   // n = 107
            8'd108: ln2_nk = {32'h4295B830, 32'h3921C8C8};   // n = 108
            8'd109: ln2_nk = {32'h42971B14, 32'h39234845};   // n = 109
            8'd110: ln2_nk = {32'h42987DF8, 32'h3924C7C2};   // n = 110
            8'd111: ln2_nk = {32'h4299E0DC, 32'h3926473F};   // n = 111
            8'd112: ln2_nk = {32'h429B43C0, 32'h3927C6BC};   // n = 112
            8'd113: ln2_nk = {32'h429CA6A4, 32'h39294639};   // n = 113
            8'd114: ln2_nk = {32'h429E0988, 32'h392AC5B6};   // n = 114
            8'd115: ln2_nk = {32'h429F6C6C, 32'h392C4534};   // n = 115
            8'd116: ln2_nk = {32'h42A0CF50, 32'h392DC4B1};   // n = 116
            8'd117: ln2_nk = {32'h42A23234, 32'h392F442E};   // n = 117
            8'd118: ln2_nk = {32'h42A39518, 32'h3930C3AB};   // n = 118
            8'd119: ln2_nk = {32'h42A4F7FC, 32'h39324328};   // n = 119
            8'd120: ln2_nk = {32'h42A65AE0, 32'h3933C2A5};   // n = 120
            8'd121: ln2_nk = {32'h42A7BDC4, 32'h39354222};   // n = 121
            8'd122: ln2_nk = {32'h42A920A8, 32'h3936C19F};   // n = 122
            8'd123: ln2_nk = {32'h42AA838C, 32'h3938411C};   // n = 123
            8'd124: ln2_nk = {32'h42ABE670, 32'h3939C09A};   // n = 124
            8'd125: ln2_nk = {32'h42AD4954, 32'h393B4017};   // n = 125
            8'd126: ln2_nk = {32'h42AEAC38, 32'h393CBF94};   // n = 126
            8'd127: ln2_nk = {32'h42B00F1C, 32'h393E3F11};   // n = 127
            default: ln2_nk = 64'd0;
        endcase
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t;
    wire [2:0] f;
    ot_hdc_qmul_lat__d4g_sfu #(LM) m_t (clk, rst_n, vd[1], xc, K_LOG2E, t, f[0]);   // 1 + LM

    // n = rint-to-even(t), |t| < 127.  With E = field - 127, the integer part
    // is the significand shifted right by 23 - E (E in [-1, 6]); below E = -1,
    // |t| < 1/2 and n = 0.
    wire [23:0] tm = {1'b1, t[22:0]};
    wire [7:0]  te = t[30:23];
    wire [4:0]  tsh = 5'd23 - (te[4:0] - 5'd31);      // 23 - E, as te - 127 = te[4:0] - 31 (mod 32)
    wire [23:0] tip = tm >> tsh;
    wire [4:0]  trb = tsh - 5'd1;
    wire        thalf = tm[trb];
    wire        tstk = |(tm & ~({24{1'b1}} << trb));
    wire [7:0]  tmag = (te < 8'd126) ? 8'd0 : (tip[7:0] + {7'd0, thalf && (tstk || tip[0])});
    reg  [8:0]  nint;
    always @(posedge clk) nint <= t[31] ? -{1'b0, tmag} : {1'b0, tmag};

    reg [31:0] a_hi, a_lo;
    always @(posedge clk) {a_hi, a_lo} <= ln2_nk(nint[7:0]);

    wire [31:0] r1, r, xc_d, lo_d;
    ot_hdc_delay__d4g_sfu #(.W(32), .D(T_K - 1)) d_x (clk, rst_n, xc, xc_d);
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_r1 (clk, rst_n, vd[T_K], xc_d, {~a_hi[31], a_hi[30:0]}, r1, f[1]);
    ot_hdc_delay__d4g_sfu #(.W(32), .D(LA)) d_lo (clk, rst_n, a_lo, lo_d);
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_r  (clk, rst_n, vd[T_R1], r1, {~lo_d[31], lo_d[30:0]}, r, f[2]);

    // Horner: p = C0; six times p = p*r + C[k]; r travels in (LM+LA)-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay__d4g_sfu #(.W(32), .D(LM + LA)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_qmul_lat__d4g_sfu #(LM) u_m (clk, rst_n, vd[T_R + (LM + LA)*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) u_a (clk, rst_n, vd[T_R + (LM + LA)*(k-1) + LM], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [8:0] nint_d;
    ot_hdc_delay__d4g_sfu #(.W(9), .D(T_P - T_N)) d_n (clk, rst_n, nint, nint_d);
    // 2^n into the exponent field (a keep-prefix add in the serial-domain build, LM != 3)
    wire [31:0] y_n;
    wire        unused_cy;
    ot_hdc_kadd__d4g_sfu #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_yn (.a(pa[6]), .b({{14{nint_d[8]}}, nint_d, 23'd0}), .cin(1'b0),
                                                      .s(y_n), .cout(unused_cy));
    always @(posedge clk) y <= y_n;

    assign fault = |{f, hf};
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_v41x_rsqrt__d4g_sfu #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_sfu)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat__d4g_sfu: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer IT = 3 * LM + LA;
    localparam integer DEPTH = 1 + 3 * IT;      // 37 (LM 3), 46 (LM 4)
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    wire [31:0] y0_n;
    wire        unused_cy;
    ot_hdc_kadd__d4g_sfu #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_y0 (.a(32'h5F3759DF), .b(~{1'b0, x[31:1]}), .cin(1'b1), .s(y0_n),
                                                      .cout(unused_cy));
    always @(posedge clk) y0 <= y0_n;
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_qmul_lat__d4g_sfu #(LM) m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // LM
    ot_hdc_delay__d4g_sfu #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 1 + LM
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay__d4g_sfu #(.W(32), .D(IT)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_qmul_lat__d4g_sfu #(LM) m_yy (clk, rst_n, vd[1 + IT*k],             yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_qmul_lat__d4g_sfu #(LM) m_hm (clk, rst_n, vd[1 + IT*k + LM],        hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_s  (clk, rst_n, vd[1 + IT*k + 2*LM],      32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay__d4g_sfu #(.W(32), .D(2*LM + LA)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_qmul_lat__d4g_sfu #(LM) m_y  (clk, rst_n, vd[1 + IT*k + 2*LM + LA], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION: II 1, fixed DEPTH 19.
//
// The function, the operand decode, the finish and the fault convention are
// those of rtl/hdc/v41/ot_hdc_fdiv__d4g_sfu.sv, transcribed unchanged:
//   y = RN_even(a / b), gradual underflow, every zero result +0; a nonfinite
//   operand, a zero divisor or an overflowing quotient fails closed
//   (fault, y = +0).
// What changes is the recurrence.  It forms the same 27 quotient bits and the
// same final remainder, but TWO bits per register stage.  A stage takes x = 4R
// (2 ma in the first stage), with R < mb the running remainder, so x < 4 mb.
// It forms x - mb, x - 2 mb and x - 3 mb in parallel, and the digit
// q = floor(x / mb) in [0, 3] is the largest with a non-negative difference.
// That is one subtract and a select, not two subtracts in series: the routed
// SFU lane measured two serial restoring steps at 907 MHz.  3 mb is formed
// once, in a stage after the decode.  The last stage forms one bit.  A
// correctly rounded quotient is unique, so the result is the same bit for bit.
// Stages: 1 decode, 1 (3 mb), 14 recurrence, 3 finish.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_fdiv__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer QB = 27;
    localparam integer NS = (QB + 1) / 2;      // 14
    localparam integer DEPTH = 2 + NS + 3;     // 19

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    wire [33:0] na = norm(a[30:23], a[22:0]);
    wire [33:0] nb = norm(b[30:23], b[22:0]);

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_zero <= (a[30:0] == 31'd0);
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // 3 mb, once (hbm-fmax-su: a keep-prefix add)
    wire [25:0] mb3_w;
    wire        mb3_co;
    ot_hdc_ksadd_k__d4g_sfu #(.W(26)) u_mb3 (.a({2'b0, d_mb}), .b({1'b0, d_mb, 1'b0}), .cin(1'b0), .s(mb3_w), .cout(mb3_co));
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= d_sign; e_zero <= d_zero; e_bad <= d_bad; e_e <= d_e;
        e_ma <= d_ma; e_mb <= d_mb; e_mb3 <= mb3_w;
    end

    reg [24:0]        r_rem  [0:NS-1];
    reg [QB-1:0]      r_q    [0:NS-1];
    reg [23:0]        r_mb   [0:NS-1];
    reg [25:0]        r_mb3  [0:NS-1];
    reg               r_sign [0:NS-1];
    reg               r_zero [0:NS-1];
    reg               r_bad  [0:NS-1];
    reg signed [10:0] r_e    [0:NS-1];

    genvar j;
    generate
        for (j = 0; j < NS; j = j + 1) begin : g_rec
            // quotient bits 2j and 2j+1 (bit 2^-k is restoring step k); stage NS-1 forms one bit
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            // hbm-fmax-su: the three trial subtractions as keep-prefix adders (behavioural, 177 ps over 0.833 ns at SS)
            wire [27:0]   d1, d2, d3;
            wire [2:0]    unused_dc;
            ot_hdc_ksadd_k__d4g_sfu #(.W(28)) u_d1 (.a({1'b0, x}), .b(~{4'b0, mb}), .cin(1'b1), .s(d1), .cout(unused_dc[0]));
            ot_hdc_ksadd_k__d4g_sfu #(.W(28)) u_d2 (.a({1'b0, x}), .b(~{3'b0, mb, 1'b0}), .cin(1'b1), .s(d2), .cout(unused_dc[1]));
            ot_hdc_ksadd_k__d4g_sfu #(.W(28)) u_d3 (.a({1'b0, x}), .b(~{2'b0, mb3}), .cin(1'b1), .s(d3), .cout(unused_dc[2]));
            wire [1:0]    q  = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
            wire [26:0]   r  = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
            always @(posedge clk) begin
                r_rem[j]  <= r[24:0];
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[NS-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_zero <= r_zero[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = ~({25{1'b1}} << sh);      // hbm-fmax-su: (1 << sh) - 1 without the subtract
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3: round to nearest even, encode ----------------------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    // hbm-fmax-su: the rounding increment as a keep-prefix incrementer (the behavioural add re-rippled: 233 ps over
    // 0.833 ns at SS); the same sum
    wire [30:0] code;
    wire        code_co;
    ot_hdc_inc_k__d4g_sfu #(.W(31)) u_rinc (.a({f2_field, f2_sig[22:0]}), .inc(rup), .y(code), .co(code_co));
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule

// ---------------------------------------------------------------------------
// softplus(x) and sqrt(softplus(x)): II 1, fixed DEPTH 162.  The operation order
// of rtl/hdc/v41/ot_hdc_softplus.sv (tools/hdc_golden_v41.softplus, .sqrt), on
// the fast units:
//     t = exp(-|x|)            49     ot_hdc_v41x_exp__d4g_sfu
//     u = t / (t + 2)          3 + 19 ot_hdc_qadd__d4g_sfu, ot_hdc_v41x_fdiv__d4g_sfu
//     u2 = u * u               3
//     p = 1/17; p = p*u2 + 1/(2i+1), i = 7 .. 0      8 x (3 + 3)
//     l = (u * p) * 2          3 + 3
//     sp = max(x, 0) + l       3
//     r = sqrt(sp)             31     ot_hdc_fsqrt__d4g_sfu
// The fault convention is ot_hdc_softplus's.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_softplus__d4g_sfu #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_sfu)
    parameter integer LA = 3,                   // add latency (ot_hdc_qadd_lat__d4g_sfu: 3, or 4 input cut)
    parameter integer DDIV = 19,                // c12: 21 = ot_dsrom_fdiv_f12__d4g_sfu
    parameter integer FSQ = 0                   // c12: 1 = ot_hdc_fsqrt_c12__d4g_sfu
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] sp,
    output wire [31:0] r,
    output wire        vo,
    output wire        fault
);
    localparam integer T_EXP  = 7 * LM + 8 * LA + 4;   // ot_hdc_v41x_exp__d4g_sfu DEPTH
    localparam integer T_DEN  = T_EXP + LA;
    localparam integer T_U    = T_DEN + DDIV;
    localparam integer T_U2   = T_U + LM;
    localparam integer T_P    = T_U2 + 8 * (LM + LA);
    localparam integer T_UP   = T_P + LM;
    localparam integer T_L    = T_UP + LM;
    localparam integer T_SP   = T_L + LA;
    localparam integer DEPTH  = T_SP + 31;       // 162 (LM 3), 180 (LM 4)
    localparam [32*9-1:0] C = {32'h3D70F0F1, 32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39,
                               32'h3E124925, 32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000};  // 1/17 .. 1/1
    function automatic [31:0] coef(input integer i);
        coef = C[32*(8-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    wire [31:0] t, den, t_d, u, u2, lp, l;
    wire f_exp, f_den, f_div, f_u2, f_up, f_l, f_sp, f_sq;
    ot_hdc_v41x_exp__d4g_sfu #(.LM(LM), .LA(LA)) u_exp (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b1, x[30:0]}), .y(t), .vo(), .fault(f_exp));
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_den (clk, rst_n, vd[T_EXP], t, 32'h40000000, den, f_den);
    ot_hdc_delay__d4g_sfu #(.W(32), .D(LA)) d_t (clk, rst_n, t, t_d);
    generate if (DDIV == 31) begin : g_d31
        ot_hdc_fdiv__d4g_sfu    u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    end else if (DDIV == 21) begin : g_d21
        ot_dsrom_fdiv_f12__d4g_sfu u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    end else begin : g_d19
        ot_hdc_v41x_fdiv__d4g_sfu u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    end endgenerate
    ot_hdc_qmul_lat__d4g_sfu #(LM) m_u2 (clk, rst_n, vd[T_U], u, u, u2, f_u2);

    wire [31:0] u2d [0:7];
    wire [31:0] pm  [1:8];
    wire [31:0] pa  [0:8];
    wire [16:1] hf;
    assign u2d[0] = u2;
    assign pa[0] = coef(0);
    genvar k;
    generate
        for (k = 1; k <= 8; k = k + 1) begin : g_h
            if (k < 8) begin : g_d
                ot_hdc_delay__d4g_sfu #(.W(32), .D(LM + LA)) d_u2 (clk, rst_n, u2d[k-1], u2d[k]);
            end
            ot_hdc_qmul_lat__d4g_sfu #(LM) u_m (clk, rst_n, vd[T_U2 + (LM + LA)*(k-1)], pa[k-1], u2d[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) u_a (clk, rst_n, vd[T_U2 + (LM + LA)*(k-1) + LM], pm[k], coef(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [31:0] u_d;
    ot_hdc_delay__d4g_sfu #(.W(32), .D(T_P - T_U)) d_u (clk, rst_n, u, u_d);
    ot_hdc_qmul_lat__d4g_sfu #(LM) m_up (clk, rst_n, vd[T_P], u_d, pa[8], lp, f_up);
    ot_hdc_qmul_lat__d4g_sfu #(LM) m_l  (clk, rst_n, vd[T_UP], lp, 32'h40000000, l, f_l);

    reg  [31:0] mx;
    wire [31:0] mx_d, spv;
    wire x_nan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    always @(posedge clk) mx <= (x[31] && !x_nan) ? 32'd0 : x;
    ot_hdc_delay__d4g_sfu #(.W(32), .D(T_L - 1)) d_mx (clk, rst_n, mx, mx_d);
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_sp (clk, rst_n, vd[T_L], mx_d, l, spv, f_sp);

    generate if (FSQ != 0) begin : g_sq12
        ot_hdc_fsqrt_c12__d4g_sfu u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    end else begin : g_sq
        ot_hdc_fsqrt__d4g_sfu u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    end endgenerate
    ot_hdc_delay__d4g_sfu #(.W(32), .D(DEPTH - T_SP)) d_sp (clk, rst_n, spv, sp);

    wire f_sp_d;
    ot_hdc_delay__d4g_sfu #(.W(1), .D(DEPTH - T_SP), .RESET(1)) d_fsp (clk, rst_n, f_sp, f_sp_d);
    assign fault = f_sp_d | f_sq | f_exp | f_den | f_div | f_u2 | (|hf) | f_up | f_l;
endmodule

// ---------------------------------------------------------------------------
// Insertion delay line: an item entering with depth choice k leaves exactly
// DEPTHS[k] cycles later (0 = a wire), all items through ONE exit.  It is a
// shift register toward the exit whose stage DEPTHS[k] also loads new items.
// Items keep their order only if every item leaves after the one before it;
// the controller guarantees that (ot_hdc_v41x_vec: the checkpoint rule).  A
// stage that is loaded while an item shifts into it raises `coll`.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_ins__d4g_sfu #(
    parameter integer W = 32,
    parameter integer K = 2,                 // depth choices
    parameter [16*K-1:0] DEPTHS = {16'd3, 16'd0},   // choice k = DEPTHS[16k +: 16]
    parameter integer DMAX = 3,              // max over DEPTHS
    parameter integer RESET_DATA = 0,
    // RING (CLAUDE HBM-ABSTRACTS views agent, default off): the line as a timing wheel of DMAX slots.  An item loaded at
    // edge e with depth p goes to slot (e + p) mod DMAX and is read into the output register at edge e + p - 1, the
    // cycle the shift line presents it in r[1]; a slot still holding an item due in the same cycle is the shift line's
    // collision (rv[p+1] set), the new item wins in both.  Needs every non-zero depth >= 2.  Same vo / q / coll / busy
    // as the shift line for valid items (q while vo = 0 is not defined by either form).
    parameter integer RING = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [K-1:0] sel,                 // one-hot depth choice
    input  wire [W-1:0] d,
    output wire         vo,
    output wire [W-1:0] q,
    output wire         coll,
    output wire         busy                 // an item is in the line
);
    function automatic has(input integer p, input [K-1:0] s);
        integer k;
        begin
            has = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p && s[k]) has = 1'b1;
        end
    endfunction
    function automatic canbe(input integer p);
        integer k;
        begin
            canbe = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p) canbe = 1'b1;
        end
    endfunction
    // RING 4 eligibility: even DMAX, every depth even, no data reset (otherwise the instance stays RING 3)
    function automatic r4ok(input integer dummy);
        integer k;
        begin
            r4ok = (DMAX % 2 == 0) && (RESET_DATA == 0);
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] % 2 != 0) r4ok = 1'b0;
        end
    endfunction
    localparam integer R4OK = r4ok(0);
    generate
        if (DMAX == 0) begin : g_wire
            assign vo = v; assign q = d; assign coll = 1'b0; assign busy = 1'b0;
        end else if (RING >= 4 && R4OK != 0) begin : g_ring4
            // RING 4 (el1011-hbm-sfu 2026-10-11, textbook class 1: the SFU lane's u_l4 wheel was 15,981 of its 47,785
            // clock sinks): RING 3's valid side (oh / mv / rs / qv / coll / busy, unchanged) with the DATA slots in two
            // single-port SRAM banks by slot parity (bank = slot[0], row = slot >> 1).  Every edge reads slot e+1 and
            // writes at most one slot e+DK; with N and every non-zero DK even the two always fall in different banks,
            // so each 1RW bank does one access per edge (1R1W behaviour).  The SRAM output register is the RING 3 qr.
            localparam integer N = DMAX;
            localparam integer NR = N / 2;
            localparam integer SB = $clog2(N);
            initial if (canbe(1) || DMAX < 2) $error("ot_hdc_v41x_ins__d4g_sfu RING 4: depth 1 not supported");
            reg [N-1:0] oh;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            wire [N-1:0] we;
            wire [N-1:0] rs;
            reg  [N-1:0] mv;
            genvar j, k;
            for (j = 0; j < N; j = j + 1) begin : g_s
                localparam integer JR = (j - 1 + N) % N;
                assign rs[j] = oh[JR];
                wire [K-1:0] wt;
                for (k = 0; k < K; k = k + 1) begin : g_k
                    localparam integer DK = DEPTHS[16*k +: 16];
                    localparam integer JW = (j - (DK % N) + N) % N;
                    if (DK != 0) begin : g_d
                        assign wt[k] = v && sel[k] && oh[JW];
                    end else begin : g_z
                        assign wt[k] = 1'b0;
                    end
                end
                assign we[j] = |wt;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) mv[j] <= 1'b0;
                    else if (we[j]) mv[j] <= 1'b1;
                    else if (rs[j]) mv[j] <= 1'b0;
            end
            // registered slot counters: rp = e+1 (read), wp[k] = e+DK (write of choice k); all wrap at N
            reg [SB-1:0] rp;
            reg [SB-1:0] wp [0:K-1];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) rp <= 1 % N; else rp <= (rp == N - 1) ? {SB{1'b0}} : rp + 1'b1;
            for (k = 0; k < K; k = k + 1) begin : g_wp
                localparam integer DK = DEPTHS[16*k +: 16] % N;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) wp[k] <= DK; else wp[k] <= (wp[k] == N - 1) ? {SB{1'b0}} : wp[k] + 1'b1;
            end
            reg [SB-1:0] ws;
            reg wv;
            integer kk;
            always @(*) begin
                ws = {SB{1'b0}}; wv = 1'b0;
                for (kk = 0; kk < K; kk = kk + 1)
                    if (DEPTHS[16*kk +: 16] != 0 && v && sel[kk]) begin ws = wp[kk]; wv = 1'b1; end
            end
            wire [W-1:0] rd0, rd1;
            ot_hdc_ins_ram__d4g_sfu #(.W(W), .R(NR)) u_b0 (.clk(clk), .ce(!rp[0] || (wv && !ws[0])), .we(wv && !ws[0]),
                .addr(wv && !ws[0] ? ws[SB-1:1] : rp[SB-1:1]), .wd(d), .rd(rd0));
            ot_hdc_ins_ram__d4g_sfu #(.W(W), .R(NR)) u_b1 (.clk(clk), .ce(rp[0] || (wv && ws[0])), .we(wv && ws[0]),
                .addr(wv && ws[0] ? ws[SB-1:1] : rp[SB-1:1]), .wd(d), .rd(rd1));
            reg rb;
            always @(posedge clk) rb <= rp[0];
            wire cw = |(we & mv);
            wire rdv = |(mv & rs);
            reg qv;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) qv <= 1'b0; else qv <= rdv;
            wire [W-1:0] qr = rb ? rd1 : rd0;
            wire now = v && has(0, sel);
            assign vo = now || qv;
            assign q  = now ? d : qr;
            assign coll = cw || (now && qv);
            assign busy = qv || (|mv);
        end else if (RING >= 3) begin : g_ring3
            // RING 3 (hbm-blocks 2026-10-07): RING 2's timing wheel (per-16-bit-chunk slot-pointer copies) with every
            // rotation written as constant generate wiring.  RING 2 calls rot() inside always @(*) blocks once per
            // (slot, chunk, depth) and ORs the read word bit by bit: at the SFU lane's DMAX/K/W the yosys AST frontend
            // sat > 10 h deriving this module.  Same vo / q / coll / busy as RING 2 cycle for cycle.
            localparam integer N = DMAX;
            initial if (canbe(1) || DMAX < 2) $error("ot_hdc_v41x_ins__d4g_sfu RING: depth 1 not supported");
            localparam integer CH = 16;
            localparam integer NC = (W + CH - 1) / CH;
            reg [N-1:0] oh;                          // slot e mod N (valid side)
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            wire [N-1:0] ohc [0:NC-1];               // per-chunk kept copies (data side)
            genvar c0;
            for (c0 = 0; c0 < NC; c0 = c0 + 1) begin : g_ohc
                (* keep *) reg [N-1:0] r;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) r <= {{(N-1){1'b0}}, 1'b1};
                    else r <= {r[N-2:0], r[N-1]};
                assign ohc[c0] = r;
            end
            wire [N-1:0] we;                         // valid-side write enables
            wire [N-1:0] rs;                         // slot read at this edge: rot(oh, 1)
            reg  [N-1:0] mv;
            wire [W-1:0] acc [0:N];                  // read word, OR-accumulated over the slots
            assign acc[0] = {W{1'b0}};
            genvar j, c, k;
            for (j = 0; j < N; j = j + 1) begin : g_s
                localparam integer JR = (j - 1 + N) % N;
                assign rs[j] = oh[JR];
                wire [K-1:0] wt;
                for (k = 0; k < K; k = k + 1) begin : g_k
                    localparam integer DK = DEPTHS[16*k +: 16];
                    localparam integer JW = (j - (DK % N) + N) % N;
                    if (DK != 0) begin : g_d
                        assign wt[k] = v && sel[k] && oh[JW];
                    end else begin : g_z
                        assign wt[k] = 1'b0;
                    end
                end
                assign we[j] = |wt;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) mv[j] <= 1'b0;
                    else if (we[j]) mv[j] <= 1'b1;
                    else if (rs[j]) mv[j] <= 1'b0;
                wire [W-1:0] mj;                     // slot j's data
                wire [W-1:0] rmask;                  // per-chunk read select of slot j
                for (c = 0; c < NC; c = c + 1) begin : g_c
                    localparam integer LO = c * CH;
                    localparam integer WC = (W - LO < CH) ? (W - LO) : CH;
                    wire [K-1:0] wtc;
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        localparam integer DK = DEPTHS[16*k +: 16];
                        localparam integer JW = (j - (DK % N) + N) % N;
                        if (DK != 0) begin : g_d
                            assign wtc[k] = v && sel[k] && ohc[c][JW];
                        end else begin : g_z
                            assign wtc[k] = 1'b0;
                        end
                    end
                    wire wec = |wtc;
                    reg [WC-1:0] mc;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) mc <= {WC{1'b0}}; else if (wec) mc <= d[LO +: WC];
                    end else begin : g_nd
                        always @(posedge clk) if (wec) mc <= d[LO +: WC];
                    end
                    assign mj[LO +: WC] = mc;
                    assign rmask[LO +: WC] = {WC{ohc[c][JR]}};
                end
                assign acc[j + 1] = acc[j] | (mj & rmask);
            end
            wire [W-1:0] rd = acc[N];
            wire cw = |(we & mv);
            wire rdv = |(mv & rs);
            reg qv;
            reg [W-1:0] qr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) qv <= 1'b0; else qv <= rdv;
            if (RESET_DATA != 0) begin : g_qrd
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnd
                always @(posedge clk) qr <= rd;
            end
            wire now = v && has(0, sel);
            assign vo = now || qv;
            assign q  = now ? d : qr;
            assign coll = cw || (now && qv);
            assign busy = qv || (|mv);
        end else if (RING != 0) begin : g_ring
            localparam integer N = DMAX;
            initial if (canbe(1) || DMAX < 2) $error("ot_hdc_v41x_ins__d4g_sfu RING: depth 1 not supported");
            reg [N-1:0] oh;                          // one-hot slot of the current edge e (slot e mod N)
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            // RING 2 (views agent 2026-10-07, SFU lane 67f177d39 oh -> m -24 ps over 304 endpoints, 10 levels): the slot
            // pointer in one kept copy per 16-bit data chunk (reset and rotated identically), each driving only its chunk's
            // write enables and read select.  0 cycles.
            localparam integer CH = 16;
            localparam integer NC = (RING >= 2) ? (W + CH - 1) / CH : 1;
            wire [N-1:0] ohc [0:NC-1];
            genvar c0;
            for (c0 = 0; c0 < NC; c0 = c0 + 1) begin : g_ohc
                (* keep *) reg [N-1:0] r;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) r <= {{(N-1){1'b0}}, 1'b1};
                    else r <= {r[N-2:0], r[N-1]};
                assign ohc[c0] = r;
            end
            // rot(oh, k)[j] = oh[(j - k) mod N]: the slot k edges ahead
            function automatic [N-1:0] rot(input [N-1:0] x, input integer k);
                integer j;
                begin
                    for (j = 0; j < N; j = j + 1) rot[j] = x[(j - (k % N) + N) % N];
                end
            endfunction
            reg [W-1:0] m [0:N-1];
            reg [N-1:0] mv;
            reg [W-1:0] qr;
            reg         qv;
            // write enables: the chosen depth's slot
            reg [N-1:0] we;
            reg         cw;
            integer k;
            always @(*) begin
                we = {N{1'b0}};
                for (k = 0; k < K; k = k + 1)
                    if (DEPTHS[16*k +: 16] != 0 && v && sel[k]) we = we | rot(oh, DEPTHS[16*k +: 16]);
                cw = |(we & mv);
            end
            wire [N-1:0] rs = rot(oh, 1);            // slot read at this edge (due next cycle)
            reg [N-1:0] rsc [0:NC-1];                // RING 2: per-chunk copies of rs
            integer c2;
            always @(*) for (c2 = 0; c2 < NC; c2 = c2 + 1) rsc[c2] = rot(ohc[c2], 1);
            reg [W-1:0] rd;
            reg         rdv;
            integer i, c1;
            always @(*) begin
                rd = {W{1'b0}}; rdv = 1'b0;
                for (i = 0; i < N; i = i + 1) begin
                    if (RING >= 2) begin
                        for (c1 = 0; c1 < W; c1 = c1 + 1) rd[c1] = rd[c1] | (m[i][c1] & rsc[c1 / CH][i]);
                    end else rd = rd | (m[i] & {W{rs[i]}});
                    rdv = rdv | (mv[i] & rs[i]);
                end
            end
            genvar j;
            for (j = 0; j < N; j = j + 1) begin : g_s
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) mv[j] <= 1'b0;
                    else if (we[j]) mv[j] <= 1'b1;
                    else if (rs[j]) mv[j] <= 1'b0;
                if (RING >= 2) begin : g_cw
                    genvar c;
                    for (c = 0; c < NC; c = c + 1) begin : g_c
                        localparam integer LO = c * CH;
                        localparam integer WC = (W - LO < CH) ? (W - LO) : CH;
                        reg wec; reg [N-1:0] rr;
                        integer k2;
                        always @(*) begin
                            wec = 1'b0;
                            for (k2 = 0; k2 < K; k2 = k2 + 1) begin
                                rr = rot(ohc[c], DEPTHS[16*k2 +: 16]);
                                if (DEPTHS[16*k2 +: 16] != 0 && v && sel[k2]) wec = wec | rr[j];
                            end
                        end
                        if (RESET_DATA != 0) begin : g_rd
                            always @(posedge clk or negedge rst_n)
                                if (!rst_n) m[j][LO +: WC] <= {WC{1'b0}}; else if (wec) m[j][LO +: WC] <= d[LO +: WC];
                        end else begin : g_nd
                            always @(posedge clk) if (wec) m[j][LO +: WC] <= d[LO +: WC];
                        end
                    end
                end else if (RESET_DATA != 0) begin : g_rd
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) m[j] <= {W{1'b0}}; else if (we[j]) m[j] <= d;
                end else begin : g_nd
                    always @(posedge clk) if (we[j]) m[j] <= d;
                end
            end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) qv <= 1'b0; else qv <= rdv;
            if (RESET_DATA != 0) begin : g_qrd
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnd
                always @(posedge clk) qr <= rd;
            end
            wire now = v && has(0, sel);
            assign vo = now || qv;
            assign q  = now ? d : qr;
            assign coll = cw || (now && qv);
            assign busy = qv || (|mv);
        end else begin : g_line
            reg [W-1:0] r  [1:DMAX];
            reg         rv [1:DMAX];
            wire [DMAX+1:1] cl;
            assign cl[DMAX+1] = 1'b0;
            genvar p;
            for (p = 1; p <= DMAX; p = p + 1) begin : g_s
                wire [W-1:0] nx  = (p == DMAX) ? {W{1'b0}} : r[(p == DMAX) ? p : p + 1];
                wire         nxv = (p == DMAX) ? 1'b0 : rv[(p == DMAX) ? p : p + 1];
                if (canbe(p)) begin : g_ld
                    wire ld = v && has(p, sel);
                    assign cl[p] = ld && nxv;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= ld || nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= ld ? d : nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= ld ? d : nx;
                    end
                end else begin : g_sh
                    assign cl[p] = 1'b0;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= nx;
                    end
                end
            end
            wire now = v && has(0, sel);
            assign vo = now || rv[1];
            assign q  = now ? d : r[1];
            assign coll = (|cl) || (now && rv[1]);
            reg any;
            integer b;
            always @(*) begin
                any = 1'b0;
                for (b = 1; b <= DMAX; b = b + 1) any = any | rv[b];
            end
            assign busy = any;
        end
    endgenerate
endmodule

// el1011-hbm-sfu 2026-10-11: one parity bank of the RING 4 timing wheel: R rows x W bits of single-port SRAM with a
// registered read port (one access per edge: ce & we write, ce & !we read; rd holds otherwise).  Synthesis maps it on
// the compiled ot_sram_1rw_64x128_m1 (R <= 64, W <= 128); simulation uses the same behaviour as a register array.
module ot_hdc_ins_ram__d4g_sfu #(parameter integer W = 64, parameter integer R = 64) (
    input  wire clk, input wire ce, input wire we, input wire [$clog2(R)-1:0] addr, input wire [W-1:0] wd,
    output wire [W-1:0] rd
);
`ifdef SYNTHESIS
    // compiled macro tools/mem_compiler: ot_sram_1rw_64x128_m1 (TT/SS/FF liberty, physical/asap7_memory_macros/)
    initial if (R > 64 || W > 128) $error("ot_hdc_ins_ram__d4g_sfu: R > 64 or W > 128");
    wire [127:0] rdx;
    ot_sram_1rw_64x128_m1 u_ram (.clk(clk), .ce_in(ce), .we_in(we), .addr_in({{(6-$clog2(R)){1'b0}}, addr}),
                                 .wd_in({{(128-W){1'b0}}, wd}), .w_mask_in({128{1'b1}}), .rd_out(rdx));
    assign rd = rdx[W-1:0];
`else
    reg [W-1:0] mem [0:R-1];
    reg [W-1:0] r;
    always @(posedge clk) if (ce) begin if (we) mem[addr] <= wd; else r <= mem[addr]; end
    assign rd = r;
`endif
endmodule

// Scoped source: rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv
`timescale 1ns/1ps
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_vec_lane__d4g_sfu.sv for the
// c12 build (MLAT 6 / ALAT 6 with rtl/hdc/ot_hdc_fastfp_lat_c12.sv), derived from the f12 lane
// (rtl/hbm_accel/su/pinned_native/ot_hdc_v41x_vec_lane_f12.sv, unchanged).  With OPR = 0, DDIV = 19, SIDEX = 0 it
// is that lane cycle for cycle at every port.  The routed failing classes of the f12 lane at 0.833 ns SS (light /
// SFU lane, 2026-10-04 v6 routes) and their fixes, every one bit-exact:
//   * memory-read outputs rd_addr / rd_re / rd_src came from a gather-select mux after the registers (-53 / -327
//     ps at the port): they are now REGISTERS whose inputs are the same mux of the next-cycle values (no cycle);
//   * operand multiplexers + control decode in front of a unit's first stage (AD -30, E1 -226 / -150, M1 divider
//     -155 ps): OPR = 1 puts an operand register between the multiplexer and the unit at M1, AD and E1
//     (+1 cycle each stage);
//   * the gather index add from the memory word (vi_q << sh + a, -45 ps; a macro output into logic): OPR = 1
//     registers vi_q first (+1 cycle on gather ops only);
//   * the divider's normalise stage (-29 ps from a register): DDIV = 21 uses the DS ROM kit's 1.2 GHz divider
//     ot_dsrom_fdiv_f12__d4g_sfu (rtl/hdc/v41x/ot_dsrom_su_f12.sv, same function, two more stages);
//   * the scalar side pipe's ports: SIDEX = 3 registers side_v / side_x here (lane 0), and the side pipe
//     (rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv) registers its input and its output: rsqrt, sqrt, sqrt(softplus)
//     and the gate are SIDEX deeper;
//   * coll is registered (OPR = 1): the controller registers order_fault from it one cycle later.
// Depths (controller rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv and the campaign model take the same parameters): fetch
// with a gather 6 + OPR, M1 OPR + (MLAT | DDIV), AD OPR + ALAT, E1 OPR + MLAT, divide DDIV, sigmoid
// exp + ALAT + DDIV, rsqrt / sqrt / sqrt(softplus) / gate + SIDEX, sqrt(softplus) exp + 11 MLAT + 10 ALAT + 31 + DDIV.
// ---------------------------------------------------------------------------
`ifndef OT_SFU_CH_PORTS
`ifdef OT_SFU_CHAIN_EXT
// el1011-hbm-sfu TWO-LEVEL (SFUT 2): the sigmoid chain is a separate die-placed tile; the lane exposes the seam
`define OT_SFU_CH_PORTS , output wire ch_rst_n, output wire ch_v, output wire ch_is_exp, output wire ch_is_sig, output wire ch_silu, output wire [31:0] ch_r, input wire [31:0] ch_y_exp, input wire [31:0] ch_y_div, input wire ch_f_e, input wire ch_f_den, input wire ch_f_div
`define OT_SFU_CH_CONN , .ch_rst_n(ch_rst_n), .ch_v(ch_v), .ch_is_exp(ch_is_exp), .ch_is_sig(ch_is_sig), .ch_silu(ch_silu), .ch_r(ch_r), .ch_y_exp(ch_y_exp), .ch_y_div(ch_y_div), .ch_f_e(ch_f_e), .ch_f_den(ch_f_den), .ch_f_div(ch_f_div)
`else
`define OT_SFU_CH_PORTS
`define OT_SFU_CH_CONN
`endif
`endif
module ot_hdc_v41x_vec_lane__d4g_sfu #(
    parameter integer AW = 24,
    parameter integer CW = 24,          // internal count width
    parameter integer LN = 3,           // log2 lanes (offset terms)
    parameter integer KIND = 0,         // 0 light, 1 SFU, 2 full (lane 0)
    parameter integer KVT_SH = 9,
    parameter integer LEAF = 0,         // 1: the broadcast tree's LAST stage is this lane's own leaf register (below)
    parameter integer MLAT = 3,         // multiplier latency (ot_hdc_qmul_lat__d4g_sfu): 3, 4, or 5 (W11 serial domain, 0.9 GHz)
    parameter integer ALAT = 3,         // FP add latency (ot_hdc_qadd_lat__d4g_sfu): 3, or 4 (input cut); ALAT <= MLAT
    parameter integer OPR = 0,          // c12: operand registers at M1 / AD / E1, vi_q register, coll register
    parameter integer DDIV = 19,        // divider depth: 19 ot_hdc_v41x_fdiv__d4g_sfu, 21 ot_dsrom_fdiv_f12__d4g_sfu (1.2 GHz kit)
    parameter integer SIDEX = 0,        // side pipe port registers: 0, 3 (side_v / side_x here, two in the side pipe),
                                        // or 4 (also side_y registered here)
    parameter integer CAPR = 0,         // c12: the memory words rd_q registered at the port before the capture logic
    // CLAUDE HBM-ABSTRACTS hub margin (2026-10-06, default off; the hub quarter lane views ot_su12_light__d4g_sfu / _sfu):
    parameter integer GSH = 0,          // 1 (with OPR 1): the gather word's shift (vi_q << sh) registered in its own
                                        // stage GS before G2's add: +1 cycle on gathers (controller fetch 6+OPR+CAPR+GSH)
    parameter integer KIMM = 0,         // 1: cx_imm3 arrives in order-key form okey(imm3) (the controller encodes it
                                        // before its control delay line): no key XOR in front of the X compares
    // CLAUDE HBM-ABSTRACTS views agent, SFU lane fail-fast (2026-10-06, default off; ot_su12_sfu__d4g_sfu eco2 SS +10.09 on
    // u_exp.y -> u_den decode stage, FF +11.87 on the u_l4 / u_num shift lines):
    parameter integer DENR = 0,         // 1: the sigmoid denominator adder's exp operand registered in front of u_den
                                        // (+1 cycle on sigmoid / SiLU: D_SIG + 1; the controller and the campaign
                                        // model take the same parameter; the side pipe's gate keeps its own depth)
    parameter integer RSTPIPE = 0,      // 1: three registered reset levels; no multicycle paths
    parameter integer SFUT = 0,         // el1011-hbm-sfu (default off): the sigmoid chain (u_exp / u_den / u_num / u_div)
                                        // as its own registered sub-tile ot_hdc_v41x_sfu_chain__d4g_sfu (pin registers in, registers
                                        // out: +2 cycles on exp / sigmoid / SiLU; controller and campaign model take it too)
    parameter integer DRING = 0         // 1: the SFU numerator delay (u_num) and the S insertion line (u_l4) as ring
                                        // buffers (write slot / read slot one-hot, no flop-to-flop shift chain); same
                                        // words, same cycles
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [10:0]       lane_id,   // this lane's index in the unit (a constant at every instance)
    // ---- offsets of an op being set up: lane l's offset is the sum of c[k] over the set bits k of l
    input  wire              ld,
    input  wire              ld_bank,
    input  wire [5*LN*AW-1:0] ld_c,     // stream s (A, B, C, D, O), term k: [(s*LN + k)*AW +: AW]
    // ---- emit (E): the controller's vector position and the active op's fields
    input  wire              emit,
    input  wire              bank,
    input  wire [CW-1:0]     o_v, i_v, no, ni,
    input  wire [3:0]        ls,        // log2 slot size S
    input  wire [3:0]        lvw,       // log2 of the lanes in use: slot size x slots a vector
    input  wire [5*AW-1:0]   vb,        // vector base of A, B, C, D, O
    input  wire [AW-1:0]     krow,      // transposed-KV row of the vector's first lane
    input  wire [AW-1:0]     obase,     // transposed-KV base
    input  wire [AW-1:0]     aibase,
    input  wire [1:0]        aind,
    input  wire [4:0]        gsh,       // gather: index << gsh
    input  wire              cpair,
    input  wire [1:0]        dst,
    input  wire [7:0]        srcs,      // {dsrc, csrc, bsrc, asrc}
    // ---- memories
    output reg               vi_re,
    output reg  [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    output wire [4*AW-1:0]   rd_addr,   // {D, C, B, A}
    output wire [3:0]        rd_re,
    output wire [7:0]        rd_src,    // per stream: vector memory, constant ROM lo / hi, BF16 weight ROM
    input  wire [4*32-1:0]   rd_q,      // the selected source's word (the weight ROM's BF16 in the top half)
    // ---- per-stage control from the control pipe
    input  wire [7:0]        cx_srcs,                  // at X
    input  wire              cx_arnd, cx_arelu, cx_amin, cx_cclip,
    input  wire [31:0]       cx_imm3,
    input  wire [2:0]        cp_m1,                    // at PRE (M1 inputs)
    input  wire [31:0]       cp_imm1,
    input  wire [2:0]        cm_m1,                    // at M1 out
    input  wire [1:0]        cm_m2,
    input  wire [2:0]        cm_qm,
    input  wire [31:0]       cm_imm1,
    input  wire [2:0]        ca_ad,                    // at AD in
    input  wire [31:0]       ca_imm2,
    input  wire [2:0]        ci_sfu,                   // at S in
    input  wire [2:0]        cs_sfu,                   // at S out
    input  wire [2:0]        cs_e1,
    input  wire [31:0]       cs_imm2,
    input  wire [1:0]        ce_e2,                    // at E2 in
    input  wire [31:0]       ce_imm1,
    input  wire              co_rnd,                   // at OUT in
    input  wire [1:0]        co_dst,
    // ---- scalar side pipe (lane 0)
    output wire              side_v,
    output wire [31:0]       side_x,
    input  wire [31:0]       side_y,                   // the side function's result, at S out
    // ---- writes and the reducer
    output reg               vm_we,
    output reg  [AW-1:0]     vm_waddr,
    output reg  [31:0]       vm_wdata,
    output reg               kv_we,
    output reg  [AW-1:0]     kv_waddr,
    output reg  [31:0]       kv_wdata,
    output wire              ro_v,                     // live element at OUT (with vm_we timing)
    output wire [31:0]       ro_x,
    output wire              fault,
    output wire              coll
    `OT_SFU_CH_PORTS
);
    /* verilator no_inline_module */
    localparam [1:0] SRC_VM = 0, SRC_CLO = 1, SRC_CHI = 2, SRC_WROM = 3;
    localparam [1:0] IND_NONE = 0, IND_I = 1, IND_O = 2;
    localparam [1:0] DST_NONE = 0, DST_VM = 1, DST_KV = 2, DST_KVT = 3;
    localparam [2:0] M1_BYP = 0, M1_AB = 1, M1_AA = 2, M1_AIMM = 3, M1_DIVB = 4, M1_DIVIMM = 5, M1_MAXB = 6;
    localparam [1:0] M2_BYP = 0, M2_C = 1, M2_IMM = 2;
    localparam [2:0] QM_OFF = 0, QM_POS = 1, QM_NEG = 2, QM_ALT_NP = 3, QM_ALT_PN = 4;
    localparam [2:0] AD_BYP = 0, AD_Q = 1, AD_C = 2, AD_NEGB = 3, AD_IMM = 4, AD_D = 5;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SIGM = 4, SFU_SILU = 5,
                     SFU_SPSQRT = 6, SFU_EGATE = 7;
    localparam [2:0] E1_BYP = 0, E1_MULC = 1, E1_ADDC = 2, E1_MULIMM = 3, E1_ADDIMM = 4;
    localparam [1:0] E2_BYP = 0, E2_MULB = 1, E2_MULIMM = 2;
    // stage depths; MLAT = 4 lengthens every multiplying stage by one (M1 / M2 / E1 / E2: 4) and the SFU chains
    localparam integer D_DIV = DDIV, D_EXP = 7 * MLAT + 8 * ALAT + 4, D_SIG0 = D_EXP + ALAT + D_DIV;  // 49, 71
    localparam integer D_SIG = D_SIG0 + DENR + 2 * SFUT;
    localparam integer D_EXPL = D_EXP + 2 * SFUT;            // exp as the lane sees it (sub-tile seams)
    localparam integer D_RSQ = 1 + 9 * MLAT + 3 * ALAT + SIDEX, D_SQRT = 31 + SIDEX;                // 37
    localparam integer D_SP = D_EXP + 11 * MLAT + 10 * ALAT + 31 + D_DIV + SIDEX;                    // 162
    localparam integer D_EG = 1 + 31 + 1 + D_SIG0 + SIDEX;                               // 104 (111): side pipe sigmoid
    // MLAT >= 4 is the serial-domain build: its integer adds and compares are keep-prefix adders
    // (ot_hdc_kadd__d4g_sfu / _kge / _kinc over rtl/hdc/ot_hdc_prefix.sv) and its FP adds ot_hdc_fp32_add_lat3__d4g_sfu, so ABC
    // cannot re-ripple them inside the lane; MLAT = 3 keeps the behavioural operators (the unit as it was)
    localparam integer K = (MLAT != 3 || ALAT != 3) ? 1 : 0;
    // Reset admission costs three clocks. All leaves assert/release together.
    // The pin register feeds 8 banks, each bank at most 8 consumer leaves.
    wire [52:0] local_rst_n;
    generate if (RSTPIPE != 0) begin : g_reset_tree
        (* keep, dont_touch *) reg pin_q;
        (* keep, dont_touch *) reg [7:0] bank_q;
        (* keep, dont_touch *) reg [52:0] leaf_q;
        always @(posedge clk) pin_q <= rst_n;
        genvar rb;
        for (rb=0; rb<8; rb=rb+1) begin : g_bank
            always @(posedge clk) bank_q[rb] <= pin_q;
        end
        genvar rl;
        for (rl=0; rl<53; rl=rl+1) begin : g_leaf
            always @(posedge clk) leaf_q[rl] <= bank_q[rl/8];
        end
        assign local_rst_n = leaf_q;
    end else begin : g_reset_direct
        assign local_rst_n = {53{rst_n}};
    end endgenerate
    generate if ((OPR != 0 && OPR != 1) || (DDIV != 19 && DDIV != 21 && DDIV != 31) || (SIDEX != 0 && SIDEX != 3 && SIDEX != 4) || (CAPR != 0 && CAPR != 1))
        begin : g_bad_c12
        ot_hdc_v41x_vec_lane_c12_OPR_0_1_DDIV_19_21_SIDEX_0_3 u_trap ();
    end endgenerate
    generate if (ALAT > MLAT || ALAT < 3 || ALAT > 7) begin : g_bad_alat
        ot_hdc_v41x_vec_lane_ALAT_must_be_3_to_7_and_at_most_MLAT u_trap ();
    end endgenerate
    localparam [15:0] H1_DIV = D_DIV + OPR, H1_M = MLAT + OPR;      // the M1 line: operand register + unit
    localparam [15:0] H_DIV = D_DIV, H_M = MLAT, H_EXP = D_EXPL, H_SIG = D_SIG, H_RSQ = D_RSQ, H_SQRT = D_SQRT,
                      H_SP = D_SP, H_EG = D_EG;
    localparam integer HAS_SFU = (KIND != 0);
    localparam integer FULL = (KIND == 2);

    function automatic [31:0] bf16(input [31:0] x);
        bf16 = (x + 32'h7FFF + {31'd0, x[16]}) & 32'hFFFF0000;
    endfunction
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic [31:0] fmin(input [31:0] a, input [31:0] b);
        fmin = (okey(a) <= okey(b)) ? a : b;
    endfunction
    function automatic [31:0] fmax(input [31:0] a, input [31:0] b);
        fmax = (okey(a) >= okey(b)) ? a : b;
    endfunction
    // relu then min: the two compares (v and +0 against imm) run side by side
    function automatic [31:0] pre_a(input [31:0] v, input relu, input amin, input [31:0] imm);
        reg zero, le_v, le_0;
        begin
            zero = relu && v[31];
            le_v = okey(v) <= okey(imm);
            le_0 = okey(32'd0) <= okey(imm);
            pre_a = !amin ? (zero ? 32'd0 : v) : zero ? (le_0 ? 32'd0 : imm) : (le_v ? v : imm);
        end
    endfunction

    // pre_a with its two compares supplied (le_v: okey(v) <= okey(imm), le_0: okey(+0) <= okey(imm))
    function automatic [31:0] pre_a2(input [31:0] v, input relu, input amin, input [31:0] imm, input le_v, input le_0);
        reg zero;
        begin
            zero = relu && v[31];
            pre_a2 = !amin ? (zero ? 32'd0 : v) : zero ? (le_0 ? 32'd0 : imm) : (le_v ? v : imm);
        end
    endfunction

    // ---- LEAF: the broadcast's last register stage --------------------------------------------------
    // LEAF = 0: the lane uses its inputs as they arrive (the controller's broadcast register, or the tree's
    // leaf outside the lane).  LEAF = 1 (ot_hdc_v41x_vec with BCAST_STAGES > 0): the tree's last stage is
    // this lane's own register, and it holds the lane-local partials of the vector instead of the raw
    // fields: the position (o_v + d_o, i_v + d_i), the transposed-KV row (krow + d_o), whether the lane is in
    // use, and the four stream addresses and the output address (vector base + this lane's offset).  F0 is
    // then one add / compare level (the liveness compares, the transposed-KV address, the gather index
    // address) instead of two adds feeding a three-input add.  Same cycle, same values: bit-exact.
    // Cost: 8 x 24-bit partials + 1 in-use bit, plus the fields F0 still reads (emit, no, ni, obase,
    // aibase, aind, gsh, cpair, dst, srcs: 115 bits): 308 flops a lane, plus the three-cycle offset load
    // below (604).  The offset load does not pass the leaf: it starts from the tree's stage (ld, ld_bank,
    // ld_c), where the lane without a leaf would have loaded in one cycle.
    reg [AW-1:0] off0 [0:4];
    reg [AW-1:0] off1 [0:4];
    wire [CW-1:0] lid = {{(CW-11){1'b0}}, lane_id};
    //: slot (outer) and in-slot (inner) offsets of this lane for a slot size 2^ls
    wire [CW-1:0] d_o = lid >> ls;
    wire [CW-1:0] d_i = lid & ((1 << ls) - 1);
    wire [CW-1:0] ol_c, il_c;
    wire [AW-1:0] row_c;
    wire [2:0]    unused_c0;
    ot_hdc_kadd__d4g_sfu #(.W(CW), .K(K)) u_olc (.a(o_v), .b(d_o), .cin(1'b0), .s(ol_c), .cout(unused_c0[0]));
    ot_hdc_kadd__d4g_sfu #(.W(CW), .K(K)) u_ilc (.a(i_v), .b(d_i), .cin(1'b0), .s(il_c), .cout(unused_c0[1]));
    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(K)) u_rwc (.a(krow), .b(d_o[AW-1:0]), .cin(1'b0), .s(row_c), .cout(unused_c0[2]));
    wire          lin_c = (lid < (1 << lvw));
    wire [5*AW-1:0] sum_c;
    genvar gs;
    generate for (gs = 0; gs < 5; gs = gs + 1) begin : g_sum
        wire unused_cs;
        ot_hdc_kadd__d4g_sfu #(.W(AW), .K(K)) u_s (.a(vb[gs*AW +: AW]), .b(bank ? off1[gs] : off0[gs]), .cin(1'b0),
                                          .s(sum_c[gs*AW +: AW]), .cout(unused_cs));
    end endgenerate
    // what F0 and the offset bank read: the partials and fields at the leaf
    wire             emit_e, ld_e, ldbank_e, lin_e, cpair_e;
    wire [CW-1:0]    ol_e, il_e, no_e, ni_e;
    wire [AW-1:0]    row_e, obase_e, aibase_e;
    wire [5*AW-1:0]  sum_e;
    wire [1:0]       aind_e, dst_e;
    wire [4:0]       gsh_e;
    wire [7:0]       srcs_e;
    wire [5*LN*AW-1:0] ldc_e;
    generate if (LEAF == 0) begin : g_noleaf
        assign {emit_e, ld_e, ldbank_e, ldc_e} = {emit, ld, ld_bank, ld_c};
        assign {ol_e, il_e, row_e, lin_e, sum_e} = {ol_c, il_c, row_c, lin_c, sum_c};
        assign {no_e, ni_e, obase_e, aibase_e, aind_e, dst_e, gsh_e, srcs_e, cpair_e} =
               {no, ni, obase, aibase, aind, dst, gsh, srcs, cpair};
    end else begin : g_leaf
        reg              r_emit;
        reg              r_lin, r_cpair;
        reg [CW-1:0]     r_ol, r_il, r_no, r_ni;
        reg [AW-1:0]     r_row, r_obase, r_aibase;
        reg [5*AW-1:0]   r_sum;
        reg [1:0]        r_aind, r_dst;
        reg [4:0]        r_gsh;
        reg [7:0]        r_srcs;
        always @(posedge clk or negedge local_rst_n[0]) begin
            if (!local_rst_n[0]) r_emit <= 1'b0;
            else r_emit <= emit;
        end
        always @(posedge clk) begin
            r_ol <= ol_c; r_il <= il_c; r_row <= row_c; r_lin <= lin_c; r_sum <= sum_c;
            r_no <= no; r_ni <= ni; r_obase <= obase; r_aibase <= aibase; r_aind <= aind; r_dst <= dst;
            r_gsh <= gsh; r_srcs <= srcs; r_cpair <= cpair;
        end
        assign emit_e = r_emit;
        assign {ld_e, ldbank_e, ldc_e} = {ld, ld_bank, ld_c};
        assign {ol_e, il_e, row_e, lin_e, sum_e} = {r_ol, r_il, r_row, r_lin, r_sum};
        assign {no_e, ni_e, obase_e, aibase_e, aind_e, dst_e, gsh_e, srcs_e, cpair_e} =
               {r_no, r_ni, r_obase, r_aibase, r_aind, r_dst, r_gsh, r_srcs, r_cpair};
    end endgenerate

    // ---- offsets: two banks, loaded by the op set-up --------------------------------------------
    // A lane's offset is the sum of the terms of its lane_id's set bits (LN terms).  LEAF = 0: in one cycle.
    // LEAF = 1: over THREE (W11 serial domain; the two-cycle form summed 5 terms in its first cycle and was
    // the routed lane's worst path at 1.111 ns SS): cycle 1 sums the terms in three groups (bits [0, G1),
    // [G1, G2), [G2, LN): at most ceil(LN/3) = 4 terms at LN = 10) and registers the three partials; cycle 2
    // adds the first two; cycle 3 adds the third into the bank.  Integer sums mod 2^AW: the same offsets.
    // Timing (ld_e is the tree stage's ld, one cycle before the leaf; the controller loads in the cycle
    // before the op may promote, so its first vector reaches the tree stage >= 3 cycles after ld_e): the bank
    // is written at the end of ld_e + 2 and read by the leaf's sums from ld_e + 3 on, so it lands in the
    // cycle before its first use (the two-cycle load landed one cycle earlier).  The op two back (same bank)
    // emitted its last vector >= 3 cycles before the load left the controller, so it read the bank >= 4
    // cycles before the write.  Cost 5 x 5 x AW + 4 flops (604; was 5 x 2 x AW + 2 = 242).
    localparam integer G1 = (LN + 2) / 3, G2 = 2 * ((LN + 2) / 3);
    generate if (LEAF == 0) begin : g_ld1
        integer s, k;
        reg [AW-1:0] acc;
        always @(posedge clk) begin
            if (ld_e) begin
                for (s = 0; s < 5; s = s + 1) begin
                    acc = {AW{1'b0}};
                    for (k = 0; k < LN; k = k + 1)
                        if (lane_id[k]) acc = acc + ldc_e[(s*LN + k)*AW +: AW];
                    if (ldbank_e) off1[s] <= acc; else off0[s] <= acc;
                end
            end
        end
    end else if (K == 0) begin : g_ld3
        integer s, k;
        reg [AW-1:0] g0, g1, g2;
        reg          ldp_v, ldq_v, ldp_bank, ldq_bank;
        reg [AW-1:0] ldp_0 [0:4];
        reg [AW-1:0] ldp_1 [0:4];
        reg [AW-1:0] ldp_2 [0:4];
        reg [AW-1:0] ldq_01 [0:4];
        reg [AW-1:0] ldq_2 [0:4];
        always @(posedge clk or negedge local_rst_n[1]) begin
            if (!local_rst_n[1]) begin ldp_v <= 1'b0; ldq_v <= 1'b0; end
            else begin ldp_v <= ld_e; ldq_v <= ldp_v; end
        end
        always @(posedge clk) begin
            if (ld_e) begin
                ldp_bank <= ldbank_e;
                for (s = 0; s < 5; s = s + 1) begin
                    g0 = {AW{1'b0}};
                    g1 = {AW{1'b0}};
                    g2 = {AW{1'b0}};
                    for (k = 0; k < LN; k = k + 1)
                        if (lane_id[k]) begin
                            if (k < G1)      g0 = g0 + ldc_e[(s*LN + k)*AW +: AW];
                            else if (k < G2) g1 = g1 + ldc_e[(s*LN + k)*AW +: AW];
                            else             g2 = g2 + ldc_e[(s*LN + k)*AW +: AW];
                        end
                    ldp_0[s] <= g0;
                    ldp_1[s] <= g1;
                    ldp_2[s] <= g2;
                end
            end
            if (ldp_v) begin
                ldq_bank <= ldp_bank;
                for (s = 0; s < 5; s = s + 1) begin
                    ldq_01[s] <= ldp_0[s] + ldp_1[s];
                    ldq_2[s] <= ldp_2[s];
                end
            end
            if (ldq_v)
                for (s = 0; s < 5; s = s + 1)
                    if (ldq_bank) off1[s] <= ldq_01[s] + ldq_2[s]; else off0[s] <= ldq_01[s] + ldq_2[s];
        end
    end else begin : g_ld3k
        // the same three cycles on keep-prefix adders: a group's (at most 4) masked terms in a two-level tree
        reg          ldp_v, ldq_v, ldp_bank, ldq_bank;
        always @(posedge clk or negedge local_rst_n[2]) begin
            if (!local_rst_n[2]) begin ldp_v <= 1'b0; ldq_v <= 1'b0; end
            else begin ldp_v <= ld_e; ldq_v <= ldp_v; end
        end
        always @(posedge clk) begin
            if (ld_e) ldp_bank <= ldbank_e;
            if (ldp_v) ldq_bank <= ldp_bank;
        end
        genvar ss, jj, kk;
        wire [5*AW-1:0] s_bus;                         // stream ss's offset, at the third cycle
        integer s;
        always @(posedge clk)
            if (ldq_v)
                for (s = 0; s < 5; s = s + 1)
                    if (ldq_bank) off1[s] <= s_bus[s*AW +: AW]; else off0[s] <= s_bus[s*AW +: AW];
        for (ss = 0; ss < 5; ss = ss + 1) begin : g_s
            wire [3*AW-1:0] grp;                       // the three group sums of stream ss
            for (jj = 0; jj < 3; jj = jj + 1) begin : g_j
                localparam integer LO = (jj == 0) ? 0 : (jj == 1) ? G1 : G2;
                localparam integer HI = (jj == 0) ? G1 : (jj == 1) ? G2 : LN;
                wire [4*AW-1:0] t;                     // the group's masked terms, zero-padded to 4
                for (kk = 0; kk < 4; kk = kk + 1) begin : g_t
                    if (LO + kk < HI) begin : g_on
                        assign t[kk*AW +: AW] = lane_id[LO + kk] ? ldc_e[(ss*LN + LO + kk)*AW +: AW] : {AW{1'b0}};
                    end else begin : g_off
                        assign t[kk*AW +: AW] = {AW{1'b0}};
                    end
                end
                wire [AW-1:0] s01, s23;
                wire [2:0]    unused_c;
                if (HI - LO > 2) begin : g_4
                    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(1)) u_a (.a(t[0 +: AW]), .b(t[AW +: AW]), .cin(1'b0), .s(s01), .cout(unused_c[0]));
                    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(1)) u_b (.a(t[2*AW +: AW]), .b(t[3*AW +: AW]), .cin(1'b0), .s(s23), .cout(unused_c[1]));
                    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(1)) u_c (.a(s01), .b(s23), .cin(1'b0), .s(grp[jj*AW +: AW]), .cout(unused_c[2]));
                end else if (HI - LO == 2) begin : g_2
                    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(1)) u_a (.a(t[0 +: AW]), .b(t[AW +: AW]), .cin(1'b0), .s(grp[jj*AW +: AW]), .cout(unused_c[0]));
                    assign {s01, s23, unused_c[2:1]} = 0;
                end else begin : g_1
                    assign grp[jj*AW +: AW] = t[0 +: AW];
                    assign {s01, s23, unused_c} = 0;
                end
            end
            reg  [AW-1:0] p0, p1, p2, q01, q2;
            wire [AW-1:0] s_01, s_all;
            wire [1:0]    unused_q;
            ot_hdc_kadd__d4g_sfu #(.W(AW), .K(1)) u_q (.a(p0), .b(p1), .cin(1'b0), .s(s_01), .cout(unused_q[0]));
            ot_hdc_kadd__d4g_sfu #(.W(AW), .K(1)) u_o (.a(q01), .b(q2), .cin(1'b0), .s(s_all), .cout(unused_q[1]));
            assign s_bus[ss*AW +: AW] = s_all;
            always @(posedge clk) begin
                if (ld_e) begin p0 <= grp[0 +: AW]; p1 <= grp[AW +: AW]; p2 <= grp[2*AW +: AW]; end
                if (ldp_v) begin q01 <= s_01; q2 <= p2; end
            end
        end
    end endgenerate

    // ---- F0: liveness, addresses ------------------------------------------------------------------
    wire ol_ge, il_ge;
    ot_hdc_kge__d4g_sfu #(.W(CW), .K(K)) u_olg (.a(ol_e), .b(no_e), .ge(ol_ge));
    ot_hdc_kge__d4g_sfu #(.W(CW), .K(K)) u_ilg (.a(il_e), .b(ni_e), .ge(il_ge));
    wire live0 = emit_e && lin_e && !ol_ge && !il_ge;
    // (il << 4) + row[3:0] is the concatenation {il, row[3:0]}
    wire [AW-1:0] kvt, kvt1, vi_sum;
    wire [2:0]    unused_c1;
    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(K)) u_kv1 (.a(obase_e), .b((row_e >> 4) << KVT_SH), .cin(1'b0), .s(kvt1), .cout(unused_c1[0]));
    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(K)) u_kv2 (.a(kvt1), .b({il_e[AW-5:0], row_e[3:0]}), .cin(1'b0), .s(kvt), .cout(unused_c1[1]));
    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(K)) u_via (.a(aibase_e), .b((aind_e == IND_I) ? il_e[AW-1:0] : ol_e[AW-1:0]), .cin(1'b0),
                                        .s(vi_sum), .cout(unused_c1[2]));
    reg          f_v, f_g, f_par;
    reg [AW-1:0] f_a, f_b, f_c, f_d, f_o;
    reg [7:0]    f_src;
    reg          f_cpair;
    always @(posedge clk or negedge local_rst_n[3]) begin
        if (!local_rst_n[3]) begin f_v <= 1'b0; vi_re <= 1'b0; end
        else begin f_v <= live0; vi_re <= live0 && (aind_e != IND_NONE); end
    end
    always @(posedge clk) begin
        f_g <= (aind_e != IND_NONE);
        f_a <= sum_e[0 +: AW];
        f_b <= sum_e[AW +: AW];
        f_c <= sum_e[2*AW +: AW];
        f_d <= sum_e[3*AW +: AW];
        f_o <= (dst_e == DST_KVT) ? kvt : sum_e[4*AW +: AW];
        f_par <= il_e[0];
        f_src <= srcs_e;
        f_cpair <= cpair_e;
        vi_addr <= vi_sum;
    end
    // ---- G1, G2: a gathered A (index from the vector memory, scaled by a power of two) ---------------
    // c12 (OPR = 1): the memory word vi_q is registered first (GQ), so G2's add starts from registers: one
    // more cycle for a gather (the controller's gather fetch is 6 + OPR)
    reg          g1_v, g2_v, g1_par, g2_par, g1_cpair, g2_cpair;
    reg [AW-1:0] g1_a, g1_b, g1_c, g1_d, g1_o, g2_a, g2_b, g2_c, g2_d, g2_o;
    reg [7:0]    g1_src, g2_src;
    reg [4:0]    g1_sh;
    always @(posedge clk or negedge local_rst_n[4]) begin
        if (!local_rst_n[4]) g1_v <= 1'b0;
        else g1_v <= f_v && f_g;
    end
    reg [4:0] f_sh;
    always @(posedge clk) f_sh <= gsh_e;
    always @(posedge clk) begin
        g1_a <= f_a; g1_b <= f_b; g1_c <= f_c; g1_d <= f_d; g1_o <= f_o; g1_par <= f_par; g1_src <= f_src;
        g1_cpair <= f_cpair; g1_sh <= f_sh;
    end
    // h_*: the stage G2 adds from (G1, or GQ with the registered memory word)
    wire          h_v, h_par, h_cpair;
    wire [AW-1:0] h_a, h_b, h_c, h_d, h_o;
    wire [7:0]    h_src;
    wire [AW-1:0] h_qs;                  // the gather word shifted by the op's scale (h_q << h_sh)
    generate if (OPR != 0) begin : g_gq
        reg          q_v, q_par, q_cpair;
        reg [AW-1:0] q_a, q_b, q_c, q_d, q_o;
        reg [7:0]    q_src;
        reg [4:0]    q_sh;
        reg [31:0]   q_q;
        always @(posedge clk or negedge local_rst_n[5]) begin
            if (!local_rst_n[5]) q_v <= 1'b0; else q_v <= g1_v;
        end
        always @(posedge clk) begin
            q_a <= g1_a; q_b <= g1_b; q_c <= g1_c; q_d <= g1_d; q_o <= g1_o; q_par <= g1_par; q_src <= g1_src;
            q_cpair <= g1_cpair; q_sh <= g1_sh; q_q <= vi_q;
        end
        if (GSH != 0) begin : g_gs
            // GS: the shifted gather word registered (q_q << q_sh), every other field one stage later
            reg          s_v, s_par, s_cpair;
            reg [AW-1:0] s_a, s_b, s_c, s_d, s_o, s_qs;
            reg [7:0]    s_src;
            always @(posedge clk or negedge local_rst_n[6]) begin
                if (!local_rst_n[6]) s_v <= 1'b0; else s_v <= q_v;
            end
            always @(posedge clk) begin
                s_a <= q_a; s_b <= q_b; s_c <= q_c; s_d <= q_d; s_o <= q_o; s_par <= q_par; s_src <= q_src;
                s_cpair <= q_cpair; s_qs <= q_q[AW-1:0] << q_sh;
            end
            assign {h_v, h_par, h_cpair, h_a, h_b, h_c, h_d, h_o, h_src} = {s_v, s_par, s_cpair, s_a, s_b, s_c, s_d, s_o, s_src};
            assign h_qs = s_qs;
        end else begin : g_gs0
            assign {h_v, h_par, h_cpair, h_a, h_b, h_c, h_d, h_o, h_src} = {q_v, q_par, q_cpair, q_a, q_b, q_c, q_d, q_o, q_src};
            assign h_qs = q_q[AW-1:0] << q_sh;
        end
    end else begin : g_gq0
        assign {h_v, h_par, h_cpair, h_a, h_b, h_c, h_d, h_o, h_src} =
               {g1_v, g1_par, g1_cpair, g1_a, g1_b, g1_c, g1_d, g1_o, g1_src};
        assign h_qs = vi_q[AW-1:0] << g1_sh;
    end endgenerate
    wire [AW-1:0] g2_sum;
    wire          unused_c2;
    ot_hdc_kadd__d4g_sfu #(.W(AW), .K(K)) u_g2a (.a(h_a), .b(h_qs), .cin(1'b0), .s(g2_sum), .cout(unused_c2));
    always @(posedge clk or negedge local_rst_n[7]) begin
        if (!local_rst_n[7]) g2_v <= 1'b0;
        else g2_v <= h_v;
    end
    always @(posedge clk) begin
        g2_a <= g2_sum;
        g2_b <= h_b; g2_c <= h_c; g2_d <= h_d; g2_o <= h_o; g2_par <= h_par; g2_src <= h_src;
        g2_cpair <= h_cpair;
    end
    // ---- memory reads: the F0 vector, or a gather vector two (OPR: three) cycles later ------------------
    // c12: rd_addr / rd_re / rd_src are registers loaded with the same selection of the NEXT cycle's G2 / F0
    // values (g2_* <= h_*, f_* <= the F0 inputs), so the port carries exactly the old combinational value of
    // every cycle and no logic sits between the registers and the memories
    wire          mr_nv = f_v && !f_g;
    wire          mr_v  = mr_nv || g2_v;
    wire          n_mrv = (live0 && (aind_e == IND_NONE)) || h_v;
    wire [AW-1:0] n_a   = h_v ? g2_sum : sum_e[0 +: AW];
    wire [AW-1:0] n_c   = (h_v ? h_cpair : cpair_e) ? (n_a ^ {{(AW-1){1'b0}}, 1'b1}) : (h_v ? h_c : sum_e[2*AW +: AW]);
    reg  [4*AW-1:0] rd_addr_r;
    reg  [3:0]      rd_re_r;
    reg  [7:0]      rd_src_r;
    always @(posedge clk or negedge local_rst_n[8]) begin
        if (!local_rst_n[8]) rd_re_r <= 4'd0; else rd_re_r <= {4{n_mrv}};
    end
    always @(posedge clk) begin
        rd_addr_r <= {h_v ? h_d : sum_e[3*AW +: AW], n_c, h_v ? h_b : sum_e[AW +: AW], n_a};
        rd_src_r <= h_v ? h_src : srcs_e;
    end
    assign rd_addr = rd_addr_r;
    assign rd_re = rd_re_r;
    assign rd_src = rd_src_r;
    // tags of the read, to the capture two cycles later (CAPR: three)
    reg          m_v, x_v;
    reg [AW-1:0] m_o, x_o;
    reg          m_par, x_par;
    wire         c_v, c_par;
    wire [AW-1:0] c_o;
    wire [127:0] rq;                    // the memory words as the capture logic sees them
    generate if (CAPR != 0) begin : g_capr
        // c12: the words are registered at the port (a memory-macro boundary); the capture logic below starts
        // from this register, one cycle later for every element (the controller's fetch is CAPR deeper)
        reg          cr_v, cr_par;
        reg [AW-1:0] cr_o;
        reg [127:0]  cr_q;
        always @(posedge clk or negedge local_rst_n[9]) begin
            if (!local_rst_n[9]) cr_v <= 1'b0; else cr_v <= m_v;
        end
        always @(posedge clk) begin cr_o <= m_o; cr_par <= m_par; cr_q <= rd_q; end
        assign {c_v, c_o, c_par, rq} = {cr_v, cr_o, cr_par, cr_q};
    end else begin : g_capw
        assign {c_v, c_o, c_par, rq} = {m_v, m_o, m_par, rd_q};
    end endgenerate
    always @(posedge clk or negedge local_rst_n[10]) begin
        if (!local_rst_n[10]) begin m_v <= 1'b0; x_v <= 1'b0; end
        else begin m_v <= mr_v; x_v <= c_v; end
    end
    always @(posedge clk) begin
        m_o <= g2_v ? g2_o : f_o; m_par <= g2_v ? g2_par : f_par;
        x_o <= c_o; x_par <= c_par;
    end
    // ---- X: capture (the memories answered during the cycle before) --------------------------------------
    reg [31:0] x_a, x_b, x_c, x_d;
    always @(posedge clk) begin
        x_a <= rq[31:0]; x_b <= rq[63:32]; x_c <= rq[95:64]; x_d <= rq[127:96];
    end
    // ---- PRE ------------------------------------------------------------------------------------------
    // A' = min(relu(rnd?(A)), imm3), evaluated for the three values rnd?(A) can take (A itself, A truncated to
    // BF16, and truncated + one BF16 ulp) side by side and selected by the rounding decision, so no compare
    // waits for the rounding carry (bit-identical for all inputs: tools/w11_equiv_clip.ys; W11 timing fix)
    wire [31:0] a_t  = {x_a[31:16], 16'd0};
    // hbm-fmax-su: A's BF16 round-up candidate and decision are formed at the capture from the word being captured
    // and registered beside x_a (same values one stage earlier; the PRE stage was 45 ps over 0.833 ns with them in it)
    wire [31:0] xa_in = rq[31:0];
    wire [15:0] xa_hi1;
    ot_hdc_kinc__d4g_sfu #(.W(16), .K(K)) u_au (.a(xa_in[31:16]), .inc(1'b1), .y(xa_hi1));
    reg  [15:0] a_hi1;
    reg         a_up;
    always @(posedge clk) begin
        a_hi1 <= xa_hi1;
        a_up <= xa_in[15] & ((|xa_in[14:0]) | xa_in[16]);
    end
    wire [31:0] a_u  = {a_hi1, 16'd0};
    // pre_a's compares, as prefix compares: okey(v) <= okey(imm3) for the three candidates, and +0 <= imm3
    // KIMM: cx_imm3 is already the order key; imm3's value is its inverse (off the compare path)
    wire [31:0] k_imm3 = (KIMM != 0) ? cx_imm3 : okey(cx_imm3);
    wire [31:0] v_imm3 = (KIMM != 0) ? (cx_imm3[31] ? {1'b0, cx_imm3[30:0]} : ~cx_imm3) : cx_imm3;
    wire        le_x, le_t, le_u, le_0;
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_lex (.a(k_imm3), .b(okey(x_a)), .ge(le_x));
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_let (.a(k_imm3), .b(okey(a_t)), .ge(le_t));
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_leu (.a(k_imm3), .b(okey(a_u)), .ge(le_u));
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_le0 (.a(k_imm3), .b(32'h80000000), .ge(le_0));
    wire [31:0] a_mx = pre_a2(x_a, cx_arelu, cx_amin, v_imm3, le_x, le_0);
    wire [31:0] a_mt = pre_a2(a_t, cx_arelu, cx_amin, v_imm3, le_t, le_0);
    wire [31:0] a_mu = pre_a2(a_u, cx_arelu, cx_amin, v_imm3, le_u, le_0);
    wire [31:0] a_m  = !cx_arnd ? a_mx : a_up ? a_mu : a_mt;
    // clip(C, -imm3, imm3) = fmin(fmax(C, lo), hi) with its three comparisons side by side (bit-identical,
    // ties included: proven by tools/w11_equiv_clip.ys; the chained form was the lane's critical path, W11)
    wire [31:0] c_lo = {1'b1, v_imm3[30:0]};
    wire        c_ge_lo, c_le_hi, c_lohi;
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_cgl (.a(okey(x_c)), .b(okey(c_lo)), .ge(c_ge_lo));
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_clh (.a(k_imm3), .b(okey(x_c)), .ge(c_le_hi));
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_clo (.a(k_imm3), .b(okey(c_lo)), .ge(c_lohi));
    wire [31:0] c_m = !cx_cclip ? x_c : c_ge_lo ? (c_le_hi ? x_c : v_imm3) : (c_lohi ? c_lo : v_imm3);
    reg  [31:0] p_a, p_b, p_c, p_d;
    reg  [AW-1:0] p_o;
    reg         p_v, p_par;
    always @(posedge clk or negedge local_rst_n[11]) begin
        if (!local_rst_n[11]) p_v <= 1'b0; else p_v <= x_v;
    end
    always @(posedge clk) begin
        p_a <= a_m; p_b <= x_b; p_c <= c_m; p_d <= x_d; p_o <= x_o; p_par <= x_par;
    end
    // ---- M1 ---------------------------------------------------------------------------------------------
    wire p_mul = (cp_m1 == M1_AB) || (cp_m1 == M1_AA) || (cp_m1 == M1_AIMM);
    wire p_div = (cp_m1 == M1_DIVB) || (cp_m1 == M1_DIVIMM);
    wire [31:0] mul1_y, byp1;
    wire f_m1;
    // c12 (OPR = 1): the operand register between M1's multiplexers and its units
    wire [31:0] m1_bm = (cp_m1 == M1_AB) ? p_b : (cp_m1 == M1_AA) ? p_a : cp_imm1;
    wire [31:0] m1_bd = (cp_m1 == M1_DIVB) ? p_b : cp_imm1;
    wire        o_mul, o_div;
    wire [31:0] o_a, o_bm, o_bd;
    generate if (OPR != 0) begin : g_m1r
        reg rm, rdv;
        reg [31:0] ra, rbm, rbd;
        always @(posedge clk or negedge local_rst_n[12]) begin
            if (!local_rst_n[12]) begin rm <= 1'b0; rdv <= 1'b0; end
            else begin rm <= p_v && p_mul; rdv <= p_v && p_div; end
        end
        always @(posedge clk) begin ra <= p_a; rbm <= m1_bm; rbd <= m1_bd; end
        assign {o_mul, o_div, o_a, o_bm, o_bd} = {rm, rdv, ra, rbm, rbd};
    end else begin : g_m1w
        assign {o_mul, o_div, o_a, o_bm, o_bd} = {p_v && p_mul, p_v && p_div, p_a, m1_bm, m1_bd};
    end endgenerate
    ot_hdc_qmul_lat__d4g_sfu #(MLAT) u_m1 (clk, local_rst_n[13], o_mul, o_a, o_bm, mul1_y, f_m1);
    wire        ba_ge;                               // okey(p_a) >= okey(p_b), i.e. not (okey(p_b) > okey(p_a))
    ot_hdc_kge__d4g_sfu #(.W(32), .K(K)) u_mxb (.a(okey(p_a)), .b(okey(p_b)), .ge(ba_ge));
    wire [31:0] byp_in = (cp_m1 == M1_MAXB && !ba_ge) ? p_b : p_a;
    ot_hdc_delay__d4g_sfu #(.W(32), .D(MLAT + OPR)) u_b1 (.clk(clk), .rst_n(local_rst_n[14]), .d(byp_in), .q(byp1));
    localparam integer T1W = 32 * 3 + AW + 1;            // B, C', D, O, parity
    wire [T1W-1:0] t1;
    wire           v1;
    wire [31:0]    div1_y;
    wire           f_d1, c1;
    generate
        if (HAS_SFU != 0) begin : g_m1s
            if (DDIV == 31) begin : g_d31
                ot_hdc_fdiv__d4g_sfu    u_d1 (.clk(clk), .rst_n(local_rst_n[15]), .v(o_div), .a(o_a), .b(o_bd), .y(div1_y), .vo(),
                                        .fault(f_d1));
            end else if (DDIV == 21) begin : g_d21
                ot_dsrom_fdiv_f12__d4g_sfu u_d1 (.clk(clk), .rst_n(local_rst_n[16]), .v(o_div), .a(o_a), .b(o_bd), .y(div1_y), .vo(),
                                        .fault(f_d1));
            end else begin : g_d19
                ot_hdc_v41x_fdiv__d4g_sfu u_d1 (.clk(clk), .rst_n(local_rst_n[17]), .v(o_div), .a(o_a), .b(o_bd), .y(div1_y), .vo(),
                                       .fault(f_d1));
            end
            ot_hdc_v41x_ins__d4g_sfu #(.W(T1W), .K(2), .DEPTHS({H1_DIV, H1_M}), .DMAX(D_DIV + OPR)) u_l1 (
                .clk(clk), .rst_n(local_rst_n[18]), .v(p_v), .sel({p_div, !p_div}), .d({p_b, p_c, p_d, p_o, p_par}),
                .vo(v1), .q(t1), .coll(c1), .busy());
        end else begin : g_m1l
            assign div1_y = 32'd0; assign f_d1 = 1'b0; assign c1 = 1'b0;
            ot_hdc_delay__d4g_sfu #(.W(T1W), .D(MLAT + OPR)) u_t1 (.clk(clk), .rst_n(local_rst_n[19]), .d({p_b, p_c, p_d, p_o, p_par}), .q(t1));
            wire [MLAT+OPR:0] vl;
            ot_hdc_vline__d4g_sfu #(.D(MLAT + OPR)) u_v1 (.clk(clk), .rst_n(local_rst_n[20]), .v(p_v), .vd(vl));
            assign v1 = vl[MLAT + OPR];
        end
    endgenerate
    wire [31:0] m_b = t1[T1W-1 -: 32], m_c = t1[T1W-33 -: 32], m_d = t1[T1W-65 -: 32];
    wire [AW-1:0] m_oa = t1[AW:1];
    wire        m_par1 = t1[0];
    wire [31:0] P = (cm_m1 == M1_DIVB || cm_m1 == M1_DIVIMM) ? div1_y :
                    (cm_m1 == M1_AB || cm_m1 == M1_AA || cm_m1 == M1_AIMM) ? mul1_y : byp1;
    // ---- M2 and Q -----------------------------------------------------------------------------------------
    wire [31:0] m2_y, q_y, m2_byp;
    wire f_m2, f_q;
    ot_hdc_qmul_lat__d4g_sfu #(MLAT) u_m2 (clk, local_rst_n[21], v1 && cm_m2 != M2_BYP, P, (cm_m2 == M2_C) ? m_c : cm_imm1, m2_y, f_m2);
    wire qneg = (cm_qm == QM_NEG) || (cm_qm == QM_ALT_NP && !m_par1) || (cm_qm == QM_ALT_PN && m_par1);
    ot_hdc_qmul_lat__d4g_sfu #(MLAT) u_q (clk, local_rst_n[22], v1 && cm_qm != QM_OFF, m_c, {m_d[31] ^ qneg, m_d[30:0]}, q_y, f_q);
    wire [31:0] a2_b, a2_c, a2_d;
    wire [AW-1:0] a2_o;
    wire [1:0]  a2_m2;
    ot_hdc_delay__d4g_sfu #(.W(32 * 4 + AW + 2), .D(MLAT)) u_d2 (.clk(clk), .rst_n(local_rst_n[23]),
        .d({P, m_b, m_c, m_d, m_oa, cm_m2}), .q({m2_byp, a2_b, a2_c, a2_d, a2_o, a2_m2}));
    wire [MLAT:0] v2l;
    ot_hdc_vline__d4g_sfu #(.D(MLAT)) u_v2 (.clk(clk), .rst_n(local_rst_n[24]), .v(v1), .vd(v2l));
    wire v2 = v2l[MLAT];
    wire [31:0] P2 = (a2_m2 == M2_BYP) ? m2_byp : m2_y;
    // ---- AD ------------------------------------------------------------------------------------------------
    reg [31:0] ad_y;
    always @(*) begin
        case (ca_ad)
            AD_Q:    ad_y = q_y;
            AD_C:    ad_y = a2_c;
            AD_NEGB: ad_y = {~a2_b[31], a2_b[30:0]};
            AD_IMM:  ad_y = ca_imm2;
            default: ad_y = a2_d;
        endcase
    end
    wire [31:0] add_y, add_byp;
    wire f_ad;
    // c12 (OPR = 1): the operand register between AD's multiplexers and the adder
    wire        ad_v;
    wire [31:0] ad_a, ad_b;
    generate if (OPR != 0) begin : g_adr
        reg rv;
        reg [31:0] ra, rb;
        always @(posedge clk or negedge local_rst_n[25]) begin
            if (!local_rst_n[25]) rv <= 1'b0; else rv <= v2 && ca_ad != AD_BYP;
        end
        always @(posedge clk) begin ra <= P2; rb <= ad_y; end
        assign {ad_v, ad_a, ad_b} = {rv, ra, rb};
    end else begin : g_adw
        assign {ad_v, ad_a, ad_b} = {v2 && ca_ad != AD_BYP, P2, ad_y};
    end endgenerate
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP(K), .LAT(ALAT)) u_ad (clk, local_rst_n[26], ad_v, ad_a, ad_b, add_y, f_ad);
    wire [31:0] r_b, r_c;
    wire [AW-1:0] r_o;
    wire [2:0]  r_ad;
    ot_hdc_delay__d4g_sfu #(.W(32 * 3 + AW + 3), .D(ALAT + OPR)) u_d3 (.clk(clk), .rst_n(local_rst_n[27]),
        .d({P2, a2_b, a2_c, a2_o, ca_ad}), .q({add_byp, r_b, r_c, r_o, r_ad}));
    wire [ALAT+OPR:0] v3l;
    ot_hdc_vline__d4g_sfu #(.D(ALAT + OPR)) u_v3 (.clk(clk), .rst_n(local_rst_n[28]), .v(v2), .vd(v3l));
    wire v3 = v3l[ALAT + OPR];
    wire [31:0] R = (r_ad == AD_BYP) ? add_byp : add_y;
    // ---- S --------------------------------------------------------------------------------------------------
    // c12 SIDEX = 4: lane 0 also registers the side pipe's result at its port (counted in the side depths)
    wire [31:0] side_yi;
    generate if (SIDEX == 4 && FULL != 0) begin : g_syr
        reg [31:0] sy_r;
        always @(posedge clk) sy_r <= side_y;
        assign side_yi = sy_r;
    end else begin : g_syw
        assign side_yi = side_y;
    end endgenerate
    localparam integer T4W = 32 * 3 + AW;                 // R, B, C', O
    wire [T4W-1:0] t4;
    wire           v4, c4;
    wire [31:0]    S;
    wire           f_sfu;
    generate
        if (HAS_SFU != 0) begin : g_sfu
            // sigmoid chain: exp(-R); +1; (1 | R) / that
            wire is_exp = (ci_sfu == SFU_EXP), is_sig = (ci_sfu == SFU_SIGM || ci_sfu == SFU_SILU);
            wire [31:0] y_exp, y_div;
            wire f_e, f_den, f_div;
            if (SFUT >= 2) begin : g_chain_seam
                // TWO-LEVEL hierarchy (owner 10-11 ~21:00): the chain is its own die-placed tile.  Die-level seam
                // registered on both sides: lane-side launch registers here, the chain's own pin registers, the
                // chain's registered outputs, lane-side capture registers here (+4 = 2 * SFUT cycles on exp / sigmoid)
                (* keep *) reg so_rst, so_v, so_ie, so_is, so_si;
                (* keep *) reg [31:0] so_r;
                always @(posedge clk) begin
                    so_rst <= local_rst_n[29]; so_v <= v3; so_ie <= is_exp; so_is <= is_sig; so_si <= (ci_sfu == SFU_SILU);
                    so_r <= R;
                end
                wire [31:0] ci_ye, ci_yd;
                wire ci_fe, ci_fden, ci_fdiv;
`ifdef OT_SFU_CHAIN_EXT
                assign ch_rst_n = so_rst; assign ch_v = so_v; assign ch_is_exp = so_ie; assign ch_is_sig = so_is;
                assign ch_silu = so_si; assign ch_r = so_r;
                assign ci_ye = ch_y_exp; assign ci_yd = ch_y_div; assign ci_fe = ch_f_e; assign ci_fden = ch_f_den;
                assign ci_fdiv = ch_f_div;
`elsif OT_SFU_CHAIN_HARD
                // LANE CLUSTER (GLUE PLACEMENT rule 2): the chain is a hard child of the lane: no parameter overrides
                if (MLAT != 6 || ALAT != 6 || DDIV != 21 || DENR != 1 || DRING != 4 || K != 1) begin : g_chain_cfg_err2
                    OT_SFU_CHAIN_HARD_VIEW_IS_MLAT6_ALAT6_DDIV21_DENR1_DRING4_K1 u_cfg_err ();   // undefined: elaboration stops
                end
                ot_hdc_v41x_sfu_chain__d4g_sfu u_chain (
                    .clk(clk), .rst_n(so_rst), .v(so_v), .is_exp(so_ie), .is_sig(so_is), .silu(so_si), .r(so_r),
                    .y_exp(ci_ye), .y_div(ci_yd), .f_e(ci_fe), .f_den(ci_fden), .f_div(ci_fdiv));
`else
                ot_hdc_v41x_sfu_chain__d4g_sfu #(.MLAT(MLAT), .ALAT(ALAT), .DDIV(DDIV), .DENR(DENR), .DRING(DRING), .K(K)) u_chain (
                    .clk(clk), .rst_n(so_rst), .v(so_v), .is_exp(so_ie), .is_sig(so_is), .silu(so_si), .r(so_r),
                    .y_exp(ci_ye), .y_div(ci_yd), .f_e(ci_fe), .f_den(ci_fden), .f_div(ci_fdiv));
`endif
                (* keep *) reg [31:0] yi_e, yi_d;
                (* keep *) reg fi_e, fi_den, fi_div;
                always @(posedge clk) begin
                    yi_e <= ci_ye; yi_d <= ci_yd; fi_e <= ci_fe; fi_den <= ci_fden; fi_div <= ci_fdiv;
                end
                assign y_exp = yi_e; assign y_div = yi_d; assign f_e = fi_e; assign f_den = fi_den; assign f_div = fi_div;
            end else if (SFUT != 0) begin : g_chain_tile
`ifdef OT_SFU_CHAIN_HARD
                // hard sub-tile: no parameter overrides (the LEF/LIB cell); its defaults must be this lane's config
                if (MLAT != 6 || ALAT != 6 || DDIV != 21 || DENR != 1 || DRING != 4 || K != 1) begin : g_chain_cfg_err
                    OT_SFU_CHAIN_HARD_VIEW_IS_MLAT6_ALAT6_DDIV21_DENR1_DRING4_K1 u_cfg_err ();   // undefined: elaboration stops
                end
                ot_hdc_v41x_sfu_chain__d4g_sfu u_chain (
`else
                ot_hdc_v41x_sfu_chain__d4g_sfu #(.MLAT(MLAT), .ALAT(ALAT), .DDIV(DDIV), .DENR(DENR), .DRING(DRING), .K(K)) u_chain (
`endif
                    .clk(clk), .rst_n(local_rst_n[29]), .v(v3), .is_exp(is_exp), .is_sig(is_sig),
                    .silu(ci_sfu == SFU_SILU), .r(R), .y_exp(y_exp), .y_div(y_div), .f_e(f_e), .f_den(f_den), .f_div(f_div));
            end else begin : g_chain_flat
            wire [31:0] den, num_d;
            wire [D_EXP:0] ve;
            wire [D_EXP+DENR:0] vs;                 // a sigmoid-chain element, along the exp
            ot_hdc_vline__d4g_sfu #(.D(D_EXP)) u_ve (.clk(clk), .rst_n(local_rst_n[29]), .v(v3 && (is_exp || is_sig)), .vd(ve));
            ot_hdc_vline__d4g_sfu #(.D(D_EXP + DENR)) u_vs (.clk(clk), .rst_n(local_rst_n[30]), .v(v3 && is_sig), .vd(vs));
            ot_hdc_v41x_exp__d4g_sfu #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk), .rst_n(local_rst_n[31]), .v(v3 && (is_exp || is_sig)),
                                   .x(is_exp ? R : {~R[31], R[30:0]}), .y(y_exp), .vo(), .fault(f_e));
            wire [31:0] y_den_in;
            if (DENR != 0) begin : g_denr
                (* keep *) reg [31:0] y_den_r;      // own copy next to u_den (y_exp also feeds S)
                always @(posedge clk) y_den_r <= y_exp;
                assign y_den_in = y_den_r;
            end else begin : g_nodenr
                assign y_den_in = y_exp;
            end
            ot_hdc_qadd_lat__d4g_sfu #(.KEEP(K), .LAT(ALAT)) u_den (clk, local_rst_n[32], vs[D_EXP + DENR], y_den_in, 32'h3F800000, den, f_den);
            wire silu_in = (ci_sfu == SFU_SILU);
            wire [31:0] num_in = silu_in ? R : 32'h3F800000;
            ot_hdc_delay_ring__d4g_sfu #(.W(32), .D(D_EXP + DENR + ALAT), .RING(DRING)) u_num (.clk(clk), .rst_n(local_rst_n[33]), .d(num_in), .q(num_d));
            wire [ALAT:0] vdn;
            ot_hdc_vline__d4g_sfu #(.D(ALAT)) u_vdn (.clk(clk), .rst_n(local_rst_n[34]), .v(vs[D_EXP + DENR]), .vd(vdn));
            if (DDIV == 31) begin : g_s31
                ot_hdc_fdiv__d4g_sfu    u_div (.clk(clk), .rst_n(local_rst_n[35]), .v(vdn[ALAT]), .a(num_d), .b(den), .y(y_div), .vo(),
                                         .fault(f_div));
            end else if (DDIV == 21) begin : g_s21
                ot_dsrom_fdiv_f12__d4g_sfu u_div (.clk(clk), .rst_n(local_rst_n[36]), .v(vdn[ALAT]), .a(num_d), .b(den), .y(y_div), .vo(),
                                         .fault(f_div));
            end else begin : g_s19
                ot_hdc_v41x_fdiv__d4g_sfu u_div (.clk(clk), .rst_n(local_rst_n[37]), .v(vdn[ALAT]), .a(num_d), .b(den), .y(y_div), .vo(),
                                        .fault(f_div));
            end
            end
            wire [6:0] sel;
            assign sel = {ci_sfu == SFU_EGATE, ci_sfu == SFU_SPSQRT, ci_sfu == SFU_SQRT, ci_sfu == SFU_RSQRT,
                          is_sig, is_exp, ci_sfu == SFU_NONE};
            if (FULL != 0) begin : g_full
                ot_hdc_v41x_ins__d4g_sfu #(.W(T4W), .K(7),
                    .DEPTHS({H_EG, H_SP, H_SQRT, H_RSQ, H_SIG, H_EXP, 16'd0}), .DMAX(D_SP), .RING(DRING)) u_l4 (
                    .clk(clk), .rst_n(local_rst_n[38]), .v(v3), .sel(sel), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4), .coll(c4), .busy());
            end else begin : g_vec
                ot_hdc_v41x_ins__d4g_sfu #(.W(T4W), .K(3), .DEPTHS({H_SIG, H_EXP, 16'd0}), .DMAX(D_SIG), .RING(DRING)) u_l4 (
                    .clk(clk), .rst_n(local_rst_n[39]), .v(v3), .sel(sel[2:0]), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4),
                    .coll(c4), .busy());
            end
            assign S = (cs_sfu == SFU_EXP) ? y_exp : (cs_sfu == SFU_SIGM || cs_sfu == SFU_SILU) ? y_div :
                       (cs_sfu == SFU_NONE) ? t4[T4W-1 -: 32] : side_yi;
            assign f_sfu = f_e | f_den | f_div;
        end else begin : g_nosfu
            assign t4 = {R, r_b, r_c, r_o}; assign v4 = v3; assign c4 = 1'b0;
            assign S = R; assign f_sfu = 1'b0;
        end
    endgenerate
    wire side_vc = (FULL != 0) && v3 && (ci_sfu == SFU_RSQRT || ci_sfu == SFU_SQRT || ci_sfu == SFU_SPSQRT ||
                                         ci_sfu == SFU_EGATE);
    generate if (SIDEX != 0 && FULL != 0) begin : g_sider
        // c12: lane 0's side outputs leave from registers (the side pipe is its own hardened block)
        reg        sv_r;
        reg [31:0] sx_r;
        always @(posedge clk or negedge local_rst_n[40]) begin
            if (!local_rst_n[40]) sv_r <= 1'b0; else sv_r <= side_vc;
        end
        always @(posedge clk) sx_r <= R;
        assign side_v = sv_r;
        assign side_x = sx_r;
    end else begin : g_sidew
        assign side_v = side_vc;
        assign side_x = R;
    end endgenerate
    wire [31:0] s_b = t4[T4W-33 -: 32], s_c = t4[T4W-65 -: 32];
    wire [AW-1:0] s_o = t4[AW-1:0];
    // ---- E1 -------------------------------------------------------------------------------------------------
    wire [31:0] e1m, e1a, e1_byp;
    wire f_e1m, f_e1a;
    // c12 (OPR = 1): the operand register between E1's multiplexers (and the S selection) and its units
    wire        e1_vm, e1_va;
    wire [31:0] e1_a, e1_bm, e1_ba;
    generate if (OPR != 0) begin : g_e1r
        reg rvm, rva;
        reg [31:0] ra, rbm, rba;
        always @(posedge clk or negedge local_rst_n[41]) begin
            if (!local_rst_n[41]) begin rvm <= 1'b0; rva <= 1'b0; end
            else begin
                rvm <= v4 && (cs_e1 == E1_MULC || cs_e1 == E1_MULIMM);
                rva <= v4 && (cs_e1 == E1_ADDC || cs_e1 == E1_ADDIMM);
            end
        end
        always @(posedge clk) begin
            ra <= S; rbm <= (cs_e1 == E1_MULC) ? s_c : cs_imm2; rba <= (cs_e1 == E1_ADDC) ? s_c : cs_imm2;
        end
        assign {e1_vm, e1_va, e1_a, e1_bm, e1_ba} = {rvm, rva, ra, rbm, rba};
    end else begin : g_e1w
        assign {e1_vm, e1_va, e1_a, e1_bm, e1_ba} = {v4 && (cs_e1 == E1_MULC || cs_e1 == E1_MULIMM),
                                                    v4 && (cs_e1 == E1_ADDC || cs_e1 == E1_ADDIMM), S,
                                                    (cs_e1 == E1_MULC) ? s_c : cs_imm2, (cs_e1 == E1_ADDC) ? s_c : cs_imm2};
    end endgenerate
    ot_hdc_qmul_lat__d4g_sfu #(MLAT) u_e1m (clk, local_rst_n[42], e1_vm, e1_a, e1_bm, e1m, f_e1m);
    wire [31:0] e1a3;
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP(K), .LAT(ALAT)) u_e1a (clk, local_rst_n[43], e1_va, e1_a, e1_ba, e1a3, f_e1a);
    // E1 is MLAT deep (its multiply); the 3-cycle add waits MLAT - 3 more
    ot_hdc_delay__d4g_sfu #(.W(32), .D(MLAT - ALAT)) u_e1ad (.clk(clk), .rst_n(local_rst_n[44]), .d(e1a3), .q(e1a));
    wire [31:0] e_b;
    wire [AW-1:0] e_o;
    wire [2:0]  e_e1;
    ot_hdc_delay__d4g_sfu #(.W(32 * 2 + AW + 3), .D(MLAT + OPR)) u_d5 (.clk(clk), .rst_n(local_rst_n[45]), .d({S, s_b, s_o, cs_e1}),
                                                   .q({e1_byp, e_b, e_o, e_e1}));
    wire [MLAT+OPR:0] v5l;
    ot_hdc_vline__d4g_sfu #(.D(MLAT + OPR)) u_v5 (.clk(clk), .rst_n(local_rst_n[46]), .v(v4), .vd(v5l));
    wire v5 = v5l[MLAT + OPR];
    wire [31:0] T = (e_e1 == E1_MULC || e_e1 == E1_MULIMM) ? e1m : (e_e1 == E1_ADDC || e_e1 == E1_ADDIMM) ? e1a :
                    e1_byp;
    // ---- E2 ---------------------------------------------------------------------------------------------------
    wire [31:0] e2m, e2_byp;
    wire f_e2;
    ot_hdc_qmul_lat__d4g_sfu #(MLAT) u_me2 (clk, local_rst_n[47], v5 && ce_e2 != E2_BYP, T, (ce_e2 == E2_MULB) ? e_b : ce_imm1, e2m, f_e2);
    wire [AW-1:0] u_o;
    wire [1:0]  u_e2;
    ot_hdc_delay__d4g_sfu #(.W(32 + AW + 2), .D(MLAT)) u_d6 (.clk(clk), .rst_n(local_rst_n[48]), .d({T, e_o, ce_e2}),
                                               .q({e2_byp, u_o, u_e2}));
    wire [MLAT:0] v6l;
    ot_hdc_vline__d4g_sfu #(.D(MLAT)) u_v6 (.clk(clk), .rst_n(local_rst_n[49]), .v(v5), .vd(v6l));
    wire v6 = v6l[MLAT];
    wire [31:0] U = (u_e2 == E2_BYP) ? e2_byp : e2m;
    // ---- OUT --------------------------------------------------------------------------------------------------
    // bf16(U) = (U[31:16] + inc) << 16, inc = U[15] & (U[16] | U[14:0] != 0): round to nearest even.  The KV
    // write is bf16(out) = bf16(U) whether or not out was rounded (bf16 of a BF16 value is itself)
    wire [15:0] u_hi1;
    ot_hdc_kinc__d4g_sfu #(.W(16), .K(K)) u_rnd (.a(U[31:16]), .inc(U[15] & (U[16] | (|U[14:0]))), .y(u_hi1));
    wire [31:0] u_bf = {u_hi1, 16'd0};
    wire [31:0] out = co_rnd ? u_bf : U;
    reg         ov_r;
    reg  [31:0] o_x;
    always @(posedge clk or negedge local_rst_n[50]) begin
        if (!local_rst_n[50]) begin vm_we <= 1'b0; kv_we <= 1'b0; ov_r <= 1'b0; end
        else begin
            vm_we <= v6 && co_dst == DST_VM;
            kv_we <= v6 && (co_dst == DST_KV || co_dst == DST_KVT);
            ov_r <= v6;
        end
    end
    always @(posedge clk) begin
        vm_waddr <= u_o; vm_wdata <= out;
        kv_waddr <= u_o; kv_wdata <= u_bf;
        o_x <= out;
    end
    assign ro_v = ov_r;
    assign ro_x = o_x;
    // ---- status ---------------------------------------------------------------------------------------------------
    reg fault_r;
    always @(posedge clk or negedge local_rst_n[51]) begin
        if (!local_rst_n[51]) fault_r <= 1'b0;
        else fault_r <= f_m1 | f_d1 | f_m2 | f_q | f_ad | f_sfu | f_e1m | f_e1a | f_e2;
    end
    assign fault = fault_r;
    generate if (OPR != 0) begin : g_collr
        reg coll_r;
        always @(posedge clk or negedge local_rst_n[52]) begin
            if (!local_rst_n[52]) coll_r <= 1'b0; else coll_r <= c1 | c4;
        end
        assign coll = coll_r;
    end else begin : g_collw
        assign coll = c1 | c4;
    end endgenerate
endmodule

// el1011-hbm-sfu 2026-10-11 (textbook class 1, SFU lane: 47,785 sinks on one root): the lane's sigmoid chain as a
// hardened sub-tile.  Every input is a pin register, every output a register (no logic between pin and flop); the
// reset enters through its own pin flop.  Same words as the in-lane chain, 2 cycles later.
`ifndef OT_SFU_CHAIN_HARD  // lane cluster build: the chain is the hard child (LEF/LIB), not RTL
module ot_hdc_v41x_sfu_chain__d4g_sfu #(
    // defaults = the HARDENED configuration (a hard child has no parameters: preamble PARENT SYNTHESIS rule)
    parameter integer MLAT = 6, parameter integer ALAT = 6, parameter integer DDIV = 21, parameter integer DENR = 1,
    parameter integer DRING = 4, parameter integer K = 1
) (
    input  wire clk, input wire rst_n,
    input  wire v, input wire is_exp, input wire is_sig, input wire silu, input wire [31:0] r,
    output reg  [31:0] y_exp, output reg [31:0] y_div, output reg f_e, output reg f_den, output reg f_div
);
    localparam integer D_DIV = DDIV, D_EXP = 7 * MLAT + 8 * ALAT + 4;
    reg rst_q; always @(posedge clk) rst_q <= rst_n;
    wire [4:0] local_rst_n = {5{rst_q}};
    reg v3, ie_q, is_q, si_q; reg [31:0] R;
    always @(posedge clk or negedge rst_q) if (!rst_q) v3 <= 1'b0; else v3 <= v;
    always @(posedge clk) begin ie_q <= is_exp; is_q <= is_sig; si_q <= silu; R <= r; end
    wire is_exp_i = ie_q, is_sig_i = is_q;
    wire [31:0] y_exp_c, y_div_c, den, num_d;
    wire f_e_c, f_den_c, f_div_c;
    wire [D_EXP:0] ve;
    wire [D_EXP+DENR:0] vs;
    ot_hdc_vline__d4g_sfu #(.D(D_EXP)) u_ve (.clk(clk), .rst_n(local_rst_n[0]), .v(v3 && (is_exp_i || is_sig_i)), .vd(ve));
    ot_hdc_vline__d4g_sfu #(.D(D_EXP + DENR)) u_vs (.clk(clk), .rst_n(local_rst_n[1]), .v(v3 && is_sig_i), .vd(vs));
    ot_hdc_v41x_exp__d4g_sfu #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk), .rst_n(local_rst_n[2]), .v(v3 && (is_exp_i || is_sig_i)),
                           .x(is_exp_i ? R : {~R[31], R[30:0]}), .y(y_exp_c), .vo(), .fault(f_e_c));
    wire [31:0] y_den_in;
    generate if (DENR != 0) begin : g_denr
        (* keep *) reg [31:0] y_den_r;
        always @(posedge clk) y_den_r <= y_exp_c;
        assign y_den_in = y_den_r;
    end else begin : g_nodenr
        assign y_den_in = y_exp_c;
    end endgenerate
    ot_hdc_qadd_lat__d4g_sfu #(.KEEP(K), .LAT(ALAT)) u_den (clk, local_rst_n[3], vs[D_EXP + DENR], y_den_in, 32'h3F800000, den, f_den_c);
    wire [31:0] num_in = si_q ? R : 32'h3F800000;
    ot_hdc_delay_ring__d4g_sfu #(.W(32), .D(D_EXP + DENR + ALAT), .RING(DRING)) u_num (.clk(clk), .rst_n(local_rst_n[4]), .d(num_in), .q(num_d));
    wire [ALAT:0] vdn;
    ot_hdc_vline__d4g_sfu #(.D(ALAT)) u_vdn (.clk(clk), .rst_n(rst_q), .v(vs[D_EXP + DENR]), .vd(vdn));
    generate if (DDIV == 21) begin : g_s21
        ot_dsrom_fdiv_f12__d4g_sfu u_div (.clk(clk), .rst_n(rst_q), .v(vdn[ALAT]), .a(num_d), .b(den), .y(y_div_c), .vo(), .fault(f_div_c));
    end else begin : g_bad
        initial $error("ot_hdc_v41x_sfu_chain__d4g_sfu: DDIV 21 only");
    end endgenerate
    always @(posedge clk) begin y_exp <= y_exp_c; y_div <= y_div_c; end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin f_e <= 1'b0; f_den <= 1'b0; f_div <= 1'b0; end
        else begin f_e <= f_e_c; f_den <= f_den_c; f_div <= f_div_c; end
endmodule
`endif  // OT_SFU_CHAIN_HARD

// Scoped source: rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): PHYSICAL VEHICLES of the c12 stream unit's hardened
// elements (fixed-parameter tops, so a route needs no -chparam), built from rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv,
// ot_hdc_v41x_vec_side_c12.sv, ot_hdc_v41x_sfu_c12.sv and rtl/hdc/ot_hdc_fastfp_lat_c12.sv at MLAT 6 / ALAT 6,
// OPR 1, DDIV 21, SIDEX 4, CAPR 1, FSQ 1.  As rtl/hdc/v41x/ot_hdc_v41x_w11_phys.sv's ot_hdc_v41x_vec_lane1024r, a lane is
// driven from one register (b_q) that stands for the broadcast tree's stage BCAST_STAGES - 1; the lane's own leaf
// register is the tree's last stage.
//   ot_su12_light__d4g_sfu  KIND 0 (lanes M .. N-1)      ot_su12_sfu__d4g_sfu  KIND 1 (lanes 1 .. M-1)
//   ot_su12_full__d4g_sfu   KIND 2 (lane 0, with the side pipe's ports)    ot_su12_side__d4g_sfu  the scalar side pipe
// Every output of the lane vehicles and of the side pipe leaves a register (rd_* / side_* / coll registered in the
// c12 lane, y / fault in the c12 side) and every input enters a register (b_q, the memory-word register (CAPR),
// the gather-word register (OPR), lane 0's side_y register (SIDEX 4), the side pipe's input registers), so the
// routes false-path the block's IO (--false-path-io), checked on the routed netlist (outcheck / incheck).
// ---------------------------------------------------------------------------
`ifndef OT_SFU_CH_PORTS
`ifdef OT_SFU_CHAIN_EXT
// el1011-hbm-sfu TWO-LEVEL (SFUT 2): the sigmoid chain is a separate die-placed tile; the lane exposes the seam
`define OT_SFU_CH_PORTS , output wire ch_rst_n, output wire ch_v, output wire ch_is_exp, output wire ch_is_sig, output wire ch_silu, output wire [31:0] ch_r, input wire [31:0] ch_y_exp, input wire [31:0] ch_y_div, input wire ch_f_e, input wire ch_f_den, input wire ch_f_div
`define OT_SFU_CH_CONN , .ch_rst_n(ch_rst_n), .ch_v(ch_v), .ch_is_exp(ch_is_exp), .ch_is_sig(ch_is_sig), .ch_silu(ch_silu), .ch_r(ch_r), .ch_y_exp(ch_y_exp), .ch_y_div(ch_y_div), .ch_f_e(ch_f_e), .ch_f_den(ch_f_den), .ch_f_div(ch_f_div)
`else
`define OT_SFU_CH_PORTS
`define OT_SFU_CH_CONN
`endif
`endif
module ot_su12_lane__d4g_sfu #(
    parameter integer KIND = 0,
    parameter integer LANE = 37,
    parameter integer MLAT = 6,         // multiplier latency (W11 serial domain: 5)
    parameter integer ALAT = 6,         // FP add latency (W11 serial domain: 4)
    parameter integer OPR = 1,
    parameter integer DDIV = 21,
    parameter integer SIDEX = 4,
    parameter integer CAPR = 1,
    parameter integer GSH = 0,          // CLAUDE HBM-ABSTRACTS hub lane margin (default off): gather shift register
    parameter integer KIMM = 0,         // ... and imm3 in order-key form (rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv)
    parameter integer DENR = 0,         // views agent SFU lane fail-fast (default off): sigmoid den operand register
    parameter integer RSTPIPE = 0,
    parameter integer SFUT = 0,         // el1011-hbm-sfu: sigmoid chain as a registered sub-tile (+2 exp / sigmoid)
    parameter integer DRING = 0         // ... and the SFU delay lines as ring buffers
) (
    input  wire clk, input wire rst_n,
    input  wire ld, input wire ld_bank, input wire [1199:0] ld_c,
    input  wire emit, input wire bank, input wire [23:0] o_v, i_v, no, ni, input wire [3:0] ls, lvw,
    input  wire [119:0] vb, input wire [23:0] krow, obase, aibase, input wire [1:0] aind, input wire [4:0] gsh,
    input  wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire [95:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [127:0] rd_q,
    input  wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3, input wire [2:0] cp_m1,
    input  wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2, input wire [2:0] cm_qm,
    input  wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2, input wire [2:0] ci_sfu,
    cs_sfu, cs_e1, input wire [31:0] cs_imm2, input wire [1:0] ce_e2, input wire [31:0] ce_imm1,
    input  wire co_rnd, input wire [1:0] co_dst,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y
    `OT_SFU_CH_PORTS
);
    localparam integer BW = 1 + 1 + 1200 + 1 + 1 + 4 * 24 + 4 + 4 + 120 + 3 * 24 + 2 + 5 + 1 + 2 + 8
                          + 4 + 32 + 3 + 32 + 3 + 2 + 3 + 32 + 3 + 32 + 3 + 3 + 3 + 32 + 2 + 32 + 1 + 2;
    wire [BW-1:0] b_in = {ld, ld_bank, ld_c, emit, bank, o_v, i_v, no, ni, ls, lvw, vb, krow, obase, aibase, aind, gsh,
                          cpair, dst, srcs, cx_arnd, cx_arelu, cx_amin, cx_cclip, cx_imm3, cp_m1, cp_imm1, cm_m1,
                          cm_m2, cm_qm, cm_imm1, ca_ad, ca_imm2, ci_sfu, cs_sfu, cs_e1, cs_imm2, ce_e2, ce_imm1,
                          co_rnd, co_dst};
    reg  [BW-1:0] b_q;
    always @(posedge clk) b_q <= b_in;
    wire r_ld, r_ld_bank, r_emit, r_bank, r_cpair, r_arnd, r_arelu, r_amin, r_cclip, r_rnd;
    wire [1199:0] r_ld_c; wire [23:0] r_o_v, r_i_v, r_no, r_ni, r_krow, r_obase, r_aibase; wire [3:0] r_ls, r_lvw;
    wire [119:0] r_vb; wire [1:0] r_aind, r_dst, r_m2, r_e2, r_odst; wire [4:0] r_gsh; wire [7:0] r_srcs;
    wire [31:0] r_imm3, r_pimm1, r_mimm1, r_aimm2, r_simm2, r_eimm1;
    wire [2:0] r_pm1, r_mm1, r_qm, r_ad, r_isfu, r_ssfu, r_e1;
    assign {r_ld, r_ld_bank, r_ld_c, r_emit, r_bank, r_o_v, r_i_v, r_no, r_ni, r_ls, r_lvw, r_vb, r_krow, r_obase,
            r_aibase, r_aind, r_gsh, r_cpair, r_dst, r_srcs, r_arnd, r_arelu, r_amin, r_cclip, r_imm3, r_pm1, r_pimm1,
            r_mm1, r_m2, r_qm, r_mimm1, r_ad, r_aimm2, r_isfu, r_ssfu, r_e1, r_simm2, r_e2, r_eimm1, r_rnd,
            r_odst} = b_q;
    // the lane with LEAF = 1: its own register is the broadcast tree's last stage (claude/w11-su d734e304);
    // b_q above stands for the tree's stage BCAST_STAGES - 1
    ot_hdc_v41x_vec_lane__d4g_sfu #(.AW(24), .LN(10), .KIND(KIND), .LEAF(1), .MLAT(MLAT), .ALAT(ALAT), .OPR(OPR),
                           .DDIV(DDIV), .SIDEX(SIDEX), .CAPR(CAPR), .GSH(GSH), .KIMM(KIMM), .DENR(DENR), .DRING(DRING), .RSTPIPE(RSTPIPE), .SFUT(SFUT)) u (
        .clk(clk), .rst_n(rst_n), .lane_id(LANE[10:0]), .ld(r_ld), .ld_bank(r_ld_bank), .ld_c(r_ld_c), .emit(r_emit),
        .bank(r_bank), .o_v(r_o_v), .i_v(r_i_v), .no(r_no), .ni(r_ni), .ls(r_ls), .lvw(r_lvw), .vb(r_vb),
        .krow(r_krow), .obase(r_obase), .aibase(r_aibase), .aind(r_aind), .gsh(r_gsh), .cpair(r_cpair), .dst(r_dst),
        .srcs(r_srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_srcs(8'd0), .cx_arnd(r_arnd), .cx_arelu(r_arelu), .cx_amin(r_amin),
        .cx_cclip(r_cclip), .cx_imm3(r_imm3), .cp_m1(r_pm1), .cp_imm1(r_pimm1), .cm_m1(r_mm1), .cm_m2(r_m2),
        .cm_qm(r_qm), .cm_imm1(r_mimm1), .ca_ad(r_ad), .ca_imm2(r_aimm2), .ci_sfu(r_isfu), .cs_sfu(r_ssfu),
        .cs_e1(r_e1), .cs_imm2(r_simm2), .ce_e2(r_e2), .ce_imm1(r_eimm1), .co_rnd(r_rnd), .co_dst(r_odst),
        .side_v(side_v), .side_x(side_x), .side_y(side_y),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll) `OT_SFU_CH_CONN);
endmodule

module ot_su12_light__d4g_sfu #(parameter integer GSH = 0, parameter integer KIMM = 0) (
    input  wire clk, input wire rst_n,
    input  wire ld, input wire ld_bank, input wire [1199:0] ld_c,
    input  wire emit, input wire bank, input wire [23:0] o_v, i_v, no, ni, input wire [3:0] ls, lvw,
    input  wire [119:0] vb, input wire [23:0] krow, obase, aibase, input wire [1:0] aind, input wire [4:0] gsh,
    input  wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire [95:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [127:0] rd_q,
    input  wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3, input wire [2:0] cp_m1,
    input  wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2, input wire [2:0] cm_qm,
    input  wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2, input wire [2:0] ci_sfu,
    cs_sfu, cs_e1, input wire [31:0] cs_imm2, input wire [1:0] ce_e2, input wire [31:0] ce_imm1,
    input  wire co_rnd, input wire [1:0] co_dst,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y
);
    ot_su12_lane__d4g_sfu #(.KIND(0), .LANE(37), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21), .SIDEX(4), .CAPR(1), .GSH(GSH), .KIMM(KIMM)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(), .side_x(), .side_y(32'd0) `OT_SFU_CH_CONN);
endmodule

module ot_su12_sfu__d4g_sfu #(parameter integer GSH = 0, parameter integer KIMM = 0, parameter integer DENR = 0, parameter integer DRING = 0, parameter integer RSTPIPE = 0, parameter integer SFUT = 0) (
    input  wire clk, input wire rst_n,
    input  wire ld, input wire ld_bank, input wire [1199:0] ld_c,
    input  wire emit, input wire bank, input wire [23:0] o_v, i_v, no, ni, input wire [3:0] ls, lvw,
    input  wire [119:0] vb, input wire [23:0] krow, obase, aibase, input wire [1:0] aind, input wire [4:0] gsh,
    input  wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire [95:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [127:0] rd_q,
    input  wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3, input wire [2:0] cp_m1,
    input  wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2, input wire [2:0] cm_qm,
    input  wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2, input wire [2:0] ci_sfu,
    cs_sfu, cs_e1, input wire [31:0] cs_imm2, input wire [1:0] ce_e2, input wire [31:0] ce_imm1,
    input  wire co_rnd, input wire [1:0] co_dst,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y
    `OT_SFU_CH_PORTS
);
    ot_su12_lane__d4g_sfu #(.KIND(1), .LANE(5), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21), .SIDEX(4), .CAPR(1), .GSH(GSH), .KIMM(KIMM), .DENR(DENR), .DRING(DRING), .RSTPIPE(RSTPIPE), .SFUT(SFUT)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(), .side_x(), .side_y(32'd0));
endmodule

module ot_su12_full__d4g_sfu (
    input  wire clk, input wire rst_n,
    input  wire ld, input wire ld_bank, input wire [1199:0] ld_c,
    input  wire emit, input wire bank, input wire [23:0] o_v, i_v, no, ni, input wire [3:0] ls, lvw,
    input  wire [119:0] vb, input wire [23:0] krow, obase, aibase, input wire [1:0] aind, input wire [4:0] gsh,
    input  wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire [95:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [127:0] rd_q,
    input  wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3, input wire [2:0] cp_m1,
    input  wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2, input wire [2:0] cm_qm,
    input  wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2, input wire [2:0] ci_sfu,
    cs_sfu, cs_e1, input wire [31:0] cs_imm2, input wire [1:0] ce_e2, input wire [31:0] ce_imm1,
    input  wire co_rnd, input wire [1:0] co_dst,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y
);
    ot_su12_lane__d4g_sfu #(.KIND(2), .LANE(0), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21), .SIDEX(4), .CAPR(1), .GSH(0), .KIMM(0)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(side_v), .side_x(side_x), .side_y(side_y));
endmodule

// ot_su12_full__d4g_sfu with DDIV 31 (Claude:hbm-su 2026-10-07, aggressive su_full variant): both dividers (M1 and the softplus
// gate) are rtl/hdc/v41/ot_hdc_fdiv__d4g_sfu (one quotient bit a stage, DEPTH 31) instead of the kit ot_dsrom_fdiv_f12__d4g_sfu (DEPTH 21,
// worst class of full_u30_h25: r_rem stage +4.77 at 833).  +10 cycles on every divide (M1 DIVB/DIVIMM, SIGM/SILU,
// softplus, EGATE); the controller / side run at DDIV 31 with it.
module ot_su12_full31__d4g_sfu (
    input  wire clk, input wire rst_n,
    input  wire ld, input wire ld_bank, input wire [1199:0] ld_c,
    input  wire emit, input wire bank, input wire [23:0] o_v, i_v, no, ni, input wire [3:0] ls, lvw,
    input  wire [119:0] vb, input wire [23:0] krow, obase, aibase, input wire [1:0] aind, input wire [4:0] gsh,
    input  wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire [95:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [127:0] rd_q,
    input  wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3, input wire [2:0] cp_m1,
    input  wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2, input wire [2:0] cm_qm,
    input  wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2, input wire [2:0] ci_sfu,
    cs_sfu, cs_e1, input wire [31:0] cs_imm2, input wire [1:0] ce_e2, input wire [31:0] ce_imm1,
    input  wire co_rnd, input wire [1:0] co_dst,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y
);
    ot_su12_lane__d4g_sfu #(.KIND(2), .LANE(0), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(31), .SIDEX(4), .CAPR(1)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(side_v), .side_x(side_x), .side_y(side_y));
endmodule

// the scalar side pipe: v / fn / x from lane 0's registers (fn: the controller's S-in code), y to lane 0's S output
module ot_su12_side__d4g_sfu (input wire clk, rst_n, v, input wire [2:0] fn, input wire [31:0] x, input wire [2:0] fn_out,
                     output wire [31:0] y, output wire fault);
    ot_hdc_v41x_vec_side #(.MLAT(6), .ALAT(6), .DDIV(21), .SIDEX(4), .FSQ(1)) u (.*);
endmodule

// Scoped source: rtl/lib/ot_rst_relay.sv
`timescale 1ns/1ps
// Registered, replicated local reset relay (synchronous-release reset tree).
//
// Design standard (coordinator 2026-10-10, drive-1010): a block's rst_n INPUT PORT drives only this relay.  The port net
// fans out to SYNC_STAGES synchronizer flops plus the asynchronous clear of the REGIONS*TREE_STAGES relay flops (assert
// stays asynchronous and immediate); release is synchronous and takes SYNC_STAGES + TREE_STAGES rising clk edges.
// Each region k then resets its own flops from rst_n[k], a flop output that placement can put next to that region, so no
// net from the port (or from one relay flop) spans the block.  On ~7 blocks the port -> thousands of reset flops net was
// the worst setup / hold path (hgi su_unit / su_ctl, idx-topk, qwen tile_e, ds qelem x1b).
//
// The region copies are logically identical, so synthesis would merge them: they are (* keep *) registers, which the
// ORFS flow's SYNTH_CANONICALIZE_TCL hook (physical/common_flow/ot_keep_regs.tcl, 0d3958d56) turns into kept flop cells.
//
// Consumers: release is delayed by RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES cycles (exactness is transaction-level; any
// logic that counts cycles from reset release must count from rst_n[k], never from the port).
module ot_rst_relay__d4g_sfu #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

    // relay tree: stage t, region r.  Every stage is replicated per region so each copy drives only its own region.
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

    assign rst_n = relay_q[TREE_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay__d4g_sfu: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay__d4g_sfu: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay__d4g_sfu: REGIONS must be >= 1");
    end
`endif
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 SQUARE ROOT for the V4.1 decode core: II 1, fixed
// DEPTH 31.  A stage-rebalanced copy of the qualified
// rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv (FRAC_SHIFT 15), with the decode
// core's port convention (v/a -> y/vo/fault).
//
// WHAT CHANGED, AND WHY.  The qualified pipe routes at 766 MHz on ASAP7: its
// critical path is the single finishing stage, which finds the root's leading
// bit by a priority encoder over all 28 root bits, shifts by a variable amount,
// rounds and encodes in one cycle.  But the leading bit is not variable: the
// radicand is a 24- or 25-bit significand times 2^(2*FRAC_SHIFT), so the root
// lies in [2^(11.5+F), 2^(12.5+F)) and its top bit is bit F+12 or bit F+11.
// Here the finish is a 2-way select on root[F+12] (stage 1: truncated
// significand, guard, sticky, exponent) and a separate round-and-encode
// (stage 2).  The digit recurrence and the decode stage are transcribed
// unchanged.  rtl/test/tb_hdc_fsqrt_equiv.sv drives both modules from one
// stimulus and requires the same code and the same refusal for every operand,
// one cycle later.
//
// FUNCTION.  y = RN_even(sqrt(a)); sqrt(+-0) = +0; subnormal arguments are
// normalised; a negative or nonfinite argument FAILS CLOSED (fault, y = +0).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;   // the root's possible top bit

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (as qualified) ------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage (as qualified) --------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire take = (shifted >= trial);
            always @(posedge clk) begin
                rem_stage[g]  <= take ? (shifted - trial) : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1 -------------------------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    reg [23:0] f_trunc;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg signed [EXP_W-1:0] f_unb;       // unbiased exponent before the rounding carry
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        if (hi) begin
            f_trunc  <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
            f_unb    <= $signed(TOP) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end else begin
            f_trunc  <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
            f_unb    <= $signed(TOP - 1) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end
    end

    // ---- finish 2: round to nearest even, encode --------------------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc[0]);
    wire [24:0] rounded  = {1'b0, f_trunc} + {24'd0, round_up};
    wire        carried  = rounded[24];
    wire [23:0] sig_out  = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] biased = f_unb + (carried ? 12'sd1 : 12'sd0) + 12'sd127;
    wire out_of_range = (biased < 12'sd1) || (biased > 12'sd254);
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased[7:0], sig_out[22:0]}; fault <= 1'b0; end
    end
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt_c12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fsqrt_c12__d4g_sfu: the 1.2 GHz (0.833 ns ASAP7 SS) successor of rtl/hdc/v41/ot_hdc_fsqrt__d4g_sfu.sv for the HBM SU
// (hbm-su closure, 2026-10-05).  Same ports, same DEPTH 31, the same {vo, y, fault} on every cycle, bit for bit
// (rtl/test/tb_hdc_fsqrt_c12_equiv.sv drives both from one stimulus).  New file; the original is unchanged.
// Timing-only rewrites (closure kit: kept prefix adders, precomputed carries), no register moved:
//   * digit stage: `shifted >= trial` and `shifted - trial` are ONE kept Kogge-Stone subtractor
//     (ot_hdc_ksadd_k__d4g_sfu: shifted + ~trial + 1; its carry out is the take bit), instead of a behavioural compare and
//     subtract that ABC ripples (routed -114 ps in the SU side pipe);
//   * finish 1 also registers both candidate biased exponents (no rounding carry / carry) and their
//     out-of-range flags, from the stage's own half exponent and top-bit select;
//   * finish 2 is only the kept 24-bit rounding increment (ot_hdc_inc_k__d4g_sfu) and a carry select (was -167 ps).
//     When the increment carries out, the rounded significand is 2^24, so the 23 stored fraction bits are the
//     increment's low 23 bits either way.
// Needs rtl/hdc/ot_hdc_prefix.sv (ot_hdc_ksadd_k__d4g_sfu, ot_hdc_inc_k__d4g_sfu) and ot_hdc_vline__d4g_sfu (rtl/hdc/ot_hdc_sfu.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt_c12__d4g_sfu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_sfu #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (unchanged) ----------------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage, one kept subtractor -------------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire [REM_W-1:0] diff;
            wire             take;      // carry out of shifted + ~trial + 1  ==  (shifted >= trial)
            ot_hdc_ksadd_k__d4g_sfu #(.W(REM_W)) u_sub (.a(shifted), .b(~trial), .cin(1'b1), .s(diff), .cout(take));
            always @(posedge clk) begin
                rem_stage[g]  <= take ? diff : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1; both candidate exponents ------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    // biased = f_unb + 127 (+1 on a rounding carry); f_unb = half + (TOP - FRAC_SHIFT) (hi) or one less
    wire signed [EXP_W-1:0] h = half_stage[STAGES];
    wire signed [EXP_W-1:0] b_lo_hi = h + $signed(TOP - FRAC_SHIFT + 127);      // hi, no carry
    wire signed [EXP_W-1:0] b_lo_lo = h + $signed(TOP - 1 - FRAC_SHIFT + 127);  // lo, no carry
    wire signed [EXP_W-1:0] b_hi_hi = h + $signed(TOP - FRAC_SHIFT + 128);      // hi, carry
    wire [EXP_W-1:0] b0 = hi ? b_lo_hi : b_lo_lo;
    wire [EXP_W-1:0] b1 = hi ? b_hi_hi : b_lo_hi;                                 // lo + carry == hi, no carry
    reg [22:0] f_trunc_l;   // the truncated significand, low 23 bits
    reg        f_trunc23;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg [7:0]  f_b0, f_b1;
    reg        f_oor0, f_oor1;
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        f_b0 <= b0[7:0];
        f_b1 <= b1[7:0];
        f_oor0 <= ($signed(b0) < 12'sd1) || ($signed(b0) > 12'sd254);
        f_oor1 <= ($signed(b1) < 12'sd1) || ($signed(b1) > 12'sd254);
        if (hi) begin
            {f_trunc23, f_trunc_l} <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
        end else begin
            {f_trunc23, f_trunc_l} <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
        end
    end

    // ---- finish 2: kept rounding increment, carry select, encode --------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc_l[0]);
    wire [23:0] rounded;
    wire        carried;
    ot_hdc_inc_k__d4g_sfu #(.W(24)) u_inc (.a({f_trunc23, f_trunc_l}), .inc(round_up), .y(rounded), .co(carried));
    wire [7:0] biased = carried ? f_b1 : f_b0;
    wire       out_of_range = carried ? f_oor1 : f_oor0;
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased, rounded[22:0]}; fault <= 1'b0; end
    end
endmodule

