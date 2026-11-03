module hbm_arch_q_b113_storeA_regional4 (
    input  wire clk,
    input  wire arst_n,
    input wire [3:0] strap_u_sfucore_Q_lane14_map_lane_j,    
    input wire [3:0] strap_u_sfucore_Q_lane15_map_lane_j,    
    output wire rst_o_0,    
    output wire rst_o_1,    
    input  wire [4:0] L127_i,    
    input  wire [514:0] L54_i,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4,    
    input  wire [32:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5,    
    input  wire [514:0] xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0,    
    input  wire [514:0] xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1,    
    input  wire [514:0] xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2,    
    input  wire [2:0] xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0,    
    input  wire [2:0] xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1,    
    input  wire [2:0] xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2,    
    input  wire [471:0] xi_u_sfucore_Q_ctl_u_core_procdff_66936_D,    
    input  wire [1742:0] xi_u_sfucore_Q_ctl_u_core_procdff_66941_D,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8,    
    input  wire [1:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9,    
    input  wire [32:0] xi_u_sfucore_Q_lane14_lane_vi_q,    
    input  wire [32:0] xi_u_sfucore_Q_lane15_lane_vi_q,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__0,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__1,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__10,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__11,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__12,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__13,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__2,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__3,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__4,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__5,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__6,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__7,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__8,    
    input  wire [96:0] xi_u_sfucore_Q_opstore_a_cmd1_D__9,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__0,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__1,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__10,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__11,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__12,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__13,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__2,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__3,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__4,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__5,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__6,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__7,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__8,    
    input  wire [8:0] xi_u_sfucore_Q_opstore_a_cmd2_D__9,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__0,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__1,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__10,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__11,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__12,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__13,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__2,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__3,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__4,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__5,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__6,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__7,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__8,    
    input  wire [4:0] xi_u_sfucore_Q_opstore_a_cmd3_D__9,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__0,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__1,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__10,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__11,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__12,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__13,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__2,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__3,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__4,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__5,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__6,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__7,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__8,    
    input  wire [24:0] xi_u_sfucore_Q_opstore_b_cmd3_D__9,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__0,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__1,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__10,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__11,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__12,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__13,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__2,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__3,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__4,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__5,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__6,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__7,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__8,    
    input  wire [32:0] xi_u_sfucore_Q_opstore_b_cmd4_D__9,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__0,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__1,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__10,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__11,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__12,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__13,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__2,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__3,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__4,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__5,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__6,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__7,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__8,    
    input  wire [1:0] xi_u_sfucore_Q_opstore_b_cmd6_D__9,    
    output wire [596:0] L47_o,    
    output wire [1662:0] L730_o,    
    output wire [596:0] L731_o,    
    output wire [1:0] xo_u_sfucore_Q_ctl_u_core_procdff_66891_Q,    
    output wire [8:0] xo_u_sfucore_Q_ctl_u_core_procdff_66896_Q,    
    output wire [8:0] xo_u_sfucore_Q_ctl_u_core_procdff_66901_Q,    
    output wire [256:0] xo_u_sfucore_Q_ctl_u_core_procdff_66906_Q,    
    output wire [256:0] xo_u_sfucore_Q_ctl_u_core_procdff_66911_Q,    
    output wire [34:0] xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__0,    
    output wire [34:0] xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__1,    
    output wire [562:0] xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__0,    
    output wire [562:0] xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__1,    
    output wire [1022:0] xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__0,    
    output wire [1022:0] xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__1,    
    output wire [24:0] xo_u_sfucore_Q_lane14_lane_kv_waddr,    
    output wire [32:0] xo_u_sfucore_Q_lane14_lane_kv_wdata,    
    output wire [1:0] xo_u_sfucore_Q_lane14_lane_kv_we,    
    output wire [24:0] xo_u_sfucore_Q_lane14_lane_vi_addr,    
    output wire [1:0] xo_u_sfucore_Q_lane14_lane_vi_re,    
    output wire [24:0] xo_u_sfucore_Q_lane15_lane_kv_waddr,    
    output wire [32:0] xo_u_sfucore_Q_lane15_lane_kv_wdata,    
    output wire [1:0] xo_u_sfucore_Q_lane15_lane_kv_we,    
    output wire [24:0] xo_u_sfucore_Q_lane15_lane_vi_addr,    
    output wire [1:0] xo_u_sfucore_Q_lane15_lane_vi_re,    
    output wire [256:0] xo_u_sfucore_Q_opstore_a_cmd0_Q__0,    
    output wire [320:0] xo_u_sfucore_Q_opstore_a_cmd0_Q__1,    
    output wire [256:0] xo_u_sfucore_Q_opstore_b_cmd0_Q__0,    
    output wire [320:0] xo_u_sfucore_Q_opstore_b_cmd0_Q__1,    
    input  wire [20:0] L106x7_i,    
    output wire [20:0] L106x7_o,    
    input  wire [7:0] L125x1_i,    
    output wire [7:0] L125x1_o    
);
    wire [3:0] L127_i_q;
    wire L127_i_eq;
    wire [513:0] L54_i_q;
    wire L54_i_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4_eq;
    wire [31:0] xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5_eq;
    wire [513:0] xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0_eq;
    wire [513:0] xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1_eq;
    wire [513:0] xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2_eq;
    wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0_eq;
    wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1_eq;
    wire [1:0] xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2_eq;
    wire [470:0] xi_u_sfucore_Q_ctl_u_core_procdff_66936_D_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66936_D_eq;
    wire [1741:0] xi_u_sfucore_Q_ctl_u_core_procdff_66941_D_q;
    wire xi_u_sfucore_Q_ctl_u_core_procdff_66941_D_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8_eq;
    wire [0:0] xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9_q;
    wire xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9_eq;
    wire [31:0] xi_u_sfucore_Q_lane14_lane_vi_q_q;
    wire xi_u_sfucore_Q_lane14_lane_vi_q_eq;
    wire [31:0] xi_u_sfucore_Q_lane15_lane_vi_q_q;
    wire xi_u_sfucore_Q_lane15_lane_vi_q_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__0_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__0_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__1_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__1_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__10_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__10_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__11_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__11_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__12_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__12_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__13_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__13_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__2_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__2_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__3_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__3_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__4_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__4_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__5_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__5_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__6_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__6_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__7_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__7_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__8_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__8_eq;
    wire [95:0] xi_u_sfucore_Q_opstore_a_cmd1_D__9_q;
    wire xi_u_sfucore_Q_opstore_a_cmd1_D__9_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__0_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__0_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__1_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__1_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__10_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__10_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__11_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__11_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__12_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__12_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__13_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__13_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__2_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__2_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__3_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__3_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__4_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__4_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__5_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__5_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__6_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__6_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__7_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__7_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__8_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__8_eq;
    wire [7:0] xi_u_sfucore_Q_opstore_a_cmd2_D__9_q;
    wire xi_u_sfucore_Q_opstore_a_cmd2_D__9_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__0_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__0_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__1_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__1_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__10_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__10_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__11_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__11_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__12_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__12_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__13_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__13_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__2_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__2_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__3_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__3_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__4_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__4_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__5_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__5_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__6_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__6_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__7_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__7_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__8_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__8_eq;
    wire [3:0] xi_u_sfucore_Q_opstore_a_cmd3_D__9_q;
    wire xi_u_sfucore_Q_opstore_a_cmd3_D__9_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__0_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__0_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__1_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__1_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__10_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__10_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__11_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__11_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__12_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__12_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__13_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__13_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__2_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__2_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__3_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__3_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__4_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__4_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__5_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__5_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__6_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__6_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__7_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__7_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__8_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__8_eq;
    wire [23:0] xi_u_sfucore_Q_opstore_b_cmd3_D__9_q;
    wire xi_u_sfucore_Q_opstore_b_cmd3_D__9_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__0_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__0_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__1_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__1_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__10_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__10_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__11_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__11_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__12_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__12_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__13_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__13_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__2_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__2_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__3_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__3_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__4_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__4_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__5_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__5_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__6_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__6_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__7_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__7_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__8_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__8_eq;
    wire [31:0] xi_u_sfucore_Q_opstore_b_cmd4_D__9_q;
    wire xi_u_sfucore_Q_opstore_b_cmd4_D__9_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__0_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__0_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__1_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__1_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__10_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__10_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__11_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__11_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__12_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__12_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__13_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__13_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__2_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__2_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__3_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__3_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__4_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__4_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__5_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__5_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__6_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__6_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__7_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__7_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__8_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__8_eq;
    wire [0:0] xi_u_sfucore_Q_opstore_b_cmd6_D__9_q;
    wire xi_u_sfucore_Q_opstore_b_cmd6_D__9_eq;
    wire [0:0] w_u_core_u_engine_u_memory_auto_proc_dff_cc_220_proc_dff_66978_Y;
    wire [0:0] w_u_core_u_engine_u_memory_auto_proc_dff_cc_220_proc_dff_66983_Y;
    wire [0:0] w_u_core_u_engine_u_memory_logic_not_ot_hgi_sfu_static_operand_store_sp2_sv_47_8078_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_auto_proc_dff_cc_220_proc_dff_66954_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_auto_proc_dff_cc_220_proc_dff_66959_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8764_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8766_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8768_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8770_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8772_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8774_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8776_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8778_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_74_8780_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_74_8782_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8119_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8123_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8124_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8128_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8129_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8133_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8134_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8138_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8139_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8143_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8144_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8148_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8149_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8153_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8154_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8158_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8159_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8163_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8164_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8168_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8169_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8173_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8174_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8178_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8179_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8183_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8184_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8188_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8189_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8193_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8194_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8198_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8199_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8203_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8204_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8208_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8209_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8213_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8214_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8218_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8219_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8223_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8224_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8228_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8229_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8233_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8234_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8238_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8239_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8243_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8244_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8248_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8249_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8253_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8254_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8258_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8259_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8263_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8264_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8268_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8269_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8273_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8274_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8278_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8279_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8283_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8284_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8288_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8289_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8293_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8294_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8298_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8299_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8303_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8304_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8308_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8309_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8313_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8314_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8318_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8319_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8323_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8324_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8328_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8329_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8333_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8334_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8338_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8339_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8343_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8344_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8348_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8349_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8353_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8354_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8358_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8359_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8363_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8364_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8368_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8369_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8373_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8374_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8378_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8379_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8383_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8384_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8388_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8389_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8393_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8394_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8398_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8399_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8403_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8404_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8408_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8409_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8413_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8414_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8418_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8419_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8423_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8424_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8428_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8429_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8433_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8434_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8438_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8477_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8495_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8513_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8531_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8549_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8567_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8585_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8603_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8621_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8639_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8657_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8675_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8693_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8711_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8729_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8747_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8479_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8481_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8483_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8485_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8487_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8489_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8491_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8493_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8497_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8499_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8501_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8503_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8505_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8507_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8509_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8511_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8515_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8517_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8519_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8521_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8523_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8525_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8527_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8529_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8533_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8535_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8537_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8539_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8541_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8543_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8545_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8547_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8551_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8553_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8555_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8557_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8559_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8561_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8563_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8565_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8569_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8571_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8573_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8575_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8577_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8579_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8581_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8583_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8587_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8589_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8591_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8593_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8595_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8597_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8599_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8601_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8605_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8607_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8609_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8611_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8613_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8615_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8617_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8619_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8623_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8625_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8627_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8629_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8631_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8633_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8635_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8637_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8641_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8643_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8645_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8647_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8649_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8651_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8653_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8655_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8659_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8661_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8663_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8665_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8667_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8669_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8671_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8673_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8677_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8679_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8681_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8683_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8685_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8687_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8689_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8691_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8695_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8697_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8699_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8701_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8703_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8705_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8707_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8709_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8713_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8715_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8717_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8719_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8721_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8723_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8725_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8727_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8731_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8733_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8735_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8737_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8739_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8741_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8743_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8745_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8749_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8751_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8753_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8755_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8757_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8759_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8761_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8763_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8765_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8767_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8769_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8771_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8773_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8775_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8777_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8779_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_74_8781_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_74_8783_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8785_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8787_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8789_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8791_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8793_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8795_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8797_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8799_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8801_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8803_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8805_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8807_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8809_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8811_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8813_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8815_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8817_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8819_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8821_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8823_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8825_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8827_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8829_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8831_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8833_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8835_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8837_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8839_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8841_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8843_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8845_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8847_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8849_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8851_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8853_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8855_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8857_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8859_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8861_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8863_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8865_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8867_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8869_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8871_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8873_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8875_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8877_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8879_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8881_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8883_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8885_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8887_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8889_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8891_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8893_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8895_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8897_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8899_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8901_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8903_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8905_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8907_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8909_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8911_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8920_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8921_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8922_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8923_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8924_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8925_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8926_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8927_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8928_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8929_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8930_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8931_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8932_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8933_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8934_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8935_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9034_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9035_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9036_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9037_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9038_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9039_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9040_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9041_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9042_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9043_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9044_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9045_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9046_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9047_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9048_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9049_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9148_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9149_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9150_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9151_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9152_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9153_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9154_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9155_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9156_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9157_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9158_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9159_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9160_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9161_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9162_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9163_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9262_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9263_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9264_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9265_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9266_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9267_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9268_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9269_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9270_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9271_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9272_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9273_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9274_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9275_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9276_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9277_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_56_8099_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8120_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8125_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8130_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8135_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8140_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8145_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8150_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8155_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8160_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8165_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8170_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8175_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8180_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8185_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8190_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8195_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8200_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8205_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8210_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8215_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8220_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8225_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8230_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8235_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8240_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8245_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8250_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8255_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8260_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8265_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8270_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8275_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8280_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8285_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8290_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8295_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8300_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8305_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8310_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8315_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8320_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8325_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8330_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8335_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8340_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8345_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8350_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8355_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8360_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8365_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8370_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8375_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8380_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8385_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8390_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8395_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8400_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8405_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8410_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8415_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8420_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8425_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8430_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8435_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8478_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8482_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8486_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8490_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8496_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8500_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8504_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8508_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8514_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8518_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8522_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8526_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8532_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8536_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8540_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8544_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8550_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8554_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8558_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8562_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8568_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8572_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8576_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8580_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8586_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8590_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8594_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8598_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8604_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8608_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8612_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8616_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8622_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8626_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8630_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8634_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8640_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8644_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8648_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8652_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8658_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8662_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8666_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8670_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8676_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8680_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8684_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8688_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8694_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8698_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8702_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8706_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8712_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8716_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8720_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8724_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8730_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8734_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8738_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8742_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8748_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8752_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8756_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8760_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_80_8913_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8122_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8127_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8132_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8137_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8142_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8147_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8152_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8157_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8162_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8167_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8172_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8177_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8182_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8187_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8192_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8197_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8202_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8207_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8212_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8217_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8222_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8227_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8232_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8237_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8242_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8247_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8252_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8257_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8262_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8267_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8272_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8277_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8282_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8287_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8292_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8297_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8302_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8307_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8312_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8317_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8322_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8327_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8332_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8337_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8342_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8347_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8352_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8357_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8362_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8367_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8372_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8377_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8382_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8387_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8392_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8397_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8402_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8407_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8412_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8417_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8422_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8427_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8432_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8437_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8914_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8915_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8917_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8121_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8126_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8131_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8136_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8141_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8146_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8151_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8156_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8161_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8166_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8171_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8176_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8181_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8186_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8191_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8196_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8201_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8206_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8211_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8216_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8221_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8226_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8231_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8236_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8241_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8246_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8251_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8256_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8261_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8266_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8271_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8276_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8281_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8286_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8291_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8296_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8301_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8306_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8311_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8316_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8321_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8326_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8331_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8336_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8341_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8346_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8351_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8356_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8361_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8366_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8371_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8376_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8381_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8386_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8391_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8396_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8401_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8406_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8411_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8416_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8421_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8426_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8431_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8436_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8784_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8786_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8788_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8790_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8792_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8794_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8796_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8798_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8800_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8802_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8804_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8806_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8808_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8810_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8812_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8814_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8816_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8818_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8820_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8822_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8824_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8826_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8828_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8830_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8832_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8834_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8836_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8838_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8840_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8842_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8844_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8846_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8848_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8850_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8852_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8854_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8856_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8858_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8860_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8862_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8864_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8866_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8868_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8870_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8872_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8874_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8876_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8878_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8880_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8882_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8884_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8886_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8888_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8890_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8892_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8894_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8896_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8898_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8900_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8902_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8904_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8906_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8908_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8910_Y;
    wire [3:0] w_u_core_u_engine_u_memory_u_store_or_ot_hgi_sfu_static_operand_store_sv_56_8100_Y;
    wire [511:0] w_u_core_u_engine_u_memory_u_store_procdff_66942_Q;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procdff_66943_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66944_Q;
    wire [511:0] w_u_core_u_engine_u_memory_u_store_procdff_66945_Q;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procdff_66946_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66947_Q;
    wire [511:0] w_u_core_u_engine_u_memory_u_store_procdff_66948_Q;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procdff_66949_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66950_Q;
    wire [511:0] w_u_core_u_engine_u_memory_u_store_procdff_66951_Q;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procdff_66952_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66953_Q;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procdff_66958_Q;
    wire [3:0] w_u_core_u_engine_u_memory_u_store_procdff_66963_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66964_Q;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procdff_66965_Q;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procdff_66966_Q;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procdff_66967_Q;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procdff_66968_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66969_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66970_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66971_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procdff_66972_Q;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55855_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55857_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55859_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55861_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55863_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55865_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55867_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55869_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55871_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55873_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55875_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55877_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55879_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55881_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55883_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55885_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55887_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55889_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55891_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55893_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55895_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55897_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55899_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55901_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55903_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55905_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55907_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55909_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55911_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55913_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55915_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55917_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55919_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55921_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55923_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55925_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55927_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55929_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55931_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55933_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55935_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55937_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55939_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55941_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55943_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55945_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55947_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55949_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55951_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55953_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55955_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55957_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55959_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55961_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55963_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55965_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55967_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55969_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55971_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55973_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55975_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55977_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55979_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_55981_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_55983_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_55986_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_55989_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_55992_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_55995_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_55998_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56001_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56004_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56007_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56010_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56013_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56016_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56019_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56022_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56025_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56028_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56031_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56034_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56037_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56040_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56043_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56046_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56049_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56052_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56055_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56058_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56061_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56064_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56067_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56070_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56073_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56076_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56079_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56082_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56085_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56088_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56091_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56094_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56097_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56100_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56103_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56106_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56109_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56112_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56115_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56118_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56121_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56124_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56127_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56130_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56133_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56136_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56139_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56142_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56145_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56148_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56151_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56154_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56157_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56160_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56163_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56166_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56169_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56172_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56175_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56178_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56181_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56184_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56187_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56190_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56193_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56196_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56199_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56202_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56205_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56208_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56211_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56214_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56217_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56220_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56223_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56226_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56229_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56232_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56235_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56238_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56241_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56244_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56247_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56250_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56253_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56256_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56259_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56262_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56265_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56268_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56271_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56274_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56277_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56280_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56283_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56286_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56289_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56292_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56295_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56298_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56301_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56304_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56307_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56310_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56313_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56316_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56319_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56322_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56325_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56328_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56331_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56334_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56337_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56340_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56343_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56346_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56349_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56352_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56355_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56358_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56361_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56364_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56367_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56370_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56373_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56376_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56379_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56382_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56385_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56388_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56391_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56394_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56397_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56400_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56403_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56406_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56409_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56412_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56415_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56418_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56421_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56424_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56427_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56430_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56433_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56436_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56439_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56442_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56445_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56448_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56451_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56454_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56457_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56460_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56463_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56466_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56469_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56472_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56475_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56478_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56481_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56484_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56487_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56490_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56493_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56496_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56499_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56502_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56505_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56508_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56511_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56514_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56517_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56520_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56523_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56526_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56529_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56532_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56535_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56538_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56541_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56544_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56547_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56550_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56553_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56556_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56559_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56562_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56565_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56568_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56571_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56574_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56577_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56580_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56583_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56586_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56589_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56592_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56595_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56598_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56601_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56604_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56607_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56610_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56613_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56616_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56619_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56622_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56625_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56628_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56631_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56634_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_procmux_56637_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_56639_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_56641_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_56643_Y;
    wire [31:0] w_u_core_u_engine_u_memory_u_store_procmux_56645_Y;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procmux_56647_Y;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procmux_56649_Y;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procmux_56651_Y;
    wire [23:0] w_u_core_u_engine_u_memory_u_store_procmux_56653_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8476_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8494_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8512_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8530_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8548_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8566_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8584_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8602_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8620_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8638_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8656_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8674_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8692_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8710_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8728_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8746_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8480_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8484_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8488_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8492_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8498_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8502_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8506_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8510_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8516_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8520_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8524_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8528_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8534_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8538_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8542_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8546_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8552_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8556_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8560_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8564_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8570_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8574_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8578_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8582_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8588_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8592_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8596_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8600_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8606_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8610_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8614_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8618_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8624_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8628_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8632_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8636_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8642_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8646_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8650_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8654_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8660_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8664_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8668_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8672_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8678_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8682_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8686_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8690_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8696_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8700_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8704_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8708_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8714_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8718_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8722_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8726_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8732_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8736_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8740_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8744_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8750_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8754_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8758_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8762_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_81_8916_Y;
    wire [0:0] w_u_core_u_engine_u_memory_u_store_u_output_flt;
    wire [511:0] w_u_core_u_engine_u_memory_u_store_u_output_sr_d;
    wire [1:0] w_u_core_u_engine_u_memory_u_store_u_output_sr_rv;
    wire [0:0] w_u_sfucore_Q_lane14_lane_coll;
    wire [0:0] w_u_sfucore_Q_lane14_lane_fault;
    wire [23:0] w_u_sfucore_Q_lane14_lane_kv_waddr;
    wire [31:0] w_u_sfucore_Q_lane14_lane_kv_wdata;
    wire [0:0] w_u_sfucore_Q_lane14_lane_kv_we;
    wire [95:0] w_u_sfucore_Q_lane14_lane_rd_addr;
    wire [3:0] w_u_sfucore_Q_lane14_lane_rd_re;
    wire [7:0] w_u_sfucore_Q_lane14_lane_rd_src;
    wire [0:0] w_u_sfucore_Q_lane14_lane_ro_v;
    wire [31:0] w_u_sfucore_Q_lane14_lane_ro_x;
    wire [23:0] w_u_sfucore_Q_lane14_lane_vi_addr;
    wire [0:0] w_u_sfucore_Q_lane14_lane_vi_re;
    wire [23:0] w_u_sfucore_Q_lane14_lane_vm_waddr;
    wire [31:0] w_u_sfucore_Q_lane14_lane_vm_wdata;
    wire [0:0] w_u_sfucore_Q_lane14_lane_vm_we;
    wire [0:0] w_u_sfucore_Q_lane15_lane_coll;
    wire [0:0] w_u_sfucore_Q_lane15_lane_fault;
    wire [23:0] w_u_sfucore_Q_lane15_lane_kv_waddr;
    wire [31:0] w_u_sfucore_Q_lane15_lane_kv_wdata;
    wire [0:0] w_u_sfucore_Q_lane15_lane_kv_we;
    wire [95:0] w_u_sfucore_Q_lane15_lane_rd_addr;
    wire [3:0] w_u_sfucore_Q_lane15_lane_rd_re;
    wire [7:0] w_u_sfucore_Q_lane15_lane_rd_src;
    wire [0:0] w_u_sfucore_Q_lane15_lane_ro_v;
    wire [31:0] w_u_sfucore_Q_lane15_lane_ro_x;
    wire [23:0] w_u_sfucore_Q_lane15_lane_vi_addr;
    wire [0:0] w_u_sfucore_Q_lane15_lane_vi_re;
    wire [23:0] w_u_sfucore_Q_lane15_lane_vm_waddr;
    wire [31:0] w_u_sfucore_Q_lane15_lane_vm_wdata;
    wire [0:0] w_u_sfucore_Q_lane15_lane_vm_we;
    wire [0:0] w_u_sfucore_Q_opstore_a_store0_flt;
    wire [0:0] w_u_sfucore_Q_opstore_a_store1_flt;
    wire [1023:0] w_u_sfucore_Q_opstore_a_cmd0_Q;
    wire [767:0] w_u_sfucore_Q_opstore_a_cmd1_Q;
    wire [63:0] w_u_sfucore_Q_opstore_a_cmd2_Q;
    wire [31:0] w_u_sfucore_Q_opstore_a_cmd3_Q;
    wire [0:0] w_u_sfucore_Q_opstore_b_store0_flt;
    wire [0:0] w_u_sfucore_Q_opstore_b_store1_flt;
    wire [1023:0] w_u_sfucore_Q_opstore_b_cmd0_Q;
    wire [767:0] w_u_sfucore_Q_opstore_b_cmd1_Q;
    wire [63:0] w_u_sfucore_Q_opstore_b_cmd2_Q;
    wire [383:0] w_u_sfucore_Q_opstore_b_cmd3_Q;
    wire [511:0] w_u_sfucore_Q_opstore_b_cmd4_Q;
    wire [31:0] w_u_sfucore_Q_opstore_b_cmd5_Q;
    wire [15:0] w_u_sfucore_Q_opstore_b_cmd6_Q;
    wire [0:0] w_u_sfucore_Q_ctl_u_core_procdff_66891_Q;
    wire [7:0] w_u_sfucore_Q_ctl_u_core_procdff_66896_Q;
    wire [7:0] w_u_sfucore_Q_ctl_u_core_procdff_66901_Q;
    wire [255:0] w_u_sfucore_Q_ctl_u_core_procdff_66906_Q;
    wire [255:0] w_u_sfucore_Q_ctl_u_core_procdff_66911_Q;
    wire [135:0] w_u_sfucore_Q_ctl_u_core_procdff_66916_Q;
    wire [2247:0] w_u_sfucore_Q_ctl_u_core_procdff_66921_Q;
    wire [33:0] w_u_sfucore_Q_ctl_u_core_procdff_66936_Q;
    wire [1021:0] w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q;
    wire [0:0] w_u_sfucore_Q_ctl_u_core_u_rst_rst_n;
    wire [1:0] w_u_sfucore_Q_ctl_u_core_u_vm_drain_v;
    wire [127:0] w_u_sfucore_Q_ctl_u_core_u_vm_scalar_data;
    wire [3:0] w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load;
    wire [95:0] w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load_addr;
    wire [119:0] w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr;
    wire [2047:0] w_u_sfucore_Q_ctl_u_core_u_vm_stage_data;
    wire [15:0] w_u_sfucore_Q_ctl_u_core_u_vm_stage_group;
    wire [63:0] w_u_sfucore_Q_ctl_u_core_u_vm_stage_mask;
    wire [7:0] w_u_sfucore_Q_ctl_u_core_u_vm_stage_v;
    wire [20:0] L106x7_o_s0;
    wire [20:0] L106x7_o_s1;
    wire [20:0] L106x7_o_s2;
    wire [20:0] L106x7_o_s3;
    wire [7:0] L125x1_o_s0;
    wire [7:0] L125x1_o_s1;
    wire [7:0] L125x1_o_s2;
     
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));   
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_n_t9;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t13;
    wire rst_n_t14;
    wire rst_n_t15;
    wire rst_n_t16;
    wire rst_n_t17;
    wire rst_n_t18;
    wire rst_n_t19;
    wire rst_n_t20;
    wire rst_n_t21;
    wire rst_n_t22;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));   
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));   
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));   
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));   
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));   
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));   
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t14));   
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_1), .q(rst_rl_7));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));   
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));   
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));   
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_n_t13));   
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_7), .q(rst_rl_12));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));   
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t6));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_13), .q(rst_rl_16));   
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t5));   
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_7), .q(rst_rl_18));   
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));   
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));   
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t16));   
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_7), .q(rst_rl_22));   
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));   
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));   
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_n_t17));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_root_n), .q(rst_rl_26));   
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));   
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));   
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));   
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));   
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));   
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_n_t7));   
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_root_n), .q(rst_rl_33));   
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));   
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_rl_35));   
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));   
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));   
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));   
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t8));   
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_root_n), .q(rst_rl_40));   
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));   
    wire rst_rl_42;
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_rl_42));   
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_42), .q(rst_rl_43));   
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));   
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_rl_45));   
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_n_t9));   
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_41), .q(rst_rl_47));   
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));   
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));   
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));   
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_n_t4));   
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_47), .q(rst_rl_52));   
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));   
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));   
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t3));   
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_52), .q(rst_rl_56));   
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));   
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_n_t2));   
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_56), .q(rst_rl_59));   
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_n_t1));   
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_59), .q(rst_n_t0));   
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_root_n), .q(rst_rl_62));   
    wire rst_rl_63;
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_rl_63));   
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_63), .q(rst_rl_64));   
    wire rst_rl_65;
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_rl_65));   
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_65), .q(rst_rl_66));   
    wire rst_rl_67;
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_rl_67));   
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_67), .q(rst_n_t10));   
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_66), .q(rst_rl_69));   
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_n_t22));   
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_66), .q(rst_rl_71));   
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_n_t15));   
    wire rst_rl_73;
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_root_n), .q(rst_rl_73));   
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_73), .q(rst_rl_74));   
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));   
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_rl_76));   
    wire rst_rl_77;
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_rl_77));   
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_77), .q(rst_rl_78));   
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_n_t12));   
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_78), .q(rst_n_t11));   
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_root_n), .q(rst_rl_81));   
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));   
    wire rst_rl_83;
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_rl_83));   
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_rl_83), .q(rst_rl_84));   
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));   
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));   
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_n_t19));   
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_86), .q(rst_n_t18));   
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_root_n), .q(rst_rl_89));   
    wire rst_rl_90;
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_rl_90));   
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_90), .q(rst_rl_91));   
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));   
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));   
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));   
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_o_0));   
    ot_dp_rrelay u_rrl_95_t (.clk(clk), .d(rst_rl_94), .q(rst_n_t20));   
    wire rst_rl_96;
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_root_n), .q(rst_rl_96));   
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_96), .q(rst_rl_97));   
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));   
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));   
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_rl_100));   
    wire rst_rl_101;
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_rl_101));   
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_101), .q(rst_o_1));   
    ot_dp_rrelay u_rrl_102_t (.clk(clk), .d(rst_rl_101), .q(rst_n_t21));   
    wire rst_n = rst_n_t12;
    ot_dp_st #(.W(4)) u_bin_L127_i (.clk(clk), .rst_n(rst_n), .d(L127_i[3:0]), .ea(L127_i[4]), .q(L127_i_q), .eq(L127_i_eq));
    ot_dp_st #(.W(514)) u_bin_L54_i (.clk(clk), .rst_n(rst_n), .d(L54_i[513:0]), .ea(L54_i[514]), .q(L54_i_q), .eq(L54_i_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5[1]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5[31:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5[32]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5_eq));
    ot_dp_st #(.W(514)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0[513:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0[514]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0_eq));
    ot_dp_st #(.W(514)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1[513:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1[514]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1_eq));
    ot_dp_st #(.W(514)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2[513:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2[514]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2_eq));
    ot_dp_st #(.W(2)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0[1:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0[2]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0_eq));
    ot_dp_st #(.W(2)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1[1:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1[2]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1_eq));
    ot_dp_st #(.W(2)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2[1:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2[2]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2_eq));
    ot_dp_st #(.W(471)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66936_D (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66936_D[470:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66936_D[471]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66936_D_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66936_D_eq));
    ot_dp_st #(.W(1742)) u_bin_xi_u_sfucore_Q_ctl_u_core_procdff_66941_D (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_procdff_66941_D[1741:0]), .ea(xi_u_sfucore_Q_ctl_u_core_procdff_66941_D[1742]), .q(xi_u_sfucore_Q_ctl_u_core_procdff_66941_D_q), .eq(xi_u_sfucore_Q_ctl_u_core_procdff_66941_D_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9[0:0]), .ea(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9[1]), .q(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9_q), .eq(xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_lane14_lane_vi_q (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_lane14_lane_vi_q[31:0]), .ea(xi_u_sfucore_Q_lane14_lane_vi_q[32]), .q(xi_u_sfucore_Q_lane14_lane_vi_q_q), .eq(xi_u_sfucore_Q_lane14_lane_vi_q_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_lane15_lane_vi_q (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_lane15_lane_vi_q[31:0]), .ea(xi_u_sfucore_Q_lane15_lane_vi_q[32]), .q(xi_u_sfucore_Q_lane15_lane_vi_q_q), .eq(xi_u_sfucore_Q_lane15_lane_vi_q_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__0[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__0[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__0_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__0_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__1[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__1[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__1_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__1_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__10[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__10[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__10_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__10_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__11[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__11[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__11_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__11_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__12[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__12[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__12_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__12_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__13 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__13[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__13[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__13_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__13_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__2[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__2[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__2_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__2_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__3[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__3[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__3_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__3_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__4[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__4[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__4_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__4_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__5[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__5[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__5_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__5_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__6[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__6[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__6_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__6_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__7[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__7[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__7_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__7_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__8[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__8[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__8_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__8_eq));
    ot_dp_st #(.W(96)) u_bin_xi_u_sfucore_Q_opstore_a_cmd1_D__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd1_D__9[95:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd1_D__9[96]), .q(xi_u_sfucore_Q_opstore_a_cmd1_D__9_q), .eq(xi_u_sfucore_Q_opstore_a_cmd1_D__9_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__0[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__0[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__0_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__0_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__1[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__1[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__1_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__1_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__10[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__10[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__10_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__10_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__11[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__11[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__11_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__11_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__12[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__12[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__12_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__12_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__13 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__13[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__13[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__13_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__13_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__2[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__2[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__2_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__2_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__3[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__3[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__3_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__3_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__4[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__4[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__4_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__4_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__5[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__5[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__5_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__5_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__6[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__6[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__6_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__6_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__7[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__7[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__7_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__7_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__8[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__8[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__8_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__8_eq));
    ot_dp_st #(.W(8)) u_bin_xi_u_sfucore_Q_opstore_a_cmd2_D__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd2_D__9[7:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd2_D__9[8]), .q(xi_u_sfucore_Q_opstore_a_cmd2_D__9_q), .eq(xi_u_sfucore_Q_opstore_a_cmd2_D__9_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__0[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__0[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__0_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__0_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__1[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__1[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__1_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__1_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__10[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__10[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__10_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__10_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__11[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__11[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__11_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__11_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__12[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__12[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__12_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__12_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__13 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__13[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__13[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__13_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__13_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__2[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__2[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__2_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__2_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__3[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__3[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__3_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__3_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__4[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__4[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__4_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__4_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__5[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__5[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__5_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__5_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__6[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__6[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__6_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__6_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__7[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__7[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__7_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__7_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__8[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__8[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__8_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__8_eq));
    ot_dp_st #(.W(4)) u_bin_xi_u_sfucore_Q_opstore_a_cmd3_D__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_a_cmd3_D__9[3:0]), .ea(xi_u_sfucore_Q_opstore_a_cmd3_D__9[4]), .q(xi_u_sfucore_Q_opstore_a_cmd3_D__9_q), .eq(xi_u_sfucore_Q_opstore_a_cmd3_D__9_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__0[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__0[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__0_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__0_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__1[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__1[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__1_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__1_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__10[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__10[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__10_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__10_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__11[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__11[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__11_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__11_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__12[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__12[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__12_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__12_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__13 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__13[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__13[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__13_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__13_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__2[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__2[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__2_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__2_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__3[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__3[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__3_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__3_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__4[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__4[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__4_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__4_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__5[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__5[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__5_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__5_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__6[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__6[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__6_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__6_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__7[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__7[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__7_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__7_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__8[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__8[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__8_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__8_eq));
    ot_dp_st #(.W(24)) u_bin_xi_u_sfucore_Q_opstore_b_cmd3_D__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd3_D__9[23:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd3_D__9[24]), .q(xi_u_sfucore_Q_opstore_b_cmd3_D__9_q), .eq(xi_u_sfucore_Q_opstore_b_cmd3_D__9_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__0[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__0[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__0_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__0_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__1[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__1[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__1_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__1_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__10[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__10[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__10_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__10_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__11[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__11[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__11_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__11_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__12[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__12[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__12_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__12_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__13 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__13[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__13[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__13_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__13_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__2[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__2[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__2_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__2_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__3[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__3[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__3_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__3_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__4[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__4[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__4_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__4_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__5[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__5[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__5_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__5_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__6[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__6[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__6_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__6_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__7[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__7[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__7_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__7_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__8[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__8[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__8_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__8_eq));
    ot_dp_st #(.W(32)) u_bin_xi_u_sfucore_Q_opstore_b_cmd4_D__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd4_D__9[31:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd4_D__9[32]), .q(xi_u_sfucore_Q_opstore_b_cmd4_D__9_q), .eq(xi_u_sfucore_Q_opstore_b_cmd4_D__9_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__0[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__0[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__0_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__1[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__1[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__1_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__10 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__10[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__10[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__10_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__10_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__11 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__11[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__11[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__11_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__11_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__12 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__12[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__12[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__12_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__12_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__13 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__13[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__13[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__13_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__13_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__2[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__2[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__2_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__3[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__3[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__3_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__4[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__4[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__4_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__4_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__5[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__5[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__5_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__5_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__6[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__6[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__6_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__6_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__7 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__7[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__7[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__7_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__7_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__8 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__8[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__8[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__8_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__8_eq));
    ot_dp_st #(.W(1)) u_bin_xi_u_sfucore_Q_opstore_b_cmd6_D__9 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_opstore_b_cmd6_D__9[0:0]), .ea(xi_u_sfucore_Q_opstore_b_cmd6_D__9[1]), .q(xi_u_sfucore_Q_opstore_b_cmd6_D__9_q), .eq(xi_u_sfucore_Q_opstore_b_cmd6_D__9_eq));
    ot_dp_st #(.W(596)) u_bout_L47_o (.clk(clk), .rst_n(rst_n), .d({w_u_sfucore_Q_ctl_u_core_procdff_66921_Q[561:0], w_u_sfucore_Q_ctl_u_core_procdff_66916_Q[33:0]}), .ea(rst_n), .q(L47_o[595:0]), .eq(L47_o[596]));
    ot_dp_st #(.W(1662)) u_bout_L730_o (.clk(clk), .rst_n(rst_n), .d({w_u_sfucore_Q_opstore_b_cmd0_Q[895:576], w_u_sfucore_Q_opstore_a_cmd0_Q[895:576], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1021:0]}), .ea(rst_n), .q(L730_o[1661:0]), .eq(L730_o[1662]));
    ot_dp_st #(.W(596)) u_bout_L731_o (.clk(clk), .rst_n(rst_n), .d({w_u_sfucore_Q_ctl_u_core_procdff_66921_Q[1685:1124], w_u_sfucore_Q_ctl_u_core_procdff_66916_Q[101:68]}), .ea(rst_n), .q(L731_o[595:0]), .eq(L731_o[596]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66891_Q (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66891_Q[0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66891_Q[0:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66891_Q[1]));
    ot_dp_st #(.W(8)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66896_Q (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66896_Q[7:0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66896_Q[7:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66896_Q[8]));
    ot_dp_st #(.W(8)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66901_Q (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66901_Q[7:0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66901_Q[7:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66901_Q[8]));
    ot_dp_st #(.W(256)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66906_Q (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66906_Q[255:0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66906_Q[255:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66906_Q[256]));
    ot_dp_st #(.W(256)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66911_Q (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66911_Q[255:0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66911_Q[255:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66911_Q[256]));
    ot_dp_st #(.W(34)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__0 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66916_Q[67:34]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__0[33:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__0[34]));
    ot_dp_st #(.W(34)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__1 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66916_Q[135:102]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__1[33:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66916_Q__1[34]));
    ot_dp_st #(.W(562)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__0 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66921_Q[1123:562]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__0[561:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__0[562]));
    ot_dp_st #(.W(562)) u_bout_xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__1 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_procdff_66921_Q[2247:1686]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__1[561:0]), .eq(xo_u_sfucore_Q_ctl_u_core_procdff_66921_Q__1[562]));
    ot_dp_st #(.W(1022)) u_bout_xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__0 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1021:0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__0[1021:0]), .eq(xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__0[1022]));
    ot_dp_st #(.W(1022)) u_bout_xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__1 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1021:0]), .ea(rst_n), .q(xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__1[1021:0]), .eq(xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__1[1022]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane14_lane_kv_waddr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane14_lane_kv_waddr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane14_lane_kv_waddr[23:0]), .eq(xo_u_sfucore_Q_lane14_lane_kv_waddr[24]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane14_lane_kv_wdata (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane14_lane_kv_wdata[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane14_lane_kv_wdata[31:0]), .eq(xo_u_sfucore_Q_lane14_lane_kv_wdata[32]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane14_lane_kv_we (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane14_lane_kv_we[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane14_lane_kv_we[0:0]), .eq(xo_u_sfucore_Q_lane14_lane_kv_we[1]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane14_lane_vi_addr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane14_lane_vi_addr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane14_lane_vi_addr[23:0]), .eq(xo_u_sfucore_Q_lane14_lane_vi_addr[24]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane14_lane_vi_re (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane14_lane_vi_re[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane14_lane_vi_re[0:0]), .eq(xo_u_sfucore_Q_lane14_lane_vi_re[1]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane15_lane_kv_waddr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane15_lane_kv_waddr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane15_lane_kv_waddr[23:0]), .eq(xo_u_sfucore_Q_lane15_lane_kv_waddr[24]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane15_lane_kv_wdata (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane15_lane_kv_wdata[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane15_lane_kv_wdata[31:0]), .eq(xo_u_sfucore_Q_lane15_lane_kv_wdata[32]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane15_lane_kv_we (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane15_lane_kv_we[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane15_lane_kv_we[0:0]), .eq(xo_u_sfucore_Q_lane15_lane_kv_we[1]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane15_lane_vi_addr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane15_lane_vi_addr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane15_lane_vi_addr[23:0]), .eq(xo_u_sfucore_Q_lane15_lane_vi_addr[24]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane15_lane_vi_re (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane15_lane_vi_re[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane15_lane_vi_re[0:0]), .eq(xo_u_sfucore_Q_lane15_lane_vi_re[1]));
    ot_dp_st #(.W(256)) u_bout_xo_u_sfucore_Q_opstore_a_cmd0_Q__0 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_opstore_a_cmd0_Q[255:0]), .ea(rst_n), .q(xo_u_sfucore_Q_opstore_a_cmd0_Q__0[255:0]), .eq(xo_u_sfucore_Q_opstore_a_cmd0_Q__0[256]));
    ot_dp_st #(.W(320)) u_bout_xo_u_sfucore_Q_opstore_a_cmd0_Q__1 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_opstore_a_cmd0_Q[575:256]), .ea(rst_n), .q(xo_u_sfucore_Q_opstore_a_cmd0_Q__1[319:0]), .eq(xo_u_sfucore_Q_opstore_a_cmd0_Q__1[320]));
    ot_dp_st #(.W(256)) u_bout_xo_u_sfucore_Q_opstore_b_cmd0_Q__0 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_opstore_b_cmd0_Q[255:0]), .ea(rst_n), .q(xo_u_sfucore_Q_opstore_b_cmd0_Q__0[255:0]), .eq(xo_u_sfucore_Q_opstore_b_cmd0_Q__0[256]));
    ot_dp_st #(.W(320)) u_bout_xo_u_sfucore_Q_opstore_b_cmd0_Q__1 (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_opstore_b_cmd0_Q[575:256]), .ea(rst_n), .q(xo_u_sfucore_Q_opstore_b_cmd0_Q__1[319:0]), .eq(xo_u_sfucore_Q_opstore_b_cmd0_Q__1[320]));
    ot_dp_st #(.W(20)) u_ft_L106x7_o_0 (.clk(clk), .rst_n(rst_n), .d(L106x7_i[19:0]), .ea(L106x7_i[20]), .q(L106x7_o_s0[19:0]), .eq(L106x7_o_s0[20]));
    ot_dp_st #(.W(20)) u_ft_L106x7_o_1 (.clk(clk), .rst_n(rst_n), .d(L106x7_o_s0[19:0]), .ea(L106x7_o_s0[20]), .q(L106x7_o_s1[19:0]), .eq(L106x7_o_s1[20]));
    ot_dp_st #(.W(20)) u_ft_L106x7_o_2 (.clk(clk), .rst_n(rst_n), .d(L106x7_o_s1[19:0]), .ea(L106x7_o_s1[20]), .q(L106x7_o_s2[19:0]), .eq(L106x7_o_s2[20]));
    ot_dp_st #(.W(20)) u_ft_L106x7_o_3 (.clk(clk), .rst_n(rst_n), .d(L106x7_o_s2[19:0]), .ea(L106x7_o_s2[20]), .q(L106x7_o_s3[19:0]), .eq(L106x7_o_s3[20]));
    ot_dp_st #(.W(20)) u_ft_L106x7_o_4 (.clk(clk), .rst_n(rst_n), .d(L106x7_o_s3[19:0]), .ea(L106x7_o_s3[20]), .q(L106x7_o[19:0]), .eq(L106x7_o[20]));
    ot_dp_st #(.W(7)) u_ft_L125x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L125x1_i[6:0]), .ea(L125x1_i[7]), .q(L125x1_o_s0[6:0]), .eq(L125x1_o_s0[7]));
    ot_dp_st #(.W(7)) u_ft_L125x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L125x1_o_s0[6:0]), .ea(L125x1_o_s0[7]), .q(L125x1_o_s1[6:0]), .eq(L125x1_o_s1[7]));
    ot_dp_st #(.W(7)) u_ft_L125x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L125x1_o_s1[6:0]), .ea(L125x1_o_s1[7]), .q(L125x1_o_s2[6:0]), .eq(L125x1_o_s2[7]));
    ot_dp_st #(.W(7)) u_ft_L125x1_o_3 (.clk(clk), .rst_n(rst_n), .d(L125x1_o_s2[6:0]), .ea(L125x1_o_s2[7]), .q(L125x1_o[6:0]), .eq(L125x1_o[7]));
    assign w_u_core_u_engine_u_memory_auto_proc_dff_cc_220_proc_dff_66978_Y = ~w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];
    assign w_u_core_u_engine_u_memory_auto_proc_dff_cc_220_proc_dff_66983_Y = ~w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];
    assign w_u_core_u_engine_u_memory_logic_not_ot_hgi_sfu_static_operand_store_sp2_sv_47_8078_Y = !w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];   
    assign w_u_core_u_engine_u_memory_u_store_auto_proc_dff_cc_220_proc_dff_66954_Y = ~w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];
    assign w_u_core_u_engine_u_memory_u_store_auto_proc_dff_cc_220_proc_dff_66959_Y = ~w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8764_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[14:0] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8766_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[29:15] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8768_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[44:30] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8770_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[59:45] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8772_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[74:60] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8774_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[89:75] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8776_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[104:90] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8778_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[119:105] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_74_8780_Y = w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[18:4] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_74_8782_Y = w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[33:19] > 32'b00000000000000000111111111111000;   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8119_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[0] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8123_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8119_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8122_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8124_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[1] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8128_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8124_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8127_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8129_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[0] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8133_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8129_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8132_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8134_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[1] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8138_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8134_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8137_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8139_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[2] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8143_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8139_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8142_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8144_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[3] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8148_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8144_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8147_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8149_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[2] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8153_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8149_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8152_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8154_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[3] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8158_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8154_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8157_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8159_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[4] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8163_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8159_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8162_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8164_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[5] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8168_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8164_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8167_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8169_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[4] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8173_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8169_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8172_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8174_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[5] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8178_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8174_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8177_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8179_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[6] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8183_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8179_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8182_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8184_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[7] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8188_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8184_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8187_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8189_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[6] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8193_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8189_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8192_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8194_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[7] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8198_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8194_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8197_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8199_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[8] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8203_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8199_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8202_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8204_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[9] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8208_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8204_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8207_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8209_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[8] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8213_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8209_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8212_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8214_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[9] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8218_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8214_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8217_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8219_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[10] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8223_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8219_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8222_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8224_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[11] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8228_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8224_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8227_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8229_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[10] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8233_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8229_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8232_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8234_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[11] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8238_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8234_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8237_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8239_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[12] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8243_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8239_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8242_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8244_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[13] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8248_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8244_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8247_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8249_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[12] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8253_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8249_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8252_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8254_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[13] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8258_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8254_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8257_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8259_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[14] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8263_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8259_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8262_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8264_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[15] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8268_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8264_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8267_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8269_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[14] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8273_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8269_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8272_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8274_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[15] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8278_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8274_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8277_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8279_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[16] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8283_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8279_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8282_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8284_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[17] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8288_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8284_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8287_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8289_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[16] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8293_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8289_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8292_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8294_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[17] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8298_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8294_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8297_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8299_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[18] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8303_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8299_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8302_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8304_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[19] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8308_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8304_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8307_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8309_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[18] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8313_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8309_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8312_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8314_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[19] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8318_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8314_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8317_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8319_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[20] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8323_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8319_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8322_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8324_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[21] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8328_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8324_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8327_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8329_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[20] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8333_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8329_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8332_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8334_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[21] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8338_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8334_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8337_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8339_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[22] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8343_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8339_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8342_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8344_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[23] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8348_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8344_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8347_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8349_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[22] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8353_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8349_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8352_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8354_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[23] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8358_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8354_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8357_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8359_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[24] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8363_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8359_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8362_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8364_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[25] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8368_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8364_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8367_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8369_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[24] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8373_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8369_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8372_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8374_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[25] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8378_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8374_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8377_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8379_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[26] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8383_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8379_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8382_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8384_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[27] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8388_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8384_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8387_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8389_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[26] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8393_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8389_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8392_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8394_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[27] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8398_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8394_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8397_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8399_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[28] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8403_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8399_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8402_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8404_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[29] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8408_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8404_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8407_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8409_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[28] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8413_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8409_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8412_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8414_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[29] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8418_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8414_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8417_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8419_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[30] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8423_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8419_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8422_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8424_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[31] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8428_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8424_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8427_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8429_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[30] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8433_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8429_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8432_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8434_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[31] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8438_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8434_Y[0] && w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8437_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8477_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8476_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8495_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[1] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8494_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8513_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[2] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8512_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8531_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[3] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8530_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8549_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[4] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8548_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8567_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[5] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8566_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8585_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[6] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8584_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8603_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[7] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8602_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8621_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[8] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8620_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8639_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[9] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8638_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8657_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[10] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8656_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8675_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[11] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8674_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8693_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[12] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8692_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8711_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[13] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8710_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8729_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[14] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8728_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8747_Y = w_u_sfucore_Q_opstore_b_cmd6_Q[15] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8746_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8479_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[0] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8478_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8481_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8479_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8480_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8483_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[1] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8482_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8485_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8483_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8484_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8487_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[0] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8486_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8489_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8487_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8488_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8491_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[1] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8490_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8493_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8491_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8492_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8497_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[2] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8496_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8499_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8497_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8498_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8501_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[3] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8500_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8503_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8501_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8502_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8505_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[2] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8504_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8507_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8505_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8506_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8509_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[3] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8508_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8511_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8509_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8510_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8515_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[4] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8514_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8517_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8515_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8516_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8519_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[5] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8518_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8521_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8519_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8520_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8523_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[4] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8522_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8525_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8523_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8524_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8527_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[5] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8526_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8529_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8527_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8528_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8533_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[6] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8532_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8535_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8533_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8534_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8537_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[7] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8536_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8539_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8537_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8538_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8541_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[6] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8540_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8543_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8541_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8542_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8545_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[7] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8544_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8547_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8545_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8546_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8551_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[8] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8550_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8553_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8551_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8552_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8555_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[9] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8554_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8557_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8555_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8556_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8559_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[8] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8558_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8561_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8559_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8560_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8563_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[9] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8562_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8565_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8563_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8564_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8569_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[10] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8568_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8571_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8569_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8570_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8573_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[11] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8572_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8575_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8573_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8574_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8577_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[10] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8576_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8579_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8577_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8578_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8581_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[11] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8580_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8583_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8581_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8582_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8587_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[12] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8586_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8589_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8587_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8588_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8591_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[13] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8590_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8593_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8591_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8592_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8595_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[12] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8594_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8597_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8595_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8596_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8599_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[13] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8598_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8601_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8599_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8600_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8605_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[14] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8604_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8607_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8605_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8606_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8609_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[15] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8608_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8611_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8609_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8610_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8613_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[14] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8612_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8615_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8613_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8614_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8617_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[15] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8616_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8619_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8617_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8618_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8623_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[16] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8622_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8625_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8623_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8624_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8627_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[17] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8626_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8629_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8627_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8628_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8631_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[16] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8630_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8633_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8631_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8632_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8635_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[17] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8634_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8637_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8635_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8636_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8641_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[18] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8640_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8643_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8641_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8642_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8645_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[19] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8644_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8647_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8645_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8646_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8649_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[18] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8648_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8651_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8649_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8650_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8653_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[19] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8652_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8655_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8653_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8654_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8659_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[20] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8658_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8661_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8659_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8660_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8663_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[21] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8662_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8665_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8663_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8664_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8667_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[20] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8666_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8669_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8667_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8668_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8671_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[21] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8670_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8673_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8671_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8672_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8677_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[22] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8676_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8679_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8677_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8678_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8681_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[23] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8680_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8683_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8681_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8682_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8685_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[22] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8684_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8687_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8685_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8686_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8689_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[23] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8688_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8691_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8689_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8690_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8695_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[24] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8694_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8697_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8695_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8696_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8699_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[25] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8698_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8701_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8699_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8700_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8703_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[24] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8702_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8705_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8703_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8704_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8707_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[25] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8706_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8709_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8707_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8708_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8713_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[26] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8712_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8715_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8713_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8714_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8717_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[27] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8716_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8719_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8717_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8718_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8721_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[26] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8720_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8723_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8721_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8722_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8725_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[27] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8724_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8727_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8725_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8726_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8731_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[28] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8730_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8733_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8731_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8732_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8735_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[29] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8734_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8737_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8735_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8736_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8739_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[28] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8738_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8741_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8739_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8740_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8743_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[29] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8742_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8745_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8743_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8744_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8749_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[30] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8748_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8751_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8749_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8750_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8753_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[31] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8752_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8755_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8753_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8754_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8757_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[30] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8756_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8759_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8757_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8758_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8761_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[31] && w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8760_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8763_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8761_Y[0] && w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8762_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8765_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[0] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8764_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8767_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[1] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8766_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8769_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[2] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8768_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8771_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[3] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8770_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8773_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[4] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8772_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8775_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[5] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8774_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8777_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[6] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8776_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8779_Y = w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[7] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_72_8778_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_74_8781_Y = w_u_sfucore_Q_ctl_u_core_u_vm_drain_v[0] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_74_8780_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_74_8783_Y = w_u_sfucore_Q_ctl_u_core_u_vm_drain_v[1] && w_u_core_u_engine_u_memory_u_store_gt_ot_hgi_sfu_static_operand_store_sv_74_8782_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8785_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[0] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8784_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8787_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[1] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8786_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8789_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[0] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8788_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8791_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[1] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8790_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8793_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[2] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8792_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8795_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[3] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8794_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8797_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[2] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8796_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8799_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[3] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8798_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8801_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[4] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8800_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8803_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[5] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8802_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8805_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[4] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8804_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8807_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[5] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8806_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8809_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[6] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8808_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8811_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[7] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8810_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8813_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[6] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8812_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8815_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[7] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8814_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8817_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[8] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8816_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8819_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[9] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8818_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8821_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[8] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8820_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8823_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[9] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8822_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8825_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[10] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8824_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8827_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[11] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8826_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8829_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[10] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8828_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8831_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[11] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8830_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8833_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[12] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8832_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8835_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[13] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8834_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8837_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[12] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8836_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8839_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[13] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8838_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8841_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[14] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8840_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8843_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[15] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8842_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8845_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[14] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8844_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8847_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[15] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8846_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8849_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[16] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8848_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8851_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[17] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8850_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8853_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[16] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8852_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8855_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[17] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8854_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8857_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[18] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8856_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8859_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[19] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8858_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8861_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[18] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8860_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8863_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[19] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8862_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8865_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[20] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8864_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8867_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[21] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8866_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8869_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[20] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8868_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8871_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[21] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8870_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8873_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[22] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8872_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8875_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[23] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8874_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8877_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[22] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8876_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8879_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[23] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8878_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8881_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[24] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8880_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8883_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[25] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8882_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8885_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[24] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8884_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8887_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[25] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8886_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8889_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[26] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8888_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8891_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[27] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8890_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8893_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[26] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8892_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8895_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[27] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8894_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8897_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[28] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8896_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8899_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[29] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8898_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8901_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[28] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8900_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8903_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[29] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8902_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8905_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[30] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8904_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8907_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[31] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8906_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8909_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[30] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8908_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8911_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[31] && w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8910_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8920_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[0] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8921_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[2] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8922_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[4] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8923_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[6] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8924_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[8] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8925_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[10] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8926_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[12] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8927_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[14] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8928_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[16] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8929_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[18] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8930_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[20] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8931_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[22] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8932_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[24] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8933_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[26] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8934_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[28] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8935_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[30] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9034_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[1] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9035_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[3] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9036_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[5] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9037_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[7] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9038_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[9] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9039_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[11] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9040_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[13] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9041_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[15] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9042_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[17] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9043_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[19] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9044_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[21] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9045_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[23] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9046_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[25] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9047_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[27] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9048_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[29] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9049_Y = w_u_sfucore_Q_opstore_a_cmd3_Q[31] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9148_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[0] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9149_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[2] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9150_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[4] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9151_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[6] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9152_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[8] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9153_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[10] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9154_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[12] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9155_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[14] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9156_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[16] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9157_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[18] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9158_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[20] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9159_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[22] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9160_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[24] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9161_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[26] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9162_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[28] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9163_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[30] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9262_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[1] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9263_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[3] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9264_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[5] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9265_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[7] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9266_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[9] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9267_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[11] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9268_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[13] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9269_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[15] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9270_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[17] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9271_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[19] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9272_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[21] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9273_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[23] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9274_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[25] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9275_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[27] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9276_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[29] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9277_Y = w_u_sfucore_Q_opstore_b_cmd5_Q[31] && w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_56_8099_Y = !w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8120_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8125_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8130_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8135_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8140_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8145_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8150_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8155_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8160_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8165_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8170_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8175_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8180_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8185_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8190_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8195_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8200_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8205_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8210_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8215_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8220_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8225_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8230_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8235_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8240_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8245_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8250_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8255_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8260_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8265_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8270_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8275_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8280_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8285_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8290_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8295_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8300_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8305_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8310_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8315_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8320_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8325_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8330_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8335_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8340_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8345_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8350_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8355_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8360_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8365_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8370_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8375_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8380_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8385_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8390_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8395_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8400_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8405_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8410_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8415_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8420_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8425_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8430_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8435_Y = !w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8478_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8482_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8486_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8490_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8496_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8500_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8504_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8508_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8514_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8518_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8522_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8526_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8532_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8536_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8540_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8544_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8550_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8554_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8558_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8562_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8568_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8572_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8576_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8580_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8586_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8590_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8594_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8598_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8604_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8608_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8612_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8616_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8622_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8626_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8630_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8634_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8640_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8644_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8648_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8652_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8658_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8662_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8666_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8670_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8676_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8680_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8684_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8688_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8694_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8698_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8702_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8706_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8712_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8716_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8720_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8724_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8730_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8734_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8738_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8742_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8748_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8752_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8756_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_69_8760_Y = !w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    assign w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_80_8913_Y = !w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8122_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8120_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8121_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8127_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8125_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8126_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8132_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8130_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8131_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8137_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8135_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8136_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8142_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8140_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8141_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8147_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8145_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8146_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8152_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8150_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8151_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8157_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8155_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8156_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8162_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8160_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8161_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8167_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8165_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8166_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8172_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8170_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8171_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8177_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8175_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8176_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8182_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8180_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8181_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8187_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8185_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8186_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8192_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8190_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8191_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8197_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8195_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8196_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8202_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8200_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8201_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8207_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8205_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8206_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8212_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8210_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8211_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8217_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8215_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8216_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8222_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8220_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8221_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8227_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8225_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8226_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8232_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8230_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8231_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8237_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8235_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8236_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8242_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8240_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8241_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8247_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8245_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8246_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8252_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8250_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8251_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8257_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8255_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8256_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8262_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8260_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8261_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8267_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8265_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8266_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8272_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8270_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8271_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8277_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8275_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8276_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8282_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8280_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8281_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8287_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8285_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8286_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8292_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8290_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8291_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8297_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8295_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8296_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8302_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8300_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8301_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8307_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8305_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8306_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8312_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8310_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8311_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8317_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8315_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8316_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8322_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8320_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8321_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8327_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8325_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8326_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8332_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8330_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8331_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8337_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8335_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8336_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8342_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8340_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8341_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8347_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8345_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8346_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8352_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8350_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8351_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8357_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8355_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8356_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8362_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8360_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8361_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8367_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8365_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8366_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8372_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8370_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8371_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8377_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8375_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8376_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8382_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8380_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8381_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8387_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8385_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8386_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8392_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8390_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8391_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8397_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8395_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8396_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8402_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8400_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8401_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8407_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8405_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8406_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8412_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8410_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8411_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8417_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8415_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8416_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8422_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8420_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8421_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8427_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8425_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8426_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8432_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8430_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8431_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_61_8437_Y = w_u_core_u_engine_u_memory_u_store_logic_not_ot_hgi_sfu_static_operand_store_sv_61_8435_Y[0] || w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8436_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8914_Y = w_u_core_u_engine_u_memory_u_store_procmux_55986_Y[0] || w_u_core_u_engine_u_memory_u_store_procmux_56178_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8915_Y = w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8914_Y[0] || w_u_core_u_engine_u_memory_u_store_procmux_56448_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8917_Y = w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8915_Y[0] || w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_81_8916_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8121_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[23:0] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8126_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[47:24] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8131_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[23:0] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8136_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[47:24] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8141_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[71:48] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8146_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[95:72] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8151_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[71:48] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8156_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[95:72] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8161_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[119:96] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8166_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[143:120] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8171_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[119:96] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8176_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[143:120] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8181_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[167:144] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8186_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[191:168] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8191_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[167:144] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8196_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[191:168] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8201_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[215:192] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8206_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[239:216] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8211_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[215:192] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8216_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[239:216] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8221_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[263:240] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8226_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[287:264] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8231_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[263:240] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8236_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[287:264] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8241_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[311:288] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8246_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[335:312] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8251_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[311:288] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8256_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[335:312] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8261_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[359:336] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8266_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[383:360] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8271_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[359:336] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8276_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[383:360] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8281_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[407:384] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8286_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[431:408] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8291_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[407:384] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8296_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[431:408] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8301_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[455:432] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8306_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[479:456] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8311_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[455:432] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8316_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[479:456] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8321_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[503:480] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8326_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[527:504] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8331_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[503:480] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8336_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[527:504] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8341_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[551:528] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8346_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[575:552] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8351_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[551:528] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8356_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[575:552] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8361_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[599:576] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8366_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[623:600] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8371_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[599:576] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8376_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[623:600] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8381_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[647:624] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8386_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[671:648] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8391_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[647:624] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8396_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[671:648] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8401_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[695:672] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8406_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[719:696] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8411_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[695:672] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8416_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[719:696] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8421_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[743:720] != w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8426_Y = w_u_sfucore_Q_opstore_a_cmd1_Q[767:744] != w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8431_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[743:720] != w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_61_8436_Y = w_u_sfucore_Q_opstore_b_cmd1_Q[767:744] != w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8784_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[1:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8786_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[3:2];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8788_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[1:0];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8790_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[3:2];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8792_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[5:4];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8794_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[7:6];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8796_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[5:4];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8798_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[7:6];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8800_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[9:8];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8802_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[11:10];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8804_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[9:8];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8806_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[11:10];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8808_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[13:12];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8810_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[15:14];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8812_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[13:12];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8814_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[15:14];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8816_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[17:16];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8818_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[19:18];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8820_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[17:16];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8822_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[19:18];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8824_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[21:20];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8826_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[23:22];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8828_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[21:20];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8830_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[23:22];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8832_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[25:24];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8834_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[27:26];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8836_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[25:24];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8838_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[27:26];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8840_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[29:28];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8842_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[31:30];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8844_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[29:28];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8846_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[31:30];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8848_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[33:32];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8850_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[35:34];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8852_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[33:32];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8854_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[35:34];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8856_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[37:36];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8858_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[39:38];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8860_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[37:36];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8862_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[39:38];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8864_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[41:40];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8866_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[43:42];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8868_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[41:40];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8870_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[43:42];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8872_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[45:44];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8874_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[47:46];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8876_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[45:44];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8878_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[47:46];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8880_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[49:48];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8882_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[51:50];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8884_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[49:48];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8886_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[51:50];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8888_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[53:52];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8890_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[55:54];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8892_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[53:52];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8894_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[55:54];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8896_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[57:56];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8898_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[59:58];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8900_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[57:56];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8902_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[59:58];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8904_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[61:60];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8906_Y = |w_u_sfucore_Q_opstore_a_cmd2_Q[63:62];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8908_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[61:60];   
    assign w_u_core_u_engine_u_memory_u_store_ne_ot_hgi_sfu_static_operand_store_sv_77_8910_Y = |w_u_sfucore_Q_opstore_b_cmd2_Q[63:62];   
    assign w_u_core_u_engine_u_memory_u_store_or_ot_hgi_sfu_static_operand_store_sv_56_8100_Y = w_u_core_u_engine_u_memory_u_store_procdff_66963_Q[3:0] | w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[3:0];   
    reg [511:0] g_u_core_u_engine_u_memory_u_store_procdff_66942_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66942_Q = g_u_core_u_engine_u_memory_u_store_procdff_66942_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66942_q <= {w_u_core_u_engine_u_memory_u_store_procmux_55855_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55857_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55859_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55861_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55863_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55865_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55867_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55869_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55871_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55873_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55875_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55877_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55879_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55881_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55883_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55885_Y[31:0]};   
    reg [0:0] g_u_core_u_engine_u_memory_u_store_procdff_66943_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66943_Q = g_u_core_u_engine_u_memory_u_store_procdff_66943_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66943_q <= w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66944_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66944_Q = g_u_core_u_engine_u_memory_u_store_procdff_66944_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66944_q <= 32'b00000000000000000000000000010000;   
    reg [511:0] g_u_core_u_engine_u_memory_u_store_procdff_66945_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66945_Q = g_u_core_u_engine_u_memory_u_store_procdff_66945_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66945_q <= {w_u_core_u_engine_u_memory_u_store_procmux_55887_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55889_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55891_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55893_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55895_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55897_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55899_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55901_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55903_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55905_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55907_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55909_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55911_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55913_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55915_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55917_Y[31:0]};   
    reg [0:0] g_u_core_u_engine_u_memory_u_store_procdff_66946_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66946_Q = g_u_core_u_engine_u_memory_u_store_procdff_66946_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66946_q <= w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66947_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66947_Q = g_u_core_u_engine_u_memory_u_store_procdff_66947_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66947_q <= 32'b00000000000000000000000000010000;   
    reg [511:0] g_u_core_u_engine_u_memory_u_store_procdff_66948_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66948_Q = g_u_core_u_engine_u_memory_u_store_procdff_66948_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66948_q <= {w_u_core_u_engine_u_memory_u_store_procmux_55919_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55921_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55923_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55925_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55927_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55929_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55931_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55933_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55935_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55937_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55939_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55941_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55943_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55945_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55947_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55949_Y[31:0]};   
    reg [0:0] g_u_core_u_engine_u_memory_u_store_procdff_66949_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66949_Q = g_u_core_u_engine_u_memory_u_store_procdff_66949_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66949_q <= w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66950_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66950_Q = g_u_core_u_engine_u_memory_u_store_procdff_66950_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66950_q <= 32'b00000000000000000000000000010000;   
    reg [511:0] g_u_core_u_engine_u_memory_u_store_procdff_66951_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66951_Q = g_u_core_u_engine_u_memory_u_store_procdff_66951_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66951_q <= {w_u_core_u_engine_u_memory_u_store_procmux_55951_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55953_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55955_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55957_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55959_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55961_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55963_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55965_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55967_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55969_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55971_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55973_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55975_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55977_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55979_Y[31:0], w_u_core_u_engine_u_memory_u_store_procmux_55981_Y[31:0]};   
    reg [0:0] g_u_core_u_engine_u_memory_u_store_procdff_66952_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66952_Q = g_u_core_u_engine_u_memory_u_store_procdff_66952_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66952_q <= w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66953_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66953_Q = g_u_core_u_engine_u_memory_u_store_procdff_66953_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66953_q <= 32'b00000000000000000000000000010000;   
    reg [0:0] g_u_core_u_engine_u_memory_u_store_procdff_66958_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66958_Q = g_u_core_u_engine_u_memory_u_store_procdff_66958_q;
    always @(posedge clk or negedge w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0])
        if (!w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0]) g_u_core_u_engine_u_memory_u_store_procdff_66958_q <= 1'b0; else g_u_core_u_engine_u_memory_u_store_procdff_66958_q <= w_u_core_u_engine_u_memory_u_store_procmux_55983_Y[0];   
    reg [3:0] g_u_core_u_engine_u_memory_u_store_procdff_66963_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66963_Q = g_u_core_u_engine_u_memory_u_store_procdff_66963_q;
    always @(posedge clk or negedge w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0])
        if (!w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0]) g_u_core_u_engine_u_memory_u_store_procdff_66963_q <= 4'b0000; else g_u_core_u_engine_u_memory_u_store_procdff_66963_q <= w_u_core_u_engine_u_memory_u_store_or_ot_hgi_sfu_static_operand_store_sv_56_8100_Y[3:0];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66964_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66964_Q = g_u_core_u_engine_u_memory_u_store_procdff_66964_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66964_q <= 32'b00000000000000000000000000000100;   
    reg [23:0] g_u_core_u_engine_u_memory_u_store_procdff_66965_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66965_Q = g_u_core_u_engine_u_memory_u_store_procdff_66965_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66965_q <= w_u_core_u_engine_u_memory_u_store_procmux_56653_Y[23:0];   
    reg [23:0] g_u_core_u_engine_u_memory_u_store_procdff_66966_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66966_Q = g_u_core_u_engine_u_memory_u_store_procdff_66966_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66966_q <= w_u_core_u_engine_u_memory_u_store_procmux_56651_Y[23:0];   
    reg [23:0] g_u_core_u_engine_u_memory_u_store_procdff_66967_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66967_Q = g_u_core_u_engine_u_memory_u_store_procdff_66967_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66967_q <= w_u_core_u_engine_u_memory_u_store_procmux_56649_Y[23:0];   
    reg [23:0] g_u_core_u_engine_u_memory_u_store_procdff_66968_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66968_Q = g_u_core_u_engine_u_memory_u_store_procdff_66968_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66968_q <= w_u_core_u_engine_u_memory_u_store_procmux_56647_Y[23:0];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66969_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66969_Q = g_u_core_u_engine_u_memory_u_store_procdff_66969_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66969_q <= w_u_core_u_engine_u_memory_u_store_procmux_56645_Y[31:0];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66970_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66970_Q = g_u_core_u_engine_u_memory_u_store_procdff_66970_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66970_q <= w_u_core_u_engine_u_memory_u_store_procmux_56643_Y[31:0];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66971_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66971_Q = g_u_core_u_engine_u_memory_u_store_procdff_66971_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66971_q <= w_u_core_u_engine_u_memory_u_store_procmux_56641_Y[31:0];   
    reg [31:0] g_u_core_u_engine_u_memory_u_store_procdff_66972_q;
    assign w_u_core_u_engine_u_memory_u_store_procdff_66972_Q = g_u_core_u_engine_u_memory_u_store_procdff_66972_q;
    always @(posedge clk) g_u_core_u_engine_u_memory_u_store_procdff_66972_q <= w_u_core_u_engine_u_memory_u_store_procmux_56639_Y[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55855_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9277_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[511:480];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55857_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9276_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[479:448];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55859_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9275_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[447:416];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55861_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9274_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[415:384];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55863_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9273_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[383:352];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55865_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9272_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[351:320];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55867_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9271_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[319:288];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55869_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9270_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[287:256];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55871_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9269_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[255:224];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55873_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9268_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[223:192];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55875_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9267_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[191:160];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55877_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9266_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[159:128];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55879_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9265_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[127:96];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55881_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9264_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[95:64];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55883_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9263_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[63:32];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55885_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9262_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55887_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9163_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[511:480];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55889_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9162_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[479:448];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55891_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9161_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[447:416];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55893_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9160_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[415:384];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55895_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9159_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[383:352];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55897_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9158_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[351:320];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55899_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9157_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[319:288];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55901_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9156_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[287:256];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55903_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9155_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[255:224];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55905_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9154_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[223:192];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55907_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9153_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[191:160];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55909_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9152_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[159:128];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55911_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9151_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[127:96];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55913_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9150_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[95:64];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55915_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9149_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[63:32];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55917_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9148_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55919_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9049_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[511:480];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55921_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9048_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[479:448];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55923_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9047_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[447:416];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55925_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9046_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[415:384];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55927_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9045_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[383:352];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55929_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9044_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[351:320];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55931_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9043_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[319:288];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55933_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9042_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[287:256];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55935_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9041_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[255:224];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55937_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9040_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[223:192];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55939_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9039_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[191:160];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55941_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9038_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[159:128];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55943_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9037_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[127:96];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55945_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9036_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[95:64];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55947_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9035_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[63:32];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55949_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_9034_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55951_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8935_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[511:480];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55953_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8934_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[479:448];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55955_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8933_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[447:416];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55957_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8932_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[415:384];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55959_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8931_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[383:352];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55961_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8930_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[351:320];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55963_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8929_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[319:288];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55965_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8928_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[287:256];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55967_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8927_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[255:224];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55969_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8926_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[223:192];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55971_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8925_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[191:160];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55973_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8924_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[159:128];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55975_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8923_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[127:96];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55977_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8922_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[95:64];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55979_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8921_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[63:32];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55981_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_90_8920_Y[0] ? w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55983_Y = w_u_core_u_engine_u_memory_u_store_logic_or_ot_hgi_sfu_static_operand_store_sv_81_8917_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procdff_66958_Q[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55986_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8911_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_55989_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55989_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8909_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_55992_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55992_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8907_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_55995_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55995_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8905_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_55998_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_55998_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8903_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56001_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56001_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8901_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56004_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56004_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8899_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56007_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56007_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8897_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56010_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56010_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8895_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56013_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56013_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8893_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56016_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56016_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8891_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56019_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56019_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8889_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56022_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56022_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8887_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56025_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56025_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8885_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56028_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56028_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8883_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56031_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56031_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8881_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56034_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56034_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8879_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56037_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56037_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8877_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56040_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56040_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8875_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56043_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56043_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8873_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56046_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56046_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8871_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56049_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56049_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8869_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56052_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56052_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8867_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56055_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56055_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8865_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56058_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56058_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8863_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56061_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56061_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8861_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56064_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56064_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8859_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56067_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56067_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8857_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56070_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56070_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8855_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56073_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56073_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8853_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56076_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56076_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8851_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56079_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56079_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8849_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56082_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56082_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8847_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56085_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56085_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8845_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56088_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56088_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8843_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56091_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56091_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8841_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56094_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56094_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8839_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56097_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56097_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8837_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56100_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56100_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8835_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56103_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56103_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8833_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56106_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56106_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8831_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56109_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56109_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8829_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56112_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56112_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8827_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56115_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56115_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8825_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56118_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56118_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8823_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56121_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56121_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8821_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56124_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56124_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8819_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56127_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56127_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8817_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56130_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56130_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8815_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56133_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56133_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8813_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56136_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56136_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8811_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56139_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56139_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8809_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56142_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56142_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8807_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56145_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56145_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8805_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56148_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56148_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8803_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56151_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56151_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8801_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56154_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56154_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8799_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56157_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56157_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8797_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56160_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56160_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8795_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56163_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56163_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8793_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56166_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56166_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8791_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56169_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56169_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8789_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56172_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56172_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8787_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56175_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56175_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_77_8785_Y[0] ? 1'b1 : 1'b0;   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56178_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_74_8783_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56181_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56181_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_74_8781_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56184_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56184_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8779_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56187_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56187_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8777_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56190_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56190_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8775_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56193_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56193_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8773_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56196_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56196_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8771_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56199_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56199_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8769_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56202_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56202_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8767_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56205_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56205_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_72_8765_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56208_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56208_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8763_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56211_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56211_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8759_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56214_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56214_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8755_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56217_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56217_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8751_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56220_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56220_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8747_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56223_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56223_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8745_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56226_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56226_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8741_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56229_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56229_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8737_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56232_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56232_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8733_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56235_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56235_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8729_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56238_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56238_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8727_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56241_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56241_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8723_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56244_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56244_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8719_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56247_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56247_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8715_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56250_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56250_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8711_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56253_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56253_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8709_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56256_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56256_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8705_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56259_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56259_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8701_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56262_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56262_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8697_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56265_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56265_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8693_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56268_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56268_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8691_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56271_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56271_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8687_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56274_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56274_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8683_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56277_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56277_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8679_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56280_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56280_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8675_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56283_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56283_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8673_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56286_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56286_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8669_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56289_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56289_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8665_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56292_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56292_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8661_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56295_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56295_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8657_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56298_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56298_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8655_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56301_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56301_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8651_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56304_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56304_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8647_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56307_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56307_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8643_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56310_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56310_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8639_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56313_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56313_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8637_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56316_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56316_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8633_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56319_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56319_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8629_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56322_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56322_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8625_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56325_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56325_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8621_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56328_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56328_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8619_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56331_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56331_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8615_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56334_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56334_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8611_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56337_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56337_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8607_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56340_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56340_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8603_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56343_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56343_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8601_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56346_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56346_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8597_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56349_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56349_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8593_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56352_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56352_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8589_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56355_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56355_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8585_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56358_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56358_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8583_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56361_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56361_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8579_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56364_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56364_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8575_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56367_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56367_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8571_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56370_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56370_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8567_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56373_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56373_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8565_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56376_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56376_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8561_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56379_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56379_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8557_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56382_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56382_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8553_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56385_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56385_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8549_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56388_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56388_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8547_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56391_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56391_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8543_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56394_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56394_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8539_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56397_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56397_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8535_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56400_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56400_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8531_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56403_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56403_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8529_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56406_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56406_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8525_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56409_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56409_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8521_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56412_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56412_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8517_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56415_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56415_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8513_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56418_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56418_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8511_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56421_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56421_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8507_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56424_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56424_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8503_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56427_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56427_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8499_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56430_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56430_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8495_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56433_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56433_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8493_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56436_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56436_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8489_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56439_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56439_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8485_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56442_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56442_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_69_8481_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56445_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56445_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_67_8477_Y[0] ? 1'b1 : 1'b0;   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56448_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8438_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56451_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56451_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8433_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56454_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56454_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8428_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56457_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56457_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8423_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56460_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56460_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8418_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56463_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56463_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8413_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56466_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56466_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8408_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56469_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56469_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8403_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56472_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56472_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8398_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56475_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56475_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8393_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56478_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56478_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8388_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56481_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56481_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8383_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56484_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56484_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8378_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56487_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56487_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8373_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56490_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56490_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8368_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56493_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56493_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8363_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56496_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56496_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8358_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56499_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56499_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8353_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56502_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56502_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8348_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56505_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56505_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8343_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56508_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56508_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8338_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56511_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56511_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8333_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56514_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56514_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8328_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56517_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56517_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8323_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56520_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56520_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8318_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56523_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56523_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8313_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56526_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56526_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8308_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56529_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56529_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8303_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56532_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56532_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8298_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56535_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56535_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8293_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56538_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56538_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8288_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56541_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56541_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8283_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56544_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56544_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8278_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56547_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56547_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8273_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56550_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56550_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8268_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56553_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56553_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8263_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56556_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56556_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8258_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56559_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56559_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8253_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56562_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56562_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8248_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56565_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56565_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8243_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56568_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56568_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8238_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56571_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56571_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8233_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56574_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56574_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8228_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56577_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56577_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8223_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56580_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56580_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8218_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56583_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56583_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8213_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56586_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56586_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8208_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56589_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56589_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8203_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56592_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56592_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8198_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56595_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56595_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8193_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56598_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56598_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8188_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56601_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56601_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8183_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56604_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56604_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8178_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56607_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56607_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8173_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56610_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56610_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8168_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56613_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56613_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8163_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56616_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56616_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8158_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56619_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56619_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8153_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56622_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56622_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8148_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56625_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56625_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8143_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56628_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56628_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8138_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56631_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56631_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8133_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56634_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56634_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8128_Y[0] ? 1'b1 : w_u_core_u_engine_u_memory_u_store_procmux_56637_Y[0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56637_Y = w_u_core_u_engine_u_memory_u_store_logic_and_ot_hgi_sfu_static_operand_store_sv_60_8123_Y[0] ? 1'b1 : 1'b0;   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56639_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[3] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_data[127:96] : w_u_core_u_engine_u_memory_u_store_procdff_66972_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56641_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[2] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_data[95:64] : w_u_core_u_engine_u_memory_u_store_procdff_66971_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56643_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[1] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_data[63:32] : w_u_core_u_engine_u_memory_u_store_procdff_66970_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56645_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[0] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_data[31:0] : w_u_core_u_engine_u_memory_u_store_procdff_66969_Q[31:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56647_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[3] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load_addr[95:72] : w_u_core_u_engine_u_memory_u_store_procdff_66968_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56649_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[2] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load_addr[71:48] : w_u_core_u_engine_u_memory_u_store_procdff_66967_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56651_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[1] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load_addr[47:24] : w_u_core_u_engine_u_memory_u_store_procdff_66966_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_procmux_56653_Y = w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load[0] ? w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load_addr[23:0] : w_u_core_u_engine_u_memory_u_store_procdff_66965_Q[23:0];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8476_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[23:15];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8494_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[47:39];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8512_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[71:63];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8530_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[95:87];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8548_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[119:111];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8566_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[143:135];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8584_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[167:159];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8602_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[191:183];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8620_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[215:207];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8638_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[239:231];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8656_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[263:255];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8674_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[287:279];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8692_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[311:303];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8710_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[335:327];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8728_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[359:351];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_67_8746_Y = |w_u_sfucore_Q_opstore_b_cmd3_Q[383:375];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8480_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[23:15];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8484_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[47:39];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8488_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[23:15];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8492_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[47:39];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8498_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[71:63];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8502_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[95:87];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8506_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[71:63];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8510_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[95:87];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8516_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[119:111];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8520_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[143:135];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8524_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[119:111];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8528_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[143:135];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8534_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[167:159];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8538_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[191:183];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8542_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[167:159];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8546_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[191:183];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8552_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[215:207];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8556_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[239:231];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8560_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[215:207];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8564_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[239:231];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8570_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[263:255];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8574_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[287:279];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8578_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[263:255];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8582_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[287:279];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8588_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[311:303];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8592_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[335:327];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8596_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[311:303];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8600_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[335:327];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8606_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[359:351];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8610_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[383:375];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8614_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[359:351];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8618_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[383:375];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8624_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[407:399];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8628_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[431:423];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8632_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[407:399];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8636_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[431:423];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8642_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[455:447];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8646_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[479:471];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8650_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[455:447];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8654_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[479:471];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8660_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[503:495];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8664_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[527:519];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8668_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[503:495];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8672_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[527:519];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8678_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[551:543];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8682_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[575:567];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8686_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[551:543];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8690_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[575:567];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8696_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[599:591];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8700_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[623:615];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8704_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[599:591];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8708_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[623:615];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8714_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[647:639];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8718_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[671:663];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8722_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[647:639];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8726_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[671:663];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8732_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[695:687];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8736_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[719:711];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8740_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[695:687];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8744_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[719:711];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8750_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[743:735];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8754_Y = |w_u_sfucore_Q_opstore_a_cmd1_Q[767:759];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8758_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[743:735];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_69_8762_Y = |w_u_sfucore_Q_opstore_b_cmd1_Q[767:759];   
    assign w_u_core_u_engine_u_memory_u_store_reduce_or_ot_hgi_sfu_static_operand_store_sv_81_8916_Y = |{w_u_core_u_engine_u_memory_u_store_u_output_flt[0], w_u_sfucore_Q_opstore_b_store1_flt[0], w_u_sfucore_Q_opstore_b_store0_flt[0], w_u_sfucore_Q_opstore_a_store1_flt[0], w_u_sfucore_Q_opstore_a_store0_flt[0]};   
     
    ot_hgi_su_lgroup2_drain #(.AW(24), .LWB(15), .M(16), .MACRO(1), .MUT_XBAR(0), .N(16), .NLW(16), .NS(2)) u_u_core_u_engine_u_memory_u_store_u_output (
        .clk(clk),
        .flt(w_u_core_u_engine_u_memory_u_store_u_output_flt),
        .lw(w_u_sfucore_Q_opstore_b_cmd6_Q[15:0]),
        .lwa(w_u_sfucore_Q_opstore_b_cmd3_Q[383:0]),
        .lwd(w_u_sfucore_Q_opstore_b_cmd4_Q[511:0]),
        .rst_n(w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0]),
        .sr_addr(w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[33:4]),
        .sr_d(w_u_core_u_engine_u_memory_u_store_u_output_sr_d),
        .sr_rv(w_u_core_u_engine_u_memory_u_store_u_output_sr_rv),
        .sr_v(w_u_sfucore_Q_ctl_u_core_u_vm_drain_v[1:0])
    );
     
    wire[151:0]storeA_meta87_D;
        wire storeA_ctl_reset_n;
        wire[2055:0]storeA_capture_rr_D;
    wire[2047:0]storeA_capture_payload_D;
                    assign storeA_capture_rr_D={xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2_q[513:0], xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1_q[513:0], xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0_q[513:0], L54_i_q[509:0], L127_i_q[3:0]};
    for(genvar rb=0;rb<8;rb=rb+1)assign storeA_capture_payload_D[256*rb+:256]=storeA_capture_rr_D[257*rb+:256];
        ot_hgi_sfu_ctl_storeA_regional_export u_u_sfucore_Q_ctl (
        .storeA_meta87_D(storeA_meta87_D),
        .storeA_ctl_reset_n(storeA_ctl_reset_n),
        .clk(clk),
        .rst_n(rst_n_t22),
        .u_core_procdff_66891__Q(w_u_sfucore_Q_ctl_u_core_procdff_66891_Q),
        .u_core_procdff_66896__D({xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__7_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__6_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__5_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__4_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__3_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__2_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__1_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66896_D__0_q[0]}),
        .u_core_procdff_66896__Q(w_u_sfucore_Q_ctl_u_core_procdff_66896_Q),
        .u_core_procdff_66901__D({w_u_sfucore_Q_lane15_lane_ro_v[0], w_u_sfucore_Q_lane14_lane_ro_v[0], xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__3_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__2_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__1_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__0_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__5_q[0], xi_u_sfucore_Q_ctl_u_core_procdff_66901_D__4_q[0]}),
        .u_core_procdff_66901__Q(w_u_sfucore_Q_ctl_u_core_procdff_66901_Q),
        .u_core_procdff_66906__D({xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__7_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__6_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__5_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__4_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__3_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__2_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__1_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66906_D__0_q[31:0]}),
        .u_core_procdff_66906__Q(w_u_sfucore_Q_ctl_u_core_procdff_66906_Q),
        .u_core_procdff_66911__D({w_u_sfucore_Q_lane15_lane_ro_x[31:0], w_u_sfucore_Q_lane14_lane_ro_x[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__3_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__2_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__1_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__0_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__5_q[31:0], xi_u_sfucore_Q_ctl_u_core_procdff_66911_D__4_q[31:0]}),
        .u_core_procdff_66911__Q(w_u_sfucore_Q_ctl_u_core_procdff_66911_Q),
        .u_core_procdff_66916__Q(w_u_sfucore_Q_ctl_u_core_procdff_66916_Q),
        .u_core_procdff_66921__Q(w_u_sfucore_Q_ctl_u_core_procdff_66921_Q),
        .u_core_procdff_66926__D({xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__2_q[513:0], xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__1_q[513:0], xi_u_sfucore_Q_ctl_u_core_procdff_66926_D__0_q[513:0], L54_i_q[509:0], L127_i_q[3:0]}),
        .u_core_procdff_66931__D({xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__2_q[1:0], xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__1_q[1:0], xi_u_sfucore_Q_ctl_u_core_procdff_66931_D__0_q[1:0], L54_i_q[511:510]}),
        .u_core_procdff_66936__D(xi_u_sfucore_Q_ctl_u_core_procdff_66936_D_q[470:0]),
        .u_core_procdff_66936__Q(w_u_sfucore_Q_ctl_u_core_procdff_66936_Q),
        .u_core_procdff_66941__D(xi_u_sfucore_Q_ctl_u_core_procdff_66941_D_q[1741:0]),
        .u_core_u_engine_logic_or_ot_hgi_sfu_static_engine_sp2_sv_72_8058__A(w_u_core_u_engine_u_memory_u_store_procdff_66958_Q[0]),
        .u_core_u_engine_reduce_or_ot_hgi_sfu_static_engine_sp2_sv_72_8057__A({w_u_sfucore_Q_lane15_lane_fault[0], w_u_sfucore_Q_lane14_lane_fault[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__4_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__3_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__2_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__1_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__12_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__11_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__10_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__9_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__8_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__7_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__6_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__5_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__1ba633cf__0_q[0], L54_i_q[513]}),
        .u_core_u_engine_reduce_or_ot_hgi_sfu_static_engine_sp2_sv_72_8059__A({w_u_sfucore_Q_lane15_lane_coll[0], w_u_sfucore_Q_lane14_lane_coll[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__4_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__3_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__2_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__1_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__12_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__11_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__10_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__9_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__8_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__7_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__6_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__5_q[0], xi_u_sfucore_Q_ctl_u_core_u_engine_reduce_or_ot_hgi_sfu_static__023e3182__0_q[0], L54_i_q[512]}),
        .u_core_u_engine_u_arithmetic_procdff_71639__Q(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q),
        .u_core_u_rst__rst_n(w_u_sfucore_Q_ctl_u_core_u_rst_rst_n),
        .u_core_u_vm__drain_data(w_u_core_u_engine_u_memory_u_store_u_output_sr_d[511:0]),
        .u_core_u_vm__drain_result_v(w_u_core_u_engine_u_memory_u_store_u_output_sr_rv[1:0]),
        .u_core_u_vm__drain_v(w_u_sfucore_Q_ctl_u_core_u_vm_drain_v),
        .u_core_u_vm__scalar_data(w_u_sfucore_Q_ctl_u_core_u_vm_scalar_data),
        .u_core_u_vm__scalar_load(w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load),
        .u_core_u_vm__scalar_load_addr(w_u_sfucore_Q_ctl_u_core_u_vm_scalar_load_addr),
        .u_core_u_vm__stage_addr(w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr),
        .u_core_u_vm__stage_data(w_u_sfucore_Q_ctl_u_core_u_vm_stage_data),
        .u_core_u_vm__stage_group(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group),
        .u_core_u_vm__stage_mask(w_u_sfucore_Q_ctl_u_core_u_vm_stage_mask),
        .u_core_u_vm__stage_v(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v)
    );
     
    ot_hnx_sfu_lane__cf694489f05c u_u_sfucore_Q_lane14 (
        .lane_coll(w_u_sfucore_Q_lane14_lane_coll),
        .lane_fault(w_u_sfucore_Q_lane14_lane_fault),
        .lane_kv_waddr(w_u_sfucore_Q_lane14_lane_kv_waddr),
        .lane_kv_wdata(w_u_sfucore_Q_lane14_lane_kv_wdata),
        .lane_kv_we(w_u_sfucore_Q_lane14_lane_kv_we),
        .lane_rd_addr(w_u_sfucore_Q_lane14_lane_rd_addr),
        .lane_rd_q({w_u_sfucore_Q_opstore_b_cmd0_Q[959:896], w_u_sfucore_Q_opstore_a_cmd0_Q[959:896]}),
        .lane_rd_re(w_u_sfucore_Q_lane14_lane_rd_re),
        .lane_rd_src(w_u_sfucore_Q_lane14_lane_rd_src),
        .lane_ro_v(w_u_sfucore_Q_lane14_lane_ro_v),
        .lane_ro_x(w_u_sfucore_Q_lane14_lane_ro_x),
        .lane_vi_addr(w_u_sfucore_Q_lane14_lane_vi_addr),
        .lane_vi_q(xi_u_sfucore_Q_lane14_lane_vi_q_q[31:0]),
        .lane_vi_re(w_u_sfucore_Q_lane14_lane_vi_re),
        .lane_vm_waddr(w_u_sfucore_Q_lane14_lane_vm_waddr),
        .lane_vm_wdata(w_u_sfucore_Q_lane14_lane_vm_wdata),
        .lane_vm_we(w_u_sfucore_Q_lane14_lane_vm_we),
        .map_clk(clk),
        .map_i_emit(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[539]),
        .map_i_i_v(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[513:490]),
        .map_i_krow(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[313:290]),
        .map_i_ls(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[441:438]),
        .map_i_lvw(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[437:434]),
        .map_i_o_v(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[537:514]),
        .map_i_pass({w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1021:1020], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[538], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[489:442], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[433:314], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[289:0]}),
        .map_lane_j(strap_u_sfucore_Q_lane14_map_lane_j[3:0]),
        .map_ld_terms(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1019:540]),
        .map_rst_n(rst_n)
    );
     
    ot_hnx_sfu_lane__cf694489f05c u_u_sfucore_Q_lane15 (
        .lane_coll(w_u_sfucore_Q_lane15_lane_coll),
        .lane_fault(w_u_sfucore_Q_lane15_lane_fault),
        .lane_kv_waddr(w_u_sfucore_Q_lane15_lane_kv_waddr),
        .lane_kv_wdata(w_u_sfucore_Q_lane15_lane_kv_wdata),
        .lane_kv_we(w_u_sfucore_Q_lane15_lane_kv_we),
        .lane_rd_addr(w_u_sfucore_Q_lane15_lane_rd_addr),
        .lane_rd_q({w_u_sfucore_Q_opstore_b_cmd0_Q[1023:960], w_u_sfucore_Q_opstore_a_cmd0_Q[1023:960]}),
        .lane_rd_re(w_u_sfucore_Q_lane15_lane_rd_re),
        .lane_rd_src(w_u_sfucore_Q_lane15_lane_rd_src),
        .lane_ro_v(w_u_sfucore_Q_lane15_lane_ro_v),
        .lane_ro_x(w_u_sfucore_Q_lane15_lane_ro_x),
        .lane_vi_addr(w_u_sfucore_Q_lane15_lane_vi_addr),
        .lane_vi_q(xi_u_sfucore_Q_lane15_lane_vi_q_q[31:0]),
        .lane_vi_re(w_u_sfucore_Q_lane15_lane_vi_re),
        .lane_vm_waddr(w_u_sfucore_Q_lane15_lane_vm_waddr),
        .lane_vm_wdata(w_u_sfucore_Q_lane15_lane_vm_wdata),
        .lane_vm_we(w_u_sfucore_Q_lane15_lane_vm_we),
        .map_clk(clk),
        .map_i_emit(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[539]),
        .map_i_i_v(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[513:490]),
        .map_i_krow(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[313:290]),
        .map_i_ls(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[441:438]),
        .map_i_lvw(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[437:434]),
        .map_i_o_v(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[537:514]),
        .map_i_pass({w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1021:1020], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[538], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[489:442], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[433:314], w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[289:0]}),
        .map_lane_j(strap_u_sfucore_Q_lane15_map_lane_j[3:0]),
        .map_ld_terms(w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q[1019:540]),
        .map_rst_n(rst_n)
    );
     
    ot_hnx_sfu_store_a_regional4_captured u_u_sfucore_Q_opstore_a (
        .capture_payload_D(storeA_capture_payload_D),
        .capture_meta87_D(storeA_meta87_D),
        .capture_ctl_reset_n(storeA_ctl_reset_n),
        .capture_meta_reset_n(rst_n_t22),
        .cmd0_Q(w_u_sfucore_Q_opstore_a_cmd0_Q),
        .cmd1_D({w_u_sfucore_Q_lane15_lane_rd_addr[47:0], w_u_sfucore_Q_lane14_lane_rd_addr[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__5_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__4_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__3_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__2_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__13_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__12_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__11_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__10_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__9_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__8_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__7_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__6_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__1_q[47:0], xi_u_sfucore_Q_opstore_a_cmd1_D__0_q[47:0]}),
        .cmd1_Q(w_u_sfucore_Q_opstore_a_cmd1_Q),
        .cmd2_D({w_u_sfucore_Q_lane15_lane_rd_src[3:0], w_u_sfucore_Q_lane14_lane_rd_src[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__5_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__4_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__3_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__2_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__13_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__12_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__11_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__10_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__9_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__8_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__7_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__6_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__1_q[3:0], xi_u_sfucore_Q_opstore_a_cmd2_D__0_q[3:0]}),
        .cmd2_Q(w_u_sfucore_Q_opstore_a_cmd2_Q),
        .cmd3_D({w_u_sfucore_Q_lane15_lane_rd_re[1:0], w_u_sfucore_Q_lane14_lane_rd_re[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__5_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__4_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__3_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__2_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__13_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__12_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__11_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__10_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__9_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__8_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__7_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__6_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__1_q[1:0], xi_u_sfucore_Q_opstore_a_cmd3_D__0_q[1:0]}),
        .cmd3_Q(w_u_sfucore_Q_opstore_a_cmd3_Q),
        .comb128_A(w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[0]),
        .comb144_A(w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[1]),
        .comb48_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[31:0]),
        .comb48_S(w_u_core_u_engine_u_memory_u_store_procdff_66952_Q[0]),
        .comb49_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[63:32]),
        .comb50_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[95:64]),
        .comb51_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[127:96]),
        .comb52_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[159:128]),
        .comb53_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[191:160]),
        .comb54_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[223:192]),
        .comb55_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[255:224]),
        .comb56_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[287:256]),
        .comb57_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[319:288]),
        .comb58_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[351:320]),
        .comb59_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[383:352]),
        .comb60_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[415:384]),
        .comb61_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[447:416]),
        .comb62_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[479:448]),
        .comb63_B(w_u_core_u_engine_u_memory_u_store_procdff_66951_Q[511:480]),
        .comb64_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[31:0]),
        .comb64_S(w_u_core_u_engine_u_memory_u_store_procdff_66949_Q[0]),
        .comb65_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[63:32]),
        .comb66_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[95:64]),
        .comb67_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[127:96]),
        .comb68_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[159:128]),
        .comb69_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[191:160]),
        .comb70_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[223:192]),
        .comb71_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[255:224]),
        .comb72_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[287:256]),
        .comb73_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[319:288]),
        .comb74_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[351:320]),
        .comb75_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[383:352]),
        .comb76_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[415:384]),
        .comb77_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[447:416]),
        .comb78_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[479:448]),
        .comb79_B(w_u_core_u_engine_u_memory_u_store_procdff_66948_Q[511:480]),
        .store0_clk(clk),
        .store0_flt(w_u_sfucore_Q_opstore_a_store0_flt),
        .store0_rst_n(w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0]),
        .store1_flt(w_u_sfucore_Q_opstore_a_store1_flt)
    );
     
    ot_hnx_sfu_store_b__1300886e9f18 u_u_sfucore_Q_opstore_b (
        .cmd0_Q(w_u_sfucore_Q_opstore_b_cmd0_Q),
        .cmd1_D({w_u_sfucore_Q_lane15_lane_rd_addr[95:48], w_u_sfucore_Q_lane14_lane_rd_addr[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__5_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__4_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__3_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__2_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__13_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__12_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__11_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__10_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__9_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__8_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__7_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__6_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__1_q[95:48], xi_u_sfucore_Q_opstore_a_cmd1_D__0_q[95:48]}),
        .cmd1_Q(w_u_sfucore_Q_opstore_b_cmd1_Q),
        .cmd2_D({w_u_sfucore_Q_lane15_lane_rd_src[7:4], w_u_sfucore_Q_lane14_lane_rd_src[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__5_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__4_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__3_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__2_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__13_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__12_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__11_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__10_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__9_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__8_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__7_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__6_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__1_q[7:4], xi_u_sfucore_Q_opstore_a_cmd2_D__0_q[7:4]}),
        .cmd2_Q(w_u_sfucore_Q_opstore_b_cmd2_Q),
        .cmd3_D({w_u_sfucore_Q_lane15_lane_vm_waddr[23:0], w_u_sfucore_Q_lane14_lane_vm_waddr[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__5_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__4_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__3_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__2_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__13_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__12_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__11_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__10_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__9_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__8_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__7_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__6_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__1_q[23:0], xi_u_sfucore_Q_opstore_b_cmd3_D__0_q[23:0]}),
        .cmd3_Q(w_u_sfucore_Q_opstore_b_cmd3_Q),
        .cmd4_D({w_u_sfucore_Q_lane15_lane_vm_wdata[31:0], w_u_sfucore_Q_lane14_lane_vm_wdata[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__5_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__4_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__3_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__2_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__13_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__12_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__11_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__10_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__9_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__8_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__7_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__6_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__1_q[31:0], xi_u_sfucore_Q_opstore_b_cmd4_D__0_q[31:0]}),
        .cmd4_Q(w_u_sfucore_Q_opstore_b_cmd4_Q),
        .cmd5_D({w_u_sfucore_Q_lane15_lane_rd_re[3:2], w_u_sfucore_Q_lane14_lane_rd_re[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__5_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__4_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__3_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__2_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__13_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__12_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__11_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__10_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__9_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__8_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__7_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__6_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__1_q[3:2], xi_u_sfucore_Q_opstore_a_cmd3_D__0_q[3:2]}),
        .cmd5_Q(w_u_sfucore_Q_opstore_b_cmd5_Q),
        .cmd6_D({w_u_sfucore_Q_lane15_lane_vm_we[0], w_u_sfucore_Q_lane14_lane_vm_we[0], xi_u_sfucore_Q_opstore_b_cmd6_D__5_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__4_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__3_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__2_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__13_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__12_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__11_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__10_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__9_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__8_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__7_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__6_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__1_q[0], xi_u_sfucore_Q_opstore_b_cmd6_D__0_q[0]}),
        .cmd6_Q(w_u_sfucore_Q_opstore_b_cmd6_Q),
        .comb128_A(w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[2]),
        .comb144_A(w_u_sfucore_Q_ctl_u_core_procdff_66936_Q[3]),
        .comb32_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[0]),
        .comb33_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[1]),
        .comb34_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[2]),
        .comb35_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[3]),
        .comb36_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[4]),
        .comb37_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[5]),
        .comb38_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[6]),
        .comb39_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_v[7]),
        .comb48_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[31:0]),
        .comb48_S(w_u_core_u_engine_u_memory_u_store_procdff_66946_Q[0]),
        .comb49_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[63:32]),
        .comb50_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[95:64]),
        .comb51_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[127:96]),
        .comb52_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[159:128]),
        .comb53_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[191:160]),
        .comb54_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[223:192]),
        .comb55_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[255:224]),
        .comb56_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[287:256]),
        .comb57_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[319:288]),
        .comb58_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[351:320]),
        .comb59_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[383:352]),
        .comb60_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[415:384]),
        .comb61_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[447:416]),
        .comb62_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[479:448]),
        .comb63_B(w_u_core_u_engine_u_memory_u_store_procdff_66945_Q[511:480]),
        .comb64_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[31:0]),
        .comb64_S(w_u_core_u_engine_u_memory_u_store_procdff_66943_Q[0]),
        .comb65_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[63:32]),
        .comb66_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[95:64]),
        .comb67_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[127:96]),
        .comb68_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[159:128]),
        .comb69_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[191:160]),
        .comb70_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[223:192]),
        .comb71_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[255:224]),
        .comb72_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[287:256]),
        .comb73_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[319:288]),
        .comb74_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[351:320]),
        .comb75_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[383:352]),
        .comb76_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[415:384]),
        .comb77_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[447:416]),
        .comb78_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[479:448]),
        .comb79_B(w_u_core_u_engine_u_memory_u_store_procdff_66942_Q[511:480]),
        .comb80_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[1:0]),
        .comb81_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[3:2]),
        .comb82_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[5:4]),
        .comb83_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[7:6]),
        .comb84_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[9:8]),
        .comb85_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[11:10]),
        .comb86_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[13:12]),
        .comb87_A(w_u_sfucore_Q_ctl_u_core_u_vm_stage_group[15:14]),
        .store0_clk(clk),
        .store0_flt(w_u_sfucore_Q_opstore_b_store0_flt),
        .store0_rst_n(w_u_sfucore_Q_ctl_u_core_u_rst_rst_n[0]),
        .store0_sw_addr(w_u_sfucore_Q_ctl_u_core_u_vm_stage_addr[119:0]),
        .store0_sw_d(w_u_sfucore_Q_ctl_u_core_u_vm_stage_data[2047:0]),
        .store0_sw_mask(w_u_sfucore_Q_ctl_u_core_u_vm_stage_mask[63:0]),
        .store1_flt(w_u_sfucore_Q_opstore_b_store1_flt)
    );
endmodule
