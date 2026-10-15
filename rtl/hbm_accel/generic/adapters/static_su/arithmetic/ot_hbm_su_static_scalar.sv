`timescale 1ns/1ps
// Actual single KIND2 head capacity from native N512 static arithmetic.
// Same 1742-bit compiler word, registered once, native6-SRAM bank external.
// Related1:1 phase0 roots; original fixed SIDE latency, no interface register.
module ot_hbm_su_static_scalar #(parameter integer FETCH_EXTRA_EDGES=2, SIDE_MUT=0)(
 input wire [7:0] clk_lane,input wire [3:0] clk_insert,input wire [5:0] clk_side,
 input wire clk_bcast,rst_n,
 input wire [1741:0] control,input wire [31:0] vi_q,input wire [127:0] rd_q,
 output wire side_v,output wire [31:0] side_x,output wire [2:0] side_fn,side_fn_out,
 output wire vi_re,vm_we,kv_we,ro_v,fault,coll,
 output wire [23:0] vi_addr,vm_waddr,kv_waddr,
 output wire [95:0] rd_addr,output wire [3:0] rd_re,output wire [7:0] rd_src,
 output wire [31:0] vm_wdata,kv_wdata,ro_x
);
 reg [1741:0] ctl;
 always @(posedge clk_bcast or negedge rst_n) if(!rst_n)ctl<=0;else ctl<=control;
 wire [31:0] side_y;
 wire lane_fault,side_fault;
 ot_hbm_su_static_side #(.MUT(SIDE_MUT)) side(.clk(clk_side),.rst_n(rst_n),.v(side_v),
 .fn(side_fn),.x(side_x),.fn_out(side_fn_out),.y(side_y),.fault(side_fault));
 assign fault=lane_fault|side_fault;
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
  assign {c_ld,c_ld_bank,c_ld_c,c_emit,c_bank,c_o_v,c_i_v,c_no,c_ni,c_ls,c_lvw,c_vb,c_krow,c_obase,c_aibase,c_aind,c_gsh,c_cpair,c_dst,c_srcs,c_cx_arnd,c_cx_arelu,c_cx_amin,c_cx_cclip,c_cx_imm3,c_cp_m1,c_cp_imm1,c_cm_m1,c_cm_m2,c_cm_qm,c_cm_imm1,c_ca_ad,c_ca_imm2,c_ci_sfu,c_cs_sfu,c_cs_e1,c_cs_imm2,c_ce_e2,c_ce_imm1,c_co_rnd,c_co_dst}=ctl;
  wire [839:0] terms;
  for(genvar s=0;s<5;s=s+1)begin:g_terms
   assign terms[s*168+:168]=c_ld_c[s*240+:168];
  end
  wire sv; wire [31:0] sx;
  assign side_v=sv; assign side_x=sx; assign side_fn=c_ci_sfu; assign side_fn_out=c_cs_sfu;
  ot_hbm_su_static_lane #(.LN(7),.KIND(2),.MLAT(3),.ALAT(3),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)) u_lane(
   .clk_stage(clk_lane),
   .clk_insert(clk_insert),
   .rst_n(rst_n),
   .lane_id(11'd0),
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
   .vi_q(vi_q),
   .rd_q(rd_q),
   .vi_re(vi_re),
   .vm_we(vm_we),
   .kv_we(kv_we),
   .ro_v(ro_v),
   .fault(lane_fault),
   .coll(coll),
   .vi_addr(vi_addr),
   .vm_waddr(vm_waddr),
   .kv_waddr(kv_waddr),
   .rd_addr(rd_addr),
   .rd_re(rd_re),
   .rd_src(rd_src),
   .vm_wdata(vm_wdata),
   .kv_wdata(kv_wdata),
   .ro_x(ro_x),
   .side_v(sv),
   .side_x(sx),
   .side_y(side_y));
endmodule
