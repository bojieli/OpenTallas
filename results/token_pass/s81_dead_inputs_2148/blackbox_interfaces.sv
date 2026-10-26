// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv
`define OT_S81SL_QREL_DELAYS 128'd0
`define OT_S81SL_XRT_PDSK_DEF 15'd0
`define OT_S81SL_XRT_PDSK_DEF 15'o01234   
`define OT_S81SL_XR_FOREG_DEF 1
`define OT_S81SL_XR_FOREG_DEF 0




module ot_s81sl_rstd_release #(parameter [127:0] DELAYS=128'd0) (
    input wire clk, rst_n, input wire [3:0] sid,
    input wire i_v, input wire [31:0] i_d,
    output wire o_v, output wire [31:0] o_d, output wire fault
);

endmodule

module ot_s81sl_xrt #(
    parameter [127:0] QDELAYS = 128'd0, 
    parameter [14:0] PDSK = 15'd0,
    parameter integer HB = 0,
    parameter integer FOREG = 0,          
    parameter integer FACE_LAND = 1,      
                                          
    parameter integer W  = 1104,
    parameter integer V  = 276,
    parameter integer BW = 513           
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    
    
    
    
    
    input  wire            dl_ev, input wire [W-29:1] dl_e,
    input  wire            dl_wv, input wire [W-29:1] dl_w,
    input  wire            dl_vv, input wire [V-1:1] dl_vb,
    (* keep *) output reg  [2:0] ci_dir,   
    output wire [W-29:0]   ci_b,
    
    input  wire [W-59:0]   bi,
    output wire [BW-1:0]   bo,
    
    output reg  [4:0]      c_v,
    (* keep *) output reg [159:0] c_d,       
    output reg  [4:0]      sw_v,
    output reg  [5*10-1:0] sw_a,
    (* keep *) output reg [5*8-1:0] sw_m,   
    output reg  [5*256-1:0] sw_d,
    input  wire [4:0]      lo_v,
    input  wire [5*256-1:0] lo_d,
    input  wire [4:0]      p_v,
    input  wire [5*32-1:0] p_d,
    output reg             rb_v,              
    output reg  [31:0]     rb_d,
    
    input  wire [4:0]      e_v,
    input  wire [5*2-1:0]  e_c,
    input  wire [5*96-1:0] e_d,
    input  wire            eg_v,
    input  wire [1:0]      eg_c,
    input  wire [31:0]     eg_d,
    output reg             g_v,               
    output reg  [1:0]      g_c,
    output reg  [31:0]     g_d,
    
    output reg             x_go,
    output reg             x_mode,        
                                          
    output wire [31:0]     x_eps,
    output wire [31:0]     x_scale,
    output reg             x_sv,
    output reg  [6:0]      x_si,              
    output reg  [31:0]     x_s,
    input  wire            x_rbv,
    input  wire [31:0]     x_rbd,
    
    output reg             is_v,
    (* keep *) output reg [159:0] is_d,
    output reg             cfg_v,
    (* keep *) output reg [159:0] cfg_d,
    output reg             fault          
                                          
);

endmodule




module ot_s81sl_xrt1 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF, parameter integer FACE_LAND = 1,
    parameter [14:0] PDSK = `OT_S81SL_XRT_PDSK_DEF, parameter [127:0] QDELAYS=`OT_S81SL_QREL_DELAYS) (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1075:1] dl_e, input wire dl_wv, input wire [1075:1] dl_w,
    input  wire dl_vv, input wire [275:1] dl_vb, output wire [2:0] ci_dir, output wire [1075:0] ci_b,
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [6:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);

endmodule

module ot_s81sl_xrt3 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF, parameter integer FACE_LAND = 1,
    parameter [14:0] PDSK = `OT_S81SL_XRT_PDSK_DEF, parameter [127:0] QDELAYS=`OT_S81SL_QREL_DELAYS) (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1075:1] dl_e, input wire dl_wv, input wire [1075:1] dl_w,
    input  wire dl_vv, input wire [275:1] dl_vb, output wire [2:0] ci_dir, output wire [1075:0] ci_b,
    input  wire [1045:0] bi, output wire [512:0] bo,     
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [6:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);

endmodule

(* keep_hierarchy="yes" *)
module ot_s81sl_xr_cp #(parameter integer W=1, ID=0)(input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_xr_rcp #(parameter integer ID=0)(input wire clk, rst_n, d, output wire q);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv
`define OT_S81SL_XR_FOREG_DEF 1
`define OT_S81SL_XR_FOREG_DEF 0
module ot_s81sl_xr #(
    parameter integer HB = 0,
    parameter integer FOREG = 0,          
    parameter integer W  = 1104,
    parameter integer V  = 276,
    parameter integer BW = 513           
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    
    input  wire            dl_ev, input wire [W-1:0] dl_e,
    input  wire            dl_wv, input wire [W-1:0] dl_w,
    input  wire            dl_vv, input wire [V-1:0] dl_vb,
    output reg  [2:0]      ci_dir,
    output wire [W-1:0]    ci_b,
    
    input  wire [W-1:0]    bi,
    output wire [BW-1:0]   bo,
    
    output reg  [4:0]      c_v,
    (* keep *) output reg [159:0] c_d,       
    output reg  [4:0]      sw_v,
    output reg  [5*10-1:0] sw_a,
    output reg  [5*8-1:0]  sw_m,
    output reg  [5*256-1:0] sw_d,
    input  wire [4:0]      lo_v,
    input  wire [5*256-1:0] lo_d,
    input  wire [4:0]      p_v,
    input  wire [5*32-1:0] p_d,
    output reg             rb_v,              
    output reg  [31:0]     rb_d,
    
    input  wire [4:0]      e_v,
    input  wire [5*2-1:0]  e_c,
    input  wire [5*96-1:0] e_d,
    input  wire            eg_v,
    input  wire [1:0]      eg_c,
    input  wire [31:0]     eg_d,
    output reg             g_v,               
    output reg  [1:0]      g_c,
    output reg  [31:0]     g_d,
    
    output reg             x_go,
    output wire            x_mode,
    output wire [31:0]     x_eps,
    output wire [31:0]     x_scale,
    output reg             x_sv,
    output reg  [7:0]      x_si,
    output reg  [31:0]     x_s,
    input  wire            x_rbv,
    input  wire [31:0]     x_rbd,
    
    output reg             is_v,
    (* keep *) output reg [159:0] is_d,
    output reg             cfg_v,
    (* keep *) output reg [159:0] cfg_d,
    output reg             fault
);

endmodule


module ot_s81sl_xr1 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF) (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);

endmodule

module ot_s81sl_xr3 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF) (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    input  wire [1103:0] bi, output wire [512:0] bo,
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_xg.sv






module ot_s81sl_xg (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [4:0]      xf_v, input wire [4:0] xf_s, input wire [5*276-1:0] xf,
    output wire [172:0]    nx_wi, output wire [172:0] nx_ei, input wire [172:0] nx_eo, input wire [172:0] nx_wo,
    output wire            dl_ev, output wire [1103:0] dl_e, output wire dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir, input wire [1075:0] ci_b,
    input  wire            is_v,  input wire [159:0] is_d,
    
    output wire [1100:0]   xw_d,
    output wire            fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv








module ot_s81sl_vsw #(
    parameter integer LM = 5,
    parameter integer LA = 4,
    
    
    
    
    
    parameter integer LR = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [255:0]  i_d,
    input  wire [31:0]   i_w,
    input  wire [31:0]   i_lim,
    output reg           o_v,
    (* keep *) output reg  [63:0]   o_d,
    output reg           o_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv
`define S81_VS_CONTROL_KEEP (* keep="true" *)
`define S81_VS_CONTROL_KEEP
`define S81_VS_ACC(i) cmd_accept[i]
`define S81_VS_ACC(i) acc_cmd
`undef S81_VS_ACC
`undef S81_VS_CONTROL_KEEP


























































module ot_s81sl_vs #(
    parameter integer XL = 6,          
    parameter integer MUT = 0          
                                       
                                       
                                       
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire          s_v,
    input  wire [157:0]  s_d,       
                                     
    
    output reg           x_rv,
    output reg  [9:0]    x_ra,
    input  wire          x_qv,
    input  wire [255:0]  x_qd,
    output reg           x_wv,
    (* keep *) output reg [9:0]    x_wa,
    (* keep *) output reg [7:0]    x_wm,
    (* keep *) output reg [255:0]  x_wd,
    
    output reg           u_v,
    (* keep *) output reg [2:0]    u_i,
    (* keep *) output reg [255:0]  u,
    output reg           um_v,
    (* keep *) output reg um_q,
    (* keep *) output reg um_b,
    (* keep *) output reg [7:0]    um_i,
    
    output reg           sw_v,
    output reg  [255:0]  sw_d,
    output reg  [31:0]   sw_w,
    output reg  [31:0]   sw_lim,
    input  wire          sw_vi,
    input  wire [63:0]   sw_ri,
    input  wire          sw_fi,
    
    output reg           ra_v,
    output reg  [31:0]   ra_x,
    input  wire          ra_vi,
    input  wire [30:0]   ra_ri,       
    input  wire          ra_fi,
    
    output reg           ve_rv,
    output reg  [1:0]    ve_rc,
    output wire [63:0]   ve_rh,           
    output reg  [127:0]  ve_rk,
    output reg  [127:0]  ve_rw,
    input  wire          ve_pv,
    input  wire [1:0]    ve_pc,
    input  wire [31:0]   ve_phh,
    input  wire [31:0]   ve_pkk,
    input  wire [31:0]   ve_pdd,
    output reg           ve_av,
    output reg  [1:0]    ve_ac,
    output wire [127:0]  ve_ah,           
    output reg  [255:0]  ve_aval,
    output reg  [31:0]   ve_ag,
    input  wire          ve_ov,
    input  wire [1:0]    ve_oc,
    input  wire [127:0]  ve_oy,           
    input  wire          ve_fi,
    
    output reg           e_v,
    output reg  [1:0]    e_c,
    output reg  [95:0]   e_d,
    input  wire          g_v,
    input  wire [1:0]    g_c,
    input  wire [31:0]   g_d,
    (* keep *) output reg fault
);

endmodule


(* keep_hierarchy="yes" *)
module ot_s81sl_vs_lane_ctl(input wire clk,rst_n,rst_v,busy,xqv,input wire[3:0]accept,cop,output wire[3:0]op,output wire[7:0]ka,output wire[31:0]op_copy,ka_copy,output wire arr);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_op4(input wire clk,accept,input wire[3:0]cop,output reg[3:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_ka8(input wire clk,rst_n,accept,busy,xqv,output reg[7:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_busy6(input wire clk,rst_n,sv,bad,done,output wire[5:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_operand4 #(parameter [3:0]NEG=0,parameter integer MUT=0)(input wire clk,input wire[3:0]op,input wire[2:0]expert,input wire[3:0]ra,rb,m0,m1,x,acc,output reg[3:0]a,b);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_output8 #(parameter integer RWORD=0)(input wire clk,input wire[3:0]op,input wire[1:0]rk,input wire[7:0]sw,usw,qb,rar,ra,rb,eng,moe,output reg[7:0]wd,u);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_odec8(input wire[3:0]op,output wire d8,d9,d10,d11,d14);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_weight8 #(parameter integer BYTE=0,SECOND=0,MUT=0)(input wire clk,input wire[1:0]accept,input wire[2:0]sel,input wire[7:0]imm,input wire arr,input wire[3:0]op,input wire wr,input wire[7:0]ka,input wire[255:0]row,output reg[7:0]w);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_xresult8 #(parameter integer LOW=0)(input wire clk,input wire[3:0]op,input wire[7:0]full,bf,qr,output reg[7:0]y);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_cmd8(input wire clk,accept,input wire[7:0]d,output reg[7:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_accept32(input wire clk,rst_n,sv,busy_after,input wire[159:0]packet,input wire[6:0]incoming_op,input wire[1:0]stream_bad,input wire[3:0]gmask_after,output wire[31:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_pending #(parameter integer N=16)(input wire clk,rs,arr,input wire[3:0]op,input wire ph,input wire[7:0]ka,output wire[N-1:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_qrhold8(input wire clk,en,input wire[7:0]d,output reg[7:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_qren(input wire v,input wire[3:0]op,input wire odd,output wire en);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_swweight8 #(parameter integer BYTE=0,MUT=0)(input wire clk,input wire[7:0]ka,input wire wr,input wire[7:0]w0,w1,output reg[7:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_kge8(input wire[7:0]ka,input wire wr,output wire hi);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_bankctl8 #(parameter integer PARITY=0,COPY=0)(input wire clk,rs,pre,input wire[3:0]op_next,input wire ph_next,input wire[7:0]ka,input wire arr,accept,input wire ov,input wire[1:0]oc,output wire[7:0]fill,add);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_kcapture8 #(parameter integer ODD=0)(input wire clk,rs,pre,input wire[7:0]ka,input wire arr,accept,output wire[7:0]q);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_dec2(input wire[1:0]k,output wire[3:0]y);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_gsel8(input wire[1:0]k,input wire[7:0]g0,g1,g2,g3,output wire[7:0]y);

endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_vs_hqpre(input wire qv,busy_next,input wire[3:0]op_next,input wire ph_next,output wire q);

endmodule

(* keep_hierarchy="yes" *)
module ot_s81sl_vs_count2(input wire clk,rs,input wire[1:0]d,output reg[1:0]q);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv
















module ot_s81sl_vq #(
    
    
    
    
    
    
    
    parameter integer AQ_XMEM = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          y_v,          
    input  wire [2:0]    y_i,
    input  wire [127:0]  y,             
    input  wire          u_v,          
    input  wire [2:0]    u_i,
    input  wire [255:0]  u,
    input  wire [3:0]    sid,        
    input  wire [2:0]    k,
    input  wire          m_v,        
    input  wire          m_q,        
    input  wire          m_b,
    input  wire [7:0]    m_i,
    input  wire          um_v,       
    input  wire          um_q,
    input  wire          um_b,
    input  wire [7:0]    um_i,
    output reg           xf_v,
    output reg           xf_s,
    output reg  [275:0]  xf,
    (* keep *) output reg fault          
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v




module ot_sram_1r1w_512x128_m4_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [8:0] r_addr_in,
    output reg  [127:0] rd_out,
    input  wire w_ce_in,
    input  wire [8:0] w_addr_in,
    input  wire [127:0] wd_in,
    input  wire [127:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [13:0] cr_sel
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/lib/ot_rst_relay.sv














module ot_rst_relay #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/ot_hdc_delay.sv



module ot_hdc_delay #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv








module ot_dsrom_su_hcpost_lane_pr #(
    parameter integer ML = 5,
    parameter integer AL = 4,
    parameter integer MUTANT = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    
    
    
    input  wire [31:16] r0, r1, r2, r3,
    input  wire [31:0] y,
    input  wire [31:0] c0, c1, c2, c3, p,
    output wire        vo,
    
    
    output wire [31:16] o,
    output wire        fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_leaf.sv




















module ot_s81sl_kv_leaf #(
 parameter integer CNIK=0, CP=0, HARD_RQ=0, CP_MUT=0, CNIK_MUT=0
)(
 input wire clk,rst_n,input wire c_v,input wire [159:0] c_d,
 output reg busy,done,output reg fault,
 output reg x_rv,output reg [9:0] x_ra,input wire x_qv,input wire [255:0] x_qd,
 output reg x_wv,output reg [9:0] x_wa,output reg [7:0] x_wm,output reg [255:0] x_wd
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv




















module ot_s81_su_rxc #(
    parameter integer S_RD = 5, LM = 5, LA = 4, XMUT = 0,
    parameter integer QW = 2                  
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output reg                    o_v,
    output reg  [13:0]            o_a,
    output reg  [15:0]            o_m,
    output reg  [511:0]           o_d,
    output reg                    o_v2,       
    output reg  [13:0]            o_a2,
    output reg  [511:0]           o_d2,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid,
    
    output reg                    xa_v,
    output reg  [511:0]           xa_x,
    input  wire                   xa_vi,
    input  wire [511:0]           xa_r,
    input  wire [15:0]            xa_f,       
    
    output reg  [1:0]             xq_v,
    output reg  [1023:0]          xq_x,       
    output reg  [511:0]           xq_c,
    output reg  [511:0]           xq_s,
    input  wire [1:0]             xq_vi,
    input  wire [1023:0]          xq_y,
    input  wire [3:0]             xq_f,
    
    output reg                    xb_v,       
    output reg                    xw_st,      
    output reg                    xw_v,       
    output reg                    xw_last,    
    output reg  [39:0]            xw_cfg,     
    input  wire                   xb_vi,
    input  wire                   xb_wi,      
    input  wire [511:0]           xb_y,
    input  wire [15:0]            xb_m,
    input  wire                   xb_f
);

endmodule



module ot_s81_su_rxsf #(parameter integer PCUT = 1, parameter integer TFTZ = 0) (
    input  wire        clk, rst_in,
    input  wire        i_v,
    input  wire [31:0] i_x,
    output reg         o_v,
    output reg  [31:0] o_u, o_u2, o_mx,
    output reg         o_f
);

endmodule




module ot_s81_su_rxsb #(parameter integer PCUT = 1, MUT = 0) (
    input  wire        clk, rst_in,
    input  wire        i_v,
    input  wire [31:0] i_u, i_u2, i_mx,
    input  wire        i_f,
    output reg         o_v,
    output reg  [31:0] o_r,
    output reg         o_f
);

endmodule




module ot_s81_su_rxqr #(
    parameter integer LM = 5, LA = 4, MUT = 0,
    parameter integer QL = 16                 
) (
    input  wire               clk, rst_in,
    input  wire               i_v,
    input  wire [32*QL-1:0]   i_x,
    input  wire [16*QL-1:0]   i_c, i_s,
    output reg                o_v,
    output reg  [32*QL-1:0]   o_y,
    output reg                o_f
);

endmodule





module ot_s81_su_rxrb #(
    parameter integer LM = 5, LA = 4, MUT = 0
) (
    input  wire            clk, rst_in,
    input  wire            i_v,
    input  wire [1023:0]   i_x,
    input  wire            w_st, w_v, w_last,
    input  wire [39:0]     w_cfg,
    output reg             o_v,
    output reg             o_w,
    output reg  [511:0]    o_y,
    output reg  [15:0]     o_m,
    output reg             o_f
);

endmodule



module ot_s81_su_rxh #(
    parameter integer S_RD = 5, LM = 5, LA = 4, XMUT = 0,
    parameter integer QL = 8                  
) (
    input  wire                   clk, rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output wire                   o_v,
    output wire [13:0]            o_a,
    output wire [15:0]            o_m,
    output wire [511:0]           o_d,
    output wire                   o_v2,
    output wire [13:0]            o_a2,
    output wire [511:0]           o_d2,
    output wire                   o_fu, o_fo, o_alive, o_den, o_rdy,
    output wire [7:0]             o_rjid
);

endmodule


module dsfd_su_t_rxc (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [7:0] dn_jid, input wire [4:0] dn_v,
    input  wire [2559:0] dn_d,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d,
    output wire          o_v2, output wire [13:0] o_a2, output wire [511:0] o_d2,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid,
    output wire          xa_v, output wire [511:0] xa_x, input wire xa_vi, input wire [511:0] xa_r, input wire [15:0] xa_f,
    output wire [1:0]    xq_v, output wire [1023:0] xq_x, output wire [511:0] xq_c, xq_s,
    input  wire [1:0]    xq_vi, input wire [1023:0] xq_y, input wire [3:0] xq_f,
    output wire          xb_v, xw_st, xw_v, xw_last, output wire [39:0] xw_cfg,
    input  wire          xb_vi, xb_wi, input wire [511:0] xb_y, input wire [15:0] xb_m, input wire xb_f
);

endmodule
module dsfd_su_t_rxrb (
    input wire ck, rst, i_v, input wire [1023:0] i_x, input wire w_st, w_v, w_last, input wire [39:0] w_cfg,
    output wire o_v, o_w, output wire [511:0] o_y, output wire [15:0] o_m, output wire o_f
);

endmodule
module dsfd_su_t_rxsf (
    input wire ck, rst, i_v, input wire [31:0] i_x,
    
    
    output wire o_v, output wire [30:0] o_u, o_u2, output wire [31:0] o_mx, output wire o_f
);

endmodule
module dsfd_su_t_rxsb (
    
    input wire ck, rst, i_v, input wire [30:0] i_u, i_u2, input wire [31:0] i_mx, input wire i_f,
    
    output wire o_v, output wire [30:0] o_r, output wire o_f
);

endmodule
module dsfd_su_t_rxqr (
    input wire ck, rst, i_v, input wire [255:0] i_x, input wire [127:0] i_c, i_s,
    output wire o_v, output wire [255:0] o_y, output wire o_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg.sv























module ot_s81sl_eg #(parameter integer D = 5120, LM = 5, LA = 4, MUT = 0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] eps,
    input  wire [31:0] scale,
    input  wire        i_v,
    input  wire [1:0]  i_c,
    input  wire [31:0] i_hh,
    input  wire [31:0] i_kk,
    input  wire [31:0] i_dd,
    output reg         g_v,
    output reg  [1:0]  g_c,
    output reg  [31:0] g,
    output reg         fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/cap_end/ot_s81sl_capc2_w3.sv





module ot_s81sl_capc2_w3 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [209:0]  rt_w,
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv
















module ot_s81dv_norm_finish #(
    parameter integer NV = 80,          
    parameter integer K  = 5,           
    parameter integer P  = 3,           
    parameter integer D  = 5120,
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*8-1:0]    f_base,      
    input  wire [P*K*32-1:0] f_d,
    input  wire [31:0]       eps,
    output wire              r_v,
    output wire [31:0]       r,
    output wire              fault
);

endmodule










module ot_s81dv_eng_finish #(
    parameter integer NV = 80,
    parameter integer K  = 5,
    parameter integer P  = 3,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [P-1:0]      f_v,
    input  wire [P*2-1:0]    f_t,         
    input  wire [P*8-1:0]    f_base,      
    input  wire [P*K*32-1:0] f_d,
    output reg               r_v,         
    output reg  [31:0]       r_hh, r_kk, r_dd,
    output wire              fault
);

endmodule








module ot_s81dv_xstop #(
    parameter integer K  = 5,
    parameter integer HE = 8,
    parameter integer HW = 7
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            inj_v,
    input  wire [7:0]      inj_base,
    input  wire [K*32-1:0] inj_d,
    input  wire            wi_v,  input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [K*32-1:0] wi_d,   
    input  wire            ei_v,  input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [K*32-1:0] ei_d,   
    output reg             eo_v,  output reg  [3:0] eo_h, output reg  [7:0] eo_b, output reg  [K*32-1:0] eo_d,
    output reg             wo_v,  output reg  [3:0] wo_h, output reg  [7:0] wo_b, output reg  [K*32-1:0] wo_d,
    output wire [2:0]      dl_v,                  
    output wire [3*8-1:0]  dl_b,
    output wire [3*K*32-1:0] dl_d,
    
    
    
    
    input  wire            eng,
    input  wire            ej_v,
    input  wire [7:0]      ej_b,
    input  wire [K*32-1:0] ej_d,
    output wire            ej_free,
    output reg             fault
);

endmodule






module ot_s81dv_xfin #(
    parameter integer NS  = 16,
    parameter integer NVL = 5,
    parameter integer LM  = 5,
    parameter integer LA  = 6,
    
    
    
    parameter integer SIW = 7
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire               mode,         
    input  wire [3:0]         sid,          
    input  wire [31:0]        eps,
    input  wire               s_v,          
    input  wire [SIW-1:0]     s_i,
    input  wire [31:0]        s,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [NVL*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [NVL*32-1:0] ei_d,
    output wire               eo_v, output wire [3:0] eo_h, output wire [7:0] eo_b, output wire [NVL*32-1:0] eo_d,
    output wire               wo_v, output wire [3:0] wo_h, output wire [7:0] wo_b, output wire [NVL*32-1:0] wo_d,
    output reg                rb_v,         
    output reg  [31:0]        rb_d,
    output reg                e_v,          
    output reg  [1:0]         e_c,
    output reg  [31:0]        e_hh, e_kk, e_dd,
    output reg                fault         
);

endmodule




module ot_s81dv_norm_slice #(
    parameter integer SID = 0,
    parameter integer NS  = 16,
    parameter integer NVL = 5,
    parameter integer LM  = 5,
    parameter integer LA  = 6
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire               in_v,
    input  wire [4*64*32-1:0] in_x,
    input  wire [127:0]       pre,
    input  wire [31:0]        eps,
    input  wire               wl_v,
    input  wire [7:0]         wl_i,
    input  wire [64*32-1:0]   wl_d,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [NVL*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [NVL*32-1:0] ei_d,
    output wire               eo_v, output wire [3:0] eo_h, output wire [7:0] eo_b, output wire [NVL*32-1:0] eo_d,
    output wire               wo_v, output wire [3:0] wo_h, output wire [7:0] wo_b, output wire [NVL*32-1:0] wo_d,
    output wire               y_v,
    output wire [7:0]         y_i,
    output wire [64*32-1:0]   y,
    output wire               r_v,
    output wire [31:0]        r,
    output wire               fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_xgt_xo.sv




















module ot_s81sl_xgt_xo (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [4:0]      xf_v, input wire [4:0] xf_s, input wire [5*276-1:0] xf,
    output wire [172:0]    nx_wi, output wire [172:0] nx_ei, input wire [172:0] nx_eo, input wire [172:0] nx_wo,
    output wire            dl_ev, output wire [1103:0] dl_e, output wire dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir, input wire [1075:0] ci_b,
    input  wire            is_v,  input wire [159:0] is_d,
    
    output wire [1100:0]   xw_d,
    output wire            fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_glue.sv







module ot_s81sl_ckf (
    input  wire        clk,
    output wire [15:0] ck_line,
    output wire [1:0]  ck_v,
    output wire [15:0] ck_xc,
    output wire [7:0]  ck_rt
);

endmodule

module ot_s81sl_mk (
    input  wire       clk,
    input  wire       rst_n,
    output reg  [1:0] mk
);

endmodule

module ot_s81sl_sflt #(parameter integer N = 10) (
    input  wire         clk,
    input  wire [N-1:0] f,
    output wire         q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r_e6.sv





module ot_s81sl_capc5r_e6 #(
    parameter integer MUT = 0
) (
    input wire [279:0] rt_w,
    input wire [139:0] rt_e,
    input wire cfg_v,
    input wire [159:0] cfg_d,
    output wire [5:0] cw_s_v,
    output wire [71:0] cw_s_a,
    output wire [191:0] cw_s_d,
    output wire [3:0] cw_n_v,
    output wire [47:0] cw_n_a,
    output wire [127:0] cw_n_d,
    output wire fault,
    input wire ck_rt,
    input wire ck_cw,
    input wire ck_ce,
    input wire ck_rn,
    input wire ck_rs,
    input wire rst_n_rt,
    input wire rst_n_cw,
    input wire rst_n_ce,
    input wire rst_n_rn,
    input wire rst_n_rs
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/common/landed_parent/ot_pl_land.sv












module ot_pl_land_w #(
    parameter integer W  = 514,
    parameter integer D  = 4,                          
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,                       
    input  wire              rsi,                      
    input  wire [W-1:0]      i,                        
    output wire [D*W-1:0]    bank,                     
    output wire [D*(AW+1)-1:0] epo,                    
    output wire [D-1:0]      vld                       
);

endmodule

module ot_pl_land_r #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,                          
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,                       
    input  wire              rsi,                      
    input  wire [D*W-1:0]    bank,
    input  wire [D*(AW+1)-1:0] epo,
    input  wire [D-1:0]      vld,
    output reg  [W-1:0]      o                         
);

endmodule





module ot_pl_land_chunk_w #(
    parameter integer W = 514, D = 4, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld
);

endmodule

module ot_pl_land_chunk_r #(
    parameter integer W = 514, D = 4, K = 2, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld,
    output wire [W-1:0] o
);

endmodule




module ot_pl_land_local_w #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);

endmodule

module ot_pl_land_local_r #(
    parameter integer W = 24, D = 4, K = 2,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D-1:0] vld,
    output reg [W-1:0] o
);

endmodule



module ot_pl_pad #(
    parameter integer W = 1,
    parameter integer N = 1
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/common/landed_parent/ot_pl_land_reset_forest.sv
module ot_pl_land_reset_forest #(
    parameter integer DEPTH=8, LEAVES=47, ROOT_LOADS=1
)(input wire ck,d, output wire [LEAVES-1:0] q);

endmodule

module ot_pl_land_vector_reset_w #(
    parameter integer W=1073,D=4,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,input wire [W-1:0] i,
    output wire [D*W-1:0] bank,output wire [D*(AW+1)-1:0] epo,
    output wire [D*CHUNKS-1:0] vld
);

endmodule

module ot_pl_land_vector_reset_r #(
    parameter integer W=1073,D=4,K=2,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,
    input wire [D*W-1:0] bank,input wire [D*(AW+1)-1:0] epo,
    input wire [D*CHUNKS-1:0] vld,output wire [W-1:0] o
);

endmodule
module ot_pl_land_reset_forest3 #(
    parameter integer DEPTH=8, LEAVES=2048, ROOT_LOADS=1
)(input wire ck,d, output wire [LEAVES-1:0] q);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/common/landed_parent/ot_pl_land_kept_enable.sv












module ot_pl_land_local_kw #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);

endmodule

module ot_pl_land_vector_reset_kw_w #(
    parameter integer W=1073,D=4,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,input wire [W-1:0] i,
    output wire [D*W-1:0] bank,output wire [D*(AW+1)-1:0] epo,
    output wire [D*CHUNKS-1:0] vld
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/common/landed_parent/ot_pl_land_n32.sv













(* keep_hierarchy = "yes" *)
module ot_pl_land_n32_oh #(parameter integer D = 4, ID = 0) (
    input wire ck, rq,
    output wire [D-1:0] oh
);

endmodule

module ot_pl_land_n32_local_w #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer GB = 12                                  
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);

endmodule

module ot_pl_land_n32_chunk_w #(
    parameter integer W = 514, D = 4, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld
);

endmodule

module ot_pl_land_n32_split_w #(
    parameter integer W = 1088, D = 4, CHUNK_BITS = 24, RG = 32,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NC = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input wire ck,
    input wire [(NC + RG - 1) / RG - 1:0] rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*NC-1:0] vld
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv








































































































module ot_s81sl_lep_core #(
    parameter integer DT = 512,        
    parameter integer DR = 8,          
    parameter integer CRED = 8,        
    parameter integer SRAM = 1,        
    parameter integer HOST_EN = 1,     
    parameter integer MU_EN = 0,       
    parameter integer AB_EN = 0,       
    parameter integer NB = 80,         
    parameter integer RX_SRAM = 0,     
    parameter integer TXRP = 1,        
    parameter integer NATIVE32_STD = 0, 
    parameter integer NATIVE32 = 0,    
    parameter integer IDX_EN = 0,      
    parameter integer RT_EN = 1,       
                                       
    parameter integer IDX_TP = 0,      
                                       
                                       
    parameter integer IDX_MRG = 0,     
    parameter integer IDX_Q = 0,       
                                       
    parameter integer IN_PIPE = 0      
                                       
) (
    input  wire            clk,
    input  wire            rst_n,
    
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,        
    
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,      
    input  wire [1:0]      l1_st,
    
    input  wire [76:0]     t_host,     
    input  wire [53:0]     t_kd,       
    output wire [514:0]    f_host,     
    output wire [3:0]      f_lf,       
    output wire [52:0]     f_ks,       
    
    input  wire [33:0]     mu_c,       
    output wire [31:0]     mu_rt,      
    output wire            ml_wv,      
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,      
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,       
    
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output reg             fault,
    
    
    input  wire [275:0]    tl,
    output wire [275:0]    ca,
    output wire [275:0]    cb,
    
    
    input  wire [275:0]    tm,
    input  wire [257:0]    qc,
    output wire [512:0]    ql
);

endmodule



module ot_s81sl_lep #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer HOST_EN = 1, parameter integer NATIVE32_STD = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    output wire            fault
);

endmodule


module ot_s81sl_lep_nh #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1, parameter integer NATIVE32_STD = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    output wire            fault
);

endmodule





module ot_s81sl_lep_mu #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer HOST_EN = 0, parameter integer AB_EN = 1, parameter integer NB = 80, parameter integer RX_SRAM = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);

endmodule






module ot_s81sl_lep_mu_ab #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);

endmodule







module ot_s81sl_lep_mu_ab_idx #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input  wire [275:0]    tl,
    output wire [275:0]    ca,
    output wire [275:0]    cb
);

endmodule





module ot_s81sl_lep_mu_ab_idxq #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input  wire [275:0]    tl,
    output wire [275:0]    ca,
    output wire [275:0]    cb,
    input  wire [275:0]    tm,
    input  wire [257:0]    qc,
    output wire [512:0]    ql
);

endmodule




module ot_s81sl_lep_mu_h_tp #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault,
    input  wire [275:0]    tp_i,
    output wire [275:0]    tp_o
);

endmodule



module ot_s81sl_lep_mu_a_tpt #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault,
    input  wire [275:0]    tp_i
);

endmodule



module ot_s81sl_lep_mu_a_tpr #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault,
    output wire [275:0]    tp_o
);

endmodule






module ot_s81sl_lep_mu_a #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault
);

endmodule





module ot_s81sl_lep_mu_a_nrt #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault
);

endmodule







module ot_s81sl_lep_mu_h #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault
);

endmodule











module ot_s81sl_lep_mu_hab #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);

endmodule








module ot_s81sl_slice_lep #(
    parameter integer SIDE = 0,
    parameter integer HOST_EN = 1,       
    parameter integer MU_EN = 0,
    parameter integer AB_EN = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_n,         
    output wire [1103:0]   ro_n,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [1103:0] bo,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    input  wire            ch_b,
    output wire [511:0]    tx0, output wire [511:0] tx1,
    input  wire [513:0]    rx0, input  wire [513:0] rx1,
    output wire [1:0]      tf,
    input  wire [76:0]     t_host, input wire [53:0] t_kd,
    output wire [514:0]    f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    input  wire [33:0]     mu_c,         
    input  wire [10:0]     mu_rc,        
    output wire [31:0]     mu_rt,        
    output wire [511:0]    tx2, output wire [511:0] tx3,
    input  wire [513:0]    rx2, input  wire [513:0] rx3,
    output wire [1:0]      tfb,
    output wire            fault
);

endmodule





module ot_s81sl_slice_lepw (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);

endmodule
module ot_s81sl_slice_lepe (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    input  wire [76:0] t_host, input wire [53:0] t_kd, output wire [514:0] f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    output wire fault
);

endmodule
module ot_s81sl_slice_lepe_nh (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);

endmodule



(* keep_hierarchy="yes" *) module ot_s81sl_lep_rx_control(
 input wire [3:0] ne,ring,hk,tag,input wire mv,input wire [4:0] mt,output wire [5:0] sel);

endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_event(input wire [11:0] now_status,old_status,input wire valid,output wire event_o);

endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_tx_push(input wire ring,host_go,key_go,open,pair_b,output wire [1:0] pp);

endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_enable(input wire ne0,ne1,hit,output wire en);

endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_stamp(input wire [31:0] count,input wire ring,output wire stamp);

endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_hold8(
 input wire [11:0] now_status,old_status,input wire valid,rn,pending,send_now,old_valid,
 input wire [7:0] keep_mask,old_data,new_data,output wire [7:0] next_data);

endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_key_hold8(input wire rn,valid,input wire [7:0] old_data,new_data,output wire [7:0] next_data);

endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_preserve(input wire pending,send_now,old_valid,new_valid,output wire preserve);

endmodule


(* keep_hierarchy="yes" *) module ot_s81sl_lep_vcopy(input wire clk, input wire d, output reg q);

endmodule


(* keep_hierarchy="yes" *) module ot_s81sl_lep_idx_sel(input wire clk, input wire rn, input wire d, output reg q);

endmodule


(* keep_hierarchy=1 *) module ot_s81sl_lep_status_region(
 input wire clk,rn,input wire [12:0] sample,
 output wire [11:0] now_status,output reg [11:0] old_status,output wire valid);

endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_pair_ready(input wire a,b,output wire q);

endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_return8(
 input wire [3:0] ne,input wire [1:0] ring,land,
 input wire [4:0] ring_code,replay_code,input wire [7:0] ring_data,replay_data,
 output wire [7:0] q);

endmodule


(* keep_hierarchy=1 *) module ot_s81sl_lep_std_enable(input wire a,b,ring,output wire q);

endmodule


(* keep_hierarchy=1 *) module ot_s81sl_std_tx_qualify #(parameter integer AT=9,CW=4,DT=512)(
 input wire push,input wire [AT:0] count,input wire [CW-1:0] credit,output wire wr,rd);

endmodule



(* keep_hierarchy=1 *) module ot_s81sl_lep_bsel_next (input wire [3:0] ne, output wire q);

endmodule


module ot_s81sl_lep_mu_hab_tp #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input wire [275:0]     tp_i,
    output wire [275:0]    tp_o
);

endmodule


module ot_s81sl_lep_mu_ab_tpr #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    output wire [275:0]     tp_o
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv
















module ot_s81_mu72_lnland #(parameter integer MUT = 0) (
    input  wire         ck_k, ck_n, rs_k, rs_n,
    
    input  wire         k_lo_v,  input  wire [552:0] k_lo_d, output wire k_lo_r,
    output wire         k_li_v,  output wire [552:0] k_li_d, input  wire k_li_r,
    input  wire         k_rxv,   output wire [2:0]   k_flt,  output wire [1:0] k_st,
    
    output wire         n_lo_v,  output wire [552:0] n_lo_d, input  wire n_lo_r,
    input  wire         n_li_v,  input  wire [552:0] n_li_d, output wire n_li_r,
    output wire         n_rxv,   input  wire [2:0]   n_flt,  input  wire [1:0] n_st
);

endmodule







module ot_s81_mu72_lnland_nst #(parameter integer MUT = 0) (
    input  wire         ck_k, ck_n, rs_k, rs_n,
    
    input  wire         k_lo_v,  input  wire [552:0] k_lo_d, output wire k_lo_r,
    output wire         k_li_v,  output wire [552:0] k_li_d, input  wire k_li_r,
    input  wire         k_rxv,   output wire [2:0]   k_flt,
    
    output wire         n_lo_v,  output wire [552:0] n_lo_d, input  wire n_lo_r,
    input  wire         n_li_v,  input  wire [552:0] n_li_d, output wire n_li_r,
    output wire         n_rxv,   input  wire [2:0]   n_flt
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv


module ot_s81_mu72_land #(parameter integer W=1)(
    input wire ck_w, ck_r, rs_w, rs_r,
    input wire [W-1:0] i, output wire [W-1:0] o
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv














module ot_s81ph_coll_lane_safe4 #(
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 700,
    parameter integer IDLE_P = 1024,
    parameter integer TF_CLEANUP = 0,
    
    
    
    
    
    
    
    
    
    
    
    
    parameter integer REACH = 0,
    parameter integer CORE_CRED = 8 
) (
    input  wire          clk,
    input  wire          rs_n,
    input  wire          ch_b,
    input  wire [514:0]  rx,
    output wire [511:0]  tx,
    output wire          tf,
    input  wire          lo_v,
    output wire          lo_r,
    input  wire [552:0]  lo_d,
    output wire          li_v,
    input  wire          li_r,
    output wire [552:0]  li_d,
    output reg  [2:0]    flt
);

endmodule


module dsfd_coll_lane_w_safe4 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule
module dsfd_coll_lane_e_safe4 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule


module dsfd_coll_lane_w_safe7 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule
module dsfd_coll_lane_e_safe7 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule


module dsfd_coll_lane_w_safe8 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule
module dsfd_coll_lane_e_safe8 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule







module dsfd_coll_lane_w_safe8_ntf #(parameter integer CORE_CRED = 8) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule
module dsfd_coll_lane_e_safe8_ntf #(parameter integer CORE_CRED = 8) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv




























module dsdv_mu_land #(
    parameter integer W = 1104,
    parameter integer NB = 80,          
    parameter integer NS = 1,           
    parameter integer SRAM = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          wv,            
    input  wire [W-1:0]  wd,
    input  wire [10:0]   rc,            
    output reg           rv,            
    output reg  [W-1:0]  rd,
    output reg           fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_hostb_stage_hbc.sv


































module dsdv_hostb_stage_hbc #(
 parameter integer ENABLE=0, LOCAL_STAGE=255, LOCAL_RANK=4, PHASE_BOUND=0,
 parameter integer RETURN_LOCAL=0, RETURN_REQUIRE_KIT=1, VARIABLE_WORDS=0, ALLOW_RELOAD=0,
 parameter [47:0] RETURN_ARRIVAL_DEADLINE=48'hffffffffffff,
 parameter [63:0] CLOCK_RESET_ID=64'd0,
 parameter [47:0] BOOT_HEADER_EDGE=48'hffffffffffff,
 parameter [47:0] BOOT_COMMIT_EDGE=48'hffffffffffff
)(
 input wire ck,rst_n,job_active,starter_armed,
 input wire [1103:0] from_prev,local_ro,return_ro,
 input wire [76:0] status_t_host,input wire [53:0] status_t_kd,
 output wire [1103:0] to_local,next_ro,
 output wire [514:0] f_host,output wire [52:0] ks_descriptor,
 output wire [2:0] ks_slot,
 output reg fault);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_bsplit.sv




















module dsdv_idx_bsplit #(
    parameter integer BW = 513,
    parameter integer MUT = 0      
) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [BW-1:0]  i,       
    output reg  [BW-1:0]  o_s,     
    output reg  [BW-1:0]  o_i      
);

endmodule

module ot_s81sl_slice_iq #(
    parameter integer HB = 0,
    parameter integer DL = 4,
    parameter integer DR = 6,
    parameter integer DX = 6,
    parameter integer VQ_XMEM = 2,
    parameter integer VS_MUT = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [512:0] bo,
    output wire [512:0]    iq,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    output wire            fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r_w3.sv





module ot_s81sl_capc5r_w3 #(
    parameter integer MUT = 0
) (
    input wire [209:0] rt_w,
    input wire cfg_v,
    input wire [159:0] cfg_d,
    output wire [5:0] cw_s_v,
    output wire [71:0] cw_s_a,
    output wire [191:0] cw_s_d,
    output wire [3:0] cw_n_v,
    output wire [47:0] cw_n_a,
    output wire [127:0] cw_n_d,
    output wire fault,
    input wire ck_rt,
    input wire ck_cw,
    input wire ck_rn,
    input wire ck_rs,
    input wire rst_n_rt,
    input wire rst_n_cw,
    input wire rst_n_rn,
    input wire rst_n_rs
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/ot_s81_frs.sv




















module ot_s81_frs #(
    parameter integer NL  = 1,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [NL-1:0] f,     
    input  wire          fi,    
    output reg           fo     
);

endmodule

module ot_s81_frs0 (
    input  wire ck,
    input  wire rst_n,
    input  wire fi,
    output reg  fo
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv

















module ot_pdie_serdes_col #(parameter integer PMA_LAT = 4, parameter integer TXL = 2, parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck
);

endmodule







module ot_s81_pma_txm #(parameter integer LAT = 4) (
    input  wire          ck,
    input  wire          d_v,
    input  wire [543:0]  d,
    output wire [543:0]  pma_tx,
    output wire          pma_tck
);

endmodule

module ot_s81_pma_rxm #(parameter integer LAT = 4) (
    input  wire          pma_rck,
    input  wire [543:0]  pma_rx,
    output wire [543:0]  q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_link/ot_hbm3e_phy_v41x_aw30_e8p5_k.sv









module ot_hbm3e_phy_v41x_aw30_e8p5_k #(parameter integer MUT = 0, parameter integer TREFI_PB = 240) (
    input  wire clk,
    input  wire rst_n,
    input  wire [31:0] k_v,
    output wire [31:0] k_rdy,
    input  wire [959:0] k_addr,
    input  wire [127:0] k_len,
    input  wire [543:0] k_tag,
    input  wire [31:0] k_we,
    input  wire [8191:0] k_wdata,
    input  wire [1023:0] k_wstrb,
    output wire [31:0] k_wr_done,
    output wire [31:0] kr_v,
    input  wire [31:0] kr_rdy,
    output wire [543:0] kr_tag,
    output wire [127:0] kr_beat,
    output wire [8191:0] kr_data,
    output reg  k_oor
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv
module dsfd_rly_15_NS (input wire ck, input wire rs, input wire [14:0] i, output wire [14:0] o);

endmodule
module dsfd_rly_15_SW (input wire ck, input wire rs, input wire [14:0] i, output wire [14:0] o);

endmodule
module dsfd_rly_1_WN (input wire ck, input wire rs, input wire i, output wire o);

endmodule
module dsfd_rly_54_WN (input wire ck, input wire rs, input wire [53:0] i, output wire [53:0] o);

endmodule
module dsfd_rly_63_NW (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_63_SN (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_66_ES (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule

module dsfd_rly_66_EW (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
module dsfd_rly_66_NE (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
module dsfd_rly_66_NW (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
module dsfd_rly_66_WS (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv
module ot_dvrly_st #(parameter integer W = 276, parameter integer HC = 0) (input wire ck, input wire rs, input wire [W-1:0] i,
                                                                      output wire [W-1:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_276_EW (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_276_WE (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_276_NS (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_276_SN (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_512_EW (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_512_WE (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_562_EW (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_562_SN (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_562_WE (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_682_EW (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_682_NS (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_682_WE (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_70_NS (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_70_SN (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);

endmodule


module dsfd_dvrlyh_512_NS (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_512_SN (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);

endmodule
module dsfd_dvrlyh_562_NS (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/land/dsfd_dvland_pvrd.sv
























module dsfd_dvland_pvrd #(parameter integer MUT = 0) (
    input  wire          ck_f,
    input  wire [561:0]  i,
    input  wire          ck,
    input  wire          rs,
    input  wire [2:0]    k,
    input  wire [7:0]    nw,
    input  wire [9:0]    rb,
    output reg  [1103:0] o,
    output wire          fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv




module dsfd_dvland_70  (input wire ck_f, input wire [69:0]  i, input wire ck, input wire rs, input wire [2:0] k, output wire [69:0]  o, output wire fault);

endmodule
module dsfd_dvland_276 (input wire ck_f, input wire [275:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [275:0] o, output wire fault);

endmodule
module dsfd_dvland_512 (input wire ck_f, input wire [511:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [511:0] o, output wire fault);

endmodule
module dsfd_dvland_562 (input wire ck_f, input wire [561:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [561:0] o, output wire fault);

endmodule
module dsfd_dvland_682 (input wire ck_f, input wire [681:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [681:0] o, output wire fault);

endmodule
module dsfd_dvland_276l (input wire ck_f, input wire [275:0] i, input wire ck, input wire rs, input wire [5:0] k, output wire [275:0] o, output wire fault);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg3.sv
module dsfd_ctrl_rg3 #(
    parameter integer DQ  = 8,     
    parameter integer DR  = 8,     
    parameter integer RFD = 24,    
    parameter integer MUT = 0
) (
    input  wire           clk,
    input  wire           ckh,
    input  wire           rst_n,
    input  wire [681:0]   rq,
    output wire [561:0]   rd,
    output wire           ck_o,
    input  wire [91:0]    rrq,       
    output reg  [543:0]   rrd,       
    output wire [1:0]     k_v,
    input  wire [1:0]     k_rdy,
    output wire [59:0]    k_addr,
    output wire [7:0]     k_len,
    output wire [33:0]    k_tag,
    output wire [1:0]     k_we,
    output wire [511:0]   k_wdata,
    output wire [63:0]    k_wstrb,
    input  wire [1:0]     k_wr_done,
    input  wire [1:0]     kr_v,
    output wire [1:0]     kr_rdy,
    input  wire [33:0]    kr_tag,
    input  wire [7:0]     kr_beat,
    input  wire [511:0]   kr_data
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv



















module ot_s81_svc_job #(parameter integer JQ = 8, MUT = 0) (
    input  wire          ck, rs_n,
    input  wire [32:0]   j_cmd,          
    output reg  [1:0]    j_dn,           
    input  wire [514:0]  q,              
    output wire [514:0]  core_q,         
    input  wire [1025:0] ad,             
    input  wire [513:0]  xd,
    input  wire [513:0]  od
);

endmodule









module dsfd_svc_join #(parameter integer NS = 4, MUT = 0, EPMUT = 0) (
    input  wire             ck,     
    input  wire             rst,
    input  wire [84:0]      c_cmd,
    output wire [8:0]       c_done,
    output wire [1:0]       c_st,
    output reg  [33*NS-1:0] j_cmd,
    input  wire [2*NS-1:0]  j_dn
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv






















module ot_s81_su_sms #(
    parameter integer SM_NVMAX = 40, LM = 5, LA = 4, SRL = 2, MUT = 0
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire [3:0]    cfg_g,
    input  wire          j_st,
    input  wire [3:0]    j_kind,
    input  wire [7:0]    j_jid,
    input  wire          r_v,
    input  wire          r_p,
    input  wire [2:0]    r_j,
    input  wire [511:0]  r_d,
    output wire          w_v,
    output wire [13:0]   w_a,
    output wire [15:0]   w_m,
    output wire [511:0]  w_d,
    output wire          o_fu,
    output wire          o_fo,
    output wire          o_alive,
    output wire          o_den,
    output wire [7:0]    o_rjid
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv










module dsfd_svc_pc (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,          
    input  wire [340:0] qrq,          
    output reg  [340:0] rq,           
    input  wire [0:0]   rk,           
    output reg  [0:0]   qrk,          
    input  wire [0:0]   wd,
    output reg  [0:0]   qwd,
    input  wire [0:0]   rv,           
    input  wire [255:0] r_data,
    input  wire [16:0]  r_tag,
    input  wire [3:0]   r_beat,
    output reg  [0:0]   qrv,          
    output reg  [255:0] qr_data,
    output reg  [16:0]  qr_tag,
    output reg  [3:0]   qr_beat
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx.sv
































module dsdv_svc_sx #(
    parameter integer MUT = 0,
    parameter integer NR = 1,              
    parameter integer FX = 5,
    parameter integer F12 = 1,
    
    
    
    parameter logic [3:0] FM_GI = 4'hf, FM_GO = 4'hf, FM_SI = 4'hf, FM_SO = 4'hf
) (
    input  wire              ck,
    input  wire              rst,
    input  wire [3:0]        sid,
    input  wire              l_v,
    input  wire [2131:0]     l_d,
    input  wire [3:0]        gi_v,
    input  wire [4*2132-1:0] gi_d,
    output wire [3:0]        go_v,
    output wire [4*2132-1:0] go_d,
    input  wire [3:0]        si_v,
    input  wire [4*1076-1:0] si_d,
    output wire [3:0]        so_v,
    output wire [4*1076-1:0] so_d,
    output wire              rt_v,
    output wire [2131:0]     rt_d,
    output wire              t_v,
    output wire [19:0]       t_tag,
    output wire [127:0]      t_y,
    output wire [3:0]        t_f,
    output wire              fault
);

endmodule


module dsdv_sx_rly_in #(parameter integer F = 0) (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);

endmodule
module dsdv_sx_rly_out #(parameter integer F = 0) (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/sm_target/dsdv_sm_wire.sv


























module dsdv_svc_sot #(parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,          
    input  wire [3:0]   tile,           
    input  wire         q_v,
    input  wire [511:0] q_d,
    output reg          cfg_v,
    output reg  [19:0]  cfg_owner,
    output reg  [7:0]   cfg_se_jid, cfg_so_jid,
    output reg  [13:0]  cfg_obase,
    output reg  [15:0]  cfg_first, cfg_last, cfg_read, cfg_retire,
    output reg  [1:0]   route,
    output reg  [15:0]  gw_first, gw_last,
    output reg  [2:0]   fault_code
);

endmodule

module dsdv_sm_gw (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    head,
    input  wire          g_v,
    input  wire [6:0]    g_idx,
    input  wire [1023:0] g_d,
    input  wire [19:0]   g_owner,
    input  wire          g_group,
    output reg           gw_v,
    output reg  [512:0]  gw_d,
    output reg           fault
);

endmodule


module dsdv_sm_gx (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        cfg_v,          
    input  wire [1:0]  route,
    input  wire [15:0] gw_first, gw_last,
    input  wire        w_v,            
    output reg  [47:0] pv_x
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv





























































module ot_hdc_v41x_dly #(parameter integer W = 1, parameter integer D = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);

endmodule


module ot_hdc_v41x_vdly #(parameter integer D = 1) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);

endmodule








module ot_hdc_v41x_attn_bmul (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        pad,
    output reg  [31:0] y,
    output reg         flt
);

endmodule




module ot_hdc_v41x_attn_deq (
    input  wire [17:0] e,          
    output reg  [15:0] y,
    output reg         flt
);

endmodule






module ot_hdc_v41x_attn_chunk (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [8*32-1:0] p,
    input  wire [7:0]    pf,
    output wire [31:0]   y,
    output wire          f
);

endmodule






module ot_hdc_v41x_attn_hdp #(
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [TD-1:0]     we,
    input  wire [BW-1:0]     wbank,
    input  wire [TD*16-1:0]  wd,
    input  wire [8*BW-1:0]   sk_bank,
    input  wire [TD*18-1:0]  sk_b,
    output wire [31:0]       y,
    output wire              f
);

endmodule


module ot_hdc_v41x_attn_tile #(
    parameter integer H = 16,          
    parameter integer TD = 64,         
    parameter integer NBANK = 3,       
    parameter integer BW = 2,          
    parameter integer PWORDS = 1       
) (
    input  wire              clk,
    input  wire              rst_n,
    
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,   
    
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      oflt
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/v41x/ot_hdc_v41x_kreg.sv


(* keep_hierarchy *)
module ot_hdc_v41x_kreg #(
    parameter integer W = 1,
    parameter integer R = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/v41x/ot_hdc_v41x_attn.sv





































































module ot_hdc_v41x_attn_merge #(
    parameter integer H = 16,
    parameter integer DPT = 16,
    parameter integer MLEV = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,          
    input  wire              ifin,        
    input  wire [MLEV-1:0]   iblk,        
    input  wire [H*32-1:0]   iy,
    input  wire [H-1:0]      if_,
    output wire              ov,          
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      of_
);

endmodule

module ot_hdc_v41x_attn #(
    parameter integer H = 16,          
    parameter integer D = 512,         
    parameter integer TD = 64,         
    parameter integer NL = 4,          
    parameter integer TROWS = 640,     
    parameter integer SC_CRED = 64,     
    parameter integer PV_CRED = 64,    
    parameter bit SRAM_MACRO = 0,      
    parameter integer PWORDS = 1,      
    parameter integer ILV = 0,         
    parameter integer REPL = 0,        
                                       
                                       
                                       
                                       
                                       
    parameter integer PHYS = 0,        
    parameter integer NSTAGE = 1,      
                                       
    parameter integer MODES = 0        
                                       
                                       
                                       
                                       
) (
    input  wire                   clk,
    input  wire                   rst_n,
    
    input  wire                   job_v,
    input  wire [15:0]            job_t,
    output wire                   job_ready,
    
    input  wire                   q_v,
    input  wire [D*16-1:0]        q_w,
    output wire                   q_ready,
    
    input  wire                   kv_v,
    input  wire [NL-1:0]          kv_m,
    input  wire [NL*(D/32)*265-1:0] kv_w,
    output wire                   kv_ready,
    
    output reg                    sc_v,
    output reg  [15:0]            sc_row,
    output reg  [NL-1:0]          sc_m,
    output reg  [NL*H*32-1:0]     sc_y,
    output reg  [NL*H-1:0]        sc_f,
    input  wire                   sc_cr,
    
    input  wire                   p_v,
    input  wire [PWORDS*TD*16-1:0] p_w,
    output wire                   p_ready,
    
    output reg                    pv_v,
    output reg  [7:0]             pv_c,
    output reg  [NL*(D/TD)*H*32-1:0] pv_y,
    output reg  [NL*(D/TD)*H-1:0] pv_f,
    input  wire                   pv_cr,
    
    output wire                   qk_iss,
    output wire                   pv_iss
);

endmodule








module ot_hdc_v41x_attn_tr #(
    parameter integer TD = 64,
    parameter integer DPT = 16,
    parameter integer NL = 4,
    parameter integer XOFF = 0,
    parameter integer REPL = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              w_en_i,
    input  wire              w_half_i,
    input  wire [7:0]        w_cnt_i,
    input  wire [NL-1:0]     w_pad_i,
    input  wire [NL*265-1:0] w_g,
    input  wire              r_half_i,
    input  wire [7:0]        r_c_i,
    input  wire              sel_i,
    input  wire [TD*18-1:0]  qk_ib,
    output wire [TD*18-1:0]  col,
    output wire [TD*18-1:0]  eib
);

endmodule





module ot_hdc_v41x_attn_tr_phs #(
    parameter integer TD = 64, parameter integer DPT = 16, parameter integer NL = 4,
    parameter integer XOFF = 0, parameter integer REPL = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              w_en_i,
    input  wire              w_half_i,
    input  wire [7:0]        w_cnt_i,
    input  wire [NL-1:0]     w_pad_i,
    input  wire [NL*265-1:0] w_g,
    input  wire              r_half_i,
    input  wire [7:0]        r_c_i,
    input  wire              sel_i,
    input  wire [TD*18-1:0]  qk_ib,
    output wire [TD*18-1:0]  col,
    output reg  [TD*18-1:0]  eib
);

endmodule

module ot_hdc_v41x_attn_merge_phs #(
    parameter integer H = 16, parameter integer DPT = 16, parameter integer MLEV = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,
    input  wire              ifin,
    input  wire [MLEV-1:0]   iblk,
    input  wire [H*32-1:0]   iy,
    input  wire [H-1:0]      if_,
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      of_
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv



















module ot_hdc_v41x_attn_bmul_l #(
    parameter integer ML = 3
) (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        pad,
    output reg  [31:0] y,
    output reg         flt
);

endmodule






module ot_hdc_v41x_attn_chunk_l #(
    parameter integer FPL = 3
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [8*32-1:0] p,
    input  wire [7:0]    pf,
    output wire [31:0]   y,
    output wire          f
);

endmodule






module ot_hdc_v41x_attn_hdp_l #(
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer FPL = 3,
    parameter integer FML = 3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [TD-1:0]     we,
    input  wire [BW-1:0]     wbank,
    input  wire [TD*16-1:0]  wd,
    input  wire [8*BW-1:0]   sk_bank,
    input  wire [TD*18-1:0]  sk_b,
    output wire [31:0]       y,
    output wire              f
);

endmodule


module ot_hdc_v41x_attn_tile_l #(
    parameter integer H = 16,          
    parameter integer TD = 64,         
    parameter integer NBANK = 3,       
    parameter integer BW = 2,          
    parameter integer PWORDS = 1,      
    parameter integer FPL = 3,         
    parameter integer FML = 3          
) (
    input  wire              clk,
    input  wire              rst_n,
    
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,   
    
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      oflt
);

endmodule







module ot_hdc_v41x_qaddl #(
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

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv



module ot_hdc_v41x_attn_staging #(
    parameter integer D = 512,
    parameter integer NL = 4,
    parameter integer TROWS = 640,
    parameter bit SRAM_MACRO = 0
) (
    input  wire clk,
    input  wire [NL-1:0] wr_en,
    input  wire [$clog2((TROWS+NL-1)/NL)-1:0] wr_addr,
    input  wire [NL*(D/32)*265-1:0] wr_data,
    input  wire [$clog2((TROWS+NL-1)/NL)-1:0] rd_addr,
    output wire [NL*(D/32)*265-1:0] rd_data
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/sm_target/dsdv_sm_so_target.sv





module dsdv_sm_so_target #(
    parameter integer HEAD = 0,
    parameter integer MUT = 0
) (
    input wire clk, rst_n,
    input wire [3:0] head,
    input wire cfg_v,
    input wire [19:0] cfg_owner,
    input wire [7:0] cfg_se_jid, cfg_so_jid,
    input wire [13:0] cfg_obase,
    input wire [15:0] cfg_first, cfg_last, cfg_read, cfg_retire,
    input wire op_st,
    input wire [3:0] op_kind,
    input wire [7:0] op_jid,
    input wire w_v,
    input wire [13:0] w_a,
    input wire [15:0] w_m,
    input wire [511:0] w_d,
    input wire [11:0] w_st,
    output reg g_v,
    output reg [6:0] g_idx,
    output reg [1023:0] g_d,
    output reg [19:0] g_owner,
    output reg g_group,
    output reg retired,
    output reg retire_error,
    output reg [19:0] retire_owner,
    output wire fault,
    output reg [11:0] fault_code
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_pv_so_program.sv









module dsdv_pv_so_program #(parameter integer ENABLE=0, parameter integer TF=1)(
 input wire clk,rst_n,input wire[514:0]q,output wire[514:0]q_pass,
 output reg cfg_v,output reg[19:0]owner,output reg[20:0]position,output reg[7:0]se_jid,so_jid,
 output reg[15:0]local_first,peer_first,
 output reg param_v,output reg[2:0]param_row,output reg[19:0]param_owner,output reg[20:0]param_position,output reg[511:0]param_d,
 output reg launch,output reg fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress.sv



module dsdv_pv_so_ingress #(parameter integer ENABLE=0,HEADER_DEN=0)(
 input wire clk,rst_n,
 input wire cfg_v,input wire[19:0]cfg_owner,input wire[20:0]cfg_position,input wire[7:0]cfg_se_jid,cfg_so_jid,
 input wire pv_v,input wire[1:0]pv_quarter,input wire[512:0]pv_d,
 input wire param_v,input wire[2:0]param_row,input wire[19:0]param_owner,input wire[20:0]param_position,input wire[511:0]param_d,
 input wire den_v,input wire[15:0]den_mask,input wire[19:0]den_owner,input wire[7:0]den_jid,
 input wire launch,
 output wire q_v,output wire[511:0]q_d,output wire ready,done,
 output wire fault,output wire[11:0]fault_code
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_half_join.sv






module dsdv_pv_half_join(
 input wire clk,rst_n,input wire cfg_v,
 input wire[15:0]local_first,peer_first,
 input wire[561:0]local_pv,peer_pv,
 output reg pv_v,output reg[1:0]pv_quarter,output reg[512:0]pv_d,
 output reg fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/land/dsdv_svc_busland.sv


module dsdv_svc_busland_16 (input wire ck_f, input wire [15:0] i,
 input wire ck, input wire rs, input wire [2:0] k,
 output wire [15:0] o, output wire fault);

endmodule
module dsdv_svc_busland_514 (input wire ck_f, input wire [513:0] i,
 input wire ck, input wire rs, input wire [2:0] k,
 output wire [513:0] o, output wire fault);

endmodule
module dsdv_svc_busland_805 (input wire ck_f, input wire [804:0] i,
 input wire ck, input wire rs, input wire [2:0] k,
 output wire [804:0] o, output wire fault);

endmodule
module dsdv_svc_busland_1077 (input wire ck_f, input wire [1076:0] i,
 input wire ck, input wire rs, input wire [2:0] k,
 output wire [1076:0] o, output wire fault);

endmodule
module dsdv_svc_busland_2133 (input wire ck_f, input wire [2132:0] i,
 input wire ck, input wire rs, input wire [2:0] k,
 output wire [2132:0] o, output wire fault);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_local_n32_source4.sv



module dsdv_pv_local_land_n32_source4_276(
 input wire ck_f,input wire [275:0] i,input wire ck,rs,input wire [5:0] k,
 output wire [275:0] o,output wire fault);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_rg3_nq.sv




module dsdv_idx_rg3_nq #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,
    parameter integer IQD = 512,
    parameter integer SQD = 256,
    parameter integer LFD = 256,
    parameter integer EL = 124,
    parameter integer IH = 0,           
    parameter integer KR = 0            
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,
    input  wire [275:0]  si,
    output wire [275:0]  so,
    output wire [183:0]  rqo,
    input  wire [1087:0] rri,
    output wire          fault   
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_rg3.sv

























module dsdv_idx_rg3 #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,         
    parameter integer IQD = 512,        
    parameter integer SQD = 256,        
    parameter integer LFD = 256,        
    parameter integer EL = 124,         
    
    
    
    
    
    
    parameter integer OH = 2,
    parameter integer RH = 2,
    
    
    
    
    
    
    
    parameter integer IH = 0,
    parameter integer KR = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,           
    input  wire [512:0]  qi,
    output wire [512:0]  qo,
    input  wire [275:0]  si,
    output wire [275:0]  so,
    output reg  [183:0]  rqo,           
    input  wire [1087:0] rri,           
    
    
    output reg           fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_qfs.sv









module dsdv_idx_qfs #(
    parameter integer MUT = 0,       
    parameter integer SMUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [512:0]  qs,
    input  wire [512:0]  ql,
    output wire [512:0]  qr,
    output wire [257:0]  qc,
    output wire          fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_hostb_seqhost_mux.sv
























module dsdv_hostb_seqhost_mux #(parameter integer HOSTB_ENABLE=0, STATIC_KS6=0,
 parameter integer STATIC_KS_SPAN=0, parameter [31:0] STATIC_KS_GRAPH_TAG=0,
 parameter integer FMUT=0) (   
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input wire select_hbe,input wire [514:0] hbe_f_host,input wire [52:0] starter_f_ks,
    input wire [2:0] hbe_ks_slot,
    output wire [52:0] engram_f_ks,
    output wire hb_starter_armed,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    input  wire          sid_ri, vid_ri,   
    output wire          sid_ro, vid_ro,   
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l5f.sv







module dsdv_gunit_l5f #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          xe_v, input wire [31:0] xe_x, output reg ye_v, output reg [31:0] ye_y, output reg ye_f,
    input  wire          xd_v, input wire [31:0] xd_b, output reg yd_v, output reg [31:0] yd_y, output reg yd_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l5.sv
`define OT_S81_GUNIT_PIN_COPY 0
`define OT_S81_GUNIT_CONTROL_SAFE 0
`define OT_S81_GUNIT_Q4 0
`define OT_S81_GUNIT_FANOUT_SAFE 0
`define OT_S81_GUNIT_NAT32 0










module dsdv_gunit_l5 #(
    parameter integer MUT = 0,
    parameter integer PIN_COPY = `OT_S81_GUNIT_PIN_COPY,
    parameter integer CONTROL_SAFE = `OT_S81_GUNIT_CONTROL_SAFE,
    parameter integer Q4 = `OT_S81_GUNIT_Q4,
    parameter integer FANOUT_SAFE = `OT_S81_GUNIT_FANOUT_SAFE,
    
    parameter integer NAT32 = `OT_S81_GUNIT_NAT32
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          launch, input wire mx_v, input wire [4:0] mx_i, input wire [31:0] mx_y, input wire t_set, input wire t_w, input wire [9:0] t_row,
    input  wire [4:0]    t_lm, input wire [15:0] t_sm,
    
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [169:0] ct_b, output reg fault,
    
    output wire [275:0]  vo_n,  input wire [275:0] vi_n,
    
    output wire          xe_v, output wire [31:0] xe_x, input wire ye_v, input wire [31:0] ye_y, input wire ye_f,
    output wire          xd_v, output wire [31:0] xd_b, input wire yd_v, input wire [31:0] yd_y, input wire yd_f
);

endmodule

(* keep_hierarchy = 1 *) module dsdv_gunit_index5(input wire clk, input wire [4:0] d, output reg [4:0] q);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l4r.sv








module dsdv_gunit_l4r #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ss_v, input wire [31:0] ss, input wire [31:0] eps_c,
    output reg           r_v, output reg [31:0] r_y, output reg r_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l4.sv




























module dsdv_gunit_l4 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          g_v, input wire [3:0] g_i, input wire [4:0] g_acc, input wire [319:0] g_d,
    input  wire          j_v, input wire j_set, input wire j_w, input wire [9:0] j_row, input wire [4:0] j_lm,
    input  wire [15:0]   j_sm,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    
    output wire          hct_v, output wire [169:0] hct_b,
    output reg           mix_go_s, output reg launch_s, output reg fault,
    
    output wire [275:0]  rn_o,  input wire [275:0] rn_i,
    output reg           launch, output reg mx_v, output reg [4:0] mx_i, output reg [31:0] mx_y, output reg t_set, output reg t_w, output reg [9:0] t_row,
    output reg  [4:0]    t_lm, output reg [15:0] t_sm,
    output reg           cwo_v, output reg [7:0] cwo_a, output reg [255:0] cwo_d, output wire [3:0] sid_o,
    input  wire          hct5_v, input wire [169:0] hct5_b, input wire f5,
    
    output reg           ss_v, output reg [31:0] ss, output reg [31:0] eps_c,
    input  wire          r_v, input wire [31:0] r_y, input wire r_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l3.sv










module dsdv_gunit_l3 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    input  wire          rw_st, input wire rw_v, input wire rw_l, input wire [191:0] rw_x,   
    input  wire [31:0]   rw_scale, input wire [9:0] rw_row, input wire [4:0] rw_lm, input wire [15:0] rw_sm,
    input  wire [3:0]    sid_i,
    output reg           w_v, output reg [169:0] w_b, output reg fault,   
    
    output wire [275:0]  vo_s,  input wire [275:0] vi_s
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l2.sv
















module dsdv_gunit_l2 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    
    
    output reg           hp_av, output reg [243:40] hp_a, output reg hp_bv, output reg [243:40] hp_b,
    output wire          cwn_v, output wire [7:0] cwn_a, output wire [255:0] cwn_d, output wire [3:0] sidn,
    input  wire          hct_v, input wire [169:0] hct_b, input wire hf,
    
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    output wire          dl_av, output wire [236:0] dl_a, output wire dl_bv, output wire [236:0] dl_b,
    output wire          cws_v, output wire [7:0] cws_a, output wire [255:0] cws_d, output wire [3:0] sids,
    input  wire          rct_v, input wire [169:0] rct_b, input wire rf,
    
    input  wire [3:0]    sid,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d,   
    output reg           fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f.sv

















































(* keep_hierarchy *)
module dsdv_l1f_term8 (input wire [7:0] en, input wire [7:0] hit, output wire [7:0] p);

endmodule


(* keep_hierarchy *)
module dsdv_l1f_mux8 (input wire s, input wire [7:0] a, input wire [7:0] b, output wire [7:0] y);

endmodule


(* keep_hierarchy *)
module dsdv_l1f_or8 (input wire [7:0] a, output wire y);

endmodule



(* keep_hierarchy *)
module dsdv_l1f_wdec8 (
    input  wire [7:0]   en,
    input  wire [7:0]   hit,
    input  wire [127:0] d,
    output wire [1:0]   wh,
    output reg  [15:0]  wd
);

endmodule


(* keep_hierarchy *)
module dsdv_l1f_dec64 (input wire [5:0] a, output wire [63:0] y);

endmodule


(* keep_hierarchy *)
module dsdv_l1f_dec7 (input wire [2:0] a, output wire [6:0] y);

endmodule

module dsdv_gunit_l1f #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [5:0]    sa_r, input wire [223:0] sa_d, input wire [5:0] sb_r, input wire [223:0] sb_d,
    input  wire [13:0]   we,                 
    input  wire          c_go, input wire c_fw, input wire c_l, input wire [2:0] c_bn, input wire [4:0] c_lvn,
    input  wire          re, input wire [3:0] ra,                         
    input  wire [1:0]    bw_e, input wire [3:0] bw_a, input wire [255:0] bw_d, 
    
    input  wire          g_go, input wire [5:0] g_hit, input wire [41:0] g_a,  
    output reg           o_v, output reg o_f, output reg o_l, output reg o_g, output wire [244:0] o_d,   
    output reg           o_flt
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1c.sv























module dsdv_gunit_l1c #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    
    
    input  wire [0:0]    f_v, input wire [0:0] f_f, input wire [0:0] f_l, input wire [0:0] f_g,
    input  wire [4*245-1:0] f_d, input wire [3:0] f_flt,
    output reg           g_go, output reg [23:0] g_hit, output reg [41:0] g_a,
    
    output reg           i_v, output reg [53:0] i_ids,
    output reg           s_v, output reg [191:0] s_d,
    output reg           fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1.sv


































module dsdv_gunit_l1 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    
    
    
    input  wire          dl_av, input wire [236:0] dl_a, input wire dl_bv, input wire [236:0] dl_b,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [169:0] ct_b, output reg fault,
    
    output wire [275:0]  rs_o,  input wire [275:0] rs_i,
    output reg           rw_st, output reg rw_v, output reg rw_l, output reg [191:0] rw_x,
    output reg  [31:0]   rw_scale, output reg [9:0] rw_row, output reg [4:0] rw_lm, output reg [15:0] rw_sm,
    output reg  [3:0]    sid_o,
    input  wire          w_v, input wire [169:0] w_b, input wire f3,
    
    output reg  [5:0]    sa_r, output reg [223:0] sa_d, output reg [5:0] sb_r, output reg [223:0] sb_d,
    output reg  [55:0]   we, output reg c_go, output reg c_fw, output reg c_l, output reg [2:0] c_bn,
    output reg  [19:0]   c_lvn, output reg re, output reg [3:0] ra,
    output reg  [7:0]    bw_e, output reg [3:0] bw_a, output reg [255:0] bw_d,
    
    input  wire          i_v, input wire [53:0] i_ids, input wire gs_v, input wire [191:0] gs_d, input wire fc
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0r.sv


















module dsdv_gunit_l0r #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          wr_av, input wire [4:0] wr_agh, input wire [191:0] wr_ad,
    input  wire          wr_bv, input wire [4:0] wr_bgh, input wire [191:0] wr_bd, input wire wr_b,
    input  wire          go_a, input wire [4:0] go_acc, input wire go_b,
    output reg           r_v, output reg [3:0] r_i, output reg [4:0] r_acc, output reg [319:0] r_d, output reg r_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0.sv
































module dsdv_gunit_l0 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    
    input  wire          hp_av, input wire [243:40] hp_a, input wire hp_bv, input wire [243:40] hp_b,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output wire          hct_v, output wire [169:0] hct_b, output reg fault,
    
    output wire [275:0]  rn_o,  input wire [275:0] rn_i,
    output reg           g_v, output reg [3:0] g_i, output reg [4:0] g_acc, output reg [319:0] g_d,
    output reg           j_v, output reg j_set, output reg j_w, output reg [9:0] j_row, output reg [4:0] j_lm,
    output reg  [15:0]   j_sm,
    output reg           cwo_v, output reg [7:0] cwo_a, output reg [255:0] cwo_d, output wire [3:0] sid_o,
    input  wire          hct4_v, input wire [169:0] hct4_b, input wire mix_go, input wire launch, input wire f4,
    
    output reg           wr_av, output reg [4:0] wr_agh, output reg [191:0] wr_ad,
    output reg           wr_bv, output reg [4:0] wr_bgh, output reg [191:0] wr_bd, output reg wr_b,
    output reg           go_a, output reg [4:0] go_acc, output reg go_b,
    input  wire          r_v, input wire [3:0] r_i, input wire [4:0] r_acc, input wire [319:0] r_d, input wire r_f
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv
  `define OT_S81ENG_RR_SPLIT_NEEDS_N32

module dsdv_eng_rr_e #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer XQ_MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_en,
    input  wire          cfg_layer,
    input  wire [1:0]    cfg_rank,
    input  wire [52:0]   f_ks,
    
    
    
    
    
    
    output wire [38:0]   rco,
    input  wire [263:0]  pci,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    output reg  [3:0]    st,
    
    output wire [67:0]   hx_w,
    input  wire [1151:0] hx_res
);

endmodule


module dsdv_eng_rr_h0 (input wire ck, input wire [67:0] in_w, output wire [575:0] out_res);

endmodule

module dsdv_eng_rr_h1 (input wire ck, input wire [67:0] in_w, output wire [575:0] out_res);

endmodule






module dsdv_eng_rr_split #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer XQ_MUT = 0,
    parameter integer SPLIT_MUT = 0
) (
    input wire ck, input wire rst_n, input wire cfg_en, input wire cfg_layer, input wire [1:0] cfg_rank,
    input wire [52:0] f_ks, output wire [42:0] rco, input wire [267:0] pci,
    input wire [275:0] vi_s, output wire [275:0] vo_s, input wire [275:0] vi_n, output wire [275:0] vo_n,
    output wire [3:0] st
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv















































(* keep_hierarchy="yes" *)
module dsdv_tx_copy #(parameter integer W=1,RESET=0,ID=0)(
 input wire ck,rn,input wire[W-1:0]d,output wire[W-1:0]q);

endmodule




(* keep_hierarchy="yes" *)
module dsdv_tx_pop_pred #(parameter integer ID=0)(
 input wire any,armed,hdr_q,fin,wv,r_in,flush_ok,output wire pop);

endmodule
(* keep_hierarchy="yes" *)
module dsdv_tx_score_enable #(parameter integer ID=0)(
 input wire accept,onehot,output wire en);

endmodule
(* keep_hierarchy="yes" *)
module dsdv_tx_open_enable #(parameter integer BANK=0,ID=0)(
 input wire pop,inwin,target,output wire en);

endmodule
(* keep_hierarchy="yes" *)
module dsdv_tx_score_field #(parameter integer ID=0)(
 input wire ck,en,input wire[15:0]d,output wire[15:0]q);

endmodule
(* keep_hierarchy="yes" *)
module dsdv_tx_window_valid #(parameter integer ID=0)(
 input wire ck,open,acc,input wire[3:0]mask,output wire[3:0]q);

endmodule
(* keep_hierarchy="yes" *)
module dsdv_tx_window_addr #(parameter integer ID=0)(
 input wire ck,open,input wire[9:0]d,output wire[9:0]q);

endmodule
(* keep_hierarchy="yes" *)
module dsdv_tx_priority_mux #(parameter integer W=10,OFF=0,ID=0)(
 input wire ck,input wire[15:0]lvl_next,input wire[319:0]iw,output reg[W-1:0]q);

endmodule

module dsdv_idx_txm_n32 #(
    parameter integer D = 8192,
    parameter bit SRAM_MACRO = 0,
    
    
    
    
    parameter integer RDL = 0,
    parameter integer WDL = 0,
    
    
    
    parameter integer WDC = 0,
    parameter integer WCB = 5,
    
    
    
    parameter integer RIL = 0,
    parameter integer RIL_MUT = 0,  
    
    
    
    
    parameter integer SPLIT = 0
) (
    input  wire                 ck,
    input  wire                 re,
    input  wire [$clog2(D)-1:0] ra,
    output reg  [255:0]         rd,
    input  wire                 we,
    input  wire [$clog2(D)-1:0] wa,
    input  wire [255:0]         wd,
    input wire[255:0]wm,
    input wire[15:0]wm_next, 
    input  wire                 we_b,     
    input  wire [$clog2(D)-1:0] wa_b,
    input  wire [255:0]         wd_b
);

endmodule






module dsdv_idx_txm_grp #(
    parameter integer D = 8192,
    parameter integer B0 = 0,
    parameter integer NG = 5,
    parameter integer RDL = 1,
    parameter integer WDL = 1,
    parameter integer RIL = 1,
    parameter integer RIL_MUT = 0,
    
    
    
    
    parameter integer POUT = 0
) (
    input  wire                 ck,
    input  wire                 re,
    input  wire [$clog2(D)-1:0] ra,
    input  wire                 we,
    input  wire [$clog2(D)-1:0] wa,
    input  wire [255:0]         wd,
    input  wire [15:0]          wm_next,
    output reg  [255:0]         p
);

endmodule












module dsdv_idx_tx_n32 #(
    parameter integer V = 276,
    parameter integer IK = 4,
    parameter integer EK = 5,
    parameter integer UID = 8'h5C,
    parameter integer D = 8192,
    parameter integer IB = 64,
    parameter bit SRAM_MACRO = 0,
    parameter integer MUT = 0,
    parameter integer RDL = 0,      
    parameter integer WDL = 0,      
    parameter integer WDC = 0,      
    parameter integer SCS = 0,      
    parameter integer RIL = 0,      
    parameter integer RHP = 0,      
    parameter integer SPLIT = 0     
) (
    input  wire          ck,
    input  wire          rst,       
    input  wire [V-1:0]  vi,        
    input  wire [V-1:0]  vo,        
    output reg  [V-1:0]  lo,        
    output reg  [15:0]   st
);

endmodule



















module dsdv_bk_selids #(
    parameter integer V   = 276,
    parameter integer EK  = 5,
    parameter integer UID = 8'h5C,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,       
    input  wire [V-1:0]  vo,        
    output reg  [V-1:0]  o,         
    output reg           fault
);

endmodule













module dsdv_bk_sel_vmtx #(
    parameter integer V      = 276,
    parameter integer MUT    = 0,
    parameter integer TX_MUT = 0,
    parameter bit     TX_SRAM = 1,
    parameter integer SELE = 1,
    parameter integer SEL_MUT = 0,
    parameter integer IDX_MUT = 0,
    parameter integer VM_MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    input  wire [V-1:0]  vi_idx,
    input  wire [V-1:0]  ca,
    input  wire [V-1:0]  cb,
    output wire          fault,
    output wire [V-1:0]  tl_o,
    output wire [V-1:0]  tpn_o,
    output wire [V-1:0]  tps_o,
    input  wire [V-1:0]  tpn_i
);

endmodule


module dsdv_idx_vmux6 #(
    parameter integer V = 276,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [V-1:0]  i_r,
    input  wire [V-1:0]  i_s,
    input  wire [V-1:0]  i_a,
    input  wire [V-1:0]  i_b,
    input  wire [V-1:0]  i_n,
    input  wire [V-1:0]  i_l,
    output reg  [V-1:0]  o,
    output reg           fault
);

endmodule


module dsdv_idx_loop_lane3 #(parameter integer V=276, MUT=0)(
    input wire [V-1:0] i, output reg [V-1:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_col.sv















module dsdv_bk_col #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,       
    input  wire [7:0]    tap_k,       
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,        
    input  wire [V-1:0]  vi_s,        
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,        
    output wire [V-1:0]  vo_s,
    output wire          fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv
// hardened parameter set baked from the frame kit hard_params sidecar: EARLY=1, FAST=1, MTP=1, NB=2, PP=1, PQ=1, QM=5, QPIPE=1, QP_CAP=0, QP_CSAM=10, QP_P1=1, QP_XS=1, QS=5, QTIMING_FIX=1, QW=0, QX=10, QY=1, QZ=1, QZ_NE=4, QZ_NS=8, RSTP=1



















module ot_v41_rom_elem_q_qxpq_w10 #(
    parameter integer NB = 2,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer FRONT_PAR = 0,
    parameter integer QTIMING_FIX = 1,
    parameter integer QPIPE = 1,
    parameter integer QP_XS = 1,
    parameter integer QP_CAP = 0,
    parameter integer QP_P1 = 1,
    parameter integer QP_CSAM = 10,
    parameter integer QZ = 1,
    parameter integer QZ_NS = 8,
    parameter integer QZ_NE = 4,
    parameter integer QY = 1,
    parameter integer QX = 10,
    parameter integer PQ = 1,
    parameter integer QW = 0,
    parameter integer QM = 5,
    parameter integer QS = 5,          
    parameter integer RSTP = 1,        
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire [1:0]   go_tag,
    output wire         walking,
    output wire         bank_free,
    output wire         sh_free,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv





module ot_s81_sstn_payload536 (
    input wire ck, rs,
    input wire [535:0] i,
    output wire [535:0] o
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv











module ot_s81_sstn_base566 (
    input wire ck, rs,
    input wire [14:0] cci,
    input wire [282:0] xai,
    input wire [265:0] xbi,
    input wire [1:0] e0, e1, c0, c1, si,
    input wire nf,
    output wire [14:0] cc,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [1:0] so
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/v41die/ot_s81_cfg7_seq_bfp.sv
// hardened parameter set baked from the frame kit hard_params sidecar: LAYOUT=1, PINREG=1











module ot_s81_cfg7_seq_bfp #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer DELTA = 0,
    parameter integer LAYOUT = 1,
    parameter integer PINREG = 1) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [71:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    output wire [37:0]         f_prog
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/v41die/ot_s81_cfg7_seq.sv













































module ot_s81_cfg7_seq_local #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer PQ = 0,
    parameter integer LAYOUT = 0,
    parameter integer LOCAL_COPY = 0,
    parameter integer PINREG = 0,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    input  wire [1:0]          ef,          
    output wire [1:0]          go_tag,      
    output wire [6:0]          ce_local,
    output wire [5:0]          cfg_local,   
    output wire               go_local
);

endmodule






module ot_s81_cfg7_seq_bf_local #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer LAYOUT = 0,
    parameter integer LOCAL_COPY = 0,
    parameter integer PINREG = 0
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    output wire [6:0]          ce_local,
    output wire [5:0]          cfg_local,
    output wire               go_local
);

endmodule
// hardened parameter set baked from the frame kit hard_params sidecar: LAYOUT=1, PINREG=1, PQ=1


module ot_s81_cfg7_seq #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer PQ = 1,
    parameter integer LAYOUT = 1,
    parameter integer PINREG = 1,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    input  wire [1:0]          ef,          
    output wire [1:0]          go_tag       
);

endmodule


module ot_s81_cfg7_seq_bf #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer LAYOUT = 0,
    parameter integer PINREG = 0
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v




module ot_rom_4096x72_m8 #(parameter string VIAMAP = "", parameter string INSTANCE = "") (
    input  wire clk,
    input  wire ce_in,
    input  wire [11:0] addr_in,
    output reg  [71:0] rd_out
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/common/landed_parent/ot_pl_seam.sv













module ot_pl_seam_w #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      i,
    output wire [W-1:0]      q                          
);

endmodule

module ot_pl_seam_r #(
    parameter integer W = 1073, K = 2, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      d,                         
    output wire [W-1:0]      o                          
);

endmodule








module ot_pl_seam_w_pl #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      i,
    output wire [W-1:0]      q                          
);

endmodule

module ot_pl_seam_r_pl #(
    parameter integer W = 1073, K = 2, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      d,                         
    output wire [W-1:0]      o
);

endmodule















module ot_pl_seam_r_plq #(
    parameter integer W = 1073, K = 2, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,
    input  wire [W-1:0]      d,                         
    output wire [W-1:0]      o
);

endmodule









module ot_pl_seam_w_plr #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer RSREG = 1,                        
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] rsi,                       
    input  wire              rse,                       
    input  wire [W-1:0]      ir,                        
    output wire [W-1:0]      q                          
);

endmodule


module ot_pl_seam_cq #(
    parameter integer W = 1073, CHUNK_BITS = 24,
    parameter integer CHUNKS = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input  wire              ck,
    input  wire [CHUNKS-1:0] clr_n,
    input  wire [W-1:0]      d,
    output wire [W-1:0]      q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv
module dsfd_rly_63_WE (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_63_NS (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_63_WS (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_2_NS (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_15_SN (input wire ck, input wire rs, input wire [14:0] i, output wire [14:0] o);

endmodule
module dsfd_rly_63_NE (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_66_NS (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
module dsfd_rly_1_WE (input wire ck, input wire rs, input wire i, output wire o);

endmodule
module dsfd_rly_266_SN (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);

endmodule
module dsfd_rly_266_WE (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);

endmodule
module dsfd_rly_283_SN (input wire ck, input wire rs, input wire [282:0] i, output wire [282:0] o);

endmodule
module dsfd_rly_283_WE (input wire ck, input wire rs, input wire [282:0] i, output wire [282:0] o);

endmodule
module dsfd_rly_2_ES (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_2_EW (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_2_WE (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_2_WS (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_54_EW (input wire ck, input wire rs, input wire [53:0] i, output wire [53:0] o);

endmodule
module dsfd_rly_2_NW (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_2_SN (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_63_WN (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_66_SN (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
module dsfd_rly_1_EW (input wire ck, input wire rs, input wire i, output wire o);

endmodule
module dsfd_rly_63_SE (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
module dsfd_rly_2_NE (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);

endmodule
module dsfd_rly_68_EW (input wire ck, input wire rs, input wire [67:0] i, output wire [67:0] o);

endmodule
module dsfd_rly_15_EN (input wire ck, input wire rs, input wire [14:0] i, output wire [14:0] o);

endmodule
module dsfd_rly_63_ES (input wire ck, input wire rs, input wire [62:0] i, output wire [62:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv
module dsfd_rly_536_SN (input wire ck, input wire rs, input wire [535:0] i, output wire [535:0] o);

endmodule
module dsfd_rly_536_SW (input wire ck, input wire rs, input wire [535:0] i, output wire [535:0] o);

endmodule
module dsfd_rly_536_WS (input wire ck, input wire rs, input wire [535:0] i, output wire [535:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv

module dsfd_rly_38_WN (input wire ck, input wire rs, input wire [37:0] i, output wire [37:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv
module dsfd_rly_283_EW (input wire ck, input wire rs, input wire [282:0] i, output wire [282:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters_266ew.sv
module dsfd_rly_266_EW (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv
module dsfd_qbank_S (
    input wire [0:0] ck,
    input wire [53:0] i_cfg,
    input wire [0:0] i_go,
    input wire [282:0] i_x0,
    input wire [265:0] i_x1,
    output wire [53:0] o_cfg,
    output wire [0:0] o_go,
    output wire [282:0] o_x0,
    output wire [265:0] o_x1,
    input wire [0:0] rs
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv
module dsfd_qbank_N (
    input wire [0:0] ck,
    output wire [62:0] d_r0,
    output wire [62:0] d_r1,
    output wire [1:0] d_st,
    input wire [62:0] e_r0,
    input wire [62:0] e_r1,
    input wire [1:0] e_st,
    input wire [0:0] rs
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv
module dsfd_node_NNfu (
    input wire [65:0] a,
    input wire [65:0] b,
    input wire [0:0] clk,
    input wire [0:0] fi,
    output wire [0:0] fo,
    output wire [65:0] o,
    input wire [0:0] rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfd.sv
module dsfd_node_NNfd (
    input wire [65:0] a,
    input wire [65:0] b,
    input wire [0:0] clk,
    input wire [0:0] fi,
    output wire [0:0] fo,
    output wire [65:0] o,
    input wire [0:0] rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfu.sv
module dsfd_node_LLfu (
    input wire [62:0] a,
    input wire [62:0] b,
    input wire [0:0] clk,
    input wire [0:0] fi,
    output wire [0:0] fo,
    output wire [65:0] o,
    input wire [0:0] rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfd.sv
module dsfd_node_LLfd (
    input wire [62:0] a,
    input wire [62:0] b,
    input wire [0:0] clk,
    input wire [0:0] fi,
    output wire [0:0] fo,
    output wire [65:0] o,
    input wire [0:0] rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLd.sv
module dsfd_node_LLd (
    input wire [62:0] a,
    input wire [62:0] b,
    input wire [0:0] clk,
    output wire [0:0] fo,
    output wire [65:0] o,
    input wire [0:0] rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv
`define DSFD_BF_SOQ 0
`define DSFD_BF_SOQ_SWD 160
`define DSFD_BF_N32 0
module dsfd_bf_front_roots #(parameter INSTANCE = "") (
    output wire [775:0] c0,
    output wire [775:0] c1,
    input  wire qy0,
    input  wire qy1,
    input  wire [282:0] x0,
    input  wire [265:0] x1,
    input  wire go,
    input  wire [53:0] cfg,
    output wire [1:0] st,
    input  wire ck,
    input  wire rs,
    input wire [1023:0] xb_data,
    input wire [43:0] xb_meta,
    input wire [37:0] f_prog,
    input wire io_clk,
    input wire io_n,io_w,io_e
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv





module dsfd_bf_col #(parameter INSTANCE = "", parameter integer MB = 0) (
    input  wire [775:0] ci,
    output wire [0:0] qy,
    input  wire [0:0] ck,
    input  wire [0:0] rs,
    output wire [62:0] r
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv
module dsfd_rstg (
    input wire [0:0] ck,
    input wire [65:0] i,
    output wire [65:0] o,
    input wire [0:0] rs
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/dsfd_rly_masters_c26l.sv
module dsfd_rly_536_EN (input wire ck, input wire rs, input wire [535:0] i, output wire [535:0] o);

endmodule
module dsfd_rly_66_SW (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
module dsfd_rly_66_EN (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_glue/ot_s81_rly.sv
module ot_s81_rly #(
    parameter int W = 63,
    parameter int RSREG = 0
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);

endmodule





module ot_s81_rly_k #(
    parameter int W = 63,
    parameter int RSREG = 0,
    parameter int ID = 0
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);

endmodule

module ot_s81_rly_rq #(
    parameter int ID = 0
) (
    input  wire ck,
    input  wire rs,
    output wire q
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/lib/ot_reset_sync.sv


module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2,
    parameter integer OUTPUT_COPIES = 1,
    
    
    
    parameter integer TREE = 0
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv
module dsfd_cfifo_crs4 (
    output wire [14:0] cc,
    input wire cr,
    input wire cr_s,
    output wire [69:0] rd,
    input wire [65:0] ri,
    output wire rs,
    input wire rst,
    input wire [1:0] st,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [535:0] x2,
    input wire [275:0] xl0,      
    input wire [275:0] xl1,      
    input wire [275:0] xl2,      
    input wire [275:0] xl3,      
    input wire [3:0] xk,         
    input wire [11:0] lk         
);

endmodule
// ---- interface of /srv/opentallas-scratch2/claude/tok-sched/s81_srcgraph/v10/physical/die_plan/s81/bind/models/cells_used.v

module BUFx8_ASAP7_75t_R (input A, output Y);

endmodule
module INVx2_ASAP7_75t_R (input A, output Y);

endmodule
module ICGx4_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK);

endmodule
