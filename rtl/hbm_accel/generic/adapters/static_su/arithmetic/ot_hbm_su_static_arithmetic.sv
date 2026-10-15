`timescale 1ns/1ps
`default_nettype none
// Full-shape wires-only cluster: all 512 native lane identities remain live.
// Each quarter control is compiler-rebased explicitly; no hidden address translation.
// All clock entries are independent physical roots with a common scheduled phase.
// Scalar native side pipe is external and belongs only to global lane0.
module ot_hbm_su_static_arithmetic #(parameter integer FETCH_EXTRA_EDGES=2, MLAT=3, ALAT=3, LEAF=0)(
 input wire [4095:0] clk_lane, input wire [2047:0] clk_insert,
 input wire [511:0] rst_lane_n,
 input wire [63:0] clk_bcast, rst_bcast_n,
 input wire [6967:0] control,
 input wire [16383:0] vi_q,
 input wire [65535:0] rd_q,
 input wire [31:0] side_y,
 output wire side_v, output wire [31:0] side_x,
 output wire [2:0] side_fn, side_fn_out,
 output wire [511:0] vi_re, vm_we, kv_we, ro_v, fault, coll,
 output wire [12287:0] vi_addr, vm_waddr, kv_waddr,
 output wire [49151:0] rd_addr,
 output wire [2047:0] rd_re,
 output wire [4095:0] rd_src,
 output wire [16383:0] vm_wdata, kv_wdata, ro_x
);
 for(genvar b=0;b<64;b=b+1)begin:g_bcast
  // Eight actual replicas per root = 8*1742=13936 sinks, below 15000.
  reg [1741:0] ctl [0:7];
  for(genvar k=0;k<8;k=k+1)begin:g_replica
   always @(posedge clk_bcast[b] or negedge rst_bcast_n[b])
    if(!rst_bcast_n[b])ctl[k]<=0; else ctl[k]<=control[(b/16)*1742+:1742];
  end
 end
 for(genvar l=0;l<512;l=l+1)begin:g_lane
  localparam integer LOCAL=l%128;
  localparam integer KIND=(l==0)?2:(LOCAL<32)?1:0;
  wire [0:0] c_ld;
  wire [0:0] c_ld_bank;
  wire [1199:0] c_ld_c;
  wire [0:0] c_emit;
  wire [0:0] c_bank;
  wire [23:0] c_o_v;
  wire [23:0] c_i_v;
  wire [23:0] c_no;
  wire [23:0] c_ni;
  wire [3:0] c_ls;
  wire [3:0] c_lvw;
  wire [119:0] c_vb;
  wire [23:0] c_krow;
  wire [23:0] c_obase;
  wire [23:0] c_aibase;
  wire [1:0] c_aind;
  wire [4:0] c_gsh;
  wire [0:0] c_cpair;
  wire [1:0] c_dst;
  wire [7:0] c_srcs;
  wire [0:0] c_cx_arnd;
  wire [0:0] c_cx_arelu;
  wire [0:0] c_cx_amin;
  wire [0:0] c_cx_cclip;
  wire [31:0] c_cx_imm3;
  wire [2:0] c_cp_m1;
  wire [31:0] c_cp_imm1;
  wire [2:0] c_cm_m1;
  wire [1:0] c_cm_m2;
  wire [2:0] c_cm_qm;
  wire [31:0] c_cm_imm1;
  wire [2:0] c_ca_ad;
  wire [31:0] c_ca_imm2;
  wire [2:0] c_ci_sfu;
  wire [2:0] c_cs_sfu;
  wire [2:0] c_cs_e1;
  wire [31:0] c_cs_imm2;
  wire [1:0] c_ce_e2;
  wire [31:0] c_ce_imm1;
  wire [0:0] c_co_rnd;
  wire [1:0] c_co_dst;
  assign {c_ld,c_ld_bank,c_ld_c,c_emit,c_bank,c_o_v,c_i_v,c_no,c_ni,c_ls,c_lvw,c_vb,c_krow,c_obase,c_aibase,c_aind,c_gsh,c_cpair,c_dst,c_srcs,c_cx_arnd,c_cx_arelu,c_cx_amin,c_cx_cclip,c_cx_imm3,c_cp_m1,c_cp_imm1,c_cm_m1,c_cm_m2,c_cm_qm,c_cm_imm1,c_ca_ad,c_ca_imm2,c_ci_sfu,c_cs_sfu,c_cs_e1,c_cs_imm2,c_ce_e2,c_ce_imm1,c_co_rnd,c_co_dst}=g_bcast[l/8].ctl[l%8];
  wire [839:0] terms;
  for(genvar s=0;s<5;s=s+1)begin:g_terms
   assign terms[s*168+:168]=c_ld_c[s*240+:168];
  end
  wire sv; wire [31:0] sx;
  if(l==0)begin:g_side
   assign side_v=sv; assign side_x=sx; assign side_fn=c_ci_sfu; assign side_fn_out=c_cs_sfu;
  end
  ot_hbm_su_static_lane #(.LN(7),.KIND(KIND),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)) u_lane(
   .clk_stage(clk_lane[l*8+:8]),
   .clk_insert(clk_insert[l*4+:4]),
   .rst_n(rst_lane_n[l]),
   .lane_id(11'(LOCAL)),
   .cx_srcs(c_srcs),
   .ld(c_ld),
   .ld_bank(c_ld_bank),
   .ld_c(terms),
   .emit(c_emit),
   .bank(c_bank),
   .o_v(c_o_v),
   .i_v(c_i_v),
   .no(c_no),
   .ni(c_ni),
   .ls(c_ls),
   .lvw(c_lvw),
   .vb(c_vb),
   .krow(c_krow),
   .obase(c_obase),
   .aibase(c_aibase),
   .aind(c_aind),
   .gsh(c_gsh),
   .cpair(c_cpair),
   .dst(c_dst),
   .srcs(c_srcs),
   .cx_arnd(c_cx_arnd),
   .cx_arelu(c_cx_arelu),
   .cx_amin(c_cx_amin),
   .cx_cclip(c_cx_cclip),
   .cx_imm3(c_cx_imm3),
   .cp_m1(c_cp_m1),
   .cp_imm1(c_cp_imm1),
   .cm_m1(c_cm_m1),
   .cm_m2(c_cm_m2),
   .cm_qm(c_cm_qm),
   .cm_imm1(c_cm_imm1),
   .ca_ad(c_ca_ad),
   .ca_imm2(c_ca_imm2),
   .ci_sfu(c_ci_sfu),
   .cs_sfu(c_cs_sfu),
   .cs_e1(c_cs_e1),
   .cs_imm2(c_cs_imm2),
   .ce_e2(c_ce_e2),
   .ce_imm1(c_ce_imm1),
   .co_rnd(c_co_rnd),
   .co_dst(c_co_dst),
   .vi_q(vi_q[l*32+:32]),
   .rd_q(rd_q[l*128+:128]),
   .vi_re(vi_re[l*1+:1]),
   .vm_we(vm_we[l*1+:1]),
   .kv_we(kv_we[l*1+:1]),
   .ro_v(ro_v[l*1+:1]),
   .fault(fault[l*1+:1]),
   .coll(coll[l*1+:1]),
   .vi_addr(vi_addr[l*24+:24]),
   .vm_waddr(vm_waddr[l*24+:24]),
   .kv_waddr(kv_waddr[l*24+:24]),
   .rd_addr(rd_addr[l*96+:96]),
   .rd_re(rd_re[l*4+:4]),
   .rd_src(rd_src[l*8+:8]),
   .vm_wdata(vm_wdata[l*32+:32]),
   .kv_wdata(kv_wdata[l*32+:32]),
   .ro_x(ro_x[l*32+:32]),
   .side_v(sv),
   .side_x(sx),
   .side_y(side_y));
 end
endmodule
`default_nettype wire
